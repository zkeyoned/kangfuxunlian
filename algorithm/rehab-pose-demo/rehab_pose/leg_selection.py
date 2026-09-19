"""Explicit visual confirmation of a model-labelled leg; no identity guarantee."""
from .core import metrics


class LegSelection:
    def __init__(self,side,required):
        self.side=side
        self.confirmed=not required
        self.required=required
        self.generation=0

    def reset(self):
        self.confirmed=not self.required
        self.generation+=1

    def choose(self,side):
        self.side=side
        self.reset()

    def click(self,x,y,landmarks,w,h,confidence):
        import math
        distances=[]
        for side in ('left','right'):
            m=metrics(landmarks,w,h,side,confidence)
            if m['visible']:
                distances.append((min(math.hypot(x-m['keypoints'][n]['x'],y-m['keypoints'][n]['y']) for n in ('knee','ankle')),side))
        distances.sort()
        if not distances or distances[0][0]>.08*math.hypot(w,h):return False
        if len(distances)>1 and distances[1][0]-distances[0][0]<.015*math.hypot(w,h):return False
        self.choose(distances[0][1]);return True

    def confirm(self,landmarks,w,h,confidence):
        m=metrics(landmarks,w,h,self.side,confidence)
        if not m['visible']:return False
        if any(not (0<=p['x']<=w and 0<=p['y']<=h) for n,p in m['keypoints'].items() if n in ('hip','knee','ankle')):return False
        self.confirmed=True
        return True

    def draw(self,frame,landmarks,confidence):
        import cv2
        h,w=frame.shape[:2]
        for side,color in [('left',(255,180,0)),('right',(180,0,255))]:
            m=metrics(landmarks,w,h,side,confidence)
            if not m['visible']:continue
            pts=m['keypoints']
            for a,b in [('hip','knee'),('knee','ankle')]:
                cv2.line(frame,(int(pts[a]['x']),int(pts[a]['y'])),(int(pts[b]['x']),int(pts[b]['y'])),color,3)
            cv2.putText(frame,side.upper(),(int(pts['knee']['x']),int(pts['knee']['y'])-15),0,.7,color,2)
        cv2.putText(frame,'Click knee/ankle or L/K; ENTER confirms '+self.side.upper(),(15,h-45),0,.65,(0,255,255),2)
