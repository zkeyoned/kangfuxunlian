"""康迹 RehabTrack · 服务端（后端（常）：API / 数据库 / 权限 / 机构端 / 部署与日志）

跑法：  python3 backend/main.py [端口]      默认 8801
文档：  http://127.0.0.1:8801/docs          （FastAPI 自动生成）
前端：  http://127.0.0.1:8801/              （frontend/ 目录静态托管；frontend/ 里没有页面文件时，
                                              根路径返回一段指向 /docs 的 JSON，不影响服务启动）
"""
from __future__ import annotations

import csv
import io
import json
import logging
import logging.handlers
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from scoring import DEFAULT_WEIGHTS, score_item  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
APP_VERSION = "0.1.0"

# ---------- 日志：控制台 + 滚动文件 ----------
db.DATA_DIR.mkdir(parents=True, exist_ok=True)
(db.DATA_DIR / "logs").mkdir(exist_ok=True)
log = logging.getLogger("rehabtrack")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_fh = logging.handlers.RotatingFileHandler(db.DATA_DIR / "logs" / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)

app = FastAPI(title="康迹 RehabTrack API", version=APP_VERSION, docs_url="/docs", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    db.init_db(seed=True)
    log.info("startup version=%s db=%s", APP_VERSION, db.DB_PATH)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    if request.url.path.startswith("/api/") or request.url.path == "/healthz":
        log.info("%s %s %s %.1fms ip=%s", request.method, request.url.path, resp.status_code, ms, request.client.host if request.client else "-")
    return resp


# ---------- 鉴权 ----------
def get_con():
    con = db.connect()
    try:
        yield con
    finally:
        con.close()


def current_user(request: Request, con=Depends(get_con)) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.query_params.get("token", "")
    user = db.user_by_token(con, token) if token else None
    if not user:
        raise HTTPException(401, "未登录或登录已过期")
    if user["role"] == "patient":
        p = db.one(con.execute("SELECT id FROM patients WHERE user_id=?", (user["id"],)))
        user["patient_id"] = p["id"] if p else None
    return user


def require_role(*roles):
    def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, f"需要角色：{'/'.join(roles)}")
        return user
    return dep


def patient_in_scope(con, user: dict, patient_id: int) -> dict:
    """机构隔离：康复师只能看本机构患者；患者只能看自己。"""
    p = db.one(con.execute("SELECT * FROM patients WHERE id=?", (patient_id,)))
    if not p:
        raise HTTPException(404, "患者不存在")
    if user["role"] == "patient" and p["user_id"] != user["id"]:
        raise HTTPException(403, "只能查看自己的数据")
    if user["role"] in ("therapist", "admin") and p["institution_id"] != user["institution_id"]:
        raise HTTPException(403, "不属于你的机构")
    return p


# ---------- 模型 ----------
class LoginIn(BaseModel):
    username: str
    password: str


class SessionStart(BaseModel):
    plan_id: Optional[int] = None
    device: Optional[str] = None
    camera_side: Optional[str] = "side"
    client_version: Optional[str] = None


class RepIn(BaseModel):
    rep_index: int
    peak_angle: Optional[float] = None
    duration_ms: Optional[int] = None
    valid: bool = True
    flags: list[str] = Field(default_factory=list)


class SessionItemIn(BaseModel):
    """前端（景）→ 后端（常） 的核心契约：一组动作做完上传一条。字段说明见 docs/03-接口契约.md"""
    plan_item_id: Optional[int] = None
    exercise_code: str
    set_index: int = 1
    reps_target: int
    reps_done: int
    reps_valid: int
    peak_angle_max: Optional[float] = None
    peak_angle_mean: Optional[float] = None
    duration_ms: Optional[int] = None
    quality_score: Optional[float] = None
    score_breakdown: Optional[dict[str, float]] = None
    compensation_count: int = 0
    capture_quality: Optional[float] = None
    low_confidence: bool = False
    angle_trace: Optional[list[float]] = None
    reps: list[RepIn] = Field(default_factory=list)


class SessionFinish(BaseModel):
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)
    note: Optional[str] = None


class PlanItemIn(BaseModel):
    exercise_code: str
    sets: int = 3
    reps: int = 10
    target_angle: Optional[float] = None
    min_valid_angle: Optional[float] = None
    rest_sec: int = 60
    notes: Optional[str] = None


class PlanIn(BaseModel):
    title: str
    start_date: str
    end_date: Optional[str] = None
    days_per_week: int = 5
    goal_text: Optional[str] = None
    items: list[PlanItemIn]


