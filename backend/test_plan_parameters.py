import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'algorithm/rehab-pose-demo'))
from plan_parameters import apply_targets,validate_targets
from rehab_pose.exercises import ExerciseAnalyzer
from rehab_pose.core import Config
from rehab_pose.exercise_rules import ExerciseRulesConfig
from rehab_pose.session import TrainingPlan

class ParametersTests(unittest.TestCase):
    def test_real_engines_and_session(self):
        for ex,angle,signal in [('1',175,175),('2',35,125),('6',45,135),('8',170,170)]:
            with self.subTest(exercise=ex):
                r=ExerciseRulesConfig();a=ExerciseAnalyzer(ex,Config(),rules=r)
                apply_targets(ex,dict(target_deg=angle,hold_s=4,return_s=2,rest_s=45),a,r)
                self.assertEqual(a.engine.config.target_deg,signal)
                self.assertEqual(a.engine.config.min_hold_s,4)
                self.assertEqual(a.engine.config.min_return_s,2)
        self.assertEqual(TrainingPlan(2,7,4,45).rest_s,45)
    def test_reject_unknown_and_bad_range(self):
        for values in [dict(target_deg=999,hold_s=3,return_s=2,rest_s=30),dict(target_deg=175,hold_s=3,return_s=2,rest_s=float('nan')),dict(target_deg=175)]:
            with self.assertRaises(ValueError):validate_targets('seated',values)

if __name__=='__main__':unittest.main()
