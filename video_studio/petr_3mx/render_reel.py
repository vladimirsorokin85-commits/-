# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // 3MX «ПЁТР» — вертикальный Reels 9:16 (1080×1920, 30 fps)."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/petr_3mx"
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
    "hero": "photo_5323466278561324224_y.jpg", "three": "photo_5323466278561324225_y.jpg",
    "side": "photo_5323466278561324226_y.jpg", "batt": "photo_5323466278561324227_y.jpg",
    "jack": "photo_5323466278561324228_y.jpg", "btn": "photo_5323466278561324229_y.jpg",
    "disp": "photo_5323466278561324230_y.jpg", "mic": "photo_5323466278561324231_y.jpg",
    "kit": "photo_5341673641361480989_y.jpg", "hand": "photo_5341673641361480990_y.jpg",
    "kit2": "photo_5341673641361480991_y.jpg", "pouch": "photo_5341673641361480992_y.jpg",
    "bag": "photo_5341673641361480993_y.jpg", "set": "photo_5341673641361480994_y.jpg",
    "case": "photo_5341673641361480995_y.jpg",
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
    d.text((44, 90), "ТАКТИЧЕСКАЯ СВЯЗЬ  //  3MX «ПЁТР»", font=F(MONO, 17), fill=a(DIM, 235))
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

