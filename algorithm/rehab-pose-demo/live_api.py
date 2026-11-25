"""网页摄像头桥接服务，支持本机与受鉴权保护的公网 RTMPose。

浏览器只发送临时 JPEG 帧；服务不会保存视频或关键点。姿态识别和动作状态机
复用 rehab_pose 中的实现。公网部署与版本校验见 deploy/RTMPOSE_ROLLOUT.md。
"""
from __future__ import annotations

import base64
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import uuid
from functools import lru_cache
from rtmpose_reference import verify as verify_reference
from frame_batch import decode_batch, process_batch

import numpy as np

# OpenCV 只有"服务端自己解码画面"这条路径才用得上（本机 JPEG 模式）。
# 浏览器模式下关键点已经在客户端算好，服务端不碰像素，所以装不装 opencv 都能跑。
# 部署到只跑规则的服务器时可以不装，省掉一个上百 MB 的依赖。
try:
    import cv2
except ImportError:  # pragma: no cover - 取决于部署方式
    cv2 = None

from rehab_pose.slr import SupineAnalyzer
from rehab_pose.sts import SitStandAnalyzer
from rehab_pose.squat import SquatAnalyzer
from rehab_pose.core import Config
from rehab_pose.exercise_rules import ExerciseFeedback, ExerciseRulesConfig
from rehab_pose.exercises import ExerciseAnalyzer, NAMES
from rehab_pose.measures import MeasureConfig, MotionMeasures
from rehab_pose.model import PoseModel, RTMPoseModel
from rehab_pose.session import TrainingPlan, TrainingSession
from plan_parameters import apply_targets, validate_targets
from rehab_pose.tracking import PoseTracker, TrackingConfig
from rehab_pose.subject_recovery import RecoveringSubjectLock, stable_appearance
from rehab_pose.brief_report import build_brief, brief_text
from rehab_pose.auto_facing import AutoFacing


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
RTM_MODEL_DIR = Path(os.environ.get("REHAB_RTMPOSE_MODEL_DIR", ROOT / "models" / "rtmpose"))
MAX_BODY_BYTES = 2_500_000
START_LOCK = threading.Lock()
REMOTE_RTMPOSE = os.environ.get("REHAB_VISION_REMOTE_RTMPOSE", "off").lower() == "on"

@lru_cache(maxsize=1)
def reference_status():
    return verify_reference(model_dir=RTM_MODEL_DIR) if REMOTE_RTMPOSE else {"ready":False,"reference_id":None}

# 公网部署开关。默认值一律保持本机联调时的原有行为，
# 只有部署脚本显式设置环境变量时才启用更严格的策略。
VISION_BIND = os.environ.get("REHAB_VISION_BIND", "127.0.0.1")
VISION_PORT = int(os.environ.get("REHAB_VISION_PORT", "8802"))
VISION_AUTH = os.environ.get("REHAB_VISION_AUTH", "off").strip().lower() == "on"
VISION_ORIGINS = [o.strip() for o in os.environ.get("REHAB_VISION_ORIGINS", "*").split(",") if o.strip()]
MAX_SESSIONS = int(os.environ.get("REHAB_VISION_MAX_SESSIONS", "8"))
# 挂在反向代理的子路径下时用它剥前缀。cloudflared 按路径转发时不会剥掉前缀，
# 会把 /vision/api/live/... 原样送过来，而本服务是按路径分段解析的。
VISION_PREFIX = os.environ.get("REHAB_VISION_PREFIX", "").rstrip("/")
SESSION_IDLE_S = float(os.environ.get("REHAB_VISION_IDLE_S", "120"))

LANDMARK_COUNT = 33
# 一次请求最多带几帧。公网往返在实测里是几百毫秒量级，逐帧一次请求会把帧率
# 压到 1-2 fps；攒几帧一起发能把往返摊薄。时间戳由客户端打，所以合批不影响
# 规则层对时长、保持时间的判断。
MAX_FRAMES_PER_BATCH = 40
POSE_STATUS_ALLOWED = ("single_person", "no_person", "multiple_people", "select_subject", "subject_temporarily_lost", "subject_lost_reconfirm")


