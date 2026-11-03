# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // ДРОНЫ В НАЛИЧИИ — вертикальный Reels 9:16, динамика + эффекты."""
import os, math, json, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/drones_lineup"
ASSETS = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

BOUNDS = [0.00, 4.20, 10.60, 17.40, 23.60, 30.20, 34.60, 40.60]
TOTAL = BOUNDS[-1]
BPM = 122.4
BEAT = 60.0 / BPM

BG = (5, 7, 11)
ACC = (0, 229, 160)
ACC2 = (46, 140, 255)
AMB = (255, 176, 32)
HOT = (255, 74, 42)
TXT = (242, 246, 255)
DIM = (140, 162, 186)
LINE = (30, 46, 66)
RED = (255, 60, 60)

RUSSO, DAYS, MONO = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf", "JetBrainsMono-VF.ttf")


def F(n, s):
    return ImageFont.truetype(os.path.join(FD, n), s)


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def c01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def eout(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def ein(x):
    x = c01(x)
    return x * x * x


def eback(x):
    x = c01(x)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def eio(x):
    x = c01(x)
    return x * x * (3 - 2 * x)


def a(col, al):
    return (col[0], col[1], col[2], int(clamp(al, 0, 255)))


def tw(d, s, f):
    return d.textlength(s, font=f)


# ─────────────────────────── ФОТО ───────────────────────────
_MASTER = {}


def master(name, maxdim=2600):
    if name in _MASTER:
        return _MASTER[name]
    im = Image.open(os.path.join(ASSETS, name + ".jpg")).convert("RGB")
    s = maxdim / max(im.size)
    if s < 1:
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    _MASTER[name] = im
    return im


def photo(name, w, h, zoom=1.0, ox=0.0, oy=0.0):
    """Кадр cover-заполнения w×h: zoom≥1 приближает, ox/oy ∈ [-1,1] — сдвиг."""
    m = master(name)
    cs = max(w / m.width, h / m.height)
    sc = cs * zoom
    rw, rh = w / sc, h / sc
    rw = min(rw, m.width)
    rh = min(rh, m.height)
    cx = m.width / 2 + clamp(ox, -1, 1) * max(0, (m.width - rw) / 2)
    cy = m.height / 2 + clamp(oy, -1, 1) * max(0, (m.height - rh) / 2)
    x0 = int(clamp(cx - rw / 2, 0, m.width - rw))
    y0 = int(clamp(cy - rh / 2, 0, m.height - rh))
    return m.crop((x0, y0, x0 + int(rw), y0 + int(rh))).resize((w, h), Image.LANCZOS)


def grade(im, dark=0.62, contrast=1.10, tint=ACC, tinta=0.05, sat=1.0, gamma=1.0):
    arr = np.asarray(im).astype(np.float32)
    arr = (arr - 128.0) * contrast + 128.0
    if sat != 1.0:
        g = arr.mean(2, keepdims=True)
        arr = g + (arr - g) * sat
    if gamma != 1.0:
        arr = 255.0 * np.power(np.clip(arr, 0, 255) / 255.0, gamma)
    arr *= dark
    arr = arr * (1 - tinta) + np.array(tint, np.float32) * tinta
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


INFERNO = [
    (0, 0, 4), (22, 11, 57), (66, 10, 104), (106, 23, 110), (147, 38, 103),
    (188, 55, 84), (221, 81, 58), (243, 120, 25), (252, 165, 10), (246, 215, 70),
    (252, 255, 164)]


def thermalize(im, dark=0.95):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255.0
    g = np.clip((g - 0.12) * 1.35, 0, 1)
    n = len(INFERNO) - 1
    idx = g * n
    i0 = np.floor(idx).astype(np.int32)
    i1 = np.clip(i0 + 1, 0, n)
    f = (idx - i0)[..., None]
    lut = np.array(INFERNO, np.float32)
    arr = lut[i0] * (1 - f) + lut[i1] * f
    arr *= dark
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def blur_photo(name, w=W // 4, h=H // 4, dark=0.35):
    return grade(photo(name, w, h, 1.06), dark=dark, contrast=1.0).filter(
        ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)


# ─────────────────────────── ОВЕРЛЕИ ───────────────────────────
SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 24))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_vd = ImageDraw.Draw(VIGN)
for i in range(120):
    k = i / 120.0
    ins = int(-190 + k * 430)
    _vd.ellipse([ins, ins * 1.08, W - ins, H - ins * 1.08], outline=(0, 0, 0, int(3 + k * 2)), width=5)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(28))

_rng = np.random.default_rng(11)
GRAIN = []
for _ in range(5):
    n = _rng.integers(0, 34, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 20))))


