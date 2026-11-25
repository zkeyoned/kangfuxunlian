# 给部署负责人：公网与本地 RTMPose 对齐

此版本尚未部署。它需要服务器推理，不能只更新网页。先在测试副本验收，完成后切换正式服务。2核2G服务器不保证与本机同帧率；初始限制1名训练者，必须测量推理速度和公网往返。

## 变化与依赖

- 公网默认 remote，不再默认 MediaPipe；本机默认 local。`?vision=browser` 仅作对照。
- 原摄像头临时JPEG上传服务端，复用本机YOLOX tiny、RTMPose、RecoveringSubjectLock和四动作规则。不更换模型，不降低分辨率或置信度掩盖错误。
- 图像、骨架、角度按frame_id配对显示，左侧是已识别画面而非零延迟预览；上方显示延迟。批量请求减少往返。网络积压时明确停止并保存部分结果，不保证弱网计数等同本地。
- .vision-venv 与业务后端 .venv 隔离；数据库/录像无需迁移，不重置账号。

## 部署步骤

1. 备份当前部署源码和systemd配置，保留原数据库目录。将本PR的frontend、algorithm及deploy更新到测试副本。同步时排除data、.venv、.vision-venv及已有模型，避免删除环境。
2. 准备 Python 3.12，在副本运行 `bash deploy/prepare-rtmpose.sh`。它安装与本地相同版本的依赖、下载模型并校验SHA256及规则源码。若安装或校验失败就停止，不跳过检查。
3. 确保运行账号rehab可以读取模型和.vision-venv；模型文件不入Git。将验证通过的源码与环境放在 /opt/rehabtrack。
4. 把 deploy/rehab-vision-rtmpose.conf 放到 /etc/systemd/system/rehab-vision.service.d/rtmpose.conf（创建目录），保留原有8803端口、鉴权、数据库目录和 /vision 前缀。然后 `sudo systemctl daemon-reload`、`sudo systemctl restart rehab-vision`。
5. 检查 `curl -fsS http://127.0.0.1:8803/healthz`：remote_rtmpose_ready=true、auth=on、reference_id与config/rtmpose_reference.json一致。False时查journal，不发布网页。若需要模型服务器分离，现有直接读业务DB的鉴权必须另改，不能随意复制用户库。
6. 更新网页 app.js、frame-queue.js、index.html等全部文件并刷新版本缓存。反向代理 /vision 必须允许2.5MB请求及足够处理超时（至少25秒），不得缓存帧请求。业务API使用同源路径。
7. 手机/电脑登录实测：四动作、左右腿、路人经过、短遮挡、床面与坐站标定、结束时最后一批计次、报告录像回放。确认画面与数值一致，并观察延迟是否可接受。不接受则改善服务器性能/网络，不能冒称效果相同。

## 回滚

恢复部署前的前端与视觉源码，撤销仅本次添加的rtmpose.conf，daemon-reload后重启视觉服务。保留数据库及录像；不要执行数据库reset。原浏览器模式资源仍可保留。

## 校验范围

同输入、同时间戳、同规则和权重才可比较。reference校验包含运行依赖版本，但不同操作系统/CPU数值仍需容差验收。真人原始视频可以本机运行测试，不提交患者录像或关键点。训练辅助，非医疗诊断。

可在算法目录运行 `python tests/replay_transport_parity.py /path/to/private-video.mp4 --seconds 120 --side left --facing left`。它比较真实模型逐帧与批量入口的全部输出（排除运行耗时），不导出视频或关键点。拍摄侧和朝向按实际录像填写；这项测试验证传输一致性，不代表动作识别准确率。
