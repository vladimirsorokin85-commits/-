# -*- coding: utf-8 -*-
"""Рендер анонсов радио «В ОКОПЕ»: pillow-кадры → ffmpeg (H.264 + AAC).

    python3 render.py r15                 # пробные кадры в /tmp/ra
    python3 render.py r15 --still 2 5.5   # кадры на заданных секундах
    python3 render.py r15 --full          # полный mp4

Сцены и общая длина — из timeline_<tag>.json (пишет build_audio.py).
"""
import importlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

import base as B
from base import H, W, ac

FF = "/home/user/.local/bin/ffmpeg"


def load_tl(tag):
    with open(os.path.join(B.BASE, "timeline_%s.json" % tag), encoding="utf-8") as f:
        tl = json.load(f)
    items = sorted(((n, t) for n, t in tl["scenes"]), key=lambda z: z[1])
    items[0] = (items[0][0], 0.0)
    return tl, items


def frame(mod, scenes, tl, t):
    name, st = scenes[0]
    for n2, s0 in scenes:
        if t >= s0 - 1e-6:
            name, st = n2, s0
    l = t - st
    cv = Image.new("RGBA", (W, H), ac(B.BG0, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    mod.FN[name](cv, d, t, l)
    out = Image.alpha_composite(cv, ui)

    hud_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    B.hud(ImageDraw.Draw(hud_l), t, tl["total"])
    out = Image.alpha_composite(out, hud_l)

    B.sweep(out, t, B.OLV, 26, 2.4)
    B.scanlines(out)
    B.grain(out, t)
    out = out.convert("RGB")
    out = B.punch(out, t, [s for _, s in scenes[1:]], 0.045)

    arr = np.asarray(out).astype(np.float32)
    k = 1.0 + 0.020 * B.beat_pulse(t, tl["bpm"])
    arr = np.clip(arr * k, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def main():
    tag = sys.argv[1]
    mod = importlib.import_module("reel" + tag[1:])
    tl, scenes = load_tl(tag)
    full = "--full" in sys.argv

    if not full:
        os.makedirs("/tmp/ra", exist_ok=True)
        times = []
        for a in sys.argv[2:]:
            if a == "--still":
                continue
            try:
                times.append(float(a))
            except ValueError:
                pass
        if not times:
            for n, st in scenes:
                times += [st + 0.3, st + 1.1]
        for t in times:
            if t >= tl["total"]:
                continue
            frame(mod, scenes, tl, t).save("/tmp/ra/%s_%05.2f.jpg" % (tag, t), quality=92)
            print("saved", round(t, 2), flush=True)
        return

    audio = os.path.join(B.BASE, "master_%s.m4a" % tag)
    out = os.path.join(B.BASE, "v_okope_radio_%s_9x16.mp4" % tag)
    n = int(round(tl["total"] * B.FPS))
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(B.FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-x264-params", "keyint=48:min-keyint=24:scenecut=0",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-t", "%.2f" % tl["total"], out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(mod, scenes, tl, i / float(B.FPS)).tobytes())
        if i % 150 == 0:
            el = time.time() - t0
            print("%d/%d %.2ffps" % (i, n, i / max(el, .01)), flush=True)
    p.stdin.close()
    print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
    print("size", os.path.getsize(out) if os.path.exists(out) else "MISSING", flush=True)


if __name__ == "__main__":
    main()
