"""Procedural drum sound synthesis + playback via pygame.mixer.

No audio files needed - each hit sound is generated as a numpy waveform.
"""
from __future__ import annotations

import numpy as np
import pygame

SAMPLE_RATE = 44100


def _to_pygame_sound(wave: np.ndarray) -> pygame.mixer.Sound:
    wave = np.clip(wave, -1.0, 1.0)
    stereo = np.column_stack([wave, wave])
    int_wave = (stereo * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(int_wave))


def _kick(duration: float = 0.28) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(160, 38, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.exp(-t * 14)
    # louder + a bit of click for presence on small speakers
    click = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 60) * 0.35
    return (np.sin(phase) * envelope + click) * 1.4


def _snare(duration: float = 0.22) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 20)
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 25) * 0.4
    return (noise * envelope + body) * 0.95


def _hihat(duration: float = 0.09) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 42)
    return noise * envelope * 0.7


def _tom(freq_start: float, freq_end: float, decay: float, duration: float,
         gain: float = 1.3) -> np.ndarray:
    """Parametrized tom - lower freq = deeper drum."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(freq_start, freq_end, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.exp(-t * decay)
    # small attack transient so it cuts through on laptop speakers
    attack = np.exp(-t * 80) * 0.4
    return (np.sin(phase) * envelope + attack * np.sin(2 * np.pi * freq_start * t)) * gain


def _crash(duration: float = 0.65) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 3.8)
    return noise * envelope * 0.55


def _ride(duration: float = 0.85) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    noise_env = np.exp(-t * 2.8)
    ping = np.sin(2 * np.pi * 780 * t) * np.exp(-t * 2.0)
    return (noise * noise_env * 0.4 + ping * 0.35)


class AudioEngine:
    def __init__(self):
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=2)
        pygame.mixer.init()
        self._sounds = {
            "kick": _to_pygame_sound(_kick()),
            "snare": _to_pygame_sound(_snare()),
            "hihat": _to_pygame_sound(_hihat()),
            "tom1": _to_pygame_sound(_tom(freq_start=300, freq_end=140, decay=14, duration=0.25, gain=1.45)),
            "tom2": _to_pygame_sound(_tom(freq_start=220, freq_end=95, decay=12, duration=0.28, gain=1.4)),
            "floor_tom": _to_pygame_sound(_tom(freq_start=145, freq_end=50, decay=8, duration=0.4, gain=1.5)),
            "crash": _to_pygame_sound(_crash()),
            "ride": _to_pygame_sound(_ride()),
        }

    def play(self, name: str):
        sound = self._sounds.get(name)
        if sound:
            sound.play()
        else:
            print(f"[audio] WARNING: no sound registered for '{name}'")
