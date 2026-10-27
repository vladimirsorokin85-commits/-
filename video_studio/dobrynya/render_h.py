# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // ДРОНОБОЙ «ДОБРЫНЯ» — дульная насадка для АК. Горизонталь 16:9."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FPS = 30
BASE = "/home/user/-/video_studio/dobrynya"
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
    "nose":     "dr_00.jpg",   # насадка, вид со стороны байонета
    "engr":     "dr_01.jpg",   # гравировка 01.030.017 АК12 ДРОБОБОЙ
    "set4":     "dr_02.jpg",   # картриджи в держателях + насадка
    "base":     "dr_03.jpg",   # картридж, металлическое дно, 4 отверстия
    "window":   "dr_04.jpg",   # картридж с окном, видны дробины
    "barrel":   "dr_05.jpg",   # ствол с маркировкой и байонетом
    "kit":      "dr_06.jpg",   # насадка + 4 картриджа
    "rack":     "dr_07.jpg",   # 4 картриджа в ряд
    "single":   "dr_08.jpg",   # один картридж в полный рост
    "compare":  "dr_09.jpg",   # сравнение с патроном 12 калибра
    "fpv":      "dr_10.jpg",   # FPV-дрон рядом со смартфоном
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
    s1 = "//  СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА"
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
    d.text((26, H - 44), "ДРОНОБОЙ «ДОБРЫНЯ»  //  АК-74 И АК-12", font=ff, fill=a(DIM, 235))
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
# ═════════════ сцена 1: представление ═════════════
def scene1(base, ov, d, t, l):
    if l < 6.40:                      # титул
        d.rectangle([0, 296, 1240, 1000], fill=(6, 9, 14, 228))
        d.rectangle([0, 296, 9, 1000], fill=a(ACC, 255))
        kicker(d, 70, 328, "ТЕХНИЧЕСКИЙ ОБЗОР  //  ДОБРЫНЯ", ACC, 26)
        p1 = eout(c01((l - .14) / .50))
        d.text((66, 378 + (1 - p1) * 26), "ДОБРЫНЯ", font=fit("ДОБРЫНЯ", RUSSO, 148, 1140),
               fill=a(TXT, 255 * p1))
        p2 = eout(c01((l - .44) / .44))
        d.text((72, 556 + (1 - p2) * 18), "ДРОНОБОЙ", font=F(RUSSO, 88), fill=a(ACC, 255 * p2))
        d.text((72, 664), "ДЛЯ АК-74 И АК-12", font=F(MONO, 34), fill=a(DIM, 255 * p2))
        p3 = eout(c01((l - .70) / .40))
        d.text((74, 726), "ДУЛЬНАЯ НАСАДКА ПОД ДРОБОВОЙ ВЫСТРЕЛ",
               font=fit("ДУЛЬНАЯ НАСАДКА ПОД ДРОБОВОЙ ВЫСТРЕЛ", RUSSO, 44, 1150), fill=a(TXT, 255 * p3))
        d.text((74, 790), "против FPV-дронов в ближней зоне", font=F(MONO, 30), fill=a(DIM, 245 * p3))

        chips = ["24 ММ", "750 / 800 Г", "ДО 200 ДРОБИН"]
        for i, c in enumerate(chips):
            pp = c01((l - .98 - i * .1) / .40)
            if pp <= 0: continue
            cf = F(MONO, 30); cw = tw(d, c, cf) + 44
            cx = 74 + i * 340
            yy = int(866 + (1 - eout(pp)) * 16)
            d.rounded_rectangle([cx, yy, cx + cw, yy + 60], 2, fill=(11, 16, 24, 242), outline=a(ACC, 130))
            d.text((cx + 22, yy + 15), c, font=cf, fill=a(TXT, 255 * eout(pp)))

        if 1.30 < l < 6.2:
            photo_panel(ov, d, "nose", 1300, 330, 560, 500, t, 1.07, label="ДУЛЬНАЯ НАСАДКА, БАЙОНЕТ")

    elif l < 12.20:                   # мелкая цель
        head(d, "ПРОБЛЕМА", "ЦЕЛЬ ЧУТЬ БОЛЬШЕ СМАРТФОНА", WARN, 100, 60)
        d.text((70, 262), "попасть в такой аппарат одиночной пулей крайне сложно", font=F(MONO, 30), fill=a(DIM, 240))

        photo_panel(ov, d, "fpv", 70, 336, 780, 520, t, 1.05, label="FPV-ДРОН И СМАРТФОН ДЛЯ МАСШТАБА", idx="01")

        rows = [("ГАБАРИТ", "корпус меньше ладони, размах винтов — десятки сантиметров", WARN),
                ("СКОРОСТЬ", "подлёт занимает секунды, прицеливаться некогда", WARN),
                ("ПЛОЩАДЬ", "одна пуля против цели размером с телефон", WARN)]
        for i, (k, v, col) in enumerate(rows):
            pp = c01((l - .25 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(350 + i * 168 + (1 - eout(pp)) * 18)
            d.rectangle([910, yy, 1850, yy + 148], fill=(10, 14, 21, 246), outline=a(col, 130))
            d.rectangle([910, yy, 918, yy + 148], fill=a(col, 255))
            d.text((948, yy + 16), k, font=F(RUSSO, 36), fill=a(col, 255))
            d.text((948, yy + 68), v, font=fit(v, MONO, 26, 860), fill=a(TXT, 240))

    elif l < 18.40:                   # до 200 дробин
        head(d, "РЕШЕНИЕ", "ДО 200 ДРОБИН ЗА ВЫСТРЕЛ", ACC, 100, 62)
        d.text((70, 264), "не одна пуля, а облако дроби — шанс попасть кратно выше", font=F(MONO, 30), fill=a(DIM, 240))

        # схема разлёта
        d.rectangle([70, 340, 1120, 900], fill=(7, 10, 16, 242), outline=a(LINE, 255))
        cx, cy = 250, 620
        pp = eout(c01((l - .20) / 1.3))
        d.rectangle([cx - 26, cy - 120, cx + 26, cy + 120], fill=(22, 28, 36, 255), outline=a(DIM, 200), width=3)
        d.text((cx, cy + 148), "ДУЛЬНЫЙ СРЕЗ", font=F(MONO, 26), fill=a(DIM, 225), anchor="ma")
        import math as _m
        for i in range(64):
            ang = (-1 + 2 * (i / 63.0)) * 0.55
            dist = 120 + int((0.35 + 0.65 * ((i * 37) % 100) / 100.0) * 380 * pp)
            x2 = cx + 30 + int(_m.cos(ang) * dist)
            y2 = cy + int(_m.sin(ang) * dist * 0.86)
            r = 3 if i % 3 else 5
            d.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=a(ACC if i % 2 else ACC2, 210))
        # плашка под подписи (справа от схемы разлёта)
        d.rectangle([712, 360, 1110, 690], fill=(6, 9, 14, 246), outline=a(ACC, 120))
        d.rectangle([712, 360, 717, 690], fill=a(ACC, 255))
        d.text((740, 384), "ДРОБЬ", font=F(MONO, 26), fill=a(ACC, 235))
        d.text((740, 420), "до 200", font=F(RUSSO, 50), fill=a(TXT, 255))
        d.text((740, 480), "дробин", font=F(RUSSO, 50), fill=a(TXT, 255))
        d.text((740, 572), "облако перекрывает", font=F(MONO, 26), fill=a(DIM, 235))
        d.text((740, 610), "цель целиком", font=F(MONO, 26), fill=a(DIM, 235))

        photo_panel(ov, d, "compare", 1180, 340, 680, 500, t, 1.04,
                    label="КАРТРИДЖ «ДОБРЫНИ» И ПАТРОН 12 КАЛИБРА", idx="02")

    else:                             # автомат остаётся автоматом
        head(d, "СМЫСЛ КОНСТРУКЦИИ", "АВТОМАТ ОСТАЁТСЯ АВТОМАТОМ", ACC2, 100, 56)
        d.text((70, 258), "насадка не меняет оружие — она дополняет его", font=F(MONO, 30), fill=a(DIM, 240))

        items = [("01", "НАКРУТИЛ", "вместо штатного пламегасителя"),
                 ("02", "ВЫСТРЕЛИЛ", "штатным боевым патроном"),
                 ("03", "СРАБОТАЛ", "картридж ушёл в цель дробью")]
        for i, (num, k, s) in enumerate(items):
            pp = c01((l - .20 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(336 + i * 150 + (1 - eout(pp)) * 20)
            d.rectangle([70, yy, 1090, yy + 130], fill=(11, 16, 23, 246), outline=a(LINE, 255))
            d.rectangle([70, yy, 78, yy + 130], fill=a(ACC2, 255))
            d.text((106, yy + 20), num, font=F(RUSSO, 40), fill=a(ACC2, 235))
            d.text((186, yy + 18), k, font=F(RUSSO, 38), fill=a(TXT, 255))
            d.text((186, yy + 72), s, font=F(MONO, 28), fill=a(DIM, 240))

        d.rectangle([70, 812, 1090, 900], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((102, 832), "ШТАТНЫЕ ПАТРОНЫ, ШТАТНЫЙ РЕЖИМ ОГНЯ", font=F(RUSSO, 32), fill=a(ACC, 250))
        d.text((102, 872), "никаких переделок оружия", font=F(MONO, 26), fill=a(DIM, 235))

        photo_panel(ov, d, "kit", 1160, 300, 700, 560, t, 1.05, label="НАСАДКА И ЧЕТЫРЕ КАРТРИДЖА В ДЕРЖАТЕЛЯХ")


# ═════════════ сцена 2: технические характеристики ═════════════
def scene2(base, ov, d, t, l):
    if l < 7.60:                      # калибр и диаметр
        head(d, "ТАКТИКО-ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ", "КАЛИБР И СЕЧЕНИЕ", ACC, 100, 58)

        d.rectangle([70, 300, 1000, 900], fill=(7, 10, 16, 242), outline=a(LINE, 255))
        cx, cy, R = 320, 600, 180
        pp = eout(c01((l - .20) / 1.1))
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=a(ACC, 240), width=5)
        d.ellipse([cx - R + 26, cy - R + 26, cx + R - 26, cy + R - 26], outline=a(ACC, 90), width=2)
        d.line([(cx - R - 40, cy), (cx + R + 40, cy)], fill=a(WARN, 180), width=2)
        d.text((cx, cy - 34), "24", font=F(RUSSO, 78), fill=a(TXT, 255), anchor="ma")
        d.text((cx, cy + 44), "ММ", font=F(MONO, 30), fill=a(ACC, 235), anchor="ma")
        d.text((cx, cy + R + 30), "ВНУТРЕННИЙ ДИАМЕТР", font=F(MONO, 28), fill=a(DIM, 230), anchor="ma")

        rows = [("КАЛИБР", "5,45 × 39 мм"), ("ДИАМЕТР КАНАЛА", "24 мм"),
                ("ПОД ПАТРОН", "штатный ПсГс"), ("ВЫСТРЕЛ", "дробовой картридж")]
        for i, (k, v) in enumerate(rows):
            pp2 = c01((l - .25 - i * .14) / .5)
            if pp2 <= 0: continue
            yy = int(330 + i * 140 + (1 - eout(pp2)) * 18)
            row2(d, 1090, yy, 760, k, v, ACC, 120, 34, 30)

    elif l < 15.00:                   # масса
        head(d, "МАССА", "750 / 800 ГРАММОВ", ACC2, 100, 64)
        d.text((70, 262), "масса насадки: АК-74 и АК-12, плюс снаряжённый картридж", font=F(MONO, 30), fill=a(DIM, 240))

        blocks = [("АК-74", 750, ACC), ("АК-12", 800, ACC2)]
        for i, (nm, v, col) in enumerate(blocks):
            pp = eout(c01((l - .20 - i * .22) / .8))
            yy = 336 + i * 190
            d.text((70, yy), nm, font=F(MONO, 30), fill=a(DIM, 235))
            d.text((70, yy + 34), f"{int(v * pp)} г", font=F(RUSSO, 84), fill=a(col, 255))
            d.rectangle([70, yy + 148, 70 + 620, yy + 162], fill=(16, 22, 30, 255))
            d.rectangle([70, yy + 148, 70 + int(620 * (v / 1000) * pp), yy + 162], fill=a(col, 235))

        d.rectangle([70, 740, 690, 860], fill=(10, 15, 22, 246), outline=a(ACC, 140))
        d.text((104, 762), "ЗАРЯЖЕННЫЙ КАРТРИДЖ", font=F(MONO, 26), fill=a(DIM, 235))
        d.text((104, 796), "135 Г", font=F(RUSSO, 54), fill=a(ACC, 255))

        photo_panel(ov, d, "single", 760, 336, 520, 520, t, 1.05, label="КАРТРИДЖ В СБОРЕ", idx="03")

        d.rectangle([1330, 336, 1850, 856], fill=(9, 13, 19, 242), outline=a(LINE, 255))
        d.text((1364, 362), "МАТЕРИАЛ", font=F(MONO, 26), fill=a(DIM, 235))
        d.text((1364, 402), "КОНСТРУКЦИОННАЯ", font=fit("КОНСТРУКЦИОННАЯ", RUSSO, 32, 450), fill=a(TXT, 255))
        d.text((1364, 446), "СТАЛЬ", font=F(RUSSO, 48), fill=a(TXT, 255))
        d.text((1364, 512), "покрытие —", font=F(MONO, 28), fill=a(DIM, 235))
        d.text((1364, 552), "ВОРОНЕНИЕ", font=F(RUSSO, 44), fill=a(ACC2, 255))
        d.text((1364, 640), "модульная схема:", font=F(MONO, 26), fill=a(DIM, 230))
        d.text((1364, 678), "ствол", font=F(MONO, 28), fill=a(TXT, 240))
        d.text((1364, 716), "+ резьбовая муфта", font=F(MONO, 28), fill=a(TXT, 240))

    elif l < 22.40:                   # соединение
        head(d, "УСТАНОВКА", "БАЙОНЕТ ИЛИ РЕЗЬБА", ACC, 100, 60)
        d.text((70, 260), "тип соединения зависит от исполнения насадки", font=F(MONO, 30), fill=a(DIM, 240))

        cards = [("БАЙОНЕТ", "быстрая постановка и снятие", ACC, "поворот до упора"),
                 ("24 × 1,5 R", "метрическая резьба", ACC2, "накручивание по резьбе")]
        for i, (k, v, col, sub_) in enumerate(cards):
            pp = c01((l - .20 - i * .22) / .6)
            if pp <= 0: continue
            x = 70 + i * 660
            yy = int(340 + (1 - eout(pp)) * 22)
            d.rectangle([x, yy, x + 620, yy + 400], fill=(10, 14, 21, 246), outline=a(col, 150), width=2)
            d.text((x + 34, yy + 30), k, font=fit(k, RUSSO, 56, 550), fill=a(col, 255))
            d.text((x + 34, yy + 116), v, font=fit(v, MONO, 30, 550), fill=a(TXT, 240))
            d.text((x + 34, yy + 300), sub_, font=F(MONO, 28), fill=a(DIM, 235))

        photo_panel(ov, d, "barrel", 1380, 320, 480, 560, t, 1.05, label="СТВОЛ И МУФТА", idx="04")

        d.rectangle([70, 790, 1330, 900], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((102, 812), "СОВМЕСТИМОСТЬ: АК-12, АК-74 И АНАЛОГИ С ТАКОЙ ЖЕ РЕЗЬБОЙ", font=F(MONO, 30), fill=a(TXT, 245))
        d.text((102, 856), "устанавливается вместо пламегасителя или дульного тормоза", font=F(MONO, 28), fill=a(DIM, 235))

    else:                             # маркировка и совместимость
        head(d, "МАРКИРОВКА", "ЧТО НАПИСАНО НА КОРПУСЕ", ACC2, 100, 56)
        d.text((70, 258), "индекс изделия, тип оружия и производитель", font=F(MONO, 30), fill=a(DIM, 240))

        photo_panel(ov, d, "engr", 70, 330, 900, 500, t, 1.04, label="ГРАВИРОВКА НА СТВОЛЕ", idx="05")

        rows = [("ИНДЕКС", "01.030.017"), ("ТИП", "АК12, дронобой"), ("ИЗГОТОВЛЕНИЕ", "сделано в России")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - .25 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(350 + i * 150 + (1 - eout(pp)) * 18)
            row2(d, 1030, yy, 820, k, v, ACC2, 130, 34, 30)

        d.text((70, 906), "исполнение по программе «Брат»", font=F(MONO, 26), fill=a(DIM, 230))


# ═════════════ сцена 3: механика ═════════════
def scene3(base, ov, d, t, l):
    if l < 7.20:                      # инициирование
        head(d, "МЕХАНИКА", "ВЫСТРЕЛ БОЕВЫМ ПАТРОНОМ", ACC, 100, 58)
        d.text((70, 260), "отдельного запала нет — импульс даёт сам патрон", font=F(MONO, 30), fill=a(DIM, 240))

        # схема: патрон -> импульс -> картридж
        y0 = 420
        d.rectangle([80, y0, 420, y0 + 300], fill=(11, 16, 23, 246), outline=a(ACC2, 140))
        d.text((104, y0 + 24), "ПАТРОН", font=F(MONO, 28), fill=a(ACC2, 240))
        d.text((104, y0 + 74), "ПсГс", font=F(RUSSO, 64), fill=a(TXT, 255))
        d.text((104, y0 + 170), "штатный,", font=F(MONO, 28), fill=a(DIM, 235))
        d.text((104, y0 + 208), "боевой", font=F(MONO, 28), fill=a(DIM, 235))

        pp = eout(c01((l - .35) / .9))
        for k in range(9):
            xx = 450 + k * 62
            if xx < 450 + 380 * pp:
                d.line([(xx, y0 + 150), (xx + 40, y0 + 150)], fill=a(ACC, 200), width=5)
        d.polygon([(846, y0 + 132), (846, y0 + 168), (884, y0 + 150)], fill=a(ACC, 235))

        d.rectangle([900, y0, 1240, y0 + 300], fill=(11, 16, 23, 246), outline=a(WARN, 150))
        d.text((924, y0 + 24), "ИМПУЛЬС", font=F(MONO, 28), fill=a(WARN, 240))
        d.text((924, y0 + 74), "ПЛАМЯ", font=F(RUSSO, 56), fill=a(TXT, 255))
        d.text((924, y0 + 170), "энергия +", font=F(MONO, 28), fill=a(DIM, 235))
        d.text((924, y0 + 208), "пламенный импульс", font=F(MONO, 28), fill=a(DIM, 235))

        for k in range(9):
            xx = 1272 + k * 62
            if xx < 1272 + 340 * pp:
                d.line([(xx, y0 + 150), (xx + 40, y0 + 150)], fill=a(ACC, 200), width=5)
        d.polygon([(1634, y0 + 132), (1634, y0 + 168), (1672, y0 + 150)], fill=a(ACC, 235))

        d.rectangle([1690, y0, 1850, y0 + 300], fill=(11, 16, 23, 246), outline=a(ACC, 150))
        d.text((1712, y0 + 24), "В ЦЕЛЬ", font=F(MONO, 24), fill=a(ACC, 240))
        d.text((1712, y0 + 78), "ДРОБЬ", font=fit("ДРОБЬ", RUSSO, 40, 118), fill=a(TXT, 255))

        d.text((80, 790), "перезаряжать насадку вручную не нужно", font=F(RUSSO, 40), fill=a(ACC, 250))
        d.text((80, 852), "цикл идёт от штатного патрона", font=F(MONO, 30), fill=a(DIM, 235))

    elif l < 13.00:                   # непрерывность огня
        head(d, "НЕПРЕРЫВНОСТЬ ОГНЯ", "СТРЕЛОК НЕ ОТВЛЕКАЕТСЯ", ACC2, 100, 56)
        d.text((70, 258), "никакой отдельной перезарядки между выстрелами", font=F(MONO, 30), fill=a(DIM, 240))

        items = [("БЕЗ ПЕРЕЗАРЯДКИ", "насадка не требует ручной подачи картриджа"),
                 ("БЕЗ ПАУЗЫ", "следующий выстрел — сразу, тем же автоматом"),
                 ("БЕЗ СМЕНЫ ХВАТА", "оружие остаётся в штатном положении")]
        for i, (k, v) in enumerate(items):
            pp = c01((l - .20 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(340 + i * 150 + (1 - eout(pp)) * 18)
            d.rectangle([70, yy, 1120, yy + 130], fill=(11, 16, 23, 246), outline=a(ACC2, 130))
            d.rectangle([70, yy, 78, yy + 130], fill=a(ACC2, 255))
            d.text((110, yy + 18), k, font=fit(k, RUSSO, 36, 900), fill=a(TXT, 255))
            d.text((110, yy + 72), v, font=fit(v, MONO, 28, 960), fill=a(DIM, 240))

        photo_panel(ov, d, "rack", 1180, 320, 680, 500, t, 1.04, label="КАРТРИДЖИ В ДЕРЖАТЕЛЯХ", idx="06")

    elif l < 18.20:                   # остаётся установленной
        head(d, "ПОСЛЕ ВЫСТРЕЛА", "НАСАДКА ОСТАЁТСЯ НА СТВОЛЕ", ACC, 100, 58)
        d.text((70, 262), "устройство не снимается после дробового выстрела", font=F(MONO, 30), fill=a(DIM, 240))

        d.rectangle([70, 350, 1130, 560], fill=(10, 15, 22, 246), outline=a(ACC, 150))
        d.text((104, 376), "ДАЛЬШЕ — ШТАТНЫЕ ПАТРОНЫ", font=F(RUSSO, 42), fill=a(ACC, 255))
        d.text((104, 444), "огонь продолжается в обычном режиме", font=F(MONO, 30), fill=a(TXT, 240))
        d.text((104, 492), "автоматический режим не страдает", font=F(MONO, 30), fill=a(DIM, 235))

        d.rectangle([70, 600, 1130, 810], fill=(10, 15, 22, 246), outline=a(ACC2, 150))
        d.text((104, 626), "ДРОБОВОЙ ВЫСТРЕЛ — ОДИН", font=F(RUSSO, 42), fill=a(ACC2, 255))
        d.text((104, 694), "дальше насадка работает как дульный прибор", font=F(MONO, 30), fill=a(TXT, 240))

        photo_panel(ov, d, "set4", 1190, 350, 670, 460, t, 1.04, label="КАРТРИДЖИ И НАСАДКА", idx="07")

    else:                             # вспышка и звук
        head(d, "ДОПОЛНИТЕЛЬНО", "ВСПЫШКА И ЗВУК", ACC2, 100, 58)
        d.text((70, 262), "побочные эффекты, которые важны в бою", font=F(MONO, 30), fill=a(DIM, 240))

        cards = [("ВСПЫШКА", "яркость выстрела снижается", ACC2),
                 ("АКУСТИКА", "звук выстрела меняется", ACC)]
        for i, (k, v, col) in enumerate(cards):
            pp = c01((l - .20 - i * .20) / .6)
            if pp <= 0: continue
            x = 70 + i * 640
            yy = int(350 + (1 - eout(pp)) * 22)
            d.rectangle([x, yy, x + 600, yy + 300], fill=(10, 14, 21, 246), outline=a(col, 150))
            d.text((x + 34, yy + 40), k, font=F(RUSSO, 48), fill=a(col, 255))
            d.text((x + 34, yy + 130), v, font=fit(v, MONO, 30, 520), fill=a(TXT, 240))

        photo_panel(ov, d, "nose", 70, 700, 640, 200, t, 1.06)
        d.text((70, 920), "меньше демаскирующих признаков выстрела", font=F(MONO, 28), fill=a(DIM, 230))

        photo_panel(ov, d, "window", 1380, 350, 480, 550, t, 1.05, label="ОКНО С ДРОБЬЮ", idx="08")


# ═════════════ сцена 4: эксплуатация ═════════════
def scene4(base, ov, d, t, l):
    if l < 5.60:                      # установка
        head(d, "ЭКСПЛУАТАЦИЯ", "УСТАНОВКА НА АВТОМАТ", ACC, 100, 60)
        d.text((70, 262), "вместо штатного пламегасителя или дульного тормоза", font=F(MONO, 30), fill=a(DIM, 240))

        steps = [("01", "СНЯТЬ", "штатный пламегаситель"),
                 ("02", "ПОСТАВИТЬ", "насадку по резьбе или байонету"),
                 ("03", "ЗАФИКСИРОВАТЬ", "на АК-74 — крышку ствольной коробки")]
        for i, (num, k, v) in enumerate(steps):
            pp = c01((l - .20 - i * .18) / .55)
            if pp <= 0: continue
            yy = int(340 + i * 152 + (1 - eout(pp)) * 18)
            d.rectangle([70, yy, 1120, yy + 132], fill=(11, 16, 23, 246), outline=a(ACC, 130))
            d.rectangle([70, yy, 78, yy + 132], fill=a(ACC, 255))
            d.text((108, yy + 18), num, font=F(RUSSO, 36), fill=a(ACC, 235))
            d.text((190, yy + 16), k, font=F(RUSSO, 40), fill=a(TXT, 255))
            d.text((190, yy + 74), v, font=fit(v, MONO, 28, 900), fill=a(DIM, 240))

        d.rectangle([70, 812, 1120, 900], fill=(9, 13, 19, 246), outline=a(WARN, 120))
        d.text((102, 834), "НА АК-74 КРЫШКА СТВОЛЬНОЙ КОРОБКИ ФИКСИРУЕТСЯ ОБЯЗАТЕЛЬНО",
               font=F(MONO, 26), fill=a(WARN, 245))

        photo_panel(ov, d, "barrel", 1180, 320, 680, 520, t, 1.05, label="НАСАДКА И РЕЗЬБОВАЯ МУФТА", idx="09")

    elif l < 11.00:                   # зарядка
        head(d, "ЗАРЯЖАНИЕ", "МИНОМЁТНЫЙ СПОСОБ", ACC2, 100, 60)
        d.text((70, 262), "картридж забрасывается в насадку донной частью вперёд", font=F(MONO, 30), fill=a(DIM, 240))

        # схема
        d.rectangle([70, 340, 1120, 800], fill=(7, 10, 16, 242), outline=a(LINE, 255))
        d.rectangle([150, 470, 330, 700], fill=(20, 26, 34, 255), outline=a(DIM, 190), width=3)
        d.text((240, 716), "НАСАДКА", font=F(MONO, 26), fill=a(DIM, 225), anchor="ma")
        d.text((240, 520), "24 ММ", font=F(RUSSO, 36), fill=a(DIM, 200), anchor="ma")

        pp = eout(c01((l - .25) / 1.0))
        xx = 640 - int(300 * pp)
        d.rectangle([xx, 520, xx + 120, 650], fill=(28, 34, 44, 255), outline=a(ACC, 220), width=3)
        d.rectangle([xx + 120, 540, xx + 150, 630], fill=(150, 156, 166, 255))
        d.line([(xx + 200, 500), (xx + 152, 528)], fill=a(ACC, 190), width=4)
        d.line([(xx + 200, 670), (xx + 152, 642)], fill=a(ACC, 190), width=4)
        d.text((xx + 60, 486), "КАРТРИДЖ", font=F(MONO, 26), fill=a(ACC, 235), anchor="ma")
        d.text((xx + 84, 686), "ДНО ВПЕРЁД", font=F(MONO, 24), fill=a(ACC2, 235), anchor="ma")

        # две подсказки — под схемой, отдельными строками
        d.rectangle([770, 470, 1110, 596], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((794, 488), "ЗАБРОСИТЬ", font=F(MONO, 24), fill=a(ACC, 235))
        d.text((794, 522), "донной частью", font=F(MONO, 26), fill=a(TXT, 240))
        d.text((794, 556), "к резьбе", font=F(MONO, 26), fill=a(TXT, 240))
        d.rectangle([770, 616, 1110, 742], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((794, 634), "ДЕРЖАТЬ", font=F(MONO, 24), fill=a(ACC2, 235))
        d.text((794, 668), "автомат не ниже", font=F(MONO, 26), fill=a(TXT, 240))
        d.text((794, 702), "горизонтали", font=F(MONO, 26), fill=a(TXT, 240))

        photo_panel(ov, d, "base", 1180, 340, 680, 460, t, 1.04, label="ДНО КАРТРИДЖА: ЧЕТЫРЕ ОТВЕРСТИЯ", idx="10")

    elif l < 16.40:                   # патрон и запреты
        head(d, "ПАТРОН", "ПсГс — И ТОЛЬКО ОН", WARN, 100, 60)
        d.text((70, 262), "для выстрела используется штатный патрон ПсГс", font=F(MONO, 30), fill=a(DIM, 240))

        d.rectangle([70, 340, 1120, 620], fill=(9, 26, 22, 246), outline=a(ACC, 160), width=2)
        d.text((104, 366), "РАЗРЕШЕНО", font=F(MONO, 28), fill=a(ACC, 240))
        d.text((104, 412), "ПсГс", font=F(RUSSO, 96), fill=a(ACC, 255))
        d.text((104, 528), "штатный патрон, одиночные выстрелы или очереди", font=F(MONO, 28), fill=a(TXT, 240))

        d.rectangle([70, 660, 1120, 900], fill=(30, 12, 12, 250), outline=a(RED, 170), width=2)
        d.text((104, 686), "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО", font=F(MONO, 28), fill=a(RED, 245))
        d.text((104, 734), "БРОНЕБОЙНЫЕ И ПпГс", font=fit("БРОНЕБОЙНЫЕ И ПпГс", RUSSO, 52, 960), fill=a(RED, 255))
        d.text((104, 812), "это приведёт к поломке изделия", font=F(MONO, 30), fill=a(TXT, 240))

        photo_panel(ov, d, "compare", 1180, 340, 680, 520, t, 1.04,
                    label="КАРТРИДЖ И ПАТРОН 12 КАЛИБРА", idx="11")

    elif l < 20.75:                   # снаряжение: три шага
        head(d, "СНАРЯЖЕНИЕ КАРТРИДЖА", "ПОРОХ, ДОЗАТОР, ПУЛЕУЛАВЛИВАТЕЛЬ", ACC2, 100, 50)
        d.text((70, 246), "три шага, рекомендованных производителем", font=F(MONO, 30), fill=a(DIM, 240))

        steps = [("01", "ПОРОХ", "в стакан-дозатор: 3,1-3,2 г"),
                 ("02", "ГЕРМЕТИЗАЦИЯ", "стакан до упора, дно — крышка"),
                 ("03", "ПУЛЕУЛАВЛИВАТЕЛЬ", "металлический, до упора")]
        for i, (num, k, v) in enumerate(steps):
            pp = c01((l - .20 - i * .16) / .55)
            if pp <= 0: continue
            yy = int(320 + i * 160 + (1 - eout(pp)) * 16)
            d.rectangle([70, yy, 1120, yy + 140], fill=(11, 16, 23, 246), outline=a(ACC2, 130))
            d.rectangle([70, yy, 80, yy + 140], fill=a(ACC2, 255))
            d.text((108, yy + 16), num, font=F(MONO, 28), fill=a(ACC2, 235))
            d.text((184, yy + 14), k, font=F(RUSSO, 38), fill=a(TXT, 255))
            d.text((184, yy + 76), v, font=fit(v, MONO, 29, 910), fill=a(DIM, 245))

        photo_panel(ov, d, "window", 1180, 300, 680, 520, t, 1.04, label="ОКНО: ВИДНЫ ДРОБИНЫ", idx="12")

    elif l < 24.60:                   # пороха
        head(d, "НАВЕСКИ ПОРОХА", "ЧЕМ СНАРЯЖАТЬ", WARN, 100, 60)
        d.text((70, 262), "рекомендации производителя по типу пороха", font=F(MONO, 30), fill=a(DIM, 240))

        rows = [("«ИРБИС» 32", "2,1-2,4 Г", ACC),
                ("«ИРБИС» МАГНУМ 42", "2,1-2,4 Г", ACC),
                ("«ИРБИС» ОХОТА 35", "2,1-2,4 Г", ACC),
                ("«СУНАР» 35", "2,1 Г", ACC),
                ("«СОКОЛ»", "80/20 С ДЫМНЫМ", WARN)]
        for i, (nm, val, col) in enumerate(rows):
            pp = c01((l - .20 - i * .10) / .45)
            if pp <= 0: continue
            yy = int(340 + i * 104 + (1 - eout(pp)) * 14)
            d.rectangle([70, yy, 1120, yy + 88], fill=(11, 16, 23, 246), outline=a(col, 120))
            d.rectangle([70, yy, 78, yy + 88], fill=a(col, 255))
            d.text((110, yy + 22), nm, font=F(RUSSO, 36), fill=a(TXT, 255))
            d.text((700, yy + 26), val, font=fit(val, MONO, 32, 396), fill=a(col, 245))

        photo_panel(ov, d, "kit", 1180, 340, 680, 460, t, 1.04, label="КОМПЛЕКТ: НАСАДКА И КАРТРИДЖИ", idx="13")

    elif l < 29.60:                   # фасовка
        head(d, "ПОСТАВКА", "ФАСОВКА КРАТНО 15", ACC, 100, 60)
        d.text((70, 262), "заряды поставляются в гофрокоробках кратно пятнадцати штук", font=F(MONO, 30), fill=a(DIM, 240))

        pp = eout(c01((l - .20) / 1.2))
        # гофрокороб
        d.rectangle([70, 356, 700, 890], fill=(38, 32, 24, 250), outline=(120, 104, 78, 255), width=3)
        d.polygon([(70, 356), (150, 404), (150, 890), (70, 890)], fill=(48, 41, 31, 255))
        d.polygon([(700, 356), (620, 404), (620, 890), (700, 890)], fill=(30, 25, 19, 255))
        d.rectangle([150, 404, 620, 890], fill=(20, 17, 13, 255))
        d.line([(150, 404), (620, 404)], fill=(120, 104, 78, 255), width=3)

        for row in range(3):
            for col in range(5):
                idx = row * 5 + col
                if idx >= int(15 * pp): continue
                x = 166 + col * 90
                y = 424 + row * 156
                d.rounded_rectangle([x, y, x + 64, y + 112], 18, fill=(38, 46, 58, 255), outline=(86, 98, 116, 255), width=2)
                d.ellipse([x + 8, y - 6, x + 56, y + 20], fill=(30, 34, 42, 255), outline=(96, 106, 122, 255), width=2)
                d.rounded_rectangle([x - 2, y + 112, x + 66, y + 140], 5, fill=(196, 160, 86, 255))
                d.rectangle([x + 4, y + 122, x + 60, y + 126], fill=(24, 20, 16, 255))

        d.text((760, 350), "15", font=F(RUSSO, 210), fill=a(ACC, 255))
        d.text((774, 600), "ШТУК В КОРОБКЕ", font=F(MONO, 32), fill=a(DIM, 240))
        d.rectangle([770, 672, 1130, 892], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((796, 694), "КРАТНО 15", font=F(MONO, 24), fill=a(ACC, 235))
        d.text((796, 730), "только полными", font=F(MONO, 28), fill=a(TXT, 242))
        d.text((796, 768), "коробками", font=F(MONO, 28), fill=a(TXT, 242))
        d.text((796, 820), "гофрокороб", font=F(MONO, 26), fill=a(DIM, 235))

        photo_panel(ov, d, "rack", 1240, 340, 620, 480, t, 1.04, label="КАРТРИДЖИ В ДЕРЖАТЕЛЯХ", idx="13")

    else:                             # финал
        p = eout(c01((l - .1) / .8))
        d.rectangle([0, 180, W, 980], fill=(6, 9, 14, 232))
        d.rectangle([0, 180, 9, 980], fill=a(ACC, 255))
        d.text((80, 210 + (1 - p) * 20), "ДОБРЫНЯ", font=fit("ДОБРЫНЯ", RUSSO, 120, 1150), fill=a(TXT, 255 * p))
        d.text((84, 356), "ДРОНОБОЙ ДЛЯ АК-74 И АК-12", font=F(RUSSO, 40), fill=a(ACC, 255 * p))
        d.text((84, 428), "24 ММ  •  750 / 800 Г  •  ДО 200 ДРОБИН  •  ПсГс", font=F(MONO, 28), fill=a(DIM, 240))

        p2 = c01((l - .45) / .8)
        d.text((84, 520), "ПОДПИСЫВАЙТЕСЬ НА «В ОКОПЕ»", font=F(MONO, 30), fill=a(TXT, 255 * p2))

        links = [("TELEGRAM", "t.me/vokope_ru"), ("VK", "vk.com/vokope_rus"),
                 ("AVITO", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
        for i, (k, v) in enumerate(links):
            pp = c01((l - .70 - i * .16) / .45)
            if pp <= 0: continue
            yy = int(596 + i * 108 + (1 - eout(pp)) * 20)
            d.rectangle([80, yy, 1260, yy + 94], fill=(11, 16, 23, 246), outline=a(ACC, 120))
            d.rectangle([80, yy, 88, yy + 94], fill=a(ACC, 255))
            d.text((118, yy + 14), k, font=F(RUSSO, 30), fill=a(ACC, 255))
            d.text((118, yy + 52), v, font=F(MONO, 24), fill=a(TXT, 240))

        photo_panel(ov, d, "kit", 1330, 240, 520, 520, t, 1.04, label="НАСАДКА И КАРТРИДЖИ")


def intro(base, ov, d, t, l):
    p = eout(c01(t / .9))
    d.rectangle([0, H // 2 - 150, W, H // 2 + 120], fill=(5, 8, 13, int(200 * p)))
    d.text((W // 2, H // 2 - 92), "«В ОКОПЕ»", font=F(RUSSO, 96), fill=a(TXT, int(255 * c01(t / .7))), anchor="ma")
    d.text((W // 2, H // 2 + 22), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 34),
           fill=a(ACC, int(230 * c01((t - .4) / .7))), anchor="ma")
    w = 520 * eout(c01((t - .5) / .8))
    d.rectangle([W // 2 - w / 2, H // 2 + 72, W // 2 + w / 2, H // 2 + 75], fill=a(ACC, 220))
    waveform(d, W // 2 - 380, H - 260, 760, 120, t, ACC, 110, 72, 1.0)


SCENES = [(2.60, scene1), (26.95, scene2), (56.90, scene3), (79.85, scene4)]
TOTAL = 114.45
CUTS = [2.60, 8.90, 14.80, 20.60, 24.80, 26.95, 34.55, 41.95, 49.35, 54.35,
        56.90, 63.10, 69.40, 75.15, 79.85, 85.45, 90.85, 96.25, 104.45, 100.60, 109.45]


def render_frame(t):
    if t < 2.60:
        idx = -1; st, fn = 0.0, intro; l = t; name = "nose"
    else:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001: idx = i
        st, fn = SCENES[idx]; l = t - st
        if idx == 0:
            name = "nose" if l < 6.40 else ("fpv" if l < 12.20 else ("compare" if l < 18.40 else "kit"))
        elif idx == 1:
            name = "nose" if l < 7.60 else ("single" if l < 15.00 else ("barrel" if l < 22.40 else "engr"))
        elif idx == 2:
            name = "barrel" if l < 7.20 else ("rack" if l < 13.00 else ("set4" if l < 18.20 else "window"))
        else:
            name = "barrel" if l < 5.60 else ("base" if l < 11.00 else ("compare" if l < 16.40 else ("window" if l < 24.60 else ("rack" if l < 29.60 else "kit"))))

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
