#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка каталога поставщика front-ts.ru из выгрузки моста.

Вход:  suppliers/frontts/data/products.json   (ветка frontts-data, не в git)
       suppliers/frontts/data/groups.json     (наши разделы: slug → группа, коммитится вручную)
Выход: suppliers/frontts/catalog.json         (в git: товары без фото-файлов, только данные)
       prices/frontts_zakup.csv               (ВНЕ git: РРЦ и закуп владельца = РРЦ − 15 %)

Запуск: python3 suppliers/frontts/build_catalog.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "catalog.json")
PRICES = os.path.join(ROOT, "prices", "frontts_zakup.csv")

MARGIN = 0.15          # договорённость с поставщиком: −15 % от их цены


def main():
    src = os.path.join(DATA, "products.json")
    items = json.load(open(src, encoding="utf-8"))
    groups = {}
    gp = os.path.join(HERE, "groups.json")
    if os.path.exists(gp):
        flat = json.load(open(gp, encoding="utf-8"))
        for g, slugs in flat.items():
            for sl in slugs:
                groups[sl] = g

    out, no_photo, no_price = [], [], []
    for it in items:
        slug = it["slug"]
        rec = {
            "slug": slug,
            "name": re.sub(r"\s+", " ", it["name"]).strip(),
            "url": it["url"],
            "price_rrc": it.get("price"),
            "stock": it.get("stock"),
            "sku": it.get("sku", ""),
            "brand": it.get("brand", ""),
            "colors": it.get("colors", []),
            "descr": it.get("descr", ""),
            "photos": it.get("photos", []),
            "group": groups.get(slug, ""),
        }
        out.append(rec)
        if not rec["photos"]:
            no_photo.append(slug)
        if not rec["price_rrc"]:
            no_price.append(slug)

    out.sort(key=lambda r: (r["group"], r["name"]))
    json.dump({"supplier": "front-ts.ru", "margin": MARGIN, "count": len(out), "items": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    os.makedirs(os.path.dirname(PRICES), exist_ok=True)
    with open(PRICES, "w", encoding="utf-8") as f:
        f.write("товар;РРЦ (наша цена);закуп (РРЦ-15%);артикул;ссылка\n")
        for r in out:
            rrc = r["price_rrc"] or 0
            f.write(f"{r['name']};{rrc};{round(rrc * (1 - MARGIN))};{r['sku']};{r['url']}\n")

    print(f"каталог: {OUT} — {len(out)} товаров")
    print(f"без фото: {len(no_photo)} {no_photo[:6]}")
    print(f"без цены: {len(no_price)} {no_price[:6]}")
    noph = [r["slug"] for r in out if not r["group"]]
    print(f"без раздела: {len(noph)}")
    for s in noph:
        print("   ", s)


if __name__ == "__main__":
    main()
