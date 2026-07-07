import platform
import subprocess

SYSTEM = platform.system()


def open_app(app_name):
    try:
        if SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
            return f"Opened {app_name}, sir."

        elif SYSTEM == "Linux":
            subprocess.Popen([app_name.lower()])
            return f"Opened {app_name}, sir."

        elif SYSTEM == "Windows":
            subprocess.Popen(["start", app_name], shell=True)
            return f"Opened {app_name}, sir."

        return f"Unsupported operating system: {SYSTEM}"

    except Exception as e:
        return f"Failed to open {app_name}: {e}"


def close_app(app_name):
    try:
        if SYSTEM == "Darwin":
            result = subprocess.run(
                ["osascript", "-e", f'tell application "{app_name}" to quit'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return f"Closed {app_name}, sir."

            subprocess.run(
                ["pkill", "-i", app_name],
                capture_output=True,
                text=True
            )
            return f"Force-closed {app_name}, sir."

        elif SYSTEM == "Linux":
            subprocess.run(
                ["pkill", "-i", app_name],
                capture_output=True,
                text=True
            )
            return f"Closed {app_name}, sir."

        elif SYSTEM == "Windows":
            subprocess.run(
                ["taskkill", "/IM", app_name + ".exe", "/F"],
                shell=True,
                capture_output=True,
                text=True
            )
            return f"Closed {app_name}, sir."

        return f"Unsupported operating system: {SYSTEM}"

    except Exception as e:
        return f"Failed to close {app_name}: {e}"
