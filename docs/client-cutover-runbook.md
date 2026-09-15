# Camera client cutover

## Physical prerequisite

Write Raspberry Pi OS Lite 64-bit (Debian 13 / Trixie) and keep a verified,
compressed image of the previous 32 GB card as the physical rollback source.

In Raspberry Pi Imager, preconfigure:

- hostname `yanoastro`;
- username `smeets`;
- SSH enabled with the YaNoa public key;
- timezone `Europe/Brussels`;
- the setup Wi-Fi only as a fallback to wired Ethernet;
- no public inbound port forwarding.

The wired DHCP reservation follows the Raspberry Pi Ethernet MAC address, so
the setup address should remain stable after swapping cards. Confirm this in
the router rather than assigning a second static address on the Pi.

## Installation sequence

1. Boot the new card and confirm SSH, DNS, NTP and outbound HTTPS.
2. Update Raspberry Pi OS and reboot before installing camera software.
3. Clone this repository and its pinned `indi-allsky` submodule.
4. Add the signed upstream indi-allsky APT repository and install the version
   matching the pinned source tag. Do not use the deprecated source installer.
5. Configure the Raspberry Pi HQ / IMX477 direct libcamera interface.
6. Confirm local capture before configuring any remote synchronization.
7. Restore the audited exposure, gain, resolution, cadence and daily-product
   settings manually; do not import legacy Allsky configuration wholesale.
8. Install the repository-owned weather receiver and fail-safe climate service.
   The climate service exclusively owns fan GPIO18 and heater GPIO21. Missing
   or stale sensor data must leave the heater off.
9. Configure SyncAPI for `https://allsky.yanoa.be/indi-allsky`, using the
   protected server key, user `dirk`, certificate verification enabled and one
   synchronized still per ten captures initially.
10. Prove daylight, dusk, night and dawn capture plus image, timelapse, keogram
    and startrail synchronization.
11. Test recovery from a controlled network interruption and verify storage
    growth before enabling destructive retention.
12. Move the accepted camera to its outside DHCP reservation and confirm the
    administrative WireGuard return route.

## Client services

Restore the existing weather-station certificate and key to
`/etc/yanoa-weather/tls/` without committing them, then install the tracked
services:

```sh
sudo ./scripts/install-camera-client.sh
sudo reboot
```

The weather station is on the outside `192.168.3.x` network. During bench setup
on `192.168.2.x`, `yanoa-climate.service` deliberately reports
`sensor-data-unavailable` and holds both outputs at zero. After deployment it
automatically becomes active only after receiving a weather sample newer than
five minutes.

## Rollback

If capture, GPIO control, thermals or networking fail, shut down cleanly and
reinsert the labelled legacy card. Do not alter that card during the observation
period. A second file-level rollback copy is held in protected YaNoa backup
storage and included in the offsite backup scope.
