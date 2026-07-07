"""Finalize drawn traces into circles/rectangles and crop inspected regions."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class InspectShape:
    kind: str  # circle | rectangle | polygon
    points: np.ndarray
    bbox: tuple[int, int, int, int]


def finalize_trace(trace: list[tuple[int, int]], frame_size: tuple[int, int]) -> InspectShape | None:
    if len(trace) < 10:
        return None

    w, h = frame_size
    pts = np.array(trace, dtype=np.int32)

    start = pts[0]
    end = pts[-1]
    closed = np.linalg.norm(start - end) < 0.12 * min(w, h)

    contour = pts.reshape(-1, 1, 2)
    perimeter = cv2.arcLength(contour, closed)
    area = cv2.contourArea(contour)

    if perimeter < 20 or area < 200:
        return None

    circularity = 4 * np.pi * area / (perimeter * perimeter + 1e-6)

    if circularity > 0.62 or (closed and circularity > 0.45):
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        radius = max(int(radius), 12)
        circle_pts = cv2.ellipse2Poly(
            (int(cx), int(cy)),
            (radius, radius),
            0,
            0,
            360,
            8,
        )
        x1 = max(int(cx - radius), 0)
        y1 = max(int(cy - radius), 0)
        x2 = min(int(cx + radius), w - 1)
        y2 = min(int(cy + radius), h - 1)
        return InspectShape("circle", circle_pts, (x1, y1, x2, y2))

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect).astype(np.int32)
    x1 = max(int(box[:, 0].min()), 0)
    y1 = max(int(box[:, 1].min()), 0)
    x2 = min(int(box[:, 0].max()), w - 1)
    y2 = min(int(box[:, 1].max()), h - 1)
    return InspectShape("rectangle", box, (x1, y1, x2, y2))


def draw_trace(frame, trace: list[tuple[int, int]]) -> None:
    if len(trace) < 2:
        return
    pts = np.array(trace, dtype=np.int32)
    cv2.polylines(frame, [pts], False, (40, 220, 255), 2, cv2.LINE_AA)


def draw_shape(frame, shape: InspectShape) -> None:
    color = (255, 180, 80) if shape.kind == "circle" else (220, 120, 255)
    if shape.kind == "circle":
        x1, y1, x2, y2 = shape.bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        radius = max((x2 - x1) // 2, (y2 - y1) // 2)
        cv2.circle(frame, (cx, cy), radius, color, 2, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [shape.points], True, color, 2, cv2.LINE_AA)


def crop_inspection(frame, shape: InspectShape, padding: int = 12) -> tuple[np.ndarray, dict]:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = shape.bbox
    x1 = max(x1 - padding, 0)
    y1 = max(y1 - padding, 0)
    x2 = min(x2 + padding, w)
    y2 = min(y2 + padding, h)

    crop = frame[y1:y2, x1:x2].copy()
    meta = {
        "ready": True,
        "shape": shape.kind,
        "bbox": [x1, y1, x2, y2],
    }
    return crop, meta
