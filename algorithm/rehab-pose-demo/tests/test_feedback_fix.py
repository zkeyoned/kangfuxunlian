import unittest
from unittest.mock import patch
from rehab_pose.measures import MotionMeasures,MeasureConfig
from rehab_pose.leg_selection import LegSelection
from test_v04 import observed


class FeedbackFixTests(unittest.TestCase):
    def ready(self):
        m=MotionMeasures('right',MeasureConfig(calibration_s=.5))
        for i in range(15):m.update(i*.05,observed(),640,480)
        return m

    def test_forward_and_backward_even_at_rest(self):
        m=self.ready();events=[]
        for i in range(15,26):events+=m.update(i*.05,observed(trunk=25),640,480,'rest')['feedback_events']
        for i in range(26,38):events+=m.update(i*.05,observed(trunk=-25),640,480,'rest')['feedback_events']
        self.assertEqual([e['code'] for e in events],['TRUNK_FORWARD','TRUNK_BACKWARD'])

    def test_instantaneous_speed_is_measured_but_not_used_as_action1_failure(self):
        m=self.ready();events=[]
        for i in range(1,7):
            events+=m.update(.7+i*.04,observed(90+i*12),640,480,'rest')['feedback_events']
        self.assertEqual(events,[])
        self.assertGreater(abs(m.update(1.0,observed(170),640,480,'rest')['measurement_metrics']['knee_velocity_deg_s']),0)

    def test_slow_motion_not_automatically_wrong(self):
        m=self.ready();events=[]
        for i in range(1,15):events+=m.update(.7+i*.04,observed(90+i),640,480,'rest')['feedback_events']
        self.assertEqual(events,[])

    def test_uncalibrated_cannot_judge(self):
        m=MotionMeasures('right')
        for i in range(12):
            self.assertEqual(m.update(i*.05,observed(170,trunk=35),640,480)['feedback_events'],[])

    def test_leg_requires_valid_confirmation_and_reselection(self):
        leg=LegSelection('left',True)
        self.assertFalse(leg.confirm([],640,480,.3))
        with patch('rehab_pose.leg_selection.metrics',return_value=observed()):
            self.assertTrue(leg.confirm([],640,480,.3))
        leg.choose('right')
        self.assertFalse(leg.confirmed)
        self.assertEqual(leg.side,'right')
