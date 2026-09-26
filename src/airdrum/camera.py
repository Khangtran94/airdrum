"""Camera capture wrapper.

Works with any device OpenCV can see, including iVCam, which registers
itself as a normal webcam device on Windows once the desktop client is
running and the iPhone/iPad app is connected.
"""
from __future__ import annotations

import cv2

# Prefer DSHOW first — many virtual cameras (iVCam, OBS, etc.) work more
# reliably with DirectShow than with MSMF on Windows.
_BACKENDS = [
    ("DSHOW", cv2.CAP_DSHOW),
    ("MSMF", cv2.CAP_MSMF),
    ("ANY", cv2.CAP_ANY),
]


def _try_open(index: int, width: int = 1280, height: int = 720):
    """Try each backend for this index, return (cap, backend_name) for the
    first one that actually opens and returns a frame, else (None, None)."""
    for name, backend in _BACKENDS:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            ok, _ = cap.read()
            if ok:
                return cap, name
        cap.release()
    return None, None


def list_cameras(max_index: int = 6) -> list[tuple[int, str]]:
    """Probe device indices 0..max_index and return (index, backend_name)
    pairs for the ones that open and return a real frame.
    """
    available = []
    for i in range(max_index):
        cap, backend = _try_open(i)
        if cap is not None:
            available.append((i, backend))
            cap.release()
    return available


class Camera:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720,
                 mirror: bool = True):
        self.mirror = mirror
        self.cap, backend = _try_open(index, width, height)
        if self.cap is None:
            raise RuntimeError(
                f"Could not open camera index {index} with any backend (tried "
                f"{[n for n, _ in _BACKENDS]}). Run `python -m airdrum.camera` to "
                f"list available indices, and make sure the iVCam desktop client "
                f"is running and connected."
            )
        print(f"Opened camera index {index} using backend {backend}  (mirror={mirror})")

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        if self.mirror:
            return cv2.flip(frame, 1)  # horizontal flip (selfie / mirror view)
        return frame

    def release(self):
        self.cap.release()


if __name__ == "__main__":
    print("Scanning for camera devices...")
    found = list_cameras()
    print(f"Available camera indices (index, backend): {found}")
    print("If iVCam isn't showing up, make sure the iVCam desktop app is open "
          "and your iPhone/iPad app is connected over USB/WiFi first.")
