import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from live_api import LiveAnalyzer
from test_v04 import observed
from rehab_pose.session import TrainingPlan, TrainingSession

class LiveBridgeTests(unittest.TestCase):
    def make(self, facing="right"):
        with patch("live_api.RTMPoseModel") as model:
            a=LiveAnalyzer("1","right",facing,1,10)
        a.model.detect.return_value=([],"locked")
        a.tracker=MagicMock()
        return a

    def run_angle(self,a,t,angle):
        a.tracker.update.return_value=(observed(angle),{"quality_flags":[],"measurement_source":"observed"})
        return a.process(np.zeros((480,640,3),np.uint8),t)

    def test_complete_cycle_counts_even_if_hold_short(self):
        a=self.make()
        sequence=[90]*35+list(range(90,176,5))+[175]*8+list(range(175,89,-5))+[90]*10
        for i,angle in enumerate(sequence):r=self.run_angle(a,.001+i*.1,angle)
        self.assertEqual(r["completed_reps"],1)
        self.assertEqual(r["training_progress"]["reps_in_set"],1)
        self.assertFalse(a.analyzer.reps[0]["target_comparison"]["hold_met"])

    def test_wrong_direction_is_explained_and_does_not_count(self):
        a=self.make("left")
        for i in range(35):r=self.run_angle(a,.001+i*.1,90)
        self.assertIsNone(r["calibration"]["baseline"])
        self.assertIn("朝向",r["guidance"]["message"])
        self.assertEqual(r["completed_reps"],0)

    def test_reselection_clears_reference(self):
        a=self.make()
        for i in range(35):self.run_angle(a,.001+i*.1,90)
        self.assertIsNotNone(a.measures.baseline)
        a.select_subject({"reset":True})
        self.assertIsNone(a.measures.baseline)
        self.assertEqual(a.model.subject.status,"select_subject")

    def test_rest_cycles_are_not_counted_and_report_is_grouped(self):
        a=self.make()
        a.training=TrainingSession(TrainingPlan(sets=2,reps_per_set=1,hold_s=3,rest_s=30))
        sequence=[90]*35+list(range(90,176,5))+[175]*8+list(range(175,89,-5))+[90]*10
        for i,angle in enumerate(sequence):self.run_angle(a,.001+i*.1,angle)
        self.assertEqual(a.training.status,'resting')
        for i,angle in enumerate(sequence,len(sequence)):self.run_angle(a,.001+i*.1,angle)
        self.assertEqual(len(a.analyzer.reps),1)
        result=a.result()
        self.assertEqual(result['brief_report']['sets'][0]['completed_reps'],1)
        self.assertEqual(result['brief_report']['sets'][1]['completed_reps'],0)
        self.assertIs(result,a.result())

    def test_occlusion_aborts_active_attempt(self):
        a=self.make()
        sequence=[90]*35+list(range(90,176,5))
        for i,angle in enumerate(sequence):self.run_angle(a,.001+i*.1,angle)
        self.assertIsNotNone(a.analyzer.engine.active)
        a.model.detect.return_value=([],'subject_temporarily_lost')
        a.tracker.update.return_value=({'visible':False,'value':None,'keypoints':{}},{'quality_flags':[]})
        a.process(np.zeros((480,640,3),np.uint8),len(sequence)*.1+.001)
        self.assertIsNone(a.analyzer.engine.active)
        self.assertEqual(len(a.analyzer.reps),0)
