"""Quarter-note based charts and progressive four-beat drum lessons."""
from dataclasses import dataclass
import json
import math

PAD_IDS = {"kick", "snare", "hihat", "tom1", "tom2", "floor_tom", "crash", "ride"}
LESSONS = {
    "pulse": ("Quarter notes: steady hi-hat; count 1 2 3 4.", [(i, "hihat") for i in range(4)]),
    "backbeat": ("Backbeat: kick on 1/3, snare on 2/4.", [(0, "kick"), (1, "snare"), (2, "kick"), (3, "snare")]),
    "rock": ("Rock groove: eighth-note hi-hat + kick 1/3 + snare 2/4.", [(i / 2, "hihat") for i in range(8)] + [(0, "kick"), (1, "snare"), (2, "kick"), (3, "snare")]),
    "fill": ("Simple fill: snare, high tom, low tom, floor tom.", [(0, "snare"), (1, "tom1"), (2, "tom2"), (3, "floor_tom")]),
}

@dataclass
class Note:
    time: float  # timestamp on the game's monotonic clock
    pad: str
    hit: bool = False
    missed: bool = False

DEFAULT_PATTERN = ["kick", "hihat", "snare", "hihat", "kick", "hihat", "snare", "crash"]

def validate_tempo(bpm):
    if isinstance(bpm, bool) or not isinstance(bpm, (float, int)) or not math.isfinite(bpm) or not 30 <= bpm <= 240:
        raise ValueError("BPM must be a finite number between 30 and 240")

def build_demo_beatmap(bpm, start_time, bars=8, pattern=None):
    """Compatibility demo: bars now means complete 4/4 measures."""
    validate_tempo(bpm)
    if bars < 1:
        raise ValueError("bars must be positive")
    pattern = DEFAULT_PATTERN if pattern is None else pattern
    if not pattern or any(p not in PAD_IDS for p in pattern):
        raise ValueError("pattern must contain known pads")
    return [Note(start_time + i * 60 / bpm, pattern[i % len(pattern)]) for i in range(bars * 4)]

def build_lesson(bpm, start_time, bars=8, lesson="pulse"):
    validate_tempo(bpm)
    if bars < 1:
        raise ValueError("bars must be positive")
    pattern = LESSONS[lesson][1]
    return sorted([Note(start_time + (bar * 4 + beat) * 60 / bpm, pad)
                   for bar in range(bars) for beat, pad in pattern], key=lambda n: n.time)

def load_beatmap_from_json(path, start_time):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    bpm = data["bpm"]
    validate_tempo(bpm)
    notes = []
    for n in data["notes"]:
        beat = n["beat"]
        if isinstance(beat, bool) or not isinstance(beat, (int, float)) or not math.isfinite(beat) or beat < 0 or n["pad"] not in PAD_IDS:
            raise ValueError("Each note needs a nonnegative finite beat and a known pad")
        notes.append(Note(start_time + beat * 60 / bpm, n["pad"]))
    if not notes:
        raise ValueError("Chart must contain notes")
    return bpm, sorted(notes, key=lambda n: n.time)
