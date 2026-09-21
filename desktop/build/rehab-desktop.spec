# -*- mode: python ; coding: utf-8 -*-
"""康师复桌面包的 PyInstaller 配置。

用 onedir 模式。onefile 每次启动都要把几百 MB 解压到临时目录，打开要等十几秒，
用户会以为程序没反应。

用法见同目录的 build-macos.sh 与 build-windows.ps1，不要直接手敲 pyinstaller。
"""
from pathlib import Path

REPO = Path(SPECPATH).resolve().parents[1]
DESKTOP = REPO / "desktop"
VISION = REPO / "algorithm" / "rehab-pose-demo"
FRONTEND = REPO / "frontend"
MODELS = VISION / "models" / "rtmpose"

VERSION = "0.1.0"

# live_api.py 用 Path(__file__).resolve().parent 找 config/ 与 models/。
# 打包后这个目录就是 PyInstaller 的资源目录，所以两者都放到资源根下，
# live_api.py 一行都不用改。
datas = [
    (str(VISION / "config"), "config"),
    (str(MODELS / "pose.onnx"), "models/rtmpose"),
    (str(MODELS / "detector.onnx"), "models/rtmpose"),
]
for extra in ("pose.source.json", "detector.source.json"):
    if (MODELS / extra).is_file():
        datas.append((str(MODELS / extra), "models/rtmpose"))

# 前端按文件列，不整目录塞：测试脚本、说明文档、node_modules 之类不进包。
FRONTEND_FILES = ["index.html", "app.js", "config.js", "styles.css", "pose-worker.js"]
for name in FRONTEND_FILES:
    source = FRONTEND / name
    if not source.is_file():
        raise SystemExit("前端文件缺失：%s" % source)
    datas.append((str(source), "frontend"))
datas.append((str(FRONTEND / "assets"), "frontend/assets"))

# 打包后这些 import 都在运行时才发生，Analysis 看不见，必须显式声明。
hiddenimports = [
    "live_api", "plan_parameters", "selftest",
    "cv2", "numpy", "onnxruntime", "rtmlib", "tqdm",
]

# 本机 rtmpose 路径用不到的大件。mediapipe 在 rehab_pose/model.py 里是延迟导入，
# av 只有离线视频工具用得上，一起排掉能省一两百 MB。
excludes = [
    "mediapipe", "av", "matplotlib", "scipy", "pandas", "PIL", "sounddevice",
    "tkinter", "IPython", "pytest", "PyQt5", "PyQt6", "PySide2", "PySide6",
    "gi", "gtk", "torch", "torchvision", "openvino",
]

a = Analysis(
    [str(DESKTOP / "launcher.py")],
    pathex=[str(DESKTOP), str(VISION)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KangShiFu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KangShiFu",
)

app = BUNDLE(
    coll,
    name="康师复.app",
    icon=None,
    # 反向域名格式的包标识符，只是个本机标识，不对应任何真实域名或服务器。
    bundle_identifier="local.kangshifu.desktop",
    version=VERSION,
    info_plist={
        "CFBundleName": "康师复",
        "CFBundleDisplayName": "康师复",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # 内嵌 WKWebView 里调 getUserMedia 时，系统按这条说明向用户要摄像头权限。
        # 没有这一条，进程会被系统直接终止。
        "NSCameraUsageDescription": "康师复用摄像头识别你的康复训练动作。画面只在这台电脑上处理，不上传、不保存。训练辅助，非医疗诊断。",
        "NSHumanReadableCopyright": "康迹 RehabTrack。训练辅助，非医疗诊断。",
    },
)
