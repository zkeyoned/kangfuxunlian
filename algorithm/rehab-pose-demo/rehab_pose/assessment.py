"""Post-session, rule-based reports; never infer missing motion samples."""
import json
from pathlib import Path


def assess(summary, rows):
    if summary['exercise']!='SEATED_KNEE_EXTENSION' and 'exercise_rules' in summary:
        from .assessment_extended import assess_extended
        return assess_extended(summary,rows)
    params = summary['effective_parameters']
    supported = summary['exercise'] == 'SEATED_KNEE_EXTENSION'
    items = []
    attempts = [(r, True) for r in summary.get('repetitions', [])]
    attempts += [(r, False) for r in summary.get('interrupted_attempts', [])]
    for rep, completed in sorted(attempts, key=lambda pair: pair[0]['start_s']):
        samples = [r for r in rows if rep['start_s'] <= r['timestamp_s'] <= rep['end_s']]
        observed = [r for r in samples if r.get('visible') and
                    r.get('measurement_source') != 'predicted' and not r.get('bridge_pending')
                    and r.get('measurement_metrics', {}).get('knee_included_deg') is not None]
        angles = [r['measurement_metrics']['knee_included_deg'] for r in observed]
        observed_ids={id(r) for r in observed}
        valid_duration=sum(max(0,b['timestamp_s']-a['timestamp_s']) for a,b in zip(samples,samples[1:])
                           if id(a) in observed_ids)
        attempt_duration=max(0,rep['end_s']-rep['start_s'])
        predicted = sum(bool(r.get('bridge_pending')) for r in samples)
        gaps = any(b['timestamp_s']-a['timestamp_s'] > params.get('max_gap_s', .3)
                   for a, b in zip(samples, samples[1:]))
        uncertain = (not completed or not samples or len(observed) != len(samples)
                     or gaps or bool(rep.get('needs_review')) or bool(rep.get('bridged_gaps')))
        quality = {'frame_count': len(samples), 'observed_frame_count': len(observed),
                   'observed_frame_ratio': len(observed)/len(samples) if samples else None,
                   'prediction_frame_count': predicted, 'timestamp_gap': gaps,
                   'requires_review': uncertain,
                   'note': '图像可用性统计，不是角度准确率或身份认证'}
        metrics = {'observed_min_knee_deg': min(angles) if angles else None,
                   'observed_max_knee_deg': max(angles) if angles else None,
                   'observed_excursion_deg': max(angles)-min(angles) if angles else None,
                   'knee_start_deg':rep.get('knee_start_deg'), 'knee_peak_deg':rep.get('knee_peak_deg'),
                   'knee_excursion_deg':rep.get('knee_excursion_deg'),
                   'time_to_target_s':rep.get('time_to_target_s'),
                   'target_hold_s': rep.get('target_hold_s'), 'return_s': rep.get('return_s'),
                   'cycle_duration_s':rep.get('cycle_duration_s'),
                   'valid_time_ratio':min(1,valid_duration/attempt_duration) if attempt_duration else None}
        checks = []
        for key, label, actual, target in [
            ('amplitude', '伸膝幅度', metrics['observed_max_knee_deg'], params['target_deg']),
            ('hold', '连续保持时间', metrics['target_hold_s'], params['min_hold_s']),
            ('extension_time', '伸出用时', metrics['time_to_target_s'], 1),
            ('return', '返回用时', metrics['return_s'], params['min_return_s'])]:
            target_not_reached=key=='extension_time' and actual is None and not uncertain
            unknown = uncertain or not supported or (actual is None and not target_not_reached)
            status = 'unable_to_assess' if unknown else ('not_met' if target_not_reached else 'met' if actual >= target else 'not_met')
            checks.append({'metric': key, 'label': label, 'measured': actual,
                           'target_min': target if supported else None,
                           'unit': 'deg' if key == 'amplitude' else 's', 'status': status,
                           'reason': ('当前报告仅支持动作1' if not supported else
                                      '动作未完整完成或测量不连续，需复核' if unknown else
                                      '未到达目标角度，无法形成到达目标用时' if target_not_reached else
                                      '达到设置目标' if status == 'met' else '未达到设置目标')})
        overall = ('unable_to_assess' if any(c['status']=='unable_to_assess' for c in checks)
                   else 'not_met' if any(c['status']=='not_met' for c in checks) else 'met')
        items.append({'attempt': len(items)+1, 'completed_rep_index': rep.get('index'),
                      'start_s': rep['start_s'], 'end_s': rep['end_s'], 'completed': completed,
                      'target_completed':bool(rep.get('target_completed')) if completed else False,
                      'interruption_reason': rep.get('reason'), 'quality': quality,
                      'measurements': metrics, 'checks': checks, 'status': overall})
    return {'schema_version': '1.1', 'rule_version': 'seated-extension-v0.1-report-2',
            'training_session': summary.get('training_session'),
            'exercise': summary['exercise'], 'supported': supported,
            'scope': '评估伸膝幅度、连续保持、伸出与返回用时；姿态提醒单独记录，不是临床疗效判断',
            'parameters': params, 'calibration_completed': bool(summary.get('calibrations')),
            'excursion_definition': '记录的动作开始至返回期间，可靠观测膝夹角的最大值减最小值；非完整临床活动范围',
            'attempts': items, 'counts': {**{s: sum(i['status']==s for i in items)
                                         for s in ('met', 'not_met', 'unable_to_assess')},
                                         'completed_cycles':sum(i['completed'] for i in items),
                                         'target_completed':sum(i['target_completed'] for i in items)}}


