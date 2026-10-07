#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РАСЧЁТ СКИДКИ по комплекту: сколько можно скинуть и как это подать — в ₽ или в %.

  # цены владельца списком, в порядке позиций (основа + позиции)
  python3 vk/discount.py shturmovik --retail 152000,15500,10500,13500,7900,7900,1800,1000
  # минимальная маржа, ниже которой не опускаемся (по умолчанию 12%)
  python3 vk/discount.py shturmovik --retail … --min-margin 10
  # записать цены в kit.json (для карточек/слайдов)
  python3 vk/discount.py shturmovik --retail … --save

Считаем: розница комплекта, закупка, маржа (₽ и % от розницы), максимальная скидка на комплект
при заданной минимальной марже, рабочая скидка 3–5 %, и как выгоднее показать — ₽ или %.
Лист для планшета: prices/<slug>_skidka.jpg (вне git: закупки не публикуем).
"""
import argparse
import json
import os
import sys

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "media", "blank"))
from blank import INK, MUTED, FRAME, TEXT, WHITE, font, paper, wrap  # noqa: E402  (PIL через vendor)

OUT = os.path.join(ROOT, "prices")
W, H = 1240, 1754
M = 70


def money(v):
    return f"{v:,.0f}".replace(",", " ") + " ₽"


def rub_short(v):
    return f"{v:,.0f}".replace(",", " ") + " ₽"


def load(slug):
    kit = json.load(open(os.path.join(HERE, "kits", f"{slug}.json"), encoding="utf-8"))
    idx = {r["id"]: r for r in json.load(open(
        os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))}
    rows = []
    for n in [kit["main"]] + kit["items"]:
        r = idx.get(n["id"], {})
        rows.append({"name": n.get("short") or n["name"], "buy": r.get("price") or 0})
    return kit, rows


def present_style(discount, retail):
    """Как выгоднее показать скидку: в рублях или в процентах."""
    pct = discount / retail * 100 if retail else 0
    if pct >= 10:
        return "percent", pct
    if discount < 1500:
        return "percent", pct
    return "money", pct


def draw(slug, kit, rows, retail, min_margin, example=False):
    buy_total = sum(r["buy"] for r in rows)
    retail_total = sum(retail)
    margin = retail_total - buy_total
    margin_pct = margin / retail_total * 100 if retail_total else 0
    d_max = max(0.0, retail_total - buy_total / (1 - min_margin / 100))
    style, d_pct = present_style(d_max, retail_total)
    work_lo, work_hi = retail_total * 0.03, retail_total * 0.05

    h = 260 + 104 * len(rows) + 780
    img = paper(W, h)
    d = ImageDraw.Draw(img)
    d.text((M, 56), "В ОКОПЕ · МАГАЗИН БРОНИ", font=font("PTSans-Bold.ttf", 26), fill=MUTED)
    d.text((M, 96), "ЦЕНЫ И СКИДКА", font=font("RussoOne.ttf", 52), fill=INK)
    d.text((M, 168), kit["title"], font=font("PTSans-Bold.ttf", 30), fill=TEXT)
    if example:
        d.rectangle([W - M - 240, 92, W - M, 152], outline=FRAME, width=3)
        d.text((W - M - 120, 122), "ПРИМЕР", font=font("Oswald.ttf", 34, "Medium"),
               fill=FRAME, anchor="mm")
    d.line([(M, 214), (W - M, 214)], fill=INK, width=3)

    y = 232
    d.text((M, y), "ПОЗИЦИЯ", font=font("PTSans-Bold.ttf", 22), fill=MUTED)
    d.text((W - M - 520, y), "ЗАКУПКА", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="ra")
    d.text((W - M - 280, y), "ВАША ЦЕНА", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="ra")
    d.text((W - M, y), "МАКС. СКИДКА", font=font("PTSans-Bold.ttf", 22), fill=MUTED, anchor="ra")
    y += 40
    for i, (r, p) in enumerate(zip(rows, retail), 1):
        if i % 2 == 0:
            d.rectangle([M - 12, y - 6, W - M + 12, y + 84], fill=WHITE)
        cy = y + 40  # вертикальный центр строки
        d.text((M, cy), f"{i}", font=font("Oswald.ttf", 30, "Medium"), fill=FRAME, anchor="mm")
        f = font("PTSans-Bold.ttf", 22)
        name_lines = wrap(r["name"], f, 360)[:2]
        ny = cy - (len(name_lines) - 1) * 15
        for ln in name_lines:
            d.text((M + 44, ny), ln, font=f, fill=TEXT, anchor="lm")
            ny += 30
        d.text((W - M - 520, cy), rub_short(r["buy"]),
               font=font("Oswald.ttf", 30, "Medium"), fill=MUTED, anchor="rm")
        d.text((W - M - 280, cy), rub_short(p),
               font=font("Oswald.ttf", 32, "Medium"), fill=INK, anchor="rm")
        pos_max = max(0.0, p - r["buy"] / (1 - min_margin / 100))
        d.text((W - M, cy), f"−{rub_short(pos_max)}" if pos_max >= 1 else "—",
               font=font("Oswald.ttf", 28, "Medium"), fill=FRAME, anchor="rm")
        y += 104

    y += 14
    d.line([(M, y), (W - M, y)], fill=INK, width=3)
    y += 20
    lines = [
        ("Розница комплекта", rub_short(retail_total), True),
        ("Закупка комплекта", rub_short(buy_total), False),
        (f"Маржа при этих ценах", f"{rub_short(margin)}   ({margin_pct:.0f} % от цены)", False),
        (f"Максимум скидки (маржа не ниже {min_margin:.0f} %)", f"{rub_short(d_max)}   ({d_pct:.1f} % от цены)", True),
    ]
    for i, (label, value, strong) in enumerate(lines):
        if i == 3:
            d.rectangle([M - 12, y - 8, W - M + 12, y + 62], outline=INK, width=3)
        d.text((M, y), label, font=font("PTSans-Bold.ttf" if strong else "PTSans-Regular.ttf", 26),
               fill=INK if strong else TEXT)
        d.text((W - M, y), value, font=font("Oswald.ttf", 34 if strong else 30, "Medium"),
               fill=INK if strong else TEXT, anchor="ra")
        y += 66

    y += 20
    d.line([(M, y), (W - M, y)], fill=FRAME, width=1)
    y += 18
    d.text((M, y), "КАК ПОДАТЬ", font=font("PTSans-Bold.ttf", 22), fill=MUTED)
    y += 36
    if style == "money":
        headline = f"Скидка на комплект — {rub_short(d_max)}"
    else:
        headline = f"Скидка на комплект — {d_pct:.1f} %"
    fs = 44
    while font("Oswald.ttf", fs, "Bold").getlength(headline) > W - 2 * M and fs > 26:
        fs -= 2
    d.text((M, y), headline, font=font("Oswald.ttf", fs, "Bold"), fill=INK)
    y += fs + 22
    other = (f"({d_pct:.1f} % от цены)" if style == "money" else f"({rub_short(d_max)})")
    d.text((M, y), f"в скобках или мелким шрифтом — {other}", font=font("PTSans-Regular.ttf", 24), fill=MUTED)
    y += 50
    d.text((M, y), f"Рабочий диапазон по вашему правилу (3–5 %): "
                   f"{rub_short(work_lo)} – {rub_short(work_hi)}", font=font("PTSans-Regular.ttf", 26), fill=TEXT)
    y += 46
    for note in [
        "Скидка — только на комплект целиком; отдельные позиции считаем по столбцу «макс. скидка».",
        "В пост скидка идёт только после вашего «ок»; цену в текст поста не пишем (правило магазина).",
    ]:
        for ln in wrap(note, font("PTSans-Regular.ttf", 23), W - 2 * M):
            d.text((M, y), ln, font=font("PTSans-Regular.ttf", 23), fill=MUTED)
            y += 32
        y += 8

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{slug}_skidka.jpg")
    img.save(path, quality=92, optimize=True)
    return path, dict(retail=retail_total, buy=buy_total, margin=margin, margin_pct=margin_pct,
                      d_max=d_max, d_pct=d_pct, style=style, work=(work_lo, work_hi))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--retail", required=True, help="цены через запятую, в порядке позиций")
    ap.add_argument("--min-margin", type=float, default=12.0)
    ap.add_argument("--save", action="store_true", help="записать цены в vk/kits/<slug>.json")
    ap.add_argument("--example", action="store_true", help="пометить лист как пример")
    a = ap.parse_args()

    retail = [float(x) for x in a.retail.replace(" ", "").split(",")]
    kit, rows = load(a.slug)
    if len(retail) != len(rows):
        raise SystemExit(f"СТОП: цен {len(retail)}, а позиций {len(rows)}")

    path, calc = draw(a.slug, kit, rows, retail, a.min_margin, example=a.example)
    print(f"лист: {path}")
    print(f"  розница: {money(calc['retail'])} | закупка: {money(calc['buy'])} | "
          f"маржа: {money(calc['margin'])} ({calc['margin_pct']:.1f} %)")
    print(f"  макс. скидка: {money(calc['d_max'])} = {calc['d_pct']:.1f} % | подать: "
          f"{'в рублях' if calc['style'] == 'money' else 'в процентах'}")
    print(f"  рабочий диапазон 3–5 %: {money(calc['work'][0])} – {money(calc['work'][1])}")

    if a.save:
        kit["main"]["price"] = retail[0]
        for n, p in zip(kit["items"], retail[1:]):
            n["price"] = p
        kit["kit"]["price"] = calc["retail"]
        json.dump(kit, open(os.path.join(HERE, "kits", f"{a.slug}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("  цены записаны в kit.json")


if __name__ == "__main__":
    main()
