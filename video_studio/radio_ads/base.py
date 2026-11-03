# -*- coding: utf-8 -*-
"""Графика анонсов радио «В ОКОПЕ»: 1080×1920, 30 fps.

Палитра и приёмы — из фирменного стиля канала: тёмный уголь, оливковый акцент,
янтарь радиолампы, красная лампа «В ЭФИРЕ».
"""
import json
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
OLV = (176, 202, 112)
OLV2 = (122, 144, 60)
AMBER = (255, 178, 72)
RED = (255, 74, 58)
TXT = (245, 246, 243)
DIM = (150, 156, 142)
KHAKI = (198, 182, 116)

RUSSO = "RussoOne-Regular.ttf"
MONO = "JetBrainsMono-VF.ttf"
COND = "FiraSansExtraCondensed-Black.ttf"
DAYS = "DaysOne-Regular.ttf"


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), int(s))


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


# ───────────────────────── фон
def _grad(w, h, c0, c1):
    a = np.zeros((h, w, 3), np.float32)
    v = np.linspace(0, 1, h)[:, None]
    for i in range(3):
        a[:, :, i] = c0[i] + (c1[i] - c0[i]) * v
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


STAGE = _grad(W, H, (24, 26, 20), (6, 7, 5))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 22))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(120):
    k = i / 120
    ins = int(-190 + k * 430)
    _v.ellipse([ins, ins * 1.05, W - ins, H - ins * 1.05], outline=(0, 0, 0, int(3 + k * 2)), width=7)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(28))

_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 22, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 15))))

_cache = {}
_spec = {}


def photo(name):
    if name not in _cache:
        fn = name if os.path.splitext(name)[1] else name + ".jpg"
        _cache[name] = Image.open(os.path.join(A, fn)).convert("RGB")
    return _cache[name]


def spectrum(tag):
    """Реальный спектр мастер-дорожки: 24 полосы на кадр."""
    if tag not in _spec:
        with open(os.path.join(BASE, "spectrum_%s.json" % tag), encoding="utf-8") as f:
            _spec[tag] = json.load(f)
    return _spec[tag]


def stage(cv, accent=OLV, glow=0.0, t=0.0):
    cv.alpha_composite(STAGE)
    if glow > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        r = 560 + 50 * math.sin(t * 1.2)
        d.ellipse([540 - r, 960 - r * 0.75, 540 + r, 960 + r * 0.75],
                  fill=ac(accent, int(26 * glow)))
        cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(120)))


def bg_photo(cv, name, zoom=1.0, dx=0.0, dy=0.0, dark=0.0, sat=1.0, cy=None):
    """Полноэкранное фото 9:16 с мягким затемнением и сдвигом (Ken Burns)."""
    im = photo(name)
    tw, th = int(W * zoom), int(H * zoom)
    k = max(tw / im.width, th / im.height)
    im = im.resize((max(2, int(im.width * k)), max(2, int(im.height * k))), Image.LANCZOS)
    x0 = int((W - im.width) / 2 + dx)
    y0 = int((H - im.height) / 2 + dy) if cy is None else int(cy - im.height / 2 + dy)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(im.convert("RGBA"), (x0, y0))
    cv.alpha_composite(lay)
    if dark > 0:
        ov = Image.new("RGBA", (W, H), ac((4, 5, 4), 255 * dark))
        cv.alpha_composite(ov)


