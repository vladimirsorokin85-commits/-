# -*- coding: utf-8 -*-
"""Общая графика роликов «Рюкзак 7.62»: сцена, рюкзак с тенью, текст, HUD.

Все кадры рисуются в PIL по фото заказчика (вырезанные PNG в `assets/cut`),
никаких сгенерированных изображений товара.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(BASE, "assets", "cut")
SHA = os.path.join(BASE, "assets", "shadow")
FD = "/home/user/-/video_studio/toolkit/fonts"

BG0 = (10, 11, 13)
BG1 = (17, 19, 22)
KHAKI = (198, 182, 116)      # хаки / khaki
COY = (224, 138, 56)         # койот / tan
TXT = (245, 246, 247)
DIM = (150, 156, 162)
RED = (255, 74, 58)
ICE = (110, 205, 235)

RUSSO, DAYS, MONO, COND = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf",
                           "JetBrainsMono-VF.ttf", "FiraSansExtraCondensed-Black.ttf")


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), s)


def cl(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


c01 = cl


def eo(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def eo2(x):
    x = c01(x)
    return 1 - (1 - x) ** 4


def eb(x):
    x = c01(x)
    c = 2.6
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────────── фоны
_cache = {}


def bag_img(name):
    key = "bag:" + name
    if key not in _cache:
        _cache[key] = Image.open(os.path.join(CUT, name + ".png")).convert("RGBA")
    return _cache[key]


def shadow_img(name):
    key = "sha:" + name
    if key not in _cache:
        _cache[key] = Image.open(os.path.join(SHA, name + ".png")).convert("RGBA")
    return _cache[key]


def _grad(w, h, c0, c1, vertical=True):
    a = np.zeros((h, w, 3), np.float32)
    for i in range(3):
        if vertical:
            v = np.linspace(0, 1, h)[:, None]
        else:
            v = np.linspace(0, 1, w)[None, :]
        a[:, :, i] = c0[i] + (c1[i] - c0[i]) * v
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


STAGE = _grad(W, H, (24, 26, 30), (8, 9, 11))

_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_dg = ImageDraw.Draw(_glow)
for i in range(28):
    r = 900 - i * 28
    _dg.ellipse([W / 2 - r, 620 - r * 0.72, W / 2 + r, 620 + r * 0.72],
                fill=(46, 44, 34, 5))
STAGE = Image.alpha_composite(STAGE, _glow.filter(ImageFilter.GaussianBlur(90)))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 18))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(130):
    k = i / 130
    ins = int(-210 + k * 440)
    _v.ellipse([ins, ins * 1.06, W - ins, H - ins * 1.06], outline=(0, 0, 0, int(3 + k * 2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(30))

_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 24, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 15))))


def stage(cv, t=0.0, accent=KHAKI, glow=0.0):
    cv.alpha_composite(STAGE)
    if glow > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        r = 520 + 60 * math.sin(t * 1.4)
        d.ellipse([540 - r, 900 - r * 0.8, 540 + r, 900 + r * 0.8], fill=ac(accent, int(26 * glow)))
        cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(110)))


def bag(cv, name, cx, cy, hgt, shadow=1.0, alpha=255, bloom=0.0, accent=KHAKI):
    im = bag_img(name)
    k = hgt / im.height
    w, hh = max(2, int(im.width * k)), max(2, int(hgt))
    if alpha < 255:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    im = im.resize((w, hh), Image.LANCZOS)
    if bloom > 0:
        gl = Image.new("RGBA", (w + 80, hh + 80), (0, 0, 0, 0))
        gl.paste(Image.new("RGBA", im.size, ac(accent, int(70 * bloom))), (40, 40), im)
        cv.alpha_composite(gl.filter(ImageFilter.GaussianBlur(34)), (int(cx - w / 2) - 40, int(cy - hh / 2) - 40))
    if shadow > 0:
        sh = shadow_img(name)
        ks = hgt / sh.height
        sw, shh = max(2, int(sh.width * ks)), hh
        sh = sh.resize((sw, shh), Image.LANCZOS)
        t2 = sh.copy()
        t2.putalpha(t2.getchannel("A").point(lambda v: int(v * shadow)))
        cv.alpha_composite(t2, (int(cx - sw / 2) + 16, int(cy - shh / 2) + 26))
    cv.alpha_composite(im, (int(cx - w / 2), int(cy - hh / 2)))
    return (int(cx - w / 2), int(cy - hh / 2), w, hh)


def floor(cv, cy, accent=KHAKI, alpha=90):
    """Мягкая «площадка» под рюкзаком."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(16):
        k = i / 16
        d.ellipse([120 + 30 * i, cy - 26 + 4 * i, W - 120 - 30 * i, cy + 26 - 4 * i],
                  outline=ac(accent, int(alpha * (1 - k) * 0.22)))
    cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(16)))


