"""接口冒烟测试：对着一个跑着的服务打一遍完整闭环。

用法：先 ./start.sh --reset 起一个干净的演示库，再 python3 tests/test_api.py [base_url]
默认 http://127.0.0.1:8801。每一步失败会直接抛出，方便联调时定位。
每次跑之前必须重置演示库（./start.sh --reset）：本测试会新建一条训练计划、新建一个规则版本，
连续跑两遍会因为撞到已存在的规则版本号而失败。
"""
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8801"
c = httpx.Client(base_url=BASE, timeout=10)


def ok(r, code=200):
    assert r.status_code == code, f"{r.request.method} {r.request.url} -> {r.status_code} {r.text[:300]}"
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text


def login_demo(username,password):
    result=c.post('/api/v1/auth/login',json={'username':username,'password':password})
    if result.status_code==403 and result.json().get('code')=='PASSWORD_RESET_REQUIRED':
        new_password=password+'2026'
        ok(c.post('/api/v1/auth/change-password',json={'username':username,'old_password':password,'new_password':new_password}))
        result=c.post('/api/v1/auth/login',json={'username':username,'password':new_password})
    return ok(result)

print("健康检查", ok(c.get("/healthz")))

# ---- 患者端闭环 ----
tok = login_demo("p.zhang", "zhang123")["token"]
P = {"Authorization": f"Bearer {tok}"}
today = ok(c.get("/api/v1/me/plan/today", headers=P))
assert today["plan"], "患者应有激活计划"
item = next(i for i in today["items"] if i["exercise_code"] == "KNEE_FLEX")
print("今日计划", today["plan"]["title"], "→", [i["exercise_code"] for i in today["items"]])

sid = ok(c.post("/api/v1/sessions", json={"plan_id": today["plan"]["id"], "device": "test", "camera_side": "side"}, headers=P))["session_id"]
payload = {
    "plan_item_id": item["id"], "exercise_code": item["exercise_code"], "set_index": 1,
    "reps_target": item["reps"], "reps_done": 10, "reps_valid": 9,
    "peak_angle_max": 97.5, "peak_angle_mean": 93.2, "duration_ms": 41000,
    "compensation_count": 1, "capture_quality": 0.93, "low_confidence": False,
    "angle_trace": [168, 150, 120, 98, 110, 140, 165] * 3,
    "reps": [{"rep_index": i + 1, "peak_angle": 95 + (i % 3), "duration_ms": 3800, "valid": i != 4, "flags": ["amplitude_low"] if i == 4 else []} for i in range(10)],
}
res = ok(c.post(f"/api/v1/sessions/{sid}/items", json=payload, headers=P))
assert 0 <= res["quality_score"] <= 100 and res["score_breakdown"], res
print("上传一组 → 服务端缺省评分", res["quality_score"], res["score_breakdown"], "规则", res["rule_version"])

# 越权：患者不能看别人的训练
assert c.get("/api/v1/patients", headers=P).status_code == 403

fin = ok(c.post(f"/api/v1/sessions/{sid}/finish", json={"pain_score": 7, "note": "膝盖有点酸"}, headers=P))
assert fin["session"]["status"] == "finished"
print("结束训练 → 自动提醒", [a["type"] for a in fin["alerts_created"]])
assert any(a["type"] == "pain_high" for a in fin["alerts_created"]), "疼痛 7 分应触发 pain_high"

detail = ok(c.get(f"/api/v1/sessions/{sid}", headers=P))
assert len(detail["items"][0]["reps"]) == 10
tr = ok(c.get("/api/v1/me/trend", params={"exercise": "KNEE_FLEX"}, headers=P))
print("趋势点数", len(tr), "最新", tr[-1])

# ---- 康复师端 ----
tok = login_demo("dr.lin", "lin123")["token"]
T = {"Authorization": f"Bearer {tok}"}
pts = ok(c.get("/api/v1/patients", headers=T))
assert len(pts) >= 2
zhang = next(p for p in pts if p["username"] == "p.zhang")
print("患者列表", [(p["display_name"], p["completion_7d"], p["open_alerts"]) for p in pts])

al = ok(c.get("/api/v1/alerts", headers=T))
assert al and al[0]["severity"] == "high", "高优先提醒应排最前"
ok(c.post(f"/api/v1/alerts/{al[0]['id']}/ack", headers=T))

prof = ok(c.get(f"/api/v1/patients/{zhang['id']}", headers=T))
assert prof["active_plan"] and prof["sessions"]
csv_text = ok(c.get(f"/api/v1/patients/{zhang['id']}/export.csv", headers=T))
assert csv_text.count("\n") >= 5
print("CSV 导出行数", csv_text.count("\n"))

# 计划配置：新计划自动结束旧计划
plan = ok(c.post(f"/api/v1/patients/{zhang['id']}/plans", json={
    "title": "测试计划", "start_date": "2026-09-09", "days_per_week": 5, "goal_text": "膝屈曲 105°",
    "items": [{"exercise_code": "KNEE_FLEX", "sets": 3, "reps": 12, "target_angle": 105, "min_valid_angle": 120}]}, headers=T), 201)
assert plan["items"][0]["rule"]["version"]
plans = ok(c.get(f"/api/v1/patients/{zhang['id']}/plans", headers=T))
assert sum(1 for p in plans if p["status"] == "active") == 1

# 规则版本：没 reviewer 不许激活
test_version = f"v0.2-test-{int(time.time())}"
rid = ok(c.post("/api/v1/rules", json={"exercise_code": "SQUAT", "version": test_version, "params": {"target_angle": 85}, "rationale": "测试"}, headers=T), 201)["id"]
assert c.post(f"/api/v1/rules/{rid}/activate", headers=T).status_code == 409
print("规则双人审核闸门 ✓")

# 管理员审计
tok = login_demo("admin", "admin123")["token"]
aud = ok(c.get("/api/v1/audit", params={"limit": 5}, headers={"Authorization": f"Bearer {tok}"}))
print("审计最近", [a["action"] for a in aud])
print("\n全部通过 ✓")
