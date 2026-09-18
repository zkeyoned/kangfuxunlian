import math
import unittest
import numpy as np
from rehab_pose.subject import SubjectLock
from rehab_pose.measures import MotionMeasures,MeasureConfig
from rehab_pose.core import Config
from rehab_pose.exercises import ExerciseAnalyzer
from rehab_pose.tracking import OneEuro,TrackingConfig


def observed(knee=90,trunk=0,hipflex=90):
    h={'x':200.,'y':250.,'confidence':.9}
    s={'x':200+150*math.sin(math.radians(trunk)),'y':250-150*math.cos(math.radians(trunk)),'confidence':.9}
    return dict(visible=True,value=knee,keypoints={'hip':h,'shoulder':s,
                'knee':dict(x=350.,y=250.,confidence=.9),'ankle':dict(x=350.,y=450.,confidence=.9)})


def measure_ready(exercise):
    return dict(calibration={'baseline':{'knee_included_deg':180 if exercise=='6' else 90,
                                        'hip_flexion_proxy_deg':0}},
                measurement_metrics={'hip_flexion_proxy_deg':0})


class SubjectTests(unittest.TestCase):
    def setUp(self):
        self.s=SubjectLock();self.a=np.array([1.,0.]);self.b=np.array([0.,1.])
        self.box=[10,10,110,210]

    def test_requires_confirmation(self):
        self.assertIsNone(self.s.update([self.box],[self.a])[0])
        self.s.confirm();self.assertEqual(self.s.update([self.box],[self.a])[0],0)

    def test_distant_bystander_does_not_change_subject(self):
        self.s.update([self.box],[self.a]);self.s.confirm();self.s.update([self.box],[self.a])
        idx,status=self.s.update([[300,10,400,210],[12,10,112,210]],[self.b,self.a])
        self.assertEqual(idx,1);self.assertEqual(status,'locked')

    def test_crossing_pauses_and_never_auto_reacquires(self):
        self.s.update([self.box],[self.a]);self.s.confirm();self.s.update([self.box],[self.a])
        self.assertIsNone(self.s.update([self.box,[30,10,130,210]],[self.a,self.b])[0])
        self.assertIsNone(self.s.update([self.box],[self.a])[0])
        self.s.confirm();self.assertEqual(self.s.update([self.box],[self.a])[0],0)
        self.assertEqual(self.s.generation,2)

    def test_appearance_swap_rejected(self):
        self.s.update([self.box],[self.a]);self.s.confirm();self.s.update([self.box],[self.a])
        self.assertIsNone(self.s.update([self.box],[self.b])[0])

    def test_multiple_people_require_click(self):
        boxes=[self.box,[300,10,400,210]]
        self.s.update(boxes,[self.a,self.b]);self.s.confirm()
        self.assertIsNone(self.s.update(boxes,[self.a,self.b])[0])
        self.s.click(350,100);self.s.confirm()
        self.assertEqual(self.s.update(boxes,[self.a,self.b])[0],1)


