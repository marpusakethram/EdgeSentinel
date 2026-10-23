# Telemetry anomaly: temperature and vibration

Policy: normal simulated telemetry is 45 C and 1 mm/s. The fixed demo operating
envelope flags temperature above 80 C OR vibration above 5 mm/s. Equality is allowed.
This is a hand-written rule, not a learned baseline or machine-learning model.

1. Inspect the linked telemetry event and compare recent temperature and vibration readings.
2. Check the selected demo scenario. A high reading describes a symptom, not a diagnosed mechanical fault.
3. In a real system, a qualified operator would validate sensor calibration and
   equipment-specific limits before deciding what action is safe.

The next in-envelope telemetry event clears the alert. No remediation is performed.
