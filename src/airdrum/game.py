"""Main game loop: capture -> track hands -> detect strikes -> score -> render."""
from __future__ import annotations

import time

import cv2

from .audio_engine import AudioEngine
from .beatmap import Note, build_demo_beatmap
from .camera import Camera
from .drum_kit import PADS, detect_pad_hit
from .hand_tracker import HandTracker

STRIKE_VELOCITY = 2.2       # normalized units/sec, downward, to count as a "hit"
STRIKE_COOLDOWN = 0.15      # seconds, debounce per hand
HIT_WINDOW = 0.18           # seconds tolerance around a note's target time
TRAVEL_TIME = 1.2           # seconds for a falling note to reach its pad
COUNT_IN = 2.0              # seconds before the beatmap starts


class HandState:
    def __init__(self):
        self.prev_y: float | None = None
        self.prev_t: float | None = None
        self.cooldown_until: float = 0.0


class GameState:
    def __init__(self, bpm: float):
        self.score = 0
        self.combo = 0
        self.hit_notes = 0
        self.total_notes_seen = 0
        self.bpm = bpm


def run_practice(camera_index: int = 0, show_skeleton: bool = True):
    """Practice mode: no beatmap, no scoring, no strike-velocity requirement.
    Just touch a ring with your fingertip and it plays that drum's sound -
    once per entry, like a real drumstick bouncing off a head. To trigger
    the same pad again you have to leave the ring and come back in."""
    cam = Camera(index=camera_index)
    tracker = HandTracker()
    audio = AudioEngine()

    # Per hand: which pad (if any) it was inside on the previous frame.
    # None means "outside all pads". Sound only fires on the transition
    # from None -> some pad (an "entry" edge), not while lingering inside.
    last_pad_id: dict[int, str | None] = {}

    window_name = "Air Drum - Practice Mode"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("Practice mode: touch a ring with your fingertip to play its sound. Press 'q' to quit.")

    try:
        while True:
            frame = cam.read()
            if frame is None:
                print("Camera read failed - check iVCam connection.")
                break

            h, w = frame.shape[:2]

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tips, result = tracker.process(frame_rgb)

            if show_skeleton:
                tracker.draw_landmarks(frame, result)

            for tip in tips:
                nx, ny = tip.x, tip.y
                pad = detect_pad_hit(nx, ny)
                prev_pad_id = last_pad_id.get(tip.hand_id)

                if pad is not None and prev_pad_id is None:
                    # entering a ring from outside -> fire once
                    audio.play(pad.id)
                    print(f"[hit] hand {tip.hand_id} -> {pad.label}")

                last_pad_id[tip.hand_id] = pad.id if pad else None

                px, py = int(nx * w), int(ny * h)
                color = (0, 255, 0) if pad else (255, 255, 255)
                cv2.circle(frame, (px, py), 12, color, -1)

            _draw_pads(frame)
            cv2.putText(frame, "PRACTICE MODE - touch a ring", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "Press 'q' to quit", (20, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()


def run(camera_index: int = 0, bpm: float = 100.0, bars: int = 64, show_skeleton: bool = True):
    cam = Camera(index=camera_index)
    tracker = HandTracker()
    audio = AudioEngine()
    state = GameState(bpm)
    hand_states: dict[int, HandState] = {}

    song_start = time.time() + COUNT_IN
    notes: list[Note] = build_demo_beatmap(bpm, song_start, bars=bars)

    window_name = "Air Drum"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            frame = cam.read()
            if frame is None:
                print("Camera read failed - check iVCam connection.")
                break

            now = time.time()
            h, w = frame.shape[:2]

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tips, result = tracker.process(frame_rgb)

            if show_skeleton:
                tracker.draw_landmarks(frame, result)

            for tip in tips:
                nx, ny = tip.x, tip.y
                hs = hand_states.setdefault(tip.hand_id, HandState())
                if hs.prev_y is not None:
                    dt = max(now - hs.prev_t, 1 / 60)
                    vy = (ny - hs.prev_y) / dt
                    if vy > STRIKE_VELOCITY and now > hs.cooldown_until:
                        pad = detect_pad_hit(nx, ny)
                        if pad:
                            _register_hit(pad.id, now, notes, state, audio)
                            hs.cooldown_until = now + STRIKE_COOLDOWN
                hs.prev_y = ny
                hs.prev_t = now

                # draw the tracked "stick tip" marker
                px, py = int(nx * w), int(ny * h)
                cv2.circle(frame, (px, py), 10, (255, 255, 255), -1)

            _draw_pads(frame)
            _draw_falling_notes(frame, notes, now)
            _draw_hud(frame, state)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()


def _register_hit(pad_id: str, now_abs: float, notes: list[Note], state: GameState, audio: AudioEngine):
    """now_abs: absolute time.time() the strike occurred. notes[].time is also
    an absolute epoch time (see build_demo_beatmap), so we compare directly."""
    best: Note | None = None
    best_dt = float("inf")
    for n in notes:
        if n.hit or n.pad != pad_id:
            continue
        dt = abs(n.time - now_abs)
        if dt < best_dt:
            best_dt, best = dt, n

    if best is not None and best_dt <= HIT_WINDOW:
        best.hit = True
        state.hit_notes += 1
        state.combo += 1
        judged_perfect = best_dt < 0.06
        state.score += (100 if judged_perfect else 50) + state.combo
    else:
        state.combo = 0
    audio.play(pad_id)


def _draw_pads(frame):
    h, w = frame.shape[:2]
    for pad in PADS:
        cx, cy, r = int(pad.cx * w), int(pad.cy * h), int(pad.r * w)
        cv2.circle(frame, (cx, cy), r, pad.color, 4)
        cv2.putText(frame, pad.label, (cx - 40, cy + r + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, pad.color, 2)


def _draw_falling_notes(frame, notes: list[Note], now: float):
    h, w = frame.shape[:2]
    for n in notes:
        if n.hit:
            continue
        time_to_hit = n.time - now
        if time_to_hit > TRAVEL_TIME or time_to_hit < -0.3:
            continue
        pad = next(p for p in PADS if p.id == n.pad)
        progress = 1 - time_to_hit / TRAVEL_TIME
        start_y = -0.15
        y = (start_y + (pad.cy - start_y) * progress) * h
        x = pad.cx * w
        cv2.circle(frame, (int(x), int(y)), int(pad.r * w * 0.55), pad.color, -1)

        if time_to_hit < -HIT_WINDOW and not n.missed:
            n.missed = True


def _draw_hud(frame, state: GameState):
    cv2.putText(frame, f"Score: {state.score}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f"Combo: {state.combo}", (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f"BPM: {state.bpm:.0f}", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, "Press 'q' to quit", (20, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
