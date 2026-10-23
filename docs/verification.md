# Verification : 23 October 2026

Environment: Windows, Python 3.13.5. A project-local virtual environment was created
and `pip install -r requirements.txt` completed successfully. Direct versions are
pinned to the installed FastAPI 0.161.1, Uvicorn 0.54.0, and HTTPX 0.28.1.

Executed checks:

- `python -m unittest discover -s tests -v`: **11 tests passed**. Covers valid and
  invalid parsing; all four detectors and boundaries; evidence linking and incident
  deduplication; no-key read-only assistant and bounded narrative; runbook retrieval;
  persistence/reset ID behavior; API, dashboard assets, scenarios, malformed TCP,
  oversized input, and disconnected clients.
- `python tests/smoke.py`: a separate Uvicorn process and temporary SQLite database
  exercised normal traffic and all four scenarios through real HTTP/TCP. It waited
  7 seconds for offline detection, checked that only cooling-03 was offline, verified
  cited investigations, recovered the device, and reset events/alerts. All assertions passed.
- `python -m pip check` in `.venv`: no broken requirements.
- `node --check static/app.js`: syntax check passed.
- In-app browser: the final beginner dashboard rendered; Start / return to normal
  made all three cards say Sending updates; Make the press run hot created a
  visible alert; Explain this alert displayed message sources, a plain-English
  answer, and next checks. The earlier control-write button was also exercised.
  Real screenshots are saved as `dashboard.png` and `investigation.png`.
- The SVG architecture diagram parsed as valid XML. A text check found no em dashes
  in the project source or docs and no local user paths or obvious token patterns
  in the publishable files. This is not a security audit.

The initial sandboxed tests stalled in Python's asyncio loopback socket setup,
before application startup. Approved execution outside that sandbox succeeded.
The shared global Python environment had unrelated package conflicts; the isolated
project environment does not. Starlette 1.9 emits a test-client deprecation warning
for HTTPX in favor of HTTPX2; current tests still pass. No warning was suppressed.

These are functional checks, not a full browser regression suite, load benchmark,
security audit, real-device integration test, or Python-version/OS matrix. Python
3.11+ is the intended support floor; execution here used only Python 3.13.5. The
sample JSON contains actual simulated data from the smoke run, not industrial data.
