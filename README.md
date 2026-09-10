# Air Drum

An air-drumming rhythm game for learning and practicing drums.
MediaPipe tracks your hands over a webcam (or iPhone/iPad via iVCam).
You strike downward toward on-screen drum pads in time with falling notes —
inspired by SongArc and Magic Tiles, but built around a real drum-kit layout.

## Status: v1.1

- Index fingertip used as the stick tip (no physical stick required yet).
- 8-piece kit from the **drummer’s point of view** (Crash, Tom 1, Tom 2, Ride, Hi-Hat, Snare, Floor Tom, Kick).
- Procedurally generated demo beatmap + practice mode.
- Synthesized drum sounds (no audio files needed).
- Score, combo, Perfect / Great / Good / Miss feedback, hit flashes.
- Latency compensation flag for iVCam pipelines.

## Why this kit size?

A classic 5-piece (kick + snare + hi-hat + one or two toms) is too limited for real practice.
An 8-piece gives you the voices you actually need for most rock / pop / funk grooves and fills while still fitting cleanly in a camera frame. The layout mirrors a real acoustic kit as seen by the player.

## Setup

This project uses [uv](https://docs.astral.sh/uv/).

```bash
cd airdrum
uv sync
```

## Using your iPhone / iPad as the camera (iVCam)

1. Open the iVCam desktop client on your PC and the iVCam app on your phone/tablet and let them connect.
2. iVCam usually appears as a normal webcam device, but it is often **not** index 0.
   Find the correct index:

   ```bash
   uv run python -m airdrum.camera
   ```

3. Run the game with that index:

   ```bash
   uv run airdrum --camera 1
   ```

If notes feel consistently early or late because of the extra camera pipeline delay, add a small latency offset (in seconds):

```bash
uv run airdrum --camera 1 --latency 0.08
```

## Controls

- Hold your hands up in frame — a white dot marks each tracked fingertip.
- Strike **downward** through a drum ring in time with the falling note to score.
- `q` — quit.

## CLI options

```bash
uv run airdrum --camera 1 --bpm 110 --bars 100 --latency 0.06 --no-skeleton
uv run airdrum --practice --camera 1
```

| Flag            | Default | Meaning                                              |
|-----------------|---------|------------------------------------------------------|
| `--camera`      | 0       | Camera device index                                  |
| `--bpm`         | 100     | Tempo of the demo beatmap                            |
| `--bars`        | 64      | Number of notes generated                            |
| `--latency`     | 0.0     | Compensation for camera / iVCam delay (seconds)      |
| `--no-skeleton` | off     | Hide full hand skeleton, show only tip marker        |
| `--practice`    | off     | Free-play mode (touch rings to hear sounds)          |

## Project layout

```
airdrum/
  pyproject.toml
  src/airdrum/
    camera.py         # OpenCV capture wrapper (iVCam friendly)
    hand_tracker.py   # MediaPipe Hands (Tasks API) → fingertip positions
    audio_engine.py   # Procedural drum synthesis + pygame.mixer
    drum_kit.py       # 8-pad layout + hit-test + drawing
    beatmap.py        # Demo generation + JSON song loader stub
    game.py           # Main loop, scoring, visuals
    main.py           # CLI entry point
```

## Framework choice

**MediaPipe HandLandmarker** remains the best free, pure-webcam solution for this project in 2026:
- Accurate 21-landmark tracking
- Multi-hand support
- Acceptable latency on ordinary CPUs
- Already battle-tested for air instruments and gesture control

Alternatives considered (Leap Motion 2, YOLO pose variants, native iOS Vision/ARKit) either require extra hardware or force a full mobile rewrite. We stay on the current Python + OpenCV + MediaPipe stack for fast iteration while testing with iPhone/iPad via iVCam.

## Known rough edges / next steps

- **Strike threshold tuning**: `STRIKE_VELOCITY` in `game.py` is still a fixed constant. A short calibration step (tap along to a metronome) would make it more reliable across different users and camera angles.
- **Real drumstick tracking**: currently uses the index fingertip. Adding HSV color-blob detection for a bright tip (tape/marker) and fusing it with the hand position is a natural upgrade.
- **Real songs**: `beatmap.load_beatmap_from_json` is ready. Wire a `--song path.json` flag and start authoring charts.
- **More practice modes**: metronome, call-and-response patterns, difficulty tiers.
- **Visual polish**: particle bursts, better pad art, song-selection screen.

## License

MIT (or whatever you prefer — currently unlicensed).
