"""Pure-Python geometry and conservative repetition segmentation."""
from dataclasses import dataclass, asdict
import math


@dataclass
class Config:
    # TECHNICAL TEST PARAMETERS, not clinical targets.
    rest_max_deg: float = 105
    start_deg: float = 115
    target_deg: float = 160
    hysteresis_deg: float = 5
    min_excursion_deg: float = 20
    reversal_deg: float = 8
    min_hold_s: float = 2
    min_return_s: float = 1
    rest_dwell_s: float = .25
    max_gap_s: float = .3
    smoothing_tau_s: float = .08
    min_confidence: float = .6
    rest_min_deg: float = 0
    start_dwell_s: float = 0
    target_dwell_s: float = 0
    reversal_dwell_s: float = 0
    attempt_timeout_s: float = 0

    def __post_init__(self):
        for key, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid configuration: {key}")
        if not 0 <= self.rest_min_deg < self.rest_max_deg <= self.start_deg < self.target_deg <= 180:
            raise ValueError("Expected 0 <= rest_min_deg < rest_max_deg <= start_deg < target_deg <= 180")
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be 0..1")
        for key in ("hysteresis_deg", "min_excursion_deg", "reversal_deg", "rest_dwell_s", "max_gap_s"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if any(getattr(self, k) < 0 for k in ("min_hold_s", "min_return_s", "smoothing_tau_s",
                                               "start_dwell_s", "target_dwell_s", "reversal_dwell_s",
                                               "attempt_timeout_s")):
            raise ValueError("Times must be nonnegative")
        if self.target_deg - self.hysteresis_deg <= self.start_deg:
            raise ValueError("Target hysteresis must stay above start threshold")


def angle(a, b, c):
    """Unsigned pixel-space angle ABC, 0..180; cannot detect hyperextension."""
    u = (a[0]-b[0], a[1]-b[1])
    v = (c[0]-b[0], c[1]-b[1])
    den = math.hypot(*u) * math.hypot(*v)
    if den < 1e-8:
        return None
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x,y in zip(u,v))/den))))


def metrics(landmarks, width, height, side="left", min_confidence=.6):
    """Input 33 normalized landmarks; compute in pixels (aspect-ratio corrected)."""
    if side not in ("left", "right"):
        raise ValueError("side must be left or right")
    ids = (11,23,25,27) if side == "left" else (12,24,26,28)
    names = ("shoulder", "hip", "knee", "ankle")
    empty = {"value": None, "aux": {}, "visible": False, "confidence": 0., "keypoints": {}}
    if len(landmarks) != 33 or width <= 0 or height <= 0:
        return empty
    points = {}
    for name, idx in zip(names, ids):
        p = landmarks[idx]
        x,y = p["x"],p["y"]
        conf = min(p.get("visibility",0), p.get("presence",0))
        valid = all(math.isfinite(v) for v in (x,y,conf)) and 0 <= x <= 1 and 0 <= y <= 1
        points[name] = {"x": x*width if math.isfinite(x) else None,
                        "y": y*height if math.isfinite(y) else None,
                        "confidence": conf if valid else 0.}
    confidence = min(points[n]["confidence"] for n in ("hip","knee","ankle"))
    out = dict(empty, keypoints=points, confidence=confidence)
    if confidence < min_confidence:
        return out
    def xy(n):
        return points[n]["x"],points[n]["y"]
    knee = angle(xy("hip"),xy("knee"),xy("ankle"))
    if knee is None:
        return out
    trunk = None
    if points["shoulder"]["confidence"] >= min_confidence:
        s,h = xy("shoulder"),xy("hip")
        if math.dist(s,h)>1e-8:
            trunk=math.degrees(math.atan2(abs(s[0]-h[0]), h[1]-s[1]))
    return dict(out, value=knee, visible=True,
                aux={"knee_included_deg":knee, "knee_flexion_proxy_deg":180-knee,
                     "trunk_unsigned_tilt_deg":trunk})


