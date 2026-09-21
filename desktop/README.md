# 康师复桌面安装包

把「本机识别」这条路做成双击就能用的程序。用户不装 Python，不敲命令，识别在
自己电脑上全速跑；账号、训练计划、训练结果、报告仍然走云端。

训练辅助，非医疗诊断。

## 它是怎么跑起来的

```
┌─────────── 用户电脑（安装包内）───────────┐
│ 启动器 launcher.py                          │
│  ├─ 子进程：视觉服务 127.0.0.1:8802         │
│  ├─ 线程：静态页面服务 127.0.0.1:<自动端口> │
│  └─ 窗口：内嵌 WebView，或系统默认浏览器    │
└──────────────┬──────────────────────────────┘
               │ 只有账号、计划、训练结果、报告走网络
               ▼
        云端业务后端 /api/v1
```

- 摄像头画面只在本机两个进程之间传，不出这台电脑。
- 页面从 `http://127.0.0.1` 打开，前端现有逻辑会自动选本机视觉模式，这条路径没有改动。
- 视觉服务固定 8802，因为 `frontend/app.js` 里写死了这个地址。
- 两个服务都只监听 `127.0.0.1`，同一个局域网里的别人连不上。
- 视觉服务按本机方式启动：不开鉴权，不设任何反向代理相关的环境变量。

## 目录里有什么

| 文件 | 作用 |
|---|---|
| `launcher.py` | 启动器，也是打包入口。`--vision-service` 是它自己的子进程模式 |
| `selftest.py` | 无界面自检，退出码 0 表示通过 |
| `build/rehab-desktop.spec` | PyInstaller 配置，onedir 模式 |
| `build/build-macos.sh` | macOS 构建脚本 |
| `build/build-windows.ps1` | Windows 构建脚本 |
| `build/fetch_models.py` | 下载或复制模型权重，核对 SHA256 |
| `build/model-sha256.json` | 模型权重的基准摘要 |

模型文件、虚拟环境、安装包成品都不入库。

## 怎么构建

### macOS

```bash
# 需要 Python 3.12。没有的话：brew install python@3.12
bash desktop/build/build-macos.sh
```

第一次会在 `~/.venvs/rehab-desktop-build` 建一个干净的虚拟环境，只装真正用得到的包。
产物在 `~/.cache/rehab-desktop-build/dist/康师复.app`。

可用的环境变量：

- `REHAB_BUILD_VENV`：换虚拟环境位置。
- `REHAB_BUILD_OUT`：换产物目录。
- `REHAB_BUILD_PYTHON`：换 Python 解释器，默认 `python3.12`。
- `REHAB_PIP_INDEX`：换 pip 镜像源。国内直连 PyPI 很慢时用。
- `REHAB_MODELS_FROM`：从已有目录复制模型，不联网下载。

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File desktop\build\build-windows.ps1
```

产物在 `%LOCALAPPDATA%\rehab-desktop-build\dist\KangShiFu\`，同时打一份
`康师复-windows-x64.zip`。

### 依赖为什么是这几个

版本与 `algorithm/rehab-pose-demo/requirements.txt`、`requirements-rtmpose.txt` 一致：
`numpy==2.5.3`、`opencv-contrib-python==5.0.0.93`、`onnxruntime==1.30.0`、
`tqdm==4.70.1`，外加 `rtmlib==0.0.16`。

`rtmlib` 必须用 `--no-deps` 装。它同时声明了两个 OpenCV 包，直接装会装出重复的 cv2。

不装 `mediapipe` 和 `av`。本机 rtmpose 路径用不到，`mediapipe` 在
`rehab_pose/model.py` 里是延迟导入，排掉能省一两百 MB。

### 模型权重

本机路径实际用到的是 `pose.onnx` 与 `detector.onnx`，不是 `detector_m.onnx`。
理由：`live_api.py` 里构造的是 `RTMPoseModel(..., "detected")`，之后才把
`roi_mode` 改成 `locked`，而检测器实例在构造时就定下来了，用的是 416 输入的
yolox_tiny。`detector_m.onnx` 有 97MB，白装进去等于凭空胖一圈。

构建脚本会核对 SHA256，对不上就中止。

## 怎么配置云端地址

仓库里不写任何真实域名与 IP。运行时按这个顺序找：

1. 环境变量 `REHAB_CLOUD_BASE`，例如 `https://<你的域名>`。
2. 安装目录旁的 `config.json`，内容是 `{"apiBase": "https://<你的域名>/api/v1"}`。
   macOS 放在 `康师复.app` 的同级目录，Windows 放在 `KangShiFu.exe` 同目录。
3. 用户目录下的 `config.json`。macOS 是
   `~/Library/Application Support/KangShiFu/config.json`，Windows 是
   `%LOCALAPPDATA%\KangShiFu\config.json`。
4. 都没有时退回 `http://127.0.0.1:8801/api/v1`，也就是本机后端，并在日志里提示。

启动器把这个地址生成成一份 `config.js` 随页面发出去，`frontend/app.js` 里的
`API_BASE` 有它就用它，没有就保持原值。本地联调与线上部署的行为都不变。

