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

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
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
systemctl daemon-reload
systemctl enable --now rehabtrack
sleep 2
curl -s http://127.0.0.1:8801/healthz && echo && echo "后端已在 127.0.0.1:8801 运行"
