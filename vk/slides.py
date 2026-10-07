#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СЛАЙДЫ-КАРУСЕЛЬ «В ОКОПЕ» — пост-история из картинок 1080×1350.

Смысл: вместо одной длинной карточки — набор слайдов, которые листаются в ВК:
обложка → задача → товары → состав с итогом → призыв.

  from vk.slides import build
  build(spec, out_dir)     # spec — список слайдов (см. build_spec)

Стиль берём из media/blank/blank.py (полевой бланк, логотип, крафт).
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "media", "blank"))
from blank import (INK, TEXT, MUTED, FRAME, WHITE, PAPER,  # noqa: E402
                   dashed_h, font, fmt_money, logo_asset, paper, rivet, stamp,
                   tracked, wrap)

W, H = 1080, 1350
M = 64


def _logo(size=132, radius=22):
    """Логотип в скруглённой рамке (как в карточках)."""
    lg = Image.open(logo_asset()).convert("RGBA")
    lg.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(lg, ((size - lg.width) // 2, (size - lg.height) // 2), lg)
    return canvas


def _head(img, d, title, subtitle="", small=False):
    """Шапка слайда: логотип + название магазина. Возвращает Y после шапки."""
    size = 96 if small else 132
    lg = _logo(size, 20 if small else 26)
    img.paste(lg, (M, 54), lg)
    d.rounded_rectangle([M, 54, M + size - 1, 54 + size - 1], 20 if small else 26,
                        outline=FRAME, width=2)
    tx = M + size + 26
    tracked(d, (tx, 62), "В ОКОПЕ · МАГАЗИН БРОНИ", font("PTSans-Bold.ttf", 24 if small else 28),
            INK, tracking=2)
    if subtitle:
        d.text((tx, 62 + (44 if small else 52)), subtitle, font=font("PTSans-Regular.ttf", 22),
               fill=MUTED)
    y = 54 + size + 34
    d.line([(M, y), (W - M, y)], fill=INK, width=3)
    d.line([(M, y + 6), (W - M, y + 6)], fill=INK, width=1)
    return y + 40


def _foot(img, d, note="", n=None, total=None):
    y = H - 96
    dashed_h(d, M, W - M, y, FRAME, width=1)
    if note:
        d.text((W / 2, y + 30), note, font=font("PTSans-Regular.ttf", 22), fill=MUTED, anchor="mm")
    if n and total:
        d.text((W - M, y + 30), f"{n}/{total}", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="rm")


def _wrap_fit(text, width, sizes, max_lines=3, weight=None, name="PTSans-Bold.ttf"):
    f, lines = None, []
    for s in sizes:
        f = font(name, s, weight)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    return f, lines[:max_lines]


def slide_cover(spec, n, total):
    img = paper(W, H)
    d = ImageDraw.Draw(img)
    y = _head(img, d, "", "Собрано из наличия · СДЭК, оплата при получении")

    f, lines = _wrap_fit(spec.get("title", ""), W - 2 * M, (78, 68, 58), 3, name="RussoOne.ttf")
    for ln in lines:
        d.text((M, y), ln, font=f, fill=INK)
        y += f.size + 12
    y += 14
    if spec.get("lead"):
        fl = font("PTSans-Regular.ttf", 32)
        for ln in wrap(spec["lead"], fl, W - 2 * M)[:3]:
            d.text((M, y), ln, font=fl, fill=TEXT)
            y += 44
    y += 20

    photos = [p for p in (spec.get("photos") or [])][:3]
    if photos:
        gap = 18
        cw = (W - 2 * M - gap * (len(photos) - 1)) // max(1, len(photos))
        ch = min(520, H - y - 380)
        for i, ph in enumerate(photos):
            px = M + i * (cw + gap)
            d.rectangle([px, y, px + cw, y + ch], fill=WHITE, outline=FRAME, width=2)
            im = Image.open(ph if os.path.isabs(ph) else os.path.join(ROOT, ph)).convert("RGB")
            im.thumbnail((cw - 18, ch - 18), Image.LANCZOS)
            img.paste(im, (px + (cw - im.width) // 2, y + (ch - im.height) // 2))

    st = stamp("В НАЛИЧИИ", spec.get("date", ""))
    img.paste(st, (M, H - 320), st)
    _foot(img, d, "Листайте дальше — покажем, что входит", n, total)
    return img


def slide_text(spec, n, total):
    img = paper(W, H)
    d = ImageDraw.Draw(img)
    y = _head(img, d, "", spec.get("subtitle", ""))
    f, lines = _wrap_fit(spec.get("title", ""), W - 2 * M, (62, 54, 48), 2)
    for ln in lines:
        d.text((M, y), ln, font=f, fill=INK)
        y += f.size + 10
    y += 30
    fb = font("PTSans-Regular.ttf", 34)
    for b in spec.get("bullets", []):
        d.text((M, y + 6), "▪", font=font("PTSans-Bold.ttf", 30), fill=FRAME)
        for ln in wrap(b, fb, W - 2 * M - 44):
            d.text((M + 44, y), ln, font=fb, fill=TEXT)
            y += 46
        y += 22
    if spec.get("note"):
        y += 8
        for ln in wrap(spec["note"], font("PTSans-Regular.ttf", 26), W - 2 * M):
            d.text((M, y), ln, font=font("PTSans-Regular.ttf", 26), fill=MUTED)
            y += 36
    _foot(img, d, spec.get("foot", ""), n, total)
    return img


def slide_product(spec, n, total):
    """Слайд товара. Список items (2 позиции) — раскладка в два горизонтальных блока."""
    img = paper(W, H)
    d = ImageDraw.Draw(img)
    y = _head(img, d, "", spec.get("subtitle", ""))

    items = spec.get("items") or [spec]
    two = len(items) > 1

    if two:
        # два блока: фото слева, текст справа — экономит высоту
        BOX = 300
        for it in items:
            name = it.get("name", "")
            f, lines = _wrap_fit(name, W - 2 * M - BOX - 40, (40, 36, 32), 2)
            tx = M + BOX + 40
            ty = y + 6
            for ln in lines:
                d.text((tx, ty), ln, font=f, fill=TEXT)
                ty += f.size + 8
            if it.get("variant"):
                for ln in wrap(it["variant"], font("PTSans-Regular.ttf", 26), W - 2 * M - BOX - 40)[:2]:
                    d.text((tx, ty), ln, font=font("PTSans-Regular.ttf", 26), fill=MUTED)
                    ty += 34
            ty += 8
            fb = font("PTSans-Regular.ttf", 26)
            limit = min(y + BOX, H - 310)
            for b in (it.get("facts") or [])[:2]:
                for ln in wrap(b, fb, W - 2 * M - BOX - 40)[:2]:
                    if ty + 34 > limit:
                        break
                    d.text((tx, ty), "• " + ln, font=fb, fill=TEXT)
                    ty += 34
            d.rectangle([M, y, M + BOX, y + BOX], fill=WHITE, outline=FRAME, width=2)
            im = Image.open(it["photo"] if os.path.isabs(it["photo"]) else os.path.join(ROOT, it["photo"])).convert("RGB")
            im.thumbnail((BOX - 20, BOX - 20), Image.LANCZOS)
            img.paste(im, (M + (BOX - im.width) // 2, y + (BOX - im.height) // 2))
            y += BOX + 34
    else:
        it = items[0]
        facts_reserve = 300
        name = it.get("name", "")
        f, lines = _wrap_fit(name, W - 2 * M, (52, 44, 40), 2)
        for ln in lines:
            d.text((M, y), ln, font=f, fill=TEXT)
            y += f.size + 8
        if it.get("variant"):
            d.text((M, y), it["variant"], font=font("PTSans-Regular.ttf", 28), fill=MUTED)
            y += 40
        y += 12
        if it.get("photo"):
            box_h = int(max(240, min(470, (H - 300) - y - facts_reserve)))
            d.rectangle([M, y, W - M, y + box_h], fill=WHITE, outline=FRAME, width=2)
            im = Image.open(it["photo"] if os.path.isabs(it["photo"]) else os.path.join(ROOT, it["photo"])).convert("RGB")
            im.thumbnail((W - 2 * M - 24, box_h - 24), Image.LANCZOS)
            img.paste(im, ((W - im.width) // 2, y + (box_h - im.height) // 2))
            y += box_h + 24
        fb = font("PTSans-Regular.ttf", 30)
        for b in (it.get("facts") or [])[:4]:
            lines_ = wrap(b, fb, W - 2 * M - 40)
            if y + 40 * len(lines_) > H - 290:
                break
            d.text((M, y + 4), "•", font=font("PTSans-Bold.ttf", 28), fill=INK)
            for ln in lines_:
                d.text((M + 40, y), ln, font=fb, fill=TEXT)
                y += 40
            y += 8

    price = spec.get("price")
    bx = [M, H - 268, W - M, H - 150]
    d.rectangle(bx, outline=INK, width=4)
    d.rectangle([bx[0] + 7, bx[1] + 7, bx[2] - 7, bx[3] - 7], outline=INK, width=1)
    d.text((bx[0] + 26, (bx[1] + bx[3]) / 2), "ЦЕНА:", font=font("Oswald.ttf", 32, "Medium"),
           fill=INK, anchor="lm")
    if price is None:
        d.text((bx[2] - 26, (bx[1] + bx[3]) / 2), "по запросу",
               font=font("Oswald.ttf", 38, "Medium"), fill=MUTED, anchor="rm")
    else:
        d.text((bx[2] - 26, (bx[1] + bx[3]) / 2), fmt_money(price),
               font=font("Oswald.ttf", 52, "Bold"), fill=INK, anchor="rm")
    _foot(img, d, spec.get("foot", "Все позиции в наличии"), n, total)
    return img


def slide_summary(spec, n, total):
    img = paper(W, H)
    d = ImageDraw.Draw(img)
    y = _head(img, d, "", spec.get("subtitle", "Комплект целиком"))
    f, lines = _wrap_fit(spec.get("title", ""), W - 2 * M, (58, 50), 2)
    for ln in lines:
        d.text((M, y), ln, font=f, fill=INK)
        y += f.size + 10
    y += 26
    rows = spec.get("rows", [])
    limit = (H - 320) - 16
    size = 32 if len(rows) <= 7 else (28 if len(rows) <= 9 else 25)
    fn = font("PTSans-Regular.ttf", size)
    for row in rows:
        name = row.get("name", "")
        lines_ = wrap(name, fn, W - 2 * M - 260)[:2]
        if y + len(lines_) * (size + 12) > limit:
            break
        for ln in lines_:
            d.text((M, y), ln, font=fn, fill=TEXT)
            y += size + 12
        y += 12
    y += 12
    bx = [M, H - 320, W - M, H - 150]
    d.rectangle(bx, outline=INK, width=4)
    d.rectangle([bx[0] + 7, bx[1] + 7, bx[2] - 7, bx[3] - 7], outline=INK, width=1)
    fl = font("Oswald.ttf", 30, "Medium")
    lab = spec.get("total_label", "КОМПЛЕКТ")
    while fl.getlength(lab) > (bx[2] - bx[0]) - 320 and fl.size > 20:
        fl = font("Oswald.ttf", fl.size - 2, "Medium")
    d.text((bx[0] + 26, bx[1] + 56), lab, font=fl, fill=INK, anchor="lm")
    d.text((bx[0] + 26, bx[1] + 112), "Все позиции в наличии · отправка СДЭК",
           font=font("PTSans-Regular.ttf", 23), fill=MUTED, anchor="lm")
    price = spec.get("price")
    if price is None:
        d.text((bx[2] - 26, (bx[1] + bx[3]) / 2), "по запросу",
               font=font("Oswald.ttf", 40, "Medium"), fill=MUTED, anchor="rm")
    else:
        d.text((bx[2] - 26, (bx[1] + bx[3]) / 2), fmt_money(price),
               font=font("Oswald.ttf", 54, "Bold"), fill=INK, anchor="rm")
    _foot(img, d, spec.get("foot", ""), n, total)
    return img


def slide_cta(spec, n, total):
    img = paper(W, H)
    d = ImageDraw.Draw(img)
    lg = _logo(220, 34)
    img.paste(lg, ((W - 220) // 2, 150), lg)
    d.rounded_rectangle([(W - 220) // 2, 150, (W + 220) // 2, 370], 34, outline=FRAME, width=3)
    y = 430
    f, lines = _wrap_fit(spec.get("title", "Напишите в личные сообщения"), W - 2 * M, (60, 52), 3)
    for ln in lines:
        d.text((W / 2, y), ln, font=f, fill=INK, anchor="ma")
        y += f.size + 12
    y += 30
    for b in spec.get("bullets", []):
        for ln in wrap(b, font("PTSans-Regular.ttf", 34), W - 2 * M):
            d.text((W / 2, y), ln, font=font("PTSans-Regular.ttf", 34), fill=TEXT, anchor="ma")
            y += 46
        y += 18
    tracked(d, (W / 2, H - 190), "В ОКОПЕ · МАГАЗИН БРОНИ", font("Oswald.ttf", 26, "Medium"),
            MUTED, 5, "mm")
    _foot(img, d, "", n, total)
    return img


BUILDERS = {"cover": slide_cover, "text": slide_text, "product": slide_product,
            "summary": slide_summary, "cta": slide_cta}


def build_spec(kit, card, resolved, story=None):
    """Собрать спецификацию слайдов из комплекта (не больше 10 штук)."""
    slides = []
    main = card["product"]
    items = card.get("options", {}).get("items", [])

    cover_photos = (main.get("photos") or [])[:1]
    for it in items:
        if len(cover_photos) >= 3:
            break
        if it.get("photo"):
            cover_photos.append(it["photo"])
    slides.append({"type": "cover", "title": kit["title"], "date": kit.get("date", ""),
                   "lead": kit.get("cover_lead", ""), "photos": cover_photos})

    if story:
        slides.append({"type": "text", "title": story.get("title", ""),
                       "bullets": story.get("bullets", []), "note": story.get("note", ""),
                       "subtitle": "Зачем этот комплект"})

    # позиции: основа + что к ней
    product_slides = [{"name": main["name"], "variant": main.get("sub", ""),
                       "photo": (main.get("photos") or [None])[0],
                       "facts": (main.get("sections") or [{}])[0].get("bullets", []),
                       "price": main.get("price")}]
    kit_items = kit.get("items", [])
    for i, it in enumerate(items):
        k = kit_items[i] if i < len(kit_items) else {}
        product_slides.append({"name": it["name"], "variant": it.get("sub", ""),
                               "photo": it.get("photo"),
                               "facts": k.get("facts") or [it.get("sub", "")],
                               "price": it.get("price")})

    # укладываемся в 10 слайдов: часть позиций — по две на слайд
    room = 10 - len(slides) - 2  # минус итог и призыв
    need = max(0, len(product_slides) - room)
    if need == 0:
        packs = [[p] for p in product_slides]
    else:
        # склеиваем хвост попарно: 2 позиции на один слайд
        split = len(product_slides) - 2 * need
        keep, tail = product_slides[:split], product_slides[split:]
        merged = [{"items": [tail[i], tail[i + 1]]} for i in range(0, len(tail), 2)]
        packs = [[p] for p in keep] + [[m] for m in merged]
    for pack in packs:
        if "items" in pack[0]:
            slides.append({"type": "product", "items": pack[0]["items"], "subtitle": "Комплект"})
        else:
            slides.append({"type": "product", **pack[0], "subtitle": "Комплект"})

    rows = [{"name": main["name"], "variant": main.get("sub", "")}]
    for it in items:
        rows.append({"name": it.get("short") or it["name"], "variant": it.get("sub", "")})
    slides.append({"type": "summary", "title": "Что входит в комплект", "rows": rows,
                   "total_label": kit.get("kit", {}).get("label", "КОМПЛЕКТ"),
                   "price": kit.get("kit", {}).get("price")})
    slides.append({"type": "cta", "title": "Соберём под ваш размер и задачу",
                   "bullets": ["СДЭК по России, оплата при получении",
                               "Напишите в личные сообщения — подберём"]})
    return slides[:10]


def build(spec, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    total = len(spec)
    for i, s in enumerate(spec, 1):
        img = BUILDERS[s["type"]](s, i, total)
        d = ImageDraw.Draw(img)
        for cx, cy in ((20, 20), (W - 20, 20), (20, H - 20), (W - 20, H - 20)):
            rivet(d, cx, cy)
        img.save(os.path.join(out_dir, f"{i:02d}.jpg"), quality=90, optimize=True)
    return out_dir