def write_report(directory, summary=None):
    directory = Path(directory)
    if summary is None:
        summary = json.loads((directory/'summary.json').read_text(encoding='utf-8-sig'))
    with (directory/'frames.jsonl').open(encoding='utf-8-sig') as f:
        rows = [json.loads(line) for line in f if line.strip()]
    report = assess(summary, rows)
    report['feedback_events']=summary.get('feedback_events',[])
    (directory/'assessment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    labels = {'met': '达标', 'not_met': '未达标', 'unable_to_assess': '无法判断'}
    names={'SEATED_KNEE_EXTENSION':'坐姿伸膝','SUPINE_STRAIGHT_LEG_RAISE':'卧姿直腿抬高','SUPPORTED_MINI_SQUAT':'扶物微蹲','SIT_TO_STAND':'坐立'}
    lines = ['# '+names.get(summary['exercise'],summary['exercise'])+'训练报告', '', report['scope'], '',
             '目标来自本次运行的测试配置，尚未经康复师确认。', '']
    if not report['supported']: lines.append('本动作暂不支持此报告规则。')
    if report.get('unsupported_checks'):lines += ['不支持判断：'+'；'.join(report['unsupported_checks']),'']
    if report['training_session']:
        training=report['training_session'];plan=training['plan'];progress=training['progress']
        state_label={'ended_incomplete':'已结束，计划未完成','completed':'计划已完成','training':'进行中','paused':'暂停','resting':'组间休息'}.get(progress['status'],progress['status'])
        lines += [f"本次计划：{plan['sets']}组，每组{plan['reps_per_set']}次，保持{plan['hold_s']}秒，组间休息{plan['rest_s']}秒。",
                  f"系统确认完整动作{progress['completed_repetitions']}次，计划状态：{state_label}。次数不代表全部达标；此处不统计每日累计训练量。",'']
    if not report['calibration_completed']: lines.append('未完成初始标定，不能据此判断训练合格。')
    if not report['attempts']: lines.append('未记录到可报告的动作尝试。')
    if report['attempts']:
        lines += [f"完整动作 {report['counts']['completed_cycles']} 次；达到目标角度并连续保持达标 {report['counts']['target_completed']} 次。",'']
    if report['feedback_events']:
        lines += ['','## 实际提醒','']
        for event in report['feedback_events']:lines.append(f"- {event['timestamp_s']:.2f}秒：{event['message']}")
        lines.append('')
    for item in report['attempts']:
        lines += [f"## 尝试{item['attempt']}（{item['start_s']:.2f}～{item['end_s']:.2f}秒）：{labels[item['status']]}", '']
        ratio = item['quality']['observed_frame_ratio']
        lines.append('可靠观测画面比例：'+(f'{ratio:.1%}' if ratio is not None else '无数据')+'（不代表测量准确率）。')
        excursion = item['measurements']['observed_excursion_deg']
        lines += ['观测角度变化幅度：'+(f'{excursion:.1f}°' if excursion is not None else '无数据'), '']
        for check in item['checks']:
            value = check['measured']; target = check['target_min']
            shown = f'{value:.2f}' if value is not None else '缺失'
            unit = '°' if check['unit']=='deg' else '秒' if check['unit']=='s' else '（1为是，0为否）'
            target_text=('下限'+str(target) if target is not None else '')+(' 上限'+str(check['target_max']) if check.get('target_max') is not None else '')
            lines.append(f"- {check['label']}：{labels[check['status']]}；观测值 {shown}{unit}；目标 {target_text}。{check['reason']}")
        lines.append('')
    (directory/'assessment.md').write_text('\n'.join(lines), encoding='utf-8')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    write_report(args.directory)

