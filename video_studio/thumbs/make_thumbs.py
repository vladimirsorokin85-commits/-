#!/usr/bin/env python3
"""A/B thumbnails 1280x720 for «Окопная смекалка» — text composited over AI backgrounds."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

D = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(D, "..", "fonts")
W, H = 1280, 720
YEL, WHT, RED, BLK = (255, 204, 0), (255, 255, 255), (230, 30, 30), (0, 0, 0)


def font(n, s):
    return ImageFont.truetype(os.path.join(F, f"Roboto-{n}.woff"), s)


def bg(name, shift=0.5):
    im = Image.open(os.path.join(D, name)).convert("RGB")
    sc = H / im.height
    im = im.resize((round(im.width * sc), H), Image.LANCZOS)
    x = int((im.width - W) * shift)
    im = im.crop((x, 0, x + W, H))
    im = ImageEnhance.Contrast(im).enhance(1.12)
    return ImageEnhance.Color(im).enhance(1.15)


def shade(im, side="left", w=0.6, a=200):
    g = Image.new("L", (W, 1))
    for x in range(W):
        t = x / W if side == "left" else 1 - x / W
        g.putpixel((x, 0), int(a * max(0, 1 - t / w) ** 1.3))
    g = g.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), BLK), im, g)


def text(im, xy, s, f, fill, stroke=10, shadow=True):
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((xy[0] + 8, xy[1] + 10), s, font=f, fill=(0, 0, 0, 200),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
        im.paste(sh.filter(ImageFilter.GaussianBlur(8)), (0, 0), sh.filter(ImageFilter.GaussianBlur(8)))
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=BLK)
    return d.textbbox(xy, s, font=f, stroke_width=stroke)


def fit(s, n, maxw, start):
    sz = start
    while ImageFont.truetype(os.path.join(F, f"Roboto-{n}.woff"), sz).getlength(s) > maxw:
        sz -= 4
    return font(n, sz)


def plate(im, xy, s, f, bgc, fg=WHT, pad=(22, 10), rot=0):
    tw = f.getbbox(s)
    w, h = tw[2] + pad[0] * 2, tw[3] + pad[1] * 2
    p = Image.new("RGBA", (w, h), bgc + (255,))
    ImageDraw.Draw(p).text((pad[0], pad[1] - 2), s, font=f, fill=fg)
    if rot:
        p = p.rotate(rot, expand=True, resample=Image.BICUBIC)
    im.paste(p, xy, p)
    return xy[0] + p.width, xy[1] + p.height


def brand(im, xy=(34, 640)):
    plate(im, xy, "«В ОКОПЕ» · ОКОПНАЯ СМЕКАЛКА", font("Black", 30), (20, 20, 20), YEL, pad=(18, 8))


def ring(im, c, r, col=RED, w=12):
    d = ImageDraw.Draw(im)
    for k in range(w):
        d.ellipse((c[0] - r - k, c[1] - r - k, c[0] + r + k, c[1] + r + k), outline=col)


def arrow(im, a, b, col=RED, w=18):
    import math
    d = ImageDraw.Draw(im)
    d.line([a, b], fill=col, width=w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    L = 46
    p1 = (b[0] - L * math.cos(ang - 0.5), b[1] - L * math.sin(ang - 0.5))
    p2 = (b[0] - L * math.cos(ang + 0.5), b[1] - L * math.sin(ang + 0.5))
    d.polygon([(b[0] + 10 * math.cos(ang), b[1] + 10 * math.sin(ang)), p1, p2], fill=col)


# ---------- A: эмоция + деталь (чулок на прицеле) ----------
a = shade(bg("bg_a.jpg", 0.5), "left", 0.62, 215)
ring(a, (724, 330), 112)
arrow(a, (470, 520), (612, 420))
text(a, (40, 40), "ЧУЛОК", fit("ЧУЛОК", "Black", 470, 200), YEL, 12)
text(a, (44, 238), "НА ПРИЦЕЛЕ?!", fit("НА ПРИЦЕЛЕ?!", "Black", 470, 110), WHT, 9)
plate(a, (44, 380), "БЛИКА НЕТ · 0 ₽", font("Black", 46), RED, rot=3)
brand(a)
a.save(os.path.join(D, "thumb_A_chulok.jpg"), quality=92)

# ---------- B: экшен (FPV в рабицу) ----------
b = shade(bg("bg_b.jpg", 0.35), "left", 0.55, 190)
text(b, (36, 50), "ДРОН", fit("ДРОН", "Black", 470, 230), WHT, 12)
text(b, (40, 278), "НЕ ПРОБЬЁТ", fit("НЕ ПРОБЬЁТ", "Black", 500, 120), YEL, 10)
plate(b, (44, 440), "РАБИЦА + МИКРОВОЛНОВКА", font("Black", 38), RED, rot=-2)
brand(b)
b.save(os.path.join(D, "thumb_B_dron.jpg"), quality=92)

# ---------- C: любопытство (5 вещей) ----------
c = bg("bg_c.jpg", 0.5)
top = Image.new("L", (1, H))
for y in range(H):
    top.putpixel((0, y), int(210 * max(0, 1 - y / (H * 0.55)) ** 1.2))
c = Image.composite(Image.new("RGB", (W, H), BLK), c, top.resize((W, H)))
text(c, (40, 22), "5 ВЕЩЕЙ ЗА КОПЕЙКИ", fit("5 ВЕЩЕЙ ЗА КОПЕЙКИ", "Black", 1200, 150), YEL, 12)
text(c, (44, 192), "КОТОРЫЕ СПАСАЮТ ЖИЗНЬ", fit("КОТОРЫЕ СПАСАЮТ ЖИЗНЬ", "Black", 860, 74), WHT, 8)
for xy, s in (((300, 420), "0 ₽"), ((560, 380), "200 ₽"), ((905, 300), "500 ₽")):
    plate(c, xy, s, font("Black", 40), YEL, BLK, pad=(14, 6), rot=-6)
brand(c, (34, 652))
c.save(os.path.join(D, "thumb_C_5veshey.jpg"), quality=92)
print("ok")
