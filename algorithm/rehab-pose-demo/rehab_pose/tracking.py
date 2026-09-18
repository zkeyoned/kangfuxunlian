"""Temporal quality gate and separately labelled short display predictions.

One Euro filter equations: Casiez et al. 2012, https://gery.casiez.net/1euro/ .
New implementation; no upstream source copied. Thresholds are technical heuristics.
"""
import copy
from dataclasses import dataclass,asdict
import math
from .core import metrics


@dataclass
class TrackingConfig:
    min_cutoff_hz: float = 1.5
    beta: float = .04  # normalized-coordinate speed sensitivity
    derivative_cutoff_hz: float = 1.
    max_gap_s: float = .3
    min_segment_diagonal: float = .025
    jump_floor_diagonal: float = .04
    max_speed_diagonal_s: float = 1.5
    length_change_fraction: float = .4
    reacquire_s: float = .3
    prediction_s: float = .25
    recovery_diagonal: float = .04
    prediction_speed_diagonal_s: float = .5

    def __post_init__(self):
        if any(not math.isfinite(v) or v<=0 for v in asdict(self).values()):
            raise ValueError("Tracking parameters must be positive finite numbers")
        if self.prediction_s>self.max_gap_s:
            raise ValueError("Prediction duration must not exceed tracking gap limit")


class OneEuro:
    def __init__(self,cfg):
        self.cfg=cfg
        self.previous=None
        self.filtered=None
        self.derivative=0.
        self.t=None

    @staticmethod
    def alpha(dt,cutoff):
        r=2*math.pi*cutoff*dt
        return r/(r+1)

    def update(self,t,value):
        if self.t is None:
            self.previous=self.filtered=value
        else:
            dt=t-self.t
            if dt<=0:
                raise ValueError("Filter timestamps must increase")
            derivative=(value-self.previous)/dt
            da=self.alpha(dt,self.cfg.derivative_cutoff_hz)
            self.derivative+=da*(derivative-self.derivative)
            cutoff=self.cfg.min_cutoff_hz+self.cfg.beta*abs(self.derivative)
            self.filtered+=self.alpha(dt,cutoff)*(value-self.filtered)
            self.previous=value
        self.t=t
        return self.filtered


