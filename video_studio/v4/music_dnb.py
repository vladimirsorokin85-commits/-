#!/usr/bin/env python3
"""Procedural drum'n'bass / jungle soundtrack synthesizer (numpy only, 174 BPM).

Track A «neuro»  — F minor, two-step DnB, detuned reese bass with filter wobble, dark pad.
Track B «jungle» — D minor, amen-style chopped breakbeat, rolling sub, hardcore hoover stabs.

python3 music_dnb.py  ->  music_catalog/dnb_neuro_174.ogg, music_catalog/jungle_hoover_174.ogg
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
BPM = 174
BEAT = 60 / BPM
STEP = BEAT / 4          # 16th note
BAR = BEAT * 4
OUT = Path("/home/user/-/video_studio/music_catalog")
rng = np.random.default_rng(174)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype="high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def saw_from_freq(f):
    """Band-limited (polyBLEP) sawtooth for an instantaneous-frequency array."""
    dt = f / SR
    ph = np.cumsum(dt) + rng.random()
    t = ph % 1.0
    y = 2 * t - 1
    m1 = t < dt
    x = t[m1] / dt[m1]
    y[m1] -= x + x - x * x - 1
    m2 = t > 1 - dt
    x = (t[m2] - 1) / dt[m2]
    y[m2] -= x * x + x + x + 1
    return y


def adsr(n, a=0.005, d=0.1, s=0.8, r=0.05):
    e = np.full(n, s, dtype=float)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    nd2 = min(nd, max(0, n - na))
    e[na:na + nd2] = np.linspace(1, s, nd2)
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ---------------------------------------------------------------- drums
def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 48 + 140 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.16)
    click = hp(rng.standard_normal(n), 3000) * env_exp(n, 0.004) * 0.5
    x = np.tanh((body + click) * 2.4)
    return x / np.abs(x).max()


def snare(bright=1.0):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * env_exp(n, 0.06) + 0.5 * np.sin(2 * np.pi * 330 * t) * env_exp(n, 0.03)
    nz = bp(rng.standard_normal(n), 1400, 9500) * env_exp(n, 0.11 * bright)
    crack = hp(rng.standard_normal(n), 4000) * env_exp(n, 0.012)
    x = tone * 0.7 + nz * 1.0 + crack * 0.6
    room = np.convolve(x, hp(rng.standard_normal(int(0.09 * SR)), 500) * env_exp(int(0.09 * SR), 0.03) * 0.04)[:n]
    x = np.tanh((x + room) * 1.6)
    return x / np.abs(x).max()


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    x = hp(rng.standard_normal(n), 7500, 4) * env_exp(n, 0.07 if open_ else 0.014)
    return x / np.abs(x).max()


def ride():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    metal = sum(np.sin(2 * np.pi * f * t) for f in (3150, 4270, 5400, 6810)) / 4
    x = (hp(rng.standard_normal(n), 6000) * 0.6 + metal * 0.5) * env_exp(n, 0.12)
    return x / np.abs(x).max()


def crash():
    n = int(1.8 * SR)
    x = hp(rng.standard_normal(n), 3500) * env_exp(n, 0.5)
    return x / np.abs(x).max()


# ---------------------------------------------------------------- synths
def reese(midi, dur, wobble_rate, cut_lo=220, cut_hi=1500):
    n = int(dur * SR)
    f = hz(midi)
    v = sum(saw_from_freq(np.full(n, f * 2 ** (d / 1200))) for d in (-18, -6, 7, 19)) / 4
    t = np.arange(n) / SR
    dark, bright = lp(v, cut_lo, 4), lp(v, cut_hi, 2)
    lfo = 0.5 - 0.5 * np.cos(2 * np.pi * wobble_rate * t)
    x = dark * (1 - lfo) + bright * lfo
    x = np.tanh(x * 3.0) * 0.8
    sub = np.sin(2 * np.pi * (f / 2) * t) * 0.9
    return (x + sub) * adsr(n, 0.01, 0.2, 0.9, 0.04)


def hoover(midi, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = hz(midi)
    glide = f0 * 2 ** ((7 * np.exp(-t / 0.05)) / 12)  # classic downward swoop
    voices = []
    for d in (-30, -14, -4, 5, 15, 29):
        voices.append(saw_from_freq(glide * 2 ** (d / 1200)))
    voices.append(saw_from_freq(glide / 2) * 0.8)
    x = sum(voices) / 7
    x = lp(x, 3200, 2)
    x = np.tanh(x * 2.2)
    return x * adsr(n, 0.004, 0.15, 0.7, 0.06)


def pad(midis, dur):
    n = int(dur * SR)
    x = np.zeros(n)
    for m in midis:
        for d in (-9, 8):
            x += saw_from_freq(np.full(n, hz(m) * 2 ** (d / 1200)))
    x = lp(x / (2 * len(midis)), 900, 2)
    return x * adsr(n, 0.8, 0.5, 0.85, 0.8)


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    noise = rng.standard_normal(n)
    chunks = 24
    for c in range(chunks):
        a, b = c * n // chunks, (c + 1) * n // chunks
        out[a:b] = hp(noise[max(0, a - 2048):b], 300 * (25 ** (c / chunks)))[-(b - a):]
    return out / np.abs(out).max() * (t / dur) ** 2


# ---------------------------------------------------------------- arranger
def place(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m] * g


def sidechain(n, kick_times):
    g = np.ones(n)
    k = 1 - 0.65 * env_exp(int(0.2 * SR), 0.07)
    for t in kick_times:
        i = int(t * SR)
        m = min(len(k), n - i)
        if m > 0:
            g[i:i + m] = np.minimum(g[i:i + m], k[:m])
    return g


def build(style, bars=132):
    n = int(bars * BAR * SR) + SR
    drums = np.zeros(n)
    bass = np.zeros(n)
    music = np.zeros(n)
    K, S, Sg, H, Ho, R, C = kick(), snare(), snare(0.6), hat(), hat(True), ride(), crash()
    kicks = []

    def section(b):
        if b < 8:
            return "intro"
        if b < 16:
            return "build"
        if 48 <= b < 56:
            return "break"
        if b >= 128:
            return "outro"
        return "drop"

    if style == "neuro":
        root = 41  # F2
        prog = [0, 0, -4, -2, 0, 0, 3, -2]          # F F Db Eb F F Ab Eb  (per 2-bar block, cycles)
        chord = lambda r: [r + 24, r + 27, r + 31]   # minor triad
    else:
        root = 38  # D2
        prog = [0, 0, -2, -4, 0, 0, 3, 5]           # D D C Bb D D F G
        chord = lambda r: [r + 24, r + 27, r + 31]

    for b in range(bars):
        sec = section(b)
        t0 = b * BAR
        r = root + prog[(b // 2) % len(prog)]
        # ---- drums
        if sec in ("drop", "build", "outro"):
            half = sec == "build" and b < 12
            if style == "neuro":
                ks = [0, 10] if b % 2 == 0 else [0, 10, 11]
                ss = [4, 12]
                gs = [7, 15] if b % 4 == 3 else [15]
            else:
                ks = [0, 2, 10] if b % 2 == 0 else [0, 10, 13]
                ss = [4, 12]
                gs = [7, 9, 14] if b % 2 == 0 else [6, 9, 11, 15]
            if half:
                ks, ss, gs = [0], [8], []
            for s in ks:
                place(drums, K, t0 + s * STEP, 1.0)
                kicks.append(t0 + s * STEP)
            for s in ss:
                place(drums, S, t0 + s * STEP, 0.85)
            for s in gs:
                place(drums, Sg, t0 + s * STEP, 0.28 if style == "neuro" else 0.4)
            for s in range(16):
                if style == "neuro":
                    g = 0.22 if s % 2 == 0 else 0.12
                    place(drums, Ho if s in (2, 10) else H, t0 + s * STEP, g * (1.2 if s in (2, 10) else 1))
                else:
                    place(drums, H, t0 + s * STEP + (0.012 if s % 2 else 0), 0.18 if s % 2 == 0 else 0.1)
                    if s % 4 == 2:
                        place(drums, R, t0 + s * STEP, 0.12)
            # fills every 8 bars
            if b % 8 == 7 and sec == "drop":
                for k in range(8):
                    place(drums, Sg, t0 + (12 + k * 0.5) * STEP, 0.25 + 0.06 * k)
            if b % 16 == 0 and sec == "drop":
                place(drums, C, t0, 0.35)
        elif sec == "break":
            for s in range(0, 16, 2):
                place(drums, H, t0 + s * STEP, 0.08)
        elif sec == "intro":
            for s in range(0, 16, 2):
                place(drums, H, t0 + s * STEP, 0.06 + 0.012 * b)
        # ---- bass
        if sec in ("drop", "outro") or (sec == "build" and b >= 12):
            if style == "neuro":
                if b % 2 == 0:
                    x = reese(r, 2 * BAR, wobble_rate=BPM / 60 / (2 if b % 4 == 0 else 1))
                    place(bass, x, t0, 0.55)
            else:
                # rolling sub 8ths + octave jumps
                pat = [0, 0, 12, 0, 0, 12, 0, 7]
                for k, iv in enumerate(pat):
                    nn = int(BEAT / 2 * SR * 0.92)
                    tt = np.arange(nn) / SR
                    f = hz(r + iv - 12)
                    x = (np.sin(2 * np.pi * f * tt) + 0.25 * np.tanh(3 * np.sin(2 * np.pi * f * tt))) * adsr(nn, 0.003, 0.05, 0.85, 0.02)
                    place(bass, x, t0 + k * BEAT / 2, 0.6)
                # hoover stabs
                for s in ([0, 3, 6, 10] if b % 2 == 0 else [0, 3, 6]):
                    place(music, hoover(r + 12 + (3 if s == 6 else 0), STEP * 2.6), t0 + s * STEP, 0.32)
        # ---- pad / atmosphere
        if b % 2 == 0:
            g = {"intro": 0.32, "build": 0.28, "break": 0.36, "drop": 0.1, "outro": 0.2}[sec]
            place(music, pad(chord(r), 2 * BAR), t0, g)
        if sec == "break" and b == 55 or (sec == "build" and b == 15):
            place(music, riser(BAR), t0, 0.3)

    sc = sidechain(n, kicks)
    mix = drums * 0.9 + bass * sc * 0.85 + music * sc
    mix = hp(mix, 28)
    mix /= np.percentile(np.abs(mix), 99.9)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    music = music / np.percentile(np.abs(mix), 99.9)
    # stereo width: small Haas on music bus
    d = int(0.011 * SR)
    left = mix + np.concatenate([np.zeros(d), music[:-d] * sc[:-d]]) * 0.15
    right = mix - np.concatenate([np.zeros(d), music[:-d] * sc[:-d]]) * 0.15
    st = np.stack([left, right], axis=1)
    st = st[: int(bars * BAR * SR)]
    st /= np.abs(st).max() / 0.95
    return st.astype(np.float32)


def main():
    for style, name in (("neuro", "dnb_neuro_174"), ("jungle", "jungle_hoover_174")):
        st = build(style)
        wav = Path(f"/tmp/{name}.wav")
        wavfile.write(wav, SR, (st * 32767).astype(np.int16))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "5",
                        str(OUT / f"{name}.ogg")], check=True)
        print(name, f"{len(st)/SR:.1f}s")


if __name__ == "__main__":
    main()
