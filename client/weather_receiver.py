#!/usr/bin/env python3
"""Receive the legacy weather-station upload and relay current telemetry."""

from __future__ import annotations

import json
import os
import queue
import signal
import ssl
import tempfile
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo


STATE_FILE = Path(os.environ.get("YANOA_WEATHER_STATE", "/var/lib/yanoa-weather/latest.json"))
CERT_FILE = os.environ.get("YANOA_WEATHER_CERT", "/etc/yanoa-weather/tls/cert.pem")
KEY_FILE = os.environ.get("YANOA_WEATHER_KEY", "/etc/yanoa-weather/tls/key.pem")
TELEMETRY_URL = os.environ.get("YANOA_TELEMETRY_URL", "https://telemetry.yanoa.be/weather/IZONHO45")
LOCAL_TZ = ZoneInfo("Europe/Brussels")
POST_QUEUE: queue.Queue[dict] = queue.Queue(maxsize=20)
STOP = threading.Event()


def number(value: str | None, *, integer: bool = False):
    try:
        return int(float(value)) if integer else float(value)
    except (TypeError, ValueError):
        return None


def telemetry_payload(args: dict[str, str]) -> dict:
    observed = args.get("datetime")
    observed_local = observed
    observed_utc = None
    epoch = None
    if observed:
        try:
            local_dt = datetime.strptime(observed, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LOCAL_TZ)
            utc_dt = local_dt.astimezone(timezone.utc)
            observed_local = local_dt.strftime("%Y-%m-%d %H:%M:%S")
            observed_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            epoch = int(utc_dt.timestamp())
        except ValueError:
            pass

    return {
        "stationID": "IZONHO45",
        "neighborhood": "Zonhoven",
        "softwareType": "vws versionxx",
        "country": "BE",
        "lat": 51.007,
        "lon": 5.371,
        "qcStatus": 1,
        "realtimeFrequency": None,
        "obsTimeLocal": observed_local,
        "obsTimeUtc": observed_utc,
        "epoch": epoch,
        "uv": number(args.get("t1uvi")),
        "solarRadiation": number(args.get("t1solrad")),
        "winddir": number(args.get("t1wdir"), integer=True),
        "humidity": number(args.get("t1hum")),
        "metric": {
            "temp": number(args.get("t1tem")),
            "heatIndex": number(args.get("t1heat")),
            "dewpt": number(args.get("t1dew")),
            "windChill": number(args.get("t1chill")),
            "windSpeed": number(args.get("t1ws")),
            "windGust": number(args.get("t1wgust")),
            "pressure": number(args.get("abar")),
            "precipRate": number(args.get("t1rainhr")),
            "precipTotal": number(args.get("t1raindy")),
            "elev": 14.9,
        },
    }


def write_state(args: dict[str, str], remote: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "remote": remote,
        "args": args,
    }
    with tempfile.NamedTemporaryFile("w", dir=STATE_FILE.parent, delete=False) as handle:
        json.dump(state, handle, separators=(",", ":"))
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(STATE_FILE)


def relay_worker() -> None:
    while not STOP.is_set():
        try:
            payload = POST_QUEUE.get(timeout=1)
        except queue.Empty:
            continue
        try:
            request = urllib.request.Request(
                TELEMETRY_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                response.read()
        except Exception as exc:  # keep the receiver responsive during WAN failures
            print(f"Telemetry relay failed: {exc}", flush=True)
        finally:
            POST_QUEUE.task_done()


class WeatherHandler(BaseHTTPRequestHandler):
    server_version = "YaNoaWeather/1"

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_request()

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_request()

    def _handle_request(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/":
            self._respond(200, b"wx receiver up\n")
            return
        if parsed.path != "/data/upload.php":
            self._respond(404, b"not found\n")
            return

        values = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if self.command == "POST":
            length = min(int(self.headers.get("Content-Length", "0")), 65536)
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("application/x-www-form-urlencoded"):
                body_values = urllib.parse.parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)
                values.update(body_values)
            elif length:
                self.rfile.read(length)

        args = {key: entries[-1] for key, entries in values.items()}
        write_state(args, self.client_address[0])
        try:
            POST_QUEUE.put_nowait(telemetry_payload(args))
        except queue.Full:
            print("Telemetry queue full; newest relay dropped", flush=True)
        self._respond(200, b"OK")

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main() -> None:
    relay = threading.Thread(target=relay_worker, daemon=True)
    relay.start()
    server = ThreadingHTTPServer(("0.0.0.0", 5000), WeatherHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    def stop(*_args) -> None:
        STOP.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("Weather receiver listening on https://0.0.0.0:5000", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
