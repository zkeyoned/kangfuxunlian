import unittest,math
from rehab_pose.sts import SitStandAnalyzer
class STSTests(unittest.TestCase):
 def setup_engine(self):
  a=SitStandAnalyzer();self.t=0
  def feed(p=0,knee=90,n=1,visible=True,trunk=0):
   for _ in range(n):
    self.t=round(self.t+.05,6);hy=600-200*p
    q={'hip':{'x':400,'y':hy,'confidence':1},'shoulder':{'x':400+200*math.sin(math.radians(trunk)),'y':hy-200*math.cos(math.radians(trunk)),'confidence':1},'knee':{'x':480,'y':700,'confidence':1},'ankle':{'x':480,'y':900,'confidence':1}}
    a.process(self.t,{'visible':visible,'value':knee,'keypoints':q},1000,1000)
  a.calibrate('sit',{'assistance':'none'});feed(n=50)
  self.assertEqual(a.stage,'need_stand')
  a.calibrate('stand');feed(1,170,50);self.assertEqual(a.stage,'confirm_stand')
  self.assertEqual(len(a.reps),0);a.calibrate('confirm');feed(n=20)
  return a,feed
 def movement(self,f,top=1,up=True):
  for i in range(41):
   p=top*(i/40 if up else 1-i/40);f(p,90+80*p)
 def test_normal(self):
  a,f=self.setup_engine();self.movement(f);f(1,170,25);self.movement(f,up=False);f(n=20)
  self.assertEqual(len(a.reps),1);self.assertTrue(a.reps[0]['goal_met'])
 def test_seated_extension(self):
  a,f=self.setup_engine();f(0,170,100);f(n=20);self.assertEqual(len(a.reps),0);self.assertEqual(len(a.attempts),0)
 def test_half_rise(self):
  a,f=self.setup_engine();self.movement(f,.5);f(.5,130,20);self.movement(f,.5,False);f(n=20)
  self.assertEqual(len(a.reps),0);self.assertEqual(len(a.attempts),1);self.assertFalse(a.attempts[0]['standing_reached'])
 def test_short_hold(self):
  a,f=self.setup_engine();self.movement(f);f(1,170,10);self.movement(f,up=False);f(n=20)
  self.assertEqual(len(a.reps),1);self.assertFalse(a.reps[0]['goal_met'])
 def test_standing_without_return(self):
  a,f=self.setup_engine();self.movement(f);f(1,170,40);a.finish()
  self.assertEqual(len(a.reps),0);self.assertTrue(a.attempts[0]['standing_reached'])
 def test_lean_and_occlusion(self):
  a,f=self.setup_engine();f(n=40,trunk=40);f(n=20);self.assertEqual(len(a.reps),0)
  self.movement(f);f(1,170,40);f(1,170,5,False);self.movement(f,up=False);f(n=20)
  self.assertEqual(len(a.reps),0);self.assertEqual(a.attempts[0]['evaluation_status'],'unable_to_evaluate')
if __name__=='__main__':unittest.main()
