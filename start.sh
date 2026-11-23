#!/bin/bash
# 康师复：本机一键启动（后端 + 静态前端同一个端口）
cd "$(dirname "$0")"
PORT=8801
DATA_DIR="${REHAB_DATA_DIR:-data}"
for a in "$@"; do case "$a" in
  --reset)
    shopt -s nullglob
    files=("$DATA_DIR"/rehabtrack.sqlite3*)
    shopt -u nullglob
    if [ "${#files[@]}" -gt 0 ]; then rm -f "${files[@]}"; echo "已重置为演示数据（$DATA_DIR）"; else echo "没有找到 $DATA_DIR 下的演示库，未删除任何文件"; fi
    ;;
  *) PORT="$a";;
esac; done
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "缺依赖，安装：pip3 install -r requirements.txt"; exit 1
fi
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "端口 $PORT 已被占用，换一个：./start.sh 8802"; exit 1
fi
mkdir -p data/logs
python3 backend/main.py "$PORT" > data/logs/server.out 2>&1 &
PID=$!
for i in $(seq 1 40); do curl -s -m 1 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && break; sleep 0.25; done
if ! curl -s -m 1 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then echo "启动失败，看 data/logs/server.out"; tail -20 data/logs/server.out; exit 1; fi
echo "服务 PID=$PID"
if compgen -G "frontend/*.html" > /dev/null; then
  echo "  前端页面 http://127.0.0.1:$PORT/"
  open "http://127.0.0.1:$PORT/" 2>/dev/null || true
else
  echo "  前端页面尚未就绪，先看 API 文档 http://127.0.0.1:$PORT/docs"
fi
echo "  API 文档 http://127.0.0.1:$PORT/docs"
echo "  停止     kill $PID"
wait $PID
