"""Integration test suite for the HTTP API server in web/server.py."""

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

# Set test data file before importing server
TEST_DIR = tempfile.mkdtemp()
TEST_DATA = Path(TEST_DIR) / "test_events.json"
os.environ["EVENT_PLANNER_DATA_FILE"] = str(TEST_DATA)

import web.server as server_module


class TestServerAPI(unittest.TestCase):
    """Test all HTTP server endpoints and responses."""

    @classmethod
    def setUpClass(cls):
        # Reset planner with test data file
        server_module.planner = server_module.EventPlanner(TEST_DATA)
        cls.httpd = ThreadingHTTPServer(("localhost", 0), server_module.EventPlannerHandler)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://localhost:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    def setUp(self):
        # Ensure standard sample events are loaded before each test
        server_module.planner.load_sample_events()

    def request(self, path, method="GET", data=None):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method=method)
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
            req.data = body

        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                headers = dict(resp.getheaders())
                body = resp.read()
                return status, headers, body
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read()

    def test_static_index(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Smart College Event Planning Assistant", body)

    def test_samples_and_list_events(self):
        # Load samples
        status, _, body = self.request("/api/samples", method="POST")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["success"])

        # List events
        status, _, body = self.request("/api/events")
        self.assertEqual(status, 200)
        events_data = json.loads(body.decode("utf-8"))
        self.assertEqual(len(events_data["events"]), 4)

    def test_single_event_and_edit_put(self):
        # Fetch EVT001
        status, _, body = self.request("/api/events/EVT001")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["event"]["event_id"], "EVT001")

        # Edit EVT001 time
        edit_payload = {
            "start_time": "14:00",
            "end_time": "15:00",
        }
        status, _, body = self.request("/api/events/EVT001", method="PUT", data=edit_payload)
        self.assertEqual(status, 200)
        res = json.loads(body.decode("utf-8"))
        self.assertTrue(res["success"])

        # Verify update
        status, _, body = self.request("/api/events/EVT001")
        updated = json.loads(body.decode("utf-8"))["event"]
        self.assertEqual(updated["start_time"], "14:00")
        self.assertEqual(updated["end_time"], "15:00")
        self.assertEqual(updated["status"], "Scheduled")

    def test_schedule_post(self):
        status, _, body = self.request("/api/schedule", method="POST")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["scheduled"], 4)

    def test_conflicts_get(self):
        status, _, body = self.request("/api/conflicts")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("simultaneous_clashes", data)
        self.assertIn("potential_conflicts", data)

    def test_priority_get(self):
        status, _, body = self.request("/api/priority")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("ranking", data)
        self.assertEqual(len(data["ranking"]), 4)

    def test_suggestions_get(self):
        # Path parameter format
        status, _, body = self.request("/api/events/EVT001/suggestions")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("valid_slots", data)
        self.assertIn("rejected_slots", data)

        # Query parameter format
        status, _, body = self.request("/api/suggestions?event_id=EVT002")
        self.assertEqual(status, 200)
        data2 = json.loads(body.decode("utf-8"))
        self.assertEqual(data2["event_id"], "EVT002")

    def test_validation_get(self):
        status, _, body = self.request("/api/validation")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("valid", data)
        self.assertIn("errors", data)
        self.assertIn("warnings", data)

    def test_analytics_get(self):
        status, _, body = self.request("/api/analytics")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("total_events", data)
        self.assertIn("venue_usage", data)
        self.assertIn("slot_usage", data)

    def test_buffer_get_and_post(self):
        # GET buffer
        status, _, body = self.request("/api/buffer")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("venue_buffer", data)

        # POST buffer change to 25
        status, _, body = self.request("/api/buffer", method="POST", data={"buffer": 25})
        self.assertEqual(status, 200)
        data2 = json.loads(body.decode("utf-8"))
        self.assertEqual(data2["venue_buffer"], 25)

    def test_csv_export(self):
        status, headers, body = self.request("/api/export")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type") or headers.get("content-type")
        self.assertIn("text/csv", content_type)
        csv_str = body.decode("utf-8")
        self.assertIn("Event ID", csv_str)
        self.assertIn("Venue", csv_str)


if __name__ == "__main__":
    unittest.main()
