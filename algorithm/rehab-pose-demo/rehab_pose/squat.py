"""Supported mini-squat candidate v0.1. Image displacement is not loading."""
import math
from statistics import median
from .slr import SupineAnalyzer, wrap
from .core import angle


def percentile(values, fraction):
    values=sorted(values);position=(len(values)-1)*fraction
    lo=int(position);hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(position-lo)


class SquatAnalyzer(SupineAnalyzer):
    def __init__(self,targets=None):
        super().__init__(targets or dict(target_deg=30,hold_s=1,return_s=1,rest_s=30))
        self.direction=1;self.setup=None;self.attempts=[];self.gaps=[];self.rest_since=None
        self.stage='confirm_support'

    def configure(self,setup):
        if not isinstance(setup,dict) or setup.get('support_confirmed') is not True:raise ValueError('请先人工确认双手扶稳稳定支撑物')
        if setup.get('support') not in ('chair','fixed_surface'):raise ValueError('请选择椅背或固定台面')
        if not isinstance(setup.get('foot_position',''),str) or len(setup.get('foot_position',''))>200:raise ValueError('脚位说明过长')
        self.abort(self.last_t or 0,'recalibration');self.setup=dict(support=setup['support'],foot_position=setup.get('foot_position',''),support_confirmed=True,assistance='both_hands',verification_source='user_confirmation')
        self.base=None;self.cal.clear();self.samples.clear();self.previous=None;self.rest_since=None;self.stage='hold_start_pose'

    def abort(self,t,reason):
        if self.active:
            self.attempts.append(dict(start_s=self.active['start_s'],end_s=t,cycle_completed=False,goal_met=False,evaluation_status='unable_to_evaluate' if 'unreliable' in reason or 'subject' in reason or 'side' in reason else 'incomplete',reason=reason))
        super().abort(t,reason)

    def process(self,t,m,width,height):
        old=self.last_t;gap=old is not None and t-old>.3
        if old is not None and t<=old:raise ValueError('时间戳必须递增')
        self.last_t=t;p=m.get('keypoints',{})
        valid=m.get('visible',False) and all(p.get(k,{}).get('confidence',0)>=.7 for k in ('shoulder','hip','knee','ankle'))
        valid=valid and all(0<=p[k]['x']<=width and 0<=p[k]['y']<=height for k in ('shoulder','hip','knee','ankle'))
        v=dict.fromkeys(('knee_included_deg','knee_flexion_deg','trunk_signed_deg','trunk_delta_deg','thigh_elevation_deg','thigh_delta_deg','hip_flexion_proxy_deg','hip_drop_shank_ratio','knee_velocity_deg_s','flexion_velocity_deg_s','joint_hold_s'))
        events=[]
        if gap or not valid:
            self.samples.clear();self.cal.clear();self.previous=None;self.rest_since=None;self.start_since=None
            if self.active:self.active.update(hold=None,entry=None,reverse=None,rise=None,bounce=None,rest=None,depth_since=None,hold_trunks=[],needs_review=True)
            self.lost=self.lost if self.lost is not None else (old if gap else t)
            if t-self.lost>=2:self.abort(t,'unreliable_detection');self.base=None;self.stage='hold_start_pose' if self.setup else 'confirm_support'
            events=self.emit(t,'SQUAT_OCCLUDED','暂时看不清，请调整手机位置。',True,.5)
            if not valid:return self.out(v,events,False)
        if self.lost is not None:self.gaps.append(dict(start_s=self.lost,end_s=t))
        self.lost=None;self.since.pop('SQUAT_OCCLUDED',None)
        h,s,k,a=(p[n] for n in ('hip','shoulder','knee','ankle'))
        f=180-m['value'];height_value=a['y']-h['y'];trunk=math.degrees(math.atan2(self.direction*(s['x']-h['x']),h['y']-s['y']))
        calf=math.hypot(k['x']-a['x'],k['y']-a['y'])
        thigh=math.degrees(math.atan2(h['y']-k['y'],self.direction*(k['x']-h['x'])))
        hip=angle((s['x'],s['y']),(h['x'],h['y']),(k['x'],k['y']))
        self.samples.append((t,f,height_value,trunk,calf,thigh))
        while self.samples and t-self.samples[0][0]>.15:self.samples.popleft()
        f,height_value,trunk,calf,thigh=(median(row[i] for row in self.samples) for i in (1,2,3,4,5))
        v.update(knee_included_deg=180-f,knee_flexion_deg=f,trunk_signed_deg=trunk,thigh_elevation_deg=thigh,hip_flexion_proxy_deg=None if hip is None else 180-hip)
        if self.setup is None:return self.out(v,[],False)
        if self.base is None:
            if not 0<=f<=10 or self.targets['target_deg']-f<20 or calf<1:
                self.cal.clear();self.stage='check_start_pose_and_direction';return self.out(v,[],True)
            self.stage='hold_start_pose';self.cal.append((t,f,height_value,trunk,calf,thigh))
            while self.cal and t-self.cal[0][0]>2.15:self.cal.popleft()
            if any(max(r[i] for r in self.cal)-min(r[i] for r in self.cal)>limit for i,limit in ((1,4),(2,calf*.02),(3,8))):
                self.cal.clear();return self.out(v,[],True)
            if len(self.cal)>=10 and t-self.cal[0][0]>=2:
                self.base=dict(flexion0=median(r[1] for r in self.cal),height0=median(r[2] for r in self.cal),trunk0=median(r[3] for r in self.cal),shank0=median(r[4] for r in self.cal),thigh0=median(r[5] for r in self.cal),captured_at_s=t,flexion_noise_deg=max(r[1] for r in self.cal)-min(r[1] for r in self.cal),height_noise_ratio=(max(r[2] for r in self.cal)-min(r[2] for r in self.cal))/calf)
                self.state='waiting_for_rest'
            else:return self.out(v,[],True)
        b=self.base;delta=f-b['flexion0'];drop=(b['height0']-height_value)/b['shank0'];td=wrap(trunk-b['trunk0'])
        v.update(hip_drop_shank_ratio=drop,trunk_delta_deg=td,thigh_delta_deg=wrap(thigh-b['thigh0']))
        if self.previous:
            speed=(f-self.previous[1])/(t-self.previous[0]);v.update(flexion_velocity_deg_s=speed,knee_velocity_deg_s=-speed)
        self.previous=(t,f)
        in_rest=abs(delta)<=5 and abs(drop)<=.03 and abs(td)<=10
        if self.state=='waiting_for_rest':
            self.rest_since=(t if self.rest_since is None else self.rest_since) if in_rest else None
            if self.rest_since is not None and t-self.rest_since>=.5:self.state='rest';self.stage='ready'
        if self.state=='rest':
            self.start_since=(t if self.start_since is None else self.start_since) if delta>=8 and drop>=.02 else None
            if self.start_since is not None and t-self.start_since>=.2:
                self.active=dict(start_s=self.start_since,peak=f,peak_t=t,first_peak_t=None,drop_peak=drop,forward=trunk,entry=None,hold=None,max_hold=0.,target_time=None,reverse=None,rise=None,minimum=f,bounce=None,rest=None,needs_review=False,depth_since=None,depth_latched=False,depth_count=0,range_ok=True,hold_trunks=[],best_range=None)
                self.state='extending'
        r=self.active
        if r:
            if t-r['start_s']>=30:
                self.abort(t,'attempt_timeout');self.base=None;self.cal.clear();self.stage='hold_start_pose'
                return self.out(v,self.emit(t,'SQUAT_TIMEOUT','本次30秒内未完成，请暂停并重新准备。'),True)
            if f>r['peak']:r['peak']=f;r['peak_t']=t
            r['drop_peak']=max(r['drop_peak'],drop);r['forward']=max(r['forward'],trunk)
            target=self.targets['target_deg']
            if f>target+8:
                if r['depth_since'] is None:r['depth_since']=t
                if t-r['depth_since']>=.3 and not r['depth_latched']:
                    r['range_ok']=False;r['depth_latched']=True;r['depth_count']+=1
                    events+=self.emit(t,'SQUAT_DEPTH_EXCEEDED','已超过本次设定范围，慢慢站回。')
            else:r['depth_since']=None;r['depth_latched']=False
            if r['hold'] is not None and (abs(f-target)>8 or drop<.02):r['hold']=None;r['entry']=None;r['hold_trunks']=[]
            if r['hold'] is None:
                if abs(f-target)<=5 and drop>=.03:
                    if r['entry'] is None:r['entry']=t;r['hold_trunks']=[]
                    r['hold_trunks'].append(trunk)
                    if t-r['entry']>=.2:
                        r['hold']=r['entry']
                        if r['target_time'] is None:r['target_time']=r['entry']
                else:r['entry']=None;r['hold_trunks']=[]
            if r['hold'] is not None:
                r['hold_trunks'].append(trunk);held=t-r['hold'];v['joint_hold_s']=held
                if held>=r['max_hold']:
                    r['max_hold']=held;r['best_range']=percentile(r['hold_trunks'],.95)-percentile(r['hold_trunks'],.05) if held>=1 else None
            else:v['joint_hold_s']=0
            if r['rise'] is None:
                cond=r['peak']-f>=5;r['reverse']=(t if r['reverse'] is None else r['reverse']) if cond else None
                if r['reverse'] is not None and t-r['reverse']>=.2:
                    r['rise']=r['reverse'];r['minimum']=f
                    if r['first_peak_t'] is None:r['first_peak_t']=r['peak_t']
            else:
                r['minimum']=min(r['minimum'],f);cond=f-r['minimum']>=5
                r['bounce']=(t if r['bounce'] is None else r['bounce']) if cond else None
                if r['bounce'] is not None and t-r['bounce']>=.2:r['rise']=None;r['reverse']=None;r['rest']=None;r['bounce']=None
            self.state='returning' if r['rise'] is not None else 'holding' if r['hold'] is not None else 'extending'
            if in_rest and r['rise'] is not None:
                if r['rest'] is None:r['rest']=t
                if t-r['rest']>=.5:
                    row=self.complete(r,r['rest'])
                    if row['time_to_target_s'] is not None and row['time_to_target_s']<1:events+=self.emit(t,'EXTENSION_TOO_FAST','下一次慢慢下蹲。')
                    if row['rise_s']<self.targets['return_s']:events+=self.emit(t,'RETURN_TOO_FAST','下一次慢慢站起。')
                    if row['trunk_hold_range_deg'] is not None and row['trunk_hold_range_deg']>10:events+=self.emit(t,'SQUAT_HOLD_SWAY','下一次放慢动作，保持肩背姿势平稳。')
                    self.active=None;self.start_since=None;self.state='rest'
            else:r['rest']=None
        return self.out(v,events,True)

    def complete(self,r,end):
        excursion=r['peak']-self.base['flexion0'];complete=excursion>=15 and r['drop_peak']>=.03 and not r['needs_review'];reached=r['target_time'] is not None
        hold=r['max_hold']>=self.targets['hold_s'];goal=complete and reached and hold and r['range_ok']
        tt=None if not reached else r['target_time']-r['start_s'];pt=None if r['first_peak_t'] is None else r['first_peak_t']-r['start_s']
        row=dict(exercise_id='supported_mini_squat',rule_version='squat_v0.1_joint',start_s=r['start_s'],end_s=end,cycle_duration_s=end-r['start_s'],knee_flexion_peak_deg=r['peak'],knee_flexion_excursion_deg=excursion,hip_drop_peak=r['drop_peak'],trunk_forward_peak_deg=r['forward'],trunk_hold_range_deg=r['best_range'],depth_exceeded=r['depth_count']>0,depth_exceeded_count=r['depth_count'],range_control_met=r['range_ok'],target_reached=reached,cycle_completed=complete,goal_met=goal,target_completed=goal,evaluation_status='unable_to_evaluate' if r['needs_review'] else 'complete' if complete else 'incomplete',descent_to_first_peak_s=pt,time_to_target_s=tt,target_hold_s=r['max_hold'],rise_s=end-r['rise'],return_s=end-r['rise'],needs_review=r['needs_review'],setup=self.setup,baseline=self.base,targets=self.targets,pause_mode='no_pause' if self.targets['hold_s']==0 else 'pause',heel_contact_verified='unknown',support_load_verified='unknown')
        self.attempts.append(row)
        if complete:self.reps.append(dict(row,index=len(self.reps)+1,rep_id=len(self.reps)+1,exercise='SUPPORTED_MINI_SQUAT',movement_to_first_peak_s=pt,target_comparison=dict(amplitude_met=reached,hold_met=hold,extension_time_met=None if tt is None else tt>=1,return_time_met=row['rise_s']>=self.targets['return_s'])))
        return row

    def out(self,v,events,valid):
        return dict(measurement_metrics=v,calibration=dict(status=self.stage,progress=min(1,(self.last_t-self.cal[0][0])/2) if self.cal else 0,baseline=self.base,rule_version='squat_v0.1_joint',setup=self.setup),feedback_events=events),self.snapshot(valid)
