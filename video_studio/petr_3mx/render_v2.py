# -*- coding: utf-8 -*-
"""
«В ОКОПЕ» // 3MX «ПЁТР» — горизонтальный 16:9 обзор.
Motion-движок: непрерывное движение камеры, кинетическая типографика,
HUD-телеметрия, макро-инсерты, реальная звуковая волна из мастера.
"""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1920, 1080
FPS = 30
BASE = "/home/user/-/video_studio/petr_3mx"
ASSETS = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

# ─────────────────────────── палитра ───────────────────────────
BG      = (6, 8, 12)
PANEL   = (10, 13, 20)
PANEL2  = (8, 10, 15)
ACC     = (0, 229, 160)      # основной зелёный
ACC2    = (0, 176, 255)      # циан
WARN    = (255, 176, 32)     # тревога
RED     = (255, 82, 82)
TXT     = (242, 246, 255)
DIM     = (140, 162, 186)
LINE    = (34, 52, 74)


def F(name, size):
    return ImageFont.truetype(os.path.join(FD, name), size)

RUSSO, DAYS, MONO, TEK, OSW = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf",
                               "JetBrainsMono-VF.ttf", "Tektur-VF.ttf", "Oswald-VF.ttf")

# ─────────────────────────── утилиты ───────────────────────────
def clamp(x, a, b):
    return a if x < a else (b if x > b else x)

def c01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def eout(x):
    x = c01(x); return 1 - (1 - x) ** 3

def eio(x):
    x = c01(x); return x * x * (3 - 2 * x)

def eback(x):
    x = c01(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def a(col, alpha):
    return (col[0], col[1], col[2], int(clamp(alpha, 0, 255)))

def tw(d, s, font):
    return d.textlength(s, font=font)

def fit(text, font_name, size, max_w, min_size=10):
    s = size
    while s > min_size:
        f = F(font_name, s)
        if f.getlength(text) <= max_w:
            return f
        s -= 2
    return F(font_name, min_size)

# ─────────────────────────── фото ───────────────────────────
PHOTOS = {}
for fn in sorted(os.listdir(ASSETS)):
    if fn.endswith(".jpg") and "(" not in fn:
        PHOTOS[fn] = Image.open(os.path.join(ASSETS, fn)).convert("RGB")

P = {
    "hero":   "photo_5323466278561324224_y.jpg",
    "three":  "photo_5323466278561324225_y.jpg",
    "side":   "photo_5323466278561324226_y.jpg",
    "batt":   "photo_5323466278561324227_y.jpg",
    "jack":   "photo_5323466278561324228_y.jpg",
    "btn":    "photo_5323466278561324229_y.jpg",
    "disp":   "photo_5323466278561324230_y.jpg",
    "mic":    "photo_5323466278561324231_y.jpg",
    "kit":    "photo_5341673641361480989_y.jpg",
    "hand":   "photo_5341673641361480990_y.jpg",
    "kit2":   "photo_5341673641361480991_y.jpg",
    "pouch":  "photo_5341673641361480992_y.jpg",
    "bag":    "photo_5341673641361480993_y.jpg",
    "set":    "photo_5341673641361480994_y.jpg",
    "case":   "photo_5341673641361480995_y.jpg",
}

BGW, BGH = 2560, 1440           # мастер-холст фона (с запасом под зум)
COVER = {}


def bg_plate(name):
    """Затемнённая киношная подложка 16:9 из фото."""
    if name in COVER:
        return COVER[name]
    im = PHOTOS[P[name]]
    s = max(BGW / im.width, BGH / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - BGW) // 2
    y = (im.height - BGH) // 2
    im = im.crop((x, y, x + BGW, y + BGH))
    # кино-грейд: приглушение + холод
    im = im.point(lambda v: int(v * 0.46))
    tint = Image.new("RGB", (BGW, BGH), (10, 22, 40))
    im = Image.blend(im, tint, 0.30)
    COVER[name] = im
    return im


PCACHE = {}

def photo_tile(name, w, h, zoom=1.0, px=0.0, py=0.0, bright=1.0):
    """Кадрирование фото в плитку w×h с зумом/панорамой (быстрый путь)."""
    key = (name, w, h)
    if key not in PCACHE:
        im = PHOTOS[P[name]]
        s = max(w * 1.7 / im.width, h * 1.7 / im.height)
        im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
        PCACHE[key] = im
    src = PCACHE[key]
    cw, ch = int(w * 1.7 / zoom), int(h * 1.7 / zoom)
    cw = min(cw, src.width); ch = min(ch, src.height)
    cx = src.width / 2 + px * (src.width - cw) / 2
    cy = src.height / 2 + py * (src.height - ch) / 2
    x0 = int(clamp(cx - cw / 2, 0, src.width - cw))
    y0 = int(clamp(cy - ch / 2, 0, src.height - ch))
    out = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)
    # кино-грейд: чуть темнее и холоднее
    out = out.point(lambda v: int(clamp(v * 0.90 * bright, 0, 255)))
    gr = Image.new("RGB", (w, h), (12, 26, 44))
    out = Image.blend(out, gr, 0.10)
    return out


def camera(name, t, dur, z0=1.0, z1=1.08, px=0.0, py=0.0, shake=1.0):
    """Непрерывный проезд камеры по фоновой плите."""
    img = bg_plate(name)
    p = eio(c01(t / max(dur, 0.001)))
    z = z0 + (z1 - z0) * p
    cw, ch = BGW / z, BGH / z
    cx = BGW / 2 + px * (BGW - cw) / 2 + shake * math.sin(t * 1.31) * 4
    cy = BGH / 2 + py * (BGH - ch) / 2 + shake * math.cos(t * 1.73) * 3
    x0 = int(clamp(cx - cw / 2, 0, BGW - cw))
    y0 = int(clamp(cy - ch / 2, 0, BGH - ch))
    return img.crop((x0, y0, x0 + int(cw), y0 + int(ch))).resize((W, H), Image.BILINEAR)


# ─────────────────────────── статика оверлея ───────────────────────────
VIGNETTE = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_vd = ImageDraw.Draw(VIGNETTE)
for i in range(140):
    k = i / 140.0
    ins = int(-260 + k * 620)
    _vd.ellipse([ins, ins * 0.62, W - ins, H - ins * 0.62],
                outline=(0, 0, 0, int(3 + k * 2.2)), width=6)
VIGNETTE = VIGNETTE.filter(ImageFilter.GaussianBlur(24))

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_sd = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _sd.line([(0, y), (W, y)], fill=(0, 0, 0, 26))

_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 34, (H // 2, W // 2), dtype=np.uint8)
    gi = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (gi, gi, gi, Image.new("L", (W, H), 20))))

# ─────────────────────────── звуковая волна ───────────────────────────
ENV = None
_env_path = os.path.join(BASE, "env.npy")
if os.path.exists(_env_path):
    ENV = np.load(_env_path)

# ─────────────────────────── примитивы ───────────────────────────
def panel(ov, x, y, w, h, fill=(10, 13, 20, 236), stroke=(34, 52, 74, 255),
          bar=None, r=3, bar_w=4):
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x, y, x + w, y + h], r, fill=fill, outline=stroke, width=1)
    if bar:
        d.rectangle([x, y + 6, x + bar_w, y + h - 6], fill=bar)


def brackets(d, x, y, w, h, col=(0, 229, 160, 190), ln=18, wd=2):
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        d.line([(cx, cy), (cx + sx * ln, cy)], fill=col, width=wd)
        d.line([(cx, cy), (cx, cy + sy * ln)], fill=col, width=wd)


def kicker(d, x, y, text, col=ACC, padx=12, size=15):
    f = F(MONO, size)
    w = tw(d, text, f)
    d.rectangle([x, y, x + w + padx * 2, y + 30], fill=a((8, 26, 22), 235), outline=a(col, 150), width=1)
    d.rectangle([x, y, x + 4, y + 30], fill=a(col, 255))
    d.text((x + padx, y + 8), text, font=f, fill=a(col, 255))


def reveal_text(d, xy, text, font, color, p, dy=26, anchor="la"):
    p = c01(p)
    if p <= 0:
        return
    e = eout(p)
    d.text((xy[0], xy[1] + (1 - e) * dy), text, font=font, fill=a(color, 255 * e), anchor=anchor)


