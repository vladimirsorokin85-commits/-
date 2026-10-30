# -*- coding: utf-8 -*-
"""«Алдан-12» — вертикальный Reels 9:16. Динамика: бит-монтаж, глитч, кинетика."""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/aldan12"
A = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"
TOTAL = 40.40
BPM = 162.0
BEAT = 60.0 / BPM

SCENES = [
    ("hook", 0.00), ("steps", 5.90), ("qr", 9.90), ("otg", 14.50),
    ("flash", 19.60), ("features", 23.80), ("led", 28.10), ("ascent", 32.00),
]

BG = (7, 8, 10)
ORG = (255, 122, 46)      # акцент из брифа #FF7A2E
TXT = (242, 243, 245)
DIM = (140, 146, 155)
TEA = (46, 200, 190)
RED = (255, 72, 60)

RUSSO, DAYS, MONO = "RussoOne-Regular.ttf", "DaysOne-Regular.ttf", "JetBrainsMono-VF.ttf"


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), s)


def cl(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def c01(x):
    return cl(x)


def eo(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def eb(x):
    x = c01(x)
    c = 2.2
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ── изображения
_CACHE = {}


def img(name, size=None):
    key = (name, size)
    if key in _CACHE:
        return _CACHE[key]
    p = os.path.join(A, name)
    im = Image.open(p).convert("RGBA")
    if size:
        im = im.resize(size, Image.LANCZOS)
    _CACHE[key] = im
    return im


def cover(name, w, h, zoom=1.0, ox=0.0, oy=0.0):
    m = Image.open(os.path.join(A, name)).convert("RGB")
    cs = max(w / m.width, h / m.height) * zoom
    rw, rh = min(w / cs, m.width), min(h / cs, m.height)
    cx = m.width / 2 + cl(ox, -1, 1) * max(0, (m.width - rw) / 2)
    cy = m.height / 2 + cl(oy, -1, 1) * max(0, (m.height - rh) / 2)
    x0 = int(cl(cx - rw / 2, 0, m.width - rw))
    y0 = int(cl(cy - rh / 2, 0, m.height - rh))
    return m.crop((x0, y0, x0 + int(rw), y0 + int(rh))).resize((w, h), Image.LANCZOS)


def grade(im, dark=0.55, con=1.12, sat=0.9, tint=(40, 90, 110), amt=0.06):
    a = np.asarray(im).astype(np.float32)
    a = (a - 128) * con + 128
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * sat
    a *= dark
    a = a * (1 - amt) + np.array(tint, np.float32) * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 22))
SCAN_SOFT = SCAN.copy()
SCAN_SOFT.putalpha(SCAN_SOFT.getchannel("A").point(lambda v: int(v * 0.35)))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(110):
    k = i / 110
    ins = int(-170 + k * 400)
    _v.ellipse([ins, ins * 1.06, W - ins, H - ins * 1.06], outline=(0, 0, 0, int(3 + k * 2)), width=5)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(26))

_r = np.random.default_rng(5)
GRAIN = []
for _ in range(4):
    n = _r.integers(0, 30, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 18))))


def text_lay(s, fn, size, col, track=0):
    f = F(fn, size)
    w = int(f.getlength(s)) + 24 + track * max(0, len(s) - 1)
    lay = Image.new("RGBA", (max(2, w), int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = 12
    for ch in s:
        d.text((x, 4), ch, font=f, fill=col)
        x += f.getlength(ch) + track
    return lay


def slam(cv, s, fn, size, x, y, col, p, anchor="lt", trail=40, dx=1, chroma=True):
    if p <= 0:
        return
    lay = text_lay(s, fn, size, col, track=0)
    maxw = W - 96
    if lay.width > maxw:                    # не даём тексту вылезти за кадр
        lay = lay.resize((maxw, max(2, int(lay.height * maxw / lay.width))), Image.LANCZOS)
    k = 1 + 0.42 * (1 - eb(p))
    lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.0))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor == "ma" else int(x)
    py = int(y - lay.height / 2) if anchor == "mm" else int(y)
    if chroma and p < 0.5:
        ca = int(80 * (1 - p / 0.5))
        for off, c in ((-5, (255, 60, 90)), (5, (60, 200, 255))):
            t = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            t.paste(Image.new("RGBA", lay.size, ac(c, ca)), (0, 0), lay)
            cv.alpha_composite(t, (px + off, py))
    if trail:
        for i in range(4, 0, -1):
            kk = 1 - eo(p)
            ox = int(-dx * trail * i / 4 * kk)
            if not ox:
                continue
            t = lay.copy()
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.14 * (5 - i) / 4 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=ORG, size=26, h=54, alpha=255):
    f = F(MONO, size)
    w = f.getlength(s)
    d.rectangle([x, y, x + w + 40, y + h], fill=ac((10, 11, 14), alpha * 0.9), outline=ac(col, alpha * 0.8))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size) / 2 - 4), s, font=f, fill=ac(col, alpha))
    return w + 40


