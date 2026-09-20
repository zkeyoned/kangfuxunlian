import unittest, math
from rehab_pose.squat import SquatAnalyzer

class SquatTests(unittest.TestCase):
 def engine(self,hold=1):
  a=SquatAnalyzer(dict(target_deg=30,hold_s=hold,return_s=1,rest_s=30));self.t=0
  a.configure(dict(support='chair',support_confirmed=True))
  def feed(f=0,n=1,visible=True,trunk=0,drop=None):
   for _ in range(n):
    self.t=round(self.t+.05,6);hy=500+200*(f/300 if drop is None else drop)
    p={'hip':{'x':400,'y':hy,'confidence':1},'shoulder':{'x':400+200*math.sin(math.radians(trunk)),'y':hy-200*math.cos(math.radians(trunk)),'confidence':1},'knee':{'x':480,'y':700,'confidence':1},'ankle':{'x':480,'y':900,'confidence':1}}
    a.process(self.t,dict(visible=visible,value=180-f,keypoints=p),1000,1000)
  feed(n=65);self.assertEqual(a.stage,'ready');return a,feed
 def ramp(self,f,start,end):
  for i in range(41):f(start+(end-start)*i/40)
 def cycle(self,f,peak=30):
  self.ramp(f,0,peak);f(peak,25);self.ramp(f,peak,0);f(n=20)
 def test_normal(self):
  a,f=self.engine();self.cycle(f);self.assertEqual(len(a.reps),1);self.assertTrue(a.reps[0]['goal_met'])
 def test_waist_only(self):
  a,f=self.engine();f(n=80,trunk=40,drop=.1);f(n=20);self.assertEqual(len(a.reps),0)
 def test_shallow_complete(self):
  a,f=self.engine();self.cycle(f,18);self.assertEqual(len(a.reps),1);self.assertFalse(a.reps[0]['goal_met'])
 def test_depth_latches(self):
  a,f=self.engine();self.ramp(f,0,50);f(50,20);self.ramp(f,50,30);f(30,25);self.ramp(f,30,0);f(n=20)
  self.assertEqual(len(a.reps),1);self.assertFalse(a.reps[0]['goal_met']);self.assertTrue(a.reps[0]['depth_exceeded'])
 def test_gap_not_accumulated(self):
  a,f=self.engine();f(30,12);f(30,2,False);f(30,14);f(0,20)
  self.assertEqual(len(a.reps),0);self.assertEqual(a.attempts[0]['evaluation_status'],'unable_to_evaluate');self.assertLess(a.attempts[0]['target_hold_s'],1)
 def test_bottom_pulses(self):
  a,f=self.engine();self.ramp(f,0,30)
  for _ in range(3):f(24,10);f(32,10)
  self.assertEqual(len(a.reps),0);self.ramp(f,32,0);f(n=20);self.assertEqual(len(a.reps),1)
 def test_identity_change(self):
  a,f=self.engine();self.ramp(f,0,30);a.abort(self.t,'subject_selection');f(n=20)
  self.assertEqual(len(a.reps),0);self.assertEqual(a.attempts[0]['evaluation_status'],'unable_to_evaluate')
 def test_no_pause_and_normal_forward_lean(self):
  a,f=self.engine(0);self.ramp(f,0,30);f(30,8,trunk=25);self.ramp(f,30,0);f(n=20)
  self.assertTrue(a.reps[0]['goal_met']);self.assertEqual(a.reps[0]['pause_mode'],'no_pause')

if __name__=='__main__':unittest.main()
