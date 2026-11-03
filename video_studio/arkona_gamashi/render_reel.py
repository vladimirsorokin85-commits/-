# -*- coding: utf-8 -*-
"""«Гамаши тактические АРКОНА» — вертикальный Reels 9:16 (1080×1920, 47,5 с).

Источники: 5 фото заказчика (метка «ФОТО»), схемы и таблица размеров («МАКЕТ»).
Никаких цен. Только факты из facts.md.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = "/home/user/-/video_studio/arkona_gamashi"
A = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"
TOTAL = 58.50
BPM, BEAT = 120.0, 0.5

SCENES = [
    ("hook", 0.00), ("why", 7.00), ("fabric", 12.50), ("fit", 20.00),
    ("fasten", 25.50), ("cable", 29.50), ("kit", 34.50), ("sizes", 41.00),
    ("outro", 51.50),
]

BG = (9, 10, 12)
ORG = (255, 140, 42)
OLV = (176, 202, 112)
ICE = (94, 208, 255)
TXT = (244, 245, 246)
DIM = (148, 154, 160)
RED = (255, 72, 56)

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
    c = 2.3
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────── источники
_CACHE = {}


def photo(name):
    if name not in _CACHE:
        _CACHE[name] = Image.open(os.path.join(A, name)).convert("RGB")
    return _CACHE[name]


def cover(name, zoom=1.0, ox=0.0, oy=0.0, size=(W, H)):
    im = photo(name)
    w, h = size
    cs = max(w / im.width, h / im.height) * zoom
    rw, rh = min(w / cs, im.width), min(h / cs, im.height)
    cx = im.width / 2 + cl(ox, -1, 1) * max(0, (im.width - rw) / 2)
    cy = im.height / 2 + cl(oy, -1, 1) * max(0, (im.height - rh) / 2)
    x0 = int(cl(cx - rw / 2, 0, im.width - rw))
    y0 = int(cl(cy - rh / 2, 0, im.height - rh))
    return im.crop((x0, y0, x0 + int(rw), y0 + int(rh))).resize((w, h), Image.LANCZOS)


def grade(im, dark=0.55, con=1.16, sat=0.92, tint=(255, 170, 90), amt=0.05):
    a = np.asarray(im).astype(np.float32)
    a = (a - 128) * con + 128
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * sat
    a *= dark
    a = a * (1 - amt) + np.array(tint, np.float32) * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def _spot_mask(w, h, cx, cy, r0=0.30, r1=0.85, power=1.5):
    y, x = np.mgrid[0:h, 0:w]
    dx = (x - cx * w) / w
    dy = (y - cy * h) / h
    d = np.sqrt(dx * dx + dy * dy) / 0.62
    k = np.clip((d - r0) / max(1e-3, r1 - r0), 0, 1) ** power
    return Image.fromarray((k * 235).astype(np.uint8))


def full_photo(cv, name, l, zoom=1.03, ox=0.0, oy=0.0, dark=0.42, spot=0.55, sat=0.9):
    im = grade(cover(name, zoom, ox, oy), dark, 1.18, sat, (255, 168, 88), 0.06)
    cv.alpha_composite(im)
    m = _spot_mask(W, H, 0.5, spot)
    cv.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 4), Image.new("L", (W, H), 5),
                                            Image.new("L", (W, H), 8), m)))
    # нижний скрим под текст
    sc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sc)
    for y in range(0, H, 3):
        k = y / H
        ds.line([(0, y), (W, y)], fill=(5, 6, 9, int(10 + 150 * cl((k - .55) / .45) ** 1.4)))


def scr(cv, y0, y1, a0=0, a1=200, col=(5, 6, 9)):
    sc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sc)
    for y in range(y0, y1, 3):
        k = (y - y0) / max(1, (y1 - y0))
        ds.line([(0, y), (W, y)], fill=ac(col, a0 + (a1 - a0) * k))
    cv.alpha_composite(sc)


def fit_photo(cv, name, cy=980, w=1000, dark=0.34, spot=0.44, sat=0.85, glow=OLV):
    """Фото целиком (без кропа) на затемнённом фоне — для горизонтальных кадров."""
    im = photo(name)
    st = w / im.width
    ph = im.resize((w, max(2, int(im.height * st))), Image.LANCZOS)
    ph = grade(ph, 0.94, 1.08, sat, (255, 168, 88), 0.03)
    bg = grade(cover(name, 1.5, 0, 0), 0.22, 1.0, 0.45, (255, 160, 80), 0.05)
    bg = bg.filter(ImageFilter.GaussianBlur(26))
    cv.alpha_composite(bg)
    m = _spot_mask(W, H, 0.5, 0.5, 0.20, 0.95)
    cv.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 4), Image.new("L", (W, H), 5),
                                            Image.new("L", (W, H), 8), m)))
    sh = Image.new("RGBA", (ph.width + 100, ph.height + 100), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", ph.size, (0, 0, 0, 205)), (50, 56), ph)
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)),
                       (int(W / 2 - sh.width / 2), int(cy - sh.height / 2) + 16))
    fr = Image.new("RGBA", (ph.width + 12, ph.height + 12), (8, 9, 12, 250))
    fr.paste(ph, (6, 6))
    d = ImageDraw.Draw(fr)
    d.rectangle([0, 0, fr.width - 1, fr.height - 1], outline=ac(glow, 205), width=3)
    cv.alpha_composite(fr, (int(W / 2 - fr.width / 2), int(cy - fr.height / 2)))


def full_photo2(cv, a, b, k, za=1.05, zb=1.06, dark=0.34, spot=0.44, sat=0.8):
    """Плавный переход между двумя фото (k=0 → a, k=1 → b)."""
    ia = grade(cover(a, za, 0, 0), dark, 1.18, sat, (255, 168, 88), 0.06)
    ib = grade(cover(b, zb, 0, 0), dark, 1.18, sat, (255, 168, 88), 0.06)
    im = Image.blend(ia.convert("RGB"), ib.convert("RGB"), cl(k, 0, 1)).convert("RGBA")
    cv.alpha_composite(im)
    m = _spot_mask(W, H, 0.5, spot)
    cv.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 4), Image.new("L", (W, H), 5),
                                            Image.new("L", (W, H), 8), m)))


def card(cv, name, box, cx, cy, w, h, accent=ORG, alpha=255):
    """Кроп фото в рамке-карточке (для деталей)."""
    if alpha <= 3:
        return None
    im = photo(name)
    l, t, r, b = box
    c = im.crop((int(im.width * l), int(im.height * t), int(im.width * r), int(im.height * b)))
    c = grade(c, 0.72, 1.14, 0.86, (255, 168, 88), 0.05).convert("RGB").resize((w, h), Image.LANCZOS)
    plate = Image.new("RGBA", (w + 16, h + 16), (8, 9, 12, 250))
    plate.paste(c.convert("RGBA"), (8, 8))
    dd = ImageDraw.Draw(plate)
    dd.rectangle([0, 0, plate.width - 1, plate.height - 1], outline=ac(accent, 215), width=3)
    for (x, y, sx, sy) in ((5, 5, 1, 1), (plate.width - 5, 5, -1, 1),
                           (5, plate.height - 5, 1, -1), (plate.width - 5, plate.height - 5, -1, -1)):
        dd.line([(x, y), (x + sx * 42, y)], fill=ac(accent, 255), width=5)
        dd.line([(x, y), (x, y + sy * 42)], fill=ac(accent, 255), width=5)
    if alpha < 255:
        plate.putalpha(plate.getchannel("A").point(lambda v: int(v * alpha / 255)))
    sh = Image.new("RGBA", (plate.width + 90, plate.height + 90), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", plate.size, (0, 0, 0, 195)), (45, 54), plate)
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)),
                       (int(cx - sh.width / 2), int(cy - sh.height / 2) + 14))
    cv.alpha_composite(plate, (int(cx - plate.width / 2), int(cy - plate.height / 2)))
    return (int(cx - plate.width / 2) + 8, int(cy - plate.height / 2) + 8, w, h)


# ─────────────────────── слои
SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 20))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(120):
    k = i / 120
    ins = int(-190 + k * 420)
    _v.ellipse([ins, ins * 1.05, W - ins, H - ins * 1.05], outline=(0, 0, 0, int(3 + k * 2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(28))

_r = np.random.default_rng(17)
GRAIN = []
for _ in range(4):
    n = _r.integers(0, 26, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 16))))


# ─────────────────────── текст
def text_lay(s, fn, size, col):
    f = F(fn, size)
    lay = Image.new("RGBA", (max(2, int(f.getlength(s)) + 28), int(size * 1.55)), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((14, 4), s, font=f, fill=col)
    return lay


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", trail=36, maxw=None, chroma=True):
    if p <= 0:
        return
    lay = text_lay(s, fn, size, col)
    lim = maxw or (W - 88)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.36 * (1 - eb(p))
    lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.2))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor == "ma" else int(x)
    py = int(y - lay.height / 2) if anchor == "mm" else int(y)
    if chroma and p < 0.45:
        ca = int(70 * (1 - p / 0.45))
        for off, c in ((-5, (255, 70, 90)), (5, (70, 200, 255))):
            t = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            t.paste(Image.new("RGBA", lay.size, ac(c, ca)), (0, 0), lay)
            cv.alpha_composite(t, (px + off, py))
    if trail:
        for i in range(4, 0, -1):
            kk = 1 - eo(p)
            ox = int(-trail * i / 4 * kk)
            if not ox:
                continue
            t = lay.copy()
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.13 * (5 - i) / 4 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=ORG, size=26, h=56, alpha=255, solid=False):
    f = F(MONO, size)
    w = f.getlength(s)
    d.rectangle([x, y, x + w + 40, y + h],
                fill=ac(col if solid else (10, 11, 14), alpha * (0.94 if solid else 0.86)),
                outline=ac(col, alpha * 0.85))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size) / 2 - 5), s, font=f, fill=ac((10, 11, 14) if solid else col, alpha))
    return w + 40


def tag(cv, s, y=1650, col=DIM, alpha=230):
    if alpha <= 3:
        return
    f = F(MONO, 22)
    w = f.getlength(s)
    bx = (W - int(w + 34)) // 2
    d = ImageDraw.Draw(cv)
    d.rectangle([bx, y, bx + w + 34, y + 38], fill=ac((6, 7, 9), 208 * alpha / 255),
                outline=ac(col, 150 * alpha / 255))
    d.text((bx + 17, y + 8), s, font=f, fill=ac(col, alpha))


def title_band(cv, y0, y1, blur=16, dark=0.80, feather=90):
    """Размывает и затемняет полосу фона — под ней текст читается всегда."""
    band = cv.crop((0, max(0, y0 - feather), W, min(H, y1 + feather)))
    band = band.filter(ImageFilter.GaussianBlur(blur))
    ov = Image.new("RGBA", band.size, (6, 7, 10, int(255 * dark)))
    band = Image.alpha_composite(band, ov)
    mask = Image.new("L", band.size, 0)
    dm = ImageDraw.Draw(mask)
    h = band.height
    for y in range(h):
        k = 1.0
        if y < feather:
            k = y / feather
        elif y > h - feather:
            k = max(0.0, (h - y) / feather)
        dm.line([(0, y), (band.width, y)], fill=int(255 * k * k))
    cv.paste(band, (0, max(0, y0 - feather)), mask)


def topbar(cv, y0, y1):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for y in range(y0, y1):
        k = (y - y0) / max(1, (y1 - y0))
        a = int(238 - 150 * k)
        dl.line([(0, y), (W, y)], fill=(7, 8, 11, a))
    cv.alpha_composite(lay)


def hud(d, t):
    d.rectangle([0, 0, W, 108], fill=(6, 7, 9, 234))
    d.rectangle([0, 0, W, 4], fill=ac(OLV, 255))
    d.text((42, 26), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=ac(TXT, 255))
    d.text((42, 76), "ГАМАШИ «АРКОНА» // МУЛЬТИКАМ", font=F(MONO, 20), fill=ac(DIM, 230))
    b = 0.5 + 0.5 * math.sin(t * 7.5)
    d.ellipse([W - 68, 64, W - 46, 86], fill=ac(RED, int(105 + 130 * b)))
    d.text((W - 84, 62), "REC", font=F(MONO, 20), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / TOTAL)
    d.rectangle([0, 108, W, 114], fill=(16, 18, 22, 245))
    d.rectangle([0, 108, int(W * p), 114], fill=ac(OLV, 245))
    d.rectangle([0, H - 122, W, H], fill=(5, 6, 8, 246))
    d.rectangle([0, H - 125, W, H - 121], fill=ac(OLV, 95))
    d.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 25),
           fill=ac(ORG, 240), anchor="ma")
    d.text((W // 2, H - 52), "ГАМАШИ «АРКОНА» · КОМПЛЕКТ 2 ШТ", font=F(RUSSO, 19),
           fill=ac(DIM, 210), anchor="ma")


def beatshake(t, amp=4):
    b = (t / BEAT) % 1.0
    k = math.exp(-b * 9) * amp
    rnd = random.Random(int(t * 100))
    return (rnd.uniform(-1, 1) * k, rnd.uniform(-1, 1) * k)


def punch(im, t, cuts):
    for c in cuts:
        dd = t - c
        if 0 <= dd < 0.20:
            k = 1 - dd / 0.20
            z = 1 + 0.05 * k
            w, h = int(W / z), int(H / z)
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize((W, H), Image.BILINEAR)
    return im


def gridlines(d, t, alpha=30, hz=1260, col=OLV):
    for i in range(-8, 24):
        x = i * 120
        d.line([(W / 2 + (x - W / 2) * 0.18, hz), (x, H)], fill=ac(col, alpha * 0.5), width=2)
    for i in range(8):
        y = hz + int((H - hz) * (i / 7.0) ** 2)
        d.line([(0, y), (W, y)], fill=ac(col, alpha * 0.45), width=2)


def callout(d, x, y, txt, p, col=ORG, side=1):
    """Точка на детали + подпись рядом."""
    if p <= 0:
        return
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=ac(col, int(245 * p)))
    d.ellipse([x - 19, y - 19, x + 19, y + 19], outline=ac(col, int(130 * p)), width=2)
    f = F(MONO, 25)
    tw = f.getlength(txt)
    need = tw + 30
    if side > 0 and x + 40 + need > W - 40:
        side = -1
    elif side < 0 and x - 40 - need < 40:
        side = 1
    bx = x + 40 if side > 0 else x - 40 - need
    bx = int(cl(bx, 34, W - need - 34))
    d.rectangle([bx, y - 20, bx + tw + 30, y + 20], fill=ac((6, 7, 9), int(215 * p)),
                outline=ac(col, int(150 * p)))
    d.text((bx + 15, y - 12), txt, font=f, fill=ac(col, int(245 * p)))
    d.line([(x + side * 20, y), (bx if side > 0 else bx + tw + 30, y)], fill=ac(col, int(180 * p)), width=3)


# ─────────────────────── сцены
def s_hook(cv, d, t, l):
    if l < 3.6:
        full_photo(cv, "on_boot_side.jpg", l, 1.04 + 0.10 * eo(l / 3.6), ox=0.02, dark=0.46, spot=0.44, sat=0.95)
    else:
        cv.alpha_composite(Image.new("RGBA", (W, H), ac((9, 10, 12), 255)))
        k = eo(c01((l - 3.6) / .5))
        fit_photo(cv, "pair_flat.jpg", cy=490 - int(24 * k), w=990, sat=1.0, glow=OLV)
    title_band(cv, 940, 1560, blur=18, dark=0.78)
    slam(cv, "ГАМАШИ", RUSSO, 152, 540, 940, ac(TXT, 255), c01((l - .06) / .30), "ma", 46, maxw=980)
    slam(cv, "«АРКОНА»", DAYS, 118, 540, 1108, ac(OLV, 255), c01((l - .34) / .30), "ma", 38, maxw=980)
    if l > .9:
        p = c01((l - .9) / .35)
        w1 = chip(d, 96, 1246, "КОМПЛЕКТ 2 ШТ", ORG, 27, 58, int(255 * p), solid=True)
        chip(d, 96 + w1 + 16, 1246, "МУЛЬТИКАМ", OLV, 27, 58, int(255 * p))
    if 1.5 < l < 3.9:
        p = c01((l - 1.5) / .35) * (1 - c01((l - 3.6) / .3))
        slam(cv, "КОРДУРА 1000D · ИК-РЕМИССИЯ", MONO, 30, 540, 1410, ac(TXT, 240 * p), p, "ma", 20)
    if l > 4.1:
        p = c01((l - 4.1) / .40)
        slam(cv, "ТРОСИК 35 СМ · 4 КРЕПЛЕНИЯ", MONO, 30, 540, 1330, ac(TXT, 240 * p), p, "ma", 18)
    tag(cv, "ФОТО", 1520, ORG, int(235 * c01((l - .5) / .5)))


def s_why(cv, d, t, l):
    fit_photo(cv, "kit_flat.jpg", cy=560, w=640, sat=0.85)
    scr(cv, 900, 1600, 0, 232)
    slam(cv, "ОДЕЖДА И ОБУВЬ", RUSSO, 86, 540, 1000, ac(TXT, 255), c01((l - .05) / .30), "ma", 32, maxw=940)
    slam(cv, "ЗАЩИЩАЮТ", DAYS, 116, 540, 1130, ac(OLV, 255), c01((l - .35) / .30), "ma", 40, maxw=930)
    if l > .9:
        p = c01((l - .9) / .40)
        x = 150
        for i, s in enumerate(("ГРЯЗЬ", "РОСА", "СНЕГ")):
            w = chip(d, x, 1268, s, ORG if i == 0 else OLV, 28, 58, int(255 * p))
            x += w + 16
    if l > 1.9:
        p = c01((l - 1.9) / .40)
        d.rectangle([150, 1368, 158, 1428], fill=ac(OLV, int(220 * p)))
        slam(cv, "ОТ ПОВРЕЖДЕНИЙ, РОСЫ И СНЕГА", MONO, 28, 150, 1378, ac(TXT, 240 * p), p, "lt", 16)
    tag(cv, "ФОТО", 1520, ORG, int(235 * c01((l - .5) / .5)))


def s_fabric(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 13), 255)))
    ui = ImageDraw.Draw(cv)
    gridlines(ui, t, 22, 1240)
    sh = beatshake(t)
    box = card(cv, "boot_close.jpg", (0.00, 0.03, 0.80, 0.50), 540 + sh[0], 840 + sh[1], 960, 600, OLV)
    topbar(cv, 214, 520)
    slam(cv, "ТКАНЬ", RUSSO, 132, 540, 262, ac(TXT, 255), c01((l - .05) / .28), "ma", 40, maxw=900)
    if l > .45:
        p = c01((l - .45) / .30)
        slam(cv, "КОРДУРА 1000D", DAYS, 96, 540, 412, ac(OLV, 255 * p), p, "ma", 30, maxw=900)
    if l > 1.1 and box:
        callout(d, box[0] + 330, box[1] + 210, "ПЛОТНОЕ ПЛЕТЕНИЕ", c01((l - 1.1) / .4), OLV, 1)
    if l > 1.9:
        p = c01((l - 1.9) / .40)
        chip(d, 190, 1300, "ПЛОТНАЯ ТКАНЬ", OLV, 30, 62, int(255 * p))
        chip(d, 540, 1300, "ИК-РЕМИССИЯ", ICE, 30, 62, int(255 * p))
        slam(cv, "ТКАНЬ С ИК-РЕМИССИЕЙ — КАК В КАРТОЧКЕ ТОВАРА", MONO, 24, 540, 1412, ac(DIM, 228 * p), p, "ma", 14)
    tag(cv, "ФОТО", 1540, OLV, int(235 * c01((l - .5) / .5)))


def s_fit(cv, d, t, l):
    full_photo(cv, "on_boot_side.jpg", l, 1.10 + 0.06 * eo(l / 5), ox=-0.04, oy=0.02, dark=0.34, spot=0.40)
    scr(cv, 250, 800, 210, 0)
    scr(cv, 1150, 1600, 0, 232)
    # мерная линия по высоте
    p = eo(c01((l - .35) / .8))
    x = 940
    y0, y1 = 620, 620 + int(760 * p)
    d.line([(x, y0), (x, y1)], fill=ac(ORG, 225), width=4)
    for yy in (y0, y1):
        d.line([(x - 18, yy), (x + 18, yy)], fill=ac(ORG, 235), width=5)
    if p > .96:
        d.text((x + 26, (y0 + y1) / 2 - 16), "40 / 45 СМ", font=F(MONO, 26), fill=ac(ORG, 240), anchor="lm")
    slam(cv, "ПО НОГЕ", RUSSO, 124, 540, 300, ac(TXT, 255), c01((l - .05) / .28), "ma", 40, maxw=900)
    if l > .5:
        p2 = c01((l - .5) / .35)
        slam(cv, "ОБЛЕГАЮТ ГОЛЕНЬ И ОБУВЬ", MONO, 30, 540, 432, ac(OLV, 245 * p2), p2, "ma", 20)
    if l > 1.2:
        p3 = c01((l - 1.2) / .40)
        chip(d, 96, 1250, "РЕГУЛИРОВКА ПО ОБЪЁМУ", ORG, 28, 60, int(255 * p3), solid=True)
        chip(d, 96, 1326, "M И L", OLV, 28, 60, int(255 * p3))
    tag(cv, "ФОТО + МАКЕТ", 1520, ORG, int(235 * c01((l - .5) / .5)))


def s_fasten(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 13), 255)))
    ui = ImageDraw.Draw(cv)
    gridlines(ui, t, 20, 1250)
    sh = beatshake(t)
    box = card(cv, "top_buckle.jpg", (0.05, 0.10, 0.95, 0.62), 540 + sh[0], 900 + sh[1], 980, 660, ORG)
    topbar(cv, 214, 500)
    slam(cv, "ФИКСАЦИЯ", RUSSO, 118, 540, 256, ac(TXT, 255), c01((l - .05) / .28), "ma", 38, maxw=950)
    if l > .45:
        p = c01((l - .45) / .30)
        slam(cv, "ВЕЛКРО + КНОПКА", DAYS, 84, 540, 404, ac(ORG, 255 * p), p, "ma", 28, maxw=940)
    if l > 1.1 and box:
        callout(d, box[0] + 500, box[1] + 130, "СТЯЖКА", c01((l - 1.1) / .4), ICE, 1)
    if l > 1.7:
        p = c01((l - 1.7) / .40)
        w1 = chip(d, 300, 1290, "ВЕЛКРО", ORG, 27, 58, int(255 * p), solid=True)
        chip(d, 300 + w1 + 16, 1290, "КНОПКА-ДУБЛЬ", ICE, 27, 58, int(255 * p))
    if l > 2.2:
        p = c01((l - 2.2) / .40)
        slam(cv, "ЗАСТЁГИВАЕТСЯ ПОВЕРХ ГОЛЕНИ", MONO, 28, 540, 1400, ac(DIM, 235 * p), p, "ma", 18)
    tag(cv, "ФОТО", 1540, ORG, int(235 * c01((l - .5) / .5)))


def s_cable(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((9, 11, 14), 255)))
    ui = ImageDraw.Draw(cv)
    gridlines(ui, t, 24, 1200, ICE)
    sh = beatshake(t)
    box = card(cv, "boot_close.jpg", (0.14, 0.34, 0.98, 0.84), 540 + sh[0], 890 + sh[1], 980, 640, ICE)
    topbar(cv, 214, 500)
    slam(cv, "НА ОБУВИ", RUSSO, 118, 540, 256, ac(TXT, 255), c01((l - .05) / .28), "ma", 38, maxw=950)
    if l > .45:
        p = c01((l - .45) / .30)
        slam(cv, "СТАЛЬНОЙ ТРОСИК", DAYS, 82, 540, 404, ac(ICE, 255 * p), p, "ma", 28, maxw=940)
    if l > 1.1 and box:
        pp = c01((l - 1.1) / .45)
        callout(d, box[0] + 430, box[1] + 300, "ТРОСИК", pp, ICE, 1)
        callout(d, box[0] + 250, box[1] + 470, "КРЮЧОК · АЦЕТАЛЬ", pp, ORG, -1)
    if l > 1.9:
        p = c01((l - 1.9) / .40)
        w1 = chip(d, 210, 1290, "СТАЛЬНОЙ ТРОСИК", ICE, 27, 58, int(255 * p))
        chip(d, 210 + w1 + 16, 1290, "КРЮЧОК — АЦЕТАЛЬ", ORG, 27, 58, int(255 * p))
    if l > 2.4:
        p = c01((l - 2.4) / .40)
        slam(cv, "ДЕРЖИТ ГАМАШ НА БОТИНКЕ", MONO, 28, 540, 1400, ac(DIM, 235 * p), p, "ma", 18)
    tag(cv, "ФОТО", 1540, ICE, int(235 * c01((l - .5) / .5)))


def s_kit(cv, d, t, l):
    full_photo(cv, "kit_flat.jpg", l, 1.03 + 0.08 * eo(l / 5.5), ox=0.0, oy=-0.02, dark=0.36, spot=0.42)
    scr(cv, 250, 780, 215, 0)
    scr(cv, 1080, 1600, 0, 235)
    slam(cv, "ЧТО В КОМПЛЕКТЕ", RUSSO, 88, 540, 300, ac(TXT, 255), c01((l - .05) / .28), "ma", 34, maxw=960)
    rows = [("2 ГАМАША", ORG), ("ТРОСИК 35 СМ", ICE), ("4 КРЕПЛЕНИЯ · ПО 2 НА ГАМАШ", OLV)]
    y = 1150
    for i, (s, col) in enumerate(rows):
        p = c01((l - .55 - i * .28) / .40)
        if p <= 0:
            continue
        d.rectangle([96, y + 6, 96 + int(10 * p), y + 52], fill=ac(col, 235))
        slam(cv, s, MONO, 40, 132, y, ac(TXT, 245 * p), p, "lt", 22, maxw=880)
        y += 96
    tag(cv, "ФОТО", 1520, ORG, int(235 * c01((l - .5) / .5)))


def s_sizes(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((9, 10, 13), 255)))
    ui = ImageDraw.Draw(cv)
    gridlines(ui, t, 18, 1300, OLV)
    slam(cv, "РАЗМЕРЫ", RUSSO, 112, 540, 280, ac(TXT, 255), c01((l - .05) / .28), "ma", 38, maxw=900)
    # таблица
    cols = [("", 96), ("ВЫСОТА", 430), ("СВЕРХУ", 700), ("СНИЗУ", 900)]
    p = c01((l - .35) / .5)
    d.line([(90, 470), (990, 470)], fill=ac(OLV, int(220 * p)), width=4)
    for name, x in cols[1:]:
        d.text((x, 428), name, font=F(MONO, 22), fill=ac(DIM, int(235 * p)), anchor="la")
    rows = [("M", "40 СМ", "49 СМ", "46 СМ", ORG), ("L", "45 СМ", "51 СМ", "46 СМ", ICE)]
    for i, (sz, a, b, c, col) in enumerate(rows):
        pp = c01((l - .6 - i * .35) / .45)
        if pp <= 0:
            continue
        y = 530 + i * 200
        d.rectangle([80, y, 1000, y + 160], fill=ac((13, 15, 18), int(215 * pp)),
                    outline=ac(col, int(190 * pp)))
        d.text((150, y + 78), sz, font=F(DAYS, 74), fill=ac(col, int(255 * pp)), anchor="mm")
        for v, x in ((a, 400), (b, 660), (c, 890)):
            d.text((x, y + 78), v, font=F(MONO, 40), fill=ac(TXT, int(250 * pp)), anchor="mm")
    if l > 2.4:
        pp = c01((l - 2.4) / .4)
        slam(cv, "ОБЪЁМ — СВЕРХУ И СНИЗУ ГОЛЕНИ", MONO, 26, 540, 900, ac(DIM, 235 * pp), pp, "ma", 16)
    # шкала высот M / L
    if l > 4.6:
        p3 = eo(c01((l - 4.6) / .8))
        base_y = 1330
        for i, (sz, hh, lbl, col) in enumerate((("M", 300, "40 СМ", ORG), ("L", 340, "45 СМ", ICE))):
            x0 = 330 + i * 240
            top = base_y - int(hh * p3)
            d.rectangle([x0, top, x0 + 120, base_y], fill=ac(col, 40), outline=ac(col, 220), width=4)
            d.text((x0 + 60, top - 34), sz, font=F(DAYS, 40), fill=ac(col, 245), anchor="ma")
            d.text((x0 + 60, base_y + 36), lbl, font=F(MONO, 32), fill=ac(TXT, 242), anchor="ma")
        if p3 > .95:
            top_l = base_y - 340
            d.text((812, top_l + 6), "+5 СМ", font=F(MONO, 36), fill=ac(TXT, 240))
            d.line([(792, top_l), (792, top_l + 40)], fill=ac(TXT, 170), width=3)
            d.line([(792, top_l), (804, top_l)], fill=ac(TXT, 170), width=3)
            d.line([(792, top_l + 40), (804, top_l + 40)], fill=ac(TXT, 170), width=3)
    tag(cv, "МАКЕТ", 1580, OLV, int(235 * c01((l - .5) / .5)))


def s_outro(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((8, 9, 12), 255)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(OLV, int(34 * (1 - k) ** 2)))
    cv.alpha_composite(g)
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-600 + (l / 4.5) * (W + 1200))
    ds.polygon([(x, 0), (x + 220, 0), (x + 220 - 420, H), (x - 420, H)], fill=ac(OLV, 26))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(18)))
    slam(cv, "«В ОКОПЕ»", RUSSO, 178, 540, 740, ac(TXT, 255), c01((l - .05) / .30), "ma", 44, maxw=980)
    if l > .5:
        p = c01((l - .5) / .30)
        slam(cv, "ГАМАШИ «АРКОНА»", MONO, 40, 540, 910, ac(OLV, 250 * p), p, "ma", 22)
    if l > 1.0:
        p = c01((l - 1.0) / .30)
        d.rectangle([240, 1000, 240 + int(600 * eo(p)), 1008], fill=ac(OLV, 220))
    if l > 1.3:
        p = c01((l - 1.3) / .30)
        slam(cv, "ПОЛНЫЙ РАЗБОР", RUSSO, 54, 540, 1080, ac(TXT, 240 * p), p, "ma", 20)
        slam(cv, "t.me/vokope_ru", MONO, 34, 540, 1170, ac(ICE, 235 * p), p, "ma", 16)
        slam(cv, "vk.com/vokope_rus", MONO, 34, 540, 1226, ac(ICE, 235 * p), p, "ma", 16)
    if l > 1.9:
        p = c01((l - 1.9) / .35)
        chip(d, 366, 1310, "ПОДПИШИСЬ", ORG, 30, 62, int(255 * p), solid=True)
    if l > .3:
        q = c01((l - .3) / .5)
        d.rectangle([46, 200, W - 46, H - 250], outline=ac(OLV, int(70 * q)), width=4)


FN = {"hook": s_hook, "why": s_why, "fabric": s_fabric, "fit": s_fit, "fasten": s_fasten,
      "cable": s_cable, "kit": s_kit, "sizes": s_sizes, "outro": s_outro}


def render_frame(t):
    name, st = SCENES[0]
    for n2, s0 in SCENES:
        if t >= s0 - 1e-6:
            name, st = n2, s0
    l = t - st
    cv = Image.new("RGBA", (W, H), ac(BG, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    FN[name](cv, d, t, l)
    out = Image.alpha_composite(cv, ui)
    hud_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hud(ImageDraw.Draw(hud_l), t)
    out = Image.alpha_composite(out, hud_l)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 15) % 4])
    out = out.convert("RGB")
    out = punch(out, t, [s for _, s in SCENES[1:]])
    arr = np.asarray(out).astype(np.float32)
    beat = (t / BEAT) % 1.0
    arr *= 1.0 + 0.018 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    import sys
    os.makedirs("/tmp/ak", exist_ok=True)
    for a in sys.argv[1:]:
        tt = float(a)
        render_frame(tt).save("/tmp/ak/a_%05.2f.jpg" % tt, quality=90)
        print("saved", tt, flush=True)
