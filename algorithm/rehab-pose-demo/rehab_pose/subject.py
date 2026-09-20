"""Conservative user-confirmed box association, not biometric identification."""
import math
import numpy as np


def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    aa=max(0,a[2]-a[0])*max(0,a[3]-a[1]);bb=max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return inter/max(aa+bb-inter,1e-9)


def appearance(image,box):
    import cv2
    x1,y1,x2,y2=map(float,box[:4]);w=x2-x1;h=y2-y1
    crop=image[max(0,int(y1+h*.15)):min(image.shape[0],int(y1+h*.65)),
               max(0,int(x1+w*.2)):min(image.shape[1],int(x2-w*.2))]
    if crop.size==0:return np.zeros(128)
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    hist=cv2.calcHist([hsv],[0,1],None,[16,8],[0,180,0,256]).reshape(-1)
    return hist/max(float(np.linalg.norm(hist)),1e-9)


class SubjectLock:
    """A detection loss/ambiguity invalidates lock until explicit reconfirmation."""
    def __init__(self):
        self.boxes=[];self.features=[];self.proposal=None;self.anchor=None
        self.box=None;self.status='select_subject';self.confirm_requested=False
        self.generation=0

    def reset(self):
        self.box=None;self.anchor=None;self.proposal=None
        self.status='select_subject';self.confirm_requested=False

    def click(self,x,y):
        if self.status=='locked':return
        hits=[i for i,b in enumerate(self.boxes) if b[0]<=x<=b[2] and b[1]<=y<=b[3]]
        if len(hits)==1:
            i=hits[0];self.proposal=(self.boxes[i].copy(),self.features[i].copy())
            self.status='confirm_subject'

    def confirm(self):
        if self.status!='locked':self.confirm_requested=True

    def _match(self,box,feature):
        candidates=[i for i,b in enumerate(self.boxes) if iou(box,b)>=.25]
        if len(candidates)!=1:return None
        i=candidates[0];b=self.boxes[i]
        ratio=((b[2]-b[0])*(b[3]-b[1]))/max((box[2]-box[0])*(box[3]-box[1]),1)
        if not .5<=ratio<=2 or float(np.dot(feature,self.features[i]))<.6:return None
        # Any competing box substantially overlapping the subject causes a pause.
        if any(i!=j and iou(b,other)>.10 for j,other in enumerate(self.boxes)):return None
        return i

    def update(self,boxes,features,timestamp_s=None):
        self.boxes=[np.asarray(b[:4],float) for b in boxes]
        self.features=[np.asarray(f,float) for f in features]
        if self.status=='locked':
            idx=self._match(self.box,self.anchor)
            if idx is None:
                self.status='subject_lost_reconfirm';self.box=None;self.proposal=None
                return None,self.status
            self.box=self.boxes[idx].copy()
            return idx,'locked'
        if self.confirm_requested:
            self.confirm_requested=False
            if self.proposal is None and len(self.boxes)==1:
                self.proposal=(self.boxes[0].copy(),self.features[0].copy())
            if self.proposal is not None:
                idx=self._match(*self.proposal)
                if idx is not None:
                    self.box=self.boxes[idx].copy();self.anchor=self.features[idx].copy()
                    self.generation+=1;self.status='locked';self.proposal=None
                    return idx,'locked'
            self.proposal=None;self.status='selection_ambiguous'
        return None,self.status

    def snapshot(self):
        return {'status':self.status,'generation':self.generation,
                'box':self.box.tolist() if self.box is not None else None,
                'detected_people':len(self.boxes),'identity_verified':False}

    def draw(self,frame):
        import cv2
        for i,b in enumerate(self.boxes):
            selected=self.box is not None and iou(self.box,b)>.99
            color=(80,220,80) if selected else (160,160,160)
            x1,y1,x2,y2=map(int,b)
            cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
            cv2.putText(frame,f'Person {i+1}',(x1,max(18,y1)),0,.55,color,2)
        cv2.putText(frame,'Click person, C confirm | R reselect | '+self.status,
                    (8,frame.shape[0]-15),0,.45,(0,220,255),1)
