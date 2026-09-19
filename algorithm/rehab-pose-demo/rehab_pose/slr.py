"""Side-view SLR candidate rules from the supplied v0.1 document; not diagnosis."""
import math
from collections import deque
from statistics import median
from types import SimpleNamespace


def wrap(a):
    return (a + 180) % 360 - 180


class SupineAnalyzer:
    def __init__(self, targets=None):
        self.targets = targets or dict(target_deg=30, hold_s=5, return_s=1, rest_s=30)
        self.config = SimpleNamespace(min_hold_s=self.targets['hold_s'])
        self.engine = self
        self.reps = []; self.interrupted = []; self.last_t = None
        self.surface = None; self.base = None; self.active = None
        self.state = 'waiting_for_rest'; self.samples = deque(); self.cal = deque()
        self.since = {}; self.sent = {}; self.lost = None; self.previous = None
        self.start_since = None; self.trunk_latched = False

    def set_surface(self, points):
        if not isinstance(points, list) or len(points) != 2:
            raise ValueError('请选择床面上朝脚方向的两个点')
        if any(len(p) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p) for p in points):
            raise ValueError('参考线坐标无效')
        if math.dist(*points) < .1: raise ValueError('参考线太短，请选择相距更远的两个点')
        self.abort(self.last_t or 0, 'surface_changed')
        self.surface = points; self.base = None; self.cal.clear(); self.samples.clear(); self.previous=None; self.since.clear(); self.trunk_latched=False

    def abort(self, t, reason):
        if self.active: self.interrupted.append(dict(start_s=self.active['start_s'], end_s=t, reason=reason))
        self.active = None; self.start_since = None; self.state = 'waiting_for_rest'

    def finish(self):
        self.abort(self.last_t or 0, 'unfinished')

    def update(self, t, angle=None, valid=False):
        self.last_t = t
        return self.snapshot(False)

    def snapshot(self, valid):
        return dict(phase=self.state, completed_reps=len(self.reps), detection_status='reliable' if valid else 'unreliable')

    def emit(self, t, code, message, condition=True, dwell=0):
        if not condition:
            self.since.pop(code, None); return []
        self.since.setdefault(code, t)
        if t-self.since[code]+1e-8 < dwell or t-self.sent.get(code,-100) < 5: return []
        self.sent[code] = t
        return [dict(timestamp_s=t, code=code, message=message, level='notice')]

    def process(self, t, m, width, height):
        self.frame_size = (width,height)
        gap = self.last_t is not None and t-self.last_t > .3
        if self.last_t is not None and t <= self.last_t: raise ValueError('时间戳必须递增')
        previous_t = self.last_t; self.last_t = t
        p = m.get('keypoints', {})
        valid = bool(m.get('visible')) and all(p.get(k,{}).get('confidence',0) >= .7 for k in ('shoulder','hip','knee','ankle'))
        values = dict.fromkeys(('knee_included_deg','knee_flexion_deg','slr_thigh_surface_deg','slr_raise_delta_deg','slr_trunk_delta_deg','knee_bend_delta_deg','raise_velocity_deg_s','leg_raise_delta_deg','leg_raise_velocity_deg_s','joint_hold_s'))
        events = []; status = 'ready'; progress = 0
        if not valid or gap:
            self.samples.clear(); self.cal.clear(); self.previous = None; self.start_since = None
            if self.active:
                self.active.update(hold=None, entry=None, reversal=None, reverse_start=None, rest=None, bend_since=None, needs_review=True)
            self.lost = self.lost if self.lost is not None else (previous_t if gap else t)
            if t-self.lost >= 2:
                self.abort(t,'unreliable_detection'); self.base = None
            events = self.emit(t,'SLR_OCCLUDED','暂时看不清训练腿，请调整手机位置。',True,.5)
            status = 'waiting_for_points'
            if not valid: return self.output(values,status,progress,events,False)
        if valid:
            self.lost = None; self.since.pop('SLR_OCCLUDED',None)
        if self.surface is None: return self.output(values,'select_surface',0,[],False)
        a,b = self.surface
        dx=(b[0]-a[0])*width; dy=-(b[1]-a[1])*height
        ref=math.degrees(math.atan2(dy,dx)); sign=1 if dx>=0 else -1
        h,k,s=p['hip'],p['knee'],p['shoulder']
        angle=sign*wrap(math.degrees(math.atan2(h['y']-k['y'],k['x']-h['x']))-ref)
        trunk=math.degrees(math.atan2(s['y']-h['y'],h['x']-s['x']))
        f=180-m['value']
        self.samples.append((t,angle,f,trunk))
        while self.samples and t-self.samples[0][0]>.15:self.samples.popleft()
        angle,f,trunk=(median(row[i] for row in self.samples) for i in (1,2,3))
        values.update(knee_included_deg=180-f,knee_flexion_deg=f,slr_thigh_surface_deg=angle)
        if self.base is None:
            if f>10 or abs(angle)>10 or self.targets['target_deg']-angle<20:
                self.cal.clear();return self.output(values,'check_start_pose_and_direction',0,[],True)
            self.cal.append((t,angle,f,trunk))
            while self.cal and t-self.cal[0][0]>2.15:self.cal.popleft()
            if any(max(r[i] for r in self.cal)-min(r[i] for r in self.cal)>6 for i in (1,2,3)):
                self.cal.clear();return self.output(values,'hold_start_pose',0,[],True)
            progress=min(1,(t-self.cal[0][0])/2)
            if progress<1 or len(self.cal)<10:return self.output(values,'hold_start_pose',progress,[],True)
            self.base=dict(alpha0=median(r[1] for r in self.cal),flexion0=median(r[2] for r in self.cal),trunk0=median(r[3] for r in self.cal),captured_at_s=t)
            self.state='rest'
        delta=angle-self.base['alpha0']; td=wrap(trunk-self.base['trunk0'])
        velocity=None if self.previous is None else (angle-self.previous[1])/(t-self.previous[0])
        self.previous=(t,angle)
        values.update(slr_raise_delta_deg=delta,leg_raise_delta_deg=delta,slr_trunk_delta_deg=td,knee_bend_delta_deg=f-self.base['flexion0'],raise_velocity_deg_s=velocity,leg_raise_velocity_deg_s=velocity)
        if self.state=='waiting_for_rest':
            if abs(delta)<=5:self.state='rest'
        if self.state=='rest':
            self.start_since=(self.start_since if self.start_since is not None else t) if delta>=8 else None
            if self.start_since is not None and t-self.start_since+1e-8>=.2:
                self.active=dict(start_s=self.start_since,peak=angle,peak_t=t,first_peak=None,first_peak_t=None,hold=None,entry=None,max_hold=0.,target_time=None,reverse_start=None,reversal=None,return_min=None,rest=None,max_f=f,max_bend=f-self.base['flexion0'],bend_since=None,bend_latched=False,bend_count=0,knee_ok=True,needs_review=False)
                self.state='extending'
        r=self.active
        if r:
            if t-r['start_s']>=30:
                self.abort(t,'attempt_timeout');self.base=None;self.cal.clear()
                events+=self.emit(t,'SLR_TIMEOUT','本次30秒内未完成，请暂停并重新准备。')
                return self.output(values,'hold_start_pose',0,events,True)
            if angle>r['peak']:r['peak']=angle;r['peak_t']=t
            r['max_f']=max(r['max_f'],f);r['max_bend']=max(r['max_bend'],f-self.base['flexion0'])
            if f>15:
                if r['bend_since'] is None:r['bend_since']=t
                if t-r['bend_since']+1e-8>=.3 and not r['bend_latched']:
                    r['bend_latched']=True;r['bend_count']+=1;r['knee_ok']=False
                    events+=self.emit(t,'SLR_KNEE_BENT','先放下休息，下一次先让膝盖保持伸直，再慢慢抬腿。')
            else:r['bend_since']=None;r['bend_latched']=False
            target=self.targets['target_deg']
            if r['hold'] is not None and (abs(angle-target)>8 or f>15):r['hold']=None;r['entry']=None
            if r['hold'] is None:
                if abs(angle-target)<=5 and f<=10:
                    if r['entry'] is None:r['entry']=t
                    if t-r['entry']+1e-8>=.2:
                        r['hold']=r['entry']
                        if r['target_time'] is None:r['target_time']=r['entry']
                else:r['entry']=None
            if r['hold'] is not None:
                r['max_hold']=max(r['max_hold'],t-r['hold']);values['joint_hold_s']=t-r['hold']
            else:values['joint_hold_s']=0
            events+=self.emit(t,'SLR_RANGE','试着回到设定范围。',r['target_time'] is not None and abs(angle-target)>8,.5)
            if abs(td)>10:self.trunk_latched=True
            elif abs(td)<=5:self.trunk_latched=False
            events+=self.emit(t,'SLR_TRUNK_MOVED','让肩背保持起始姿势，慢慢抬腿。',self.trunk_latched,.5)
            if r['reverse_start'] is None:
                if r['peak']-angle>=5:
                    if r['reversal'] is None:r['reversal']=t
                    if t-r['reversal']+1e-8>=.2:
                        r['reverse_start']=r['reversal'];r['return_min']=angle
                        if r['first_peak'] is None:r['first_peak']=r['peak'];r['first_peak_t']=r['peak_t']
                else:r['reversal']=None
            else:
                r['return_min']=min(r['return_min'],angle)
                if angle-r['return_min']>=5:r['reverse_start']=None;r['reversal']=None;r['rest']=None
            self.state='returning' if r['reverse_start'] is not None else 'holding' if r['hold'] is not None else 'extending'
            if r['reverse_start'] is not None and abs(delta)<=5:
                if r['rest'] is None:r['rest']=t
                if t-r['rest']+1e-8>=.5:
                    if r['peak']-self.base['alpha0']>=15:
                        self.complete(r,r['rest'])
                        rep=self.reps[-1]
                        if rep['time_to_target_s'] is not None and rep['time_to_target_s']<1:events+=self.emit(t,'EXTENSION_TOO_FAST','下一次慢慢抬起。')
                        if rep['return_s']<self.targets['return_s']:events+=self.emit(t,'RETURN_TOO_FAST','下一次慢慢放下。')
                    self.active=None;self.start_since=None;self.state='rest'
            else:r['rest']=None
        return self.output(values,'ready',1,events,True)

    def complete(self,r,end):
        joint=r['target_time'] is not None; hold=r['max_hold']>=self.targets['hold_s']-1e-8
        met=joint and hold and r['knee_ok'] and not r['needs_review']
        tt=None if not joint else r['target_time']-r['start_s']
        rt=end-r['reverse_start'];pt=None if r['first_peak_t'] is None else r['first_peak_t']-r['start_s']
        self.reps.append(dict(index=len(self.reps)+1,exercise='SUPINE_STRAIGHT_LEG_RAISE',exercise_id='supine_straight_leg_raise',rule_version='slr_v0.1_surface',start_s=r['start_s'],end_s=end,cycle_duration_s=end-r['start_s'],raise_peak_deg=r['peak'],raise_excursion_deg=r['peak']-self.base['alpha0'],max_motion_delta_deg=r['peak']-self.base['alpha0'],knee_flexion_max_deg=r['max_f'],knee_bend_delta_deg=r['max_bend'],knee_control_met=r['knee_ok'],bend_event_count=r['bend_count'],joint_target_reached=joint,target_hold_s=r['max_hold'],raise_to_first_peak_s=pt,movement_to_first_peak_s=pt,time_to_target_s=tt,return_s=rt,needs_review=r['needs_review'],target_completed=met,reference_frame='supine_surface',surface_points=self.surface,reference_line_angle_deg=math.degrees(math.atan2(-(self.surface[1][1]-self.surface[0][1])*self.frame_size[1],(self.surface[1][0]-self.surface[0][0])*self.frame_size[0])),baseline=dict(self.base),targets=dict(self.targets),target_comparison=dict(amplitude_met=joint,hold_met=hold,extension_time_met=None if tt is None else tt>=1,return_time_met=rt>=self.targets['return_s'])))

    def output(self,values,status,progress,events,valid):
        return dict(measurement_metrics=values,calibration=dict(status=status,progress=progress,baseline=self.base,reference_frame='supine_surface',surface_points=self.surface,rule_version='slr_v0.1_surface',filter='causal_median_0.15s'),feedback_events=events[:1]),self.snapshot(valid)
