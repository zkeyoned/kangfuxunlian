#!/bin/bash
# macOS 上安装并启动本机视觉识别服务（algorithm/rehab-pose-demo/live_api.py，端口 8802）。
#
# 为什么需要它：网页的「开始训练」会把摄像头画面发给本机 http://127.0.0.1:8802 做识别，
# 这个服务必须跑在做训练的那台电脑上。algorithm/rehab-pose-demo/setup.ps1 只覆盖 Windows，
# 本脚本是 macOS 的对应做法，安装的依赖与版本和 setup.ps1 完全一致，不改动 algorithm/ 下任何文件。
#
# 用法：bash deploy/start-vision-mac.sh          首次运行会安装依赖并下载模型，之后直接启动
#       Ctrl+C 停止
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/algorithm/rehab-pose-demo"
# 虚拟环境放在仓库外面：仓库的 .gitignore 没有排除 algorithm/ 下的 .venv，放里面容易被误提交。
VENV="${REHAB_VISION_VENV:-$HOME/.venvs/rehab-vision}"
# 国内直连 PyPI 很慢，走代理更慢，默认用镜像；不需要时设 REHAB_PIP_INDEX=https://pypi.org/simple
INDEX="${REHAB_PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"

PY=""
for c in python3.13 python3.12 python3.11; do
  if command -v "$c" >/dev/null 2>&1; then PY="$(command -v "$c")"; break; fi
done
if [ -z "$PY" ]; then
  echo "需要 Python 3.11–3.13。可用 Homebrew 安装：brew install python@3.13" >&2
  exit 1
fi

pip_install() {
  # 装包时绕开本机代理，镜像站直连更快
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    "$VENV/bin/pip" install --progress-bar off -q -i "$INDEX" "$@"
}

if ! "$VENV/bin/python" -c "import cv2, numpy, av, mediapipe, onnxruntime, rtmlib" >/dev/null 2>&1; then
  echo "首次运行：安装依赖（几分钟）……"
  [ -d "$VENV" ] || "$PY" -m venv "$VENV"
  cd "$DEMO"
  pip_install -r requirements.txt
  pip_install -r requirements-rtmpose.txt
  # rtmlib 同时声明了两个 OpenCV 包，opencv-contrib-python 已提供 cv2，所以不带依赖安装（与 setup.ps1 一致）
  pip_install --no-deps rtmlib==0.0.16
fi

cd "$DEMO"
if [ ! -f models/pose_landmarker_full.task ] || [ ! -f models/rtmpose/pose.onnx ]; then
  echo "下载识别模型……"
  "$VENV/bin/python" -m rehab_pose.run --download-model 2>&1 | grep -v "^objc" || true
  "$VENV/bin/python" -m rehab_pose.run --backend rtmpose --download-model 2>&1 | grep -v "^objc" || true
fi

if lsof -nP -iTCP:8802 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "8802 端口已经有程序在用，视觉服务可能已在运行。" >&2
  exit 1
fi

echo "启动视觉服务。请用 Chrome 打开网页进行训练（Safari 会拦截 https 页面访问本机服务）。"
# cv2 与 av 各自带了一份 ffmpeg 动态库，macOS 会打印 objc 重复类的警告，不影响使用，这里过滤掉
exec "$VENV/bin/python" live_api.py 2> >(grep -v "^objc" >&2)
