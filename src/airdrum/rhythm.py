"""Device-independent timing and scoring, using one monotonic clock."""
from dataclasses import dataclass, field
from .beatmap import Note

HIT_WINDOW = 0.20

@dataclass
class Session:
    notes: list[Note]
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    misses: int = 0
    extra_hits: int = 0
    errors: list[float] = field(default_factory=list)

    def expire(self, now: float):
        for note in self.notes:
            if not note.hit and not note.missed and now - note.time > HIT_WINDOW:
                note.missed = True
                self.misses += 1
                self.combo = 0

    def strike(self, pad: str, now: float) -> tuple[str, float | None]:
        self.expire(now)
        candidates = [n for n in self.notes if n.pad == pad and not n.hit
                      and not n.missed and abs(now - n.time) <= HIT_WINDOW]
        if not candidates:
            self.combo = 0
            self.extra_hits += 1
            return "EXTRA", None
        note = min(candidates, key=lambda n: abs(now - n.time))
        note.hit = True
        error = now - note.time
        self.errors.append(error)
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        label, points = ("PERFECT", 100) if abs(error) < .07 else (("GREAT", 70) if abs(error) < .13 else ("GOOD", 40))
        self.score += points
        return label, error

    @property
    def accuracy(self):
        """Coverage penalized by extra strikes; unfinished notes remain in denominator."""
        return 100 * len(self.errors) / max(1, len(self.notes) + self.extra_hits)

    @property
    def finished(self):
        return all(n.hit or n.missed for n in self.notes)