# ═════════════ СЦЕНА 1: «СЛЫШАТ НЕБО» ═════════════
def s1(ov, d, t, l):
    if l < 3.4:                     # титул
        p = eout(c01((l - 0.15) / 1.0))
        d.rectangle([0, 300, W, 1180], fill=(5, 8, 13, 225))
        d.rectangle([0, 300, 7, 1180], fill=a(ACC, 255))
        kicker(d, 56, 340, "ТЕХНИЧЕСКИЙ ОБЗОР  //  3MX", ACC, 16)
        f, sz = fit("ПЁТР", RUSSO, 300, 900)
        d.text((44, 400 + (1 - p) * 40), "ПЁТР", font=f, fill=a(TXT, 255 * p))
        f2, _ = fit("АКТИВНЫЕ ТАКТИЧЕСКИЕ НАУШНИКИ", RUSSO, 44, 940)
        rtext(d, (56, 780), "АКТИВНЫЕ", f2, ACC, (l - 0.55) / 0.5)
        rtext(d, (56, 838), "ТАКТИЧЕСКИЕ НАУШНИКИ", f2, ACC, (l - 0.7) / 0.5)
        d.rectangle([56, 930, 56 + 700 * eout(c01((l - 0.9) / 0.8)), 934], fill=a(ACC, 220))
        rtext(d, (56, 970), "ЗАЩИТА СЛУХА • ДЕТЕКЦИЯ БПЛА", F(MONO, 22), TXT, (l - 1.05) / 0.6)
        rtext(d, (56, 1010), "ЗАКРЫТЫЙ ИНТЕРКОМ AES-256", F(MONO, 22), TXT, (l - 1.2) / 0.6)

        chips = ["IP66/67", "50 Ч", "413 Г"]
        for i, c in enumerate(chips):
            pp = c01((l - 1.5 - i * 0.1) / 0.4)
            if pp <= 0: continue
            cf = F(MONO, 20); cw = tw(d, c, cf) + 40
            cx = 56 + i * 220
            d.rounded_rectangle([cx, 1080, cx + cw, 1132], 2, fill=(11, 16, 24, 240), outline=a(ACC, 120))
            d.text((cx + 20, 1094), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        if l > 2.2:
            card(ov, d, "disp", 700, 1210, 320, 300, l, 1.1, None, "01")
            card(ov, d, "mic", 56, 1250, 300, 320, l, 1.12, None, "02")

    elif l < 7.2:                   # детекция — радар
        kicker(d, 56, 200, "ДЕТЕКЦИЯ БПЛА", WARN, 17)
        f, _ = fit("СЛЫШИТ НЕБО", RUSSO, 84, 960)
        rtext(d, (48, 260), "СЛЫШИТ", f, TXT, (l - 0.1) / 0.45)
        rtext(d, (48, 356), "НЕБО", f, WARN, (l - 0.22) / 0.45)
        d.text((56, 470), "тревога от детектора — прямо в ухо", font=F(MONO, 21), fill=a(DIM, 240))

        cx, cy, R = 560, 1030, 350
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(4, 10, 12, 232), outline=a(ACC, 110), width=2)
        for k in (0.35, 0.68):
            d.ellipse([cx - R * k, cy - R * k, cx + R * k, cy + R * k], outline=a(ACC, 70))
        d.line([(cx - R, cy), (cx + R, cy)], fill=a(ACC, 55))
        d.line([(cx, cy - R), (cx, cy + R)], fill=a(ACC, 55))
        ang = -math.pi / 2 + (l * 1.7) % (2 * math.pi)
        sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sw)
        for i in range(24):
            aa = ang - i * 0.04
            sd.line([(cx, cy), (cx + math.cos(aa) * R, cy + math.sin(aa) * R)],
                    fill=a(ACC, 120 - i * 4), width=4)
        ov.alpha_composite(sw.filter(ImageFilter.GaussianBlur(4)))
        for k, (bx, by, ph) in enumerate([(-190, -140, 0.4), (150, -220, 1.9), (230, 110, 3.1), (-90, 230, 2.4)]):
            on = ((l + ph) % 2.6) < 1.2
            rr = 10 if on else 4
            d.ellipse([cx + bx - rr, cy + by - rr, cx + bx + rr, cy + by + rr],
                      fill=a(WARN, 245) if on else a(ACC, 90))
            if on:
                d.text((cx + bx + 18, cy + by - 11), f"UAV-0{k+1}", font=F(MONO, 15), fill=a(WARN, 225))
        d.text((cx, cy + R + 30), "СЕКТОР 360°  //  30–50 М", font=F(MONO, 17), fill=a(ACC, 225), anchor="ma")

        pp = c01((l - 0.9) / 0.5)
        if pp > 0:
            d.rectangle([56, 1470, 1024, 1600], fill=(22, 15, 6, 242), outline=a(WARN, 200), width=2)
            d.rectangle([56, 1470, 63, 1600], fill=a(WARN, 255))
            d.text((92, 1490), "ТРЕВОГА  //  «БУЛАТ v.4»", font=F(RUSSO, 26), fill=a(WARN, 255))
            d.text((92, 1532), "ЗАДЕРЖКА < 1 с   •   БЕЗ ОТВЛЕЧЕНИЯ", font=F(MONO, 19), fill=a(TXT, 245))

    elif l < 11.4:                  # режим БПЛА — макро кнопки
        kicker(d, 56, 200, "РЕЖИМЫ СЛУХА", WARN, 17)
        f, _ = fit("РЕЖИМ БПЛА", RUSSO, 80, 950)
        rtext(d, (48, 258), "РЕЖИМ", f, TXT, (l - 0.1) / 0.4)
        rtext(d, (48, 348), "БПЛА", f, WARN, (l - 0.2) / 0.4)
        d.text((56, 452), "усиление частот винтов квадрокоптера", font=F(MONO, 20), fill=a(DIM, 240))

        card(ov, d, "btn", 56, 530, 968, 720, l, 1.06, "БЛОК УПРАВЛЕНИЯ", "03")
        d.rectangle([56, 1310, 1024, 1430], fill=(10, 15, 22, 246), outline=a(WARN, 120))
        d.rectangle([56, 1310, 62, 1430], fill=a(WARN, 255))
        d.text((88, 1330), "ПЕРЕКЛЮЧЕНИЕ ВСЛЕПУЮ", font=F(RUSSO, 26), fill=a(TXT, 255))
        d.text((88, 1376), "три режима — без снятия перчаток", font=F(MONO, 18), fill=a(DIM, 240))

        # три профиля громкости
        d.text((56, 1480), "ПРОФИЛИ УСИЛЕНИЯ", font=F(MONO, 16), fill=a(DIM, 225))
        for i, (nm, col) in enumerate([("БПЛА", WARN), ("БЕРУШИ", ACC), ("ПАССИВ", ACC2)]):
            pp = c01((l - 0.5 - i * 0.15) / 0.4)
            if pp <= 0: continue
            yy = 1516 + i * 62
            d.rectangle([56, yy, 1024, yy + 50], fill=(10, 15, 22, 240), outline=a(LINE, 255))
            d.rectangle([56, yy, 61, yy + 50], fill=a(col, 255))
            d.text((88, yy + 13), nm, font=F(RUSSO, 20), fill=a(col, 255))
            for k in range(12):
                on = k < (9 - i * 2)
                d.rectangle([660 + k * 28, yy + 18, 678 + k * 28, yy + 32],
                            fill=a(col if on else LINE, 220 if on else 110))

    else:                           # 3 режима
        kicker(d, 56, 200, "ТРИ ПРОФИЛЯ", ACC, 17)
        f, _ = fit("РЕЖИМЫ", RUSSO, 80, 900)
        d.text((48, 258), "РЕЖИМЫ", font=f, fill=a(TXT, 255))
        modes = [("БПЛА", "винты квадрокоптера", WARN),
                 ("БЕРУШИ", "максимум громкости", ACC),
                 ("ПАССИВ", "защита без усиления", ACC2)]
        for i, (nm, sub, col) in enumerate(modes):
            pp = c01((l - 0.2 - i * 0.18) / 0.45)
            if pp <= 0: continue
            yy = int(380 + i * 210 + (1 - eout(pp)) * 30)
            d.rectangle([56, yy, 1024, yy + 176], fill=(11, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([56, yy, 63, yy + 176], fill=a(col, 255))
            d.text((92, yy + 24), nm, font=F(RUSSO, 44), fill=a(col, 255))
            d.text((92, yy + 96), sub, font=F(MONO, 20), fill=a(DIM, 240))
            d.text((988, yy + 24), f"0{i+1}", font=F(MONO, 18), fill=a(col, 200), anchor="ra")
        card(ov, d, "disp", 56, 1050, 968, 480, l, 1.04, "ДИСПЛЕЙ И УПРАВЛЕНИЕ", "04")
        wave(d, 56, 1580, 968, 90, t, ACC, 140, 58, 1.1)

# ═════════════ СЦЕНА 2: ИНТЕРКОМ ═════════════
def s2(ov, d, t, l):
    if l < 3.3:                     # заголовок + сеть
        kicker(d, 56, 200, "ЗАКРЫТЫЙ ИНТЕРКОМ", ACC, 17)
        f, _ = fit("ГРУППА БЕЗ РАЦИИ", RUSSO, 68, 960)
        rtext(d, (48, 258), "ГРУППА", f, TXT, (l - 0.1) / 0.4)
        rtext(d, (48, 330), "БЕЗ РАЦИИ", f, ACC, (l - 0.2) / 0.4)
        d.text((56, 420), "четверо говорят одновременно", font=F(MONO, 21), fill=a(DIM, 240))

        cx, cy = 540, 1010
        nodes = [(-330, -210), (330, -210), (-330, 250), (330, 250)]
        for i, (nx, ny) in enumerate(nodes):
            act = ((l * 1.1 + i * 0.5) % 2.2) < 0.85
            col = ACC if act else ACC2
            steps = 28
            for k in range(steps):
                if (k + int(l * 22)) % 2 == 0:
                    d.line([(cx + nx * k / steps, cy + ny * k / steps),
                            (cx + nx * (k + 1) / steps, cy + ny * (k + 1) / steps)],
                           fill=a(col, 160 if act else 75), width=4)
            d.ellipse([cx + nx - 66, cy + ny - 66, cx + nx + 66, cy + ny + 66],
                      fill=(9, 14, 20, 248), outline=a(col, 215), width=3)
            d.text((cx + nx, cy + ny), f"0{i+1}", font=F(RUSSO, 34), fill=a(TXT, 255), anchor="mm")
        pulse = 84 + 8 * math.sin(l * 3.4)
        d.ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], fill=(10, 22, 26, 252),
                  outline=a(ACC, 245), width=3)
        d.text((cx, cy - 18), "AES", font=F(RUSSO, 34), fill=a(ACC, 255), anchor="mm")
        d.text((cx, cy + 26), "256", font=F(MONO, 24), fill=a(TXT, 255), anchor="mm")

        d.rectangle([56, 1520, 1024, 1660], fill=(9, 13, 19, 244), outline=a(ACC, 120))
        d.text((88, 1544), "ПЕРЕХВАТ СНАРУЖИ НЕВОЗМОЖЕН", font=F(RUSSO, 25), fill=a(ACC, 255))
        d.text((88, 1590), "шифрование потока AES-256", font=F(MONO, 18), fill=a(DIM, 240))

    elif l < 7.0:                   # частота + спектр
        kicker(d, 56, 200, "РАБОЧИЕ ЧАСТОТЫ", ACC, 17)
        f, _ = fit("864 / 915", RUSSO, 78, 940)
        d.text((48, 258), "864 / 915", font=f, fill=a(TXT, 255))
        d.text((56, 372), "МГц  •  до 4 абонентов", font=F(MONO, 24), fill=a(ACC, 245))

        bx, by, bw, bh = 56, 470, 968, 560
        d.rectangle([bx, by, bx + bw, by + bh], fill=(7, 11, 16, 248), outline=a(LINE, 255))
        for k in range(7):
            yy = by + bh - k * bh / 6
            d.line([(bx, yy), (bx + bw, yy)], fill=a(LINE, 90))
        n = 40
        for i in range(n):
            fx = i / n
            base = 0.30 + 0.42 * math.exp(-((fx - 0.30) ** 2) / 0.02) + 0.34 * math.exp(-((fx - 0.74) ** 2) / 0.016)
            v = clamp(base * (0.74 + 0.26 * math.sin(t * 5 + i * 0.8) * math.cos(t * 1.6 + i * 0.3)), 0.03, 1)
            hh = int(v * (bh - 40))
            xx = bx + 18 + i * ((bw - 36) / n)
            col = ACC if abs(fx - 0.5) > 0.24 else ACC2
            d.rectangle([xx, by + bh - 20 - hh, xx + (bw - 36) / n - 6, by + bh - 20], fill=a(col, 215))
        for fxp, lbl in ((0.30, "864"), (0.74, "915")):
            xx = bx + 18 + fxp * (bw - 36)
            d.line([(xx, by + 14), (xx, by + bh - 20)], fill=a(WARN, 215), width=3)
            d.rectangle([xx - 46, by + 16, xx + 46, by + 54], fill=(26, 19, 6, 245), outline=a(WARN, 200))
            d.text((xx, by + 24), lbl, font=F(MONO, 20), fill=a(WARN, 255), anchor="ma")

        card(ov, d, "side", 56, 1090, 968, 460, l, 1.05, "АНТЕННЫЙ МОДУЛЬ  //  850–930 МГц", "05")
        d.rectangle([56, 1600, 1024, 1700], fill=(9, 13, 19, 240), outline=a(ACC, 110))
        d.text((88, 1626), "УЗКИЕ КАНАЛЫ = ПОМЕХОЗАЩИЩЁННОСТЬ", font=F(MONO, 21), fill=a(TXT, 245))

    elif l < 10.4:                  # дальность
        kicker(d, 56, 200, "ДАЛЬНОСТЬ СВЯЗИ", ACC, 17)
        f, _ = fit("50 / 100 М", RUSSO, 74, 950)
        d.text((48, 258), "50 / 100 М", font=f, fill=a(TXT, 255))
        d.text((56, 366), "уверенно в лесу и в застройке", font=F(MONO, 20), fill=a(DIM, 240))

        cx, cy = 540, 1150
        for i, (rr, lbl) in enumerate([(140, "25 м"), (250, "50 м"), (360, "100 м")]):
            prog = c01((l - 0.2 - i * 0.22) / 0.6)
            if prog <= 0: continue
            d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=200, end=340, fill=a(ACC, 225), width=4)
            ang = math.radians(200 + 140 * eout(prog))
            d.text((cx + math.cos(ang) * (rr + 30), cy + math.sin(ang) * (rr + 30)), lbl,
                   font=F(MONO, 18), fill=a(ACC, 225), anchor="mm")
        d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=a(ACC, 255))
        d.arc([cx - 360, cy - 360, cx + 360, cy + 360], start=200, end=340, fill=a(LINE, 255), width=3)

        for i, (k, v, col) in enumerate([("ОПТИМАЛЬНО", "50 м", ACC), ("МАКСИМУМ", "100 м", ACC2)]):
            yy = 1470 + i * 130
            d.rectangle([56, yy, 1024, yy + 110], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([56, yy, 62, yy + 110], fill=a(col, 255))
            d.text((92, yy + 18), k, font=F(MONO, 16), fill=a(DIM, 240))
            d.text((92, yy + 46), v, font=F(RUSSO, 44), fill=a(col, 255))

    else:                           # микрофон
        kicker(d, 56, 200, "МИКРОФОННЫЙ УЗЕЛ", ACC2, 17)
        f, _ = fit("СЛЫШНО В ШУМЕ", RUSSO, 62, 960)
        d.text((48, 258), "СЛЫШНО", font=f, fill=a(TXT, 255))
        d.text((48, 336), "В ШУМЕ", font=f, fill=a(ACC2, 255))
        card(ov, d, "mic", 56, 450, 968, 700, l, 1.05, "ВЕТРОЗАЩИТА  //  IP67", "06")
        rows = [("ЧУВСТВИТЕЛЬНОСТЬ", "−60 дБВ/Па"), ("ШТАНГА", "регулируемая 360°")]
        for i, (k, v) in enumerate(rows):
            yy = 1290 + i * 128
            d.rectangle([56, yy, 1024, yy + 108], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([56, yy, 62, yy + 108], fill=a(ACC2, 255))
            d.text((92, yy + 16), k, font=F(MONO, 17), fill=a(DIM, 235))
            d.text((92, yy + 50), v, font=F(RUSSO, 30), fill=a(TXT, 255))
        wave(d, 56, 1560, 968, 100, t, ACC2, 130, 60, 1.15)

# ═════════════ СЦЕНА 3: ЖЕЛЕЗО + CTA ═════════════
def s3(ov, d, t, l):
    if l < 3.0:                     # питание
        kicker(d, 56, 200, "ПИТАНИЕ", ACC, 17)
        f, _ = fit("ДО 50", RUSSO, 110, 900)
        d.text((48, 258), "ДО 50", font=f, fill=a(TXT, 255))
        d.text((48, 390), "ЧАСОВ", font=F(RUSSO, 70), fill=a(ACC, 255))
        d.text((56, 490), "две батарейки AAA — без зарядки в поле", font=F(MONO, 20), fill=a(DIM, 240))

        p = eout(c01((l - 0.2) / 1.3))
        d.text((56, 560), f"{int(50*p):02d}", font=F(RUSSO, 190), fill=a(ACC, 255))
        d.text((450, 680), "часов", font=F(MONO, 30), fill=a(DIM, 240))
        d.rectangle([56, 790, 1024, 812], fill=(15, 22, 32, 240))
        d.rectangle([56, 790, 56 + int(968 * p), 812], fill=a(ACC, 255))

        card(ov, d, "batt", 56, 860, 968, 560, l, 1.05, "ОТСЕК 2×AAA", "07")
        d.rectangle([56, 1540, 1024, 1660], fill=(9, 13, 19, 244), outline=a(ACC, 120))
        d.text((88, 1564), "ЗАМЕНА БЕЗ ИНСТРУМЕНТОВ", font=F(RUSSO, 27), fill=a(ACC, 255))
        d.text((88, 1608), "в поле, в темноте, в перчатках", font=F(MONO, 18), fill=a(DIM, 240))

    elif l < 6.4:                   # защита / IP
        kicker(d, 56, 200, "ЗАЩИТА КОРПУСА", ACC2, 17)
        f, _ = fit("IP66 / IP67", RUSSO, 70, 960)
        d.text((48, 258), "IP66 / IP67", font=f, fill=a(TXT, 255))
        d.text((56, 360), "–20…+40 °C  •  пыль, вода, мороз", font=F(MONO, 20), fill=a(DIM, 240))

        d.rectangle([56, 450, 1024, 640], fill=(10, 15, 22, 246), outline=a(ACC, 130))
        d.text((88, 476), "IP66", font=F(RUSSO, 54), fill=a(ACC, 255))
        d.text((88, 546), "наушники: пыль и струи воды", font=F(MONO, 20), fill=a(TXT, 240))
        d.rectangle([56, 670, 1024, 860], fill=(10, 15, 22, 246), outline=a(ACC2, 130))
        d.text((88, 696), "IP67", font=F(RUSSO, 54), fill=a(ACC2, 255))
        d.text((88, 766), "микрофон: кратковременное погружение", font=F(MONO, 20), fill=a(TXT, 240))

        card(ov, d, "case", 56, 900, 968, 500, l, 1.04, "ТАКТИЧЕСКИЙ КЕЙС", "08")

        gx, gy, gw = 56, 1460, 968
        d.rectangle([gx, gy, gx + gw, gy + 90], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(7):
            xx = gx + 24 + i * (gw - 48) / 6
            d.line([(xx, gy + 46), (xx, gy + 90)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 96), f"{-20+i*10}", font=F(MONO, 16), fill=a(DIM, 230), anchor="ma")
        pp = eout(c01((l - 0.4) / 1.2))
        d.rectangle([gx + 24, gy + 30, gx + 24 + int((gw - 48) * pp), gy + 46], fill=a(ACC, 210))

    elif l < 9.6:                   # вес
        kicker(d, 56, 200, "ЭРГОНОМИКА", ACC2, 17)
        f, _ = fit("413 Г", RUSSO, 150, 700)
        d.text((48, 258), "413 Г", font=f, fill=a(TXT, 255))
        d.text((56, 440), "с батареями — без перегруза шеи", font=F(MONO, 20), fill=a(DIM, 240))
        card(ov, d, "hero", 56, 540, 968, 780, l, 1.04, "ПОСАДКА И БАЛАНС", "09")
        for i, txt in enumerate(["прижим регулируется", "совместимость со шлемом", "микрофон не мешает прикладу"]):
            yy = 1400 + i * 82
            d.text((56, yy), "—", font=F(RUSSO, 24), fill=a(ACC, 255))
            d.text((88, yy + 2), txt, font=F(MONO, 20), fill=a(TXT, 240))

    else:                           # CTA
        p = eout(c01((l - 0.1) / 0.7))
        d.rectangle([0, 240, W, 1700], fill=(5, 8, 13, 228))
        d.rectangle([0, 240, 7, 1700], fill=a(ACC, 255))
        d.text((56, 300), "3MX", font=F(RUSSO, 120), fill=a(TXT, 255 * p))
        d.text((56, 440), "«ПЁТР»", font=F(RUSSO, 120), fill=a(ACC, 255 * p))
        d.line([(56, 620), (56 + 900 * p, 620)], fill=a(ACC, 180), width=3)
        d.text((56, 660), "ЗАЩИТА • ДЕТЕКЦИЯ • ИНТЕРКОМ", font=F(RUSSO, 34), fill=a(TXT, 255 * p))

        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - 0.5 - i * 0.16) / 0.4)
            if pp <= 0: continue
            yy = int(780 + i * 118 + (1 - eout(pp)) * 22)
            d.rectangle([56, yy, 1024, yy + 100], fill=(11, 16, 23, 246), outline=a(ACC, 120))
            d.rectangle([56, yy, 63, yy + 100], fill=a(ACC, 255))
            d.text((92, yy + 14), k, font=F(RUSSO, 22), fill=a(ACC, 255))
            d.text((92, yy + 54), v, font=F(MONO, 17), fill=a(TXT, 240))

        card(ov, d, "set", 56, 1140, 968, 420, l, 1.03, None, "10")
        d.text((56, 1600), "ТЕХНИЧЕСКИЙ ОБЗОР  //  БЕЗ ЦЕН  //  ФАКТЫ ИЗ ПАСПОРТА",
               font=F(MONO, 16), fill=a(DIM, 210))

SCENES = [(1.80, s1), (15.48, s2), (27.77, s3)]
TOTAL = 45.44
CUTS = [1.8, 3.4, 7.2, 11.4, 15.48, 18.78, 22.48, 25.88, 27.77, 30.77, 34.17, 37.37, 40.57]

def render_frame(t):
    if t < 1.80:
        idx = -1; l = t; name = "hero"; fn = None
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001: idx = i
        st, fn = SCENES[idx]; l = t - st
        if idx == 0:
            name = "hero" if l < 3.4 else ("btn" if l < 7.2 else ("disp" if l < 11.4 else "three"))
        elif idx == 1:
            name = "side" if l < 3.3 else ("three" if l < 7.0 else ("side" if l < 10.4 else "mic"))
        else:
            name = "batt" if l < 3.0 else ("case" if l < 6.4 else ("hero" if l < 9.6 else "set"))

    z0 = 1.03 + 0.012 * math.sin(t * .9)
    base = cam(name, l, 4.0, z0, z0 + .10, .30 * math.sin(t * .15), .16 * math.cos(t * .19)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    top(ov, d, t, TOTAL)
    if fn is None:
        p = eout(c01(t / .9))
        d.rectangle([0, 800, W, 1200], fill=(5, 8, 13, int(215 * p)))
        d.text((W // 2, 860), "«В ОКОПЕ»", font=F(RUSSO, 92), fill=a(TXT, int(255 * c01(t / .6))), anchor="ma")
        d.text((W // 2, 990), "ТАКТИЧЕСКАЯ СВЯЗЬ", font=F(MONO, 26), fill=a(ACC, int(235 * c01((t - .3) / .6))), anchor="ma")
        w = 560 * eout(c01((t - .35) / .7))
        d.rectangle([W // 2 - w / 2, 1054, W // 2 + w / 2, 1058], fill=a(ACC, 220))
        wave(d, 160, 1120, 760, 120, t, ACC, 120, 60, 1.0)
    else:
        fn(ov, d, t, l)

    d.rectangle([0, H - 152, W, H], fill=(7, 10, 16, 246))
    d.line([(0, H - 152), (W, H - 152)], fill=a(ACC, 110), width=1)
    d.text((W // 2, H - 118), "t.me/vokope_ru   •   vk.com/vokope_rus", font=F(MONO, 24), fill=a(ACC, 240), anchor="ma")
    d.text((W // 2, H - 76), "3MX «ПЁТР»  //  ТАКТИЧЕСКАЯ СВЯЗЬ", font=F(RUSSO, 17), fill=a(DIM, 225), anchor="ma")

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
