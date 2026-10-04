"""Jungle/DnB bed from real CC0 samples (Sonic Pi sample pack, github.com/alex-esc/sample-pi).

174 BPM: amen break (re-pitched like classic jungle) + two-step kick reinforcement, reese/sub bass
line, dark pad; impacts and reverse-cymbal risers on cue points. No synthetic drums.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt, resample_poly

SR = 44100
BPM = 174
BEAT = 60 / BPM
BAR = 4 * BEAT
SPI = Path("/tmp/spi")
LOCAL = Path(__file__).parent / "samples"  # copies of the used CC0 samples


def load(rel, rate_ratio=1.0):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(LOCAL / Path(rel).name if (LOCAL / Path(rel).name).exists() else SPI / rel), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    if rate_ratio != 1.0:  # speed+pitch change (tape style)
        up, down = 1000, int(round(1000 * rate_ratio))
        x = resample_poly(x, up, down)
    return x / (np.abs(x).max() + 1e-9)


def pitch(x, semis):
    return load_ratio(x, 2 ** (semis / 12))


def load_ratio(x, r):
    up, down = 1000, int(round(1000 * r))
    return resample_poly(x, up, down)


def place(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * g


def lp(x, f, o=2):
    return sosfilt(butter(o, f, "lp", fs=SR, output="sos"), x)


def hp(x, f, o=2):
    return sosfilt(butter(o, f, "hp", fs=SR, output="sos"), x)


def make_music(total, cues, drop_from=None):
    """cues: times (s) of section hits; drop_from: time after which drums stop (outro)."""
    n = int((total + 1) * SR)
    drums = np.zeros(n)
    bass = np.zeros(n)
    pad = np.zeros(n)
    fx = np.zeros(n)

    amen_src = load("drums/loops/loop_amen_full.flac")
    src_bpm = 16 / (len(amen_src) / SR)
    amen = load_ratio(amen_src, BPM / src_bpm)  # 4 bars at 174
    amen_len = len(amen) / SR
    slices = np.array_split(amen, 32)  # 8th-note slices for fills
    kick = load("drums/one-shots/kick/drum_heavy_kick.flac")
    snare = load("drums/one-shots/snare/drum_snare_hard.flac")
    boom = load("misc/misc_cineboom.flac")
    splash = load("drums/one-shots/other/drum_splash_hard.flac")
    rev = splash[::-1][-int(0.9 * SR):]
    reese = load("bass/bass_voxy_c.flac")
    drone = load("ambient/ambi_drone.flac")

    t0 = BAR  # drums enter on bar 2 (after the splash hit)
    end_drums = drop_from if drop_from else total
    t = t0
    k = 0
    while t < end_drums:
        if k % 2 == 1:  # every 2nd loop: chopped variation in the last bar (fill)
            v = np.concatenate(slices[:24] + [slices[i] for i in (24, 24, 26, 27, 30, 30, 31, 31)])
        else:
            v = amen
        seg = v[: int(min(len(v), (end_drums - t) * SR))]
        fade = min(len(seg), int(0.01 * SR))
        seg = seg.copy()
        seg[-fade:] *= np.linspace(1, 0, fade)
        place(drums, seg, t, 0.9)
        # two-step kick reinforcement + snare layer on 2 & 4
        for b in range(int(amen_len / BAR)):
            bt = t + b * BAR
            if bt >= end_drums:
                break
            place(drums, kick, bt, 0.7)
            place(drums, kick, bt + 2.5 * BEAT, 0.55)
            place(drums, snare, bt + BEAT, 0.35)
            place(drums, snare, bt + 3 * BEAT, 0.35)
        t += amen_len
        k += 1

    # bass: F, F, Db, Eb (2 bars each) — reese (bass_voxy is in C) + sine sub
    prog = [5, 5, 1, 3]  # semitones above C
    t = t0
    i = 0
    while t < total - 0.5:
        semi = prog[(i // 2) % 4] - 12
        r = pitch(reese, semi)[: int(2 * BAR * SR)]
        env = np.ones(len(r))
        a = int(0.01 * SR)
        env[:a] = np.linspace(0, 1, a)
        env[-int(0.08 * SR):] = np.linspace(1, 0, int(0.08 * SR))
        if t >= end_drums:
            env *= 0.6
        place(bass, lp(r * env, 900), t, 0.45)
        f0 = 65.41 * 2 ** ((prog[(i // 2) % 4] - 12) / 12)  # C2 * ...
        tt = np.arange(int(2 * BAR * SR)) / SR
        sub = np.sin(2 * np.pi * f0 * tt) * env[: len(tt)] if len(env) >= len(tt) else np.sin(2 * np.pi * f0 * tt)
        place(bass, sub, t, 0.5)
        t += 2 * BAR
        i += 2

    # dark pad (looped drone, crossfaded) under everything
    d = lp(pitch(drone, -5), 2500)
    L = len(d)
    xf = int(0.5 * SR)
    t = 0.0
    while t < total:
        seg = d.copy()
        seg[:xf] *= np.linspace(0, 1, xf)
        seg[-xf:] *= np.linspace(1, 0, xf)
        place(pad, seg, t, 0.35)
        t += (L - xf) / SR

    # impacts on cues, risers before them
    for c in cues:
        place(fx, boom, max(0, c - 0.02), 0.9)
        place(fx, splash, c, 0.35)
        if c > 1.0:
            place(fx, rev, c - len(rev) / SR, 0.35)

    drums = hp(drums, 40)
    mix = drums + bass + pad + fx
    mix = hp(mix, 30)
    mix /= np.percentile(np.abs(mix), 99.9) + 1e-9
    mix = np.tanh(mix * 1.0) * 0.9
    return mix[: int(total * SR)]
