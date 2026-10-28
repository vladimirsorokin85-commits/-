#!/usr/bin/env python3
"""Сборка продающей инфографики: 4 слайда 1080×1350 (4:5) для VK / TG / Avito.

Запуск:  .venv/bin/python infographics/src/build.py
Результат: infographics/out/slide_01..04.png  +  pdf  +  zip
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
FONTS = REPO / "video_studio" / "toolkit" / "fonts"
OUT = REPO / "infographics" / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ── формат ────────────────────────────────────────────────────────────────
W, H = 1080, 1350
S = 2                      # суперсэмплинг
CW, CH = W * S, H * S

# ── палитра ───────────────────────────────────────────────────────────────
INK      = (13, 15, 18)      # фон
INK2     = (20, 23, 27)
PANEL    = (26, 30, 35)
PANEL_HI = (36, 41, 47)
YELLOW   = (246, 197, 26)
YELLOW_D = (196, 152, 12)
WHITE    = (243, 241, 235)
GREY     = (154, 161, 168)
GREY_D   = (86, 93, 100)
OLIVE    = (72, 84, 63)


def u(v: float) -> int:
    return int(round(v * S))


# ── шрифты ────────────────────────────────────────────────────────────────
_cache: dict = {}


def F(family: str, size: float, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    key = (family, size, weight)
    if key in _cache:
        return _cache[key]
    fn = {"oswald": "Oswald-VF.ttf", "mont": "Montserrat-VF.ttf"}[family]
    f = ImageFont.truetype(str(FONTS / fn), u(size))
    try:
        f.set_variation_by_name(weight.encode())
    except Exception:
        pass
    _cache[key] = f
    return f


# ── текст ─────────────────────────────────────────────────────────────────
def text_w(s: str, font: ImageFont.FreeTypeFont, track: float = 0.0) -> float:
    w = font.getlength(s)
    return w + track * S * max(len(s) - 1, 0)


def draw_text(img, xy, s, font, fill, anchor="la", track=0.0,
              shadow=None, shadow_blur=8, shadow_off=(0, 4),
              gradient=None, upper=False):
    """Рисует текст с трекингом, тенью и опциональным градиентом по заливке."""
    if upper:
        s = s.upper()
    tr = track * S
    x0, y0 = u(xy[0]), u(xy[1])
    total = text_w(s, font, track)

    if anchor[0] == "m":
        x0 -= total / 2
    elif anchor[0] == "r":
        x0 -= total
    if anchor[1] == "m":
        y0 -= font.size * 0.62
    elif anchor[1] == "b":
        y0 -= font.size * 1.02
    elif anchor[1] == "t":
        y0 -= font.size * 0.06

    if gradient is None and shadow is None:
        d = ImageDraw.Draw(img)
        if tr == 0:
            d.text((x0, y0), s, font=font, fill=fill)
        else:
            cx = x0
            for ch in s:
                d.text((cx, y0), ch, font=font, fill=fill)
                cx += font.getlength(ch) + tr
        return

    pad = u(40)
    box_w, box_h = int(total) + pad * 2, int(font.size * 1.6) + pad * 2
    layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    bx, by = pad, pad
    if tr == 0:
        ld.text((bx, by), s, font=font, fill=(255, 255, 255, 255))
    else:
        cx = bx
        for ch in s:
            ld.text((cx, by), ch, font=font, fill=(255, 255, 255, 255))
            cx += font.getlength(ch) + tr
    mask = layer.getchannel("A")

    if shadow is not None:
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(u(shadow_blur))))
        sh = Image.composite(
            Image.new("RGBA", layer.size, tuple(shadow) + (255,)),
            Image.new("RGBA", layer.size, (0, 0, 0, 0)), sh.getchannel("A"))
        img.alpha_composite(sh, (int(x0 - pad + u(shadow_off[0])),
                                 int(y0 - pad + u(shadow_off[1]))))

    if gradient is None:
        col = Image.new("RGBA", layer.size, tuple(fill) + (255,))
    else:
        c0, c1 = gradient
        g = Image.new("RGB", layer.size, c0)
        gd = ImageDraw.Draw(g)
        for i in range(layer.size[1]):
            t = i / max(layer.size[1] - 1, 1)
            gd.line([(0, i), (layer.size[0], i)],
                    fill=tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
        col = g.convert("RGBA")
    col.putalpha(mask)
    img.alpha_composite(col, (int(x0 - pad), int(y0 - pad)))


# ── графика ───────────────────────────────────────────────────────────────
def rrect(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle([u(box[0]), u(box[1]), u(box[2]), u(box[3])],
                        radius=u(r), fill=fill, outline=outline, width=u(width))


def rounded_panel(canvas, box, r=18, fill=PANEL, outline=None, glow=False):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if glow:
        g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle(
            [u(box[0]), u(box[1]), u(box[2]), u(box[3])], radius=u(r),
            fill=(232, 190, 32, 40))
        canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(u(18))))
    d.rounded_rectangle([u(box[0]), u(box[1]), u(box[2]), u(box[3])], radius=u(r),
                        fill=fill, outline=outline, width=u(1) if outline else 0)
    canvas.alpha_composite(layer)


def background(seed=7):
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, CH)[:, None]
    x = np.linspace(0, 1, CW)[None, :]
    # тёплый верхний свет -> глубокий низ
    base = np.zeros((CH, CW, 3), dtype=np.float32)
    for k in range(3):
        base[..., k] = INK[k] + (INK2[k] - INK[k]) * (1 - y)
    # радиальный блик за товаром
    cx, cy = 0.42, 0.44
    r = np.sqrt(((x - cx) * 1.05) ** 2 + (y - cy) ** 2)
    spot = np.clip(1 - r / 0.62, 0, 1) ** 2.2
    for k in range(3):
        base[..., k] += spot * (46 if k < 2 else 34)

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

    # диагональная штриховка 45°
    hatch = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hatch)
    step = u(14)
    for i in range(-CH, CW + CH, step):
        hd.line([(i, 0), (i + CH, CH)], fill=(255, 255, 255, 7), width=u(1))
    img.alpha_composite(hatch)

    # тонкая сетка
    grid = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for gx in range(0, W + 1, 60):
        gd.line([(u(gx), 0), (u(gx), CH)], fill=(255, 255, 255, 6), width=1)
    for gy in range(0, H + 1, 60):
        gd.line([(0, u(gy)), (CW, u(gy))], fill=(255, 255, 255, 6), width=1)
    img.alpha_composite(grid)

    # виньетка
    v = np.clip(1 - (((x - 0.5) ** 2 * 1.5 + (y - 0.5) ** 2 * 1.15) ** 0.5) / 0.78, 0, 1) ** 0.9
    v = (0.42 + 0.58 * v)[..., None]
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * v
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    return grain(img, 3.0)


def grain(img, amount=3.0, seed=3):
    rng = np.random.default_rng(seed)
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    n = rng.normal(0, amount, arr.shape[:2])[..., None]
    arr = np.clip(arr + n, 0, 255)
    return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")


def place(img, path, box, rotate=0.0, opacity=1.0, shadow=True, shadow_blur=28,
          shadow_alpha=170):
    """Вписывает PNG с альфой в рамку box (x0,y0,x1,y1) в дизайн-координатах."""
    prod = Image.open(path).convert("RGBA")
    if rotate:
        prod = prod.rotate(rotate, expand=True, resample=Image.BICUBIC)
    bw, bh = u(box[2] - box[0]), u(box[3] - box[1])
    k = min(bw / prod.width, bh / prod.height)
    prod = prod.resize((max(1, int(prod.width * k)), max(1, int(prod.height * k))),
                       Image.LANCZOS)
    if opacity < 1:
        a = prod.getchannel("A").point(lambda v: int(v * opacity))
        prod.putalpha(a)
    x = u(box[0]) + (bw - prod.width) // 2
    y = u(box[1]) + (bh - prod.height) // 2
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        m = prod.getchannel("A").filter(ImageFilter.GaussianBlur(u(shadow_blur)))
        sh.paste(Image.new("RGBA", prod.size, (0, 0, 0, shadow_alpha)), (x, y + u(14)), m)
        img.alpha_composite(sh)
    img.alpha_composite(prod, (x, y))
    return (x, y, prod.width, prod.height)


def brand_bar(canvas, page, total=4, label="ТАКТИЧЕСКАЯ ЭКИПИРОВКА · СДЭК ПО РОССИИ"):
    d = ImageDraw.Draw(canvas)
    y = 1272
    d.line([(u(64), u(y)), (u(W - 64), u(y))], fill=(255, 255, 255, 26), width=u(1))
    draw_text(canvas, (64, y + 18), "«В ОКОПЕ»", F("oswald", 26, "Bold"), YELLOW, track=1.2)
    draw_text(canvas, (188, y + 22), label, F("mont", 15, "Medium"), GREY_D, track=1.6)
    # пагинация
    for i in range(total):
        cx = W - 64 - (total - 1 - i) * 22
        on = (i + 1 == page)
        if on:
            d.rounded_rectangle([u(cx - 11), u(y + 26), u(cx + 11), u(y + 32)],
                                radius=u(3), fill=YELLOW)
        else:
            d.ellipse([u(cx - 3.5), u(y + 26), u(cx + 3.5), u(y + 33)], fill=GREY_D)


def kicker(canvas, x, y, s, color=YELLOW):
    f = F("mont", 16, "Bold")
    pad = 13
    w = text_w(s, f, 1.8) / S
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([u(x), u(y), u(x + w + pad * 2), u(y + 36)],
                        radius=u(4), fill=(246, 197, 26, 26),
                        outline=(246, 197, 26, 110), width=u(1))
    d.rectangle([u(x), u(y), u(x + 4), u(y + 36)], fill=YELLOW)
    draw_text(canvas, (x + pad + 4, y + 18), s, f, color, anchor="lm", track=1.8)


# ── слайд 1: обложка ──────────────────────────────────────────────────────
def slide1():
    c = background(seed=11)
    kicker(c, 64, 74, "В НАЛИЧИИ · БЕЗ ОЖИДАНИЯ")

    draw_text(c, (62, 132), "ПЕРЕВЯЗОЧНЫЙ", F("oswald", 66, "SemiBold"), WHITE, track=2.0)
    draw_text(c, (62, 196), "КОМПРЕССИОННЫЙ", F("oswald", 66, "SemiBold"), WHITE, track=2.0)
    draw_text(c, (58, 258), "БАНДАЖ", F("oswald", 118, "Bold"), None, track=1.0,
              gradient=(YELLOW, (216, 158, 20)), shadow=(0, 0, 0), shadow_blur=16,
              shadow_off=(0, 8))

    draw_text(c, (64, 392), "Израильский · 6 дюймов · стерильный",
              F("mont", 24, "Medium"), GREY, track=0.4)

    place(c, ROOT / "bandage_1.png", (96, 452, 984, 900), shadow_blur=34)

    # три буллета
    bullets = [("СТЕРИЛЬНО", "заводская упаковка"),
               ("ОДНОЙ РУКОЙ", "фиксатор-барашек"),
               ("30 СЕКУНД", "до полной фиксации")]
    x = 64
    bw = (W - 128 - 2 * 14) / 3
    for i, (t, sub) in enumerate(bullets):
        bx = x + i * (bw + 14)
        rounded_panel(c, (bx, 930, bx + bw, 1042), r=12, fill=(24, 28, 33, 235),
                      outline=(255, 255, 255, 22))
        ImageDraw.Draw(c).rectangle([u(bx), u(930), u(bx + 3), u(1042)], fill=YELLOW)
        draw_text(c, (bx + 20, 956), t, F("oswald", 25, "Bold"), WHITE, track=1.0)
        draw_text(c, (bx + 20, 994), sub, F("mont", 14, "Medium"), GREY, track=0.2)

    # хук
    rounded_panel(c, (64, 1072, W - 64, 1224), r=16, fill=(246, 197, 26, 20),
                  outline=(246, 197, 26, 120))
    draw_text(c, (88, 1100), "Накладывается одной рукой —", F("oswald", 40, "Bold"),
              WHITE, track=0.6)
    draw_text(c, (88, 1150), "и держит даже при сильном кровотечении",
              F("oswald", 40, "Bold"), YELLOW, track=0.6)

    brand_bar(c, 1)
    return c


# ── слайд 2: почему берут ─────────────────────────────────────────────────
def slide2():
    c = background(seed=22)
    kicker(c, 64, 74, "ПОЧЕМУ ЕГО БЕРУТ В АПТЕЧКУ")
    draw_text(c, (62, 128), "4 ПРИЧИНЫ", F("oswald", 92, "Bold"), None, track=0.5,
              gradient=(WHITE, (176, 181, 187)), shadow=(0, 0, 0), shadow_blur=14,
              shadow_off=(0, 6))
    draw_text(c, (64, 232), "взять именно этот бандаж", F("oswald", 34, "Light"),
              YELLOW, track=1.4)

    items = [
        ("01", "ОДНОЙ РУКОЙ",
         "Фиксатор-барашек затягивается\nсам и стопорит ленту. Помощник\nне нужен."),
        ("02", "30 СЕКУНД",
         "Развернул, наложил, затянул.\nБез узлов, булавок и\nдолгих манипуляций."),
        ("03", "ДАВЛЕНИЕ ПОД КОНТРОЛЕМ",
         "Силу сжатия регулируешь на ходу:\nподтянул при кровотечении,\nослабил при отёке."),
        ("04", "НЕ СПОЛЗАЕТ",
         "Эластичная лента с фиксатором\nдержится при движении,\nтранспортировке и беге."),
    ]
    y = 306
    for num, title, body in items:
        rounded_panel(c, (64, y, W - 64, y + 196), r=14, fill=(23, 27, 32, 240),
                      outline=(255, 255, 255, 20))
        ImageDraw.Draw(c).rectangle([u(64), u(y), u(68), u(y + 196)], fill=YELLOW)
        draw_text(c, (96, y + 34), num, F("oswald", 54, "Bold"), (255, 255, 255, 34), track=0)
        draw_text(c, (96, y + 34), title, F("oswald", 39, "Bold"), WHITE, track=0.8)
        yy = y + 100
        for line in body.split("\n"):
            draw_text(c, (98, yy), line, F("mont", 19, "Regular"), GREY, track=0.2)
            yy += 32
        y += 216

    # подпись-плашка
    rounded_panel(c, (64, 1200, W - 64, 1244 + 30), r=10, fill=(246, 197, 26, 240))
    draw_text(c, (W / 2, 1237), "ЧЕМ БОЛЬШЕ КРОВОТЕЧЕНИЕ — ТЕМ ВАЖНЕЕ ДАВЛЕНИЕ, А НЕ КРАСОТА УЗЛА",
              F("oswald", 25, "Bold"), (26, 22, 8), anchor="mm", track=1.2)

    brand_bar(c, 2)
    return c


# ── слайд 3: как наложить ─────────────────────────────────────────────────
def slide3():
    c = background(seed=33)
    kicker(c, 64, 74, "ИНСТРУКЦИЯ · 3 ШАГА")
    draw_text(c, (62, 128), "30 СЕКУНД", F("oswald", 92, "Bold"), None, track=0.5,
              gradient=(YELLOW, (212, 152, 16)), shadow=(0, 0, 0), shadow_blur=14,
              shadow_off=(0, 6))
    draw_text(c, (64, 232), "и повязка держит", F("oswald", 40, "Light"), WHITE, track=1.2)

    steps = [
        ("1", "РАЗОРВИ УПАКОВКУ", "потяни за насечку — пакет\nвскрывается одним движением", 300),
        ("2", "НАЛОЖИ ПОДУШЕЧКУ", "подушечка точно на рану,\nленту ведёшь по кругу", 660),
        ("3", "ЗАТЯНИ БАРАШЕК", "фиксатор стопорит ленту —\nдавление остаётся нужным", 1020),
    ]
    for num, title, body, y in steps:
        rounded_panel(c, (64, y, W - 64, y + 288), r=16, fill=(23, 27, 32, 242),
                      outline=(255, 255, 255, 22))
        # номер в круге
        d = ImageDraw.Draw(c)
        d.ellipse([u(96), u(y + 40), u(186), u(y + 130)], fill=(246, 197, 26),
                  outline=(255, 255, 255, 60), width=u(2))
        draw_text(c, (141, y + 86), num, F("oswald", 62, "Bold"), (20, 17, 6), anchor="mm")
        draw_text(c, (214, y + 52), title, F("oswald", 38, "Bold"), WHITE, track=0.9)
        yy = y + 110
        for line in body.split("\n"):
            draw_text(c, (216, yy), line, F("mont", 19, "Regular"), GREY, track=0.2)
            yy += 31
        # миниатюра товара
        place(c, ROOT / "bandage_3.png", (W - 380, y + 56, W - 96, y + 240),
              shadow_blur=16, shadow_alpha=120)

    rounded_panel(c, (64, 1322 - 60, W - 64, 1322 - 6), r=8, fill=(0, 0, 0, 0))
    draw_text(c, (64, 1240), "Итого: без узлов, без булавок, без второй пары рук.",
              F("mont", 20, "Medium"), (233, 231, 224), track=0.3)
    brand_bar(c, 3)
    return c


# ── слайд 4: CTA ──────────────────────────────────────────────────────────
def slide4():
    c = background(seed=44)
    kicker(c, 64, 74, "ДОСТАВКА СДЭК · ВСЯ РОССИЯ")
    draw_text(c, (62, 126), "В НАЛИЧИИ", F("oswald", 104, "Bold"), None, track=1.0,
              gradient=(YELLOW, (214, 156, 18)), shadow=(0, 0, 0), shadow_blur=16,
              shadow_off=(0, 7))
    draw_text(c, (64, 240), "тактический бандаж 6″ · стерильный", F("mont", 23, "Medium"),
              GREY, track=0.4)

    place(c, ROOT / "bandage_2.png", (150, 288, 930, 620), shadow_blur=30)

    # сценарии
    chips = ["авто и дом", "поход и рыбалка", "полигон и служба", "аптечка и медицина"]
    x, y = 64, 660
    f = F("mont", 19, "SemiBold")
    for i, s in enumerate(chips):
        w = text_w(s, f, 0.3) / S + 44
        if x + w > W - 64:
            x, y = 64, y + 62
        rounded_panel(c, (x, y, x + w, y + 48), r=24, fill=(30, 34, 40, 245),
                      outline=(255, 255, 255, 30))
        draw_text(c, (x + 22, y + 24), s, f, (222, 220, 213), anchor="lm", track=0.3)
        x += w + 12

    # СДЭК
    rounded_panel(c, (64, 790, W - 64, 1000), r=16, fill=(23, 27, 32, 242),
                  outline=(246, 197, 26, 90))
    draw_text(c, (96, 816), "ОТПРАВКА СО СКЛАДА", F("mont", 15, "Bold"), YELLOW, track=2.0)
    draw_text(c, (96, 846), "СДЭК по всей России", F("oswald", 46, "Bold"), WHITE, track=0.6)
    draw_text(c, (96, 910), "Есть в наличии — не ждём поставку. Отправим\nв день заказа, трек-номер пришлём в чат.",
              F("mont", 19, "Regular"), GREY, track=0.2)
    # иконка коробки/грузовика — простой пиктограф
    d = ImageDraw.Draw(c)
    bx, by = W - 232, 862
    d.rounded_rectangle([u(bx), u(by), u(bx + 120), u(by + 76)], radius=u(8),
                        outline=YELLOW, width=u(3))
    d.line([(u(bx), u(by + 26)), (u(bx + 120), u(by + 26))], fill=YELLOW, width=u(3))
    d.line([(u(bx + 60), u(by)), (u(bx + 60), u(by + 26))], fill=YELLOW, width=u(3))
    for cx in (bx + 26, bx + 94):
        d.ellipse([u(cx - 12), u(by + 66), u(cx + 12), u(by + 90)], outline=YELLOW,
                  width=u(3), fill=INK)

    # CTA
    d.rounded_rectangle([u(64), u(1024), u(W - 64), u(1180)], radius=u(16), fill=YELLOW)
    draw_text(c, (96, 1050), "НАПИШИТЕ В СООБЩЕНИЯ", F("oswald", 44, "Bold"),
              (24, 20, 8), track=0.8)
    draw_text(c, (96, 1108), "Помогу с выбором размера и количества — ответ в течение дня.",
              F("mont", 19, "SemiBold"), (56, 44, 14), track=0.2)
    d.polygon([(u(W - 148), u(1078)), (u(W - 96), u(1078)), (u(W - 122), u(1128))], fill=(24, 20, 8))

    brand_bar(c, 4, label="ИЗРАИЛЬСКИЙ ПЕРЕВЯЗОЧНЫЙ БАНДАЖ · 6 ДЮЙМОВ")
    return c


def main():
    slides = []
    for i, fn in enumerate((slide1, slide2, slide3, slide4), start=1):
        img = fn().convert("RGB").resize((W, H), Image.LANCZOS)
        p = OUT / f"slide_{i:02d}.png"
        img.save(p, quality=95)
        slides.append(img)
        print("ok", p)

    pdf = OUT / "bandage_infographic.pdf"
    slides[0].save(pdf, save_all=True, append_images=slides[1:], resolution=150)
    print("ok", pdf)


if __name__ == "__main__":
    main()