def validate_landmarks(body: dict):
    """校验浏览器送上来的关键点，把不合规的输入挡在规则层之外。

    规则层要求恰好 33 个归一化坐标点（rehab_pose/core.py 的 metrics 对长度不符直接返回空），
    所以这里宁可 400 也不要放半截数据进去。
    """
    status = str(body.get("pose_status", "single_person"))
    if status not in POSE_STATUS_ALLOWED:
        raise ValueError("pose_status 取值不合法")
    raw = body.get("landmarks")
    if status == "single_person":
        if not isinstance(raw, list) or len(raw) != LANDMARK_COUNT:
            raise ValueError("关键点必须是 %d 个" % LANDMARK_COUNT)
    else:
        # 与服务端模型的既有行为一致：没认出唯一一个训练者时不带关键点
        # （rehab_pose/model.py 的 no_person / multiple_people 分支返回空列表），
        # 规则层据此走"暂停测量"路径。
        raw = []
    try:
        width = int(body["width"]); height = int(body["height"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("缺少画面宽高")
    if width <= 0 or height <= 0:
        raise ValueError("画面宽高必须为正")
    points = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("关键点格式不正确")
        try:
            x = float(item.get("x", 0.0)); y = float(item.get("y", 0.0))
            visibility = float(item.get("visibility", 0.0))
        except (TypeError, ValueError):
            raise ValueError("关键点坐标必须是数字")
        if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(visibility)):
            raise ValueError("关键点坐标必须是有限数字")
        # 浏览器版 MediaPipe 的 NormalizedLandmark 没有 presence 字段，
        # 而规则层一律用 min(visibility, presence) 做门槛（core.py、tracking.py）。
        # 缺失时用 visibility 顶上，保证阈值语义与服务端 mediapipe 后端一致。
        presence = item.get("presence")
        try:
            presence = float(presence) if presence is not None else visibility
        except (TypeError, ValueError):
            presence = visibility
        if not np.isfinite(presence):
            presence = visibility
        points.append({"x": x, "y": y, "visibility": visibility, "presence": presence})
    timestamp = body.get("timestamp_s")
    if timestamp is None:
        raise ValueError("缺少画面时间戳")
    return points, status, width, height, float(timestamp)


GUIDANCE = {
    "waiting_for_points": "评估暂停：请让训练侧髋、膝、踝完整入镜。",
    "check_start_pose_and_direction": "请回到动作起始姿势，并保持侧面拍摄、训练腿完整入镜。",
    "hold_start_pose": "保持起始姿势不动，正在完成约 2 秒标定。",
    "ready": "标定完成，可以开始训练。",
}


class LiveAnalyzer:
    def __init__(self, exercise: str, side: str, facing: str, sets: int, reps: int, backend: str = "rtmpose", targets: dict | None = None):
        if exercise not in NAMES:
            raise ValueError("暂不支持这个动作")
        if side not in ("left", "right"):
            raise ValueError("训练腿必须是 left 或 right")
        if facing not in ("auto", "left", "right"):
            raise ValueError("身体朝向必须是 auto、left 或 right")

        if backend not in ("rtmpose", "mediapipe", "browser"):
            raise ValueError("不支持的姿态模型")
        if targets is not None:validate_targets({"1":"seated","2":"supine","6":"squat","8":"stand"}[exercise],targets)
        self.backend = backend
        document = json.loads((ROOT / "config" / "knee_extension.json").read_text(encoding="utf-8-sig"))
        params = dict(document["parameters"])
        # browser 模式下关键点由浏览器里的 MediaPipe 算出，模型与 backend="mediapipe"
        # 用的是同一个 pose_landmarker_full.task（sha256 已核对一致），所以沿用同一组阈值。
        # rtmpose 那组的 min_confidence 与之不同，两组不可混用。
        params.update(document.get("backend_parameters", {}).get(
            "mediapipe" if backend == "browser" else backend, {}))
        params["smoothing_tau_s"] = 0
        self.config = Config(**params)
        self.exercise = exercise
        self.side = side
        self.facing = None if facing == "auto" else facing
        self.auto_facing = AutoFacing(exercise,self.config.min_confidence) if facing == "auto" else None
        self.model = (None if backend == "browser"
                      else RTMPoseModel(RTM_MODEL_DIR, "detected") if backend == "rtmpose"
                      else PoseModel(ROOT / "models" / "pose_landmarker_full.task"))
        # Reuse the desktop association logic with the already loaded tiny detector.
        # Only the initial single person is auto-selected; never switch after loss.
        if backend == "rtmpose":
            self.model.roi_mode = "locked"
            self.model.subject = RecoveringSubjectLock()
            self.model.appearance_extractor = stable_appearance
            self.model.subject.confirm()
        self.tracker = PoseTracker(side, self.config.min_confidence, TrackingConfig(**document.get("tracking", {})))
        rules = ExerciseRulesConfig(**document.get("exercise_rules", {}))
        self.analyzer = ExerciseAnalyzer(
            exercise,
            self.config,
            document.get("exercise_profiles", {}).get(exercise),
            rules,
        )
        hold_s = 3 if exercise == "1" else 5 if exercise == "2" else 1 if exercise in ("6","8") else 0
        self.analyzer.engine.config.min_hold_s = hold_s
        if targets is not None:
            apply_targets(exercise,targets,self.analyzer,rules)
            hold_s=targets["hold_s"]
        self.effective_targets=targets
        self.measures = MotionMeasures(
            self.facing or "right",
            MeasureConfig(**document.get("measurement", {})),
            self.config.min_confidence,
            exercise,
        )
        if exercise == "2":
            self.analyzer = SupineAnalyzer(targets)
            self.auto_facing = None
        if exercise == "8": self.analyzer = SitStandAnalyzer(targets)
        if exercise == "6": self.analyzer = SquatAnalyzer(targets)
        self.extra_feedback = ExerciseFeedback(exercise, rules)
        self.training = TrainingSession(TrainingPlan(sets=sets, reps_per_set=reps, hold_s=hold_s, rest_s=targets["rest_s"] if targets is not None else 30))
        self.tracking_config = TrackingConfig(**document.get("tracking", {}))
        self.started = time.monotonic()
        self.last_seen = self.started
        self.feedback_history: list[dict] = []
        self.lock = threading.Lock()
        self.batch_lock = threading.Lock()
        self.group_quality = {}
        self.finished = False
        self.cached_result = None

    def select_subject(self, body):
        with self.lock:
            if self.backend == "browser":
                if body.get("reset") is not True:
                    raise ValueError("浏览器训练者请在画面中选择，只支持重置测量基线")
            else:
                if self.backend != "rtmpose":
                    raise ValueError("人物锁定请使用 RTMPose")
                subject = self.model.subject
                if body.get("reset"):
                    subject.reset()
                else:
                    x, y = float(body["x"]), float(body["y"])
                    if not np.isfinite(x) or not np.isfinite(y):
                        raise ValueError("无效的人物选择坐标")
                    subject.click(x, y)
                    subject.confirm()
            self.tracker = PoseTracker(self.side, self.config.min_confidence, self.tracking_config)
            self.measures.reset()
            if self.auto_facing:
                self.auto_facing.reset()
                self.facing=None
            self.analyzer.abort(self.analyzer.engine.last_t or 0, "subject_selection")
            if self.exercise == "8":
                self.analyzer.sit=None;self.analyzer.stand=None;self.analyzer.pending_stand=None;self.analyzer.stage="need_sit"
            if self.exercise == "6":
                self.analyzer.base=None;self.analyzer.cal.clear();self.analyzer.samples.clear();self.analyzer.previous=None;self.analyzer.stage="hold_start_pose" if self.analyzer.setup else "confirm_support"
            if self.exercise == "2":
                self.analyzer.base = None
                self.analyzer.surface = None
                self.analyzer.cal.clear()
            return {"ok": True}

    def close(self):
        if self.model is not None:
            self.model.close()

    def _prelude(self, timestamp_s):
        """时间戳校验与每帧只跑一次的状态推进。调用方必须已持有 self.lock。

        单独拆出来是因为 self.training.tick(t) 是每帧只能执行一次的状态迁移，
        它推进出来的 current_group / training_active 会被后面多处消费；两个公开
        入口各自调用一次，绝不能重复执行。
        """
        if self.finished:
            raise ValueError("训练已结束")
        now = time.monotonic()
        t = max(0.001, now - self.started) if timestamp_s is None else float(timestamp_s)
        if not np.isfinite(t) or t < 0 or (self.analyzer.engine.last_t is not None and t <= self.analyzer.engine.last_t):
            raise ValueError("画面时间戳必须递增")
        self.last_seen = now
        self.training.tick(t)
        return now, t, self.training.group, self.training.status == "training"

    def process(self, bgr: np.ndarray, timestamp_s=None) -> dict:
        """本机模式：服务端自己推理。行为与改造前完全一致。"""
        if cv2 is None:
            raise RuntimeError("这台服务器没有安装 opencv，只支持浏览器端出关键点的模式")
        with self.lock:
            now, t, current_group, training_active = self._prelude(timestamp_s)
            height, width = bgr.shape[:2]
            landmarks, pose_status = self.model.detect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), t)
            return self._analyze(landmarks, pose_status, width, height, now, t, current_group, training_active)

    def process_landmarks(self, landmarks, pose_status, width, height, timestamp_s) -> dict:
        """浏览器模式：关键点由客户端算好送来，服务端只跑规则，不加载任何模型。"""
        with self.lock:
            now, t, current_group, training_active = self._prelude(timestamp_s)
            return self._analyze(landmarks, pose_status, width, height, now, t, current_group, training_active)

    def _analyze(self, landmarks, pose_status, width, height, now, t, current_group, training_active) -> dict:
        """规则层调度。整段与改造前 process() 的第 160-316 行逐字一致，只减了一级缩进
        （可用 `git diff -w` 核对：忽略空白后这一段没有任何改动）。

        self.lock 是不可重入的 threading.Lock，所以这里不加锁，由调用方持有。
        """
        if pose_status in ("subject_temporarily_lost", "subject_lost_reconfirm"):
            # An obscured attempt cannot accumulate hold time or complete
            # through an unobserved interval, even when identity recovers.
            if self.exercise not in ("2","6","8"): self.analyzer.abort(t, "subject_occluded_or_uncertain")
        measured, quality = self.tracker.update(t, landmarks, width, height)
        if self.exercise == "6" and "possible_side_switch" in quality.get("quality_flags",[]):
            self.analyzer.abort(t,"side_identity_uncertain");self.analyzer.base=None;self.analyzer.cal.clear()
        direction_status="manual"
        if self.auto_facing:
            resolved,direction_status=self.auto_facing.update(t,measured,landmarks,width)
            self.facing=resolved
            if direction_status=="direction_changed":
                self.facing=resolved
                self.measures.direction=-1 if resolved=="left" else 1
                self.measures.reset()
                self.analyzer.abort(t,"automatic_direction_changed")
                if self.exercise == "6": self.analyzer.base=None;self.analyzer.cal.clear()
            if not resolved or direction_status in ("checking_direction","waiting_for_direction"):
                self.measures.reset()
                self.analyzer.abort(t,"automatic_direction_pending")
                measured={**measured,"visible":False,"value":None}
        if self.exercise in ("2","6","8"):
            reliable = measured["visible"] and all(measured.get("keypoints",{}).get(k,{}).get("confidence",0)>=.7 for k in ("shoulder","hip","knee","ankle"))
            measured = {**measured,"visible":reliable}
        if training_active:
            q = self.group_quality.setdefault(current_group, {"frames": 0, "observed_frames": 0})
            q["frames"] += 1
            q["observed_frames"] += int(measured["visible"])
        before_reps = len(self.analyzer.reps)
        if self.exercise in ("2","6","8"):
            if self.exercise in ("6","8"): self.analyzer.direction = -1 if self.facing == "left" else 1
            if not training_active: self.analyzer.abort(t, "between_sets_or_completed")
            measure, state = self.analyzer.process(t, measured if training_active else {**measured,"visible":False}, width, height)
        else:
            measure = self.measures.update(t, measured, width, height, self.analyzer.state)
            measure["feedback_events"].extend(self.extra_feedback.update(t, measure, self.analyzer.state))

        # Keep legacy explicit-direction requests from silently stalling.
        points = measured.get("keypoints", {})
        direction_mismatch = (self.exercise in ("1", "8") and measured["visible"]
            and measured["value"] <= 130 and "hip" in points and "knee" in points
            and self.measures.direction * (points["knee"]["x"]-points["hip"]["x"]) < -width*.03)
        if self.exercise in ("2","6","8"):
            pass
        elif training_active:
            state = self.analyzer.update(t, measured, measure, quality.get("bridge_pending", False))
        else:
            self.analyzer.abort(t, "between_sets_or_completed")
            state = self.analyzer.engine.update(t, None, False)
            measure["feedback_events"] = []
        new_reps = []
        if len(self.analyzer.reps) > before_reps:
            rep = self.analyzer.reps[-1]
            self.training.record_rep(t, rep)
            new_reps.append(rep)
            comparisons = [
                ("amplitude_met", "AMPLITUDE_BELOW_TARGET", "本次尚未达到目标角度，请在舒适范围内缓慢完成。"),
                ("hold_met", "HOLD_TOO_SHORT", "本次连续保持时间不足。"),
                ("extension_time_met", "EXTENSION_TOO_FAST", "本次下蹲过快。" if self.exercise == "6" else "本次抬起或伸出过快。"),
                ("return_time_met", "RETURN_TOO_FAST", "本次起身过快，请缓慢控制。" if self.exercise == "6" else "本次放回过快，请缓慢控制。"),
            ]
            for key, code, message in comparisons:
                if rep["target_comparison"].get(key) is False:
                    measure["feedback_events"].append(
                        {"code": code, "message": message, "level": "notice", "timestamp_s": t, "rep_index": rep["index"]}
                    )
                    break

        if self.exercise in ("6","8"):
            for attempt in self.analyzer.attempts: attempt.setdefault("training_set",current_group)
        for event in measure["feedback_events"]:
            event["training_set"] = current_group
        self.feedback_history.extend(measure["feedback_events"])
        if self.exercise in ("2","6","8"):
            measured["visible"] = state["detection_status"] == "reliable"
            measure["feedback_events"] = measure["feedback_events"][:1]
        calibration = measure["calibration"]
        guidance_status = calibration["status"]
        guidance = GUIDANCE.get(guidance_status, guidance_status)
        if self.exercise == "2":
            if guidance_status == "select_surface": guidance = "先点击床面标定按钮，沿床沿从头端向脚端选两个点。"
            elif guidance_status == "check_start_pose_and_direction": guidance = "请仰卧放平训练腿，膝盖保持舒适伸直；不能达到时先暂停，请康复师调整。"
            elif guidance_status == "ready": guidance = f"抬腿进入目标±5°且膝屈曲≤10°后计时；本段连续保持 {measure['measurement_metrics'].get('joint_hold_s') or 0:.1f} 秒 / {self.training.plan.hold_s:g} 秒"

        if pose_status == "subject_temporarily_lost":
            guidance = "训练者暂时被遮挡或匹配不确定，已暂停测量；请稍候，正在尝试找回原训练者。"
        elif pose_status in ("select_subject", "confirm_subject", "selection_ambiguous", "subject_lost_reconfirm"):
            guidance = "请点击画面中训练者的人体框，锁定后再开始；旁人单独入镜不会中止训练。"
            if pose_status == "subject_lost_reconfirm":
                guidance = "训练者跟踪丢失或重叠，请重新点击训练者确认。"
        elif self.exercise == "6" and direction_status not in ("checking_direction","waiting_for_direction"):
            stage_messages={"confirm_support":"先确认双手扶稳支撑物，再点击开始站姿标定。","hold_start_pose":"扶稳，舒适站立保持2秒，正在标定。","check_start_pose_and_direction":"请舒适站直；初始屈膝过大或目标过近，请让康复师调整。","ready":f"缓慢下蹲至目标附近，再慢慢站回；本段连续保持 {measure['measurement_metrics'].get('joint_hold_s') or 0:.1f} 秒 / {self.training.plan.hold_s:g} 秒"}
            guidance=stage_messages.get(guidance_status,"正在准备微蹲标定")
            if not measured["visible"] and guidance_status!="confirm_support": guidance="暂时看不清，请调整手机位置。"
        elif self.exercise == "8":
            stage_messages={"need_sit":"先记录座椅及辅助方式，再点击采集坐姿。","capture_sit":"坐稳保持2秒，正在采集坐姿基线。","need_stand":"请在能够安全完成的前提下舒适站起，再点击采集站姿。","capture_stand":"舒适站稳保持2秒；不要为标定强行顶膝。","confirm_stand":"请人工核对是否舒适站直，再点击确认站姿。","return_to_sit":"请慢慢坐回；准备动作不计次。","ready":f"上身稍向前，慢慢站起；站稳后慢慢坐回。当前连续保持 {measure['measurement_metrics'].get('joint_hold_s') or 0:.1f} 秒"}
            guidance=stage_messages.get(guidance_status,"正在准备坐站标定")
            if not measured["visible"]: guidance="暂时看不清，请调整手机位置。"
        elif direction_mismatch:
            guidance = "朝向与起始姿势不一致，请重新选择训练者，并保持侧面起始姿势。"
        elif self.auto_facing and direction_status in ("checking_direction","waiting_for_direction"):
            guidance = ("正在自动判断朝向，请侧身站稳，让头部、髋、膝、踝入镜。"
                        if self.exercise=="6" else "正在自动判断朝向，请侧对镜头，保持动作起始姿势，髋、膝、踝完整入镜。")
        elif guidance_status == "hold_start_pose":
            start_pose = {"1": "放下小腿坐稳", "2": "仰卧放平训练腿", "6": "扶稳站直", "8": "坐稳"}[self.exercise]
            guidance = f"{start_pose}，标定进度 {round(calibration['progress']*100)}%，完成后才开始计次。"
        elif pose_status == "multiple_people":
            guidance = "检测到多人，已暂停计数。请确保画面中只有训练者。"
        elif pose_status == "no_person":
            guidance = "没有检测到训练者，请调整相机位置。"

        elif not measured["visible"]:
            explanations = {
                "possible_side_switch": "训练腿左右对应不稳定，已暂停评估；请分开双腿并确认所选训练侧。",
                "leg_length_jump": "腿部关键点位置跳变，已暂停评估；请保持侧面拍摄，减少衣物和椅子的遮挡。",
                "stabilizing": "正在稳定腿部关键点，请保持起始姿势片刻。",
            }
            for flag in quality.get("quality_flags", []):
                if flag in explanations:
                    guidance = explanations[flag]
                    break

        if self.training.status == "resting":
            guidance = f"本组次数已完成，休息还剩 {self.training.snapshot(t)['rest_remaining_s']:.0f} 秒。"
        elif self.training.status == "completed":
            guidance = "计划次数已完成，正在生成本次训练简报。"
        return {
            "schema_version": "1.2-live",
            "backend": self.backend,
            "subject": ({**self.model.subject.snapshot(), "boxes": [b.tolist() for b in self.model.subject.boxes]}
                        if self.backend == "rtmpose" else None),
            "frame_size": {"width": width, "height": height},
            "processing_ms": round((time.monotonic()-now)*1000, 1),
            "timestamp_s": t,
            "exercise": NAMES[self.exercise],
            "side": self.side,
            "facing": self.facing,
            "facing_mode": "auto" if self.auto_facing else "manual",
            "facing_status": direction_status,
            "pose_status": pose_status,
            "value": measured.get("value"),
            "aux": measured.get("aux", {}),
            "visible": bool(measured["visible"]),
            "confidence": measured.get("confidence", 0),
            "keypoints": measured.get("keypoints", {}),
            "quality_flags": quality.get("quality_flags", []),
            "measurement_source": quality.get("measurement_source", "unavailable"),
            "phase": state["phase"],
            "completed_reps": state["completed_reps"],
            "detection_status": state["detection_status"],
            "measurement_metrics": measure["measurement_metrics"],
            "calibration": calibration,
            "guidance": {"status": guidance_status, "message": guidance},
            "feedback_events": measure["feedback_events"],
            "new_reps": new_reps,
            "training_progress": self.training.snapshot(t),
        }

    def result(self) -> dict:
        with self.lock:
            if self.cached_result is not None:
                return self.cached_result
            self.finished = True
            t = max(self.analyzer.engine.last_t or 0, time.monotonic() - self.started)
            self.analyzer.finish()
            if self.exercise in ("6","8"):
                for attempt in self.analyzer.attempts: attempt.setdefault("training_set",self.training.group)
            self.training.finish(t, "user_stopped")
            reps = list(self.analyzer.reps)
            valid = sum(1 for rep in reps if rep.get("target_completed", bool(rep.get("target_comparison", {}).get("amplitude_met")
                        and rep.get("target_comparison", {}).get("hold_met"))))
            training = self.training.result(t)
            training["effective_targets"]=self.effective_targets
            if self.exercise == "2":
                training["rule_version"]="slr_v0.1_surface"
                training["model_version"]=self.backend
                training["reference_frame"]="supine_surface"
                training["surface_points"]=self.analyzer.surface
                training["baseline"]=self.analyzer.base
                training["filter"]="causal_median_0.15s"
                training["tolerances"]={"entry_deg":5,"hold_deg":8,"knee_entry_flexion_deg":10,"knee_hold_flexion_deg":15}
            if self.exercise == "8":
                training.update(rule_version="sts_v0.1_dual_baseline",model_version=self.backend,filter="causal_median_0.15s",setup=self.analyzer.setup,baselines={"sit":self.analyzer.sit,"stand":self.analyzer.stand},attempts=self.analyzer.attempts,occlusion_intervals=self.analyzer.gaps)
            if self.exercise == "6":
                training.update(rule_version="squat_v0.1_joint",model_version=self.backend,filter="causal_median_0.15s",setup=self.analyzer.setup,baseline=self.analyzer.base,attempts=self.analyzer.attempts,occlusion_intervals=self.analyzer.gaps)
            brief = build_brief(self.exercise, self.side, training, reps, self.feedback_history,
                                self.group_quality, self.analyzer.interrupted)
            if self.exercise in ("6","8"):
                brief["attempted_reps"]=len(self.analyzer.attempts)
                brief["unable_to_evaluate"]=sum(a["evaluation_status"]=="unable_to_evaluate" for a in self.analyzer.attempts)
                brief["incomplete_attempts"]=sum(a["evaluation_status"]=="incomplete" for a in self.analyzer.attempts)
                brief["goal_reps"]=sum(a.get("goal_met",False) for a in self.analyzer.attempts)
                brief["goal_rate"]=None if not reps else brief["goal_reps"]/len(reps)
                if brief["incomplete_attempts"]:
                    brief["suggestions"].insert(0,"有尝试未确认完整微蹲，请扶稳后缓慢下蹲、站回，不为补次数强行完成。" if self.exercise == "6" else "有尝试未确认完整坐站；在舒适范围内站稳后再坐回，不为补次数强行完成。")
                if brief["unable_to_evaluate"]:
                    brief["suggestions"].insert(0,"部分尝试因画面中断无法评价，请调整取景后复测。")
            self.cached_result = {
                "exercise": NAMES[self.exercise], "side": self.side,
                "training_session": training, "repetitions": reps,
                "rule_version": "slr_v0.1_surface" if self.exercise == "2" else "sts_v0.1_dual_baseline" if self.exercise == "8" else "squat_v0.1_joint" if self.exercise == "6" else None,
                "reps_done": len(reps), "reps_valid": valid,
                "feedback_events": self.feedback_history,
                "brief_report": brief, "brief_report_text": brief_text(brief),
            }
            return self.cached_result


