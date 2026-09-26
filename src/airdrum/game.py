"""Main game loop: capture -> track hands -> detect strikes -> score -> render."""
from __future__ import annotations

import time

import cv2
import numpy as np

from .audio_engine import AudioEngine
from .beatmap import Note, build_demo_beatmap
from .camera import Camera
from .drum_kit import PADS, detect_pad_hit, draw_pads, pad_by_id
from .hand_tracker import HandTracker

# Tunable constants
STRIKE_VELOCITY = 1.6       # lower = easier to trigger repeated hits
STRIKE_COOLDOWN = 0.12      # seconds between hits on the same hand
HIT_WINDOW = 0.20
TRAVEL_TIME = 1.35
COUNT_IN = 2.5

FLASH_DURATION = 0.28
JUDGE_DURATION = 0.55


class HandState:
    def __init__(self):
        self.prev_y: float | None = None
        self.prev_t: float | None = None
        self.cooldown_until: float = 0.0


class Flash:
    def __init__(self, pad_id: str, t: float):
        self.pad_id = pad_id
        self.t = t


class Judgment:
    def __init__(self, text: str, color: tuple[int, int, int], t: float, x: float, y: float):
        self.text = text
        self.color = color
        self.t = t
        self.x = x
        self.y = y


class GameState:
    def __init__(self, bpm: float):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hit_notes = 0
        self.missed_notes = 0
        self.bpm = bpm
        self.flashes: list[Flash] = []
        self.judgments: list[Judgment] = []


def _detect_strike(tip_y: float, hs: HandState, now: float) -> bool:
    """Return True if this frame is a downward strike."""
    if hs.prev_y is None:
        hs.prev_y = tip_y
        hs.prev_t = now
        return False

    dt = max(now - hs.prev_t, 1 / 60)
    vy = (tip_y - hs.prev_y) / dt
    hs.prev_y = tip_y
    hs.prev_t = now

    if vy > STRIKE_VELOCITY and now > hs.cooldown_until:
        hs.cooldown_until = now + STRIKE_COOLDOWN
        return True
    return False


