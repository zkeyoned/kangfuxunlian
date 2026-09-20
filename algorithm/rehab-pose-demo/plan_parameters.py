"""Shared transport validation; ranges are technical bounds, not prescriptions."""
import math

RANGES={'seated':(130,180),'supine':(20,44),'squat':(20,80),'stand':(130,180)}
def validate_targets(exercise, targets):
    if exercise not in RANGES or not isinstance(targets,dict):raise ValueError('不支持的动作目标')
    ranges={'target_deg':RANGES[exercise],'hold_s':(0,30),'return_s':(0,20),'rest_s':(0,300)}
    if set(targets)!=set(ranges):raise ValueError('目标字段必须包含角度、保持、返回和组间休息')
    for key,(low,high) in ranges.items():
        v=targets[key]
        if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:raise ValueError(f'{key} 应在 {low}–{high} 范围内')
    return targets


def apply_targets(exercise, targets, analyzer, rules):
    key={'1':'seated','2':'supine','6':'squat','8':'stand'}[exercise]
    validate_targets(key,targets)
    c=analyzer.engine.config
    c.target_deg=targets['target_deg']+(90 if exercise in ('2','6') else 0)
    c.min_hold_s=targets['hold_s'];c.min_return_s=targets['return_s']
    c.__post_init__()
    if exercise=='2':rules.slr_target_min_deg=targets['target_deg']
    if exercise=='8':rules.standing_knee_min_deg=targets['target_deg']
