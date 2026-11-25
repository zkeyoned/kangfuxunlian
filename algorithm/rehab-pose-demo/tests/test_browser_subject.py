import unittest
from live_api import LiveAnalyzer, validate_landmarks

class BrowserSubjectTests(unittest.TestCase):
    def test_lost_identity_cannot_forward_points(self):
        for status in ('select_subject','subject_temporarily_lost','subject_lost_reconfirm'):
            points, *_ = validate_landmarks(dict(landmarks=[{}]*33,pose_status=status,width=640,height=480,timestamp_s=1))
            self.assertEqual(points, [])

    def test_reselection_resets_baseline_without_model(self):
        a=LiveAnalyzer('1','left','auto',1,10,backend='browser')
        try:
            self.assertEqual(a.select_subject({'reset':True}), {'ok':True})
            with self.assertRaises(ValueError): a.select_subject({'x':10,'y':20})
            for i,status in enumerate(('select_subject','subject_temporarily_lost','subject_lost_reconfirm')):
                r=a.process_landmarks([],status,640,480,i+1)
                self.assertEqual(r['completed_reps'],0)
                self.assertFalse(r['visible'])
        finally: a.close()
