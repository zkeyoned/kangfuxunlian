#!/bin/bash
# 准备浏览器端识别所需的静态资源（MediaPipe 运行库 + 姿态模型）。
#
# 这些文件约 43MB，按 .gitignore 不入库；在一台能联网的机器上跑一次即可，
# 之后 deploy/install-alinux.sh 会随 frontend/ 一起同步到服务器。
#
# 用法：bash deploy/prepare-vendor.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/frontend/vendor/mediapipe"
# 版本锁死，不用 latest：官方正在高频发 1.1.0-rc 预发布版，
# 行为漂移必须由我们主动升级，而不是被动接收。
VERSION="1.0.1"
MODEL_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
# 与 algorithm/rehab-pose-demo/models/pose_landmarker_full.task 是同一个文件。
# 浏览器端与服务端 mediapipe 后端共用同一模型，关键点口径才可比。
MODEL_SHA="5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"

mkdir -p "$DEST/wasm"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "下载 @mediapipe/tasks-vision@$VERSION ……"
TARBALL="https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-$VERSION.tgz"
curl -fsSL --retry 3 -o "$TMP/pkg.tgz" "$TARBALL"
tar xzf "$TMP/pkg.tgz" -C "$TMP"

# vision_bundle.js 是 IIFE 版本（挂全局 Vision）。必须用它而不是 .mjs：
# MediaPipe 内部靠 importScripts 加载 wasm 胶水层，module worker 里没有这个函数。
cp "$TMP/package/vision_bundle.js" "$DEST/"
cp "$TMP/package/wasm/"* "$DEST/wasm/"

LOCAL_MODEL="$ROOT/algorithm/rehab-pose-demo/models/pose_landmarker_full.task"
if [ -f "$LOCAL_MODEL" ] && [ "$(shasum -a 256 "$LOCAL_MODEL" | awk '{print $1}')" = "$MODEL_SHA" ]; then
  echo "复用已有的姿态模型（与服务端同一份）"
  cp "$LOCAL_MODEL" "$DEST/pose_landmarker_full.task"
else
  echo "下载姿态模型（约 9MB）……"
  curl -fsSL --retry 3 -o "$DEST/pose_landmarker_full.task" "$MODEL_URL"
fi

ACTUAL="$(shasum -a 256 "$DEST/pose_landmarker_full.task" | awk '{print $1}')"
if [ "$ACTUAL" != "$MODEL_SHA" ]; then
  echo "模型校验失败：期望 $MODEL_SHA，实际 $ACTUAL" >&2
  exit 1
fi

echo "完成。资源位于 $DEST（$(du -sh "$DEST" | awk '{print $1}')）"
