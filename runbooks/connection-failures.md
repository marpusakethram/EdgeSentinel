# Connection failures: repeated simulated failures

Policy: at least 3 connection_failure events for one device within an inclusive
10-second gateway-receipt window raise a medium-severity alert.

1. Inspect the linked failure events and their receipt times.
2. Compare heartbeats: the failure event describes a simulated downstream attempt,
   not the TCP connection that successfully delivered this message.
3. Check reported details and gateway logs. Do not infer an outage or attack from
   the counter alone.

This incident remains latched until a demo reset. It records a threshold crossing,
not a claim that failures are still happening. No external connection is attempted.
