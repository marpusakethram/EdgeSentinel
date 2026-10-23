"""Explainable rules, not machine learning. Timing uses gateway receipt time."""

from .schema import DEVICES

OFFLINE_SECONDS = 6
FAILURE_WINDOW = 10
FAILURE_THRESHOLD = 3
APPROVED_SOURCE = "192.0.2.10"


class Detector:
    def __init__(self, store, now):
        self.store = store
        self.started_at = now
        self.heartbeats = {}
        self.failures = {device: [] for device in DEVICES}

    def ingest(self, message, now):
        event_id = self.store.add_event(message, now)
        device = message.device_id
        if message.event_type == "heartbeat":
            self.heartbeats[device] = (now, event_id)
            self.store.resolve(device, "device_offline")
        elif message.event_type == "telemetry":
            if message.temperature > 80 or message.vibration > 5:
                self.store.raise_alert(device, "telemetry_anomaly", "high", now, [event_id],
                    "A sensor reading went above the demo limit: temperature over 80 C or vibration over 5 mm/s.",
                    "Compare this reading with earlier ones. Check which demo mode is running before deciding why it happened.")
            else:
                self.store.resolve(device, "telemetry_anomaly")
        elif message.event_type == "connection_failure":
            failures = [(ts, eid) for ts, eid in self.failures[device] if now - ts <= FAILURE_WINDOW]
            failures.append((now, event_id))
            self.failures[device] = failures[-100:]
            if len(failures) >= FAILURE_THRESHOLD:
                self.store.raise_alert(device, "connection_failures", "medium", now,
                    [eid for _, eid in failures], "This machine reported at least 3 failed connections within 10 seconds. These reports are made up for the demo.",
                    "Read the failure messages and check whether the machine is still checking in. These reports do not prove a real network problem.")
        elif message.event_type == "control_write":
            if message.source_ip != APPROVED_SOURCE or message.details != "set_speed=50":
                self.store.raise_alert(device, "unusual_control_write", "critical", now, [event_id],
                    "A pretend request to change a setting did not match the rules. Only sender 192.0.2.10 with request set_speed=50 is allowed.",
                    "Compare the reported sender and request with the guide. The sender is just a claim in the message. Do not send any machine commands.")
        return event_id

    def check_offline(self, now):
        for device in DEVICES:
            last, event_id = self.heartbeats.get(device, (self.started_at, None))
            if now - last > OFFLINE_SECONDS:
                self.store.raise_alert(device, "device_offline", "high", now,
                    [event_id] if event_id else [],
                    "No check-in arrived for more than 6 seconds, counting from the last heartbeat or when the app started.",
                    "Check whether the demo is running. Then look at the last check-in and the server messages. Silence alone does not tell us the cause.")

    def statuses(self, now):
        return [{"device_id": device,
                 "status": ("offline" if now - self.heartbeats.get(device, (self.started_at, None))[0] > OFFLINE_SECONDS
                            else "online" if device in self.heartbeats else "waiting"),
                 "last_heartbeat_received_at": self.heartbeats.get(device, (None, None))[0],
                 "last_heartbeat_event_id": self.heartbeats.get(device, (None, None))[1]}
                for device in DEVICES]
