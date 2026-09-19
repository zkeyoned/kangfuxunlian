import unittest
from rehab_pose.assessment import assess


class AssessmentTests(unittest.TestCase):
    def fixture(self):
        summary = {'exercise':'SEATED_KNEE_EXTENSION', 'calibrations':[{}],
                   'effective_parameters':{'target_deg':160, 'min_hold_s':2, 'min_return_s':1, 'max_gap_s':.3},
                   'repetitions':[{'index':1,'start_s':0,'end_s':.4,'time_to_target_s':1.1,'target_hold_s':.5,'return_s':1.2}],
                   'interrupted_attempts':[]}
        rows = [{'timestamp_s':t, 'visible':True, 'measurement_source':'observed',
                 'measurement_metrics':{'knee_included_deg':a}}
                for t,a in [(0,120),(.2,170),(.4,100)]]
        return summary, rows

    def test_complete_checks_and_excursion(self):
        s,r=self.fixture(); item=assess(s,r)['attempts'][0]
        self.assertEqual(item['measurements']['observed_excursion_deg'],70)
        self.assertEqual([c['status'] for c in item['checks']],['met','not_met','met','met'])

    def test_prediction_cannot_be_used_to_pass(self):
        s,r=self.fixture(); r[1]['bridge_pending']=True
        item=assess(s,r)['attempts'][0]
        self.assertEqual(item['status'],'unable_to_assess')
        self.assertEqual(item['measurements']['observed_max_knee_deg'],120)
        self.assertEqual(item['quality']['prediction_frame_count'],1)

    def test_interrupted_is_not_failed_exercise(self):
        s,r=self.fixture(); s['repetitions']=[]
        s['interrupted_attempts']=[{'start_s':0,'end_s':.4,'reason':'unreliable_detection'}]
        self.assertEqual(assess(s,r)['attempts'][0]['status'],'unable_to_assess')

    def test_missing_time_cannot_pass(self):
        s,r=self.fixture(); r.pop(1)
        self.assertEqual(assess(s,r)['attempts'][0]['status'],'unable_to_assess')

    def test_other_exercise_not_using_knee_target(self):
        s,r=self.fixture(); s['exercise']='SUPPORTED_MINI_SQUAT'
        report=assess(s,r)
        self.assertFalse(report['supported'])
        self.assertTrue(all(c['target_min'] is None for c in report['attempts'][0]['checks']))

