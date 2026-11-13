# -*- coding: utf-8 -*-
"""Сетка и типографика для прайс-роликов. Версия 2.

Главное отличие от первой версии: каждый блок знает свою высоту, элементы
ставятся друг за другом, а все текстовые боксы регистрируются и в конце
кадра проверяются на пересечения. Наложение текста на текст становится
ошибкой сборки, а не сюрпризом в эфире.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.abspath(__file__))
FD = "/home/user/-/video_studio/toolkit/fonts"

# палитра серии
BG0 = (28, 35, 23)
BG1 = (14, 18, 12)
TXT = (237, 232, 215)
LIME = (201, 242, 75)
DIM = (150, 154, 141)
INK = (20, 24, 16)

OSW = "Oswald-VF.ttf"      # заголовки и цифры: чистая кириллица, есть ₽
TEK = "Tektur-VF.ttf"      # только латинские/цифровые подписи
MONT = "Montserrat-VF.ttf"

# зоны кадра
TOP = 148          # ниже HUD
BOT = 1740         # выше нижней плашки
MARGIN = 76

_boxes = []


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), s)


def cl(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


c01 = cl


def eo(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ─────────────────────────── проверка вёрстки
def reset_boxes():
    _boxes.clear()


def reg(name, x0, y0, x1, y1):
    _boxes.append((name, x0, y0, x1, y1))


def collisions(pad=2):
    """Возвращает пары пересекающихся блоков (без учёта вложенности)."""
    out = []
    n = len(_boxes)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = _boxes[i], _boxes[j]
            if a[1] < b[3] - pad and b[1] < a[3] - pad and a[2] < b[4] - pad and b[2] < a[4] - pad:
                out.append((a[0], b[0], (a[1], a[2], a[3], a[4]), (b[1], b[2], b[3], b[4])))
    return out


# ─────────────────────────── фон
def _bg():
    a = np.zeros((H, W, 3), np.float32)
    v = np.linspace(0, 1, H)[:, None]
    for i in range(3):
        a[:, :, i] = BG1[i] + (BG0[i] - BG1[i]) * v
    im = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(gl)
    for i in range(16):
        r = 880 - i * 36
        d.ellipse([W / 2 - r, 420 - r * 0.6, W / 2 + r, 420 + r * 0.6], fill=(120, 150, 50, 4))
    return Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(130)))


STAGE = _bg()

_rng = np.random.default_rng(5)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 18, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 11))))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(110):
    k = i / 110
    ins = int(-180 + k * 420)
    _v.ellipse([ins, ins * 1.05, W - ins, H - ins * 1.05], outline=(0, 0, 0, int(3 + k * 2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(34))


def stage(cv, glow=0.0, t=0.0, accent=LIME):
    cv.alpha_composite(STAGE)
    if glow > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        r = 520 + 40 * np.sin(t * 1.1)
        d.ellipse([W / 2 - r, 700 - r * 0.7, W / 2 + r, 700 + r * 0.7], fill=ac(accent, int(14 * glow)))
        cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(120)))


_T = 0.0


def grid(d, alpha=10, col=LIME, step=120):
    """Сетка ползёт по вертикали — кадр не выглядит стоп-кадром."""
    off = int((_T * 7) % step)
    for i in range(0, W + 1, step):
        d.line([(i, TOP), (i, BOT)], fill=ac(col, alpha), width=1)
    for j in range(TOP - step + off, BOT + step, step):
        d.line([(0, j), (W, j)], fill=ac(col, alpha), width=1)


# ─────────────────────────── текст с учётом bbox
def text(d, s, fn, size, x, y, col, anchor="lt", maxw=None, name=None, alpha=255):
    """Рисует строку и регистрирует её бокс. anchor: l*/m*/r* по X, t/m/b по Y."""
    if alpha <= 0 or not s:
        return 0
    f = F(fn, size)
    w = f.getlength(s)
    if maxw and w > maxw:
        size = max(11, int(size * maxw / w))
        f = F(fn, size)
        w = f.getlength(s)
    asc, desc = f.getmetrics()
    h = asc + desc
    x0 = x - w / 2 if anchor[0] == "m" else (x - w if anchor[0] == "r" else x)
    y0 = y - h / 2 if len(anchor) > 1 and anchor[1] == "m" else (y - h if len(anchor) > 1 and anchor[1] == "b" else y)
    d.text((x0, y0), s, font=f, fill=ac(col, alpha))
    reg(name or s[:18], int(x0), int(y0), int(x0 + w), int(y0 + h))
    return int(h)


def rule(d, y, x0=MARGIN, x1=W - MARGIN, col=LIME, alpha=90, width=2, name="rule"):
    d.rectangle([x0, y, x1, y + width - 1], fill=ac(col, alpha))
    reg(name, x0, y, x1, y + width)


# ─────────────────────────── пиктограммы (линии, без фото)
def icon(d, kind, x, y, s=96, col=LIME, alpha=255, name="icon"):
    """Линейная пиктограмма в квадрате s×s с левым верхним углом (x, y)."""
    a = alpha
    if kind == "van":
        # фургон в профиль: капот, кабина, кузов, купол на крыше, колёса
        b = y + s * .92
        d.line([(x + s * .06, b), (x + s * .06, y + s * .60), (x + s * .20, y + s * .56),
                (x + s * .34, y + s * .40), (x + s * .58, y + s * .38),
                (x + s * .92, y + s * .38), (x + s * .95, y + s * .42),
                (x + s * .95, b)], fill=ac(col, a), width=4)
        d.line([(x + s * .06, b), (x + s * .95, b)], fill=ac(col, a), width=4)
        d.rectangle([x + s * .22, y + s * .44, x + s * .33, y + s * .58], outline=ac(col, a), width=3)
        d.rectangle([x + s * .60, y + s * .44, x + s * .74, y + s * .58], outline=ac(col, a), width=3)
        d.rectangle([x + s * .78, y + s * .44, x + s * .90, y + s * .58], outline=ac(col, a), width=3)
        d.arc([x + s * .38, y + s * .08, x + s * .68, y + s * .38], 180, 360, fill=ac(col, a), width=4)
        d.line([(x + s * .38, y + s * .23), (x + s * .68, y + s * .23)], fill=ac(col, a), width=3)
        for cx in (x + s * .24, x + s * .80):
            d.ellipse([cx - s * .12, b - s * .10, cx + s * .12, b + s * .14], outline=ac(col, a), width=4)
    elif kind == "pack":
        d.rounded_rectangle([x + s * .26, y + s * .24, x + s * .74, y + s * .94], radius=10,
                            outline=ac(col, a), width=4)
        d.arc([x + s * .36, y + s * .06, x + s * .64, y + s * .34], 200, 340, fill=ac(col, a), width=4)
        d.rectangle([x + s * .34, y + s * .50, x + s * .66, y + s * .66], outline=ac(col, a), width=3)
        d.line([(x + s * .26, y + s * .40), (x + s * .16, y + s * .60)], fill=ac(col, a), width=3)
        d.line([(x + s * .74, y + s * .40), (x + s * .84, y + s * .60)], fill=ac(col, a), width=3)
    elif kind == "tower":
        d.line([(x + s * .50, y + s * .96), (x + s * .50, y + s * .30)], fill=ac(col, a), width=5)
        d.line([(x + s * .30, y + s * .96), (x + s * .70, y + s * .96)], fill=ac(col, a), width=5)
        for i, r in enumerate((.10, .18, .26)):
            d.arc([x + s * .50 - s * r, y + s * .30 - s * r, x + s * .50 + s * r, y + s * .30 + s * r],
                  210, 330, fill=ac(col, int(a * (0.9 - i * 0.2))), width=3)
        d.ellipse([x + s * .46, y + s * .24, x + s * .54, y + s * .32], fill=ac(col, a))
    elif kind == "moto":
        for cx in (x + s * .24, x + s * .76):
            d.ellipse([cx - s * .15, y + s * .66, cx + s * .15, y + s * .96], outline=ac(col, a), width=4)
        d.line([(x + s * .24, y + s * .80), (x + s * .46, y + s * .52), (x + s * .70, y + s * .52)],
               fill=ac(col, a), width=4)
        d.line([(x + s * .46, y + s * .52), (x + s * .54, y + s * .80), (x + s * .76, y + s * .80)],
               fill=ac(col, a), width=4)
        d.line([(x + s * .66, y + s * .52), (x + s * .82, y + s * .40)], fill=ac(col, a), width=4)
        d.line([(x + s * .34, y + s * .40), (x + s * .58, y + s * .40)], fill=ac(col, a), width=4)
    reg(name, int(x), int(y), int(x + s), int(y + s))


def badge(d, s, x, y, col=LIME, alpha=255, size=34, fill=None, name=None):
    f = F(OSW, size)
    w = f.getlength(s) + 40
    h = int(size * 1.9)
    d.rectangle([x, y, x + w, y + h], fill=ac(fill or BG1, alpha),
                outline=ac(col, int(alpha * .8)))
    d.rectangle([x, y, x + 4, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size * 1.25) / 2), s, font=f, fill=ac(col, alpha))
    reg(name or "badge:" + s, int(x), int(y), int(x + w), int(y + h))
    return int(w)


# ─────────────────────────── HUD и пост-обработка
def hud(d, t, total, accent=LIME):
    """Верхняя шапка и нижняя плашка канала."""
    d.rectangle([0, 0, W, 128], fill=(15, 19, 13, 240))
    d.rectangle([0, 0, W, 3], fill=ac(accent, 255))
    d.text((44, 18), "В ОКОПЕ", font=F(OSW, 54), fill=ac(TXT, 255))
    d.text((44, 88), "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ", font=F(TEK, 17), fill=ac(DIM, 235))
    b = 0.5 + 0.5 * np.sin(t * 7.0)
    d.ellipse([W - 62, 44, W - 44, 62], fill=ac(accent, int(90 + 150 * b)))
    d.text((W - 76, 40), "REC", font=F(TEK, 17), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / max(total, .01))
    d.rectangle([0, 128, W, 133], fill=(21, 26, 18, 246))
    d.rectangle([0, 128, int(W * p), 133], fill=ac(accent, 250))

    d.rectangle([0, 1762, W, H], fill=(11, 14, 9, 250))
    d.rectangle([0, 1759, W, 1762], fill=ac(accent, 90))
    d.text((W // 2, 1788), "t.me/vokope_ru   ·   vk.com/vokope_rus", font=F(TEK, 24),
           fill=ac(TXT, 240), anchor="ma")
    d.text((W // 2, 1830), "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ · РОЗНИЦА", font=F(TEK, 16),
           fill=ac(DIM, 225), anchor="ma")
    d.text((W // 2, 1868), "@VES_nn  ·  Москва и Липецк", font=F(OSW, 22),
           fill=ac(LIME, 220), anchor="ma")


def punch(im, t, cuts, amp=0.04):
    for c in cuts:
        dd = t - c
        if 0 <= dd < 0.18:
            k = 1 - dd / 0.18
            z = 1 + amp * k
            w, h = int(W / z), int(H / z)
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize((W, H), Image.BILINEAR)
    return im
