# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // ДРОНОБОЙ «ДОБРЫНЯ» — вертикальный Reels 9:16 (1080×1920, 30 fps)."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/dobrynya"
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

def ffit(*a, **k):
    return fit(*a, **k)[0]

PH = {}
for fn in sorted(os.listdir(ASSETS)):
    if fn.endswith(".jpg") and "(" not in fn:
        PH[fn] = Image.open(os.path.join(ASSETS, fn)).convert("RGB")

P = {
    "nose": "dr_00.jpg", "engr": "dr_01.jpg", "set4": "dr_02.jpg", "base": "dr_03.jpg",
    "window": "dr_04.jpg", "barrel": "dr_05.jpg", "kit": "dr_06.jpg", "rack": "dr_07.jpg",
    "single": "dr_08.jpg", "compare": "dr_09.jpg", "fpv": "dr_10.jpg",
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

def kicker(d, x, y, s, col=ACC, size=26):
    f = F(MONO, size)
    w = tw(d, s, f)
    d.rectangle([x, y, x + w + 34, y + 46], fill=a((8, 26, 22), 236), outline=a(col, 150))
    d.rectangle([x, y, x + 7, y + 46], fill=a(col, 255))
    d.text((x + 18, y + 11), s, font=f, fill=a(col, 255))

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
        f_i = F(MONO, 24)
        iw = tw(d, idx, f_i)
        d.rectangle([x + w - iw - 32, y + 8, x + w - 8, y + 56], fill=(7, 10, 16, 226))
        d.text((x + w - 18, y + 14), idx, font=f_i, fill=a(ACC, 240), anchor="ra")
    if label:
        f = F(MONO, 24)
        lw = tw(d, label, f)
        d.rectangle([x - 8, y + h + 8, x + lw + 40, y + h + 62], fill=(8, 11, 17, 248))
        d.rectangle([x - 8, y + h + 8, x - 2, y + h + 62], fill=a(ACC, 255))
        d.text((x + 8, y + h + 16), label, font=f, fill=a(ACC, 250))

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
    d.text((44, 30), "«В ОКОПЕ»", font=F(RUSSO, 40), fill=a(TXT, 255))
    d.text((44, 86), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА  //  ДОБРЫНЯ", font=F(MONO, 25), fill=a(DIM, 235))
    # индикатор записи
    d.ellipse([W - 62, 40, W - 40, 62], fill=a(RED, 235))
    # прогресс
    p = clamp(t / total, 0, 1)
    d.rectangle([0, 132, W, 137], fill=(14, 20, 30, 250))
    d.rectangle([0, 132, int(W * p), 137], fill=a(ACC, 240))

def bottom(ov, d, t, total, text="t.me/vokope_ru  •  vk.com/vokope_rus"):
    d.rectangle([0, H - 210, W, H - 150], fill=(6, 9, 14, 190))
    d.text((W // 2, H - 196), text, font=F(MONO, 21), fill=a(ACC, 235), anchor="ma")
    d.text((W // 2, H - 168), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 15), fill=a(DIM, 200), anchor="ma")


# ═════════════ СЦЕНА 1: ЗАДАЧА И РЕШЕНИЕ ═════════════
def s1(base, ov, d, t, l):
    if l < 3.60:                      # титул
        d.rectangle([0, 250, W, 1250], fill=(5, 8, 13, 232))
        d.rectangle([0, 250, 9, 1250], fill=a(ACC, 255))
        kicker(d, 56, 296, "ТЕХНИЧЕСКИЙ ОБЗОР // ДОБРЫНЯ", ACC, 26)
        p1 = eout(c01((l - .14) / .5))
        f, _ = fit("ДОБРЫНЯ", RUSSO, 168, 960)
        d.text((46, 372 + (1 - p1) * 30), "ДОБРЫНЯ", font=f, fill=a(TXT, 255 * p1))
        p2 = eout(c01((l - .44) / .44))
        d.text((50, 566 + (1 - p2) * 22), "ДРОНОБОЙ", font=F(RUSSO, 96), fill=a(ACC, 255 * p2))
        p3 = eout(c01((l - .70) / .40))
        d.text((50, 700), "ДЛЯ АК-74 И АК-12", font=F(MONO, 38), fill=a(DIM, 255 * p3))
        d.text((50, 776), "дульная насадка", font=F(RUSSO, 52), fill=a(TXT, 255 * p3))
        d.text((50, 844), "под дробовой выстрел", font=F(RUSSO, 52), fill=a(TXT, 255 * p3))
        d.text((52, 932), "против FPV-дронов в ближней зоне", font=F(MONO, 30), fill=a(DIM, 245 * p3))

        chips = ["24 ММ", "750 / 800 Г", "ДО 200 ДРОБИН"]
        cxx, cyy = 50, 1030
        for i, c in enumerate(chips):
            pp = c01((l - .95 - i * .09) / .4)
            if pp <= 0: continue
            cf = F(MONO, 30); cw = tw(d, c, cf) + 40
            if cxx + cw > 1030:
                cxx = 50; cyy += 78
            yy = int(cyy + (1 - eout(pp)) * 16)
            d.rounded_rectangle([cxx, yy, cxx + cw, yy + 66], 2, fill=(11, 16, 24, 242), outline=a(ACC, 130))
            d.text((cxx + 20, yy + 17), c, font=cf, fill=a(TXT, 255 * eout(pp)))
            cxx += cw + 16
        if l > 1.25:
            card(ov, d, "nose", 92, 1300, 470, 300, l, 1.05, "БАЙОНЕТ", "01")

    elif l < 8.40:                    # проблема
        kicker(d, 56, 190, "ПРОБЛЕМА", WARN, 26)
        f, _ = fit("ЦЕЛЬ ЧУТЬ БОЛЬШЕ", RUSSO, 74, 960)
        rtext(d, (48, 250), "ЦЕЛЬ ЧУТЬ БОЛЬШЕ", f, TXT, (l - .08) / .4)
        f2, _ = fit("СМАРТФОНА", RUSSO, 74, 960)
        rtext(d, (48, 332), "СМАРТФОНА", f2, TXT, (l - .16) / .4)
        d.text((54, 430), "одной пулей попасть крайне сложно", font=F(MONO, 28), fill=a(DIM, 240))

        card(ov, d, "fpv", 56, 492, 968, 560, l, 1.05, "FPV-ДРОН И СМАРТФОН", "02")

        rows = [("ГАБАРИТ", "корпус меньше ладони"),
                ("СКОРОСТЬ", "подлёт — считанные секунды"),
                ("ПЛОЩАДЬ", "цель размером с телефон")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - .5 - i * .16) / .5)
            if pp <= 0: continue
            yy = int(1100 + i * 168 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 144], fill=(10, 14, 21, 246), outline=a(WARN, 130))
            d.rectangle([56, yy, 65, yy + 144], fill=a(WARN, 255))
            d.text((96, yy + 16), k, font=F(RUSSO, 40), fill=a(WARN, 255))
            d.text((96, yy + 76), v, font=F(MONO, 28), fill=a(TXT, 240))

    else:                             # до 200 дробин
        kicker(d, 56, 190, "РЕШЕНИЕ", ACC, 26)
        f, _ = fit("ДО 200 ДРОБИН", RUSSO, 84, 960)
        rtext(d, (48, 250), "ДО 200 ДРОБИН", f, TXT, (l - .08) / .4)
        d.text((54, 356), "не одна пуля, а облако дроби", font=F(MONO, 30), fill=a(DIM, 240))

        # схема разлёта
        d.rectangle([56, 430, 1024, 1180], fill=(7, 10, 16, 244), outline=a(LINE, 255))
        d.rectangle([104, 560, 232, 950], fill=(20, 26, 34, 255), outline=a(DIM, 180), width=3)
        d.text((168, 600), "24", font=F(RUSSO, 62), fill=a(DIM, 210), anchor="ma")
        d.text((168, 676), "ММ", font=F(MONO, 26), fill=a(DIM, 200), anchor="ma")
        d.text((168, 980), "ДУЛЬНЫЙ СРЕЗ", font=F(MONO, 26), fill=a(DIM, 225), anchor="ma")
        cx, cy = 620, 780
        pp = eout(c01((l - .35) / 1.1))
        for i in range(46):
            ang = (i * 2.399) % (2 * math.pi)
            rr = (26 + (i * 61) % 290) * pp
            x = 232 + abs(math.cos(ang)) * 60 + rr * .55
            y = cy + math.sin(ang) * rr * 1.05
            col = ACC if i % 3 else ACC2
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=a(col, 235))

        d.rectangle([56, 1210, 1024, 1500], fill=(9, 13, 19, 248), outline=a(ACC, 130))
        d.rectangle([56, 1210, 65, 1500], fill=a(ACC, 255))
        d.text((104, 1238), "ОБЛАКО ПЕРЕКРЫВАЕТ", font=ffit("ОБЛАКО ПЕРЕКРЫВАЕТ", RUSSO, 40, 860), fill=a(ACC, 250))
        d.text((104, 1298), "ЦЕЛЬ ЦЕЛИКОМ", font=F(RUSSO, 40), fill=a(ACC, 250))
        d.text((104, 1372), "ювелирный прицел не нужен", font=F(MONO, 30), fill=a(TXT, 242))
        d.text((104, 1420), "шанс попасть кратно выше", font=F(MONO, 30), fill=a(DIM, 235))


# ═════════════ СЦЕНА 2: ХАРАКТЕРИСТИКИ ═════════════
def s2(base, ov, d, t, l):
    if l < 4.80:                      # калибр и диаметр
        kicker(d, 56, 190, "ТАКТИКО-ТЕХНИЧЕСКИЕ", ACC2, 24)
        f, _ = fit("КАЛИБР И СЕЧЕНИЕ", RUSSO, 70, 960)
        rtext(d, (48, 250), "КАЛИБР И СЕЧЕНИЕ", f, TXT, (l - .08) / .4)

        d.rectangle([56, 372, 1024, 880], fill=(7, 10, 16, 244), outline=a(LINE, 255))
        cx, cy, R = 300, 600, 178
        pp = eout(c01((l - .2) / .9))
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * pp, fill=a(ACC, 235), width=6)
        d.arc([cx - R + 34, cy - R + 34, cx + R - 34, cy + R - 34], -90, -90 + 360 * pp, fill=a(ACC, 110), width=3)
        d.text((cx, cy - 66), "24", font=F(RUSSO, 140), fill=a(TXT, 255))
        d.text((cx, cy + 92), "ММ", font=F(MONO, 34), fill=a(ACC, 240), anchor="ma")
        d.text((cx, cy + 226), "ВНУТРЕННИЙ ДИАМЕТР", font=F(MONO, 26), fill=a(DIM, 235), anchor="ma")

        rows = [("КАЛИБР", "5,45 × 39 ММ", ACC2),
                ("ПОД ПАТРОН", "штатный, ПсГс", ACC2),
                ("ВЫСТРЕЛ", "дробовой картридж", ACC2)]
        for i, (k, v, col) in enumerate(rows):
            q = c01((l - .3 - i * .14) / .5)
            if q <= 0: continue
            yy = int(420 + i * 156 + (1 - eout(q)) * 16)
            d.rectangle([610, yy, 1024, yy + 132], fill=(11, 16, 23, 246), outline=a(col, 130))
            d.text((640, yy + 14), k, font=F(MONO, 24), fill=a(col, 240))
            d.text((640, yy + 54), v, font=ffit(v, RUSSO, 38, 356), fill=a(TXT, 255))

    elif l < 9.80:                    # масса
        kicker(d, 56, 190, "МАССА", ACC2, 26)
        f, _ = fit("750 / 800 ГРАММОВ", RUSSO, 66, 960)
        rtext(d, (48, 250), "750 / 800 ГРАММОВ", f, TXT, (l - .08) / .4)
        d.text((54, 356), "плюс снаряжённый картридж", font=F(MONO, 28), fill=a(DIM, 240))

        bars = [("АК-74", "750 Г", 750, ACC), ("АК-12", "800 Г", 800, ACC2), ("КАРТРИДЖ", "135 Г", 135, WARN)]
        for i, (nm, val, v, col) in enumerate(bars):
            pp = eout(c01((l - .2 - i * .18) / .55))
            yy = 430 + i * 232
            d.text((56, yy), nm, font=F(MONO, 30), fill=a(DIM, 240))
            d.text((56, yy + 42), val, font=F(RUSSO, 62), fill=a(col, 255))
            bw = 940 * (v / 800) * pp
            d.rectangle([56, yy + 126, 996, yy + 142], fill=(18, 24, 34, 255))
            d.rectangle([56, yy + 126, 56 + bw, yy + 142], fill=a(col, 235))
        card(ov, d, "single", 620, 1180, 404, 380, l, 1.05, "КАРТРИДЖ В СБОРЕ", "05")
        d.rectangle([56, 1160, 560, 1460], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((90, 1210), "МАТЕРИАЛ", font=F(MONO, 24), fill=a(ACC2, 240))
        d.text((90, 1252), "КОНСТРУКЦИОННАЯ", font=F(RUSSO, 38), fill=a(TXT, 255))
        d.text((90, 1300), "СТАЛЬ", font=F(RUSSO, 38), fill=a(TXT, 255))
        d.text((90, 1368), "покрытие — воронение", font=F(MONO, 28), fill=a(ACC, 240))

    elif l < 13.40:                   # крепление
        kicker(d, 56, 190, "УСТАНОВКА", ACC2, 26)
        f, _ = fit("БАЙОНЕТ ИЛИ РЕЗЬБА", RUSSO, 64, 960)
        rtext(d, (48, 250), "БАЙОНЕТ ИЛИ РЕЗЬБА", f, TXT, (l - .08) / .4)
        d.text((54, 356), "тип соединения зависит от исполнения", font=F(MONO, 28), fill=a(DIM, 240))

        for i, (k, v, sub, col) in enumerate([("БАЙОНЕТ", "24 × 1,5 R", "быстрая постановка\nи снятие", ACC),
                                             ("РЕЗЬБА", "МЕТРИЧЕСКАЯ", "накручивание\nдо упора", ACC2)]):
            pp = eout(c01((l - .2 - i * .2) / .55))
            yy = 410 + i * 252
            d.rectangle([56, yy, 1024, yy + 224], fill=(11, 16, 23, 246), outline=a(col, 150))
            d.rectangle([56, yy, 65, yy + 224], fill=a(col, 255))
            d.text((104, yy + 26), k, font=F(RUSSO, 56), fill=a(col, 255))
            d.text((104, yy + 110), v, font=ffit(v, RUSSO, 44, 800), fill=a(TXT, 255))
            d.text((104, yy + 168), sub.split("\n")[0], font=F(MONO, 28), fill=a(DIM, 240))

        d.rectangle([56, 930, 1024, 1060], fill=(9, 13, 19, 248), outline=a(ACC, 120))
        d.text((92, 954), "СОВМЕСТИМОСТЬ", font=F(MONO, 24), fill=a(ACC, 235))
        d.text((92, 994), "АК-12, АК-74 и аналогичные", font=F(RUSSO, 36), fill=a(TXT, 255))
        card(ov, d, "barrel", 56, 1110, 468, 300, l, 1.05, "СТВОЛ И МУФТА", "06")
        card(ov, d, "nose", 556, 1110, 468, 300, l, 1.05, "БАЙОНЕТ", "01")

    else:                             # маркировка
        kicker(d, 56, 190, "МАРКИРОВКА", ACC2, 26)
        f, _ = fit("ЧТО НА КОРПУСЕ", RUSSO, 66, 960)
        rtext(d, (48, 250), "ЧТО НА КОРПУСЕ", f, TXT, (l - .08) / .4)
        d.text((54, 356), "индекс изделия, тип и производитель", font=F(MONO, 28), fill=a(DIM, 240))

        card(ov, d, "engr", 56, 420, 968, 560, l, 1.06, "ГРАВИРОВКА НА СТВОЛЕ", "07")
        rows = [("ИНДЕКС", "01.030.017"), ("ТИП", "АК12, дронобой"), ("ИЗГОТОВЛЕНИЕ", "Сделано в России")]
        for i, (k, v) in enumerate(rows):
            q = c01((l - .3 - i * .14) / .5)
            if q <= 0: continue
            yy = int(1050 + i * 152 + (1 - eout(q)) * 16)
            d.rectangle([56, yy, 1024, yy + 128], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
            d.rectangle([56, yy, 62, yy + 128], fill=a(ACC2, 255))
            d.text((92, yy + 12), k, font=F(MONO, 24), fill=a(ACC2, 240))
            d.text((92, yy + 56), v, font=ffit(v, RUSSO, 36, 880), fill=a(TXT, 255))


# ═════════════ СЦЕНА 3: МЕХАНИКА ═════════════
def s3(base, ov, d, t, l):
    if l < 6.20:                      # цепочка выстрела
        kicker(d, 56, 190, "МЕХАНИКА", ACC, 26)
        f, _ = fit("ВЫСТРЕЛ ШТАТНЫМ ПАТРОНОМ", RUSSO, 56, 960)
        rtext(d, (48, 250), "ВЫСТРЕЛ ШТАТНЫМ ПАТРОНОМ", f, TXT, (l - .08) / .4)
        d.text((54, 320), "отдельного запала нет", font=F(MONO, 30), fill=a(DIM, 240))

        blocks = [("ПАТРОН", "ПсГс", "штатный, боевой", ACC),
                  ("ИМПУЛЬС", "ПЛАМЯ", "энергия + пламенный импульс", WARN),
                  ("В ЦЕЛЬ", "ДРОБЬ", "до 200 дробин", ACC2)]
        for i, (k, big, sub, col) in enumerate(blocks):
            pp = eout(c01((l - .2 - i * .28) / .6))
            if pp <= 0: continue
            yy = 410 + i * 400
            d.rectangle([56, yy, 1024, yy + 300], fill=(11, 16, 23, 248), outline=a(col, 150))
            d.rectangle([56, yy, 65, yy + 300], fill=a(col, 255))
            d.text((104, yy + 22), k, font=F(MONO, 26), fill=a(col, 240))
            d.text((104, yy + 66), big, font=ffit(big, RUSSO, 76, 860), fill=a(TXT, 255))
            d.text((104, yy + 176), sub, font=ffit(sub, MONO, 30, 860), fill=a(DIM, 240))
            if i < 2:
                ax = 540
                ay = yy + 344
                d.line([(ax, ay - 14), (ax, ay + 14)], fill=a(col, 200), width=5)
                d.polygon([(ax - 16, ay + 12), (ax + 16, ay + 12), (ax, ay + 34)], fill=a(col, 220))

        d.rectangle([56, 1600, 1024, 1690], fill=(9, 26, 22, 244), outline=a(ACC, 150))
        d.text((92, 1622), "ПЕРЕЗАРЯЖАТЬ ВРУЧНУЮ НЕ НУЖНО", font=F(RUSSO, 34), fill=a(ACC, 255))

    elif l < 10.20:                   # остаётся на стволе
        kicker(d, 56, 190, "ПОСЛЕ ВЫСТРЕЛА", ACC, 26)
        f, _ = fit("НАСАДКА ОСТАЁТСЯ", RUSSO, 70, 960)
        rtext(d, (48, 250), "НАСАДКА ОСТАЁТСЯ", f, TXT, (l - .08) / .4)
        f2, _ = fit("НА СТВОЛЕ", RUSSO, 70, 960)
        rtext(d, (48, 330), "НА СТВОЛЕ", f2, ACC, (l - .16) / .4)
        d.text((54, 428), "устройство не снимается после выстрела", font=F(MONO, 28), fill=a(DIM, 240))

        card(ov, d, "base", 56, 496, 968, 520, l, 1.05, "ДНО КАРТРИДЖА", "08")

        d.rectangle([56, 1080, 1024, 1330], fill=(9, 26, 22, 248), outline=a(ACC, 160))
        d.rectangle([56, 1080, 65, 1330], fill=a(ACC, 255))
        d.text((104, 1108), "ДАЛЬШЕ — ШТАТНЫЕ ПАТРОНЫ", font=ffit("ДАЛЬШЕ — ШТАТНЫЕ ПАТРОНЫ", RUSSO, 40, 860), fill=a(ACC, 255))
        d.text((104, 1180), "огонь продолжается", font=F(MONO, 32), fill=a(TXT, 242))
        d.text((104, 1232), "в обычном режиме", font=F(MONO, 32), fill=a(TXT, 242))

        d.rectangle([56, 1370, 1024, 1500], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((92, 1394), "ДРОБОВОЙ ВЫСТРЕЛ — ОДИН", font=ffit("ДРОБОВОЙ ВЫСТРЕЛ — ОДИН", RUSSO, 34, 880), fill=a(TXT, 255))
        d.text((92, 1444), "дальше насадка работает как дульный прибор", font=F(MONO, 26), fill=a(DIM, 235))

    else:                             # автоматический огонь
        kicker(d, 56, 190, "РЕЖИМ ОГНЯ", ACC, 26)
        f, _ = fit("АВТОМАТИЧЕСКИЙ", RUSSO, 70, 960)
        rtext(d, (48, 250), "АВТОМАТИЧЕСКИЙ", f, TXT, (l - .08) / .4)
        f2, _ = fit("ОГОНЬ НЕ СТРАДАЕТ", RUSSO, 56, 960)
        rtext(d, (48, 336), "ОГОНЬ НЕ СТРАДАЕТ", f2, ACC, (l - .16) / .4)
        d.text((54, 424), "насадка не меняет оружие — она его дополняет", font=F(MONO, 27), fill=a(DIM, 240))

        steps = [("01", "НАКРУТИЛ", "вместо пламегасителя"),
                 ("02", "ВЫСТРЕЛИЛ", "штатным боевым патроном"),
                 ("03", "СРАБОТАЛ", "картридж ушёл в цель дробью")]
        for i, (num, k, v) in enumerate(steps):
            pp = c01((l - .2 - i * .16) / .5)
            if pp <= 0: continue
            yy = int(500 + i * 232 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 200], fill=(11, 16, 23, 246), outline=a(ACC, 130))
            d.rectangle([56, yy, 65, yy + 200], fill=a(ACC, 255))
            d.text((102, yy + 18), num, font=F(MONO, 28), fill=a(ACC, 235))
            d.text((166, yy + 16), k, font=F(RUSSO, 46), fill=a(TXT, 255))
            d.text((166, yy + 92), v, font=ffit(v, MONO, 28, 800), fill=a(DIM, 240))

        card(ov, d, "set4", 56, 1236, 968, 380, l, 1.05, "НАСАДКА И КАРТРИДЖИ В ДЕРЖАТЕЛЯХ", "09")


# ═════════════ СЦЕНА 4: ЭКСПЛУАТАЦИЯ ═════════════
def s4(base, ov, d, t, l):
    if l < 6.60:                      # установка
        kicker(d, 56, 190, "ЭКСПЛУАТАЦИЯ", WARN, 26)
        f, _ = fit("УСТАНОВКА НА АВТОМАТ", RUSSO, 62, 960)
        rtext(d, (48, 250), "УСТАНОВКА НА АВТОМАТ", f, TXT, (l - .08) / .4)
        d.text((54, 350), "вместо пламегасителя или ДТК", font=F(MONO, 28), fill=a(DIM, 240))

        steps = [("01", "СНЯТЬ", "штатный пламегаситель"),
                 ("02", "ПОСТАВИТЬ", "насадку на резьбу или байонет"),
                 ("03", "ЗАФИКСИРОВАТЬ", "на АК-74 — крышку ствольной коробки")]
        for i, (num, k, v) in enumerate(steps):
            pp = c01((l - .2 - i * .16) / .5)
            if pp <= 0: continue
            yy = int(440 + i * 218 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 188], fill=(11, 16, 23, 246), outline=a(WARN, 130))
            d.rectangle([56, yy, 65, yy + 188], fill=a(WARN, 255))
            d.text((102, yy + 18), num, font=F(MONO, 26), fill=a(WARN, 235))
            d.text((166, yy + 16), k, font=F(RUSSO, 42), fill=a(TXT, 255))
            d.text((166, yy + 86), v, font=ffit(v, MONO, 26, 800), fill=a(DIM, 240))

        card(ov, d, "barrel", 56, 1120, 968, 400, l, 1.05, "НАСАДКА И РЕЗЬБОВАЯ МУФТА", "06")
        d.rectangle([56, 1556, 1024, 1690], fill=(26, 18, 8, 246), outline=a(WARN, 150))
        d.rectangle([56, 1556, 65, 1690], fill=a(WARN, 255))
        d.text((100, 1578), "на АК-74 крышка ствольной коробки", font=F(MONO, 26), fill=a(WARN, 245))
        d.text((100, 1624), "фиксируется обязательно", font=F(MONO, 26), fill=a(TXT, 242))

    elif l < 11.40:                   # миномётный способ
        kicker(d, 56, 190, "ЗАРЯЖАНИЕ", WARN, 26)
        f, _ = fit("МИНОМЁТНЫЙ СПОСОБ", RUSSO, 64, 960)
        rtext(d, (48, 250), "МИНОМЁТНЫЙ СПОСОБ", f, TXT, (l - .08) / .4)
        d.text((54, 350), "картридж забрасывается донной частью вперёд", font=F(MONO, 27), fill=a(DIM, 240))

        d.rectangle([56, 430, 1024, 1000], fill=(7, 10, 16, 244), outline=a(LINE, 255))
        d.rectangle([110, 620, 330, 900], fill=(20, 26, 34, 255), outline=a(DIM, 180), width=3)
        d.text((220, 926), "НАСАДКА", font=F(MONO, 26), fill=a(DIM, 225), anchor="ma")
        d.text((220, 700), "24 ММ", font=F(RUSSO, 40), fill=a(DIM, 200), anchor="ma")
        pp = eout(c01((l - .25) / 1.0))
        xx = 820 - int(300 * pp)
        d.rectangle([xx, 690, xx + 110, 830], fill=(28, 34, 44, 255), outline=a(ACC, 220), width=3)
        d.rectangle([xx + 110, 716, xx + 142, 804], fill=(150, 156, 166, 255))
        d.text((xx + 55, 650), "КАРТРИДЖ", font=F(MONO, 26), fill=a(ACC, 235), anchor="ma")
        d.text((xx + 55, 866), "ДНО ВПЕРЁД", font=F(MONO, 26), fill=a(ACC2, 235), anchor="ma")

        for i, (k, v1, v2, col) in enumerate([("ЗАБРОСИТЬ", "донной частью", "к резьбе", ACC),
                                             ("ДЕРЖАТЬ", "автомат не ниже", "горизонтали", ACC2)]):
            yy = 1040 + i * 180
            d.rectangle([56, yy, 1024, yy + 160], fill=(11, 16, 23, 246), outline=a(col, 130))
            d.rectangle([56, yy, 62, yy + 160], fill=a(col, 255))
            d.text((96, yy + 12), k, font=F(MONO, 24), fill=a(col, 240))
            d.text((96, yy + 52), v1, font=F(MONO, 30), fill=a(TXT, 245))
            d.text((96, yy + 98), v2, font=F(MONO, 30), fill=a(TXT, 245))
        card(ov, d, "base", 56, 1412, 460, 250, l, 1.05, None, "08")
        d.rectangle([552, 1412, 1024, 1662], fill=(9, 13, 19, 248), outline=a(ACC2, 120))
        d.text((586, 1446), "ДНО КАРТРИДЖА", font=F(MONO, 24), fill=a(ACC2, 240))
        d.text((586, 1492), "четыре отверстия", font=F(RUSSO, 40), fill=a(TXT, 255))
        d.text((586, 1566), "под пламенный импульс", font=F(MONO, 26), fill=a(DIM, 238))

    elif l < 17.20:                   # патрон и запреты
        kicker(d, 56, 190, "ПАТРОН", WARN, 26)
        f, _ = fit("ПсГс — И ТОЛЬКО ОН", RUSSO, 68, 960)
        rtext(d, (48, 250), "ПсГс — И ТОЛЬКО ОН", f, TXT, (l - .08) / .4)

        d.rectangle([56, 380, 1024, 800], fill=(9, 26, 22, 248), outline=a(ACC, 170), width=2)
        d.text((96, 410), "РАЗРЕШЕНО", font=F(MONO, 28), fill=a(ACC, 240))
        d.text((96, 462), "ПсГс", font=F(RUSSO, 128), fill=a(ACC, 255))
        d.text((96, 640), "штатный патрон,", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((96, 690), "одиночные или очереди", font=F(MONO, 30), fill=a(TXT, 240))

        d.rectangle([56, 840, 1024, 1240], fill=(30, 12, 12, 250), outline=a(RED, 180), width=2)
        d.text((96, 870), "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО", font=F(MONO, 28), fill=a(RED, 245))
        d.text((96, 926), "БРОНЕБОЙНЫЕ", font=ffit("БРОНЕБОЙНЫЕ", RUSSO, 56, 880), fill=a(RED, 255))
        d.text((96, 1000), "И ПпГс", font=F(RUSSO, 56), fill=a(RED, 255))
        d.text((96, 1100), "это приведёт к поломке изделия", font=F(MONO, 28), fill=a(TXT, 240))

        card(ov, d, "compare", 56, 1280, 968, 330, l, 1.05, "КАРТРИДЖ И ПАТРОН 12 КАЛИБРА", "03")

    else:                             # финал
        p = eout(c01((l - .1) / .7))
        d.rectangle([0, 250, W, 1500], fill=(6, 9, 14, 238))
        d.rectangle([0, 250, 9, 1500], fill=a(ACC, 255))
        f, _ = fit("ДОБРЫНЯ", RUSSO, 150, 940)
        d.text((52, 300 + (1 - p) * 26), "ДОБРЫНЯ", font=f, fill=a(TXT, 255 * p))
        d.text((56, 470), "ДРОНОБОЙ ДЛЯ АК-74 И АК-12", font=ffit("ДРОНОБОЙ ДЛЯ АК-74 И АК-12", RUSSO, 40, 940), fill=a(ACC, 255 * p))
        d.text((56, 560), "24 ММ  ·  750 / 800 Г  ·  ДО 200 ДРОБИН", font=F(MONO, 28), fill=a(DIM, 240 * p))
        d.text((56, 610), "штатный патрон ПсГс", font=F(MONO, 28), fill=a(DIM, 240 * p))

        p2 = c01((l - .5) / .6)
        d.text((56, 720), "ПОДПИСЫВАЙСЯ НА «В ОКОПЕ»", font=F(RUSSO, 38), fill=a(TXT, 255 * p2))
        links = [("ТЕЛЕГРАМ", "t.me/vokope_ru"), ("ВКОНТАКТЕ", "vk.com/vokope_rus"),
                 ("АВИТО", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            yy = 800 + i * 176
            d.rectangle([56, yy, 1024, yy + 152], fill=(9, 13, 19, 248), outline=a(ACC, 130))
            d.text((92, yy + 16), k, font=F(MONO, 24), fill=a(ACC, 240))
            d.text((92, yy + 58), v, font=ffit(v, MONO, 30, 900), fill=a(TXT, 245))
        card(ov, d, "kit", 560, 1330, 464, 330, l, 1.05, "НАСАДКА И КАРТРИДЖИ", "09")


SCENES = [(2.80, s1), (15.85, s2), (33.30, s3), (46.55, s4)]
TOTAL = 69.55
CUTS = [2.80, 6.40, 11.20, 15.85, 20.65, 25.65, 29.25, 33.30, 39.50, 43.50,
        46.55, 53.15, 58.00, 63.75, 66.40]


def render_frame(t):
    if t < 2.80:
        idx = -1; l = t; name = "nose"; fn = None
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001: idx = i
        st, fn = SCENES[idx]; l = t - st
        if idx == 0:
            name = "nose" if l < 3.60 else ("fpv" if l < 8.40 else "compare")
        elif idx == 1:
            name = "barrel" if l < 4.80 else ("single" if l < 9.80 else ("nose" if l < 13.40 else "engr"))
        elif idx == 2:
            name = "barrel" if l < 6.20 else ("base" if l < 10.20 else "set4")
        else:
            name = "barrel" if l < 6.60 else ("base" if l < 11.40 else ("compare" if l < 17.20 else "kit"))

    z0 = 1.03 + .012 * math.sin(t * .9)
    base = cam(name, l, 5.0, z0, z0 + .10, .30 * math.sin(t * .15), .16 * math.cos(t * .19)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    top(ov, d, t, TOTAL)
    if fn is None:
        p = eout(c01(t / .9))
        d.rectangle([0, 760, W, 1240], fill=(5, 8, 13, int(215 * p)))
        d.text((W // 2, 830), "«В ОКОПЕ»", font=F(RUSSO, 94), fill=a(TXT, int(255 * c01(t / .6))), anchor="ma")
        d.text((W // 2, 966), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 28),
               fill=a(ACC, int(235 * c01((t - .3) / .6))), anchor="ma")
        w = 620 * eout(c01((t - .35) / .7))
        d.rectangle([W // 2 - w / 2, 1024, W // 2 + w / 2, 1028], fill=a(ACC, 220))
        wave(d, 180, 1090, 720, 110, t, ACC, 120, 60, 1.0)
    else:
        fn(base, ov, d, t, l)

    out = Image.alpha_composite(base, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])
    for c in CUTS:
        dd = abs(t - c)
        if dd < .12:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), (1 - dd / .12) * .18)
    return out.convert("RGB")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        tt = float(arg)
        render_frame(tt).save(os.path.join(BASE, f"rf_{tt:06.2f}.jpg"), quality=92)
        print("saved", tt)