class StrictPoseTracker:
    def __init__(self,side="left",min_confidence=.6,config=None):
        self.side=side
        self.min_confidence=min_confidence
        self.config=config or TrackingConfig()
        self.previous=None
        self.previous_t=None
        self.warm_since=None
        self.filters={}
        self.last_t=None
        self.shape=None

    def reset(self):
        self.previous=None
        self.previous_t=None
        self.warm_since=None
        self.filters={}

    def update(self,t,landmarks,width,height):
        if not math.isfinite(t) or (self.last_t is not None and t<=self.last_t):
            raise ValueError("Tracking timestamps must increase")
        if self.last_t is not None and (t-self.last_t>self.config.max_gap_s or self.shape!=(width,height)):
            self.reset()
        self.last_t=t
        self.shape=(width,height)
        raw=metrics(landmarks,width,height,self.side,self.min_confidence)
        ids=(11,23,25,27) if self.side=="left" else (12,24,26,28)
        flags=[]
        for name,idx in zip(("hip","knee","ankle"),ids[1:]):
            p=raw["keypoints"].get(name)
            if not p:
                flags.append("no_pose")
                break
            if p["x"] is None or p["y"] is None or not 0<=p["x"]<=width or not 0<=p["y"]<=height:
                flags.append(name+"_out_of_frame")
            elif p["confidence"]<self.min_confidence:
                flags.append(name+"_low_confidence")
        diagonal=math.hypot(width,height)
        def position(p):
            return p["x"],p["y"]
        if not flags:
            points=raw["keypoints"]
            lengths=[math.dist(position(points[a]),position(points[b])) for a,b in (("hip","knee"),("knee","ankle"))]
            if min(lengths)<diagonal*self.config.min_segment_diagonal:
                flags.append("degenerate_leg_geometry")
            if self.previous is not None:
                dt=t-self.previous_t
                limit=diagonal*(self.config.jump_floor_diagonal+self.config.max_speed_diagonal_s*dt)
                if any(math.dist(position(points[n]),position(self.previous[n]))>limit for n in ("hip","knee","ankle")):
                    flags.append("keypoint_jump")
                old_lengths=[math.dist(position(self.previous[a]),position(self.previous[b])) for a,b in (("hip","knee"),("knee","ankle"))]
                if any(abs(now/old-1)>self.config.length_change_fraction for now,old in zip(lengths,old_lengths) if old>1e-6):
                    flags.append("leg_length_jump")
                # Flag only strong bilateral reversal evidence. Never auto-swap anatomical sides.
                other=metrics(landmarks,width,height,"right" if self.side=="left" else "left",self.min_confidence)
                if other["visible"]:
                    own=sum(math.dist(position(points[n]),position(self.previous[n])) for n in ("knee","ankle"))
                    alt=sum(math.dist(position(other["keypoints"][n]),position(self.previous[n])) for n in ("knee","ankle"))
                    if own>diagonal*.08 and alt<own*.35:
                        flags.append("possible_side_switch")
        if flags or not raw["visible"]:
            self.reset()
            result=copy.deepcopy(raw)
            result.update(value=None,aux={},visible=False,keypoints={})
            return result,{"quality_flags":flags or ["invalid_geometry"],"raw_metrics":raw}
        self.previous=copy.deepcopy(raw["keypoints"])
        self.previous_t=t
        if self.warm_since is None:
            self.warm_since=t
        filtered=copy.deepcopy(landmarks)
        for idx in ids:
            p=landmarks[idx]
            if min(p.get("visibility",0),p.get("presence",0))<self.min_confidence or not 0<=p['x']<=1 or not 0<=p['y']<=1:
                for axis in ("x","y"):
                    self.filters.pop((idx,axis),None)
                continue
            for axis in ("x","y"):
                f=self.filters.setdefault((idx,axis),OneEuro(self.config))
                filtered[idx][axis]=f.update(t,p[axis])
        result=metrics(filtered,width,height,self.side,self.min_confidence)
        if t-self.warm_since<self.config.reacquire_s:
            result.update(value=None,aux={},visible=False,keypoints={})
            flags=["stabilizing"]
        return result,{"quality_flags":flags,"raw_metrics":raw}


