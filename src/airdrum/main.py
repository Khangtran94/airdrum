import argparse

from .game import run, run_practice


def main():
    parser = argparse.ArgumentParser(description="Air Drum - MediaPipe hand-tracking rhythm game")
    parser.add_argument("--camera", type=int, default=0,
                         help="Camera device index. Run `python -m airdrum.camera` to list options "
                              "if you're not sure which index iVCam registered as.")
    parser.add_argument("--bpm", type=float, default=100.0, help="Beats per minute for the demo beatmap")
    parser.add_argument("--bars", type=int, default=64, help="Number of notes in the demo beatmap")
    parser.add_argument("--no-skeleton", action="store_true", help="Hide the hand skeleton overlay")
    parser.add_argument("--practice", action="store_true",
                         help="Practice mode: no beatmap/scoring, just touch a ring to hear its sound")
    args = parser.parse_args()

    if args.practice:
        run_practice(camera_index=args.camera, show_skeleton=not args.no_skeleton)
    else:
        run(camera_index=args.camera, bpm=args.bpm, bars=args.bars, show_skeleton=not args.no_skeleton)


if __name__ == "__main__":
    main()
