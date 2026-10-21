import argparse

from .game import run, run_practice


def main():
    parser = argparse.ArgumentParser(
        description="Air Drum — MediaPipe hand-tracking rhythm game for learning drums"
    )
    parser.add_argument(
        "--camera", type=int, default=0,
        help="Camera device index. Run `python -m airdrum.camera` to list options."
    )
    parser.add_argument(
        "--bpm", type=float, default=100.0,
        help="Beats per minute for the demo beatmap"
    )
    parser.add_argument(
        "--bars", type=int, default=8,
        help="Number of complete 4/4 bars"
    )
    parser.add_argument(
        "--no-skeleton", action="store_true",
        help="Hide the full hand-skeleton overlay (show only the tip marker)"
    )
    parser.add_argument(
        "--practice", action="store_true",
        help="Practice mode: no beatmap/scoring — just touch a ring to hear its sound"
    )
    parser.add_argument(
        "--latency", type=float, default=0.0,
        help="Latency compensation in seconds (e.g. 0.08 for ~80 ms iVCam delay). "
             "Positive values subtract camera delay from strike timestamps."
    )
    parser.add_argument(
        "--no-mirror", action="store_true",
        help="Disable horizontal flip. Use this with iVCam when the image already "
             "looks correct in the iVCam window (right hand moves right)."
    )
    parser.add_argument("--lesson", choices=["pulse", "backbeat", "rock", "fill"], default="pulse")
    parser.add_argument("--song", help="Path to a JSON beatmap")
    parser.add_argument("--keyboard", action="store_true", help="Play without camera or hand model")
    parser.add_argument("--listen", action="store_true", help="Listen to an unscored demonstration")
    parser.add_argument("--no-metronome", action="store_true")
    args = parser.parse_args()
    import math
    if not math.isfinite(args.bpm) or not 30 <= args.bpm <= 240 or args.bars < 1:
        parser.error("BPM must be 30..240 and bars must be positive")
    if not math.isfinite(args.latency) or not 0 <= args.latency <= .5:
        parser.error("latency must be between 0 and 0.5 seconds")
    if args.practice and (args.keyboard or args.listen or args.song):
        parser.error("--practice is camera free-play; omit it for keyboard/listen/song")

    mirror = not args.no_mirror

    if args.practice:
        run_practice(
            camera_index=args.camera,
            show_skeleton=not args.no_skeleton,
            mirror=mirror,
        )
    else:
        run(
            camera_index=args.camera,
            bpm=args.bpm,
            bars=args.bars,
            show_skeleton=not args.no_skeleton,
            latency=args.latency,
            lesson=args.lesson, song=args.song, keyboard=args.keyboard,
            listen=args.listen, metronome=not args.no_metronome,
            mirror=mirror,
        )


if __name__ == "__main__":
    main()
