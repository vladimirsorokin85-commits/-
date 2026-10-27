# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // 3MX «ПЁТР» — вертикальный Reels 9:16 (1080×1920, 30 fps)."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/pauk_30b"
ASSETS = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

BG     = (6, 8, 12)
ACC    = (0, 229, 160)
ACC2   = (0, 176, 255)
WARN   = (255, 176, 32)
TXT    = (242, 246, 255)
DIM    = (140, 162, 186)
LINE   = (34, 52, 74)
RED    = (255, 82, 82)

RUSSO, DAYS, MONO = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf",
                     "JetBrainsMono-VF.ttf")

def F(n, s): return ImageFont.truetype(os.path.join(FD, n), s)
def clamp(x, a, b): return a if x < a else (b if x > b else x)
def c01(x): return 0.0 if x < 0 else (1.0 if x > 1 else x)
def eout(x): x = c01(x); return 1 - (1 - x) ** 3
def eio(x): x = c01(x); return x * x * (3 - 2 * x)
def a(col, al): return (col[0], col[1], col[2], int(clamp(al, 0, 255)))
def tw(d, s, f): return d.textlength(s, font=f)

def fit(txt, fn, size, max_w, min_size=14):
    s = size
    while s > min_size:
        f = F(fn, s)
        if f.getlength(txt) <= max_w:
            return f, s
        s -= 2
    return F(fn, min_size), min_size

PH = {}
for fn in sorted(os.listdir(ASSETS)):
    if fn.endswith(".jpg") and "(" not in fn:
        PH[fn] = Image.open(os.path.join(ASSETS, fn)).convert("RGB")

P = {
    "set4": "pauk_00.jpg", "set6": "pauk_01.jpg", "set6b": "pauk_02.jpg", "stack": "pauk_03.jpg",
    "set4b": "pauk_04.jpg", "full": "pauk_05.jpg", "holster": "pauk_06.jpg", "pouch": "pauk_07.jpg",
    "holster2": "pauk_08.jpg", "pouch_emr": "pauk_09.jpg", "pouch_mc": "pauk_10.jpg",
    "pouch2": "pauk_11.jpg", "pouch3": "pauk_12.jpg", "pouch4": "pauk_13.jpg",
}

# вертикальная подложка 9:16
BW, BH = 1440, 2560
PLATES = {}

def plate(name, dark=0.42):
    key = (name, dark)
    if key in PLATES:
        return PLATES[key]
    im = PH[P[name]]
    s = max(BW / im.width, BH / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - BW) // 2
    y = (im.height - BH) // 2
    im = im.crop((x, y, x + BW, y + BH))
    im = im.point(lambda v: int(v * dark))
    im = Image.blend(im, Image.new("RGB", (BW, BH), (9, 20, 36)), 0.30)
    PLATES[key] = im
    return im

TILE = {}
def tile(name, w, h, zoom=1.0, px=0.0, py=0.0):
    key = (name, w, h)
    if key not in TILE:
        im = PH[P[name]]
        s = max(w * 1.5 / im.width, h * 1.5 / im.height)
        TILE[key] = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    src = TILE[key]
    cw, ch = int(w * 1.5 / zoom), int(h * 1.5 / zoom)
    cw = min(cw, src.width); ch = min(ch, src.height)
    cx = src.width / 2 + px * (src.width - cw) / 2
    cy = src.height / 2 + py * (src.height - ch) / 2
    x0 = int(clamp(cx - cw / 2, 0, src.width - cw)); y0 = int(clamp(cy - ch / 2, 0, src.height - ch))
    out = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)
    out = out.point(lambda v: int(clamp(v * 0.92, 0, 255)))
    return Image.blend(out, Image.new("RGB", (w, h), (12, 26, 44)), 0.08)

def cam(name, l, dur, z0=1.0, z1=1.10, px=0.0, py=0.0):
    img = plate(name)
    p = eio(c01(l / max(dur, .001)))
    z = z0 + (z1 - z0) * p
    cw, ch = BW / z, BH / z
    cx = BW / 2 + px * (BW - cw) / 2 + math.sin(l * 1.1) * 5
    cy = BH / 2 + py * (BH - ch) / 2 + math.cos(l * 1.4) * 4
    x0 = int(clamp(cx - cw / 2, 0, BW - cw)); y0 = int(clamp(cy - ch / 2, 0, BH - ch))
    return img.crop((x0, y0, x0 + int(cw), y0 + int(ch))).resize((W, H), Image.BILINEAR)

