# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // ПАУК 30Б — ручной пехотный сеткомёт. Горизонталь 16:9."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FPS = 30
BASE = "/home/user/-/video_studio/pauk_30b"
ASSETS = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

BG     = (6, 8, 12)
ACC    = (0, 229, 160)     # основной зелёный
ACC2   = (0, 176, 255)     # циан
WARN   = (255, 176, 32)    # тревога / цель
RED    = (255, 82, 82)
TXT    = (242, 246, 255)
DIM    = (140, 162, 186)
LINE   = (34, 52, 74)

RUSSO, DAYS, MONO = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf", "JetBrainsMono-VF.ttf")

def F(n, s): return ImageFont.truetype(os.path.join(FD, n), s)
def clamp(x, a, b): return a if x < a else (b if x > b else x)
def c01(x): return 0.0 if x < 0 else (1.0 if x > 1 else x)
def eout(x): x = c01(x); return 1 - (1 - x) ** 3
def eio(x): x = c01(x); return x * x * (3 - 2 * x)
def a(col, al): return (col[0], col[1], col[2], int(clamp(al, 0, 255)))
def tw(d, s, f): return d.textlength(s, font=f)

def fit(txt, fn, size, max_w, min_size=12):
    s = size
    while s > min_size:
        f = F(fn, s)
        if f.getlength(txt) <= max_w:
            return f
        s -= 2
    return F(fn, min_size)

# ───────── фото ─────────
PH = {}
for fn in sorted(os.listdir(ASSETS)):
    if fn.endswith(".jpg"):
        PH[fn] = Image.open(os.path.join(ASSETS, fn)).convert("RGB")

# карта кадров
P = {
    "set4":   "pauk_00.jpg",   # пистолет + 4 снаряда
    "set6":   "pauk_01.jpg",
    "set6b":  "pauk_02.jpg",
    "stack":  "pauk_03.jpg",   # 4-зарядный блок + снаряды
    "set4b":  "pauk_04.jpg",
    "full":   "pauk_05.jpg",   # полный сет с чехлами
    "holster":"pauk_06.jpg",   # пистолет в чехле
    "pouch":  "pauk_07.jpg",
    "holster2":"pauk_08.jpg",
    "pouch_emr":"pauk_09.jpg",
    "pouch_mc":"pauk_10.jpg",
    "pouch2": "pauk_11.jpg",
    "pouch3": "pauk_12.jpg",
    "pouch4": "pauk_13.jpg",
}

BGW, BGH = 2560, 1440
COVER = {}

def bg_plate(name):
    if name in COVER:
        return COVER[name]
    im = PH[P[name]]
    s = max(BGW / im.width, BGH / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - BGW) // 2; y = (im.height - BGH) // 2
    im = im.crop((x, y, x + BGW, y + BGH))
    im = im.point(lambda v: int(v * 0.44))
    im = Image.blend(im, Image.new("RGB", (BGW, BGH), (10, 22, 40)), 0.32)
    COVER[name] = im
    return im

PCACHE = {}

def photo_tile(name, w, h, zoom=1.0, px=0.0, py=0.0):
    key = (name, w, h)
    if key not in PCACHE:
        im = PH[P[name]]
        s = max(w * 1.7 / im.width, h * 1.7 / im.height)
        PCACHE[key] = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    src = PCACHE[key]
    cw, ch = int(w * 1.7 / zoom), int(h * 1.7 / zoom)
    cw = min(cw, src.width); ch = min(ch, src.height)
    cx = src.width / 2 + px * (src.width - cw) / 2
    cy = src.height / 2 + py * (src.height - ch) / 2
    x0 = int(clamp(cx - cw / 2, 0, src.width - cw))
    y0 = int(clamp(cy - ch / 2, 0, src.height - ch))
    out = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)
    out = out.point(lambda v: int(clamp(v * 0.90, 0, 255)))
    return Image.blend(out, Image.new("RGB", (w, h), (12, 26, 44)), 0.10)

def camera(name, t, dur, z0=1.0, z1=1.08, px=0.0, py=0.0):
    img = bg_plate(name)
    p = eio(c01(t / max(dur, .001)))
    z = z0 + (z1 - z0) * p
    cw, ch = BGW / z, BGH / z
    cx = BGW / 2 + px * (BGW - cw) / 2 + math.sin(t * 1.31) * 4
    cy = BGH / 2 + py * (BGH - ch) / 2 + math.cos(t * 1.73) * 3
    x0 = int(clamp(cx - cw / 2, 0, BGW - cw)); y0 = int(clamp(cy - ch / 2, 0, BGH - ch))
    return img.crop((x0, y0, x0 + int(cw), y0 + int(ch))).resize((W, H), Image.BILINEAR)

# ───────── статика ─────────
VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_v = ImageDraw.Draw(VIGN)
for i in range(140):
    k = i / 140.0; ins = int(-260 + k * 620)
    _v.ellipse([ins, ins * .62, W - ins, H - ins * .62], outline=(0, 0, 0, int(3 + k * 2.2)), width=6)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(24))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 26))

