"""Procedural drum sound synthesis + playback via pygame.mixer.

No audio files needed - each hit sound is generated as a numpy waveform,
matching the approach used in the browser prototype's Web Audio synthesis.
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


def _kick(duration: float = 0.2) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(150, 40, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.exp(-t * 18)
    return np.sin(phase) * envelope


def _snare(duration: float = 0.2) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 22)
    return noise * envelope


def _hihat(duration: float = 0.08) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 45)
    return noise * envelope * 0.6


def _tom(freq_start: float, freq_end: float, decay: float, duration: float) -> np.ndarray:
    """Parametrized tom - lower freq_start/freq_end and slower decay = deeper drum."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(freq_start, freq_end, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.exp(-t * decay)
    return np.sin(phase) * envelope


def _crash(duration: float = 0.6) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    envelope = np.exp(-t * 4)
    return noise * envelope * 0.5


def _ride(duration: float = 0.8) -> np.ndarray:
    """Ride: brighter, more sustained shimmer than crash, with a subtle
    tonal 'ping' overlay (crash is pure noise; a ride has more definite pitch)."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, t.size)
    noise_env = np.exp(-t * 3)
    ping = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 2.2)
    return noise * noise_env * 0.35 + ping * 0.3


class AudioEngine:
    def __init__(self):
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=2)
        pygame.mixer.init()
        self._sounds = {
            "kick": _to_pygame_sound(_kick()),
            "snare": _to_pygame_sound(_snare()),
            "hihat": _to_pygame_sound(_hihat()),
            "tom1": _to_pygame_sound(_tom(freq_start=280, freq_end=150, decay=15, duration=0.22)),
            "tom2": _to_pygame_sound(_tom(freq_start=200, freq_end=100, decay=13, duration=0.25)),
            "floor_tom": _to_pygame_sound(_tom(freq_start=130, freq_end=55, decay=9, duration=0.35)),
            "crash": _to_pygame_sound(_crash()),
            "ride": _to_pygame_sound(_ride()),
        }

    def play(self, name: str):
        sound = self._sounds.get(name)
        if sound:
            sound.play()
