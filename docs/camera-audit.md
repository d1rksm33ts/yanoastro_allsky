# Existing camera audit

The current camera remains untouched until this audit and a rollback backup
are complete.

## Connectivity prerequisite

The camera is directly reachable from the setup workstation. Administrative
access from the YaNoa server still lacks a working return route through
WireGuard. Confirm the return route on the camera LAN router before relying on
remote administration. A temporary route can be used for testing, but the
gateway address must first be verified on that LAN; do not guess it.

Normal future SyncAPI operation is outbound HTTPS and does not depend on this
administrative route.

## Collect

Run from the repository checkout on the camera:

```sh
./scripts/audit-camera.sh
```

The script creates a timestamped `.tar.gz` in `audit-output/`. It collects
read-only system, storage, camera, service and package information. It does not
collect private keys or print complete environment/configuration files.

Review the archive locally before committing or sharing it. Audit archives are
ignored by Git.

## Inspect manually after collection

- current Allsky release and repository state;
- 64-bit OS compatibility with the pinned indi-allsky package;
- boot medium capacity, free space and filesystem health;
- Raspberry Pi power/thermal throttling;
- IMX477 enumeration and libcamera/rpicam functionality;
- day/night exposure, gain, orientation, crop and capture cadence;
- fan, heater, sensor, GPIO, I2C or SPI dependencies;
- local retention, failed uploads and queued artifacts;
- services, cron jobs and timers that must be disabled at cutover;
- files/database required for a restorable rollback.

After the audit, change the interactive camera password because it has been
shared during setup. The production path should use SSH keys for administration
and a separate HMAC API key for SyncAPI.

The first audit findings are recorded in
[current-camera-findings.md](current-camera-findings.md).
