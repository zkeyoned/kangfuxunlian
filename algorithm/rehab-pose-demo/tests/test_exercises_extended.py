import unittest
from rehab_pose.exercise_rules import ExerciseFeedback,ExerciseRulesConfig
from rehab_pose.exercises import ExerciseAnalyzer,NAMES
from rehab_pose.core import Config
from rehab_pose.assessment import assess
from rehab_pose.session import TrainingPlan,TrainingSession


def measured(knee=175,amount=0,trunk=0,hip=0,speed=0):
    return {'calibration':{'baseline':{'captured_at_s':0,'knee_included_deg':180,'hip_flexion_proxy_deg':0}},
            'measurement_metrics':{'knee_included_deg':knee,'knee_flexion_deg':180-knee,
             'thigh_delta_deg':amount,'trunk_signed_deg':trunk,'trunk_delta_deg':trunk,
             'hip_flexion_proxy_deg':hip,'knee_velocity_deg_s':speed}}


class ExtendedExerciseTests(unittest.TestCase):
    def test_slr_uses_thigh_speed_not_knee_speed(self):
        f=ExerciseFeedback('2');events=[]
        for i in range(10):
            m=measured(amount=i*5);events+=f.update(i*.04,m,'extending')
        self.assertIn('SLR_TOO_FAST',[e['code'] for e in events])
        self.assertAlmostEqual(m['measurement_metrics']['leg_raise_velocity_deg_s'],125)
        self.assertEqual(m['measurement_metrics']['knee_velocity_deg_s'],0)

    def test_slr_bend_alert_not_muscle_diagnosis(self):
        f=ExerciseFeedback('2');events=[]
        for i in range(10):events+=f.update(i*.05,measured(knee=150,amount=35),'extending')
        self.assertIn('SLR_KNEE_BENT',[e['code'] for e in events])

    def test_slr_five_second_hold_and_overheight(self):
        for top,hold_met in [(35,True),(60,False)]:
            a=ExerciseAnalyzer('2',Config())
            seq=[0]*10+list(range(0,top+1,5))+[top]*60+list(range(top,-1,-5))+[0]*10
            for i,v in enumerate(seq):a.update(i*.1,{'visible':True,'value':175},measured(amount=v))
            self.assertEqual(len(a.reps),1)
            self.assertEqual(a.reps[0]['target_comparison']['hold_met'],hold_met)

    def test_squat_depth_and_forward(self):
        f=ExerciseFeedback('6');events=[]
        for i in range(10):events+=f.update(i*.05,measured(knee=80,trunk=25),'holding')
        self.assertEqual({e['code'] for e in events},{'SQUAT_TOO_DEEP','SQUAT_FORWARD'})

    def test_sit_to_stand_normal_forward_not_error(self):
        f=ExerciseFeedback('8');events=[]
        for i in range(10):events+=f.update(i*.05,measured(knee=110,trunk=35,hip=65),'extending')
        self.assertEqual(events,[])
        for i in range(10,20):events+=f.update(i*.05,measured(knee=175,trunk=30,hip=35),'holding')
        self.assertIn('STS_TOP_NOT_UPRIGHT',[e['code'] for e in events])

    def test_unreliable_suppresses_all_new_feedback(self):
        for ex in ('2','6','8'):
            f=ExerciseFeedback(ex);m=measured();m['measurement_metrics']['knee_included_deg']=None
            self.assertEqual(f.update(0,m,'holding'),[])

    def test_each_new_exercise_has_report(self):
        from dataclasses import asdict
        for ex in ('2','6','8'):
            s={'exercise':NAMES[ex],'exercise_rules':asdict(ExerciseRulesConfig()),'effective_parameters':asdict(Config()),
               'calibrations':[],'repetitions':[],'interrupted_attempts':[],'unsupported_checks':['受力']}
            report=assess(s,[])
            self.assertTrue(report['supported']);self.assertEqual(report['counts']['met'],0)
            self.assertEqual(report['unsupported_checks'],['受力'])

    def test_user_stop_is_incomplete(self):
        s=TrainingSession(TrainingPlan(3,10,5));s.finish(1,'stopped_by_user')
        self.assertEqual(s.status,'ended_incomplete')
