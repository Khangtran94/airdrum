# Air Drum

An air-drumming rhythm game: MediaPipe tracks your hands over webcam (or iVCam),
you strike downward toward on-screen drum rings in time with falling notes,
Songarc/Beat-Saber style.

## Status: v1 prototype
- Uses your index fingertip as the "stick tip" (no physical stick needed yet).
- One procedurally generated demo beatmap (simple 8-step kick/hihat/snare/crash pattern).
- Drum sounds are synthesized on the fly (no audio files).
- Score, combo tracked; no persistent leaderboard yet.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) (same as your Air Fruit Ninja project).

```bash
cd airdrum
uv sync
```

## Using your iPhone as the camera (iVCam)

1. Open the iVCam desktop client on your PC and the iVCam app on your iPhone, and let them connect.
2. iVCam registers itself as a normal webcam device — but it's usually **not** index 0
   if you also have a built-in laptop webcam. Find the right index:
   ```bash
   uv run python -m airdrum.camera
   ```
   This prints which indices actually open. Try the iVCam one (often index 1 or 2).
3. Run the game with that index:
   ```bash
   uv run airdrum --camera 1
   ```

## Controls

- Hold your hands up in frame — a white dot marks each tracked fingertip.
- Strike downward through a drum ring in time with the falling note to score.
- `q` — quit.

## CLI options

```bash
uv run airdrum --camera 1 --bpm 110 --bars 100 --no-skeleton
```

| Flag | Default | Meaning |
|---|---|---|
| `--camera` | 0 | Camera device index |
| `--bpm` | 100 | Tempo of the demo beatmap |
| `--bars` | 64 | Number of notes generated |
| `--no-skeleton` | off | Hide the full hand-skeleton overlay, show only the tip dot |

## Project layout

```
airdrum/
  pyproject.toml
  src/airdrum/
    camera.py        # OpenCV capture wrapper, works with iVCam
    hand_tracker.py   # MediaPipe Hands wrapper -> fingertip positions
    audio_engine.py   # Procedural drum sound synthesis + playback (pygame.mixer)
    drum_kit.py       # Pad layout (position, radius, color) + hit-test
    beatmap.py        # Beatmap generation / (future) JSON song loading
    game.py           # Main loop: capture -> track -> detect strikes -> render
    main.py           # CLI entry point
```

## Known rough edges / next steps

- **Strike threshold tuning**: `STRIKE_VELOCITY` in `game.py` is a fixed constant.
  If hits feel unresponsive or trigger too easily, that's the first thing to tune —
  ideally exposed as a calibration step (tap along to a metronome, auto-fit the threshold).
- **No latency compensation**: iVCam adds extra pipeline latency (phone camera -> WiFi/USB ->
  iVCam driver -> OpenCV) on top of MediaPipe inference. If notes feel consistently early/late,
  add a fixed offset to `HIT_WINDOW` comparisons based on a calibration measurement.
- **Real drumstick tracking**: currently uses your index fingertip. To track an actual stick,
  add HSV color-blob detection for a bright tip (tape/marker) as a second signal, and fuse it
  with the hand position to know roughly where to search.
- **Real songs**: `beatmap.load_beatmap_from_json` is stubbed in for loading a
  `{"bpm": ..., "notes": [{"beat": 0, "pad": "kick"}, ...]}` file — wire this into `main.py`
  with a `--song path.json` flag once you want to author real charts.
- **Song selection UI**: still just launches straight into the demo beatmap; a menu screen is a
  natural next step once you have more than one song file.
