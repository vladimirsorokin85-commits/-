#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сравнение подложки: тихая (по ТЗ) и драйв (по MUSIC_POLICY канала).

Собирает один и тот же выпуск в двух режимах и выкладывает короткие фрагменты,
чтобы владелец послушал и выбрал. Режим задаётся в сценарии: 

    "music": {"track": "fvi-Arpent.ogg", "offset": 12.0, "level": 0.20, "mode": "quiet"}

`drive` берёт громкость по правилам канала: музыка −12 LUFS, дакинг 9:1 под голос.
`quiet` — тихая подложка из ТЗ: верх срезан, низкий уровень.

    python3 music_ab.py scripts/demo_format.json -o ../music_ab
"""
import argparse
import json
import os
import subprocess
import sys

import build

EXCERPT_START = 24.0
EXCERPT_LEN = 26.0


def make(spec, mode, out_dir, tag):
    spec = json.loads(json.dumps(spec))
    spec.setdefault("vo_dir", spec["slug"])
    spec["slug"] = "%s_%s" % (spec["slug"], tag)
    spec["music"]["mode"] = mode
    tl, master = build.build_audio(spec)
    mp3 = os.path.join(out_dir, "%s.mp3" % tag)
    build.run([build.ffmpeg(), "-y", "-ss", "%.1f" % EXCERPT_START, "-t", "%.1f" % EXCERPT_LEN,
               "-i", master, "-c:a", "libmp3lame", "-b:a", "160k", "-ar", "44100", "-ac", "2", mp3])
    return mp3, tl["total"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", default=os.path.join("..", "music_ab"))
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    res = []
    for mode in ("quiet", "drive"):
        mp3, total = make(spec, mode, a.out, mode)
        print("%-6s → %s (выпуск %.1f с)" % (mode, mp3, total))
        res.append((mode, mp3))
    print("\nсравнение: %s и %s — по %d с, начиная с %.0f-й секунды"
          % (res[0][1], res[1][1], EXCERPT_LEN, EXCERPT_START))
    return 0


if __name__ == "__main__":
    sys.exit(main())
