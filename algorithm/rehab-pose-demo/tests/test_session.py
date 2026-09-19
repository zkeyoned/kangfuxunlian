import unittest
from rehab_pose.session import TrainingPlan,TrainingSession


class SessionTests(unittest.TestCase):
    def test_set_boundary_and_rest(self):
        s=TrainingSession(TrainingPlan(2,1,3))
        rep={'index':1};s.record_rep(5,rep)
        self.assertEqual(s.status,'resting');self.assertEqual(rep['training_set'],1)
        s.record_rep(6,{'index':2});self.assertEqual(s.total,1)
        s.tick(34.9);self.assertEqual(s.status,'resting')
        s.tick(35);self.assertEqual(s.group,2);self.assertEqual(s.count,0)
        s.record_rep(36,{'index':2});self.assertEqual(s.status,'completed')
        s.record_rep(37,{'index':3});self.assertEqual(s.total,2)

    def test_pause_does_not_consume_rest(self):
        s=TrainingSession(TrainingPlan(2,1));s.record_rep(0,{'index':1})
        s.toggle_pause(10);s.tick(100)
        self.assertEqual(s.snapshot(100)['rest_remaining_s'],20)
        s.toggle_pause(100);s.tick(119);self.assertEqual(s.status,'resting')
        s.tick(120);self.assertEqual(s.status,'training')

    def test_paused_and_duplicate_reps_not_counted(self):
        s=TrainingSession(TrainingPlan());s.record_rep(0,{'index':1})
        s.record_rep(1,{'index':1});self.assertEqual(s.total,1)
        s.toggle_pause(2);s.record_rep(3,{'index':2});self.assertEqual(s.total,1)

    def test_invalid_plan(self):
        for args in [(0,10,2),(3,0,2),(3,10,1),(3,10,float('nan')),(True,10,2)]:
            with self.assertRaises(ValueError):TrainingPlan(*args)

    def test_nonqualified_cycle_counts_as_performed(self):
        s=TrainingSession(TrainingPlan(1,1))
        s.record_rep(1,{'index':1,'target_comparison':{'hold_met':False}})
        self.assertEqual(s.status,'completed')
