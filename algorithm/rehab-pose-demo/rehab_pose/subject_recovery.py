"""Short, conservative reacquisition of the originally selected person.

Association uses box continuity and an immutable clothing histogram, not identity
recognition. No landmarks are returned while association is uncertain.
"""
import math
import time
import numpy as np
from .subject import SubjectLock, iou


def stable_appearance(image,box):
    """Ignore unstable hue of gray/white clothing; retain chromatic bins.

    A square-root histogram limits background dominance as the leg changes the
    detector's box. This is a weak appearance cue, not a person identity model.
    """
    import cv2
    x1,y1,x2,y2=map(float,box[:4]);w=x2-x1;h=y2-y1
    crop=image[max(0,int(y1+h*.15)):min(image.shape[0],int(y1+h*.65)),
               max(0,int(x1+w*.2)):min(image.shape[1],int(x2-w*.2))]
    if not crop.size:
        return np.zeros(68)
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV).astype(np.int32)
    hue=np.minimum(hsv[:,:,0]*16//180,15)
    saturation=np.minimum(hsv[:,:,1]//64,3)
    bins=hue*4+saturation
    bins[hsv[:,:,1]<40]=64+np.minimum(hsv[:,:,2][hsv[:,:,1]<40]//64,3)
    histogram=np.sqrt(np.bincount(bins.ravel(),minlength=68).astype(float))
    return histogram/max(float(np.linalg.norm(histogram)),1e-9)


class RecoveringSubjectLock(SubjectLock):
    def __init__(self, grace_s=3., recovery_s=.15):
        super().__init__()
        self.grace_s=grace_s
        self.recovery_s=recovery_s
        self.lost_since=None
        self.recovery_since=None
        self.recovery_box=None
        self.recovery_frames=0
        self.recoveries=0
        self.last_timestamp=None

    def reset(self):
        super().reset()
        self.lost_since=self.recovery_since=None
        self.recovery_box=None
        self.recovery_frames=0

    def _match(self, box, feature):
        recovering=self.lost_since is not None
        candidates=[]
        for i,b in enumerate(self.boxes):
            overlap=iou(box,b)
            ratio=((b[2]-b[0])*(b[3]-b[1]))/max((box[2]-box[0])*(box[3]-box[1]),1)
            similarity=float(np.dot(feature,self.features[i]))
            if overlap>=.25 and .5<=ratio<=2 and similarity>=(.80 if recovering else .65):
                candidates.append((.55*overlap+.45*similarity,i))
        candidates.sort(reverse=True)
        if not candidates or (len(candidates)>1 and candidates[0][0]-candidates[1][0]<.15):
            return None
        index=candidates[0][1]
        chosen=self.boxes[index]
        area=max((chosen[2]-chosen[0])*(chosen[3]-chosen[1]),1)
        for j,other in enumerate(self.boxes):
            if j==index:
                continue
            intersection=max(0,min(chosen[2],other[2])-max(chosen[0],other[0]))*max(0,min(chosen[3],other[3])-max(chosen[1],other[1]))
            # Substantial overlap is uncertain; modest box overlap alone is not
            # evidence that the patient's measured leg is hidden.
            if intersection/area>.45:
                return None
        return index

    def update(self, boxes, features, timestamp_s=None):
        t=time.monotonic() if timestamp_s is None else float(timestamp_s)
        if not math.isfinite(t) or (self.last_timestamp is not None and t<self.last_timestamp):
            raise ValueError('Subject timestamps must increase')
        self.last_timestamp=t
        if self.status not in ('locked','subject_temporarily_lost'):
            selected,status=super().update(boxes,features,t)
            if selected is not None:
                self.lost_since=self.recovery_since=None
                self.recovery_frames=0
            return selected,status
        self.boxes=[np.asarray(b[:4],float) for b in boxes]
        self.features=[np.asarray(f,float) for f in features]
        if self.lost_since is not None and t-self.lost_since>self.grace_s:
            self.status='subject_lost_reconfirm'
            self.box=None
            self.proposal=None
            return None,self.status
        index=self._match(self.box,self.anchor)
        if index is None:
            if self.lost_since is None:
                self.lost_since=t
            self.recovery_since=None
            self.recovery_box=None
            self.recovery_frames=0
            self.status='subject_temporarily_lost'
            return None,self.status
        if self.lost_since is not None:
            b=self.boxes[index]
            if self.recovery_box is None or iou(self.recovery_box,b)<.5:
                self.recovery_since=t
                self.recovery_frames=0
            self.recovery_box=b.copy()
            self.recovery_frames+=1
            if self.recovery_frames<3 or t-self.recovery_since<self.recovery_s:
                return None,'subject_temporarily_lost'
            self.lost_since=self.recovery_since=None
            self.recovery_frames=0
            self.recoveries+=1
        self.box=self.boxes[index].copy()
        self.status='locked'
        return index,self.status

    def snapshot(self):
        return {**super().snapshot(),'automatic_recoveries':self.recoveries,
                'recovery_window_s':self.grace_s}
