"""评分参考实现（服务端缺省/校验用）。

公式归算法（常）所有；后端（常）只在前端没传 quality_score 时用这份缺省算法补一个，
并把 breakdown 一起存下来，保证报告里永远能解释"分是怎么来的"。
权重来自规则版本 params.score_weights，不写死。
"""
from __future__ import annotations


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


DEFAULT_WEIGHTS = {"completion": .3, "amplitude": .25, "posture": .25, "tempo": .1, "stability": .1}


def score_item(item: dict, params: dict) -> tuple[float, dict]:
    """返回 (总分 0-100, 各维度得分)。item 是 session_items 的字段字典。"""
    # 规则里的 score_weights 可能只覆盖部分维度（例如康复师只改了 completion），
    # 缺的维度必须补默认值，否则下面按键取值会 KeyError，把上报接口打挂。
    w = {**DEFAULT_WEIGHTS, **(params.get("score_weights") or {})}
    target = item.get("reps_target") or 1
    done = item.get("reps_done") or 0
    valid = item.get("reps_valid") or 0
    peak = item.get("peak_angle_max")
    target_angle = params.get("target_angle")
    rest_angle = params.get("rest_angle", 0)
    direction = params.get("direction", "down")

    # 完成度：有效次数 / 目标次数
    completion = clamp(valid / target)

    # 幅度：峰值相对个体目标的达成比例（按运动方向归一）
    if peak is None or target_angle is None:
        amplitude = 0.5  # 没有角度就给中性值，不奖不罚
    else:
        span = abs(target_angle - rest_angle) or 1
        reached = abs(peak - rest_angle)
        amplitude = clamp(reached / span)

    # 姿态：代偿次数越多越低
    comp = item.get("compensation_count") or 0
    posture = clamp(1 - comp / max(done, 1))

    # 节奏：太快/停顿的次数由前端在 reps.flags 里标；这里用比例
    too_fast = item.get("_too_fast_count", 0)
    tempo = clamp(1 - too_fast / max(done, 1))

    # 稳定性：关键点可用帧率直接当稳定性代理
    stability = clamp(item.get("capture_quality") if item.get("capture_quality") is not None else 0.8)

    parts = {
        "completion": round(100 * w["completion"] * completion, 1),
        "amplitude": round(100 * w["amplitude"] * amplitude, 1),
        "posture": round(100 * w["posture"] * posture, 1),
        "tempo": round(100 * w["tempo"] * tempo, 1),
        "stability": round(100 * w["stability"] * stability, 1),
    }
    total = round(sum(parts.values()), 1)
    return total, parts
