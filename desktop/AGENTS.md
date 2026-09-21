# desktop/ 规则（负责人：数据库（得）暂管）

本目录把「本机识别」这条路打成双击可用的桌面程序。交付物是 Windows 与 macOS
的安装包、构建脚本、自检脚本。

训练辅助，非医疗诊断。

## 归属

本目录归数据库（得）暂管，与 deploy/ 同理。视觉算法本身归后端（常），前端页面
归前端（景），这里只负责「把它们装进一个能双击的壳子里」。

## 交付物清单

- `launcher.py`：启动器，也是打包入口
- `selftest.py`：无界面自检
- `build/`：PyInstaller 配置与两个系统的构建脚本
- `README.md`：怎么构建、怎么装、未签名时怎么打开、常见问题

## 可以做什么

- 改启动器、自检、构建脚本、打包配置。
- 改 `.github/workflows/desktop-build.yml`。
- 在 README 里写安装与排错说明。

## 不可以做什么

- **不改 `algorithm/rehab-pose-demo/rehab_pose/` 下任何文件。** 那是经过多轮验证的规则层。
- 不改 `live_api.py`。目前一行都没改，打包靠把 `config/` 与 `models/` 放到
  PyInstaller 的资源根目录来对齐 `Path(__file__).resolve().parent`。
  真的非改不可时，改动要最小、要有 `getattr(sys, "frozen", False)` 之类的守卫、
  不得改变非打包场景的行为，并在 PR 里单独列出请后端（常）审。
- 改 `frontend/` 同理，请前端（景）审。
- 不在仓库里写任何真实域名、IP、密钥。云端地址一律走环境变量或安装目录旁的配置文件。
- 不把模型权重、虚拟环境、安装包成品提交进仓库。
- 不改视觉服务的端口。前端 `app.js` 写死了 `127.0.0.1:8802`。

## 开工前读什么

1. `PROGRESS.md`
2. 本文件与 `desktop/README.md`
3. `docs/03-接口契约.md`（看帧级契约与实时视觉那两节）
4. `algorithm/rehab-pose-demo/live_api.py`（打包要对齐它找 `config/` 与 `models/` 的方式）

## 改完怎么验

```bash
# 自检，退出码 0 才算过。8802 被占时加 --port 换端口
python desktop/selftest.py

# 仓库原有测试也要过
./start.sh --reset      # 另开一个窗口
python3 tests/test_api.py
cd frontend && for f in test_*.cjs; do node "$f"; done
```

前端测试必须在 `frontend/` 目录里跑，它们用相对路径读 `app.js`。

## 几个容易踩的点

- 本机 rtmpose 路径用的是 `pose.onnx` 加 `detector.onnx`，不是 `detector_m.onnx`。
  `live_api.py` 构造的是 `RTMPoseModel(..., "detected")`，之后才改 `roi_mode`，
  检测器实例在构造时就定下来了。
- `rtmlib` 必须 `--no-deps` 装，它同时声明了两个 OpenCV 包。
- 不要打包 `mediapipe` 和 `av`，本机路径用不到，能省一两百 MB。
- onedir，不要 onefile。onefile 每次启动都要解压几百 MB。
- 视觉服务子进程的 stdout 在父进程死后是坏管道，子进程里凡是「父进程没了就退出」
  这类收尾逻辑，不能把 `print` 写在 `os._exit` 前面而不兜异常。
