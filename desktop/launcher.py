"""康师复桌面启动器。

一个进程负责三件事：
1. 用子进程起本机视觉服务，固定 127.0.0.1:8802，前端写死了这个地址。
2. 起一个只监听 127.0.0.1 的静态页面服务，把 frontend/ 原样发出去，端口自动选。
3. 打开窗口。优先内嵌 WebView，拿不到摄像头时回退系统默认浏览器。

摄像头画面只在本机两个进程之间传输，不出这台电脑。云端只承载账号、计划、
训练结果与报告。训练辅助，非医疗诊断。
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "KangShiFu"
APP_TITLE = "康师复 | 智能康复协作平台"
VISION_HOST = "127.0.0.1"
# 前端 frontend/app.js 把本机视觉服务写死在 127.0.0.1:8802，这里不能改。
VISION_PORT = 8802
DEFAULT_API_BASE = "http://127.0.0.1:8801/api/v1"
FROZEN = bool(getattr(sys, "frozen", False))
IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"

# 子进程里冒出来的噪音日志，过滤掉，避免日志被刷屏。
NOISE_MARKERS = (
    "objc[",
    "Class AVF",
    "is implemented in both",
    '"POST /api/live/',
    '"GET /healthz',
    '"OPTIONS /api/live/',
)


# ---------------------------------------------------------------- 路径

def resource_root() -> Path:
    """打包后是 PyInstaller 的资源目录，开发时是仓库根目录。"""
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def vision_dir() -> Path:
    """视觉服务的 config/ 与 models/ 所在目录。"""
    if FROZEN:
        return resource_root()
    return resource_root() / "algorithm" / "rehab-pose-demo"


def frontend_dir() -> Path:
    if FROZEN:
        return resource_root() / "frontend"
    return resource_root() / "frontend"


def user_base_dirs() -> tuple[Path, Path]:
    """返回（日志目录，状态目录）。一律写用户目录，不写安装目录。"""
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / APP_NAME
        return base / "Logs", base
    if IS_MACOS:
        return (Path.home() / "Library" / "Logs" / APP_NAME,
                Path.home() / "Library" / "Application Support" / APP_NAME)
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")) / APP_NAME
    return base / "logs", base


# ---------------------------------------------------------------- 日志

_LOG_LOCK = threading.Lock()
_LOG_PATH: Path | None = None


def log_path() -> Path:
    global _LOG_PATH
    if _LOG_PATH is None:
        directory = user_base_dirs()[0]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "launcher.log"
        # 简单按大小轮转，只留一份历史，日志不会无限长。
        try:
            if path.exists() and path.stat().st_size > 2_000_000:
                path.replace(directory / "launcher.log.1")
        except OSError:
            pass
        _LOG_PATH = path
    return _LOG_PATH


def log(message: str) -> None:
    """只写我们自己的文字与子进程的状态行。

    画面数据、关键点、登录令牌都不会经过这里：视觉服务的逐帧访问日志被
    NOISE_MARKERS 过滤掉，云端地址只记协议与主机名，不记路径与参数。
    """
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), message)
    with _LOG_LOCK:
        try:
            with log_path().open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass
    try:
        print(line, flush=True)
    except (ValueError, OSError):
        pass


# ---------------------------------------------------------------- 配置

def read_cloud_base() -> tuple[str, str]:
    """决定前端该把云端接口指向哪里，返回（地址，来源说明）。

    顺序：环境变量 REHAB_CLOUD_BASE，安装目录旁的 config.json，用户目录的
    config.json，最后退回本机后端地址。仓库里不写任何真实地址。
    """
    raw = (os.environ.get("REHAB_CLOUD_BASE") or "").strip()
    if raw:
        return normalise_api_base(raw), "环境变量 REHAB_CLOUD_BASE"
    candidates = []
    if FROZEN:
        # Windows：exe 同目录。macOS：.app 里的 Contents/MacOS，以及 .app 的同级目录，
        # 后者才是用户能看见、能放文件的地方。
        executable = Path(sys.executable).resolve()
        candidates.append(executable.parent / "config.json")
        for level in (2, 3):
            if len(executable.parents) > level:
                candidates.append(executable.parents[level] / "config.json")
    candidates.append(user_base_dirs()[1] / "config.json")
    for path in candidates:
        try:
            if not path.is_file():
                continue
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        value = str(document.get("apiBase") or "").strip()
        if value:
            return normalise_api_base(value), "配置文件 %s" % path.name
    return DEFAULT_API_BASE, "默认本机后端（未配置云端地址）"


def normalise_api_base(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise SystemExit("云端地址必须以 http:// 或 https:// 开头，当前配置不合法")
    if not value.endswith("/api/v1"):
        value = value + "/api/v1"
    return value


def config_js_bytes(api_base: str) -> bytes:
    document = json.dumps({"apiBase": api_base}, ensure_ascii=False)
    text = ("// 由桌面启动器在运行时生成，请勿手工修改。\n"
            "window.REHAB_CONFIG = %s;\n" % document)
    return text.encode("utf-8")


def safe_origin(value: str) -> str:
    """日志里只留协议与主机名，不留路径与查询串。"""
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(value)
        return "%s://%s" % (parts.scheme, parts.hostname or "")
    except Exception:
        return "(无法解析)"


# ---------------------------------------------------------------- 端口

def port_free(port: int, host: str = VISION_HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def http_get(url: str, timeout: float = 2.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def vision_healthz(port: int = VISION_PORT, timeout: float = 2.0) -> dict | None:
    try:
        status, raw = http_get("http://%s:%d/healthz" % (VISION_HOST, port), timeout)
    except (urllib.error.URLError, OSError, TimeoutError):
        return None
    if status != 200:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return None


def describe_port_holder(port: int) -> str:
    """尽量说清 8802 被谁占了，说不清就诚实地说说不清。"""
    health = vision_healthz(port, timeout=1.0)
    if health and health.get("service") == "rehab-vision":
        return "端口上已经有一个康师复视觉服务在跑（可能是上一次没退干净，或者你手工起过 live_api.py）。"
    return "端口被另一个程序占用，不是康师复的视觉服务。"


# ---------------------------------------------------------------- 视觉服务子进程

def vision_child_command() -> list[str]:
    if FROZEN:
        return [sys.executable, "--vision-service"]
    return [sys.executable, str(Path(__file__).resolve()), "--vision-service"]


def vision_child_env(port: int) -> dict:
    env = dict(os.environ)
    # 本机模式：不开鉴权，只监听本机，不设任何反向代理相关变量。
    env["REHAB_VISION_BIND"] = VISION_HOST
    env["REHAB_VISION_PORT"] = str(port)
    env["REHAB_VISION_AUTH"] = "off"
    env.pop("REHAB_VISION_ORIGINS", None)
    env.pop("REHAB_VISION_PREFIX", None)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # 启动器被强杀时，子进程靠这个自己退出，不留残骸占着 8802。
    env["REHAB_PARENT_PID"] = str(os.getpid())
    return env


def parent_gone(pid: int) -> bool:
    """判断启动器还在不在。

    POSIX 上优先看自己的父进程号：启动器被强杀后我们会被过继给 1 号进程，
    ppid 立刻变化。只看 os.kill(pid, 0) 不够，被杀的父进程在被它自己的父进程
    回收之前是僵尸态，PID 还在，信号也发得出去。
    """
    if not IS_WINDOWS:
        return os.getppid() != pid
    return not process_alive(pid)


def watch_parent(pid: int) -> None:
    """父进程没了就跟着退。父进程正常退出时会先 terminate 我们，走不到这里。"""
    def loop():
        while True:
            time.sleep(3)
            if not parent_gone(pid):
                continue
            # 父进程一死，我们的 stdout 管道读端就关了，这里 print 会抛
            # BrokenPipeError。不兜住的话线程先死在这一句上，退出就永远执行不到。
            try:
                print("vision: 启动器已退出，视觉服务跟随退出", flush=True)
            except Exception:
                pass
            os._exit(0)
    threading.Thread(target=loop, daemon=True).start()


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        try:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        except Exception:
            return True
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_vision_service() -> int:
    """子进程入口：把视觉服务跑起来，行为与直接跑 live_api.py 一致。"""
    parent = int(os.environ.get("REHAB_PARENT_PID") or 0)
    if parent:
        watch_parent(parent)
    directory = vision_dir()
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    try:
        os.chdir(directory)
    except OSError:
        pass
    import live_api  # noqa: E402  打包后由 PyInstaller 提供
    live_api.main()
    return 0


class VisionService:
    def __init__(self, port: int = VISION_PORT):
        self.port = port
        self.process: subprocess.Popen | None = None
        self._pump: threading.Thread | None = None

    def start(self, wait_s: float = 90.0) -> None:
        creation = 0
        if IS_WINDOWS:
            creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            vision_child_command(),
            env=vision_child_env(self.port),
            cwd=str(vision_dir()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creation,
        )
        self._pump = threading.Thread(target=self._drain, daemon=True)
        self._pump.start()
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("视觉服务启动后立刻退出，退出码 %s，详情见日志" % self.process.returncode)
            if vision_healthz(self.port, timeout=1.0):
                log("视觉服务已就绪：http://%s:%d" % (VISION_HOST, self.port))
                return
            time.sleep(0.3)
        raise RuntimeError("视觉服务在 %.0f 秒内没有就绪" % wait_s)

    def _drain(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for raw in self.process.stdout:
            line = raw.rstrip()
            if not line or any(marker in line for marker in NOISE_MARKERS):
                continue
            log("[视觉] " + line)

    def stop(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        log("正在停止视觉服务")
        try:
            process.terminate()
            process.wait(timeout=8)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=5)
            except Exception:
                log("视觉服务无法结束，请手工检查进程 %s" % process.pid)


# ---------------------------------------------------------------- 静态页面服务

CONSOLE_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>康师复 桌面启动器</title>
<style>body{font-family:system-ui,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;
padding:48px 40px;background:#18332c;color:#f4f6f5;line-height:1.9}
h1{font-size:22px;margin:0 0 18px}p{margin:0 0 12px;font-size:15px}
code{background:rgba(255,255,255,.12);padding:2px 6px;border-radius:5px}
a.btn,button{display:inline-block;margin-top:20px;margin-right:12px;padding:10px 20px;border:0;
border-radius:10px;background:#f5c451;color:#18332c;font-size:15px;font-weight:600;cursor:pointer;
text-decoration:none}small{opacity:.72;display:block;margin-top:28px;font-size:13px}</style></head>
<body><h1>训练页面已在系统浏览器中打开</h1>
<p>请切换到浏览器窗口开始训练。地址是 <code>__URL__</code>。</p>
<p>浏览器没有自动打开时，点下面这个按钮再试一次。</p>
<p>训练结束后回到这个窗口点「退出程序」，或者直接关闭这个窗口，本机的视觉服务会一起停掉。</p>
<a class="btn" href="__URL__" target="_blank" rel="noopener">再打开一次训练页面</a>
<button onclick="fetch('/__quit').then(()=>{document.body.innerHTML='<h1>已退出，可以关闭这个窗口。</h1>'})">退出程序</button>
<small>摄像头画面只在本机处理，不上传云端。训练辅助，非医疗诊断。</small></body></html>
"""


