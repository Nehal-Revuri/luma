from pathlib import Path
from datetime import datetime

import mss
from PIL import Image


SCREENSHOT_DIR = Path.home() / "Desktop" / "LUMA_screenshots"


def capture_screen():
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = SCREENSHOT_DIR / f"screen_{timestamp}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        img = Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.rgb
        )

        img.save(output_path)

    return str(output_path)


def whats_on_screen():
    path = capture_screen()
    return path