def speedlines(cv, t, n=12, alpha=60):
    d = ImageDraw.Draw(cv)
    rnd = random.Random(int(t * 24))
    for _ in range(n):
        y0 = rnd.randint(-200, H)
        ln = rnd.randint(140, 420)
        x = int((rnd.randint(0, W) + t * rnd.uniform(2400, 4200)) % (W + 700)) - 350
        d.line([(x, y0), (x + ln * 0.3, y0 - ln)], fill=(225, 240, 255, alpha), width=rnd.choice([1, 2, 3]))


def hud(d, t):
    d.rectangle([0, 0, W, 118], fill=(6, 7, 9, 232))
    d.rectangle([0, 0, W, 4], fill=ac(ORG, 255))
    d.text((44, 28), "«В ОКОПЕ»", font=F(RUSSO, 40), fill=ac(TXT, 255))
    d.text((44, 80), "АЛДАН-12  //  ПРОШИВКА", font=F(MONO, 22), fill=ac(DIM, 230))
    d.text((W - 44, 30), f"{int(t*30):04d}", font=F(MONO, 22), fill=ac(DIM, 190), anchor="ra")
    b = 0.5 + 0.5 * math.sin(t * 7)
    d.ellipse([W - 66, 66, W - 44, 88], fill=ac(RED, int(110 + 130 * b)))
    p = cl(t / TOTAL)
    d.rectangle([0, 118, W, 124], fill=(16, 18, 22, 245))
    d.rectangle([0, 118, int(W * p), 124], fill=ac(ORG, 245))
    d.rectangle([0, H - 128, W, H], fill=(5, 6, 8, 246))
    d.rectangle([0, H - 131, W, H - 127], fill=ac(ORG, 90))
    d.text((W // 2, H - 96), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 26),
           fill=ac(ORG, 240), anchor="ma")
    d.text((W // 2, H - 54), "АЛДАН-12 · ОБНОВЛЕНИЕ", font=F(RUSSO, 20), fill=ac(DIM, 215), anchor="ma")


def plate(cv, name, cx, cy, w, alpha=255, accent=ORG, label="", tilt=0.0, dark=0.45, crop=None):
    """Фото товара в дизайнерской плашке: тёмный грейд, виньетка, акцентная рамка, подпись."""
    if alpha <= 2:
        return
    src = Image.open(os.path.join(A, name)).convert("RGB")
    if crop:
        l, t_, r_, b_ = crop
        src = src.crop((int(src.width * l), int(src.height * t_),
                        int(src.width * r_), int(src.height * b_)))
    st = w / src.width
    ph = src.resize((w, max(1, int(src.height * st))), Image.LANCZOS)
    a = np.asarray(ph).astype(np.float32)
    a = (a - 110) * 1.22 + 96            # контраст + тёмная точка
    a *= dark
    a[:, :, 0] *= 1.06
    a[:, :, 2] *= 0.97
    a = np.clip(a, 0, 255) ** 1.12        # глубже тени
    ph = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # виньетка внутри фото
    vg = Image.new("L", ph.size, 0)
    ImageDraw.Draw(vg).rectangle([0, 0, ph.width, ph.height], fill=255)
    ph = Image.composite(ph, Image.new("RGB", ph.size, (5, 6, 8)), vg)
    ph = ph.convert("RGBA")
    pad = 14
    lab_h = 58 if label else 0
    cw, ch = ph.width + pad * 2, ph.height + pad * 2 + lab_h
    plate_im = Image.new("RGBA", (cw, ch), (9, 10, 13, 252))
    plate_im.paste(ph, (pad, pad))
    d = ImageDraw.Draw(plate_im)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], 10, outline=ac(accent, 225), width=3)
    d.rectangle([0, 0, cw - 1, 7], fill=ac(accent, 255))
    # уголки
    for (x, y, sx, sy) in ((6, 6, 1, 1), (cw - 6, 6, -1, 1), (6, ch - 6, 1, -1), (cw - 6, ch - 6, -1, -1)):
        d.line([(x, y), (x + sx * 34, y)], fill=ac(accent, 255), width=4)
        d.line([(x, y), (x, y + sy * 34)], fill=ac(accent, 255), width=4)
    if label:
        f = F(MONO, 25)
        while f.getlength(label) > cw - 40 and f.size > 13:
            f = F(MONO, f.size - 1)
        d.text((pad + 6, ch - lab_h + 14), label, font=f, fill=ac(accent, 240))
    if tilt:
        plate_im = plate_im.rotate(tilt, expand=True, resample=Image.BICUBIC)
    if alpha < 255:
        plate_im.putalpha(plate_im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    sil = Image.new("RGBA", plate_im.size, (0, 0, 0, 0))
    sil.paste(Image.new("RGBA", plate_im.size, (0, 0, 0, 200)), (0, 0), plate_im)
    sil = sil.filter(ImageFilter.GaussianBlur(34))
    cv.alpha_composite(sil, (int(cx - plate_im.width / 2) + 6, int(cy - plate_im.height / 2) + 14))
    cv.alpha_composite(plate_im, (int(cx - plate_im.width / 2), int(cy - plate_im.height / 2)))


def text_lay(s, fn, size, col, track=0):
    f = F(fn, size)
    w = int(f.getlength(s)) + 24 + track * max(0, len(s) - 1)
    lay = Image.new("RGBA", (max(2, w), int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = 12
    for ch in s:
        d.text((x, 4), ch, font=f, fill=col)
        x += f.getlength(ch) + track
    return lay


def slam(cv, s, fn, size, x, y, col, p, anchor="lt", trail=40, dx=1, chroma=True):
    if p <= 0:
        return
    lay = text_lay(s, fn, size, col, track=0)
    maxw = W - 96
    if lay.width > maxw:                    # не даём тексту вылезти за кадр
        lay = lay.resize((maxw, max(2, int(lay.height * maxw / lay.width))), Image.LANCZOS)
    k = 1 + 0.42 * (1 - eb(p))
    lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.0))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor == "ma" else int(x)
    py = int(y - lay.height / 2) if anchor == "mm" else int(y)
    if chroma and p < 0.5:
        ca = int(80 * (1 - p / 0.5))
        for off, c in ((-5, (255, 60, 90)), (5, (60, 200, 255))):
            t = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            t.paste(Image.new("RGBA", lay.size, ac(c, ca)), (0, 0), lay)
            cv.alpha_composite(t, (px + off, py))
    if trail:
        for i in range(4, 0, -1):
            kk = 1 - eo(p)
            ox = int(-dx * trail * i / 4 * kk)
            if not ox:
                continue
            t = lay.copy()
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.14 * (5 - i) / 4 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=ORG, size=26, h=54, alpha=255):
    f = F(MONO, size)
    w = f.getlength(s)
    d.rectangle([x, y, x + w + 40, y + h], fill=ac((10, 11, 14), alpha * 0.9), outline=ac(col, alpha * 0.8))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 20, y + (h - size) / 2 - 4), s, font=f, fill=ac(col, alpha))
    return w + 40


