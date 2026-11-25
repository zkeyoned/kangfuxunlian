import unittest
from rehab_pose.core import Analyzer,Config
class SeatedRegression(unittest.TestCase):
 def make(self):
  return Analyzer(Config(rest_min_deg=79,rest_max_deg=99,start_deg=110,target_deg=170,hysteresis_deg=5,reversal_deg=5,min_hold_s=1,rest_dwell_s=.5,start_dwell_s=.2,target_dwell_s=.2,reversal_dwell_s=.2,smoothing_tau_s=0),seated=True)
 def feed(self,a,angle,n):
  for _ in range(n):a.update(round((a.last_t or 0)+.1,6),angle)
 def test_hold_band_is_not_return(self):
  a=self.make()
  for angle,n in [(89,10),(125,5),(174,10),(168,40)]:self.feed(a,angle,n)
  self.assertEqual(a.state,'holding');self.assertGreater(a.active['max_hold_s'],4)
  self.feed(a,71,10);self.assertEqual(len(a.reps),1);self.assertTrue(a.reps[0]['target_comparison']['hold_met'])
 def test_ninth_cycle_and_rest_rebound(self):
  a=self.make()
  for i in range(9):
   for angle,n in [(89,10),(125,5),(174,15),(71,3),(89,8)]:self.feed(a,angle,n)
   self.assertEqual(len(a.reps),i+1)
 def test_incomplete_return_not_counted(self):
  a=self.make()
  for angle,n in [(89,10),(125,5),(174,15),(120,15)]:self.feed(a,angle,n)
  self.assertEqual(len(a.reps),0)
 def test_gap_cannot_be_hold(self):
  a=self.make()
  for angle,n in [(89,10),(125,5),(174,5)]:self.feed(a,angle,n)
  a.update(a.last_t+1,174)
  self.assertEqual(len(a.reps),0);self.assertIsNone(a.active)