def brackets(d, x, y, w, h, col=(0, 229, 160, 190), ln=26, wd=3):
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        d.line([(cx, cy), (cx + sx * ln, cy)], fill=col, width=wd)
        d.line([(cx, cy), (cx, cy + sy * ln)], fill=col, width=wd)


def chip(d, x, y, s, col=ACC, size=24, bg=(8, 26, 22), padx=18, h=44, alpha=255):
    f = F(MONO, size)
    w = tw(d, s, f)
    d.rectangle([x, y, x + w + padx * 2, y + h], fill=a(bg, int(alpha * .92)), outline=a(col, int(alpha * .75)))
    d.text((x + padx, y + (h - size) / 2 - 3), s, font=f, fill=a(col, alpha))
    return w + padx * 2


def ticks(d, x, y, n, step=26, col=(46, 72, 100, 150), up=True, wd=2, h=10):
    for i in range(n):
        d.line([(x + i * step, y), (x + i * step, y - h if up else y + h)], fill=col, width=wd)


def text_layer(s, fn, size, col, track=0):
    f = F(fn, size)
    w = int(f.getlength(s)) + 20 + track * max(0, len(s) - 1)
    lay = Image.new("RGBA", (max(2, w), int(size * 1.55)), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    x = 10
    for ch in s:
        dl.text((x, 6), ch, font=f, fill=col)
        x += f.getlength(ch) + track
    return lay


def slam(cv, s, fn, size, x, y, col, p, dx=0.0, dy=0.0, trail=34, anchor="lt",
         chroma=True, track=0):
    """Кинетический вход текста: масштаб-овершут + след движения + хроматика."""
    if p <= 0:
        return
    lay = text_layer(s, fn, size, col, track)
    k = 1.0 + 0.45 * (1 - eback(p))
    lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))), Image.BILINEAR)
    al = eout(min(1.0, p * 1.8))
    if al < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    if anchor == "ma":
        px, py = int(x - lay.width / 2), int(y)
    elif anchor == "mm":
        px, py = int(x - lay.width / 2), int(y - lay.height / 2)
    else:
        px, py = int(x), int(y)
    if chroma and p < 0.55:
        ca = int(70 * (1 - p / 0.55))
        for off, c in ((-4, (255, 60, 90)), (4, (60, 210, 255))):
            t = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            t.paste(Image.new("RGBA", lay.size, a(c, ca)), (0, 0), lay)
            cv.alpha_composite(t, (px + off, py))
    if trail:
        steps = 5
        for i in range(steps, 0, -1):
            k2 = (1 - eout(p))
            ox = int(-dx * trail * i / steps * k2)
            oy = int(-dy * trail * i / steps * k2)
            if ox == 0 and oy == 0:
                continue
            t = lay.copy()
            t.putalpha(t.getchannel("A").point(lambda v: int(v * (0.16 * (steps - i + 1) / steps * k2))))
            cv.alpha_composite(t, (px + ox, py + oy))
    cv.alpha_composite(lay, (px, py))