def wipe_title(d, xy, text, font, color, p, fill_bg=(10, 13, 20, 240)):
    """Кинетический заголовок: плашка раскрывается слева, буквы наплывают."""
    p = c01(p)
    if p <= 0:
        return
    w = tw(d, text, font)
    reveal_w = w * eout(min(1, p * 1.8))
    d.rectangle([xy[0] - 22, xy[1] - 12, xy[0] + reveal_w + 18, xy[1] + font.size * 1.28],
                fill=fill_bg)
    if p > 0.05:
        d.text(xy, text, font=font, fill=a(color, 255 * c01((p - 0.05) / 0.6)))


def waveform(d, x, y, w, h, t, col=ACC, alpha=120, bars=64, drive=1.0):
    if ENV is None:
        return
    i0 = int(t * FPS) % len(ENV)
    step = max(1, len(ENV) // 400)
    for i in range(bars):
        idx = (i0 + i * step) % len(ENV)
        v = float(ENV[idx]) * drive
        bh = max(2, int(clamp(v, 0, 1) * h))
        bx = x + i * (w / bars)
        d.rectangle([bx, y + (h - bh) / 2, bx + max(2, w / bars - 2), y + (h + bh) / 2],
                    fill=a(col, alpha))


def meter(d, x, y, t, n=18, col=ACC):
    i0 = int(t * FPS) % max(1, len(ENV) if ENV is not None else 1)
    for i in range(n):
        v = float(ENV[(i0 + i * 3) % len(ENV)]) if ENV is not None else 0.4
        bh = int(4 + v * 16)
        d.rectangle([x + i * 6, y - bh + 10, x + i * 6 + 4, y + 10], fill=a(col, 150 + v * 100))


def hex_stream(d, x, y, w, h, t, rows=6, col=ACC2, alpha=70, size=13):
    f = F(MONO, size)
    rng = np.random.default_rng(int(t * 12))
    for r in range(rows):
        s = "".join(rng.choice(list("0123456789ABCDEF"), 26))
        d.text((x, y + r * (h / rows)), s, font=f, fill=a(col, alpha * (0.4 + 0.6 * (r / rows))))


# ─────────────────────────── ambient motion ───────────────────────────
SWEEP = None

def make_sweep():
    g = Image.new("RGBA", (W + 700, H + 700), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for i in range(26):
        dg.line([(i * 26, 0), (i * 26 + 700, H + 700)], fill=(120, 255, 220, 5), width=26)
    return g.filter(ImageFilter.GaussianBlur(40))

SWEEP = make_sweep()

def ambient(ov, d, t):
    """Постоянное фоновое движение: световой скан + бегущая строка."""
    period = 7.0
    p = (t % period) / period
    off = int(-700 + p * (W + 1400))
    ov.alpha_composite(SWEEP, (off, -350))
    # бегущая строка
    strip_y = H - 96
    d.rectangle([0, strip_y, W, strip_y + 30], fill=(8, 11, 17, 238))
    d.line([(0, strip_y), (W, strip_y)], fill=a((26, 40, 58), 255), width=1)
    msg = ("АКТИВНАЯ ЗАЩИТА СЛУХА  •  ДЕТЕКЦИЯ БПЛА «БУЛАТ v.4» / «МАРС» / «ТАИР»  •  "
           "ИНТЕРКОМ AES-256, 864/915 МГЦ  •  ДО 4 АБОНЕНТОВ  •  ДО 50 ЧАСОВ  •  "
           "IP66 / IP67  •  413 Г  •  АДАПТЕРЫ НА ШЛЕМ В КОМПЛЕКТЕ  •  ")
    fm = F(MONO, 15)
    mw = tw(d, msg, fm)
    x = int(-(t * 90) % mw)
    while x < W:
        d.text((x, strip_y + 7), msg, font=fm, fill=a((150, 200, 195), 170))
        x += mw


# ─────────────────────────── верх / низ ───────────────────────────
def chrome(ov, d, t, total, section):
    # верхняя панель
    d.rectangle([0, 0, W, 62], fill=(9, 12, 18, 248))
    d.line([(0, 62), (W, 62)], fill=a(ACC, 120), width=1)
    d.rectangle([0, 0, 6, 62], fill=a(ACC, 255))
    fb = F(RUSSO, 22)
    d.text((26, 20), "«В ОКОПЕ»", font=fb, fill=a(TXT, 255))
    xb = 26 + tw(d, "«В ОКОПЕ»", fb) + 18
    d.text((xb, 23), "//  ТАКТИЧЕСКАЯ СВЯЗЬ И РЭБ", font=F(MONO, 15), fill=a(DIM, 235))
    d.text((xb + 268, 23), f"//  {section}", font=F(MONO, 15), fill=a(ACC, 240))

    # прогресс
    p = clamp(t / total, 0, 1)
    d.rectangle([0, 63, W, 66], fill=(12, 18, 26, 245))
    d.rectangle([0, 63, int(W * p), 66], fill=a(ACC, 235))
    d.rectangle([int(W * p) - 2, 61, int(W * p) + 2, 68], fill=a(ACC, 255))

    # таймкод + индикатор
    tc = f"TC {int(t//60):02d}:{int(t%60):02d}:{int((t*FPS)%FPS):02d}"
    d.text((W - 214, 21), tc, font=F(MONO, 16), fill=a(ACC, 240))
    d.ellipse([W - 250, 24, W - 238, 36], fill=a(RED, 230))
    meter(d, W - 470, 44, t)

    # нижняя панель
    ambient(ov, d, t)
    d.rectangle([0, H - 58, W, H], fill=(9, 12, 18, 252))
    d.line([(0, H - 58), (W, H - 58)], fill=a(LINE, 255), width=1)
    d.text((26, H - 40), "3MX «ПЁТР»  //  ТАКТИЧЕСКАЯ СВЯЗЬ", font=F(MONO, 15), fill=a(DIM, 235))
    d.text((W - 430, H - 40), "t.me/vokope_ru", font=F(MONO, 15), fill=a(ACC, 235))
    d.text((W - 250, H - 40), "vk.com/vokope_rus", font=F(MONO, 15), fill=a(ACC, 235))


# ─────────────────────────── фото-плитки ───────────────────────────
def photo_panel(ov, d, name, x, y, w, h, t, zoom=1.03, py=0.0, label=None, idx=None, bright=1.0):
    d.rectangle([x - 10, y - 10, x + w + 10, y + h + 10], fill=(7, 10, 16, 246))
    d.rectangle([x - 10, y - 10, x + w + 10, y + h + 10], outline=a(LINE, 255), width=1)
    z = zoom + 0.035 * math.sin(t * 0.55) + 0.012 * math.sin(t * 1.7)
    ov.paste(photo_tile(name, w, h, z, 0.22 * math.sin(t * 0.38), py + 0.10 * math.cos(t * 0.31), bright), (x, y))
    brackets(d, x - 10, y - 10, w + 20, h + 20, a(ACC, 200))
    if label:
        lf = F(MONO, 15)
        lw = tw(d, label, lf)
        d.rectangle([x - 10, y + h + 10, x + lw + 30, y + h + 50], fill=(8, 11, 17, 248))
        d.rectangle([x - 10, y + h + 10, x - 4, y + h + 50], fill=a(ACC, 255))
        d.text((x + 4, y + h + 20), label, font=lf, fill=a(ACC, 250))
    if idx:
        d.text((x + w - 16, y + 14), idx, font=F(MONO, 15), fill=a(ACC, 215), anchor="ra")


# ═══════════════════════════ СЦЕНА 1 ═══════════════════════════
def scene1(base, ov, d, t, l):
    if l < 5.6:                                   # 2.6–8.2  — хиро
        p = eout(c01((l - 0.3) / 1.2))
        d.rectangle([0, 330, 1180, 900], fill=(7, 10, 16, 205))
        d.rectangle([0, 330, 8, 900], fill=a(ACC, 255))
        kicker(d, 70, 300 if False else 292, "ТЕХНИЧЕСКИЙ ОБЗОР  //  3MX", ACC, size=15)

        f1 = fit("ПЁТР", RUSSO, 168, 1080)
        wipe_title(d, (70, 348), "ПЁТР", f1, TXT, (l - 0.5) / 0.7)
        f2 = F(RUSSO, 40)
        reveal_text(d, (76, 560), "АКТИВНЫЕ ТАКТИЧЕСКИЕ НАУШНИКИ", f2, ACC, (l - 1.0) / 0.6)
        f3 = F(MONO, 21)
        reveal_text(d, (78, 620), "ЗАЩИТА СЛУХА • ДЕТЕКЦИЯ БПЛА • ЗАКРЫТЫЙ ИНТЕРКОМ",
                    f3, TXT, (l - 1.35) / 0.7)
        d.line([(78, 668), (78 + 760 * eout(c01((l - 1.5) / 0.8)), 668)], fill=a(ACC, 200), width=2)

        chips = ["IP66 / IP67", "ДО 50 ЧАСОВ", "413 Г", "AES-256"]
        for i, c in enumerate(chips):
            pp = c01((l - 1.9 - i * 0.12) / 0.45)
            if pp <= 0:
                continue
            cf = F(MONO, 17)
            cw = tw(d, c, cf) + 34
            cx = 78 + i * 214
            yy = int(706 + (1 - eout(pp)) * 18)
            d.rounded_rectangle([cx, yy, cx + cw, yy + 42], 2, fill=(11, 16, 24, 240),
                                outline=a(ACC, 120), width=1)
            d.text((cx + 17, yy + 11), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        # макро-инсерт в правом нижнем углу
        if 1.6 < l < 5.4:
            pp = eout(c01((l - 1.6) / 0.5))
            ix, iy, iw, ih = 1290, 640, 540, 300
            d.rectangle([ix - 8, iy - 8, ix + iw + 8, iy + ih + 8], fill=(7, 10, 16, 235))
            ov.paste(photo_tile("disp", iw, ih, 1.12, 0.0, 0.0), (ix, iy))
            brackets(d, ix - 8, iy - 8, iw + 16, ih + 16, a(ACC, 190))
            d.rectangle([ix - 8, iy + ih + 8, ix + 250, iy + ih + 46], fill=(8, 11, 17, 245))
            d.text((ix + 2, iy + ih + 18), "МОДУЛЬ УПРАВЛЕНИЯ", font=F(MONO, 14), fill=a(ACC, 240))
            d.rectangle([ix - 8, iy - 16, ix - 8 + int((iw + 16) * pp), iy - 10], fill=a(ACC, 200))

        # боковой вертикальный лейбл
        d.text((W - 44, 300), "3MX // ПЁТР // 2025", font=F(MONO, 14), fill=a(DIM, 150), anchor="ra")
        for i in range(10):
            d.rectangle([W - 40, 340 + i * 26, W - 26, 340 + i * 26 + 14],
                        fill=a(ACC, 60 + 40 * ((i + int(t * 4)) % 10 == 0)))

    elif l < 10.6:                                # 8.2–13.2 — три функции
        d.rectangle([0, 260, 1080, 880], fill=(7, 10, 16, 210))
        d.rectangle([0, 260, 8, 880], fill=a(ACC, 255))
        kicker(d, 70, 292, "ФУНКЦИОНАЛ", ACC)
        f = fit("ТРИ СИСТЕМЫ В ОДНОМ КОРПУСЕ", RUSSO, 54, 980)
        reveal_text(d, (70, 342), "ТРИ СИСТЕМЫ", f, TXT, (l - 0.2) / 0.5)
        reveal_text(d, (70, 402), "В ОДНОМ КОРПУСЕ", f, ACC, (l - 0.35) / 0.55)

        rows = [("01", "АКТИВНАЯ ЗАЩИТА СЛУХА", "пассивное подавление 24 дБ"),
                ("02", "ДЕТЕКЦИЯ БПЛА", "тревоги от «Булат v.4», «Марс», «Таир»"),
                ("03", "ЗАКРЫТЫЙ ИНТЕРКОМ", "AES-256, до 4 абонентов")]
        for i, (num, tt, sub) in enumerate(rows):
            pp = c01((l - 0.7 - i * 0.18) / 0.5)
            if pp <= 0:
                continue
            yy = int(500 + i * 118 + (1 - eout(pp)) * 26)
            d.rectangle([70, yy, 1040, yy + 98], fill=(12, 17, 25, 240), outline=a(LINE, 255))
            d.rectangle([70, yy, 76, yy + 98], fill=a(ACC, 255))
            d.text((94, yy + 26), num, font=F(RUSSO, 34), fill=a(ACC, 235))
            d.text((172, yy + 16), tt, font=F(RUSSO, 27), fill=a(TXT, 255 * eout(pp)))
            d.text((172, yy + 56), sub, font=F(MONO, 17), fill=a(DIM, 255 * eout(pp)))
            d.line([(94, yy + 98), (94 + 940 * eout(pp), yy + 98)], fill=a(ACC, 90), width=1)

        photo_panel(ov, d, "hero", 1160, 250, 700, 560, t, 1.05, label="3MX «ПЁТР» / ОБЩИЙ ВИД", idx="01")

    elif l < 16.0:                                # 13.2–18.6 — ТТХ
        d.rectangle([0, 96, W, 232], fill=(6, 9, 14, 232))
        kicker(d, 40, 112, "ТАКТИКО-ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ", ACC)
        d.text((40, 152), "ЧТО ВАЖНО ЗНАТЬ ДО ПОКУПКИ", font=fit("ЧТО ВАЖНО ЗНАТЬ ДО ПОКУПКИ", RUSSO, 46, 1200),
               fill=a(TXT, 255))

        specs = [("НАЗНАЧЕНИЕ", "оперативные группы, расчёты РЭБ, штурмовики"),
                 ("ПОДАВЛЕНИЕ", "пассивное 24 дБ, максимум 82 дБ"),
                 ("ИНТЕРКОМ", "864 / 915 МГц, до 4 абонентов"),
                 ("ШИФРОВАНИЕ", "AES-256"),
                 ("АВТОНОМНОСТЬ", "до 50 часов, 2×AAA"),
                 ("ЗАЩИТА", "IP66 / IP67, –20…+40 °C")]
        for i, (k, v) in enumerate(specs):
            pp = c01((l - 0.25 - i * 0.13) / 0.45)
            if pp <= 0:
                continue
            yy = int(262 + i * 104 + (1 - eout(pp)) * 22)
            d.rectangle([40, yy, 1100, yy + 88], fill=(11, 15, 22, 242), outline=a(LINE, 255))
            d.rectangle([40, yy, 45, yy + 88], fill=a(ACC, 255))
            d.text((68, yy + 18), k, font=F(RUSSO, 21), fill=a(ACC, 250))
            d.text((68, yy + 52), v, font=F(MONO, 18), fill=a(TXT, 255 * eout(pp)))
            # бегущий индикатор
            d.rectangle([40, yy + 84, 40 + int(1060 * c01((l - 0.25 - i * 0.13) / 1.2)), yy + 88],
                        fill=a(ACC, 110))

        photo_panel(ov, d, "disp", 1170, 280, 700, 420, t, 1.1, label="ДИСПЛЕЙ И ОРГАНЫ УПРАВЛЕНИЯ", idx="02")
        photo_panel(ov, d, "batt", 1170, 762, 700, 240, t, 1.12, label="ОТСЕК ПИТАНИЯ 2×AAA")

    elif l < 22.3:                                # 18.6–24.9 — комплект
        kicker(d, 40, 112, "ОБЗОР КОМПЛЕКТА", ACC)
        d.text((40, 152), "ЧТО В КОРОБКЕ", font=fit("ЧТО В КОРОБКЕ", RUSSO, 52, 900), fill=a(TXT, 255))
        items = [("kit", "СУМКА-КЕЙС", "модульные ячейки"),
                 ("hand", "ОГОЛОВЬЕ", "быстрая регулировка"),
                 ("kit2", "БАТАРЕИ + КАБЕЛИ", "полный ЗИП")]
        for i, (nm, tt, sub) in enumerate(items):
            pp = c01((l - 0.2 - i * 0.22) / 0.55)
            if pp <= 0:
                continue
            x = 40 + i * 596
            y = int(250 + (1 - eout(pp)) * 40)
            d.rectangle([x, y, x + 560, y + 560], fill=(7, 11, 17, 244), outline=a(LINE, 255))
            ov.paste(photo_tile(nm, 544, 460, 1.02 + 0.03 * math.sin(t * 0.6 + i), 0, 0), (x + 8, y + 8))
            brackets(d, x, y, 560, 560, a(ACC, 170))
            d.rectangle([x, y + 476, x + 560, y + 552], fill=(9, 12, 18, 248))
            d.text((x + 18, y + 488), tt, font=F(RUSSO, 22), fill=a(TXT, 255))
            d.text((x + 18, y + 520), sub, font=F(MONO, 15), fill=a(ACC, 235))
            d.text((x + 536, y + 20), f"0{i+1}", font=F(MONO, 17), fill=a(ACC, 220), anchor="ra")

        # нижняя лента итога
        pp = c01((l - 1.6) / 0.6)
        if pp > 0:
            d.rectangle([40, 846, 1640, 928], fill=(10, 15, 22, 246), outline=a(ACC, 120))
            d.text((66, 866), "В КОМПЛЕКТЕ: НАУШНИКИ • ОГОЛОВЬЕ • АДАПТЕРЫ НА ШЛЕМ • КАБЕЛИ • СУМКА",
                   font=F(MONO, 19), fill=a(TXT, 255 * eout(pp)))


# ═══════════════════════════ СЦЕНА 2 ═══════════════════════════
def scene2(base, ov, d, t, l):
    if l < 5.7:                                   # радар
        d.rectangle([0, 96, 900, 520], fill=(6, 9, 14, 205))
        d.rectangle([0, 96, 8, 520], fill=a(WARN, 255))
        kicker(d, 46, 118, "ИНТЕГРАЦИЯ С ДЕТЕКТОРАМИ", WARN)
        d.text((46, 166), "КОНТРОЛЬ НЕБА", font=fit("КОНТРОЛЬ НЕБА", RUSSO, 62, 820), fill=a(TXT, 255))
        d.text((46, 244), "тревога приходит прямо в ухо оператора", font=F(MONO, 20), fill=a(DIM, 245))

        # радар
        cx, cy, R = 1420, 560, 300
        o = ov
        dd = d
        dd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(4, 10, 12, 225), outline=a(ACC, 110), width=2)
        for k in (0.33, 0.66):
            dd.ellipse([cx - R * k, cy - R * k, cx + R * k, cy + R * k], outline=a(ACC, 70), width=1)
        dd.line([(cx - R, cy), (cx + R, cy)], fill=a(ACC, 55))
        dd.line([(cx, cy - R), (cx, cy + R)], fill=a(ACC, 55))
        ang = -math.pi / 2 + (l * 1.5) % (2 * math.pi)
        sweep = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sw = ImageDraw.Draw(sweep)
        for i in range(26):
            aa = ang - i * 0.035
            sw.line([(cx, cy), (cx + math.cos(aa) * R, cy + math.sin(aa) * R)],
                    fill=a(ACC, 120 - i * 4), width=3)
        ov.alpha_composite(sweep.filter(ImageFilter.GaussianBlur(3)))
        dd.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=a(ACC, 255))
        for k, (bx, by, ph) in enumerate([(-160, -120, 0.4), (120, -190, 1.9), (210, 90, 3.1), (-70, 200, 2.4)]):
            on = ((l + ph) % 3.0) < 1.4
            rr = 7 if on else 3
            dd.ellipse([cx + bx - rr, cy + by - rr, cx + bx + rr, cy + by + rr],
                       fill=a(WARN, 240) if on else a(ACC, 90))
            if on:
                dd.text((cx + bx + 14, cy + by - 9), f"UAV-0{k+1}", font=F(MONO, 13), fill=a(WARN, 220))
        dd.text((cx, cy + R + 24), "СЕКТОР 360°  //  ДАЛЬНОСТЬ 30–50 М", font=F(MONO, 15),
                fill=a(ACC, 220), anchor="ma")

        # карточка тревоги
        pp = c01((l - 1.2) / 0.5)
        if pp > 0:
            ax = int(46 + (1 - eout(pp)) * -40)
            d.rectangle([ax, 600, ax + 760, 782], fill=(20, 14, 6, 240), outline=a(WARN, 200), width=2)
            d.rectangle([ax, 600, ax + 8, 782], fill=a(WARN, 255))
            d.text((ax + 26, 618), "⚠  ТРЕВОГА", font=F(RUSSO, 26), fill=a(WARN, 255))
            d.text((ax + 26, 660), "«БУЛАТ v.4»  →  НАУШНИКИ «ПЁТР»", font=F(MONO, 21), fill=a(TXT, 255))
            d.text((ax + 26, 700), "ЗАДЕРЖКА < 1 с     ЗВУКОВОЕ ОПОВЕЩЕНИЕ     БЕЗ ОТВЛЕЧЕНИЯ ОПЕРАТОРА",
                   font=F(MONO, 14), fill=a(DIM, 240))

        waveform(d, 46, 818, 760, 90, t, ACC, 120, 56, 1.1)
        d.text((46, 916), "СИГНАЛ В РЕАЛЬНОМ ВРЕМЕНИ", font=F(MONO, 14), fill=a(DIM, 200))

    elif l < 11.1:                                # макро кнопки
        kicker(d, 46, 112, "РЕЖИМЫ СЛУХА", WARN)
        d.text((46, 160), "ПЕРЕКЛЮЧЕНИЕ НА ОЩУПЬ", font=fit("ПЕРЕКЛЮЧЕНИЕ НА ОЩУПЬ", RUSSO, 46, 900),
               fill=a(TXT, 255))
        d.text((46, 224), "три режима, не снимая перчаток", font=F(MONO, 19), fill=a(DIM, 240))

        # полоса частотных профилей
        d.rectangle([46, 258, 700, 292], fill=(10, 15, 22, 240), outline=a(LINE, 255))
        for k in range(46):
            fx = k / 46
            v = 0.30 + 0.62 * math.exp(-((fx - 0.34) ** 2) / 0.020)
            hh = int(v * 24)
            d.rectangle([54 + k * 14, 284 - hh, 54 + k * 14 + 9, 284],
                        fill=a(WARN, 200) if fx < 0.34 else a(LINE, 200))
        d.text((560, 264), "0.3–4 кГц", font=F(MONO, 13), fill=a(WARN, 220))

        modes = [("БПЛА", "усиление частот винтов", WARN),
                 ("БЕРУШИ", "максимум громкости", ACC),
                 ("ПАССИВ", "защита без усиления", ACC2)]
        for i, (nm, sub, col) in enumerate(modes):
            pp = c01((l - 0.5 - i * 0.25) / 0.5)
            if pp <= 0:
                continue
            yy = int(300 + i * 130 + (1 - eout(pp)) * 24)
            d.rectangle([46, yy, 700, yy + 110], fill=(11, 15, 22, 244), outline=a(LINE, 255))
            d.rectangle([46, yy, 52, yy + 110], fill=a(col, 255))
            d.text((76, yy + 18), nm, font=F(RUSSO, 28), fill=a(col, 255))
            d.text((76, yy + 62), sub, font=F(MONO, 16), fill=a(DIM, 240))
            # индикатор
            for k in range(3):
                on = (i == k)
                d.rectangle([600 + k * 32, yy + 46, 622 + k * 32, yy + 66],
                            fill=a(col if on else LINE, 255 if on else 120))

        photo_panel(ov, d, "btn", 780, 300, 700, 404, t, 1.08, label="ПРОРЕЗИНЕННЫЙ БЛОК КНОПОК", idx="03")
        photo_panel(ov, d, "jack", 1520, 300, 360, 250, t, 1.10, label="РАЗЪЁМ", idx="04")
        photo_panel(ov, d, "mic", 1520, 616, 360, 240, t, 1.10, label="МИКРОФОН", idx="05")
        d.rectangle([780, 752, 1480, 864], fill=(9, 13, 19, 246), outline=a(WARN, 130))
        d.rectangle([780, 752, 786, 864], fill=a(WARN, 255))
        d.text((812, 776), "УПРАВЛЕНИЕ ВСЛЕПУЮ", font=F(RUSSO, 26), fill=a(WARN, 250))
        d.text((812, 814), "БЕЗ СНЯТИЯ ПЕРЧАТОК, НА ОЩУПЬ", font=F(MONO, 17), fill=a(TXT, 240))
        d.text((812, 838), "тактильная маркировка режимов на корпусе", font=F(MONO, 14), fill=a(DIM, 230))

    elif l < 17.1:                                # таблица детекторов
        d.rectangle([0, 96, W, 216], fill=(6, 9, 14, 228))
        kicker(d, 40, 112, "СОВМЕСТИМОСТЬ", ACC)
        d.text((40, 152), "РАБОТАЕТ С ДЕТЕКТОРАМИ 3MX",
               font=fit("РАБОТАЕТ С ДЕТЕКТОРАМИ 3MX", RUSSO, 44, 1000), fill=a(TXT, 255))

        cols = [("«БУЛАТ v.4»", "флагманский детектор", "300–8000 МГц"),
                ("«МАРС»", "носимый комплект", "полный диапазон"),
                ("«ТАИР»", "стационарный пост", "круглосуточно")]
        for i, (nm, sub, tag) in enumerate(cols):
            pp = c01((l - 0.2 - i * 0.16) / 0.5)
            if pp <= 0:
                continue
            x = 40 + i * 614
            y = int(262 + (1 - eout(pp)) * 30)
            d.rectangle([x, y, x + 586, y + 268], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([x, y, x + 586, y + 6], fill=a(ACC, 255))
            d.text((x + 26, y + 30), f"0{i+1}", font=F(MONO, 16), fill=a(ACC, 200))
            d.text((x + 26, y + 62), nm, font=F(RUSSO, 34), fill=a(TXT, 255))
            d.text((x + 26, y + 116), sub, font=F(MONO, 17), fill=a(DIM, 240))
            d.text((x + 26, y + 154), tag, font=F(MONO, 16), fill=a(ACC2, 235))
            d.line([(x + 26, y + 196), (x + 560, y + 196)], fill=a(LINE, 255))
            d.text((x + 26, y + 212), "ПРЯМАЯ ПЕРЕДАЧА ТРЕВОГИ", font=F(MONO, 14), fill=a(ACC, 220))
            # бегущая полоса
            d.rectangle([x + 26, y + 246, x + 26 + int(534 * ((l * 0.5 + i * 0.2) % 1)), y + 251],
                        fill=a(ACC, 90))

        photo_panel(ov, d, "side", 40, 530, 700, 280, t, 1.04, label="3MX «ПЁТР» / ПРОФИЛЬ", idx="04")
        photo_panel(ov, d, "hand", 780, 530, 700, 280, t, 1.04, label="ПОСАДКА НА ГОЛОВУ", idx="05")
        d.rectangle([1520, 530, 1880, 860], fill=(9, 13, 19, 246), outline=a(WARN, 120))
        d.text((1544, 522), "ЗАДЕРЖКА", font=F(MONO, 15), fill=a(DIM, 240))
        d.text((1544, 548), "<1", font=F(RUSSO, 72), fill=a(WARN, 255))
        d.text((1700, 600), "сек", font=F(MONO, 22), fill=a(WARN, 240))
        d.line([(1544, 660), (1856, 660)], fill=a(LINE, 255))
        d.text((1544, 680), "ДАЛЬНОСТЬ", font=F(MONO, 15), fill=a(DIM, 240))
        d.text((1544, 706), "30–50", font=F(RUSSO, 44), fill=a(TXT, 255))
        d.text((1544, 790), "метров", font=F(MONO, 18), fill=a(DIM, 240))

    elif l < 20.7:                                # макро разъём / PTT
        kicker(d, 46, 112, "ПОДКЛЮЧЕНИЕ К РАЦИИ", ACC2)
        d.text((46, 160), "ШТАТНЫЙ PTT", font=fit("ШТАТНЫЙ PTT", RUSSO, 52, 760), fill=a(TXT, 255))
        d.text((46, 226), "работа с внешней радиостанцией", font=F(MONO, 19), fill=a(DIM, 240))
        lines = [("РАЗЪЁМ", "быстросъёмный, гарнитурный"),
                 ("КАНАЛ", "дуплекс + внешний PTT"),
                 ("СОВМЕСТИМОСТЬ", "штатные армейские рации")]
        for i, (k, v) in enumerate(lines):
            pp = c01((l - 0.4 - i * 0.18) / 0.5)
            if pp <= 0:
                continue
            yy = int(320 + i * 120 + (1 - eout(pp)) * 20)
            d.rectangle([46, yy, 740, yy + 100], fill=(11, 15, 22, 244), outline=a(LINE, 255))
            d.rectangle([46, yy, 51, yy + 100], fill=a(ACC2, 255))
            d.text((72, yy + 16), k, font=F(RUSSO, 19), fill=a(ACC2, 245))
            d.text((72, yy + 50), v, font=F(MONO, 17), fill=a(TXT, 255 * eout(pp)))
        photo_panel(ov, d, "jack", 800, 300, 680, 460, t, 1.10, label="ГАРНИТУРНЫЙ РАЗЪЁМ", idx="06")
        photo_panel(ov, d, "mic", 1500, 300, 380, 460, t, 1.10, label="МИКРОФОН", idx="07")

    else:                                         # 20.7–25.7 bluetooth
        kicker(d, 46, 112, "НАСТРОЙКА", ACC2)
        d.text((46, 160), "ПРИЛОЖЕНИЕ 3MX", font=fit("ПРИЛОЖЕНИЕ 3MX", RUSSO, 54, 860), fill=a(TXT, 255))
        d.text((46, 228), "Bluetooth 5.0 — до 50 метров", font=F(MONO, 22), fill=a(ACC2, 245))

        cards = [("BT 5.0", "дальность до 50 м"), ("ПРОШИВКА", "обновление по воздуху"),
                 ("ЭКВАЛАЙЗЕР", "профили под задачу")]
        for i, (nm, sub) in enumerate(cards):
            pp = c01((l - 0.3 - i * 0.18) / 0.5)
            if pp <= 0: continue
            yy = int(330 + i * 128 + (1 - eout(pp)) * 22)
            d.rectangle([46, yy, 720, yy + 108], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([46, yy, 52, yy + 108], fill=a(ACC, 255))
            d.text((76, yy + 18), nm, font=F(RUSSO, 26), fill=a(TXT, 255))
            d.text((76, yy + 58), sub, font=F(MONO, 16), fill=a(DIM, 240))
        photo_panel(ov, d, "set", 790, 300, 1080, 560, t, 1.05, label="ПОЛНЫЙ КОМПЛЕКТ 3MX «ПЁТР»", idx="08")


# ═══════════════════════════ СЦЕНА 3 ═══════════════════════════
def scene3(base, ov, d, t, l):
    if l < 5.9:                                   # сеть абонентов
        d.rectangle([0, 96, 860, 470], fill=(6, 9, 14, 205))
        d.rectangle([0, 96, 8, 470], fill=a(ACC, 255))
        kicker(d, 46, 118, "ЗАКРЫТЫЙ ИНТЕРКОМ", ACC)
        d.text((46, 166), "ГРУППА БЕЗ РАЦИИ", font=fit("ГРУППА БЕЗ РАЦИИ", RUSSO, 56, 790), fill=a(TXT, 255))
        d.text((46, 240), "четверо говорят одновременно", font=F(MONO, 20), fill=a(DIM, 245))

        cx, cy = 1400, 590
        # связи
        nodes = [(-300, -170), (300, -170), (-300, 190), (300, 190)]
        for i, (nx, ny) in enumerate(nodes):
            act = ((l * 0.9 + i * 0.55) % 2.4) < 0.9
            col = ACC if act else ACC2
            # пунктир
            steps = 26
            for k in range(steps):
                if (k + int(l * 18)) % 2 == 0:
                    x1 = cx + nx * k / steps; y1 = cy + ny * k / steps
                    x2 = cx + nx * (k + 1) / steps; y2 = cy + ny * (k + 1) / steps
                    d.line([(x1, y1), (x2, y2)], fill=a(col, 150 if act else 70), width=3)
            d.ellipse([cx + nx - 54, cy + ny - 54, cx + nx + 54, cy + ny + 54],
                      fill=(9, 14, 20, 246), outline=a(col, 210), width=2)
            d.text((cx + nx, cy + ny - 8), f"0{i+1}", font=F(RUSSO, 26), fill=a(TXT, 255), anchor="mm")
            d.ellipse([cx + nx + 38, cy + ny - 46, cx + nx + 52, cy + ny - 32],
                      fill=a(col, 255) if act else a(LINE, 255))

        # хаб
        pulse = 54 + 6 * math.sin(l * 3)
        d.ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], fill=(10, 22, 26, 250),
                  outline=a(ACC, 240), width=3)
        d.text((cx, cy - 10), "AES", font=F(RUSSO, 24), fill=a(ACC, 255), anchor="mm")
        d.text((cx, cy + 18), "256", font=F(MONO, 18), fill=a(TXT, 255), anchor="mm")
        d.text((cx, cy + 330), "ДО 4 АБОНЕНТОВ ОДНОВРЕМЕННО", font=F(MONO, 16), fill=a(ACC, 220), anchor="mm")

        d.rectangle([46, 300, 800, 500], fill=(8, 12, 18, 238), outline=a(ACC2, 90))
        d.text((66, 316), "ШИФРОВАННЫЙ ПОТОК", font=F(MONO, 14), fill=a(ACC2, 200))
        hex_stream(d, 66, 348, 700, 140, t, 5, ACC2, 105, 14)
        d.rectangle([46, 520, 800, 600], fill=(9, 13, 19, 240), outline=a(ACC, 110))
        d.text((66, 538), "ПЕРЕХВАТ СНАРУЖИ НЕВОЗМОЖЕН", font=F(MONO, 18), fill=a(ACC, 245))
        d.text((66, 568), "шифрование потока AES-256", font=F(MONO, 14), fill=a(DIM, 240))

    elif l < 11.4:                                # частоты
        d.rectangle([0, 96, W, 236], fill=(6, 9, 14, 228))
        kicker(d, 40, 112, "РАБОЧИЕ ЧАСТОТЫ", ACC)
        d.text((40, 152), "864 / 915 МГц", font=fit("864 / 915 МГц", RUSSO, 50, 900), fill=a(TXT, 255))
        d.text((40, 212) if False else (1000, 178), "опционально 850–930 МГц", font=F(MONO, 18), fill=a(DIM, 240))

        # спектр
        bx0, by0, bw, bh = 40, 280, 1840, 380
        d.rectangle([bx0, by0, bx0 + bw, by0 + bh], fill=(7, 11, 16, 246), outline=a(LINE, 255))
        for k in range(9):
            yy = by0 + bh - k * bh / 8
            d.line([(bx0, yy), (bx0 + bw, yy)], fill=a(LINE, 90))
            d.text((bx0 + 12, yy - 18), f"{-k*8}dB", font=F(MONO, 12), fill=a(DIM, 120))
        nbar = 92
        for i in range(nbar):
            fx = i / nbar
            base = 0.30 + 0.36 * math.exp(-((fx - 0.30) ** 2) / 0.012) + 0.30 * math.exp(-((fx - 0.72) ** 2) / 0.010)
            v = base * (0.72 + 0.28 * math.sin(t * 5 + i * 0.7) * math.cos(t * 1.7 + i * 0.23))
            v = clamp(v, 0.03, 1.0)
            hh = int(v * (bh - 30))
            xx = bx0 + 16 + i * ((bw - 32) / nbar)
            col = ACC if abs(fx - 0.5) > 0.25 else ACC2
            d.rectangle([xx, by0 + bh - 16 - hh, xx + (bw - 32) / nbar - 4, by0 + bh - 16], fill=a(col, 205))
        # маркеры частот
        for fxp, lbl in ((0.30, "864 МГц"), (0.72, "915 МГц")):
            xx = bx0 + 16 + fxp * (bw - 32)
            d.line([(xx, by0 + 10), (xx, by0 + bh - 16)], fill=a(WARN, 210), width=2)
            d.rectangle([xx - 60, by0 + 12, xx + 60, by0 + 42], fill=(24, 18, 6, 240), outline=a(WARN, 200))
            d.text((xx, by0 + 20), lbl, font=F(MONO, 16), fill=a(WARN, 255), anchor="ma")

        d.text((40, 700), "УЗКИЕ КАНАЛЫ В ЛИЦЕНЗИОННОМ ДИАПАЗОНЕ — ПОМЕХОЗАЩИЩЁННОСТЬ ВЫШЕ",
               font=F(MONO, 17), fill=a(DIM, 240))
        photo_panel(ov, d, "side", 40, 686, 460, 232, t, 1.05, label="АНТЕННЫЙ МОДУЛЬ")
        photo_panel(ov, d, "three", 520, 686, 460, 232, t, 1.05, label="КОРПУС")
        d.rectangle([1000, 686, 1880, 918], fill=(9, 13, 19, 242), outline=a(ACC, 120))
        d.text((1024, 706), "ШИФРОВАНИЕ", font=F(MONO, 15), fill=a(DIM, 240))
        d.text((1024, 730), "AES-256", font=F(RUSSO, 56), fill=a(ACC, 255))
        d.text((1024, 806), "ключ обновляется, поток закрыт", font=F(MONO, 17), fill=a(TXT, 240))
        d.text((1024, 838), "перехват и прослушивание исключены", font=F(MONO, 15), fill=a(DIM, 230))

    elif l < 17.1:                                # дальность
        kicker(d, 46, 112, "ДАЛЬНОСТЬ СВЯЗИ", ACC)
        d.text((46, 160), "50 / 100 МЕТРОВ", font=fit("50 / 100 МЕТРОВ", RUSSO, 54, 820), fill=a(TXT, 255))
        d.text((46, 228), "уверенно в лесу и в городской застройке", font=F(MONO, 19), fill=a(DIM, 240))

        # дуги дальности
        cx, cy = 1420, 620
        for i, (rr, lbl) in enumerate([(120, "25 м"), (200, "50 м"), (290, "100 м")]):
            prog = c01((l - 0.2 - i * 0.25) / 0.7)
            if prog <= 0: continue
            ext = int(180 * eout(prog))
            d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=200, end=340, fill=a(ACC, 220), width=3)
            ang = math.radians(200 + ext * 0.78)
            d.text((cx + math.cos(ang) * (rr + 24), cy + math.sin(ang) * (rr + 24)), lbl,
                   font=F(MONO, 15), fill=a(ACC, 220), anchor="mm")
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=a(ACC, 255))
        d.arc([cx - 290, cy - 290, cx + 290, cy + 290], start=200, end=340, fill=a(LINE, 255), width=2)

        stats = [("ОПТИМАЛЬНО", "50 м", ACC), ("МАКСИМУМ", "100 м", ACC2)]
        for i, (k, v, col) in enumerate(stats):
            yy = 380 + i * 170
            d.rectangle([46, yy, 700, yy + 140], fill=(10, 15, 22, 246), outline=a(LINE, 255))
            d.rectangle([46, yy, 52, yy + 140], fill=a(col, 255))
            d.text((78, yy + 20), k, font=F(MONO, 16), fill=a(DIM, 240))
            d.text((78, yy + 46), v, font=F(RUSSO, 58), fill=a(col, 255))

        photo_panel(ov, d, "side", 740, 380, 560, 380, t, 1.06, label="ПРОФИЛЬ КОРПУСА")

    elif l < 21.7:                                # микрофон
        kicker(d, 46, 112, "МИКРОФОННЫЙ УЗЕЛ", ACC2)
        d.text((46, 160), "СЛЫШНО В ШУМЕ", font=fit("СЛЫШНО В ШУМЕ", RUSSO, 54, 880), fill=a(TXT, 255))
        d.text((46, 228), "выносная штанга, ветрозащита, IP67", font=F(MONO, 19), fill=a(DIM, 240))
        rows = [("ЧУВСТВИТЕЛЬНОСТЬ", "-60 дБВ/Па"), ("ЗАЩИТА", "IP67"), ("ШТАНГА", "регулируемая, 360°")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - 0.4 - i * 0.18) / 0.5)
            if pp <= 0: continue
            yy = int(340 + i * 126 + (1 - eout(pp)) * 20)
            d.rectangle([46, yy, 720, yy + 106], fill=(11, 15, 22, 244), outline=a(LINE, 255))
            d.rectangle([46, yy, 51, yy + 106], fill=a(ACC2, 255))
            d.text((72, yy + 16), k, font=F(RUSSO, 18), fill=a(ACC2, 240))
            d.text((72, yy + 52), v, font=F(MONO, 18), fill=a(TXT, 255 * eout(pp)))
        photo_panel(ov, d, "mic", 780, 250, 1080, 646, t, 1.04, label="ВЕТРОЗАЩИТА И ШТАНГА МИКРОФОНА", idx="09")
        waveform(d, 46, 760, 690, 80, t, ACC2, 110, 48, 1.2)

    else:                                         # комплект / узлы
        kicker(d, 46, 112, "КОНСТРУКЦИЯ", ACC)
        d.text((46, 160), "УЗЛЫ И МАТЕРИАЛЫ", font=fit("УЗЛЫ И МАТЕРИАЛЫ", RUSSO, 50, 900), fill=a(TXT, 255))
        photo_panel(ov, d, "case", 46, 250, 560, 420, t, 1.05, label="КЕЙС-СУМКА", idx="10")
        photo_panel(ov, d, "pouch", 626, 250, 560, 420, t, 1.05, label="МОДУЛЬНЫЕ ЯЧЕЙКИ", idx="11")
        photo_panel(ov, d, "bag", 1206, 250, 660, 420, t, 1.05, label="ТРАНСПОРТИРОВКА", idx="12")

        d.rectangle([46, 730, 1866, 966], fill=(9, 13, 19, 246), outline=a(ACC, 110))
        d.text((76, 750), "МЕТАЛЛ, ПОЛИМЕР, СЪЁМНЫЕ ЭЛЕМЕНТЫ", font=F(RUSSO, 24), fill=a(TXT, 255))
        for i, (k, v) in enumerate([("ОГОЛОВЬЕ", "регулируемое"), ("АДАПТЕРЫ", "на рельсы шлема"),
                                    ("ПИТАНИЕ", "2×AAA"), ("МАССА", "413 г")]):
            x = 80 + i * 440
            d.text((x, 806), k, font=F(MONO, 15), fill=a(DIM, 230))
            d.text((x, 834), v, font=F(RUSSO, 26), fill=a(ACC, 250))


