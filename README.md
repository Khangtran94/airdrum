# Air Drum — rhythm lessons

A local Python drum-learning game with webcam/iVCam hand tracking, synthesized
sounds, falling notes, and keyboard input. Start slowly, listen to a pattern,
then repeat it with a metronome.

## Run

```bash
uv sync
# Listen first (no camera/model required)
uv run airdrum --keyboard --lesson backbeat --bpm 60 --bars 4 --listen
# Play the same lesson
uv run airdrum --keyboard --lesson backbeat --bpm 60 --bars 4
# Use webcam or iVCam
uv run airdrum --camera 1 --lesson backbeat --bpm 60 --bars 4 --latency 0.08
# Unscored camera free-play
uv run airdrum --practice --camera 1
```

Focus the game window for keyboard input. `q` exits. Each scored lesson ends
automatically after the final note. There is a four-beat count-in.

| Lesson | What to learn |
|---|---|
| `pulse` (default) | Steady quarter-note hi-hat; count 1 2 3 4 |
| `backbeat` | Kick on 1/3, snare on 2/4 |
| `rock` | Eighth-note hi-hat plus kick/snare; includes simultaneous notes |
| `fill` | Snare → high tom → low tom → floor tom |

Try 4–8 bars at 60 BPM, use `--listen`, then play. Increase BPM gradually when
you can repeat accurately. `--bars` now means **complete four-beat measures**;
older versions treated it as a note count. Default: 8 bars, 100 BPM.

| Key | Pad |
|---|---|
| A | Hi-hat |
| S | Snare |
| D | Kick |
| F | Crash |
| J / K | High / low tom |
| L | Floor tom |
| Space | Ride |

Keyboard works in camera mode too, so D can stand in for a kick pedal.
OpenCV keyboard events are a basic fallback: they do not reliably capture
simultaneous key chords. Use sequential lessons first; the rock lesson is best
with two tracked hands plus the kick key. Keyboard auto-repeat can count as extra
hits; tap and release.

## Timing and feedback

- PERFECT <70 ms, GREAT <130 ms, GOOD ≤200 ms from the target.
- Missed notes expire once, even if frames stall, and reset combo.
- Extra hits reset combo and reduce accuracy.
- Accuracy = hit notes / (all chart notes + extra hits). During a lesson this
  grows as you complete the chart; quitting early leaves unfinished notes in it.
- Final report shows score, max combo, misses, extras, and mean timing error:
  negative = early, positive = late. It is coverage accuracy, not timing precision.
- Positive `--latency` subtracts camera input delay from observed strike time;
  it does not shift the music. Start with 0, then try 0.05–0.12 for iVCam.
- `--no-metronome` mutes clicks. `--no-skeleton` hides landmarks.
  `--no-mirror` disables the selfie flip.

## Camera setup

Connect iVCam desktop and phone first, preferably over USB, then scan:

```bash
uv run python -m airdrum.camera
```

Use the returned camera index. The first camera run downloads a MediaPipe hand
model (~8 MB) into `~/.cache/airdrum/`; keyboard mode does not load it.
Strike downward inside a pad ring. Use good lighting and keep both hands visible.
The detector resets velocity history after a tracking gap and uses handedness
rather than detection list order as its hand identity.

## Custom charts

```json
{"bpm": 80, "notes": [{"beat": 0, "pad": "kick"}, {"beat": 1, "pad": "snare"}]}
```

```bash
uv run airdrum --keyboard --song path/to/chart.json
```

Beats are quarter notes from the chart start; fractional beats and simultaneous
notes are supported. Charts are sorted and validated before opening the camera.
Use pad IDs `kick`, `snare`, `hihat`, `tom1`, `tom2`, `floor_tom`, `crash`, `ride`.
BPM range: 30–240. This is a synthesized chart player; it does not load backing
songs or automatically transcribe music.

## Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell: `$env:PYTHONPATH="src"` then `uv run python -m unittest discover -s tests -v`.
Tests cover missed-note accounting, chords, duplicate hits, timing, bar length,
and chart validation without camera/audio dependencies.

## Scope

This version trains rhythm, pad familiarity and basic patterns. It cannot assess
stick grip, rebound, dynamics, foot technique, or acoustic drum sound quality.
Camera detection and audio latency must be tested on your own hardware. A MIDI
pad/pedal input and a proper multi-key event loop would be useful next upgrades.
