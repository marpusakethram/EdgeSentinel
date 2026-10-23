# Interview guide

## A truthful 45-second introduction

“EdgeSentinel is a local industrial-network simulator. Three Python devices send
JSON Lines over TCP to an asyncio gateway. It validates events, stores them in
SQLite, and applies four explicit operational/security rules. A FastAPI dashboard
lets me reproduce incidents and inspect evidence. A read-only troubleshooting
workflow retrieves local runbooks and cites events rather than inventing a cause.
The transport and storage are real; device behavior and control writes are simulated.
I did not implement industrial protocols, ML, autonomous agents, or production security.”

## Beginner-friendly module walkthrough

1. **`schema.py` : the entrance check.** `Message` defines every accepted field.
   Pydantic checks types, ranges, known devices, timezone-bearing timestamps, and
   IPv4 syntax. `parse_message` rejects oversized data before creating a model.
2. **`simulator.py` : the fake machines.** `message` constructs a reading, `send`
   writes newline-framed JSON to loopback and waits for an acknowledgement, and
   `Simulator` changes what the three devices report. Offline suppresses messages;
   a control scenario only sends a descriptive event.
3. **`gateway.py` : the receiver.** `start` opens the TCP listener. `handle` reads
   one bounded line at a time, validates it, and passes it to the detector. `watch`
   checks for absent heartbeats. `reset` and `close` stop tasks and close clients so
   old in-flight data does not quietly refill the reset database.
4. **`store.py` : the notebook.** `add_event` assigns an event ID. `raise_alert`
   creates or updates one active incident per device/rule. `evidence` fetches the
   actual records referenced by an alert. SQL parameters prevent data from becoming SQL.
5. **`detector.py` : the decision table.** `ingest` applies rules to received events;
   `check_offline` handles an absence of events. This distinction matters: offline
   detection cannot depend on a message arriving from the missing device.
6. **`assistant.py` : evidence assembly.** Four named read-only tools inspect an
   alert/device and search runbooks. `investigate` assembles cited facts and steps.
   A fixed workflow is easier to verify than an unrestricted model-driven agent.
7. **`app.py` / `__main__.py` : the front door.** Lifespan creates and closes the
   gateway. Routes expose reads and explicit demo controls. The launcher selects
   loopback and one worker. No frontend compilation or cloud account is needed.
8. **`static/` : the display.** The browser polls JSON endpoints, renders device
   cards and event rows, and shows raw evidence. It uses `textContent` so an event
   containing HTML appears as text instead of executing.
9. **`tests/test_core.py` : the proof.** Unit tests use controlled receipt times for
   boundary conditions; API tests exercise actual TCP ingestion through the simulator.
   Runbook lookup, citations, no-key behavior, reset, malformed lines, and persistence
   have explicit assertions.

## Five likely Cisco IIoT questions

**1. Why TCP, and how do you delimit messages?**
TCP gives ordered bytes, not message boundaries. Each UTF-8 JSON object ends with a
newline. The gateway reads bounded lines, rejects oversized/malformed input, and
acknowledges committed events. This is a custom simulation protocol, not industrial interoperability.

**2. How do you distinguish an offline device from a network problem?**
I cannot conclusively distinguish them here. A missing heartbeat is a symptom. I
use receipt time, a grace period, the last heartbeat ID, and other devices' events
to provide evidence for investigation. A real system would correlate switch/link
telemetry, gateway health, and authenticated device signals.

**3. Is the anomaly detector ML? Why this approach?**
No. It uses explicit limits, a rolling event count, and an allowlist. These are
cheap, reproducible, and explainable with no training set. A learned baseline would
require representative data, false-positive evaluation, drift handling, and
equipment-specific validation; this project makes no such claims.

**4. How does the assistant avoid hallucination or unsafe actions?**
It is deterministic: it reads stored evidence, retrieves local runbooks by token
overlap, and returns facts with event/alert/source citations. It has no write or
control tool. This demonstrates retrieval-grounded tool orchestration, not an LLM
agent or MCP. An optional model would need output validation and a safe fallback.

**5. What breaks when you scale this to a factory?**
Local identity is unauthenticated; SQLite work blocks one event loop; retention and
backpressure are limited; state resets on restart; wall-clock jumps affect timing;
events/alerts are not one transaction. I would first define safety and delivery
requirements, add authenticated ingress and durable bounded pipelines, measure
load, and integrate actual industrial protocols only in an authorized lab.

## Useful deeper tradeoffs

- Gateway receipt time resists forged sender times but is not a monotonic clock.
- An active incident is deduplicated; recovery permits a new incident ID. Latched
  incidents preserve a threshold crossing and should not be mistaken for live failure.
- Event persistence precedes alert persistence, leaving a crash gap that replay or
  a single transaction would need to close.
- SQLite is understandable and adequate for a tiny local demo; no throughput or
  memory benchmark has been claimed. A small deterministic pipeline also illustrates
  resource restraint without pretending to benchmark small-model inference.
- Reset stops built-in generation and closes clients; unrelated local processes
  can reconnect, which is why reset is not a production isolation mechanism.
