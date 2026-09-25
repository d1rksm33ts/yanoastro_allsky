#!/usr/bin/env python3
"""Authenticated focus helper API for the YaNoAstro AllSky camera."""

import hmac
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import lgpio
import numpy as np
from flask import Flask, Response, jsonify, request, send_file

from focus_motor import FocusMotor


IMAGE_PATH = Path(os.getenv(
    "YANOA_FOCUS_IMAGE_PATH",
    "/var/www/html/allsky/images/latest.jpg",
))
TOKEN_FILE = Path(os.getenv(
    "YANOA_FOCUS_TOKEN_FILE",
    "/etc/yanoa-allsky-focus/token",
))
MAX_MOVE_STEPS = int(os.getenv("YANOA_FOCUS_MAX_MOVE_STEPS", "2000"))
FRAME_WAIT_SECONDS = float(os.getenv("YANOA_FOCUS_FRAME_WAIT_SECONDS", "15"))
app = Flask(__name__)
operation_lock = threading.RLock()
session_lock = threading.Lock()
session = {"best_hfr": None, "best_position": None, "current": None, "points": []}


def _token():
    return TOKEN_FILE.read_text().strip()


@app.before_request
def authenticate():
    if request.path == "/health/":
        return None
    supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        expected = _token()
    except OSError:
        return jsonify({"error": "Focus token is unavailable"}), 503
    if not supplied or not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "Unauthorized"}), 401
    return None


def _position():
    with FocusMotor() as motor:
        return motor.position


def _load_image():
    image = cv2.imread(str(IMAGE_PATH), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("The latest AllSky frame is unavailable")
    return image


def _gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)


