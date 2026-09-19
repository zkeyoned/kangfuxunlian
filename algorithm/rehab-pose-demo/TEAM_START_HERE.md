# 队友接收说明 · v0.6

这是康复运动视觉分析的本地 Python 原型。解压后，用 VS Code 打开本文件所在的整个文件夹。

## 1. 第一次安装

Windows 安装 Python 3.12（安装时包含 Tcl/Tk 和 Python Launcher），VS Code 安装 Python 扩展。电脑需要联网下载依赖和模型。

在 VS Code 的终端中依次运行以下命令，不需要激活虚拟环境，也不需要修改 PowerShell 的执行策略：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-rtmpose.txt
.\.venv\Scripts\python.exe -m pip install --no-deps rtmlib==0.0.16
.\.venv\Scripts\python.exe -m rehab_pose.run --download-model
.\.venv\Scripts\python.exe -m rehab_pose.run --backend rtmpose --download-model
```

每一步成功后再执行下一步。RTMLib 的 `--no-deps` 是有意设置的，避免重复安装两个提供 cv2 的 OpenCV 包。`requirements-lock.txt` 是环境记录；安装请使用上面的步骤。也提供了 `setup.ps1` 自动安装脚本，如果系统限制脚本运行，直接使用上述命令即可。

## 2. 每次启动

```powershell
.\.venv\Scripts\python.exe app.py
```

也可以按 F5，选择“启动康复训练窗口”。弹出设置窗口后，选择动作、训练侧、组数和每组次数，再点击允许摄像头并开始；也可选择本地视频。具体标定及操作见 README.md。

若提示没有 tkinter，先修复 Python 3.12 安装并安装 Tcl/Tk；程序中的 Python 3.14 回退只是兼容原开发电脑，不要求所有队友同时安装两个版本。

## 3. 当前能做什么

- 动作 1：坐姿伸膝；动作 2：卧姿直腿抬高；动作 6：扶物微蹲；动作 8：坐立。
- 输出关键点、二维角度、速度、次数、保持时间、动作提示及训练计划完成情况。
- 动作 1 保持时间可选 2、2.5、3 秒；动作 2 默认 5 秒；动作 6、8 不要求顶端保持。组间休息 30 秒。
- 结果写到 `results/`：逐帧 `frames.jsonl`、汇总 `summary.json`、评估 `assessment.json` 和 `assessment.md`。录像只有勾选保存时才生成。

所有阈值均为可验证的演示规则，不能当作通用临床处方。动作 2、6、8 仍需用真实对应动作视频验证。摄像头不能直接测量肌肉发力、双腿受力、手部支撑力或真实三维骨盆旋转。关键点不可见时，系统应暂停相关判断。

## 4. 协作时看哪些文件

| 文件或目录 | 用途 |
| --- | --- |
| app.py | 本地启动与设置窗口 |
| rehab_pose/model.py、tracking.py、subject.py | 姿态模型、关键点跟踪、训练者锁定 |
| rehab_pose/measures.py、exercises.py、exercise_rules.py | 测量值、动作阶段与提示规则 |
| rehab_pose/session.py | 组数、次数、休息与完成情况 |
| rehab_pose/run.py | 视频处理流程和结果输出 |
| rehab_pose/assessment*.py | 训练评估报告 |
| config/ | 配置 |
| examples/ | 合成输出示例，不是患者记录 |
| tests/ | 自动化测试 |

目前没有实现网站 API、WebSocket 或数据库连接。景可以据输出字段设计页面，常后续封装服务接口，得负责保存训练记录；不能直接把本地 app.py 当作已经可以部署的网站后端。字段与语义以当前代码和 README 为准，历史比较文档描述的是旧版本。

## 5. 测试与上传共享库

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

依赖私人测试录像的回归测试在本源码包中可能跳过，这是预期情况。自动化测试通过不等同于临床准确率验证。

源码包包含程序、配置、VS Code 配置、测试、示例、安装说明及第三方许可。未包含 `.venv/`、模型权重、`results/`、私人录像、缓存或 Git 历史。模型通过安装步骤从官方来源下载。

向已有共享仓库添加文件时，先保留队友已有代码并检查重名文件。保留 `.gitignore`、`THIRD_PARTY.md` 和 `licenses/`。本包未替团队选定项目开源许可证。

压缩包内 `PACKAGE_MANIFEST.json` 记录交付文件的 SHA256，可用于检查是否完整。
