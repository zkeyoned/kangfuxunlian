# Cloudflare Tunnel：不备案、不开端口，给 <你的域名> 上 HTTPS

前提：<你的域名> 托管在 Cloudflare。服务器在大陆也没关系，域名解析到 Cloudflare，不是大陆 IP，不触发备案。

```bash
# 服务器上（root）
curl -L -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x /usr/local/bin/cloudflared
cloudflared tunnel login          # 打印一个 URL，在浏览器里打开并授权 <你的域名>
cloudflared tunnel create rehab   # 生成 ~/.cloudflared/<UUID>.json
cloudflared tunnel route dns rehab rehab.<你的域名>
cat > /etc/cloudflared/config.yml <<EOF
tunnel: rehab
credentials-file: /root/.cloudflared/<UUID>.json
ingress:
  - hostname: rehab.<你的域名>
    service: http://127.0.0.1:8801
  - service: http_status:404
EOF
cloudflared service install       # 装成 systemd，开机自启
systemctl status cloudflared
```

验证：先打开 https://rehab.<你的域名>/healthz 确认服务活着；前端页面就绪后（前端页面由前端负责人另行部署），手机用移动网络（不接 Wi-Fi）打开 https://rehab.<你的域名>/，能开摄像头即成功。

注意：GitHub 下载在大陆服务器上可能慢，慢就换用镜像加速前缀或从本机 scp 上去。