# ─────────────────────────────── текст
def _lay(s, fn, size, col, stroke=0, scol=None):
    f = F(fn, size)
    w = int(f.getlength(s)) + 40 + stroke * 2
    lay = Image.new("RGBA", (max(2, w), int(size * 1.5) + stroke * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 + stroke, 6 + stroke), s, font=f, fill=col,
                            stroke_width=stroke, stroke_fill=scol)
    return lay


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", trail=30, maxw=None,
         chroma=True, stroke=0, scol=None):
    if p <= 0:
        return
    lay = _lay(s, fn, size, col, stroke, scol)
    lim = maxw or (W - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.34 * (1 - eb(p))
    if abs(k - 1) > 0.01:
        lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.2))
    if al < 0.995:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    if chroma and p < 0.5:
        ca = int(80 * (1 - p / 0.5))
        for off, c in ((-6, (255, 66, 90)), (6, (66, 200, 255))):
            t = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            t.paste(Image.new("RGBA", lay.size, ac(c, ca)), (0, 0), lay)
            cv.alpha_composite(t, (px + off, py))
    if trail:
        for i in range(5, 0, -1):
            kk = 1 - eo(p)
            ox = int(-trail * i / 5 * kk)
            if not ox:
                continue
            t = lay.copy()
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.12 * (6 - i) / 5 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def ghost(cv, s, fn, size, cx, cy, col, alpha=46):
    """Огромная полупрозрачная цифра/слово на фоне."""
    lay = _lay(s, fn, size, ac(col, alpha))
    lay = lay.resize((max(2, int(lay.width * 1.0)), max(2, lay.height)), Image.LANCZOS)
    cv.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def chip(d, x, y, s, col=KHAKI, size=27, h=58, alpha=255, solid=False):
    f = F(MONO, size)
    w = int(f.getlength(s))
    d.rectangle([x, y, x + w + 42, y + h],
                fill=ac(col if solid else (11, 12, 15), alpha * (0.95 if solid else 0.88)),
                outline=ac(col, alpha * 0.85))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 21, y + (h - size) / 2 - 6), s, font=f, fill=ac((9, 10, 12) if solid else col, alpha))
    return w + 42