ENV = np.load(os.path.join(BASE, "env.npy")) if os.path.exists(os.path.join(BASE, "env.npy")) else None

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_vd = ImageDraw.Draw(VIGN)
for i in range(110):
    k = i / 110.0
    ins = int(-180 + k * 420)
    _vd.ellipse([ins, ins * 1.1, W - ins, H - ins * 1.1], outline=(0, 0, 0, int(3 + k * 2)), width=5)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(26))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 28))

_rng = np.random.default_rng(11)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 30, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 18))))

def brackets(d, x, y, w, h, col=(0, 229, 160, 190), ln=24, wd=2):
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        d.line([(cx, cy), (cx + sx * ln, cy)], fill=col, width=wd)
        d.line([(cx, cy), (cx, cy + sy * ln)], fill=col, width=wd)

def kicker(d, x, y, s, col=ACC, size=15):
    f = F(MONO, size)
    w = tw(d, s, f)
    d.rectangle([x, y, x + w + 26, y + 34], fill=a((8, 26, 22), 236), outline=a(col, 150))
    d.rectangle([x, y, x + 5, y + 34], fill=a(col, 255))
    d.text((x + 14, y + 9), s, font=f, fill=a(col, 255))

def rtext(d, xy, s, f, col, p, dy=30):
    p = c01(p)
    if p <= 0: return
    e = eout(p)
    d.text((xy[0], xy[1] + (1 - e) * dy), s, font=f, fill=a(col, 255 * e))

def card(ov, d, name, x, y, w, h, l, zoom=1.04, label=None, idx=None):
    d.rectangle([x - 8, y - 8, x + w + 8, y + h + 8], fill=(7, 10, 16, 244), outline=a(LINE, 255))
    ov.paste(tile(name, w, h, zoom + 0.02 * math.sin(l * 0.8), 0.2 * math.sin(l * 0.35), 0), (x, y))
    brackets(d, x - 8, y - 8, w + 16, h + 16, a(ACC, 200))
    if idx:
        d.text((x + w - 18, y + 14), idx, font=F(MONO, 15), fill=a(ACC, 215), anchor="ra")
    if label:
        f = F(MONO, 15)
        lw = tw(d, label, f)
        d.rectangle([x - 8, y + h + 8, x + lw + 34, y + h + 52], fill=(8, 11, 17, 248))
        d.rectangle([x - 8, y + h + 8, x - 2, y + h + 52], fill=a(ACC, 255))
        d.text((x + 8, y + h + 19), label, font=f, fill=a(ACC, 250))

