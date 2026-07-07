"""Launch LUMA vision detection and inspect-mode commands."""

import os
import subprocess
import time
from pathlib import Path

import requests

from core.configs.llm import ask_luma_vision

VISION_DIR = Path(__file__).resolve().parent.parent / "core" / "vision"
SRC_DIR = VISION_DIR.parent.parent
VISION_PYTHON = VISION_DIR / "venv" / "bin" / "python"
DETECT_SCRIPT = VISION_DIR / "detect_camera.py"
INSPECTION_FILE = VISION_DIR / "last_inspection.jpg"
LUMA_API = "http://127.0.0.1:8765"

_webcam_proc: subprocess.Popen | None = None


def _vision_ready() -> str | None:
    if not VISION_PYTHON.exists():
        return "Vision environment not found. Run setup in core/vision, sir."
    if not DETECT_SCRIPT.exists():
        return "Vision detection script is missing, sir."
    return None


def _ensure_webcam_running() -> str | None:
    global _webcam_proc

    err = _vision_ready()
    if err:
        return err

    if _webcam_proc is not None and _webcam_proc.poll() is None:
        return None

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)

    _webcam_proc = subprocess.Popen(
        [str(VISION_PYTHON), str(DETECT_SCRIPT)],
        cwd=str(VISION_DIR),
        env=env,
        start_new_session=True,
    )
    time.sleep(1.5)
    return None


def turn_on_webcam() -> str:
    err = _ensure_webcam_running()
    if err:
        return err
    return "Webcam vision activated, sir. Press q in the window to close."


def turn_off_webcam() -> str:
    global _webcam_proc

    try:
        requests.post(f"{LUMA_API}/vision/mode", json={"mode": "normal"}, timeout=0.5)
    except Exception:
        pass

    if _webcam_proc is None or _webcam_proc.poll() is not None:
        _webcam_proc = None
        return "Webcam vision is not running, sir."

    _webcam_proc.terminate()
    _webcam_proc = None
    return "Webcam vision closed, sir."


def enable_inspect_mode() -> str:
    err = _ensure_webcam_running()
    if err:
        return err

    try:
        requests.post(f"{LUMA_API}/vision/mode", json={"mode": "inspect"}, timeout=0.5)
    except Exception:
        return "Could not reach LUMA vision service, sir."

    return (
        "Inspect mode enabled, sir. Pinch thumb and index to start drawing, "
        "move to trace a shape, then pinch again to finish."
    )


def inspect_this_area(on_chunk=None) -> str:
    err = _ensure_webcam_running()
    if err:
        print(err, flush=True)
        if on_chunk:
            on_chunk(err)
        return err

    try:
        requests.post(f"{LUMA_API}/vision/analyze", timeout=0.5)
    except Exception:
        message = "Could not reach LUMA vision service, sir."
        print(message, flush=True)
        if on_chunk:
            on_chunk(message)
        return message

    result = None
    for _ in range(40):
        time.sleep(0.1)
        try:
            response = requests.get(f"{LUMA_API}/vision/inspection-result", timeout=0.5)
            result = response.json()
            if result.get("ready"):
                break
        except Exception:
            continue

    if not result or not result.get("ready"):
        error = (result or {}).get("error", "unknown")
        if error == "draw_a_shape_first":
            message = (
                "I do not have an inspection area yet, sir. "
                "Say inspect, draw a circle or square, then ask me to inspect this area."
            )
        else:
            message = "I could not capture the inspection area, sir. Draw a shape first."
        print(message, flush=True)
        if on_chunk:
            on_chunk(message)
        return message

    image_path = result.get("image_path") or str(INSPECTION_FILE)
    shape = result.get("shape", "region")
    detected = result.get("detected") or []

    prompt = (
        f"The user marked a {shape} on their live webcam feed and wants insights "
        f"about what is inside that region. Describe what you see clearly and give "
        f"practical observations or suggestions."
    )

    return ask_luma_vision(image_path, prompt, on_chunk=on_chunk, detected_labels=detected) or ""
