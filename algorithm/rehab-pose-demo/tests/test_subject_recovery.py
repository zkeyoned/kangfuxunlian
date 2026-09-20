import unittest
import numpy as np
from rehab_pose.subject_recovery import RecoveringSubjectLock


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.s=RecoveringSubjectLock()
        self.a=np.array([1.,0.]);self.b=np.array([0.,1.])
        self.box=[0,0,100,200]
        self.s.confirm()
        self.assertEqual(self.s.update([self.box],[self.a],0),(0,'locked'))

    def test_bystander_with_small_overlap_does_not_unlock(self):
        i,status=self.s.update([[80,0,180,200],self.box],[self.b,self.a],.1)
        self.assertEqual((i,status),(1,'locked'))

    def test_short_occlusion_recovers_only_original(self):
        self.assertEqual(self.s.update([self.box,[30,0,130,200]],[self.a,self.b],.1)[1],'subject_temporarily_lost')
        self.assertIsNone(self.s.update([self.box],[self.b],.2)[0])
        for t in (.3,.4):self.assertIsNone(self.s.update([self.box],[self.a],t)[0])
        self.assertEqual(self.s.update([self.box],[self.a],.5),(0,'locked'))
        self.assertEqual(self.s.generation,1)
        self.assertEqual(self.s.recoveries,1)

    def test_long_occlusion_needs_confirmation(self):
        self.s.update([],[],.1)
        self.assertEqual(self.s.update([self.box],[self.a],3.2)[1],'subject_lost_reconfirm')
        self.assertIsNone(self.s.update([self.box],[self.a],3.3)[0])
        self.s.click(50,50);self.s.confirm()
        self.assertEqual(self.s.update([self.box],[self.a],3.4)[1],'locked')

    def test_lookalikes_and_overlap_are_ambiguous(self):
        self.assertIsNone(self.s.update([self.box,[10,0,110,200]],[self.a,self.a],.1)[0])

    def test_no_person_switch_when_target_leaves(self):
        self.s.update([],[],.1)
        for t in (.2,.3,.4):
            self.assertIsNone(self.s.update([[300,0,400,200]],[self.a],t)[0])

