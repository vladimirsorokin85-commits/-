"""Voice QC: vocal-fry / creak detector for TTS clips.
Creaky voice = voiced frames with very low, irregular F0 (pulses < ~75 Hz) -> heard as «треск/хрип».
usage: python3 voice_qc.py a.mp3 b.mp3 ..."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio_qc import load, SR


def fry(x):
    w, h = int(0.04 * SR), int(0.01 * SR)
    n = (len(x) - w) // h
    voiced = fryc = 0
    jit = []
    for i in range(n):
        f = x[i * h: i * h + w]
        e = np.sqrt(np.mean(f ** 2))
        if e < 0.02:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, "full")[w - 1:]
        ac /= ac[0] + 1e-9
        lo, hi = int(SR / 400), int(SR / 50)
        lag = lo + np.argmax(ac[lo:hi])
        if ac[lag] < 0.3:
            continue  # unvoiced
        voiced += 1
        f0 = SR / lag
        if f0 < 75:
            fryc += 1
    return voiced, fryc


if __name__ == "__main__":
    for p in sys.argv[1:]:
        v, c = fry(load(p))
        print(f"{p}: voiced frames {v}, creaky {c} ({100 * c / max(v, 1):.1f}%)")
