#!/usr/bin/env python3
"""audio_fx.py — studio-grade voice + music processing (pedalboard by Spotify, librosa, pyloudnorm).

voice_chain(x)        TTS/voice -> broadcast voice: HPF 80 · de-mud −3 dB @300 · presence +3 dB @3.5k ·
                      gated word-level leveler (kills whisper/shout jumps) · 2-stage compression ·
                      de-ess · limiter.                       -> consistent, "radio" voice
beat_grid(music)      librosa beat/downbeat tracking -> list of beat times (cut on the beat)
snap(t, beats)        snap a cut time to the nearest beat
duck(music, voice)    smooth sidechain (no pumping): depth dB, attack/release ms
master(mix)           -14 LUFS integrated, -1 dBTP limiter (YouTube / Reels / Shorts / VK)
sfx(name)             CC0 SFX from toolkit/sfx (whoosh_transition, impact_deep, riser_tension, ...)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d, maximum_filter1d

SR = 44100
SFX = Path(__file__).parent / "sfx"


def load(path, sr=SR, mono=True, tempo=1.0):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1" if mono else "2", "-ar", str(sr)]
    if tempo != 1.0:
        cmd += ["-af", f"atempo={tempo}"]
    raw = subprocess.run(cmd + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).copy()
    return x if mono else x.reshape(-1, 2).T


def save(path, x, sr=SR):
    x = np.asarray(x, np.float32)
    ch = 1 if x.ndim == 1 else x.shape[0]
    data = x if x.ndim == 1 else x.T.reshape(-1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
                    str(path)], input=data.tobytes(), check=True)


def sfx(name):
    return load(SFX / f"{name}.mp3")


# ------------------------------------------------------------------ voice
def level_words(x, target_db=-18.0, max_boost=16.0, max_cut=12.0, gate_rel=34.0, sr=SR):
    """Gated AGC: evens out word-to-word loudness without pumping pauses/breaths.
    Gate is RELATIVE to the clip's loud speech (whispered words are still lifted)."""
    x = x.astype(np.float64)
    x = x / (np.percentile(np.abs(x), 99.9) + 1e-9) * 0.5
    rms = np.sqrt(uniform_filter1d(x ** 2, int(0.05 * sr)) + 1e-12)
    rms = maximum_filter1d(rms, int(0.04 * sr))
    env = 20 * np.log10(rms)
    loud = np.percentile(env, 95)
    g = np.clip(target_db - env, -max_cut, max_boost)
    gate = env < loud - gate_rel
    g[gate] = np.minimum(g[gate], 0.0)
    out = np.empty_like(g)
    aa, ar = np.exp(-1 / (0.015 * sr)), np.exp(-1 / (0.12 * sr))
    p = 0.0
    for i in range(0, len(g), 32):  # block-wise one-pole (fast)
        v = g[i]
        a = (aa if v < p else ar) ** 32
        p = v + (p - v) * a
        out[i:i + 32] = p
    return (x * 10 ** (out / 20)).astype(np.float32)


def voice_chain(x, sr=SR, presence=3.0, warmth=1.5):
    from pedalboard import (Pedalboard, HighpassFilter, PeakFilter, LowShelfFilter, HighShelfFilter,
                            Compressor, Gain)
    x = level_words(x, sr=sr)
    board = Pedalboard([
        HighpassFilter(80),
        LowShelfFilter(cutoff_frequency_hz=140, gain_db=warmth, q=0.7),     # body
        PeakFilter(300, -3.0, 1.0),                                           # de-mud
        PeakFilter(3500, presence, 0.9),                                      # presence / intelligibility
        HighShelfFilter(cutoff_frequency_hz=10000, gain_db=1.5, q=0.7),      # air
        Compressor(threshold_db=-20, ratio=3.0, attack_ms=8, release_ms=90),
        Compressor(threshold_db=-10, ratio=6.0, attack_ms=2, release_ms=50),
        Gain(4.0),
    ])
    y = limit(board(x.astype(np.float32)[None, :], sr)[0], -1.5, sr=sr)
    # simple de-esser: compress 5–9 kHz band only when it spikes
    from scipy.signal import butter, sosfilt
    band = sosfilt(butter(2, [5000, 9000], "bandpass", fs=sr, output="sos"), y)
    e = np.sqrt(uniform_filter1d(band ** 2, int(0.005 * sr)) + 1e-12)
    thr = np.percentile(e, 97)
    red = np.clip(thr / np.maximum(e, 1e-9), 0.35, 1.0)
    y = y - band * (1 - red)
    return y.astype(np.float32)