def run_practice(camera_index: int = 0, show_skeleton: bool = True, mirror: bool = True):
    """Practice mode: velocity-based strikes (like a real drummer).

    Keep your fingertip near/inside a ring and make short downward
    motions to trigger the sound repeatedly. No need to leave the ring.
    """
    cam = Camera(index=camera_index, mirror=mirror)
    tracker = HandTracker()
    audio = AudioEngine()
    hand_states: dict[int, HandState] = {}

    window_name = "Air Drum - Practice"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("Practice mode: strike downward inside a ring (can hit repeatedly). Press 'q' to quit.")

    try:
        while True:
            frame = cam.read()
            if frame is None:
                print("Camera read failed — check iVCam connection.")
                break

            now = time.time()
            h, w = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tips, result = tracker.process(frame_rgb)

            if show_skeleton:
                tracker.draw_landmarks(frame, result)

            active: set[str] = set()

            for tip in tips:
                nx, ny = tip.x, tip.y
                hs = hand_states.setdefault(tip.hand_id, HandState())

                if _detect_strike(ny, hs, now):
                    pad = detect_pad_hit(nx, ny)
                    if pad:
                        audio.play(pad.id)
                        active.add(pad.id)
                        print(f"[hit] hand {tip.hand_id} → {pad.label}")

                # tip marker
                px, py = int(nx * w), int(ny * h)
                inside = detect_pad_hit(nx, ny) is not None
                color = (0, 255, 0) if inside else (255, 255, 255)
                cv2.circle(frame, (px, py), 12, color, -1)
                cv2.circle(frame, (px, py), 14, (0, 0, 0), 2)

            draw_pads(frame, active_pad_ids=active)
            cv2.putText(frame, "PRACTICE  •  strike down inside a ring", (20, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "q = quit", (20, h - 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

            cv2.imshow(window_name, frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()


def run(camera_index: int = 0, bpm: float = 100.0, bars: int = 64,
        show_skeleton: bool = True, latency: float = 0.0, mirror: bool = True):
    cam = Camera(index=camera_index, mirror=mirror)
    tracker = HandTracker()
    audio = AudioEngine()
    state = GameState(bpm)
    hand_states: dict[int, HandState] = {}

    song_start = time.time() + COUNT_IN + latency
    notes: list[Note] = build_demo_beatmap(bpm, song_start, bars=bars)

    window_name = "Air Drum"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print(f"Starting song @ {bpm:.0f} BPM  |  latency offset = {latency*1000:.0f} ms")
    print("Strike downward through a ring in time with the falling notes.  q = quit")

    try:
        while True:
            frame = cam.read()
            if frame is None:
                print("Camera read failed — check iVCam connection.")
                break

            now = time.time()
            h, w = frame.shape[:2]

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tips, result = tracker.process(frame_rgb)

            if show_skeleton:
                tracker.draw_landmarks(frame, result)

            active_pads: set[str] = set()

            for tip in tips:
                nx, ny = tip.x, tip.y
                hs = hand_states.setdefault(tip.hand_id, HandState())

                if _detect_strike(ny, hs, now):
                    pad = detect_pad_hit(nx, ny)
                    if pad:
                        _register_hit(pad, now, notes, state, audio)
                        active_pads.add(pad.id)

                px, py = int(nx * w), int(ny * h)
                cv2.circle(frame, (px, py), 12, (255, 255, 255), -1)
                cv2.circle(frame, (px, py), 14, (0, 0, 0), 2)

            state.flashes = [f for f in state.flashes if now - f.t < FLASH_DURATION]
            state.judgments = [j for j in state.judgments if now - j.t < JUDGE_DURATION]

            for f in state.flashes:
                active_pads.add(f.pad_id)

            draw_pads(frame, active_pad_ids=active_pads)
            _draw_falling_notes(frame, notes, now)
            _draw_flashes(frame, state.flashes, now)
            _draw_judgments(frame, state.judgments, now)
            _draw_hud(frame, state, now, song_start)

            cv2.imshow(window_name, frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()

        total = state.hit_notes + state.missed_notes
        acc = (state.hit_notes / total * 100) if total else 0
        print(f"\nSession finished")
        print(f"  Score      : {state.score}")
        print(f"  Max combo  : {state.max_combo}")
        print(f"  Hits / Miss: {state.hit_notes} / {state.missed_notes}")
        print(f"  Accuracy   : {acc:.1f}%")


def _register_hit(pad, now_abs: float, notes: list[Note], state: GameState, audio: AudioEngine):
    best: Note | None = None
    best_dt = float("inf")
    for n in notes:
        if n.hit or n.pad != pad.id:
            continue
        dt = abs(n.time - now_abs)
        if dt < best_dt:
            best_dt, best = dt, n

    audio.play(pad.id)
    state.flashes.append(Flash(pad.id, now_abs))

    px = pad.cx
    py = pad.cy - 0.08

    if best is not None and best_dt <= HIT_WINDOW:
        best.hit = True
        state.hit_notes += 1
        state.combo += 1
        state.max_combo = max(state.max_combo, state.combo)

        if best_dt < 0.07:
            points = 100 + state.combo
            judge = Judgment("PERFECT", (0, 255, 180), now_abs, px, py)
        elif best_dt < 0.13:
            points = 70 + state.combo
            judge = Judgment("GREAT", (0, 220, 255), now_abs, px, py)
        else:
            points = 40 + state.combo
            judge = Judgment("GOOD", (100, 200, 255), now_abs, px, py)

        state.score += points
        state.judgments.append(judge)
    else:
        state.combo = 0
        state.judgments.append(Judgment("MISS", (60, 60, 255), now_abs, px, py))


def _draw_falling_notes(frame, notes: list[Note], now: float):
    h, w = frame.shape[:2]
    for n in notes:
        if n.hit:
            continue
        time_to_hit = n.time - now
        if time_to_hit > TRAVEL_TIME or time_to_hit < -0.35:
            continue

        pad = pad_by_id(n.pad)
        if pad is None:
            continue

        progress = 1.0 - (time_to_hit / TRAVEL_TIME)
        progress = max(0.0, min(1.0, progress))

        start_y = -0.12
        y = (start_y + (pad.cy - start_y) * progress) * h
        x = pad.cx * w

        base_r = int(pad.r * w * 0.48)
        r = int(base_r * (0.7 + 0.4 * progress))

        alpha = 0.45 + 0.55 * progress
        color = tuple(int(c * alpha) for c in pad.color)

        cv2.circle(frame, (int(x), int(y)), r, color, -1)
        cv2.circle(frame, (int(x), int(y)), r + 2, (255, 255, 255), 1)

        if time_to_hit < -HIT_WINDOW and not n.missed:
            n.missed = True


def _draw_flashes(frame, flashes: list[Flash], now: float):
    h, w = frame.shape[:2]
    for f in flashes:
        pad = pad_by_id(f.pad_id)
        if pad is None:
            continue
        age = (now - f.t) / FLASH_DURATION
        if age >= 1.0:
            continue
        cx, cy = int(pad.cx * w), int(pad.cy * h)
        r = int(pad.r * w * (1.0 + age * 0.9))
        alpha = 1.0 - age
        color = tuple(int(c * alpha) for c in pad.color)
        cv2.circle(frame, (cx, cy), r, color, 3)


def _draw_judgments(frame, judgments: list[Judgment], now: float):
    h, w = frame.shape[:2]
    for j in judgments:
        age = (now - j.t) / JUDGE_DURATION
        if age >= 1.0:
            continue
        y_off = int(age * 40)
        x = int(j.x * w)
        y = int(j.y * h) - y_off
        alpha = 1.0 - age
        color = tuple(int(c * alpha) for c in j.color)
        scale = 0.9 + 0.25 * (1 - age)
        cv2.putText(frame, j.text, (x - 55, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)


def _draw_hud(frame, state: GameState, now: float, song_start: float):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 130), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    cv2.putText(frame, f"Score  {state.score}", (20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f"Combo  {state.combo}", (20, 72),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 200), 2)
    cv2.putText(frame, f"BPM {state.bpm:.0f}", (20, 106),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    elapsed = max(0.0, now - song_start)
    cv2.putText(frame, f"t={elapsed:.1f}s", (w - 140, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
    cv2.putText(frame, "q = quit", (20, h - 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1)
