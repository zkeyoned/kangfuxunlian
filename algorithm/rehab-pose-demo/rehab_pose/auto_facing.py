"""Resolve image-facing direction from the locked person's observed pose.

Direction is distinct from anatomical training side. Technical heuristics,
not an arbitrary-view 3D estimator. Uncertain initialization suspends scoring.
"""
import math


class AutoFacing:
    def __init__(self, exercise, min_confidence=.3):
        self.exercise=exercise
        self.min_confidence=min_confidence
        self.reset()

    def reset(self):
        self.facing=None;self.candidate=None;self.since=None;self.count=0
        self.last_observed=None;self.last_t=None

    def evidence(self, measured, landmarks, width):
        p=measured.get('keypoints',{})
        h=p.get('hip');k=p.get('knee');s=p.get('shoulder')
        if h and k and min(h.get('confidence',0),k.get('confidence',0))>=self.min_confidence:
            dx=k['x']-h['x'];dy=k['y']-h['y'];length=math.hypot(dx,dy)
            angle=measured.get('value')
            seated=self.exercise in ('1','8') and angle is not None and 55<=angle<=135
            lying=self.exercise=='2' and s and abs(s['x']-h['x'])>abs(s['y']-h['y']) and angle is not None and angle>=150
            if (seated or lying) and length>0 and abs(dx)>.04*width and abs(dx)/length>.7:
                return ('right' if dx>0 else 'left'),'leg'
        # Upright mini-squat has near-vertical thighs: use a clear face profile
        # only to initialize. Turning the head alone must not reverse scoring.
        if self.exercise=='6' and self.facing is None and len(landmarks)>8:
            def valid(i):
                q=landmarks[i]
                return min(q.get('visibility',0),q.get('presence',0))>=self.min_confidence and math.isfinite(q['x'])
            ears=[landmarks[i]['x'] for i in (7,8) if valid(i)]
            if valid(0) and ears:
                nose=landmarks[0]['x']
                if nose>max(ears)+.012:return 'right','face'
                if nose<min(ears)-.012:return 'left','face'
        return None,None

    def update(self,t,measured,landmarks,width):
        if self.last_t is not None and t-self.last_t>.4:
            self.candidate=None;self.since=None;self.count=0
        self.last_t=t
        if not measured.get('visible'):
            self.candidate=None;self.since=None;self.count=0
            if self.last_observed is not None and t-self.last_observed>2:
                self.facing=None
            return self.facing,'waiting_for_points'
        self.last_observed=t
        direction,source=self.evidence(measured,landmarks,width)
        if direction is None or direction==self.facing:
            self.candidate=None;self.since=None;self.count=0
            return self.facing,'ready' if self.facing else 'waiting_for_direction'
        if self.candidate!=direction:
            self.candidate=direction;self.since=t;self.count=0
        self.count+=1
        if t-self.since>=.7 and self.count>=5:
            self.facing=direction;self.candidate=None;self.since=None;self.count=0
            return self.facing,'direction_changed'
        return self.facing,'checking_direction'
