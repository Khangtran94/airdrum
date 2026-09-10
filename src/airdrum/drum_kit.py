"""Drum pad layout, in normalized (0-1) screen coordinates.

Arranged like a real 8-piece kit seen from the player's point of view,
matching a standard kit diagram:

    Crash    Tom1    Tom2    Ride
    Hi-Hat        Snare      Floor Tom
                  Kick

All rings are spaced so none overlap (checked: every pairwise center
distance > sum of the two radii, with margin).
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class Pad:
    id: str
    cx: float
    cy: float
    r: float
    color: tuple[int, int, int]  # BGR for OpenCV
    label: str


# BGR colors (OpenCV convention), chosen to roughly match a typical kit diagram
PADS: list[Pad] = [
    Pad("crash", 0.24, 0.12, 0.075, (35, 166, 245), "Crash"),        # gold
    Pad("tom1", 0.40, 0.30, 0.075, (178, 58, 124), "Tom 1"),         # purple
    Pad("tom2", 0.60, 0.30, 0.075, (196, 181, 45), "Tom 2"),         # teal
    Pad("ride", 0.78, 0.14, 0.08, (35, 166, 245), "Ride"),           # gold
    Pad("hihat", 0.16, 0.46, 0.075, (35, 166, 245), "Hi-Hat"),       # gold
    Pad("snare", 0.47, 0.49, 0.085, (42, 42, 231), "Snare"),         # red
    Pad("floor_tom", 0.80, 0.52, 0.09, (72, 161, 76), "Floor Tom"),  # green
    Pad("kick", 0.47, 0.80, 0.11, (140, 140, 140), "Kick"),          # gray
]


def pad_by_id(pad_id: str) -> Pad | None:
    for p in PADS:
        if p.id == pad_id:
            return p
    return None


def detect_pad_hit(nx: float, ny: float) -> Pad | None:
    """Given a normalized point, return the *nearest* pad whose ring contains
    it (within a little tolerance beyond the drawn radius), or None.

    Picking the nearest (rather than the first match in list order) matters
    if pads ever get close together again - it avoids one pad silently
    "stealing" hits meant for its neighbor.
    """
    best: Pad | None = None
    best_dist = float("inf")
    for pad in PADS:
        dx, dy = nx - pad.cx, ny - pad.cy
        dist = math.hypot(dx, dy)
        if dist < pad.r * 1.3 and dist < best_dist:
            best, best_dist = pad, dist
    return best
