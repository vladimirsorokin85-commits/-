#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
БЛАНК ПОДБОРА ИЗ КАТАЛОГА — собирает заказ/подборку по кодам товаров.

Примеры:
  python3 media/blank/order_from_catalog.py --codes 00895,00477 --prices 24900,1500
  python3 media/blank/order_from_catalog.py --codes 00327 --qty 2 --prices 7900 --title "РАСЧЁТ ПОД ЗАПРОС"
  python3 media/blank/order_from_catalog.py --query "жгут турникет" --qty 4 --json-only

Правила те же: фото — только от поставщика, цены — только владельца (иначе «по запросу»).
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from catalog import store
    from catalog.search import search, group_families, family_of
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore
    from search import search, group_families, family_of  # type: ignore

from from_catalog import photos_for, sub_from_name  # noqa: E402


def split_list(v, cast=str):
    if not v:
        return []
    return [cast(x.strip()) for x in str(v).split(",") if x.strip() != ""]


def pick_rows(rows, codes):
    out = []
    for c in codes:
        match = [r for r in rows if str(r.get("code")) == str(c)]
        if not match:
            raise SystemExit(f"Код {c} не найден в каталоге (проверь наличие в снапшоте).")
        out.append(match[0])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Бланк подбора по кодам каталога")
    ap.add_argument("--codes", help="коды через запятую: 00895,00477")
    ap.add_argument("--query", help="если кодов нет — взять первые N по запросу")
    ap.add_argument("--limit", type=int, default=1, help="сколько позиций взять по запросу")
    ap.add_argument("--qty", default="", help="количество через запятую (по умолчанию 1)")
    ap.add_argument("--prices", default="", help="розничные цены через запятую (пусто = по запросу)")
    ap.add_argument("--title", default="ПОДБОР ПОД ЗАПРОС")
    ap.add_argument("--date", default=datetime.date.today().strftime("%d.%m.%Y"))
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--json-out", default=os.path.join(HERE, "order.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out.png"))
    args = ap.parse_args(argv)

    rows, _ = store.load_index()
    if args.codes:
        picked = pick_rows(rows, split_list(args.codes))
    elif args.query:
        fams = group_families(search(args.query, rows=rows, full=store.full_by_id()))[: args.limit]
        if not fams:
            raise SystemExit(f"По запросу «{args.query}» ничего не найдено.")
        picked = [f["rows"][0] for f in fams]
    else:
        raise SystemExit("Нужен --codes или --query.")

    qtys = split_list(args.qty, int)
    prices = [float(x.replace(" ", "").replace("к", "000")) if x else None for x in split_list(args.prices)]
    if qtys and len(qtys) != len(picked):
        raise SystemExit(f"Количество: {len(qtys)} значений на {len(picked)} позиций — не совпало.")
    if prices and len(prices) != len(picked):
        raise SystemExit(f"Цены: {len(prices)} значений на {len(picked)} позиций — не совпало.")

    items, skipped = [], []
    for i, row in enumerate(picked):
        photos = photos_for(row, 1)
        if not photos:
            skipped.append((row["name"], row.get("code")))
            continue
        items.append({
            "photo": photos[0],
            "name": family_of(row["name"]),
            "sub": sub_from_name(row["name"]),
            "qty": qtys[i] if qtys else 1,
            "price": prices[i] if prices else None,
        })

    if skipped:
        print("⚠ Позиции без фото у поставщика (в бланк не попали, фото надо взять у поставщика):")
        for name, code in skipped:
            print(f"   · {name} (код {code})")
    if not items:
        raise SystemExit("СТОП: ни одного фото от поставщика — бланк собирать не из чего.")

    payload = {"date": args.date, "title": args.title, "items": items}
    json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"JSON бланка: {args.json_out} ({len(items)} поз.)")
    if args.json_only:
        return 0

    import blank  # noqa: E402
    blank.build(payload, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
