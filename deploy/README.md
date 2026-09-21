# 部署方案

本目录由数据库（得）暂管，交付物是服务器、HTTPS、进程守护。三种跑法，按需选。

公网需要与本机使用同一 RTMPose 模型时，按 [RTMPOSE_ROLLOUT.md](RTMPOSE_ROLLOUT.md) 部署；仅更新网页不会启用服务器模型。

## 一、本机演示

不用这个目录，直接在项目根目录跑：

```bash
pip install -r requirements.txt
./start.sh
```

浏览器打开 http://127.0.0.1:8801 ，摄像头功能在 localhost 下浏览器默认放行，不需要 HTTPS。适合平时开发、给评委在自己电脑上演示。

## 二、局域网演示

路演现场没有公网、只有一个 Wi-Fi 时用。评委的手机和跑服务的电脑连同一个 Wi-Fi。

1. 电脑上正常 `./start.sh` 启动。
2. 电脑上查自己的局域网 IP：`ipconfig getifaddr en0`（Mac）或 `ip addr`（Linux）。
3. 手机浏览器打开 `http://<电脑的局域网IP>:8801`。

注意：大多数手机浏览器只在 `https://` 或 `localhost` 下允许打开摄像头，纯 `http://` 局域网地址可能打不开摄像头，只能演示除摄像头识别外的其他页面。要在手机上演示摄像头识别，请用下面第三种方式。

## 三、云服务器 + Cloudflare Tunnel（推荐用于手机现场演示）

摄像头功能必须 HTTPS 才能打开，所以正式演示建议走这条路。

1. 准备一台云服务器（本项目在 Alibaba Cloud Linux 3 上验证过）和一个自己的域名。
2. 服务器上执行 `sudo bash deploy/install-alinux.sh`，装好 Python 环境、systemd 服务，后端会常驻在 `127.0.0.1:8801`。
3. 按 `deploy/cloudflared.md` 的步骤装 Cloudflare Tunnel，把域名指过去，不用开放 80/443 端口，也不用备案。
4. 打开 `https://<你的域名>/healthz` 确认服务活着；前端页面就绪后（前端页面由前端负责人另行部署），手机用移动网络打开 `https://<你的域名>/`，验证能正常打开摄像头。

如果服务器在国外或已备案、想直接用 Caddy 自动签证书（Let's Encrypt），改用 `sudo bash deploy/install.sh <你的域名>`，对应 `deploy/Caddyfile` 会把 80/443 流量转发到后端。两种方式二选一，不要同时装。

## 文件说明

- `install.sh`：Ubuntu + Caddy 方案，适合有备案域名、直接开放 80/443 的场景。
- `install-alinux.sh`：Alibaba Cloud Linux 3 + Cloudflare Tunnel 方案，不需要开端口、不需要备案。
- `rehabtrack.service`：仅 `install.sh` 路线使用；`install-alinux.sh` 自己生成一份带 `REHAB_BIND` 的变体，不读取这个文件。
- `Caddyfile`：仅 `install.sh` 路线使用的反向代理配置模板。
- `cloudflared.md`：仅 `install-alinux.sh` 路线使用的 Cloudflare Tunnel 配置步骤。

## 安全提醒

- 上线前必须改掉演示账号密码，见 `database/seed/seed.json`（那套账号密码只是本机演示用的虚构数据）。
- 服务器只对外开放经过隧道或反向代理的 HTTPS 端口，后端本身只监听 `127.0.0.1`。
