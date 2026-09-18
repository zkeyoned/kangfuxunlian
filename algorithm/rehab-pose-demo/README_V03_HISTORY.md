# 坐姿伸膝视觉演示 v0.3（常的本地 VS Code 项目）

已实现第一阶段：可切换 MediaPipe / RTMPose + 本地视频/摄像头 + 膝角度 + 动作分段计数 + JSON记录。不是重新训练的医疗模型，尚未临床验证。

## v0.3 短暂丢点衔接

- 最多约0.25秒的单个低分关节点丢失可暂时显示橙色虚线，文字提示预测中；不显示预测膝角，不累计预测保持时间。
- 其余关节点必须与历史运动相符，预测不得出画。出画、多人/无人、串腿证据、几何异常、两个以上低分关节点均不补猜。
- 恢复后需要连续两帧通过位置一致性与原有质量检查，才衔接原动作。较长遮挡仍中断。
- 衔接过缺口的完整动作标记 needs_review=true；最大角度只统计观测值，连续保持计时在缺口处重置。伸出时间、回落时间及回落达标判断置为 null，避免将不可见过程当成已测得。
- 程序不能确认低分一定由遮挡造成；虚线只是短时运动预测，不能解决任意遮挡。
- 原始2165帧记录回放：严格模式1469帧可测，新版1477帧可测、另有10帧仅预测；成功衔接1处，完整动作均为7次。详见 COMPARISON_V03.md。
- 重新运行 app.py 加载v0.3窗口，无需重新下载模型。

## v0.2 基础功能

- RTMPose-m（17点）+ ONNX Runtime CPU，映射肩/髋/膝/踝到通用输出格式。并非点越多越好。
- 中文窗口选择模型；RTMPose可选“固定单人画面（近景）”或“先检测人体（全景）”。
- 固定单人模式直接分析整幅画面，不检测人数，不自动确认身体存在；只能用于明确的一人训练画面。不要让其他人入镜。先检测模式使用YOLOX-tiny，近景截断人体时可能漏检。
- 坐标使用One Euro自适应滤波；角度不再重复平滑，以减少延迟。
- 在平滑前拦截不可信/出画关键点、突然跳变、腿段长度突变和强烈疑似左右串腿。不自动交换左右侧；符合v0.3条件的短暂低分缺口可预测显示，其余异常需要重新稳定。
- raw_metrics保留原始模型输出，主keypoints为过滤后用于画线和测量的坐标。模型分数不是准确率，RTMPose分数与MediaPipe分数不能直接比较。
- 改善抖动可能增加延迟、暂停和漏计；质量规则仍是技术启发式，不能保证阻止持续稳定的错误定位。肩部缺失不阻止膝角测量，但不再输出躯干角度。
- 关闭再运行 app.py 才会加载新版启动窗口。

## 本机直接开始

1. VS Code：文件 → 打开文件夹 → 选择本 README 所在的 `rehab-pose-demo` 文件夹。
2. 打开 `app.py`，选择 Python 解释器 `.venv\Scripts\python.exe`。
3. 按 F5，选择“启动康复训练窗口”（需要微软 Python / Python Debugger 扩展）。也可在终端运行：

```powershell
.\.venv\Scripts\python.exe app.py
```

4. 选择左腿/右腿及模型，点击 **允许使用摄像头并开始**。画面在新窗口中显示。默认不保存视频。初次可试RTMPose的固定单人模式，仍需完整拍到训练腿。
5. 若想停止，点击启动窗口的“停止”，或在视频窗口按 Q/Esc。

这台电脑的 Python 3.12 虚拟环境和模型已准备好。程序不会在打开启动窗口时自动使用摄像头。
本机3.12缺少tkinter，app.py会自动使用已安装的3.14显示启动窗口，算法子进程仍使用项目的3.12环境。其他电脑应安装含Tcl/Tk组件的Python 3.12；无需为了本项目另装3.14。
摄像头只在你点击按钮后访问；Windows 是否再弹授权提示取决于系统设置。如失败，检查 设置 → 隐私和安全性 → 摄像头 → 允许桌面应用访问摄像头，并关闭占用摄像头的其他应用。可以尝试编号1。

## 换电脑或从压缩包开始

