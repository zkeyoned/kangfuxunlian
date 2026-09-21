import json
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
import live_api


class RemoteHTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), live_api.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def post(self, path, body):
        request = urllib.request.Request('http://127.0.0.1:%d/api/live%s' % (self.server.server_port, path),
                                         json.dumps(body).encode(), {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request) as response: return response.status
        except urllib.error.HTTPError as error: return error.code

    def test_profile_failure_never_loads_another_model(self):
        with patch.object(live_api, 'authenticate', return_value=1), \
             patch.object(live_api, 'reference_status', return_value={'ready': False, 'reference_id': 'expected'}), \
             patch.object(live_api, 'LiveAnalyzer') as model:
            self.assertEqual(self.post('/start', {'backend': 'rtmpose', 'required_reference': 'expected'}), 503)
            model.assert_not_called()

    def test_frames_require_same_authenticated_owner(self):
        session = SimpleNamespace(owner=1, backend='rtmpose')
        with patch.object(live_api, 'SESSIONS', {'test': session}), \
             patch.object(live_api, 'VISION_AUTH', True), \
             patch.object(live_api, 'authenticate', return_value=2), \
             patch.object(live_api, 'process_batch') as process:
            self.assertEqual(self.post('/test/frames', {}), 403)
            process.assert_not_called()
