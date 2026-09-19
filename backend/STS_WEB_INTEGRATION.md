# 坐站候选标准网页接入
用户文档动作3对应原内部动作8/stand，扶椅微蹲仍为6/squat。候选工程标准尚待顾问及真人误差验证。
## 已在本机接入
- SitStandAnalyzer 替代动作8原膝角计次。站立进入为膝夹角目标（默认165）、髋高度进度0.90、相对站姿躯干10度，持续0.3秒。维持带目标膝角减5度、进度0.85、躯干15度。
- 坐/站可靠稳定各2秒，站姿人工确认后坐回，准备动作不计数。站坐高差须≥起始小腿像素长度0.25，站姿膝角≥165。
- 正常前倾仅记录；半起身、未坐回、遮挡不补完整次数。最长连续站稳默认1秒，坐回稳定0.5秒闭合；回弹取消当前下降段。
- 辅助方式无辅助/扶大腿/扶固定扶手由用户选择，座高可空、坐垫和脚位记录，不自动判断手臂承重。
- 报告保存真实尝试列表及配置，完整次数用于训练进度。无法评价计入尝试但不计完整次数；目标完成率分母0为null。主观疼痛与次晨反应不由算法推断，本次未增加相关问卷。
## 使用
刷新网页。新版方案须重新发布 rule_version=sts_v0.1_dual_baseline，默认演示1组3次、站稳1秒；保存过的个人组次不覆盖。
摄像头固定水平侧面，完整覆盖坐、站两种姿势。先锁定训练者，再在训练页选择辅助方式并填写配置，依次采集坐姿、采集站姿、人工确认站姿，最后坐回开始。不能安全标定者应停止并请康复师调整。
## 接线
/api/live/start 动作8须携带新版rule_version。POST /api/live/{session}/sts-calibration，{stage:sit|stand|confirm,setup:{assistance:none|thighs|armrests,seat_height_cm:number|null,cushion:boolean,foot_position:string}}。
每帧调用 SitStandAnalyzer.process(t,measured,width,height)，接收(measure,state)。保存 training_session.attempts、setup、baselines、rule_version、model_version、occlusion_intervals。角度/高度仅为二维估计，手机须保持水平。
## 验证边界
六个文档边界例子通过，全部算法108项、方案参数与发布7项、隔离库完整API测试通过；真实模型HTTP start/calibration/空白帧/stop通过，无虚构计数。尚未做真人坐站测角误差和不同椅高验证。
短时遮挡保守标无法评价，不猜测关键阶段。站立晃动数据不输出平衡能力分数。座面接触首版unknown；不自动判断左右承重、肌肉、足底压力或疼痛。
## 分发
本PR包含规则、测试、后端版本字段和契约；外部网页及独立live_api.py已在本机更新，原本不在仓库，需另行同步集成包。不能只拉取本PR就假定旧网页桥接已升级。