安装 Windows x64 Python 3.12（含 tkinter），在项目目录的 PowerShell 运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-rtmpose.txt
.\.venv\Scripts\python.exe -m pip install --no-deps rtmlib==0.0.16
.\.venv\Scripts\python.exe -m rehab_pose.run --download-model
.\.venv\Scripts\python.exe -m rehab_pose.run --backend rtmpose --download-model
.\.venv\Scripts\python.exe app.py
```

也可运行 `setup.ps1` 完成环境准备。若执行策略阻止脚本，使用上面逐行命令，不必修改系统安全设置。模型首次下载需要连接 Google / OpenMMLab 官方存储；MediaPipe下载失败时可手工下载来源文件，放入 `models/pose_landmarker_full.task`。RTMPose来源和校验记录见 models/rtmpose 下的 source.json 文件。

## 拍摄与操作

- 第一版只支持动作1坐姿伸膝。动作2、6、8未实现，不能当作已支持。
- 固定相机，侧面对准训练腿；训练侧髋、膝、踝在整个动作中完整可见；肩部可见时才分析躯干。宽松衣物或椅子可能造成遮挡。
- 左右侧是被拍摄者的解剖侧，画面不镜像。
- 先观察到屈膝起始姿态才能开始计数。默认技术参数要求角度不高于105°并持续0.25秒。
- 初版是按选定动作分析，不自动验证“是否坐在椅子上”，其他运动也可能形成类似曲线。
- MediaPipe/RTMPose检测模式检测到两人时暂停；RTMPose固定单人模式不检查人数。所有模式都要求只有一人入镜，关节点低可信或出画时不给角度判断。
- 对关键点坐标作自适应平滑，异常点先过滤。短暂缺口按照上面的v0.3规则处理，其他不可靠帧或大于0.3秒的采样间隙仍中断当前动作，等待重新回到起始姿势。
- 摄像头实际速度低于约4 FPS时可频繁中断，需要改善光照、降低分辨率或评估模型；不要随意扩大间隙掩盖丢帧。

## 输出

每次运行创建独立 `results/日期时间/`，不会覆盖旧结果：

v0.3使用schema_version 1.2。`keypoints`只存可测量的过滤后坐标；`display_prediction.keypoints`单独存预测显示坐标，分数为0并标记source=predicted。`bridge_pending`表示待确认缺口，`measurement_source`区分观测、预测显示和不可用。前端不可把预测字段用于达标评分。

- `summary.json`：次数、每次指标、未完成片段、配置快照、算法版本、模型SHA256。
- `frames.jsonl`：逐帧时间戳、关键点（像素坐标）、可信度、角度、平滑角度、阶段。
- `annotated.mp4`：仅勾选保存视频时生成，带标注、不含音轨。原始视频不会复制；原始输入也不会删除。

所有数据留在本机，本程序没有上传接口。结果可能包含敏感运动信息，请按团队约定保留和删除。

## 角度和时间定义

- 同侧髋—膝—踝三点夹角，伸直接近180°；伸膝角度增大。
- 计算前按宽高转换为像素坐标，避免在非正方形画面直接用归一化坐标算角度。
- `knee_flexion_proxy_deg = 180 - included_angle` 只是二维代理值，不等于经过校准的临床关节角度。
- 三点无符号夹角范围为0..180°，无法以“超过180°”检测锁膝/过伸。
- `extension_to_first_peak_s` 从越过启动阈值到首次达到此次最高角度；不是精确的生理动作起点。
- `target_hold_s` 是在目标附近连续停留的最长时段，不是肌肉持续收缩时间；目标带内的运动也可能被算入。
- `return_s` 从明显回落被检测到至首次回到起始区间。阈值和平滑会影响分段时刻。
- 文件输入用 PyAV 读取展示时间戳，支持可变帧率；无时间戳或非递增时明确报错，不伪造固定帧率。
- 摄像头用单调时钟。输出标注视频保留采样时刻，编码精度为0.1ms。

## 配置

编辑 `config/knee_extension.json`。`backend_parameters`区分模型分数阈值，`tracking`控制滤波和质量检查。所有阈值均为 **技术演示参数**，未获康复师批准；不自动从参考文章推导处方。完整往返计数与目标比较分开：未达到目标也可以被记为一次完整动作，不生成总评分。躯干倾斜仅记录，不自动判定代偿；不估计肌肉发力、疼痛、组织恢复、手臂受力。

## 命令行

```powershell
.\.venv\Scripts\python.exe -m rehab_pose.run --video "D:\videos\sample.mp4" --side left --preview
.\.venv\Scripts\python.exe -m rehab_pose.run --camera 0 --side right --preview --no-save-video
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

命令行默认保存标注视频，中文启动窗口默认不保存；可用 `--no-save-video` 禁用。无预览摄像头运行必须设置 `--max-seconds`。

## 与队友对接

这是算法模块，未连接仓库、未改变景的前端和得的数据库，未发布PR。
后端可调用 `rehab_pose.run.analyze(...)`，长任务应在后台工作进程运行，不能阻塞HTTP事件循环。
`examples/` 提供合成信号生成的数据契约样例，不是患者记录。现有仓库的实际接口未读取，因此没有冒充兼容 `KNEE_FLEX` 或写入数据库。建议映射 `SEATED_KNEE_EXTENSION` 时先与团队确认命名。

## 模型选择与许可

见 `THIRD_PARTY.md`。已安装版本写在 requirements.txt，完整环境见 requirements-lock.txt。rtmlib声明同时依赖两个提供cv2的OpenCV包，这里有意只安装opencv-contrib-python并对rtmlib使用--no-deps；pip check会提示缺少opencv-python，但实际cv2由contrib提供，已做真实推理验证。不要额外混装两个OpenCV包。
验证范围与未完成事项见 `VALIDATION.md`。

## RTMPose命令行

```powershell
.\.venv\Scripts\python.exe -m rehab_pose.run --backend rtmpose --rtm-roi full-frame --camera 0 --side right --preview --no-save-video
```

`--rtm-roi detected`启用人框检测；`--no-tracking`仅用于对比原始输出，正常训练请保持质量检查。
