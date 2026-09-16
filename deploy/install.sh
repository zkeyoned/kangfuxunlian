#!/bin/bash
# 在一台干净的 Ubuntu 22.04/24.04 轻量云服务器上从零部署（约 5 分钟）。
# 用法：把仓库拷到服务器后  sudo bash deploy/install.sh <你的域名>
set -e
DOMAIN=${1:?用法: install.sh <域名>}
apt-get update -y && apt-get install -y python3 python3-venv curl debian-keyring debian-archive-keyring apt-transport-https
# Caddy（自动 HTTPS）
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y && apt-get install -y caddy
fi
id -u rehab >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin rehab
mkdir -p /opt/rehabtrack /var/lib/rehabtrack /var/log/caddy
SRC=$(cd "$(dirname "$0")/.." && pwd)
cp -a "$SRC/." /opt/rehabtrack/
cd /opt/rehabtrack
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
chown -R rehab:rehab /opt/rehabtrack /var/lib/rehabtrack
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/" deploy/Caddyfile > /etc/caddy/Caddyfile
cp deploy/rehabtrack.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rehabtrack
systemctl restart caddy
echo "完成：先访问 https://$DOMAIN/healthz 确认服务活着（首次访问会自动签证书，需要域名已解析到本机且 80/443 已放行）；前端页面就绪后再用 https://$DOMAIN/ 验证摄像头，前端页面由前端负责人另行部署。"
echo "重要：立刻改掉演示账号密码，database/seed/seed.json 里的密码只用于本机演示。"
