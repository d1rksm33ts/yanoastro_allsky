# indi-allsky migration plan

## Baseline

The selected target is upstream `aaronwmorris/indi-allsky`, pinned to a tested
release. The Raspberry Pi uses the native package; the consolidated server uses
an isolated web-only Compose deployment. The legacy password-based SFTP flow is
retired only after SyncAPI has passed an observation period.

## Phase 0 — audit and preserve

1. Preserve direct administrative reachability on the setup LAN.
2. Review and, when needed, repeat the read-only audit.
3. Export/redact configuration and make a restorable camera backup.
4. Preserve the legacy 5.3 GB server archive with a checksum manifest.

## Phase 1 — remote server

1. Vendor or reproducibly fetch the exact tested upstream tag.
2. Adapt only the MariaDB, Gunicorn and web-server services.
3. Store all state and secrets under the paths documented in architecture.
4. connect only the web service to `yanoa-edge` and route
   `allsky.yanoa.be` from Caddy;
5. create the admin account and dedicated SyncAPI credentials;
6. test a synthetic SyncAPI upload;
7. add logical MariaDB backup, media backup and report-only retention.

## Phase 2 — camera migration with rollback

1. Use separate media for a fresh supported 64-bit OS if the audit shows the
   existing installation is unsuitable.
2. Install the pinned native indi-allsky package.
3. Restore the verified IMX477 settings and hardware integrations.
4. Verify local capture through daylight, dusk, night and dawn.
5. Keep the old boot medium unchanged as rollback.

## Phase 3 — synchronize

1. Configure `https://allsky.yanoa.be` and the dedicated SyncAPI key.
2. Keep TLS certificate verification enabled.
3. Upload daily products and initially one still approximately every five
   minutes; calculate the exact N-value from the audited capture cadence.
4. Test retry behavior during a short controlled network interruption.
5. Observe bandwidth, queue depth, temperature and disk growth for several
   days.

## Phase 4 — final deployment and integration

1. Move the camera to its reserved outside DHCP address.
2. Confirm NTP, DNS, outbound HTTPS and administrative WireGuard routing.
3. Add selected live/status artifacts to `web_yanoastro` without direct DB
   coupling.
4. Enable destructive retention only after backup/restore verification.
5. Remove the old SFTP credentials and old capture installation after the
   observation period.

## Acceptance criteria

- stable full day/night capture cycle without throttling;
- correctly oriented and focused IMX477 output;
- images and daily products synchronize with metadata;
- interrupted transfers retry without duplicates or corruption;
- public users cannot access configuration or administration;
- stale/offline images are labelled correctly;
- storage warnings and retention operate within policy;
- camera, database and media restore tests succeed;
- rollback remains possible until final acceptance.
