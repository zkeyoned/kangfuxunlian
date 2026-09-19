# 模型选择、来源与许可核查

核查日期：2026-09-16。以下不构成对整套产品商业合规的保证。

| 候选 | 适配判断 | 当前处理 |
| --- | --- | --- |
| MediaPipe Pose Landmarker | Python Tasks接口，预训练33点，本地视频与摄像头可共用；适合先验证CPU单人原型 | 已接入并实际加载Full模型 |
| RTMPose / MMPose | 提供不同精度、速度与部署选项，适合后续同一批视频对比；不能无硬件实测就断言比MediaPipe慢 | v0.2使用rtmlib接入RTMPose-m + YOLOX-tiny；不引用虚构FPS或误差 |
| MoveNet | 17点人体姿态模型，TensorFlow/TFLite路线，可作后续候选 | 未安装；具体发行权重许可需逐项核查 |

## MediaPipe

- 官方仓库：https://github.com/google-ai-edge/mediapipe
- 官方代码许可：https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE （Apache-2.0）
- 官方Python接口：https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python
- 模型来源：https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
- 模型卡：https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf
- 下载器保存来源和实际文件SHA256。下载地址版本固定为 float16/1。

代码的Apache-2.0允许在遵守条款的情况下修改、分发和商业使用；分发时应保留许可证、适用版权及NOTICE、标注修改等，不能简化为“README加一行即可”。已保留上游LICENSE文本在 licenses/。

**权重单列：本次未找到能明确、单独覆盖该.task权重所有商用与再分发方式的许可声明，因此不作“无额外限制”的保证。** 代码许可不能自动当作权重许可。源码压缩包不打包权重，由用户从官方地址下载；正式商用或再分发前仍应核实具体模型条款。官方仓库存在相关澄清问题：https://github.com/google-ai-edge/mediapipe/issues/6306 ，问题本身不是授权。

## 其他依赖

- OpenCV：https://github.com/opencv/opencv （当前版本Apache-2.0）；Python wheel可能含第三方组件，分发二进制需保留其许可证。
- NumPy：https://github.com/numpy/numpy （BSD-3-Clause）。
- PyAV：https://github.com/PyAV-Org/PyAV （BSD-3-Clause）；其FFmpeg及编解码器依赖有各自条款，不应忽略。
- MMPose代码：https://github.com/open-mmlab/mmpose/blob/main/LICENSE （Apache-2.0）；具体权重和检测器需分别核查，v0.2通过rtmlib调用官方ONNX权重。
- MoveNet官方教程：https://www.tensorflow.org/hub/tutorials/movenet ；本项目未使用其权重，未宣称已核查具体模型许可。

本项目为新编写的应用和分析逻辑，通过公开API调用依赖，没有复制第三方示例实现。虚拟环境属于本机运行环境，不包含在交付源码压缩包中。不要把合成测试结果作为模型准确率，也不要把一般姿态模型称为已验证的康复医疗模型。

## v0.2新增依赖与借鉴

- RTMLib 0.0.16：https://github.com/Tau-J/rtmlib ，Apache-2.0，已保存LICENSE。
- YOLOX代码：https://github.com/Megvii-BaseDetection/YOLOX ，Apache-2.0，已保存LICENSE。
- RTMPose、YOLOX模型来自RTMLib官方Body配置所列OpenMMLab下载地址；具体URL和实际SHA256保存在models/rtmpose/*.source.json及运行摘要。
- ONNX Runtime：https://github.com/microsoft/onnxruntime ，MIT；版本1.30.0 CPU。
- MMPose的特殊算法许可列表已保存。本次未使用其中列出的EDPose。代码许可不自动证明所有训练数据和权重的再分发权；正式商用仍需逐项复核，本源码包不附模型权重。
- One Euro滤波参考原作者公式说明 https://gery.casiez.net/1euro/ 和MediaPipe官方平滑实现结构，本项目为新写的Python实现，没有复制第三方实现代码。
- RTMLib使用公开推理API，本次没有修改其安装源码。通过显式单人ROI避开检测阶段属于应用模式选择，日志明确标为assumed_single_person_roi，不冒称已检测到人或可见性。


## v0.4 锁定模式新增模型

使用RTMLib安装包`tools/solution/body.py` balanced配置的官方YOLOX-m，输入640×640。来源与SHA256记录在models/rtmpose/detector_m.source.json。源码与权重适用条件仍须分别核对，新增来源不等于商用保证。锁定辅助使用位置关联和躯干区域颜色直方图，不是身份认证模型。
