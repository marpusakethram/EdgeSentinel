"""Fixed read-only tool workflow with extractive runbook retrieval; no LLM."""

import re
import time
from pathlib import Path

RUNBOOKS = Path(__file__).resolve().parent.parent / "runbooks"
EVENT_NAMES = {"heartbeat": "a check-in", "telemetry": "a sensor reading",
               "connection_failure": "a failed connection", "control_write": "a request to change a setting"}


class Assistant:
    def __init__(self, gateway, runbooks=RUNBOOKS):
        self.gateway = gateway
        self.runbooks = runbooks

    def get_device_status(self, device_id):
        return next((item for item in self.gateway.detector.statuses(time.time())
                     if item["device_id"] == device_id), None)

    def get_recent_events(self, device_id, limit=10):
        return self.gateway.store.events(device_id, max(1, min(limit, 100)))

    def get_alert_evidence(self, alert_id):
        alert = self.gateway.store.get_alert(alert_id)
        if not alert:
            return None
        return {"alert": alert, "events": self.gateway.store.evidence(alert["event_ids"])}

    def search_runbooks(self, query):
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        matches = []
        for path in sorted(self.runbooks.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            score = len(tokens & set(re.findall(r"[a-z0-9]+", content.lower())))
            if score:
                matches.append({"source": f"runbooks/{path.name}", "score": score, "text": content})
        return sorted(matches, key=lambda item: (-item["score"], item["source"]))[:2]

    def investigate(self, alert_id):
        evidence = self.get_alert_evidence(alert_id)
        if evidence is None:
            return None
        alert = evidence["alert"]
        status = self.get_device_status(alert["device_id"])
        recent = self.get_recent_events(alert["device_id"], 10)
        runbooks = self.search_runbooks(alert["rule"].replace("_", " "))
        citation = f"alert:{alert_id}"
        claims = [{"text": alert["explanation"], "citations": [citation]}]
        for event in evidence["events"][-3:]:
            claims.append({"text": f"{event['device_id']} reported {EVENT_NAMES[event['event_type']]}. "
                f"Its message listed {event['temperature']} C and vibration of {event['vibration']} mm/s. "
                f"It said the sender was {event['source_ip']}. Details: {event['details']}",
                "citations": [f"event:{event['id']}"]})
        return {"mode": "deterministic-read-only", "summary": claims[0], "evidence_claims": claims[1:],
                "next_steps": [{"text": alert["next_step"], "citations": [citation]}] +
                    [{"text": " ".join(step.split()), "citations": [book["source"]]}
                     for book in runbooks[:1]
                     for step in re.findall(r"(?m)^\d\. .*(?:\n(?!\d\. |\n).*)*", book["text"])[:2]],
                "tools_used": ["get_alert_evidence", "get_device_status", "get_recent_events", "search_runbooks"],
                "retrieved": {**evidence, "device_status": status, "recent_events": recent, "runbooks": runbooks},
                "limitations": "This answer shows up to three recent messages. All the saved evidence is below. It tells you what was reported, not what caused it. The sender address is not verified. Nothing was changed or fixed automatically."}
