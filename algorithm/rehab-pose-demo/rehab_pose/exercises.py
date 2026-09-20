"""Exercise-specific experimental phase signals; no automatic exercise diagnosis."""
from dataclasses import asdict
from .core import Analyzer,Config

NAMES={'1':'SEATED_KNEE_EXTENSION','2':'SUPINE_STRAIGHT_LEG_RAISE',
       '6':'SUPPORTED_MINI_SQUAT','8':'SIT_TO_STAND'}


class ExerciseAnalyzer:
    def __init__(self,exercise,config,profile=None,rules=None):
        if exercise not in NAMES:raise ValueError('Unsupported exercise')
        self.exercise=exercise;self.name=NAMES[exercise]
        from .exercise_rules import ExerciseRulesConfig
        self.rules=rules or ExerciseRulesConfig()
        params=asdict(config)
        if exercise in ('2','6'):
            params.update(rest_max_deg=95,start_deg=100,target_deg=120,min_excursion_deg=10,reversal_deg=5)
        if exercise=='2':params.update(min_hold_s=5)
        if exercise=='8':params.update(target_deg=165,min_hold_s=0,min_return_s=1)
        params.update(profile or {})
        if exercise=='2':params['target_deg']=90+self.rules.slr_target_min_deg
        if exercise!='1':
            # The v0.1 seated-extension timing rules do not change the three
            # experimental exercise state machines.
            params.update(rest_min_deg=0,start_dwell_s=0,target_dwell_s=0,
                          reversal_dwell_s=0,attempt_timeout_s=0)
        self.engine=Analyzer(Config(**params));self.baseline=None
        self.original_rest=params['rest_max_deg'];self.original_start=params['start_deg']

    @property
    def state(self):return self.engine.state
    @property
    def reps(self):return self.engine.reps
    @property
    def interrupted(self):return self.engine.interrupted
    def abort(self,t,reason):self.engine.abort(t,reason)
    def finish(self):self.engine.finish()

    def update(self,t,m,measure,bridge=False):
        calibration=measure['calibration'];v=measure['measurement_metrics']
        ready=calibration['baseline'] is not None
        signal=None;amount=None
        if ready and m['visible']:
            base=calibration['baseline']
            if self.exercise=='1' and base.get('captured_at_s')!=self.baseline:
                b=base['knee_included_deg'];c=self.engine.config
                self.engine.abort(t,'new_reference')
                if b+10<c.target_deg-c.hysteresis_deg:
                    c.rest_min_deg=max(0,b-10)
                    c.rest_max_deg=b+10
                    c.start_deg=b+10
                else:
                    state=self.engine.update(t,None,False)
                    state.update(phase_signal_deg=None,exercise=self.name,motion_amount_deg=None,
                                 calibration_error='reference_too_close_to_target')
                    return state
                self.baseline=base.get('captured_at_s')
            if self.exercise in ('1','8'):signal=m['value']
            elif self.exercise=='2':
                hip=v['hip_flexion_proxy_deg'];initial=base['hip_flexion_proxy_deg']
                # Leg bending invalidates a straight-leg-raise attempt.
                if 'thigh_delta_deg' in v:
                    amount=v['thigh_delta_deg']
                elif hip is not None and initial is not None:amount=hip-initial
                if amount is not None and m['value']>=self.rules.slr_min_knee_deg:
                    signal=90+max(0,amount) if -20<=amount<=90 else None
            else:
                amount=base['knee_included_deg']-m['value'];signal=90+max(0,amount) if -20<=amount<=90 else None
        count=len(self.reps)
        too_high=self.exercise=='2' and amount is not None and amount>self.rules.slr_target_max_deg
        if too_high and self.engine.active:self.engine.active['hold_start']=None
        state=self.engine.update(t,signal,ready and signal is not None,bridge and ready)
        if too_high and self.engine.active:self.engine.active['hold_start']=None
        state['phase_signal_deg']=state.pop('smoothed_included_deg')
        state['smoothed_included_deg']=m['value'] if m['visible'] else None
        state['exercise']=self.name
        state['motion_amount_deg']=amount
        state['effective_rest_max_deg']=self.engine.config.rest_max_deg
        state['effective_start_deg']=self.engine.config.start_deg
        phases={'1':('伸膝','保持','放下'),'2':('抬腿','保持','放下'),'6':('下蹲','底部','起身'),'8':('起身','站立','坐下')}
        state['phase_label']={'waiting_for_rest':'等待起始姿势','rest':'准备',**dict(zip(('extending','holding','returning'),phases[self.exercise]))}[self.state]
        if len(self.reps)>count:
            r=self.reps[-1];r['exercise']=self.name;r['experimental']=self.exercise!='1'
            if self.exercise in ('2','6'):
                # Never mislabel the internal 90-degree-offset phase signal as anatomy.
                r['max_motion_delta_deg']=r.pop('max_included_deg')-90
                r['min_motion_delta_deg']=r.pop('min_included_deg')-90
                r['phase_signal_offset_deg']=90
            r['movement_to_first_peak_s']=r.pop('extension_to_first_peak_s')
            if self.exercise=='1':
                r['extension_to_first_peak_s']=r['movement_to_first_peak_s']
                r['knee_start_deg']=self.engine.config.rest_max_deg-10
                r['knee_peak_deg']=r['max_included_deg']
                r['knee_excursion_deg']=r['knee_peak_deg']-r['knee_start_deg']
                r['target_knee_included_deg']=self.engine.config.target_deg
                r['target_reached']=r['target_comparison']['amplitude_met']
                r['target_completed']=bool(r['target_comparison']['amplitude_met'] and
                                           r['target_comparison']['hold_met'])
        return state
