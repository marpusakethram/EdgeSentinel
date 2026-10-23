"""Three fake devices; the only network destination is literal 127.0.0.1."""

import argparse
import asyncio
import json

from .schema import DEVICES, utc_now


def message(device, event_type="heartbeat", **changes):
    return {"device_id": device, "timestamp": utc_now(), "event_type": event_type,
            "temperature": 45.0, "vibration": 1.0, "status": "ok",
            "source_ip": "192.0.2.10", "details": "simulated normal operation", **changes}


async def send(port, events):
    reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), timeout=2)
    try:
        for event in events:
            writer.write(json.dumps(event).encode() + b"\n")
            await asyncio.wait_for(writer.drain(), timeout=2)
            response = json.loads(await asyncio.wait_for(reader.readline(), timeout=2))
            if not response.get("ok"):
                raise RuntimeError(response.get("error", "gateway rejected message"))
    finally:
        writer.close()
        await writer.wait_closed()


class Simulator:
    def __init__(self, port):
        self.port = port
        self.scenario = "normal"
        self.error = None
        self.task = None

    async def tick(self):
        events = []
        for device in DEVICES:
            if self.scenario == "offline" and device == "cooling-03":
                continue
            events.append(message(device))
            events.append(message(device, "telemetry",
                temperature=95.0 if self.scenario == "telemetry" and device == "press-01" else 45.0,
                details="pretend sensor reading"))
        await send(self.port, events)

    async def loop(self):
        while True:
            await asyncio.sleep(1)
            try:
                await self.tick()
                self.error = None
            except (OSError, ValueError, RuntimeError, asyncio.TimeoutError) as exc:
                self.error = f"Simulator could not reach gateway: {type(exc).__name__}"

    async def stop(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def trigger(self, scenario):
        await self.stop()
        self.scenario = scenario
        self.error = None
        # Seed a last heartbeat so the offline scenario always has concrete evidence.
        if scenario == "offline":
            await send(self.port, [message("cooling-03")])
        await self.tick()
        if scenario == "failures":
            await send(self.port, [message("conveyor-02", "connection_failure", status="failed",
                details="simulated connection timeout") for _ in range(3)])
        elif scenario == "control":
            await send(self.port, [message("press-01", "control_write", source_ip="192.0.2.99",
                details="set_speed=100", status="warning")])
        self.task = asyncio.create_task(self.loop())


async def standalone(port):
    simulator = Simulator(port)
    await simulator.trigger("normal")
    try:
        await simulator.task
    finally:
        await simulator.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(standalone(args.port))
    except KeyboardInterrupt:
        pass
