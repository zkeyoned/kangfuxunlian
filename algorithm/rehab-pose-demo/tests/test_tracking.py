import math
import unittest
from rehab_pose.tracking import OneEuro,TrackingConfig,PoseTracker
from rehab_pose.model import coco_to_landmarks
from rehab_pose.model import RTMPoseModel
from unittest.mock import Mock
import numpy as np


def pose(offset=0):
    p=[dict(x=.5,y=.5,visibility=0.,presence=0.) for _ in range(33)]
    for i,x,y in ((11,.3,.15),(23,.3,.45),(25,.6,.45),(27,.6,.85)):
        p[i]=dict(x=x+offset,y=y,visibility=.95,presence=.95)
    return p


class TrackingTests(unittest.TestCase):
    def test_detected_mode_does_not_hallucinate_full_frame(self):
        model=RTMPoseModel.__new__(RTMPoseModel)
        model.roi_mode="detected"
        model.detector=Mock(return_value=[])
        model.pose=Mock()
        points,status=model.detect(np.zeros((480,640,3),np.uint8),0)
        self.assertEqual(status,"no_person")
        model.pose.assert_not_called()

    def test_fixed_mode_explicitly_marked(self):
        model=RTMPoseModel.__new__(RTMPoseModel)
        model.roi_mode="full-frame"
        model.detector=Mock()
        model.pose=Mock(return_value=(np.zeros((1,17,2)),np.ones((1,17))))
        points,status=model.detect(np.zeros((480,640,3),np.uint8),0)
        self.assertEqual(status,"assumed_single_person_roi")
        model.detector.assert_not_called()
        self.assertEqual(len(points),33)

    def test_coco_mapping_and_score(self):
        p=coco_to_landmarks([(i*10,i*5) for i in range(17)],[.8]*17,640,480)
        self.assertAlmostEqual(p[25]['x'],130/640)
        self.assertAlmostEqual(p[28]['y'],80/480)
        self.assertEqual(p[11]['visibility'],.8)
        self.assertEqual(p[32]['visibility'],0)

    def test_no_pose_and_reacquire(self):
        t=PoseTracker()
        for i in range(10):
            m,q=t.update(i*.05,pose(),640,480)
        self.assertTrue(m['visible'])
        m,q=t.update(.5,[],640,480)
        self.assertFalse(m['visible'])
        self.assertEqual(m['keypoints'],{})
        m,q=t.update(.55,pose(),640,480)
        self.assertIn('stabilizing',q['quality_flags'])

    def test_outside_not_clamped(self):
        t=PoseTracker()
        p=pose(); p[27]['y']=1.2
        m,q=t.update(0,p,640,480)
        self.assertIn('ankle_out_of_frame',q['quality_flags'])
        self.assertFalse(m['visible'])

    def test_jump_filtered_before_smoothing(self):
        t=PoseTracker()
        for i in range(10): t.update(i*.05,pose(),640,480)
        p=pose(); p[27]['x']=.9; p[27]['y']=.5
        m,q=t.update(.5,p,640,480)
        self.assertFalse(m['visible'])
        self.assertIn('keypoint_jump',q['quality_flags'])
        self.assertEqual(m['keypoints'],{})

    def test_invalid_timestamp(self):
        t=PoseTracker(); t.update(1,pose(),640,480)
        with self.assertRaises(ValueError): t.update(1,pose(),640,480)

    def test_filter_reduces_stationary_jitter(self):
        f=OneEuro(TrackingConfig())
        samples=[.5+.01*(-1)**i for i in range(100)]
        filtered=[f.update(i/30,x) for i,x in enumerate(samples)]
        self.assertLess(max(filtered[30:])-min(filtered[30:]),.01)

    def test_side_switch_suspected_not_auto_swapped(self):
        t=PoseTracker()
        for i in range(10): t.update(i*.05,pose(),640,480)
        p=pose()
        for a,b in ((11,12),(23,24),(25,26),(27,28)): p[b]=dict(p[a])
        p[25]['x']+=.12; p[27]['x']+=.12
        m,q=t.update(.5,p,640,480)
        self.assertIn('possible_side_switch',q['quality_flags'])
        self.assertFalse(m['visible'])

    def test_missing_shoulder_does_not_block_knee(self):
        t=PoseTracker()
        p=pose(); p[11]['visibility']=0
        for i in range(10): m,q=t.update(i*.05,p,640,480)
        self.assertTrue(m['visible'])
        self.assertIsNone(m['aux']['trunk_unsigned_tilt_deg'])

    def test_slow_movement_is_accepted(self):
        t=PoseTracker()
        for i in range(20): m,q=t.update(i*.05,pose(i*.001),640,480)
        self.assertTrue(m['visible'])
        self.assertLess(m['keypoints']['hip']['x'],q['raw_metrics']['keypoints']['hip']['x'])


if __name__=='__main__': unittest.main()