SESSIONS: dict[str, LiveAnalyzer] = {}
SESSIONS_LOCK = threading.Lock()


def authenticate(headers):
    """复用业务后端已有的 token 体系，不另发一套凭证。

    REHAB_VISION_AUTH 默认 off，本机联调一行都不用改；部署脚本把它打开后，
    /start 与每帧上报都必须带 Authorization: Bearer <token>。
    backend/db.py 的 user_by_token 是不依赖 FastAPI 的纯函数，可以直接复用。
    """
    if not VISION_AUTH:
        return None
    raw = headers.get("Authorization", "") or ""
    token = raw[7:].strip() if raw[:7].lower() == "bearer " else ""
    if not token:
        raise PermissionError("需要登录后再开始训练")
    backend_dir = str(REPO / "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    import db as backend_db
    con = backend_db.connect()
    try:
        user = backend_db.user_by_token(con, token)
    finally:
        con.close()
    if not user:
        raise PermissionError("登录状态已失效，请重新登录")
    return user["id"]


def reap_idle_sessions():
    """回收没人再发帧的会话。

    LiveAnalyzer.last_seen 之前只写不读，会话建了就一直留着；只监听本机时无所谓，
    挂到公网后必须有人清理，否则内存会随访客数单调增长。
    """
    while True:
        time.sleep(30)
        now = time.monotonic()
        with SESSIONS_LOCK:
            stale = [k for k, v in SESSIONS.items() if now - v.last_seen > SESSION_IDLE_S]
            dropped = [SESSIONS.pop(k) for k in stale]
        for session in dropped:
            try:
                session.close()
            except Exception as exc:
                print("vision reap error", repr(exc), flush=True)
        if dropped:
            print("vision reaped %d idle session(s)" % len(dropped), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "RehabVision/1.0"

    def log_message(self, fmt, *args):
        print("vision", self.address_string(), fmt % args, flush=True)

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if "*" in VISION_ORIGINS:
            allowed = "*"
        elif origin and origin in VISION_ORIGINS:
            allowed = origin
        else:
            allowed = VISION_ORIGINS[0] if VISION_ORIGINS else "null"
        self.send_header("Access-Control-Allow-Origin", allowed)
        if allowed != "*":
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Capture-Time, Authorization")

    def _json(self, status: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _route(self) -> str:
        """去掉反向代理前缀后的路径。没配前缀时与 self.path 完全相同。"""
        path = self.path
        if VISION_PREFIX and (path == VISION_PREFIX or path.startswith(VISION_PREFIX + "/")):
            path = path[len(VISION_PREFIX):] or "/"
        return path

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("请求体为空或过大")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self._route() == "/healthz":
            return self._json(200, {"ok": True, "service": "rehab-vision", "sessions": len(SESSIONS),
                                    "auth": "on" if VISION_AUTH else "off", "max_sessions": MAX_SESSIONS,
                                    "remote_rtmpose_ready": reference_status()["ready"], "reference_id": reference_status()["reference_id"]})
        self._json(404, {"error": "not_found"})

    def do_POST(self):
        try:
            if self._route() == "/api/live/start":
                owner = authenticate(self.headers)
                with SESSIONS_LOCK:
                    if len(SESSIONS) >= MAX_SESSIONS:
                        return self._json(429, {"error": "当前训练人数已满，请稍后再试"})
                body = self._body()
                # 浏览器识别只上传关键点、服务端不加载任何模型，不受「服务器只跑 RTMPose」开关约束。
                if body.get("backend") != "browser" and (body.get("required_reference") or REMOTE_RTMPOSE):
                    profile = reference_status()
                    if not profile["ready"] or body.get("required_reference") != profile["reference_id"] or body.get("backend") != "rtmpose":
                        return self._json(503, {"error":"服务器尚未准备好与本地一致的RTMPose模型及规则，请联系管理员部署；不会自动切换模型"})
                if str(body.get("exercise","1")) == "2" and body.get("rule_version") != "slr_v0.1_surface":
                    raise ValueError("动作二已升级为床面角规则，请刷新网页后重新开始")
                if str(body.get("exercise","1")) == "8" and body.get("rule_version") != "sts_v0.1_dual_baseline":
                    raise ValueError("坐站已升级为双基线规则，请刷新网页")
                if str(body.get("exercise","1")) == "6" and body.get("rule_version") != "squat_v0.1_joint":
                    raise ValueError("微蹲已升级为膝屈曲规则，请刷新网页")
                with START_LOCK:
                    with SESSIONS_LOCK:
                        if len(SESSIONS) >= MAX_SESSIONS:
                            return self._json(429, {"error":"当前训练人数已满，请稍后再试"})
                    session = LiveAnalyzer(
                        exercise=str(body.get("exercise", "1")),
                        side=str(body.get("side", "left")),
                        facing=str(body.get("facing", "auto")),
                        sets=int(body.get("sets", 1)),
                        reps=int(body.get("reps", 10)),
                        backend=str(body.get("backend", "rtmpose")),
                        targets=body.get("targets"),
                    )
                    session_id = uuid.uuid4().hex
                    session.owner = owner
                    with SESSIONS_LOCK:
                        if len(SESSIONS) >= MAX_SESSIONS:
                            session.close()
                            return self._json(429, {"error": "当前训练人数已满，请稍后再试"})
                        SESSIONS[session_id] = session
                    return self._json(200, {"session_id": session_id, "model": session.backend, "stores_video": False, "reference_id": reference_status()["reference_id"]})

            parts = self._route().strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "live"]:
                session_id, action = parts[2], parts[3]
                with SESSIONS_LOCK:
                    session = SESSIONS.get(session_id)
                if session is None:
                    return self._json(404, {"error": "训练会话不存在或已经结束"})
                caller = authenticate(self.headers)
                if VISION_AUTH and getattr(session, "owner", None) != caller:
                    return self._json(403, {"error": "无权操作该训练会话"})

                if action == "squat-setup":
                    body=self._body()
                    if session.exercise != "6": raise ValueError("仅微蹲支持此设置")
                    with session.lock: session.analyzer.configure(body)
                    return self._json(200,{"ok":True})
                if action == "sts-calibration":
                    body=self._body()
                    if session.exercise != "8": raise ValueError("仅坐站支持此标定")
                    with session.lock: session.analyzer.calibrate(body.get("stage"),body.get("setup"))
                    return self._json(200,{"ok":True})
                if action == "surface":
                    body = self._body()
                    if session.exercise != "2": raise ValueError("仅动作2支持床面标定")
                    with session.lock: session.analyzer.set_surface(body.get("points"))
                    return self._json(200, {"ok":True})
                if action == "subject":
                    return self._json(200, session.select_subject(self._body()))
                if action == "facing":
                    with session.lock:
                        session.auto_facing = None  # Legacy API only; patient UI uses auto.
                        session.facing = "right" if session.facing == "left" else "left"
                        session.measures.direction *= -1
                        session.measures.reset()
                        session.analyzer.abort(session.analyzer.engine.last_t or 0, "facing_changed")
                    return self._json(200, {"facing": session.facing})
                if action == "frames":
                    if session.backend != "rtmpose": raise ValueError("图像批量入口仅支持RTMPose")
                    decoded = decode_batch(self._body(), cv2)
                    with session.batch_lock:
                        return self._json(200, process_batch(session, decoded))
                if action == "frame":
                    if cv2 is None:
                        raise ValueError("这台服务器只支持浏览器端出关键点的模式，请刷新网页后重试")
                    if self.headers.get("Content-Type", "").startswith("image/jpeg"):
                        size = int(self.headers.get("Content-Length", 0))
                        if not 0 < size <= MAX_BODY_BYTES:
                            raise ValueError("画面大小无效")
                        frame = cv2.imdecode(np.frombuffer(self.rfile.read(size), dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is None:
                            raise ValueError("无法读取画面")
                        return self._json(200, session.process(frame, float(self.headers["X-Capture-Time"])))
                    body = self._body()
                    encoded = str(body.get("image", ""))
                    if "," in encoded:
                        encoded = encoded.split(",", 1)[1]
                    raw = base64.b64decode(encoded, validate=True)
                    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        raise ValueError("无法读取摄像头画面")
                    return self._json(200, session.process(frame, body.get("timestamp_s")))

                if action == "landmarks":
                    # 浏览器模式：关键点已在客户端算好，服务端只跑规则层。
                    # 画面不离开用户设备，这里收到的只有 33 个归一化坐标。
                    body = self._body()
                    frames = body.get("frames")
                    if frames is None:
                        points, status, width, height, timestamp = validate_landmarks(body)
                        return self._json(200, session.process_landmarks(points, status, width, height, timestamp))
                    # 批量形式：逐帧按序喂给规则层，效果与逐帧单发完全一致，
                    # 只是少了 N-1 次公网往返。返回最后一帧的状态，并把这一批里
                    # 产生的计次与提示事件全部带上，避免中间帧的事件被丢掉。
                    if not isinstance(frames, list) or not frames:
                        raise ValueError("frames 必须是非空数组")
                    if len(frames) > MAX_FRAMES_PER_BATCH:
                        raise ValueError("一次最多 %d 帧" % MAX_FRAMES_PER_BATCH)
                    latest, new_reps, events = None, [], []
                    for item in frames:
                        points, status, width, height, timestamp = validate_landmarks(item)
                        latest = session.process_landmarks(points, status, width, height, timestamp)
                        new_reps.extend(latest.get("new_reps") or [])
                        events.extend(latest.get("feedback_events") or [])
                    return self._json(200, {**latest, "new_reps": new_reps,
                                            "feedback_events": events, "batch_frames": len(frames)})

                if action == "stop":
                    with SESSIONS_LOCK:
                        session = SESSIONS.pop(session_id, None)
                    if session is None:
                        return self._json(404, {"error": "训练会话不存在或已经结束"})
                    result = session.result()
                    session.close()
                    return self._json(200, result)

            self._json(404, {"error": "not_found"})
        except PermissionError as exc:
            self._json(401, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            # 异常原文只进日志，不回给客户端：这个服务现在会对公网暴露。
            print("vision error", repr(exc), flush=True)
            self._json(500, {"error": "视觉服务处理失败"})


def main():
    server = ThreadingHTTPServer((VISION_BIND, VISION_PORT), Handler)
    threading.Thread(target=reap_idle_sessions, daemon=True).start()
    print("视觉算法服务：http://%s:%d  鉴权=%s  会话上限=%d  (Ctrl+C 停止)"
          % (VISION_BIND, VISION_PORT, "on" if VISION_AUTH else "off", MAX_SESSIONS), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        with SESSIONS_LOCK:
            sessions = list(SESSIONS.values())
            SESSIONS.clear()
        for session in sessions:
            session.close()


if __name__ == "__main__":
    main()