class PatientIn(BaseModel):
    username: str
    password: str
    display_name: str
    surgery_type: Optional[str] = None
    surgery_date: Optional[str] = None
    affected_side: Optional[str] = None
    phase: Optional[str] = None
    baseline: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class RuleIn(BaseModel):
    exercise_code: str
    version: str
    params: dict[str, Any]
    rationale: Optional[str] = None
    reviewer: Optional[str] = None
    activate: bool = False


# ---------- 小助手 ----------
def active_rule(con, code: str) -> Optional[dict]:
    r = db.one(con.execute("SELECT * FROM rule_versions WHERE exercise_code=? AND is_active=1 ORDER BY id DESC LIMIT 1", (code,)))
    if r:
        r["params"] = json.loads(r["params_json"])
    return r


def plan_with_items(con, plan_id: int) -> Optional[dict]:
    plan = db.one(con.execute("SELECT * FROM plans WHERE id=?", (plan_id,)))
    if not plan:
        return None
    items = db.rows(con.execute(
        "SELECT pi.*, e.name AS exercise_name, e.metric, e.direction, e.camera_side, rv.version AS rule_version, rv.params_json "
        "FROM plan_items pi JOIN exercises e ON e.code=pi.exercise_code "
        "LEFT JOIN rule_versions rv ON rv.id=pi.rule_version_id WHERE plan_id=? ORDER BY sort_order", (plan_id,)))
    for it in items:
        rule = None
        if it.get("params_json"):
            rule = {"version": it["rule_version"], "params": json.loads(it["params_json"])}
        else:
            ar = active_rule(con, it["exercise_code"])
            rule = {"version": ar["version"], "params": ar["params"]} if ar else None
        it["rule"] = rule
        it.pop("params_json", None)
    plan["items"] = items
    return plan


def session_detail(con, sid: int) -> dict:
    s = db.one(con.execute("SELECT * FROM sessions WHERE id=?", (sid,)))
    if not s:
        raise HTTPException(404, "训练不存在")
    items = db.rows(con.execute("SELECT si.*, e.name AS exercise_name FROM session_items si JOIN exercises e ON e.code=si.exercise_code WHERE session_id=? ORDER BY id", (sid,)))
    for it in items:
        it["score_breakdown"] = json.loads(it.pop("score_breakdown_json") or "{}")
        it["angle_trace"] = json.loads(it.pop("angle_trace_json") or "null")
        it["reps"] = db.rows(con.execute("SELECT rep_index,peak_angle,duration_ms,valid,flags_json FROM reps WHERE session_item_id=? ORDER BY rep_index", (it["id"],)))
        for r in it["reps"]:
            r["flags"] = json.loads(r.pop("flags_json") or "[]")
    s["items"] = items
    s["rule_versions"] = json.loads(s.pop("rule_versions_json") or "{}")
    return s


def trend(con, patient_id: int, exercise: Optional[str], metric: str) -> list[dict]:
    if metric not in ("peak_angle_max", "quality_score", "reps_valid", "compensation_count"):
        raise HTTPException(400, "metric 不支持")
    sql = (f"SELECT substr(s.started_at,1,10) AS day, si.exercise_code, "
           f"{'MAX' if metric=='peak_angle_max' else 'AVG'}(si.{metric}) AS value "
           "FROM session_items si JOIN sessions s ON s.id=si.session_id "
           "WHERE s.patient_id=? AND s.status='finished' AND si.low_confidence=0 ")
    args: list = [patient_id]
    if exercise:
        sql += "AND si.exercise_code=? "
        args.append(exercise)
    sql += "GROUP BY day, si.exercise_code ORDER BY day"
    out = db.rows(con.execute(sql, args))
    for r in out:
        r["value"] = round(r["value"], 1) if r["value"] is not None else None
    return out


