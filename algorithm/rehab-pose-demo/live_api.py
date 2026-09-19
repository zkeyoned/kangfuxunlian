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

from rehab_pose.core import Config
from rehab_pose.exercise_rules import ExerciseFeedback, ExerciseRulesConfig
from rehab_pose.exercises import ExerciseAnalyzer, NAMES
from rehab_pose.measures import MeasureConfig, MotionMeasures
from rehab_pose.model import PoseModel
from rehab_pose.session import TrainingPlan, TrainingSession
from rehab_pose.tracking import PoseTracker, TrackingConfig


ROOT = Path(__file__).resolve().parent
MAX_BODY_BYTES = 2_500_000


GUIDANCE = {
    "waiting_for_points": "评估暂停：请让训练侧髋、膝、踝完整入镜。",
    "check_start_pose_and_direction": "请回到动作起始姿势，并检查训练腿和身体朝向。",
    "hold_start_pose": "保持起始姿势不动，正在完成约 2 秒标定。",
    "ready": "标定完成，可以开始训练。",
}


class LiveAnalyzer:
    def __init__(self, exercise: str, side: str, facing: str, sets: int, reps: int):
        if exercise not in NAMES:
            raise ValueError("暂不支持这个动作")
        if side not in ("left", "right"):
            raise ValueError("训练腿必须是 left 或 right")
        if facing not in ("left", "right"):
            raise ValueError("身体朝向必须是 left 或 right")

        document = json.loads((ROOT / "config" / "knee_extension.json").read_text(encoding="utf-8-sig"))
        params = dict(document["parameters"])
        params.update(document.get("backend_parameters", {}).get("mediapipe", {}))
        params["smoothing_tau_s"] = 0
        self.config = Config(**params)
        self.exercise = exercise
        self.side = side
        self.facing = facing
        self.model = PoseModel(ROOT / "models" / "pose_landmarker_full.task")
        self.tracker = PoseTracker(side, self.config.min_confidence, TrackingConfig(**document.get("tracking", {})))
        rules = ExerciseRulesConfig(**document.get("exercise_rules", {}))
        self.analyzer = ExerciseAnalyzer(
            exercise,
            self.config,
            document.get("exercise_profiles", {}).get(exercise),
            rules,
        )
        hold_s = 3 if exercise == "1" else 5 if exercise == "2" else 0
        self.analyzer.engine.config.min_hold_s = hold_s
        self.measures = MotionMeasures(
            facing,
            MeasureConfig(**document.get("measurement", {})),
            self.config.min_confidence,
            exercise,
        )
        self.extra_feedback = ExerciseFeedback(exercise, rules)
        self.training = TrainingSession(TrainingPlan(sets=sets, reps_per_set=reps, hold_s=hold_s, rest_s=30))
        self.started = time.monotonic()
        self.last_seen = self.started
        self.feedback_history: list[dict] = []
        self.lock = threading.Lock()

    def close(self):
        self.model.close()

    def process(self, bgr: np.ndarray) -> dict:
        with self.lock:
            now = time.monotonic()
            t = max(0.001, now - self.started)
            self.last_seen = now
            self.training.tick(t)
            height, width = bgr.shape[:2]
            landmarks, pose_status = self.model.detect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), t)
            measured, quality = self.tracker.update(t, landmarks, width, height)
            measure = self.measures.update(t, measured, width, height, self.analyzer.state)
            measure["feedback_events"].extend(self.extra_feedback.update(t, measure, self.analyzer.state))

            before_reps = len(self.analyzer.reps)
            state = self.analyzer.update(
                t,
                measured,
                measure,
                quality.get("bridge_pending", False),
            )
            new_reps = []
            if len(self.analyzer.reps) > before_reps:
                rep = self.analyzer.reps[-1]
                self.training.record_rep(t, rep)
                new_reps.append(rep)
                comparisons = [
                    ("amplitude_met", "AMPLITUDE_BELOW_TARGET", "本次尚未达到目标角度，请在舒适范围内缓慢完成。"),
                    ("hold_met", "HOLD_TOO_SHORT", "本次连续保持时间不足。"),
                    ("extension_time_met", "EXTENSION_TOO_FAST", "本次抬起或伸出过快。"),
                    ("return_time_met", "RETURN_TOO_FAST", "本次放回过快，请缓慢控制。"),
                ]
                for key, code, message in comparisons:
                    if rep["target_comparison"].get(key) is False:
                        measure["feedback_events"].append(
                            {"code": code, "message": message, "level": "notice", "timestamp_s": t, "rep_index": rep["index"]}
                        )
                        break

            self.feedback_history.extend(measure["feedback_events"])
            calibration = measure["calibration"]
            guidance_status = calibration["status"]
            guidance = GUIDANCE.get(guidance_status, guidance_status)
            if pose_status == "multiple_people":
                guidance = "检测到多人，已暂停计数。请确保画面中只有训练者。"
            elif pose_status == "no_person":
                guidance = "没有检测到训练者，请调整相机位置。"

            return {
                "schema_version": "1.0-live",
                "timestamp_s": t,
                "exercise": NAMES[self.exercise],
                "side": self.side,
                "facing": self.facing,
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
        t = max(0.001, time.monotonic() - self.started)
        self.training.finish(t, "user_stopped")
        reps = list(self.analyzer.reps)
        valid = sum(
            1
            for rep in reps
            if rep.get("target_comparison", {}).get("amplitude_met")
            and rep.get("target_comparison", {}).get("hold_met")
        )
        return {
            "exercise": NAMES[self.exercise],
            "side": self.side,
            "training_session": self.training.result(t),
            "repetitions": reps,
            "reps_done": len(reps),
            "reps_valid": valid,
            "feedback_events": self.feedback_history,
        }


SESSIONS: dict[str, LiveAnalyzer] = {}
SESSIONS_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "RehabVision/1.0"

    def log_message(self, fmt, *args):
        print("vision", self.address_string(), fmt % args, flush=True)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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
                session = LiveAnalyzer(
                    exercise=str(body.get("exercise", "1")),
                    side=str(body.get("side", "left")),
                    facing=str(body.get("facing", "left")),
                    sets=int(body.get("sets", 1)),
                    reps=int(body.get("reps", 10)),
                )
                session_id = uuid.uuid4().hex
                with SESSIONS_LOCK:
                    SESSIONS[session_id] = session
                return self._json(200, {"session_id": session_id, "model": "MediaPipe Pose Full", "stores_video": False})

            parts = self.path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "live"]:
                session_id, action = parts[2], parts[3]
                with SESSIONS_LOCK:
                    session = SESSIONS.get(session_id)
                if session is None:
                    return self._json(404, {"error": "训练会话不存在或已经结束"})

                if action == "frame":
                    body = self._body()
                    encoded = str(body.get("image", ""))
                    if "," in encoded:
                        encoded = encoded.split(",", 1)[1]
                    raw = base64.b64decode(encoded, validate=True)
                    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        raise ValueError("无法读取摄像头画面")
                    return self._json(200, session.process(frame))

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
