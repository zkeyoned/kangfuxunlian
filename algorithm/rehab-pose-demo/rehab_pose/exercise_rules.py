"""Image-plane heuristics. Never infer muscle activation, force or contact."""
from dataclasses import dataclass,asdict
from collections import deque
import math


@dataclass
class ExerciseRulesConfig:
    slr_min_knee_deg:float=170
    slr_target_min_deg:float=30
    slr_target_max_deg:float=45
    slr_speed_limit_deg_s:float=90
    slr_trunk_delta_limit_deg:float=15
    squat_max_flexion_deg:float=90
    squat_forward_limit_deg:float=15
    knee_speed_limit_deg_s:float=180
    standing_knee_min_deg:float=165
    standing_trunk_limit_deg:float=15
    standing_hip_flexion_max_deg:float=20
    dwell_s:float=.3
    speed_dwell_s:float=.08
    cooldown_s:float=3

    def __post_init__(self):
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in asdict(self).values()):raise ValueError('Invalid exercise rule parameter')
        if not self.slr_target_min_deg<self.slr_target_max_deg<90:raise ValueError('Invalid SLR range')


UNSUPPORTED={
 '2':['股四头肌是否绷紧/发力','骨盆三维旋转','腰椎弓起或贴床','另一腿是否接触床面'],
 '6':['膝内扣（需额外正面验证）','足跟离地（当前模型无可靠足跟点）','双腿受力是否均匀','是否真正扶稳支撑物'],
 '8':['手部是否真正借力','双腿受力对称性','椅面接触和落座冲击力']}


class ExerciseFeedback:
    def __init__(self,exercise,config=None):
        self.exercise=exercise;self.config=config or ExerciseRulesConfig()
        self.reference=None;self.history=deque();self.since={};self.sent={}

    def update(self,t,measure,phase):
        c=self.config;v=measure['measurement_metrics'];base=measure['calibration']['baseline']
        v['leg_raise_delta_deg']=None;v['leg_raise_velocity_deg_s']=None
        if self.exercise not in UNSUPPORTED:return []
        ref=base.get('captured_at_s') if base else None
        if ref!=self.reference:
            self.history.clear();self.since.clear();self.sent.clear();self.reference=ref
        knee=v.get('knee_included_deg')
        if base is None or knee is None:
            self.history.clear();self.since.clear();return []
        checks={};trunk=v.get('trunk_signed_deg');delta=v.get('trunk_delta_deg');speed=v.get('knee_velocity_deg_s')
        if self.exercise=='2':
            amount=v.get('thigh_delta_deg');v['leg_raise_delta_deg']=amount
            if amount is not None:
                if self.history and t-self.history[-1][0]>.3:self.history.clear()
                self.history.append((t,amount))
                while self.history and t-self.history[0][0]>.2:self.history.popleft()
                if len(self.history)>=3 and t-self.history[0][0]>=.08:
                    mt=sum(x for x,y in self.history)/len(self.history);my=sum(y for x,y in self.history)/len(self.history)
                    den=sum((x-mt)**2 for x,y in self.history)
                    v['leg_raise_velocity_deg_s']=sum((x-mt)*(y-my) for x,y in self.history)/den if den else None
            active=amount is not None and amount>5
            rs=v['leg_raise_velocity_deg_s']
            checks={
              'SLR_KNEE_BENT':(active and knee<c.slr_min_knee_deg,'抬腿时膝盖弯曲超出设置容差；请先降低幅度并检查姿势'),
              'SLR_TOO_HIGH':(active and amount>c.slr_target_max_deg,'抬腿幅度超过设置上限'),
              'SLR_TOO_FAST':(active and rs is not None and abs(rs)>c.slr_speed_limit_deg_s,'抬腿或放下速度超出设置范围'),
              'SLR_TRUNK_MOVED':(active and delta is not None and abs(delta)>c.slr_trunk_delta_limit_deg,'躯干方向变化超出设置范围；不能据此判断腰椎代偿')}
        elif self.exercise=='6':
            checks={
              'SQUAT_TOO_DEEP':(180-knee>c.squat_max_flexion_deg,'膝屈曲超过设置深度上限'),
              'SQUAT_FORWARD':(trunk is not None and trunk>c.squat_forward_limit_deg,'下蹲时躯干前倾超过设置范围'),
              'SQUAT_TOO_FAST':(speed is not None and abs(speed)>c.knee_speed_limit_deg_s,'下蹲或起身速度超出设置范围')}
        else:
            hip=v.get('hip_flexion_proxy_deg')
            at_top=knee>=c.standing_knee_min_deg
            checks={
              'STS_TOP_NOT_UPRIGHT':(at_top and ((trunk is not None and abs(trunk)>c.standing_trunk_limit_deg) or (hip is not None and hip>c.standing_hip_flexion_max_deg)), '站立阶段躯干或髋部尚未达到设置的伸展要求'),
              'STS_TOO_FAST':(speed is not None and abs(speed)>c.knee_speed_limit_deg_s,'起身或坐下过快；此指标不等于测量惯性或冲击力')}
        events=[]
        for code in list(self.since):
            if code not in checks or not checks[code][0]:self.since.pop(code,None)
        for code,(condition,message) in checks.items():
            if not condition:continue
            self.since.setdefault(code,t)
            dwell=c.speed_dwell_s if code.endswith('FAST') else c.dwell_s
            if t-self.since[code]>=dwell and t-self.sent.get(code,-1e9)>=c.cooldown_s:
                events.append({'code':code,'message':message,'timestamp_s':t,'level':'notice'})
                self.sent[code]=t
        return events