def shade(cv, y0, y1, a0=0, a1=210, col=(4, 5, 4)):
    """Вертикальный градиент-затемнение под текст."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    n = max(1, y1 - y0)
    for i in range(n):
        a = int(a0 + (a1 - a0) * (i / n))
        d.line([(0, y0 + i), (W, y0 + i)], fill=(col[0], col[1], col[2], a))
    cv.alpha_composite(lay)


def grid(d, alpha=14, col=OLV, step=90):
    for i in range(0, W + 1, step):
        d.line([(i, 120), (i, H - 130)], fill=ac(col, alpha), width=1)
    for j in range(140, H - 120, step):
        d.line([(0, j), (W, j)], fill=ac(col, alpha), width=1)


# ───────────────────────── текст
def _lay(s, fn, size, col, stroke=0, scol=None, spacing=0):
    f = F(fn, size)
    w = int(f.getlength(s)) + 40 + stroke * 2
    lay = Image.new("RGBA", (max(2, w), int(size * 1.55) + stroke * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 + stroke, 6 + stroke), s, font=f, fill=col,
                             stroke_width=stroke, stroke_fill=scol)
    return lay


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", trail=24, maxw=None,
         chroma=True, stroke=0, scol=None):
    if p <= 0:
        return
    lay = _lay(s, fn, size, col, stroke, scol)
    lim = maxw or (W - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.30 * (1 - eb(p))
    if abs(k - 1) > 0.01:
        lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.4))
    if al < 0.995:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    if chroma and p < 0.45:
        ca = int(80 * (1 - p / 0.45))
        for off, c in ((-7, (255, 60, 84)), (7, (60, 198, 255))):
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
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.10 * (6 - i) / 5 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=OLV, size=26, h=56, alpha=255, solid=False):
    f = F(MONO, size)
    w = int(f.getlength(s))
    d.rectangle([x, y, x + w + 40, y + h],
                fill=ac(col if solid else (9, 10, 8), int(alpha * (0.95 if solid else 0.92))),
                outline=ac(col, int(alpha * 0.9)))
    d.rectangle([x, y, x + 5, y + h], fill=ac(col, int(alpha)))
    d.text((x + 20, y + (h - size) / 2 - 6), s, font=f,
           fill=ac((9, 10, 8) if solid else col, alpha))
    return w + 40


def chips_row(d, y, items, alpha=255, size=26, gap=14):
    ws = [int(F(MONO, size).getlength(s)) + 40 for s, _, _ in items]
    total = sum(ws) + gap * (len(items) - 1)
    x = int((W - total) / 2)
    for (s, col, solid), w in zip(items, ws):
        chip(d, x, y, s, col, size, int(56 * size / 26), alpha, solid)
        x += w + gap


def plate(cv, box, fill=(9, 10, 8), alpha=238, outline=None, oalpha=215, width=2, accent=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rectangle(box, fill=ac(fill, alpha), outline=ac(outline, oalpha) if outline else None, width=width)
    if accent:
        dd.rectangle([box[0], box[1], box[2], box[1] + 6], fill=ac(accent, 255))
    cv.alpha_composite(lay)


def tick_marks(d, col=OLV, alpha=70):
    for (x, y, sx, sy) in ((44, 130, 1, 1), (W - 44, 130, -1, 1),
                           (44, H - 172, 1, -1), (W - 44, H - 172, -1, -1)):
        d.line([(x, y), (x + sx * 46, y)], fill=ac(col, alpha), width=3)
        d.line([(x, y), (x, y + sy * 46)], fill=ac(col, alpha), width=3)


def hud(d, t, total, accent=OLV, sub="РАДИО «В ОКОПЕ» · 24/7", onair=True):
    d.rectangle([0, 0, W, 108], fill=(6, 7, 5, 240))
    d.rectangle([0, 0, W, 4], fill=ac(accent, 255))
    d.text((42, 24), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=ac(TXT, 255))
    d.text((42, 74), sub, font=F(MONO, 19), fill=ac(DIM, 235))
    if onair:
        b = 0.5 + 0.5 * math.sin(t * 6.2)
        d.ellipse([W - 172, 62, W - 150, 84], fill=ac(RED, int(110 + 130 * b)))
        d.text((W - 196, 60), "В ЭФИРЕ", font=F(MONO, 20), fill=ac(DIM, 205), anchor="ra")
    p = cl(t / max(total, 0.01))
    d.rectangle([0, 108, W, 114], fill=(14, 16, 10, 246))
    d.rectangle([0, 108, int(W * p), 114], fill=ac(accent, 246))
    d.rectangle([0, H - 122, W, H], fill=(4, 5, 4, 250))
    d.rectangle([0, H - 125, W, H - 121], fill=ac(accent, 100))
    d.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 25),
           fill=ac(KHAKI, 240), anchor="ma")
    d.text((W // 2, H - 52), "РАДИО «В ОКОПЕ» · ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ", font=F(RUSSO, 17),
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
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize(
                (W, H), Image.BILINEAR)
    return im


def beat_pulse(t, bpm):
    b = (t * bpm / 60.0) % 1.0
    return math.exp(-b * 6.5)


# ───────────────────────── фирменные элементы
def logo_mark(cv, cx, cy, s=1.0, p=1.0, col=OLV, glow=1.0, sub=True):
    """Знак радио: «В ОКОПЕ» в рамке с волнами и подписью."""
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    w = int(640 * s)
    h = int(306 * s)
    box = [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]
    d.rectangle(box, fill=ac((7, 8, 6), int(214 * p)), outline=ac(col, int(232 * p)), width=max(2, int(3 * s)))
    d.rectangle([box[0] + 10, box[1] + 10, box[2] - 10, box[3] - 10],
                outline=ac(col, int(90 * p)), width=max(1, int(1.6 * s)))
    # волны по бокам
    for side in (-1, 1):
        for i in range(3):
            r = int((52 + i * 34) * s)
            bx = cx + side * (w // 2 + 8)
            d.arc([bx - r, cy - r, bx + r, cy + r],
                  -32 if side > 0 else 148, 32 if side > 0 else 212,
                  fill=ac(col, int((150 - 34 * i) * p)), width=max(2, int(3 * s)))
    cv.alpha_composite(lay)
    slam(cv, "«В ОКОПЕ»", RUSSO, int(100 * s), cx, cy - int(104 * s), ac(TXT, int(255 * p)),
         p, "ma", int(24 * s), maxw=int(w * 0.86))
    if sub:
        slam(cv, "Р А Д И О", MONO, int(28 * s), cx, cy - int(14 * s), ac(col, int(250 * p)),
             p, "ma", 8)
        slam(cv, "24 / 7", COND, int(62 * s), cx, cy + int(30 * s), ac(TXT, int(250 * p)),
             p, "ma", 14)
    if glow > 0:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rectangle(box, fill=ac(col, int(26 * glow * p)))
        cv.alpha_composite(g.filter(ImageFilter.GaussianBlur(int(46 * s))))


def eq_bars(cv, x, y, w, h, n, vals, col=OLV, alpha=255, mirror=True, gap=4, cap=1.0):
    """Эквалайзер по реальному спектру кадра."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bw = (w - gap * (n - 1)) / float(n)
    for i in range(n):
        v = cl(vals[i] if i < len(vals) else 0.0) * cap
        bh = max(3, int(h * v))
        x0 = x + i * (bw + gap)
        if mirror:
            d.rectangle([x0, y - bh, x0 + bw, y + bh], fill=ac(col, int(alpha * (0.45 + 0.55 * v))))
        else:
            d.rectangle([x0, y + h - bh, x0 + bw, y + h], fill=ac(col, int(alpha * (0.45 + 0.55 * v))))
    cv.alpha_composite(lay)


