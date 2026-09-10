# Air Drum — How to Install, Run & Test

This guide walks you through everything needed to get the game running on your PC, using either the built-in webcam or your iPhone/iPad via iVCam.

---

## 1. Prerequisites

### Software
- **Python 3.10 or newer** (3.11 / 3.12 recommended)
- **[uv](https://docs.astral.sh/uv/)** — modern Python package manager (very fast)

Install uv if you don’t have it yet:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Hardware options

| Input source          | What you need                                      |
|-----------------------|----------------------------------------------------|
| Built-in laptop webcam| Nothing extra                                      |
| iPhone / iPad         | iVCam app (phone) + iVCam desktop client (PC)      |

---

## 2. Clone & Install

```bash
git clone https://github.com/Khangtran94/airdrum.git
cd airdrum
uv sync
```

`uv sync` creates a virtual environment and installs all dependencies (OpenCV, MediaPipe, pygame, numpy).

On the **first run** MediaPipe will automatically download the hand-landmarker model (~8 MB) into `~/.cache/airdrum/`. After that it works offline.

---

## 3. Find the correct camera index

Especially important when using iVCam.

```bash
uv run python -m airdrum.camera
```

Example output:
```
Scanning for camera devices...
Available camera indices (index, backend): [(0, 'MSMF'), (1, 'MSMF')]
```

- Index `0` is usually the built-in webcam.
- Index `1` or `2` is often the iVCam virtual camera.

**Tip:** Make sure the iVCam desktop client is running **and** the phone/tablet is connected **before** you scan.

---

## 4. Run the game

### Practice mode (recommended first)
No falling notes, no scoring. Just touch the rings with your fingertip to hear the drum sounds.

```bash
uv run airdrum --practice --camera 1
```

### Normal song mode
Falling notes + scoring.

```bash
uv run airdrum --camera 1
```

### Useful flags

| Flag              | Example                  | Meaning                                              |
|-------------------|--------------------------|------------------------------------------------------|
| `--camera`        | `--camera 1`             | Camera device index                                  |
| `--bpm`           | `--bpm 120`              | Tempo of the demo beatmap                            |
| `--bars`          | `--bars 32`              | How many notes to generate                           |
| `--latency`       | `--latency 0.08`         | Compensate for camera delay (seconds). Try 0.05–0.12 |
| `--no-skeleton`   | `--no-skeleton`          | Hide full hand skeleton (only show tip dot)          |
| `--practice`      | `--practice`             | Free-play mode                                       |

**Full example with iVCam + latency compensation:**

```bash
uv run airdrum --camera 1 --latency 0.08 --bpm 100 --no-skeleton
```

---

## 5. How to play

1. Stand or sit so both hands are clearly visible in the camera frame.
2. A **white dot** appears on each index fingertip.
3. **Strike downward** through a colored drum ring at the moment the falling note reaches it.
4. Feedback appears:
   - **PERFECT** (green) – very accurate timing
   - **GREAT** / **GOOD** – acceptable timing
   - **MISS** (red) – too early/late or wrong pad
5. Press **`q`** to quit. A short session summary (score, max combo, accuracy) is printed in the terminal.

### Practice tips
- Start in `--practice` mode to get used to the pad positions and the strike motion.
- The game detects a **downward velocity**, not just presence inside the ring. A quick downward “hit” motion works best.
- If hits feel unresponsive → lower `STRIKE_VELOCITY` in `src/airdrum/game.py` (currently `2.0`).
- If notes feel consistently early or late → adjust `--latency`.

---

## 6. Troubleshooting

| Problem                              | Solution                                                                 |
|--------------------------------------|--------------------------------------------------------------------------|
| “Could not open camera index X”      | Run `uv run python -m airdrum.camera` and try another index. Make sure iVCam desktop + phone app are connected. |
| Black / frozen video                 | Restart iVCam client, unplug/replug USB, or switch to Wi-Fi mode in iVCam. |
| Hands not detected                   | Improve lighting, face the camera, keep hands inside the frame, avoid very dark backgrounds. |
| Hits feel late / early               | Add `--latency 0.06` … `0.12` and experiment.                            |
| Hits too sensitive / not sensitive   | Edit `STRIKE_VELOCITY` in `game.py` (lower = easier to trigger).         |
| Model download fails                 | Check internet on first run. The file is cached afterwards.              |
| pygame / audio issues                | Make sure your system audio output is working.                           |

---

## 7. Project structure (quick reference)

```
src/airdrum/
  camera.py         → webcam / iVCam capture
  hand_tracker.py   → MediaPipe hand landmarks
  drum_kit.py       → pad layout + drawing + hit detection
  audio_engine.py   → procedural drum sounds
  beatmap.py        → note generation
  game.py           → main loop, scoring, visuals
  main.py           → CLI entry point
```

---

## 8. Next things you can try

- Change BPM and bar count to practice at different speeds.
- Edit pad positions / radii in `src/airdrum/drum_kit.py` if the layout doesn’t fit your camera angle.
- Add real song charts later (JSON format is already supported in `beatmap.py`).

Enjoy practicing!
