"""Signed image-plane metrics, stable reference capture and debounced demo feedback."""
from collections import deque
from dataclasses import dataclass,asdict
import math
from statistics import median
from .core import angle


@dataclass
class MeasureConfig:
    calibration_s: float=2.
    stable_angle_span_deg: float=6.
    stable_position_diagonal: float=.04
    velocity_window_s: float=.2
    max_sample_gap_s: float=.3
    invalidate_after_s: float=2.
    feedback_dwell_s: float=.3
    feedback_cooldown_s: float=3.
    trunk_delta_limit_deg: float=15.
    thigh_delta_limit_deg: float=15.
    speed_limit_deg_s: float=180.
    speed_dwell_s: float=.08

    def __post_init__(self):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in asdict(self).values()):
            raise ValueError('Measurement parameters must be positive finite numbers')


def difference(a,b):
    return (a-b+180)%360-180


class MotionMeasures:
    def __init__(self,facing='left',config=None,min_confidence=.3,exercise='1'):
        if facing not in ('left','right'):raise ValueError('Choose on-screen facing direction')
        self.direction=-1 if facing=='left' else 1
        self.config=config or MeasureConfig();self.confidence=min_confidence;self.exercise=exercise
        self.last_t=None;self.reset()

    def reset(self):
        self.samples=deque();self.speeds=deque();self.baseline=None
        self.since={};self.sent={};self.latched={};self.last_seen=None

    def update(self,t,m,width,height,phase='waiting_for_rest'):
        if not math.isfinite(t) or (self.last_t is not None and t<=self.last_t):raise ValueError('Measurement timestamps must increase')
        if self.last_t is not None and t-self.last_t>self.config.max_sample_gap_s:
            self.samples.clear();self.speeds.clear();self.since.clear()
        self.last_t=t;c=self.config
        keys=('knee_included_deg','knee_flexion_deg','trunk_signed_deg','trunk_delta_deg',
              'thigh_elevation_deg','thigh_delta_deg','hip_flexion_proxy_deg','knee_velocity_deg_s')
        values=dict.fromkeys(keys)
        if not m['visible']:
            self.samples.clear();self.speeds.clear();self.since.clear()
            if self.last_seen is not None and t-self.last_seen>c.invalidate_after_s:self.baseline=None
            return self._out(values,'waiting_for_points',0.,[])
        if self.last_seen is not None and t-self.last_seen>c.invalidate_after_s:self.baseline=None
        self.last_seen=t
        p=m['keypoints'];hip=p['hip'];knee=p['knee'];shoulder=p.get('shoulder')
        values['knee_included_deg']=m['value'];values['knee_flexion_deg']=180-m['value']
        values['thigh_elevation_deg']=math.degrees(math.atan2(hip['y']-knee['y'],self.direction*(knee['x']-hip['x'])))
        if shoulder and shoulder['confidence']>=self.confidence:
            s=(shoulder['x'],shoulder['y']);h=(hip['x'],hip['y']);k=(knee['x'],knee['y'])
            if math.dist(s,h)>1:
                values['trunk_signed_deg']=math.degrees(math.atan2(self.direction*(s[0]-h[0]),h[1]-s[1]))
                hipangle=angle(s,h,k)
                values['hip_flexion_proxy_deg']=None if hipangle is None else 180-hipangle
        self.speeds.append((t,m['value']))
        while self.speeds and t-self.speeds[0][0]>c.velocity_window_s:self.speeds.popleft()
        if len(self.speeds)>=3 and t-self.speeds[0][0]>=.08:
            mt=sum(x for x,y in self.speeds)/len(self.speeds);my=sum(y for x,y in self.speeds)/len(self.speeds)
            den=sum((x-mt)**2 for x,y in self.speeds)
            if den>0:values['knee_velocity_deg_s']=sum((x-mt)*(y-my) for x,y in self.speeds)/den
        status='ready';progress=1.
        if self.baseline is None:
            knee_angle=values['knee_included_deg'];thigh=values['thigh_elevation_deg'];trunk=values['trunk_signed_deg']
            seated_limit=130 if self.exercise=='1' else 115
            suitable=(55<=knee_angle<=seated_limit and abs(thigh)<35) if self.exercise in ('1','8') else (
                knee_angle>=150 and trunk is not None and abs(trunk)>=55 and values['hip_flexion_proxy_deg']<=35
                if self.exercise=='2' else knee_angle>=150 and trunk is not None and abs(trunk)<35)
            if not suitable:
                self.samples.clear();return self._out(values,'check_start_pose_and_direction',0.,[])
            # Stability is checked against the entire contiguous reference window.
            self.samples.append((t,dict(values),hip['x'],hip['y']))
            while self.samples and t-self.samples[0][0]>c.calibration_s+.1:self.samples.popleft()
            unstable=False
            for metric in ('knee_included_deg','thigh_elevation_deg','trunk_signed_deg'):
                vs=[v[metric] for _,v,_,_ in self.samples if v[metric] is not None]
                if vs:
                    ordered=sorted(vs);trim=len(vs)//10
                    robust=ordered[trim:len(vs)-trim] if trim else ordered
                    if max(robust)-min(robust)>c.stable_angle_span_deg:unstable=True
            diag=math.hypot(width,height)
            if any(math.hypot(x-hip['x'],y-hip['y'])>diag*c.stable_position_diagonal for _,_,x,y in self.samples):unstable=True
            if unstable:
                # Slide one observation instead of throwing away all stable history.
                if len(self.samples)>1:self.samples.popleft()
            progress=min(1.,(t-self.samples[0][0])/c.calibration_s)
            status='hold_start_pose'
            if progress>=1 and len(self.samples)>=10 and not unstable:
                self.baseline={}
                for metric in ('knee_included_deg','thigh_elevation_deg','trunk_signed_deg','hip_flexion_proxy_deg'):
                    vs=[v[metric] for _,v,_,_ in self.samples if v[metric] is not None]
                    self.baseline[metric]=median(vs) if len(vs)==len(self.samples) else None
                self.baseline['captured_at_s']=t;status='ready'
        alerts=[]
        if self.baseline:
            for source,dest in (('trunk_signed_deg','trunk_delta_deg'),('thigh_elevation_deg','thigh_delta_deg')):
                a=values[source];b=self.baseline[source]
                if a is not None and b is not None:values[dest]=difference(a,b)
            checks={}
            if self.exercise=='1':
                trunk=values['trunk_delta_deg'];thigh=values['thigh_delta_deg']
                def latch(code,trigger,clear):
                    if self.latched.get(code):
                        if clear:self.latched[code]=False
                    elif trigger:self.latched[code]=True
                    return self.latched.get(code,False)
                checks={
                    'TRUNK_FORWARD':(latch('TRUNK_FORWARD',trunk is not None and trunk>c.trunk_delta_limit_deg,
                                           trunk is None or trunk<=10),'身体前倾超出设置范围'),
                    'TRUNK_BACKWARD':(latch('TRUNK_BACKWARD',trunk is not None and trunk<-c.trunk_delta_limit_deg,
                                            trunk is None or trunk>=-10),'身体后仰超出设置范围'),
                    'THIGH_MOVEMENT':(latch('THIGH_MOVEMENT',thigh is not None and abs(thigh)>c.thigh_delta_limit_deg,
                                           thigh is None or abs(thigh)<=5),'大腿位置变化超出设置范围')}
            for code in list(self.since):
                if code not in checks or not checks[code][0]:self.since.pop(code,None)
            emitted=False
            for code,(condition,message) in checks.items():
                if condition:
                    self.since.setdefault(code,t)
                    dwell=c.speed_dwell_s if code=='KNEE_TOO_FAST' else c.feedback_dwell_s
                    if not emitted and t-self.since[code]>=dwell and t-self.sent.get(code,-1e9)>=c.feedback_cooldown_s:
                        alerts.append(dict(code=code,message=message,level='notice',timestamp_s=t))
                        self.sent[code]=t;emitted=True
        return self._out(values,status,progress,alerts)

    def _out(self,values,status,progress,alerts):
        return {'measurement_metrics':values,'calibration':{'status':status,'progress':progress,
                'baseline':dict(self.baseline) if self.baseline else None,
                'facing':'left' if self.direction<0 else 'right'},'feedback_events':alerts}