class PoseTracker:
    """Bridge one low-score joint, never treat a predicted point as a measurement.

    Retain the strict filter state during bounded dropouts. Two consecutive
    geometrically consistent observations are required to resume measurement.
    Missing people, out-of-frame points and side-switch evidence never bridge.
    """
    def __init__(self,side="left",min_confidence=.6,config=None):
        self.config=config or TrackingConfig()
        self.strict=StrictPoseTracker(side,min_confidence,self.config)
        self.history=[]
        self.pending=False
        self.recovery_count=0
        self.last_t=None
        self.shape=None

    def _prediction(self,t,width,height):
        last_t,last_raw,last_filtered=self.history[-1]
        points=copy.deepcopy(last_raw["keypoints"])
        display=copy.deepcopy(last_filtered)
        diagonal=math.hypot(width,height)
        for name in ("hip","knee","ankle"):
            vx=vy=0.
            if len(self.history)>1:
                old_t,old,_=self.history[0]
                dt=last_t-old_t
                if dt>0:
                    vx=(points[name]["x"]-old["keypoints"][name]["x"])/dt
                    vy=(points[name]["y"]-old["keypoints"][name]["y"])/dt
                    speed=math.hypot(vx,vy)
                    limit=diagonal*self.config.prediction_speed_diagonal_s
                    scale=min(1.,limit/max(speed,1e-9))
                    vx*=scale; vy*=scale
            for axis,velocity in (("x",vx),("y",vy)):
                points[name][axis]+=velocity*(t-last_t)
                display["keypoints"][name][axis]+=velocity*(t-last_t)
        # No trunk extrapolation: only the leg is displayed while uncertain.
        display["keypoints"].pop("shoulder",None)
        display.update(value=None,aux={},visible=False,confidence=0.)
        for p in display["keypoints"].values():
            p["confidence"]=0.
            p["source"]="predicted"
        return points,display

    def update(self,t,landmarks,width,height):
        if self.last_t is not None and (t-self.last_t>self.config.max_gap_s or self.shape!=(width,height)):
            self.history=[]; self.pending=False; self.recovery_count=0
        self.last_t=t; self.shape=(width,height)
        before=copy.deepcopy(self.strict)
        result,quality=self.strict.update(t,landmarks,width,height)
        quality.update(bridge_pending=False,measurement_source="observed" if result["visible"] else "unavailable",
                       display_prediction=None)
        flags=quality["quality_flags"]
        low=[n for n in ("hip","knee","ankle") if n+"_low_confidence" in flags]
        eligible=(len(flags)==1 and len(low)==1) or (self.pending and result["visible"])
        if eligible and len(self.history)>=3 and t-self.history[-1][0]<=self.config.prediction_s:
            predicted,display=self._prediction(t,width,height)
            raw=quality["raw_metrics"]["keypoints"]
            diagonal=math.hypot(width,height)
            inside=all(0<=predicted[n]["x"]<=width and 0<=predicted[n]["y"]<=height
                       for n in ("hip","knee","ankle"))
            display_inside=all(0<=p["x"]<=width and 0<=p["y"]<=height for p in display["keypoints"].values())
            consistent=all(math.dist((raw[n]["x"],raw[n]["y"]),(predicted[n]["x"],predicted[n]["y"]))
                           <=diagonal*self.config.recovery_diagonal for n in ("hip","knee","ankle") if n not in low)
            lengths=[math.dist((predicted[a]["x"],predicted[a]["y"]),(predicted[b]["x"],predicted[b]["y"]))
                     for a,b in (("hip","knee"),("knee","ankle"))]
            last=self.history[-1][1]["keypoints"]
            old_lengths=[math.dist((last[a]["x"],last[a]["y"]),(last[b]["x"],last[b]["y"]))
                         for a,b in (("hip","knee"),("knee","ankle"))]
            plausible=all(x>diagonal*self.config.min_segment_diagonal and abs(x/y-1)<=self.config.length_change_fraction
                          for x,y in zip(lengths,old_lengths))
            if inside and display_inside and consistent and plausible:
                self.recovery_count=self.recovery_count+1 if result["visible"] else 0
                if self.recovery_count>=2:
                    quality["quality_flags"]=["recovered_after_short_gap"]
                    self.pending=False; self.recovery_count=0
                    self.history=[]
                else:
                    self.strict=before
                    self.strict.last_t=t
                    self.pending=True
                    quality.update(bridge_pending=True,measurement_source="predicted_display_only",
                                   display_prediction=display)
                    quality["quality_flags"]=flags+["short_gap_prediction" if low else "checking_recovery"]
                    return dict(value=None,aux={},visible=False,confidence=0.,keypoints={}),quality
            elif self.pending:
                quality["quality_flags"]=flags+["recovery_mismatch"]
                result.update(value=None,aux={},visible=False,keypoints={})
        if self.pending:
            self.pending=False; self.recovery_count=0
            self.strict.reset()
            result.update(value=None,aux={},visible=False,keypoints={})
            quality["quality_flags"]=quality["quality_flags"]+["short_gap_rejected"]
        if result["visible"]:
            self.history.append((t,copy.deepcopy(quality["raw_metrics"]),copy.deepcopy(result)))
            self.history=[h for h in self.history if t-h[0]<=.15]
        else:
            self.history=[]
            quality["measurement_source"]="unavailable"
        return result,quality