class Analyzer:
    """Requires observed rest; only explicitly qualified short gaps may pause.

    Completeness and configured target comparisons are separate. No medical score.
    """
    def __init__(self, config=None):
        self.config=config or Config()
        self.state="waiting_for_rest"
        self.last_t=None
        self.smooth=None
        self.rest_since=None
        self.active=None
        self.reps=[]
        self.interrupted=[]
        self.last_observed_t=None
        self.gap_pending=False
        self.start_since=None

    def abort(self, t, reason):
        if self.active:
            self.interrupted.append({"start_s":self.active["start_s"],"end_s":t,"reason":reason})
        self.active=None
        self.state="waiting_for_rest"
        self.rest_since=None
        self.smooth=None
        self.gap_pending=False
        self.start_since=None

    def update(self, t, raw_angle, valid=True, bridge_pending=False):
        if not math.isfinite(t) or t < 0 or (self.last_t is not None and t <= self.last_t):
            raise ValueError("Timestamps must be finite, nonnegative and strictly increasing")
        dt=0 if self.last_t is None else t-self.last_t
        self.last_t=t
        c=self.config
        if dt>c.max_gap_s:
            self.abort(t,"timestamp_gap")
            bridge_pending=False
        if bridge_pending:
            if self.last_observed_t is None or t-self.last_observed_t>c.max_gap_s:
                self.abort(t,"prediction_timeout")
                return self.snapshot(t,None,"unreliable")
            self.rest_since=None
            if self.active:
                if not self.gap_pending:
                    self.active["bridged_gaps"]+=1
                # No inferred hold/rest dwell; retain longest observed hold only.
                self.active["hold_start"]=None
                self.active["rest_start"]=None
            self.gap_pending=True
            return self.snapshot(t,None,"prediction_only")
        if not valid or raw_angle is None or not math.isfinite(raw_angle) or not 0<=raw_angle<=180:
            self.abort(t,"unreliable_detection")
            return self.snapshot(t,None,"unreliable")
        if self.gap_pending and t-self.last_observed_t>c.max_gap_s:
            self.abort(t,"prediction_timeout")
        if self.gap_pending:
            self.smooth=None
        self.gap_pending=False
        self.last_observed_t=t
        alpha=1 if c.smoothing_tau_s==0 else 1-math.exp(-dt/c.smoothing_tau_s)
        self.smooth=raw_angle if self.smooth is None else self.smooth+alpha*(raw_angle-self.smooth)
        a=self.smooth
        if self.state=="waiting_for_rest":
            in_rest=c.rest_min_deg<=a<=c.rest_max_deg
            self.rest_since = (t if self.rest_since is None else self.rest_since) if in_rest else None
            if self.rest_since is not None and t-self.rest_since>=c.rest_dwell_s:
                self.state="rest"
        elif self.state=="rest":
            if a>=c.start_deg:
                if self.start_since is None:self.start_since=t
                if t-self.start_since>=c.start_dwell_s:
                    self.active={"start_s":self.start_since,"min_deg":a,"max_deg":a,"peak_s":t,
                                 "target_candidate_start":None,"target_reached":False,
                                 "hold_start":None,"max_hold_s":0.,"reversal_start":None,
                                 "return_start":None,"return_min":None,"rest_start":None,"bridged_gaps":0}
                    self.start_since=None;self.state="extending"
            else:self.start_since=None
        else:
            r=self.active
            if c.attempt_timeout_s and t-r["start_s"]>=c.attempt_timeout_s:
                self.abort(t,"attempt_timeout")
                return self.snapshot(t,a,"reliable")
            r["min_deg"]=min(r["min_deg"],a)
            if a>r["max_deg"]:
                r["max_deg"],r["peak_s"]=a,t
            if self.state in ("extending","holding"):
                if a>=c.target_deg:
                    if r["target_candidate_start"] is None:r["target_candidate_start"]=t
                    if t-r["target_candidate_start"]>=c.target_dwell_s:
                        was_reached=r["target_reached"]
                        r["target_reached"]=True
                        if r["hold_start"] is None:r["hold_start"]=t if was_reached else r["target_candidate_start"]
                        self.state="holding"
                elif not r["target_reached"]:
                    r["target_candidate_start"]=None;r["hold_start"]=None
                if r["target_reached"] and r["hold_start"] is not None:
                    if a>=c.target_deg-c.hysteresis_deg:r["max_hold_s"]=max(r["max_hold_s"],t-r["hold_start"])
                    else:r["hold_start"]=None
                if r["max_deg"]-a>=c.reversal_deg:
                    if r["reversal_start"] is None:r["reversal_start"]=t
                    if t-r["reversal_start"]>=c.reversal_dwell_s:
                        self.state="returning";r["return_start"]=r["reversal_start"];r["return_min"]=a
                else:r["reversal_start"]=None
            if self.state=="returning":
                r["return_min"]=a if r["return_min"] is None else min(r["return_min"],a)
                if c.reversal_dwell_s and a-r["return_min"]>=c.reversal_deg:
                    self.state="holding" if r["target_reached"] and a>=c.target_deg-c.hysteresis_deg else "extending"
                    r["reversal_start"]=None;r["return_start"]=None;r["return_min"]=None;r["rest_start"]=None
                elif not c.rest_min_deg<=a<=c.rest_max_deg:
                    r["rest_start"]=None
                else:
                    if r["rest_start"] is None:
                        r["rest_start"]=t
                    if t-r["rest_start"]>=c.rest_dwell_s:
                        if r["max_deg"]-r["min_deg"]>=c.min_excursion_deg:
                            end=r["rest_start"]
                            time_to_target=(None if not r["target_reached"] else r["target_candidate_start"]-r["start_s"])
                            cycle_duration=end-r["start_s"]
                            self.reps.append({"index":len(self.reps)+1,"start_s":r["start_s"],"end_s":end,
                                "min_included_deg":r["min_deg"],"max_included_deg":r["max_deg"],
                                "extension_to_first_peak_s":None if r["bridged_gaps"] else r["peak_s"]-r["start_s"],
                                "time_to_target_s":None if r["bridged_gaps"] else time_to_target,
                                "target_hold_s":r["max_hold_s"],
                                "return_s":None if r["bridged_gaps"] else max(0,end-r["return_start"]),
                                "cycle_duration_s":cycle_duration,
                                "bridged_gaps":r["bridged_gaps"],
                                "needs_review":bool(r["bridged_gaps"]),
                                "target_comparison":{"amplitude_met":r["target_reached"],
                                    "hold_met":r["max_hold_s"]>=c.min_hold_s,
                                    "extension_time_met":None if r["bridged_gaps"] or time_to_target is None else time_to_target>=1,
                                    "return_time_met":None if r["bridged_gaps"] else end-r["return_start"]>=c.min_return_s}})
                        else:
                            self.interrupted.append({"start_s":r["start_s"],"end_s":t,"reason":"excursion_too_small"})
                        self.active=None
                        self.state="rest"
        return self.snapshot(t,a,"reliable")

    def snapshot(self,t,a,status):
        return {"timestamp_s":t,"smoothed_included_deg":a,"phase":self.state,
                "completed_reps":len(self.reps),"detection_status":status}

    def finish(self):
        if self.active:
            self.abort(self.last_t,"end_before_return")