# ═══════════════════════════ СЦЕНА 4 ═══════════════════════════
def scene4(base, ov, d, t, l):
    if l < 5.0:                                   # питание
        d.rectangle([0, 96, 960, 560], fill=(6, 9, 14, 210))
        d.rectangle([0, 96, 8, 560], fill=a(ACC, 255))
        kicker(d, 46, 118, "ПИТАНИЕ", ACC)
        d.text((46, 166), "ДО 50 ЧАСОВ", font=fit("ДО 50 ЧАСОВ", RUSSO, 76, 880), fill=a(TXT, 255))
        d.text((46, 268), "две батарейки AAA — и никакой зарядки в поле", font=F(MONO, 20), fill=a(DIM, 245))

        # счётчик
        p = eout(c01((l - 0.3) / 1.6))
        num = int(50 * p)
        d.text((46, 340), f"{num:02d}", font=F(RUSSO, 150), fill=a(ACC, 255))
        d.text((300, 420), "часов", font=F(MONO, 26), fill=a(DIM, 240))
        d.rectangle([46, 524, 900, 540], fill=(15, 22, 32, 240))
        d.rectangle([46, 524, 46 + int(854 * p), 540], fill=a(ACC, 255))

        # блок выработки ресурса
        d.rectangle([46, 590, 1010, 940], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((72, 612), "РЕСУРС ПО ЧАСАМ", font=F(MONO, 15), fill=a(DIM, 235))
        tasks = [("ПАТРУЛЬ", 0.55, "12 ч"), ("ДЕЖУРСТВО", 0.80, "24 ч"), ("ПОЛНЫЙ РЕСУРС", 1.0, "50 ч")]
        for i, (nm, frac, lbl) in enumerate(tasks):
            pp = eout(c01((l - 0.55 - i * 0.22) / 0.8))
            yy = 652 + i * 84
            d.text((72, yy), nm, font=F(MONO, 16), fill=a(TXT, 240))
            d.text((920, yy), lbl, font=F(RUSSO, 20), fill=a(ACC, 255 * pp), anchor="ra")
            d.rectangle([72, yy + 28, 920, yy + 46], fill=(14, 20, 30, 255))
            bw = int(848 * frac * pp)
            d.rectangle([72, yy + 28, 72 + bw, yy + 46], fill=a(ACC, 230))
            for k in range(10):
                xx = 72 + k * 84.8
                d.line([(xx, yy + 28), (xx, yy + 46)], fill=a((10, 13, 20), 255), width=2)
        d.text((72, 906), "2 × AAA 1.5 В  •  ЗАМЕНА БЕЗ ИНСТРУМЕНТОВ", font=F(MONO, 15), fill=a(DIM, 225))

        photo_panel(ov, d, "batt", 1064, 340, 806, 556, t, 1.06, label="ОТСЕК ПИТАНИЯ 2×AAA", idx="13")

    elif l < 10.0:                                # среда
        kicker(d, 46, 112, "УСЛОВИЯ ЭКСПЛУАТАЦИИ", ACC2)
        d.text((46, 160), "ОТ –20 ДО +40 °C", font=fit("ОТ –20 ДО +40 °C", RUSSO, 52, 1000), fill=a(TXT, 255))
        d.text((46, 228), "IP66 на наушниках, IP67 на микрофоне", font=F(MONO, 19), fill=a(DIM, 240))

        # температурная шкала
        gx, gy, gw = 46, 340, 1820
        d.rectangle([gx, gy, gx + gw, gy + 74], fill=(10, 15, 22, 246), outline=a(LINE, 255))
        for i in range(7):
            xx = gx + 30 + i * (gw - 60) / 6
            d.line([(xx, gy + 40), (xx, gy + 74)], fill=a(LINE, 255), width=2)
            d.text((xx, gy + 82), f"{-20 + i*10}", font=F(MONO, 15), fill=a(DIM, 230), anchor="ma")
        p = eout(c01((l - 0.4) / 1.4))
        d.rectangle([gx + 30, gy + 26, gx + 30 + int((gw - 60) * p), gy + 40],
                    fill=a(ACC, 200))
        # маркер
        mx = gx + 30 + int((gw - 60) * p)
        d.polygon([(mx, gy + 12), (mx - 12, gy - 4), (mx + 12, gy - 4)], fill=a(ACC, 255))

        ip = [("IP66", "наушники: пыль и струи воды", ACC),
              ("IP67", "микрофон: кратковременное погружение", ACC2)]
        for i, (k, v, col) in enumerate(ip):
            pp = c01((l - 0.7 - i * 0.2) / 0.5)
            if pp <= 0: continue
            x = 46 + i * 920
            d.rectangle([x, 500, x + 880, 660], fill=(10, 15, 22, 246), outline=a(col, 130))
            d.text((x + 28, 520), k, font=F(RUSSO, 54), fill=a(col, 255))
            d.text((x + 28, 596), v, font=F(MONO, 17), fill=a(TXT, 240))

        photo_panel(ov, d, "case", 46, 676, 880, 222, t, 1.04, label="ТАКТИЧЕСКИЙ КЕЙС")
        photo_panel(ov, d, "set", 966, 676, 900, 222, t, 1.04, label="РАБОЧИЙ КОМПЛЕКТ")

    elif l < 15.0:                                # крепления
        kicker(d, 46, 112, "УСТАНОВКА", ACC)
        d.text((46, 160), "НА ШЛЕМ ЗА СЕКУНДЫ", font=fit("НА ШЛЕМ ЗА СЕКУНДЫ", RUSSO, 50, 1000), fill=a(TXT, 255))
        photo_panel(ov, d, "hand", 46, 240, 560, 452, t, 1.05, label="ОГОЛОВЬЕ / РЕГУЛИРОВКА", idx="14")
        photo_panel(ov, d, "kit2", 656, 240, 560, 452, t, 1.05, label="АДАПТЕРЫ И КАБЕЛИ", idx="15")
        photo_panel(ov, d, "set", 1266, 240, 600, 452, t, 1.05, label="В СБОРЕ", idx="16")

        d.rectangle([46, 772, 1866, 946], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        for i, (k, v) in enumerate([("КРЕПЛЕНИЕ", "рельсы шлема"), ("ОГОЛОВЬЕ", "в комплекте"),
                                    ("МАССА", "413 г с батареями"), ("ПОДГОНКА", "без инструментов")]):
            x = 76 + i * 448
            d.text((x, 796), k, font=F(MONO, 15), fill=a(DIM, 225))
            d.text((x, 826), v, font=F(RUSSO, 26), fill=a(TXT, 255))
            d.rectangle([x, 876, x + 380, 880], fill=a(ACC, 70))

    elif l < 21.0:                                # вес / эргономика
        kicker(d, 46, 112, "ЭРГОНОМИКА", ACC2)
        d.text((46, 160), "413 ГРАММОВ", font=fit("413 ГРАММОВ", RUSSO, 62, 1000), fill=a(TXT, 255))
        d.text((46, 232), "с батареями — без перегруза шеи", font=F(MONO, 19), fill=a(DIM, 240))
        photo_panel(ov, d, "hero", 46, 300, 820, 620, t, 1.05, label="ПОСАДКА И БАЛАНС", idx="16")

        # весы / шкала массы
        pp = eout(c01((l - 0.3) / 1.5))
        d.rectangle([920, 300, 1866, 560], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((950, 322), "МАССА", font=F(MONO, 16), fill=a(DIM, 235))
        d.text((950, 350), f"{int(413*pp)} г", font=F(RUSSO, 72), fill=a(ACC, 255))
        d.text((950, 448), "с батареями", font=F(MONO, 16), fill=a(DIM, 230))
        d.rectangle([950, 496, 1836, 512], fill=(15, 22, 32, 240))
        d.rectangle([950, 496, 950 + int(886 * pp * 0.72), 512], fill=a(ACC, 255))

        d.rectangle([920, 590, 1866, 920], fill=(9, 13, 19, 246), outline=a(LINE, 255))
        d.text((950, 612), "БАЛАНС", font=F(MONO, 16), fill=a(DIM, 235))
        for i, txt in enumerate(["прижим регулируется", "аэрация амбушюр", "совместимость со шлемом",
                                 "микрофон не мешает прикладу"]):
            d.text((950, 648 + i * 62), "—", font=F(RUSSO, 20), fill=a(ACC, 255))
            d.text((980, 650 + i * 62), txt, font=F(MONO, 18), fill=a(TXT, 240))

    else:                                         # финал
        p = eout(c01((l - 0.2) / 0.9))
        d.rectangle([0, 200, W, 900], fill=(5, 8, 13, 225))
        d.rectangle([0, 200, 8, 900], fill=a(ACC, 255))

        f = F(RUSSO, 108)
        d.text((100, 250 + (1 - p) * 20), "3MX «ПЁТР»", font=f, fill=a(TXT, 255 * p))
        d.text((104, 392), "ЗАЩИТА • ДЕТЕКЦИЯ • ИНТЕРКОМ", font=F(RUSSO, 34), fill=a(ACC, 255 * p))

        d.line([(104, 470), (104 + 1200 * p, 470)], fill=a(ACC, 180), width=2)

        p2 = c01((l - 0.7) / 0.8)
        d.text((104, 510), "ПОДПИСЫВАЙТЕСЬ НА «В ОКОПЕ»", font=F(MONO, 22), fill=a(DIM, 255 * p2))
        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - 1.0 - i * 0.22) / 0.5)
            if pp <= 0: continue
            yy = int(566 + i * 96 + (1 - eout(pp)) * 18)
            d.rectangle([104, yy, 1240, yy + 78], fill=(11, 16, 23, 246), outline=a(ACC, 110))
            d.rectangle([104, yy, 110, yy + 78], fill=a(ACC, 255))
            d.text((134, yy + 14), k, font=F(RUSSO, 20), fill=a(ACC, 255))
            d.text((134, yy + 44), v, font=F(MONO, 17), fill=a(TXT, 240))

        photo_panel(ov, d, "hero", 1330, 250, 520, 520, t, 1.04, label="3MX «ПЁТР»")

        d.text((104, 850), "ТЕХНИЧЕСКИЙ ОБЗОР  //  БЕЗ РЕКЛАМНЫХ ЦЕН  //  ФАКТЫ ИЗ ПАСПОРТА ИЗДЕЛИЯ",
               font=F(MONO, 15), fill=a(DIM, 200))


def intro(base, ov, d, t, l):
    """0–2.6 c: атмосферный пролёт, бренд, затем слэм в титул."""
    p = eout(c01(t / 0.9))
    d.rectangle([0, H // 2 - 150, W, H // 2 + 120], fill=(5, 8, 13, int(200 * p)))
    d.text((W // 2, H // 2 - 92), "«В ОКОПЕ»", font=F(RUSSO, 96), fill=a(TXT, int(255 * c01(t / 0.7))), anchor="ma")
    d.text((W // 2, H // 2 + 20), "ТАКТИЧЕСКАЯ СВЯЗЬ  //  РЭБ  //  ЭКИПИРОВКА",
           font=F(MONO, 22), fill=a(ACC, int(230 * c01((t - 0.4) / 0.7))), anchor="ma")
    w = 520 * eout(c01((t - 0.5) / 0.8))
    d.rectangle([W // 2 - w / 2, H // 2 + 72, W // 2 + w / 2, H // 2 + 75], fill=a(ACC, 220))
    # нарастающая волна снизу
    waveform(d, W // 2 - 380, H - 260, 760, 120, t, ACC, 110, 72, 1.0)


SCENES = [(2.60, scene1), (24.90, scene2), (50.59, scene3), (76.13, scene4)]
TOTAL = 104.06

CUTS = [2.60, 8.20, 13.20, 18.60, 24.90, 30.60, 36.00, 42.00, 46.20,
        50.59, 56.49, 61.99, 67.69, 72.29, 76.13, 81.13, 86.13, 91.13, 97.13]


def render_frame(t):
    # выбор сцены
    if t < 2.60:
        idx = -1
        st, fn = 0.0, intro
        l = t
        name = "hero"
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - 0.001:
                idx = i
        st, fn = SCENES[idx]
        l = t - st

        if idx == 0:
            name = "hero" if l < 5.6 else ("hand" if l < 10.6 else ("kit" if l < 16.0 else "kit2"))
        elif idx == 1:
            name = "hero" if l < 5.7 else ("btn" if l < 11.1 else ("side" if l < 17.1 else ("jack" if l < 20.7 else "kit")))
        elif idx == 2:
            name = "side" if l < 5.9 else ("three" if l < 11.4 else ("hero" if l < 17.1 else ("mic" if l < 21.7 else "kit2")))
        else:
            name = "batt" if l < 5.0 else ("case" if l < 10.0 else ("set" if l < 15.0 else "hero"))

    z0 = 1.02 + 0.012 * math.sin(t * 0.9)
    base = camera(name, l, 6.0, z0, z0 + 0.10, px=0.35 * math.sin(t * 0.13), py=0.18 * math.cos(t * 0.17)).convert("RGBA")

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    section = "ПРЕДСТАВЛЕНИЕ" if idx <= 0 else ["ПРЕДСТАВЛЕНИЕ", "ДЕТЕКЦИЯ БПЛА", "ИНТЕРКОМ AES-256", "ЖЕЛЕЗО И КОМПЛЕКТ"][idx]
    chrome(ov, d, t, TOTAL, section)
    fn(base, ov, d, t, l)

    # мягкое затемнение у нижней кромки
    d.rectangle([0, H - 96, W, H - 96 + 1], fill=(6, 9, 14, 60))

    out = Image.alpha_composite(base, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGNETTE)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])

    # вспышка на монтажных склейках
    for c in CUTS:
        dd = abs(t - c)
        if dd < 0.12:
            k = (1 - dd / 0.12) * 0.22
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), k)

    return out.convert("RGB")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        tt = float(arg)
        fr = render_frame(tt)
        p = os.path.join(BASE, f"frame_{tt:06.2f}.jpg")
        fr.save(p, quality=92)
        print("saved", p)
