# -*- coding: utf-8 -*-
"""«В ОКОПЕ» // РЭБ-рюкзак «ЗОНТ. Модель S8» — вертикальный Reels 9:16."""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
BASE = "/home/user/-/video_studio/zont_s8"
ASSETS = os.path.join(BASE, "assets")
FD = "/home/user/-/video_studio/toolkit/fonts"

BG   = (6, 8, 12)
ACC  = (0, 229, 160)
ACC2 = (0, 176, 255)
WARN = (255, 176, 32)
TXT  = (242, 246, 255)
DIM  = (140, 162, 186)
LINE = (34, 52, 74)
RED  = (255, 82, 82)

RUSSO, DAYS, MONO = ("RussoOne-Regular.ttf", "DaysOne-Regular.ttf", "JetBrainsMono-VF.ttf")


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


def ffit(txt, fn, size, max_w):
    return fit(txt, fn, size, max_w)[0]


# ───────── вырезка фона (белый) ─────────
def cutout(path):
    import scipy.ndimage as nd
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).astype(np.int16)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    whitish = (r > 232) & (g > 232) & (b > 232) & (abs(r - g) < 16) & (abs(g - b) < 16)
    lab, n = nd.label(whitish)
    keep = np.zeros(n + 1, dtype=bool)
    h, w = whitish.shape
    edge = np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])
    sizes = nd.sum(whitish, lab, index=np.arange(n + 1))
    big = sizes > 0.0008 * h * w          # крупные белые области — фон
    for lid in np.unique(edge):
        if lid:
            keep[lid] = True
    for lid in range(1, n + 1):
        if big[lid]:
            keep[lid] = True
    transparent = keep[lab]
    fg = ~transparent
    # заделать мелкие дырки внутри изделия
    filled = nd.binary_fill_holes(fg)
    holes = filled & fg.__invert__()
    hlab, hn = nd.label(holes)
    if hn:
        hs = nd.sum(holes, hlab, index=np.arange(hn + 1))
        small = np.zeros(hn + 1, dtype=bool)
        small[1:] = hs[1:] < 0.004 * fg.size
        fg = fg | small[hlab]
    # убрать белую кромку
    fg = nd.binary_erosion(fg, iterations=3)
    alpha = np.where(fg, 255, 0).astype(np.uint8)
    am = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.9))
    out = im.convert("RGBA")
    out.putalpha(am)
    bbox = am.point(lambda v: 255 if v > 24 else 0).getbbox()
    return out.crop(bbox)


CUT = {}
for nm in ("panel", "side", "back"):
    CUT[nm] = cutout(os.path.join(ASSETS, f"{nm}.jpg"))


def big(name, height):
    key = (name, height)
    if key in CUT:
        return CUT[key]
    im = CUT[name]
    s = height / im.height
    out = im.resize((max(1, int(im.width * s)), height), Image.LANCZOS)
    CUT[key] = out
    return out


def product(canvas, name, cx, cy, height, zoom=1.0, px=0.0, py=0.0, alpha=1.0, glow=ACC):
    """Кладёт вырезку изделия на canvas (RGBA) с мягким свечением."""
    src = big(name, 1700)
    cw, ch = int(src.width / zoom), int(src.height / zoom)
    x0 = int(clamp(src.width / 2 + px * (src.width - cw) / 2 - cw / 2, 0, src.width - cw))
    y0 = int(clamp(src.height / 2 + py * (src.height - ch) / 2 - ch / 2, 0, src.height - ch))
    piece = src.crop((x0, y0, x0 + cw, y0 + ch))
    s = height / piece.height
    piece = piece.resize((max(1, int(piece.width * s)), height), Image.LANCZOS)
    if alpha < 1:
        al = piece.getchannel("A").point(lambda v: int(v * alpha))
        piece.putalpha(al)
    px0, py0 = int(cx - piece.width / 2), int(cy - piece.height / 2)
    # свечение
    if glow is not None:
        sil = Image.new("RGBA", piece.size, (0, 0, 0, 0))
        sil.paste(Image.new("RGBA", piece.size, a(glow, 90)), (0, 0), piece)
        sil = sil.filter(ImageFilter.GaussianBlur(38))
        canvas.alpha_composite(sil, (px0, py0))
    canvas.alpha_composite(piece, (px0, py0))
    return piece.size


