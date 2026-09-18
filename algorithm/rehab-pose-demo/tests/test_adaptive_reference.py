import unittest
from unittest.mock import patch
from rehab_pose.measures import MotionMeasures,MeasureConfig
from rehab_pose.exercises import ExerciseAnalyzer
from rehab_pose.core import Config
from rehab_pose.leg_selection import LegSelection
from test_v04 import observed


class AdaptiveReferenceTests(unittest.TestCase):
    def test_120_degree_reference_and_round_trip(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        a=ExerciseAnalyzer('1',Config())
        for i in range(20):
            p=observed(120);o=m.update(i*.05,p,640,480);a.update(i*.05,p,o)
        self.assertIsNotNone(o['calibration']['baseline'])
        self.assertAlmostEqual(a.engine.config.rest_max_deg,126)
        self.assertAlmostEqual(a.engine.config.start_deg,132)
        sequence=list(range(120,171,5))+[170]*50+list(range(170,119,-2))+[120]*10
        for i,k in enumerate(sequence,20):
            p=observed(k);o=m.update(i*.05,p,640,480);a.update(i*.05,p,o)
        self.assertEqual(len(a.reps),1)
        self.assertEqual(a.engine.config.target_deg,160)

    def test_extended_leg_not_accepted_as_rest(self):
        m=MotionMeasures('right')
        for i in range(80):o=m.update(i*.05,observed(170),640,480)
        self.assertIsNone(o['calibration']['baseline'])

    def test_continuous_movement_not_reference(self):
        m=MotionMeasures('right')
        for i in range(100):o=m.update(i*.05,observed(90+(i%20)*2),640,480)
        self.assertIsNone(o['calibration']['baseline'])

    def test_overlapping_legs_not_click_selected(self):
        leg=LegSelection('left',True)
        with patch('rehab_pose.leg_selection.metrics',return_value=observed()):
            self.assertFalse(leg.click(350,250,[],640,480,.3))
        self.assertFalse(leg.confirmed)
