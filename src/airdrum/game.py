"""Main game loop: capture -> track hands -> detect strikes -> score -> render."""
from __future__ import annotations

import time

import cv2
import numpy as np

from .audio_engine import AudioEngine
from .beatmap import Note, build_lesson, load_beatmap_from_json, LESSONS
from .rhythm import Session
from .camera import Camera
from .drum_kit import PADS, detect_pad_hit, draw_pads, pad_by_id

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
    if hs.prev_y is None or now - hs.prev_t > 0.25:
        hs.prev_y = tip_y
        hs.prev_t = now
        return False

    dt = max(now - hs.prev_t, 0.001)
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
    from .hand_tracker import HandTracker
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

            now = time.perf_counter()
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
        show_skeleton: bool = True, latency: float = 0.0, mirror: bool = True,
        lesson: str = "pulse", song: str | None = None, keyboard: bool = False,
        listen: bool = False, metronome: bool = True):
    # Read/validate charts before opening hardware.
    if song:
        bpm, _ = load_beatmap_from_json(song, 0)
    cam = None
    tracker = None
    audio = None
    try:
        if not keyboard:
            from .hand_tracker import HandTracker
            cam = Camera(index=camera_index, mirror=mirror)
            tracker = HandTracker()
        audio = AudioEngine()
    except Exception:
        if cam:
            cam.release()
        if tracker:
            tracker.close()
        raise
    state = GameState(bpm)
    hand_states: dict[int, HandState] = {}
    song_start = time.perf_counter() + 4 * 60 / bpm
    notes = load_beatmap_from_json(song, song_start)[1] if song else build_lesson(bpm, song_start, bars, lesson)
    state.session = Session(notes)
    next_click = song_start - 4 * 60 / bpm
    click_index = 0
    demonstrated = set()
    key_pads = dict(zip("asdfjkl ", ["hihat", "snare", "kick", "crash", "tom1", "tom2", "floor_tom", "ride"]))
    print(LESSONS[lesson][0] if not song else f"Chart: {song}")
    print("Keys: A hi-hat, S snare, D kick, F crash, J/K toms, L floor tom, SPACE ride")

    window_name = "Air Drum"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print(f"Starting song @ {bpm:.0f} BPM  |  latency offset = {latency*1000:.0f} ms")
    print("Strike downward through a ring in time with the falling notes.  q = quit")

    try:
        while True:
            frame = np.zeros((720, 1280, 3), dtype=np.uint8) if keyboard else cam.read()
            if frame is None:
                print("Camera read failed — check connection.")
                break
            now = time.perf_counter()
            h, w = frame.shape[:2]
            tips, result = ([], None) if keyboard else tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            # Positive latency subtracts observed input delay, without moving the music.
            if not listen:
                state.session.expire(now - latency)
            state.missed_notes = state.session.misses
            state.combo = state.session.combo
            if metronome and now >= next_click:
                audio.click(click_index % 4 == 0)
                skipped = int((now - next_click) / (60 / bpm)) + 1
                click_index += skipped
                next_click += skipped * 60 / bpm
            if listen:
                for i, note in enumerate(notes):
                    if i not in demonstrated and now >= note.time:
                        if now - note.time < .2:
                            audio.play(note.pad)
                            state.flashes.append(Flash(note.pad, now))
                        demonstrated.add(i)
            if show_skeleton and tracker:
                tracker.draw_landmarks(frame, result)

            active_pads: set[str] = set()

            for tip in tips:
                nx, ny = tip.x, tip.y
                hs = hand_states.setdefault(tip.hand_id, HandState())

                if _detect_strike(ny, hs, now) and not listen:
                    pad = detect_pad_hit(nx, ny)
                    if pad:
                        _register_hit(pad, now, notes, state, audio, latency)
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
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if not listen and chr(key) in key_pads:
                _register_hit(pad_by_id(key_pads[chr(key)]), time.perf_counter(), notes, state, audio, latency)
            end_time = notes[-1].time + max(60 / bpm, HIT_WINDOW + latency)
            if now > end_time:
                break
    finally:
        if cam:
            cam.release()
        if tracker:
            tracker.close()
        audio.close()
        cv2.destroyAllWindows()
        session = state.session
        if listen:
            print("Demo finished. Replay without --listen to try it yourself.")
        else:
            bias = sum(session.errors) / len(session.errors) * 1000 if session.errors else 0
            print(f"Score: {session.score} | Max combo: {session.max_combo} | Hits: {len(session.errors)} | Misses: {session.misses} | Extra: {session.extra_hits}")
            print(f"Accuracy: {session.accuracy:.1f}% | Mean timing: {bias:+.0f} ms (+ late / - early)")
            print("Try a faster BPM when accurate; slow down if timing is inconsistent.")


def _register_hit(pad, now_abs: float, notes: list[Note], state: GameState, audio: AudioEngine, latency: float = 0.0):
    label, error = state.session.strike(pad.id, now_abs - latency)
    audio.play(pad.id)
    state.flashes.append(Flash(pad.id, now_abs))
    state.score = state.session.score
    state.combo = state.session.combo
    state.max_combo = state.session.max_combo
    state.hit_notes = len(state.session.errors)
    state.missed_notes = state.session.misses
    color = (0, 255, 180) if error is not None else (60, 60, 255)
    timing = "" if error is None else f" {error * 1000:+.0f}ms"
    state.judgments.append(Judgment(label + timing, color, now_abs, pad.cx, pad.cy - .08))


def _draw_falling_notes(frame, notes: list[Note], now: float):
    h, w = frame.shape[:2]
    for n in notes:
        if n.hit or n.missed:
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

    if now < song_start:
        count = int((song_start - now) / (60 / state.bpm)) + 1
        cv2.putText(frame, f"GET READY {min(4, count)}", (w // 2 - 140, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    elapsed = max(0.0, now - song_start)
    cv2.putText(frame, f"{state.session.accuracy:.0f}%  {elapsed:.1f}s", (w - 140, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
    cv2.putText(frame, "A:hat S:snare D:kick F:crash J/K:toms L:floor SPACE:ride | q:quit", (20, h - 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
