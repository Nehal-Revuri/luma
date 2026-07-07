from fastapi import FastAPI
import queue
import threading

app = FastAPI()

pending_voice = queue.Queue()
listen_callback = None

vision_lock = threading.Lock()
vision_state = {
    "mode": "normal",
    "analyze_requested": False,
    "last_inspection": None,
}


@app.post("/listen")
def listen():
    if listen_callback is None:
        return {"status": "no_listener"}

    threading.Thread(target=listen_callback, daemon=True).start()
    return {"status": "listening"}


@app.post("/interrupt")
def interrupt():
    return {"status": "interrupt_not_connected_yet"}


@app.get("/vision/state")
def get_vision_state():
    with vision_lock:
        return {
            "mode": vision_state["mode"],
            "analyze_requested": vision_state["analyze_requested"],
            "last_inspection": vision_state["last_inspection"],
        }


@app.post("/vision/mode")
def set_vision_mode(payload: dict):
    mode = payload.get("mode", "normal")
    with vision_lock:
        vision_state["mode"] = mode
        if mode != "inspect":
            vision_state["analyze_requested"] = False
    return {"status": "ok", "mode": mode}


@app.post("/vision/analyze")
def request_vision_analyze():
    with vision_lock:
        vision_state["analyze_requested"] = True
    return {"status": "requested"}


@app.post("/vision/inspection-result")
def post_inspection_result(payload: dict):
    with vision_lock:
        vision_state["last_inspection"] = payload
        vision_state["analyze_requested"] = False
    return {"status": "ok"}


@app.get("/vision/inspection-result")
def get_inspection_result():
    with vision_lock:
        result = vision_state.get("last_inspection")
        return result or {"ready": False}
