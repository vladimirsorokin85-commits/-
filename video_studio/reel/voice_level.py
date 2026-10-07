"""Speech leveler for TTS clips that jump between whisper and shout.

Gated AGC: RMS envelope (~60 ms) -> per-sample gain toward a target level, only where speech is
present (gate), boost/cut caps, gain smoothed with separate attack/release, then soft-knee
compression + true-peak style limiter. Inspired by ffmpeg speechnorm / Dynamic Audio Normalizer,
but with a noise gate so pauses and breaths are not pumped up.
"""
import numpy as np
from scipy.ndimage import uniform_filter1d, maximum_filter1d
from scipy.signal import butter, sosfilt

SR = 44100


def _db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def level(x, target_db=-18.0, max_boost=14.0, max_cut=12.0, gate_db=-42.0, sr=SR):
    x = x.astype(np.float64)
    x = sosfilt(butter(2, 75, "hp", fs=sr, output="sos"), x)
    # loudness-ish envelope: RMS over 60 ms, K-ish emphasis by high-shelf proxy
    emph = x + 0.5 * sosfilt(butter(1, 1500, "hp", fs=sr, output="sos"), x)
    rms = np.sqrt(uniform_filter1d(emph ** 2, int(0.06 * sr)) + 1e-12)
    # hold the envelope over short dips between syllables so consonants are not pumped
    rms = maximum_filter1d(rms, int(0.05 * sr))
    env_db = _db(rms)
    gain_db = np.clip(target_db - env_db, -max_cut, max_boost)
    gate = env_db < gate_db
    gain_db[gate] = 0.0  # leave silence alone
    # smooth: fast-ish for cuts (attack 15 ms), slower for boosts (release 120 ms)
    g = np.empty_like(gain_db)
    a_att = np.exp(-1 / (0.015 * sr))
    a_rel = np.exp(-1 / (0.12 * sr))
    prev = 0.0
    for i, v in enumerate(gain_db):  # one-pole with asymmetric coefficients
        a = a_att if v < prev else a_rel
        prev = a * prev + (1 - a) * v
        g[i] = prev
    y = x * 10 ** (g / 20)
    # gentle compressor above target+4 dB
    env2 = _db(np.sqrt(uniform_filter1d(y ** 2, int(0.02 * sr)) + 1e-12))
    over = np.maximum(0, env2 - (target_db + 4))
    cg = uniform_filter1d(-(over * (1 - 1 / 3)), int(0.01 * sr))  # smoothed gain: no crackle
    y *= 10 ** (cg / 20)
    # lookahead limiter at -1 dBFS
    lim = 10 ** (-1 / 20)
    pk = maximum_filter1d(np.abs(y), int(0.008 * sr))
    gl = np.minimum(1.0, lim / np.maximum(pk, 1e-9))
    gl = uniform_filter1d(gl, int(0.008 * sr))  # smooth gain changes (no stepwise crackle)
    y = np.clip(y * gl, -lim, lim)
    y = expand(y, sr)
    return y.astype(np.float32)


def expand(y, sr=SR, below_db=30.0, depth_db=24.0):
    """Downward expander: anything more than `below_db` under the speech level (TTS breaths, hiss,
    crackly onsets) is smoothly pulled down by up to `depth_db`. 5 ms attack, 60 ms release."""
    env = _db(np.sqrt(uniform_filter1d(y.astype(np.float64) ** 2, int(0.01 * sr)) + 1e-12))
    speech = np.percentile(env[env > -60], 80) if np.any(env > -60) else -20
    thr = speech - below_db
    target = -np.clip((thr - env) * 2.0, 0, depth_db)  # 1:3 expansion below threshold
    g = np.empty_like(target)
    a_att, a_rel = np.exp(-1 / (0.005 * sr)), np.exp(-1 / (0.06 * sr))
    prev = 0.0
    for i, v in enumerate(target):
        a = a_att if v > prev else a_rel   # open fast, close slowly
        prev = a * prev + (1 - a) * v
        g[i] = prev
    return y * 10 ** (g / 20)


def spread(x, sr=SR):
    w = int(0.3 * sr)
    r = np.array([_db(np.sqrt(np.mean(x[i:i + w] ** 2))) for i in range(0, len(x) - w, w)])
    r = r[r > -45]
    return float(np.percentile(r, 90) - np.percentile(r, 10))
