# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // «СИГНАЛ-М2» и комплект станции РЭБ — Reels 9:16 (1080×1920, 30 fps)."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/signal_m2"
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
    "pole": "sig_5386435425448171211.jpg", "signal": "sig_5386435425448171212.jpg",
    "kapushon": "sig_5386435425448171213.jpg", "rebus": "sig_5386435425448171214.jpg",
    "shtora": "sig_5386435425448171215.jpg", "offer": "sig_5386435425448171216.jpg",
    "kit": "sig_5454272999369415345.jpg", "conv": "sig_5454272999369415346.jpg",
    "panel": "sig_5454272999369415347.jpg", "comm": "sig_5454272999369415348.jpg",
}

# вертикальная подложка 9:16
BW, BH = 1440, 2560
PLATES = {}

def plate(name, dark=0.30):
    key = (name, dark)
    if key in PLATES:
        return PLATES[key]
    im = PH[P[name]]
    s = max(BW / im.width, BH / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - BW) // 2
    y = (im.height - BH) // 2
    im = im.crop((x, y, x + BW, y + BH))
    im = im.filter(ImageFilter.GaussianBlur(14))
    im = im.point(lambda v: int(v * dark))
    im = Image.blend(im, Image.new("RGB", (BW, BH), (9, 20, 36)), 0.58)
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
    out = img.crop((x0, y0, x0 + int(cw), y0 + int(ch))).resize((W, H), Image.BILINEAR)
    return Image.blend(out, Image.new("RGB", (W, H), (8, 12, 20)), 0.28)

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
    d.text((44, 86), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА  //  РЭБ", font=F(MONO, 25), fill=a(DIM, 235))
    # индикатор записи
    d.ellipse([W - 62, 40, W - 40, 62], fill=a(RED, 235))
    # прогресс
    p = clamp(t / total, 0, 1)
    d.rectangle([0, 132, W, 137], fill=(14, 20, 30, 250))
    d.rectangle([0, 132, int(W * p), 137], fill=a(ACC, 240))

def bottom(ov, d, t, total, text="t.me/vokope_ru  •  vk.com/vokope_rus"):
    d.rectangle([0, H - 150, W, H], fill=(6, 9, 14, 250))
    d.rectangle([0, H - 152, W, H - 149], fill=a(ACC, 90))
    d.text((W // 2, H - 118), text, font=F(MONO, 26), fill=a(ACC, 240), anchor="ma")
    d.text((W // 2, H - 72), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 22), fill=a(DIM, 225), anchor="ma")


# ═════════════ ОБЩИЕ БЛОКИ ═════════════
def endcard(d, l, sub=""):
    """Финальная заставка «В ОКОПЕ» с каналами связи."""
    p0 = eout(c01((l - .05) / .5))
    if p0 <= 0: return
    d.rectangle([0, 190, W, 1700], fill=(6, 9, 14, int(242 * p0)))
    d.rectangle([0, 190, 9, 1700], fill=a(ACC, int(255 * p0)))
    brackets(d, 40, 220, W - 80, 1450, a(ACC, 90), 34, 3)
    kicker(d, 60, 250, "КАНАЛ  //  В ОКОПЕ", ACC, 26)

    p1 = eout(c01((l - .15) / .5))
    d.text((52, 306 + (1 - p1) * 26), "«В ОКОПЕ»", font=ffit("«В ОКОПЕ»", RUSSO, 118, 940), fill=a(TXT, 255 * p1))
    p2 = eout(c01((l - .28) / .45))
    d.text((58, 452), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 26), fill=a(ACC, 240 * p2))
    w = 900 * eout(c01((l - .34) / .55))
    d.rectangle([58, 500, 58 + w, 504], fill=a(ACC, 200))

    p3 = eout(c01((l - .44) / .5))
    if sub:
        d.text((58, 534), sub, font=ffit(sub, RUSSO, 44, 940), fill=a(TXT, 255 * p3))

    links = [("TELEGRAM", "t.me/vokope_ru"), ("ВКОНТАКТЕ", "vk.com/vokope_rus"),
             ("АВИТО", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
    for i, (k, v) in enumerate(links):
        pp = c01((l - .58 - i * .16) / .45)
        if pp <= 0: continue
        yy = int(700 + i * 196 + (1 - eout(pp)) * 24)
        d.rectangle([56, yy, 1024, yy + 170], fill=(9, 13, 19, 248), outline=a(ACC, int(150 * eout(pp))))
        d.rectangle([56, yy, 63, yy + 170], fill=a(ACC, 255))
        d.text((100, yy + 20), k, font=F(MONO, 26), fill=a(ACC, 245))
        d.text((100, yy + 68), v, font=ffit(v, MONO, 32, 860), fill=a(TXT, 246))

    pp = c01((l - 1.15) / .5)
    if pp > 0:
        pulse = .55 + .45 * math.sin(l * 3.4)
        d.rectangle([56, 1310, 1024, 1420], fill=(9, 34, 28, 250), outline=a(ACC, 210))
        d.ellipse([96, 1352, 124, 1380], fill=a(ACC, int(235 * pulse * eout(pp))))
        d.text((152, 1340), "ПОДПИСЫВАЙТЕСЬ", font=F(RUSSO, 44), fill=a(ACC, 255))
        d.text((56, 1470), "подберём решение под ваши задачи", font=F(MONO, 28), fill=a(DIM, 235 * eout(pp)))


def head(d, kick, title, col=ACC, x=56, y=176, size=64):
    kicker(d, x, y, kick, col, 26)
    f, _ = fit(title, RUSSO, size, 960)
    d.text((x - 8, y + 62), title, font=f, fill=a(TXT, 255))


# ═════════════ ФИЛЬМ A: «СИГНАЛ-М2» ═════════════
def a1(base, ov, d, t, l):
    if l < 2.80:                      # титул
        d.rectangle([0, 250, W, 1290], fill=(5, 8, 13, 232))
        d.rectangle([0, 250, 9, 1290], fill=a(ACC, 255))
        kicker(d, 56, 296, "ОБНАРУЖЕНИЕ БПЛА", ACC, 26)
        p1 = eout(c01((l - .14) / .5))
        d.text((50, 372 + (1 - p1) * 30), "«СИГНАЛ-М2»", font=ffit("«СИГНАЛ-М2»", RUSSO, 132, 940), fill=a(TXT, 255 * p1))
        p2 = eout(c01((l - .42) / .44))
        d.text((52, 526), "ОБНАРУЖИТЕЛЬ", font=F(RUSSO, 56), fill=a(ACC, 255 * p2))
        d.text((52, 594), "ДРОНОВ", font=F(RUSSO, 56), fill=a(ACC, 255 * p2))
        p3 = eout(c01((l - .68) / .4))
        d.text((52, 686), "всех типов: FPV, MAVIC, AUTEL", font=F(MONO, 28), fill=a(DIM, 245 * p3))

        chips = ["ДО 5000 М", "300–10 000 МГЦ", "24/7"]
        cxx, cyy = 52, 776
        for i, c in enumerate(chips):
            pp = c01((l - .92 - i * .08) / .4)
            if pp <= 0: continue
            cf = F(MONO, 27); cw = tw(d, c, cf) + 36
            if cxx + cw > 1020:
                cxx = 52; cyy += 74
            d.rectangle([cxx, cyy, cxx + cw, cyy + 60], fill=(11, 16, 24, 242), outline=a(ACC, 120))
            d.text((cxx + 18, cyy + 15), c, font=cf, fill=a(TXT, 245 * eout(pp)))
            cxx += cw + 14
        if l > 1.3:
            card(ov, d, "signal", 56, 900, 968, 380, l, 1.05, "ОБНАРУЖИТЕЛЬ «СИГНАЛ-М2»", "01")
    else:                             # хук
        kicker(d, 56, 190, "ЗАЧЕМ ЭТО", WARN, 26)
        f, _ = fit("ДРОН УЖЕ В КАДРЕ —", RUSSO, 66, 960)
        rtext(d, (48, 250), "ДРОН УЖЕ В КАДРЕ —", f, TXT, (l - 2.9) / .4)
        f2, _ = fit("ВЫ ОПОЗДАЛИ", RUSSO, 66, 960)
        rtext(d, (48, 326), "ВЫ ОПОЗДАЛИ", f2, WARN, (l - 2.98) / .4)
        d.text((54, 424), "защита начинается раньше —", font=F(MONO, 30), fill=a(DIM, 240))
        d.text((54, 466), "когда угроза только входит в зону контроля", font=F(MONO, 26), fill=a(DIM, 235))

        card(ov, d, "kapushon", 56, 530, 968, 470, l, 1.05,
             "СТАНЦИЯ «КАПЮШОН» К-12М", "02")

        rows = [("РАНЬШЕ", "оператор слышит дрон и реагирует"),
                ("ТЕПЕРЬ", "обнаружитель видит сигнал и включает РЭБ")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - 3.9 - i * .2) / .5)
            if pp <= 0: continue
            yy = int(1040 + i * 190 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 166], fill=(10, 14, 21, 246), outline=a(WARN if i == 0 else ACC, 130))
            d.rectangle([56, yy, 65, yy + 166], fill=a(WARN if i == 0 else ACC, 255))
            d.text((100, yy + 16), k, font=F(MONO, 26), fill=a(WARN if i == 0 else ACC, 245))
            d.text((100, yy + 62), v, font=ffit(v, MONO, 27, 880), fill=a(TXT, 242))


def a2(base, ov, d, t, l):
    head(d, "ТАКТИКО-ТЕХНИЧЕСКИЕ", "ЧТО УМЕЕТ", ACC2, 56, 176, 72)
    d.text((54, 322), "цифры изделия — без рекламных округлений", font=F(MONO, 28), fill=a(DIM, 240))

    items = [("ДАЛЬНОСТЬ", "ДО 5000 М", "обнаружение до подлёта", ACC),
             ("ДИАПАЗОН", "300–10 000 МГЦ", "сплошная полоса", ACC2),
             ("РЕЖИМ", "24/7", "без оператора", WARN)]
    for i, (k, big, sub, col) in enumerate(items):
        pp = eout(c01((l - .2 - i * .22) / .55))
        if pp <= 0: continue
        yy = 410 + i * 300
        d.rectangle([56, yy, 1024, yy + 250], fill=(11, 16, 23, 248), outline=a(col, 150))
        d.rectangle([56, yy, 65, yy + 250], fill=a(col, 255))
        d.text((104, yy + 22), k, font=F(MONO, 26), fill=a(col, 240))
        d.text((104, yy + 62), big, font=ffit(big, RUSSO, 66, 850), fill=a(TXT, 255))
        d.text((104, yy + 164), sub, font=F(MONO, 28), fill=a(DIM, 240))

    d.rectangle([56, 1330, 1024, 1470], fill=(9, 26, 22, 246), outline=a(ACC, 150))
    d.text((96, 1358), "СПЛОШНОЙ ДИАПАЗОН —", font=F(RUSSO, 34), fill=a(ACC, 255))
    d.text((96, 1404), "не «нарезка» из отдельных частот", font=F(MONO, 27), fill=a(TXT, 240))



def a3(base, ov, d, t, l):
    head(d, "АВТОМАТИКА", "НАШЁЛ — ВКЛЮЧИЛ РЭБ", ACC, 56, 176, 62)
    d.text((54, 300), "в течение нескольких секунд", font=F(MONO, 30), fill=a(DIM, 240))

    blocks = [("01", "ОБНАРУЖИЛ", "сигнал дрона в диапазоне", ACC),
              ("02", "РАСПОЗНАЛ", "аналоговый или цифровой", ACC2),
              ("03", "ВКЛЮЧИЛ", "станцию РЭБ на подавление", WARN)]
    for i, (num, k, v, col) in enumerate(blocks):
        pp = eout(c01((l - .2 - i * .22) / .55))
        if pp <= 0: continue
        yy = 380 + i * 250
        d.rectangle([56, yy, 1024, yy + 210], fill=(11, 16, 23, 248), outline=a(col, 140))
        d.rectangle([56, yy, 65, yy + 210], fill=a(col, 255))
        d.text((102, yy + 20), num, font=F(MONO, 28), fill=a(col, 240))
        d.text((170, yy + 16), k, font=F(RUSSO, 48), fill=a(TXT, 255))
        d.text((170, yy + 100), v, font=ffit(v, MONO, 28, 800), fill=a(DIM, 242))

    # полоса «секунды от сигнала до подавления»
    pw = 968 * eout(c01((l - .9) / 2.4))
    d.rectangle([56, 1112, 1024, 1124], fill=(18, 24, 34, 255))
    d.rectangle([56, 1112, 56 + pw, 1124], fill=a(WARN, 235))
    d.text((56, 1136), "СИГНАЛ → ПОДАВЛЕНИЕ", font=F(MONO, 22), fill=a(DIM, 235))
    d.text((1024, 1136), "СЕКУНДЫ", font=F(MONO, 22), fill=a(WARN, 240), anchor="ra")

    q1 = eout(c01((l - 3.1) / .5))
    if q1 > 0:
        yy = int(1176 + (1 - q1) * 24)
        d.rectangle([56, yy, 1024, yy + 176], fill=(9, 26, 22, 248), outline=a(ACC, int(150 * q1)))
        d.text((96, yy + 20), "БЕЗ ЧЕЛОВЕЧЕСКОГО ФАКТОРА", font=ffit("БЕЗ ЧЕЛОВЕЧЕСКОГО ФАКТОРА", RUSSO, 34, 880), fill=a(ACC, 255 * q1))
        d.text((96, yy + 90), "обнаружитель работает сам", font=F(MONO, 28), fill=a(TXT, 242 * q1))

    q2 = eout(c01((l - 4.3) / .5))
    if q2 > 0:
        yy = int(1382 + (1 - q2) * 24)
        d.rectangle([56, yy, 1024, yy + 176], fill=(9, 13, 19, 248), outline=a(ACC2, int(120 * q2)))
        d.text((96, yy + 18), "ВЫВОД ДАННЫХ", font=F(MONO, 24), fill=a(ACC2, 240 * q2))
        d.text((96, yy + 58), "смартфон · планшет · ПК", font=ffit("смартфон · планшет · ПК", RUSSO, 38, 880), fill=a(TXT, 255 * q2))



def a4(base, ov, d, t, l):
    if l < 6.00:                      # связки
        head(d, "В СВЯЗКЕ", "КУПОЛ + НАПРАВЛЕННАЯ", ACC, 56, 176, 58)

        d.rectangle([56, 320, 1024, 800], fill=(9, 13, 19, 246), outline=a(ACC, 130))
        d.text((96, 344), "НА ТЕХНИКЕ", font=F(MONO, 24), fill=a(ACC, 240))
        d.text((96, 384), "Купольные станции", font=F(RUSSO, 42), fill=a(TXT, 255))
        d.text((96, 452), "«Капюшон» К-8М / К-12М / К-15М", font=ffit("«Капюшон» К-8М / К-12М / К-15М", MONO, 28, 880), fill=a(DIM, 242))
        d.text((96, 502), "«Поле-31» — против спутниковой", font=F(MONO, 28), fill=a(DIM, 242))
        d.text((96, 548), "навигации, в движении", font=F(MONO, 28), fill=a(DIM, 242))
        d.text((96, 640), "автомобиль · броня · КУНГ", font=F(MONO, 27), fill=a(ACC, 235))
        card(ov, d, "kapushon", 96, 690, 420, 90, l, 1.0, None, "04") if False else None

        d.rectangle([56, 830, 1024, 1300], fill=(9, 13, 19, 246), outline=a(ACC2, 130))
        d.text((96, 854), "НА ОБЪЕКТЕ", font=F(MONO, 24), fill=a(ACC2, 240))
        d.text((96, 894), "Направленные станции", font=F(RUSSO, 42), fill=a(TXT, 255))
        d.text((96, 962), "«Штора» К-12/700", font=F(MONO, 28), fill=a(DIM, 242))
        d.text((96, 1008), "«Ребус-4» — круговой обзор, 12 генераторов", font=ffit("«Ребус-4» — круговой обзор, 12 генераторов", MONO, 27, 880), fill=a(DIM, 242))
        d.text((96, 1100), "тренога · здания · территория", font=F(MONO, 27), fill=a(ACC2, 235))

        card(ov, d, "shtora", 56, 1330, 468, 260, l, 1.05, "ШТОРА К-12/700", "05")
        card(ov, d, "rebus", 556, 1330, 468, 260, l, 1.05, "РЕБУС-4", "06")
    else:
        endcard(d, l - 6.00, "ОБНАРУЖИТЕЛЬ «СИГНАЛ-М2»")


# ═════════════ ФИЛЬМ B: КОМПЛЕКТ ═════════════
def b1(base, ov, d, t, l):
    if l < 3.20:                      # титул
        d.rectangle([0, 250, W, 1330], fill=(5, 8, 13, 232))
        d.rectangle([0, 250, 9, 1330], fill=a(ACC, 255))
        kicker(d, 56, 296, "СТАНЦИИ РЭБ", ACC, 26)
        p1 = eout(c01((l - .14) / .5))
        d.text((50, 372 + (1 - p1) * 30), "ЧТО ВХОДИТ", font=ffit("ЧТО ВХОДИТ", RUSSO, 96, 940), fill=a(TXT, 255 * p1))
        p2 = eout(c01((l - .36) / .45))
        d.text((50, 480), "В КОМПЛЕКТ", font=ffit("В КОМПЛЕКТ", RUSSO, 96, 940), fill=a(ACC, 255 * p2))
        p3 = eout(c01((l - .62) / .45))
        d.text((52, 606), "три схемы подключения", font=F(RUSSO, 44), fill=a(TXT, 255 * p3))
        d.text((52, 674), "под задачу и объект", font=F(MONO, 30), fill=a(DIM, 240))
        if l > .7:
            card(ov, d, "conv", 56, 760, 968, 380, l, 1.05, "ПРЕОБРАЗОВАТЕЛИ И ИП-24/100", "01")
        d.rectangle([56, 1180, 1024, 1300], fill=(9, 26, 22, 246), outline=a(ACC, 150))
        d.text((96, 1208), "УНИВЕРСАЛЬНОЙ КОМПЛЕКТАЦИИ НЕТ", font=ffit("УНИВЕРСАЛЬНОЙ КОМПЛЕКТАЦИИ НЕТ", RUSSO, 30, 880), fill=a(ACC, 255))
    else:                             # три варианта
        head(d, "ТРИ СХЕМЫ", "ПОД КАЖДЫЙ ОБЪЕКТ", WARN, 56, 176, 62)
        items = [("01", "ЛЕГКОВОЙ АВТОМОБИЛЬ", "12 → 24 В, преобразователь ПН", ACC),
                 ("02", "ГРУЗОВАЯ ТЕХНИКА, БРОНЯ", "коммутатор 24 В с защитой цепи", ACC2),
                 ("03", "СТАЦИОНАР", "щит питания СЩ-220/24 В", WARN)]
        for i, (num, k, v, col) in enumerate(items):
            pp = c01((l - 3.4 - i * .2) / .5)
            if pp <= 0: continue
            yy = int(360 + i * 300 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 260], fill=(11, 16, 23, 246), outline=a(col, 140))
            d.rectangle([56, yy, 65, yy + 260], fill=a(col, 255))
            d.text((104, yy + 18), num, font=F(MONO, 26), fill=a(col, 240))
            d.text((104, yy + 62), k, font=ffit(k, RUSSO, 40, 860), fill=a(TXT, 255))
            d.text((104, yy + 132), v, font=ffit(v, MONO, 27, 860), fill=a(DIM, 242))

        card(ov, d, "conv", 56, 1290, 468, 300, l, 1.05, "ПН И ИП-24/100", "02")
        card(ov, d, "panel", 556, 1290, 468, 300, l, 1.05, "ЩИТ СЩ-220/24", "03")


def b2(base, ov, d, t, l):
    head(d, "ВАРИАНТ 1", "ЛЕГКОВОЙ АВТОМОБИЛЬ", ACC, 56, 176, 56)
    d.text((54, 300), "питание от бортовой сети", font=F(MONO, 30), fill=a(DIM, 240))

    d.rectangle([56, 380, 1024, 720], fill=(11, 16, 23, 248), outline=a(ACC, 150))
    d.rectangle([56, 380, 65, 720], fill=a(ACC, 255))
    d.text((104, 406), "ПРЕОБРАЗОВАТЕЛЬ 12 → 24 В", font=F(MONO, 26), fill=a(ACC, 240))
    d.text((104, 452), "ПН 12/24", font=F(RUSSO, 64), fill=a(TXT, 255))
    d.text((104, 556), "мощность подбирается под станцию", font=F(MONO, 27), fill=a(DIM, 242))
    d.text((104, 606), "типовые номиналы — 30 или 50 А", font=F(MONO, 27), fill=a(DIM, 242))

    for i, (k, v) in enumerate([("30 А", "большинство станций"), ("50 А", "повышенное потребление")]):
        pp = eout(c01((l - .3 - i * .2) / .55))
        yy = 760 + i * 230
        d.rectangle([56, yy, 1024, yy + 200], fill=(9, 13, 19, 246), outline=a(ACC, 120))
        d.text((104, yy + 20), k, font=F(RUSSO, 54), fill=a(ACC, 255))
        d.text((104, yy + 100), v, font=F(MONO, 28), fill=a(DIM, 242))

    d.text((56, 1250), "мощный преобразователь —", font=F(MONO, 27), fill=a(DIM, 235))
    d.text((56, 1296), "для спецзаказов и оборудования", font=F(MONO, 27), fill=a(DIM, 235))
    card(ov, d, "conv", 56, 1360, 968, 300, l, 1.05, "ПРЕОБРАЗОВАТЕЛИ НАПРЯЖЕНИЯ", "02")


def b3(base, ov, d, t, l):
    if l < 5.50:                      # 24 В
        head(d, "ВАРИАНТ 2", "ГРУЗОВАЯ ТЕХНИКА", ACC2, 56, 176, 58)
        d.text((54, 300), "бортовая сеть 24 В", font=F(MONO, 30), fill=a(DIM, 240))

        d.rectangle([56, 380, 1024, 760], fill=(11, 16, 23, 248), outline=a(ACC2, 150))
        d.rectangle([56, 380, 65, 760], fill=a(ACC2, 255))
        d.text((104, 406), "КОММУТАТОР 24 В", font=F(MONO, 26), fill=a(ACC2, 240))
        d.text((104, 452), "защита цепи питания", font=F(RUSSO, 48), fill=a(TXT, 255))
        d.text((104, 540), "от короткого замыкания", font=F(MONO, 27), fill=a(DIM, 242))
        d.text((104, 590), "и нештатных режимов", font=F(MONO, 27), fill=a(DIM, 242))

        d.text((56, 820), "грузовые автомобили · бронетехника", font=F(MONO, 27), fill=a(DIM, 240))
        d.text((56, 866), "тракторы · специальная техника", font=F(MONO, 27), fill=a(DIM, 240))
        card(ov, d, "comm", 56, 950, 968, 400, l, 1.05, "КОММУТАТОР 24 В И ТЕСТЕР Т-9", "03")

        d.rectangle([56, 1420, 1024, 1560], fill=(9, 13, 19, 246), outline=a(ACC2, 120))
        d.text((96, 1446), "ТЕСТЕР Т-9", font=F(MONO, 24), fill=a(ACC2, 240))
        d.text((96, 1486), "проверка станции в поле", font=F(MONO, 28), fill=a(TXT, 242))
    else:                             # стационар
        head(d, "ВАРИАНТ 3", "СТАЦИОНАР", WARN, 56, 176, 62)
        d.text((54, 300), "здание, вышка, тренога", font=F(MONO, 30), fill=a(DIM, 240))

        d.rectangle([56, 380, 1024, 760], fill=(11, 16, 23, 248), outline=a(WARN, 150))
        d.rectangle([56, 380, 65, 760], fill=a(WARN, 255))
        d.text((104, 406), "ЩИТ ПИТАНИЯ", font=F(MONO, 26), fill=a(WARN, 240))
        d.text((104, 452), "СЩ-220/24 В", font=F(RUSSO, 58), fill=a(TXT, 255))
        d.text((104, 560), "сеть 220 В — питание станции", font=F(MONO, 27), fill=a(DIM, 242))

        d.text((56, 820), "предприятия · склады", font=F(MONO, 27), fill=a(DIM, 240))
        d.text((56, 866), "производственные площадки · инфраструктура", font=ffit("производственные площадки · инфраструктура", MONO, 27, 900), fill=a(DIM, 240))
        card(ov, d, "panel", 56, 950, 968, 400, l, 1.05, "СТАЦИОНАРНЫЙ ЩИТ СЩ-220/24 В", "04")

        d.rectangle([56, 1420, 1024, 1560], fill=(9, 26, 22, 246), outline=a(ACC, 140))
        d.text((96, 1450), "один из трёх вариантов —", font=F(MONO, 26), fill=a(DIM, 240))
        d.text((96, 1496), "в комплекте всегда", font=F(RUSSO, 32), fill=a(ACC, 255))


def b4(base, ov, d, t, l):
    if l < 7.20:
        head(d, "ДОПОЛНИТЕЛЬНО", "ЧТО ЕЩЁ В КОМПЛЕКТЕ", ACC, 56, 176, 56)

        rows = [("КАБЕЛЬ", "длину определяем индивидуально", ACC),
                ("РАЗЪЁМ", "под обнаружитель «Сигнал-М2»", ACC2),
                ("РЕЗЕРВ", "ИП-24/100 или ИП-24/210", WARN),
                ("ПРОВЕРКА", "РЭБ-тестер Т-9, чехол MOLLE", ACC)]
        for i, (k, v, col) in enumerate(rows):
            pp = c01((l - .2 - i * .16) / .5)
            if pp <= 0: continue
            yy = int(320 + i * 220 + (1 - eout(pp)) * 18)
            d.rectangle([56, yy, 1024, yy + 186], fill=(11, 16, 23, 246), outline=a(col, 135))
            d.rectangle([56, yy, 65, yy + 186], fill=a(col, 255))
            d.text((104, yy + 16), k, font=F(MONO, 24), fill=a(col, 240))
            d.text((104, yy + 58), v, font=ffit(v, RUSSO, 34, 860), fill=a(TXT, 255))

        card(ov, d, "comm", 56, 1180, 968, 330, l, 1.05, "ТЕСТЕР Т-9 В ЧЕХЛЕ MOLLE", "05")
        d.text((56, 1560), "аксессуары добавляются под задачу", font=F(MONO, 27), fill=a(DIM, 235))
    else:
        endcard(d, l - 7.20, "КОМПЛЕКТ СТАНЦИИ РЭБ")


# ═════════════ СБОРКА ═════════════
FILMS = {
    "A": {"scenes": [(2.60, a1), (11.40, a2), (21.95, a3), (31.85, a4)], "total": 43.90,
          "cuts": [2.60, 6.40, 11.40, 16.60, 21.95, 26.40, 31.85, 36.20, 37.85],
          "bg": {0: [("signal", 2.80), ("offer", 5.40)],
                 1: [("signal", 5.20), ("pole", 8.60)],
                 2: [("pole", 4.20), ("signal", 7.40)],
                 3: [("kapushon", 3.40), ("rebus", 4.60), ("shtora", 9.00), ("signal", 6.00)]}},
    "B": {"scenes": [(2.60, b1), (11.40, b2), (18.45, b3), (29.40, b4)], "total": 44.05,
          "cuts": [2.60, 5.60, 11.40, 14.60, 18.45, 23.95, 29.40, 34.00, 36.60],
          "bg": {0: [("kit", 3.20), ("panel", 5.20)],
                 1: [("conv", 3.40), ("comm", 5.40)],
                 2: [("comm", 5.50), ("panel", 6.00)],
                 3: [("kit", 4.20), ("conv", 7.50), ("comm", 9.60)]}},
}


def bg_name(film, idx, l):
    spans = FILMS[film]["bg"].get(idx, [("signal", 0.0)])
    name = spans[0][0]
    for nm, st in spans:
        if l >= st:
            name = nm
    return name


def render_frame(film, t):
    cfg = FILMS[film]
    total = cfg["total"]
    scenes = cfg["scenes"]
    if t < scenes[0][0]:
        idx = -1; l = t; name = cfg["bg"][0][0][0]; fn = None
    else:
        idx = 0
        for i, (s0, _) in enumerate(scenes):
            if t >= s0 - .001: idx = i
        st, fn = scenes[idx]; l = t - st
        name = bg_name(film, idx, l)

    z0 = 1.03 + .012 * math.sin(t * .9)
    base = cam(name, l, 5.0, z0, z0 + .10, .30 * math.sin(t * .15), .16 * math.cos(t * .19)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    if not (fn is None):
        fn(base, ov, d, t, l)
    top(ov, d, t, total)

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
        bottom(ov, d, t, total)

    out = Image.alpha_composite(base, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])
    for c in cfg["cuts"]:
        dd = abs(t - c)
        if dd < .12:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), (1 - dd / .12) * .18)
    return out.convert("RGB")


if __name__ == "__main__":
    import sys
    film = sys.argv[1]
    for arg in sys.argv[2:]:
        tt = float(arg)
        render_frame(film, tt).save(os.path.join(BASE, f"qa_{film}_{tt:06.2f}.jpg"), quality=92)
        print("saved", film, tt)
