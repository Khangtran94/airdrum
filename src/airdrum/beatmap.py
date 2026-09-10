"""Beatmap generation and (future) loading.

v1: procedurally generates a simple metronome-based pattern from a BPM.
Later: replace `build_demo_beatmap` with `load_beatmap_from_json(path)` so
you can author real songs as {"bpm": 100, "notes": [{"beat": 0, "pad": "kick"}, ...]}.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json


@dataclass
class Note:
    time: float          # absolute time (seconds, since song start) the note should be hit
    pad: str
    hit: bool = False
    missed: bool = False


DEFAULT_PATTERN = ["kick", "hihat", "snare", "hihat", "kick", "hihat", "snare", "crash"]


def build_demo_beatmap(bpm: float, start_time: float, bars: int = 32,
                        pattern: list[str] | None = None) -> list[Note]:
    pattern = pattern or DEFAULT_PATTERN
    beat_sec = 60.0 / bpm
    notes = []
    for i in range(bars):
        notes.append(Note(time=start_time + i * beat_sec, pad=pattern[i % len(pattern)]))
    return notes


def load_beatmap_from_json(path: str, start_time: float) -> tuple[float, list[Note]]:
    """Load a song file of the form:
    {
      "bpm": 100,
      "notes": [{"beat": 0, "pad": "kick"}, {"beat": 1, "pad": "hihat"}, ...]
    }
    `beat` is in units of quarter-notes from the start of the song.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bpm = data["bpm"]
    beat_sec = 60.0 / bpm
    notes = [
        Note(time=start_time + n["beat"] * beat_sec, pad=n["pad"])
        for n in data["notes"]
    ]
    return bpm, notes
