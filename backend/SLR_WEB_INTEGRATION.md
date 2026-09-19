# 动作2网页接入与验收
本次本机网页已使用 SupineAnalyzer，动作1/6/8保留原引擎。此模块为候选工程规则，待康复师确认。
## 本机测试步骤
1. 自主选择仰卧直腿抬高，或由康复师重新发布含 rule_version=slr_v0.1_surface 的方案。初始演示1组3次、目标30度、保持5秒；已存个人组次不覆盖。
2. 固定侧面机位，训练腿靠近镜头，肩髋膝踝完整可见。进入识别、锁定训练者。
3. 点“动作二：标定床面参考线”，沿同一侧面的床沿先点头端、再点脚端；白线确认后，放平训练腿保持2秒。换侧、移动相机后重新标定。
4. 缓慢抬腿、保持、放回。膝弯曲仍可记录完整尝试，但目标完成不增加。查看真实报告的床面峰值、联合保持、屈膝事件与次数。
## 工程接线
LiveAnalyzer 对动作2使用 SupineAnalyzer(targets)，每帧调用 process(t, measured, width, height)，返回 measure 与 state，替代旧 MotionMeasures/ExerciseAnalyzer/ExerciseFeedback 的动作2分支。其它动作不变。
/api/live/start 的动作2必须携带 rule_version=slr_v0.1_surface；旧网页拒绝启动，避免旧角度口径混用。
POST /api/live/{id}/surface 接收 {points:[[x1,y1],[x2,y2]]}，归一化坐标映射原始非镜像帧。调用 set_surface，重新校准。报告保存参考线、起始基线、规则版本和生效目标，snapshot保留本次方案。
网页使用 slr_thigh_surface_deg、knee_flexion_deg、raise_velocity_deg_s、joint_hold_s；须只在可靠联合带显示保持计时。使用 target_completed 作为目标完成，而不是把所有计数称为合格。
## 分发边界
本PR包含独立规则模块、测试、后端版本字段和文档。本机网页 dist/app.js、dist/index.html 与独立运行的 live_api.py 已修改，但原先未纳入共享仓库，仍需随本机集成代码一起分发。不能只拉取本PR就假定旧网页桥接已自动升级。
## 验证与局限
文档五例和左右朝向合成关键点测试通过；真实模型HTTP启动、参考线、空白帧、停止回传通过。合成轨迹不能证明真人误差合格，尚需固定侧面实拍复测。摄像头不判断肌肉激活、腰椎贴床、骨盆旋转或疼痛；这些为教学/本人反馈/人工复核。标定只校正画面旋转，不消除斜拍透视。
长时丢失或30秒未闭合后重新准备。当前实现保守地将含短时遮挡的周期标为需复核，不把遮挡前后时间相加。主观疼痛、次晨反应不由本次规则自动产生。
