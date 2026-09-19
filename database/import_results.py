"""离线导入姿态识别原型（algorithm/rehab-pose-demo）跑出来的 results/ 目录到数据库。

背景：原型现在没有 API/WebSocket，本脚本是「先做离线导入，出可演示效果」这条路径（方案 a），
详见 知识库/10_卡片/项目/康迹-原型输出落库映射-20260918.md。原型和 docs/03-接口契约.md 假设的
不是同一套状态机，字段名字大量对不上，本脚本里的换算规则就是把两边接起来的地方，换算依据都在
函数注释里，和映射报告第 2/3 节一一对应。

用法：
    python3 database/import_results.py <results目录> --patient-id 1 \\
        [--plan-id 1] [--plan-item-id 1] [--db data/rehabtrack.sqlite3] [--dry-run] \\
        [--score-mode none|contract-d]

<results目录> 是原型 rehab_pose.run 每次运行产出的那个目录（如 results/20260918_231045_123456/），
必须包含 summary.json 和 frames.jsonl；assessment.json 可选，缺失时只是少落一列 checks_json。

只用标准库：json / sqlite3 / argparse / pathlib / statistics / datetime，不新增依赖。

幂等：用 summary.json 的 created_utc（缺失时退化成目录名）作为 sessions.import_source_key，
重复导入同一个目录会直接跳过，不会插入第二条 session。

动作代号映射、reps_valid 判定口径已由队友「常」拍板，规则写在下面 CROSSWALK / TOO_FAST_CODES /
COMPENSATION_FLAG 几个常量和各函数的注释里，不要在这个脚本里再擅自改动动作代号或角度口径的假设
——如果发现原型输出和这里的假设对不上，去 docs/decisions/ 记一条，别悄悄改这个脚本让它"能跑就行"。

评分口径**还没定**（20260919 常明确提出：提示有冷却时间，识别不到不等于动作正确，条数不能直接
拿来扣分）：默认 --score-mode none，quality_score 留 NULL，score_breakdown_json 只存原始输入并
标 provisional；--score-mode contract-d 才按接口契约 D 节公式现算，仅供联调对比，不代表这个公式
已经拍板。原型的逐条提示事件（feedback_events）原样落进新表 session_events，供以后回放或做别的
判定逻辑用，不因为这次不拿它算分就丢掉。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "database" / "schema.sql"
DEFAULT_DB = ROOT / "data" / "rehabtrack.sqlite3"

# ---------------------------------------------------------------------------
# 动作代号映射（常拍板，20260918-19）：
#   原型 1 SEATED_KNEE_EXTENSION -> 新增 exercises.code SEATED_KNEE_EXTENSION
#   原型 2 SUPINE_STRAIGHT_LEG_RAISE -> SLR
#   原型 6 SUPPORTED_MINI_SQUAT -> SQUAT
#   原型 8 SIT_TO_STAND -> STS
#   KNEE_FLEX 保留，不用于坐姿伸膝，本脚本不会产出 KNEE_FLEX 的记录。
# ---------------------------------------------------------------------------
CROSSWALK = {
    "SEATED_KNEE_EXTENSION": "SEATED_KNEE_EXTENSION",
    "SUPINE_STRAIGHT_LEG_RAISE": "SLR",
    "SUPPORTED_MINI_SQUAT": "SQUAT",
    "SIT_TO_STAND": "STS",
}
# 这两个动作的主指标是"相对初始方向的变化量"（已扣掉 90 度人工偏移，rehab_pose/exercises.py），
# 不是解剖角，peak_angle_max/peak_angle 按原样存这个相对量，不折算成绝对角度。
RELATIVE_ANGLE_EXERCISES = {"SLR", "SQUAT"}

# 原型 exercise_rules.py / measures.py 里实际会触发的提示代号 -> 接口契约 A 节的 flags 枚举。
# 契约枚举只有 amplitude_low / too_fast / trunk_lean / knee_bent / hip_shift / arm_assist 六个，
# 原型代号更细，两边对不上的（SLR_TOO_HIGH 幅度过大、SQUAT_TOO_DEEP 蹲太深）契约里没有对应
# 语义的 flag，不塞进 flags_json（避免乱造枚举值），只计入下面 UNMAPPED_EVENT_CODES 统计，
# 写进 PR「待确认」，不在这里自作主张扩展枚举。
TOO_FAST_CODES = {"KNEE_TOO_FAST", "SLR_TOO_FAST", "SQUAT_TOO_FAST", "STS_TOO_FAST"}
COMPENSATION_FLAG = {
    "TRUNK_FORWARD": "trunk_lean",
    "TRUNK_BACKWARD": "trunk_lean",
    "THIGH_MOVEMENT": "hip_shift",       # 契约里 hip_shift 原本写给 KNEE_FLEX 用，这里借用其"髋部/参考肢段明显移动"的含义
    "SLR_KNEE_BENT": "knee_bent",
    "SLR_TRUNK_MOVED": "trunk_lean",
    "SQUAT_FORWARD": "trunk_lean",
    "STS_TOP_NOT_UPRIGHT": "trunk_lean",
}
UNMAPPED_EVENT_CODES = {"SLR_TOO_HIGH", "SQUAT_TOO_DEEP"}

# summary.status（原型）-> sessions.status（schema）。failed 不落库，见 SKIP_STATUS。
STATUS_MAP = {
    "plan_completed": "finished",
    "completed": "finished",
    "stopped_by_user": "aborted",
    "time_limit": "aborted",
}
SKIP_STATUS = {"failed"}

# 契约 D 节初始权重建议（docs/03-接口契约.md），原型不产出权重，这里复用同一套默认值。
DEFAULT_SCORE_WEIGHTS = {
    "completion": 0.30, "amplitude": 0.25, "posture": 0.25, "tempo": 0.10, "stability": 0.10,
}


class ImportError_(Exception):
    """导入过程中遇到无法继续的问题（不是 Python 内置 ImportError，避免误导）。"""


# ---------------------------------------------------------------------------
# 读取原型产物
# ---------------------------------------------------------------------------

def load_run(directory: Path):
    directory = Path(directory)
    summary_path = directory / "summary.json"
    frames_path = directory / "frames.jsonl"
    if not summary_path.exists():
        raise ImportError_(f"缺 summary.json：{summary_path}")
    if not frames_path.exists():
        raise ImportError_(f"缺 frames.jsonl：{frames_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    rows = []
    with frames_path.open(encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    assessment = None
    assessment_path = directory / "assessment.json"
    if assessment_path.exists():
        try:
            assessment = json.loads(assessment_path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            assessment = None  # 可选文件，读不了就当没有，不阻塞导入
    return summary, rows, assessment


def resolve_exercise(summary: dict, rows: list) -> tuple[str, str]:
    """返回 (原型英文枚举名, schema exercise_code)。summary 缺 exercise 字段时退化到第一帧。"""
    name = summary.get("exercise")
    if not name and rows:
        name = rows[0].get("exercise")
    if not name:
        raise ImportError_("summary.json 和 frames.jsonl 里都没有 exercise 字段，无法判断动作代号")
    code = CROSSWALK.get(name)
    if not code:
        raise ImportError_(f"动作 {name!r} 不在已拍板的代号映射表里（{sorted(CROSSWALK)}），先别导，去问常/陈")
    return name, code


# ---------------------------------------------------------------------------
# 时间戳 / 幂等键
# ---------------------------------------------------------------------------

def _parse_iso(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def resolve_timing(summary: dict, rows: list, directory: Path):
    """返回 (started_at, ended_at, started_at_source, import_source_key)，均为字符串（本地时区文本）。

    timing_source=video_presentation_timestamps（回放视频文件）时，frames 的 timestamp_s 是视频内部
    呈现时间戳，和真实墙钟时间无关，started_at 只能退化成"结果文件写入时刻"，必须打标记
    （已拍板，见任务说明）。timing_source=monotonic_clock（实时摄像头）时，用 created_utc 减去
    最后一帧 timestamp_s 近似算出开始时刻。两种情况 ended_at 都用 created_utc。
    """
    created_utc = summary.get("created_utc")
    created_dt = _parse_iso(created_utc) if created_utc else None
    timing_source = summary.get("timing_source")

    if created_dt is None:
        # 老格式样例没有 created_utc，退化用结果文件的 mtime，并在来源标记里说明白。
        mtime = None
        for name in ("summary.json", "frames.jsonl"):
            p = directory / name
            if p.exists():
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                break
        created_dt = mtime or datetime.now(timezone.utc)
        import_key = directory.name
        source_suffix = "_fallback_file_mtime"
    else:
        import_key = created_utc
        source_suffix = ""

    ended_at = created_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

    if timing_source == "video_presentation_timestamps":
        started_at = ended_at
        started_at_source = "file_write_time_video_replay" + source_suffix
    elif timing_source == "monotonic_clock" and rows:
        last_t = max((r.get("timestamp_s") for r in rows if r.get("timestamp_s") is not None), default=0.0)
        started_dt = created_dt - timedelta(seconds=last_t)
        started_at = started_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        started_at_source = "observed_wallclock_estimate" + source_suffix
    else:
        # timing_source 缺失（老格式样例）：无法判断，标记清楚，退化成写入时刻。
        started_at = ended_at
        started_at_source = "unknown_timing_source" + source_suffix

    return started_at, ended_at, started_at_source, import_key


# ---------------------------------------------------------------------------
# 按组（training_set）切分 repetitions
# ---------------------------------------------------------------------------

def group_repetitions(summary: dict):
    """按 training_set 分组；没设 --sets 时原型不产出 training_set/rep_in_set 字段，整次运行算一组。"""
    reps = summary.get("repetitions", [])
    groups: dict[int, list[dict]] = {}
    for rep in reps:
        set_index = rep.get("training_set", 1)
        groups.setdefault(set_index, []).append(rep)
    for set_index in groups:
        groups[set_index].sort(key=lambda r: r.get("rep_in_set", r.get("index", 0)))
    return dict(sorted(groups.items()))


def primary_peak(exercise_code: str, rep: dict):
    """一次动作的主指标峰值：动作 1/8 是真实解剖角（max_included_deg），
    动作 SLR/SQUAT 是相对初始方向的变化量（max_motion_delta_deg，已扣 90 度偏移，按原样存）。"""
    if exercise_code in RELATIVE_ANGLE_EXERCISES:
        return rep.get("max_motion_delta_deg")
    return rep.get("max_included_deg")


def events_in_window(feedback_events: list, start_s: float, end_s: float):
    return [e for e in feedback_events if start_s <= e.get("timestamp_s", -1) <= end_s]


def rep_flags(events: list) -> list[str]:
    flags = []
    for e in events:
        code = e.get("code")
        if code in TOO_FAST_CODES:
            flag = "too_fast"
        else:
            flag = COMPENSATION_FLAG.get(code)
        if flag and flag not in flags:
            flags.append(flag)
    return flags


def rep_is_valid(rep: dict, events: list) -> bool:
    """reps_valid 只按幅度达标 + 没有 too_fast 类事件判（已拍板，"无提醒"不等于"合格"）。"""
    amplitude_met = bool((rep.get("target_comparison") or {}).get("amplitude_met"))
    too_fast_hit = any(e.get("code") in TOO_FAST_CODES for e in events)
    return amplitude_met and not too_fast_hit


# ---------------------------------------------------------------------------
# 组级聚合：capture_quality / 二维测量角度 / 标定快照
# ---------------------------------------------------------------------------

def frames_in_window(rows: list, start_s: float, end_s: float):
    return [r for r in rows if start_s <= r.get("timestamp_s", -1) <= end_s]


def compute_capture_quality(rows: list, reps: list):
    """可见帧 / 总帧，取各 rep 时间窗并集内的帧（不含组间休息时段）。"""
    frames = []
    for rep in reps:
        frames.extend(frames_in_window(rows, rep["start_s"], rep["end_s"]))
    if not frames:
        return None
    observed = sum(1 for r in frames if r.get("visible") and not r.get("bridge_pending"))
    return observed / len(frames)


def compute_measurement_angle_json(rows: list, reps: list):
    """二维测量角度参考值：组内可信观测帧的 knee_included_deg 范围，不与 peak_angle_max 混用。"""
    values = []
    frame_count = 0
    for rep in reps:
        for r in frames_in_window(rows, rep["start_s"], rep["end_s"]):
            if not r.get("visible") or r.get("bridge_pending"):
                continue
            mm = r.get("measurement_metrics") or {}
            v = mm.get("knee_included_deg")
            if v is None:
                continue
            frame_count += 1
            values.append(v)
    if not values:
        return None
    return json.dumps({
        "observed_knee_min_deg": min(values),
        "observed_knee_max_deg": max(values),
        "observed_frame_count": frame_count,
    }, ensure_ascii=False)


def compute_calibration_json(summary: dict, reps: list):
    """标定信息保留：取最后一个 rep 开始前最近一次标定基线，原样保留。"""
    calibrations = summary.get("calibrations") or []
    if not calibrations or not reps:
        return None
    last_start = reps[-1]["start_s"]
    candidates = [c for c in calibrations if c.get("captured_at_s") is not None and c["captured_at_s"] <= last_start]
    chosen = candidates[-1] if candidates else calibrations[0]
    return json.dumps(chosen, ensure_ascii=False)


def compute_checks_json(assessment: dict | None, reps: list):
    if not assessment:
        return None
    by_index = {}
    for attempt in assessment.get("attempts", []):
        idx = attempt.get("completed_rep_index")
        if idx is not None:
            by_index[idx] = attempt.get("checks")
    out = {}
    for rep in reps:
        idx = rep.get("index")
        if idx in by_index and by_index[idx] is not None:
            out[str(idx)] = by_index[idx]
    return json.dumps(out, ensure_ascii=False) if out else None


# ---------------------------------------------------------------------------
# 评分（契约 D 节公式，原型不产出，这里现算）
# ---------------------------------------------------------------------------

def rest_target_angles(exercise_code: str, effective_parameters: dict):
    """幅度公式要用的 rest_angle / target_angle。

    动作 1/8：直接用原型的 rest_max_deg / target_deg（真实解剖角）。
    动作 SLR/SQUAT：主指标是相对量，"静息"定义为相对变化 0，目标是 target_deg-90
    （exercises.py 把这两个动作的 target_deg 定义成 90+相对目标量，这里反过来减掉，
    只用来算幅度得分，不影响落库的 peak_angle_max 原始值）。
    这是本脚本自己的推导，不是常/陈明确给的公式，已在 PR「待确认」里列出，需要确认。
    """
    if exercise_code in RELATIVE_ANGLE_EXERCISES:
        target = effective_parameters.get("target_deg")
        return 0.0, (target - 90 if target is not None else None)
    return effective_parameters.get("rest_max_deg"), effective_parameters.get("target_deg")


def clamp01(x):
    if x is None:
        return None
    return max(0.0, min(1.0, x))


def compute_provisional_breakdown(*, reps_valid, reps_target, reps_done, peak_angle_max, rest_angle,
                                   target_angle, compensation_count, too_fast_count, capture_quality):
    """默认（--score-mode 不传，即 'none'）的 score_breakdown_json：只存各维度的原始输入，
    不折算成 0-100 分，quality_score 这一列对应留 NULL。

    这是队友（常）20260919 的硬要求：提示事件有冷却时间（同一秒钟前倾了 5 次也只算一次提示），
    识别不到（低置信度、遮挡）也不等于动作做对了，"保持不足"/"无法判断"这类状态到底该不该扣分、
    扣多少，还没和 陈（临床）共同定下来，数据库层不该在没有这个公式之前，自己拿事件条数当扣分
    依据编一个分数出来给人看。真要对比契约 D 节公式，用 --score-mode contract-d 显式打开。
    """
    if peak_angle_max is not None and rest_angle is not None and target_angle is not None and target_angle != rest_angle:
        amplitude_ratio = round(abs(peak_angle_max - rest_angle) / abs(target_angle - rest_angle), 4)
    else:
        amplitude_ratio = None
    return {
        "reps_valid": reps_valid, "reps_target": reps_target, "reps_done": reps_done,
        "amplitude_ratio": amplitude_ratio,
        "compensation_event_count": compensation_count,
        "too_fast_event_count": too_fast_count,
        "capture_quality": capture_quality,
        "provisional": True,
        "reason": "评分口径待常/陈确认：提示有冷却时间、识别不到不等于动作正确，"
                  "保持不足/无法判断如何处理仍需共同确定，见 docs/decisions/0002",
    }


def compute_contract_d_score(*, reps_valid, reps_target, reps_done, peak_angle_max, rest_angle, target_angle,
                              compensation_count, too_fast_count, capture_quality, score_weights):
    """只在 --score-mode contract-d 显式打开时才调用，按接口契约 D 节公式现算，供联调对比用，
    不是默认行为（见 compute_provisional_breakdown 的说明）。"""
    completion = clamp01(reps_valid / reps_target) if reps_target else 0.0
    if peak_angle_max is not None and rest_angle is not None and target_angle is not None and target_angle != rest_angle:
        amplitude = clamp01(abs(peak_angle_max - rest_angle) / abs(target_angle - rest_angle))
    else:
        amplitude = 0.0
    posture = clamp01(1 - compensation_count / reps_done) if reps_done else 0.0
    tempo = clamp01(1 - too_fast_count / reps_done) if reps_done else 0.0
    stability = clamp01(capture_quality) if capture_quality is not None else 0.0
    dims = {"completion": completion, "amplitude": amplitude, "posture": posture, "tempo": tempo, "stability": stability}
    breakdown = {k: round(100 * score_weights.get(k, DEFAULT_SCORE_WEIGHTS[k]) * v, 2) for k, v in dims.items()}
    breakdown["score_mode"] = "contract-d"
    quality_score = round(sum(v for k, v in breakdown.items() if k != "score_mode"), 2)
    return quality_score, breakdown


# ---------------------------------------------------------------------------
# 逐条提示事件（session_events）：原样落库，不用于评分
# ---------------------------------------------------------------------------

def _event_distance(t, extent):
    start, end = extent
    if t is None:
        return 0.0
    if start <= t <= end:
        return 0.0
    return start - t if t < start else t - end


def _stored_rep_index(rep: dict):
    """reps.rep_index 落库时存的是组内序号 rep_in_set（原型没分组时退化成全局 index）。
    session_events.rep_index 必须跟这一列对齐，不能直接存原型的全局 index。"""
    return rep.get("rep_in_set", rep.get("index"))


def assign_events_to_groups(feedback_events: list, groups: dict):
    """把 summary.feedback_events 分配给各个 training_set 分组（session_items 的粒度）。
    事件自带 rep_index（原型全局序号）时直接归那一次动作所在的组；没有就按时间戳判：
    每组的时间窗是该组内各 rep 的 [start_s,end_s] 并集的外包络，事件落在某组窗内就归那组，
    落在组间空档（如组间休息）就近归给外包络边界最近的组，tie 时归 set_index 较小的组。
    没有任何一组（reps 全部被中断、没有 repetitions）时返回空字典，事件不落库
    （session_events 需要 session_item_id，没有 session_item 就没地方挂）。"""
    if not groups:
        return {}
    extents = {}
    index_to_group = {}
    for set_index, reps in groups.items():
        extents[set_index] = (min(r["start_s"] for r in reps), max(r["end_s"] for r in reps))
        for rep in reps:
            if rep.get("index") is not None:
                index_to_group[rep["index"]] = set_index
    assigned = {set_index: [] for set_index in groups}
    for event in feedback_events:
        own = event.get("rep_index")
        if own is not None and own in index_to_group:
            assigned[index_to_group[own]].append(event)
            continue
        t = event.get("timestamp_s")
        best = min(extents, key=lambda k: (_event_distance(t, extents[k]), k))
        assigned[best].append(event)
    return assigned


def build_session_events(events: list, reps: list):
    """回填 rep_index：优先用事件自带的 rep_index（原型全局序号，换算成落库用的组内序号），
    没带才按时间戳落在哪个 rep 的 [start_s,end_s] 窗内判，两样都对不上就留空。

    为什么优先用事件自带的：原型里 AMPLITUDE_BELOW_TARGET / HOLD_TOO_SHORT / RETURN_TOO_FAST
    这三类"这一次动作没达标"的事件，是在这一次动作被判定完成的那一帧才发出的，而 rep 的 end_s
    取的是小腿回到静息位的时刻，比那一帧早至少一个 rest_dwell_s，所以这三类事件的时间戳必然落在
    所有 rep 窗口之外。只按时间窗回填，最该有 rep_index 的这三类事件反而会全部落空。
    原始事件整条存进 raw_json，不丢字段。
    """
    by_global_index = {rep["index"]: rep for rep in reps if rep.get("index") is not None}
    rows = []
    for event in events:
        t = event.get("timestamp_s")
        rep_index = None
        own_index = event.get("rep_index")
        if own_index is not None and own_index in by_global_index:
            rep_index = _stored_rep_index(by_global_index[own_index])
        elif t is not None:
            for rep in reps:
                if rep["start_s"] <= t <= rep["end_s"]:
                    rep_index = _stored_rep_index(rep)
                    break
        rows.append({
            "rep_index": rep_index,
            "timestamp_s": t,
            "code": event.get("code"),
            "message": event.get("message"),
            "severity": event.get("level"),
            "raw_json": json.dumps(event, ensure_ascii=False),
        })
    return rows


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not db_path.exists()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if fresh:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.commit()
    return con


def already_imported(con: sqlite3.Connection, import_key: str):
    row = con.execute("SELECT id FROM sessions WHERE import_source_key=?", (import_key,)).fetchone()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build_session_item(*, exercise_code, set_index, reps, rows, summary, assessment, training_session, score_mode="none"):
    feedback_events = summary.get("feedback_events", [])
    effective_parameters = summary.get("effective_parameters") or summary.get("configuration") or {}
    rest_angle, target_angle = rest_target_angles(exercise_code, effective_parameters)

    reps_target = None
    if training_session:
        reps_target = (training_session.get("plan") or {}).get("reps_per_set")
    if not reps_target:
        reps_target = len(reps)

    rep_rows = []
    reps_valid_count = 0
    too_fast_count = 0
    compensation_count = 0
    any_needs_review = False
    for rep in reps:
        events = events_in_window(feedback_events, rep["start_s"], rep["end_s"])
        flags = rep_flags(events)
        valid = rep_is_valid(rep, events)
        if valid:
            reps_valid_count += 1
        if "too_fast" in flags:
            too_fast_count += 1
        compensation_count += sum(1 for f in flags if f != "too_fast")
        needs_review = bool(rep.get("needs_review"))
        any_needs_review = any_needs_review or needs_review
        rep_rows.append({
            "rep_index": rep.get("rep_in_set", rep.get("index")),
            "peak_angle": primary_peak(exercise_code, rep),
            "duration_ms": int(round((rep["end_s"] - rep["start_s"]) * 1000)),
            "valid": 1 if valid else 0,
            "flags_json": json.dumps(flags, ensure_ascii=False),
            "hold_s": rep.get("target_hold_s"),
            "return_s": rep.get("return_s"),
            "bridged_gaps": rep.get("bridged_gaps", 0) or 0,
            "needs_review": 1 if needs_review else 0,
        })

    reps_done = len(reps)
    peaks = [primary_peak(exercise_code, r) for r in reps]
    peaks = [p for p in peaks if p is not None]
    peak_angle_max = max(peaks) if peaks else None
    peak_angle_mean = statistics.fmean(peaks) if peaks else None
    duration_ms = sum(rr["duration_ms"] for rr in rep_rows)
    capture_quality = compute_capture_quality(rows, reps)
    low_confidence = bool(capture_quality is not None and capture_quality < 0.6)

    if score_mode == "contract-d":
        quality_score, score_breakdown = compute_contract_d_score(
            reps_valid=reps_valid_count, reps_target=reps_target, reps_done=reps_done,
            peak_angle_max=peak_angle_max, rest_angle=rest_angle, target_angle=target_angle,
            compensation_count=compensation_count, too_fast_count=too_fast_count,
            capture_quality=capture_quality, score_weights=DEFAULT_SCORE_WEIGHTS,
        )
    else:
        quality_score = None
        score_breakdown = compute_provisional_breakdown(
            reps_valid=reps_valid_count, reps_target=reps_target, reps_done=reps_done,
            peak_angle_max=peak_angle_max, rest_angle=rest_angle, target_angle=target_angle,
            compensation_count=compensation_count, too_fast_count=too_fast_count,
            capture_quality=capture_quality,
        )

    item = {
        "exercise_code": exercise_code,
        "set_index": set_index,
        "reps_target": reps_target,
        "reps_done": reps_done,
        "reps_valid": reps_valid_count,
        "peak_angle_max": peak_angle_max,
        "peak_angle_mean": peak_angle_mean,
        "duration_ms": duration_ms,
        "quality_score": quality_score,
        "score_breakdown_json": json.dumps(score_breakdown, ensure_ascii=False),
        "compensation_count": compensation_count,
        "capture_quality": capture_quality,
        "low_confidence": 1 if low_confidence else 0,
        "angle_trace_json": compute_angle_trace(rows, reps, exercise_code),
        "checks_json": compute_checks_json(assessment, reps),
        "measurement_angle_json": compute_measurement_angle_json(rows, reps),
        "calibration_json": compute_calibration_json(summary, reps),
        "needs_review": 1 if any_needs_review else 0,
    }
    return item, rep_rows


def compute_angle_trace(rows: list, reps: list, exercise_code: str, step_s: float = 0.1):
    """每 100ms 一个点，取组内各 rep 时间窗并集，用和 peak_angle 同一口径的量
    （动作 1/8 用 smoothed_included_deg 真实角，SLR/SQUAT 用 motion_amount_deg 相对量，
    后者原型帧记录里已经是未做二次偏移的原始相对值）。"""
    if not reps:
        return None
    key = "motion_amount_deg" if exercise_code in RELATIVE_ANGLE_EXERCISES else "smoothed_included_deg"
    points = []
    next_t = None
    for rep in sorted(reps, key=lambda r: r["start_s"]):
        for r in sorted(frames_in_window(rows, rep["start_s"], rep["end_s"]), key=lambda r: r.get("timestamp_s", 0)):
            t = r.get("timestamp_s")
            v = r.get(key)
            if t is None or v is None:
                continue
            if next_t is None or t >= next_t:
                points.append(round(v, 1))
                next_t = t + step_s
    return json.dumps(points, ensure_ascii=False) if points else None


def import_run(directory: Path, *, patient_id: int, plan_id, plan_item_id, db_path: Path, dry_run: bool,
                score_mode: str = "none"):
    summary, rows, assessment = load_run(directory)
    status = summary.get("status")
    if status in SKIP_STATUS:
        print(f"[跳过] status={status!r}，大概率不该落库（原型运行失败）：{directory}")
        return None
    exercise_name, exercise_code = resolve_exercise(summary, rows)
    started_at, ended_at, started_at_source, import_key = resolve_timing(summary, rows, directory)
    schema_status = STATUS_MAP.get(status, "finished")
    if status not in STATUS_MAP:
        print(f"[提示] summary.status={status!r} 不在已知映射表里，按 finished 处理，去核对一下")

    groups = group_repetitions(summary)
    training_session = summary.get("training_session")
    event_groups = assign_events_to_groups(summary.get("feedback_events", []), groups)

    algorithm_version = summary.get("algorithm_version")
    rule_snapshot = {
        exercise_code: {
            "algorithm_version": algorithm_version,
            "backend": summary.get("backend"),
            "prototype_exercise": exercise_name,
            "effective_parameters": summary.get("effective_parameters") or summary.get("configuration"),
            "exercise_rules": summary.get("exercise_rules"),
            "measurement_parameters": summary.get("measurement_parameters"),
        }
    }

    con = open_db(db_path)
    try:
        existing = already_imported(con, import_key)
        if existing:
            print(f"[跳过] 已经导入过（sessions.id={existing}，import_source_key={import_key!r}）：{directory}")
            return existing

        patient_row = con.execute("SELECT id FROM patients WHERE id=?", (patient_id,)).fetchone()
        if not patient_row:
            raise ImportError_(f"patients 表里没有 id={patient_id} 这个患者，先建好演示患者或换一个 --patient-id")

        items = []
        for set_index, reps in groups.items():
            item, rep_rows = build_session_item(
                exercise_code=exercise_code, set_index=set_index, reps=reps, rows=rows,
                summary=summary, assessment=assessment, training_session=training_session,
                score_mode=score_mode,
            )
            event_rows = build_session_events(event_groups.get(set_index, []), reps)
            items.append((item, rep_rows, event_rows))

        if dry_run:
            print(f"[dry-run] 将导入 {directory}：动作={exercise_code}，{len(items)} 组，"
                  f"共 {sum(len(r) for _, r, _ in items)} 次动作，"
                  f"{sum(len(e) for _, _, e in items)} 条提示事件，status={schema_status}，"
                  f"score_mode={score_mode}")
            for item, rep_rows, event_rows in items:
                print(f"  - 第{item['set_index']}组：reps_done={item['reps_done']} "
                      f"reps_valid={item['reps_valid']} quality_score={item['quality_score']} "
                      f"事件数={len(event_rows)}")
            return None

        cur = con.execute(
            "INSERT INTO sessions(patient_id,plan_id,started_at,ended_at,status,device,camera_side,"
            "rule_versions_json,client_version,pain_score,note,import_source_key,started_at_source) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (patient_id, plan_id, started_at, ended_at, schema_status,
             f"prototype:{summary.get('backend')}", "side",
             json.dumps(rule_snapshot, ensure_ascii=False), algorithm_version, None,
             f"离线导入自 {directory.name}", import_key, started_at_source),
        )
        session_id = cur.lastrowid

        for item, rep_rows, event_rows in items:
            cur = con.execute(
                "INSERT INTO session_items(session_id,plan_item_id,exercise_code,set_index,reps_target,reps_done,"
                "reps_valid,peak_angle_max,peak_angle_mean,duration_ms,quality_score,score_breakdown_json,"
                "compensation_count,capture_quality,low_confidence,angle_trace_json,checks_json,"
                "measurement_angle_json,calibration_json,needs_review) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session_id, plan_item_id, item["exercise_code"], item["set_index"], item["reps_target"],
                 item["reps_done"], item["reps_valid"], item["peak_angle_max"], item["peak_angle_mean"],
                 item["duration_ms"], item["quality_score"], item["score_breakdown_json"],
                 item["compensation_count"], item["capture_quality"], item["low_confidence"],
                 item["angle_trace_json"], item["checks_json"], item["measurement_angle_json"],
                 item["calibration_json"], item["needs_review"]),
            )
            item_id = cur.lastrowid
            for rr in rep_rows:
                con.execute(
                    "INSERT INTO reps(session_item_id,rep_index,peak_angle,duration_ms,valid,flags_json,"
                    "hold_s,return_s,bridged_gaps,needs_review) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (item_id, rr["rep_index"], rr["peak_angle"], rr["duration_ms"], rr["valid"],
                     rr["flags_json"], rr["hold_s"], rr["return_s"], rr["bridged_gaps"], rr["needs_review"]),
                )
            for ev in event_rows:
                con.execute(
                    "INSERT INTO session_events(session_item_id,rep_index,timestamp_s,code,message,severity,"
                    "raw_json) VALUES(?,?,?,?,?,?,?)",
                    (item_id, ev["rep_index"], ev["timestamp_s"], ev["code"], ev["message"], ev["severity"],
                     ev["raw_json"]),
                )
            if item["low_confidence"]:
                con.execute(
                    "INSERT INTO alerts(patient_id,session_id,type,severity,message) VALUES(?,?,?,?,?)",
                    (patient_id, session_id, "low_capture", "info",
                     f"训练组第{item['set_index']}组 capture_quality="
                     f"{item['capture_quality']:.2f} 低于 0.6（离线导入自原型结果，非实时判定）"),
                )
        con.commit()
        print(f"[完成] session_id={session_id}，{len(items)} 组，"
              f"共 {sum(len(r) for _, r, _ in items)} 次动作，"
              f"{sum(len(e) for _, _, e in items)} 条提示事件，来自 {directory}")
        return session_id
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", type=Path, help="原型运行结果目录（含 summary.json / frames.jsonl）")
    parser.add_argument("--patient-id", type=int, required=True)
    parser.add_argument("--plan-id", type=int, default=None)
    parser.add_argument("--plan-item-id", type=int, default=None)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true", help="只打印将要导入的内容，不写数据库")
    parser.add_argument("--score-mode", choices=["none", "contract-d"], default="none",
                         help="默认 none：quality_score 留 NULL，score_breakdown_json 只存原始输入"
                              "（reps_valid/reps_target、幅度比、事件计数、capture_quality），标 provisional。"
                              "评分口径待常/陈确认，见 docs/decisions/0002。传 contract-d 才按接口契约 D 节"
                              "公式现算并写进 quality_score，供联调对比用，不是默认行为。")
    args = parser.parse_args(argv)

    try:
        import_run(
            args.directory, patient_id=args.patient_id, plan_id=args.plan_id,
            plan_item_id=args.plan_item_id, db_path=args.db, dry_run=args.dry_run,
            score_mode=args.score_mode,
        )
    except ImportError_ as exc:
        print(f"[失败] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