def speedlines(cv, t, n=12, alpha=60):
    d = ImageDraw.Draw(cv)
    rnd = random.Random(int(t * 24))
    for _ in range(n):
        y0 = rnd.randint(-200, H)
        ln = rnd.randint(140, 420)
        x = int((rnd.randint(0, W) + t * rnd.uniform(2400, 4200)) % (W + 700)) - 350
        d.line([(x, y0), (x + ln * 0.3, y0 - ln)], fill=(225, 240, 255, alpha), width=rnd.choice([1, 2, 3]))


def hud(d, t):
    d.rectangle([0, 0, W, 118], fill=(6, 7, 9, 232))
    d.rectangle([0, 0, W, 4], fill=ac(ORG, 255))
    d.text((44, 28), "«В ОКОПЕ»", font=F(RUSSO, 40), fill=ac(TXT, 255))
    d.text((44, 80), "АЛДАН-12  //  ПРОШИВКА", font=F(MONO, 22), fill=ac(DIM, 230))
    d.text((W - 44, 30), f"{int(t*30):04d}", font=F(MONO, 22), fill=ac(DIM, 190), anchor="ra")
    b = 0.5 + 0.5 * math.sin(t * 7)
    d.ellipse([W - 66, 66, W - 44, 88], fill=ac(RED, int(110 + 130 * b)))
    p = cl(t / TOTAL)
    d.rectangle([0, 118, W, 124], fill=(16, 18, 22, 245))
    d.rectangle([0, 118, int(W * p), 124], fill=ac(ORG, 245))
    d.rectangle([0, H - 128, W, H], fill=(5, 6, 8, 246))
    d.rectangle([0, H - 131, W, H - 127], fill=ac(ORG, 90))
    d.text((W // 2, H - 96), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 26),
           fill=ac(ORG, 240), anchor="ma")
    d.text((W // 2, H - 54), "АЛДАН-12 · ОБНОВЛЕНИЕ", font=F(RUSSO, 20), fill=ac(DIM, 215), anchor="ma")


def key_out(name, w, bg_lum=178.0, floor=118.0):
    """Убирает светлый фон фото (luma key), оставляя товар и мягкую тень."""
    src = Image.open(os.path.join(A, name)).convert("RGB")
    if crop:
        l, t_, r_, b_ = crop
        src = src.crop((int(src.width * l), int(src.height * t_),
                        int(src.width * r_), int(src.height * b_)))
    st = w / src.width
    src = src.resize((w, max(1, int(src.height * st))), Image.LANCZOS)
    a = np.asarray(src).astype(np.float32)
    lum = a.mean(2)
    al = np.clip((bg_lum - lum) / max(1.0, bg_lum - floor), 0, 1)
    al = al ** 0.85
    al = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    out = src.copy()
    # подтянуть тёмное, чтобы на тёмном фоне не было «дыр»
    a2 = np.clip((a - 40) * 1.12 + 26, 0, 255).astype(np.uint8)
    out = Image.fromarray(a2).convert("RGBA")
    out.putalpha(Image.fromarray((al * 255).astype(np.uint8)))
    bb = out.getchannel("A").point(lambda v: 255 if v > 18 else 0).getbbox()
    return out.crop(bb) if bb else out


def card(cv, name, cx, cy, w, alpha=255, accent=ORG, label="", rot=0, tilt=0.0):
    """Реальное фото товара в карточке: белый фон фото тонируется, рамка в акцент."""
    if alpha <= 2:
        return
    ph = key_out(name, w)
    c = Image.new("RGBA", (ph.width + 8, ph.height + (54 if label else 8)), (0, 0, 0, 0))
    c.paste(ph, (4, 4))
    if label:
        dc = ImageDraw.Draw(c)
        f = F(MONO, 25)
        while f.getlength(label) > c.width - 20 and f.size > 14:
            f = F(MONO, f.size - 1)
        dc.text((10, c.height - 44), label, font=f, fill=ac(accent, 235))
        dc.rectangle([10, c.height - 8, min(c.width - 10, 10 + int(f.getlength(label))), c.height - 5],
                     fill=ac(accent, 200))
    if tilt:
        c = c.rotate(tilt, expand=True, resample=Image.BICUBIC)
    if alpha < 255:
        c.putalpha(c.getchannel("A").point(lambda v: int(v * alpha / 255)))
    # мягкая тень-свечение
    sil = Image.new("RGBA", c.size, (0, 0, 0, 0))
    sil.paste(Image.new("RGBA", c.size, ac(accent, 55)), (0, 0), c)
    sil = sil.filter(ImageFilter.GaussianBlur(30))
    cv.alpha_composite(sil, (int(cx - c.width / 2), int(cy - c.height / 2)))
    cv.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))


# ───────────────────────── СЦЕНЫ ─────────────────────────
def s_hook(cv, d, t, l):
    cv.alpha_composite(grade(cover("drone_night.jpg", W, H, 1.02 + .10 * eo(l / 5.9), ox=-0.1 + .2 * eo(l / 5.9)), 0.5, 1.2, 0.8, (20, 70, 90), 0.08))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(H):
        k = y / H
        dd.line([(0, y), (W, y)], fill=(4, 6, 9, int(30 + 170 * cl((k - .2) / .8) ** 1.5)))
    cv.alpha_composite(ov)
    speedlines(cv, t, 14, 55)
    slam(cv, "ОДИН ВИДИТ", RUSSO, 128, 540, 470, ac(TXT, 255), c01((l - .10) / .38), anchor="ma", trail=44)
    slam(cv, "ВТОРОЙ МОЛЧИТ", RUSSO, 108, 540, 620, ac(RED, 255), c01((l - .55) / .38), anchor="ma", trail=40)
    if l > 1.75:
        p = c01((l - 1.75) / .40)
        slam(cv, "ДЕЛО В ПРОШИВКЕ", DAYS, 84, 540, 790, ac(ORG, 255), p, anchor="ma", trail=34)
    if l > 2.5:
        p = eo(c01((l - 2.5) / .5))
        plate(cv, "hero_kit.jpg", 540, 1330, 740, int(255 * p), ORG, "«АЛДАН-12» · КОМПЛЕКТ", tilt=-1.4, dark=0.62, crop=(0.10, 0.00, 0.92, 0.60))
        chip(d, 60, 150, "ВЕРСИЯ РЕШАЕТ", ORG, 28, 56, int(255 * p))
    if l > 4.2:
        q = c01((l - 4.2) / .45)
        d.rectangle([60, 216, 60 + 960 * eo(q), 224], fill=ac(ORG, 220))


def s_steps(cv, d, t, l):
    cv.alpha_composite(grade(cover("hands_phone.jpg", W, H, 1.05 + .05 * l, ox=.05), 0.45, 1.15, 0.75, (30, 60, 70), 0.06))
    d.rectangle([0, 300, W, 1500], fill=(4, 5, 7, 150))
    k = 1 + .25 * (1 - eb(c01(l / .5)))
    big = text_lay("8", RUSSO, 620, ac(ORG, 235))
    big = big.resize((int(big.width * k), int(big.height * k)), Image.BILINEAR)
    cv.alpha_composite(big, (int(70 - big.width * .12), 380))
    slam(cv, "ШАГОВ", RUSSO, 150, 540, 900, ac(TXT, 255), c01((l - .15) / .4), anchor="ma", trail=40)
    if l > .9:
        slam(cv, "БЕЗ КОМПЬЮТЕРА", DAYS, 86, 540, 1060, ac(TEA, 255), c01((l - .9) / .4), anchor="ma", trail=30)
    chip(d, 70, 1640, "ТОЛЬКО ТЕЛЕФОН + КАБЕЛЬ", ORG, 26, 56, int(255 * c01((l - 1.4) / .4)))


def s_qr(cv, d, t, l):
    cv.alpha_composite(grade(cover("dark_table.jpg", W, H, 1.06, oy=-.1), 0.42, 1.1, 0.85, (30, 55, 60), 0.05))
    steps = [("QR-КОД", 0.10), ("КАНАЛ", 0.95), ("ПРИЛОЖЕНИЕ", 1.80)]
    y = 430
    for i, (name, st) in enumerate(steps):
        p = c01((l - st) / .38)
        if p <= 0:
            continue
        yy = y + i * 330
        dx = int((1 - eb(p)) * 420)
        d.rectangle([60 - dx, yy, W - 60 - dx, yy + 260], fill=(10, 11, 14, int(238 * eo(p))),
                    outline=ac(ORG, int(200 * eo(p))))
        d.rectangle([60 - dx, yy, 70 - dx, yy + 260], fill=ac(ORG, 255))
        d.text((110 - dx, yy + 40), f"0{i+1}", font=F(MONO, 46), fill=ac(ORG, 245))
        d.text((110 - dx, yy + 110), name, font=F(RUSSO, 92 if len(name) < 8 else 74), fill=ac(TXT, 255))
    # телефон-контур справа
    p = eo(c01((l - .3) / .6))
    if p > 0:
        d.rounded_rectangle([806, 1290, 1006, 1580], 24, outline=ac(ORG, int(170 * p)), width=5,
                            fill=(9, 10, 13, int(200 * p)))
        d.rectangle([832, 1326, 980, 1544], fill=ac((20, 24, 30), int(190 * p)))
        sweep = (t * 300) % 300
        d.line([(832, 1326 + sweep * .7), (980, 1326 + sweep * .7)], fill=ac(ORG, int(120 * p)), width=3)
    chip(d, 70, 1640, "ОДИН КОД ВЕДЁТ КО ВСЕМУ", TEA, 25, 54, int(255 * c01((l - 2.1) / .4)))


def s_otg(cv, d, t, l):
    cv.alpha_composite(grade(cover("firmware_drop.jpg", W, H, 1.04 + .04 * l), 0.4, 1.15, 0.8, (30, 55, 60), 0.06))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    dd.rectangle([0, 0, W, 760], fill=(4, 6, 9, 190))
    dd.rectangle([0, 1420, W, H], fill=(4, 6, 9, 210))
    cv.alpha_composite(ov)
    slam(cv, "ДВЕ КНОПКИ", RUSSO, 104, 540, 330, ac(TXT, 255), c01((l - .10) / .38), anchor="ma", trail=38)
    slam(cv, "РЕЖИМ ПРОШИВКИ", DAYS, 80, 540, 470, ac(ORG, 255), c01((l - .55) / .38), anchor="ma", trail=30)
    # схема: две боковые кнопки = режим прошивки
    if l > .95:
        q = c01((l - .95) / .40)
        bx0, by0, bx1, by1 = 372, 930, 752, 1360
        d.rounded_rectangle([bx0, by0, bx1, by1], 34, fill=(16, 19, 24, int(238 * q)),
                            outline=ac(ORG, int(200 * q)), width=4)
        d.rounded_rectangle([bx0 + 44, by0 + 70, bx1 - 44, by0 + 250], 14,
                            fill=(8, 9, 11, int(240 * q)), outline=ac(DIM, int(120 * q)))
        d.text((540, by0 + 160), "АЛДАН-12", font=F(MONO, 34), fill=ac(DIM, int(230 * q)), anchor="mm")
        for i in range(12):
            d.rounded_rectangle([bx0 + 56 + (i % 4) * 78, by1 - 150 + (i // 4) * 40,
                                 bx0 + 106 + (i % 4) * 78, by1 - 122 + (i // 4) * 40], 8,
                                fill=ac((44, 48, 56), int(220 * q)))
        # обе боковые кнопки на левом боку: верхняя и нижняя
        for ky, lab, ph in ((by0 + 70, "ВЕРХНЯЯ БОКОВАЯ", .0), (by0 + 232, "НИЖНЯЯ БОКОВАЯ", .5)):
            pulse = .55 + .45 * math.sin((t * 3.4) - ph * 6.28)
            d.rounded_rectangle([bx0 - 30, ky, bx0 + 24, ky + 92], 12,
                                fill=ac(ORG, int((140 + 115 * pulse) * q)))
            d.line([(bx0 - 36, ky + 46), (bx0 - 96, ky + 46)], fill=ac(TEA, int(180 * q)), width=3)
            d.text((bx0 - 108, ky + 46), lab, font=F(MONO, 23), fill=ac(TEA, int(238 * q)), anchor="rm")
        d.text((540, by1 + 46), "ЗАЖАТЬ ОБЕ ОДНОВРЕМЕННО", font=F(MONO, 26),
               fill=ac(TXT, int(225 * q)), anchor="ma")
    if l > 1.9:
        p = c01((l - 1.9) / .4)
        chip(d, 70, 1560, "КАБЕЛЬ USB TYPE-C", ORG, 26, 56, int(255 * p))
        chip(d, 70, 1640, "OTG — В НАСТРОЙКАХ", ORG, 26, 56, int(255 * c01((l - 2.2) / .4)))


def s_flash(cv, d, t, l):
    cv.alpha_composite(grade(cover("spectrum.jpg", W, H, 1.06, ox=-.05), 0.45, 1.15, 0.9, (25, 70, 85), 0.08))
    slam(cv, "МЕСТНАЯ", RUSSO, 118, 540, 620, ac(TXT, 255), c01((l - .08) / .36), anchor="ma", trail=40)
    slam(cv, "ПРОШИВКА", RUSSO, 118, 540, 760, ac(ORG, 255), c01((l - .45) / .36), anchor="ma", trail=40)
    # прогресс
    if l > 1.3:
        p = cl((l - 1.3) / 1.5)
        y = 940
        d.rectangle([90, y, 990, y + 46], fill=(12, 14, 18, 240), outline=ac(ORG, 190))
        d.rectangle([90, y, 90 + int(900 * p), y + 46], fill=ac(ORG, 245))
        d.text((540, y + 66), f"{int(p*100)} %", font=F(MONO, 40), fill=ac(TXT, 240), anchor="ma")
    if l > 2.9:
        q = eo(c01((l - 2.9) / .5))
        d.rectangle([90, 1090, 990, 1260], fill=(10, 22, 20, int(240 * q)), outline=ac(TEA, int(220 * q)))
        d.text((540, 1124), "ВЕРСИЯ 1.6", font=F(RUSSO, 82), fill=ac(TEA, int(255 * q)), anchor="ma")
        d.text((540, 1212), "СОВПАЛО — ГОТОВО", font=F(MONO, 26), fill=ac(DIM, int(240 * q)), anchor="ma")
    chip(d, 70, 1640, "ПРИБОР ВЫКЛЮЧИЛСЯ — ЭТО НОРМА", TEA, 24, 54, int(255 * c01((l - 3.4) / .4)))


def s_features(cv, d, t, l):
    cv.alpha_composite(grade(cover("roof_antenna.jpg", W, H, 1.05, oy=.08), 0.38, 1.12, 0.8, (25, 60, 80), 0.07))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    dd.rectangle([0, 240, W, 1740], fill=(4, 5, 8, 170))
    cv.alpha_composite(ov)
    slam(cv, "5 ФУНКЦИЙ", RUSSO, 150, 540, 360, ac(ORG, 255), c01((l - .08) / .4), anchor="ma", trail=46)
    for i in range(5):
        p = c01((l - .35 - i * .08) / .3)
        if p <= 0:
            continue
        x = 80 + i * 190
        d.rectangle([x, 560, x + 150, 570], fill=ac(ORG, int(230 * p)))
    rows = [("БЫСТРЫЕ КЛАВИШИ", 0.85), ("РЕЖИМ «ШТУРМ»", 1.55), ("СВЕТОДИОД · ЯРКОСТЬ", 2.25)]
    for i, (s, st) in enumerate(rows):
        p = c01((l - st) / .36)
        if p <= 0:
            continue
        yy = 700 + i * 300
        dx = int((1 - eb(p)) * 340)
        d.rectangle([60 - dx, yy, W - 60 - dx, yy + 240], fill=(10, 11, 14, int(236 * eo(p))),
                    outline=ac(ORG, int(190 * eo(p))))
        d.rectangle([60 - dx, yy, 68 - dx, yy + 240], fill=ac(ORG, 255))
        d.text((104 - dx, yy + 34), f"0{i+1}", font=F(MONO, 40), fill=ac(ORG, 240))
        d.text((104 - dx, yy + 96), s, font=F(RUSSO, 62 if len(s) > 14 else 72), fill=ac(TXT, 255))


def s_led(cv, d, t, l):
    base = Image.new("RGBA", (W, H), ac((4, 4, 6), 255))
    cv.alpha_composite(base)
    if l > 0.2:
        plate(cv, "hero_kit.jpg", 540, 700, 760, int(120 * c01((l - 0.2) / .6)), ORG, "",
              dark=0.34, crop=(0.10, 0.0, 0.94, 0.60))
        ov2 = Image.new("RGBA", (W, H), (4, 4, 6, 96))
        cv.alpha_composite(ov2)
    # гаснущий светодиод
    pulse = max(0.0, 1.0 - l / 1.4)
    if pulse > 0.02:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        r = int(160 + 60 * math.sin(t * 6))
        gd.ellipse([540 - r, 760 - r, 540 + r, 760 + r], fill=ac((255, 60, 40), int(120 * pulse)))
        cv.alpha_composite(gl.filter(ImageFilter.GaussianBlur(40)))
    d.ellipse([512, 732, 568, 788], fill=ac((70, 20, 16), 255),
              outline=ac((255, 70, 50), int(220 * pulse)))
    slam(cv, "СВЕТОДИОД — ВЫКЛ", RUSSO, 86, 540, 1080, ac(TXT, 255), c01((l - .35) / .38), anchor="ma", trail=34)
    slam(cv, "ЯРКОСТЬ — ДО НУЛЯ", RUSSO, 86, 540, 1190, ac(ORG, 255), c01((l - 1.0) / .38), anchor="ma", trail=34)
    if l > 1.9:
        chip(d, 70, 1560, "ПОЗИЦИЯ НЕ ВЫДАЁТ СЕБЯ", TEA, 26, 56, int(255 * c01((l - 1.9) / .4)))
    if l > 2.4:
        chip(d, 70, 1640, "НАСТРОЙКИ → LED → ВЫКЛ", ORG, 25, 54, int(255 * c01((l - 2.4) / .4)))


def s_ascent(cv, d, t, l):
    cv.alpha_composite(grade(cover("spectrum.jpg", W, H, 1.10, ox=.08), 0.35, 1.2, 0.95, (30, 80, 95), 0.09))
    speedlines(cv, t, 10, 45)
    slam(cv, "ASCENT", RUSSO, 130, 540, 470, ac(TXT, 255), c01((l - .10) / .38), anchor="ma", trail=44)
    slam(cv, "5800 МГЦ", DAYS, 132, 540, 640, ac(ORG, 255), c01((l - .55) / .40), anchor="ma", trail=44)
    if l > 1.7:
        p = eo(c01((l - 1.7) / .5))
        d.rectangle([70, 900, 1010, 1160], fill=(10, 12, 16, int(240 * p)), outline=ac(ORG, int(210 * p)))
        d.text((540, 936), "ПОЛНЫЙ РАЗБОР", font=F(RUSSO, 56), fill=ac(TXT, int(255 * p)), anchor="ma")
        d.text((540, 1014), "8 ШАГОВ + 5 ФУНКЦИЙ", font=F(MONO, 32), fill=ac(ORG, int(245 * p)), anchor="ma")
        d.text((540, 1074), "НА КАНАЛЕ «В ОКОПЕ»", font=F(MONO, 30), fill=ac(DIM, int(240 * p)), anchor="ma")
    if l > 3.0:
        q = eo(c01((l - 3.0) / .6))
        plate(cv, "watch_close.jpg", 540, 1460, 620, int(255 * q), TEA, "ЧАСЫ ОПОВЕЩЕНИЯ · КНОПКА 5T", dark=1.0, crop=(0.06, 0.03, 0.94, 0.92))
    # финальный флеш-эндкард
    if l > 6.45:
        p = eo(c01((l - 6.45) / .26))
        d.rectangle([0, 0, W, H], fill=(5, 6, 8, int(255 * p)))
        d.rectangle([0, 0, W, 8], fill=ac(ORG, int(255 * p)))
        d.text((540, 760), "«В ОКОПЕ»", font=F(RUSSO, 108), fill=ac(TXT, int(255 * p)), anchor="ma")
        d.text((540, 900), "АЛДАН-12 · ПРОШИВКА", font=F(MONO, 32), fill=ac(ORG, int(245 * p)), anchor="ma")
        for i, s in enumerate(("t.me/vokope_ru", "vk.com/vokope_rus", "avito.ru/brands/…")):
            qq = c01((l - 6.78 - i * .16) / .30)
            if qq <= 0:
                continue
            d.text((540, 1060 + i * 110), s, font=F(MONO, 42), fill=ac(TXT, int(250 * qq)), anchor="ma")
        blink = (.84 + .16 * math.sin(t * 5)) * c01((l - 7.0) / .25)
        d.text((540, 1520), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 60), fill=ac(ORG, int(255 * blink * p)), anchor="ma")


FN = {"hook": s_hook, "steps": s_steps, "qr": s_qr, "otg": s_otg,
      "flash": s_flash, "features": s_features, "led": s_led, "ascent": s_ascent}


def rgb_split(im, amt):
    if amt <= 0:
        return im
    a = np.asarray(im).astype(np.int16)
    o = a.copy()
    o[:, :, 0] = np.roll(a[:, :, 0], amt, 1)
    o[:, :, 2] = np.roll(a[:, :, 2], -amt, 1)
    return Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))


def glitch(im, t, strength=28):
    a = np.asarray(im)
    rnd = random.Random(int(t * 991))
    o = a.copy()
    for _ in range(rnd.randint(4, 8)):
        y = rnd.randint(0, H - 60)
        hh = rnd.randint(6, 70)
        o[y:y + hh] = np.roll(a[y:y + hh], rnd.randint(-strength, strength), 1)
    return Image.fromarray(o)


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
    endcard = (name == "ascent" and l > 6.45)
    out = Image.alpha_composite(out, SCAN_SOFT if endcard else SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 15) % 4])
    out = out.convert("RGB")

    # зум-панч на каждой склейке
    for _, b in SCENES[1:]:
        dd = t - b
        if 0 <= dd < .18:
            kk = 1 - dd / .18
            z = 1 + .05 * kk
            cw, ch = int(W / z), int(H / z)
            out = out.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
            rnd = random.Random(int(t * 331))
            out = Image.fromarray(np.roll(np.roll(np.asarray(out), int(rnd.randint(-8, 8) * kk), 0),
                                          int(rnd.randint(-8, 8) * kk), 1))
    arr = np.asarray(out).astype(np.float32)
    beat = (t / BEAT) % 1.0
    arr *= 1.0 + .022 * math.exp(-beat * 7)
    for _, b in SCENES[1:]:
        dd = abs(t - b)
        if dd < .13:
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            im = glitch(im, t, 30)
            im = rgb_split(im, int(11 * (1 - dd / .13)))
            arr = np.asarray(im).astype(np.float32)
            fl = (1 - dd / .13) * .32
            arr = arr * (1 - fl) + np.array([255, 255, 255], np.float32) * fl
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    import sys
    os.makedirs("/tmp/chk", exist_ok=True)
    for a in sys.argv[1:]:
        tt = float(a)
        render_frame(tt).save(f"/tmp/chk/al_{tt:05.2f}.jpg", quality=90)
        print("saved", tt)
