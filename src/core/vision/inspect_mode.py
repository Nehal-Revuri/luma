"""Inspect mode: pinch-to-draw regions on the webcam feed."""

from pathlib import Path

import cv2

from core.vision.ipc import post_inspection_result
from core.vision.pinch import PinchToggle, fingertip_points, pinch_anchor
from core.vision.shapes import InspectShape, crop_inspection, draw_shape, draw_trace, finalize_trace

INSPECTION_FILE = Path(__file__).parent / "last_inspection.jpg"


class InspectSession:
    def __init__(self):
        self.enabled = False
        self.drawing = False
        self.trace: list[tuple[int, int]] = []
        self.shape: InspectShape | None = None
        self.pinch = PinchToggle()
        self.last_frame = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.reset()

    def reset(self) -> None:
        self.drawing = False
        self.trace.clear()
        self.shape = None
        self.pinch = PinchToggle()

    def update(self, frame, hand_result) -> None:
        self.last_frame = frame
        h, w = frame.shape[:2]
        frame_size = (w, h)

        if self.shape is not None:
            draw_shape(frame, self.shape)

        if self.drawing and self.trace:
            draw_trace(frame, self.trace)

        if not hand_result.hand_landmarks:
            return

        hand = hand_result.hand_landmarks[0]

        if self.pinch.update(hand, frame_size):
            if not self.drawing:
                self.drawing = True
                self.trace.clear()
                self.shape = None
            else:
                self.drawing = False
                self.shape = finalize_trace(self.trace, frame_size)

        if self.drawing:
            anchor = pinch_anchor(hand, frame_size)
            thumb, index = fingertip_points(hand, frame_size)
            self.trace.append(anchor)
            self.trace.append(thumb)
            self.trace.append(index)

            if len(self.trace) > 2000:
                self.trace = self.trace[-2000:]

    def analyze(self, detected: list[str] | None = None) -> bool:
        if self.last_frame is None or self.shape is None:
            post_inspection_result({"ready": False, "error": "no_shape"})
            return False

        crop, meta = crop_inspection(self.last_frame, self.shape)
        cv2.imwrite(str(INSPECTION_FILE), crop)
        meta["image_path"] = str(INSPECTION_FILE)
        if detected:
            meta["detected"] = detected
        post_inspection_result(meta)
        return True

    def draw_hud(self, frame) -> None:
        if not self.enabled:
            return

        if self.drawing:
            text = "Drawing — pinch again to finish shape"
        elif self.shape is None:
            text = "Inspect mode — pinch thumb + index to draw"
        else:
            text = f"{self.shape.kind.title()} ready — say inspect this area"

        cv2.rectangle(frame, (8, 8), (420, 42), (20, 20, 20), -1)
        cv2.putText(frame, text, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA)
