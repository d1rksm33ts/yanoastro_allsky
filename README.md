# YaNoAstro AllSky

Independent capture and publication environment for the YaNoAstro AllSky
camera. This repository owns the future `indi-allsky` client/server migration
and the service published at <https://allsky.yanoa.be>.

The responsibilities are deliberately separated:

- `yanoastro_allsky`: camera capture, SyncAPI, operational gallery, retention
  and AllSky storage;
- `web_yanoastro`: editorial portfolio for projects, equipment, workflows and
  curated astrophotography.

No camera password, API key, database password, exact private location or
other secret belongs in Git.

## Current status

- `allsky.yanoa.be` resolves to the consolidated YaNoa server;
- the existing Raspberry Pi was audited read-only on its current LAN;
- a separate DHCP reservation exists for its final deployment location;
- the Raspberry Pi runs the pinned indi-allsky APT release on 64-bit Trixie;
- IMX477 capture and authenticated SyncAPI publication are operational;
- the isolated server stack is live at <https://allsky.yanoa.be>;
- MariaDB backups run daily and AllSky media is in the encrypted offsite scope;
- destructive media retention remains disabled until a restore test passes;
- a verified compressed image and protected file-level archive preserve the
  legacy installation for rollback;
- climate/weather migration is implemented with fail-safe GPIO ownership and
  is commissioned separately from image capture.

See:

- [target architecture](docs/architecture.md)
- [camera audit runbook](docs/camera-audit.md)
- [migration plan](docs/migration-plan.md)
- [camera client cutover](docs/client-cutover-runbook.md)

## Remote server stack

The official upstream source is pinned as a Git submodule. Clone with:

```sh
git clone --recurse-submodules https://github.com/d1rksm33ts/yanoastro_allsky.git
```

The Compose project intentionally contains only MariaDB, the indi-allsky
Gunicorn application and a small internal nginx frontend. It publishes no host
ports; Caddy reaches `yanoastro-allsky-web:8080` through `yanoa-edge`.

Validate it without production secrets:

```sh
make validate
```

Production uses
`/srv/yanoa/secrets/yanoastro_allsky/server.env`, never the checked-in example.
Generate it once on the server with `scripts/generate-server-env.sh`; the
script refuses to overwrite an existing secret file.

Prepare bind-mount directories before the first Compose start:

```sh
sudo ./scripts/prepare-server-storage.sh
```

The public media root is traversable by the read-only nginx container, while
database, migration and backup roots remain private.

After the first successful application start, create a dedicated SyncAPI key
without printing it to the terminal or logs:

```sh
sudo ./scripts/generate-syncapi-key.sh
```

The protected key file is intentionally separate from the Compose environment
and is copied to the camera only during the client migration.

On the YaNoa host, `.env` is a local symlink to the non-secret
`deploy/compose.env`. This keeps deployment paths consistent while all real
credentials remain in the protected server environment file.

## Repeat the safe audit

Run the audit locally on the camera and copy the resulting archive to a secure
workstation location. It does not change system configuration:

```sh
./scripts/audit-camera.sh
```

Review the archive before sharing it. Network configuration and logs can still
contain private operational data.