def generate_alerts(con, patient_id: int, session: dict) -> list[dict]:
    """训练结束时跑一遍规则，生成给康复师的提醒。规则本身故意简单、可解释。"""
    created = []
    def add(t, sev, msg):
        con.execute("INSERT INTO alerts(patient_id,session_id,type,severity,message) VALUES(?,?,?,?,?)", (patient_id, session["id"], t, sev, msg))
        created.append({"type": t, "severity": sev, "message": msg})

    if session.get("pain_score") is not None and session["pain_score"] >= 6:
        add("pain_high", "high", f"训练后疼痛自评 {session['pain_score']}/10，建议联系患者")
    for it in session["items"]:
        if it["reps_done"] and it["compensation_count"] / it["reps_done"] >= 0.3:
            add("compensation_high", "warn", f"{it['exercise_name']}：{it['compensation_count']}/{it['reps_done']} 次出现代偿")
        if it.get("capture_quality") is not None and it["capture_quality"] < 0.6:
            add("low_capture", "info", f"{it['exercise_name']}：拍摄质量偏低（{int(it['capture_quality']*100)}%），本组数据仅供参考")
        if it.get("peak_angle_max") is not None and not it["low_confidence"]:
            prev = db.rows(con.execute(
                "SELECT si.peak_angle_max FROM session_items si JOIN sessions s ON s.id=si.session_id "
                "WHERE s.patient_id=? AND si.exercise_code=? AND s.id<? AND s.status='finished' AND si.low_confidence=0 "
                "ORDER BY s.id DESC LIMIT 3", (patient_id, it["exercise_code"], session["id"])))
            vals = [p["peak_angle_max"] for p in prev if p["peak_angle_max"] is not None]
            if len(vals) >= 2:
                base = sum(vals) / len(vals)
                direction = db.one(con.execute("SELECT direction FROM exercises WHERE code=?", (it["exercise_code"],)))["direction"]
                drop = (base - it["peak_angle_max"]) if direction == "up" else (it["peak_angle_max"] - base)
                if drop >= 8:
                    add("angle_drop", "warn", f"{it['exercise_name']}：峰值角度较近 3 次均值退步 {drop:.0f}°")
    con.commit()
    return created


def inactive_check(con, patient_id: int) -> Optional[dict]:
    last = db.one(con.execute("SELECT MAX(started_at) AS t FROM sessions WHERE patient_id=? AND status='finished'", (patient_id,)))
    active = db.one(con.execute("SELECT id FROM plans WHERE patient_id=? AND status='active'", (patient_id,)))
    if not active or not last or not last["t"]:
        return None
    days = (date.today() - datetime.strptime(last["t"][:10], "%Y-%m-%d").date()).days
    if days >= 3:
        exists = db.one(con.execute("SELECT id FROM alerts WHERE patient_id=? AND type='inactive_3d' AND acknowledged_at IS NULL", (patient_id,)))
        if not exists:
            con.execute("INSERT INTO alerts(patient_id,type,severity,message) VALUES(?,?,?,?)", (patient_id, "inactive_3d", "warn", f"已连续 {days} 天未训练"))
            con.commit()
        return {"days": days}
    return None


# ---------- 公共 ----------
@app.get("/healthz")
def healthz(con=Depends(get_con)):
    n = db.one(con.execute("SELECT COUNT(*) AS n FROM users"))["n"]
    return {"ok": True, "version": APP_VERSION, "users": n, "time": db.now()}


@app.post("/api/v1/auth/login")
def login(body: LoginIn, request: Request, con=Depends(get_con)):
    u = db.one(con.execute("SELECT * FROM users WHERE username=? AND is_active=1", (body.username,)))
    if not u or not db.verify_password(body.password, u["password_hash"]):
        db.audit(con, None, "login.fail", f"user:{body.username}", ip=request.client.host if request.client else None)
        raise HTTPException(401, "用户名或密码错误")
    tok = db.issue_token(con, u["id"])
    db.audit(con, u["id"], "login", None, ip=request.client.host if request.client else None)
    out = {k: u[k] for k in ("id", "role", "display_name", "institution_id", "username")}
    if u["role"] == "patient":
        p = db.one(con.execute("SELECT id FROM patients WHERE user_id=?", (u["id"],)))
        out["patient_id"] = p["id"] if p else None
    return {"token": tok, "user": out}


@app.post("/api/v1/auth/logout")
def logout(request: Request, user=Depends(current_user), con=Depends(get_con)):
    auth = request.headers.get("authorization", "")
    con.execute("DELETE FROM tokens WHERE token=?", (auth[7:],))
    con.commit()
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user=Depends(current_user)):
    return {k: v for k, v in user.items() if k != "password_hash"}


@app.get("/api/v1/exercises")
def exercises(con=Depends(get_con)):
    out = db.rows(con.execute("SELECT * FROM exercises ORDER BY code"))
    for e in out:
        r = active_rule(con, e["code"])
        e["active_rule"] = {"id": r["id"], "version": r["version"], "params": r["params"]} if r else None
    return out


