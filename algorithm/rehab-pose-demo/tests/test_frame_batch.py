import base64
import unittest
from types import SimpleNamespace
import cv2
import numpy as np
from frame_batch import decode_batch, process_batch

class BatchTests(unittest.TestCase):
    def item(self,t=1,fid=1):
        ok, data=cv2.imencode('.jpg',np.zeros((48,64,3),np.uint8))
        return dict(image=base64.b64encode(data).decode(),timestamp_s=t,frame_id=fid)

    def test_decode_and_aggregate(self):
        class Session:
            analyzer=SimpleNamespace(engine=SimpleNamespace(last_t=None))
            def process(self,frame,t):
                self.analyzer.engine.last_t=t
                return dict(timestamp_s=t,new_reps=[t],feedback_events=[t])
        decoded=decode_batch({'frames':[self.item(1,5),self.item(2,6)]},cv2)
        r=process_batch(Session(),decoded)
        self.assertEqual(r['frame_id'],6)
        self.assertEqual(r['new_reps'],[1,2])
        self.assertEqual(r['feedback_events'],[1,2])

    def test_invalid_batch_is_rejected_before_processing(self):
        for frames in ([],[self.item()]*9,[self.item(2),self.item(1,2)],
                       [self.item(1),self.item(2)], [self.item(float('nan'))]):
            with self.assertRaises(ValueError):decode_batch({'frames':frames},cv2)
        bad=self.item();bad['image']=base64.b64encode(b'not jpeg').decode()
        with self.assertRaises(ValueError):decode_batch({'frames':[bad]},cv2)
        ok,data=cv2.imencode('.jpg',np.zeros((961,2,3),np.uint8));bad['image']=base64.b64encode(data).decode()
        with self.assertRaises(ValueError):decode_batch({'frames':[bad]},cv2)

    def test_old_batch_rejected(self):
        session=SimpleNamespace(analyzer=SimpleNamespace(engine=SimpleNamespace(last_t=5)))
        with self.assertRaises(ValueError):process_batch(session,decode_batch({'frames':[self.item()]},cv2))
