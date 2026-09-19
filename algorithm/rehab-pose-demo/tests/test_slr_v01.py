import unittest, math
from rehab_pose.slr import SupineAnalyzer
class SlrTests(unittest.TestCase):
 def run_cycle(self, angle=30, flex=5, split=False, lost=False, direction=1):
  a=SupineAnalyzer();a.set_surface([[.2,.7],[.8,.7]] if direction==1 else [[.8,.7],[.2,.7]])
  t=0
  def feed(deg,f=5,n=1,valid=True):
   nonlocal t
   for _ in range(n):
    t=round(t+.05,6);h={'x':500,'y':700,'confidence':1}
    k={'x':500+direction*200*math.cos(math.radians(deg)),'y':700-200*math.sin(math.radians(deg)),'confidence':1}
    p={'hip':h,'knee':k,'shoulder':{'x':500-direction*200,'y':700,'confidence':1},'ankle':{'x':k['x']+direction*200,'y':k['y'],'confidence':1}}
    a.process(t,{'visible':valid,'value':180-f,'keypoints':p},1000,1000)
  feed(0,n=60)
  for i in range(41):feed(angle*i/40,flex)
  if split:
   feed(angle,flex,40);feed(angle,flex,8,not lost) if lost else feed(45,flex,12);feed(angle,flex,60)
  else:feed(angle,flex,110)
  for i in range(41):feed(angle*(1-i/40),flex)
  feed(0,n=20)
  return a
 def test_five_examples_and_mirror(self):
  for d in (1,-1):
   a=self.run_cycle(direction=d);self.assertEqual(len(a.reps),1);self.assertTrue(a.reps[0]['target_completed'])
  a=self.run_cycle(flex=25);self.assertEqual(len(a.reps),1);self.assertFalse(a.reps[0]['target_completed']);self.assertGreater(a.reps[0]['bend_event_count'],0)
  a=self.run_cycle(angle=18);self.assertEqual(len(a.reps),1);self.assertFalse(a.reps[0]['target_completed'])
  for lost in (True,False):
   a=self.run_cycle(split=True,lost=lost);self.assertEqual(len(a.reps),1);self.assertLess(a.reps[0]['target_hold_s'],5);self.assertFalse(a.reps[0]['target_completed'])
  self.assertEqual(len(self.run_cycle(angle=0).reps),0)
if __name__=='__main__':unittest.main()
