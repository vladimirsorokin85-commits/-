# -*- coding: utf-8 -*-
"""Рендер ролика «Рюкзак 7.62»: pillow-кадры → ffmpeg (H.264 + AAC).

    python3 render.py r1        # только кадры в /tmp (проверка)
    python3 render.py r1 --full # полный рендер mp4
"""
import importlib
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


def frame(mod, t):
    name, st = mod.SCENES[0]
    for n2, s0 in mod.SCENES:
        if t >= s0 - 1e-6:
            name, st = n2, s0
    l = t - st
    cv = Image.new("RGBA", (W, H), ac(B.BG0, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    mod.FN[name](cv, d, t, l)
    out = Image.alpha_composite(cv, ui)
    hud_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    B.hud(ImageDraw.Draw(hud_l), t, mod.TOTAL, mod.TITLE)
    out = Image.alpha_composite(out, hud_l)
    B.scanlines(out)
    B.grain(out, t)
    out = out.convert("RGB")
    out = B.punch(out, t, [s for _, s in mod.SCENES[1:]])
    arr = np.asarray(out).astype(np.float32)
    beat = (t / 0.5) % 1.0
    arr *= 1.0 + 0.015 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main():
    tag = sys.argv[1]
    mod = importlib.import_module("reel" + tag[1:])
    full = "--full" in sys.argv
    if not full:
        os.makedirs("/tmp/rk", exist_ok=True)
        for a in sys.argv[2:]:
            if a.startswith("--"):
                continue
            t = float(a)
            frame(mod, t).save("/tmp/rk/%s_%05.2f.jpg" % (tag, t), quality=92)
            print("saved", t, flush=True)
        return

    audio = os.path.join(B.BASE, "master_%s.m4a" % tag)
    out = os.path.join(B.BASE, "v_okope_ruck762_%s_9x16.mp4" % tag)
    n = int(round(mod.TOTAL * 30))
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", "30", "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-x264-params", "keyint=48:min-keyint=24:scenecut=0",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(mod, i / 30).tobytes())
        if i % 150 == 0:
            el = time.time() - t0
            print("%d/%d %.2ffps" % (i, n, i / max(el, .01)), flush=True)
    p.stdin.close()
    print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
    print("size", os.path.getsize(out) if os.path.exists(out) else "MISSING", flush=True)


if __name__ == "__main__":
    main()