# ───────── фон / оверлеи ─────────
def make_bg():
    g = Image.new("RGB", (W, H), (7, 10, 16))
    d = ImageDraw.Draw(g)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(9 + 9 * (1 - k)), int(13 + 12 * (1 - k)), int(20 + 16 * (1 - k))))
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grid)
    for x in range(0, W, 60):
        dg.line([(x, 0), (x, H)], fill=(24, 40, 58, 60))
    for y in range(0, H, 60):
        dg.line([(0, y), (W, y)], fill=(24, 40, 58, 60))
    g = Image.alpha_composite(g.convert("RGBA"), grid)
    return g


BGIMG = make_bg().convert("RGB")

SCAN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_s = ImageDraw.Draw(SCAN)
for y in range(0, H, 3):
    _s.line([(0, y), (W, y)], fill=(0, 0, 0, 26))

VIGN = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_vd = ImageDraw.Draw(VIGN)
for i in range(110):
    k = i / 110.0
    ins = int(-180 + k * 420)
    _vd.ellipse([ins, ins * 1.1, W - ins, H - ins * 1.1], outline=(0, 0, 0, int(3 + k * 2)), width=5)
VIGN = VIGN.filter(ImageFilter.GaussianBlur(26))

_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(4):
    n = _rng.integers(0, 30, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 18))))


def brackets(d, x, y, w, h, col=(0, 229, 160, 190), ln=26, wd=3):
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        d.line([(cx, cy), (cx + sx * ln, cy)], fill=col, width=wd)
        d.line([(cx, cy), (cx, cy + sy * ln)], fill=col, width=wd)


def kicker(d, x, y, s, col=ACC, size=26):
    f = F(MONO, size)
    w = tw(d, s, f)
    d.rectangle([x, y, x + w + 34, y + 46], fill=a((8, 26, 22), 236), outline=a(col, 150))
    d.rectangle([x, y, x + 7, y + 46], fill=a(col, 255))
    d.text((x + 18, y + 11), s, font=f, fill=a(col, 255))


def top(d, t, total):
    d.rectangle([0, 0, W, 132], fill=(8, 11, 17, 238))
    d.rectangle([0, 0, W, 5], fill=a(ACC, 255))
    d.text((44, 30), "«В ОКОПЕ»", font=F(RUSSO, 40), fill=a(TXT, 255))
    d.text((44, 86), "РЭБ  //  РЮКЗАК «ЗОНТ» S8", font=F(MONO, 25), fill=a(DIM, 235))
    d.ellipse([W - 62, 40, W - 40, 62], fill=a(RED, 235))
    p = clamp(t / total, 0, 1)
    d.rectangle([0, 132, W, 137], fill=(14, 20, 30, 250))
    d.rectangle([0, 132, int(W * p), 137], fill=a(ACC, 240))


