# -*- coding: utf-8 -*-
"""Графика передачи «СВОДКА» — 1280×720, 25 fps, тёмно-зелёный + золото.

Требования ТЗ: без чужих логотипов и водяных знаков, крупный читаемый текст,
щит с «В ОКОПЕ · РАДИО» сверху, заголовок «СВОДКА» и дата, тезисы по ходу озвучки.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1280, 720, 25
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
FD = os.path.join(ROOT, "video_studio", "toolkit", "fonts")

# палитра: тёмно-зелёный/чёрный, золото
BG0 = (10, 14, 11)
BG1 = (4, 6, 5)
OLV = (150, 176, 96)
GOLD = (214, 176, 92)
GOLD2 = (168, 132, 62)
TXT = (243, 245, 238)
DIM = (150, 158, 144)
RED = (206, 78, 62)

RUSSO = "RussoOne-Regular.ttf"
MONO = "JetBrainsMono-VF.ttf"
COND = "FiraSansExtraCondensed-Black.ttf"
UNB = "Unbounded-VF.ttf"


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
    c = 2.2
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────────── фон
def _grad(w, h, c0, c1, dither=1.6):
    a = np.zeros((h, w, 3), np.float32)
    v = np.linspace(0, 1, h)[:, None]
    for i in range(3):
        a[:, :, i] = c0[i] + (c1[i] - c0[i]) * v
    # дизеринг: иначе на градиенте видны полосы после H.264
    rng = np.random.default_rng(11)
    a += rng.normal(0, dither, (h, w, 3))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


STAGE = _grad(W, H, (22, 30, 22), (6, 9, 7))

# диагональная штриховка
_hatch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_dh = ImageDraw.Draw(_hatch)
for x in range(-H, W + H, 26):
    _dh.line([(x, H), (x + H, 0)], fill=(120, 140, 90, 7), width=1)
STAGE = Image.alpha_composite(STAGE, _hatch)

# виньетка
VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(90):
    k = i / 90
    ins = int(-120 + k * 300)
    _v.ellipse([ins, ins * 0.68, W - ins, H - ins * 0.68], outline=(0, 0, 0, int(4 + k * 3)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(22))

# зерно
_rng = np.random.default_rng(5)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 16, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 10))))


_GLOW = None


def _make_glow():
    """Мягкое оливковое свечение сверху слева — без швов и без движения."""
    h = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(h)
    d.ellipse([-160, -200, 640, 260], fill=26)
    h = h.filter(ImageFilter.GaussianBlur(44)).resize((W, H), Image.BILINEAR)
    lay = Image.new("RGBA", (W, H), ac(OLV, 255))
    lay.putalpha(h)
    return lay


def stage(cv, t=0.0, warm=0.0):
    global _GLOW
    if _GLOW is None:
        _GLOW = _make_glow()
    cv.alpha_composite(STAGE)
    cv.alpha_composite(_GLOW)
    if warm > 0:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rectangle([0, 0, W, H], fill=ac(GOLD, int(10 * warm)))
        cv.alpha_composite(g)


def scanlines(cv):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, 14))
    cv.alpha_composite(lay)
    cv.alpha_composite(VIGN)


def grain(cv, t):
    cv.alpha_composite(GRAIN[int(t * 12) % 4])


def sweep(cv, t, period=9.0):
    """Медленный световой блик сверху вниз — тонкая линия с мягким ореолом."""
    k = (t % period) / period
    y = int(-80 + (H + 160) * k)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(1, 34):
        a = max(0, int(11 * (1 - i / 34) ** 2))
        if a:
            d.line([(0, y - i), (W, y - i)], fill=ac(OLV, a))
            d.line([(0, y + i // 3), (W, y + i // 3)], fill=ac(OLV, a // 2))
    d.line([(0, y), (W, y)], fill=ac(GOLD, 16))
    cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2.0)))


# ─────────────────────────────── текст
def _lay(s, fn, size, col, stroke=0, scol=None):
    f = F(fn, size)
    w = int(f.getlength(s)) + 40 + stroke * 2
    lay = Image.new("RGBA", (max(2, w), int(size * 1.4) + stroke * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 + stroke, 4 + stroke), s, font=f, fill=col,
                             stroke_width=stroke, stroke_fill=scol)
    return lay


def text(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", maxw=None, stroke=0, scol=None,
         track=None):
    if p <= 0 or not s:
        return
    lay = _lay(s, fn, size, col, stroke, scol)
    lim = maxw or (W - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    al = eo(min(1, p * 2.6))
    if al < 0.995:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    cv.alpha_composite(lay, (px, py))


def slam(cv, s, fn, size, x, y, col, p=1.0, anchor="lt", maxw=None, track=18):
    """Появление с наездом — для заголовков."""
    if p <= 0:
        return
    lay = _lay(s, fn, size, col)
    lim = maxw or (W - 80)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.14 * (1 - eb(p))
    if abs(k - 1) > 0.01:
        lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.4))
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor[0] == "m" else int(x)
    py = int(y - lay.height / 2) if len(anchor) > 1 and anchor[1] == "m" else int(y)
    cv.alpha_composite(lay, (px, py))


def plate(cv, box, fill=(8, 11, 9), alpha=230, outline=None, oalpha=200, width=2, accent=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle(box, fill=ac(fill, alpha), outline=ac(outline, oalpha) if outline else None, width=width)
    if accent:
        d.rectangle([box[0], box[1], box[0] + 6, box[3]], fill=ac(accent, 245))
    cv.alpha_composite(lay)


def chip(d, x, y, s, col=OLV, size=22, h=44, alpha=255, solid=False):
    f = F(MONO, size)
    w = int(f.getlength(s))
    d.rectangle([x, y, x + w + 32, y + h],
                fill=ac(col if solid else (9, 12, 10), int(alpha * (0.95 if solid else 0.92))),
                outline=ac(col, int(alpha * 0.9)))
    d.text((x + 16, y + (h - size) / 2 - 4), s, font=f,
           fill=ac((9, 12, 10) if solid else col, alpha))
    return w + 32


def chips_row(d, y, items, alpha=255, size=22, gap=12, h=None):
    h = h or int(44 * size / 22)
    ws = [int(F(MONO, size).getlength(s)) + 32 for s, _, _ in items]
    total = sum(ws) + gap * (len(items) - 1)
    x = int((W - total) / 2)
    for (s, col, solid), w in zip(items, ws):
        chip(d, x, y, s, col, size, h, alpha, solid)
        x += w + gap


# ─────────────────────────────── фирменные элементы
def shield(cv, x, y, h, p=1.0, col=GOLD):
    """Лого-щит: контур щита, внутри «В ОКОПЕ», под ним «РАДИО»."""
    if p <= 0:
        return
    w = int(h * 0.82)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x, y), (x + w, y), (x + w, y + h * 0.52),
           (x + w * 0.5, y + h), (x, y + h * 0.52)]
    d.polygon(pts, fill=ac((10, 14, 10), int(250 * p)))
    d.line(pts + [pts[0]], fill=ac(col, int(235 * p)), width=max(2, int(h * 0.035)), joint="curve")
    d.line([(x + w * 0.5, y + h * 0.10), (x + w * 0.5, y + h * 0.16)],
           fill=ac(col, int(90 * p)), width=2)
    cv.alpha_composite(lay)
    text(cv, "В", RUSSO, int(h * 0.34), x + w * 0.36, y + h * 0.20, ac(TXT, 250 * p), p, "mt", )
    text(cv, "О", RUSSO, int(h * 0.34), x + w * 0.64, y + h * 0.20, ac(TXT, 250 * p), p, "mt")


def header(cv, d, t, total, date_txt, shift, accent=GOLD):
    """Верхняя плашка: щит, «В ОКОПЕ · РАДИО», дата, утро/вечер."""
    d.rectangle([0, 0, W, 64], fill=(6, 9, 7, 232))
    d.rectangle([0, 0, W, 3], fill=ac(accent, 255))
    shield(cv, 26, 10, 44, 1.0, accent)
    text(cv, "В ОКОПЕ", RUSSO, 25, 76, 17, ac(TXT, 255), 1.0)
    text(cv, "РАДИО", MONO, 15, 77, 42, ac(accent, 245), 1.0)
    d.line([(196, 16), (196, 50)], fill=ac(accent, 90), width=2)
    text(cv, "СВОДКА · ЕЖЕДНЕВНО", MONO, 14, 212, 26, ac(DIM, 225), 1.0)
    # дата справа
    text(cv, date_txt.upper(), RUSSO, 21, W - 214, 14, ac(TXT, 240), 1.0, "rt")
    text(cv, shift.upper(), MONO, 15, W - 214, 40, ac(accent, 240), 1.0, "rt")
    # прогресс
    d.rectangle([0, 64, W, 67], fill=(18, 22, 17, 235))
    d.rectangle([0, 64, int(W * cl(t / max(total, .01))), 67], fill=ac(accent, 235))


def footer(cv, d, t, total):
    d.rectangle([0, H - 34, W, H], fill=(4, 6, 5, 244))
    text(cv, "t.me/vokope_ru   ·   vk.com/vokope_rus", MONO, 16, W // 2, H - 27,
         ac(GOLD, 225), 1.0, "ma")
    # таймкод
    mm, ss = int(t // 60), int(t % 60)
    tm, ts = int(total // 60), int(total % 60)
    text(cv, "%02d:%02d / %02d:%02d" % (mm, ss, tm, ts), MONO, 14, 18, H - 26,
         ac(DIM, 210), 1.0)


def tick_marks(d, col=GOLD, alpha=70):
    for (x, y, sx, sy) in ((14, 84, 1, 1), (W - 14, 84, -1, 1),
                           (14, H - 48, 1, -1), (W - 14, H - 48, -1, -1)):
        d.line([(x, y), (x + sx * 26, y)], fill=ac(col, alpha), width=2)
        d.line([(x, y), (x, y + sy * 26)], fill=ac(col, alpha), width=2)


def subtitle(cv, s, p=1.0, accent=GOLD, size=34):
    """Нижняя строка тезиса — крупно, с плашкой."""
    if not s or p <= 0:
        return
    maxw = W - 160
    f = F(COND, size)
    # перенос по словам в 2 строки максимум
    words = s.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    lines = lines[:2]
    lh = int(size * 1.06)
    box_h = lh * len(lines) + 30
    y0 = H - 34 - box_h - 10
    plate(cv, [60, y0, W - 60, y0 + box_h], (7, 10, 8), int(214 * p), accent, int(90 * p), 1)
    for i, ln in enumerate(lines):
        text(cv, ln, COND, size, W // 2, y0 + 15 + i * lh, ac(TXT, 252 * p), p, "mt", maxw=maxw)


def counter(cv, num, label, p=1.0, accent=GOLD):
    """Крупный номер слева: 01/02/…"""
    if p <= 0:
        return
    slam(cv, num, COND, 150, 92, 300, ac(accent, 245 * p), p, "lt", maxw=200)
    text(cv, label.upper(), MONO, 17, 96, 462, ac(DIM, 235 * p), p, "lt")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rectangle([92, 448, 92 + int(120 * eo(p)), 451], fill=ac(accent, 220))
    cv.alpha_composite(lay)