def wave(d, x, y, w, h, t, col=ACC, alpha=130, bars=54, drive=1.0):
    if ENV is None: return
    i0 = int(t * FPS) % len(ENV)
    step = max(1, len(ENV) // 300)
    for i in range(bars):
        v = float(ENV[(i0 + i * step) % len(ENV)]) * drive
        bh = max(3, int(clamp(v, 0, 1) * h))
        bx = x + i * (w / bars)
        d.rectangle([bx, y + (h - bh) / 2, bx + max(2, w / bars - 3), y + (h + bh) / 2], fill=a(col, alpha))

def top(ov, d, t, total):
    """Верхняя плашка: без таймкода (требование для Reels)."""
    d.rectangle([0, 0, W, 132], fill=(8, 11, 17, 235))
    d.rectangle([0, 0, W, 5], fill=a(ACC, 255))
    d.text((44, 40), "«В ОКОПЕ»", font=F(RUSSO, 34), fill=a(TXT, 255))
    d.text((44, 90), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА  //  ПАУК 30Б", font=F(MONO, 17), fill=a(DIM, 235))
    # индикатор записи
    d.ellipse([W - 62, 46, W - 42, 66], fill=a(RED, 235))
    d.text((W - 74, 44), "", font=F(MONO, 14), fill=a(TXT, 200))
    # прогресс
    p = clamp(t / total, 0, 1)
    d.rectangle([0, 132, W, 137], fill=(14, 20, 30, 250))
    d.rectangle([0, 132, int(W * p), 137], fill=a(ACC, 240))

def bottom(ov, d, t, total, text="t.me/vokope_ru  •  vk.com/vokope_rus"):
    d.rectangle([0, H - 210, W, H - 150], fill=(6, 9, 14, 190))
    d.text((W // 2, H - 196), text, font=F(MONO, 21), fill=a(ACC, 235), anchor="ma")
    d.text((W // 2, H - 168), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 15), fill=a(DIM, 200), anchor="ma")


# ═════════════ СЦЕНА 1: ПЕРЕХВАТ ═════════════
def s1(ov, d, t, l):
    if l < 3.4:                      # титул
        p = eout(c01((l - .15) / 1.0))
        d.rectangle([0, 300, W, 1200], fill=(5, 8, 13, 228))
        d.rectangle([0, 300, 7, 1200], fill=a(ACC, 255))
        kicker(d, 56, 340, "ТЕХНИЧЕСКИЙ ОБЗОР  //  ПАУК 30Б", ACC, 16)
        f, _ = fit("ПАУК", RUSSO, 240, 880)
        d.text((44, 392 + (1 - p) * 40), "ПАУК", font=f, fill=a(TXT, 255 * p))
        f2, _ = fit("30Б", RUSSO, 150, 500)
        pp2 = eout(c01((l - .45) / .6))
        d.text((48, 640 + (1 - pp2) * 24), "30Б", font=f2, fill=a(ACC, 255 * pp2))

        f3, _ = fit("РУЧНОЙ ПЕХОТНЫЙ СЕТКОМЁТ", RUSSO, 40, 960)
        rtext(d, (56, 830), "РУЧНОЙ ПЕХОТНЫЙ", f3, TXT, (l - .7) / .5)
        rtext(d, (56, 886), "СЕТКОМЁТ", f3, TXT, (l - .8) / .5)
        d.rectangle([56, 966, 56 + 780 * eout(c01((l - .95) / .8)), 970], fill=a(ACC, 220))
        rtext(d, (56, 1000), "ПЕРЕХВАТ МУЛЬТИРОТОРНЫХ ДРОНОВ", F(MONO, 20), DIM, (l - 1.1) / .6)

        chips = ["25–30 М", "6 М²", "400/650 Г"]
        for i, c in enumerate(chips):
            pp = c01((l - 1.4 - i * .1) / .4)
            if pp <= 0: continue
            cf = F(MONO, 19); cw = tw(d, c, cf) + 36
            cx = 56 + i * 240
            d.rounded_rectangle([cx, 1096, cx + cw, 1150], 2, fill=(11, 16, 24, 240), outline=a(ACC, 120))
            d.text((cx + 18, 1110), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        if l > 2.0:
            card(ov, d, "holster", 620, 1200, 400, 380, l, 1.05, None, "01")
            card(ov, d, "set4", 56, 1250, 520, 330, l, 1.03, None, "02")

    elif l < 8.4:                    # геометрия сети
        kicker(d, 56, 200, "ГЕОМЕТРИЯ", ACC, 17)
        f, _ = fit("СЕТЬ", RUSSO, 90, 900)
        rtext(d, (48, 258), "СЕТЬ", f, TXT, (l - .1) / .4)
        f2, _ = fit("2,5 × 2,5 М", RUSSO, 70, 960)
        rtext(d, (48, 372), "2,5 × 2,5 М", f2, ACC, (l - .25) / .45)
        d.text((56, 476), "квадратное полотно, шесть квадратных метров", font=F(MONO, 20), fill=a(DIM, 240))

        # большой квадрат
        gx, gy, gs = 128, 570, 824
        pp = eout(c01((l - .3) / 1.2))
        d.rectangle([gx, gy, gx + gs * pp, gy + gs * pp], outline=a(ACC, 240), width=4)
        step = 82.4
        for k in range(1, int(10 * pp)):
            xx = gx + k * step * pp
            d.line([(xx, gy), (xx, gy + gs * pp)], fill=a(ACC, 90))
            d.line([(gx, gy + k * step * pp), (gx + gs * pp, gy + k * step * pp)], fill=a(ACC, 90))
        d.text((gx + gs * pp / 2, gy - 46), "2,5 М", font=F(RUSSO, 34), fill=a(ACC, 255), anchor="ma")
        d.text((gx + gs * pp / 2, gy + gs * pp + 30), "6 М²", font=F(RUSSO, 48), fill=a(TXT, 255), anchor="ma")

        d.rectangle([56, 1520, 1024, 1660], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((88, 1544), "НАКРЫВАЕТ ВИНТЫ, А НЕ КОРПУС", font=F(RUSSO, 25), fill=a(ACC, 250))
        d.text((88, 1590), "дрон теряет тягу и падает рядом", font=F(MONO, 19), fill=a(DIM, 240))

    elif l < 12.9:                   # дальность
        kicker(d, 56, 200, "ДАЛЬНОСТЬ", ACC2, 17)
        f, _ = fit("25–30 М", RUSSO, 120, 920)
        rtext(d, (48, 254), "25–30 М", f, TXT, (l - .1) / .5)
        d.text((56, 430), "рабочая дистанция перехвата", font=F(MONO, 21), fill=a(DIM, 240))

        # шкала
        gx, gy, gw = 56, 540, 968
        d.rectangle([gx, gy, gx + gw, gy + 90], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(7):
            xx = gx + 30 + i * (gw - 60) / 6
            d.line([(xx, gy + 56), (xx, gy + 90)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 98), str(i * 5), font=F(MONO, 17), fill=a(DIM, 225), anchor="ma")
        pp = eout(c01((l - .3) / 1.3))
        d.rectangle([gx + 30, gy + 30, gx + 30 + int((gw - 60) * .92 * pp), gy + 56], fill=a(ACC, 210))
        for xx, lbl in ((25, "25 М"), (30, "30 М")):
            px = gx + 30 + xx * (gw - 60) / 30
            d.line([(px, gy - 10), (px, gy + 56)], fill=a(WARN, 225), width=3)
            d.text((px, gy - 44), lbl, font=F(RUSSO, 22), fill=a(WARN, 255), anchor="ma")

        # скорость
        d.rectangle([56, 730, 1024, 900], fill=(10, 15, 22, 247), outline=a(ACC2, 130))
        d.text((88, 754), "СКОРОСТЬ СНАРЯДА", font=F(MONO, 16), fill=a(DIM, 235))
        d.text((88, 782), "30 М/С", font=F(RUSSO, 62), fill=a(ACC2, 255))
        d.text((520, 812), "дистанция — за 1 секунду", font=F(MONO, 18), fill=a(TXT, 240))

        card(ov, d, "holster2", 56, 950, 968, 620, l, 1.04, "ПАУК 30Б В ЧЕХЛЕ", "03")
        d.rectangle([56, 1610, 1024, 1690], fill=(9, 13, 19, 240), outline=a(WARN, 120))
        d.text((88, 1630), "ПО ПЕРЕСЕЧЕНИЮ КУРСА, А НЕ ПО ШУМУ", font=F(MONO, 19), fill=a(WARN, 245))

    else:                            # направил-выстрелил-поймал
        kicker(d, 56, 200, "ПРИНЦИП", ACC, 17)
        f, _ = fit("НАПРАВИЛ", RUSSO, 62, 920)
        rtext(d, (48, 258), "НАПРАВИЛ", f, TXT, (l - .1) / .4)
        f2, _ = fit("ВЫСТРЕЛИЛ", RUSSO, 62, 920)
        rtext(d, (48, 350), "ВЫСТРЕЛИЛ", f2, TXT, (l - .25) / .4)
        f3, _ = fit("ПОЙМАЛ", RUSSO, 62, 920)
        rtext(d, (48, 442), "ПОЙМАЛ", f3, ACC, (l - .4) / .4)

        steps = [("01", "ЭЛЕКТРОННЫЙ ЗАПАЛ", "срабатывает по тумблеру"),
                 ("02", "ПИРОПАТРОН", "выбрасывает полотно"),
                 ("03", "СЕТЬ В ПОЛЁТЕ", "раскрывается в квадрат")]
        for i, (num, tt, sub) in enumerate(steps):
            pp = c01((l - .55 - i * .18) / .45)
            if pp <= 0: continue
            yy = int(560 + i * 150 + (1 - eout(pp)) * 24)
            d.rectangle([56, yy, 1024, yy + 128], fill=(11, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([56, yy, 63, yy + 128], fill=a(ACC, 255))
            d.text((94, yy + 20), num, font=F(MONO, 18), fill=a(ACC, 200))
            d.text((150, yy + 24), tt, font=F(RUSSO, 22), fill=a(TXT, 255))
            d.text((150, yy + 72), sub, font=F(MONO, 17), fill=a(DIM, 240))

        card(ov, d, "set4", 56, 1060, 968, 560, l, 1.03, "ПИСТОЛЕТ + 4 СНАРЯДА", "04")
        wave(d, 56, 1650, 968, 90, t, ACC, 140, 58, 1.1)

# ═════════════ СЦЕНА 2: МЕХАНИКА ═════════════
def s2(ov, d, t, l):
    if l < 3.6:                      # перезарядка
        kicker(d, 56, 200, "ПЕРЕЗАРЯДКА", ACC, 17)
        f, _ = fit("ОТ 2 СЕКУНД", RUSSO, 84, 960)
        rtext(d, (48, 258), "ОТ 2", f, TXT, (l - .1) / .4)
        rtext(d, (48, 356), "СЕКУНД", f, ACC, (l - .22) / .4)
        d.text((56, 470), "сменный снаряд вместо разборки", font=F(MONO, 20), fill=a(DIM, 240))

        steps = [("СНЯТЬ", "отработанный картридж"), ("ПОСТАВИТЬ", "новый снаряд"),
                 ("ГОТОВ", "к следующему выстрелу")]
        for i, (k, sub) in enumerate(steps):
            pp = c01((l - .35 - i * .22) / .45)
            if pp <= 0: continue
            yy = int(560 + i * 150 + (1 - eout(pp)) * 24)
            d.rectangle([56, yy, 1024, yy + 128], fill=(11, 15, 22, 246), outline=a(LINE, 255))
            d.ellipse([86, yy + 34, 146, yy + 94], fill=(10, 18, 22, 250), outline=a(ACC, 230), width=3)
            d.text((116, yy + 52), f"{i+1}", font=F(RUSSO, 26), fill=a(ACC, 255), anchor="ma")
            d.text((176, yy + 24), k, font=F(RUSSO, 26), fill=a(TXT, 255))
            d.text((176, yy + 74), sub, font=F(MONO, 17), fill=a(DIM, 240))

        card(ov, d, "pouch2", 56, 1070, 968, 500, l, 1.03, "СМЕННЫЙ СНАРЯД", "05")
        d.rectangle([56, 1610, 1024, 1700], fill=(9, 13, 19, 244), outline=a(ACC, 120))
        d.text((88, 1632), "КОРПУС МНОГОРАЗОВЫЙ, СНАРЯД — РАСХОДНИК", font=F(MONO, 18), fill=a(ACC, 245))

    elif l < 7.9:                    # электроника
        kicker(d, 56, 200, "ЭЛЕКТРОНИКА", ACC2, 17)
        f, _ = fit("5 В / 3,5 А·Ч", RUSSO, 72, 960)
        d.text((48, 258), "5 В / 3,5 А·Ч", font=f, fill=a(TXT, 255))
        d.text((56, 366), "USB Type-C, электронная инициация", font=F(MONO, 20), fill=a(DIM, 240))

        rows = [("ПИТАНИЕ", "+5 В"), ("АККУМУЛЯТОР", "3,5 А·ч"),
                ("ЗАРЯДКА", "USB Type-C"), ("ПРЕДОХРАНИТЕЛЬ", "двухпозиционный тумблер")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - .2 - i * .13) / .45)
            if pp <= 0: continue
            yy = int(470 + i * 140 + (1 - eout(pp)) * 20)
            d.rectangle([56, yy, 1024, yy + 118], fill=(11, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([56, yy, 62, yy + 118], fill=a(ACC2, 255))
            d.text((92, yy + 18), k, font=F(MONO, 16), fill=a(ACC2, 240))
            d.text((92, yy + 52), v, font=F(RUSSO, 30), fill=a(TXT, 255))

        card(ov, d, "holster", 56, 1080, 968, 470, l, 1.03, "КОРПУС И ОРГАНЫ УПРАВЛЕНИЯ", "06")

    elif l < 12.3:                   # автономность
        kicker(d, 56, 200, "АВТОНОМНОСТЬ", ACC, 17)
        f, _ = fit("8 НЕДЕЛЬ", RUSSO, 86, 950)
        d.text((48, 258), "8 НЕДЕЛЬ", font=f, fill=a(TXT, 255))
        d.text((56, 376), "во включённом состоянии, без подзарядки", font=F(MONO, 20), fill=a(DIM, 240))

        pp = eout(c01((l - .3) / 1.5))
        d.text((56, 470), f"{int(56 * pp)}", font=F(RUSSO, 190), fill=a(ACC, 255))
        d.text((450, 588), "дней", font=F(MONO, 28), fill=a(DIM, 240))

        # календарь 8x7
        for wk in range(8):
            for dd in range(7):
                on = (wk * 7 + dd) < int(56 * pp)
                x = 56 + dd * 138
                y = 730 + wk * 74
                d.rectangle([x, y, x + 118, y + 58],
                            fill=a(ACC, 235) if on else a((15, 21, 29), 255),
                            outline=a((28, 40, 54), 255))

        card(ov, d, "pouch3", 56, 1340, 968, 330, l, 1.03, "ТРИ ЧЕХЛА ПОД РАЗНЫЕ КАМУФЛЯЖИ", "07")

    else:                            # безопасность
        kicker(d, 56, 200, "БЕЗОПАСНОСТЬ", WARN, 17)
        f, _ = fit("ТУМБЛЕР", RUSSO, 84, 900)
        rtext(d, (48, 258), "ДВУХПОЗИЦИОННЫЙ", F(RUSSO, 40), TXT, (l - .1) / .4)
        rtext(d, (48, 322), "ТУМБЛЕР", f, WARN, (l - .2) / .4)
        d.text((56, 440), "запал не сработает без взведения", font=F(MONO, 20), fill=a(DIM, 240))

        # тумблер
        cx, cy = 540, 620
        pp = eout(c01((l - .3) / 1.1))
        knob_x = (cx - 190) + int(380 * pp)
        d.rounded_rectangle([cx - 320, cy - 90, cx + 320, cy + 90], 46, fill=(12, 17, 24, 252),
                            outline=a(LINE, 255), width=2)
        d.rounded_rectangle([knob_x - 96, cy - 70, knob_x + 96, cy + 70], 36,
                            fill=(32, 40, 50, 255), outline=a(WARN, 225), width=3)
        d.rectangle([knob_x - 36, cy - 30, knob_x + 36, cy + 30], fill=a((18, 23, 30), 255))
        d.ellipse([knob_x - 14, cy - 14, knob_x + 14, cy + 14], fill=a(WARN, 205))
        d.text((cx - 190, cy + 116), "ЗАЩЁЛКА", font=F(MONO, 17), fill=a(WARN, 240), anchor="ma")
        d.text((cx + 190, cy + 116), "ВЗВЕДЕНО", font=F(MONO, 17), fill=a(ACC, 240), anchor="ma")

        rules = [("ЗАЩЁЛКА", "запал заблокирован", WARN), ("ВЗВЕДЕНО", "цепь замкнута", ACC)]
        for i, (k, v, col) in enumerate(rules):
            yy = 830 + i * 150
            d.rectangle([56, yy, 1024, yy + 128], fill=(11, 15, 22, 246), outline=a(col, 130))
            d.rectangle([56, yy, 62, yy + 128], fill=a(col, 255))
            d.text((94, yy + 24), k, font=F(RUSSO, 26), fill=a(col, 250))
            d.text((94, yy + 74), v, font=F(MONO, 18), fill=a(TXT, 240))

        card(ov, d, "full", 56, 1160, 968, 500, l, 1.03, "ПОЛНЫЙ КОМПЛЕКТ С ЧЕХЛАМИ", "08")
        d.text((56, 1690), "ПОДСУМОК НА MOLLE, КЛАПАН НА ФАСТЕКСЕ", font=F(MONO, 17), fill=a(DIM, 210))

# ═════════════ СЦЕНА 3: ЭКСПЛУАТАЦИЯ + ФИНАЛ ═════════════
def s3(ov, d, t, l):
    if l < 3.6:                      # вес
        kicker(d, 56, 200, "МАССА", ACC2, 17)
        f, _ = fit("400 / 650", RUSSO, 92, 950)
        d.text((48, 258), "400 / 650", font=f, fill=a(TXT, 255))
        d.text((56, 390), "граммов", font=F(RUSSO, 40), fill=a(ACC, 255))
        d.text((56, 470), "без картриджа / снаряжённый", font=F(MONO, 20), fill=a(DIM, 240))

        for i, (k, v, col) in enumerate([("БЕЗ КАРТРИДЖА", "400 г", ACC), ("В СНАРЯЖЁННОМ ВИДЕ", "650 г", ACC2)]):
            pp = eout(c01((l - .3 - i * .25) / .9))
            yy = 570 + i * 210
            d.rectangle([56, yy, 1024, yy + 180], fill=(10, 15, 22, 247), outline=a(col, 130))
            d.text((92, yy + 24), k, font=F(MONO, 17), fill=a(DIM, 235))
            d.text((92, yy + 58), v, font=F(RUSSO, 74), fill=a(col, 255))
            d.rectangle([92, yy + 148, 92 + int(860 * (int(v[:3]) / 700)) * 1, yy + 156], fill=a(col, 230))

        card(ov, d, "holster2", 56, 1010, 968, 560, l, 1.03, "В РУКЕ — БАЛАНС КАК У ПИСТОЛЕТА", "09")

    elif l < 7.4:                    # IP54 / мороз
        kicker(d, 56, 200, "УСЛОВИЯ", ACC2, 17)
        f, _ = fit("IP54", RUSSO, 120, 700)
        d.text((48, 258), "IP54", font=f, fill=a(TXT, 255))
        d.text((56, 430), "−40 °C", font=F(RUSSO, 68), fill=a(ACC2, 255))
        d.text((56, 528), "брызги со всех сторон и мороз", font=F(MONO, 20), fill=a(DIM, 240))

        # температурная шкала
        gx, gy, gw = 56, 620, 968
        d.rectangle([gx, gy, gx + gw, gy + 100], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(7):
            xx = gx + 28 + i * (gw - 56) / 6
            d.line([(xx, gy + 52), (xx, gy + 100)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 108), f"{-40+i*16}", font=F(MONO, 15), fill=a(DIM, 225), anchor="ma")
        pp = eout(c01((l - .3) / 1.2))
        d.rectangle([gx + 28, gy + 32, gx + 28 + int((gw - 56) * pp), gy + 52], fill=a(ACC, 210))

        rows = [("IP54", "брызги со всех сторон"), ("−40 °C", "морозостойкость")]
        for i, (k, v) in enumerate(rows):
            yy = 800 + i * 150
            d.rectangle([56, yy, 1024, yy + 130], fill=(10, 15, 22, 246), outline=a(ACC2, 130))
            d.text((92, yy + 22), k, font=F(RUSSO, 34), fill=a(ACC2, 250))
            d.text((92, yy + 76), v, font=F(MONO, 18), fill=a(TXT, 240))

        card(ov, d, "pouch_emr", 56, 1130, 968, 480, l, 1.03, "ЧЕХОЛ В РУССКОМ ЦИФРОВОМ", "10")

    elif l < 10.8:                   # комплект поставки
        kicker(d, 56, 200, "ПОСТАВКА", ACC, 17)
        f, _ = fit("4 / 6 / 10", RUSSO, 88, 960)
        d.text((48, 258), "4 / 6 / 10", font=f, fill=a(TXT, 255))
        d.text((56, 390), "снарядов в комплекте", font=F(MONO, 22), fill=a(ACC, 245))
        d.text((56, 440), "плюс сам сеткомёт и чехол", font=F(MONO, 19), fill=a(DIM, 240))

        opts = [("4", "базовый", "set4"), ("6", "оптимальный", "set6"), ("10", "максимальный", "full")]
        for i, (n, sub, nm) in enumerate(opts):
            pp = c01((l - .3 - i * .2) / .5)
            if pp <= 0: continue
            x = 56 + i * 320
            y = int(540 + (1 - eout(pp)) * 26)
            d.rectangle([x, y, x + 296, y + 300], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            ov.paste(tile(nm, 280, 200, 1.03), (x + 8, y + 8))
            d.text((x + 24, y + 220), n, font=F(RUSSO, 56), fill=a(ACC, 255))
            d.text((x + 24, y + 278), sub, font=F(MONO, 15), fill=a(DIM, 240))

        d.rectangle([56, 900, 1024, 1080], fill=(9, 13, 19, 244), outline=a(ACC, 120))
        d.text((88, 924), "ДЕКЛАРАЦИЯ О СООТВЕТСТВИИ", font=F(RUSSO, 24), fill=a(ACC, 250))
        d.text((88, 970), "на изделие имеется документ", font=F(MONO, 18), fill=a(TXT, 240))
        d.text((88, 1010), "предъявляется по запросу", font=F(MONO, 16), fill=a(DIM, 230))

        card(ov, d, "stack", 56, 1120, 968, 480, l, 1.03, "БЛОК ИЗ 4 СНАРЯДОВ", "11")

    else:                            # финал
        p = eout(c01((l - .1) / .7))
        d.rectangle([0, 240, W, 1700], fill=(5, 8, 13, 230))
        d.rectangle([0, 240, 7, 1700], fill=a(ACC, 255))
        d.text((56, 300), "ПАУК", font=F(RUSSO, 120), fill=a(TXT, 255 * p))
        d.text((56, 440), "30Б", font=F(RUSSO, 150), fill=a(ACC, 255 * p))
        d.line([(56, 640), (56 + 900 * p, 640)], fill=a(ACC, 180), width=3)
        d.text((56, 680), "ПЕРЕХВАТ БПЛА СЕТЬЮ", font=F(RUSSO, 34), fill=a(TXT, 255 * p))
        d.text((56, 730), "25–30 М  •  6 М²  •  ОТ 2 С", font=F(MONO, 20), fill=a(ACC, 240))

        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - .45 - i * .16) / .4)
            if pp <= 0: continue
            yy = int(810 + i * 118 + (1 - eout(pp)) * 22)
            d.rectangle([56, yy, 1024, yy + 100], fill=(11, 16, 23, 246), outline=a(ACC, 120))
            d.rectangle([56, yy, 63, yy + 100], fill=a(ACC, 255))
            d.text((92, yy + 14), k, font=F(RUSSO, 22), fill=a(ACC, 255))
            d.text((92, yy + 54), v, font=F(MONO, 17), fill=a(TXT, 240))

        card(ov, d, "set4b", 56, 1170, 968, 400, l, 1.03, None, "12")
        d.text((56, 1600), "ФАКТЫ ИЗ ПАСПОРТА  //  БЕЗ ЦЕН", font=F(MONO, 17), fill=a(DIM, 215))

SCENES = [(1.80, s1), (16.94, s2), (32.37, s3)]
TOTAL = 50.83
CUTS = [1.8, 3.4, 8.4, 12.9, 16.94, 20.54, 24.84, 29.24,
        32.37, 35.97, 39.77, 43.17, 46.57]

def render_frame(t):
    if t < 1.80:
        idx = -1; l = t; name = "set4"; fn = None
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001: idx = i
        st, fn = SCENES[idx]; l = t - st
        if idx == 0:
            name = "set4" if l < 3.4 else ("set6" if l < 8.4 else ("holster2" if l < 12.9 else "set6b"))
        elif idx == 1:
            name = "pouch2" if l < 3.6 else ("holster" if l < 7.9 else ("pouch3" if l < 12.3 else "full"))
        else:
            name = "holster2" if l < 3.6 else ("pouch_emr" if l < 7.4 else ("set6" if l < 10.8 else "set4b"))

    z0 = 1.03 + .012 * math.sin(t * .9)
    base = cam(name, l, 4.0, z0, z0 + .10, .30 * math.sin(t * .15), .16 * math.cos(t * .19)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    top(ov, d, t, TOTAL)
    if fn is None:
        p = eout(c01(t / .9))
        d.rectangle([0, 800, W, 1200], fill=(5, 8, 13, int(215 * p)))
        d.text((W // 2, 860), "«В ОКОПЕ»", font=F(RUSSO, 92), fill=a(TXT, int(255 * c01(t / .6))), anchor="ma")
        d.text((W // 2, 990), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 22),
               fill=a(ACC, int(235 * c01((t - .3) / .6))), anchor="ma")
        w = 560 * eout(c01((t - .35) / .7))
        d.rectangle([W // 2 - w / 2, 1054, W // 2 + w / 2, 1058], fill=a(ACC, 220))
        wave(d, 160, 1120, 760, 120, t, ACC, 120, 60, 1.0)
    else:
        fn(ov, d, t, l)

    d.rectangle([0, H - 152, W, H], fill=(7, 10, 16, 246))
    d.line([(0, H - 152), (W, H - 152)], fill=a(ACC, 110), width=1)
    d.text((W // 2, H - 118), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 24), fill=a(ACC, 240), anchor="ma")
    d.text((W // 2, H - 76), "ПАУК 30Б  //  СЕТКОМЁТ", font=F(RUSSO, 17), fill=a(DIM, 225), anchor="ma")

    out = Image.alpha_composite(base, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])
    for c in CUTS:
        dd = abs(t - c)
        if dd < .10:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), (1 - dd / .10) * .20)
    return out.convert("RGB")

if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        tt = float(arg)
        render_frame(tt).save(os.path.join(BASE, f"reel_{tt:06.2f}.jpg"), quality=92)
        print("saved", tt)