# ---------- 患者端 ----------
@app.get("/api/v1/me/plan/today")
def my_plan_today(user=Depends(require_role("patient")), con=Depends(get_con)):
    pid = user["patient_id"]
    plan = db.one(con.execute("SELECT id FROM plans WHERE patient_id=? AND status='active' ORDER BY id DESC LIMIT 1", (pid,)))
    if not plan:
        return {"plan": None, "items": [], "done_today": {}}
    plan = plan_with_items(con, plan["id"])
    today = date.today().isoformat()
    done = db.rows(con.execute(
        "SELECT si.plan_item_id, COUNT(*) AS sets_done FROM session_items si JOIN sessions s ON s.id=si.session_id "
        "WHERE s.patient_id=? AND substr(s.started_at,1,10)=? AND si.plan_item_id IS NOT NULL GROUP BY si.plan_item_id", (pid, today)))
    patient = db.one(con.execute("SELECT p.*, u.display_name FROM patients p JOIN users u ON u.id=p.user_id WHERE p.id=?", (pid,)))
    patient["baseline"] = json.loads(patient.pop("baseline_json") or "{}")
    return {"plan": plan, "items": plan["items"], "done_today": {d["plan_item_id"]: d["sets_done"] for d in done}, "patient": patient}


@app.post("/api/v1/sessions")
def session_start(body: SessionStart, user=Depends(require_role("patient")), con=Depends(get_con)):
    pid = user["patient_id"]
    snapshot = {}
    for e in db.rows(con.execute("SELECT code FROM exercises")):
        r = active_rule(con, e["code"])
        if r:
            snapshot[e["code"]] = r["version"]
    cur = con.execute(
        "INSERT INTO sessions(patient_id,plan_id,device,camera_side,rule_versions_json,client_version) VALUES(?,?,?,?,?,?)",
        (pid, body.plan_id, (body.device or "")[:200], body.camera_side, json.dumps(snapshot), body.client_version))
    con.commit()
    db.audit(con, user["id"], "session.start", f"session:{cur.lastrowid}")
    return {"session_id": cur.lastrowid, "rule_versions": snapshot}


