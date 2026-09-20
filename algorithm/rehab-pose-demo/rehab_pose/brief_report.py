"""Deterministic, evidence-based session brief; no medical score or diagnosis."""
from collections import Counter

NAMES={'1':'坐姿伸膝','2':'仰卧直腿抬高','6':'扶椅微蹲','8':'坐站训练'}
POSTURE={
    'SQUAT_DEPTH_EXCEEDED':('下蹲超出本次目标范围','下一组减小下蹲深度，扶稳后慢慢站回，不追求更深。'),
    'SQUAT_HOLD_SWAY':('保持阶段躯干波动较大','下一组放慢动作，保持肩背姿势平稳。'),
    'TRUNK_FORWARD':('身体前倾超出设置范围','下一组留意上身相对起始坐姿的变化，参考页面提示调整。'),
    'TRUNK_BACKWARD':('身体后仰超出设置范围','下一组留意是否在伸膝时向后靠，先回到标定时的坐姿。'),
    'THIGH_MOVEMENT':('大腿位置变化超出设置范围','下一组留意大腿是否随小腿一起明显抬起。'),
    'SLR_KNEE_BENT':('抬腿时膝盖弯曲超过设置容差','下一组按康复师要求检查膝盖伸直情况。'),
    'SLR_TOO_HIGH':('抬腿幅度超过设置上限','下一组参考已设置的抬腿范围。'),
    'SLR_TOO_FAST':('抬腿或放回速度超出设置范围','下一组参考已设置的动作节奏。'),
    'SLR_TRUNK_MOVED':('抬腿时躯干方向变化超出设置范围','下一组留意躯干位置是否随抬腿变化。'),
    'SQUAT_TOO_DEEP':('下蹲深度超过设置上限','下一组参考已设置的下蹲深度。'),
    'SQUAT_FORWARD':('下蹲时前倾超过设置范围','下一组留意躯干角度并请康复师核对目标。'),
    'SQUAT_TOO_FAST':('下蹲或起身速度超出设置范围','下一组参考已设置的动作节奏。'),
    'STS_TOP_NOT_UPRIGHT':('站立阶段未达到设置的伸展要求','下一组站稳后再核对页面中的站立提示。'),
    'STS_TOO_FAST':('起身或坐下速度超出设置范围','下一组参考已设置的动作节奏。'),
}


def build_brief(exercise,side,training,reps,events,quality,interrupted):
    plan=training['plan']
    rows=[]
    for group in range(1,plan['sets']+1):
        selected=[r for r in reps if r.get('training_set')==group]
        alerts=[e for e in events if e.get('training_set')==group]
        q=quality.get(group,{'frames':0,'observed_frames':0})
        problems=[]
        amplitude='伸膝幅度' if exercise=='1' else '动作幅度'
        checks=[('amplitude_met','AMPLITUDE_BELOW_TARGET',amplitude+'未达到设置目标','下一组参考页面目标范围；目标难以完成时请康复师调整。'),
                ('hold_met','HOLD_TOO_SHORT','连续保持时间不足',f"下一组达到目标后，参考页面计时连续保持{plan['hold_s']:g}秒。"),
                ('extension_time_met','EXTENSION_TOO_FAST','运动阶段用时短于设置要求','下一组参考页面节奏，减慢伸出或抬起过程。'),
                ('return_time_met','RETURN_TOO_FAST','放回阶段用时短于设置要求','下一组参考页面节奏，缓慢放回。')]
        for key,code,label,advice in checks:
            if exercise=='6' and key=='extension_time_met': label,advice='下蹲阶段用时短于设置要求','下一组参考页面节奏，缓慢下蹲。'
            if exercise=='6' and key=='return_time_met': label,advice='起身阶段用时短于设置要求','下一组扶稳支撑物，慢慢站回。'
            failed=sum(r.get('target_comparison',{}).get(key) is False for r in selected)
            if failed:
                problems.append({'code':code,'count':failed,'unit':'次动作','message':label,'advice':advice})
        counters=Counter(e['code'] for e in alerts if e.get('code') in POSTURE)
        for code,count in counters.items():
            label,advice=POSTURE[code]
            problems.append({'code':code,'count':count,'unit':'条提醒','message':label,'advice':advice})
        met=sum(r.get('target_completed',r.get('target_comparison',{}).get('amplitude_met') is True and
                r.get('target_comparison',{}).get('hold_met') is True) for r in selected)
        unassessed=sum(any(v is None for v in r.get('target_comparison',{}).values()) or r.get('needs_review',False) for r in selected)
        status='未开始' if not q['frames'] and not selected else '次数完成' if len(selected)>=plan['reps_per_set'] else '记录未完成'
        if not selected:
            finding='没有识别到完整动作，不能判断本组动作是否达到目标。'
        elif problems:
            finding='；'.join(f"{p['message']}（{p['count']}{p['unit']}）" for p in problems[:3])+'。'
        else:
            finding='已记录动作未触发当前规则提醒；不代表所有姿势和康复效果均已验证。'
        rows.append({'set':group,'status':status,'completed_reps':len(selected),'target_reps':plan['reps_per_set'],
                     'angle_hold_met_reps':met,'needs_review_reps':unassessed,'problems':problems,
                     'finding':finding,'measurement_quality':q})
    total=sum(r['completed_reps'] for r in rows)
    suggestions=[]
    for row in rows:
        for p in row['problems']:
            if p['advice'] not in suggestions:
                suggestions.append(p['advice'])
    invalid=sum(q['frames']-q['observed_frames'] for q in quality.values())
    if invalid or interrupted:
        suggestions.insert(0,'本次存在遮挡、漏检或中断，记录次数可能少于实际次数；先检查取景与训练者锁定，再复测。')
    if not total:
        suggestions.insert(0,'先确认训练侧和画面朝向，等待起始标定完成后，再做一次完整动作。')
    if not suggestions:
        suggestions.append('继续参考康复师已设置的训练目标；本报告供训练记录和复核使用。')
    return {'version':'1.0','title':'本次训练简报','exercise':NAMES[exercise],'side':'左腿' if side=='left' else '右腿',
            'completed_reps':total,'target_reps':plan['sets']*plan['reps_per_set'],
            'sets':rows,'suggestions':suggestions[:3],'interrupted_attempts':len(interrupted),
            'scope':'二维视觉训练辅助；达到角度和保持目标不等于动作完全合格，也不用于判断伤势恢复。',
            'delivery':'仅在当前页面生成，可下载；尚未自动发送给康复师。','video_saved':False}


def brief_text(report):
    lines=[report['title'],f"{report['exercise']} · {report['side']}",
           f"识别完成 {report['completed_reps']} / 计划 {report['target_reps']} 次",'']
    for row in report['sets']:
        lines += [f"第{row['set']}组：{row['completed_reps']}/{row['target_reps']}次，{row['status']}",row['finding']]
    lines += ['','下次留意：']+['- '+s for s in report['suggestions']]
    lines += ['',report['scope'],report['delivery']]
    return '\n'.join(lines)
