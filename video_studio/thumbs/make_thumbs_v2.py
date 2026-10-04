#!/usr/bin/env python3
"""Thumbnails v2 — loud, extravagant style: 3D extruded gradient text, double stroke, tilted stickers."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

D = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(D, "..", "fonts", "Roboto-Black.woff")
W, H = 1280, 720


def F(s):
    return ImageFont.truetype(FONT, s)


def bg(name, shift=0.5, sat=1.25, con=1.12):
    im = Image.open(os.path.join(D, name)).convert("RGB")
    sc = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    x = int((im.width - W) * shift)
    im = im.crop((x, 0, x + W, H))
    im = ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(con)).enhance(sat)
    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.45 * (((xx - W / 2) / (W / 1.3)) ** 2 + ((yy - H / 2) / (H / 1.2)) ** 2)
    a = np.asarray(im).astype(float) * np.clip(v, 0.4, 1)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def shade_left(im, w=0.5, a=170):
    g = np.clip(1 - np.linspace(0, 1, W) / w, 0, 1) ** 1.4 * a
    m = Image.fromarray(np.tile(g, (H, 1)).astype(np.uint8))
    return Image.composite(Image.new("RGB", (W, H)), im, m)


def gradient(size, top, bot):
    g = np.linspace(0, 1, size[1])[:, None, None]
    arr = np.array(top)[None, None] * (1 - g) + np.array(bot)[None, None] * g
    return Image.fromarray(np.repeat(arr, size[0], 1).astype(np.uint8))


def mega(im, xy, s, size, top=(255, 240, 80), bot=(255, 140, 0), rot=-4, depth=14, maxw=None):
    """3D-extruded, gradient-filled, double-stroked word art."""
    f = F(size)
    if maxw:
        while f.getlength(s) > maxw:
            size -= 4
            f = F(size)
    bb = f.getbbox(s, stroke_width=18)
    tw, th = bb[2] - bb[0] + depth + 40, bb[3] - bb[1] + depth + 40
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = 20 - bb[0], 20 - bb[1]
    # extrusion
    for k in range(depth, 0, -1):
        d.text((ox + k, oy + k), s, font=f, fill=(25, 10, 0, 255), stroke_width=12, stroke_fill=(25, 10, 0, 255))
    # outer white stroke + inner black stroke
    d.text((ox, oy), s, font=f, fill=(0, 0, 0, 255), stroke_width=18, stroke_fill=(255, 255, 255, 255))
    d.text((ox, oy), s, font=f, fill=(0, 0, 0, 255), stroke_width=9, stroke_fill=(0, 0, 0, 255))
    # gradient fill via mask
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).text((ox, oy), s, font=f, fill=255)
    grad = gradient((tw, th), top, bot)
    layer.paste(grad, (0, 0), mask)
    # glossy highlight on upper half
    hi = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(hi).rectangle((0, 0, tw, oy + (bb[3] - bb[1]) * 0.45 + bb[1]), fill=70)
    hi = Image.composite(hi, Image.new("L", (tw, th), 0), mask)
    layer.paste(Image.new("RGB", (tw, th), (255, 255, 255)), (0, 0), hi)
    layer = layer.rotate(rot, expand=True, resample=Image.BICUBIC)
    # glow / shadow
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.85)))
    im.paste(sh, (xy[0] + 6, xy[1] + 10), sh)
    im.paste(layer, xy, layer)
    return xy[0] + layer.width, xy[1] + layer.height


def sticker(im, xy, s, size, bgc=(230, 20, 30), fg=(255, 255, 255), rot=5, pad=(26, 12)):
    f = F(size)
    bb = f.getbbox(s)
    w, h = bb[2] - bb[0] + pad[0] * 2, bb[3] - bb[1] + pad[1] * 2
    p = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    d.rounded_rectangle((8, 8, 8 + w, 8 + h), 12, fill=bgc + (255,), outline=(255, 255, 255, 255), width=6)
    d.text((8 + pad[0] - bb[0], 8 + pad[1] - bb[1]), s, font=f, fill=fg)
    p = p.rotate(rot, expand=True, resample=Image.BICUBIC)
    sh = Image.new("RGBA", p.size, (0, 0, 0, 0))
    sh.putalpha(p.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .7)))
    im.paste(sh, (xy[0] + 6, xy[1] + 8), sh)
    im.paste(p, xy, p)


def brand(im, xy=(26, 22)):
    sticker(im, xy, "«В ОКОПЕ»", 34, bgc=(15, 15, 15), fg=(255, 204, 0), rot=0, pad=(18, 8))


def arrow(im, a, b, col=(255, 255, 255), w=16):
    import math
    d = ImageDraw.Draw(im)
    for c, ww in (((0, 0, 0), w + 10), (col, w)):
        d.line([a, b], fill=c, width=ww)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = 44 + (ww - w)
        p1 = (b[0] - L * math.cos(ang - .55), b[1] - L * math.sin(ang - .55))
        p2 = (b[0] - L * math.cos(ang + .55), b[1] - L * math.sin(ang + .55))
        d.polygon([(b[0] + 6 * math.cos(ang), b[1] + 6 * math.sin(ang)), p1, p2], fill=c)


# 1 — «5 ХИТРОСТЕЙ ЗА КОПЕЙКИ» (под название ролика)
im = shade_left(bg("v2_bg1.jpg", 0.75), 0.55, 120)
mega(im, (10, 70), "5 ХИТРОСТЕЙ", 150, maxw=720, rot=-5)
mega(im, (24, 260), "ЗА КОПЕЙКИ", 132, top=(255, 255, 255), bot=(200, 220, 255), maxw=660, rot=-5)
sticker(im, (70, 470), "СПАСАЮТ ЖИЗНЬ", 58, rot=4)
brand(im)
im.save(os.path.join(D, "THUMB_1_5hitrostey.jpg"), quality=93)

# 2 — чулок против блика
im = shade_left(bg("v2_bg2.jpg", 0.55, sat=1.15), 0.45, 150)
mega(im, (6, 60), "ЧУЛОК", 190, maxw=520, rot=-6)
mega(im, (10, 270), "ПРОТИВ", 104, top=(255, 255, 255), bot=(220, 220, 220), maxw=430, rot=-6)
mega(im, (10, 400), "СНАЙПЕРА", 104, top=(255, 90, 90), bot=(200, 0, 0), maxw=470, rot=-6)
sticker(im, (880, 40), "БЛИК", 50, rot=-6)
sticker(im, (720, 560), "БЛИКА НЕТ · 0 ₽", 46, bgc=(30, 160, 40), rot=4)
arrow(im, (950, 140), (900, 250))
arrow(im, (820, 560), (790, 470))
brand(im, (26, 640))
im.save(os.path.join(D, "THUMB_2_chulok.jpg"), quality=93)

# 3 — дрон не пройдёт
im = shade_left(bg("v2_bg3.jpg", 0.6), 0.5, 140)
mega(im, (8, 50), "ДРОН", 210, top=(255, 255, 255), bot=(210, 225, 255), maxw=520, rot=-6)
mega(im, (10, 290), "НЕ ПРОЙДЁТ!", 128, maxw=640, rot=-6)
sticker(im, (60, 500), "РАБИЦА ЗА КОПЕЙКИ", 50, rot=4)
brand(im)
im.save(os.path.join(D, "THUMB_3_dron.jpg"), quality=93)
print("ok")
