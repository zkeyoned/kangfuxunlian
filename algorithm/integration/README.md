# 本机视觉方案接入

仓库内桌面原型与本机实时 live_api.py 分开维护。本次不复制整个实时桥接，以免覆盖此前跟踪优化。

部署时：

1. 同步 backend/plan_parameters.py 到实时服务 live_api.py 同级。
2. 对现有实时桥接应用 live_api_prescription.patch。
3. 同步本 PR 的 rehab_pose/session.py 保持和休息范围校验。
4. 重启实时服务，/api/live/start 的 targets 应进入 engine.config，并在结果 training_session.effective_targets 中返回。

动作 2/6 的内部信号增加90度仅用于状态机，传入方案依旧是相对起始位幅度。其他代偿阈值沿用现有配置。方案输入是技术范围，具体目标待康复师确认。训练辅助，非医疗诊断。

本机前端独立维护，需同步 app.js/index.html。它每次训练冻结方案版本与实际组次，存入报告 training_session.prescription_snapshot；不能只更新网页显示却漏更新实时服务。
