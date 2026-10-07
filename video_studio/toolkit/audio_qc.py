"""Audio QC: click/crackle detector + HF-noise meter.
usage: python3 audio_qc.py file.(wav|mp4|mp3) ..."""
import subprocess, sys
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import stft
SR = 44100
FF = str(Path.home() / ".local/bin/ffmpeg")


def load(p):
    raw = subprocess.run([FF, "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def clicks(x):
    d = np.diff(x, 2)
    wide = np.sqrt(np.maximum(uniform_filter1d(d ** 2, int(0.05 * SR)), 0)) + 1e-6
    ev = np.where((np.abs(d) / wide > 9) & (np.abs(d) > 0.01))[0]
    if not len(ev):
        return 0, []
    g = [ev[0]] + [e for a, e in zip(ev[:-1], ev[1:]) if e - a > int(0.005 * SR)]
    return len(g), [round(i / SR, 2) for i in g[:15]]


def hf_noise(x):
    f, t, Z = stft(x, SR, nperseg=2048)
    P = np.abs(Z) ** 2 + 1e-15
    b = (f > 6000) & (f < 14000)
    flat = np.exp(np.mean(np.log(P[b]), 0)) / np.mean(P[b], 0)
    hf = 10 * np.log10(P[b].sum(0) / P.sum(0))
    return round(float(np.median(hf)), 1), round(float(np.median(flat)), 2)


def report(x, name):
    n, t = clicks(x)
    hf, fl = hf_noise(x)
    pk = 20 * np.log10(np.abs(x).max() + 1e-12)
    print(f"{name}: clicks={n} {t}  HFshare={hf}dB flatness={fl}  peak={pk:.2f}dBFS clipped={int((np.abs(x) >= 0.999).sum())}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        report(load(p), Path(p).name)
