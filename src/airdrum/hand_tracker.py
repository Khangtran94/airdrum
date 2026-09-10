"""MediaPipe hand tracking wrapper, using the Tasks API (HandLandmarker).

Newer mediapipe pip wheels (Windows/Python 3.12 especially) no longer ship
the legacy `mediapipe.solutions` API, so this uses the actively-maintained
Tasks API instead - the same one the browser prototype used.

On first run this downloads the hand_landmarker.task model file (~8MB) to a
local cache folder; subsequent runs reuse it, no internet needed after that.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

INDEX_FINGERTIP = 8  # landmark id

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def _ensure_model() -> str:
    cache_dir = Path.home() / ".cache" / "airdrum"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "hand_landmarker.task"
    if not model_path.exists():
        print("Downloading hand landmarker model (first run only, ~8MB)...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print(f"Saved model to {model_path}")
    return str(model_path)


@dataclass
class TipPoint:
    x: float  # normalized 0-1
    y: float  # normalized 0-1
    hand_id: int


class HandTracker:
    def __init__(self, max_hands: int = 2, detection_conf: float = 0.6, tracking_conf: float = 0.6):
        model_path = _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._frame_index = 0

    def process(self, frame_rgb) -> tuple[list[TipPoint], object]:
        """frame_rgb must be a numpy array in RGB format (not BGR).
        Returns (tip_points, raw_result) where raw_result.hand_landmarks is a
        list of lists of landmarks (21 per hand), useful for drawing."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        # timestamp must be monotonically increasing; ms works fine for VIDEO mode
        timestamp_ms = self._frame_index * 33  # assume ~30fps spacing; strictly increasing is what matters
        self._frame_index += 1
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        tips: list[TipPoint] = []
        if result.hand_landmarks:
            for idx, hand_landmarks in enumerate(result.hand_landmarks):
                lm = hand_landmarks[INDEX_FINGERTIP]
                tips.append(TipPoint(x=lm.x, y=lm.y, hand_id=idx))
        return tips, result

    def draw_landmarks(self, frame_bgr, result):
        """Draws all 21 landmarks per hand as dots (no solutions.drawing_utils
        available, so this is a simple manual version)."""
        if not result.hand_landmarks:
            return
        h, w = frame_bgr.shape[:2]
        for hand_landmarks in result.hand_landmarks:
            for lm in hand_landmarks:
                cv2.circle(frame_bgr, (int(lm.x * w), int(lm.y * h)), 3, (0, 255, 0), -1)

    def close(self):
        self._landmarker.close()

