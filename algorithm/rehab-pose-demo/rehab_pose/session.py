"""Training progress is separate from pose measurement and quality scoring."""
from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class TrainingPlan:
    sets: int = 3
    reps_per_set: int = 10
    hold_s: float = 5.
    rest_s: float = 30.

    def __post_init__(self):
        for name,maximum in [('sets',20),('reps_per_set',100)]:
            value=getattr(self,name)
            if type(value) is not int or not 1<=value<=maximum:
                raise ValueError(f'{name} must be an integer in 1..{maximum}')
        if not math.isfinite(self.hold_s) or self.hold_s not in (0,2,2.5,3,5):
            raise ValueError('不支持的保持时间')
        if not math.isfinite(self.rest_s) or self.rest_s!=30:
            raise ValueError('当前组间休息固定30秒')


class TrainingSession:
    def __init__(self,plan):
        self.plan=plan;self.status='training';self.group=1;self.count=0
        self.total=0;self.rest_until=None;self.events=[];self.last_rep=0
        self.paused_at=None;self.previous_status=None;self.last_t=None

    def tick(self,t):
        if not math.isfinite(t) or (self.last_t is not None and t<self.last_t):raise ValueError('Session time must increase')
        self.last_t=t
        if self.status=='resting' and t>=self.rest_until:
            self.status='training';self.group+=1;self.count=0;self.rest_until=None
            self.events.append({'code':'SET_STARTED','timestamp_s':t,'set':self.group})

    def toggle_pause(self,t):
        self.tick(t)
        if self.status=='completed':return
        if self.status=='paused':
            if self.previous_status=='resting':self.rest_until+=t-self.paused_at
            self.status=self.previous_status
            self.events.append({'code':'RESUMED','timestamp_s':t})
        else:
            self.previous_status=self.status;self.status='paused';self.paused_at=t
            self.events.append({'code':'PAUSED','timestamp_s':t,'reason':'user_request'})

    def record_rep(self,t,rep):
        self.tick(t)
        if self.status!='training' or rep['index']<=self.last_rep:return
        self.last_rep=rep['index'];self.count+=1;self.total+=1
        rep['training_set']=self.group;rep['rep_in_set']=self.count
        if self.count>=self.plan.reps_per_set:
            self.events.append({'code':'SET_COMPLETED','timestamp_s':t,'set':self.group})
            if self.group==self.plan.sets:
                self.status='completed'
            else:self.status='resting';self.rest_until=t+self.plan.rest_s

    def snapshot(self,t):
        clock=self.paused_at if self.status=='paused' else t
        return {'status':self.status,'current_set':self.group,'total_sets':self.plan.sets,
                'reps_in_set':self.count,'target_reps_in_set':self.plan.reps_per_set,
                'completed_repetitions':self.total,
                'rest_remaining_s':max(0,self.rest_until-clock) if self.rest_until is not None else 0,
                'count_policy':'completed_cycles_including_not_met; not qualified_repetitions'}

    def result(self,t):return {'plan':asdict(self.plan),'progress':self.snapshot(t),'events':self.events,
                               'scope':'one_session_one_side; not a daily prescription or daily quota'}

    def finish(self,t,reason):
        if self.status!='completed':
            self.status='ended_incomplete';self.rest_until=None
            self.events.append({'code':'SESSION_ENDED','timestamp_s':t,'reason':reason})

