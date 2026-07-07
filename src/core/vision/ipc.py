"""Poll and post vision state through the LUMA FastAPI server."""

import requests

LUMA_API = "http://127.0.0.1:8765"


def fetch_state() -> dict:
    try:
        response = requests.get(f"{LUMA_API}/vision/state", timeout=0.05)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"mode": "normal", "analyze_requested": False}


def post_inspection_result(payload: dict) -> None:
    try:
        requests.post(
            f"{LUMA_API}/vision/inspection-result",
            json=payload,
            timeout=0.5,
        )
    except Exception:
        pass
