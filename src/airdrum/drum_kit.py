"""Drum pad layout in normalized (0-1) screen coordinates.

8-piece kit arranged from the drummer's point of view:

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


PADS: list[Pad] = [
    Pad("crash",     0.22, 0.13, 0.080, (30, 180, 255), "Crash"),
    Pad("tom1",      0.40, 0.28, 0.080, (180, 60, 140), "Tom 1"),
    Pad("tom2",      0.60, 0.28, 0.080, (200, 180, 40), "Tom 2"),
    Pad("ride",      0.80, 0.15, 0.085, (30, 180, 255), "Ride"),
    Pad("hihat",     0.15, 0.45, 0.080, (40, 200, 255), "Hi-Hat"),
    Pad("snare",     0.48, 0.50, 0.095, (40, 40, 240),  "Snare"),
    Pad("floor_tom", 0.82, 0.52, 0.098, (70, 170, 80),  "Floor Tom"),
    Pad("kick",      0.48, 0.80, 0.125, (160, 160, 160), "Kick"),
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
        if dist < pad.r * 1.55 and dist < best_dist:
            best, best_dist = pad, dist
    return best


def draw_pads(frame: np.ndarray, active_pad_ids: set[str] | None = None) -> None:
    """Draw thin, mostly transparent rings so hands stay visible."""
    h, w = frame.shape[:2]
    active = active_pad_ids or set()

    for pad in PADS:
        cx, cy = int(pad.cx * w), int(pad.cy * h)
        r = int(pad.r * w)

        is_active = pad.id in active
        color = pad.color
        if is_active:
            color = tuple(min(255, int(c * 1.4)) for c in pad.color)

        # very light fill (almost transparent)
        overlay = frame.copy()
        fill = tuple(max(0, c // 6) for c in pad.color)
        cv2.circle(overlay, (cx, cy), r, fill, -1)
        cv2.addWeighted(overlay, 0.25 if is_active else 0.12, frame, 0.75 if is_active else 0.88, 0, frame)

        # thin outer ring
        thickness = 4 if is_active else 2
        cv2.circle(frame, (cx, cy), r, color, thickness)

        # tiny center crosshair so you can aim
        cv2.drawMarker(frame, (cx, cy), color, markerType=cv2.MARKER_CROSS, markerSize=8, thickness=1)

        # label
        label = pad.label
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(frame, label, (cx - tw // 2, cy + r + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
