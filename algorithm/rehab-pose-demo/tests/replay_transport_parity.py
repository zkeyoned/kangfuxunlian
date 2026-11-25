"""Optional real-model regression. Supply a local video; no video/data is exported."""
import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
from live_api import LiveAnalyzer, RTM_MODEL_DIR
from frame_batch import decode_batch, process_batch
from rtmpose_reference import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--side', choices=['left', 'right'], default='left')
    parser.add_argument('--facing', choices=['auto', 'left', 'right'], default='auto')
    args = parser.parse_args()
    profile = verify(model_dir=RTM_MODEL_DIR)
    assert profile['ready'], profile
    cap = cv2.VideoCapture(args.video)
    assert cap.isOpened(), 'Video could not be opened'
    fps = cap.get(cv2.CAP_PROP_FPS)
    stride = max(1, round(fps / 10))
    sessions = [LiveAnalyzer('1', args.side, args.facing, 20, 100) for _ in range(2)]
    batch, expected, count = [], [], 0
    selected = False
    visible_frames = 0

    def check():
        nonlocal selected
        decoded = decode_batch({'frames': batch}, cv2)
        actual = process_batch(sessions[1], decoded)
        target = dict(expected[-1])
        target['new_reps'] = [r for e in expected for r in e['new_reps']]
        target['feedback_events'] = [r for e in expected for r in e['feedback_events']]
        target.update(frame_id=batch[-1]['frame_id'], batch_frames=len(batch))
        actual.pop('processing_ms'); target.pop('processing_ms')
        assert actual == target, 'Single-frame and batch outputs differ'
        # Simulate the user's first click once a single box is available.
        # Never automatically choose another person after identity loss.
        subject = actual['subject']
        if not selected and subject['detected_people'] == 1:
            if subject['status'] != 'locked':
                x1, y1, x2, y2 = subject['boxes'][0]
                for session in sessions:
                    session.select_subject({'x': (x1+x2)/2, 'y': (y1+y2)/2})
            selected = True
        batch.clear(); expected.clear()

    try:
        index = 0
        while index / fps < args.seconds:
            ok, frame = cap.read()
            if not ok: break
            index += 1
            if (index-1) % stride: continue
            h, w = frame.shape[:2]
            scale = min(1, 960/w, 960/h)
            frame = cv2.resize(frame, (round(w*scale), round(h*scale)))
            ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            assert ok
            item = dict(image=base64.b64encode(encoded).decode(), timestamp_s=index/fps, frame_id=index)
            decoded = decode_batch({'frames':[item]}, cv2)
            expected.append(sessions[0].process(decoded[0][0], item['timestamp_s']))
            visible_frames += int(expected[-1]['visible'])
            batch.append(item); count += 1
            if len(batch) == 8: check()
        if batch: check()
        assert count > 0
        assert visible_frames > 0, 'No valid measurements; cannot validate model measurement parity'
        print(json.dumps(dict(passed=True, frames=count, reference_id=profile['reference_id'],
                             visible_frames=visible_frames,
                             completed_reps=len(sessions[0].analyzer.engine.reps))))
    finally:
        cap.release()
        for session in sessions: session.close()


if __name__ == '__main__': main()
