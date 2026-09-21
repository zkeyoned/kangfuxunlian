# 2026-09-21 · 姿态模型移到浏览器，规则继续跑在服务端

- 日期：2026-09-21
- 背景：训练功能依赖用户本机的 Python 视觉服务（`algorithm/rehab-pose-demo/live_api.py`，端口 8802），网页把每帧 JPEG 发给它做识别。这带来三个限制：访客必须先在自己电脑上装好 Python 环境和模型才能训练；Safari 会拦截 https 页面访问本机 http 服务，装了也用不了；手机与平板无法运行本机服务，只能看数据。把网址发给别人，对方只能看，不能练。

- 决定：
  1. **只把"出关键点"这一步搬到浏览器，动作判定不搬。** 浏览器用 MediaPipe Tasks Vision 算出 33 个关键点，发给服务端；`rehab_pose/` 下约 2260 行的规则、状态机、评估与简报生成继续在服务端运行，本次一行未改。依据是规则层的入口只接受 `landmarks(33) + width + height`（`rehab_pose/core.py:56`、`tracking.py:82`、`measures.py:44`、`auto_facing.py:42`），全程不接触原始画面、不使用 z 坐标。
  2. **新增端点，不改旧端点。** 新增 `POST /api/live/{id}/landmarks`（契约见 `docs/03-接口契约.md` N 节）；原有 `/frame` 的两种请求体与全部行为保持不变。`backend` 参数新增取值 `browser`，原有 `rtmpose` 与 `mediapipe` 两条路径的参数选择、模型加载、人物锁定逻辑均不变。
  3. **两种模式共存，按访问来源自动选择。** 页面在 `localhost` 打开时默认走本机模式（行为与改造前完全一致），在公网域名打开时默认走浏览器模式；`?vision=local` 与 `?vision=browser` 可手动覆盖，任一端出问题都能当场切回。
  4. **浏览器端与服务端使用同一个模型文件。** `pose_landmarker_full.task`，sha256 `5134a3aa…`，与 `algorithm/rehab-pose-demo/models/` 下那份逐字节相同。这样浏览器模式与服务端 `backend=mediapipe` 的关键点口径一致，精度差异只来自"MediaPipe 与 RTMPose 的区别"这一个变量。
  5. **运行库与模型自托管，版本锁定 1.0.1。** 放在 `frontend/vendor/mediapipe/`，不走 Google CDN（国内访问不稳定）。约 43MB，按 `.gitignore` 不入库，由 `deploy/prepare-vendor.sh` 准备，随 `frontend/` 一起同步到服务器。不使用 `latest`：官方正在高频发布 1.1.0-rc 预发布版，行为变化应由我们主动升级而不是被动接收。
  6. **接受人物锁定与遮挡自动找回的功能降级。** 现有机制同时依赖 YOLOX 的多人检测框与对原始像素裁剪计算的外观直方图（`subject.py:12-20`、`subject_recovery.py:12-30`），浏览器端 PoseLandmarker 两样都不提供。浏览器模式下改为：检测到多于一人即 `multiple_people` 暂停计数，单人被遮挡时关键点缺失走 `visible=false`，规则层自然不累计。口径是**宁可不计，不能多计**。本机模式的人物锁定能力完全保留。
  7. **规则服务对公网开放前补齐防护。** 鉴权复用业务后端已有的登录令牌（`backend/db.py` 的 `user_by_token`），不另发凭证；加会话数上限、空闲回收、CORS 白名单、监听地址可配；500 响应不再回显异常原文。以上均由环境变量控制，默认值保持本机联调的原有行为。

- 影响谁：
  - **后端与视觉算法（常）**：`live_api.py` 被重构为 `_prelude` / `_analyze` / `process` / `process_landmarks` 四段。`_analyze` 是原 `process()` 第 160-316 行整段搬移，逐行核对与原文一致（可用 `git diff -w` 验证），只减了一级缩进。`rehab_pose/` 未改动。
  - **前端（景）**：新增 `frontend/pose-worker.js` 与 `frontend/vendor/mediapipe/`；`app.js` 新增浏览器模式的取帧与上报路径，原有 JPEG 路径保留。
  - **数据库（得）**：`deploy/` 下新增规则服务的 systemd 单元与资源准备脚本；`backend/main.py` 增加两行静态资源 MIME 注册。

- 待确认：
  1. 精度验证尚未完成。换模型必然带来角度与计次的差异，需要用同一批录像对比 `rtmpose`（现状）与 `browser`（目标态），指标与可接受范围见 `docs/03-接口契约.md` N 节末尾。结论需要后端（常）与医学（陈）共同判断。
  2. 低端设备若被迫改用 lite 模型，等于又换一次模型，精度需重新验证，不能沿用 full 的结论。
  3. 何时对陌生访客默认启用浏览器模式，由项目所有者决定。

- 谁签：数据库（得）起草并实施；**待后端与视觉算法（常）、前端（景）审阅**。
