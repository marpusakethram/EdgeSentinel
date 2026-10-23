"""Small synchronous SQLite store; only the event loop thread uses it."""

import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL, event_type TEXT NOT NULL,
                received_at REAL NOT NULL, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_device_time
                ON events(device_id, received_at);
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                severity TEXT NOT NULL, device_id TEXT NOT NULL,
                rule TEXT NOT NULL, first_observed REAL NOT NULL,
                latest_observed REAL NOT NULL, event_ids TEXT NOT NULL,
                explanation TEXT NOT NULL, next_step TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_alert
                ON alerts(device_id, rule) WHERE active=1;
        """)

    def add_event(self, message, now: float) -> int:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO events(device_id,event_type,received_at,payload) VALUES (?,?,?,?)",
                (message.device_id, message.event_type, now, message.model_dump_json()),
            )
        return cursor.lastrowid

    @staticmethod
    def event(row):
        return {"id": row["id"], "received_at": row["received_at"], **json.loads(row["payload"])}

    def events(self, device_id=None, limit=50):
        rows = self.db.execute(
            "SELECT * FROM events WHERE (? IS NULL OR device_id=?) ORDER BY id DESC LIMIT ?",
            (device_id, device_id, limit),
        ).fetchall()
        return [self.event(row) for row in rows]

    def evidence(self, ids):
        return [self.event(row) for event_id in ids if (row := self.db.execute(
            "SELECT * FROM events WHERE id=?", (event_id,)
        ).fetchone())]

    @staticmethod
    def alert(row):
        if row is None:
            return None
        return {**dict(row), "event_ids": json.loads(row["event_ids"]), "active": bool(row["active"])}

    def alerts(self):
        return [self.alert(row) for row in self.db.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100")]

    def get_alert(self, alert_id):
        return self.alert(self.db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone())

    def raise_alert(self, device, rule, severity, now, ids, explanation, next_step):
        current = self.db.execute(
            "SELECT * FROM alerts WHERE device_id=? AND rule=? AND active=1", (device, rule)
        ).fetchone()
        with self.db:
            if current:
                # shortcut: retain the latest 100 evidence links; use a join table for long-running deployments.
                ids = list(dict.fromkeys(json.loads(current["event_ids"]) + ids))[-100:]
                self.db.execute(
                    "UPDATE alerts SET latest_observed=?,event_ids=? WHERE id=?",
                    (now, json.dumps(ids), current["id"]),
                )
                return current["id"]
            return self.db.execute(
                """INSERT INTO alerts(severity,device_id,rule,first_observed,latest_observed,
                   event_ids,explanation,next_step) VALUES (?,?,?,?,?,?,?,?)""",
                (severity, device, rule, now, now, json.dumps(ids), explanation, next_step),
            ).lastrowid

    def resolve(self, device, rule):
        with self.db:
            self.db.execute("UPDATE alerts SET active=0 WHERE device_id=? AND rule=? AND active=1", (device, rule))

    def reset(self):
        with self.db:
            self.db.execute("DELETE FROM alerts")
            self.db.execute("DELETE FROM events")

    def close(self):
        self.db.close()
