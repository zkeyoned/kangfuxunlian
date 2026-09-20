"""本机网页摄像头桥接服务。

浏览器只发送临时 JPEG 帧；服务不会保存视频或关键点。姿态识别和动作状态机
复用 rehab_pose 中的实现。此文件是本地联调层，不改变算法模块的数据结构。
"""
from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import uuid

import cv2
import numpy as np

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
MAX_BODY_BYTES = 2_500_000


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

        if backend not in ("rtmpose", "mediapipe"):
            raise ValueError("不支持的姿态模型")
        if targets is not None:validate_targets({"1":"seated","2":"supine","6":"squat","8":"stand"}[exercise],targets)
        self.backend = backend
        document = json.loads((ROOT / "config" / "knee_extension.json").read_text(encoding="utf-8-sig"))
        params = dict(document["parameters"])
        params.update(document.get("backend_parameters", {}).get(backend, {}))
        params["smoothing_tau_s"] = 0
        self.config = Config(**params)
        self.exercise = exercise
        self.side = side
        self.facing = None if facing == "auto" else facing
        self.auto_facing = AutoFacing(exercise,self.config.min_confidence) if facing == "auto" else None
        self.model = (RTMPoseModel(ROOT / "models" / "rtmpose", "detected") if backend == "rtmpose"
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
        self.group_quality = {}
        self.finished = False
        self.cached_result = None

    def select_subject(self, body):
        with self.lock:
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
        self.model.close()

    def process(self, bgr: np.ndarray, timestamp_s=None) -> dict:
        with self.lock:
            if self.finished:
                raise ValueError("训练已结束")
            now = time.monotonic()
            t = max(0.001, now - self.started) if timestamp_s is None else float(timestamp_s)
            if not np.isfinite(t) or t < 0 or (self.analyzer.engine.last_t is not None and t <= self.analyzer.engine.last_t):
                raise ValueError("画面时间戳必须递增")
            self.last_seen = now
            self.training.tick(t)
            current_group = self.training.group
            training_active = self.training.status == "training"
            height, width = bgr.shape[:2]
            landmarks, pose_status = self.model.detect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), t)
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


class Handler(BaseHTTPRequestHandler):
    server_version = "RehabVision/1.0"

    def log_message(self, fmt, *args):
        print("vision", self.address_string(), fmt % args, flush=True)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Capture-Time")

    def _json(self, status: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

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
        if self.path == "/healthz":
            return self._json(200, {"ok": True, "service": "rehab-vision", "sessions": len(SESSIONS)})
        self._json(404, {"error": "not_found"})

    def do_POST(self):
        try:
            if self.path == "/api/live/start":
                body = self._body()
                if str(body.get("exercise","1")) == "2" and body.get("rule_version") != "slr_v0.1_surface":
                    raise ValueError("动作二已升级为床面角规则，请刷新网页后重新开始")
                if str(body.get("exercise","1")) == "8" and body.get("rule_version") != "sts_v0.1_dual_baseline":
                    raise ValueError("坐站已升级为双基线规则，请刷新网页")
                if str(body.get("exercise","1")) == "6" and body.get("rule_version") != "squat_v0.1_joint":
                    raise ValueError("微蹲已升级为膝屈曲规则，请刷新网页")
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
                with SESSIONS_LOCK:
                    SESSIONS[session_id] = session
                return self._json(200, {"session_id": session_id, "model": session.backend, "stores_video": False})

            parts = self.path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "live"]:
                session_id, action = parts[2], parts[3]
                with SESSIONS_LOCK:
                    session = SESSIONS.get(session_id)
                if session is None:
                    return self._json(404, {"error": "训练会话不存在或已经结束"})

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
                if action == "frame":
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

                if action == "stop":
                    with SESSIONS_LOCK:
                        session = SESSIONS.pop(session_id, None)
                    result = session.result()
                    session.close()
                    return self._json(200, result)

            self._json(404, {"error": "not_found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            print("vision error", repr(exc), flush=True)
            self._json(500, {"error": "视觉服务处理失败", "detail": str(exc)})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8802), Handler)
    print("视觉算法服务：http://127.0.0.1:8802  (Ctrl+C 停止)", flush=True)
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