class UIHandler(SimpleHTTPRequestHandler):
    server_version = "RehabDesktop/1.0"
    config_payload = b""
    console_payload = b""
    on_raise = None
    on_quit = None

    def log_message(self, fmt, *args):  # noqa: N802  静态资源访问不写日志
        return

    def send_response(self, code, message=None):
        # 本地页面被浏览器缓存后，改动会看起来"没生效"，一律不缓存。
        super().send_response(code, message)
        self.send_header("Cache-Control", "no-store")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route == "/config.js":
            return self._send(200, type(self).config_payload, "application/javascript; charset=utf-8")
        if route == "/__console":
            return self._send(200, type(self).console_payload, "text/html; charset=utf-8")
        if route == "/__raise":
            callback = type(self).on_raise
            if callback:
                threading.Thread(target=callback, daemon=True).start()
            return self._send(200, b'{"ok":true}', "application/json")
        if route == "/__quit":
            callback = type(self).on_quit
            if callback:
                threading.Thread(target=callback, daemon=True).start()
            return self._send(200, b'{"ok":true}', "application/json")
        return super().do_GET()


class StaticServer:
    def __init__(self, directory: Path, api_base: str):
        self.directory = directory
        handler = partial(UIHandler, directory=str(directory))
        self.httpd = ThreadingHTTPServer((VISION_HOST, 0), handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        UIHandler.config_payload = config_js_bytes(api_base)
        UIHandler.console_payload = CONSOLE_HTML.replace("__URL__", self.url).encode("utf-8")
        self._thread = threading.Thread(target=self.httpd.serve_forever,
                                        kwargs={"poll_interval": 0.25}, daemon=True)

    @property
    def url(self) -> str:
        return "http://%s:%d/index.html" % (VISION_HOST, self.port)

    @property
    def base(self) -> str:
        return "http://%s:%d" % (VISION_HOST, self.port)

    def start(self) -> None:
        self._thread.start()
        log("页面服务已就绪：%s" % self.base)

    def stop(self) -> None:
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass


# ---------------------------------------------------------------- 单实例

def instance_file() -> Path:
    directory = user_base_dirs()[1]
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "instance.json"


def try_wake_running_instance() -> bool:
    """已经有一份在跑就把它的窗口叫到前台，然后本次直接退出。"""
    path = instance_file()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    base = str(document.get("base") or "")
    if not base.startswith("http://127.0.0.1:"):
        return False
    try:
        status, _ = http_get(base + "/__raise", timeout=2.0)
    except (urllib.error.URLError, OSError, TimeoutError):
        return False
    return status == 200


def write_instance_file(base: str) -> None:
    try:
        instance_file().write_text(json.dumps({"pid": os.getpid(), "base": base,
                                               "started_at": int(time.time())}, ensure_ascii=False),
                                   encoding="utf-8")
    except OSError:
        pass


def clear_instance_file() -> None:
    try:
        instance_file().unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------- 窗口

def grant_macos_camera_permission() -> str:
    """给 pywebview 的 WKWebView 补上摄像头授权回调。

    WKWebView 收到 getUserMedia 时会问 WKUIDelegate 要许可，pywebview 6.2 没有
    实现这个回调，缺省行为是拒绝。这里用 pyobjc 把方法补到它的 delegate 类上。
    返回一句话描述结果，写进日志。
    """
    try:
        import objc
        from webview.platforms.cocoa import BrowserView
    except Exception as exc:
        return "未能加载 cocoa 后端，跳过摄像头授权补丁：%r" % (exc,)
    delegate = getattr(BrowserView, "BrowserDelegate", None)
    if delegate is None:
        return "pywebview 的 BrowserDelegate 结构与预期不同，跳过摄像头授权补丁"
    selector = b"webView:requestMediaCapturePermissionForOrigin:initiatedByFrame:type:decisionHandler:"
    if delegate.instancesRespondToSelector_(selector):
        return "pywebview 自带摄像头授权回调，无需补丁"

    def handler(self, webview_, origin, frame, capture_type, decision_handler):
        # 1 = WKPermissionDecisionGrant。页面来自 127.0.0.1，是我们自己起的服务。
        decision_handler(1)

    try:
        method = objc.selector(handler, selector=selector, signature=b"v@:@@@q@?")
        objc.classAddMethods(delegate, [method])
    except Exception as exc:
        return "摄像头授权补丁打不上：%r" % (exc,)
    return "已给 WKWebView 补上摄像头授权回调"


class Application:
    def __init__(self, args):
        self.args = args
        self.vision_port = int(getattr(args, "vision_port", VISION_PORT) or VISION_PORT)
        self.vision = VisionService(self.vision_port)
        self.static: StaticServer | None = None
        self.window = None
        self.stopping = threading.Event()
        self.cleaned = threading.Event()
        self.browser_mode = False

    # -- 生命周期 ----------------------------------------------------
    def run(self) -> int:
        api_base, source = read_cloud_base()
        log("康师复桌面启动器 %s / Python %s / %s" % (platform.platform(), platform.python_version(),
                                                  "打包版" if FROZEN else "源码版"))
        log("云端接口指向 %s，来源：%s" % (safe_origin(api_base), source))
        if api_base == DEFAULT_API_BASE:
            log("提示：没有配置云端地址，页面会去找本机 8801 端口的后端。"
                "正式使用请设置环境变量 REHAB_CLOUD_BASE，或在安装目录旁放 config.json。")

        if not self.args.allow_multiple and try_wake_running_instance():
            log("已经有一份康师复在运行，已把它的窗口叫到前台，本次退出。")
            return 0

        if self.vision_port != VISION_PORT:
            log("注意：视觉服务被指定在 %d 端口，而前端写死的是 %d，页面里的训练功能会连不上。"
                "这个选项只用于调试与自检。" % (self.vision_port, VISION_PORT))
        if not port_free(self.vision_port):
            log("本机 %d 端口被占用，无法启动视觉服务。%s"
                % (self.vision_port, describe_port_holder(self.vision_port)))
            log("请关掉占用该端口的程序后重新打开康师复。"
                "macOS 可以用 lsof -nP -iTCP:8802 -sTCP:LISTEN 查，"
                "Windows 可以用 netstat -ano | findstr 8802 查。")
            return 2

        self.static = StaticServer(frontend_dir(), api_base)
        UIHandler.on_raise = self.raise_window
        UIHandler.on_quit = self.request_stop
        self.static.start()
        write_instance_file(self.static.base)

        try:
            self.vision.start()
        except Exception as exc:
            log("视觉服务启动失败：%r" % (exc,))
            self.shutdown()
            return 3

        self._install_signals()
        try:
            self.open_ui()
        finally:
            self.shutdown()
        return 0

    def _install_signals(self) -> None:
        for name in ("SIGINT", "SIGTERM"):
            handler = getattr(signal, name, None)
            if handler is None:
                continue
            try:
                signal.signal(handler, lambda *_: self.request_stop())
            except (ValueError, OSError):
                pass

    def shutdown(self) -> None:
        # 注意不要用 self.stopping 当哨兵：request_stop() 已经把它置位了，
        # 用它挡重入会让真正的清理被跳过，视觉服务子进程就留在那里不退。
        if self.cleaned.is_set():
            return
        self.cleaned.set()
        self.stopping.set()
        self.vision.stop()
        if self.static is not None:
            self.static.stop()
        clear_instance_file()
        log("已退出。")

    def request_stop(self) -> None:
        self.stopping.set()
        if self.window is not None:
            try:
                self.window.destroy()
                return
            except Exception:
                pass

    # -- 界面 --------------------------------------------------------
    def open_ui(self) -> None:
        assert self.static is not None
        mode = (self.args.ui or os.environ.get("REHAB_DESKTOP_UI") or "webview").strip().lower()
        if mode not in ("webview", "browser", "none"):
            mode = "webview"
        if mode == "none":
            log("无界面模式：页面地址 %s，按 Ctrl+C 退出。" % self.static.url)
            self._block()
            return
        if mode == "webview":
            try:
                self._open_webview(self.static.url)
                return
            except Exception as exc:
                log("内嵌窗口打不开，改用系统默认浏览器：%r" % (exc,))
        self._open_browser(self.static.url)

    def _open_webview(self, url: str) -> None:
        import webview
        if IS_MACOS:
            log(grant_macos_camera_permission())
        self.window = webview.create_window(APP_TITLE, url, width=1200, height=840,
                                            min_size=(960, 640), confirm_close=False)
        log("内嵌窗口已打开。摄像头如果拿不到画面，请改用浏览器模式，见 desktop/README.md。")
        webview.start()

    def _open_browser(self, url: str) -> None:
        self.browser_mode = True
        log("正在用系统默认浏览器打开 %s" % url)
        try:
            webbrowser.open(url, new=1)
        except Exception as exc:
            log("没能自动打开浏览器：%r，请手工访问 %s" % (exc, url))
        assert self.static is not None
        try:
            import webview
        except Exception:
            log("没有内嵌窗口可用，程序会留在后台。关闭这个终端窗口即可退出。")
            self._block()
            return
        if IS_MACOS:
            log(grant_macos_camera_permission())
        self.window = webview.create_window("康师复 启动器", self.static.base + "/__console",
                                            width=680, height=460, confirm_close=False)
        webview.start()

    def _block(self) -> None:
        try:
            while not self.stopping.wait(0.5):
                pass
        except KeyboardInterrupt:
            pass

    def raise_window(self) -> None:
        window = self.window
        if window is None:
            if self.static is not None:
                webbrowser.open(self.static.url, new=1)
            return
        try:
            window.show()
            window.restore()
        except Exception as exc:
            log("窗口置前失败：%r" % (exc,))


# ---------------------------------------------------------------- 入口

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="康师复", description="康师复桌面启动器")
    parser.add_argument("--vision-service", action="store_true", help="内部使用：只跑视觉服务")
    parser.add_argument("--selftest", action="store_true", help="无界面自检，通过时退出码 0")
    parser.add_argument("--ui", choices=["webview", "browser", "none"], default=None,
                        help="界面方式：内嵌窗口、系统浏览器、无界面")
    parser.add_argument("--allow-multiple", action="store_true", help="允许同时开多份，调试用")
    parser.add_argument("--vision-port", type=int, default=VISION_PORT,
                        help="视觉服务端口，默认 8802；前端写死了 8802，改了页面就连不上，只用于调试")
    parser.add_argument("--selftest-port", type=int, default=VISION_PORT, help="自检用的视觉服务端口")
    parser.add_argument("--selftest-frames", type=int, default=5, help="自检送几帧")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--vision-service" in argv:
        return run_vision_service()
    args, _unknown = build_parser().parse_known_args(argv)
    if args.selftest:
        import selftest
        return selftest.run(port=args.selftest_port, frames=args.selftest_frames)
    return Application(args).run()


if __name__ == "__main__":
    sys.exit(main())
