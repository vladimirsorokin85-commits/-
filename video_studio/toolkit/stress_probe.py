#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замер ударения по звуку: где в слове реально стоит акцент.

Метод (без слуха, как у «старшего товарища»):
  синтезируем одну и ту же фразу дважды, меняя только знак «+»;
  если движок понимает разметку — ударный слог становится длиннее и выше по тону.

Использование:
    python3 video_studio/toolkit/stress_probe.py take1.mp3 take2.mp3 ...

Печатает таблицу слогов (длительность, F0, громкость) и помечает самый
выраженный слог — именно он и есть ударный.
"""
import subprocess
import sys

import numpy as np

FF = "/home/user/.local/bin/ffmpeg"
SR = 16000


def load(p):
    r = subprocess.run([FF, "-v", "quiet", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if len(x) == 0:
        raise SystemExit(f"!! не читается: {p}")
    idx = np.where(np.abs(x) > 0.02)[0]
    return x[idx[0]: idx[-1] + 1] if len(idx) else x


def syllables(x, hop=80):
    n = (len(x) - 512) // hop
    rms = np.array([np.sqrt((x[i * hop:i * hop + 512] ** 2).mean()) for i in range(n)])
    rms = rms / (rms.max() + 1e-9)
    on = rms > 0.10
    segs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and (on[j] or (j + 5 < n and on[j:j + 5].any())):
                j += 1
            if (j - i) * hop / SR > 0.04:
                segs.append((i, j))
            i = j
        else:
            i += 1
    out = []
    for s, e in segs:
        f0 = []
        for k in range(s, e):
            fr = x[k * hop:k * hop + 512]
            if np.sqrt((fr ** 2).mean()) < 0.01:
                continue
            fr = fr - fr.mean()
            ac = np.correlate(fr, fr, "full")[511:]
            lo, hi = int(SR / 400), int(SR / 70)
            lag = lo + int(np.argmax(ac[lo:hi]))
            if ac[lag] > 0.3 * ac[0]:
                f0.append(SR / lag)
        out.append(dict(t0=s * hop / SR, t1=e * hop / SR, dur=(e - s) * hop / SR,
                        f0=float(np.median(f0)) if f0 else 0.0, amp=float(rms[s:e].mean())))
    return out


def scores(syl):
    """Ударный слог: длиннее, громче, выше по тону. Нормируем к максимуму во фразе."""
    if not syl:
        return []
    dmax = max(s["dur"] for s in syl) or 1e-9
    amax = max(s["amp"] for s in syl) or 1e-9
    fmax = max(s["f0"] for s in syl) or 1e-9
    return [(s["dur"] / dmax) * 0.45 + (s["amp"] / amax) * 0.35 + (s["f0"] / fmax) * 0.20
            for s in syl]


def probe(paths):
    rows = []
    for p in paths:
        syl = syllables(load(p))
        if not syl:
            print(f"{p}: нет речи")
            continue
        sc = scores(syl)
        top = int(np.argmax(sc))
        rows.append((p, syl, sc, top))
        print(f"\n{p} · слогов: {len(syl)}")
        for i, (s, k) in enumerate(zip(syl, sc)):
            mark = "  ← ударный" if i == top else ""
            print(f"  {i+1:2d}. {s['t0']:5.2f}–{s['t1']:5.2f}с · {1000*s['dur']:4.0f} мс · "
                  f"F0 {s['f0']:4.0f} Гц · громк {s['amp']:.2f} · счёт {k:.2f}{mark}")
    if len(rows) >= 2:
        print("\nСВОДКА (номер ударного слога):")
        for p, syl, sc, top in rows:
            print(f"  {p}: слог {top+1} из {len(syl)}")
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    probe(sys.argv[1:])
