"""Thumb-index pinch detection for inspect drawing."""

THUMB_TIP = 4
INDEX_TIP = 8


class PinchToggle:
    """Fire once when thumb and index clasp together."""

    def __init__(self, on_threshold: float = 0.05, off_threshold: float = 0.07, cooldown: int = 12):
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold
        self.cooldown = cooldown
        self._closed = False
        self._cooldown_left = 0

    def _distance(self, hand, frame_size: tuple[int, int]) -> float:
        w, h = frame_size
        thumb = hand[THUMB_TIP]
        index = hand[INDEX_TIP]
        tx, ty = thumb.x * w, thumb.y * h
        ix, iy = index.x * w, index.y * h
        return ((tx - ix) ** 2 + (ty - iy) ** 2) ** 0.5

    def update(self, hand, frame_size: tuple[int, int]) -> bool:
        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return False

        dist = self._distance(hand, frame_size)
        min_side = min(frame_size)

        if not self._closed and dist < self.on_threshold * min_side:
            self._closed = True
            self._cooldown_left = self.cooldown
            return True

        if self._closed and dist > self.off_threshold * min_side:
            self._closed = False

        return False


def pinch_anchor(hand, frame_size: tuple[int, int]) -> tuple[int, int]:
    """Midpoint between thumb and index — the drawing anchor."""
    w, h = frame_size
    thumb = hand[THUMB_TIP]
    index = hand[INDEX_TIP]
    cx = int((thumb.x + index.x) * 0.5 * w)
    cy = int((thumb.y + index.y) * 0.5 * h)
    return cx, cy


def fingertip_points(hand, frame_size: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    w, h = frame_size
    thumb = hand[THUMB_TIP]
    index = hand[INDEX_TIP]
    return (int(thumb.x * w), int(thumb.y * h)), (int(index.x * w), int(index.y * h))
