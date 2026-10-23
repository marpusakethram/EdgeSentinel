# Demo commands

The browser buttons are the easiest way to try the app. These commands do the same
thing if you prefer a terminal. Start the app first using the [README](../README.md),
then open a second PowerShell window.

## Start normal traffic

```powershell
$demoHeaders = @{ 'X-EdgeSentinel-Demo' = '1' }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/demo/normal -Headers $demoHeaders
```

## Try each problem

Run one at a time so you can inspect the result. A new mode replaces the previous
one but keeps the old alerts.

```powershell
# Make the press run hot.
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/demo/telemetry -Headers $demoHeaders

# Report three pretend connection failures.
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/demo/failures -Headers $demoHeaders

# Report a write request that does not match the demo rules.
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/demo/control -Headers $demoHeaders

# Stop cooling-03's messages and wait for the missing check-in alert.
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/demo/offline -Headers $demoHeaders
Start-Sleep -Seconds 7
```

## Read the result

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/devices
Invoke-RestMethod 'http://127.0.0.1:8000/api/events?limit=10'
$demoAlerts = Invoke-RestMethod http://127.0.0.1:8000/api/alerts
$demoAlerts
Invoke-RestMethod "http://127.0.0.1:8000/api/alerts/$($demoAlerts[0].id)/investigation" | ConvertTo-Json -Depth 12
```

## Clear the demo

This stops the built-in simulator and deletes stored demo messages and alerts.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/reset -Headers $demoHeaders
```

## macOS/Linux equivalent

Use `curl` with the same paths. For example:

```sh
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/demo/normal
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/demo/telemetry
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/demo/failures
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/demo/control
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/demo/offline
sleep 7
curl http://127.0.0.1:8000/api/alerts
curl -X POST -H 'X-EdgeSentinel-Demo: 1' http://127.0.0.1:8000/api/reset
```

## Optional: run the machines as a separate process

```powershell
.\.venv\Scripts\python.exe -m edge_sentinel.simulator --port 8765
```

This only sends normal traffic. Stop it with Ctrl+C before using dashboard scenarios.
Otherwise, its check-ins can hide the quiet-device problem you are trying to show.
