"""数据库层：SQLite 起步，纯标准库。换 PostgreSQL 时只改这里。"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("REHAB_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "rehabtrack.sqlite3"
SCHEMA = ROOT / "database" / "schema.sql"
SEED = ROOT / "database" / "seed" / "seed.json"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- 密码与令牌 ----------
def hash_password(pw: str, iterations: int = 200_000) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, iters, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


def issue_token(con, user_id: int, hours: int = 72) -> str:
    tok = secrets.token_urlsafe(32)
    exp = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    con.execute("INSERT INTO tokens(token,user_id,expires_at) VALUES(?,?,?)", (tok, user_id, exp))
    con.commit()
    return tok


def user_by_token(con, token: str):
    row = con.execute(
        "SELECT u.* FROM tokens t JOIN users u ON u.id=t.user_id "
        "WHERE t.token=? AND t.expires_at>? AND u.is_active=1",
        (token, now()),
    ).fetchone()
    return dict(row) if row else None


# ---------- 初始化与演示数据 ----------
def init_db(seed: bool = True) -> None:
    fresh = not DB_PATH.exists()
    con = connect()
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()
    if fresh and seed and SEED.exists():
        load_seed(con, json.loads(SEED.read_text(encoding="utf-8")))
    con.close()


def load_seed(con, s: dict) -> None:
    """把 seed/seed.json 灌进空库。演示人物全部虚构。"""
    inst_ids = {}
    for inst in s["institutions"]:
        cur = con.execute("INSERT INTO institutions(name) VALUES(?)", (inst["name"],))
        inst_ids[inst["key"]] = cur.lastrowid

    user_ids = {}
    for u in s["users"]:
        cur = con.execute(
            "INSERT INTO users(institution_id,role,username,password_hash,display_name) VALUES(?,?,?,?,?)",
            (inst_ids[u["institution"]], u["role"], u["username"], hash_password(u["password"]), u["display_name"]),
        )
        user_ids[u["username"]] = cur.lastrowid

    for e in s["exercises"]:
        con.execute(
            "INSERT OR REPLACE INTO exercises(code,name,joint,metric,direction,camera_side,description) VALUES(?,?,?,?,?,?,?)",
            (e["code"], e["name"], e["joint"], e["metric"], e["direction"], e["camera_side"], e["description"]),
        )

    rule_ids = {}
    for r in s["rule_versions"]:
        cur = con.execute(
            "INSERT INTO rule_versions(exercise_code,version,params_json,rationale,author,reviewer,is_active) VALUES(?,?,?,?,?,?,?)",
            (r["exercise_code"], r["version"], json.dumps(r["params"], ensure_ascii=False), r["rationale"], r["author"], r["reviewer"], 1 if r.get("active") else 0),
        )
        rule_ids[(r["exercise_code"], r["version"])] = cur.lastrowid

    patient_ids = {}
    for p in s["patients"]:
        cur = con.execute(
            "INSERT INTO patients(user_id,institution_id,therapist_id,surgery_type,surgery_date,affected_side,phase,baseline_json,notes) VALUES(?,?,?,?,?,?,?,?,?)",
            (user_ids[p["username"]], inst_ids[p["institution"]], user_ids[p["therapist"]], p["surgery_type"], p["surgery_date"], p["affected_side"], p["phase"], json.dumps(p["baseline"], ensure_ascii=False), p.get("notes")),
        )
        patient_ids[p["username"]] = cur.lastrowid
        con.execute(
            "INSERT INTO consents(patient_id,version,text_sha256) VALUES(?,?,?)",
            (cur.lastrowid, "consent-v0.1", hashlib.sha256(b"consent-v0.1").hexdigest()),
        )

    for pl in s["plans"]:
        cur = con.execute(
            "INSERT INTO plans(patient_id,therapist_id,title,start_date,end_date,days_per_week,goal_text) VALUES(?,?,?,?,?,?,?)",
            (patient_ids[pl["patient"]], user_ids[pl["therapist"]], pl["title"], pl["start_date"], pl.get("end_date"), pl.get("days_per_week", 5), pl.get("goal_text")),
        )
        plan_id = cur.lastrowid
        for i, it in enumerate(pl["items"]):
            con.execute(
                "INSERT INTO plan_items(plan_id,exercise_code,sets,reps,target_angle,min_valid_angle,rest_sec,rule_version_id,sort_order,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (plan_id, it["exercise_code"], it["sets"], it["reps"], it.get("target_angle"), it.get("min_valid_angle"), it.get("rest_sec", 60), rule_ids.get((it["exercise_code"], it.get("rule_version", "v0.1"))), i, it.get("notes")),
            )

    # 历史训练：用 seed 里的每日摘要生成 sessions / session_items，方便趋势图有东西看
    for h in s.get("history", []):
        pid = patient_ids[h["patient"]]
        plan_row = con.execute("SELECT id FROM plans WHERE patient_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        started = f"{h['date']} {h.get('time','19:30')}:00"
        cur = con.execute(
            "INSERT INTO sessions(patient_id,plan_id,started_at,ended_at,status,device,camera_side,rule_versions_json,pain_score) VALUES(?,?,?,?,?,?,?,?,?)",
            (pid, plan_row["id"] if plan_row else None, started, started, "finished", "seed", "side", json.dumps({"SQUAT": "v0.1", "KNEE_FLEX": "v0.1", "SLR": "v0.1", "STS": "v0.1"}), h.get("pain")),
        )
        sid = cur.lastrowid
        for it in h["items"]:
            con.execute(
                "INSERT INTO session_items(session_id,exercise_code,set_index,reps_target,reps_done,reps_valid,peak_angle_max,peak_angle_mean,duration_ms,quality_score,score_breakdown_json,compensation_count,capture_quality,low_confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, it["exercise_code"], it.get("set_index", 1), it.get("reps_target", 10), it["reps_done"], it["reps_valid"], it["peak_angle_max"], it.get("peak_angle_mean", it["peak_angle_max"] - 4), it.get("duration_ms", 45000), it["quality_score"], json.dumps(it.get("breakdown", {})), it.get("compensation_count", 0), it.get("capture_quality", 0.95), 0),
            )
    con.commit()


# ---------- 小工具 ----------
def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def one(cur):
    r = cur.fetchone()
    return dict(r) if r else None


def audit(con, user_id, action: str, target: str | None = None, detail: dict | None = None, ip: str | None = None) -> None:
    con.execute(
        "INSERT INTO audit_logs(user_id,action,target,detail_json,ip) VALUES(?,?,?,?,?)",
        (user_id, action, target, json.dumps(detail, ensure_ascii=False) if detail else None, ip),
    )
    con.commit()
