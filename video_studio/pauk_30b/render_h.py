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

def kicker(d, x, y, s, col=ACC, size=15):
    f = F(MONO, size); w = tw(d, s, f)
    d.rectangle([x, y, x + w + 24, y + 30], fill=a((8, 26, 22), 236), outline=a(col, 150), width=1)
    d.rectangle([x, y, x + 4, y + 30], fill=a(col, 255))
    d.text((x + 12, y + 8), s, font=f, fill=a(col, 255))

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
        d.text((x + w - 16, y + 14), idx, font=F(MONO, 15), fill=a(ACC, 215), anchor="ra")
    if label:
        f = F(MONO, 15); lw = tw(d, label, f)
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
           "400 / 650 Г  •  IP54  •  ДО −40 °C  •  ")
    fm = F(MONO, 15); mw = tw(d, msg, fm)
    x = int(-(t * 90) % mw)
    while x < W:
        d.text((x, sy + 7), msg, font=fm, fill=a((150, 200, 195), 170))
        x += mw

def chrome(ov, d, t, total, section):
    d.rectangle([0, 0, W, 62], fill=(9, 12, 18, 248))
    d.line([(0, 62), (W, 62)], fill=a(ACC, 120), width=1)
    d.rectangle([0, 0, 6, 62], fill=a(ACC, 255))
    fb = F(RUSSO, 22)
    d.text((26, 20), "«В ОКОПЕ»", font=fb, fill=a(TXT, 255))
    xb = 26 + tw(d, "«В ОКОПЕ»", fb) + 18
    d.text((xb, 23), "//  СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 15), fill=a(DIM, 235))
    d.text((xb + 330, 23), f"//  {section}", font=F(MONO, 15), fill=a(ACC, 240))

    p = clamp(t / total, 0, 1)
    d.rectangle([0, 63, W, 66], fill=(12, 18, 26, 245))
    d.rectangle([0, 63, int(W * p), 66], fill=a(ACC, 235))
    d.rectangle([int(W * p) - 2, 61, int(W * p) + 2, 68], fill=a(ACC, 255))

    d.text((W - 214, 21), f"TC {int(t//60):02d}:{int(t%60):02d}:{int((t*FPS)%FPS):02d}",
           font=F(MONO, 16), fill=a(ACC, 240))
    d.ellipse([W - 250, 24, W - 238, 36], fill=a(RED, 230))
    meter(d, W - 470, 44, t)

    ambient(ov, d, t)
    d.rectangle([0, H - 58, W, H], fill=(9, 12, 18, 252))
    d.line([(0, H - 58), (W, H - 58)], fill=a(LINE, 255), width=1)
    d.text((26, H - 40), "ПАУК 30Б  //  РУЧНОЙ СЕТКОМЁТ", font=F(MONO, 15), fill=a(DIM, 235))
    d.text((W - 430, H - 40), "t.me/vokope_ru", font=F(MONO, 15), fill=a(ACC, 235))
    d.text((W - 250, H - 40), "vk.com/vokope_rus", font=F(MONO, 15), fill=a(ACC, 235))

# ═════════════ сцена 1: представление ═════════════
def scene1(base, ov, d, t, l):
    if l < 6.0:
        d.rectangle([0, 320, 1180, 900], fill=(7, 10, 16, 205))
        d.rectangle([0, 320, 8, 900], fill=a(ACC, 255))
        kicker(d, 70, 282, "ТЕХНИЧЕСКИЙ ОБЗОР  //  ПАУК 30Б", ACC, 15)
        f1 = fit("ПАУК", RUSSO, 168, 1000)
        wipe_title(d, (70, 340), "ПАУК", f1, TXT, (l - .45) / .7)
        f1b = F(RUSSO, 96)
        reveal = c01((l - .75) / .6)
        if reveal > 0:
            e = eout(reveal)
            d.text((76, 512 + (1 - e) * 24), "30Б", font=f1b, fill=a(ACC, 255 * e))
            d.text((330, 560), "БЫСТРОЗАРЯДНЫЙ", font=F(MONO, 24), fill=a(DIM, 255 * e))
        d.text((78, 640), "РУЧНОЙ ПЕХОТНЫЙ СЕТКОМЁТ", font=fit("РУЧНОЙ ПЕХОТНЫЙ СЕТКОМЁТ", RUSSO, 36, 900),
               fill=a(TXT, 255))
        d.text((78, 692), "ПЕРЕХВАТ МУЛЬТИРОТОРНЫХ ДРОНОВ", font=F(MONO, 20), fill=a(DIM, 245))
        d.line([(78, 736), (78 + 760 * eout(c01((l - 1.3) / .8)), 736)], fill=a(ACC, 200), width=2)

        chips = ["25–30 М", "6 М²", "400 / 650 Г", "IP54"]
        for i, c in enumerate(chips):
            pp = c01((l - 1.6 - i * .12) / .45)
            if pp <= 0: continue
            cf = F(MONO, 17); cw = tw(d, c, cf) + 34
            cx = 78 + i * 214
            yy = int(770 + (1 - eout(pp)) * 18)
            d.rounded_rectangle([cx, yy, cx + cw, yy + 42], 2, fill=(11, 16, 24, 240), outline=a(ACC, 120))
            d.text((cx + 17, yy + 11), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        if 1.4 < l < 5.8:
            ix, iy, iw, ih = 1300, 620, 520, 300
            d.rectangle([ix - 8, iy - 8, ix + iw + 8, iy + ih + 8], fill=(7, 10, 16, 235))
            ov.paste(photo_tile("holster", iw, ih, 1.10), (ix, iy))
            brackets(d, ix - 8, iy - 8, iw + 16, ih + 16, a(ACC, 190))
            d.rectangle([ix - 8, iy + ih + 8, ix + 290, iy + ih + 46], fill=(8, 11, 17, 245))
            d.text((ix + 2, iy + ih + 18), "В ЧЕХЛЕ, НА СНАРЯЖЕНИИ", font=F(MONO, 14), fill=a(ACC, 240))

    elif l < 12.0:
        d.rectangle([0, 250, 1080, 890], fill=(7, 10, 16, 210))
        d.rectangle([0, 250, 8, 890], fill=a(ACC, 255))
        kicker(d, 70, 282, "ПРИНЦИП РАБОТЫ", ACC)
        f = fit("НАПРАВИЛ. ВЫСТРЕЛИЛ. ПОЙМАЛ.", RUSSO, 46, 980)
        reveal_text = c01((l - .15) / .5)
        d.text((70, 336), "НАПРАВИЛ.", font=f, fill=a(TXT, 255 * eout(reveal_text)))
        d.text((70, 396), "ВЫСТРЕЛИЛ.", font=f, fill=a(TXT, 255 * eout(c01((l - .3) / .5))))
        d.text((70, 456), "ПОЙМАЛ.", font=f, fill=a(ACC, 255 * eout(c01((l - .45) / .5))))
        d.line([(70, 540), (70 + 900 * eout(c01((l - .6) / .7)), 540)], fill=a(ACC, 170), width=2)

        steps = [("01", "ПРИЦЕЛИВАНИЕ", "пистолетная рукоять, ровная кисть"),
                 ("02", "ВЫСТРЕЛ", "электронный запал, пиропатрон"),
                 ("03", "ПЕРЕХВАТ", "сеть накрывает винты дрона")]
        for i, (num, tt, sub) in enumerate(steps):
            pp = c01((l - .8 - i * .18) / .5)
            if pp <= 0: continue
            yy = int(580 + i * 104 + (1 - eout(pp)) * 24)
            d.rectangle([70, yy, 1040, yy + 88], fill=(12, 17, 25, 240), outline=a(LINE, 255))
            d.rectangle([70, yy, 76, yy + 88], fill=a(ACC, 255))
            d.text((94, yy + 22), num, font=F(RUSSO, 30), fill=a(ACC, 235))
            d.text((164, yy + 14), tt, font=F(RUSSO, 24), fill=a(TXT, 255 * eout(pp)))
            d.text((164, yy + 50), sub, font=F(MONO, 16), fill=a(DIM, 255 * eout(pp)))

        photo_panel(ov, d, "set4", 1160, 250, 700, 560, t, 1.04, label="ПАУК 30Б / 4 СНАРЯДА", idx="01")

    elif l < 17.4:
        # схема перехвата
        d.rectangle([0, 96, W, 214], fill=(6, 9, 14, 232))
        kicker(d, 40, 112, "СХЕМА ПЕРЕХВАТА", ACC)
        d.text((40, 152), "СЕТЬ, А НЕ ПОМЕХА", font=fit("СЕТЬ, А НЕ ПОМЕХА", RUSSO, 44, 900), fill=a(TXT, 255))

        # поле схемы
        d.rectangle([40, 250, 1880, 660], fill=(7, 10, 16, 236), outline=a(LINE, 255))
        # сетка поля
        for gx2 in range(40, 1880, 60):
            d.line([(gx2, 250), (gx2, 660)], fill=a((14, 20, 28), 255))
        for gy2 in range(250, 660, 60):
            d.line([(40, gy2), (1880, gy2)], fill=a((14, 20, 28), 255))

        # стрелок слева — пистолет
        px0, py0 = 190, 455
        d.rounded_rectangle([px0 - 70, py0 - 26, px0 + 70, py0 + 26], 8,
                            fill=(24, 30, 38, 255), outline=a(DIM, 200), width=2)
        d.rectangle([px0 + 60, py0 - 14, px0 + 130, py0 + 14], fill=(40, 46, 56, 255), outline=a(DIM, 180))
        d.text((px0, py0 + 58), "ПАУК 30Б", font=F(MONO, 15), fill=a(ACC, 235), anchor="ma")

        # цель справа
        drx, dry = 1620, 360
        bob = math.sin(l * 2.2) * 8
        d.line([(drx - 52, dry - 20 + bob), (drx + 52, dry - 20 + bob)], fill=a(DIM, 230), width=4)
        for sx in (-52, 52):
            d.ellipse([drx + sx - 32, dry - 38 + bob, drx + sx + 32, dry - 2 + bob], outline=a(WARN, 235), width=3)
        d.rectangle([drx - 24, dry - 4 + bob, drx + 24, dry + 30 + bob], fill=(20, 26, 34, 250), outline=a(WARN, 220))
        d.text((drx, dry + 58), "ЦЕЛЬ / ДРОН", font=F(MONO, 15), fill=a(WARN, 235), anchor="ma")

        # траектория
        d.line([(px0 + 140, py0 - 6), (drx - 90, dry + 20)], fill=a(LINE, 255), width=2)
        for k in range(7):
            t1 = k / 7.0
            xx = px0 + 140 + (drx - 90 - px0 - 140) * t1
            yy = py0 - 6 + (dry + 20 - py0 + 6) * t1
            d.ellipse([xx - 3, yy - 3, xx + 3, yy + 3], fill=a(ACC, 140))
        d.text((760, 596), "ЛИНИЯ ВИЗИРОВАНИЯ", font=F(MONO, 14), fill=a(DIM, 210))

        # летящая сеть
        prog = c01((l - .3) / 2.0)
        nx = 380 + (drx - 560) * eout(prog)
        ny = 420 - 30 * math.sin(l * 1.6)
        size = 70 + 90 * eout(prog)
        step = 26
        xx = nx - size
        while xx < nx + size:
            d.line([(xx, ny - size), (xx, ny + size)], fill=a(ACC, int(150 * c01(prog * 4))))
            xx += step
        yy = ny - size
        while yy < ny + size:
            d.line([(nx - size, yy), (nx + size, yy)], fill=a(ACC, int(150 * c01(prog * 4))))
            yy += step
        d.rectangle([nx - size, ny - size, nx + size, ny + size], outline=a(ACC, 230), width=2)
        d.text((nx, ny + size + 22), "СЕТЬ 2,5 × 2,5 М", font=F(MONO, 15), fill=a(ACC, 235), anchor="ma")

        # шкала дальности на поле
        d.line([(px0, 630), (drx + 60, 630)], fill=a(LINE, 255), width=2)
        for k in range(4):
            xx2 = px0 + (drx + 60 - px0) * k / 3
            d.line([(xx2, 620), (xx2, 640)], fill=a(DIM, 255), width=2)
            d.text((xx2, 646), f"{int(10 + k*10)} м", font=F(MONO, 13), fill=a(DIM, 210), anchor="ma")

        # карточки
        for i, (k, v, col) in enumerate([("ДАЛЬНОСТЬ", "25–30 М", ACC), ("СКОРОСТЬ", "30 М/С", ACC2),
                                          ("ПЛОЩАДЬ", "6 М²", ACC)]):
            x = 40 + i * 460
            d.rectangle([x, 700, x + 430, 900], fill=(10, 15, 22, 247), outline=a(col, 130))
            d.rectangle([x, 700, x + 430, 705], fill=a(col, 255))
            d.text((x + 26, 726), k, font=F(MONO, 15), fill=a(DIM, 235))
            d.text((x + 26, 758), v, font=F(RUSSO, 52), fill=a(col, 255))
            d.rectangle([x + 26, 848, x + 26 + int(360 * eout(c01((l - .4 - i * .15) / 1.0))), 852],
                        fill=a(col, 110))

        d.rectangle([1440, 700, 1880, 900], fill=(9, 13, 19, 247), outline=a(WARN, 130))
        d.text((1466, 726), "ЧТО ЭТО ЗНАЧИТ", font=F(MONO, 15), fill=a(WARN, 235))
        d.text((1466, 760), "по пересечению курса,", font=F(MONO, 18), fill=a(TXT, 245))
        d.text((1466, 794), "а не по шуму винтов", font=F(MONO, 18), fill=a(TXT, 245))
        d.text((1466, 842), "электроника цели не подавляется", font=F(MONO, 14), fill=a(DIM, 230))

    elif l < 22.9:
        # назначение
        kicker(d, 40, 112, "НАЗНАЧЕНИЕ", ACC)
        d.text((40, 152), "ГДЕ ПРИМЕНЯЕТСЯ", font=fit("ГДЕ ПРИМЕНЯЕТСЯ", RUSSO, 46, 900), fill=a(TXT, 255))
        cards = [("okop", "ПОЗИЦИЯ И ОКОП", "ближняя зона над головой"),
                 ("holster", "ПОДРАЗДЕЛЕНИЕ", "повседневное ношение в чехле"),
                 ("full", "ОХРАНА ОБЪЕКТА", "патруль и стационарный пост")]
        for i, (nm, tt, sub) in enumerate(cards):
            pp = c01((l - .15 - i * .2) / .55)
            if pp <= 0: continue
            x = 40 + i * 614
            y = int(248 + (1 - eout(pp)) * 34)
            name = nm if nm in P else "set4"
            d.rectangle([x, y, x + 586, y + 530], fill=(7, 11, 17, 244), outline=a(LINE, 255))
            ov.paste(photo_tile(name, 570, 420, 1.02 + .03 * math.sin(t * .6 + i)), (x + 8, y + 8))
            brackets(d, x, y, 586, 530, a(ACC, 170))
            d.rectangle([x, y + 436, x + 586, y + 522], fill=(9, 12, 18, 250))
            d.text((x + 18, y + 450), tt, font=F(RUSSO, 21), fill=a(TXT, 255))
            d.text((x + 18, y + 484), sub, font=F(MONO, 15), fill=a(ACC, 235))
            d.text((x + 562, y + 20), f"0{i+1}", font=F(MONO, 17), fill=a(ACC, 220), anchor="ra")

        d.rectangle([40, 812, 1640, 900], fill=(10, 15, 22, 246), outline=a(ACC, 120))
        d.rectangle([40, 812, 46, 900], fill=a(ACC, 255))
        d.text((70, 832), "ПРОСТОТА РАСЧЁТА: НАПРАВИЛ — ВЫСТРЕЛИЛ — ПОЙМАЛ",
               font=F(RUSSO, 24), fill=a(TXT, 255))
        d.text((70, 868), "не требует длительной подготовки оператора", font=F(MONO, 15), fill=a(DIM, 235))

    elif l < 27.3:
        kicker(d, 40, 112, "СРАВНЕНИЕ ПОДХОДОВ", WARN)
        d.text((40, 152), "ПЕРЕХВАТ ИЛИ ПОДАВЛЕНИЕ", font=fit("ПЕРЕХВАТ ИЛИ ПОДАВЛЕНИЕ", RUSSO, 42, 1200),
               fill=a(TXT, 255))
        cols = [("РЭБ / ПОДАВИТЕЛЬ", "глушит канал", "дрон теряет управление,\nно остаётся целым", ACC2),
                ("СЕТКОМЁТ «ПАУК»", "физический перехват", "сеть наматывается на винты,\nдрон падает рядом", ACC)]
        for i, (nm, sub, txt, col) in enumerate(cols):
            pp = c01((l - .2 - i * .25) / .5)
            if pp <= 0: continue
            x = 40 + i * 940
            y = int(260 + (1 - eout(pp)) * 30)
            d.rectangle([x, y, x + 900, y + 440], fill=(10, 15, 22, 247), outline=a(col, 150))
            d.rectangle([x, y, x + 900, y + 5], fill=a(col, 255))
            d.text((x + 28, y + 30), nm, font=F(RUSSO, 30), fill=a(col, 255))
            d.text((x + 28, y + 82), sub, font=F(MONO, 18), fill=a(TXT, 240))
            for k, line in enumerate(txt.split("\n")):
                d.text((x + 28, y + 140 + k * 34), line, font=F(MONO, 17), fill=a(DIM, 235))
            d.line([(x + 28, y + 250), (x + 872, y + 250)], fill=a(LINE, 255))
            if i == 0:
                d.text((x + 28, y + 280), "НУЖЕН РАСЧЁТ И ПИТАНИЕ", font=F(MONO, 16), fill=a(WARN, 220))
                d.text((x + 28, y + 316), "дрон может вернуться в строй", font=F(MONO, 16), fill=a(DIM, 225))
            else:
                d.text((x + 28, y + 280), "НЕ НУЖНО ПИТАНИЯ ДЛЯ ВЫСТРЕЛА", font=F(MONO, 16), fill=a(ACC, 225))
                d.text((x + 28, y + 316), "снаряд — расходник, ствол — многоразовый", font=F(MONO, 16), fill=a(DIM, 225))

        photo_panel(ov, d, "stack", 40, 730, 900, 180, t, 1.04, label="СМЕННЫЙ БЛОК СНАРЯДОВ")
        photo_panel(ov, d, "pouch_mc", 980, 730, 900, 180, t, 1.04, label="ПОДСУМОК В MULTICAM")

    else:
        # финал блока 1 — крупный кадр
        kicker(d, 40, 112, "ИЗДЕЛИЕ", ACC)
        d.text((40, 152), "ПАУК 30Б В ДЕТАЛЯХ", font=fit("ПАУК 30Б В ДЕТАЛЯХ", RUSSO, 44, 1000), fill=a(TXT, 255))
        photo_panel(ov, d, "pouch_emr", 40, 240, 620, 470, t, 1.04, label="ЧЕХОЛ В РУССКОМ ЦИФРОВОМ КАМУФЛЯЖЕ", idx="05")
        photo_panel(ov, d, "pouch3", 686, 240, 620, 470, t, 1.04, label="ТРИ ЧЕХЛА ПОД РАЗНЫЕ КАМУФЛЯЖИ", idx="06")
        d.rectangle([1332, 240, 1880, 760], fill=(9, 13, 19, 247), outline=a(ACC, 120))
        d.text((1358, 264), "ВАРИАНТЫ ПОСТАВКИ", font=F(MONO, 15), fill=a(DIM, 235))
        for i, (n, dsc) in enumerate([("4", "снаряда"), ("6", "снарядов"), ("10", "снарядов")]):
            yy = 306 + i * 148
            d.text((1358, yy), n, font=F(RUSSO, 66), fill=a(ACC, 255))
            d.text((1432, yy + 26), dsc, font=F(MONO, 19), fill=a(TXT, 240))
            d.rectangle([1358, yy + 96, 1854, yy + 100], fill=a(LINE, 255))
        photo_panel(ov, d, "pouch2", 40, 760, 1790, 152, t, 1.03, label="СНАРЯЖЕНИЕ: 4, 6 И 10 СНАРЯДОВ")


# ═════════════ сцена 2: ТТХ ═════════════
def scene2(base, ov, d, t, l):
    if l < 5.6:
        d.rectangle([0, 96, W, 230], fill=(6, 9, 14, 232))
        kicker(d, 40, 112, "ТАКТИКО-ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ", ACC)
        d.text((40, 152), "ГЕОМЕТРИЯ ПЕРЕХВАТА", font=fit("ГЕОМЕТРИЯ ПЕРЕХВАТА", RUSSO, 44, 1100), fill=a(TXT, 255))

        # квадрат сети 2,5 x 2,5
        gx, gy, gs = 120, 300, 420
        pp = eout(c01((l - .25) / 1.0))
        d.rectangle([gx, gy, gx + gs * pp, gy + gs * pp], outline=a(ACC, 240), width=3)
        step = 42
        for k in range(1, int(10 * pp)):
            xx = gx + k * step * pp
            d.line([(xx, gy), (xx, gy + gs * pp)], fill=a(ACC, 80))
            d.line([(gx, gy + k * step * pp), (gx + gs * pp, gy + k * step * pp)], fill=a(ACC, 80))
        d.line([(gx, gy - 34), (gx + gs * pp, gy - 34)], fill=a(ACC, 200), width=2)
        d.text((gx + gs * pp / 2, gy - 62), "2,5 М", font=F(RUSSO, 24), fill=a(ACC, 255), anchor="ma")
        d.line([(gx - 34, gy), (gx - 34, gy + gs * pp)], fill=a(ACC, 200), width=2)
        d.text((gx - 58, gy + gs * pp / 2), "2,5 М", font=F(RUSSO, 24), fill=a(ACC, 255), anchor="rm")
        d.text((gx + gs * pp / 2, gy + gs * pp + 22), "ПЛОЩАДЬ 6 М²", font=F(RUSSO, 26), fill=a(TXT, 255), anchor="ma")

        specs = [("МОДИФИКАЦИЯ", "ПАУК 30Б / быстрозарядный"),
                 ("СЕТЬ", "квадрат 2,5 × 2,5 м"),
                 ("ПЛОЩАДЬ ПОЛОТНА", "6 м²"),
                 ("ДАЛЬНОСТЬ", "до 25–30 м"),
                 ("СКОРОСТЬ СНАРЯДА", "30 м/с"),
                 ("ГАБАРИТЫ", "190 × 150 × 30 мм")]
        for i, (k, v) in enumerate(specs):
            p2 = c01((l - .2 - i * .12) / .45)
            if p2 <= 0: continue
            yy = int(300 + i * 104 + (1 - eout(p2)) * 22)
            d.rectangle([700, yy, 1860, yy + 88], fill=(11, 15, 22, 242), outline=a(LINE, 255))
            d.rectangle([700, yy, 705, yy + 88], fill=a(ACC, 255))
            d.text((728, yy + 18), k, font=F(RUSSO, 20), fill=a(ACC, 250))
            d.text((728, yy + 52), v, font=F(MONO, 18), fill=a(TXT, 255 * eout(p2)))

    elif l < 11.2:
        # вес и баланс
        kicker(d, 40, 112, "МАССА", ACC2)
        f = fit("400 / 650 ГРАММОВ", RUSSO, 52, 1000)
        d.text((40, 156), "400 / 650 ГРАММОВ", font=f, fill=a(TXT, 255))
        d.text((40, 226), "снаряжённый — с картриджем, готов к выстрелу", font=F(MONO, 19), fill=a(DIM, 240))

        # весы
        bars = [("БЕЗ КАРТРИДЖА", 400, ACC), ("В СНАРЯЖЁННОМ ВИДЕ", 650, ACC2)]
        for i, (k, v, col) in enumerate(bars):
            pp = eout(c01((l - .3 - i * .25) / 1.0))
            yy = 320 + i * 170
            d.text((40, yy), k, font=F(MONO, 17), fill=a(DIM, 235))
            d.text((40, yy + 28), f"{int(v*pp)} г", font=F(RUSSO, 52), fill=a(col, 255))
            d.rectangle([360, yy + 42, 1000, yy + 62], fill=(15, 22, 32, 240))
            d.rectangle([360, yy + 42, 360 + int(640 * (v / 700)) , yy + 62], fill=a(col, 255))
            for kk in range(14):
                xx = 360 + kk * 45.7
                d.line([(xx, yy + 42), (xx, yy + 62)], fill=a((8, 11, 17), 255), width=2)
        d.text((40, 690), "разница 250 г — это масса сменного картриджа", font=F(MONO, 17), fill=a(DIM, 235))

        # силуэт габаритов
        d.rectangle([1080, 300, 1880, 900], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((1104, 322), "ГАБАРИТЫ, ММ", font=F(MONO, 15), fill=a(DIM, 235))
        # прямоугольник 190x150x30 в масштабе
        sc = 2.6
        bx, by = 1170, 430
        d.rectangle([bx, by, bx + 150 * sc, by + 190 * sc], outline=a(ACC, 200), width=2)
        d.text((bx + 75 * sc, by - 26), "190", font=F(MONO, 18), fill=a(ACC, 240), anchor="ma")
        d.text((bx - 26, by + 95 * sc), "150", font=F(MONO, 18), fill=a(ACC, 240), anchor="rm")
        d.text((bx + 75 * sc, by + 62 * sc), "30", font=F(RUSSO, 60), fill=a(ACC, 255), anchor="mm")
        d.text((bx + 75 * sc, by + 190 * sc + 26), "ТОЛЩИНА КОРПУСА", font=F(MONO, 14), fill=a(DIM, 230), anchor="ma")
        d.text((1340, 820), "помещается в нагрудный подсумок", font=F(MONO, 16), fill=a(ACC, 225))

        photo_panel(ov, d, "holster2", 40, 740, 460, 172, t, 1.04, label="В РУКЕ")
        photo_panel(ov, d, "pouch4", 520, 740, 460, 172, t, 1.04, label="В ПОДСУМКЕ")

    elif l < 17.2:
        # дальность
        kicker(d, 40, 112, "ДАЛЬНОСТЬ И СКОРОСТЬ", ACC)
        d.text((40, 156), "25–30 МЕТРОВ", font=fit("25–30 МЕТРОВ", RUSSO, 56, 900), fill=a(TXT, 255))
        d.text((40, 232), "снаряд идёт 30 м/с — дистанция проходится за секунду", font=F(MONO, 19), fill=a(DIM, 240))

        # шкала дальности
        gx, gy, gw = 100, 380, 1700
        d.rectangle([gx, gy, gx + gw, gy + 60], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(31):
            xx = gx + 40 + i * (gw - 80) / 30
            hh = 26 if i % 5 == 0 else 14
            d.line([(xx, gy + 60 - hh), (xx, gy + 60)], fill=a(LINE if i % 5 else DIM, 255), width=2)
            if i % 5 == 0:
                d.text((xx, gy + 68), str(i), font=F(MONO, 14), fill=a(DIM, 220), anchor="ma")
        pp = eout(c01((l - .25) / 1.4))
        d.rectangle([gx + 40, gy + 20, gx + 40 + int((gw - 80) * 0.90 * pp), gy + 46], fill=a(ACC, 200))
        for xx, lbl in ((25, "25 М"), (30, "30 М")):
            px = gx + 40 + xx * (gw - 80) / 30
            d.line([(px, gy - 14), (px, gy + 60)], fill=a(WARN, 220), width=3)
            d.text((px, gy - 46), lbl, font=F(RUSSO, 22), fill=a(WARN, 255), anchor="ma")

        # таймлайн полёта
        d.rectangle([100, 540, 1820, 720], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((124, 562), "ВРЕМЯ ПОЛЁТА ДО ЦЕЛИ", font=F(MONO, 15), fill=a(DIM, 235))
        tt = [("10 м", "0,33 с"), ("20 м", "0,67 с"), ("30 м", "1,0 с")]
        for i, (dd, tt2) in enumerate(tt):
            x = 200 + i * 540
            d.text((x, 596), dd, font=F(RUSSO, 26), fill=a(TXT, 255))
            d.text((x, 640), tt2, font=F(RUSSO, 40), fill=a(ACC, 255))
            d.rectangle([x, 694, x + 440, 700], fill=a(LINE, 255))
            d.rectangle([x, 694, x + int(440 * eout(c01((l - .4 - i * .2) / .9))), 700], fill=a(ACC, 200))

        photo_panel(ov, d, "set6", 100, 744, 830, 168, t, 1.03, label="КОМПЛЕКТ 6 СНАРЯДОВ")
        photo_panel(ov, d, "set4b", 960, 744, 860, 168, t, 1.03, label="ПИСТОЛЕТ И БОЕКОМПЛЕКТ")

    elif l < 22.9:
        # схема снаряда
        kicker(d, 40, 112, "УСТРОЙСТВО СНАРЯДА", WARN)
        d.text((40, 156), "ОДНОРАЗОВЫЙ КАРТРИДЖ", font=fit("ОДНОРАЗОВЫЙ КАРТРИДЖ", RUSSO, 42, 1100), fill=a(TXT, 255))

        # анатомия картриджа
        d.rectangle([250, 230, 1080, 700], fill=(7, 10, 16, 240), outline=a(LINE, 255))
        cx, cy = 520, 480
        pp = eout(c01((l - .2) / .9))
        # корпус картриджа (реальная форма: скруглённый брусок)
        bw, bh = 118, 300
        box = [cx - bw, cy - bh // 2, cx + bw, cy + bh // 2]
        d.rounded_rectangle(box, 26, fill=(26, 31, 39, 255), outline=a((80, 92, 108), 255), width=2)
        # верхняя площадка со скосом
        d.rounded_rectangle([cx - bw + 16, cy - bh // 2 + 10, cx + bw - 16, cy - bh // 2 + 96], 18,
                            fill=(19, 23, 30, 255))
        # металлический узел
        d.rounded_rectangle([cx - 42, cy - bh // 2 - 46, cx + 42, cy - bh // 2 + 12], 8,
                            fill=(126, 132, 142, 255), outline=a((176, 182, 192), 255), width=2)
        for k in range(4):
            d.line([(cx - 36, cy - bh // 2 - 40 + k * 12), (cx + 36, cy - bh // 2 - 40 + k * 12)],
                   fill=a((92, 98, 108), 255), width=2)
        d.ellipse([cx - 15, cy - bh // 2 - 32, cx + 15, cy - bh // 2 - 2],
                  fill=(24, 27, 32, 255), outline=a((196, 200, 208), 255), width=2)
        # надпись и линия
        d.text((cx, cy + 10), "СЕТЬ", font=F(RUSSO, 20), fill=a(ACC, 210), anchor="mm")
        d.text((cx, cy + 44), "+ ПИРОПАТРОН", font=F(MONO, 13), fill=a(DIM, 215), anchor="ma")
        # сетка-намёк на полотно
        for k in range(-5, 6):
            d.line([(cx + k * 18, cy + 82), (cx + k * 18 + 60, cy + 190)], fill=a(ACC, 40))
        d.text((cx, cy + bh // 2 + 34), "ГАБАРИТ 118 × 300", font=F(MONO, 13), fill=a(DIM, 200), anchor="ma")

        callouts = [("МЕТАЛЛИЧЕСКИЙ УЗЕЛ", "быстрая стыковка", cy - 196, cy - 196, ACC2),
                    ("СЕТЬ 6 М²", "квадрат 2,5 × 2,5 м", cy - 20, cy - 20, ACC),
                    ("ПИРОПАТРОН", "электронная инициация", cy + 140, cy + 140, WARN)]
        for i, (k, v, node_y, y, col) in enumerate(callouts):
            p2 = c01((l - .5 - i * .22) / .5)
            if p2 <= 0: continue
            lx0, lx1 = cx + bw + 14, cx + bw + 86
            # колено, если узел выше подписи
            d.line([(lx0, node_y), (lx1, node_y)], fill=a(col, 220), width=2)
            if abs(node_y - y) > 2:
                d.line([(lx1, node_y), (lx1, y)], fill=a(col, 220), width=2)
            d.ellipse([lx0 - 5, node_y - 5, lx0 + 5, node_y + 5], fill=a(col, 255))
            d.text((lx1 + 16, y - 24), k, font=F(RUSSO, 17), fill=a(col, 255 * eout(p2)))
            d.text((lx1 + 16, y + 2), v, font=F(MONO, 13), fill=a(DIM, 240))

        photo_panel(ov, d, "stack", 1180, 240, 700, 400, t, 1.05, label="БЛОК ИЗ 4 СНАРЯДОВ", idx="07")
        photo_panel(ov, d, "pouch4", 1180, 690, 336, 242, t, 1.05, label="КАРТРИДЖ")
        photo_panel(ov, d, "full", 1544, 690, 336, 242, t, 1.05, label="КОМПЛЕКТ")

        d.rectangle([40, 700, 1120, 900], fill=(9, 13, 19, 246), outline=a(WARN, 110))
        d.text((66, 722), "СНАРЯД — РАСХОДНИК, КОРПУС — МНОГОРАЗОВЫЙ", font=F(MONO, 18), fill=a(WARN, 245))
        d.text((66, 758), "отстрелял — поставил новый, без разборки и инструментов", font=F(MONO, 16), fill=a(TXT, 235))
        d.text((66, 794), "сменный блок на 4 снаряда ускоряет снаряжение", font=F(MONO, 16), fill=a(DIM, 225))

    elif l < 27.6:
        # комплектация
        kicker(d, 40, 112, "КОМПЛЕКТАЦИЯ", ACC)
        d.text((40, 152), "ВАРИАНТЫ ПОСТАВКИ", font=fit("ВАРИАНТЫ ПОСТАВКИ", RUSSO, 46, 1000), fill=a(TXT, 255))
        d.text((40, 214), "сеткомёт плюс основной заряд: 4, 6 или 10 снарядов", font=F(MONO, 19), fill=a(DIM, 240))

        opts = [("set4", "4 СНАРЯДА", "базовый комплект"), ("set6", "6 СНАРЯДОВ", "оптимальный"),
                ("full", "10 СНАРЯДОВ", "максимальный запас")]
        for i, (nm, tt, sub) in enumerate(opts):
            pp = c01((l - .2 - i * .22) / .55)
            if pp <= 0: continue
            x = 40 + i * 614
            y = int(280 + (1 - eout(pp)) * 36)
            d.rectangle([x, y, x + 586, y + 560], fill=(7, 11, 17, 246), outline=a(LINE, 255))
            ov.paste(photo_tile(nm, 570, 440, 1.02 + .03 * math.sin(t * .6 + i)), (x + 8, y + 8))
            brackets(d, x, y, 586, 560, a(ACC, 175))
            d.rectangle([x, y + 456, x + 586, y + 552], fill=(9, 12, 18, 250))
            d.rectangle([x, y + 456, x + 6, y + 552], fill=a(ACC, 255))
            d.text((x + 20, y + 468), tt, font=F(RUSSO, 24), fill=a(TXT, 255))
            d.text((x + 20, y + 506), sub, font=F(MONO, 15), fill=a(ACC, 235))

        d.rectangle([40, 876, 1880, 964], fill=(10, 15, 22, 246), outline=a(ACC, 120))
        d.text((66, 894), "В КОМПЛЕКТЕ: ПИСТОЛЕТ 1 ШТ. + ОСНОВНОЙ ЗАРЯД + ЧЕХОЛ  •  ЦВЕТ: ЧЁРНЫЙ / ХАКИ",
               font=F(MONO, 18), fill=a(TXT, 245))
        d.text((66, 924), "на изделие есть декларация о соответствии", font=F(MONO, 15), fill=a(DIM, 230))

    else:
        # резюме блока
        kicker(d, 40, 112, "ИТОГ БЛОКА", ACC2)
        d.text((40, 152), "СУХИЕ ЦИФРЫ", font=fit("СУХИЕ ЦИФРЫ", RUSSO, 46, 800), fill=a(TXT, 255))
        grid = [("25–30 м", "дальность"), ("6 м²", "площадь сети"), ("30 м/с", "скорость снаряда"),
                ("400 г", "без картриджа"), ("650 г", "снаряжённый"), ("от 2 с", "перезарядка")]
        for i, (v, k) in enumerate(grid):
            pp = c01((l - .15 - i * .12) / .45)
            if pp <= 0: continue
            col = i % 3; row = i // 3
            x = 40 + col * 614; y = int(260 + row * 300 + (1 - eout(pp)) * 30)
            d.rectangle([x, y, x + 586, y + 270], fill=(10, 15, 22, 247), outline=a(LINE, 255))
            d.rectangle([x, y, x + 586, y + 5], fill=a(ACC, 255 * .8))
            d.text((x + 30, y + 50), v, font=F(RUSSO, 62), fill=a(ACC, 255))
            d.text((x + 30, y + 140), k, font=F(MONO, 18), fill=a(DIM, 240))
            d.rectangle([x + 30, y + 190, x + 30 + int(400 * eout(pp)), y + 194], fill=a(ACC, 90))

        d.text((40, 890), "ДАННЫЕ ИЗ ПАСПОРТА ИЗДЕЛИЯ  //  БЕЗ РЕКЛАМНЫХ ОЦЕНОК", font=F(MONO, 15), fill=a(DIM, 190))


# ═════════════ сцена 3: механика ═════════════
def scene3(base, ov, d, t, l):
    if l < 6.0:
        # перезарядка
        kicker(d, 40, 112, "ПЕРЕЗАРЯДКА", ACC)
        d.text((40, 156), "ОТ 2 СЕКУНД", font=fit("ОТ 2 СЕКУНД", RUSSO, 74, 900), fill=a(TXT, 255))
        d.text((40, 262), "сменный снаряд: снял, поставил, готов", font=F(MONO, 20), fill=a(DIM, 245))

        # таймлайн перезарядки
        steps = [("СНЯТЬ", "отработанный", .0), ("ПОСТАВИТЬ", "новый снаряд", .45), ("ГОТОВ", "к выстрелу", .9)]
        for i, (k, sub, xp) in enumerate(steps):
            pp = c01((l - .3 - i * .3) / .5)
            if pp <= 0: continue
            x = 120 + i * 560
            d.ellipse([x - 46, 470 - 46, x + 46, 470 + 46], fill=(11, 16, 23, 250),
                      outline=a(ACC, 230), width=3)
            d.text((x, 458), f"{i+1}", font=F(RUSSO, 34), fill=a(ACC, 255), anchor="ma")
            d.text((x, 540), k, font=F(RUSSO, 24), fill=a(TXT, 255 * eout(pp)), anchor="ma")
            d.text((x, 578), sub, font=F(MONO, 15), fill=a(DIM, 240), anchor="ma")
            if i < 2:
                d.line([(x + 60, 470), (x + 500 - 60, 470)], fill=a(ACC, 120), width=2)
        d.rectangle([120, 680, 1800, 700], fill=(15, 22, 32, 240))
        d.rectangle([120, 680, 120 + int(1680 * eout(c01((l - .3) / 1.6))), 700], fill=a(ACC, 235))
        d.text((120, 716), "0 С", font=F(MONO, 14), fill=a(DIM, 210))
        d.text((1740, 716), "2 С", font=F(MONO, 14), fill=a(ACC, 220), anchor="ra")

        photo_panel(ov, d, "pouch2", 40, 760, 620, 172, t, 1.03, label="СМЕННЫЙ СНАРЯД")
        photo_panel(ov, d, "set4", 686, 760, 620, 172, t, 1.03, label="СНАРЯЖЕНИЕ")
        d.rectangle([1332, 760, 1880, 932], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((1356, 782), "ЦИКЛ", font=F(MONO, 15), fill=a(DIM, 235))
        d.text((1356, 810), "без инструментов", font=F(RUSSO, 24), fill=a(ACC2, 255))
        d.text((1356, 852), "в поле, в перчатках", font=F(MONO, 16), fill=a(TXT, 240))

    elif l < 12.0:
        # электроника и питание
        kicker(d, 40, 112, "ПИТАНИЕ И ЭЛЕКТРОНИКА", ACC2)
        d.text((40, 156), "5 В / 3,5 А·Ч", font=fit("5 В / 3,5 А·Ч", RUSSO, 56, 900), fill=a(TXT, 255))
        d.text((40, 232), "USB Type-C, электронная инициация", font=F(MONO, 19), fill=a(DIM, 240))

        specs = [("НАПРЯЖЕНИЕ", "+5 В"),
                 ("ИСТОЧНИК", "3,5 А·ч"),
                 ("ЗАРЯДКА", "USB Type-C 5 В"),
                 ("ТИП ИНИЦИАЦИИ", "электронная"),
                 ("ВО ВКЛ. СОСТОЯНИИ", "8 недель"),
                 ("ПРЕДОХРАНИТЕЛЬ", "двухпозиционный тумблер")]
        for i, (k, v) in enumerate(specs):
            p2 = c01((l - .15 - i * .13) / .45)
            if p2 <= 0: continue
            yy = int(300 + i * 72 + (1 - eout(p2)) * 18)
            d.rectangle([40, yy, 980, yy + 60], fill=(11, 15, 22, 242), outline=a(LINE, 255))
            d.rectangle([40, yy, 45, yy + 60], fill=a(ACC2, 255))
            d.text((68, yy + 8), k, font=F(RUSSO, 16), fill=a(ACC2, 245))
            d.text((68, yy + 32), v, font=F(MONO, 16), fill=a(TXT, 255 * eout(p2)))

        # индикатор автономности
        d.rectangle([1050, 300, 1880, 900], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((1076, 322), "АВТОНОМНОСТЬ ВО ВКЛЮЧЁННОМ СОСТОЯНИИ", font=F(MONO, 15), fill=a(DIM, 235))
        pp = eout(c01((l - .3) / 1.6))
        d.text((1076, 360), f"{int(8 * pp)}", font=F(RUSSO, 130), fill=a(ACC, 255))
        d.text((1300, 448), "недель", font=F(MONO, 28), fill=a(DIM, 240))
        # календарная сетка 8 недель x 7 дней
        for wk in range(8):
            for dd in range(7):
                on = (wk * 7 + dd) < int(56 * pp)
                x = 1080 + dd * 44
                y = 556 + wk * 36
                d.rectangle([x, y, x + 34, y + 30],
                            fill=a(ACC, 230) if on else a((16, 22, 30), 255),
                            outline=a((28, 40, 54), 255))
        d.text((1076, 862), "56 дней в готовности без подзарядки", font=F(MONO, 17), fill=a(TXT, 240))

        photo_panel(ov, d, "holster", 40, 792, 460, 140, t, 1.03, label="ПРЕДОХРАНИТЕЛЬ")
        photo_panel(ov, d, "pouch4", 520, 792, 470, 140, t, 1.03, label="КОРПУС")

    elif l < 18.1:
        # предохранитель и безопасность
        kicker(d, 40, 112, "БЕЗОПАСНОСТЬ", WARN)
        d.text((40, 156), "ДВУХПОЗИЦИОННЫЙ ТУМБЛЕР", font=fit("ДВУХПОЗИЦИОННЫЙ ТУМБЛЕР", RUSSO, 40, 1200),
               fill=a(TXT, 255))
        d.text((40, 216), "электронный запал не сработает без взведения", font=F(MONO, 19), fill=a(DIM, 240))

        # тумблер
        cx, cy = 300, 470
        pp = eout(c01((l - .3) / .8))
        # подписи позиций
        d.text((cx - 108, cy + 104), "ЗАЩЁЛКА", font=F(MONO, 16), fill=a(WARN, 240), anchor="ma")
        d.text((cx + 108, cy + 104), "ВЗВЕДЕНО", font=F(MONO, 16), fill=a(ACC, 240), anchor="ma")
        d.text((cx, cy - 116), "ДВЕ ПОЗИЦИИ ТУМБЛЕРА", font=F(MONO, 15), fill=a(DIM, 230), anchor="ma")

        d.rounded_rectangle([cx - 185, cy - 62, cx + 185, cy + 62], 34, fill=(12, 17, 24, 252),
                            outline=a(LINE, 255), width=2)
        knob_x = (cx - 108) + int(216 * pp)
        d.rounded_rectangle([knob_x - 54, cy - 48, knob_x + 54, cy + 48], 26,
                            fill=(32, 40, 50, 255), outline=a(WARN, 225), width=3)
        d.rectangle([knob_x - 22, cy - 20, knob_x + 22, cy + 20], fill=a((18, 23, 30), 255))
        d.ellipse([knob_x - 8, cy - 8, knob_x + 8, cy + 8], fill=a(WARN, 200))

        rules = [("ЗАЩЁЛКА", "запал заблокирован, выстрела нет", WARN),
                 ("ВЗВЕДЕНО", "цепь замкнута, готов к работе", ACC)]
        for i, (k, v, col) in enumerate(rules):
            p2 = c01((l - .5 - i * .2) / .5)
            if p2 <= 0: continue
            yy = int(620 + i * 122 + (1 - eout(p2)) * 20)
            d.rectangle([40, yy, 780, yy + 102], fill=(11, 15, 22, 244), outline=a(col, 130))
            d.rectangle([40, yy, 45, yy + 102], fill=a(col, 255))
            d.text((68, yy + 18), k, font=F(RUSSO, 21), fill=a(col, 250))
            d.text((68, yy + 54), v, font=F(MONO, 15), fill=a(TXT, 240))

        photo_panel(ov, d, "pouch3", 840, 278, 500, 372, t, 1.04, label="ЧЕХЛЫ В РАБОТЕ", idx="08")
        photo_panel(ov, d, "full", 1366, 278, 514, 372, t, 1.04, label="ПОЛНЫЙ КОМПЛЕКТ", idx="09")

        d.rectangle([840, 752, 1880, 920], fill=(9, 13, 19, 248), outline=a(LINE, 255))
        d.text((866, 772), "ХРАНЕНИЕ", font=F(MONO, 15), fill=a(DIM, 235))
        d.text((866, 798), "подсумок с быстрым доступом", font=F(RUSSO, 26), fill=a(TXT, 255))
        d.text((866, 844), "клапан на фастексе, стропа MOLLE", font=F(MONO, 16), fill=a(ACC, 235))
        d.text((866, 874), "не мешает при передвижении", font=F(MONO, 16), fill=a(DIM, 230))

    elif l < 23.5:
        # выбор камуфляжа
        kicker(d, 40, 112, "ИСПОЛНЕНИЕ", ACC)
        d.text((40, 152), "ЧЁРНЫЙ ИЛИ ХАКИ", font=fit("ЧЁРНЫЙ ИЛИ ХАКИ", RUSSO, 46, 1000), fill=a(TXT, 255))
        d.text((40, 214), "корпус — чёрный полимер, подсумки под цвет снаряжения", font=F(MONO, 18), fill=a(DIM, 240))

        cols = [("pouch_mc", "MULTICAM", "универсальный"), ("pouch_emr", "РУССКИЙ ЦИФРОВОЙ", "лес / поле"),
                ("pouch4", "OLIVE / ХАКИ", "базовый")]
        for i, (nm, tt, sub) in enumerate(cols):
            pp = c01((l - .2 - i * .2) / .55)
            if pp <= 0: continue
            x = 40 + i * 614
            y = int(290 + (1 - eout(pp)) * 34)
            d.rectangle([x, y, x + 586, y + 540], fill=(7, 11, 17, 246), outline=a(LINE, 255))
            ov.paste(photo_tile(nm, 570, 420, 1.02 + .03 * math.sin(t * .6 + i)), (x + 8, y + 8))
            brackets(d, x, y, 586, 540, a(ACC, 175))
            d.rectangle([x, y + 436, x + 586, y + 532], fill=(9, 12, 18, 250))
            d.text((x + 20, y + 450), tt, font=F(RUSSO, 21), fill=a(TXT, 255))
            d.text((x + 20, y + 486), sub, font=F(MONO, 15), fill=a(ACC, 235))

        d.rectangle([40, 860, 1880, 950], fill=(10, 15, 22, 246), outline=a(ACC, 120))
        d.text((66, 880), "ВЛОЖЕНИЕ В СНАРЯЖЕНИЕ: MOLLE-СТРОПА + ФАСТЕКС", font=F(MONO, 18), fill=a(TXT, 245))
        d.text((66, 912), "подсумок открывается одной рукой", font=F(MONO, 15), fill=a(DIM, 230))

    else:
        # крупный план механики
        kicker(d, 40, 112, "МЕХАНИКА", ACC2)
        d.text((40, 152), "БЫСТРОСЪЁМНЫЙ УЗЕЛ", font=fit("БЫСТРОСЪЁМНЫЙ УЗЕЛ", RUSSO, 44, 1100), fill=a(TXT, 255))
        photo_panel(ov, d, "stack", 40, 240, 760, 440, t, 1.05, label="БЛОК СНАРЯДОВ И УЗЕЛ СТЫКОВКИ", idx="10")
        photo_panel(ov, d, "set6b", 826, 240, 514, 440, t, 1.05, label="КОМПЛЕКТ 6")
        photo_panel(ov, d, "pouch", 1366, 240, 514, 440, t, 1.05, label="ПОДСУМОК")

        d.rectangle([40, 720, 1880, 940], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        facts = [("УЗЕЛ СТЫКОВКИ", "металлический, быстрый"), ("СНАРЯД", "одноразовый, с сетью"),
                 ("ПЕРЕЗАРЯДКА", "от 2 секунд"), ("ИНСТРУМЕНТ", "не нужен")]
        for i, (k, v) in enumerate(facts):
            x = 76 + i * 452
            d.text((x, 748), k, font=F(MONO, 15), fill=a(DIM, 235))
            d.text((x, 778), v, font=F(RUSSO, 24), fill=a(ACC, 255))
            d.rectangle([x, 878, x + 400, 882], fill=a(ACC, 80))


# ═════════════ сцена 4: условия, финал ═════════════
def scene4(base, ov, d, t, l):
    if l < 5.4:
        # IP54 + мороз
        kicker(d, 40, 112, "УСЛОВИЯ ЭКСПЛУАТАЦИИ", ACC2)
        d.text((40, 156), "IP54  /  −40 °C", font=fit("IP54  /  −40 °C", RUSSO, 54, 1000), fill=a(TXT, 255))
        d.text((40, 232), "брызги со всех сторон и мороз без отказа электроники", font=F(MONO, 19), fill=a(DIM, 240))

        d.rectangle([40, 340, 900, 530], fill=(10, 15, 22, 246), outline=a(ACC2, 130))
        d.text((66, 362), "IP54", font=F(RUSSO, 54), fill=a(ACC2, 255))
        d.text((66, 432), "защита от брызг со всех сторон", font=F(MONO, 18), fill=a(TXT, 240))
        d.text((66, 466), "пыль и водяные струи под углом", font=F(MONO, 15), fill=a(DIM, 230))

        d.rectangle([920, 340, 1880, 530], fill=(10, 15, 22, 246), outline=a(ACC2, 130))
        d.text((946, 362), "−40 °C", font=F(RUSSO, 54), fill=a(ACC2, 255))
        d.text((946, 432), "морозостойкость изделия", font=F(MONO, 18), fill=a(TXT, 240))
        d.text((946, 466), "работа в зимних условиях", font=F(MONO, 15), fill=a(DIM, 230))

        # температурная шкала
        gx, gy, gw = 40, 600, 1840
        d.rectangle([gx, gy, gx + gw, gy + 90], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(6):
            xx = gx + 30 + i * (gw - 60) / 5
            val = -40 + i * 15
            d.line([(xx, gy + 46), (xx, gy + 90)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 96), f"{val}", font=F(MONO, 15), fill=a(DIM, 230), anchor="ma")
        pp = eout(c01((l - .3) / 1.3))
        d.rectangle([gx + 30, gy + 28, gx + 30 + int((gw - 60) * pp), gy + 46], fill=a(ACC, 205))

        photo_panel(ov, d, "pouch_emr", 40, 730, 620, 200, t, 1.03, label="В РУССКОМ КАМУФЛЯЖЕ")
        photo_panel(ov, d, "pouch3", 686, 730, 620, 200, t, 1.03, label="ТРИ ВАРИАНТА ЧЕХЛОВ")
        photo_panel(ov, d, "full", 1332, 730, 548, 200, t, 1.03, label="ПОЛНЫЙ КОМПЛЕКТ")

    elif l < 10.8:
        # декларация и поставка
        kicker(d, 40, 112, "ДОКУМЕНТЫ И ПОСТАВКА", ACC)
        d.text((40, 152), "ДЕКЛАРАЦИЯ О СООТВЕТСТВИИ", font=fit("ДЕКЛАРАЦИЯ О СООТВЕТСТВИИ", RUSSO, 40, 1200),
               fill=a(TXT, 255))
        d.text((40, 210), "на изделие имеется декларация о соответствии", font=F(MONO, 19), fill=a(DIM, 240))

        d.rectangle([40, 280, 900, 500], fill=(9, 15, 20, 248), outline=a(ACC, 140))
        d.text((66, 306), "ДОКУМЕНТ", font=F(MONO, 15), fill=a(DIM, 235))
        d.text((66, 336), "ДЕКЛАРАЦИЯ", font=F(RUSSO, 44), fill=a(ACC, 255))
        d.text((66, 392), "О СООТВЕТСТВИИ", font=F(RUSSO, 44), fill=a(ACC, 255))
        d.text((66, 456), "предъявляется по запросу", font=F(MONO, 16), fill=a(TXT, 235))

        opts = [("4", "снаряда"), ("6", "снарядов"), ("10", "снарядов")]
        d.rectangle([940, 280, 1880, 500], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        d.text((966, 302), "ВАРИАТИВНОСТЬ ПОСТАВКИ", font=F(MONO, 15), fill=a(DIM, 235))
        for i, (n, dsc) in enumerate(opts):
            x = 966 + i * 300
            d.text((x, 336), n, font=F(RUSSO, 76), fill=a(ACC, 255))
            d.text((x, 432), dsc, font=F(MONO, 17), fill=a(TXT, 240))

        d.rectangle([40, 530, 1880, 700], fill=(9, 13, 19, 246), outline=a(WARN, 110))
        d.text((66, 552), "СМЕННЫЙ СНАРЯД — ОДНОРАЗОВЫЙ", font=F(RUSSO, 26), fill=a(WARN, 250))
        d.text((66, 594), "сеть и пиропатрон в одном картридже; корпус пистолета переиспользуется",
               font=F(MONO, 17), fill=a(TXT, 240))
        d.text((66, 632), "поставляется отдельно как расходный элемент", font=F(MONO, 16), fill=a(DIM, 230))

        photo_panel(ov, d, "set6b", 40, 700, 470, 240, t, 1.03, label="6 СНАРЯДОВ")
        photo_panel(ov, d, "stack", 550, 700, 470, 240, t, 1.03, label="БЛОК СНАРЯДОВ")
        photo_panel(ov, d, "pouch4", 1060, 700, 250, 240, t, 1.05, label="КАРТРИДЖ")
        photo_panel(ov, d, "pouch", 1350, 700, 250, 240, t, 1.05, label="ПОДСУМОК")
        photo_panel(ov, d, "holster2", 1640, 700, 240, 240, t, 1.05, label="В СБОРЕ")

    elif l < 16.2:
        # сценарии
        kicker(d, 40, 112, "СЦЕНАРИИ", ACC2)
        d.text((40, 152), "БЛИЖНЯЯ ЗОНА", font=fit("БЛИЖНЯЯ ЗОНА", RUSSO, 48, 900), fill=a(TXT, 255))
        d.text((40, 216), "там, где дрон уже над головой и поздно бежать", font=F(MONO, 19), fill=a(DIM, 240))

        cards = [("ПОЗИЦИЯ", "окоп, блиндаж, наблюдательный пост", "pouch4"),
                 ("ПАТРУЛЬ", "движение в колонне и пешем порядке", "pouch_mc"),
                 ("ОБЪЕКТ", "охрана склада, узла связи, КПП", "full")]
        for i, (tt, sub, nm) in enumerate(cards):
            pp = c01((l - .2 - i * .22) / .55)
            if pp <= 0: continue
            x = 40 + i * 614
            y = int(290 + (1 - eout(pp)) * 34)
            d.rectangle([x, y, x + 586, y + 540], fill=(7, 11, 17, 246), outline=a(LINE, 255))
            ov.paste(photo_tile(nm, 570, 420, 1.02 + .03 * math.sin(t * .6 + i)), (x + 8, y + 8))
            brackets(d, x, y, 586, 540, a(ACC, 175))
            d.rectangle([x, y + 436, x + 586, y + 532], fill=(9, 12, 18, 250))
            d.text((x + 20, y + 450), tt, font=F(RUSSO, 22), fill=a(TXT, 255))
            d.text((x + 20, y + 486), sub, font=F(MONO, 14), fill=a(ACC, 235))

        d.text((40, 880), "РЕНТАБЕЛЬНОСТЬ: КОРПУС МНОГОРАЗОВЫЙ, СНАРЯД — РАСХОДНИК",
               font=F(MONO, 17), fill=a(DIM, 215))

    elif l < 21.6:
        # чек-лист
        kicker(d, 40, 112, "ЧЕК-ЛИСТ ПЕРЕД ПОКУПКОЙ", ACC)
        d.text((40, 152), "ЧТО УТОЧНИТЬ", font=fit("ЧТО УТОЧНИТЬ", RUSSO, 46, 900), fill=a(TXT, 255))
        items = [("ВАРИАНТ ПОСТАВКИ", "4, 6 или 10 снарядов в комплекте"),
                 ("ЦВЕТ", "чёрный или хаки"),
                 ("КАМУФЛЯЖ ЧЕХЛА", "multicam / русский цифровой / olive"),
                 ("ДЕКЛАРАЦИЯ", "запросить документ на партию"),
                 ("ЗАПАС СНАРЯДОВ", "сменный картридж поставляется отдельно")]
        for i, (k, v) in enumerate(items):
            pp = c01((l - .15 - i * .14) / .45)
            if pp <= 0: continue
            yy = int(240 + i * 130 + (1 - eout(pp)) * 22)
            d.rectangle([40, yy, 1180, yy + 112], fill=(11, 15, 22, 244), outline=a(LINE, 255))
            d.rectangle([40, yy, 45, yy + 112], fill=a(ACC, 255))
            d.text((72, yy + 18), f"0{i+1}", font=F(MONO, 15), fill=a(ACC, 200))
            d.text((120, yy + 20), k, font=F(RUSSO, 21), fill=a(TXT, 255 * eout(pp)))
            d.text((120, yy + 58), v, font=F(MONO, 16), fill=a(DIM, 240))

        photo_panel(ov, d, "holster", 1240, 240, 640, 480, t, 1.04, label="ПАУК 30Б", idx="11")
        d.rectangle([1240, 790, 1880, 900], fill=(9, 13, 19, 246), outline=a(WARN, 120))
        d.text((1264, 812), "БЕЗ ЦЕН", font=F(RUSSO, 26), fill=a(WARN, 250))
        d.text((1264, 856), "только характеристики и факты", font=F(MONO, 15), fill=a(DIM, 230))

    else:
        # финал
        p = eout(c01((l - .15) / .9))
        d.rectangle([0, 200, W, 900], fill=(5, 8, 13, 228))
        d.rectangle([0, 200, 8, 900], fill=a(ACC, 255))
        d.text((100, 248 + (1 - p) * 20), "ПАУК 30Б", font=F(RUSSO, 104), fill=a(TXT, 255 * p))
        d.text((104, 380), "ПЕРЕХВАТ БПЛА СЕТЬЮ", font=F(RUSSO, 34), fill=a(ACC, 255 * p))
        d.line([(104, 456), (104 + 1100 * p, 456)], fill=a(ACC, 180), width=2)

        p2 = c01((l - .6) / .8)
        d.text((104, 496), "ПОДПИСЫВАЙТЕСЬ НА «В ОКОПЕ»", font=F(MONO, 22), fill=a(DIM, 255 * p2))
        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - .9 - i * .22) / .5)
            if pp <= 0: continue
            yy = int(552 + i * 96 + (1 - eout(pp)) * 18)
            d.rectangle([104, yy, 1240, yy + 78], fill=(11, 16, 23, 246), outline=a(ACC, 110))
            d.rectangle([104, yy, 110, yy + 78], fill=a(ACC, 255))
            d.text((134, yy + 14), k, font=F(RUSSO, 20), fill=a(ACC, 255))
            d.text((134, yy + 44), v, font=F(MONO, 17), fill=a(TXT, 240))

        photo_panel(ov, d, "holster2", 1330, 250, 520, 520, t, 1.04, label="ПАУК 30Б / В ЧЕХЛЕ")

        d.text((104, 850), "ТЕХНИЧЕСКИЙ ОБЗОР  //  ФАКТЫ ИЗ ПАСПОРТА  //  БЕЗ РЕКЛАМНЫХ ЦЕН",
               font=F(MONO, 15), fill=a(DIM, 200))


def intro(base, ov, d, t, l):
    p = eout(c01(t / .9))
    d.rectangle([0, H // 2 - 150, W, H // 2 + 120], fill=(5, 8, 13, int(200 * p)))
    d.text((W // 2, H // 2 - 92), "«В ОКОПЕ»", font=F(RUSSO, 96), fill=a(TXT, int(255 * c01(t / .7))), anchor="ma")
    d.text((W // 2, H // 2 + 20), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 22),
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
            name = "set4" if l < 6.0 else ("set6" if l < 12.0 else ("holster2" if l < 17.4 else ("pouch3" if l < 22.9 else "full")))
        elif idx == 1:
            name = "stack" if l < 5.6 else ("holster2" if l < 11.2 else ("set6b" if l < 17.2 else ("stack" if l < 22.9 else ("pouch3" if l < 27.6 else "set4"))))
        elif idx == 2:
            name = "pouch2" if l < 6.0 else ("holster" if l < 12.0 else ("pouch3" if l < 18.1 else ("pouch_mc" if l < 23.5 else "stack")))
        else:
            name = "pouch_emr" if l < 5.4 else ("pouch4" if l < 10.8 else ("pouch_mc" if l < 16.2 else ("holster" if l < 21.6 else "holster2")))

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
