# -*- coding: utf-8 -*-
"""Графика роликов «Капюшон» К-8М (купол на машину).

Фирменная система из брифа серии: графит-олива, тёплый белый, единственный
акцент — лайм; светлые плашки под изделие, прямые углы, только типографика
и линии. Фото — только заказчика из assets/.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

BG0 = (28, 35, 23)          # #1C2317
BG1 = (14, 18, 12)
TXT = (237, 232, 215)       # #EDE8D7
LIME = (201, 242, 75)       # #C9F24B — единственный акцент
PLATE = (240, 235, 220)     # #F0EBDC
DIM = (146, 149, 137)
INK = (24, 28, 20)

COND = "SofiaSansExtraCondensed-VF.ttf"
TEK = "Tektur-VF.ttf"
MONT = "Montserrat-VF.ttf"


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
    c = 2.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────── фон
def _bg():
    a = np.zeros((H, W, 3), np.float32)
    v = np.linspace(0, 1, H)[:, None]
    for i in range(3):
        a[:, :, i] = BG1[i] + (BG0[i] - BG1[i]) * v
    im = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(gl)
    for i in range(20):
        r = 900 - i * 34
        d.ellipse([W / 2 - r, 560 - r * 0.62, W / 2 + r, 560 + r * 0.62], fill=(120, 150, 50, 4))
    return Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(120)))


STAGE = _bg()

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 16))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(120):
    k = i / 120
    ins = int(-190 + k * 430)
    _v.ellipse([ins, ins * 1.05, W - ins, H - ins * 1.05], outline=(0, 0, 0, int(3 + k * 2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(30))

_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 20, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 12))))

_cache = {}


def photo(name):
    if name not in _cache:
        fn = name if os.path.splitext(name)[1] else name + ".jpg"
        _cache[name] = Image.open(os.path.join(A, fn)).convert("RGB")
    return _cache[name]


def stage(cv, accent=LIME, glow=0.0, t=0.0):
    cv.alpha_composite(STAGE)
    if glow > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        r = 540 + 50 * math.sin(t * 1.3)
        d.ellipse([540 - r, 980 - r * 0.75, 540 + r, 980 + r * 0.75], fill=ac(accent, int(16 * glow)))
        cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(120)))


def grid(d, alpha=13, col=LIME, step=96):
    for i in range(0, W + 1, step):
        d.line([(i, 150), (i, H - 190)], fill=ac(col, alpha), width=1)
    for j in range(150, H - 186, step):
        d.line([(0, j), (W, j)], fill=ac(col, alpha), width=1)


def _cover(im, w, h, ox=0.5, oy=0.5):
    k = max(w / im.width, h / im.height)
    ww, hh = max(w, int(im.width * k + .5)), max(h, int(im.height * k + .5))
    im = im.resize((ww, hh), Image.LANCZOS)
    x = int(cl(ox * ww - w / 2, 0, ww - w))
    y = int(cl(oy * hh - h / 2, 0, hh - h))
    return im.crop((x, y, x + w, y + h))


def lplate(cv, name, box, zoom=1.0, ox=0.5, oy=0.5, p=1.0, caption=None,
           corner=True, accent=LIME, src=None):
    """Фото изделия на светлой плашке — «паспорт изделия», прямые углы."""
    if p <= 0:
        return None
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    base = photo(name)
    if src:
        base = base.crop(tuple(src))
    im = _cover(base, int(w * zoom), int(h * zoom), ox, oy)
    im = im.crop(((im.width - w) // 2, (im.height - h) // 2,
                  (im.width - w) // 2 + w, (im.height - h) // 2 + h))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(im.convert("RGBA"), (x0, y0))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=int(255 * cl(p)))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), mask))
    cv.alpha_composite(lay)
    d = ImageDraw.Draw(cv)
    if p > 0.55:
        q = c01((p - 0.55) / 0.45)
        d.rectangle([x0, y0, x1, y1], outline=ac(PLATE, int(60 * q)), width=2)
        if corner:
            for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                d.line([(cx, cy), (cx + sx * 26, cy)], fill=ac(accent, int(235 * q)), width=4)
                d.line([(cx, cy), (cx, cy + sy * 26)], fill=ac(accent, int(235 * q)), width=4)
        if caption:
            f = F(TEK, 22)
            d.rectangle([x0 + 22, y1 - 52, x0 + 22 + int(f.getlength(caption)) + 28, y1 - 14],
                        fill=ac(BG0, int(232 * q)))
            d.text((x0 + 36, y1 - 46), caption, font=f, fill=ac(TXT, int(240 * q)))
    return (x0, y0, w, h)


def photo_strip(cv, name, cy, w, zoom=1.0, ox=0.5, p=1.0, dark=0.0):
    """Фотополоса во всю ширину с растворёнными кромками."""
    im = photo(name)
    k = w / im.width * zoom
    ww, hh = int(im.width * k), int(im.height * k)
    im = im.resize((max(2, ww), max(2, hh)), Image.LANCZOS)
    x0 = int(540 - ww / 2 + (ox - .5) * w * .4)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(im.convert("RGBA"), (max(0, x0), int(cy - hh / 2)))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle([max(0, x0) + 2, int(cy - hh / 2) + 2,
                                 max(0, x0) + ww - 2, int(cy + hh / 2) - 2], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(10))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    if p < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * p)))
    cv.alpha_composite(lay)
    if dark > 0:
        cv.alpha_composite(Image.new("RGBA", (W, H), ac(BG1, int(255 * dark))))
    return (max(0, x0), int(cy - hh / 2), ww, hh)


# ─────────────────────────── текст
def _lay(s, fn, size, col, tracking=0):
    f = F(fn, size)
    if not tracking:
        w = int(f.getlength(s)) + 40
        lay = Image.new("RGBA", (max(2, w), int(size * 1.42)), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((20, 4), s, font=f, fill=col)
        return lay
    adv = [f.getlength(ch) + tracking for ch in s]
    w = int(sum(adv)) + 44
    lay = Image.new("RGBA", (max(2, w), int(size * 1.42)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    x = 20.0
    for ch, a in zip(s, adv):
        dd.text((x, 4), ch, font=f, fill=col)
        x += a
    return lay


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", maxw=None, tracking=0,
         stretch=1.0):
    if p <= 0:
        return
    lay = _lay(s, fn, size, col, tracking)
    lim = maxw or (W - 76)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    if stretch != 1.0:
        lay = lay.resize((int(lay.width * stretch), lay.height), Image.LANCZOS)
    k = 1 + 0.10 * (1 - eo(p))
    if abs(k - 1) > 0.004:
        lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.4))
    if al < 0.995:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    cv.alpha_composite(lay, (px, py))


def kicker(d, s, y, p=1.0, col=LIME, size=30, x=None, anchor="ma"):
    if p <= 0:
        return
    f = F(TEK, size)
    s2 = "  ".join(s)
    tw = int(f.getlength(s2))
    xx = (W - tw) / 2 if anchor == "ma" else x
    d.text((xx, y), s2, font=f, fill=ac(col, int(250 * p)))


def chip(d, x, y, s, col=LIME, size=25, h=54, alpha=255, solid=False):
    f = F(TEK, size)
    w = int(f.getlength(s))
    d.rectangle([x, y, x + w + 38, y + h],
                fill=ac(col if solid else BG1, alpha * (0.92 if solid else 0.86)),
                outline=ac(col, alpha * 0.8))
    d.rectangle([x, y, x + 4, y + h], fill=ac(col, alpha))
    d.text((x + 19, y + (h - size) / 2 - 5), s, font=f,
           fill=ac(INK if solid else col, alpha))
    return w + 38


def chips_row(d, y, items, alpha=255, size=25, gap=12):
    ws = [int(F(TEK, size).getlength(s)) + 38 for s, _, _ in items]
    total = sum(ws) + gap * (len(items) - 1)
    x = int((W - total) / 2)
    for (s, col, solid), w in zip(items, ws):
        chip(d, x, y, s, col, size, int(54 * size / 25), alpha, solid)
        x += w + gap


def plate(cv, box, fill=PLATE, alpha=238, outline=None, oalpha=215, width=2, accent=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rectangle(box, fill=ac(fill, alpha), outline=ac(outline, oalpha) if outline else None, width=width)
    if accent:
        dd.rectangle([box[0], box[1], box[2], box[1] + 5], fill=ac(accent, 255))
    cv.alpha_composite(lay)


def callout(d, x, y, txt, p, col=LIME, side=1, size=22):
    if p <= 0:
        return
    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=ac(BG0, int(240 * p)))
    d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=ac(col, int(250 * p)), width=3)
    d.ellipse([x - 17, y - 17, x + 17, y + 17], outline=ac(col, int(120 * p)), width=2)
    f = F(TEK, size)
    tw = int(f.getlength(txt))
    need = tw + 30
    if side > 0 and x + 32 + need > W - 30:
        side = -1
    elif side < 0 and x - 32 - need < 30:
        side = 1
    bx = x + 32 if side > 0 else x - 32 - need
    bx = int(cl(bx, 26, W - need - 26))
    d.rectangle([bx, y - 20, bx + tw + 30, y + 20], fill=ac(BG0, int(238 * p)),
                outline=ac(col, int(190 * p)))
    d.text((bx + 15, y - 10), txt, font=f, fill=ac(col, int(250 * p)))
    d.line([(x + side * 17, y), (bx if side > 0 else bx + tw + 30, y)], fill=ac(col, int(190 * p)), width=3)


def tick_marks(d, col=LIME, alpha=64):
    for (x, y, sx, sy) in ((48, 168, 1, 1), (W - 48, 168, -1, 1),
                           (48, H - 216, 1, -1), (W - 48, H - 216, -1, -1)):
        d.line([(x, y), (x + sx * 44, y)], fill=ac(col, alpha), width=3)
        d.line([(x, y), (x, y + sy * 44)], fill=ac(col, alpha), width=3)


def hud(d, t, total, label="«КАПЮШОН» К-8М", accent=LIME):
    d.rectangle([0, 0, W, 118], fill=(15, 19, 13, 236))
    d.rectangle([0, 0, W, 3], fill=ac(accent, 255))
    d.text((44, 22), "В ОКОПЕ", font=F(COND, 56), fill=ac(TXT, 255))
    d.text((44, 86), label, font=F(TEK, 18), fill=ac(DIM, 235))
    b = 0.5 + 0.5 * math.sin(t * 7.0)
    d.ellipse([W - 60, 62, W - 42, 80], fill=ac(accent, int(90 + 150 * b)))
    d.text((W - 74, 58), "REC", font=F(TEK, 18), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / max(total, .01))
    d.rectangle([0, 118, W, 123], fill=(21, 26, 18, 246))
    d.rectangle([0, 118, int(W * p), 123], fill=ac(accent, 250))
    d.rectangle([0, H - 152, W, H], fill=(11, 14, 9, 250))
    d.rectangle([0, H - 155, W, H - 152], fill=ac(accent, 90))
    d.text((W // 2, H - 122), "t.me/vokope_ru   ·   vk.com/vokope_rus", font=F(TEK, 25),
           fill=ac(PLATE, 240), anchor="ma")
    d.text((W // 2, H - 78), "СТАНЦИЯ РЭБ «КАПЮШОН» К-8М · АВТО", font=F(TEK, 17),
           fill=ac(DIM, 225), anchor="ma")
    d.text((W // 2, H - 46), "@vokope_ru  ·  +7 (999) 136-71-42", font=F(TEK, 17),
           fill=ac(DIM, 200), anchor="ma")


def scanlines(cv):
    cv.alpha_composite(SCAN)
    cv.alpha_composite(VIGN)


def grain(cv, t):
    cv.alpha_composite(GRAIN[int(t * 13) % 4])


def punch(im, t, cuts, amp=0.045):
    for c in cuts:
        dd = t - c
        if 0 <= dd < 0.18:
            k = 1 - dd / 0.18
            z = 1 + amp * k
            w, h = int(W / z), int(H / z)
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize((W, H), Image.BILINEAR)
    return im


# ─────────────────────────── схемы
def dome(cv, cx, cy, r, p, col=LIME):
    """Схема купола 360°: вид сверху, сектор."""
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(3):
        rr = r * (0.52 + 0.24 * i)
        d.ellipse([cx - rr, cy - rr * 0.60, cx + rr, cy + rr * 0.60], outline=ac(col, int(44 * p)), width=2)
    sweep = 360 * eo(p)
    d.arc([cx - r, cy - r * 0.60, cx + r, cy + r * 0.60], -90, -90 + sweep, fill=ac(col, int(220 * p)), width=5)
    d.ellipse([cx - 22, cy - 13, cx + 22, cy + 13], fill=ac(col, int(230 * p)))
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        d.line([(cx + 30 * math.cos(a), cy + 18 * math.sin(a)),
                (cx + r * 0.97 * math.cos(a), cy + r * 0.58 * math.sin(a))],
               fill=ac(col, int(38 * p)), width=2)
    cv.alpha_composite(lay)


def rings(cv, cx, cy, r, p, col=LIME, n=4):
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(1, n + 1):
        k = i / n
        rr = r * k * eo(cl(p * 1.3 - (i - 1) * 0.12))
        if rr <= 2:
            continue
        d.ellipse([cx - rr, cy - rr * 0.58, cx + rr, cy + rr * 0.58],
                  outline=ac(col, int((110 - 20 * i) * p)), width=3 if i == n else 2)
    cv.alpha_composite(lay)


def scan_bar(d, x0, x1, y, p, col=LIME, h=4):
    """Полоса-«сканер»: растёт слева направо, как индикатор частоты."""
    if p <= 0:
        return
    d.rectangle([x0, y, x0 + int((x1 - x0) * eo(p)), y + h], fill=ac(col, 245))


def photo_in(cv, name, src, dst, p=1.0, dark=0.0):
    """Фото из заданной области исходника в заданный прямоугольник кадра."""
    im = photo(name).crop(tuple(src))
    w, h = dst[2] - dst[0], dst[3] - dst[1]
    im = _cover(im, w, h)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(im.convert("RGBA"), (dst[0], dst[1]))
    if p < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * cl(p))))
    cv.alpha_composite(lay)
    if dark > 0:
        ov = Image.new("RGBA", (W, H), ac(BG1, int(255 * dark)))
        cv.alpha_composite(ov)
    return dst
