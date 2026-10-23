"""Bounded loopback TCP ingress and lifecycle management."""

import asyncio
import logging
import time

from .detector import Detector
from .schema import MAX_MESSAGE_BYTES, parse_message
from .simulator import Simulator
from .store import Store

logger = logging.getLogger(__name__)


class Gateway:
    def __init__(self, db_path, port):
        self.store = Store(db_path)
        self.detector = Detector(self.store, time.time())
        self.port = port
        self.clients = set()
        self.monitor = None
        self.server = None
        self.simulator = None
        self.resetting = False
        self.control_lock = asyncio.Lock()

    async def start(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", self.port,
                                                 limit=MAX_MESSAGE_BYTES)
        self.port = self.server.sockets[0].getsockname()[1]
        self.simulator = Simulator(self.port)
        self.monitor = asyncio.create_task(self.watch())

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        if self.resetting or len(self.clients) >= 16:
            writer.close()
            await writer.wait_closed()
            return
        self.clients.add(task)
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(reader.readline(), timeout=5)
                except (ValueError, asyncio.TimeoutError):
                    writer.write(b'{"ok":false,"error":"line too long or idle timeout"}\n')
                    await asyncio.wait_for(writer.drain(), timeout=2)
                    break
                if not raw:
                    break
                try:
                    if not raw.endswith(b"\n"):
                        raise ValueError("incomplete line")
                    message = parse_message(raw)
                except (ValueError, UnicodeError):
                    writer.write(b'{"ok":false,"error":"invalid message; see schema documentation"}\n')
                else:
                    event_id = self.detector.ingest(message, time.time())
                    writer.write(f'{{"ok":true,"event_id":{event_id}}}\n'.encode())
                await asyncio.wait_for(writer.drain(), timeout=2)
        except (ConnectionError, OSError, asyncio.TimeoutError):
            logger.info("TCP client disconnected or timed out")
        except Exception:
            logger.exception("Gateway could not store an event")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
            self.clients.discard(task)

    async def watch(self):
        while True:
            await asyncio.sleep(0.5)
            self.detector.check_offline(time.time())

    async def close_clients(self):
        tasks = list(self.clients)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def reset(self):
        self.resetting = True
        try:
            await self.simulator.stop()
            await self.close_clients()
            self.store.reset()
            self.detector = Detector(self.store, time.time())
            self.simulator.scenario = "normal"
            self.simulator.error = None
        finally:
            self.resetting = False

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.simulator:
            await self.simulator.stop()
        if self.monitor:
            self.monitor.cancel()
            await asyncio.gather(self.monitor, return_exceptions=True)
        await self.close_clients()
        self.store.close()
