# Device offline: missing heartbeat

Policy: heartbeats arrive every 1 second. The gateway declares a device offline
after more than 6 seconds without a heartbeat, using gateway receipt time. A new
gateway process or reset gives every device a 6-second grace period.

1. Check whether the simulator is running and whether the offline scenario is selected.
2. Inspect the linked last heartbeat event and its gateway receipt time. An empty
   evidence list means no heartbeat was seen in this gateway session; it is not proof of equipment failure.
3. Compare other devices' heartbeats and check gateway logs before attributing a cause.

A received heartbeat clears this alert. This demo cannot distinguish a device
fault from a network outage or a stopped simulator. Do not issue control commands.