@app.post("/api/v1/sessions/{sid}/items")
def session_item(sid: int, body: SessionItemIn, user=Depends(require_role("patient")), con=Depends(get_con)):
    s = db.one(con.execute("SELECT * FROM sessions WHERE id=? AND patient_id=?", (sid, user["patient_id"])))
    if not s:
        raise HTTPException(404, "训练不存在")
    if s["status"] != "running":
        raise HTTPException(409, "训练已结束")
    if not db.one(con.execute("SELECT code FROM exercises WHERE code=?", (body.exercise_code,))):
        raise HTTPException(400, f"未知动作 {body.exercise_code}")
    rule = active_rule(con, body.exercise_code)
    params = rule["params"] if rule else {}
    if body.plan_item_id is not None:
        plan_item = db.one(con.execute("SELECT target_angle, min_valid_angle FROM plan_items WHERE id=?", (body.plan_item_id,)))
        if plan_item:
            # 计划项上的个体化目标覆盖规则默认值，参见 docs/03-接口契约.md C 节。
            overrides = {k: v for k, v in plan_item.items() if v is not None}
            params = {**params, **overrides}
    item = body.model_dump()
    item["_too_fast_count"] = sum(1 for r in body.reps if "too_fast" in r.flags)
    score, breakdown = (body.quality_score, body.score_breakdown or {})
    if score is None:
        score, breakdown = score_item(item, params)
    cur = con.execute(
        "INSERT INTO session_items(session_id,plan_item_id,exercise_code,set_index,reps_target,reps_done,reps_valid,peak_angle_max,peak_angle_mean,duration_ms,quality_score,score_breakdown_json,compensation_count,capture_quality,low_confidence,angle_trace_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid, body.plan_item_id, body.exercise_code, body.set_index, body.reps_target, body.reps_done, body.reps_valid, body.peak_angle_max, body.peak_angle_mean, body.duration_ms, score, json.dumps(breakdown, ensure_ascii=False), body.compensation_count, body.capture_quality, 1 if body.low_confidence else 0, json.dumps(body.angle_trace) if body.angle_trace else None))
    item_id = cur.lastrowid
    for r in body.reps:
        con.execute("INSERT INTO reps(session_item_id,rep_index,peak_angle,duration_ms,valid,flags_json) VALUES(?,?,?,?,?,?)",
                    (item_id, r.rep_index, r.peak_angle, r.duration_ms, 1 if r.valid else 0, json.dumps(r.flags)))
    con.commit()
    return {"item_id": item_id, "quality_score": score, "score_breakdown": breakdown, "rule_version": rule["version"] if rule else None}


@app.post("/api/v1/sessions/{sid}/finish")
def session_finish(sid: int, body: SessionFinish, user=Depends(require_role("patient")), con=Depends(get_con)):
    s = db.one(con.execute("SELECT * FROM sessions WHERE id=? AND patient_id=?", (sid, user["patient_id"])))
    if not s:
        raise HTTPException(404, "训练不存在")
    n = db.one(con.execute("SELECT COUNT(*) AS n FROM session_items WHERE session_id=?", (sid,)))["n"]
    status = "finished" if n > 0 else "aborted"
    con.execute("UPDATE sessions SET ended_at=?, status=?, pain_score=?, note=? WHERE id=?", (db.now(), status, body.pain_score, body.note, sid))
    con.commit()
    detail = session_detail(con, sid)
    alerts = generate_alerts(con, user["patient_id"], detail) if status == "finished" else []
    db.audit(con, user["id"], "session.finish", f"session:{sid}", {"status": status, "alerts": len(alerts)})
    return {"session": detail, "alerts_created": alerts}


@app.get("/api/v1/sessions/{sid}")
def session_get(sid: int, user=Depends(current_user), con=Depends(get_con)):
    s = db.one(con.execute("SELECT patient_id FROM sessions WHERE id=?", (sid,)))
    if not s:
        raise HTTPException(404, "训练不存在")
    patient_in_scope(con, user, s["patient_id"])
    return session_detail(con, sid)


@app.get("/api/v1/me/sessions")
def my_sessions(limit: int = 30, user=Depends(require_role("patient")), con=Depends(get_con)):
    return list_sessions(con, user["patient_id"], limit)


def list_sessions(con, pid: int, limit: int) -> list[dict]:
    out = db.rows(con.execute(
        "SELECT s.id, s.started_at, s.ended_at, s.status, s.pain_score, "
        "COUNT(si.id) AS sets, COALESCE(SUM(si.reps_valid),0) AS reps_valid, COALESCE(SUM(si.reps_done),0) AS reps_done, "
        "ROUND(AVG(si.quality_score),1) AS quality_avg, COALESCE(SUM(si.compensation_count),0) AS compensation "
        "FROM sessions s LEFT JOIN session_items si ON si.session_id=s.id WHERE s.patient_id=? "
        "GROUP BY s.id ORDER BY s.started_at DESC LIMIT ?", (pid, limit)))
    return out


@app.get("/api/v1/me/trend")
def my_trend(exercise: Optional[str] = None, metric: str = "peak_angle_max", user=Depends(require_role("patient")), con=Depends(get_con)):
    return trend(con, user["patient_id"], exercise, metric)


# ---------- 康复师 / 机构端 ----------
@app.get("/api/v1/patients")
def patients(user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    out = db.rows(con.execute(
        "SELECT p.*, u.display_name, u.username, t.display_name AS therapist_name FROM patients p "
        "JOIN users u ON u.id=p.user_id LEFT JOIN users t ON t.id=p.therapist_id WHERE p.institution_id=? ORDER BY p.id", (user["institution_id"],)))
    since = (date.today() - timedelta(days=6)).isoformat()
    for p in out:
        p["baseline"] = json.loads(p.pop("baseline_json") or "{}")
        last = db.one(con.execute("SELECT started_at, pain_score FROM sessions WHERE patient_id=? AND status='finished' ORDER BY started_at DESC LIMIT 1", (p["id"],)))
        p["last_session_at"] = last["started_at"] if last else None
        p["last_pain"] = last["pain_score"] if last else None
        plan = db.one(con.execute("SELECT id, days_per_week, title FROM plans WHERE patient_id=? AND status='active' ORDER BY id DESC LIMIT 1", (p["id"],)))
        p["active_plan"] = plan
        days = db.one(con.execute("SELECT COUNT(DISTINCT substr(started_at,1,10)) AS n FROM sessions WHERE patient_id=? AND status='finished' AND started_at>=?", (p["id"], since)))["n"]
        p["days_trained_7d"] = days
        p["completion_7d"] = round(min(1.0, days / plan["days_per_week"]) * 100) if plan and plan["days_per_week"] else None
        q = db.one(con.execute("SELECT ROUND(AVG(si.quality_score),1) AS q FROM session_items si JOIN sessions s ON s.id=si.session_id WHERE s.patient_id=? AND s.started_at>=?", (p["id"], since)))
        p["quality_7d"] = q["q"]
        inactive_check(con, p["id"])
        p["open_alerts"] = db.one(con.execute("SELECT COUNT(*) AS n FROM alerts WHERE patient_id=? AND acknowledged_at IS NULL", (p["id"],)))["n"]
    return out


@app.post("/api/v1/patients", status_code=201)
def patient_create(body: PatientIn, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    if db.one(con.execute("SELECT id FROM users WHERE username=?", (body.username,))):
        raise HTTPException(409, "用户名已存在")
    cur = con.execute("INSERT INTO users(institution_id,role,username,password_hash,display_name) VALUES(?,?,?,?,?)",
                      (user["institution_id"], "patient", body.username, db.hash_password(body.password), body.display_name))
    uid = cur.lastrowid
    cur = con.execute("INSERT INTO patients(user_id,institution_id,therapist_id,surgery_type,surgery_date,affected_side,phase,baseline_json,notes) VALUES(?,?,?,?,?,?,?,?,?)",
                      (uid, user["institution_id"], user["id"], body.surgery_type, body.surgery_date, body.affected_side, body.phase, json.dumps(body.baseline or {}, ensure_ascii=False), body.notes))
    con.commit()
    db.audit(con, user["id"], "patient.create", f"patient:{cur.lastrowid}")
    return {"patient_id": cur.lastrowid, "user_id": uid}


@app.get("/api/v1/patients/{pid}")
def patient_get(pid: int, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    p = patient_in_scope(con, user, pid)
    u = db.one(con.execute("SELECT display_name, username FROM users WHERE id=?", (p["user_id"],)))
    p.update(u)
    p["baseline"] = json.loads(p.pop("baseline_json") or "{}")
    plan = db.one(con.execute("SELECT id FROM plans WHERE patient_id=? AND status='active' ORDER BY id DESC LIMIT 1", (pid,)))
    p["active_plan"] = plan_with_items(con, plan["id"]) if plan else None
    p["sessions"] = list_sessions(con, pid, 20)
    p["alerts"] = db.rows(con.execute("SELECT * FROM alerts WHERE patient_id=? ORDER BY created_at DESC LIMIT 20", (pid,)))
    p["consent"] = db.one(con.execute("SELECT version, agreed_at, withdrawn_at FROM consents WHERE patient_id=? ORDER BY id DESC LIMIT 1", (pid,)))
    db.audit(con, user["id"], "patient.view", f"patient:{pid}")
    return p


@app.get("/api/v1/patients/{pid}/sessions")
def patient_sessions(pid: int, limit: int = 50, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    patient_in_scope(con, user, pid)
    return list_sessions(con, pid, limit)


@app.get("/api/v1/patients/{pid}/trend")
def patient_trend(pid: int, exercise: Optional[str] = None, metric: str = "peak_angle_max", user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    patient_in_scope(con, user, pid)
    return trend(con, pid, exercise, metric)


@app.get("/api/v1/patients/{pid}/plans")
def patient_plans(pid: int, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    patient_in_scope(con, user, pid)
    ids = db.rows(con.execute("SELECT id FROM plans WHERE patient_id=? ORDER BY id DESC", (pid,)))
    return [plan_with_items(con, r["id"]) for r in ids]


@app.post("/api/v1/patients/{pid}/plans", status_code=201)
def plan_create(pid: int, body: PlanIn, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    patient_in_scope(con, user, pid)
    con.execute("UPDATE plans SET status='ended' WHERE patient_id=? AND status='active'", (pid,))
    cur = con.execute("INSERT INTO plans(patient_id,therapist_id,title,start_date,end_date,days_per_week,goal_text) VALUES(?,?,?,?,?,?,?)",
                      (pid, user["id"], body.title, body.start_date, body.end_date, body.days_per_week, body.goal_text))
    plan_id = cur.lastrowid
    for i, it in enumerate(body.items):
        rule = active_rule(con, it.exercise_code)
        if not rule:
            raise HTTPException(400, f"动作 {it.exercise_code} 没有激活的规则版本")
        con.execute("INSERT INTO plan_items(plan_id,exercise_code,sets,reps,target_angle,min_valid_angle,rest_sec,rule_version_id,sort_order,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (plan_id, it.exercise_code, it.sets, it.reps, it.target_angle, it.min_valid_angle, it.rest_sec, rule["id"], i, it.notes))
    con.commit()
    db.audit(con, user["id"], "plan.create", f"plan:{plan_id}", {"patient_id": pid, "items": len(body.items)})
    return plan_with_items(con, plan_id)


@app.patch("/api/v1/plans/{plan_id}")
def plan_status(plan_id: int, status: str, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    if status not in ("active", "paused", "ended"):
        raise HTTPException(400, "status 非法")
    plan = db.one(con.execute("SELECT patient_id FROM plans WHERE id=?", (plan_id,)))
    if not plan:
        raise HTTPException(404, "计划不存在")
    patient_in_scope(con, user, plan["patient_id"])
    con.execute("UPDATE plans SET status=? WHERE id=?", (status, plan_id))
    con.commit()
    db.audit(con, user["id"], "plan.status", f"plan:{plan_id}", {"status": status})
    return {"ok": True}


@app.get("/api/v1/alerts")
def alerts(open: int = 1, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    for p in db.rows(con.execute("SELECT id FROM patients WHERE institution_id=?", (user["institution_id"],))):
        inactive_check(con, p["id"])
    sql = ("SELECT a.*, u.display_name AS patient_name FROM alerts a JOIN patients p ON p.id=a.patient_id JOIN users u ON u.id=p.user_id "
           "WHERE p.institution_id=? ")
    if open:
        sql += "AND a.acknowledged_at IS NULL "
    sql += "ORDER BY CASE a.severity WHEN 'high' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END, a.created_at DESC LIMIT 100"
    return db.rows(con.execute(sql, (user["institution_id"],)))


@app.post("/api/v1/alerts/{aid}/ack")
def alert_ack(aid: int, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    a = db.one(con.execute("SELECT patient_id FROM alerts WHERE id=?", (aid,)))
    if not a:
        raise HTTPException(404, "提醒不存在")
    patient_in_scope(con, user, a["patient_id"])
    con.execute("UPDATE alerts SET acknowledged_by=?, acknowledged_at=? WHERE id=?", (user["id"], db.now(), aid))
    con.commit()
    db.audit(con, user["id"], "alert.ack", f"alert:{aid}")
    return {"ok": True}


@app.get("/api/v1/patients/{pid}/export.csv")
def export_csv(pid: int, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    patient_in_scope(con, user, pid)
    rows = db.rows(con.execute(
        "SELECT s.id AS session_id, s.started_at, s.pain_score, si.exercise_code, si.set_index, si.reps_target, si.reps_done, si.reps_valid, "
        "si.peak_angle_max, si.peak_angle_mean, si.duration_ms, si.quality_score, si.compensation_count, si.capture_quality, si.low_confidence, s.rule_versions_json "
        "FROM session_items si JOIN sessions s ON s.id=si.session_id WHERE s.patient_id=? ORDER BY s.started_at, si.id", (pid,)))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["session_id", "started_at", "pain_score", "exercise", "set", "reps_target", "reps_done", "reps_valid", "peak_angle_max", "peak_angle_mean", "duration_ms", "quality_score", "compensation_count", "capture_quality", "low_confidence", "rule_versions"])
    for r in rows:
        w.writerow([r[k] for k in ("session_id", "started_at", "pain_score", "exercise_code", "set_index", "reps_target", "reps_done", "reps_valid", "peak_angle_max", "peak_angle_mean", "duration_ms", "quality_score", "compensation_count", "capture_quality", "low_confidence", "rule_versions_json")])
    db.audit(con, user["id"], "export", f"patient:{pid}", {"rows": len(rows)})
    data = "﻿" + buf.getvalue()
    return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=patient_{pid}_sessions.csv"})


@app.get("/api/v1/stats")
def stats(user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    inst = user["institution_id"]
    since = (date.today() - timedelta(days=6)).isoformat()
    return {
        "patients": db.one(con.execute("SELECT COUNT(*) AS n FROM patients WHERE institution_id=?", (inst,)))["n"],
        "sessions_7d": db.one(con.execute("SELECT COUNT(*) AS n FROM sessions s JOIN patients p ON p.id=s.patient_id WHERE p.institution_id=? AND s.status='finished' AND s.started_at>=?", (inst, since)))["n"],
        "open_alerts": db.one(con.execute("SELECT COUNT(*) AS n FROM alerts a JOIN patients p ON p.id=a.patient_id WHERE p.institution_id=? AND a.acknowledged_at IS NULL", (inst,)))["n"],
        "quality_7d": db.one(con.execute("SELECT ROUND(AVG(si.quality_score),1) AS q FROM session_items si JOIN sessions s ON s.id=si.session_id JOIN patients p ON p.id=s.patient_id WHERE p.institution_id=? AND s.started_at>=?", (inst, since)))["q"],
    }


# ---------- 规则版本 ----------
@app.get("/api/v1/rules")
def rules(exercise: Optional[str] = None, user=Depends(current_user), con=Depends(get_con)):
    sql = "SELECT * FROM rule_versions "
    args = ()
    if exercise:
        sql += "WHERE exercise_code=? "
        args = (exercise,)
    sql += "ORDER BY exercise_code, id DESC"
    out = db.rows(con.execute(sql, args))
    for r in out:
        r["params"] = json.loads(r.pop("params_json"))
    return out


@app.post("/api/v1/rules", status_code=201)
def rule_create(body: RuleIn, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    if not db.one(con.execute("SELECT code FROM exercises WHERE code=?", (body.exercise_code,))):
        raise HTTPException(400, "未知动作")
    if db.one(con.execute("SELECT id FROM rule_versions WHERE exercise_code=? AND version=?", (body.exercise_code, body.version))):
        raise HTTPException(409, "该版本号已存在")
    weights = (body.params or {}).get("score_weights")
    if weights is not None:
        bad = set(weights) - set(DEFAULT_WEIGHTS)
        if bad:
            raise HTTPException(400, f"score_weights 有非法键名：{sorted(bad)}，只能是 {sorted(DEFAULT_WEIGHTS)}")
    if body.activate:
        con.execute("UPDATE rule_versions SET is_active=0 WHERE exercise_code=?", (body.exercise_code,))
    cur = con.execute("INSERT INTO rule_versions(exercise_code,version,params_json,rationale,author,reviewer,is_active) VALUES(?,?,?,?,?,?,?)",
                      (body.exercise_code, body.version, json.dumps(body.params, ensure_ascii=False), body.rationale, user["display_name"], body.reviewer, 1 if body.activate else 0))
    con.commit()
    db.audit(con, user["id"], "rule.create", f"rule:{cur.lastrowid}", {"exercise": body.exercise_code, "version": body.version, "activate": body.activate})
    return {"id": cur.lastrowid}


@app.post("/api/v1/rules/{rid}/activate")
def rule_activate(rid: int, user=Depends(require_role("therapist", "admin")), con=Depends(get_con)):
    r = db.one(con.execute("SELECT * FROM rule_versions WHERE id=?", (rid,)))
    if not r:
        raise HTTPException(404, "规则不存在")
    if not r["reviewer"]:
        raise HTTPException(409, "未经复核（reviewer 为空）的规则不能激活，双人审核是硬要求")
    con.execute("UPDATE rule_versions SET is_active=0 WHERE exercise_code=?", (r["exercise_code"],))
    con.execute("UPDATE rule_versions SET is_active=1 WHERE id=?", (rid,))
    con.commit()
    db.audit(con, user["id"], "rule.activate", f"rule:{rid}", {"exercise": r["exercise_code"], "version": r["version"]})
    return {"ok": True}


@app.get("/api/v1/audit")
def audit_list(limit: int = 100, user=Depends(require_role("admin")), con=Depends(get_con)):
    return db.rows(con.execute("SELECT a.*, u.display_name FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT ?", (limit,)))


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


# ---------- 静态前端（前端负责人的地盘，从零做） ----------
# frontend/ 目录里如果还没有可运行的页面（只有 AGENTS.md / README.md），
# 就不挂载静态目录，根路径改为返回一段指向 /docs 的提示 JSON，保证服务照常启动。
_frontend_has_pages = FRONTEND.exists() and any(FRONTEND.glob("*.html"))
if _frontend_has_pages:
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "service": "康迹 RehabTrack API",
            "version": APP_VERSION,
            "docs": "/docs",
            "note": "frontend/ 目录暂无可运行页面，接口详情见 /docs",
        }


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
    # 服务器上用 REHAB_BIND=127.0.0.1 锁成只能经 Cloudflare 隧道进来；
    # 本机开发默认 0.0.0.0，方便同一 Wi-Fi 下用手机测。
    host = os.environ.get("REHAB_BIND", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="warning")
