import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from rehab_pose.run import camera_frames, AnnotatedWriter, video_frames


class CaptureQualityTests(unittest.TestCase):
    def test_actual_resolution_reported_when_request_ignored(self):
        cap = Mock()
        cap.isOpened.return_value = True
        cap.set.return_value = True
        cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        info = {}
        with patch('cv2.VideoCapture', return_value=cap):
            frames = camera_frames(0, '720p', info)
            next(frames)
            frames.close()
        self.assertEqual(info['requested_width'], 1280)
        self.assertEqual(info['actual_width'], 640)
        self.assertFalse(info['requested_size_matched'])
        cap.release.assert_called_once()

    def test_read_failure_releases_camera(self):
        cap = Mock()
        cap.isOpened.return_value = True
        cap.read.return_value = (False, None)
        with patch('cv2.VideoCapture', return_value=cap):
            with self.assertRaises(RuntimeError):
                next(camera_frames(0))
        cap.release.assert_called_once()

    def test_recording_retains_dimensions_and_variable_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'quality.mp4'
            writer = AnnotatedWriter(path, 1280, 720)
            for t in (0., .1, .35):
                writer.write(np.full((720, 1280, 3), 100, dtype=np.uint8), t)
            writer.close()
            self.assertEqual(writer.target_bitrate, 5_529_600)
            decoded = list(video_frames(path))
            self.assertEqual(len(decoded), 3)
            self.assertEqual(decoded[0][1].shape, (720, 1280, 3))
            for (t, _), expected in zip(decoded, (0., .1, .35)):
                self.assertAlmostEqual(t, expected, places=3)