def plate(cv, box, fill=(12, 13, 16), alpha=235, outline=None, oalpha=215, width=2, accent=None):
    """Плашка на канвасе (компонуется по-настоящему, а не «пробивает» дырку)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rectangle(box, fill=ac(fill, alpha), outline=ac(outline, oalpha) if outline else None, width=width)
    if accent:
        dd.rectangle([box[0], box[1], box[2], box[1] + 6], fill=ac(accent, 255))
    cv.alpha_composite(lay)


def chips_row(d, y, items, alpha=255, x0=None, gap=16, size=27):
    """Ряд чипов по центру."""
    ws = []
    for s, col, solid in items:
        f = F(MONO, size)
        ws.append(int(f.getlength(s)) + 42)
    total = sum(ws) + gap * (len(items) - 1)
    x = x0 if x0 is not None else int((W - total) / 2)
    for (s, col, solid), w in zip(items, ws):
        chip(d, x, y, s, col, size, int(58 * size / 27), alpha, solid)
        x += w + gap


def callout(d, x, y, txt, p, col=COY, side=1, size=25):
    if p <= 0:
        return
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=ac(col, int(245 * p)))
    d.ellipse([x - 20, y - 20, x + 20, y + 20], outline=ac(col, int(120 * p)), width=2)
    f = F(MONO, size)
    tw = int(f.getlength(txt))
    need = tw + 32
    if side > 0 and x + 40 + need > W - 34:
        side = -1
    elif side < 0 and x - 40 - need < 34:
        side = 1
    bx = x + 40 if side > 0 else x - 40 - need
    bx = int(cl(bx, 30, W - need - 30))
    d.rectangle([bx, y - 21, bx + tw + 32, y + 21], fill=ac((7, 8, 10), int(225 * p)),
                outline=ac(col, int(160 * p)))
    d.text((bx + 16, y - 12), txt, font=f, fill=ac(col, int(248 * p)))
    d.line([(x + side * 21, y), (bx if side > 0 else bx + tw + 32, y)], fill=ac(col, int(180 * p)), width=3)


def dim_v(d, x, y0, y1, label, p, col=KHAKI, side=1):
    """Вертикальная размерная линия со стрелками."""
    if p <= 0:
        return
    yy1 = int(y0 + (y1 - y0) * eo(p))
    d.line([(x, y0), (x, yy1)], fill=ac(col, 235), width=4)
    for yy, sgn in ((y0, -1), (yy1, 1)):
        d.polygon([(x, yy), (x - 13, yy + 22 * sgn), (x + 13, yy + 22 * sgn)], fill=ac(col, 235))
    if p > 0.85:
        f = F(MONO, 34)
        tx = x - 58 if side < 0 else x + 22
        d.rectangle([tx - 10, (y0 + y1) / 2 - 26, tx + f.getlength(label) + 12, (y0 + y1) / 2 + 26],
                    fill=ac((7, 8, 10), 220))
        d.text((tx, (y0 + y1) / 2 - 17), label, font=f, fill=ac(col, 245))


def dim_h(d, y, x0, x1, label, p, col=KHAKI):
    if p <= 0:
        return
    xx1 = int(x0 + (x1 - x0) * eo(p))
    d.line([(x0, y), (xx1, y)], fill=ac(col, 235), width=4)
    for xx, sgn in ((x0, -1), (xx1, 1)):
        d.polygon([(xx, y), (xx + 22 * sgn, y - 13), (xx + 22 * sgn, y + 13)], fill=ac(col, 235))
    if p > 0.85:
        f = F(MONO, 34)
        cx = (x0 + x1) / 2
        d.rectangle([cx - f.getlength(label) / 2 - 12, y - 54, cx + f.getlength(label) / 2 + 12, y - 6],
                    fill=ac((7, 8, 10), 220))
        d.text((cx - f.getlength(label) / 2, y - 46), label, font=f, fill=ac(col, 245))


def arrow(d, x0, y0, x1, y1, p, col=COY, w=7):
    """Растущая стрелка от точки к точке."""
    if p <= 0:
        return
    k = eo(p)
    xm, ym = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    d.line([(x0, y0), (xm, ym)], fill=ac(col, int(230)), width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    for s in (-0.42, 0.42):
        d.line([(xm, ym), (xm - 34 * math.cos(ang - s), ym - 34 * math.sin(ang - s))],
               fill=ac(col, int(230)), width=w)


def tick_marks(d, col=KHAKI, alpha=70):
    for (x, y, sx, sy) in ((44, 128, 1, 1), (W - 44, 128, -1, 1),
                           (44, H - 168, 1, -1), (W - 44, H - 168, -1, -1)):
        d.line([(x, y), (x + sx * 46, y)], fill=ac(col, alpha), width=3)
        d.line([(x, y), (x, y + sy * 46)], fill=ac(col, alpha), width=3)


def hud(d, t, total, title, accent=KHAKI):
    d.rectangle([0, 0, W, 108], fill=(7, 8, 10, 236))
    d.rectangle([0, 0, W, 4], fill=ac(accent, 255))
    d.text((42, 26), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=ac(TXT, 255))
    d.text((42, 76), title, font=F(MONO, 20), fill=ac(DIM, 235))
    b = 0.5 + 0.5 * math.sin(t * 7.5)
    d.ellipse([W - 68, 64, W - 46, 86], fill=ac(RED, int(105 + 130 * b)))
    d.text((W - 84, 62), "REC", font=F(MONO, 20), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / total)
    d.rectangle([0, 108, W, 114], fill=(16, 18, 22, 246))
    d.rectangle([0, 108, int(W * p), 114], fill=ac(accent, 246))
    d.rectangle([0, H - 122, W, H], fill=(5, 6, 8, 248))
    d.rectangle([0, H - 125, W, H - 121], fill=ac(accent, 95))
    d.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 25),
           fill=ac(COY, 240), anchor="ma")
    d.text((W // 2, H - 52), "РЮКЗАК 7.62 · 70 Л · КОЙОТ / ХАКИ", font=F(RUSSO, 19),
           fill=ac(DIM, 215), anchor="ma")


def scanlines(cv):
    cv.alpha_composite(SCAN)
    cv.alpha_composite(VIGN)


def grain(cv, t):
    cv.alpha_composite(GRAIN[int(t * 15) % 4])


def punch(im, t, cuts, amp=0.05):
    for c in cuts:
        dd = t - c
        if 0 <= dd < 0.20:
            k = 1 - dd / 0.20
            z = 1 + amp * k
            w, h = int(W / z), int(H / z)
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize((W, H), Image.BILINEAR)
    return im


def beat_shake(t, beat=0.5, amp=3.5):
    b = (t / beat) % 1.0
    k = math.exp(-b * 9) * amp
    r = random.Random(int(t * 100))
    return (r.uniform(-1, 1) * k, r.uniform(-1, 1) * k)


def shift(cv, dx, dy):
    if not dx and not dy:
        return cv
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(cv, (int(dx), int(dy)))
    return out


def fade_all(cv, k):
    if k <= 0:
        return cv
    ov = Image.new("RGBA", (W, H), (5, 6, 8, int(255 * cl(k))))
    return Image.alpha_composite(cv, ov)


def outro_card(cv, d, l, accent=KHAKI, sub="РЮКЗАК 7.62", extra="70 Л · КОЙОТ / ХАКИ",
               bags=None):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((8, 9, 12), 255)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(accent, int(34 * (1 - k) ** 2)))
    cv.alpha_composite(g)
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-700 + (cl(l / 3.2) ** 0.8) * (W + 1400))
    ds.polygon([(x, 0), (x + 240, 0), (x + 240 - 460, H), (x - 460, H)], fill=ac(accent, 24))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(18)))
    if bags:
        p0 = c01((l - .02) / .35)
        for name, cx, hh, col in bags:
            bag(cv, name, cx, 400, int(hh * eo(p0)), shadow=.9, alpha=int(255 * p0), bloom=.45, accent=col)
    slam(cv, "«В ОКОПЕ»", RUSSO, 158, 540, 852, ac(TXT, 255), c01((l - .22) / .30), "ma", 44, maxw=980)
    if l > .48:
        p = c01((l - .48) / .30)
        slam(cv, sub, MONO, 40, 540, 1008, ac(accent, 250 * p), p, "ma", 22)
    if l > .72:
        p = c01((l - .72) / .30)
        d.rectangle([540 - int(300 * eo(p)), 1068, 540 + int(300 * eo(p)), 1075], fill=ac(accent, 220))
    if l > .90:
        p = c01((l - .90) / .30)
        slam(cv, extra, MONO, 28, 540, 1110, ac(DIM, 240 * p), p, "ma", 16)
    if l > 1.10:
        p = c01((l - 1.10) / .30)
        slam(cv, "В НАЛИЧИИ", RUSSO, 56, 540, 1190, ac(TXT, 245 * p), p, "ma", 22)
    if l > 1.38:
        p = c01((l - 1.38) / .30)
        slam(cv, "t.me/vokope_ru", MONO, 33, 540, 1292, ac(ICE, 235 * p), p, "ma", 16)
        slam(cv, "vk.com/vokope_rus", MONO, 33, 540, 1346, ac(ICE, 235 * p), p, "ma", 16)
    if l > 1.68:
        p = c01((l - 1.68) / .35)
        chips_row(d, 1412, [("ПОДПИШИСЬ", COY, True)], int(255 * p))
    if l > .3:
        q = c01((l - .3) / .5)
        d.rectangle([46, 200, W - 46, H - 250], outline=ac(accent, int(70 * q)), width=4)
        tick_marks(d, accent, int(90 * q))