_rng = np.random.default_rng(5)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 34, (H // 2, W // 2), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 20))))

ENV = np.load(os.path.join(BASE, "env.npy")) if os.path.exists(os.path.join(BASE, "env.npy")) else None

SWEEP = None
def make_sweep():
    g = Image.new("RGBA", (W + 700, H + 700), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for i in range(26):
        dg.line([(i * 26, 0), (i * 26 + 700, H + 700)], fill=(120, 255, 220, 5), width=26)
    return g.filter(ImageFilter.GaussianBlur(40))
SWEEP = make_sweep()

# ───────── примитивы ─────────
def brackets(d, x, y, w, h, col=(0, 229, 160, 190), ln=18, wd=2):
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        d.line([(cx, cy), (cx + sx * ln, cy)], fill=col, width=wd)
        d.line([(cx, cy), (cx, cy + sy * ln)], fill=col, width=wd)

def kicker(d, x, y, s, col=ACC, size=24):
    f = F(MONO, size); w = tw(d, s, f)
    d.rectangle([x, y, x + w + 34, y + 44], fill=a((8, 26, 22), 236), outline=a(col, 150), width=1)
    d.rectangle([x, y, x + 6, y + 44], fill=a(col, 255))
    d.text((x + 18, y + 10), s, font=f, fill=a(col, 255))

def rtext(d, xy, s, f, col, p, dy=26):
    p = c01(p)
    if p <= 0: return
    e = eout(p)
    d.text((xy[0], xy[1] + (1 - e) * dy), s, font=f, fill=a(col, 255 * e))

def wipe_title(d, xy, s, f, col, p, fill_bg=(8, 11, 17, 238)):
    p = c01(p)
    if p <= 0: return
    w = tw(d, s, f)
    rw = w * eout(min(1, p * 1.8))
    d.rectangle([xy[0] - 20, xy[1] - 12, xy[0] + rw + 16, xy[1] + f.size * 1.28], fill=fill_bg)
    if p > 0.05:
        d.text(xy, s, font=f, fill=a(col, 255 * c01((p - .05) / .6)))

def waveform(d, x, y, w, h, t, col=ACC, alpha=120, bars=64, drive=1.0):
    if ENV is None: return
    i0 = int(t * FPS) % len(ENV)
    step = max(1, len(ENV) // 400)
    for i in range(bars):
        v = float(ENV[(i0 + i * step) % len(ENV)]) * drive
        bh = max(2, int(clamp(v, 0, 1) * h))
        bx = x + i * (w / bars)
        d.rectangle([bx, y + (h - bh) / 2, bx + max(2, w / bars - 2), y + (h + bh) / 2], fill=a(col, alpha))

def meter(d, x, y, t, n=18, col=ACC):
    if ENV is None: return
    i0 = int(t * FPS) % len(ENV)
    for i in range(n):
        v = float(ENV[(i0 + i * 3) % len(ENV)])
        bh = int(4 + v * 16)
        d.rectangle([x + i * 6, y - bh + 10, x + i * 6 + 4, y + 10], fill=a(col, 150 + v * 100))

def photo_panel(ov, d, name, x, y, w, h, t, zoom=1.03, py=0.0, label=None, idx=None):
    d.rectangle([x - 10, y - 10, x + w + 10, y + h + 10], fill=(7, 10, 16, 246))
    d.rectangle([x - 10, y - 10, x + w + 10, y + h + 10], outline=a(LINE, 255), width=1)
    z = zoom + 0.035 * math.sin(t * .55) + 0.012 * math.sin(t * 1.7)
    ov.paste(photo_tile(name, w, h, z, 0.22 * math.sin(t * .38), py + 0.10 * math.cos(t * .31)), (x, y))
    brackets(d, x - 10, y - 10, w + 20, h + 20, a(ACC, 200))
    if idx:
        d.text((x + w - 16, y + 14), idx, font=F(MONO, 24), fill=a(ACC, 215), anchor="ra")
    if label:
        f = F(MONO, 24); lw = tw(d, label, f)
        d.rectangle([x - 10, y + h + 10, x + lw + 30, y + h + 50], fill=(8, 11, 17, 248))
        d.rectangle([x - 10, y + h + 10, x - 4, y + h + 50], fill=a(ACC, 255))
        d.text((x + 4, y + h + 20), label, font=f, fill=a(ACC, 250))

def ambient(ov, d, t):
    p = (t % 7.0) / 7.0
    ov.alpha_composite(SWEEP, (int(-700 + p * (W + 1400)), -350))
    sy = H - 96
    d.rectangle([0, sy, W, sy + 30], fill=(8, 11, 17, 238))
    d.line([(0, sy), (W, sy)], fill=a((26, 40, 58), 255), width=1)
    msg = ("ПЕРЕХВАТ БПЛА  •  СЕТЬ 2,5 × 2,5 М = 6 М²  •  ДАЛЬНОСТЬ 25–30 М  •  "
           "30 М/С  •  ЭЛЕКТРОННЫЙ ЗАПАЛ  •  ПЕРЕЗАРЯДКА ОТ 2 С  •  "
           "400 / 650 Г  •  IP54  •  ДО -40 °C  •  ")
    fm = F(MONO, 24); mw = tw(d, msg, fm)
    x = int(-(t * 90) % mw)
    while x < W:
        d.text((x, sy + 7), msg, font=fm, fill=a((150, 200, 195), 170))
        x += mw

def chrome(ov, d, t, total, section):
    """Верхняя и нижняя плашки. Крупный шрифт, без бегущей строки."""
    d.rectangle([0, 0, W, 72], fill=(9, 12, 18, 250))
    d.line([(0, 72), (W, 72)], fill=a(ACC, 130), width=1)
    d.rectangle([0, 0, 7, 72], fill=a(ACC, 255))
    fb = F(RUSSO, 34)
    d.text((26, 19), "«В ОКОПЕ»", font=fb, fill=a(TXT, 255))
    xb = 26 + tw(d, "«В ОКОПЕ»", fb) + 24
    fm = F(MONO, 22)
    s1 = "//  ПРОТИВОДЕЙСТВИЕ БПЛА"
    d.text((xb, 26), s1, font=fm, fill=a(DIM, 235))
    xb2 = xb + tw(d, s1, fm) + 20
    d.text((xb2, 26), f"//  {section}", font=fm, fill=a(ACC, 240))

    p = clamp(t / total, 0, 1)
    d.rectangle([0, 73, W, 77], fill=(12, 18, 26, 245))
    d.rectangle([0, 73, int(W * p), 77], fill=a(ACC, 235))
    d.rectangle([int(W * p) - 2, 71, int(W * p) + 2, 79], fill=a(ACC, 255))

    d.ellipse([W - 30, 26, W - 14, 42], fill=a(RED, 230))
    d.text((W - 290, 26), f"TC {int(t//60):02d}:{int(t%60):02d}", font=F(MONO, 22), fill=a(ACC, 240))
    meter(d, W - 470, 52, t)

    d.rectangle([0, H - 64, W, H], fill=(9, 12, 18, 252))
    d.line([(0, H - 64), (W, H - 64)], fill=a(LINE, 255), width=1)
    ff = F(MONO, 22)
    d.text((26, H - 44), "ПАУК 30Б  //  РУЧНОЙ СЕТКОМЁТ", font=ff, fill=a(DIM, 235))
    vk = "vk.com/vokope_rus"
    d.text((W - 26, H - 44), vk, font=ff, fill=a(ACC, 235), anchor="ra")
    tg = "t.me/vokope_ru"
    d.text((W - 26 - tw(d, vk, ff) - 34, H - 44), tg, font=ff, fill=a(ACC, 235), anchor="ra")


# ───────────────────────── примитивы вёрстки ─────────────────────────
def head(d, kick, title, col=ACC, y=96, tsize=64, maxw=1680):
    kicker(d, 70, y, kick, col, 26)
    f = fit(title, RUSSO, tsize, maxw)
    d.text((70, y + 58), title, font=f, fill=a(TXT, 255))
    return y + 58 + int(f.size * 1.24)


def sub(d, x, y, s, col=DIM, size=32, maxw=None):
    f = fit(s, MONO, size, maxw) if maxw else F(MONO, size)
    d.text((x, y), s, font=f, fill=a(col, 245))
    return y + int(size * 1.3)


def row2(d, x, y, w, k, v, col=ACC, h=112, ks=38, vs=30):
    d.rectangle([x, y, x + w, y + h], fill=(10, 14, 21, 244), outline=a(LINE, 255), width=1)
    d.rectangle([x, y, x + 8, y + h], fill=a(col, 255))
    d.text((x + 34, y + 12), k, font=F(RUSSO, ks), fill=a(TXT, 255))
    d.text((x + 34, y + h - 46), v, font=F(MONO, vs), fill=a(DIM, 240))


def stat(d, x, y, val, lbl, col=ACC, vs=130, ls=28):
    d.text((x, y), val, font=F(RUSSO, vs), fill=a(col, 255))
    d.text((x, y + int(vs * 1.14)), lbl, font=F(MONO, ls), fill=a(DIM, 240))


# ═════════════ сцена 1: представление ═════════════
def scene1(base, ov, d, t, l):
    if l < 7.10:
        d.rectangle([0, 296, 1240, 1000], fill=(6, 9, 14, 226))
        d.rectangle([0, 296, 9, 1000], fill=a(ACC, 255))
        kicker(d, 70, 328, "ТЕХНИЧЕСКИЙ ОБЗОР  //  ПАУК 30Б", ACC, 26)
        p1 = eout(c01((l - .45) / .8))
        d.text((66, 396 + (1 - p1) * 26), "ПАУК", font=fit("ПАУК", RUSSO, 200, 900),
               fill=a(TXT, 255 * p1))
        p2 = eout(c01((l - .85) / .7))
        d.text((72, 612 + (1 - p2) * 18), "30Б", font=F(RUSSO, 112), fill=a(ACC, 255 * p2))
        d.text((368, 668), "БЫСТРОЗАРЯДНЫЙ", font=F(MONO, 34), fill=a(DIM, 255 * p2))
        p3 = eout(c01((l - 1.15) / .6))
        d.text((74, 748), "РУЧНОЙ ПЕХОТНЫЙ СЕТКОМЁТ",
               font=fit("РУЧНОЙ ПЕХОТНЫЙ СЕТКОМЁТ", RUSSO, 50, 1140), fill=a(TXT, 255 * p3))
        d.text((74, 816), "ПЕРЕХВАТ МУЛЬТИРОТОРНЫХ ДРОНОВ", font=F(MONO, 32), fill=a(DIM, 245 * p3))

        chips = ["25–30 М", "6 М²", "400 / 650 Г", "IP54"]
        for i, c in enumerate(chips):
            pp = c01((l - 1.5 - i * .1) / .45)
            if pp <= 0: continue
            cf = F(MONO, 30); cw = tw(d, c, cf) + 44
            cx = 74 + i * 260
            yy = int(880 + (1 - eout(pp)) * 16)
            d.rounded_rectangle([cx, yy, cx + cw, yy + 60], 2, fill=(11, 16, 24, 242), outline=a(ACC, 130))
            d.text((cx + 22, yy + 15), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        if 1.6 < l < 5.8:
            photo_panel(ov, d, "holster", 1300, 360, 560, 470, t, 1.09, label="В ЧЕХЛЕ, НА СНАРЯЖЕНИИ")

    elif l < 9.00:
        kicker(d, 70, 100, "ПРИНЦИП РАБОТЫ", ACC, 26)
        f = fit("НАПРАВИЛ.", RUSSO, 88, 900)
        for i, (txt, col, dly) in enumerate([("НАПРАВИЛ.", TXT, .1), ("ВЫСТРЕЛИЛ.", TXT, .26),
                                             ("ПОЙМАЛ.", ACC, .42)]):
            pp = eout(c01((l - dly) / .45))
            d.text((70, 186 + i * 96 + (1 - pp) * 22), txt, font=f, fill=a(col, 255 * pp))
        d.line([(70, 486), (70 + 860 * eout(c01((l - .6) / .7)), 486)], fill=a(ACC, 180), width=3)

        steps = [("01", "ПРИЦЕЛИВАНИЕ", "пистолетная рукоять, ровная кисть"),
                 ("02", "ВЫСТРЕЛ", "электронный запал, пиропатрон"),
                 ("03", "ПЕРЕХВАТ", "сеть накрывает винты дрона")]
        for i, (num, tt, s) in enumerate(steps):
            pp = c01((l - .75 - i * .18) / .5)
            if pp <= 0: continue
            yy = int(556 + i * 128 + (1 - eout(pp)) * 22)
            d.rectangle([70, yy, 1080, yy + 112], fill=(12, 17, 25, 242), outline=a(LINE, 255))
            d.rectangle([70, yy, 78, yy + 112], fill=a(ACC, 255))
            d.text((98, yy + 30), num, font=F(RUSSO, 40), fill=a(ACC, 235))
            d.text((176, yy + 14), tt, font=F(RUSSO, 38), fill=a(TXT, 255 * eout(pp)))
            d.text((176, yy + 60), s, font=F(MONO, 28), fill=a(DIM, 255 * eout(pp)))

        photo_panel(ov, d, "set4", 1160, 190, 700, 620, t, 1.05, label="ПАУК 30Б / 4 СНАРЯДА", idx="01")

    elif l < 17.50:
        d.rectangle([0, 96, W, 240], fill=(6, 9, 14, 234))
        kicker(d, 70, 108, "СХЕМА ПЕРЕХВАТА", ACC, 26)
        d.text((70, 158), "СЕТЬ, А НЕ ПОМЕХА", font=fit("СЕТЬ, А НЕ ПОМЕХА", RUSSO, 56, 900), fill=a(TXT, 255))

        d.rectangle([60, 270, 1860, 790], fill=(7, 10, 16, 240), outline=a(LINE, 255))
        for gx2 in range(60, 1860, 90):
            d.line([(gx2, 270), (gx2, 790)], fill=a((13, 19, 27), 255))
        for gy2 in range(270, 790, 90):
            d.line([(60, gy2), (1860, gy2)], fill=a((13, 19, 27), 255))

        # пистолет
        px0, py0 = 260, 560
        d.rounded_rectangle([px0 - 90, py0 - 34, px0 + 90, py0 + 34], 10,
                            fill=(26, 32, 42, 255), outline=a(DIM, 210), width=3)
        d.rectangle([px0 + 78, py0 - 18, px0 + 170, py0 + 18], fill=(42, 48, 58, 255), outline=a(DIM, 190))
        d.line([(px0 - 60, py0 + 34), (px0 - 40, py0 + 120)], fill=a(DIM, 220), width=18)
        d.text((px0, py0 + 142), "ПАУК 30Б", font=F(MONO, 32), fill=a(ACC, 240), anchor="ma")

        # дрон
        drx, dry = 1580, 420
        bob = math.sin(l * 2.2) * 10
        d.line([(drx - 70, dry - 26 + bob), (drx + 70, dry - 26 + bob)], fill=a(DIM, 235), width=5)
        d.rectangle([drx - 34, dry - 26 + bob, drx + 34, dry + 34 + bob], fill=(30, 36, 46, 255), outline=a(WARN, 210), width=3)
        for sx in (-70, 70):
            d.ellipse([drx + sx - 26, dry - 52 + bob, drx + sx + 26, dry + bob], outline=a(WARN, 200), width=3)
        d.text((drx, dry + 128 + bob), "ЦЕЛЬ / ДРОН", font=F(MONO, 32), fill=a(WARN, 240), anchor="ma")

        # траектория
        for k in range(26):
            xx = 350 + k * 46
            yy = 560 - k * 5
            if xx < drx - 90:
                d.line([(xx, yy), (xx + 22, yy - 2)], fill=a(ACC, 120), width=3)

        # сеть в полёте
        pp = eout(c01((l - .4) / 1.6))
        nx = 360 + int(890 * pp); ny = 556 - int(110 * pp)
        size = 40 + int(50 * pp)
        if l > .4:
            d.rectangle([nx, ny - size, nx + size * 2, ny + size], outline=a(ACC, 245), width=4)
            for k in range(1, 4):
                d.line([(nx + k * size / 2, ny - size), (nx + k * size / 2, ny + size)], fill=a(ACC, 150))
                d.line([(nx, ny - size + k * size / 2), (nx + size * 2, ny - size + k * size / 2)], fill=a(ACC, 150))
            d.text((nx, ny - size - 34), "СЕТЬ 6 М²", font=F(MONO, 30), fill=a(ACC, 240), anchor="ma")

        d.line([(70, 800), (1850, 800)], fill=a(LINE, 255), width=2)
        stats = [("25–30 М", "дальность", ACC), ("30 М/С", "скорость", ACC2), ("< 1 С", "подлёт", TXT)]
        for i, (v, k, col) in enumerate(stats):
            x = 70 + i * 600
            d.text((x, 838), v, font=F(RUSSO, 58), fill=a(col, 255))
            d.text((x + 4, 912), k, font=F(MONO, 30), fill=a(DIM, 235))

    elif l < 22.20:
        d.rectangle([0, 96, W, 250], fill=(6, 9, 14, 234))
        kicker(d, 70, 108, "СРАВНЕНИЕ ПОДХОДОВ", WARN, 26)
        d.text((70, 158), "ПЕРЕХВАТ ИЛИ ПОДАВЛЕНИЕ", font=fit("ПЕРЕХВАТ ИЛИ ПОДАВЛЕНИЕ", RUSSO, 56, 1400), fill=a(TXT, 255))

        cols = [(70, "РЭБ", "ПОДАВЛЕНИЕ СИГНАЛА", WARN,
                 ["глушит канал управления", "нужен расчёт и питание", "дрон может вернуться в строй"]),
                (990, "ПАУК 30Б", "ФИЗИЧЕСКИЙ ПЕРЕХВАТ", ACC,
                 ["сеть наматывается на винты", "питание нужно только для выстрела", "снаряд — расходник, корпус многоразовый"])]
        for x, nm, sub_, col, lines in cols:
            d.rectangle([x, 300, x + 860, 900], fill=(10, 14, 21, 244), outline=a(col, 150), width=2)
            d.text((x + 34, 320), nm, font=F(RUSSO, 60), fill=a(col, 255))
            d.text((x + 36, 398), sub_, font=F(MONO, 28), fill=a(TXT, 240))
            for k, line in enumerate(lines):
                yy = 480 + k * 90
                d.rectangle([x + 34, yy + 12, x + 44, yy + 22], fill=a(col, 255))
                d.text((x + 62, yy), line, font=F(MONO, 32), fill=a(DIM, 240))
            d.text((x + 34, 790), "ЦЕЛЬ ОСТАЁТСЯ В ВОЗДУХЕ" if col == WARN else "ЦЕЛЬ ПАДАЕТ РЯДОМ",
                   font=F(RUSSO, 32), fill=a(col, 240))

    else:
        d.rectangle([0, 96, W, 250], fill=(6, 9, 14, 234))
        kicker(d, 70, 108, "ДАЛЬНОСТЬ", ACC2, 26)
        d.text((70, 158), "25-30 МЕТРОВ", font=fit("25-30 МЕТРОВ", RUSSO, 56, 1200), fill=a(TXT, 255))

        gx, gy, gw = 70, 336, 1780
        d.rectangle([gx, gy, gx + gw, gy + 150], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(7):
            xx = gx + 50 + i * (gw - 100) / 6
            d.line([(xx, gy + 92), (xx, gy + 150)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 162), str(i * 5), font=F(MONO, 30), fill=a(DIM, 225), anchor="ma")
        pp = eout(c01((l - .10) / 1.05))
        d.rectangle([gx + 50, gy + 46, gx + 50 + int((gw - 100) * .92 * pp), gy + 92], fill=a(ACC, 215))
        for xx, lbl in ((25, "25 М"), (30, "30 М")):
            px = gx + 50 + xx * (gw - 100) / 30
            d.line([(px, gy - 18), (px, gy + 92)], fill=a(WARN, 225), width=4)
            d.text((px, gy - 84), lbl, font=F(RUSSO, 40), fill=a(WARN, 255), anchor="ma")

        stats = [("30 М/С", "скорость снаряда", ACC2), ("1 С", "подлёт на 30 м", ACC),
                 ("6 М²", "площадь полотна", TXT)]
        for i, (v, k, col) in enumerate(stats):
            x = 70 + i * 620
            d.text((x, 596), v, font=F(RUSSO, 78), fill=a(col, 255))
            d.text((x + 4, 694), k, font=F(MONO, 30), fill=a(DIM, 235))


# ═════════════ сцена 2: ТТХ ═════════════
def scene2(base, ov, d, t, l):
    if l < 8.75:
        y = head(d, "ТАКТИКО-ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ", "ГЕОМЕТРИЯ ПЕРЕХВАТА", ACC, 100, 60)
        # квадрат
        gx, gy, gs = 74, 330, 470
        pp = eout(c01((l - .2) / 1.2))
        d.rectangle([gx, gy, gx + gs, gy + gs], outline=a(ACC, 240), width=4)
        for k in range(1, 10):
            xx = gx + k * gs / 10
            d.line([(xx, gy), (xx, gy + gs)], fill=a(ACC, 80))
            d.line([(gx, gy + k * gs / 10), (gx + gs, gy + k * gs / 10)], fill=a(ACC, 80))
        d.text((gx + gs / 2, gy - 58), "2,5 М", font=F(RUSSO, 40), fill=a(ACC, 255), anchor="ma")
        d.text((gx + gs / 2, gy + gs + 22), "ПЛОЩАДЬ 6 М²", font=F(RUSSO, 40), fill=a(TXT, 255), anchor="ma")

        rows = [("МОДИФИКАЦИЯ", "ПАУК 30Б / быстрозарядный"),
                ("СЕТЬ", "квадрат 2,5 × 2,5 м"),
                ("ПЛОЩАДЬ", "6 м²"),
                ("ДАЛЬНОСТЬ", "25–30 м"),
                ("СКОРОСТЬ", "30 м/с"),
                ("ГАБАРИТЫ", "190 × 150 × 30 мм")]
        for i, (k, v) in enumerate(rows):
            pp2 = c01((l - .3 - i * .12) / .5)
            if pp2 <= 0: continue
            yy = int(316 + i * 106 + (1 - eout(pp2)) * 18)
            row2(d, 660, yy, 1190, k, v, ACC, 96, 34, 30)

    elif l < 13.13:
        head(d, "МАССА", "400 / 650 ГРАММОВ", ACC2, 100, 64)
        d.text((70, 262), "снаряжённый — с картриджем, готов к выстрелу", font=F(MONO, 30), fill=a(DIM, 240))

        for i, (k, v, col) in enumerate([("БЕЗ КАРТРИДЖА", 400, ACC), ("В СНАРЯЖЁННОМ ВИДЕ", 650, ACC2)]):
            pp = eout(c01((l - .3 - i * .3) / .8))
            yy = 336 + i * 190
            d.text((70, yy), k, font=F(MONO, 28), fill=a(DIM, 235))
            d.text((70, yy + 34), f"{int(v * pp)} г", font=F(RUSSO, 84), fill=a(col, 255))
            d.rectangle([70, yy + 146, 70 + 620, yy + 160], fill=(16, 22, 30, 255))
            d.rectangle([70, yy + 146, 70 + int(620 * (v / 700) * pp), yy + 160], fill=a(col, 235))

        d.text((70, 740), "разница 250 г — масса сменного картриджа", font=F(MONO, 28), fill=a(DIM, 235))
        photo_panel(ov, d, "holster2", 740, 300, 540, 340, t, 1.05, label="В РУКЕ")

        # габариты
        d.rectangle([1360, 300, 1850, 780], fill=(10, 14, 21, 242), outline=a(LINE, 255))
        d.text((1394, 322), "ГАБАРИТЫ, ММ", font=F(MONO, 28), fill=a(DIM, 235))
        d.text((1394, 372), "190 × 150 × 30", font=fit("190 × 150 × 30", RUSSO, 56, 420), fill=a(ACC, 255))
        d.text((1394, 470), "помещается", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((1394, 508), "в нагрудный", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((1394, 546), "подсумок", font=F(MONO, 30), fill=a(TXT, 240))

    elif l < 18.60:
        head(d, "УСТРОЙСТВО СНАРЯДА", "ОДНОРАЗОВЫЙ КАРТРИДЖ", WARN, 100, 56)

        # зона схемы
        d.rectangle([60, 300, 1080, 900], fill=(7, 10, 16, 242), outline=a(LINE, 255))
        cx, cy = 330, 590
        bw, bh = 190, 420
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 26,
                            fill=(16, 21, 29, 252), outline=a(WARN, 210), width=3)
        d.text((cx, cy - 70), "СЕТЬ", font=F(RUSSO, 36), fill=a(ACC, 240), anchor="ma")
        d.text((cx, cy - 20), "6 М²", font=F(MONO, 26), fill=a(DIM, 235), anchor="ma")
        d.line([(cx - 44, cy + 30), (cx + 44, cy + 30)], fill=a(WARN, 200), width=3)
        d.text((cx, cy + 56), "ПИРОПАТРОН", font=F(MONO, 24), fill=a(WARN, 235), anchor="ma")
        d.text((cx, cy + bh / 2 + 22), "ГАБАРИТ 118 × 300", font=F(MONO, 26), fill=a(DIM, 225), anchor="ma")

        calls = [("МЕТАЛЛИЧЕСКИЙ УЗЕЛ", "быстрая стыковка", cy - 150, ACC),
                 ("СЕТЬ 6 М²", "квадрат 2,5 × 2,5 м", cy - 10, ACC),
                 ("ПИРОПАТРОН", "электронная инициация", cy + 150, WARN)]
        for kk, vv, yy2, col in calls:
            d.line([(cx + bw / 2, yy2), (cx + bw / 2 + 90, yy2)], fill=a(col, 200), width=3)
            d.ellipse([cx + bw / 2 - 7, yy2 - 7, cx + bw / 2 + 7, yy2 + 7], fill=a(col, 255))
            d.text((cx + bw / 2 + 110, yy2 - 30), kk, font=F(RUSSO, 32), fill=a(col, 255))
            d.text((cx + bw / 2 + 110, yy2 + 12), vv, font=F(MONO, 26), fill=a(DIM, 240))

        # правая колонка
        d.rectangle([1120, 300, 1850, 900], fill=(9, 13, 19, 242), outline=a(ACC, 120))
        rows = [("СНАРЯД", "одноразовый, с сетью и пиропатроном", WARN),
                ("КОРПУС", "многоразовый, перезаряжается", ACC),
                ("БЛОК", "сменный, на 4 снаряда", ACC2)]
        for i, (k, v, col) in enumerate(rows):
            pp = c01((l - .35 - i * .2) / .55)
            if pp <= 0: continue
            yy = int(340 + i * 176 + (1 - eout(pp)) * 18)
            d.text((1154, yy), k, font=F(RUSSO, 34), fill=a(col, 255))
            d.text((1154, yy + 52), v, font=F(MONO, 26), fill=a(TXT, 240))
        d.text((1154, 848), "отстрелял — поставил новый", font=F(MONO, 26), fill=a(DIM, 230))

    else:
        head(d, "КОМПЛЕКТАЦИЯ", "ВАРИАНТЫ ПОСТАВКИ", ACC, 100, 56)
        d.text((70, 258), "сеткомёт плюс основной заряд: 4, 6 или 10 снарядов", font=F(MONO, 30), fill=a(DIM, 240))

        for i, (nm, n, tt, ss) in enumerate([("set4", "4", "БАЗОВЫЙ", "стартовый комплект"),
                                            ("set6", "6", "ОПТИМАЛЬНЫЙ", "баланс веса и запаса"),
                                            ("full", "10", "МАКСИМАЛЬНЫЙ", "длительная работа")]):
            pp = c01((l - .25 - i * .2) / .55)
            if pp <= 0: continue
            x = 70 + i * 600
            y = int(340 + (1 - eout(pp)) * 26)
            photo_panel(ov, d, nm, x, y, 540, 280, t, 1.04)
            d.text((x - 10, y + 320), n, font=F(RUSSO, 84), fill=a(ACC, 255))
            d.text((x + 96, y + 330), tt, font=fit(tt, RUSSO, 32, 450), fill=a(TXT, 255))
            d.text((x + 96, y + 376), ss, font=fit(ss, MONO, 26, 450), fill=a(DIM, 240))

        d.rectangle([60, 820, 1860, 940], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((92, 842), "В КОМПЛЕКТЕ: ПИСТОЛЕТ + ОСНОВНОЙ ЗАРЯД + ЧЕХОЛ  •  ЦВЕТ: ЧЁРНЫЙ / ХАКИ",
               font=F(MONO, 28), fill=a(TXT, 245))
        d.text((92, 892), "на изделие есть декларация о соответствии", font=F(MONO, 28), fill=a(ACC, 235))


# ═════════════ сцена 3: механика ═════════════
def scene3(base, ov, d, t, l):
    if l < 5.00:
        head(d, "ПЕРЕЗАРЯДКА", "ОТ 2 СЕКУНД", ACC, 100, 64)
        d.text((70, 262), "сменный снаряд: снял, поставил, готов", font=F(MONO, 30), fill=a(DIM, 245))

        steps = [("СНЯТЬ", "отработанный картридж"), ("ПОСТАВИТЬ", "новый снаряд"),
                 ("ГОТОВ", "к следующему выстрелу")]
        for i, (k, s) in enumerate(steps):
            pp = c01((l - .3 - i * .22) / .5)
            if pp <= 0: continue
            x = 70 + i * 600
            y = int(360 + (1 - eout(pp)) * 24)
            d.rectangle([x, y, x + 560, y + 300], fill=(11, 16, 23, 246), outline=a(LINE, 255))
            d.ellipse([x + 40, y + 40, x + 120, y + 120], fill=(10, 18, 22, 250), outline=a(ACC, 230), width=4)
            d.text((x + 80, y + 62), f"{i+1}", font=F(RUSSO, 46), fill=a(ACC, 255), anchor="ma")
            d.text((x + 40, y + 150), k, font=F(RUSSO, 42), fill=a(TXT, 255))
            d.text((x + 40, y + 212), s, font=F(MONO, 28), fill=a(DIM, 240))

        d.line([(70, 740), (1850, 740)], fill=a(LINE, 255), width=3)
        d.text((70, 700), "0 С", font=F(MONO, 28), fill=a(DIM, 215), anchor="ls")
        d.text((1850, 700), "2 С", font=F(MONO, 28), fill=a(ACC, 230), anchor="rs")
        pp = eout(c01((l - .5) / 1.4))
        d.rectangle([70, 726, 70 + int(1780 * pp), 754], fill=a(ACC, 225))

        d.text((70, 820), "ЦИКЛ БЕЗ ИНСТРУМЕНТОВ", font=F(RUSSO, 44), fill=a(ACC2, 255))
        d.text((70, 886), "в поле, в перчатках, одной рукой", font=F(MONO, 30), fill=a(TXT, 240))

    elif l < 10.00:
        head(d, "ПИТАНИЕ И ЭЛЕКТРОНИКА", "5 В / 3,5 А·Ч", ACC2, 100, 64)
        d.text((70, 262), "USB Type-C, электронная инициация", font=F(MONO, 30), fill=a(DIM, 240))

        rows = [("ПИТАНИЕ", "+5 В"), ("АККУМУЛЯТОР", "3,5 А·ч"),
                ("ЗАРЯДКА", "USB Type-C"), ("ПРЕДОХРАНИТЕЛЬ", "двухпозиционный тумблер")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - .25 - i * .13) / .45)
            if pp <= 0: continue
            yy = int(340 + i * 150 + (1 - eout(pp)) * 16)
            row2(d, 70, yy, 1000, k, v, ACC2, 132, 34, 30)

        d.rectangle([1120, 340, 1850, 940], fill=(10, 14, 21, 242), outline=a(ACC, 130))
        d.text((1154, 366), "АВТОНОМНОСТЬ", font=F(MONO, 28), fill=a(DIM, 235))
        d.text((1154, 410), "во включённом", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((1154, 450), "состоянии", font=F(MONO, 30), fill=a(TXT, 240))
        pp = eout(c01((l - .4) / 1.4))
        d.text((1154, 520), f"{int(8 * pp)}", font=F(RUSSO, 160), fill=a(ACC, 255))
        d.text((1400, 660), "недель", font=F(MONO, 34), fill=a(DIM, 240))
        d.text((1154, 800), "56 дней в готовности", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((1154, 846), "без подзарядки", font=F(MONO, 30), fill=a(DIM, 235))

    elif l < 14.60:
        head(d, "БЕЗОПАСНОСТЬ", "ДВУХПОЗИЦИОННЫЙ ТУМБЛЕР", WARN, 100, 52)
        d.text((70, 250), "электронный запал не сработает без взведения", font=F(MONO, 30), fill=a(DIM, 240))

        cx, cy = 560, 520
        pp = eout(c01((l - .3) / 1.1))
        knob_x = (cx - 250) + int(500 * pp)
        d.rounded_rectangle([cx - 400, cy - 90, cx + 400, cy + 90], 50, fill=(12, 17, 24, 252),
                            outline=a(LINE, 255), width=2)
        d.rounded_rectangle([knob_x - 110, cy - 70, knob_x + 110, cy + 70], 38,
                            fill=(32, 40, 50, 255), outline=a(WARN, 225), width=4)
        d.rectangle([knob_x - 40, cy - 30, knob_x + 40, cy + 30], fill=a((18, 23, 30), 255))
        d.ellipse([knob_x - 16, cy - 16, knob_x + 16, cy + 16], fill=a(WARN, 205))
        d.text((cx - 260, cy + 120), "ЗАЩЁЛКА", font=F(MONO, 28), fill=a(WARN, 240), anchor="ma")
        d.text((cx + 260, cy + 120), "ВЗВЕДЕНО", font=F(MONO, 28), fill=a(ACC, 240), anchor="ma")

        rules = [("ЗАЩЁЛКА", "запал заблокирован", WARN), ("ВЗВЕДЕНО", "цепь замкнута", ACC)]
        for i, (k, v, col) in enumerate(rules):
            yy = 730 + i * 106
            row2(d, 70, yy, 1000, k, v, col, 96, 34, 28)

        photo_panel(ov, d, "full", 1120, 300, 700, 500, t, 1.04, label="ПОЛНЫЙ КОМПЛЕКТ С ЧЕХЛАМИ", idx="08")

    elif l < 23.18:
        head(d, "ХРАНЕНИЕ", "ПОДСУМОК С БЫСТРЫМ ДОСТУПОМ", ACC, 100, 52)
        d.text((70, 250), "клапан на фастексе, стропа MOLLE", font=F(MONO, 30), fill=a(ACC, 235))

        photo_panel(ov, d, "pouch_mc", 70, 320, 720, 520, t, 1.05, label="ПОДСУМОК НА СНАРЯЖЕНИИ", idx="09")

        rows = [("ОДНА РУКА", "подсумок открывается на ходу"),
                ("MOLLE", "крепится на любой жилет"),
                ("НЕ МЕШАЕТ", "плоский профиль, без выступов")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - .3 - i * .18) / .5)
            if pp <= 0: continue
            yy = int(340 + i * 128 + (1 - eout(pp)) * 18)
            row2(d, 870, yy, 980, k, v, ACC, 108, 34, 28)

    else:
        head(d, "ИСПОЛНЕНИЕ", "ЧЁРНЫЙ ИЛИ ХАКИ", ACC, 100, 56)
        d.text((70, 258), "корпус — чёрный полимер, подсумки под цвет снаряжения", font=F(MONO, 30), fill=a(DIM, 240))

        cards = [("pouch3", "MULTICAM", "универсальный"), ("pouch_emr", "РУССКИЙ ЦИФРОВОЙ", "лес / поле"),
                 ("holster", "OLIVE / ХАКИ", "базовый")]
        for i, (nm, tt, s) in enumerate(cards):
            pp = c01((l - .25 - i * .2) / .55)
            if pp <= 0: continue
            x = 70 + i * 600
            y = int(330 + (1 - eout(pp)) * 24)
            photo_panel(ov, d, nm, x, y, 540, 340, t, 1.04)
            d.text((x - 10, y + 386), tt, font=F(RUSSO, 36), fill=a(TXT, 255))
            d.text((x - 10, y + 436), s, font=F(MONO, 28), fill=a(ACC, 235))

        d.rectangle([60, 850, 1860, 940], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((92, 872), "ВЛОЖЕНИЕ В СНАРЯЖЕНИЕ: MOLLE-СТРОПА + ФАСТЕКС", font=F(MONO, 30), fill=a(TXT, 245))


# ═════════════ сцена 4: условия, финал ═════════════
def scene4(base, ov, d, t, l):
    if l < 5.60:
        head(d, "УСЛОВИЯ ЭКСПЛУАТАЦИИ", "IP54  /  -40 °C", ACC2, 100, 68)
        d.text((70, 268), "брызги со всех сторон и мороз без отказа электроники", font=F(MONO, 30), fill=a(DIM, 240))

        blocks = [("IP54", "защита от брызг", "пыль и струи под углом"), ("-40 °C", "морозостойкость", "работа в зимних условиях")]
        for i, (v, k, s) in enumerate(blocks):
            x = 70 + i * 620
            pp = c01((l - .3 - i * .2) / .6)
            if pp <= 0: continue
            d.rectangle([x, 350, x + 560, 700], fill=(10, 14, 21, 244), outline=a(ACC2, 140))
            d.text((x + 36, 380), v, font=fit(v, RUSSO, 92, 480), fill=a(ACC2, 255))
            d.text((x + 36, 520), k, font=F(RUSSO, 34), fill=a(TXT, 255))
            d.text((x + 36, 580), s, font=F(MONO, 28), fill=a(DIM, 240))

        d.rectangle([1320, 350, 1850, 700], fill=(10, 14, 21, 244), outline=a(LINE, 255))
        d.text((1354, 372), "ТЕМПЕРАТУРНЫЙ ДИАПАЗОН", font=F(MONO, 26), fill=a(DIM, 235))
        for i in range(5):
            yy = 430 + i * 52
            d.text((1354, yy), ["-40 °C", "-24 °C", "-8 °C", "+24 °C", "+56 °C"][i],
                   font=F(MONO, 28), fill=a(TXT if i < 4 else DIM, 235))

        d.rectangle([60, 780, 1860, 900], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((92, 806), "ЗАЯВЛЕННЫЙ РЕСУРС РАБОТЫ — ДО -40 °C", font=F(RUSSO, 38), fill=a(ACC2, 250))
        d.text((92, 856), "электроника не отказывает на морозе и при брызгах", font=F(MONO, 28), fill=a(DIM, 235))

    elif l < 10.70:
        head(d, "ДОКУМЕНТЫ И ПОСТАВКА", "ДЕКЛАРАЦИЯ О СООТВЕТСТВИИ", ACC, 100, 52)
        d.text((70, 250), "на изделие имеется декларация о соответствии", font=F(MONO, 30), fill=a(DIM, 240))

        d.rectangle([70, 330, 900, 700], fill=(10, 14, 21, 244), outline=a(ACC, 160))
        d.text((106, 356), "ДОКУМЕНТ", font=F(MONO, 26), fill=a(DIM, 235))
        d.text((106, 400), "ДЕКЛАРАЦИЯ", font=F(RUSSO, 56), fill=a(ACC, 255))
        d.text((106, 470), "О СООТВЕТСТВИИ", font=F(RUSSO, 56), fill=a(ACC, 255))
        d.text((106, 590), "предъявляется по запросу", font=F(MONO, 30), fill=a(TXT, 235))

        d.rectangle([960, 330, 1850, 700], fill=(10, 14, 21, 244), outline=a(LINE, 255))
        d.text((994, 356), "ВАРИАТИВНОСТЬ ПОСТАВКИ", font=F(MONO, 26), fill=a(DIM, 235))
        for i, (n, dsc) in enumerate([("4", "базовый"), ("6", "оптимальный"), ("10", "максимальный")]):
            x = 994 + i * 280
            d.text((x, 400), n, font=F(RUSSO, 110), fill=a(ACC, 255))
            d.text((x, 570), dsc, font=F(MONO, 26), fill=a(TXT, 240))

        d.text((70, 790), "варианты поставки: 4, 6 или 10 снарядов", font=F(MONO, 30), fill=a(DIM, 240))

    elif l < 15.30:
        head(d, "РАСХОДНИК", "ОДНОРАЗОВЫЙ СНАРЯД", WARN, 100, 56)
        d.text((70, 258), "сеть и пиропатрон в одном картридже", font=F(MONO, 30), fill=a(DIM, 240))

        photo_panel(ov, d, "stack", 70, 330, 700, 470, t, 1.05, label="БЛОК ИЗ 4 СНАРЯДОВ", idx="11")

        rows = [("СНАРЯД", "одноразовый, с сетью и пиропатроном", WARN),
                ("КОРПУС", "многоразовый, перезаряжается", ACC),
                ("ПОСТАВКА", "сменный снаряд — отдельно", ACC2)]
        for i, (k, v, col) in enumerate(rows):
            pp = c01((l - .25 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(350 + i * 158 + (1 - eout(pp)) * 18)
            d.rectangle([830, yy, 1850, yy + 138], fill=(10, 14, 21, 246), outline=a(col, 130))
            d.rectangle([830, yy, 838, yy + 138], fill=a(col, 255))
            d.text((866, yy + 18), k, font=F(RUSSO, 36), fill=a(col, 255))
            d.text((866, yy + 74), v, font=F(MONO, 28), fill=a(TXT, 240))

    elif l < 19.90:
        head(d, "СЦЕНАРИИ", "БЛИЖНЯЯ ЗОНА", ACC2, 100, 60)
        d.text((70, 264), "там, где дрон уже над головой и поздно бежать", font=F(MONO, 30), fill=a(DIM, 240))

        cards = [("pouch4", "НАД ГОЛОВОЙ", "подлёт к позиции"), ("set6", "ПАТРУЛЬ", "передвижение в колонне"),
                 ("stack", "СТАЦИОНАРНЫЙ ПОСТ", "охрана объекта")]
        for i, (nm, tt, s) in enumerate(cards):
            pp = c01((l - .25 - i * .2) / .55)
            if pp <= 0: continue
            x = 70 + i * 600
            y = int(340 + (1 - eout(pp)) * 24)
            photo_panel(ov, d, nm, x, y, 540, 330, t, 1.04)
            d.text((x - 10, y + 376), tt, font=F(RUSSO, 34), fill=a(TXT, 255))
            d.text((x - 10, y + 424), s, font=F(MONO, 28), fill=a(ACC, 235))

        d.text((70, 850), "РЕНТАБЕЛЬНОСТЬ: КОРПУС МНОГОРАЗОВЫЙ, СНАРЯД — РАСХОДНИК",
               font=F(MONO, 28), fill=a(DIM, 235))

    elif l < 24.30:
        head(d, "ЧЕК-ЛИСТ ПЕРЕД ПОКУПКОЙ", "ЧТО УТОЧНИТЬ", ACC, 100, 60)
        items = [("КОМПЛЕКТАЦИЯ", "4, 6 или 10 снарядов в поставке"),
                 ("СМЕННЫЕ СНАРЯДЫ", "поставляются отдельно, как расходник"),
                 ("ЦВЕТ И ЧЕХОЛ", "чёрный / хаки, подсумок под снаряжение"),
                 ("ДОКУМЕНТЫ", "декларация о соответствии на изделие")]
        for i, (k, v) in enumerate(items):
            pp = c01((l - .2 - i * .16) / .5)
            if pp <= 0: continue
            yy = int(320 + i * 150 + (1 - eout(pp)) * 18)
            d.rectangle([70, yy, 1480, yy + 132], fill=(11, 16, 23, 246), outline=a(ACC, 110))
            d.rectangle([70, yy, 78, yy + 132], fill=a(ACC, 255))
            d.text((106, yy + 14), f"0{i+1}", font=F(MONO, 26), fill=a(ACC, 200))
            d.text((176, yy + 14), k, font=F(RUSSO, 36), fill=a(TXT, 255))
            d.text((176, yy + 68), v, font=F(MONO, 28), fill=a(DIM, 240))

        photo_panel(ov, d, "holster2", 1530, 300, 330, 500, t, 1.05)
        d.text((1530, 830), "БЕЗ ЦЕН", font=F(RUSSO, 44), fill=a(WARN, 250))
        d.text((1530, 892), "только характеристики", font=F(MONO, 26), fill=a(DIM, 230))
        d.text((1530, 930), "и факты из паспорта", font=F(MONO, 26), fill=a(DIM, 230))

    else:
        p = eout(c01((l - .1) / .8))
        d.rectangle([0, 180, W, 980], fill=(6, 9, 14, 232))
        d.rectangle([0, 180, 9, 980], fill=a(ACC, 255))
        d.text((80, 220 + (1 - p) * 20), "ПАУК 30Б", font=F(RUSSO, 130), fill=a(TXT, 255 * p))
        d.text((84, 386), "ПЕРЕХВАТ БПЛА СЕТЬЮ", font=F(RUSSO, 44), fill=a(ACC, 255 * p))
        d.text((84, 462), "25–30 М  •  6 М²  •  ОТ 2 С  •  400 / 650 Г", font=F(MONO, 30), fill=a(DIM, 240))

        p2 = c01((l - .5) / .8)
        d.text((84, 560), "ПОДПИСЫВАЙТЕСЬ НА «В ОКОПЕ»", font=F(MONO, 30), fill=a(TXT, 255 * p2))

        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - .8 - i * .16) / .45)
            if pp <= 0: continue
            yy = int(640 + i * 106 + (1 - eout(pp)) * 20)
            d.rectangle([80, yy, 1260, yy + 92], fill=(11, 16, 23, 246), outline=a(ACC, 120))
            d.rectangle([80, yy, 88, yy + 92], fill=a(ACC, 255))
            d.text((118, yy + 14), k, font=F(RUSSO, 30), fill=a(ACC, 255))
            d.text((118, yy + 52), v, font=F(MONO, 24), fill=a(TXT, 240))

        photo_panel(ov, d, "set4b", 1330, 240, 520, 520, t, 1.04, label="ПАУК 30Б / 4 СНАРЯДА")


def intro(base, ov, d, t, l):
    p = eout(c01(t / .9))
    d.rectangle([0, H // 2 - 150, W, H // 2 + 120], fill=(5, 8, 13, int(200 * p)))
    d.text((W // 2, H // 2 - 92), "«В ОКОПЕ»", font=F(RUSSO, 104), fill=a(TXT, int(255 * c01(t / .7))), anchor="ma")
    d.text((W // 2, H // 2 + 22), "ПРОТИВОДЕЙСТВИЕ БПЛА", font=F(MONO, 34),
           fill=a(ACC, int(230 * c01((t - .4) / .7))), anchor="ma")
    w = 520 * eout(c01((t - .5) / .8))
    d.rectangle([W // 2 - w / 2, H // 2 + 72, W // 2 + w / 2, H // 2 + 75], fill=a(ACC, 220))
    waveform(d, W // 2 - 380, H - 260, 760, 120, t, ACC, 110, 72, 1.0)


SCENES = [(2.60, scene1), (27.52, scene2), (50.06, scene3), (75.84, scene4)]
TOTAL = 103.16
CUTS = [2.60, 8.60, 14.60, 20.20, 24.60, 27.52, 33.12, 38.72, 44.12, 48.12,
        50.06, 56.06, 62.06, 68.16, 73.30, 75.84, 81.24, 86.64, 91.44, 97.44]

def render_frame(t):
    if t < 2.60:
        idx = -1; st, fn = 0.0, intro; l = t; name = "set4"
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001: idx = i
        st, fn = SCENES[idx]; l = t - st
        if idx == 0:
            name = "set4" if l < 7.10 else ("set6" if l < 9.00 else ("holster2" if l < 17.50 else ("pouch3" if l < 22.20 else "full")))
        elif idx == 1:
            name = "stack" if l < 8.75 else ("holster2" if l < 13.13 else ("set6b" if l < 18.60 else "pouch3"))
        elif idx == 2:
            name = "pouch2" if l < 5.00 else ("holster" if l < 10.00 else ("pouch3" if l < 14.60 else ("pouch_mc" if l < 23.18 else "stack")))
        else:
            name = "pouch_emr" if l < 5.60 else ("pouch4" if l < 10.70 else ("stack" if l < 15.30 else ("pouch_mc" if l < 19.90 else ("holster" if l < 24.30 else "holster2"))))

    z0 = 1.02 + .012 * math.sin(t * .9)
    base = camera(name, l, 6.0, z0, z0 + .10, px=.35 * math.sin(t * .13), py=.18 * math.cos(t * .17)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    section = "ПРЕДСТАВЛЕНИЕ" if idx <= 0 else ["ПРЕДСТАВЛЕНИЕ", "ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ", "МЕХАНИКА", "ЭКСПЛУАТАЦИЯ"][idx]
    chrome(ov, d, t, TOTAL, section)
    fn(base, ov, d, t, l)

    out = Image.alpha_composite(base, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])
    for c in CUTS:
        dd = abs(t - c)
        if dd < .12:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), (1 - dd / .12) * .20)
    return out.convert("RGB")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        tt = float(arg)
        render_frame(tt).save(os.path.join(BASE, f"frame_{tt:06.2f}.jpg"), quality=92)
        print("saved", tt)
