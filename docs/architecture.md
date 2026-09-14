# Architecture

## Service boundary

```text
Raspberry Pi / IMX477
  native indi-allsky client
  local SQLite and short local retention
            |
            | HTTPS SyncAPI (HMAC and TLS verification)
            v
allsky.yanoa.be
  Caddy on yanoa-edge
            |
  isolated indi-allsky web-only Compose project
  Gunicorn + web server + dedicated MariaDB
            |
  /srv/yanoa/data/yanoastro_allsky

astro.yanoa.be
  separate web_yanoastro portfolio
  consumes only intentionally published AllSky output
```

The Pi captures and processes locally. It never connects directly to the
server database. The server accepts synchronized artifacts through the
upstream SyncAPI.

## Camera network identity

The current audit address and the final outside DHCP reservation live only in
the ignored local `.env`. Application configuration uses a hostname or
environment variable where practical; neither private address nor the MAC
address is embedded in public source. SyncAPI traffic is initiated by the
camera, so the server does not require inbound access to either private address
during normal operation.

Administrative access from the YaNoa server traverses WireGuard. The camera
subnets need an appropriate return route through the LAN WireGuard router, or
equivalent forwarding/NAT must be configured there.

## Server isolation

The `yanoastro_allsky` Compose project will run only the upstream web-only
components:

- web server;
- Gunicorn/Flask application;
- dedicated MariaDB.

Capture, INDI and MQTT containers do not belong on the public server. MariaDB
and Gunicorn expose no host ports. Only the web service joins `yanoa-edge`.
Persistent state uses these host locations:

```text
/srv/yanoa/data/yanoastro_allsky/database
/srv/yanoa/data/yanoastro_allsky/images
/srv/yanoa/data/yanoastro_allsky/migrations
/srv/yanoa/backups/yanoastro_allsky
/srv/yanoa/secrets/yanoastro_allsky
```

The service is based on a pinned upstream release. It must not track `main` or
an unpinned `latest` image.

## Storage policy

- synchronized still images: initially 14 days;
- daily videos, keograms and startrails: 400 days;
- selected events/highlights: permanent;
- RAW/FITS capture data: never synchronized to the web server;
- legacy archive: immutable, checksummed and presented separately;
- deletion starts only after an encrypted offsite backup and restore test.

The web-only installation must explicitly schedule upstream expiration because
there is no capture process on the server to do it implicitly.

## Portfolio integration

`web_yanoastro` must not query the indi-allsky MariaDB schema. It can consume a
small stable adapter/API or selected public artifacts for the latest image,
freshness state, daily products and a link to the operational gallery. This
keeps upstream database migrations isolated from the portfolio.
