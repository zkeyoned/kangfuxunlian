#!/usr/bin/env bash
# 在 macOS 上构建康师复桌面包，产出 dist/康师复.app。
#
# 依赖装在仓库外的独立虚拟环境里，产物写在仓库外的目录里，都不入库。
# 训练辅助，非医疗诊断。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
VENV="${REHAB_BUILD_VENV:-$HOME/.venvs/rehab-desktop-build}"
OUT="${REHAB_BUILD_OUT:-$HOME/.cache/rehab-desktop-build}"
PYTHON_BIN="${REHAB_BUILD_PYTHON:-python3.12}"
PIP_INDEX="${REHAB_PIP_INDEX:-}"

say() { printf '\n==== %s\n' "$1"; }

if [ ! -x "$VENV/bin/python" ]; then
  say "创建构建虚拟环境 $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
  PIP_ARGS=()
  [ -n "$PIP_INDEX" ] && PIP_ARGS+=(-i "$PIP_INDEX")
  # 版本与 algorithm/rehab-pose-demo/requirements*.txt 保持一致。
  # rtmlib 必须 --no-deps：它同时声明了两个 OpenCV 包，会装出重复的 cv2。
  # mediapipe 与 av 不装：本机 rtmpose 路径用不到，能省一两百 MB。
  "$VENV/bin/pip" install "${PIP_ARGS[@]+"${PIP_ARGS[@]}"}" \
    numpy==2.5.3 opencv-contrib-python==5.0.0.93 onnxruntime==1.30.0 tqdm==4.70.1
  "$VENV/bin/pip" install "${PIP_ARGS[@]+"${PIP_ARGS[@]}"}" --no-deps rtmlib==0.0.16
  "$VENV/bin/pip" install "${PIP_ARGS[@]+"${PIP_ARGS[@]}"}" pyinstaller pywebview
fi

say "准备模型权重"
if [ -n "${REHAB_MODELS_FROM:-}" ]; then
  "$VENV/bin/python" "$HERE/fetch_models.py" --from "$REHAB_MODELS_FROM"
else
  "$VENV/bin/python" "$HERE/fetch_models.py"
fi

say "清理旧产物"
rm -rf "$OUT/build" "$OUT/dist"
mkdir -p "$OUT"

say "PyInstaller 构建"
cd "$REPO"
"$VENV/bin/pyinstaller" --noconfirm --clean \
  --distpath "$OUT/dist" --workpath "$OUT/build" \
  "$HERE/rehab-desktop.spec"

APP="$OUT/dist/康师复.app"
[ -d "$APP" ] || { echo "构建没有产出 $APP" >&2; exit 1; }

# PyInstaller 在 macOS 上会先产一份 onedir 目录，再据此打出 .app，两份内容一样。
# 留着只会让人不知道该发哪个，也白占三百 MB。
rm -rf "$OUT/dist/KangShiFu"

say "生成浏览器模式快捷方式"
cat > "$OUT/dist/以浏览器模式启动.command" <<'LAUNCH'
#!/usr/bin/env bash
# 内嵌窗口里摄像头用不了时双击这个文件，改用系统默认浏览器打开训练页面。
cd "$(dirname "$0")"
open -a "$(pwd)/康师复.app" --args --ui browser
LAUNCH
chmod +x "$OUT/dist/以浏览器模式启动.command"

if [ "${REHAB_BUILD_ZIP:-1}" = "1" ]; then
  say "打包成 zip"
  # 用 ditto，普通 zip 会丢掉 .app 里的符号链接和权限位。
  ZIP="$OUT/康师复-macos-arm64.zip"
  rm -f "$ZIP"
  ditto -c -k --sequesterRsrc --keepParent "$OUT/dist" "$ZIP"
  du -sh "$ZIP"
fi

say "构建完成"
du -sh "$APP"
echo "产物目录：$OUT/dist"
echo "自检：\"$APP/Contents/MacOS/KangShiFu\" --selftest"
