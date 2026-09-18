import math
import unittest
from rehab_pose.core import Config, Analyzer, angle, metrics


def sequence(analyzer,values,start=0,step=.05):
    for i,value in enumerate(values):
        analyzer.update(round(start+i*step,6),value,value is not None)
    return round(start+len(values)*step,6)


def full_cycle():
    return [90]*10+list(range(95,171,5))+[170]*50+list(range(165,89,-5))+[90]*10


class CoreTests(unittest.TestCase):
    def test_geometry(self):
        self.assertAlmostEqual(angle((0,0),(0,1),(1,1)),90)
        self.assertAlmostEqual(angle((0,0),(0,1),(0,2)),180)
        self.assertIsNone(angle((0,0),(0,0),(0,2)))

    def test_aspect_ratio(self):
        points=[dict(x=.5,y=.5,visibility=1,presence=1) for _ in range(33)]
        for idx,x,y in ((23,.25,.25),(25,.5,.5),(27,.75,.25)):
            points[idx].update(x=x,y=y)
        result=metrics(points,200,100)
        self.assertAlmostEqual(result["value"],126.86989765)
        points[25]["visibility"]=.2
        self.assertFalse(metrics(points,200,100)["visible"])

    def test_complete_and_hold(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        sequence(a,full_cycle())
        self.assertEqual(len(a.reps),1)
        self.assertTrue(a.reps[0]["target_comparison"]["hold_met"])
        self.assertAlmostEqual(a.reps[0]["max_included_deg"],170)

    def test_two_cycles_no_duplicate_at_rest(self):
        a=Analyzer()
        sequence(a,full_cycle()+full_cycle()+[90]*100)
        self.assertEqual(len(a.reps),2)

    def test_low_amplitude_count_separate_from_target(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        sequence(a,[90]*10+list(range(95,146,5))+list(range(140,89,-5))+[90]*10)
        self.assertEqual(len(a.reps),1)
        self.assertFalse(a.reps[0]["target_comparison"]["amplitude_met"])

    def test_occlusion_does_not_create_rep(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        t=sequence(a,[90]*10+list(range(95,171,5))+[None]*3+[170]*20+list(range(165,89,-5))+[90]*10)
        self.assertEqual(len(a.reps),0)
        sequence(a,full_cycle(),t)
        self.assertEqual(len(a.reps),1)
        self.assertEqual(a.interrupted[0]["reason"],"unreliable_detection")

    def test_start_mid_rep_and_incomplete(self):
        a=Analyzer(Config(smoothing_tau_s=0))
        sequence(a,[170]*40+list(range(165,89,-5))+[90]*10+list(range(95,171,5)))
        a.finish()
        self.assertEqual(len(a.reps),0)
        self.assertEqual(a.interrupted[0]["reason"],"end_before_return")

    def test_gap_and_invalid_time(self):
        a=Analyzer()
        t=sequence(a,[90]*10+list(range(95,171,5)))
        sequence(a,[170]*10+list(range(165,89,-5))+[90]*10,t+2)
        self.assertEqual(len(a.reps),0)
        with self.assertRaises(ValueError):
            a.update(0,90)

    def test_time_not_frame_count(self):
        def run(step):
            a=Analyzer(Config(smoothing_tau_s=0))
            t=0
            while t<7:
                value=90 if t<1 else 90+80*(t-1) if t<2 else 170 if t<5 else 170-80*(t-5) if t<6 else 90
                a.update(t,value)
                t+=step
            return a.reps[0]
        self.assertAlmostEqual(run(.02)["target_hold_s"],run(.05)["target_hold_s"],delta=.1)

    def test_bad_config(self):
        with self.assertRaises(ValueError):
            Config(start_deg=170,target_deg=160)
        with self.assertRaises(ValueError):
            Config(min_hold_s=-1)


if __name__=="__main__":
    unittest.main()
