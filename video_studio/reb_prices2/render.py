# -*- coding: utf-8 -*-
"""Рендер прайс-роликов v2 с проверкой наложений текста."""
import importlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

import layout as L
from layout import H, W, ac

import scenes as S

FF = "/home/user/.local/bin/ffmpeg"
BASE = os.path.dirname(os.path.abspath(__file__))

HUD_TITLE = "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ"
HUD_FOOT = "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ · РОЗНИЦА"
HUD_CONTACT = "@VES_nn  ·  Москва и Липецк"


def load_tl(tag):
    with open(os.path.join(BASE, "timeline_%s.json" % tag), encoding="utf-8") as f:
        tl = json.load(f)
    items = sorted(((n, t) for n, t in tl["scenes"].items()), key=lambda z: z[1])
    items[0] = (items[0][0], 0.0)
    return tl, items


def frame(tag, scenes, total, t, fns=None, check=False):
    name, st = scenes[0]
    for n2, s0 in scenes:
        if t >= s0 - 1e-6:
            name, st = n2, s0
    l = t - st
    cv = Image.new("RGBA", (W, H), ac(L.BG1, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)

    L.reset_boxes()
    L._T = t
    (fns or S.scenes(tag))[name](cv, d, t, l)
    bad = L.collisions()
    if bad and check:
        raise SystemExit("!! наложение текста в сцене %s: %s" % (name, bad[:3]))

    # медленный наплыв фона внутри плана: кадр не «стоит» 8–9 секунд,
    # текст и плашки не двигаются — только сетка
    nxt = [s0 for _, s0 in scenes if s0 > st + 1e-6]
    end = nxt[0] if nxt else total
    pz = min(max(l / max(end - st, .001), 0.0), 1.0)
    z = 1.0 + 0.035 * pz
    w2, h2 = int(W / z), int(H / z)
    x0 = (W - w2) // 2
    y0 = (H - h2) // 2
    cv = cv.crop((x0, y0, x0 + w2, y0 + h2)).resize((W, H), Image.LANCZOS)

    out = Image.alpha_composite(cv, ui)
    hud = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    L.hud(ImageDraw.Draw(hud), t, total)
    out = Image.alpha_composite(out, hud)
    out.alpha_composite(L.GRAIN[int(t * 13) % 4])
    out.alpha_composite(L.VIGN)
    out = out.convert("RGB")
    out = L.punch(out, t, [s for _, s in scenes[1:]])
    arr = np.asarray(out).astype(np.float32)
    beat = (t / 0.370) % 1.0
    arr *= 1.0 + 0.011 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def check_all(tag, scenes, total, fns):
    """Прогоняет сцены по сетке времени и падает при наложениях."""
    bad_total = []
    for n, st in scenes:
        for dt in (0.6, 1.6, 3.0, 5.0, 8.0):
            t = min(st + dt, total - .1)
            l = t - st
            cv = Image.new("RGBA", (W, H), ac(L.BG1, 255))
            ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ui)
            L.reset_boxes()
            L._T = t
            fns[n](cv, d, t, l)
            bad = L.collisions()
            if bad:
                bad_total.append((n, round(dt, 1), bad[:2]))
    return bad_total


def main():
    tag = sys.argv[1]
    tl, scenes = load_tl(tag)
    total = tl["total"]
    full = "--full" in sys.argv

    if not full:
        bad = check_all(tag, scenes, total, S.scenes(tag))
        if bad:
            print("!! НАЛОЖЕНИЯ:")
            for b in bad:
                print("  ", b)
        else:
            print("наложений нет ✔")
        os.makedirs("/tmp/rp2", exist_ok=True)
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
                times += [st + 0.6, st + 2.2, st + 4.5]
        for t in times:
            if t >= total:
                continue
            frame(tag, scenes, total, t).save("/tmp/rp2/%s_%05.2f.jpg" % (tag, t), quality=93)
            print("saved", round(t, 2), flush=True)
        return

    audio = os.path.join(BASE, "master_%s.m4a" % tag)
    out = os.path.join(BASE, "v_okope_ceny_%s_9x16.mp4" % tag)
    n = int(round(total * L.FPS))
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(L.FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-x264-params", "keyint=48:min-keyint=24:scenecut=0",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-t", "%.2f" % total, out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(tag, scenes, total, i / float(L.FPS)).tobytes())
        if i % 200 == 0:
            print("%d/%d %.2ffps" % (i, n, i / max(time.time() - t0, .01)), flush=True)
    p.stdin.close()
    print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
    print("size", os.path.getsize(out) if os.path.exists(out) else "MISSING", flush=True)


if __name__ == "__main__":
    main()