def squeeze_pauses(x, max_pause=0.24, thr_db=-40, sr=SR):
    w = int(0.02 * sr)
    n = len(x) // w
    e = 20 * np.log10(np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, 1)) + 1e-9)
    q = e < thr_db
    out, i = [], 0
    while i < n:
        j = i
        while j < n and q[j] == q[i]:
            j += 1
        c = x[i * w: j * w]
        if q[i] and 0 < i and j < n and (j - i) * w > max_pause * sr:
            k = int(max_pause * sr)
            c = np.concatenate([c[: k // 2], c[-k // 2:]])
        out.append(c)
        i = j
    return np.concatenate(out + [x[n * w:]])


# ------------------------------------------------------------------ music
def beat_grid(music, sr=SR, bpm_hint=None):
    """Beat times. bpm_hint (e.g. 174 for DnB) fixes the classic half/double-tempo error."""
    import librosa
    kw = {"start_bpm": bpm_hint} if bpm_hint else {}
    tempo, beats = librosa.beat.beat_track(y=music.astype(np.float32), sr=sr, units="time", **kw)
    tempo = float(np.atleast_1d(tempo)[0])
    beats = np.asarray(beats)
    if bpm_hint and tempo < bpm_hint * 0.7 and len(beats) > 1:  # half-time detected -> insert off-beats
        mids = (beats[:-1] + beats[1:]) / 2
        beats = np.sort(np.concatenate([beats, mids]))
        tempo *= 2
    return tempo, beats


def snap(t, beats, max_shift=0.25):
    if len(beats) == 0:
        return t
    b = beats[np.argmin(np.abs(beats - t))]
    return b if abs(b - t) <= max_shift else t


def duck(music, voice, depth_db=5.0, attack=0.25, release=0.7, sr=SR):
    n = min(len(music), len(voice))
    act = (uniform_filter1d(np.abs(voice[:n]), int(0.2 * sr)) > 0.01).astype(float)
    g = np.empty(n)
    p, aa, ar = 0.0, np.exp(-1 / (attack * sr)), np.exp(-1 / (release * sr))
    for i in range(0, n, 64):
        v = act[i]
        c = (aa if v > p else ar) ** 64
        p = v + (p - v) * c
        g[i:i + 64] = p
    return music[:n] * 10 ** (-depth_db * g / 20)


def carve(music, sr=SR, amount=0.5):
    """Static EQ pocket for the voice (700–4000 Hz) — clarity without pumping."""
    from scipy.signal import butter, sosfilt
    return music - amount * sosfilt(butter(2, [700, 4000], "bandpass", fs=sr, output="sos"), music)


def limit(x, ceiling_db=-1.0, lookahead=0.005, release=0.08, sr=SR):
    """Transparent look-ahead peak limiter (numpy). Works on (n,) or (ch, n). No make-up gain."""
    x = np.asarray(x, np.float32)
    st = x if x.ndim == 2 else x[None]
    c = 10 ** (ceiling_db / 20)
    peak = np.abs(st).max(0)
    la = max(1, int(lookahead * sr))
    need = np.minimum(1.0, c / np.maximum(maximum_filter1d(peak, 2 * la + 1), 1e-9))
    g = np.empty_like(need)
    p, ar = 1.0, np.exp(-1 / (release * sr))
    blk = 16
    for i in range(0, len(need), blk):
        v = need[i:i + blk].min()
        p = v if v < p else v + (p - v) * ar ** blk
        g[i:i + blk] = p
    g = uniform_filter1d(g, la)            # smooth attack ramp across the look-ahead window
    g = np.minimum(g, need)                # guarantee
    out = np.clip(st * g, -c, c)
    return out if x.ndim == 2 else out[0]


def lufs(x, sr=SR):
    import pyloudnorm as pyln
    x = np.asarray(x, np.float64)
    if x.ndim == 2 and x.shape[0] < x.shape[1]:   # (ch, n) -> (n, ch)
        x = x.T
    return pyln.Meter(sr).integrated_loudness(x)


def gain_to(x, target, sr=SR):
    return x * 10 ** ((target - lufs(x, sr)) / 20)


def master(mix, target=-14.0, ceiling_db=-1.0, sr=SR):
    """Gain to target LUFS, then look-ahead limit; re-check (limiting lowers loudness slightly)."""
    y = np.asarray(mix, np.float32)
    for _ in range(3):
        y = limit(gain_to(y, target, sr).astype(np.float32), ceiling_db, sr=sr)
    return y
