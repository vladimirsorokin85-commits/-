"""Asian-flavoured jungle bed: base amen/reese bed (reel/music_reel.py) + plucked guzheng lead
in F minor pentatonic (physical string model with press-bends), taiko hits and a gong wash on cues."""
import os
import sys
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reel"))
import music_reel as base  # noqa: E402
from music_reel import SR, BEAT, BAR, place, lp, hp, pitch, load  # noqa: E402,F401

rng = np.random.default_rng(7)


def ks_pluck(f, dur, bright=0.6):
    """Karplus-Strong string, plucked near the bridge (guzheng-like)."""
    n = int(dur * SR)
    N = max(2, int(round(SR / f)))
    buf = rng.uniform(-1, 1, N)
    buf = lp(buf, 1500 + 2500 * bright, 2)  # softer pluck: no harsh noise burst
    buf -= buf.mean()
    out = np.empty(n)
    fb = 0.9965
    for i in range(n):
        j = i % N
        out[i] = buf[j]
        buf[j] = fb * 0.5 * (buf[j] + buf[(j + 1) % N])
    return out


def bend(x, semis_env):
    """time-varying pitch via variable-rate reading (semis_env per-sample)."""
    rate = 2 ** (semis_env / 12)
    pos = np.cumsum(rate)
    pos = pos[pos < len(x) - 1]
    return np.interp(pos, np.arange(len(x)), x)


