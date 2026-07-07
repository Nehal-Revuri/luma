"""Live webcam: fast hand overlay, optional YOLO, inspect drawing."""

from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

from core.vision.inspect_mode import InspectSession
from core.vision.ipc import fetch_state, post_inspection_result
from core.vision.shapes import crop_inspection

VISION_DIR = Path(__file__).parent
YOLO_WEIGHTS = VISION_DIR / "yolov8n.pt"
HAND_MODEL = VISION_DIR / "hand_landmarker.task"

FINGERTIP_IDS = (4, 8, 12, 16, 20)
FINGERTIP_RADIUS = 10
FINGERTIP_COLOR = (255, 160, 60)
FINGERTIP_ALPHA = 0.42

DETECT_CONF = 0.5
DETECT_IMGSZ = 480
DETECT_EVERY_N = 8
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


def _ensure_hand_model() -> None:
    if HAND_MODEL.exists():
        return
    raise FileNotFoundError(
        f"Missing {HAND_MODEL.name}. Download with:\n"
        "curl -L -o hand_landmarker.task "
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task"
    )


def create_hand_tracker() -> HandLandmarker:
    _ensure_hand_model()
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(HAND_MODEL)),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.45,
        min_hand_presence_confidence=0.45,
        min_tracking_confidence=0.45,
    )
    return HandLandmarker.create_from_options(options)


def draw_fingertips(frame, hand_result) -> None:
    if not hand_result.hand_landmarks:
        return

    h, w = frame.shape[:2]
    overlay = frame.copy()

    for hand in hand_result.hand_landmarks:
        for tip_id in FINGERTIP_IDS:
            tip = hand[tip_id]
            cx, cy = int(tip.x * w), int(tip.y * h)
            cv2.circle(overlay, (cx, cy), FINGERTIP_RADIUS, FINGERTIP_COLOR, -1, cv2.LINE_AA)

    cv2.addWeighted(overlay, FINGERTIP_ALPHA, frame, 1 - FINGERTIP_ALPHA, 0, frame)


def draw_yolo_boxes(frame, result, names: dict) -> None:
    boxes = result.boxes
    if boxes is None:
        return

    for box in boxes:
        cls_id = int(box.cls[0])
        if cls_id == 0:
            continue
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        label = f"{names[cls_id]} {conf:.0%}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 80), 2)
        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 220, 80),
            1,
            cv2.LINE_AA,
        )


def open_camera() -> cv2.VideoCapture:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def run() -> None:
    print("Loading hand tracker...")
    hands = create_hand_tracker()
    inspect = InspectSession()

    model = None
    class_names = {}
    last_yolo = None
    frame_idx = 0
    frame_ts = 0
    remote_mode = "normal"

    cap = open_camera()
    print("Press q to quit.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)

            if frame_idx % 3 == 0:
                state = fetch_state()
                mode = state.get("mode", "normal")
                if mode != remote_mode:
                    remote_mode = mode
                    inspect.set_enabled(mode == "inspect")
                    if mode != "inspect":
                        model = None

                if state.get("analyze_requested"):
                    detected: list[str] = []
                    if inspect.shape and inspect.last_frame is not None:
                        crop, _ = crop_inspection(inspect.last_frame, inspect.shape)
                        if model is None:
                            print("Loading YOLO for inspection...", flush=True)
                            from ultralytics import YOLO

                            model = YOLO(str(YOLO_WEIGHTS))
                            class_names = model.names

                        crop_result = model.predict(
                            crop,
                            verbose=False,
                            conf=DETECT_CONF,
                            imgsz=DETECT_IMGSZ,
                            max_det=5,
                        )[0]
                        if crop_result.boxes is not None:
                            detected = [
                                class_names[int(cls_id)]
                                for cls_id in crop_result.boxes.cls
                                if int(cls_id) != 0
                            ]

                    if inspect.analyze(detected=detected):
                        print("Inspection crop saved.", flush=True)
                    else:
                        post_inspection_result({"ready": False, "error": "draw_a_shape_first"})

            if inspect.enabled:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                frame_ts += 33
                hand_result = hands.detect_for_video(mp_image, frame_ts)
                inspect.update(frame, hand_result)
                inspect.draw_hud(frame)
                draw_fingertips(frame, hand_result)
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                frame_ts += 33
                hand_result = hands.detect_for_video(mp_image, frame_ts)
                draw_fingertips(frame, hand_result)

                if frame_idx % DETECT_EVERY_N == 0:
                    if model is None:
                        print("Loading YOLO (lazy, yolov8n)...", flush=True)
                        from ultralytics import YOLO

                        model = YOLO(str(YOLO_WEIGHTS))
                        class_names = model.names

                    last_yolo = model.predict(
                        frame,
                        verbose=False,
                        conf=DETECT_CONF,
                        imgsz=DETECT_IMGSZ,
                        classes=list(range(1, 80)),
                        max_det=4,
                    )[0]

                if last_yolo is not None:
                    draw_yolo_boxes(frame, last_yolo, class_names)

            cv2.imshow("LUMA Vision Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            frame_idx += 1
    finally:
        cap.release()
        hands.close()
        cv2.destroyAllWindows()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