## 怎么装、怎么打开

### macOS

1. 把 `康师复.app` 拖进「应用程序」。
2. 第一次打开：在「访达」里右键点图标，选「打开」，再在弹窗里点「打开」。
   直接双击会被系统拦下，因为这个包没有签名也没有公证。
3. 系统弹「康师复想要访问摄像头」时点「好」。

系统设置里放行的路径是：系统设置 → 隐私与安全性 → 最下面那条「已阻止使用"康师复"」旁边点「仍要打开」。

不要尝试绕过系统的安全机制。要彻底去掉这一步，需要 Apple 开发者账号做签名与公证。

### Windows

1. 解压 `康师复-windows-x64.zip` 到任意目录，比如 `C:\康师复`。不要解压到
   「程序文件」里，那里普通用户写不进去。
2. 双击 `KangShiFu.exe`，或者双击 `双击这里启动康师复.bat`。
3. SmartScreen 弹「Windows 已保护你的电脑」时，点「更多信息」，再点「仍要运行」。
4. 浏览器或系统弹摄像头权限时点允许。

## 摄像头

内嵌窗口（macOS 的 WKWebView、Windows 的 WebView2）能不能拿到摄像头，是这件事
最大的不确定点。两条路都实现了：

- **内嵌窗口**：默认走这条。macOS 上启动器会给 WKWebView 的 delegate 补一个
  摄像头授权回调，`Info.plist` 里也写了 `NSCameraUsageDescription`。
- **系统默认浏览器**：内嵌窗口拿不到画面时改用这条。macOS 双击 `以浏览器模式启动.command`，
  Windows 双击 `以浏览器模式启动.bat`。也可以自己加参数 `--ui browser`，
  或者设环境变量 `REHAB_DESKTOP_UI=browser`。

浏览器模式下会另开一个小窗口，上面有「退出程序」按钮。关掉它，本机的视觉服务
会一起停掉。

用浏览器模式时建议用 Chrome 或 Edge。它们对 `http://127.0.0.1` 一律按安全上下文
处理，`getUserMedia` 可用。Safari 上这条路径没有实测过。

## 自检

无界面，不开窗口，只验证「打出来的这份东西真的能干活」。

```bash
# macOS，打包版
"/Applications/康师复.app/Contents/MacOS/KangShiFu" --selftest

# Windows，打包版
KangShiFu.exe --selftest

# 源码版
python desktop/selftest.py

# 8802 被别的程序占着时换个端口
python desktop/selftest.py --port 8899
```

它做五件事：起视觉服务、`GET /healthz`、`POST /api/live/start`、拿
`frontend/assets/seated-knee-extension-v2.jpg` 当一帧调 `POST /api/live/{id}/frame`、
`POST /stop`，最后打印单帧推理耗时。退出码 0 表示通过。

为什么非做不可：只看进程起没起来不够。曾经遇到过健康检查报正常、但 cv2 实际
导入失败的情况，一直到真的送一帧进去才暴露。

## 日志在哪

- macOS：`~/Library/Logs/KangShiFu/launcher.log`
- Windows：`%LOCALAPPDATA%\KangShiFu\Logs\launcher.log`

超过 2MB 自动轮转，只留一份历史。日志里不写画面数据、关键点、登录令牌；视觉
服务的逐帧访问日志被过滤掉，云端地址只记协议与主机名。

## 常见问题

**打开后提示 8802 端口被占用。**
说明这台电脑上已经有程序占着 8802。可能是上一次没退干净，也可能你手工起过
`live_api.py`。macOS 用 `lsof -nP -iTCP:8802 -sTCP:LISTEN` 查，Windows 用
`netstat -ano | findstr 8802` 查，关掉它再打开。这个端口不能改，前端写死了它。

**重复双击会不会开出两套服务。**
不会。第二次打开会把已有的窗口叫到前台，然后自己退出。

**关窗口后进程会不会残留。**
不会。关窗口时启动器会停掉视觉服务子进程。启动器被强杀时，子进程自己会在几秒
内发现并退出。

**杀毒软件报毒。**
PyInstaller 打出来的程序被误报是常见情况，尤其是 Windows Defender 和国产杀软。
遇到了就如实记录，在 `PROGRESS.md` 的「待讨论」里写一条，不要教用户关掉杀毒软件。

**体积能不能再小。**
主要占用是 onnxruntime、opencv、模型权重、Python 运行时。真要压，方向是换更小的
pose 模型，或者用 onnxruntime 的精简构建。这属于算法侧的取舍，要后端（常）拍板。

## 边界

- 不改 `algorithm/rehab-pose-demo/rehab_pose/` 下任何文件。
- `live_api.py` 一行没改。打包时把 `config/` 与 `models/` 放到 PyInstaller 的资源
  根目录，`Path(__file__).resolve().parent` 正好指到那里。
- `frontend/` 只加了一行 `config.js` 的引用，和 `API_BASE` 的一处兜底取值。
  没有 `config.js` 时行为与改动前完全一致。
