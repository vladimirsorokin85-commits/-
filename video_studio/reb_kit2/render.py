# -*- coding: utf-8 -*-
"""Рендер роликов про комплект РЭБ: pillow-кадры → ffmpeg (H.264 + AAC).

    python3 render.py r1                 # пробные кадры в /tmp/rk
    python3 render.py r1 --still 2 9.5   # кадры на заданных секундах
    python3 render.py r1 --full          # полный mp4

Сцены и общая длина берутся из timeline_<tag>.json, который пишет build_audio.py,
поэтому монтаж всегда попадает точно на старты реплик.
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
    items = sorted(((n, t) for n, t in tl["scenes"].items()), key=lambda z: z[1])
    items[0] = (items[0][0], 0.0)          # первый кадр — сразу сцена, голос входит позже
    return tl, items


def frame(mod, scenes, total, t):
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
    B.hud(ImageDraw.Draw(hud_l), t, total, mod.TITLE)
    out = Image.alpha_composite(out, hud_l)
    B.scanlines(out)
    B.grain(out, t)
    out = out.convert("RGB")
    out = B.punch(out, t, [s for _, s in scenes[1:]])
    arr = np.asarray(out).astype(np.float32)
    beat = (t / 0.5) % 1.0
    arr *= 1.0 + 0.014 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main():
    tag = sys.argv[1]
    mod = importlib.import_module("reel" + tag[1:])
    tl, scenes = load_tl(tag)
    total = tl["total"]
    full = "--full" in sys.argv

    if not full:
        os.makedirs("/tmp/rk", exist_ok=True)
        times = []
        for i, a in enumerate(sys.argv[2:]):
            if a == "--still":
                continue
            try:
                times.append(float(a))
            except ValueError:
                pass
        if not times:
            for n, st in scenes:
                times += [st + 0.35, st + 1.6, st + 3.2]
        for t in times:
            if t >= total:
                continue
            frame(mod, scenes, total, t).save("/tmp/rk/%s_%05.2f.jpg" % (tag, t), quality=92)
            print("saved", round(t, 2), flush=True)
        return

    audio = os.path.join(B.BASE, "master_%s.m4a" % tag)
    out = os.path.join(B.BASE, "v_okope_reb_kit2_%s_9x16.mp4" % tag)
    n = int(round(total * B.FPS))
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(B.FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-x264-params", "keyint=48:min-keyint=24:scenecut=0",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-t", "%.2f" % total, out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(mod, scenes, total, i / float(B.FPS)).tobytes())
        if i % 150 == 0:
            el = time.time() - t0
            print("%d/%d %.2ffps" % (i, n, i / max(el, .01)), flush=True)
    p.stdin.close()
    print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
    print("size", os.path.getsize(out) if os.path.exists(out) else "MISSING", flush=True)


if __name__ == "__main__":
    main()
