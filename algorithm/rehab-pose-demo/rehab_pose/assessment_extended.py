"""Reports for 2/6/8 using recorded image measurements, never force estimates."""
def assess_extended(summary,rows):
    ex=summary['exercise'];rules=summary['exercise_rules'];params=summary['effective_parameters']
    items=[]
    attempts=[(r,True) for r in summary.get('repetitions',[])]+[(r,False) for r in summary.get('interrupted_attempts',[])]
    for rep,complete in sorted(attempts,key=lambda x:x[0]['start_s']):
        samples=[r for r in rows if rep['start_s']<=r['timestamp_s']<=rep['end_s']]
        observed=[r for r in samples if r.get('visible') and not r.get('bridge_pending') and r.get('measurement_metrics',{}).get('knee_included_deg') is not None]
        gap=any(b['timestamp_s']-a['timestamp_s']>params['max_gap_s'] for a,b in zip(samples,samples[1:]))
        uncertain=not complete or not samples or len(observed)!=len(samples) or gap or rep.get('needs_review',False)
        def values(key):return [r['measurement_metrics'][key] for r in observed if r['measurement_metrics'].get(key) is not None]
        def extreme(key,fn=max,absolute=False):
            vs=values(key)
            return fn([abs(v) for v in vs] if absolute else vs) if vs and len(vs)==len(observed) else None
        knees=values('knee_included_deg');checks=[]
        def check(key,label,actual,low=None,high=None,unit='deg'):
            unknown=uncertain or actual is None
            status='unable_to_assess' if unknown else 'met' if (low is None or actual>=low) and (high is None or actual<=high) else 'not_met'
            checks.append(dict(metric=key,label=label,measured=actual,target_min=low,target_max=high,unit=unit,status=status,
                               reason='测量不完整或动作中断，需复核' if unknown else '达到设置范围' if status=='met' else '未达到设置范围'))
        if ex=='SUPINE_STRAIGHT_LEG_RAISE':
            check('raise','抬腿幅度（相对初始大腿方向）',extreme('leg_raise_delta_deg'),rules['slr_target_min_deg'],rules['slr_target_max_deg'])
            check('straight','膝关节伸直程度',extreme('knee_included_deg',min),rules['slr_min_knee_deg'])
            check('hold','目标范围内连续保持',rep.get('target_hold_s'),params['min_hold_s'],unit='s')
            check('trunk','躯干方向最大变化',extreme('trunk_delta_deg',absolute=True),high=rules['slr_trunk_delta_limit_deg'])
        elif ex=='SUPPORTED_MINI_SQUAT':
            check('depth_min','下蹲活动幅度',rep.get('max_motion_delta_deg'),params['target_deg']-90)
            check('depth_max','最大膝屈曲角',extreme('knee_flexion_deg'),high=rules['squat_max_flexion_deg'])
            check('trunk','最大躯干前倾角',extreme('trunk_signed_deg'),high=rules['squat_forward_limit_deg'])
        else:
            check('extension','最大膝夹角',extreme('knee_included_deg'),rules['standing_knee_min_deg'])
            top=[r['measurement_metrics'] for r in observed if r['measurement_metrics']['knee_included_deg']>=rules['standing_knee_min_deg']]
            valid=[v for v in top if v.get('trunk_signed_deg') is not None and v.get('hip_flexion_proxy_deg') is not None]
            upright=(int(any(abs(v['trunk_signed_deg'])<=rules['standing_trunk_limit_deg'] and v['hip_flexion_proxy_deg']<=rules['standing_hip_flexion_max_deg'] for v in valid)) if valid else 0 if not top else None)
            check('upright','是否达到站立姿势范围',upright,1,unit='boolean')
        check('return','返回用时（放下/起身/坐下）',rep.get('return_s'),params['min_return_s'],unit='s')
        status='unable_to_assess' if any(c['status']=='unable_to_assess' for c in checks) else 'not_met' if any(c['status']=='not_met' for c in checks) else 'met'
        items.append(dict(attempt=len(items)+1,completed_rep_index=rep.get('index'),start_s=rep['start_s'],end_s=rep['end_s'],completed=complete,
                          interruption_reason=rep.get('reason'),quality=dict(frame_count=len(samples),observed_frame_count=len(observed),
                          observed_frame_ratio=len(observed)/len(samples) if samples else None,requires_review=uncertain),
                          measurements={'observed_excursion_deg':max(knees)-min(knees) if knees else None},checks=checks,status=status))
    return dict(schema_version='1.1',rule_version='experimental-exercises-1',exercise=ex,supported=True,
                scope='实验性二维动作指标评估；不代表整体动作正确、肌肉发力或康复疗效',
                unsupported_checks=summary.get('unsupported_checks',[]),parameters=params,exercise_rules=rules,
                calibration_completed=bool(summary.get('calibrations')),training_session=summary.get('training_session'),
                attempts=items,counts={s:sum(i['status']==s for i in items) for s in ('met','not_met','unable_to_assess')})
