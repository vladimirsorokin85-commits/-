#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка готового выпуска по ТЗ. Запускать перед сдачей.

    python3 check.py out/svodka_2026-11-04_utro.mp4 [out/svodka_2026-11-04_utro.txt]

Печатает таблицу «требование → факт → вердикт» и выходит с кодом 1, если есть провал.
"""
import os
import re
import subprocess
import sys


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    e = subprocess.run([ffmpeg(), "-hide_banner", "-i", path],
                       capture_output=True, text=True).stderr
    out = {"raw": e}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)
    if m:
        out["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    for line in e.splitlines():
        if "Video:" in line and "vcodec" not in out:
            m = re.search(r"Video:\s+(\w+)", line)
            if m:
                out["vcodec"] = m.group(1)
            m = re.search(r"\b(yuv\w+|rgb\w+)", line)
            if m:
                out["pixfmt"] = m.group(1)
            m = re.search(r"(\d{2,5})x(\d{2,5})", line)
            if m:
                out["width"], out["height"] = int(m.group(1)), int(m.group(2))
            m = re.search(r"([\d.]+) fps", line)
            if m:
                out["fps"] = float(m.group(1))
    m = re.search(r"Audio: (\w+)[^,]*,\s*(\d+) Hz, (stereo|mono|5\.1)", e)
    if m:
        out["acodec"], out["ar"], out["channels"] = m.group(1), int(m.group(2)), m.group(3)
    m = re.search(r"Audio: .*?, (\d+) kb/s", e)
    if m:
        out["abitrate"] = int(m.group(1))
    return out


def loudness(path):
    e = subprocess.run([ffmpeg(), "-hide_banner", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = e[e.rfind("Summary:"):] if "Summary:" in e else e
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    i = float(m.group(1)) if m else None
    m = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    peak = float(m.group(1)) if m else None
    return i, peak


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    mp4 = sys.argv[1]
    txt = sys.argv[2] if len(sys.argv) > 2 else mp4.rsplit(".", 1)[0] + ".txt"
    rows, fails = [], 0

    def add(name, fact, ok):
        nonlocal fails
        rows.append((name, str(fact), "OK" if ok else "ПРОВАЛ"))
        if not ok:
            fails += 1

    if not os.path.exists(mp4):
        sys.exit("нет файла: " + mp4)
    p = probe(mp4)
    add("контейнер: файл открывается", "да" if p.get("duration") else "нет", bool(p.get("duration")))
    add("разрешение 1280×720", "%s×%s" % (p.get("width"), p.get("height")),
        p.get("width") == 1280 and p.get("height") == 720)
    add("кадры 25 fps", p.get("fps"), p.get("fps") == 25.0)
    add("видео H.264 yuv420p", "%s / %s" % (p.get("vcodec"), p.get("pixfmt")),
        p.get("vcodec") == "h264" and p.get("pixfmt") == "yuv420p")
    add("звук AAC 44,1 кГц стерео", "%s / %s Гц / %s" % (p.get("acodec"), p.get("ar"), p.get("channels")),
        p.get("acodec") == "aac" and p.get("ar") == 44100 and p.get("channels") == "stereo")
    add("битрейт звука ≈128 кбит/с", (p.get("abitrate") or 0), 110 <= (p.get("abitrate") or 0) <= 145)
    dur = p.get("duration") or 0
    add("длительность 120–180 с", "%.1f с" % dur, 120 <= dur <= 180)

    i, peak = loudness(mp4)
    add("громкость −14,5 ±1 LUFS", "%s LUFS" % i, i is not None and -15.5 <= i <= -13.5)
    add("пик не выше −1,0 dBFS", "%s dBFS" % peak, peak is not None and peak <= -1.0)

    if os.path.exists(txt):
        with open(txt, encoding="utf-8") as f:
            lines = f.read().splitlines()
        add("первая строка «Источник: …»", (lines[0][:48] if lines else "—"),
            bool(lines) and lines[0].lower().startswith("источник:"))
        words = len(re.findall(r"[А-Яа-яЁёA-Za-z]+", " ".join(lines)))
        add("текст 350–420 слов", words, 350 <= words <= 430)
    else:
        add("текст .txt рядом", "нет файла", False)

    w1 = max(len(r[0]) for r in rows) + 2
    w2 = max(len(r[1]) for r in rows) + 2
    print("ПРОВЕРКА: " + os.path.basename(mp4))
    for a, b, c in rows:
        print("  %-*s %-*s %s" % (w1, a, w2, b, c))
    print("итог:", "СДАЧА ВОЗМОЖНА" if not fails else "ЕСТЬ ПРОВАЛЫ: %d" % fails)
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
