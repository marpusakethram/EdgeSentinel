import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from edge_sentinel.app import create_app
from edge_sentinel.assistant import Assistant
from edge_sentinel.detector import Detector
from edge_sentinel.schema import parse_message
from edge_sentinel.simulator import message
from edge_sentinel.store import Store


def parsed(**changes):
    return parse_message(json.dumps(message("press-01", **changes)).encode())


class ParsingTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parsed().device_id, "press-01")

    def test_invalid(self):
        invalid = [b"not json", b"{}", b"x" * 4097, b"\xff", b"[]"]
        for change in [{"device_id": "unknown"}, {"timestamp": "2026-01-01"},
                       {"source_ip": "not-an-ip"}, {"temperature": float("nan")},
                       {"vibration": -1}, {"temperature": "45"}, {"status": "bogus"},
                       {"details": "x" * 513}, {"extra": True}]:
            payload = message("press-01")
            payload.update(change)
            invalid.append(json.dumps(payload).encode())
        for raw in invalid:
            with self.subTest(raw=raw[:80]), self.assertRaises((ValueError, UnicodeError)):
                parse_message(raw)


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.detector = Detector(self.store, 100)

    def tearDown(self):
        self.store.close()

    def test_offline_receipt_time_grace_and_recovery(self):
        eid = self.detector.ingest(parsed(timestamp="2099-01-01T00:00:00Z"), 100)
        self.detector.check_offline(106)
        self.assertEqual(self.store.alerts(), [])
        self.detector.check_offline(107)
        alert = next(a for a in self.store.alerts() if a["device_id"] == "press-01")
        self.assertEqual(alert["event_ids"], [eid])
        self.detector.check_offline(108)
        self.assertEqual(self.store.get_alert(alert["id"])["latest_observed"], 108)
        self.detector.ingest(parsed(), 109)
        self.assertFalse(self.store.get_alert(alert["id"])["active"])

    def test_telemetry_boundaries_evidence_and_deduplication(self):
        self.detector.ingest(parsed(event_type="telemetry", temperature=80.0, vibration=5.0), 100)
        self.assertEqual(self.store.alerts(), [])
        ids = [self.detector.ingest(parsed(event_type="telemetry", temperature=81.0), 101),
               self.detector.ingest(parsed(event_type="telemetry", vibration=5.1), 102)]
        self.assertEqual(len(self.store.alerts()), 1)
        alert = self.store.alerts()[0]
        self.assertEqual(alert["event_ids"], ids)
        self.assertEqual([e["id"] for e in self.store.evidence(ids)], ids)
        self.detector.ingest(parsed(event_type="telemetry"), 103)
        self.assertFalse(self.store.get_alert(alert["id"])["active"])

    def test_failures_window(self):
        for now in (100, 101, 112, 113):
            self.detector.ingest(parsed(event_type="connection_failure"), now)
        self.assertEqual(self.store.alerts(), [])
        self.detector.ingest(parsed(event_type="connection_failure"), 122)
        alert = self.store.alerts()[0]
        self.assertEqual(alert["rule"], "connection_failures")
        self.assertEqual(len(alert["event_ids"]), 3)

    def test_control_policy_checks_both_fields(self):
        self.detector.ingest(parsed(event_type="control_write", details="set_speed=50"), 100)
        self.assertEqual(self.store.alerts(), [])
        self.detector.ingest(parsed(event_type="control_write", details="set_speed=100"), 101)
        self.detector.ingest(parsed(event_type="control_write", details="set_speed=50", source_ip="192.0.2.99"), 102)
        self.assertEqual(len(self.store.alerts()[0]["event_ids"]), 2)
        self.assertEqual(self.store.alerts()[0]["severity"], "critical")

    def test_assistant_without_key_is_read_only_and_cited(self):
        self.detector.ingest(parsed(event_type="control_write", details="set_speed=100"), 100)
        assistant = Assistant(SimpleNamespace(store=self.store, detector=self.detector))
        self.assertEqual(assistant.search_runbooks("unusual control write")[0]["source"], "runbooks/unusual-control-write.md")
        self.assertEqual(assistant.search_runbooks("zzzznotfound"), [])
        before = self.store.db.total_changes
        with patch.dict(os.environ, {}, clear=True):
            result = assistant.investigate(1)
        self.assertEqual(result["mode"], "deterministic-read-only")
        self.assertEqual(result["summary"]["citations"], ["alert:1"])
        self.assertEqual(result["evidence_claims"][0]["citations"], ["event:1"])
        self.assertEqual(len(result["tools_used"]), 4)
        self.assertEqual(self.store.db.total_changes, before)
        self.assertIsNone(assistant.investigate(999))

    def test_persistence_and_reset_preserve_id_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "test.db")
            first = Store(path)
            eid = first.add_event(parsed(), 100)
            first.close()
            second = Store(path)
            self.assertEqual(second.events()[0]["id"], eid)
            second.reset()
            self.assertGreater(second.add_event(parsed(), 101), eid)
            second.close()

    def test_assistant_summary_is_bounded_but_preserves_full_evidence(self):
        for now in range(100, 110):
            self.detector.ingest(parsed(event_type="telemetry", temperature=95.0), now)
        assistant = Assistant(SimpleNamespace(store=self.store, detector=self.detector))
        result = assistant.investigate(1)
        self.assertEqual(len(result["evidence_claims"]), 3)
        self.assertEqual(len(result["retrieved"]["events"]), 10)
        self.assertEqual(result["evidence_claims"][-1]["citations"], ["event:10"])
        self.assertTrue(any(step["citations"] == ["runbooks/telemetry-anomaly.md"] for step in result["next_steps"]))
        self.assertLessEqual(len(result["next_steps"]), 5)


