#!/usr/bin/env python3
"""Fail-safe dome heater and fan controller for the YaNoAstro camera."""

from __future__ import annotations

import glob
import json
import os
import signal
import socket
import tempfile
import time
from pathlib import Path

FAN_PIN = 18
HEATER_PIN = 21
WEATHER_FILE = Path(os.environ.get("YANOA_WEATHER_STATE", "/var/lib/yanoa-weather/latest.json"))
STATE_FILE = Path(os.environ.get("YANOA_CLIMATE_STATE", "/run/yanoa-climate/state.json"))
MAX_WEATHER_AGE = 300
LOOP_SECONDS = 30
TARGET_DEW_MARGIN = 6.0
TARGET_AMBIENT_MARGIN = 2.0
CALIBRATION = ((0, 0.0), (5, 1.9), (10, 3.8), (15, 5.7), (20, 7.6),
               (30, 10.8), (40, 13.5), (50, 15.8), (60, 17.8), (70, 19.5),
               (80, 21.0), (90, 22.3), (100, 23.5))
STOP = False


class HardwarePwm:
    """Control a pre-initialized hardware PWM duty cycle as the gpio group."""

    def __init__(self, chip: int = 0, channel: int = 0):
        self.channel = Path(f"/sys/class/pwm/pwmchip{chip}/pwm{channel}")
        self.period_ns = int((self.channel / "period").read_text())
        if (self.channel / "enable").read_text().strip() != "1":
            raise RuntimeError(f"PWM channel is not enabled: {self.channel}")
        self.off()

    @property
    def value(self) -> float:
        return int((self.channel / "duty_cycle").read_text()) / self.period_ns

    @value.setter
    def value(self, value: float) -> None:
        bounded = max(0.0, min(1.0, value))
        (self.channel / "duty_cycle").write_text(f"{round(self.period_ns * bounded)}\n")

    def off(self) -> None:
        self.value = 0

    def close(self) -> None:
        self.off()


def notify(message: str) -> None:
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        client.connect(address)
        client.sendall(message.encode())


def cpu_temperature() -> float:
    return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000


def dome_temperature() -> float | None:
    devices = glob.glob("/sys/bus/w1/devices/28-*/w1_slave")
    if not devices:
        return None
    lines = Path(devices[0]).read_text().splitlines()
    if len(lines) < 2 or not lines[0].endswith("YES") or "t=" not in lines[1]:
        return None
    return float(lines[1].rsplit("t=", 1)[1]) / 1000


def weather() -> dict | None:
    try:
        if time.time() - WEATHER_FILE.stat().st_mtime > MAX_WEATHER_AGE:
            return None
        args = json.loads(WEATHER_FILE.read_text())["args"]
        return {
            "ambient": float(args["t1tem"]),
            "dewpoint": float(args["t1dew"]),
            "humidity": float(args["t1hum"]),
        }
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def interpolate_heater(delta: float) -> int:
    if delta <= 0:
        return 0
    for (pwm0, delta0), (pwm1, delta1) in zip(CALIBRATION, CALIBRATION[1:]):
        if delta <= delta1:
            fraction = (delta - delta0) / (delta1 - delta0)
            return round(pwm0 + fraction * (pwm1 - pwm0))
    return 100


def thermal_fan(cpu: float) -> int:
    if cpu < 60:
        return 0
    if cpu < 70:
        return 35
    if cpu < 80:
        return 70
    return 100


def calculate(current_weather: dict | None, dome: float | None, cpu: float) -> tuple[int, int, str]:
    # Missing/stale input must never energise the dome heater.
    if current_weather is None or dome is None:
        return 0, thermal_fan(cpu), "sensor-data-unavailable"

    ambient = current_weather["ambient"]
    dewpoint = current_weather["dewpoint"]
    humidity = current_weather["humidity"]
    target = max(dewpoint + TARGET_DEW_MARGIN, ambient + TARGET_AMBIENT_MARGIN)
    heater = interpolate_heater(target - dome)
    margin = dome - dewpoint

    if humidity >= 95:
        heater = max(heater, 30 if margin < 2 else 25 if margin < 4 else 20 if margin < 6 else 15)
    if ambient <= 0 and humidity >= 85:
        frost_baseline = round(max(12, min(28, 20 + 2 * (6.5 - margin))))
        heater = max(heater, frost_baseline)

    heater = max(0, min(100, heater))
    fan = thermal_fan(cpu)
    if heater:
        mixing = 28 if humidity >= 98 else 24 if humidity >= 95 else 20 if humidity >= 90 else 15
        fan = max(fan, min(55, mixing + round(heater * (0.10 if ambient <= 0 else 0.18))))
    return heater, fan, "active"


def write_state(payload: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=STATE_FILE.parent, delete=False) as handle:
        json.dump(payload, handle, separators=(",", ":"))
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(STATE_FILE)


def main() -> None:
    global STOP
    from gpiozero import PWMOutputDevice

    signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__("STOP", True))
    signal.signal(signal.SIGINT, lambda *_: globals().__setitem__("STOP", True))

    fan = HardwarePwm()
    heater = PWMOutputDevice(HEATER_PIN, frequency=500, initial_value=0)
    notify("READY=1")
    try:
        while not STOP:
            cpu = cpu_temperature()
            dome = dome_temperature()
            current_weather = weather()
            heater_pct, fan_pct, status = calculate(current_weather, dome, cpu)
            heater.value = heater_pct / 100
            fan.value = fan_pct / 100
            state = {
                "timestamp": time.time(), "status": status, "cpu_c": cpu,
                "dome_c": dome, "weather": current_weather,
                "heater_pct": heater_pct, "fan_pct": fan_pct,
            }
            write_state(state)
            print(json.dumps(state, separators=(",", ":")), flush=True)
            notify("WATCHDOG=1")
            end = time.monotonic() + LOOP_SECONDS
            while not STOP and time.monotonic() < end:
                time.sleep(0.5)
    finally:
        heater.off()
        fan.off()
        heater.close()
        fan.close()


if __name__ == "__main__":
    main()
