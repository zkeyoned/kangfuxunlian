import copy
import unittest
from unittest.mock import patch,MagicMock
import numpy as np
from rehab_pose.auto_facing import AutoFacing
from test_v04 import observed
from live_api import LiveAnalyzer


def mirrored(m):
    m=copy.deepcopy(m)
    for p in m['keypoints'].values():p['x']=640-p['x']
    return m


class FacingTests(unittest.TestCase):
    def test_initial_directions_and_jitter(self):
        for flip in (False,True):
            a=AutoFacing('1');m=mirrored(observed()) if flip else observed()
            for i in range(12):direction,state=a.update(i*.1,m,[],640)
            self.assertEqual(direction,'left' if flip else 'right')
            self.assertEqual(state,'ready')
            opposite=mirrored(m)
            self.assertEqual(a.update(1.2,opposite,[],640)[1],'checking_direction')
            self.assertEqual(a.update(1.3,m,[],640)[0],direction)

    def test_ambiguous_and_gaps(self):
        a=AutoFacing('1');m=observed();m['keypoints']['knee']['x']=202
        for i in range(20):direction,state=a.update(i*.1,m,[],640)
        self.assertIsNone(direction)
        for i in range(4):a.update(3+i*.1,observed(),[],640)
        self.assertIsNone(a.update(5,observed(),[],640)[0])

    def test_supine_both_directions(self):
        m=observed(180);m['keypoints']['shoulder'].update(x=60,y=250)
        for side in (m,mirrored(m)):
            a=AutoFacing('2')
            for i in range(12):direction,_=a.update(i*.1,side,[],640)
            self.assertEqual(direction,'right' if side is m else 'left')

    def test_squat_profile_initializes_but_head_turn_does_not_flip(self):
        for flip in (False,True):
            points=[{'x':0,'visibility':0,'presence':0} for _ in range(33)]
            for i,x in [(0,.55),(7,.5),(8,.5)]:points[i]={'x':1-x if flip else x,'visibility':.9,'presence':.9}
            a=AutoFacing('6')
            for i in range(12):direction,_=a.update(i*.1,observed(180),points,640)
            self.assertEqual(direction,'left' if flip else 'right')
            for p in points:p['x']=1-p['x']
            for i in range(20):after,_=a.update(1.2+i*.1,observed(180),points,640)
            self.assertEqual(after,direction)

    def test_mirrored_live_count_and_trunk_feedback(self):
        outcomes=[]
        for flip in (False,True):
            with patch('live_api.RTMPoseModel'):
                a=LiveAnalyzer('1','right','auto',1,10)
            a.model.detect.return_value=([],'locked');a.tracker=MagicMock()
            seq=[(90,0)]*45+[(90,25)]*10+[(90,-25)]*10+[(90,0)]*10+[(x,0) for x in range(90,176,5)]+[(175,0)]*32+[(x,0) for x in range(175,89,-5)]+[(90,0)]*10
            for i,(angle,trunk) in enumerate(seq):
                m=observed(angle,trunk);m=mirrored(m) if flip else m
                a.tracker.update.return_value=(m,{'quality_flags':[],'measurement_source':'observed'})
                result=a.process(np.zeros((480,640,3),np.uint8),.001+i*.1)
            codes={e['code'] for e in a.feedback_history}
            self.assertIn('TRUNK_FORWARD',codes);self.assertIn('TRUNK_BACKWARD',codes)
            self.assertEqual(result['facing'],'left' if flip else 'right')
            self.assertEqual(result['completed_reps'],1)
            outcomes.append(a.analyzer.reps[0]['knee_peak_deg'])
        self.assertAlmostEqual(*outcomes)

    def test_reselect_resets_automatic_direction(self):
        with patch('live_api.RTMPoseModel'):a=LiveAnalyzer('1','right','auto',1,10)
        a.auto_facing.facing='right';a.facing='right';a.select_subject({'reset':True})
        self.assertIsNone(a.auto_facing.facing);self.assertIsNone(a.facing)


if __name__=='__main__':unittest.main()
