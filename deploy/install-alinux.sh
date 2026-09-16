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
rsync -a --delete --exclude data --exclude .git --exclude __pycache__ "$(cd "$(dirname "$0")/.." && pwd)/" "$APP_DIR/"
cd "$APP_DIR"
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
