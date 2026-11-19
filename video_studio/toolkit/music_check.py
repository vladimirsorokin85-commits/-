#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка трека на «драйв» по правилам канала «В Окопе» (см. video_studio/MUSIC_POLICY.md).

    python3 video_studio/toolkit/music_check.py video_studio/music_downloaded/fvi-BeatOne.ogg

Возвращает код 0, если трек ДРАЙВОВЫЙ, и 1, если нет — сборка звука обязана на этом падать.
"""
import argparse
import os
import subprocess
import sys

import numpy as np

FF = os.environ.get("FFMPEG_BIN", "/home/user/.local/bin/ffmpeg")
SR = 22050

# пороги из MUSIC_POLICY.md, п.3
MIN_BPM = 120
MIN_SUB = 0.15          # энергия 35–100 Гц
MIN_LOW = 0.30          # суб + 100–300 Гц
MIN_RMS_DB = -18.0


def load(path):
    r = subprocess.run([FF, "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if len(x) < SR * 5:
        raise SystemExit(f"!! не читается или короче 5 с: {path}")
    return x


def measure(path, tempo_hint=None):
    x = load(path)
    rms = float(np.sqrt((x ** 2).mean()))
    db = 20 * np.log10(rms + 1e-9)

    hop = 220
    n = len(x) // hop
    env = np.abs(x[:n * hop].reshape(n, hop)).mean(1)
    e = np.maximum(env - np.convolve(env, np.ones(12) / 12, mode="same"), 0)
    if tempo_hint is None:
        ac = np.correlate(e, e, "full")[n - 1:]
        ac = ac / (ac[0] if ac[0] else 1)
        lo, hi = int(6000 / 180), int(6000 / 110)
        lag = lo + int(np.argmax(ac[lo:hi]))
        bpm = 6000.0 / lag
    else:
        # A syncopated break often peaks at 1.5 beats; score the known grid as a whole.
        centered = e - e.mean()
        ac = np.correlate(centered, centered, "full")[n - 1:]
        ac = ac / (ac[0] if ac[0] else 1)
        tempos = np.linspace(tempo_hint - 3, tempo_hint + 3, 31)
        lags = (SR / hop) * 60 / tempos
        grid = np.arange(len(ac))
        votes = sum(weight * np.interp(lags * multiple, grid, ac)
                    for multiple, weight in ((1, 1), (2, 1.15), (4, .4), (8, .22)))
        best = int(np.argmax(votes))
        # A provided grid still has to be present in the waveform.
        bpm = float(tempos[best]) if votes[best] >= .18 else 0.0

    nfft = 2048
    frames = np.lib.stride_tricks.sliding_window_view(x[: len(x) // nfft * nfft], nfft)[:: nfft // 2]
    P = np.abs(np.fft.rfft(frames * np.hanning(nfft), axis=1)).mean(0)
    fr = np.fft.rfftfreq(nfft, 1 / SR)
    tot = P.sum() + 1e-9
    sub = P[(fr >= 35) & (fr < 100)].sum() / tot
    low = P[(fr >= 100) & (fr < 300)].sum() / tot
    cent = float((P * fr).sum() / tot)
    return dict(bpm=bpm, db=db, sub=sub, low=low, sub_low=sub + low, cent=cent,
                dur=len(x) / SR)


def check(path, verbose=True, tempo_hint=None):
    m = measure(path, tempo_hint=tempo_hint)
    fails = []
    if m["bpm"] < MIN_BPM:
        fails.append(f"темп {m['bpm']:.0f} BPM < {MIN_BPM}")
    if m["sub"] < MIN_SUB:
        fails.append(f"суба-бас {100*m['sub']:.1f}% < {100*MIN_SUB:.0f}%")
    if m["sub_low"] < MIN_LOW:
        fails.append(f"низ {100*m['sub_low']:.1f}% < {100*MIN_LOW:.0f}%")
    if m["db"] < MIN_RMS_DB:
        fails.append(f"уровень {m['db']:.1f} dB < {MIN_RMS_DB} dB")
    if verbose:
        print(f"{path}")
        print(f"  {m['dur']:.0f} с · {m['bpm']:.0f} BPM · {m['db']:.1f} dB · "
              f"суб {100*m['sub']:.1f}% · низ {100*m['sub_low']:.1f}% · центр {m['cent']:.0f} Гц")
    ok = not fails
    if verbose:
        print("  ВЕРДИКТ: ДРАЙВ ✔" if ok else "  ВЕРДИКТ: НЕ ДРАЙВ ✘ — " + "; ".join(fails))
    return ok, m, fails


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Проверка музыкального мастера на драйв")
    parser.add_argument("--tempo-hint", type=float,
                        help="Проверить известную сетку трека, если у брейкбита несколько пиков")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.tempo_hint is not None and not 100 <= args.tempo_hint <= 220:
        parser.error("--tempo-hint должен быть между 100 и 220 BPM")
    allok = True
    for path in args.paths:
        ok, _, _ = check(path, tempo_hint=args.tempo_hint)
        allok = allok and ok
    sys.exit(0 if allok else 1)
