#!/usr/bin/env python3
"""28BYJ-48/ULN2003 focus motor used by the YaNoAstro AllSky camera."""

import json
import os
import threading
import time
from pathlib import Path

import lgpio


PINS = (5, 6, 13, 16)
HALFSTEPS = (
    (1, 0, 0, 0),
    (1, 1, 0, 0),
    (0, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 0),
    (0, 0, 1, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
)
STATE_FILE = Path(os.getenv(
    "YANOA_FOCUS_STATE_FILE",
    "/var/lib/yanoa-allsky-focus/focus-position.json",
))
STEP_DELAY = float(os.getenv("YANOA_FOCUS_STEP_DELAY", "0.004"))
MAX_POSITION = int(os.getenv("YANOA_FOCUS_MAX_POSITION", "20000"))
_MOTOR_LOCK = threading.Lock()


class FocusMotor:
    """Persistent half-step controller, ported from the legacy pigpio driver."""

    def __init__(self):
        self.position = 0
        self.phase_index = 0
        self._load_state()
        self.chip = lgpio.gpiochip_open(0)
        try:
            for pin in PINS:
                lgpio.gpio_claim_output(self.chip, 0, pin, 0)
        except Exception:
            lgpio.gpiochip_close(self.chip)
            raise

    def _load_state(self):
        try:
            data = json.loads(STATE_FILE.read_text())
            self.position = int(data.get("position", 0))
            self.phase_index = int(data.get("phase_index", 0)) % len(HALFSTEPS)
        except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
            self.position = 0
            self.phase_index = 0

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps({
            "position": self.position,
            "phase_index": self.phase_index,
        }))
        temporary.replace(STATE_FILE)

    def _apply_phase(self):
        for pin, value in zip(PINS, HALFSTEPS[self.phase_index]):
            lgpio.gpio_write(self.chip, pin, value)

    def move_steps(self, steps, delay=STEP_DELAY):
        steps = int(steps)
        target = self.position + steps
        if not -MAX_POSITION <= target <= MAX_POSITION:
            raise ValueError(
                f"Target {target} exceeds the configured safety range "
                f"(-{MAX_POSITION}..{MAX_POSITION})"
            )
        direction = 1 if steps > 0 else -1
        with _MOTOR_LOCK:
            for _ in range(abs(steps)):
                self.phase_index = (self.phase_index + direction) % len(HALFSTEPS)
                self._apply_phase()
                time.sleep(delay)
                self.position += direction
            self._save_state()
        return self.position

    def goto(self, target, delay=STEP_DELAY):
        return self.move_steps(int(target) - self.position, delay)

    def set_zero(self):
        self.position = 0
        self._save_state()

    def cleanup(self):
        for pin in PINS:
            try:
                lgpio.gpio_write(self.chip, pin, 0)
                lgpio.gpio_free(self.chip, pin)
            except lgpio.error:
                pass
        lgpio.gpiochip_close(self.chip)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.cleanup()
