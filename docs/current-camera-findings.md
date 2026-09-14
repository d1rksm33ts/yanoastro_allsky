# Current camera findings

Audit date: 14 September 2026. The inspection was read-only; no package,
service or camera setting was changed.

## Executive conclusion

The hardware and camera are healthy enough for migration testing, but the
current boot installation should not be upgraded in place. Build a fresh,
supported 64-bit indi-allsky client on separate higher-endurance storage and
keep the present card intact as rollback.

The remote web-only indi-allsky server should be built first. The current
camera is taking images again, while its published image and upload path are
stale. This gives us a clean boundary: prove the new server with a synthetic
SyncAPI upload before touching capture.

## Inventory

| Component | Observed state | Migration consequence |
| --- | --- | --- |
| Computer | Raspberry Pi 4 Model B Rev 1.5, 4 GB | supported and reusable |
| Architecture | aarch64 / 64-bit | suitable |
| OS | Debian 11 (Bullseye), kernel 6.1 | replace with a currently supported clean image |
| Boot storage | 32 GB microSD, about 14 GB free | too small for the preferred archive margin; use at least 128 GB high-endurance storage |
| Camera | Raspberry Pi HQ / Sony IMX477 | detected correctly by libcamera |
| Lens | 12 MP, 160 degrees, 3.2 mm | preserve in equipment metadata |
| Thermal state | about 40 degrees C, no throttling flags | healthy during audit |
| Current Allsky | `v2024.12.06_06` | replace after rollback backup |
| Local web server | Lighttpd on port 80 | retire after indi-allsky acceptance |

No failed systemd units were present. The legacy capture, periodic processing,
climate control, weather receiver and `pigpiod` services were active.

## Capture profile to preserve as baseline

- resolution/output family: 2028 x 1520 uploads from the IMX477;
- day: auto exposure, maximum 3 seconds, gain 1, approximately 27 second
  delay, images captured but not retained in the dated archive;
- night: auto exposure up to 30 seconds, auto gain up to 16, approximately one
  second inter-frame delay, night frames retained;
- image quality: JPEG 95, no rotation, no flip and no crop;
- daily products: H.264/MP4 timelapse at 2028 x 1520, 20 fps and 2 Mbps,
  plus keogram and startrail;
- local dated-image retention: one day.

The current live cadence is about 32–33 seconds during daytime once capture
and processing overhead are included. An initial SyncAPI interval of every
tenth image is therefore close to the intended five-minute server cadence. It
must be checked again at night before finalizing the value.

## Storage observations

The current Allsky tree is about 2.9 GB, of which about 2.7 GB is the retained
night folder. A separate aurora working folder consumes about 4.1 GB. The old
remote server archive remains a separate 5.3 GB migration source.

For the new camera installation:

- do not migrate the aurora work folder onto the capture volume by default;
- keep only operationally useful local frames;
- synchronize a sparse set of still images and all daily products;
- let the server's explicit retention policy manage the public archive.

## Publication failure

Capture restarted successfully and the working image updates continuously.
However, the legacy local web image is dated December 2025, the old remote
archive stopped in February 2026, and no upload events appeared after the
current restart. The old SFTP/FTPS publication path is therefore not considered
functional and should not be repaired as the target architecture.

## Custom hardware services that must be preserved

### Climate control

An independent Python service controls:

- fan PWM on GPIO 18;
- dome heater PWM on GPIO 21;
- dew/frost protection logic;
- a DS18B20-style dome temperature input;
- CSV and Influx line-protocol logging;
- ambient weather received by a separate local weather service.

This is more specialized than a generic camera heater toggle. Preserve it as a
first-class native client service, then decide after bench testing whether
indi-allsky should only display its telemetry or take over any control. There
must never be two processes driving the same GPIO pins.

At audit time the weather cache still contained February data, so the climate
controller was using its conservative fallback values. The receiver-to-weather
station path must be tested before outside deployment. This is also an explicit
dependency on the later telemetry migration.

### Focus tooling

The camera contains custom focus-motor, autofocus, capture and web helper
scripts plus calibration artifacts. They are not active systemd services, but
they must be backed up before reimaging. Test them in maintenance mode because
focus capture and indi-allsky cannot own the camera simultaneously.

## Network findings

Ethernet and Wi-Fi were both active on different private subnets, each with a
default route. Ethernet currently has the preferred metric. For the outside
deployment, use one intended primary interface and make the other an explicit
fallback or disable it; two unmanaged default routes make diagnostics and
source-address selection ambiguous.

The system timezone is `Europe/London`. Change the fresh installation to
`Europe/Brussels` before capture validation so dates, daily rollovers and
archive naming are consistent.

Direct SSH from the setup workstation works. The YaNoa server has a WireGuard
route toward the camera LAN, but the camera/LAN does not yet return that
traffic. Normal SyncAPI uploads are outbound HTTPS and are unaffected; remote
administration still needs the return route fixed.

## Required backup before reimage

- complete legacy Allsky configuration and custom overlays;
- current source revision plus uncommitted/local files;
- climate/weather services, Python sources and systemd units;
- focus tools, motor state and calibration captures;
- boot configuration, GPIO/1-Wire settings and installed-package manifest;
- representative daytime and nighttime source images;
- an image or verified file-level backup of the current boot medium.

Configuration contains legacy remote credentials. Store the raw backup only in
encrypted backup storage, never in this repository.

The protected file-level rollback archive was created and verified on 14
September 2026. A second verified copy is stored under the dedicated AllSky
backup tree on the YaNoa server, which is already included in encrypted offsite
backup. Temporary workstation and server transit copies were removed.
