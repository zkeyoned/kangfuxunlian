"""Optional local reference recordings; skipped in distributions without patient data."""
import json
from pathlib import Path
import unittest
from rehab_pose.measures import MotionMeasures,MeasureConfig
from rehab_pose.exercises import ExerciseAnalyzer
from rehab_pose.core import Config


class RecordedRegressionTests(unittest.TestCase):
    def test_legacy_recording_is_reinterpreted_by_v01_rules(self):
        p=Path(__file__).resolve().parents[1]/'results/20260917_221040_390174'
        if not (p/'frames.jsonl').exists():self.skipTest('Local reference recording not distributed')
        s=json.loads((p/'summary.json').read_text(encoding='utf8'))
        m=MotionMeasures(s['facing'],MeasureConfig(**s['measurement_parameters']),.3,'1')
        a=ExerciseAnalyzer('1',Config(**s['effective_parameters']));events=[]
        with (p/'frames.jsonl').open(encoding='utf8') as f:
            for line in f:
                r=json.loads(line);t=r['timestamp_s']
                # Stop at the first subject reposition, matching the reference segment.
                if t>31:break
                o=m.update(t,r,r['frame_size']['width'],r['frame_size']['height'],a.state)
                a.update(t,r,o,r.get('bridge_pending',False));events.extend(o['feedback_events'])
        # One old cycle did not return to the new baseline band and is no longer counted.
        self.assertEqual(len(a.reps),2)
        self.assertNotIn('KNEE_TOO_FAST',[e['code'] for e in events])
        self.assertIn('TRUNK_FORWARD',[e['code'] for e in events])
        self.assertTrue(all(not r['target_comparison']['hold_met'] for r in a.reps))
