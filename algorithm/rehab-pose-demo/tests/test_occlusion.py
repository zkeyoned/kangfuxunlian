import unittest

from rehab_pose.tracking import PoseTracker
from rehab_pose.core import Analyzer, Config
from test_tracking import pose


def warmed():
    tracker=PoseTracker()
    for i in range(15):
        tracker.update(i*.04,pose(),640,480)
    return tracker


def hidden():
    p=pose(); p[27]['visibility']=.1
    return p


class OcclusionTests(unittest.TestCase):
    def test_prediction_separate_and_two_frame_recovery(self):
        tr=warmed()
        m,q=tr.update(.60,hidden(),640,480)
        self.assertFalse(m['visible'])
        self.assertIsNone(m['value'])
        self.assertTrue(q['bridge_pending'])
        self.assertEqual(q['display_prediction']['keypoints']['ankle']['source'],'predicted')
        m,q=tr.update(.64,pose(),640,480)
        self.assertTrue(q['bridge_pending'])
        m,q=tr.update(.68,pose(),640,480)
        self.assertTrue(m['visible'])
        self.assertFalse(q['bridge_pending'])
        self.assertIn('recovered_after_short_gap',q['quality_flags'])

    def test_persistent_loss_times_out_and_reacquires(self):
        tr=warmed()
        for t in [.60,.64,.68,.72,.76,.80,.84]:
            m,q=tr.update(t,hidden(),640,480)
        self.assertFalse(q['bridge_pending'])
        self.assertIsNone(q['display_prediction'])
        m,q=tr.update(.88,pose(),640,480)
        self.assertIn('stabilizing',q['quality_flags'])

    def test_out_of_frame_never_predicted(self):
        tr=warmed(); p=hidden(); p[27]['x']=1.1
        m,q=tr.update(.60,p,640,480)
        self.assertFalse(q['bridge_pending'])
        self.assertIsNone(q['display_prediction'])

    def test_two_missing_joints_never_predicted(self):
        tr=warmed(); p=hidden(); p[25]['visibility']=.1
        m,q=tr.update(.60,p,640,480)
        self.assertFalse(q['bridge_pending'])

    def test_recovery_mismatch_rejected(self):
        tr=warmed(); tr.update(.60,hidden(),640,480)
        p=pose(.08)
        m,q=tr.update(.64,p,640,480)
        self.assertFalse(m['visible'])
        self.assertIn('recovery_mismatch',q['quality_flags'])
        self.assertFalse(q['bridge_pending'])

    def test_visible_joints_moving_inconsistently_reject_prediction(self):
        tr=warmed(); p=hidden(); p[23]['x']+=.12
        m,q=tr.update(.60,p,640,480)
        self.assertFalse(q['bridge_pending'])

    def test_long_timestamp_gap_does_not_bridge(self):
        tr=warmed()
        m,q=tr.update(1.0,hidden(),640,480)
        self.assertFalse(q['bridge_pending'])

    def test_prediction_stays_inside_image(self):
        tr=warmed()
        m,q=tr.update(.60,hidden(),640,480)
        for p in q['display_prediction']['keypoints'].values():
            self.assertTrue(0<=p['x']<=640 and 0<=p['y']<=480)

    def test_hold_not_accumulated_through_gap_and_rep_flagged(self):
        a=Analyzer(Config(smoothing_tau_s=0,min_hold_s=.4))
        t=0
        for angle in [90]*10+[120,140,165,170,170,170]:
            a.update(t,angle);t=round(t+.05,6)
        previous_max=a.active['max_hold_s']
        a.update(t,None,False,True);t+=.05
        a.update(t,None,False,True);t+=.05
        self.assertEqual(a.active['max_hold_s'],previous_max)
        for angle in [170,170,160,140,110]+[90]*8:
            a.update(t,angle);t+=.05
        self.assertEqual(len(a.reps),1)
        rep=a.reps[0]
        self.assertTrue(rep['needs_review'])
        self.assertFalse(rep['target_comparison']['hold_met'])
        self.assertIsNone(rep['return_s'])
        self.assertIsNone(rep['target_comparison']['return_time_met'])
        self.assertLess(rep['target_hold_s'],.4)

    def test_predictions_alone_cannot_finish_rep(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        for i,angle in enumerate([90]*10+[120,170]): a.update(i*.05,angle)
        for i in range(12,25): a.update(i*.05,None,False,True)
        self.assertEqual(len(a.reps),0)
        self.assertIsNone(a.active)

    def test_rest_dwell_cannot_cross_prediction(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        a.update(0,90);a.update(.1,90)
        a.update(.15,None,False,True)
        a.update(.2,90);a.update(.3,90)
        self.assertEqual(a.state,'waiting_for_rest')


if __name__=='__main__': unittest.main()
