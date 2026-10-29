#!/usr/bin/env python3
"""Сборка финальных слайдов: military-макеты из gen2/ + логотип-патч «В ОКОПЕ» + футер.

    python infographics/src/compose.py

out/sw_1_cover.jpg ... sw_4_cta.jpg (1080x1350) + sw_infographic.pdf
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
GEN = ROOT / "gen2"
OUT = ROOT / "out"
ASSETS = ROOT / "assets"
FONTS = REPO / "video_studio" / "toolkit" / "fonts"
OUT.mkdir(exist_ok=True)

W, H = 1080, 1350
S = 2  # суперсэмплинг

KHAKI = (196, 184, 138)
KHAKI_D = (128, 120, 86)
INK = (14, 15, 12)
YELLOW = (216, 178, 42)

SLIDES = [
    # файл,                  правки «IR SAFE» (cx, cy, w, h, angle), подпись футера
    ("sw_1_cover.png", None, "ТАКТИЧЕСКАЯ ЭКИПИРОВКА · СДЭК ПО РОССИИ"),
    ("sw_2_modes.png", None, "ШЛЕМНЫЙ ФОНАРЬ SIDEWINDER GEN 3", 0, "note"),
    ("sw_3_kit.png", None, "ПОЛЕВОЙ КОМПЛЕКТ · СТЕРИЛЬНО, ПРОЧНО, ПРОВЕРЕНО"),
    ("sw_4_cta.png", None, "ТАКТИЧЕСКИЙ ФОНАРЬ · GEN 3", -58),
]


def u(v):
    return int(round(v * S))


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), u(size))


def place_logo(canvas, path, x, y, width, angle=-2.5, alpha=255):
    logo = Image.open(path).convert("RGBA")
    k = u(width) / logo.width
    logo = logo.resize((u(width), int(logo.height * k)), Image.LANCZOS)
    if alpha < 255:
        a = logo.getchannel("A").point(lambda v: int(v * alpha / 255))
        logo.putalpha(a)
    # тень под патчем
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    m = logo.getchannel("A").filter(ImageFilter.GaussianBlur(u(10)))
    sh.paste(Image.new("RGBA", logo.size, (0, 0, 0, 150)), (u(x), u(y) + u(7)), m)
    canvas.alpha_composite(sh)
    if angle:
        pad = u(20)
        big = Image.new("RGBA", (logo.width + 2 * pad, logo.height + 2 * pad), (0, 0, 0, 0))
        big.paste(logo, (pad, pad), logo)
        big = big.rotate(angle, expand=False, resample=Image.BICUBIC)
        canvas.alpha_composite(big, (u(x) - pad, u(y) - pad))
    else:
        canvas.alpha_composite(logo, (u(x), u(y)))


def ir_label(canvas, box):
    """Ретушь зеркальной надписи на корпусе: заплатка в цвет корпуса + чистый шильдик."""
    cx, cy, w, h, ang = box
    pad = u(16)
    bw, bh = u(w) + 2 * pad, u(h) + 2 * pad

    # цвет корпуса берём вокруг пятна
    arr = np.asarray(canvas.convert("RGB"), dtype=np.float32)
    x0, y0 = int(u(cx - w / 2 - 26)), int(u(cy - h / 2 - 26))
    x1, y1 = int(u(cx + w / 2 + 26)), int(u(cy + h / 2 + 26))
    patch = arr[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
    lum = patch.mean(axis=1)
    keep = patch[(lum > 90) & (lum < 205)]
    base_col = np.median(keep, axis=0) if len(keep) > 50 else np.median(patch, axis=0)

    layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    # градиентная заливка в цвет корпуса + тканевая фактура
    col = np.zeros((bh, bw, 3), np.float32)
    gy = np.linspace(-1, 1, bh)[:, None, None]
    col[:] = base_col
    col *= 1 + gy * 0.06
    rng = np.random.default_rng(4)
    col += rng.normal(0, 5.0, (bh, bw, 1))
    body = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert("RGBA")

    # мягкая маска-эллипс, чтобы заплатка растворялась в корпусе
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad * 0.15, pad * 0.15, bw - pad * 0.15, bh - pad * 0.15],
                                          radius=bh * 0.30, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(bh * 0.22))
    body.putalpha(mask)
    layer.alpha_composite(body)

    # чистая надпись «IR SAFE →»
    d = ImageDraw.Draw(layer)
    f = font("Oswald-VF.ttf", max(10, int(h * 0.44)))
    try:
        f.set_variation_by_name(b"SemiBold")
    except Exception:
        pass
    txt = "IR SAFE"
    tw = d.textlength(txt, font=f)
    ty = bh / 2
    tx = bw / 2 - (tw + u(13)) / 2
    d.text((tx, ty), txt, font=f, fill=(236, 232, 220, 255), anchor="lm")
    ax = tx + tw + u(4)
    d.line([(ax, ty), (ax + u(9), ty)], fill=(236, 232, 220, 255), width=max(2, u(1.2)))
    d.polygon([(ax + u(9), ty), (ax + u(5), ty - u(3.2)), (ax + u(5), ty + u(3.2))],
              fill=(236, 232, 220, 255))
    # надпись тоже чуть «вплавляем»
    lay = layer.filter(ImageFilter.GaussianBlur(0.6))
    lay = lay.rotate(ang, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(lay, (int(u(cx)) - lay.width // 2, int(u(cy)) - lay.height // 2))


def product_crop():
    """Чистый кадр товара без надписей — из обложки."""
    im = Image.open(GEN / "sw_1_cover.png").convert("RGB")
    w, h = im.size
    box = (int(w * 0.13), int(h * 0.385), int(w * 0.87), int(h * 0.695))
    return im.crop(box)


def note_block(canvas):
    """Плашка внизу слайда 2: закрывает пустоту и «зеркальный» кадр."""
    x0, y0, x1, y1 = 56, 1034, 1024, 1206
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([u(x0), u(y0), u(x1), u(y1)], radius=u(10),
                        fill=(38, 42, 30, 246), outline=KHAKI_D + (200,), width=u(1.5))
    d.rounded_rectangle([u(x0 + 10), u(y0 + 8), u(x1 - 10), u(y1 - 8)], radius=u(7),
                        outline=KHAKI_D + (120,), width=u(1))
    canvas.alpha_composite(layer)

    # товар слева
    prod = product_crop()
    box_w, box_h = u(132), u(132)
    k = min(box_w / prod.width, box_h / prod.height)
    prod = prod.resize((int(prod.width * k), int(prod.height * k)), Image.LANCZOS)
    canvas.alpha_composite(prod.convert("RGBA"), (u(x0 + 24), u(y0 + 30)))

    f1 = font("Oswald-VF.ttf", 33)
    try:
        f1.set_variation_by_name(b"Bold")
    except Exception:
        pass
    f2 = font("JetBrainsMono-VF.ttf", 15)
    d2 = ImageDraw.Draw(canvas)
    d2.text((u(x0 + 180), u(y0 + 32)), "ИК-РЕЖИМ БЕЗ ЗАСВЕТА", font=f1,
            fill=(232, 228, 214, 255), anchor="la")
    d2.text((u(x0 + 180), u(y0 + 82)), "Глазом не видно — в приборе ночного видения видно.",
            font=f2, fill=(168, 162, 132, 255), anchor="la")
    d2.text((u(x0 + 180), u(y0 + 110)), "Светишь скрытно, когда нельзя светиться.",
            font=f2, fill=(168, 162, 132, 255), anchor="la")


def footer(canvas, label, page, total=4):
    d = ImageDraw.Draw(canvas)
    y = 1258
    d.line([(u(48), u(y)), (u(W - 48), u(y))], fill=KHAKI_D + (110,), width=u(1))
    place_logo(canvas, ASSETS / "logo_vokope_small.png", 48, y + 12, 186, angle=-1.5)
    f = font("JetBrainsMono-VF.ttf", 14)
    draw = ImageDraw.Draw(canvas)
    draw.text((u(56 + 196), u(y + 44)), label, font=f, fill=(158, 152, 124, 255), anchor="lm")
    # пагинация
    for i in range(total):
        cx = W - 60 - (total - 1 - i) * 24
        if i + 1 == page:
            d.rounded_rectangle([u(cx - 11), u(y + 21), u(cx + 11), u(y + 31)],
                                radius=u(2), fill=YELLOW + (255,))
        else:
            d.rectangle([u(cx - 4), u(y + 23), u(cx + 4), u(y + 29)],
                        outline=KHAKI_D + (200,), width=u(1))


def build(src, ir, label, page, dy=0, extra=None):
    im = Image.open(GEN / src).convert("RGB")
    im = im.resize((u(W), int(im.height * u(W) / im.width)), Image.LANCZOS)
    # добираем до нужной высоты, если не хватило — тянем фон вниз
    if im.height < u(H):
        pad_h = u(H) - im.height
        strip = im.crop((0, im.height - u(30), u(W), im.height)).resize((u(W), pad_h + u(30)),
                                                                        Image.LANCZOS)
        base = Image.new("RGB", (u(W), u(H)))
        base.paste(im, (0, 0))
        base.paste(strip, (0, im.height))
        im = base
    else:
        im = im.crop((0, 0, u(W), u(H)))

    # сдвиг кадра по вертикали (чтобы нижний текст не лез в футер)
    if dy:
        base = Image.new("RGB", (u(W), u(H)))
        top = im.crop((0, 0, u(W), 4)).resize((u(W), u(60)), Image.LANCZOS)
        bot = im.crop((0, im.height - 4, u(W), im.height)).resize((u(W), u(120)), Image.LANCZOS)
        base.paste(bot, (0, 0))
        base.paste(im, (0, u(dy)))
        base.paste(top.filter(ImageFilter.GaussianBlur(6)), (0, u(dy) + im.height))
        im = base
    canvas = im.convert("RGBA")

    if ir:
        ir_label(canvas, ir)

    # затемнение под футером
    if extra == "note":
        note_block(canvas)

    gh = u(150)
    grad = Image.new("RGBA", (u(W), gh), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(gh):
        a = int(165 * (i / gh) ** 0.75)
        gd.line([(0, i), (u(W), i)], fill=INK + (a,))
    canvas.alpha_composite(grad, (0, u(H) - gh))
    footer(canvas, label, page)

    out = canvas.convert("RGB").resize((W, H), Image.LANCZOS)
    out = out.filter(ImageFilter.UnsharpMask(radius=2.0, percent=45, threshold=2))
    p = OUT / src.replace(".png", ".jpg")
    out.save(p, quality=94, subsampling=1)
    print("ok", p)
    return p


if __name__ == "__main__":
    made = []
    for i, item in enumerate(SLIDES):
        src, ir, label = item[:3]
        dy = item[3] if len(item) > 3 else 0
        extra = item[4] if len(item) > 4 else None
        made.append(build(src, ir, label, i + 1, dy, extra))
    imgs = [Image.open(p).convert("RGB") for p in made]
    pdf = OUT / "sw_infographic.pdf"
    imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=150.0)
    print("ok", pdf)