def waveform(cv, x, y, w, h, vals, col=AMBER, alpha=210, lw=3):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        px = x + w * i / max(1, n - 1)
        pts.append((px, y - h * (v - 0.5) * 2))
    d.line(pts, fill=ac(col, alpha), width=lw, joint="curve")
    cv.alpha_composite(lay)


def dial(cv, cx, cy, r, freq, p=1.0, col=AMBER, ticks=44):
    """Круглая шкала настройки приёмника со стрелкой."""
    if p <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ac((8, 8, 6), int(225 * p)),
              outline=ac(col, int(120 * p)), width=3)
    for i in range(ticks):
        a = math.radians(-210 + 240 * i / (ticks - 1))
        r0 = r * (0.82 if i % 4 else 0.74)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                (cx + r * 0.93 * math.cos(a), cy + r * 0.93 * math.sin(a))],
               fill=ac(col, int((150 if i % 4 else 235) * p)), width=2 if i % 4 else 3)
    d.arc([cx - r * 0.66, cy - r * 0.66, cx + r * 0.66, cy + r * 0.66],
          -210, -210 + 240, fill=ac(OLV2, int(120 * p)), width=2)
    a = math.radians(-210 + 240 * cl(freq))
    d.line([(cx, cy), (cx + r * 0.80 * math.cos(a), cy + r * 0.80 * math.sin(a))],
           fill=ac(RED, int(240 * p)), width=5)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=ac(col, int(245 * p)))
    cv.alpha_composite(lay)