def bottom(d):
    d.rectangle([0, H - 150, W, H], fill=(6, 9, 14, 250))
    d.rectangle([0, H - 152, W, H - 149], fill=a(ACC, 90))
    d.text((W // 2, H - 118), "t.me/vokope_ru  •  vk.com/vokope_rus", font=F(MONO, 26), fill=a(ACC, 240), anchor="ma")
    d.text((W // 2, H - 72), "ПОДПИСЫВАЙСЯ", font=F(RUSSO, 22), fill=a(DIM, 225), anchor="ma")


def endcard(d, l, sub=""):
    p0 = eout(c01((l - .03) / .4))
    if p0 <= 0: return
    d.rectangle([0, 190, W, 1700], fill=(6, 9, 14, int(244 * p0)))
    d.rectangle([0, 190, 9, 1700], fill=a(ACC, int(255 * p0)))
    brackets(d, 40, 220, W - 80, 1450, a(ACC, 90), 34, 3)
    kicker(d, 60, 250, "КАНАЛ  //  В ОКОПЕ", ACC, 26)

    p1 = eout(c01((l - .10) / .45))
    d.text((52, 306 + (1 - p1) * 26), "«В ОКОПЕ»", font=ffit("«В ОКОПЕ»", RUSSO, 118, 940), fill=a(TXT, 255 * p1))
    p2 = eout(c01((l - .22) / .4))
    d.text((58, 452), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 26), fill=a(ACC, 240 * p2))
    w = 900 * eout(c01((l - .26) / .5))
    d.rectangle([58, 500, 58 + w, 504], fill=a(ACC, 200))
    if sub:
        p3 = eout(c01((l - .34) / .45))
        d.text((58, 534), sub, font=ffit(sub, RUSSO, 44, 940), fill=a(TXT, 255 * p3))

    links = [("TELEGRAM", "t.me/vokope_ru"), ("ВКОНТАКТЕ", "vk.com/vokope_rus"),
             ("АВИТО", "avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241")]
    for i, (k, v) in enumerate(links):
        pp = c01((l - .48 - i * .14) / .4)
        if pp <= 0: continue
        yy = int(700 + i * 196 + (1 - eout(pp)) * 24)
        d.rectangle([56, yy, 1024, yy + 170], fill=(9, 13, 19, 248), outline=a(ACC, int(150 * eout(pp))))
        d.rectangle([56, yy, 63, yy + 170], fill=a(ACC, 255))
        d.text((100, yy + 20), k, font=F(MONO, 26), fill=a(ACC, 245))
        d.text((100, yy + 68), v, font=ffit(v, MONO, 32, 860), fill=a(TXT, 246))

    pp = c01((l - 1.0) / .45)
    if pp > 0:
        pulse = .55 + .45 * math.sin(l * 3.6)
        d.rectangle([56, 1310, 1024, 1420], fill=(9, 34, 28, 250), outline=a(ACC, 210))
        d.ellipse([96, 1352, 124, 1380], fill=a(ACC, int(235 * pulse * eout(pp))))
        d.text((152, 1340), "ПОДПИСЫВАЙТЕСЬ", font=F(RUSSO, 44), fill=a(ACC, 255))
        d.text((56, 1470), "подберём решение под ваши задачи", font=F(MONO, 27), fill=a(DIM, 235 * eout(pp)))


# ═════════════ СЦЕНА 1: ХУК ═════════════
def s1(cv, d, t, l):
    punch = 1.14 - .14 * eout(c01((l - .05) / .7))
    z = punch + .012 * math.sin(l * 1.6)
    product(cv, "back", 742, 1120, int(680 * z), zoom=1.02, py=.08 * math.sin(l * .5),
            alpha=clamp(l / .35, 0, 1))

    p0 = eout(c01((l - .1) / .45))
    if p0 > 0:
        d.rectangle([0, 236, W, 452], fill=(6, 9, 14, int(238 * p0)))
        d.rectangle([0, 236, 9, 452], fill=a(ACC, int(255 * p0)))
        d.text((48, 254), "РЭБ-РЮКЗАК", font=F(MONO, 30), fill=a(ACC, 245 * p0))
        d.text((46, 298 + (1 - p0) * 20), "«ЗОНТ» S8", font=ffit("«ЗОНТ» S8", RUSSO, 100, 990), fill=a(TXT, 255 * p0))

    p1 = eout(c01((l - .38) / .45))
    if p1 > 0:
        d.rectangle([0, 470, W, 800], fill=(6, 9, 14, int(200 * p1)))
        sc = 1.0 + .12 * (1 - p1)
        d.text((34, 470), "500", font=F(RUSSO, int(224 * sc)), fill=a(ACC, 255 * p1))
        d.text((536, 636), "ВТ", font=F(RUSSO, 96), fill=a(TXT, 255 * p1))
        d.text((42, 706), "ЗА СПИНОЙ", font=F(RUSSO, 52), fill=a(TXT, 245 * p1))

    chips = ["200–5900 МГЦ", "10 КАНАЛОВ", "ОТ 100 М"]
    cxx, cyy = 42, 1330
    for i, c in enumerate(chips):
        pp = c01((l - .95 - i * .1) / .35)
        if pp <= 0: continue
        cf = F(MONO, 28); cw = tw(d, c, cf) + 36
        if cxx + cw > 1032:
            cxx = 42; cyy += 74
        d.rectangle([cxx, cyy, cxx + cw, cyy + 62], fill=(11, 16, 24, 250), outline=a(ACC, int(150 * pp)))
        d.text((cxx + 18, cyy + 16), c, font=cf, fill=a(TXT, 250 * eout(pp)))
        cxx += cw + 14

    d.rectangle([42, 1520, 726, 1596], fill=(9, 13, 19, 248), outline=a(ACC2, 130))
    d.text((72, 1544), "против FPV-дронов и БПЛА", font=F(MONO, 27),
           fill=a(TXT, 245 * c01((l - 1.35) / .45)))
    # вертикальная шкала мощности
    hp = eout(c01((l - 1.1) / .9))
    for k in range(16):
        yy = 1640 - k * 42
        on = k / 16 < hp
        d.rectangle([1006, yy, 1032, yy + 30], fill=a(ACC if on else (26, 36, 48), 240 if on else 255))


# ═════════════ СЦЕНА 2: ЧАСТОТЫ ═════════════
def s2(cv, d, t, l):
    p = eout(c01((l - .05) / .4))
    d.rectangle([0, 210, W, 720], fill=(6, 9, 14, int(236 * p)))
    d.text((48, 226), "ДИАПАЗОН ПОДАВЛЕНИЯ", font=F(MONO, 28), fill=a(ACC, 240 * p))
    d.text((42, 272), "200–5900", font=ffit("200–5900", RUSSO, 140, 990), fill=a(TXT, 255 * p))
    d.text((46, 434), "МЕГАГЕРЦ", font=F(RUSSO, 64), fill=a(ACC, 255 * p))
    d.text((46, 536), "куполом — по всем направлениям", font=F(MONO, 27), fill=a(DIM, 235 * p))

    # сканер спектра
    bx, bw, by = 42, 996, 690
    d.rectangle([bx, by, bx + bw, by + 190], fill=(7, 10, 16, 246), outline=a(LINE, 255))
    bands = [("200–1020", 0.05, 0.30, ACC), ("2100–2700", 0.33, 0.46, ACC2), ("5700–5900", 0.94, 1.0, WARN)]
    for i, (nm, a0, a1, col) in enumerate(bands):
        pp = eout(c01((l - .3 - i * .16) / .6))
        if pp <= 0: continue
        x0 = bx + 14 + (bw - 28) * a0
        x1 = x0 + (bw - 28) * (a1 - a0) * pp
        d.rectangle([x0, by + 20, x1, by + 62], fill=a(col, 245))
        d.text((x0, by + 72), nm, font=F(MONO, 24), fill=a(col, 240))
    # бегущая метка сканера
    sx = bx + 14 + (bw - 28) * ((l * .31) % 1.0)
    d.line([(sx, by + 12), (sx, by + 150)], fill=a(TXT, 190), width=3)
    d.text((bx + 14, by + 150), "0", font=F(MONO, 20), fill=a(DIM, 200))
    d.text((bx + bw - 14, by + 150), "6000 МГЦ", font=F(MONO, 20), fill=a(DIM, 200), anchor="ra")

    # 10 каналов
    p2 = eout(c01((l - .9) / .45))
    if p2 > 0:
        yy = 916
        d.rectangle([42, yy, 1038, yy + 208], fill=(11, 16, 23, 250), outline=a(ACC2, int(150 * p2)))
        d.text((78, yy + 18), "КАНАЛОВ ПОДАВЛЕНИЯ — 10", font=F(MONO, 24), fill=a(ACC2, 240 * p2))
        for k in range(10):
            q = c01((l - .95 - k * .055) / .3)
            if q <= 0: continue
            x = 78 + k * 94
            d.rectangle([x, yy + 62, x + 16, yy + 132], fill=a(ACC, 240 * q))
        d.text((78, yy + 148), "суммарно 500 ВТ на 10 каналов", font=F(MONO, 26), fill=a(DIM, 235 * p2))

    p3 = eout(c01((l - 1.7) / .45))
    if p3 > 0:
        yy = 1156
        d.rectangle([42, yy, 1038, yy + 200], fill=(9, 13, 19, 250), outline=a(WARN, int(140 * p3)))
        d.rectangle([42, yy, 49, yy + 200], fill=a(WARN, 255))
        d.text((86, yy + 18), "МОЩНОСТЬ", font=F(MONO, 24), fill=a(WARN, 240 * p3))
        d.text((86, yy + 54), "500 ВТ", font=ffit("500 ВТ", RUSSO, 66, 600), fill=a(TXT, 255 * p3))
        d.text((86, yy + 136), "дальность подавления — от 100 м", font=F(MONO, 26), fill=a(DIM, 240 * p3))

    p4 = eout(c01((l - 2.4) / .45))
    if p4 > 0:
        yy = 1396
        d.rectangle([42, yy, 1038, yy + 190], fill=(9, 26, 22, 250), outline=a(ACC, int(160 * p4)))
        d.rectangle([42, yy, 49, yy + 190], fill=a(ACC, 255))
        d.text((86, yy + 18), "СИСТЕМА ЗАЩИТЫ", font=F(MONO, 24), fill=a(ACC, 240 * p4))
        d.text((86, yy + 58), "КУПОЛЬНАЯ", font=ffit("КУПОЛЬНАЯ", RUSSO, 58, 620), fill=a(ACC, 255 * p4))
        d.text((86, yy + 132), "по всем направлениям", font=F(MONO, 26), fill=a(DIM, 240 * p4))
        product(cv, "panel", 900, yy + 92, 150, alpha=.92, glow=None)

    for i, txt in enumerate(["пульт управления — на кабеле, под рукой",
                             "модуль детекции частот с дисплеем"]):
        q = c01((l - 2.9 - i * .2) / .45)
        if q > 0:
            d.text((44, 1616 + i * 52), txt, font=F(MONO, 26), fill=a(DIM, 240 * q))


# ═════════════ СЦЕНА 3: АВТОНОМНОСТЬ ═════════════
def s3(cv, d, t, l):
    product(cv, "side", 866, 830, 520, zoom=1.02, py=.06 * math.sin(l * .6), alpha=.95)

    p = eout(c01((l - .05) / .4))
    d.rectangle([0, 200, 636, 500], fill=(6, 9, 14, int(236 * p)))
    d.rectangle([0, 200, 9, 500], fill=a(ACC, int(255 * p)))
    d.text((44, 218), "АВТОНОМНОСТЬ", font=F(MONO, 28), fill=a(ACC, 240 * p))
    d.text((42, 264), "РАБОТА", font=ffit("РАБОТА", RUSSO, 80, 580), fill=a(TXT, 255 * p))
    d.text((42, 352), "В ПОЛЕ", font=ffit("В ПОЛЕ", RUSSO, 80, 580), fill=a(TXT, 255 * p))

    p1 = eout(c01((l - .3) / .6))
    if p1 > 0:
        cx, cy, R = 250, 780, 140
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * p1, fill=a(ACC, 240), width=11)
        d.text((cx, cy - 58), "60", font=F(RUSSO, 124), fill=a(TXT, 255 * p1), anchor="ma")
        d.text((cx, cy + 66), "МИНУТ", font=F(MONO, 30), fill=a(ACC, 240 * p1), anchor="ma")
        d.text((cx, cy + 150), "на внутреннем АКБ", font=F(MONO, 24), fill=a(DIM, 235 * p1), anchor="ma")

    rows = [("ВНУТРЕННИЙ АКБ", "до 60 минут непрерывно", ACC),
            ("РЕЖИМ АВТОМАТИКИ", "до 24 часов работы", ACC2),
            ("ЗАРЯДКА", "от 5 часов", WARN)]
    for i, (k, v, col) in enumerate(rows):
        pp = c01((l - .5 - i * .2) / .45)
        if pp <= 0: continue
        yy = int(1010 + i * 176 + (1 - eout(pp)) * 20)
        d.rectangle([42, yy, 1038, yy + 150], fill=(11, 16, 23, 250), outline=a(col, int(150 * eout(pp))))
        d.rectangle([42, yy, 49, yy + 150], fill=a(col, 255))
        d.text((86, yy + 14), k, font=F(MONO, 23), fill=a(col, 240))
        d.text((86, yy + 50), v, font=ffit(v, RUSSO, 36, 900), fill=a(TXT, 250 * eout(pp)))

    p2 = eout(c01((l - 1.3) / .45))
    if p2 > 0:
        yy = 1544
        d.rectangle([42, yy, 1038, yy + 176], fill=(9, 13, 19, 250), outline=a(ACC, int(140 * p2)))
        d.text((86, yy + 14), "ЗАЩИТА КОРПУСА", font=F(MONO, 23), fill=a(ACC, 240 * p2))
        d.text((86, yy + 50), "КЕВЛАРОВЫЙ ЧЕХОЛ", font=ffit("КЕВЛАРОВЫЙ ЧЕХОЛ", RUSSO, 38, 900), fill=a(TXT, 255 * p2))
        d.text((86, yy + 110), "осколки · удары · активное охлаждение", font=F(MONO, 24), fill=a(DIM, 240 * p2))


# ═════════════ СЦЕНА 4: ГАБАРИТЫ + ФИНАЛ ═════════════
def s4(cv, d, t, l):
    if l < 5.40:
        product(cv, "back", 880, 560, 350, zoom=1.02, alpha=.95)

        p = eout(c01((l - .05) / .4))
        d.rectangle([0, 200, 700, 470], fill=(6, 9, 14, int(238 * p)))
        d.rectangle([0, 200, 9, 470], fill=a(WARN, int(255 * p)))
        d.text((44, 218), "ВЕС И ГАБАРИТЫ", font=F(MONO, 28), fill=a(WARN, 240 * p))
        d.text((42, 262), "16", font=ffit("16", RUSSO, 118, 300), fill=a(TXT, 255 * p))
        d.text((250, 292), "КГ", font=F(RUSSO, 74), fill=a(WARN, 255 * p))

        p1 = eout(c01((l - .3) / .45))
        if p1 > 0:
            d.rectangle([42, 500, 700, 664], fill=(11, 16, 23, 250), outline=a(WARN, int(150 * p1)))
            d.text((78, 516), "ГАБАРИТЫ, ММ", font=F(MONO, 24), fill=a(WARN, 240 * p1))
            d.text((78, 552), "400 × 200 × 650", font=ffit("400 × 200 × 650", RUSSO, 50, 600), fill=a(TXT, 255 * p1))

        p2 = eout(c01((l - .65) / .45))
        if p2 > 0:
            d.rectangle([42, 700, 700, 880], fill=(9, 13, 19, 250), outline=a(ACC, int(140 * p2)))
            d.text((78, 716), "В КОМПЛЕКТЕ", font=F(MONO, 24), fill=a(ACC, 240 * p2))
            d.text((78, 752), "рюкзак · пульт · ЗУ · паспорт", font=ffit("рюкзак · пульт · ЗУ · паспорт", MONO, 25, 600), fill=a(TXT, 245 * p2))
            d.text((78, 806), "+ «Защитник неба» опционально", font=ffit("+ «Защитник неба» опционально", MONO, 24, 600), fill=a(DIM, 238 * p2))

        rows = [("ПИТАНИЕ", "от внутреннего АКБ и внешних батарей"),
                ("СБОРКА", "возможно по вашему техзаданию")]
        for i, (k, v) in enumerate(rows):
            pp = c01((l - 1.2 - i * .22) / .45)
            if pp <= 0: continue
            yy = int(920 + i * 180 + (1 - eout(pp)) * 18)
            d.rectangle([42, yy, 1038, yy + 156], fill=(11, 16, 23, 250), outline=a(ACC2, int(140 * eout(pp))))
            d.rectangle([42, yy, 49, yy + 156], fill=a(ACC2, 255))
            d.text((86, yy + 16), k, font=F(MONO, 23), fill=a(ACC2, 240))
            d.text((86, yy + 56), v, font=ffit(v, MONO, 27, 900), fill=a(TXT, 245 * eout(pp)))

        q = c01((l - 2.0) / .45)
        if q > 0:
            d.rectangle([42, 1300, 1038, 1470], fill=(9, 26, 22, 250), outline=a(ACC, int(160 * q)))
            d.text((86, 1322), "ГЛАВНОЕ", font=F(MONO, 24), fill=a(ACC, 240 * q))
            d.text((86, 1360), "500 Вт · 200–5900 МГц", font=ffit("500 Вт · 200–5900 МГц", RUSSO, 40, 900), fill=a(TXT, 255 * q))
            d.text((86, 1418), "купол · от 100 м · 60 минут", font=F(MONO, 27), fill=a(DIM, 240 * q))

        q2 = c01((l - 2.5) / .45)
        if q2 > 0:
            d.text((44, 1520), "сборка и диапазоны — под конкретную задачу", font=F(MONO, 26), fill=a(DIM, 240 * q2))
            d.text((44, 1574), "16 кг за спиной, 500 ватт в эфире", font=F(MONO, 26), fill=a(ACC, 245 * q2))
    else:
        endcard(d, l - 5.40, "РЭБ-РЮКЗАК «ЗОНТ» S8")


SCENES = [(2.40, s1), (8.55, s2), (18.20, s3), (28.35, s4)]
TOTAL = 37.45
CUTS = [2.40, 5.10, 8.55, 12.40, 15.60, 18.20, 22.60, 26.20, 28.35, 31.20, 33.75]


def render_frame(t):
    idx = -1
    fn = None
    l = t
    if t >= SCENES[0][0]:
        idx = 0
        for i, (s0, _) in enumerate(SCENES):
            if t >= s0 - .001:
                idx = i
        st, fn = SCENES[idx]
        l = t - st

    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # подложка с лёгким движением
    zz = 1.0 + .02 * math.sin(t * .5)
    bg = BGIMG.resize((int(W * zz), int(H * zz)), Image.BILINEAR)
    ox = (bg.width - W) // 2 + int(8 * math.sin(t * .3))
    oy = (bg.height - H) // 2 + int(10 * math.cos(t * .23))
    base.paste(bg.crop((max(0, ox), max(0, oy), max(0, ox) + W, max(0, oy) + H)), (0, 0))

    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if fn:
        fn(cv, d, t, l)
    else:
        product(cv, "back", 540, 1000, 700, zoom=1.04, alpha=clamp(t / .6, 0, 1))
        p = eout(c01(t / .8))
        d.rectangle([0, 700, W, 1180], fill=(5, 8, 13, int(210 * p)))
        d.text((W // 2, 760), "«В ОКОПЕ»", font=F(RUSSO, 94), fill=a(TXT, int(255 * c01(t / .55))), anchor="ma")
        d.text((W // 2, 900), "СРЕДСТВА ПРОТИВОДЕЙСТВИЯ БПЛА", font=F(MONO, 28),
               fill=a(ACC, int(235 * c01((t - .3) / .55))), anchor="ma")
        w = 620 * eout(c01((t - .35) / .6))
        d.rectangle([W // 2 - w / 2, 958, W // 2 + w / 2, 962], fill=a(ACC, 220))

    out = Image.alpha_composite(base, cv)
    top(d, t, TOTAL)
    bottom(d)
    out = Image.alpha_composite(out, ov)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 12) % 4])
    for c in CUTS:
        dd = abs(t - c)
        if dd < .10:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 229, 160, 255)), (1 - dd / .10) * .16)
    return out.convert("RGB")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        tt = float(arg)
        render_frame(tt).save(os.path.join(BASE, f"qa_{tt:06.2f}.jpg"), quality=92)
        print("saved", tt)
