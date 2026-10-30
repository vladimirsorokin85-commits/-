# -*- coding: utf-8 -*-
"""«Тепловизор 360°» — вертикальный Reels 9:16 (1080×1920, 46 с).

Монтаж на 120 BPM (удар каждые 0.5 с). Источники:
  • реальные фото заказчика (assets/*.jpg) — метка «ФОТО»;
  • видео заказчика (assets/video/*.mp4 → последовательности assets/vidfr/*) —
    метка «ПРИМЕР РАБОТЫ · ВИДЕО ЗАКАЗЧИКА»;
  • схемы (кольцо 360°, луч лазера, табличка 24 В) — метка «МАКЕТ».
Никаких цен. Только факты из facts.md.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = "/home/user/-/video_studio/thermal_360"
A = os.path.join(BASE, "assets")
VD = os.path.join(A, "vidfr")
FD = "/home/user/-/video_studio/toolkit/fonts"
TOTAL = 46.00
BPM = 120.0
BEAT = 60.0 / BPM

SCENES = [
    ("hook", 0.00), ("mount", 4.00), ("power", 7.50), ("turn", 11.00),
    ("therm", 15.00), ("day", 19.50), ("laser", 24.00), ("focus", 27.50),
    ("monitor", 31.50), ("volt", 36.00), ("outro", 40.50),
]

BG = (9, 10, 13)
ORG = (255, 140, 42)       # тепловой янтарь
ICE = (94, 208, 255)       # холодный акцент
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
    c = 2.3
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ac(c, a):
    return (c[0], c[1], c[2], int(cl(a, 0, 255)))


# ───────────────────────── источники
_KEYS = {}
_VID = {}


def keyed(name, w=980, bg_lum=190.0, floor=142.0):
    """Фото заказчика: снимаем светло-серый фон, тень переводим в тёмную."""
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
    out_a = (al * 255).astype(np.uint8)

    body = np.clip((a - 30) * 1.15 + 24, 0, 255)
    shadow = (al < 0.97) & (lum > 95)
    body[shadow] = np.array([18, 20, 24], np.float32)
    res = Image.fromarray(body.astype(np.uint8)).convert("RGBA")
    alpha = out_a.astype(np.float32) / 255.0
    alpha = np.where(shadow, alpha * 0.55, alpha)
    res.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)))
    bb = res.getchannel("A").point(lambda v: 255 if v > 14 else 0).getbbox()
    res = res.crop(bb) if bb else res
    del a, lum, al, body, shadow
    _KEYS[k] = res
    return res


def kcard(cv, name, cx, cy, w, alpha=255, rot=0.0, bg_lum=190.0, floor=142.0,
          glow=ORG, glow_a=46, shadow=True):
    if alpha <= 3:
        return
    im = keyed(name, min(1560, max(320, int(w * 1.6))), bg_lum, floor)
    st = w / im.width
    im = im.resize((max(2, int(im.width * st)), max(2, int(im.height * st))), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 255:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    if shadow:
        sh = Image.new("RGBA", (im.width + 120, im.height + 120), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", im.size, ac((0, 0, 0), 190)), (60, 66), im)
        sh = sh.filter(ImageFilter.GaussianBlur(26))
        cv.alpha_composite(sh, (int(cx - sh.width / 2), int(cy - sh.height / 2) + 20))
    if glow_a:
        gl = Image.new("RGBA", (im.width + 160, im.height + 160), (0, 0, 0, 0))
        gl.paste(Image.new("RGBA", im.size, ac(glow, glow_a)), (80, 80), im)
        gl = gl.filter(ImageFilter.GaussianBlur(46))
        cv.alpha_composite(gl, (int(cx - gl.width / 2), int(cy - gl.height / 2)))
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def vcount(sub):
    n = 0
    while os.path.exists(os.path.join(VD, sub, "%03d.jpg" % (n + 1))):
        n += 1
    return n


def vframe(sub, t, t0):
    n = vcount(sub)
    i = int(round((t - t0) * FPS)) + 1
    i = max(1, min(n, i))
    k = (sub, i)
    if k not in _VID:
        _VID.clear()          # кадры идут последовательно — держим в памяти только текущий
        _VID[k] = Image.open(os.path.join(VD, sub, "%03d.jpg" % i)).convert("RGB")
    return _VID[k]


def cover_im(im, w, h, zoom=1.0, ox=0.0, oy=0.0):
    cs = max(w / im.width, h / im.height) * zoom
    rw, rh = min(w / cs, im.width), min(h / cs, im.height)
    cx = im.width / 2 + cl(ox, -1, 1) * max(0, (im.width - rw) / 2)
    cy = im.height / 2 + cl(oy, -1, 1) * max(0, (im.height - rh) / 2)
    x0 = int(cl(cx - rw / 2, 0, im.width - rw))
    y0 = int(cl(cy - rh / 2, 0, im.height - rh))
    return im.crop((x0, y0, x0 + int(rw), y0 + int(rh))).resize((w, h), Image.LANCZOS)


def grade(im, dark=0.62, con=1.14, sat=0.92, tint=(255, 150, 70), amt=0.05):
    a = np.asarray(im).astype(np.float32)
    a = (a - 128) * con + 128
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * sat
    a *= dark
    a = a * (1 - amt) + np.array(tint, np.float32) * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def vshot(sub, t, t0, zoom=1.0, ox=0.0, oy=0.0, dark=0.62, sat=0.92, tint=(255, 150, 70)):
    return grade(cover_im(vframe(sub, t, t0), W, H, zoom, ox, oy), dark, 1.14, sat, tint, 0.06)


# ───────────────────────── константные слои
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

_r = np.random.default_rng(11)
GRAIN = []
for _ in range(4):
    n = _r.integers(0, 28, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 16))))


# ───────────────────────── текстовые утилиты
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


def slam(cv, s, fn, size, x, y, col, p, anchor="lt", trail=38, dx=1, chroma=True, maxw=None):
    if p <= 0:
        return
    lay = text_lay(s, fn, size, col)
    lim = maxw or (W - 88)
    if lay.width > lim:
        lay = lay.resize((lim, max(2, int(lay.height * lim / lay.width))), Image.LANCZOS)
    k = 1 + 0.40 * (1 - eb(p))
    lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eo(min(1, p * 2.2))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    px = int(x - lay.width / 2) if anchor == "ma" else int(x)
    py = int(y - lay.height / 2) if anchor == "mm" else int(y)
    if chroma and p < 0.45:
        ca = int(74 * (1 - p / 0.45))
        for off, c in ((-5, (255, 70, 90)), (5, (70, 200, 255))):
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
            t.putalpha(t.getchannel("A").point(lambda v: int(v * 0.13 * (5 - i) / 4 * kk)))
            cv.alpha_composite(t, (px + ox, py))
    cv.alpha_composite(lay, (px, py))


def chip(d, x, y, s, col=ORG, size=26, h=54, alpha=255, solid=False):
    f = F(MONO, size)
    w = f.getlength(s)
    fill = ac((col if solid else (10, 11, 14))[:3], alpha * (0.94 if solid else 0.86))
    d.rectangle([x, y, x + w + 38, y + h], fill=fill, outline=ac(col, alpha * 0.85))
    d.rectangle([x, y, x + 6, y + h], fill=ac(col, alpha))
    d.text((x + 19, y + (h - size) / 2 - 5), s, font=f,
           fill=ac((10, 11, 14) if solid else col, alpha))
    return w + 38


def tag(cv, s, y=1700, col=DIM, x=None, alpha=255, sub=None):
    """Метка происхождения кадра: ФОТО / МАКЕТ / ВИДЕО ЗАКАЗЧИКА."""
    if alpha <= 3:
        return
    f = F(MONO, 21)
    t1 = s
    w = f.getlength(t1)
    bw = int(w + 30)
    bx = (W - bw) // 2 if x is None else x
    d = ImageDraw.Draw(cv)
    d.rectangle([bx, y, bx + bw, y + 34], fill=ac((6, 7, 9), 205 * alpha / 255),
                outline=ac(col, 150 * alpha / 255))
    d.text((bx + 15, y + 7), t1, font=f, fill=ac(col, alpha))
    if sub:
        f2 = F(MONO, 19)
        w2 = f2.getlength(sub)
        bx2 = (W - int(w2 + 30)) // 2
        d.rectangle([bx2, y + 40, bx2 + w2 + 30, y + 70], fill=ac((6, 7, 9), 205 * alpha / 255),
                    outline=ac(col, 150 * alpha / 255))
        d.text((bx2 + 15, y + 46), sub, font=f2, fill=ac(col, alpha))


def hud(d, t):
    d.rectangle([0, 0, W, 108], fill=(6, 7, 9, 234))
    d.rectangle([0, 0, W, 4], fill=ac(ORG, 255))
    d.text((42, 26), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=ac(TXT, 255))
    d.text((42, 76), "ТЕПЛОВИЗОР 360° // ПОВОРОТНЫЙ БЛОК", font=F(MONO, 20), fill=ac(DIM, 230))
    b = 0.5 + 0.5 * math.sin(t * 7.5)
    d.ellipse([W - 68, 64, W - 46, 86], fill=ac(RED, int(105 + 130 * b)))
    d.text((W - 84, 62), "REC", font=F(MONO, 20), fill=ac(DIM, 190), anchor="ra")
    p = cl(t / TOTAL)
    d.rectangle([0, 108, W, 114], fill=(16, 18, 22, 245))
    d.rectangle([0, 108, int(W * p), 114], fill=ac(ORG, 245))
    d.rectangle([0, H - 122, W, H], fill=(5, 6, 8, 246))
    d.rectangle([0, H - 125, W, H - 121], fill=ac(ORG, 95))
    d.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 25),
           fill=ac(ORG, 240), anchor="ma")
    d.text((W // 2, H - 52), "ТЕПЛОВИЗОР 360° · ДЕНЬ И НОЧЬ", font=F(RUSSO, 19),
           fill=ac(DIM, 210), anchor="ma")


def beatshake(t, amp=5):
    b = (t / BEAT) % 1.0
    k = math.exp(-b * 9) * amp
    rnd = random.Random(int(t * 100))
    return (rnd.uniform(-1, 1) * k, rnd.uniform(-1, 1) * k)


def punch(im, t, cuts):
    for c in cuts:
        dd = t - c
        if 0 <= dd < 0.20:
            k = 1 - dd / 0.20
            z = 1 + 0.055 * k
            w, h = int(W / z), int(H / z)
            im = im.crop(((W - w) // 2, (H - h) // 2, (W + w) // 2, (H + h) // 2)).resize((W, H), Image.BILINEAR)
    return im


def grid(cv, t, alpha=44, col=ICE, hz=980):
    d = ImageDraw.Draw(cv)
    for i in range(14):
        x = -600 + i * 170
        d.line([(540 + (x - 540) * 0.16, hz), (x, H)], fill=ac(col, alpha * 0.55), width=2)
    for i in range(9):
        y = hz + int((H - hz) * (i / 8.0) ** 2.1)
        d.line([(0, y), (W, y)], fill=ac(col, alpha * 0.5), width=2)
    hy = int(hz - 40 + 22 * math.sin(t * 1.1))
    d.line([(0, hy), (W, hy)], fill=ac(col, alpha), width=3)


def arc(d, cx, cy, r, a0, a1, col, width=6, alpha=255, dash=24, gap=16):
    """Пунктирная дуга в градусах (0° = вправо, против часовой)."""
    span = a1 - a0
    n = max(2, int(abs(span) / (360.0 / ((2 * math.pi * r) / (dash + gap)))))
    for i in range(n):
        s0 = a0 + span * i / n
        s1 = s0 + span / n * (dash / (dash + gap))
        d.arc([cx - r, cy - r, cx + r, cy + r], start=-s1, end=-s0, fill=ac(col, alpha), width=width)


# ───────────────────────── сцены
def s_hook(cv, d, t, l):
    cv.alpha_composite(vshot("a", t, 0.0, zoom=1.26 + 0.16 * eo(l / 4.0), ox=-0.14 + 0.26 * eo(l / 4.0), oy=0.06,
                             dark=0.36, sat=0.42, tint=(255, 150, 60)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(0, H, 4):
        k = y / H
        dd.line([(0, y), (W, y)], fill=(5, 6, 9, int(24 + 150 * cl((k - .25) / .75) ** 1.4)))
    cv.alpha_composite(ov)
    # вращающееся кольцо 360°
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring)
    cx, cy = 540, 690
    for k, (r, wd, al) in enumerate(((286, 5, 210), (330, 2, 120))):
        arc(dr, cx, cy, r, 18 + t * 42 * (1 if k == 0 else -1.4), 18 + t * 42 + 250 * (1 if k == 0 else -1.4),
            ORG if k == 0 else ICE, wd, al, 30, 22)
    cv.alpha_composite(ring)
    slam(cv, "ТЕПЛОВИЗОР", RUSSO, 150, 540, 405, ac(TXT, 255), c01((l - .05) / .30), "ma", 46)
    slam(cv, "360°", DAYS, 300, 540, 690, ac(ORG, 255), c01((l - .38) / .34), "ma", 52)
    if l > 1.5:
        p = c01((l - 1.5) / .35)
        w1 = chip(d, 90, 1040, "ПОВОРОТНЫЙ БЛОК", ORG, 27, 56, int(255 * p))
        chip(d, 90 + w1 + 16, 1040, "ДЕНЬ + НОЧЬ", ICE, 27, 56, int(255 * p))
    if l > 1.15:
        p = c01((l - 1.15) / .40)
        d.rectangle([96, 1210, 98 + int(8 * p), 1470], fill=ac(ORG, 210))
        slam(cv, "640×512 · VOx", MONO, 36, 132, 1230, ac(TXT, 240 * p), p, "lt", 18)
        slam(cv, "50 КАДР/С", MONO, 36, 132, 1300, ac(TXT, 240 * p), p, "lt", 18)
        slam(cv, "ЛАЗЕР ДО 1000 М", MONO, 36, 132, 1370, ac(TXT, 240 * p), p, "lt", 18)
        slam(cv, "12 В · ПУЛЬТ · МОНИТОР", MONO, 36, 132, 1440, ac(TXT, 240 * p), p, "lt", 18)
    tag(cv, "ПРИМЕР РАБОТЫ · ВИДЕО ЗАКАЗЧИКА", 1650, ICE, alpha=int(235 * c01((l - .5) / .5)))


def s_mount(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 14), 255)))
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(bg)
    for i in range(9):
        y = 1150 + i * i * 17
        db.line([(0, y), (W, y)], fill=ac(ICE, 26), width=2)
    cv.alpha_composite(bg)
    grid(cv, t, 26, ICE, 1180)
    sh = beatshake(t)
    kcard(cv, "camera_back.jpg", 540 + sh[0], 900 + 16 * math.sin(l * 2.0) + sh[1],
          760 + 40 * eo(l / 3.5), rot=-1.6 + 1.2 * math.sin(l * 1.4))
    # пульсация у основания — магнит
    p = (t / BEAT) % 1.0
    rr = int(150 + 90 * p)
    d.ellipse([540 - rr, 1180 - int(rr * 0.30), 540 + rr, 1180 + int(rr * 0.30)],
              outline=ac(ORG, int(150 * (1 - p))), width=4)
    d.line([(540, 1240), (540, 1150)], fill=ac(ORG, 220), width=5)
    d.polygon([(540, 1136), (528, 1162), (552, 1162)], fill=ac(ORG, 230))
    d.text((540, 1270), "МАГНИТНОЕ КРЕПЛЕНИЕ", font=F(MONO, 25), fill=ac(ORG, 225), anchor="ma")
    slam(cv, "ЗА МИНУТУ", RUSSO, 126, 540, 265, ac(TXT, 255), c01((l - .04) / .28), "ma", 40)
    if l > .55:
        p2 = c01((l - .55) / .30)
        d.rectangle([0, 350, int(W * eo(p2)), 356], fill=ac(ORG, 210))
        slam(cv, "МАГНИТНОЕ · БЫСТРОСЪЁМНОЕ КРЕПЛЕНИЕ", MONO, 26, 540, 392, ac(DIM, 228 * p2), p2, "ma", 18)
    tag(cv, "ФОТО", 1650, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_power(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((11, 11, 13), 255)))
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grad)
    for y in range(0, H, 3):
        k = y / H
        dg.line([(0, y), (W, y)], fill=ac((255, 150, 60), int(26 * (1 - abs(k - .5) * 1.6))))
    cv.alpha_composite(grad)
    kcard(cv, "kit_wide.jpg", 640 - 340 * eo(l / 3.5), 1120, 1420, glow_a=34)
    slam(cv, "12 В", DAYS, 250, 96, 470, ac(ORG, 255), c01((l - .05) / .30), "lt", 42)
    if l > .35:
        p = c01((l - .35) / .30)
        chip(d, 104, 700, "ПОСТОЯННЫЙ ТОК", ICE, 28, 58, int(255 * p))
        chip(d, 104 + 340, 700, "ОТ ПРИКУРИВАТЕЛЯ", ORG, 28, 58, int(255 * p))
    if l > .9:
        p = c01((l - .9) / .40)
        slam(cv, "ТОЛЬКО ПОСТОЯННЫЙ ТОК", RUSSO, 66, 100, 880, ac(TXT, 250 * p), p, "lt", 26)
    # бегущая точка по кабелю
    if l > 1.2:
        q = c01((l - 1.2) / 2.0)
        px = int(220 + 700 * q)
        d.ellipse([px - 9, 1090 - 9, px + 9, 1090 + 9], fill=ac(ICE, 235))
        d.ellipse([px - 24, 1090 - 24, px + 24, 1090 + 24], outline=ac(ICE, 90), width=3)
    tag(cv, "ФОТО", 1650, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_turn(cv, d, t, l):
    cv.alpha_composite(vshot("c", t, 11.0, zoom=1.20 + 0.12 * eo(l / 4.0), ox=0.02, oy=0.02,
                             dark=0.38, sat=0.45, tint=(255, 150, 70)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    do.rectangle([0, 0, W, H], fill=(4, 5, 8, 90))
    cv.alpha_composite(ov)
    sch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sch)
    cx, cy = 540, 1010
    base = -t * 55
    arc(ds, cx, cy, 300, base, base + 300, ORG, 6, 205, 26, 18)
    arc(ds, cx, cy, 214, base + 180, base + 430, ICE, 3, 150, 20, 16)
    ds.line([(cx, cy - 350), (cx, cy + 350)], fill=ac(ICE, 55), width=2)
    ds.line([(cx - 350, cy), (cx + 350, cy)], fill=ac(ICE, 55), width=2)
    cv.alpha_composite(sch)
    slam(cv, "ПОВОРОТ", RUSSO, 138, 540, 330, ac(TXT, 255), c01((l - .04) / .26), "ma", 42)
    slam(cv, "С ПУЛЬТА", DAYS, 96, 540, 452, ac(ORG, 255), c01((l - .30) / .26), "ma", 34)
    if l > .8:
        p = c01((l - .8) / .35)
        w1 = chip(d, 108, 1450, "ПИТАНИЕ", ORG, 26, 54, int(255 * p))
        w2 = chip(d, 108 + w1 + 14, 1450, "360° ПО ГОРИЗОНТАЛИ", ICE, 26, 54, int(255 * p))
        chip(d, 108 + w1 + w2 + 28, 1450, "НАКЛОН", ICE, 26, 54, int(255 * p))
    tag(cv, "ПРИМЕР РАБОТЫ · ВИДЕО ЗАКАЗЧИКА", 1612, ICE, alpha=int(235 * c01((l - .3) / .4)))
    tag(cv, "МАКЕТ · СХЕМА ПОВОРОТА", 1692, ORG, alpha=int(200 * c01((l - .6) / .4)))


def s_therm(cv, d, t, l):
    cv.alpha_composite(vshot("d", t, 15.0, zoom=1.30 + 0.10 * eo(l / 4.5), ox=0.0, oy=-0.02,
                             dark=0.34, sat=0.5, tint=(255, 150, 65)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    for y in range(0, H, 3):
        k = y / H
        do.line([(0, y), (W, y)], fill=(4, 5, 8, int(40 + 130 * cl((k - .45) / .55) ** 1.5)))
    cv.alpha_composite(ov)
    if l > .2:
        p = c01((l - .2) / .3)
        d.rectangle([70, 300, 1010, 300 + 6 * p], fill=ac(ICE, 220))
    slam(cv, "640×512", RUSSO, 124, 78, 360, ac(TXT, 255), c01((l - .05) / .28), "lt", 36)
    slam(cv, "ТЕПЛОВОЙ КАНАЛ", MONO, 36, 82, 520, ac(ORG, 245), c01((l - .35) / .30), "lt", 22)
    if l > .9:
        p = c01((l - .9) / .35)
        y0 = 1400
        w1 = chip(d, 76, y0, "VOX · 12 МКМ", ORG, 27, 56, int(255 * p))
        w2 = chip(d, 76 + w1 + 14, y0, "50 КАДР/С", ICE, 27, 56, int(255 * p))
        chip(d, 76 + w1 + w2 + 28, y0, "8–14 МКМ", ICE, 27, 56, int(255 * p))
    if l > 1.8:
        p = c01((l - 1.8) / .35)
        slam(cv, "ОБЪЕКТИВ 9 ММ · 51,4° × 41,1°", MONO, 30, 540, 1540, ac(TXT, 235 * p), p, "ma", 18)
    tag(cv, "ПРИМЕР РАБОТЫ · ВИДЕО ЗАКАЗЧИКА", 1640, ICE, alpha=int(235 * c01((l - .25) / .4)))


def s_day(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 12, 15), 255)))
    grid(cv, t, 30, ICE, 1250)
    kcard(cv, "camera_back_close.jpg", 640, 1120, 800 - 26 * eo(l / 4.5),
          rot=2.0 - 2.6 * eo(l / 4.5), glow_a=30)
    slam(cv, "ДЕНЬ", RUSSO, 150, 78, 300, ac(TXT, 255), c01((l - .04) / .26), "lt", 40)
    if l > .4:
        p = c01((l - .4) / .30)
        slam(cv, "FULL HD 1920×1080", MONO, 38, 82, 452, ac(ICE, 250 * p), p, "lt", 22)
        slam(cv, "102° × 60°", MONO, 38, 82, 512, ac(ICE, 250 * p), p, "lt", 22)
        slam(cv, "0,01 ЛЮКС", MONO, 38, 82, 572, ac(ICE, 250 * p), p, "lt", 22)
    if l > 1.2:
        p = c01((l - 1.2) / .35)
        slam(cv, "ДНЕВНАЯ КАМЕРА", RUSSO, 62, 82, 690, ac(ORG, 250 * p), p, "lt", 22)
    if l > 2.0:
        p = c01((l - 2.0) / .35)
        chip(d, 82, 1592, "2 МП · 2,8 ММ", ORG, 27, 56, int(255 * p))
        chip(d, 82 + 360, 1592, "CMOS 1/2.8\"", ICE, 27, 56, int(255 * p))
    tag(cv, "ФОТО", 1690, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_laser(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((7, 10, 14), 255)))
    grid(cv, t, 54, ICE, 1010)
    # цель на горизонте
    tx, ty = 940, 748
    q = c01((l - .1) / 1.1)
    ret = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ret)
    for k, r in enumerate((74, 108)):
        a0 = t * (36 + 20 * k) * (1 if k == 0 else -1)
        arc(dr, tx, ty, r, a0, a0 + 250, ORG if k == 0 else ICE, 4, int(210 * q), 20, 14)
    dr.line([(tx - 118, ty), (tx - 40, ty)], fill=ac(ICE, int(200 * q)), width=3)
    dr.line([(tx + 40, ty), (tx + 118, ty)], fill=ac(ICE, int(200 * q)), width=3)
    dr.line([(tx, ty - 118), (tx, ty - 40)], fill=ac(ICE, int(200 * q)), width=3)
    dr.line([(tx, ty + 40), (tx, ty + 118)], fill=ac(ICE, int(200 * q)), width=3)
    cv.alpha_composite(ret)
    # прибор
    kcard(cv, "camera_back.jpg", 196, 1290, 430, glow_a=30, shadow=True)
    # луч
    x0, y0 = 262, 1258
    p = eo(c01((l - .12) / 1.0))
    xe, ye = x0 + (tx - x0) * p, y0 + (ty - y0) * p
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(beam)
    db.line([(x0, y0), (xe, ye)], fill=ac(ORG, 245), width=26)
    db.line([(x0, y0), (xe, ye)], fill=ac((255, 190, 120), 200), width=10)
    beam = beam.filter(ImageFilter.GaussianBlur(18))
    cv.alpha_composite(beam)
    d.line([(x0, y0), (xe, ye)], fill=ac((255, 226, 172), 245), width=5)
    # бегущий импульс
    if p > .3:
        rp = (t * 1.6) % 1.0
        px, py = x0 + (xe - x0) * rp, y0 + (ye - y0) * rp
        d.ellipse([px - 10, py - 10, px + 10, py + 10], fill=ac((255, 245, 220), 240))
    for m in (250, 500, 750, 1000):
        qq = m / 1000.0
        if p >= qq:
            px, py = x0 + (tx - x0) * qq, y0 + (ty - y0) * qq
            d.line([(px - 12, py - 30), (px + 12, py + 30)], fill=ac(ICE, 225), width=3)
            d.text((px + 18, py + 22), "%d М" % m, font=F(MONO, 27), fill=ac(ICE, 235))
    slam(cv, "ЛАЗЕР", RUSSO, 150, 78, 330, ac(TXT, 255), c01((l - .04) / .26), "lt", 40)
    slam(cv, "ДО 1000 М", DAYS, 104, 78, 476, ac(ORG, 255), c01((l - .30) / .26), "lt", 32)
    if l > .9:
        p2 = c01((l - .9) / .3)
        chip(d, 82, 626, "КНОПКА A — ВКЛ", ORG, 27, 56, int(255 * p2), solid=True)
        chip(d, 82 + 356, 626, "КНОПКА B — ВЫКЛ", ICE, 27, 56, int(255 * p2))
    if l > 1.6:
        p3 = c01((l - 1.6) / .35)
        d.rectangle([70, 1610, W - 70, 1672], fill=ac((6, 7, 9), int(180 * p3)))
        slam(cv, "ЛАЗЕР ВКЛЮЧАЕТСЯ С МАЛОГО ПУЛЬТА", MONO, 29, 540, 1626, ac(TXT, 235 * p3), p3, "ma", 18)
    tag(cv, "МАКЕТ · СХЕМА ЛУЧА", 1530, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_focus(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((9, 10, 13), 255)))
    kcard(cv, "camera_back_close.jpg", 540 + 26 * math.sin(l * 1.3), 1120,
          1010 + 130 * eo(l / 4.0), rot=-3.2 + 6.0 * eo(l / 4.0), glow_a=24, shadow=False)
    sch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sch)
    cx, cy = 540, 1080
    q = c01((l - .2) / 1.3)
    for i, r0 in enumerate((470, 380, 300)):
        r = int(r0 - 120 * q)
        a0 = t * (34 + i * 18) * (1 if i % 2 else -1)
        arc(ds, cx, cy, r, a0, a0 + 130, ORG if i == 0 else ICE, 4, int(150 + 70 * (1 - q)), 22, 16)
    cv.alpha_composite(sch)
    if l > .9:
        p = eo(c01((l - .9) / 1.3))
        kx = int(880 - 300 * p)
        ky = int(1420 - 360 * p)
        d.line([(kx, ky), (kx + 120, ky + 30)], fill=ac(ICE, int(90 + 100 * p)), width=6)
        d.line([(kx, ky), (kx + 108, ky - 52)], fill=ac(ICE, 240), width=8)
        d.ellipse([kx - 19, ky - 19, kx + 19, ky + 19], outline=ac(ICE, 240), width=6)
        d.ellipse([kx - 30, ky - 30, kx + 30, ky + 30], outline=ac(ICE, int(120 * (1 - p))), width=3)
        d.text((kx - 12, ky + 44), "КЛЮЧ", font=F(MONO, 28), fill=ac(ICE, 240))
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rectangle([0, 236, W, 500], fill=(6, 7, 9, 208))
    cv.alpha_composite(plate)
    slam(cv, "ФОКУС КЛЮЧОМ", RUSSO, 96, 540, 300, ac(TXT, 255), c01((l - .04) / .26), "ma", 36)
    if l > .7:
        p = c01((l - .7) / .3)
        slam(cv, "ПО МОНИТОРУ · СДВИГ ≤ 1 ММ", MONO, 32, 540, 428, ac(ORG, 245 * p), p, "ma", 20)
    if l > 2.1:
        p = c01((l - 2.1) / .3)
        chip(d, 268, 1560, "ДВА ЗУБА В ОТВЕРСТИЯ", ICE, 26, 54, int(255 * p))
    tag(cv, "ФОТО + МАКЕТ", 1650, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_monitor(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 14), 255)))
    grid(cv, t, 22, ICE, 1330)
    kcard(cv, "kit_screen.jpg", 540, 960, 1120 + 60 * eo(l / 4.5), glow_a=28)
    slam(cv, "МОНИТОР", RUSSO, 128, 540, 300, ac(TXT, 255), c01((l - .04) / .26), "ma", 38)
    slam(cv, "В САЛОНЕ", DAYS, 92, 540, 420, ac(ORG, 255), c01((l - .30) / .26), "ma", 32)
    if l > 1.5:
        p = c01((l - 1.5) / .35)
        slam(cv, "УПРАВЛЕНИЕ — С МЕСТА ВОДИТЕЛЯ", MONO, 29, 540, 1500, ac(TXT, 235 * p), p, "ma", 16)
        slam(cv, "КАРТИНКА ИДЁТ НА МОНИТОР", MONO, 29, 540, 1554, ac(DIM, 225 * p), p, "ma", 16)
    tag(cv, "ФОТО", 1650, ORG, alpha=int(230 * c01((l - .3) / .4)))


def s_volt(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((18, 8, 8), 255)))
    stripes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stripes)
    for i in range(-12, 26):
        x = i * 120 + int((t * 60) % 120)
        ds.polygon([(x, 0), (x + 46, 0), (x + 46 - 520, H), (x - 520, H)], fill=ac(RED, 16))
    cv.alpha_composite(stripes)
    pulse = 0.5 + 0.5 * math.sin(t * 6.2)
    slam(cv, "24 В", DAYS, 260, 540, 560, ac(RED, 235 + 20 * pulse), c01((l - .05) / .26), "ma", 40)
    # перечёркивание
    if l > .45:
        p = eo(c01((l - .45) / .30))
        d.line([(250, 470), (250 + 580 * p, 470 + 210 * p)], fill=ac(TXT, 245), width=15)
        if p > .55:
            p2 = eo(c01((p - .55) / .45))
            d.line([(830, 470), (830 - 580 * p2, 470 + 210 * p2)], fill=ac(TXT, 245), width=15)
    if l > .95:
        p = c01((l - .95) / .28)
        slam(cv, "ВЫГОРИТ ЭЛЕКТРОНИКА", RUSSO, 72, 540, 830, ac(TXT, 250 * p), p, "ma", 26)
    if l > 1.55:
        p = c01((l - 1.55) / .30)
        d.rectangle([0, 980, int(W * eo(p)), 990], fill=ac(ORG, 230))
        slam(cv, "12 В", DAYS, 200, 540, 1150, ac(ORG, 255 * p), p, "ma", 34)
        slam(cv, "ПОСТОЯННЫЙ ТОК · ТОЛЬКО 12 В", MONO, 32, 540, 1352, ac(TXT, 240 * p), p, "ma", 18)
    if l > 2.4:
        p = c01((l - 2.4) / .30)
        chip(d, 250, 1420, "ПРОВОДИТЬ ТОЛЬКО 12 В", RED, 26, 54, int(255 * p))
    tag(cv, "МАКЕТ", 1650, RED, alpha=int(230 * c01((l - .3) / .4)))


def s_outro(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((8, 9, 12), 255)))
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grad)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(ORG, int(38 * (1 - k) ** 2)))
    cv.alpha_composite(grad)
    # световой свип
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-600 + (l / 5.5) * (W + 1200))
    ds.polygon([(x, 0), (x + 220, 0), (x + 220 - 420, H), (x - 420, H)], fill=ac(ORG, 26))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(18)))
    p = c01((l - .05) / .3)
    slam(cv, "«В ОКОПЕ»", RUSSO, 178, 540, 760, ac(TXT, 255), p, "ma", 44, maxw=980)
    if l > .5:
        q = c01((l - .5) / .3)
        slam(cv, "ТЕПЛОВИЗОР 360°", MONO, 40, 540, 930, ac(ORG, 250 * q), q, "ma", 22)
    if l > 1.0:
        q = c01((l - 1.0) / .3)
        d.rectangle([240, 1010, 240 + 600 * eo(q), 1018], fill=ac(ORG, 220))
    if l > 1.4:
        q = c01((l - 1.4) / .3)
        slam(cv, "ПОЛНЫЙ РАЗБОР", RUSSO, 56, 540, 1080, ac(TXT, 240 * q), q, "ma", 20)
        slam(cv, "t.me/vokope_ru", MONO, 36, 540, 1176, ac(ICE, 235 * q), q, "ma", 16)
        slam(cv, "vk.com/vokope_rus", MONO, 36, 540, 1232, ac(ICE, 235 * q), q, "ma", 16)
    if l > 2.0:
        q = c01((l - 2.0) / .35)
        chip(d, 372, 1310, "ПОДПИШИСЬ", ORG, 30, 62, int(255 * q), solid=True)
        slam(cv, "ТЕПЛОВИЗОР 360° · 640×512 · ДО 1000 М", MONO, 25, 540, 1420, ac(DIM, 225 * q), q, "ma", 14)
    # рамка
    if l > .3:
        q = c01((l - .3) / .5)
        k = 4 + 2 * math.sin(t * 4)
        d.rectangle([46, 210, W - 46, H - 250], outline=ac(ORG, int(70 * q)), width=int(k))


FN = {"hook": s_hook, "mount": s_mount, "power": s_power, "turn": s_turn, "therm": s_therm,
      "day": s_day, "laser": s_laser, "focus": s_focus, "monitor": s_monitor,
      "volt": s_volt, "outro": s_outro}


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
    arr *= 1.0 + 0.020 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    import sys
    os.makedirs("/tmp/chk", exist_ok=True)
    for a in sys.argv[1:]:
        tt = float(a)
        render_frame(tt).save("/tmp/chk/th_%05.2f.jpg" % tt, quality=90)
        print("saved", tt, flush=True)
