# API and message format

These are the developer details. Start with the [README](../README.md) if you just want to try the demo.

## Wire schema

Each UTF-8 JSON object must end with a newline and occupy at most 4096 bytes
including that newline. All fields below are required; extra fields are rejected.

```json
{"device_id":"press-01","timestamp":"2026-10-23T08:00:00+00:00","event_type":"telemetry","temperature":45.0,"vibration":1.0,"status":"ok","source_ip":"192.0.2.10","details":"simulated normal operation"}
```

| Field | Validation / meaning |
|---|---|
| `device_id` | `press-01`, `conveyor-02`, `cooling-03` |
| `timestamp` | ISO datetime string with timezone; normalized to UTC |
| `event_type` | `heartbeat`, `telemetry`, `connection_failure`, `control_write` |
| `temperature` | Finite number, −100 to 500 C |
| `vibration` | Finite number, 0 to 100 mm/s |
| `status` | `ok`, `warning`, `failed`; descriptive, not a rule input |
| `source_ip` | Valid IPv4 string; **untrusted reported identity**, not socket origin |
| `details` | String up to 512 characters; exact operation for control-write policy |

Good lines receive `{"ok":true,"event_id":N}`. Invalid lines get a generic error
without echoing payloads; the client can send another line. Oversize lines and
5-second idle connections are closed. TCP writes/connects have 2-second timeouts.
There is a 16-client concurrent limit. Partial/disconnected clients do not terminate
the listener. Public interfaces and external destination options are not provided.

## API

All routes are local; interactive schema at `/docs`. Every POST requires
`X-EdgeSentinel-Demo: 1`. No authentication is implied by this fixed header.

| Method | Endpoint | Result |
|---|---|---|
| GET | `/api/devices` | Session heartbeat status and last heartbeat event IDs |
| GET | `/api/events?device_id=press-01&limit=30` | Recent events; limit 1-100, device optional |
| GET | `/api/alerts` | Latest 100 alerts including recovered/latched history |
| GET | `/api/alerts/{id}` | Alert and linked evidence events |
| GET | `/api/alerts/{id}/investigation` | Deterministic cited explanation and tool outputs |
| GET | `/api/demo` | Simulator state and last connection error |
| POST | `/api/demo/{scenario}` | `normal`, `offline`, `telemetry`, `failures`, `control` |
| POST | `/api/reset` | Stop built-in simulation, close ingress clients, delete demo rows |

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/events?device_id=press-01&limit=5'
$demoAlerts = Invoke-RestMethod http://127.0.0.1:8000/api/alerts
Invoke-RestMethod "http://127.0.0.1:8000/api/alerts/$($demoAlerts[0].id)/investigation" | ConvertTo-Json -Depth 12
```

Unknown alerts return 404; invalid devices, limits, or scenarios return 422; missing
POST header returns 403; simulator connection failure returns 503.
