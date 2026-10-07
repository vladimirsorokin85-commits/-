#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бланк заказа «В ОКОПЕ» — стиль «полевой бланк» (крафт-бумага, оливковые чернила, штамп).

Запуск:
    python3 media/blank/blank.py media/blank/order.json            -> media/blank/out.png
    python3 media/blank/blank.py media/blank/order.json card.png   -> card.png

order.json:
{
  "date": "07.10.2026",                      # дата проверки наличия -> в штамп
  "items": [
    {"photo": "catalog/photos/00895/00895_1.jpg",   # ТОЛЬКО фото поставщика
     "name":  "Подсумок под пулеметный короб 100 / ленту 200",
     "sub":   "цвет «мох» · MOLLE · фастекс",        # цвет / размер / особенности
     "qty":   4,
     "price": 1500}                                  # розничная цена ВЛАДЕЛЬЦА
  ]
}
Высота картинки подстраивается под число позиций автоматически.
"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIA = os.path.join(ROOT, "media")

# ---------- палитра ----------
PAPER = (236, 228, 206)
GRID = (218, 209, 184)
INK = (58, 66, 38)
TEXT = (40, 43, 30)
MUTED = (112, 114, 92)
FRAME = (96, 106, 66)
TINT = (226, 217, 192)
STAMP = (46, 118, 58)
WHITE = (250, 248, 242)

W, M = 1080, 50
COL_PHOTO, COL_NAME, COL_QTY = 210, 470, 110
ROW_H, HEAD_H = 200, 52

LOG_DIRS = [
    os.path.join(MEDIA, "fonts"),
    os.path.join(ROOT, "video_studio", "toolkit", "fonts"),
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
]

FONT_ALIASES = {
    "RussoOne.ttf": ["RussoOne.ttf", "RussoOne-Regular.ttf"],
    "Oswald.ttf": ["Oswald.ttf", "Oswald-VF.ttf"],
    "Oswald-Regular.ttf": ["Oswald.ttf", "Oswald-VF.ttf"],
    "PTSans-Bold.ttf": ["PTSans-Bold.ttf", "Montserrat-VF.ttf", "DejaVuSans-Bold.ttf"],
    "PTSans-Regular.ttf": ["PTSans-Regular.ttf", "Montserrat-VF.ttf", "DejaVuSans.ttf"],
}
VARIATION_FOR = {"PTSans-Bold.ttf": "Bold", "PTSans-Regular.ttf": "Regular"}
_font_cache = {}


def find_font_file(name):
    for cand in FONT_ALIASES.get(name, [name]):
        for d in LOG_DIRS:
            p = os.path.join(d, cand)
            if os.path.exists(p):
                return p
    return None


def font(name, size, weight=None):
    key = (name, size, weight)
    if key in _font_cache:
        return _font_cache[key]
    path = find_font_file(name)
    if not path:
        f = ImageFont.load_default()
        _font_cache[key] = f
        return f
    f = ImageFont.truetype(path, size)
    for w in (weight, VARIATION_FOR.get(name)):
        if not w:
            continue
        try:
            f.set_variation_by_name(w)
            break
        except Exception:  # noqa: BLE001 — шрифт может быть не вариативным
            try:
                f.set_variation_by_axes([700 if str(w).lower().startswith(("b", "s")) else 400])
                break
            except Exception:  # noqa: BLE001
                continue
    _font_cache[key] = f
    return f


def fmt_money(n):
    """None = цену задаёт владелец в чате — так и пишем, ничего не выдумываем."""
    if n is None:
        return "по запросу"
    return f"{int(round(n)):,}".replace(",", " ") + " ₽"


def tracked(d, xy, text, f, fill, tracking=2, anchor="l"):
    """Текст с межбуквенным интервалом. anchor: l / m / r по X; Y = верх строки."""
    x, y = xy
    if not text:
        return 0
    total = sum(f.getlength(ch) for ch in text) + tracking * (len(text) - 1)
    if anchor == "m":
        x -= total / 2
    elif anchor == "r":
        x -= total
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking
    return total