def _brightest_star(gray, x=None, y=None, search_radius=70):
    height, width = gray.shape
    if x is None or y is None:
        margin = max(16, min(width, height) // 40)
        roi = gray[margin:height-margin, margin:width-margin]
        _, _, _, location = cv2.minMaxLoc(cv2.GaussianBlur(roi, (0, 0), 1.2))
        return location[0] + margin, location[1] + margin
    x, y = int(x), int(y)
    x0, x1 = max(0, x-search_radius), min(width, x+search_radius+1)
    y0, y1 = max(0, y-search_radius), min(height, y+search_radius+1)
    roi = gray[y0:y1, x0:x1]
    if not roi.size:
        raise ValueError("Selected star is outside the image")
    _, _, _, location = cv2.minMaxLoc(cv2.GaussianBlur(roi, (0, 0), 1.2))
    return location[0] + x0, location[1] + y0


def _hfr(gray, x, y, radius=18):
    height, width = gray.shape
    if x < radius or y < radius or x >= width-radius or y >= height-radius:
        raise ValueError("Selected star is too close to the image edge")
    patch = gray[y-radius:y+radius+1, x-radius:x+radius+1].copy()
    border = np.concatenate((patch[0], patch[-1], patch[:, 0], patch[:, -1]))
    patch -= float(np.median(border))
    np.maximum(patch, 0, out=patch)
    total = float(patch.sum())
    if total <= 0:
        raise ValueError("No measurable star at this position")
    yy, xx = np.indices(patch.shape)
    distances = np.sqrt((xx-radius) ** 2 + (yy-radius) ** 2).ravel()
    flux = patch.ravel()
    order = np.argsort(distances)
    cumulative = np.cumsum(flux[order])
    index = int(np.searchsorted(cumulative, total / 2.0))
    return float(distances[order[min(index, len(order)-1)]])


def _measure(x=None, y=None):
    image = _load_image()
    gray = _gray(image)
    star_x, star_y = _brightest_star(gray, x, y)
    hfr = _hfr(gray, star_x, star_y)
    position = _position()
    measured = {
        "hfr": round(hfr, 3), "x": star_x, "y": star_y,
        "position": position,
        "captured_at": datetime.fromtimestamp(
            IMAGE_PATH.stat().st_mtime, timezone.utc
        ).isoformat(),
        "width": int(image.shape[1]), "height": int(image.shape[0]),
    }
    with session_lock:
        best = session["best_hfr"]
        if best is None or hfr < best:
            session["best_hfr"] = hfr
            session["best_position"] = position
        measured["best_hfr"] = round(session["best_hfr"], 3)
        measured["best_position"] = session["best_position"]
        measured["delta"] = round(hfr - session["best_hfr"], 3)
        session["current"] = measured
        session["points"].append({
            "position": position, "hfr": round(hfr, 3),
            "captured_at": measured["captured_at"],
        })
        session["points"] = session["points"][-100:]
    return measured


def _wait_for_frame(previous_mtime):
    deadline = time.monotonic() + FRAME_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            if IMAGE_PATH.stat().st_mtime > previous_mtime:
                return True
        except FileNotFoundError:
            pass
        time.sleep(0.25)
    return False


@app.get("/health/")
def health():
    return jsonify({"status": "ok", "service": "yanoa-allsky-focus"})


@app.get("/api/focus/status/")
def status():
    with session_lock:
        result = dict(session)
        result["points"] = list(session["points"])
    result.update({
        "available": IMAGE_PATH.is_file(), "position": _position(),
        "motor": "28BYJ-48 / ULN2003", "pins": list((5, 6, 13, 16)),
    })
    return jsonify(result)


@app.post("/api/focus/reset/")
def reset():
    with session_lock:
        session.update({"best_hfr": None, "best_position": None, "current": None, "points": []})
    return jsonify({"status": "ok"})


@app.post("/api/focus/measure/")
def measure():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"status": "ok", "measurement": _measure(data.get("x"), data.get("y"))})
    except (RuntimeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422


@app.post("/api/focus/move/")
def move():
    data = request.get_json(silent=True) or {}
    try:
        steps = int(data.get("steps", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Steps must be an integer"}), 400
    if not steps or abs(steps) > MAX_MOVE_STEPS:
        return jsonify({"error": f"Steps must be between -{MAX_MOVE_STEPS} and {MAX_MOVE_STEPS}"}), 400
    if not operation_lock.acquire(blocking=False):
        return jsonify({"error": "A focus operation is already running"}), 409
    try:
        previous_mtime = IMAGE_PATH.stat().st_mtime if IMAGE_PATH.exists() else 0
        with FocusMotor() as motor:
            position = motor.move_steps(steps)
        fresh_frame = _wait_for_frame(previous_mtime)
        measurement = _measure(data.get("x"), data.get("y")) if fresh_frame else None
        return jsonify({
            "status": "ok", "position": position, "fresh_frame": fresh_frame,
            "measurement": measurement,
        })
    except (OSError, RuntimeError, ValueError, lgpio.error) as exc:
        return jsonify({"error": str(exc)}), 422
    finally:
        operation_lock.release()


@app.get("/api/focus/image/")
def image():
    if not IMAGE_PATH.is_file():
        return Response(status=404)
    return send_file(IMAGE_PATH, mimetype="image/jpeg", max_age=0)


@app.get("/api/focus/crop/")
def crop():
    try:
        image = _load_image()
        gray = _gray(image)
        x, y = _brightest_star(gray, request.args.get("x"), request.args.get("y"))
        size = min(240, max(32, int(request.args.get("size", 96))))
        radius = size // 2
        padded = cv2.copyMakeBorder(image, radius, radius, radius, radius, cv2.BORDER_CONSTANT)
        cutout = padded[y:y+size, x:x+size]
        cutout = cv2.resize(cutout, (480, 480), interpolation=cv2.INTER_NEAREST)
        ok, encoded = cv2.imencode(".jpg", cutout, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise RuntimeError("Unable to encode star crop")
        return Response(encoded.tobytes(), mimetype="image/jpeg", headers={"Cache-Control": "no-store"})
    except (RuntimeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422