class ApiTests(unittest.TestCase):
    def test_api_scenarios_dashboard_and_reset(self):
        with TestClient(create_app(":memory:", 0)) as client:
            self.assertEqual(len(client.get("/api/devices").json()), 3)
            self.assertIn("EdgeSentinel", client.get("/").text)
            self.assertIn("Make the press run hot", client.get("/").text)
            self.assertIn("What am I looking at?", client.get("/static/guide.html").text)
            self.assertEqual(client.get("/static/app.js").status_code, 200)
            self.assertEqual(client.get("/api/events?limit=101").status_code, 422)
            self.assertEqual(client.get("/api/events?device_id=unknown").status_code, 422)
            self.assertEqual(client.get("/api/alerts/999").status_code, 404)
            self.assertEqual(client.post("/api/reset").status_code, 403)
            headers = {"X-EdgeSentinel-Demo": "1"}
            for scenario, rule in [("normal", None), ("telemetry", "telemetry_anomaly"),
                                   ("failures", "connection_failures"), ("control", "unusual_control_write")]:
                response = client.post(f"/api/demo/{scenario}", headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["message"])
                if rule:
                    alert = next(a for a in client.get("/api/alerts").json() if a["rule"] == rule)
                    evidence = client.get(f"/api/alerts/{alert['id']}").json()
                    self.assertTrue(evidence["events"])
                    self.assertEqual(client.get(f"/api/alerts/{alert['id']}/investigation").status_code, 200)
            self.assertEqual(client.post("/api/demo/unknown", headers=headers).status_code, 422)
            self.assertEqual(client.post("/api/reset", headers=headers).status_code, 200)
            self.assertEqual(client.get("/api/events").json(), [])
            self.assertEqual(client.get("/api/alerts").json(), [])
            self.assertFalse(client.get("/api/demo").json()["running"])

    def test_tcp_bad_lines_disconnect_and_oversize_do_not_break_gateway(self):
        app = create_app(":memory:", 0)
        with TestClient(app) as client:
            port = app.state.gateway.port
            with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
                stream = sock.makefile("rb")
                sock.sendall(b"bad json\n")
                self.assertFalse(json.loads(stream.readline())["ok"])
                sock.sendall(json.dumps(message("press-01")).encode() + b"\n")
                self.assertTrue(json.loads(stream.readline())["ok"])
                stream.close()
            with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
                sock.sendall(b"x" * 5000 + b"\n")
                self.assertIn(b"line too long", sock.recv(1024))
            with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
                sock.sendall(b'{"partial":')
            self.assertEqual(client.post("/api/demo/normal", headers={"X-EdgeSentinel-Demo": "1"}).status_code, 200)
            self.assertGreaterEqual(len(client.get("/api/events").json()), 7)


if __name__ == "__main__":
    unittest.main()
