import platform
import subprocess
from pathlib import Path

import psutil

SYSTEM = platform.system()


def notify(message):
    try:
        if SYSTEM == "Darwin":
            script = f'display notification "{message}"'
            subprocess.run(["osascript", "-e", script])

        elif SYSTEM == "Linux":
            subprocess.run(["notify-send", message])

        elif SYSTEM == "Windows":
            return f"{message}"

        return f"{message}"

    except Exception as e:
        return f"Notification failed: {e}"


def battery_status():
    battery = psutil.sensors_battery()

    if battery is None:
        return notify("No battery detected.")

    percent = battery.percent
    plugged = "charging" if battery.power_plugged else "not charging"

    return notify(f"Battery is at {percent}% and {plugged}.")


def hardware_status():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    return notify(f"CPU {cpu}% | RAM {ram}% | Disk {disk}%")

def downloads_status():
    downloads = Path.home() / "Downloads"

    if not downloads.exists():
        return notify("Downloads folder not found.")

    files = [f for f in downloads.iterdir() if f.is_file()]

    if not files:
        return notify("No files in Downloads.")

    latest = max(files, key=lambda f: f.stat().st_mtime)

    incomplete_extensions = [".crdownload", ".download", ".part"]

    active_downloads = [
        f.name for f in files
        if any(f.name.endswith(ext) for ext in incomplete_extensions)
    ]

    if active_downloads:
        return notify(f"Active download detected: {active_downloads[0]}")

    return notify(f"Latest file: {latest.name}")