def interference(cv, t, amount=1.0, seed=0):
    """Полосы помех и срыв строки — как на аналоговом приёмнике."""
    if amount <= 0:
        return
    rnd = random.Random(int(t * 24) + seed * 97)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(int(4 * amount)):
        yy = rnd.randint(100, H - 130)
        hh = rnd.randint(2, 9)
        a = rnd.randint(14, 46)
        d.rectangle([rnd.randint(0, W // 3), yy, rnd.randint(2 * W // 3, W), yy + hh],
                    fill=(230, 240, 225, int(a * amount)))
    for _ in range(int(2 * amount)):
        yy = rnd.randint(100, H - 130)
        d.rectangle([rnd.randint(0, W // 2), yy, rnd.randint(W // 2, W), yy + rnd.randint(2, 6)],
                    fill=ac(OLV, rnd.randint(18, 46)))
    cv.alpha_composite(lay)


def sweep(cv, t, col=OLV, alpha=90, period=1.6, y0=120, y1=H - 130):
    """Бегущая строка развёртки."""
    k = ((t % period) / period)
    yy = int(y0 + (y1 - y0) * k)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(24):
        a = int(alpha * (1 - i / 24.0))
        d.line([(0, yy - i), (W, yy - i)], fill=ac(col, a))
    cv.alpha_composite(lay)


def onair(cv, cx, cy, t, p=1.0, label="В ЭФИРЕ"):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    b = 0.55 + 0.45 * math.sin(t * 6.0)
    f = F(MONO, 26)
    tw = int(f.getlength(label))
    d.rectangle([cx - tw // 2 - 60, cy - 26, cx + tw // 2 + 20, cy + 26],
                fill=ac((20, 6, 5), int(220 * p)), outline=ac(RED, int(190 * p)))
    d.ellipse([cx - tw // 2 - 46, cy - 11, cx - tw // 2 - 24, cy + 11],
              fill=ac(RED, int((120 + 135 * b) * p)))
    d.text((cx - tw // 2 - 12, cy - 13), label, font=f, fill=ac((255, 210, 200), int(240 * p)))
    cv.alpha_composite(lay)


def vinyl_ring(cv, cx, cy, r, t, col=OLV, p=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(5):
        rr = r * (0.4 + i * 0.15)
        a = int((60 - i * 8) * p * (0.6 + 0.4 * math.sin(t * 2 + i)))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=ac(col, a), width=2)
    cv.alpha_composite(lay)


def end_card(cv, d, l, accent=OLV, tag="r15"):
    """Финальная карточка: знак, слоган, площадки."""
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((7, 8, 6), 255)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(accent, int(26 * (1 - k) ** 2)))
    cv.alpha_composite(g)
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-700 + (cl(l / 2.6) ** 0.85) * (W + 1400))
    ds.polygon([(x, 0), (x + 220, 0), (x + 220 - 430, H), (x - 430, H)], fill=ac(accent, 20))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(16)))
    logo_mark(cv, 540, 520, min(1.0, 0.7 + 0.3 * eo(l / 0.4)), c01((l - .04) / .30), accent, 0.8)
    if l > .34:
        p = c01((l - .34) / .28)
        slam(cv, "МЫ ТАМ, ГДЕ НАШИ", RUSSO, 58, 540, 730, ac(TXT, 250 * p), p, "ma", 22, maxw=940)
    if l > .56:
        p = c01((l - .56) / .28)
        d.rectangle([540 - int(290 * eo(p)), 800, 540 + int(290 * eo(p)), 807], fill=ac(accent, 220))
    if l > .70:
        p = c01((l - .70) / .26)
        slam(cv, "СЛУШАЙ ВКОНТАКТЕ И В TELEGRAM", MONO, 25, 540, 850, ac(DIM, 240 * p), p, "ma", 12, maxw=900)
        slam(cv, "t.me/vokope_ru   ·   vk.com/vokope_rus", MONO, 27, 540, 906, ac(KHAKI, 242 * p), p, "ma", 12)
    if l > .92:
        p = c01((l - .92) / .30)
        chips_row(d, 1010, [("24 / 7 · БЕЗ ОСТАНОВОК", accent, True)], int(255 * p), size=26)
    if l > .3:
        q = c01((l - .3) / .5)
        d.rectangle([46, 190, W - 46, H - 250], outline=ac(accent, int(64 * q)), width=4)
        tick_marks(d, accent, int(86 * q))