class MeasureTests(unittest.TestCase):
    def test_reference_and_signed_angles(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        for i in range(15):out=m.update(i*.05,observed(),640,480)
        self.assertEqual(out['calibration']['status'],'ready')
        out=m.update(.8,observed(trunk=20),640,480)
        self.assertAlmostEqual(out['measurement_metrics']['trunk_delta_deg'],20)
        out=m.update(.9,observed(trunk=-10),640,480)
        self.assertAlmostEqual(out['measurement_metrics']['trunk_delta_deg'],-10)

    def test_wrong_direction_does_not_calibrate_seated(self):
        m=MotionMeasures('left',MeasureConfig(calibration_s=.5))
        for i in range(20):out=m.update(i*.05,observed(),640,480)
        self.assertIsNone(out['calibration']['baseline'])

    def test_missing_shoulder_keeps_knee_available(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5));p=observed();p['keypoints']['shoulder']['confidence']=0
        for i in range(15):out=m.update(i*.05,p,640,480)
        self.assertIsNotNone(out['calibration']['baseline'])
        self.assertIsNone(out['measurement_metrics']['trunk_delta_deg'])

    def test_velocity_uses_actual_time_and_clears_after_loss(self):
        m=MotionMeasures('right')
        for t in [0,.025,.061,.112,.175]:out=m.update(t,observed(90+40*t),640,480)
        self.assertAlmostEqual(out['measurement_metrics']['knee_velocity_deg_s'],40)
        m.update(.2,{'visible':False},640,480)
        out=m.update(.23,observed(120),640,480)
        self.assertIsNone(out['measurement_metrics']['knee_velocity_deg_s'])

    def test_reference_cannot_span_lost_points(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        for i in range(9):m.update(i*.05,observed(),640,480)
        m.update(.45,{'visible':False},640,480)
        out=m.update(.5,observed(),640,480)
        self.assertIsNone(out['calibration']['baseline'])
        self.assertEqual(out['calibration']['progress'],0)

    def test_alert_dwell_cooldown_and_invalid_suppression(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        for i in range(15):m.update(i*.05,observed(),640,480)
        events=[]
        for i in range(15,35):events+=m.update(i*.05,observed(trunk=25),640,480,'holding')['feedback_events']
        self.assertEqual([e['code'] for e in events],['TRUNK_FORWARD'])
        self.assertEqual(m.update(1.8,{'visible':False},640,480,'holding')['feedback_events'],[])

    def test_long_loss_invalidates_reference(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        for i in range(15):m.update(i*.05,observed(),640,480)
        out=m.update(3.,{'visible':False},640,480)
        self.assertIsNone(out['calibration']['baseline'])


class ExerciseTests(unittest.TestCase):
    def test_each_exercise_has_separate_roundtrip_signal(self):
        for ex in ['1','2','6','8']:
            a=ExerciseAnalyzer(ex,Config(smoothing_tau_s=0));cal=measure_ready(ex)
            amounts=[0]*10+list(range(0,81,5))+[80]*10+list(range(80,-1,-5))+[0]*12
            for i,amount in enumerate(amounts):
                if ex in ('1','8'):knee=90+amount
                elif ex=='6':knee=180-amount
                else:knee=175
                cal['measurement_metrics']['hip_flexion_proxy_deg']=amount
                a.update(i*.05,observed(knee),cal)
            self.assertEqual(len(a.reps),1,ex)
            self.assertEqual(a.reps[0]['experimental'],ex!='1')
            if ex in ('2','6'):
                self.assertNotIn('max_included_deg',a.reps[0])
                self.assertEqual(a.reps[0]['max_motion_delta_deg'],80)

    def test_bent_knee_interrupts_straight_leg_raise(self):
        a=ExerciseAnalyzer('2',Config(smoothing_tau_s=0));cal=measure_ready('2')
        for i in range(10):a.update(i*.05,observed(175),cal)
        cal['measurement_metrics']['hip_flexion_proxy_deg']=30
        a.update(.5,observed(175),cal);a.update(.55,observed(130),cal)
        self.assertIsNone(a.engine.active)
        self.assertEqual(len(a.reps),0)

    def test_uncalibrated_never_counts(self):
        a=ExerciseAnalyzer('1',Config());cal={'calibration':{'baseline':None},'measurement_metrics':{}}
        for i,knee in enumerate([90]*10+[170]*10+[90]*10):a.update(i*.05,observed(knee),cal)
        self.assertEqual(len(a.reps),0)


class FilterTests(unittest.TestCase):
    def test_responsive_profile_reduces_ramp_lag_without_large_stationary_jitter(self):
        slow=OneEuro(TrackingConfig(beta=.04));fast=OneEuro(TrackingConfig(beta=8))
        for i in range(120):
            t=i/30;v=.2+.1*t;a=slow.update(t,v);b=fast.update(t,v)
        self.assertLess(v-b,v-a)
        f=OneEuro(TrackingConfig(beta=8));samples=[f.update(i/30,.5+.01*(-1)**i) for i in range(100)]
        self.assertLess(max(samples[30:])-min(samples[30:]),.01)


if __name__=='__main__':unittest.main()
