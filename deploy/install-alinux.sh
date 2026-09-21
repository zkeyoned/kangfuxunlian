#!/bin/bash
# Alibaba Cloud Linux 3（RHEL 系，dnf）版部署脚本：只装后端 + systemd，不装 Caddy。
# HTTPS 由 Cloudflare Tunnel 提供（见 deploy/cloudflared.md），所以不需要开 80/443，也不需要备案。
# 用法（在服务器上）：sudo bash deploy/install-alinux.sh
set -e
APP_DIR=/opt/rehabtrack
DATA_DIR=/var/lib/rehabtrack

# 1. Python ≥3.10（Alinux3 自带 3.6 太旧）
if ! command -v python3.11 >/dev/null 2>&1; then
  dnf install -y python3.11 python3.11-pip >/dev/null
fi
PY=$(command -v python3.11)

# 2. 目录与用户
id -u rehab >/dev/null 2>&1 || useradd -r -s /sbin/nologin rehab
mkdir -p "$APP_DIR" "$DATA_DIR/logs"

# 2.1 已有旧库的升级检查
#
# backend/db.py 的 init_db() 每次启动都会对已有库重跑一遍 database/schema.sql。
# CREATE TABLE / CREATE INDEX 都带 IF NOT EXISTS，对结构相同的库是幂等的；但如果
# 库是更早版本建的，表已存在所以不会补新列，而 schema.sql 末尾的索引又引用了新列，
# 启动时会直接抛 `no such column: <列名>` 并退出，报错信息看不出是版本不匹配。
#
# ALTER TABLE ADD COLUMN 不支持 IF NOT EXISTS，所以补列语句不能留在 schema.sql 里，
# 只能放 database/migrations/ 手工执行（该目录文件头有说明）。这里替部署做掉这一步：
# 检测到旧库就先备份再补列，补不上的列（通常是已经有了）跳过，不中断部署。
DB_FILE="$DATA_DIR/rehabtrack.sqlite3"
if [ -f "$DB_FILE" ]; then
  SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
  NEED=$("$PY" - "$DB_FILE" <<'PYEOF'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
cols = [r[1] for r in con.execute("PRAGMA table_info(sessions)")]
print("yes" if cols and "import_source_key" not in cols else "no")
PYEOF
)
  if [ "$NEED" = "yes" ]; then
    STAMP=$(date +%Y%m%d-%H%M%S)
    cp "$DB_FILE" "$DATA_DIR/rehabtrack.sqlite3.bak-$STAMP"
    echo "检测到旧版本数据库，已备份为 rehabtrack.sqlite3.bak-$STAMP，正在补列……"
    for mig in "$SRC_DIR"/database/migrations/*.sql; do
      [ -f "$mig" ] || continue
      # ALTER 逐条执行，已存在的列会报 duplicate column name，跳过即可
      "$PY" - "$DB_FILE" "$mig" <<'PYEOF'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
sql = open(sys.argv[2], encoding="utf-8").read()
for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
    try:
        con.execute(stmt)
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("  跳过一条语句：%s" % e)
con.commit()
PYEOF
    done
    echo "旧库升级完成。原库备份在 $DATA_DIR/rehabtrack.sqlite3.bak-$STAMP"
  fi
fi
# --exclude .venv 必须有：虚拟环境建在 $APP_DIR/.venv，而源目录没有它，
# 少了这条 --delete 会在第二次部署时删掉正在用的 venv，且删不干净（目录非空），
# 下一行的 .venv/bin/pip 随即 No such file or directory，重装必然中断。
rsync -a --delete --exclude data --exclude .git --exclude __pycache__ --exclude .venv "$(cd "$(dirname "$0")/.." && pwd)/" "$APP_DIR/"
cd "$APP_DIR"

# 2.2 线上副本的接口地址适配
#
# frontend/app.js 里 API_BASE 写的是本地联调地址 http://127.0.0.1:8801/api/v1。
# 公网访问时这个地址指向的是访客自己的电脑，页面能打开但登录和数据请求全部失败。
# 线上由后端同源托管 frontend/，所以只在部署出来的这份副本里改成相对路径，
# 仓库源码与本地联调方式不变。VISION_BASE（本机视觉服务 8802）按设计保持本机地址。
# 找不到要替换的那一行就中止，避免前端改了写法后这里悄悄失效。
if [ -f frontend/app.js ]; then
  if grep -q '"http://127.0.0.1:8801/api/v1"' frontend/app.js; then
    sed -i 's#"http://127.0.0.1:8801/api/v1"#"/api/v1"#' frontend/app.js
  elif ! grep -q 'API_BASE = "/api/v1"' frontend/app.js; then
    echo "frontend/app.js 里没找到预期的 API_BASE 写法，请检查后再部署" >&2
    exit 1
  fi
fi

# 2.3 给前端脚本打版本戳，避免浏览器拿旧缓存
#
# index.html 引用的是固定的 app.js，浏览器会把它缓存下来；更新部署后访客可能
# 仍在跑上一版脚本，表现为新功能"没生效"而又不报错，很难排查。
# 这里只改部署出来的副本，仓库源码保持干净。
STAMP=$(date +%Y%m%d%H%M%S)
if [ -f frontend/index.html ]; then
  sed -i "s#src=\"app.js\"#src=\"app.js?v=$STAMP\"#g" frontend/index.html
  sed -i "s#href=\"styles.css\"#href=\"styles.css?v=$STAMP\"#g" frontend/index.html
  # 其它同页脚本（如 subject-lock.js）可能自带固定版本号，一并换成本次部署的戳，
  # 否则它们更新后访客仍会命中旧缓存。
  sed -i -E "s#src=\"([a-z-]+\.js)(\?v=[^\"]*)?\"#src=\"\1?v=$STAMP\"#g" frontend/index.html
fi
# worker 是 app.js 用 new Worker() 起的，同样要带版本，否则改了识别逻辑也不生效。
if [ -f frontend/app.js ]; then
  sed -i "s#new Worker(\"pose-worker.js\")#new Worker(\"pose-worker.js?v=$STAMP\")#g" frontend/app.js
fi

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
# 规则服务额外需要 numpy（rehab_pose 的人物跟踪模块用到）。
# 不装 opencv / mediapipe / onnxruntime：浏览器模式下服务端不解码画面、不加载模型。
.venv/bin/pip install -q -i https://mirrors.aliyun.com/pypi/simple/ numpy
chown -R rehab:rehab "$APP_DIR" "$DATA_DIR"

# 3. systemd（只监听本机 127.0.0.1:8801，外面只能经隧道进来）
cat > /etc/systemd/system/rehabtrack.service <<EOF
[Unit]
Description=RehabTrack API
After=network.target

[Service]
User=rehab
WorkingDirectory=$APP_DIR
Environment=REHAB_DATA_DIR=$DATA_DIR
Environment=REHAB_BIND=127.0.0.1
ExecStart=$APP_DIR/.venv/bin/python backend/main.py 8801
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
# 4. 规则服务（浏览器模式下由它跑动作判定，不加载任何模型）
#
# 浏览器把画面变成 33 个关键点后发到这里，判定、计次、评分仍由 rehab_pose 完成。
# 只监听 127.0.0.1，外面经 cloudflared 进来；鉴权复用业务后端的登录令牌。
if [ -f "$APP_DIR/algorithm/rehab-pose-demo/live_api.py" ]; then
  install -m 644 "$APP_DIR/deploy/rehab-vision.service" /etc/systemd/system/rehab-vision.service
  VISION_UNIT=1
else
  echo "警告：未找到 live_api.py，跳过规则服务安装" >&2
  VISION_UNIT=0
fi

systemctl daemon-reload
# 必须 restart 而不是 enable --now：后者对已经在运行的服务不做任何事，
# 结果是代码文件更新了、进程还跑着上一版，表现为"部署了但没生效"。
systemctl enable rehabtrack >/dev/null 2>&1
systemctl restart rehabtrack
if [ "$VISION_UNIT" = "1" ]; then
  systemctl enable rehab-vision >/dev/null 2>&1
  systemctl restart rehab-vision
fi
sleep 3
curl -s http://127.0.0.1:8801/healthz && echo && echo "后端已在 127.0.0.1:8801 运行"
if [ "$VISION_UNIT" = "1" ]; then
  curl -s http://127.0.0.1:8803/healthz && echo && echo "规则服务已在 127.0.0.1:8803 运行"
fi

# 5. 浏览器端识别资源自检
#
# 这批文件按 .gitignore 不入库，靠 deploy/prepare-vendor.sh 在本地准备后随 frontend/ 同步上来。
# 缺了的话公网访问者点开始训练会一直停在"正在准备识别模型"，所以这里明确提示而不是静默放过。
if [ ! -f "$APP_DIR/frontend/vendor/mediapipe/vision_bundle.js" ] || \
   [ ! -f "$APP_DIR/frontend/vendor/mediapipe/pose_landmarker_full.task" ]; then
  echo "警告：frontend/vendor/mediapipe/ 资源缺失，浏览器端识别将无法使用。" >&2
  echo "      请在本地执行 bash deploy/prepare-vendor.sh 后重新部署。" >&2
fi
