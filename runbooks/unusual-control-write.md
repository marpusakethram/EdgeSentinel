# Unusual control write: allowlist policy

Policy: a simulated control_write is approved only when source_ip is exactly
192.0.2.10 AND details is exactly set_speed=50. Every other combination raises a
critical policy alert. These addresses are documentation-only payload values.

1. Inspect the event's claimed source_ip and exact operation in details.
2. Compare both fields against the allowlist above. The source is self-reported
   and is not authenticated; this is policy demonstration, not attacker attribution.
3. Preserve the evidence for review. Do not issue a compensating control command.

The alert remains latched until a demo reset. No write is executed on any device.
