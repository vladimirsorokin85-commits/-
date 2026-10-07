#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
КАРТОЧКА КОМПЛЕКТА «В ОКОПЕ» — основа + что к ней (+ итог по комплекту).

Стиль тот же, что у одиночной карточки («полевой бланк», крафт):
логотип, заголовок, фото поставщика, особенности, штамп «В НАЛИЧИИ»,
цена, список позиций к комплекту и итоговая рамка.

Запуск:
    python3 media/blank/kit_card.py <kit.json> <out.jpg>

JSON:
{
  "date": "07.10.2026",
  "title": "КОМПЛЕКТ «ШТУРМОВИК»",
  "subtitle": "Собрано из наличия · расчёт под ваш запрос",
  "product": {                       # основа
    "name": "...", "sub": "...",
    "photos": ["catalog/photos/00796/00796_1.jpg"],
    "sections": [{"h": "ОСОБЕННОСТИ", "bullets": ["...", "..."]}],
    "price_label": "ПЛИТНИК", "price": 42500        # цена ВЛАДЕЛЬЦА; null → «по запросу»
  },
  "options": {                       # что к нему — на выбор
    "label": "К НЕМУ — НА ВЫБОР",
    "items": [{"name": "...", "sub": "...", "sub2": "...",
               "photo": "...", "price": 14000}]
  },
  "kit": {                           # итог по комплекту
    "label": "КОМПЛЕКТ: ПЛИТНИК + ШЛЕМ + НАУШНИКИ + АПТЕЧКА",
    "price": 78000
  }
}

Железные правила (те же): фото — только поставщика; цены — только от владельца;
нет цены — печатаем «по запросу», не выдумываем.
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

CANVAS_H = 5600


def fit_font(name, text, width, sizes, max_lines=2, weight=None):
    f, lines = None, []
    for s in sizes:
        f = font(name, s, weight)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    return f, lines[:max_lines]


def photo_path(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def price_text(price):
    return fmt_money(price) if price is not None else "по запросу"


def build(data, out_path):
    prod = data["product"]
    options = data.get("options") or {}
    opt_items = options.get("items") or []
    kit = data.get("kit") or {}

    check_photos([{"photo": p} for p in prod.get("photos", [])]
                 + [{"photo": it.get("photo")} for it in opt_items])
    if not prod.get("photos"):
        raise SystemExit("СТОП: нет фото от поставщика — карточку не собираем.")

    img = paper(W, CANVAS_H)
    d = ImageDraw.Draw(img)
    x0, x1 = M, W - M
    CW = x1 - x0

    HEAD_END = head_block(img, d, data.get("title", "КОМПЛЕКТ"),
                          data.get("subtitle", "Собрано из наличия"), x1)
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
    price_font = font("Oswald.ttf", 54 if prod.get("price") is not None else 40, "Bold")
    d.text((bx1 - 26, (by0 + by1) / 2), price_text(prod.get("price")),
           font=price_font, fill=INK if prod.get("price") is not None else MUTED, anchor="rm")
    st = stamp("В НАЛИЧИИ", data.get("date", ""))
    img.paste(st, (M + 6, y - 26), st)
    y = by1 + 36

    # ---- позиции к комплекту (на выбор) ----
    if opt_items:
        dashed_h(d, M, x1, y, FRAME)
        y += 28
        tracked(d, (M, y), options.get("label", "К НЕМУ — НА ВЫБОР"),
                font("Oswald.ttf", 26, "Medium"), INK, tracking=4)
        y += 54
        ROW_H, box = 232, 200
        for it in opt_items:
            d.rectangle([M, y, M + box, y + ROW_H], fill=WHITE, outline=FRAME, width=2)
            im = Image.open(photo_path(it["photo"])).convert("RGB")
            im.thumbnail((box - 14, ROW_H - 14), Image.LANCZOS)
            img.paste(im, (M + (box - im.width) // 2, y + (ROW_H - im.height) // 2))
            tx = M + box + 26
            price_w = 230
            tw = (x1 - 22 - price_w) - tx
            f_an, alines = fit_font("PTSans-Bold.ttf", it["name"], tw, (31, 28, 25))
            alh = f_an.size + 8
            f_as = font("PTSans-Regular.ttf", 23)
            subs = []
            for s_ in (it.get("sub", ""), it.get("sub2", "")):
                if s_:
                    subs += wrap(s_, f_as, tw)[:2]
            block_h = alh * len(alines) + (32 * len(subs) if subs else 0)
            ty = y + (ROW_H - block_h) // 2
            for ln in alines:
                d.text((tx, ty), ln, font=f_an, fill=TEXT)
                ty += alh
            for s in subs:
                d.text((tx, ty + 4), s, font=f_as, fill=MUTED)
                ty += 32
            f_pr = font("Oswald.ttf", 40 if it.get("price") is not None else 32, "SemiBold")
            d.text((x1 - 22, y + ROW_H / 2), price_text(it.get("price")), font=f_pr,
                   fill=INK if it.get("price") is not None else MUTED, anchor="rm")
            y += ROW_H + 18

    # ---- итог по комплекту ----
    if kit:
        y += 26
        d.rectangle([M, y, x1, y + 140], outline=INK, width=4)
        d.rectangle([M + 7, y + 7, x1 - 7, y + 133], outline=INK, width=1)
        f_kl = font("Oswald.ttf", 30, "Medium")
        kl = kit.get("label", "КОМПЛЕКТ")
        while f_kl.getlength(kl) > CW - 340 and f_kl.size > 20:
            f_kl = font("Oswald.ttf", f_kl.size - 2, "Medium")
        d.text((M + 26, y + 46), kl, font=f_kl, fill=INK, anchor="lm")
        d.text((M + 26, y + 100), "Все позиции в наличии · отправка СДЭК",
               font=font("PTSans-Regular.ttf", 23), fill=MUTED, anchor="lm")
        f_kp = font("Oswald.ttf", 56 if kit.get("price") is not None else 40, "Bold")
        d.text((x1 - 26, y + 70), price_text(kit.get("price")), font=f_kp,
               fill=INK if kit.get("price") is not None else MUTED, anchor="rm")
        y += 140 + 34

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
    print("saved", out_path, img.size, "| комплект:", price_text(kit.get("price")),
          "| позиций к комплекту:", len(opt_items))
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "kit.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "kit_out.jpg")
    with open(src, encoding="utf-8") as fh:
        build(json.load(fh), out)
