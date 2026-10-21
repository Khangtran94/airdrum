import json
import tempfile
import unittest
from pathlib import Path
from airdrum.beatmap import Note, build_lesson, build_demo_beatmap, load_beatmap_from_json
from airdrum.rhythm import Session

class RhythmTests(unittest.TestCase):
    def test_misses_expire_once_even_after_frame_stall(self):
        s = Session([Note(1, 'snare'), Note(2, 'kick')])
        s.expire(10); s.expire(11)
        self.assertEqual(s.misses, 2)
        self.assertTrue(s.finished)
        self.assertEqual(s.accuracy, 0)
        self.assertEqual(s.strike('snare', 1)[0], 'EXTRA')

    def test_chord_and_duplicate(self):
        s = Session([Note(1, 'snare'), Note(1, 'hihat')])
        self.assertEqual(s.strike('snare', 1)[0], 'PERFECT')
        s.strike('hihat', 1.08)
        self.assertEqual(s.max_combo, 2)
        self.assertEqual(s.score, 170)
        self.assertEqual(s.accuracy, 100)
        s.strike('snare', 1.09)
        self.assertEqual(s.extra_hits, 1)
        self.assertAlmostEqual(s.accuracy, 200 / 3)

    def test_nearest_and_timing_sign(self):
        s = Session([Note(1, 'snare'), Note(1.2, 'snare')])
        _, error = s.strike('snare', 1.15)
        self.assertAlmostEqual(error, -.05)
        self.assertTrue(s.notes[1].hit)

    def test_lesson_measures_and_chords(self):
        notes = build_lesson(60, 10, 2, 'rock')
        self.assertEqual(len(notes), 24)
        self.assertEqual(notes[-1].time, 17.5)
        self.assertEqual(sum(n.time == 10 for n in notes), 2)
        self.assertEqual(len(build_demo_beatmap(60, 0, 2)), 8)

    def test_invalid_tempo(self):
        for bpm in (0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                build_lesson(bpm, 0)

    def test_chart_validation_and_sort(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'chart.json'
            p.write_text(json.dumps({'bpm': 120, 'notes': [{'beat': 2, 'pad': 'snare'}, {'beat': 0, 'pad': 'kick'}]}))
            bpm, notes = load_beatmap_from_json(p, 10)
            self.assertEqual([n.time for n in notes], [10, 11])
            for beat, pad in [(-1, 'kick'), (0, 'unknown')]:
                p.write_text(json.dumps({'bpm': 120, 'notes': [{'beat': beat, 'pad': pad}]}))
                with self.assertRaises(ValueError):
                    load_beatmap_from_json(p, 0)

if __name__ == '__main__':
    unittest.main()
