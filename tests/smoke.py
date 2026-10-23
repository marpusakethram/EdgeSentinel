"""Launch a real HTTP/TCP server, exercise scenarios, save an actual response, and stop."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    http_port, tcp_port = available_port(), available_port()
    while tcp_port == http_port:
        tcp_port = available_port()
    base = f"http://127.0.0.1:{http_port}"

    def request(path, method="GET"):
        req = Request(base + path, method=method, headers={"X-EdgeSentinel-Demo": "1"})
        with urlopen(req, timeout=5) as response:
            raw = response.read()
            return json.loads(raw) if response.headers.get_content_type() == "application/json" else raw.decode()

    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "EDGESENTINEL_DB": str(Path(tmp) / "smoke.db"), "EDGESENTINEL_TCP_PORT": str(tcp_port)}
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "edge_sentinel.app:app",
                                    "--host", "127.0.0.1", "--port", str(http_port)], cwd=ROOT, env=env)
        try:
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError("Smoke server exited before startup")
                try:
                    request("/api/devices")
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Smoke server did not start within 5 seconds")
            assert "EdgeSentinel" in request("/")
            assert "function poll" in request("/static/app.js")
            assert ".devices" in request("/static/style.css")
            request("/api/demo/normal", "POST")
            assert all(device["status"] == "online" for device in request("/api/devices"))
            for scenario, rule in [("telemetry", "telemetry_anomaly"), ("failures", "connection_failures"),
                                   ("control", "unusual_control_write"), ("offline", "device_offline")]:
                request(f"/api/demo/{scenario}", "POST")
                if scenario == "offline":
                    time.sleep(7)
                alert = next(alert for alert in request("/api/alerts") if alert["rule"] == rule)
                result = request(f"/api/alerts/{alert['id']}/investigation")
                assert result["retrieved"]["events"]
                assert result["summary"]["citations"] == [f"alert:{alert['id']}"]
                assert result["retrieved"]["runbooks"]
                print(f"PASS {scenario}: alert {alert['id']} with evidence and runbooks", flush=True)
            statuses = {item["device_id"]: item["status"] for item in request("/api/devices")}
            assert statuses == {"press-01": "online", "conveyor-02": "online", "cooling-03": "offline"}
            (ROOT / "docs" / "sample-investigation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            request("/api/demo/normal", "POST")
            assert not any(alert["active"] for alert in request("/api/alerts") if alert["rule"] == "device_offline")
            request("/api/reset", "POST")
            assert request("/api/events") == []
            assert request("/api/alerts") == []
            assert request("/api/demo")["running"] is False
            print("PASS dashboard assets, normal traffic, all four scenarios, recovery, reset", flush=True)
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