def sweep(cv, t, col=(255, 255, 255), alpha=110, speed=1.0, width=180, angle=-24):
    """Диагональный световой блик, проходящий по кадру."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = int(((t * speed) % 1.6 - 0.3) * W * 1.4)
    for i in range(width):
        k = 1 - abs(i - width / 2) / (width / 2)
        xx = cx + i
        d.line([(xx - angle * 8, 0), (xx + angle * 8, H)], fill=a(col, alpha * k * k * 0.12))
    lay = lay.filter(ImageFilter.GaussianBlur(12))
    cv.alpha_composite(lay)


def radar(cv, cx, cy, r, t, col=ACC, alpha=120, blips=5, rings=3):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(rings):
        rr = r * (0.34 + 0.22 * i)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=a(col, alpha * 0.35), width=2)
    ang = (t * 1.5) % (2 * math.pi)
    pts = []
    for i in range(28):
        aa = ang - i * 0.055
        pts.append((cx + r * math.cos(aa), cy + r * math.sin(aa)))
    pts = [(cx, cy)] + pts
    d.polygon(pts, fill=a(col, int(alpha * 0.25)))
    d.line([(cx, cy), (cx + r * math.cos(ang), cy + r * math.sin(ang))], fill=a(col, alpha + 60), width=3)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=a(col, alpha * 0.55), width=2)
    for i in range(blips):
        aa = i * 2.4 + 0.6
        rr = r * (0.35 + 0.17 * ((i * 37) % 4))
        bx, by = cx + rr * math.cos(aa), cy + rr * math.sin(aa)
        ph = (t * 1.1 + i * 0.27) % 1.0
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=a(col, int(150 * (1 - ph))))
    cv.alpha_composite(lay)


def speedlines(cv, t, n=14, alpha=70, col=(210, 235, 255)):
    d = ImageDraw.Draw(cv)
    rnd = random.Random(int(t * 30))
    for i in range(n):
        y0 = rnd.randint(-200, H)
        ln = rnd.randint(120, 460)
        sp = rnd.uniform(2200, 4200)
        x = int((rnd.randint(0, W) + t * sp) % (W + 700)) - 350
        d.line([(x, y0), (x + ln * 0.35, y0 - ln)], fill=a(col, alpha), width=rnd.choice([1, 2, 2, 3]))


def hud_top(d, t):
    d.rectangle([0, 0, W, 126], fill=(6, 9, 14, 236))
    d.rectangle([0, 0, W, 4], fill=a(ACC, 255))
    d.text((40, 26), "«В ОКОПЕ»", font=F(RUSSO, 38), fill=a(TXT, 255))
    d.text((40, 80), "ДРОНЫ  //  НАЛИЧИЕ", font=F(MONO, 24), fill=a(DIM, 235))
    p = clamp(t / TOTAL, 0, 1)
    d.text((W - 44, 28), f"{int(t*30):04d}", font=F(MONO, 24), fill=a(DIM, 200), anchor="ra")
    blink = 0.5 + 0.5 * math.sin(t * 6.0)
    d.ellipse([W - 66, 66, W - 44, 88], fill=a(RED, int(120 + 120 * blink)))
    d.rectangle([0, 126, W, 131], fill=(14, 20, 30, 250))
    d.rectangle([0, 126, int(W * p), 131], fill=a(ACC, 245))


def hud_bottom(d):
    d.rectangle([0, H - 132, W, H], fill=(5, 8, 13, 250))
    d.rectangle([0, H - 134, W, H - 131], fill=a(ACC, 90))
    d.text((W // 2, H - 100), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 26),
           fill=a(ACC, 240), anchor="ma")
    d.text((W // 2, H - 58), "ДРОНЫ В НАЛИЧИИ", font=F(RUSSO, 21), fill=a(DIM, 220), anchor="ma")


# ─────────────────────────── СЦЕНА 1: ХУК ───────────────────────────
def s_hook(cv, ui, d, t, l):
    ph = photo("hero", W, H, zoom=1.02 + 0.10 * eio(l / 4.2), ox=0.10 - 0.22 * eio(l / 4.2), oy=0.02)
    cv.alpha_composite(grade(ph, dark=0.62, contrast=1.14, sat=0.85, tint=ACC, tinta=0.07).convert("RGBA"))

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(H):
        k = y / H
        dd.line([(0, y), (W, y)], fill=(3, 6, 10, int(20 + 160 * clamp((k - 0.25) / 0.75, 0, 1) ** 1.7)))
    ui.alpha_composite(ov)
    radar(ui, 540, 1150, 470, t, ACC, 110)

    speedlines(ui, t, 16, 55)
    slam(ui, "ДРОНЫ", RUSSO, 208, 540, 470, a(TXT, 255), c01((l - 0.06) / 0.42), dx=1.0, trail=46, anchor="ma")
    slam(ui, "В НАЛИЧИИ", DAYS, 124, 540, 700, a(AMB, 255), c01((l - 0.42) / 0.40), dx=1.0, trail=30, anchor="ma")
    w = 760 * eout(c01((l - 0.62) / 0.5))
    if w > 2:
        d.rectangle([540 - w / 2, 866, 540 + w / 2, 872], fill=a(ACC, 230))
    chip(d, 72, 168, "СКЛАД  //  ПРЯМО СЕЙЧАС", ACC, 26, alpha=int(255 * c01((l - 0.2) / 0.3)))
    chip(d, 72, 224, "ПЯТЬ МОДЕЛЕЙ", AMB, 26, bg=(30, 20, 6), alpha=int(255 * c01((l - 0.9) / 0.3)))

    # счётчики
    p = eout(c01((l - 1.5) / 0.7))
    if p > 0:
        d.text((72, 1440), f"{int(round(5 * p))}", font=F(RUSSO, 132), fill=a(TXT, 255))
        d.text((86, 1590), "МОДЕЛЕЙ", font=F(MONO, 26), fill=a(DIM, 240))
        d.text((560, 1440), f"{int(round(11 * p))}", font=F(RUSSO, 132), fill=a(AMB, 255))
        d.text((574, 1590), "КОНФИГУРАЦИЙ", font=F(MONO, 26), fill=a(DIM, 240))
        brackets(d, 60, 1420, 960, 240, a(ACC, int(120 * p)), 22, 2)
    sweep(ui, l * 0.55, alpha=120)


# ─────────────────────────── СЦЕНА 2: ЛИНЕЙКА ───────────────────────────
MODELS = [
    ("01", "3 КЛАССИК", ["КОМПЛЕКТ", "ТУШКА"]),
    ("02", "3 ПРО", ["КОМБО", "КОМПЛЕКТ", "ТУШКА"]),
    ("03", "3Т", ["КОМПЛЕКТ", "ТУШКА"]),
    ("04", "4 ПРО", ["КОМПЛЕКТ", "ТУШКА"]),
    ("05", "4Т", ["КОМПЛЕКТ", "ТУШКА"]),
]


def s_lineup(cv, ui, d, t, l):
    # полный кадр: строй дронов на закате
    ph = photo("formation", W, H, zoom=1.10 + 0.06 * eio(l / 6.4), ox=-0.18 + 0.36 * eio(l / 6.4), oy=-0.25)
    cv.alpha_composite(grade(ph, dark=0.46, contrast=1.14, sat=0.85, tint=ACC2, tinta=0.06).convert("RGBA"))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(H):
        k = y / H
        dd.line([(0, y), (W, y)], fill=(4, 7, 12, int(40 + 170 * clamp((k - 0.18) / 0.82, 0, 1) ** 1.4)))
    ui.alpha_composite(ov)

    chip(d, 64, 168, "ЛИНЕЙКА  //  5 МОДЕЛЕЙ", ACC, 26, alpha=int(255 * c01((l - 0.05) / 0.3)))
    slam(ui, "ВСЯ ЛИНЕЙКА", RUSSO, 100, 60, 236, a(TXT, 255), c01((l - 0.12) / 0.42), dx=1.0, trail=30)
    d.text((64, 356), "выбирай под задачу", font=F(MONO, 27), fill=a(DIM, int(235 * c01((l - 0.5) / 0.4))))

    y0 = 424
    for i, (num, name, chips) in enumerate(MODELS):
        st = 0.55 + i * 0.52
        p = c01((l - st) / 0.34)
        if p <= 0:
            continue
        yy = y0 + i * 250
        dx = int((1 - eback(p)) * 300)
        fresh = l < st + 0.75
        col = AMB if fresh else ACC
        # плашка строки
        d.rectangle([40 + dx, yy, W - 40 + dx, yy + 212], fill=(7, 11, 17, int(232 * eout(p))),
                    outline=a(col if fresh else LINE, int(210 * eout(p))))
        d.rectangle([40 + dx, yy, 48 + dx, yy + 212], fill=a(col, 255))
        # номер
        d.text((84 + dx, yy + 16), num, font=F(MONO, 30), fill=a(ACC, int(240 * eout(p))))
        # имя
        fname = F(RUSSO, 74)
        for g in (3, 2, 1):
            gx = int((1 - eout(p)) * 44 * g)
            d.text((84 + gx + dx, yy + 62), name, font=fname, fill=a(TXT, int(34 * (4 - g) * (1 - p))))
        d.text((84 + dx, yy + 62), name, font=fname, fill=a(TXT, int(255 * (0.4 + 0.6 * eout(p)))))
        # чипы конфигураций
        xx = 88 + dx
        for j, c in enumerate(chips):
            q = c01((p - 0.3 - j * 0.1) / 0.3)
            if q <= 0:
                continue
            cc = AMB if c == "КОМБО" else (ACC2 if c == "ТУШКА" else ACC)
            wch = chip(d, xx, yy + 140, c, cc, 20, bg=(10, 16, 22), h=36, alpha=int(235 * q))
            xx += wch + 10
        # тег наличия
        if p > 0.5:
            q = c01((p - 0.5) / 0.3)
            lt = "ЕСТЬ"
            fl = F(MONO, 22)
            wl = tw(d, lt, fl)
            d.rectangle([W - 74 - wl - 34 + dx, yy + 22, W - 74 + dx, yy + 62],
                        fill=a((8, 26, 22), int(220 * q)), outline=a(ACC, int(170 * q)))
            d.text((W - 74 - wl - 17 + dx, yy + 30), lt, font=fl, fill=a(ACC, int(245 * q)))
    if l > 4.3:
        pulse = 0.55 + 0.45 * math.sin((l - 4.3) * 7)
        d.text((60, 1730), "ЕСТЬ ВСЁ  //  БЕЗ ОЖИДАНИЯ", font=F(MONO, 25), fill=a(ACC, int(120 + 120 * pulse)))
    sweep(ui, l * 0.4, alpha=80)


# ─────────────────────────── СЦЕНА 3: КОМПЛЕКТАЦИИ ───────────────────────────
CONFIGS = [("01", "ТУШКА", "только аппарат", ACC2),
           ("02", "КОМПЛЕКТ", "готов к вылету", ACC),
           ("03", "КОМБО", "расширенный набор", AMB)]


def s_configs(cv, ui, d, t, l):
    ph = photo("kit", W, H, zoom=1.14 - 0.10 * eio(l / 6.8), ox=-0.06 + 0.12 * eio(l / 6.8))
    cv.alpha_composite(grade(ph, dark=0.44, contrast=1.1, sat=0.9, tint=AMB, tinta=0.05).convert("RGBA"))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(0, H, 4):
        dd.line([(0, y), (W, y)], fill=(0, 0, 0, 26))
    ui.alpha_composite(ov)

    chip(d, 64, 168, "ТРИ КОМПЛЕКТАЦИИ", AMB, 26, bg=(30, 20, 6), alpha=int(255 * c01((l - 0.05) / 0.3)))
    slam(ui, "КАК БЕРУТ", RUSSO, 100, 60, 236, a(TXT, 255), c01((l - 0.1) / 0.4), dx=1.0, trail=28)

    for i, (num, name, sub, col) in enumerate(CONFIGS):
        st = 0.55 + i * 0.62
        p = c01((l - st) / 0.36)
        if p <= 0:
            continue
        yy = 440 + i * 400
        dx = int((1 - eback(p)) * 260)
        d.rectangle([54 + dx, yy, W - 54 + dx, yy + 340], fill=(8, 12, 18, int(232 * eout(p))),
                    outline=a(col, int(190 * eout(p))))
        d.rectangle([54 + dx, yy, 62 + dx, yy + 340], fill=a(col, 255))
        d.text((96 + dx, yy + 26), num, font=F(MONO, 32), fill=a(col, 245))
        d.text((96 + dx, yy + 70), name, font=F(RUSSO, 88), fill=a(TXT, 255))
        d.text((100 + dx, yy + 190), sub, font=F(MONO, 34), fill=a(DIM, 240))
        # полоса-заполнение
        wp = 760 * eout(c01((l - st - 0.25) / 0.55))
        if wp > 4:
            d.rectangle([100 + dx, yy + 268, 100 + wp + dx, yy + 276], fill=a(col, 230))
        # вспышка на входе
        if p < 0.3:
            fl = Image.new("RGBA", (W, H), a(col, int(90 * (1 - p / 0.3))))
            cv.alpha_composite(fl)
    # бегущая строка моделей
    if l > 3.9:
        q = c01((l - 3.9) / 0.5)
        yy = 1690
        d.rectangle([0, yy - 20, W, yy + 62], fill=(6, 10, 16, int(220 * q)))
        txt = "3 КЛАССИК   ·   3 ПРО   ·   3Т   ·   4 ПРО   ·   4Т   ·   "
        f = F(MONO, 30)
        wtx = f.getlength(txt)
        off = (l * 160) % wtx
        x = -off
        while x < W:
            d.text((x, yy), txt, font=f, fill=a(ACC, int(235 * q)))
            x += wtx
    sweep(ui, l * 0.45, alpha=110, col=(255, 235, 200))


# ─────────────────────────── СЦЕНА 4: ТЕПЛОВИЗОР ───────────────────────────
def s_thermal(cv, ui, d, t, l):
    glitch_on = 2.85 < l < 3.35
    if glitch_on:
        ph = photo("night", W, H, zoom=1.05 + 0.05 * l, ox=0.0)
        cv.alpha_composite(grade(ph, dark=0.55, contrast=1.2, sat=0.7, tint=HOT, tinta=0.08).convert("RGBA"))
    else:
        ph = thermalize(photo("thermal", W, H, zoom=1.12 + 0.06 * eio(l / 6.2), ox=0.12 - 0.24 * eio(l / 6.2)))
        cv.alpha_composite(ph.convert("RGBA"))

    # сетка тепловизора
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for x in range(0, W, 90):
        dl.line([(x, 0), (x, H)], fill=(255, 255, 255, 12))
    for y in range(0, H, 90):
        dl.line([(0, y), (W, y)], fill=(255, 255, 255, 12))
    # бегущая строка сканирования
    sy = int((l * 340) % (H + 300)) - 150
    dl.line([(0, sy), (W, sy)], fill=(255, 255, 255, 90), width=3)
    dl.line([(0, sy + 8), (W, sy + 8)], fill=(255, 200, 120, 40), width=10)
    ui.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.6)))

    # прицел
    cx, cy = 700, 1080
    pulse = 0.6 + 0.4 * math.sin(l * 5)
    brackets(d, cx - 130, cy - 110, 260, 220, a(HOT, int(210 * pulse)), 34, 4)
    d.line([(cx - 210, cy), (cx - 150, cy)], fill=a(TXT, 210), width=2)
    d.line([(cx + 150, cy), (cx + 210, cy)], fill=a(TXT, 210), width=2)
    d.text((cx - 128, cy - 150), "ЦЕЛЬ", font=F(MONO, 24), fill=a(HOT, 240))

    chip(d, 64, 168, "КАНАЛ  //  ТЕПЛОВИЗОР", HOT, 26, bg=(30, 10, 8), alpha=int(255 * c01((l - 0.05) / 0.3)))
    slam(ui, "ИНДЕКС Т", RUSSO, 150, 60, 236, a(TXT, 255), c01((l - 0.12) / 0.42), dx=1.0, trail=38)
    slam(ui, "ТЕПЛОВИЗОР", DAYS, 92, 60, 404, a(HOT, 255), c01((l - 0.38) / 0.4), dx=1.0, trail=26)

    tags = [("НОЧЬ", 3.05), ("ДЫМ", 3.35), ("ТРАВА", 3.65)]
    for s, st in tags:
        q = c01((l - st) / 0.28)
        if q > 0:
            pass
    xx = 62
    for s, st in tags:
        q = c01((l - st) / 0.28)
        if q <= 0:
            continue
        wch = chip(d, xx, 1480, s, TXT, 28, bg=(26, 12, 10), h=52, alpha=int(240 * q))
        xx += wch + 14
    if l > 4.3:
        p = eout(c01((l - 4.3) / 0.5))
        d.text((62, 1570), "видно всё, что греет", font=F(MONO, 30), fill=a(DIM, int(240 * p)))
    sweep(ui, l * 0.6, alpha=70, col=(255, 190, 140))


# ─────────────────────────── СЦЕНА 5: СКЛАД ───────────────────────────
STOCK_SHOTS = [("hero", 0.0, 1.35), ("night", 1.35, 2.70), ("formation", 2.70, 4.05), ("kit", 4.05, 6.6)]


def s_stock(cv, ui, d, t, l):
    shot = STOCK_SHOTS[-1]
    for s in STOCK_SHOTS:
        if l < s[2]:
            shot = s
            break
    name, s0, s1 = shot
    u = clamp((l - s0) / max(0.01, s1 - s0), 0, 1)
    ph = photo(name, W, H, zoom=1.16 - 0.14 * eio(u), ox=-0.18 + 0.36 * eio(u))
    cv.alpha_composite(grade(ph, dark=0.5, contrast=1.16, sat=0.85, tint=ACC2, tinta=0.05).convert("RGBA"))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    for y in range(H):
        k = y / H
        dd.line([(0, y), (W, y)], fill=(4, 7, 12, int(60 + 140 * clamp((k - 0.3) / 0.7, 0, 1) ** 1.5)))
    ui.alpha_composite(ov)
    speedlines(ui, t, 10, 45)

    chip(d, 64, 168, "СКЛАД  //  ВСЁ СРАЗУ", ACC, 26, alpha=int(255 * c01((l - 0.06) / 0.3)))
    p = c01((l - 0.2) / 0.4)
    slam(ui, "В НАЛИЧИИ", RUSSO, 132, 540, 300, a(TXT, 255), p, dx=1.0, trail=40, anchor="ma")

    # 11 квадратов «в наличии»
    gx, gy, cw = 60, 1180, 84
    for i in range(11):
        q = c01((l - 0.55 - i * 0.11) / 0.22)
        if q <= 0:
            continue
        xx = gx + (i % 11) * 88
        col = ACC if i % 3 else AMB
        d.rectangle([xx, gy, xx + cw, gy + 26], fill=a(col, int(240 * q)))
    d.text((gx, gy + 40), "11 КОНФИГУРАЦИЙ  //  МОДЕЛИ 3, 3 ПРО, 3Т, 4 ПРО, 4Т", font=F(MONO, 22), fill=a(DIM, 235))

    # счётчики
    q = eout(c01((l - 1.0) / 0.8))
    if q > 0:
        d.text((60, 1300), f"{int(round(5*q))}", font=F(RUSSO, 150), fill=a(TXT, 255))
        d.text((60, 1470), "МОДЕЛЕЙ НА СКЛАДЕ", font=F(MONO, 26), fill=a(DIM, 238))
        d.text((560, 1300), f"{int(round(11*q))}", font=F(RUSSO, 150), fill=a(AMB, 255))
        d.text((560, 1470), "КОНФИГУРАЦИЙ", font=F(MONO, 26), fill=a(DIM, 238))
    radar(ui, 880, 700, 210, t, ACC, 70, 4, 2)
    sweep(ui, l * 0.7, alpha=120)


# ─────────────────────────── СЦЕНА 6: ПРИЗЫВ ───────────────────────────
def s_cta(cv, ui, d, t, l):
    ph = photo("kit", W, H, zoom=1.08 + 0.05 * eio(l / 4.4), ox=0.1)
    cv.alpha_composite(grade(ph, dark=0.34, contrast=1.12, sat=0.9, tint=ACC, tinta=0.06).convert("RGBA"))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    dd.rectangle([0, 380, W, 1300], fill=(4, 7, 11, 190))
    ui.alpha_composite(ov)

    chip(d, 64, 168, "НАЛИЧИЕ  //  СЕЙЧАС", ACC, 26, alpha=int(255 * c01((l - 0.05) / 0.3)))
    slam(ui, "ЗАБИРАЙ", RUSSO, 168, 540, 470, a(TXT, 255), c01((l - 0.1) / 0.4), dx=1.0, trail=44, anchor="ma")
    slam(ui, "СЕЙЧАС", RUSSO, 168, 540, 650, a(AMB, 255), c01((l - 0.4) / 0.4), dx=1.0, trail=44, anchor="ma")
    p = c01((l - 0.9) / 0.45)
    if p > 0:
        d.rectangle([140, 880, 940, 900], fill=a(ACC, int(230 * eout(p))))
        d.text((540, 936), "Пиши в «В Окопе» — подберём под задачу", font=F(MONO, 33),
               fill=a(TXT, int(245 * eout(p))), anchor="ma")
    for i in range(3):
        q = c01((l - 1.2 - i * 0.18) / 0.35)
        if q <= 0:
            continue
        x = 410 + i * 130
        d.line([(x, 1090), (x + 62, 1140), (x, 1190)], fill=a(ACC, int(235 * q)), width=9)
    blink = 0.55 + 0.45 * math.sin(l * 6)
    d.rectangle([60, 1560, W - 60, 1690], fill=(8, 34, 28, 250), outline=a(ACC, 200))
    d.text((540, 1602), "В НАЛИЧИИ  •  БЕЗ ОЖИДАНИЯ", font=F(RUSSO, 44), fill=a(ACC, int(200 + 55 * blink)), anchor="ma")
    sweep(ui, l * 0.9, alpha=150)


# ─────────────────────────── СЦЕНА 7: ЭНД-КАРД ───────────────────────────
def s_endcard(cv, ui, d, t, l):
    base = Image.new("RGBA", (W, H), a(BG, 255))
    cv.alpha_composite(base)
    ph = photo("hero", W, H, zoom=1.2, ox=0.15, oy=0.1)
    cv.alpha_composite(grade(ph, dark=0.22, contrast=1.0, sat=0.4).convert("RGBA"))
    radar(ui, 540, 700, 520, t, ACC, 45, 6, 3)

    p0 = eout(c01((l - 0.02) / 0.4))
    if p0 <= 0:
        return
    brackets(d, 40, 190, W - 80, 1500, a(ACC, int(120 * p0)), 34, 3)
    chip(d, 60, 230, "КАНАЛ  //  В ОКОПЕ", ACC, 26, alpha=int(255 * p0))
    slam(ui, "«В ОКОПЕ»", RUSSO, 128, 540, 320, a(TXT, 255), c01((l - 0.08) / 0.42), dx=1.0, trail=34, anchor="ma")
    q = eout(c01((l - 0.3) / 0.45))
    if q > 0:
        d.text((60, 520), "ДРОНЫ  //  НАЛИЧИЕ", font=F(MONO, 32), fill=a(ACC, int(245 * q)))
        d.rectangle([60, 570, 60 + 960 * q, 574], fill=a(ACC, 210))

    links = [("TELEGRAM", "t.me/vokope_ru"), ("ВКОНТАКТЕ", "vk.com/vokope_rus"),
             ("АВИТО", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
    for i, (k, v) in enumerate(links):
        pp = c01((l - 0.55 - i * 0.16) / 0.4)
        if pp <= 0:
            continue
        yy = int(660 + i * 230 + (1 - eout(pp)) * 30)
        d.rectangle([56, yy, 1024, yy + 196], fill=(8, 12, 18, 246), outline=a(ACC, int(160 * eout(pp))))
        d.rectangle([56, yy, 64, yy + 196], fill=a(ACC, 255))
        d.text((104, yy + 26), k, font=F(MONO, 26), fill=a(ACC, 245))
        f = F(MONO, 34)
        while f.getlength(v) > 860 and f.size > 18:
            f = F(MONO, f.size - 2)
        d.text((104, yy + 78), v, font=f, fill=a(TXT, 246))

    pp = c01((l - 1.35) / 0.45)
    if pp > 0:
        blink = 0.6 + 0.4 * math.sin(l * 4)
        d.rectangle([56, 1400, 1024, 1520], fill=(8, 34, 28, 250), outline=a(ACC, 220))
        d.ellipse([100, 1444, 132, 1476], fill=a(ACC, int(235 * blink * eout(pp))))
        d.text((160, 1432), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 48), fill=a(ACC, 255))
    q2 = c01((l - 1.55) / 0.5)
    if q2 > 0:
        d.text((60, 1560), "наличие и комплектации — в личку", font=F(MONO, 27), fill=a(DIM, int(240 * q2)))
        xx = 60
        for i, m in enumerate(["3 КЛАССИК", "3 ПРО", "3Т", "4 ПРО", "4Т"]):
            qq = c01((l - 1.7 - i * 0.1) / 0.35)
            if qq <= 0:
                continue
            wch = chip(d, xx, 1614, m, ACC2, 21, bg=(10, 16, 22), h=40, alpha=int(235 * qq))
            xx += wch + 10


SCENES = [(BOUNDS[0], s_hook), (BOUNDS[1], s_lineup), (BOUNDS[2], s_configs),
          (BOUNDS[3], s_thermal), (BOUNDS[4], s_stock), (BOUNDS[5], s_cta), (BOUNDS[6], s_endcard)]


# ─────────────────────────── ПОСТ-ЭФФЕКТЫ ───────────────────────────
def rgb_split(im, amt):
    if amt <= 0:
        return im
    arr = np.asarray(im).astype(np.int16)
    out = arr.copy()
    out[:, :, 0] = np.roll(arr[:, :, 0], amt, axis=1)
    out[:, :, 2] = np.roll(arr[:, :, 2], -amt, axis=1)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def glitch(im, t, strength=26):
    arr = np.asarray(im)
    rnd = random.Random(int(t * 997))
    out = arr.copy()
    for _ in range(rnd.randint(4, 9)):
        y = rnd.randint(0, H - 40)
        hh = rnd.randint(6, 70)
        dx = rnd.randint(-strength, strength)
        out[y:y + hh] = np.roll(arr[y:y + hh], dx, axis=1)
    return Image.fromarray(out)


def render_frame(t):
    fn, st = SCENES[0][1], 0.0
    for s0, f in SCENES:
        if t >= s0 - 1e-6:
            fn, st = f, s0
    l = t - st
    cv = Image.new("RGBA", (W, H), a(BG, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    fn(cv, ui, d, t, l)
    out = Image.alpha_composite(cv, ui)
    hud = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hud)
    hud_top(dh, t)
    hud_bottom(dh)
    out = Image.alpha_composite(out, hud)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 15) % 5])
    out = out.convert("RGB")

    # зум-панч + тряска на склейке
    for b in BOUNDS[1:]:
        dd = t - b
        if 0 <= dd < 0.20:
            kk = 1 - dd / 0.20
            z = 1 + 0.045 * kk
            cw, ch = int(W / z), int(H / z)
            out = out.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
            rnd = random.Random(int(t * 331))
            dx = rnd.randint(-9, 9) * kk
            dy = rnd.randint(-9, 9) * kk
            out = Image.fromarray(np.roll(np.roll(np.asarray(out), int(dy), 0), int(dx), 1))

    # бит-пульс яркости — очень мягко
    beat = (t / BEAT) % 1.0
    k = 1.0 + 0.020 * math.exp(-beat * 7)
    arr = np.asarray(out.convert("RGB")).astype(np.float32) * k

    # переходы: глитч + вспышка
    for b in BOUNDS[1:-1]:
        dd = abs(t - b)
        if dd < 0.16:
            arr = np.asarray(glitch(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), t, 34)).astype(np.float32)
            arr = np.asarray(rgb_split(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), int(10 * (1 - dd / 0.16)))).astype(np.float32)
            fl = (1 - dd / 0.16) * 0.35
            arr = arr * (1 - fl) + np.array([255, 255, 255], np.float32) * fl
    # финальный флеш в энд-кард
    dd = abs(t - BOUNDS[-2])
    if dd < 0.2:
        fl = (1 - dd / 0.2) * 0.45
        arr = arr * (1 - fl) + np.array([0, 229, 160], np.float32) * fl
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    import sys
    os.makedirs("/tmp/chk", exist_ok=True)
    for arg in sys.argv[1:]:
        tt = float(arg)
        p = f"/tmp/chk/dr_{tt:05.2f}.jpg"
        render_frame(tt).save(p, quality=90)
        print("saved", p)
