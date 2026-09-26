"""Drum pad layout in normalized (0-1) screen coordinates.

8-piece kit arranged from the drummer's point of view (standard acoustic layout):

    Crash     Tom1     Tom2     Ride
    Hi-Hat         Snare        Floor Tom
                   Kick
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np


@dataclass
class Pad:
    id: str
    cx: float
    cy: float
    r: float
    color: tuple[int, int, int]  # BGR for OpenCV
    label: str


# BGR colors chosen for good contrast against typical indoor webcam backgrounds
PADS: list[Pad] = [
    Pad("crash",     0.22, 0.13, 0.078, (30, 180, 255), "Crash"),
    Pad("tom1",      0.40, 0.28, 0.078, (180, 60, 140), "Tom 1"),
    Pad("tom2",      0.60, 0.28, 0.078, (200, 180, 40), "Tom 2"),
    Pad("ride",      0.80, 0.15, 0.082, (30, 180, 255), "Ride"),
    Pad("hihat",     0.15, 0.45, 0.078, (40, 200, 255), "Hi-Hat"),
    Pad("snare",     0.48, 0.50, 0.092, (40, 40, 240),  "Snare"),
    Pad("floor_tom", 0.82, 0.52, 0.095, (70, 170, 80),  "Floor Tom"),
    Pad("kick",      0.48, 0.80, 0.12,  (160, 160, 160), "Kick"),
]


def pad_by_id(pad_id: str) -> Pad | None:
    for p in PADS:
        if p.id == pad_id:
            return p
    return None


def detect_pad_hit(nx: float, ny: float) -> Pad | None:
    """Return the nearest pad that contains the point (with tolerance)."""
    best: Pad | None = None
    best_dist = float("inf")
    for pad in PADS:
        dist = math.hypot(nx - pad.cx, ny - pad.cy)
        # 1.5x radius = more forgiving for fingertip tracking
        if dist < pad.r * 1.5 and dist < best_dist:
            best, best_dist = pad, dist
    return best


def draw_pads(frame: np.ndarray, active_pad_ids: set[str] | None = None,
              pulse_strength: float = 0.0) -> None:
    """Draw all pads with a more realistic ring + subtle fill look."""
    h, w = frame.shape[:2]
    active = active_pad_ids or set()

    for pad in PADS:
        cx, cy = int(pad.cx * w), int(pad.cy * h)
        r = int(pad.r * w)

        # subtle filled circle
        fill = tuple(max(0, c // 4) for c in pad.color)
        cv2.circle(frame, (cx, cy), r, fill, -1)

        thickness = 5 if pad.id in active else 3
        color = pad.color
        if pad.id in active or pulse_strength > 0:
            color = tuple(min(255, int(c * 1.35)) for c in pad.color)
            thickness = 6

        cv2.circle(frame, (cx, cy), r, color, thickness)
        cv2.circle(frame, (cx, cy), max(4, r - 8), color, 1)

        label = pad.label
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.putText(frame, label, (cx - tw // 2, cy + r + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
