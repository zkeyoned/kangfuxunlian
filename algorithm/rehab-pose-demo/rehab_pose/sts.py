"""Candidate sit-to-stand rules. Height progress is not force or seat contact."""
import math
from collections import deque
from statistics import median
from types import SimpleNamespace
from .slr import SupineAnalyzer, wrap


class SitStandAnalyzer(SupineAnalyzer):
    def __init__(self, targets=None):
        super().__init__(targets or dict(target_deg=165,hold_s=1,return_s=1,rest_s=30))
        self.sit=None;self.stand=None;self.pending_stand=None;self.stage='need_sit'
        self.direction=1;self.attempts=[];self.setup={};self.rest_since=None;self.gaps=[]

    def calibrate(self,stage,setup=None):
        if stage not in ('sit','stand','confirm'):raise ValueError('标定阶段无效')
        if stage=='sit':
            setup=setup or {}
            if setup.get('assistance') not in ('none','thighs','armrests'):raise ValueError('请选择辅助方式')
            height=setup.get('seat_height_cm')
            if height is not None and (type(height) not in (int,float) or not math.isfinite(height) or not 10<=height<=100):raise ValueError('座高应为10–100厘米或留空')
            if not isinstance(setup.get('foot_position',''),str) or len(setup.get('foot_position',''))>200:raise ValueError('脚位描述过长')
            self.setup=dict(assistance=setup['assistance'],seat_height_cm=height,cushion=bool(setup.get('cushion')),foot_position=setup.get('foot_position',''))
            self.abort(self.last_t or 0,'recalibration');self.sit=None;self.stand=None;self.pending_stand=None;self.stage='capture_sit'
        elif stage=='stand':
            if self.sit is None:raise ValueError('请先标定坐姿')
            self.stage='capture_stand'
        else:
            if self.pending_stand is None:raise ValueError('请先保持舒适站姿2秒')
            self.stand=self.pending_stand;self.stage='return_to_sit';self.state='waiting_for_rest'
        self.cal.clear();self.samples.clear();self.previous=None;self.rest_since=None

    def abort(self,t,reason):
        if self.active:
            self.attempts.append(dict(start_s=self.active['start_s'],end_s=t,standing_reached=self.active['standing_time'] is not None,cycle_completed=False,goal_met=False,evaluation_status='unable_to_evaluate' if 'unreliable' in reason or 'subject' in reason else 'incomplete',reason=reason))
        super().abort(t,reason)

    def process(self,t,m,width,height):
        old=self.last_t;gap=old is not None and t-old>.3
        if old is not None and t<=old:raise ValueError('时间戳必须递增')
        self.last_t=t;p=m.get('keypoints',{})
        valid=m.get('visible',False) and all(p.get(k,{}).get('confidence',0)>=.7 for k in ('shoulder','hip','knee','ankle'))
        valid=valid and all(0<=p[k]['x']<=width and 0<=p[k]['y']<=height for k in ('shoulder','hip','knee','ankle'))
        v=dict.fromkeys(('knee_included_deg','knee_flexion_deg','trunk_signed_deg','trunk_delta_deg','trunk_stand_delta_deg','hip_rise_progress','hip_rise_velocity_s','knee_velocity_deg_s','joint_hold_s'))
        events=[]
        if gap or not valid:
            self.samples.clear();self.cal.clear();self.previous=None;self.rest_since=None;self.start_since=None
            if self.active:
                self.active.update(hold=None,entry=None,reverse=None,descent=None,bounce=None,rest=None,needs_review=True)
            self.lost=self.lost if self.lost is not None else (old if gap else t)
            if t-self.lost>=2:
                self.abort(t,'unreliable_detection');self.stage='need_sit';self.sit=None;self.stand=None
            events=self.emit(t,'STS_OCCLUDED','暂时看不清，请调整手机位置。',True,.5)
            if not valid:return self.out(v,events,False)
        if self.lost is not None:self.gaps.append(dict(start_s=self.lost,end_s=t))
        self.lost=None;self.since.pop('STS_OCCLUDED',None)
        h,s,k,a=(p[n] for n in ('hip','shoulder','knee','ankle'))
        knee=m['value'];height_value=a['y']-h['y'];trunk=math.degrees(math.atan2(self.direction*(s['x']-h['x']),h['y']-s['y']))
        calf=math.hypot(k['x']-a['x'],k['y']-a['y'])
        self.samples.append((t,knee,height_value,trunk,calf))
        while self.samples and t-self.samples[0][0]>.15:self.samples.popleft()
        knee,height_value,trunk,calf=(median(row[i] for row in self.samples) for i in (1,2,3,4))
        v.update(knee_included_deg=knee,knee_flexion_deg=180-knee,trunk_signed_deg=trunk)
        if self.stage in ('capture_sit','capture_stand'):
            suitable=55<=knee<=130 if self.stage=='capture_sit' else knee>=165
            if not suitable:self.cal.clear();return self.out(v,[],True)
            self.cal.append((t,knee,height_value,trunk,calf))
            while self.cal and t-self.cal[0][0]>2.15:self.cal.popleft()
            if any(max(r[i] for r in self.cal)-min(r[i] for r in self.cal)>limit for i,limit in ((1,6),(2,max(calf*.05,2)),(3,6))):
                self.cal.clear();return self.out(v,[],True)
            if len(self.cal)>=10 and t-self.cal[0][0]>=2:
                base=dict(knee=median(r[1] for r in self.cal),height=median(r[2] for r in self.cal),trunk=median(r[3] for r in self.cal),calf=calf)
                if self.stage=='capture_sit':self.sit=base;self.stage='need_stand'
                elif base['height']-self.sit['height']>=self.sit['calf']*.25:self.pending_stand=base;self.stage='confirm_stand'
                else:self.cal.clear()
            return self.out(v,[],True)
        if self.sit is None or self.stand is None:return self.out(v,[],True)
        progress=(height_value-self.sit['height'])/(self.stand['height']-self.sit['height']);d=wrap(trunk-self.stand['trunk'])
        v.update(hip_rise_progress=progress,trunk_delta_deg=wrap(trunk-self.sit['trunk']),trunk_stand_delta_deg=d)
        if self.previous:
            dt=t-self.previous[0];v['hip_rise_velocity_s']=(progress-self.previous[1])/dt;v['knee_velocity_deg_s']=(knee-self.previous[2])/dt
        self.previous=(t,progress,knee)
        in_rest=abs(progress)<=.1 and abs(knee-self.sit['knee'])<=15
        if self.state=='waiting_for_rest':
            self.rest_since=(t if self.rest_since is None else self.rest_since) if in_rest else None
            if self.rest_since is not None and t-self.rest_since>=.5:self.state='rest';self.stage='ready'
        if self.state=='rest':
            self.start_since=(t if self.start_since is None else self.start_since) if progress>=.1 and knee-self.sit['knee']>=10 else None
            if self.start_since is not None and t-self.start_since>=.2:
                self.active=dict(start_s=self.start_since,pmax=progress,kmax=knee,forward=trunk,entry=None,hold=None,max_hold=0.,standing_time=None,stand_knees=[],stand_knee=None,reverse=None,descent=None,pmin=progress,kmin=knee,bounce=None,rest=None,needs_review=False,sway=[],best_sway=None)
                self.state='extending'
        r=self.active
        if r:
            if t-r['start_s']>=30:
                self.abort(t,'attempt_timeout');events+=self.emit(t,'STS_TIMEOUT','本次30秒内未完成，请暂停并重新准备。');return self.out(v,events,True)
            r['pmax']=max(r['pmax'],progress);r['kmax']=max(r['kmax'],knee)
            if r['standing_time'] is None:r['forward']=max(r['forward'],trunk)
            enter=knee>=self.targets['target_deg'] and progress>=.9 and abs(d)<=10
            keep=knee>=self.targets['target_deg']-5 and progress>=.85 and abs(d)<=15
            if r['hold'] is not None and not keep:r['hold']=None;r['entry']=None;r['sway']=[]
            if r['hold'] is None:
                if enter:
                    if r['entry'] is None:r['entry']=t;r['stand_knees']=[]
                    r['stand_knees'].append(knee)
                    if t-r['entry']>=.3:
                        r['hold']=r['entry']
                        if r['standing_time'] is None:r['standing_time']=r['entry'];r['stand_knee']=median(r['stand_knees'])
                else:r['entry']=None
            if r['hold'] is not None:
                r['max_hold']=max(r['max_hold'],t-r['hold']);v['joint_hold_s']=t-r['hold'];r['sway'].append((t,progress,trunk))
                if r['sway'][-1][0]-r['sway'][0][0]>=1:
                    r['best_sway']=dict(progress_range=max(x[1] for x in r['sway'])-min(x[1] for x in r['sway']),trunk_range_deg=max(x[2] for x in r['sway'])-min(x[2] for x in r['sway']))
            else:v['joint_hold_s']=0
            if abs(d)>15:self.trunk_latched=True
            elif abs(d)<=10:self.trunk_latched=False
            events+=self.emit(t,'STS_STAND_POSTURE','站稳后，回到舒适的直立姿势。',r['standing_time'] is not None and self.trunk_latched,.5)
            if r['descent'] is None:
                cond=r['pmax']-progress>=.1 and r['kmax']-knee>=10
                r['reverse']=(t if r['reverse'] is None else r['reverse']) if cond else None
                if r['reverse'] is not None and t-r['reverse']>=.2:r['descent']=r['reverse'];r['pmin']=progress;r['kmin']=knee
            else:
                r['pmin']=min(r['pmin'],progress);r['kmin']=min(r['kmin'],knee)
                cond=progress-r['pmin']>=.1 and knee-r['kmin']>=10
                r['bounce']=(t if r['bounce'] is None else r['bounce']) if cond else None
                if r['bounce'] is not None and t-r['bounce']>=.2:r['descent']=None;r['reverse']=None;r['rest']=None
            self.state='returning' if r['descent'] is not None else 'holding' if r['hold'] is not None else 'extending'
            if in_rest and r['descent'] is not None:
                if r['rest'] is None:r['rest']=t
                if t-r['rest']>=.5:
                    self.complete(r,r['rest'])
                    if r['standing_time'] is None:events+=self.emit(t,'STS_INCOMPLETE','这次未确认完全站起；请在舒适范围内完成。')
                    elif r['rest']-r['descent']<1:events+=self.emit(t,'RETURN_TOO_FAST','下一次试着慢一点坐回。')
                    self.active=None;self.start_since=None;self.state='rest'
            else:r['rest']=None
        return self.out(v,events,True)

    def complete(self,r,end):
        reached=r['standing_time'] is not None;complete=reached and not r['needs_review'];goal=complete and r['max_hold']>=self.targets['hold_s']
        row=dict(exercise_id='sit_to_stand',rule_version='sts_v0.1_dual_baseline',start_s=r['start_s'],end_s=end,cycle_duration_s=end-r['start_s'],standing_reached=reached,cycle_completed=complete,goal_met=goal,target_completed=goal,evaluation_status='unable_to_evaluate' if r['needs_review'] else 'complete' if complete else 'incomplete',rise_to_stand_s=None if not reached else r['standing_time']-r['start_s'],sit_down_s=end-r['descent'],return_s=end-r['descent'],target_hold_s=r['max_hold'],stand_knee_deg=r['stand_knee'],hip_rise_peak=r['pmax'],trunk_forward_peak_deg=r['forward'],stand_sway_range=None if r['needs_review'] else r['best_sway'],seat_contact_verified='unknown',setup=dict(self.setup),baselines=dict(sit=self.sit,stand=self.stand),targets=dict(self.targets),needs_review=r['needs_review'])
        self.attempts.append(row)
        if complete:
            rep=dict(row,index=len(self.reps)+1,exercise='SIT_TO_STAND',movement_to_first_peak_s=row['rise_to_stand_s'],target_comparison=dict(amplitude_met=True,hold_met=goal,extension_time_met=None,return_time_met=row['sit_down_s']>=self.targets['return_s']))
            self.reps.append(rep)

    def out(self,v,events,valid):
        self.base=dict(sit=self.sit,stand=self.stand) if self.sit and self.stand else None
        return dict(measurement_metrics=v,calibration=dict(status=self.stage,progress=min(1,(self.last_t-self.cal[0][0])/2) if self.cal else 0,baseline=self.base,rule_version='sts_v0.1_dual_baseline',setup=self.setup),feedback_events=events[:1]),self.snapshot(valid)
