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
- capture is running, but publication/upload is currently stale;
- no installation or mutation of the current camera has been performed;
- the public server stack is not deployed yet.

See:

- [target architecture](docs/architecture.md)
- [camera audit runbook](docs/camera-audit.md)
- [migration plan](docs/migration-plan.md)

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
