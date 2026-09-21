"""桌面包自检。无界面运行，退出码 0 表示通过。

证明的是打包出来的这份东西真的能干活：模型能加载、cv2 能导入、推理能跑完
一帧。只看进程起没起来是不够的，曾经遇到过健康检查正常但 cv2 导入失败的情况。

用法：
    python desktop/selftest.py                  # 源码版
    康师复 --selftest                            # 打包版
    python desktop/selftest.py --port 8899      # 8802 被占时换个端口

训练辅助，非医疗诊断。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 直接 python desktop/selftest.py 跑时，同目录的 launcher 不在 sys.path 里。
_HERE = str(Path(__file__).resolve().parent)
if not getattr(sys, "frozen", False) and _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import launcher  # noqa: E402

# live_api 输出的 pose_status 取值。前三个来自 rehab_pose/model.py，其余来自
# rehab_pose/subject.py 与 subject_recovery.py 的人物锁定状态机。本机 rtmpose
# 走的是 locked 模式，正常认出人时是 locked。
POSE_STATUS_ALLOWED = {
    "single_person", "no_person", "multiple_people", "assumed_single_person_roi",
    "locked", "select_subject", "confirm_subject", "selection_ambiguous",
    "subject_temporarily_lost", "subject_lost_reconfirm",
}
# 这几种表示真的认出了训练者，自检要求至少出现一次。
POSE_STATUS_DETECTED = {"single_person", "locked", "assumed_single_person_roi"}
DEMO_IMAGE = "seated-knee-extension-v2.jpg"


class SelfTestError(RuntimeError):
    pass


def post_json(url: str, payload: dict, timeout: float = 120.0) -> dict:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=raw, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise SelfTestError("%s 返回 HTTP %s" % (url, response.status))
        return json.loads(response.read().decode("utf-8"))


def post_jpeg(url: str, blob: bytes, capture_time: float, timeout: float = 120.0) -> dict:
    request = urllib.request.Request(url, data=blob, method="POST",
                                     headers={"Content-Type": "image/jpeg",
                                              "X-Capture-Time": "%.3f" % capture_time})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise SelfTestError("%s 返回 HTTP %s" % (url, response.status))
        return json.loads(response.read().decode("utf-8"))


def demo_image_path() -> Path:
    path = launcher.frontend_dir() / "assets" / DEMO_IMAGE
    if not path.is_file():
        raise SelfTestError("找不到自检用的演示图 %s" % path)
    return path


def check_bundle_layout() -> list[str]:
    """先看该在的东西在不在，缺了直接说缺哪个，别等到推理时才报怪错。"""
    notes = []
    directory = launcher.vision_dir()
    config = directory / "config" / "knee_extension.json"
    models = directory / "models" / "rtmpose"
    if not config.is_file():
        raise SelfTestError("缺少规则配置 %s" % config)
    # live_api.py 用 RTMPoseModel(..., "detected") 构造，之后才把 roi_mode 改成
    # locked，检测器实例是构造时定下的，所以真正用到的是 detector.onnx 不是 detector_m.onnx。
    for name in ("pose.onnx", "detector.onnx"):
        target = models / name
        if not target.is_file():
            raise SelfTestError("缺少模型文件 %s" % target)
        notes.append("%s %.1f MB" % (name, target.stat().st_size / 1048576))
    notes.append("规则配置 %s" % config.name)
    return notes


def run(port: int = launcher.VISION_PORT, frames: int = 5, keep_running: bool = False) -> int:
    print("康师复桌面包自检")
    print("运行方式：%s" % ("打包版" if launcher.FROZEN else "源码版"))
    print("资源目录：%s" % launcher.resource_root())
    try:
        for note in check_bundle_layout():
            print("  就位：%s" % note)
    except SelfTestError as exc:
        print("自检失败：%s" % exc)
        return 1

    if not launcher.port_free(port):
        print("自检失败：端口 %d 已被占用。%s" % (port, launcher.describe_port_holder(port)))
        print("可以用 --port 换一个空闲端口再跑。")
        return 1

    blob = demo_image_path().read_bytes()
    base = "http://%s:%d" % (launcher.VISION_HOST, port)
    service = launcher.VisionService(port)
    started = time.monotonic()
    try:
        service.start(wait_s=120)
    except Exception as exc:
        print("自检失败：视觉服务没起来：%r" % (exc,))
        return 1
    print("  1/5 视觉服务启动用时 %.1f 秒" % (time.monotonic() - started))

    exit_code = 0
    try:
        health = launcher.vision_healthz(port, timeout=5)
        if not health or not health.get("ok"):
            raise SelfTestError("GET /healthz 没有返回预期内容")
        print("  2/5 GET /healthz 200，鉴权=%s" % health.get("auth"))

        load_started = time.monotonic()
        session = post_json(base + "/api/live/start", {
            "exercise": "1", "side": "left", "facing": "auto",
            "sets": 1, "reps": 10, "backend": "rtmpose",
        })
        session_id = session.get("session_id")
        if not session_id:
            raise SelfTestError("POST /api/live/start 没有返回 session_id")
        if session.get("model") != "rtmpose":
            raise SelfTestError("后端不是 rtmpose，实际是 %r" % session.get("model"))
        print("  3/5 POST /api/live/start 200，模型加载用时 %.1f 秒，session=%s…"
              % (time.monotonic() - load_started, str(session_id)[:8]))

        durations = []
        statuses = []
        boxes_seen = 0
        for index in range(max(1, frames)):
            capture_time = 0.5 + index * 0.2
            frame_started = time.monotonic()
            result = post_jpeg("%s/api/live/%s/frame" % (base, session_id), blob, capture_time)
            elapsed_ms = (time.monotonic() - frame_started) * 1000
            status = result.get("pose_status")
            if status not in POSE_STATUS_ALLOWED:
                raise SelfTestError("pose_status 取值不合法：%r" % status)
            subject = result.get("subject")
            if not isinstance(subject, dict) or "boxes" not in subject:
                raise SelfTestError("响应里没有人物框字段，本机 rtmpose 路径可能没走通")
            boxes_seen += len(subject.get("boxes") or [])
            statuses.append(status)
            durations.append((elapsed_ms, float(result.get("processing_ms") or 0)))
            print("      第 %d 帧：往返 %.0f ms，服务端处理 %.0f ms，pose_status=%s，人物框 %d 个"
                  % (index + 1, elapsed_ms, result.get("processing_ms") or 0, status,
                     len(subject.get("boxes") or [])))
        if boxes_seen == 0:
            raise SelfTestError("所有帧都没有检出人物框，演示图里是真人，说明检测没跑通")
        if not POSE_STATUS_DETECTED.intersection(statuses):
            raise SelfTestError("没有一帧认出训练者，实际状态为 %s" % "、".join(statuses))
        warm = durations[1:] or durations
        print("  4/5 单帧推理：首帧 %.0f ms，之后平均 %.0f ms（服务端处理口径 %.0f ms）"
              % (durations[0][1], sum(d[1] for d in warm) / len(warm),
                 sum(d[1] for d in durations) / len(durations)))
        print("      往返口径：首帧 %.0f ms，之后平均 %.0f ms"
              % (durations[0][0], sum(d[0] for d in warm) / len(warm)))
        print("      pose_status 依次为：%s" % "、".join(statuses))

        stopped = post_json("%s/api/live/%s/stop" % (base, session_id), {})
        if "brief_report" not in stopped:
            raise SelfTestError("POST /stop 返回里没有训练简报")
        print("  5/5 POST /stop 200，计次 %s，有效 %s"
              % (stopped.get("reps_done"), stopped.get("reps_valid")))
        print("自检通过。摄像头画面只在本机两个进程之间传输，不出这台电脑。")
        print("训练辅助，非医疗诊断。")
    except (SelfTestError, urllib.error.URLError, OSError, ValueError) as exc:
        print("自检失败：%r" % (exc,))
        exit_code = 1
    finally:
        if not keep_running:
            service.stop()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="康师复桌面包自检")
    parser.add_argument("--port", type=int, default=launcher.VISION_PORT,
                        help="视觉服务端口，默认 8802；被占用时换一个")
    parser.add_argument("--frames", type=int, default=5, help="送几帧，默认 5")
    args = parser.parse_args(argv)
    return run(port=args.port, frames=args.frames)


if __name__ == "__main__":
    sys.exit(main())
