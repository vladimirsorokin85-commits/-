# -*- coding: utf-8 -*-
"""Графика роликов про комплект РЭБ «Капюшон» К-8М.

Кадры — из фото заказчика (две станции на кейсах) + схемы и типографика.
Никаких сгенерированных изображений самого изделия.
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

BG0 = (8, 9, 7)
BG1 = (18, 20, 14)
OLV = (176, 202, 112)      # жёлто-зелёный акцент (как на баннере заказчика)
OLV2 = (128, 150, 58)
KHAKI = (198, 182, 116)
WARN = (255, 196, 74)      # предупреждение про срок акции
TXT = (245, 246, 243)
DIM = (150, 156, 142)
RED = (255, 74, 58)

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


def eb(x):
    x = c01(x)
    c = 2.6
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────── фон
def _grad(w, h, c0, c1):
    a = np.zeros((h, w, 3), np.float32)
    v = np.linspace(0, 1, h)[:, None]
    for i in range(3):
        a[:, :, i] = c0[i] + (c1[i] - c0[i]) * v
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


STAGE = _grad(W, H, (26, 28, 21), (7, 8, 6))
_gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_dg = ImageDraw.Draw(_gl)
for i in range(26):
    r = 880 - i * 30
    _dg.ellipse([W / 2 - r, 700 - r * 0.7, W / 2 + r, 700 + r * 0.7], fill=(58, 66, 26, 5))
STAGE = Image.alpha_composite(STAGE, _gl.filter(ImageFilter.GaussianBlur(90)))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 20))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(130):
    k = i / 130
    ins = int(-210 + k * 450)
    _v.ellipse([ins, ins * 1.06, W - ins, H - ins * 1.06], outline=(0, 0, 0, int(3 + k * 2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(30))

_rng = np.random.default_rng(11)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 24, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 15))))

_cache = {}


def photo(name):
    if name not in _cache:
        fn = name if os.path.splitext(name)[1] else name + ".jpg"
        _cache[name] = Image.open(os.path.join(A, fn)).convert("RGB")
    return _cache[name]


def stage(cv, accent=OLV, glow=0.0, t=0.0):
    cv.alpha_composite(STAGE)
    if glow > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        r = 520 + 60 * math.sin(t * 1.4)
        d.ellipse([540 - r, 980 - r * 0.8, 540 + r, 980 + r * 0.8], fill=ac(accent, int(24 * glow)))
        cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(110)))


def strip(cv, name, cy, w, zoom=1.0, ox=0.0, dark=0.0, alpha=255, glow=0.0, accent=OLV):
    """Фото станции полосой: сохраняет пропорции, края затухают в фон."""
    im = photo(name)
    k = w / im.width * zoom
    ww, hh = int(im.width * k), int(im.height * k)
    im = im.resize((max(2, ww), max(2, hh)), Image.LANCZOS)
    x0 = int(540 - ww / 2 + cl(ox, -1, 1) * max(0, (ww - w) / 2))
    if alpha < 255:
        im = im.convert("RGBA")
        im.putalpha(im.convert("L").point(lambda v: v * alpha // 255))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(im.convert("RGBA"), (max(0, x0), int(cy - hh / 2)))
    # маска: мягкие края сверху/снизу и по бокам
    m = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(m)
    dm.rectangle([max(0, x0) + 2, int(cy - hh / 2), max(0, x0) + ww - 2, int(cy + hh / 2)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(6))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    cv.alpha_composite(lay)
    if dark > 0:
        ov = Image.new("RGBA", (W, H), (5, 6, 4, int(255 * dark)))
        cv.alpha_composite(ov)
    if glow > 0:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dg = ImageDraw.Draw(gl)
        dg.rectangle([max(0, x0), int(cy - hh / 2), max(0, x0) + ww, int(cy + hh / 2)], fill=ac(accent, int(40 * glow)))
        cv.alpha_composite(gl.filter(ImageFilter.GaussianBlur(60)))
    return (max(0, x0), int(cy - hh / 2), ww, hh)


def melt_top(cv, box, solid=26, fade=100, col=(9, 10, 8)):
    """Растворяет верхнюю кромку фото в фоне: перекрывает запечённый заголовок."""
    x0, y0, ww, hh = box
    h = min(hh, int(solid + fade))
    if h <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for i in range(h):
        a = 255 if i < solid else int(255 * (1 - (i - solid) / float(max(1, fade))) ** 1.35)
        dl.line([(max(0, x0), y0 + i), (max(0, x0) + ww, y0 + i)],
                fill=(col[0], col[1], col[2], a))
    cv.alpha_composite(lay)


def melt_bottom(cv, box, fade=140, col=(8, 9, 7)):
    """Растворяет нижнюю кромку фото в фоне."""
    x0, y0, ww, hh = box
    fy = y0 + hh - min(hh, fade)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for i in range(min(hh, fade)):
        a = int(255 * (i / float(max(1, fade))) ** 1.25)
        dl.line([(max(0, x0), fy + i), (max(0, x0) + ww, fy + i)],
                fill=(col[0], col[1], col[2], a))
    cv.alpha_composite(lay)


def cover(cv, box, src_w, col=(7, 8, 6)):
    """Закрывает огрызок запечённого заголовка сверху кропа (34 px в исходнике)."""
    f = box[2] / float(src_w)
    melt_top(cv, box, int(40 * f) + 2, int(130 * f) + 4, col)


def dim_photo(cv, name, cy, w, zoom=1.0, dark=0.35):
    """Полоса фото, притемнённая — под текст."""
    box = strip(cv, name, cy, w, zoom, dark=0.0)
    ov = Image.new("RGBA", (W, H), (6, 7, 5, int(255 * dark)))
    cv.alpha_composite(ov)
    return box


def grid(d, alpha=16, col=OLV, step=90):
    for i in range(0, W + 1, step):
        d.line([(i, 118), (i, H - 126)], fill=ac(col, alpha), width=1)
    for j in range(130, H - 120, step):
        d.line([(0, j), (W, j)], fill=ac(col, alpha), width=1)


# ─────────────────────────── текст
def _lay(s, fn, size, col, stroke=0, scol=None):
    f = F(fn, size)
    w = int(f.getlength(s)) + 40 + stroke * 2
    lay = Image.new("RGBA", (max(2, w), int(size * 1.5) + stroke * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 + stroke, 6 + stroke), s, font=f, fill=col,
                             stroke_width=stroke, stroke_fill=scol)
    return lay


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", trail=26, maxw=None,
         chroma=True, stroke=0, scol=None):
    if p <= 0:
        return
    lay = _lay(s, fn, size, col, stroke, scol)
    lim = maxw or (W - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.32 * (1 - eb(p))
    if abs(k - 1) > 0.01:
        lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.2))
    if al < 0.995:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    if chroma and p < 0.5:
        ca = int(70 * (1 - p / 0.5))
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
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.11 * (6 - i) / 5 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=OLV, size=26, h=56, alpha=255, solid=False):
    f = F(MONO, size)
    w = int(f.getlength(s))
    d.rectangle([x, y, x + w + 40, y + h],
                fill=ac(col if solid else (10, 11, 8), alpha * (0.95 if solid else 0.9)),
                outline=ac(col, alpha * 0.85))
    d.rectangle([x, y, x + 5, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size) / 2 - 6), s, font=f, fill=ac((10, 11, 8) if solid else col, alpha))
    return w + 40


def chips_row(d, y, items, alpha=255, size=26, gap=14):
    ws = [int(F(MONO, size).getlength(s)) + 40 for s, _, _ in items]
    total = sum(ws) + gap * (len(items) - 1)
    x = int((W - total) / 2)
    for (s, col, solid), w in zip(items, ws):
        chip(d, x, y, s, col, size, int(56 * size / 26), alpha, solid)
        x += w + gap


def plate(cv, box, fill=(11, 12, 9), alpha=238, outline=None, oalpha=215, width=2, accent=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rectangle(box, fill=ac(fill, alpha), outline=ac(outline, oalpha) if outline else None, width=width)
    if accent:
        dd.rectangle([box[0], box[1], box[2], box[1] + 6], fill=ac(accent, 255))
    cv.alpha_composite(lay)


def callout(d, x, y, txt, p, col=OLV, side=1, size=24):
    if p <= 0:
        return
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=ac(col, int(245 * p)))
    d.ellipse([x - 19, y - 19, x + 19, y + 19], outline=ac(col, int(120 * p)), width=2)
    f = F(MONO, size)
    tw = int(f.getlength(txt))
    need = tw + 32
    if side > 0 and x + 40 + need > W - 34:
        side = -1
    elif side < 0 and x - 40 - need < 34:
        side = 1
    bx = x + 40 if side > 0 else x - 40 - need
    bx = int(cl(bx, 30, W - need - 30))
    d.rectangle([bx, y - 21, bx + tw + 32, y + 21], fill=ac((7, 8, 6), int(228 * p)),
                outline=ac(col, int(160 * p)))
    d.text((bx + 16, y - 12), txt, font=f, fill=ac(col, int(248 * p)))
    d.line([(x + side * 21, y), (bx if side > 0 else bx + tw + 32, y)], fill=ac(col, int(180 * p)), width=3)


def tick_marks(d, col=OLV, alpha=70):
    for (x, y, sx, sy) in ((44, 128, 1, 1), (W - 44, 128, -1, 1),
                           (44, H - 168, 1, -1), (W - 44, H - 168, -1, -1)):
        d.line([(x, y), (x + sx * 46, y)], fill=ac(col, alpha), width=3)
        d.line([(x, y), (x, y + sy * 46)], fill=ac(col, alpha), width=3)


def hud(d, t, total, title, accent=OLV):
    d.rectangle([0, 0, W, 108], fill=(7, 8, 6, 238))
    d.rectangle([0, 0, W, 4], fill=ac(accent, 255))
    d.text((42, 26), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=ac(TXT, 255))
    d.text((42, 76), title, font=F(MONO, 19), fill=ac(DIM, 235))
    b = 0.5 + 0.5 * math.sin(t * 7.5)
    d.ellipse([W - 68, 64, W - 46, 86], fill=ac(RED, int(105 + 130 * b)))
    d.text((W - 84, 62), "REC", font=F(MONO, 20), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / total)
    d.rectangle([0, 108, W, 114], fill=(16, 18, 12, 246))
    d.rectangle([0, 108, int(W * p), 114], fill=ac(accent, 246))
    d.rectangle([0, H - 122, W, H], fill=(5, 6, 4, 248))
    d.rectangle([0, H - 125, W, H - 121], fill=ac(accent, 95))
    d.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 25),
           fill=ac(KHAKI, 240), anchor="ma")
    d.text((W // 2, H - 52), "СТАНЦИИ РЭБ «КАПЮШОН» · КОМПЛЕКТ ИЗ ДВУХ", font=F(RUSSO, 18),
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


def beat_shake(t, beat=0.5, amp=3.0):
    b = (t / beat) % 1.0
    k = math.exp(-b * 9) * amp
    r = random.Random(int(t * 100))
    return (r.uniform(-1, 1) * k, r.uniform(-1, 1) * k)


# ─────────────────────────── схемы
def dome_scheme(cv, cx, cy, r, p, col=OLV):
    """Схема купола 360°: вид сверху, сектор обзора, радиус."""
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(3):
        rr = r * (0.55 + 0.22 * i)
        d.ellipse([cx - rr, cy - rr * 0.62, cx + rr, cy + rr * 0.62], outline=ac(col, int(46 * p)), width=2)
    sweep = 360 * eo(p)
    d.arc([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], -90, -90 + sweep, fill=ac(col, int(210 * p)), width=5)
    d.ellipse([cx - 26, cy - 26 * 0.62, cx + 26, cy + 26 * 0.62], fill=ac(col, int(220 * p)))
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        d.line([(cx + 34 * math.cos(a), cy + 21 * math.sin(a)),
                (cx + r * 0.96 * math.cos(a), cy + r * 0.6 * math.sin(a))], fill=ac(col, int(40 * p)), width=2)
    cv.alpha_composite(lay)


def rings(cv, cx, cy, r, p, col=OLV, n=4):
    """Концентрические кольца зоны подавления."""
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(1, n + 1):
        k = i / n
        rr = r * k * eo(cl(p * 1.3 - (i - 1) * 0.12))
        if rr <= 2:
            continue
        d.ellipse([cx - rr, cy - rr * 0.6, cx + rr, cy + rr * 0.6],
                  outline=ac(col, int((120 - 22 * i) * p)), width=3 if i == n else 2)
    cv.alpha_composite(lay)


def outro_card(cv, d, l, accent=OLV, sub="КОМПЛЕКТ ИЗ ДВУХ СТАНЦИЙ",
               extra="8 КАНАЛОВ · 400–5900 МГЦ · ДО 300 М", deadline=True,
               photo_name="right_clean", photo_h=430):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((8, 9, 7), 255)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(accent, int(30 * (1 - k) ** 2)))
    cv.alpha_composite(g)
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-700 + (cl(l / 3.2) ** 0.8) * (W + 1400))
    ds.polygon([(x, 0), (x + 240, 0), (x + 240 - 460, H), (x - 460, H)], fill=ac(accent, 22))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(18)))
    if photo_name:
        p0 = c01((l - .02) / .40)
        box = strip(cv, photo_name, 430, int(980 * (0.94 + 0.06 * eo(p0))), alpha=int(235 * p0), dark=0.1)
        if p0 > 0.5:
            melt_top(cv, box, 38, 110)
            melt_bottom(cv, box, 110)
    slam(cv, "«В ОКОПЕ»", RUSSO, 150, 540, 760, ac(TXT, 255), c01((l - .20) / .30), "ma", 42, maxw=980)
    if l > .46:
        p = c01((l - .46) / .30)
        slam(cv, sub, MONO, 38, 540, 906, ac(accent, 250 * p), p, "ma", 20)
    if l > .68:
        p = c01((l - .68) / .30)
        d.rectangle([540 - int(300 * eo(p)), 962, 540 + int(300 * eo(p)), 969], fill=ac(accent, 220))
    if l > .84:
        p = c01((l - .84) / .30)
        slam(cv, extra, MONO, 26, 540, 1004, ac(DIM, 240 * p), p, "ma", 14)
    if l > 1.00:
        p = c01((l - 1.00) / .30)
        slam(cv, "В НАЛИЧИИ", RUSSO, 52, 540, 1046, ac(TXT, 245 * p), p, "ma", 20)
    if deadline and l > 1.22:
        p = c01((l - 1.22) / .30)
        plate(cv, [230, 1122, 850, 1200], (30, 22, 6), int(238 * p), WARN, int(230 * p), 3)
        slam(cv, "АКЦИЯ ДО 15 НОЯБРЯ", MONO, 30, 540, 1142, ac(WARN, 250 * p), p, "ma", 14)
    if l > 1.46:
        p = c01((l - 1.46) / .30)
        slam(cv, "t.me/vokope_ru", MONO, 32, 540, 1258, ac(KHAKI, 235 * p), p, "ma", 14)
        slam(cv, "vk.com/vokope_rus", MONO, 32, 540, 1310, ac(KHAKI, 235 * p), p, "ma", 14)
    if l > 1.72:
        p = c01((l - 1.72) / .35)
        chips_row(d, 1382, [("ПОДПИШИСЬ", OLV, True)], int(255 * p))
    if l > .3:
        q = c01((l - .3) / .5)
        d.rectangle([46, 200, W - 46, H - 250], outline=ac(accent, int(66 * q)), width=4)
        tick_marks(d, accent, int(86 * q))