def guzheng_note(midi, dur, kind=0):
    f = 440 * 2 ** ((midi - 69) / 12)
    x = ks_pluck(f, dur + 0.3)
    n = len(x)
    t = np.arange(n) / SR
    env = np.zeros(n)
    if kind == 1:  # press-bend up a whole tone after the attack
        env = 2.0 * np.clip((t - 0.10) / 0.12, 0, 1)
    elif kind == 2:  # slide down into the note
        env = 2.0 * (1 - np.clip(t / 0.09, 0, 1))
    env = env + 0.25 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.25) / 0.3, 0, 1)  # vibrato
    y = bend(x, env)
    y = y[: int(dur * SR)]
    y = hp(y, 180) + 0.3 * lp(y, 900)  # body resonance (filter BEFORE the fades)
    y = lp(y, 2200, 4)  # dark, soft string: no ringing upper partials (they beat like a cicada)
    att = int(0.010 * SR)
    y[:att] *= np.sin(np.linspace(0, np.pi / 2, att)) ** 2
    fade = min(len(y) // 2, int(0.08 * SR))
    y[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
    return y


PHRASES = [
    [(77, 0), None, (75, 0), (72, 1), None, (70, 0), (72, 0), None, (68, 2), None, (70, 0), None, (65, 0), None, None, None],
    [(72, 0), None, (75, 0), (77, 0), None, (80, 1), (77, 0), None, (75, 0), None, (72, 0), (75, 0), (77, 2), None, None, None],
    [(65, 0), (68, 0), (70, 0), None, (72, 1), None, (70, 0), (68, 0), (65, 2), None, None, (63, 0), (65, 0), None, None, None],
    [(84, 2), None, (80, 0), (77, 0), None, (75, 0), (77, 1), None, (72, 0), None, (75, 0), None, (77, 0), None, None, None],
]


def reverb(x, sec=1.4, wet=0.25):
    n = int(sec * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.28 * SR))
    ir = lp(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x + wet * fftconvolve(x, ir)[: len(x)]


def make_music(total, cues, drop_from=None):
    bed = base.make_music(total, cues, drop_from)
    n = len(bed)
    lead = np.zeros(n + SR)
    eighth = BEAT / 2
    t, k = 0.0, 0
    cache = {}
    while t < total:
        ph = PHRASES[k % len(PHRASES)]
        for s, note in enumerate(ph):
            if note is None:
                continue
            # note length = until next note
            nxt = next((j for j in range(s + 1, len(ph)) if ph[j] is not None), len(ph))
            dur = min(1.6, (nxt - s) * eighth + 0.01)
            key = (note, round(dur, 3))
            if key not in cache:
                cache[key] = guzheng_note(note[0], dur, note[1])
            place(lead, cache[key], t + s * eighth, 0.8 if s % 4 == 0 else 0.6)
        t += 2 * BAR
        k += 1
    lead = reverb(lead[:n])
    # taiko: pitched-down heavy kick, low-passed, on cues (dum .. dum-dum) and an intro roll
    kick = load("drums/one-shots/kick/drum_heavy_kick.flac")
    taiko = lp(pitch(kick, -7), 260) * 1.0
    perc = np.zeros(n + 4 * SR)
    for c in [0.0] + list(cues[1:]):
        for off, g in ((0, 1.0), (BEAT * 1.5, 0.55), (BEAT * 2, 0.7)):
            place(perc, taiko, c + off, g)
    # gong wash: splash cymbal down an octave + long tail
    splash = load("drums/one-shots/other/drum_splash_hard.flac")
    gong = lp(pitch(splash, -14), 3500)
    gong = reverb(np.concatenate([gong, np.zeros(SR)]), 2.5, 0.5)
    for c in [0.0] + list(cues[1:]) + ([drop_from] if drop_from else []):
        place(perc, gong, c, 0.5)
    perc = perc[:n]

    def norm(x):
        return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)
    # lead: RMS-matched (continuous); perc: PEAK-matched (sparse hits must not out-peak the bed)
    pk = lambda x: np.percentile(np.abs(x), 99.99) + 1e-9
    bedn = norm(bed)
    mix = bedn + norm(lead) * 0.42 + perc / pk(perc) * pk(bedn) * 0.55
    if os.environ.get("MUSIC_QC"):
        from scipy.ndimage import maximum_filter1d
        m = mix / (np.percentile(np.abs(mix), 99.95) + 1e-9) * 0.9
        g = np.minimum(1, 0.9 / np.maximum(maximum_filter1d(np.abs(m), 441), 1e-9))
        print("music limiter GR max dB", round(20 * np.log10(g.min()), 1), "time>2dB", round(float(np.mean(g < 0.794)), 4))
    return base.clean_limit(mix)


# ---------------------------------------------------------------- v6: real catalog track as the bed
CATALOG = Path(__file__).resolve().parent.parent / "music_catalog" / "dnb_neuro_174.ogg"


def _load_any(path):
    import subprocess
    ff = str(Path.home() / ".local/bin/ffmpeg")
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def _downbeat_phase(x, start_s=8.0, span_s=30.0):
    """Phase (s) of the strongest beat grid at 174 BPM (onset-strength fold)."""
    seg = x[int(start_s * SR): int((start_s + span_s) * SR)]
    hop = 256
    n = len(seg) // hop
    e = np.sqrt(np.mean(seg[: n * hop].reshape(n, hop) ** 2, 1))
    on = np.maximum(0, np.diff(np.log(e + 1e-6)))
    fr = SR / hop
    best, bp = -1, 0.0
    for ph in np.arange(0, BAR, 1 / fr):
        idx = (np.arange(ph, span_s - 0.1, BEAT) * fr).astype(int)
        idx = idx[idx < len(on)]
        sc = on[idx].sum() + 0.5 * on[(np.arange(ph, span_s - 0.1, BAR) * fr).astype(int)].sum()
        if sc > best:
            best, bp = sc, ph
    return start_s + bp


def make_music_v6(total, cues, drop_from=None, splash=None):
    """Intro (until first cue>0 / splash): guzheng + taiko + boom. Then the catalog DnB track (beat-aligned).
    Outro (after drop_from): track fades to 35 %, guzheng returns."""
    splash = splash if splash is not None else BAR
    n = int(total * SR)
    track = _load_any(CATALOG)
    t0 = _downbeat_phase(track, 16.0)          # start inside an established groove
    seg = track[int(t0 * SR): int(t0 * SR) + n]
    bed = np.zeros(n)
    s0 = int(splash * SR)
    bed[s0: s0 + len(seg) - 0] = seg[: n - s0]
    fi = int(0.015 * SR)
    bed[s0: s0 + fi] *= np.linspace(0, 1, fi)
    # filter-sweep entry: drums start muffled (no hi-hat «cicada» rattle) and open up over 2 bars
    sw = int(2 * BAR * SR)
    w = np.ones(n)
    w[:s0] = 0.0
    w[s0: s0 + sw] = np.linspace(0, 1, len(w[s0: s0 + sw])) ** 2
    bed = w * bed + (1 - w) * lp(lp(bed, 500), 500)
    if drop_from:
        d0 = int(drop_from * SR)
        ramp = np.ones(n)
        ramp[d0: d0 + int(0.6 * SR)] = np.linspace(1, 0.35, len(ramp[d0: d0 + int(0.6 * SR)]))
        ramp[d0 + int(0.6 * SR):] = 0.35
        bed *= ramp
    # guzheng only in intro + outro (no key clash with the track)
    lead = np.zeros(n + 2 * SR)
    eighth = BEAT / 2
    cache = {}

    def phrase(t, ph, g=0.7):
        for s, note in enumerate(ph):
            if note is None:
                continue
            nxt = next((j for j in range(s + 1, len(ph)) if ph[j] is not None), len(ph))
            dur = min(1.6, (nxt - s) * eighth + 0.01)
            key = (note, round(dur, 3))
            if key not in cache:
                cache[key] = guzheng_note(note[0], dur, note[1])
            place(lead, cache[key], t + s * eighth, g)
    phrase(0.0, PHRASES[0][:8])                 # first bar = intro splash
    if drop_from:
        t, k = drop_from, 0
        while t < total - 0.5:
            phrase(t, PHRASES[k % 4], 0.6)
            t += 2 * BAR
            k += 1
    lead = reverb(lead[:n], 1.2, 0.18)
    kick = load("drums/one-shots/kick/drum_heavy_kick.flac")
    boom = load("misc/misc_cineboom.flac")
    taiko = lp(pitch(kick, -7), 260)
    perc = np.zeros(n + 4 * SR)
    for c in [0.0] + list(cues[1:]):
        for off, g in ((0, 1.0), (BEAT * 1.5, 0.55), (BEAT * 2, 0.7)):
            place(perc, taiko, c + off, g)
        place(perc, lp(lp(boom, 1200), 1200), max(0, c - 0.02), 0.6)  # no hiss tail
    perc = perc[:n]
    pk = lambda x: np.percentile(np.abs(x), 99.99) + 1e-9
    ref = pk(seg)
    mix = bed + lead / pk(lead) * ref * 0.45 + perc / pk(perc) * ref * 0.6
    return base.clean_limit(mix)
