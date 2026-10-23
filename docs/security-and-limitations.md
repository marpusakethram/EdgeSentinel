# Security and limitations

This is a local educational simulator, not an industrial security product. It has
not been tested on PLCs, real factory networks, Modbus, OPC UA, or other industrial
protocols. Failure/control events are fictional messages. Documentation IPv4
addresses inside payloads are not network destinations.

## Implemented protections

- HTTP launcher and TCP listener bind to `127.0.0.1`. The simulator hardcodes that
  destination; it has no network-scan, remote-host, or real-control interface.
- UTF-8 JSON Lines are limited to 4096 bytes, with strict field validation,
  finite telemetry values, known devices/event types, and no unexpected fields.
- Maximum 16 concurrent TCP clients; 5-second idle read timeout and 2-second
  simulator connect/ack and socket-write timeouts. Bad messages receive generic
  errors without payload logging. Disconnects do not stop the TCP listener.
- SQLite data values use bound parameters. Browser rendering uses text nodes,
  never injected HTML from device details or runbooks.
- POST controls require a fixed custom header, no CORS is enabled, and accepted
  Host values are constrained. These reduce browser cross-origin abuse; they are
  **not authentication**. Framing and MIME sniffing are disabled by response headers.
- Assistant tools only read. There are no secrets, external model calls, or commands
  derived from event/runbook text. Reset is explicit and the dashboard asks before deletion.

## What this does not secure

Any local process can connect and forge events, device IDs, or source_ip. There is
no TLS, identity proof, RBAC, replay protection, rate limit, audit trail, encrypted
database, or authenticated control API. Host `testserver` is allowed for API tests.
Loopback binding does not make a hostile shared machine safe. Never expose these
ports publicly or forward them to a factory network.

The source_ip field is self-reported and not the socket peer address. Allowlist
violations demonstrate policy matching, not source authentication or attribution.
Payload timestamps may be stale or in the future; rules use gateway receipt time.
Gateway wall-clock adjustments can affect offline/window behavior.

Storage has no automatic retention or size cap; sustained local ingestion can fill
disk. SQLite work and keyword retrieval run on the event loop, so local overload can
delay detection. Events and alerts use separate transactions. Detector memory is
not recovered across restart. Alert evidence is capped at 100 links and API lists
at 100 rows. Failure/control alerts are latched until reset. There is no alert
acknowledgement workflow, fleet scaling, delivery guarantee, or production monitoring.

Runbooks are trusted local instructional text. Keyword retrieval is simple and may
return irrelevant secondary matches. The assistant identifies observed symptoms,
never establishes physical root cause. Real limits, protocols, identities,
calibration, and safety procedures require qualified equipment-specific engineering.
