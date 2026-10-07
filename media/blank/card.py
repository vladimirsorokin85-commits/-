#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Расширенная товарная карточка «В ОКОПЕ» — фото-сетка + описание + допродажа.
Стиль «полевой бланк / крафт». Хелперы берутся из blank.py.

Запуск:
    python3 media/blank/card.py media/blank/card_voevoda.json media/blank/card_voevoda.png

JSON:
{
  "date": "07.10.2026",
  "title": "ПОДБОР ПОД ЗАПРОС",
  "product": {
    "name": "...", "sub": "...",
    "photos": ["catalog/photos/00895/00895_1.jpg"],     # ТОЛЬКО фото поставщика
    "sections": [{"h": "СОСТАВ", "bullets": ["...", "..."]}],
    "price_label": "КОМПЛЕКТ", "price": 85381           # цена ВЛАДЕЛЬЦА
  },
  "addon": {                                            # опционально
    "label": "ДОБАВИТЬ К ПОКУПКЕ", "name": "...", "sub": "...", "sub2": "...",
    "photo": "catalog/photos/00084/00084_1.jpg", "price": 19376,
    "bundle_label": "КОМПЛЕКТ + ПОЯС"
  }
}
"""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from blank import (PAPER, INK, TEXT, MUTED, FRAME, WHITE, W, M, ROOT,  # noqa: E402
                   check_photos, dashed_h, ellipsize, fmt_money, font,
                   head_block, paper, rivet, stamp, tracked, wrap)

CANVAS_H = 4200


def fit_font(name, text, width, sizes, max_lines=2):
    f, lines = None, []
    for s in sizes:
        f = font(name, s)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    return f, lines[:max_lines]


def photo_path(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def build(data, out_path):
    prod = data["product"]
    addon = data.get("addon")
    date = data.get("date", "")
    title = data.get("title", "ПОДБОР ПОД ЗАПРОС")

    check_photos([{"photo": p} for p in prod.get("photos", [])] + ([{"photo": addon["photo"]}] if addon else []))
    if not prod.get("photos"):
        raise SystemExit("СТОП: в карточке нет ни одного фото от поставщика. "
                         "Карточку не собираем — попроси фото у поставщика.")

    img = paper(W, CANVAS_H)
    d = ImageDraw.Draw(img)
    x0, x1 = M, W - M
    CW = x1 - x0

    HEAD_END = head_block(img, d, title, "Расчёт по вашему запросу", x1)
    y = HEAD_END + 34

    f_name, lines = fit_font("PTSans-Bold.ttf", prod["name"], CW, (46, 42, 38, 34))
    lh = f_name.size + 10
    for ln in lines:
        d.text((M, y), ln, font=f_name, fill=TEXT)
        y += lh
    y += 8
    f_sub = font("PTSans-Regular.ttf", 26)
    d.text((M, y), ellipsize(prod.get("sub", ""), f_sub, CW), font=f_sub, fill=MUTED)
    y += 44

    photos = prod.get("photos", [])
    if photos:
        gap = 16
        cw = (CW - 2 * gap) // 3
        ch = 560
        rows = (len(photos) + 2) // 3
        for i, ph in enumerate(photos):
            col, row = i % 3, i // 3
            px = M + col * (cw + gap)
            py = y + row * (ch + gap)
            d.rectangle([px, py, px + cw, py + ch], fill=WHITE, outline=FRAME, width=2)
            im = Image.open(photo_path(ph)).convert("RGB")
            im.thumbnail((cw - 16, ch - 16), Image.LANCZOS)
            img.paste(im, (px + (cw - im.width) // 2, py + (ch - im.height) // 2))
        y += rows * (ch + gap) - gap + 10

    f_h = font("Oswald.ttf", 24, "Medium")
    f_b = font("PTSans-Regular.ttf", 26)
    for sec in prod.get("sections", []):
        y += 40
        tracked(d, (M, y), sec["h"], f_h, INK, tracking=3)
        d.line([(M, y + 40), (x1, y + 40)], fill=FRAME, width=1)
        y += 56
        for b in sec["bullets"]:
            blines = wrap(b, f_b, CW - 34)
            d.text((M + 2, y), "•", font=font("PTSans-Bold.ttf", 26), fill=INK)
            for ln in blines:
                d.text((M + 34, y), ln, font=f_b, fill=TEXT)
                y += 36
            y += 8

    y += 30
    bx0, by0, bx1, by1 = 545, y + 8, x1, y + 118
    d.rectangle([bx0, by0, bx1, by1], outline=INK, width=4)
    d.rectangle([bx0 + 7, by0 + 7, bx1 - 7, by1 - 7], outline=INK, width=1)
    d.text((bx0 + 26, (by0 + by1) / 2), str(prod.get("price_label", "ЦЕНА")) + ":",
           font=font("Oswald.ttf", 32, "Medium"), fill=INK, anchor="lm")
    d.text((bx1 - 26, (by0 + by1) / 2), fmt_money(prod["price"]),
           font=font("Oswald.ttf", 54, "Bold"), fill=INK, anchor="rm")
    st = stamp("В НАЛИЧИИ", date)
    img.paste(st, (M + 6, y - 26), st)
    y = by1 + 36

    if addon:
        dashed_h(d, M, x1, y, FRAME)
        y += 28
        tracked(d, (M, y), addon.get("label", "ДОБАВИТЬ К ПОКУПКЕ"),
                font("Oswald.ttf", 26, "Medium"), INK, tracking=4)
        y += 58
        ROW_H = 232
        box = 200
        d.rectangle([M, y, M + box, y + ROW_H], fill=WHITE, outline=FRAME, width=2)
        im = Image.open(photo_path(addon["photo"])).convert("RGB")
        im.thumbnail((box - 14, ROW_H - 14), Image.LANCZOS)
        img.paste(im, (M + (box - im.width) // 2, y + (ROW_H - im.height) // 2))
        tx = M + box + 26
        price_w = 200
        tw = (x1 - 22 - price_w) - tx
        f_an, alines = fit_font("PTSans-Bold.ttf", addon["name"], tw, (31, 28, 25))
        alh = f_an.size + 8
        f_as = font("PTSans-Regular.ttf", 23)
        subs = [ellipsize(s, f_as, tw) for s in (addon.get("sub", ""), addon.get("sub2", "")) if s]
        block_h = alh * len(alines) + (32 * len(subs) if subs else 0)
        ty = y + (ROW_H - block_h) // 2
        for ln in alines:
            d.text((tx, ty), ln, font=f_an, fill=TEXT)
            ty += alh
        for s in subs:
            d.text((tx, ty + 4), s, font=f_as, fill=MUTED)
            ty += 32
        d.text((x1 - 22, y + ROW_H / 2), fmt_money(addon["price"]),
               font=font("Oswald.ttf", 40, "SemiBold"), fill=INK, anchor="rm")
        y += ROW_H + 18

        y += 14
        d.rectangle([M, y, x1, y + 112], outline=INK, width=4)
        d.rectangle([M + 7, y + 7, x1 - 7, y + 105], outline=INK, width=1)
        d.text((M + 26, y + 56), addon.get("bundle_label", "ИТОГО С ДОПОЛНЕНИЕМ") + ":",
               font=font("Oswald.ttf", 34, "Medium"), fill=INK, anchor="lm")
        d.text((x1 - 26, y + 56), fmt_money(prod["price"] + addon["price"]),
               font=font("Oswald.ttf", 56, "Bold"), fill=INK, anchor="rm")
        y += 112 + 34

    y += 12
    dashed_h(d, M, x1, y, FRAME, width=1)
    tracked(d, (W / 2, y + 24), "В ОКОПЕ · МАГАЗИН БРОНИ",
            font("Oswald.ttf", 22, "Regular"), MUTED, 4, "m")
    H = y + 78

    img = img.crop((0, 0, W, H))
    d = ImageDraw.Draw(img)
    for cx, cy in ((26, 26), (W - 26, 26), (26, H - 26), (W - 26, H - 26)):
        rivet(d, cx, cy)

    if out_path.lower().endswith((".jpg", ".jpeg")):
        img.save(out_path, quality=90, optimize=True)
    else:
        img.save(out_path, quality=92)
    total = prod["price"] + (addon["price"] if addon else 0)
    print("saved", out_path, img.size, "| товар", fmt_money(prod["price"]), "| с доп.", fmt_money(total))
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "card.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "card_out.jpg")
    with open(src, encoding="utf-8") as fh:
        build(json.load(fh), out)