def wrap(text, f, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def ellipsize(text, f, width):
    text = str(text)
    if f.getlength(text) <= width:
        return text
    while text and f.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def dashed_h(d, x0, x1, y, fill, dash=10, gap=7, width=2):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=fill, width=width)
        x += dash + gap


# ---------------------------------------------------------------- логотип

LOGO_CANDIDATES = ("logo.png", "logo.webp", "logo.jpg", "logo.jpeg", "logo.PNG", "logo.JPG")


def logo_asset():
    """Логотип магазина: media/logo.png (или .webp/.jpg — какой положили)."""
    for name in LOGO_CANDIDATES:
        p = os.path.join(MEDIA, name)
        if os.path.exists(p):
            return p
    return os.path.join(MEDIA, "logo.png")


def rounded_logo(size, radius):
    """Логотип; если файла нет — заметная заглушка, чтобы карточка всё равно собралась.

    Принимает любой logo.png: прозрачный фон подкладываем крафтом (а не чёрным),
    не квадратный — вписываем по большей стороне и центрируем.
    """
    lip = logo_asset()
    if os.path.exists(lip):
        src = Image.open(lip)
        has_alpha = src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info)
        src = src.convert("RGBA") if has_alpha else src.convert("RGB")
        # вписываем в квадрат с полями, сохраняя пропорции
        pad = int(size * 0.06)
        inner = size - 2 * pad
        k = min(inner / src.width, inner / src.height)
        new = src.resize((max(1, int(src.width * k)), max(1, int(src.height * k))), Image.LANCZOS)
        if has_alpha:
            bg = Image.new("RGB", (size, size), PAPER)
            bg.paste(new, ((size - new.width) // 2, (size - new.height) // 2), new)
            lg = bg
        else:
            lg = Image.new("RGB", (size, size), PAPER)
            lg.paste(new, ((size - new.width) // 2, (size - new.height) // 2))
    else:
        lg = Image.new("RGB", (size, size), PAPER)
        dd = ImageDraw.Draw(lg)
        dd.ellipse([6, 6, size - 7, size - 7], outline=FRAME, width=4)
        f1 = font("RussoOne.ttf", int(size * 0.30))
        f2 = font("PTSans-Regular.ttf", max(9, int(size * 0.085)))
        dd.text((size / 2, size * 0.42), "ВО", font=f1, fill=INK, anchor="mm")
        dd.text((size / 2, size * 0.66), "НУЖЕН logo.png", font=f2, fill=MUTED, anchor="mm")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius, fill=255)
    return lg, mask


def paper(w, h):
    img = Image.new("RGB", (w, h), PAPER)
    noise = Image.effect_noise((w, h), 22).convert("RGB")
    img = Image.blend(img, noise, 0.09)
    d = ImageDraw.Draw(img)
    for x in range(0, w, 36):
        d.line([(x, 0), (x, h)], fill=GRID, width=1)
    for y in range(0, h, 36):
        d.line([(0, y), (w, y)], fill=GRID, width=1)
    return img


def rivet(d, cx, cy):
    d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(152, 150, 138), outline=(84, 84, 74), width=2)
    d.ellipse([cx - 4, cy - 5, cx + 1, cy], fill=(215, 213, 200))


def stamp(text, date, angle=-6):
    """Печать «В НАЛИЧИИ» с датой: рваный оттиск, повёрнута."""
    w, h = 460, 150
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([4, 4, w - 5, h - 5], 16, outline=STAMP, width=6)
    d.rounded_rectangle([16, 16, w - 17, h - 17], 10, outline=STAMP, width=2)
    fb = font("Oswald.ttf", 60, "Bold")
    fs = font("Oswald.ttf", 24, "Medium")
    d.text((w / 2, 62), text, font=fb, fill=STAMP, anchor="mm")
    tracked(d, (w / 2, 96), f"НА {date}", fs, STAMP, tracking=3, anchor="m")
    speck = Image.effect_noise((w, h), 70).point(lambda v: 255 if v > 78 else 0)
    a = layer.getchannel("A")
    a = Image.composite(a, Image.new("L", (w, h), 0), speck)
    layer.putalpha(a)
    layer = layer.filter(ImageFilter.GaussianBlur(0.5))
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    a = layer.getchannel("A").point(lambda v: int(v * 0.88))
    layer.putalpha(a)
    return layer


def head_block(img, d, title, subtitle, x1):
    lg, mask = rounded_logo(190, 26)
    img.paste(lg, (M, 46), mask)
    d.rounded_rectangle([M, 46, M + 189, 46 + 189], 26, outline=FRAME, width=2)
    ts = 64
    f_title = font("RussoOne.ttf", ts)
    while f_title.getlength(title) > (x1 - M) - 228 and ts > 38:
        ts -= 2
        f_title = font("RussoOne.ttf", ts)
    tx = M + 190 + 38
    d.text((tx, 52), title, font=f_title, fill=INK)
    bb = d.textbbox((tx, 52), title, font=f_title)
    gh = bb[3] - bb[1]
    for k in (0.36, 0.68):
        yy = bb[1] + gh * k
        d.line([(bb[0] - 4, yy), (bb[2] + 4, yy)], fill=PAPER, width=3)
    tracked(d, (tx + 2, 136), "В ОКОПЕ · МАГАЗИН БРОНИ", font("PTSans-Bold.ttf", 32), INK, tracking=3)
    d.text((tx + 2, 182), subtitle, font=font("PTSans-Regular.ttf", 24), fill=MUTED)
    HEAD_END = 268
    d.line([(M, HEAD_END), (x1, HEAD_END)], fill=INK, width=3)
    d.line([(M, HEAD_END + 7), (x1, HEAD_END + 7)], fill=INK, width=1)
    return HEAD_END


def check_photos(items):
    """Железное правило: нет фото от поставщика — карточку не собираем."""
    missing = [it.get("photo") for it in items if not it.get("photo")]
    if missing:
        raise SystemExit(
            "СТОП: у позиции нет фото от поставщика.\n"
            "Правило: фото только из каталога Димы (/getFullImages) или от поставщика.\n"
            "Нет фото → карточку не собирать: попроси фото у поставщика.\n"
            f"Проблемные позиции: {missing}")
    for it in items:
        p = it["photo"] if os.path.isabs(it["photo"]) else os.path.join(ROOT, it["photo"])
        if not os.path.exists(p):
            raise SystemExit(f"СТОП: файл фото не найден: {p}\n"
                             "Сначала забери фото из каталога (catalog/requests/photos.json → Actions → catalog_pull).")


def build(order, out_path):
    items = order["items"]
    check_photos(items)
    date = order.get("date", "")
    title = order.get("title", "БЛАНК ЗАКАЗА")

    HEAD_END = 268
    T_TOP = HEAD_END + 28
    T_BOTTOM = T_TOP + HEAD_H + ROW_H * len(items)
    BLOCK_Y = T_BOTTOM + 34
    FOOT_Y = BLOCK_Y + 186
    H = FOOT_Y + 78

    img = paper(W, H)
    d = ImageDraw.Draw(img)
    x0, x1 = M, W - M
    head_block(img, d, title, "Расчёт по вашему запросу", x1)

    cx_photo = x0 + COL_PHOTO
    cx_name = cx_photo + COL_NAME
    cx_qty = cx_name + COL_QTY
    d.rectangle([x0, T_TOP, x1, T_TOP + HEAD_H], fill=TINT)
    f_head = font("Oswald.ttf", 20, "Medium")
    hy = T_TOP + 15
    tracked(d, ((x0 + cx_photo) / 2, hy), "ФОТО", f_head, INK, 2, "m")
    tracked(d, (cx_photo + 22, hy), "НАИМЕНОВАНИЕ", f_head, INK, 2, "l")
    tracked(d, ((cx_name + cx_qty) / 2, hy), "КОЛ-ВО", f_head, INK, 2, "m")
    tracked(d, (x1 - 22, hy), "ЦЕНА", f_head, INK, 2, "r")

    f_name = [font("PTSans-Bold.ttf", s) for s in (31, 28, 25)]
    f_sub2 = font("PTSans-Regular.ttf", 23)
    f_qty = font("Oswald.ttf", 34, "SemiBold")
    f_price = font("Oswald.ttf", 40, "SemiBold")
    name_w = COL_NAME - 44

    y = T_TOP + HEAD_H
    for i, it in enumerate(items):
        if i > 0:
            dashed_h(d, x0 + 12, x1 - 12, y, FRAME)
        ph = Image.open(os.path.join(ROOT, it["photo"]) if not os.path.isabs(it["photo"]) else it["photo"]).convert("RGB")
        box = 170
        ph.thumbnail((box - 12, box - 12), Image.LANCZOS)
        px = x0 + (COL_PHOTO - box) // 2
        py = y + (ROW_H - box) // 2
        d.rectangle([px, py, px + box, py + box], fill=WHITE, outline=FRAME, width=2)
        img.paste(ph, (px + (box - ph.width) // 2 + 1, py + (box - ph.height) // 2 + 1))

        for f in f_name:
            lines = wrap(it["name"], f, name_w)
            if len(lines) <= 2:
                break
        lines = lines[:2]
        lh = f.size + 8
        sub = ellipsize(it.get("sub", ""), f_sub2, name_w)
        block_h = lh * len(lines) + (34 if sub else 0)
        ty = y + (ROW_H - block_h) // 2
        for ln in lines:
            d.text((cx_photo + 22, ty), ln, font=f, fill=TEXT)
            ty += lh
        if sub:
            d.text((cx_photo + 22, ty + 4), sub, font=f_sub2, fill=MUTED)

        d.text(((cx_name + cx_qty) / 2, y + ROW_H / 2), f"{it['qty']} шт", font=f_qty, fill=TEXT, anchor="mm")
        price = it.get("price")
        if price is None:
            f_ask = font("PTSans-Regular.ttf", 24)
            d.text((x1 - 22, y + ROW_H / 2), "по запросу", font=f_ask, fill=MUTED, anchor="rm")
        else:
            d.text((x1 - 22, y + ROW_H / 2), fmt_money(price), font=f_price, fill=INK, anchor="rm")
        y += ROW_H

    for cx in (cx_photo, cx_name, cx_qty):
        d.line([(cx, T_TOP), (cx, T_BOTTOM)], fill=FRAME, width=1)
    d.rectangle([x0, T_TOP, x1, T_BOTTOM], outline=INK, width=3)

    priced = [it for it in items if it.get("price") is not None]
    all_priced = len(priced) == len(items)
    total = sum(it["qty"] * it["price"] for it in priced)
    bx0, by0, bx1, by1 = 545, BLOCK_Y + 8, x1, BLOCK_Y + 118
    d.rectangle([bx0, by0, bx1, by1], outline=INK, width=4)
    d.rectangle([bx0 + 7, by0 + 7, bx1 - 7, by1 - 7], outline=INK, width=1)
    d.text((bx0 + 26, (by0 + by1) / 2), "ИТОГО:", font=font("Oswald.ttf", 36, "Medium"), fill=INK, anchor="lm")
    if all_priced:
        d.text((bx1 - 26, (by0 + by1) / 2), fmt_money(total), font=font("Oswald.ttf", 56, "Bold"), fill=INK, anchor="rm")
    else:
        d.text((bx1 - 26, (by0 + by1) / 2), "уточняется", font=font("Oswald.ttf", 40, "Medium"), fill=MUTED, anchor="rm")

    st = stamp("В НАЛИЧИИ", date)
    img.paste(st, (M + 6, BLOCK_Y - 30), st)

    d = ImageDraw.Draw(img)
    dashed_h(d, M, W - M, FOOT_Y, FRAME, width=1)
    tracked(d, (W / 2, FOOT_Y + 24), "В ОКОПЕ · МАГАЗИН БРОНИ", font("Oswald.ttf", 22, "Regular"), MUTED, 4, "m")
    for cx, cy in ((26, 26), (W - 26, 26), (26, H - 26), (W - 26, H - 26)):
        rivet(d, cx, cy)

    img.save(out_path, quality=92)
    print("saved", out_path, img.size, "| ИТОГО",
          fmt_money(total) if all_priced else "уточняется (не все цены заданы)")
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "media", "blank", "order.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "media", "blank", "out.png")
    with open(src, encoding="utf-8") as fh:
        build(json.load(fh), out)
