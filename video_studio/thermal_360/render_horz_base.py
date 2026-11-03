# -*- coding: utf-8 -*-
"""«Тепловизор 360°» — горизонталь 16:9, 1920×1080, 03:52.

52 кадра из timeline.json. Источники:
  • фото заказчика (assets/*.jpg) — метка «ФОТО»;
  • видео заказчика (assets/video → assets/vidfr) — метка «ВИДЕО ЗАКАЗЧИКА»;
  • схемы и типографика — метка «МАКЕТ» / «ТИТР».
Цен нет. Тексты — из factcheck-нутого timeline.json.
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
BASE = "/home/user/-/video_studio/thermal_360"
A = os.path.join(BASE, "assets")
VD = os.path.join(A, "vidfr")
FD = "/home/user/-/video_studio/toolkit/fonts"
TL = json.load(open(os.path.join(BASE, "timeline.json"), encoding="utf-8"))
SHOTS = TL["shots"]
TOTAL = TL["total"]
BPM, BEAT = 120.0, 0.5

BG = (9, 10, 13)
ORG = (255, 140, 42)
ICE = (94, 208, 255)
TXT = (243, 244, 246)
DIM = (146, 152, 162)
RED = (255, 66, 52)
RUSSO, DAYS, MONO = "RussoOne-Regular.ttf", "DaysOne-Regular.ttf", "JetBrainsMono-VF.ttf"


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), s)


def cl(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


c01 = cl


def eo(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def eb(x):
    x = c01(x)
    c = 2.2
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────── источники
_KEYS, _VID = {}, {}


def keyed(name, w, bg_lum=190.0, floor=142.0):
    k = (name, w)
    if k in _KEYS:
        return _KEYS[k]
    src = Image.open(os.path.join(A, name)).convert("RGB")
    st = w / src.width
    src = src.resize((w, max(1, int(src.height * st))), Image.LANCZOS)
    a = np.asarray(src).astype(np.float32)
    lum = a.mean(2)
    al = np.clip((bg_lum - lum) / max(1.0, bg_lum - floor), 0, 1) ** 0.85
    al = np.asarray(Image.fromarray((al * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
    body = np.clip((a - 30) * 1.15 + 24, 0, 255)
    shadow = (al < 0.97) & (lum > 95)
    body[shadow] = np.array([18, 20, 24], np.float32)
    res = Image.fromarray(body.astype(np.uint8)).convert("RGBA")
    alpha = np.where(shadow, al * 0.55, al)
    res.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)))
    bb = res.getchannel("A").point(lambda v: 255 if v > 14 else 0).getbbox()
    res = res.crop(bb) if bb else res
    del a, lum, al, body, shadow
    _KEYS[k] = res
    return res


def key_img(src, w, bg_lum=190.0, floor=142.0):
    """Тот же luma-key, но для произвольного кропа (без файла)."""
    src = src.convert("RGB")
    st = w / src.width
    src = src.resize((w, max(1, int(src.height * st))), Image.LANCZOS)
    a = np.asarray(src).astype(np.float32)
    lum = a.mean(2)
    al = np.clip((bg_lum - lum) / max(1.0, bg_lum - floor), 0, 1) ** 0.85
    al = np.asarray(Image.fromarray((al * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    body = np.clip((a - 30) * 1.18 + 26, 0, 255)
    shadow = (al < 0.97) & (lum > 95)
    body[shadow] = np.array([16, 18, 22], np.float32)
    res = Image.fromarray(body.astype(np.uint8)).convert("RGBA")
    alpha = np.where(shadow, al * 0.5, al)
    res.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)))
    bb = res.getchannel("A").point(lambda v: 255 if v > 14 else 0).getbbox()
    return res.crop(bb) if bb else res


def photo_on(cv, name, cx, cy, h=None, w=None, alpha=255, glow_a=44, glow=ORG, shadow=True):
    if alpha <= 3:
        return None
    im = keyed(name, 1500)
    if h:
        st = h / im.height
    else:
        st = w / im.width
    im = im.resize((max(2, int(im.width * st)), max(2, int(im.height * st))), Image.LANCZOS)
    if alpha < 255:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    if shadow:
        sh = Image.new("RGBA", (im.width + 120, im.height + 120), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", im.size, (0, 0, 0, 200)), (60, 66), im)
        cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)),
                           (int(cx - sh.width / 2), int(cy - sh.height / 2) + 22))
    if glow_a:
        gl = Image.new("RGBA", (im.width + 200, im.height + 200), (0, 0, 0, 0))
        gl.paste(Image.new("RGBA", im.size, ac(glow, glow_a)), (100, 100), im)
        cv.alpha_composite(gl.filter(ImageFilter.GaussianBlur(52)),
                           (int(cx - gl.width / 2), int(cy - gl.height / 2)))
    pos = (int(cx - im.width / 2), int(cy - im.height / 2))
    cv.alpha_composite(im, pos)
    return (pos[0], pos[1], im.width, im.height)


def vcount(sub):
    n = 0
    while os.path.exists(os.path.join(VD, sub, "%03d.jpg" % (n + 1))):
        n += 1
    return n


def vframe(sub, i):
    n = vcount(sub)
    i = max(1, min(n, int(i)))
    k = (sub, i)
    if k not in _VID:
        _VID.clear()
        _VID[k] = Image.open(os.path.join(VD, sub, "%03d.jpg" % i)).convert("RGB")
    return _VID[k]


def vframe_t(sub, t, t0):
    return vframe(sub, round((t - t0) * FPS) + 1)


def cover_im(im, w, h, zoom=1.0, ox=0.0, oy=0.0):
    cs = max(w / im.width, h / im.height) * zoom
    rw, rh = min(w / cs, im.width), min(h / cs, im.height)
    cx = im.width / 2 + cl(ox, -1, 1) * max(0, (im.width - rw) / 2)
    cy = im.height / 2 + cl(oy, -1, 1) * max(0, (im.height - rh) / 2)
    x0 = int(cl(cx - rw / 2, 0, im.width - rw))
    y0 = int(cl(cy - rh / 2, 0, im.height - rh))
    return im.crop((x0, y0, x0 + int(rw), y0 + int(rh))).resize((w, h), Image.LANCZOS)


def grade(im, dark=0.62, con=1.14, sat=0.9, tint=(255, 150, 70), amt=0.05):
    a = np.asarray(im).astype(np.float32)
    a = (a - 128) * con + 128
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * sat
    a *= dark
    a = a * (1 - amt) + np.array(tint, np.float32) * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def crop_photo(name, box=None):
    im = Image.open(os.path.join(A, name)).convert("RGB")
    if box:
        l, t, r, b = box
        im = im.crop((int(im.width * l), int(im.height * t), int(im.width * r), int(im.height * b)))
    return im


# ─────────────────────────── слои
SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 18))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(90):
    k = i / 90
    ins = int(-260 + k * 520)
    _v.ellipse([ins, ins * 0.62, W - ins, H - ins * 0.62], outline=(0, 0, 0, int(3 + k * 2)), width=7)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(30))

_r = np.random.default_rng(3)
GRAIN = []
for _ in range(4):
    n = _r.integers(0, 26, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 15))))


def text_lay(s, fn, size, col):
    f = F(fn, size)
    lay = Image.new("RGBA", (max(2, int(f.getlength(s)) + 30), int(size * 1.6)), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((14, 6), s, font=f, fill=col)
    return lay


def put(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", maxw=None, slide=26):
    if p <= 0:
        return
    lay = text_lay(s, fn, size, col)
    lim = maxw or (W - x - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    al = eo(min(1, p * 1.8))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    dx = int(slide * (1 - eo(min(1, p * 1.3))))
    px = int(x - lay.width / 2) if anchor == "ma" else int(x)
    py = int(y - lay.height / 2) if anchor == "mm" else int(y)
    cv.alpha_composite(lay, (px + dx, py))


def chip(d, x, y, s, col=ORG, size=27, h=58, alpha=255, solid=False):
    f = F(MONO, size)
    w = f.getlength(s)
    d.rectangle([x, y, x + w + 40, y + h],
                fill=ac(col if solid else (10, 11, 14), alpha * (0.94 if solid else 0.85)),
                outline=ac(col, alpha * 0.85))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size) / 2 - 5), s, font=f,
           fill=ac((10, 11, 14) if solid else col, alpha))
    return w + 40


def tag(d, s, x, y, col=DIM, alpha=220):
    if alpha <= 3:
        return
    f = F(MONO, 22)
    w = f.getlength(s)
    d.rectangle([x, y, x + w + 34, y + 38], fill=ac((6, 7, 9), 200 * alpha / 255),
                outline=ac(col, 140 * alpha / 255))
    d.text((x + 17, y + 8), s, font=f, fill=ac(col, alpha))


def hud(d, t, block_name):
    d.rectangle([0, 0, W, 62], fill=(6, 7, 9, 236))
    d.rectangle([0, 0, W, 4], fill=ac(ORG, 255))
    d.text((86, 12), "«В ОКОПЕ»", font=F(RUSSO, 30), fill=ac(TXT, 255))
    d.text((320, 20), "ТЕПЛОВИЗОР 360°  //  " + block_name.upper(), font=F(MONO, 20), fill=ac(DIM, 225))
    d.text((W - 96, 18), "%d:%02d" % (int(t) // 60, int(t) % 60), font=F(MONO, 24), fill=ac(DIM, 200), anchor="ra")
    b = 0.5 + 0.5 * math.sin(t * 7)
    d.ellipse([W - 66, 22, W - 46, 42], fill=ac(RED, int(100 + 130 * b)))
    p = cl(t / TOTAL)
    d.rectangle([0, 62, W, 67], fill=(16, 18, 22, 240))
    d.rectangle([0, 62, int(W * p), 67], fill=ac(ORG, 240))
    d.rectangle([0, H - 56, W, H], fill=(5, 6, 8, 246))
    d.rectangle([0, H - 59, W, H - 55], fill=ac(ORG, 85))
    d.text((86, H - 40), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 22), fill=ac(ORG, 235))
    d.text((W - 96, H - 40), "ТЕПЛОВИЗОР 360° · ПОВОРОТНЫЙ БЛОК", font=F(MONO, 20), fill=ac(DIM, 210), anchor="ra")


def bg_set(cv, t, hy=None):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 14), 255)))
    d = ImageDraw.Draw(cv)
    hy = hy if hy is not None else 760
    for i in range(-6, 22):
        x = i * 150
        d.line([(W / 2 + (x - W / 2) * 0.22, hy), (x, H)], fill=ac(ICE, 16), width=2)
    for i in range(7):
        y = hy + int((H - hy) * (i / 6.0) ** 2.0)
        d.line([(0, y), (W, y)], fill=ac(ICE, 14), width=2)


def card(cv, im, cx, cy, w, h, accent=ICE, alpha=255, label=""):
    """Медиа-карточка: рамка + тень (для видео и обрезанных фото)."""
    if alpha <= 3:
        return
    im = im.resize((w, h), Image.LANCZOS).convert("RGBA")
    if alpha < 255:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    plate = Image.new("RGBA", (w + 16, h + 16), (8, 9, 12, 250))
    plate.paste(im, (8, 8))
    dd = ImageDraw.Draw(plate)
    dd.rectangle([0, 0, plate.width - 1, plate.height - 1], outline=ac(accent, 210), width=3)
    for (x, y, sx, sy) in ((4, 4, 1, 1), (plate.width - 4, 4, -1, 1),
                           (4, plate.height - 4, 1, -1), (plate.width - 4, plate.height - 4, -1, -1)):
        dd.line([(x, y), (x + sx * 40, y)], fill=ac(accent, 255), width=5)
        dd.line([(x, y), (x, y + sy * 40)], fill=ac(accent, 255), width=5)
    if alpha < 255:
        plate.putalpha(plate.getchannel("A").point(lambda v: int(v * alpha / 255)))
    sh = Image.new("RGBA", (plate.width + 90, plate.height + 90), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", plate.size, (0, 0, 0, 190)), (45, 52), plate)
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)),
                       (int(cx - sh.width / 2), int(cy - sh.height / 2) + 14))
    cv.alpha_composite(plate, (int(cx - plate.width / 2), int(cy - plate.height / 2)))
    if label:
        d2 = ImageDraw.Draw(cv)
        d2.text((int(cx), int(cy + plate.height / 2 + 16)), label, font=F(MONO, 22),
                fill=ac(accent, alpha), anchor="ma")


def arcf(d, cx, cy, r, a0, a1, col, width=6, alpha=255, dash=26, gap=18):
    span = a1 - a0
    n = max(2, int(abs(span) / (360.0 / max(8, (2 * math.pi * r) / (dash + gap)))))
    for i in range(n):
        s0 = a0 + span * i / n
        s1 = s0 + span / n * (dash / (dash + gap))
        d.arc([cx - r, cy - r, cx + r, cy + r], start=-s1, end=-s0, fill=ac(col, alpha), width=width)


def beatshake(t, amp=4):
    b = (t / BEAT) % 1.0
    k = math.exp(-b * 9) * amp
    rnd = random.Random(int(t * 100))
    return (rnd.uniform(-1, 1) * k, rnd.uniform(-1, 1) * k)
