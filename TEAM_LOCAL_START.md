# 完整本地联调版本

本分支整合 PR #4 的前端提交和 #16 所在后端依赖链，并补齐实际运行的网页、实时视觉桥接及测试。无需复制开发者电脑路径。训练辅助，非医疗诊断；动作阈值待康复师确认。

## 首次安装（Windows，Python 3.12）

在仓库根目录运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

另在 `algorithm/rehab-pose-demo` 目录运行 `powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1`。此步骤建立算法自己的虚拟环境并下载模型，需要网络。模型和虚拟环境不进 Git。

## 启动三个服务

分别在三个终端运行，均从仓库根目录出发：

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

```powershell
$env:REHAB_BIND='127.0.0.1'
.\.venv\Scripts\python.exe backend/main.py 8801
```

```powershell
.\algorithm\rehab-pose-demo\.venv\Scripts\python.exe algorithm/rehab-pose-demo/live_api.py
```

浏览器访问 http://127.0.0.1:5500 。首次数据库启动自动初始化；不要用重置数据库命令处理已有数据。若需要额外虚构演示患者，运行 `.\.venv\Scripts\python.exe backend/provision_demo_patients.py`。注册密码为5–15字符，同时含英文字母与数字。

## 版本与验收

- 网页及实时服务必须一起更新。动作标识 seated/1、supine/2、squat/6、stand/8 不随文档序号变化。
- 动作1当前默认连续保持3秒，PR #3 的5秒说明属于旧版本；康复师发布方案时可覆盖目标。
- 新用户没有默认病症和训练方案；演示数据仅用于虚构演示账号。报告、录像、方案走数据库接口，详见接口契约 F–J 节。
- 本地录像和数据库不随源码交接。旧账号及训练记录不会在队友电脑上自动出现。
- 算法目录运行 `python -m unittest discover -s tests -q`；frontend目录逐个运行 `node test_*.cjs` 对应文件；后端完整接口测试须用隔离演示库。
- 当前属于本地联调版本，不是公网部署。实时服务没有公网身份鉴权或限流；前端仍使用本机8801/8802端口。队友下载运行后访问的是自己电脑，上传 GitHub 不会自动提供在线站点。
- 单元测试不替代摄像头实拍；左右朝向、遮挡、多人经过、四个动作和报告视频回放仍需在目标电脑验收。

## PR 合并注意

PR #4 原始前端未接数据库和摄像头，本分支已保留其提交历史并升级。新PR基于 #16，合并前请前端、后端和数据库负责人确认依赖链与接口；不要仅检出旧 main 期待获得此版本。PR #2 的离线导入仍是独立流程，未在此分支合并或改写。
