"""FastAPI dashboard and demo controls; one worker owns the TCP gateway."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .assistant import Assistant
from .gateway import Gateway
from .schema import DEVICES

ROOT = Path(__file__).resolve().parent.parent


def create_app(db_path=None, tcp_port=None):
    @asynccontextmanager
    async def lifespan(app):
        gateway = Gateway(str(db_path or os.getenv("EDGESENTINEL_DB", str(ROOT / "data" / "edgesentinel.db"))),
                          tcp_port if tcp_port is not None else int(os.getenv("EDGESENTINEL_TCP_PORT", "8765")))
        app.state.gateway = gateway
        try:
            await gateway.start()
            yield
        finally:
            await gateway.close()

    app = FastAPI(title="EdgeSentinel", description="Local simulator; no real industrial control", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_controls(request: Request, call_next):
        # A custom header blocks cross-origin simple-form writes; no CORS is enabled.
        if request.method == "POST" and request.headers.get("x-edgesentinel-demo") != "1":
            return JSONResponse({"detail": "Demo controls require X-EdgeSentinel-Demo: 1"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/api/devices")
    async def devices(request: Request):
        import time
        return request.app.state.gateway.detector.statuses(time.time())

    @app.get("/api/events")
    async def events(request: Request, device_id: str | None = None, limit: int = Query(50, ge=1, le=100)):
        if device_id is not None and device_id not in DEVICES:
            raise HTTPException(422, "Unknown device")
        return request.app.state.gateway.store.events(device_id, limit)

    @app.get("/api/alerts")
    async def alerts(request: Request):
        return request.app.state.gateway.store.alerts()

    @app.get("/api/alerts/{alert_id}")
    async def alert(request: Request, alert_id: int):
        result = Assistant(request.app.state.gateway).get_alert_evidence(alert_id)
        if result is None:
            raise HTTPException(404, "Alert not found")
        return result

    @app.get("/api/alerts/{alert_id}/investigation")
    async def investigate(request: Request, alert_id: int):
        result = Assistant(request.app.state.gateway).investigate(alert_id)
        if result is None:
            raise HTTPException(404, "Alert not found")
        return result

    @app.get("/api/demo")
    async def demo(request: Request):
        simulator = request.app.state.gateway.simulator
        return {"running": simulator.task is not None and not simulator.task.done(),
                "scenario": simulator.scenario, "error": simulator.error}

    @app.post("/api/demo/{scenario}")
    async def trigger(request: Request, scenario: Literal["normal", "offline", "telemetry", "failures", "control"]):
        gateway = request.app.state.gateway
        async with gateway.control_lock:
            try:
                await gateway.simulator.trigger(scenario)
            except (OSError, ValueError, RuntimeError, TimeoutError):
                raise HTTPException(503, "Simulator could not reach TCP gateway; check port and server logs")
        messages = {
            "normal": "All three machines are sending normal readings. Old connection and write alerts stay saved for review.",
            "offline": "cooling-03 has stopped checking in. Wait 6 to 7 seconds for its alert. The other two machines keep going.",
            "telemetry": "press-01 is now reporting 95 C. The demo limit is 80 C. Click its alert below.",
            "failures": "conveyor-02 just reported 3 pretend failed connections. Click its alert to see those messages.",
            "control": "press-01 reported an unapproved request to change a setting. No setting was actually changed. Click its alert below.",
        }
        return {"scenario": scenario, "message": messages[scenario]}

    @app.post("/api/reset")
    async def reset(request: Request):
        gateway = request.app.state.gateway
        async with gateway.control_lock:
            await gateway.reset()
        return {"message": "Demo messages and alerts are cleared. The machines are stopped. Click Start / return to normal to begin again."}

    return app


app = create_app()
