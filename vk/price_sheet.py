#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЛИСТ ЗАКУПКИ на планшет: позиции комплекта + закупочная цена + пустая колонка «ваша цена».

  python3 vk/price_sheet.py shturmovik medik zima

Результат: prices/<slug>_zakupka.jpg (картинка для владельца) — ВНЕ git: закупки не публикуем.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "media", "blank"))
from blank import INK, MUTED, FRAME, WHITE, TEXT, font, paper, wrap  # noqa: E402

OUT = os.path.join(ROOT, "prices")
W, H = 1240, 1754
M = 70


def load_catalog():
    idx = json.load(open(os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))
    return {r["id"]: r for r in idx}


def rows_for(slug, idx):
    kit = json.load(open(os.path.join(HERE, "kits", f"{slug}.json"), encoding="utf-8"))
    out = []
    for n in [kit["main"]] + kit["items"]:
        r = idx.get(n["id"], {})
        out.append({"name": n.get("short") or n["name"], "variant": n.get("variant", ""),
                    "buy": r.get("price"), "stock": r.get("stock", 0), "label": n.get("label", "")})
    return kit, out


def money(v):
    return f"{v:,.0f}".replace(",", " ") + " ₽" if v is not None else "—"


def sheet(slug, kit, rows):
    title = kit["title"]
    h = 250 + 104 * len(rows) + 300
    img = paper(W, h)
    d = ImageDraw.Draw(img)

    d.text((M, 56), "В ОКОПЕ · МАГАЗИН БРОНИ", font=font("PTSans-Bold.ttf", 26), fill=MUTED)
    d.text((M, 96), "ЗАКУПКА", font=font("RussoOne.ttf", 54), fill=INK)
    d.text((M, 170), title, font=font("PTSans-Bold.ttf", 30), fill=TEXT)
    d.line([(M, 214), (W - M, 214)], fill=INK, width=3)

    # шапка таблицы
    y = 232
    d.text((M, y), "ПОЗИЦИЯ", font=font("PTSans-Bold.ttf", 22), fill=MUTED)
    d.text((W - M - 330, y), "ЗАКУПКА", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="ra")
    d.text((W - M, y), "ВАША ЦЕНА", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="ra")
    y += 40

    for i, r in enumerate(rows, 1):
        if i % 2 == 0:
            d.rectangle([M - 12, y - 6, W - M + 12, y + 84], fill=(255, 255, 255))
        d.text((M, y + 6), f"{i}", font=font("Oswald.ttf", 30, "Medium"), fill=FRAME)
        f = font("PTSans-Bold.ttf", 25)
        lines = wrap(r["name"], f, 640)[:2]
        ty = y + 4
        for ln in lines:
            d.text((M + 44, ty), ln, font=f, fill=TEXT)
            ty += 32
        if r["variant"]:
            d.text((M + 44, ty), r["variant"], font=font("PTSans-Regular.ttf", 21), fill=MUTED)
        d.text((W - M - 330, y + 26), money(r["buy"]),
               font=font("Oswald.ttf", 32, "Medium"), fill=INK, anchor="ra")
        # пустое поле для цены владельца
        d.rectangle([W - M - 290, y + 2, W - M, y + 66], outline=FRAME, width=2)
        d.text((W - M - 16, y + 36), "₽", font=font("PTSans-Regular.ttf", 24), fill=MUTED, anchor="rm")
        y += 104

    total = sum(r["buy"] or 0 for r in rows)
    y += 16
    d.line([(M, y), (W - M, y)], fill=INK, width=3)
    d.text((M, y + 24), "ИТОГО ЗАКУПКА КОМПЛЕКТА", font=font("PTSans-Bold.ttf", 26), fill=INK)
    d.text((W - M - 290, y + 18), money(total), font=font("Oswald.ttf", 40, "Bold"), fill=INK, anchor="ra")
    d.text((M, y + 86),
           "Впишите свои цены (или пришлите числа списком) — посчитаю розницу комплекта,",
           font=font("PTSans-Regular.ttf", 22), fill=MUTED)
    d.text((M, y + 118),
           "максимальную скидку при вашей минимальной марже и покажу её в ₽ или % — что выгоднее.",
           font=font("PTSans-Regular.ttf", 22), fill=MUTED)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{slug}_zakupka.jpg")
    img.save(path, quality=92, optimize=True)
    print(f"  {slug}: {len(rows)} позиций, закупка {money(total)} → {path}")
    return path, total


def main():
    idx = load_catalog()
    slugs = sys.argv[1:] or ["shturmovik", "medik", "zima"]
    for slug in slugs:
        kit, rows = rows_for(slug, idx)
        sheet(slug, kit, rows)


if __name__ == "__main__":
    main()
