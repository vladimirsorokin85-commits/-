#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
КАРТОЧКА ИЗ КАТАЛОГА — автоматическая сборка по коду/запросу.

Собирает JSON для card.py из данных поставщика: наименование, цвет/размер,
разделы «Особенности/Характеристики» — прямо из описания, фото — только из
catalog/photos (то, что притянул workflow по заявке).

Примеры:
  python3 media/blank/from_catalog.py --code 00895 --price 24900
  python3 media/blank/from_catalog.py --query "ботинки greyman" --price 24900 --addon-code 00665 --addon-price 1500
  python3 media/blank/from_catalog.py --code 00895 --price 24900 --json-only   # только JSON, без рендера

Железные правила, которые проверяет скрипт:
  • нет фото от поставщика → карточку не собираем;
  • цена только от владельца (--price); без неё рендер запрещён.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (ROOT, os.path.join(ROOT, "media", "blank")):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from catalog import store
    from catalog.search import search, group_families, sizes_of, family_of, norm
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore
    from search import search, group_families, sizes_of, family_of, norm  # type: ignore

try:
    from vk.post import split_description, short_fact
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "vk"))
    from post import split_description, short_fact  # type: ignore


def sub_from_name(name: str) -> str:
    """«цвет Dark Green · размер 42 (270-275)» — что именно предлагаем."""
    parts = []
    m = re.search(r"цвет\s*([^,(]+)", name, re.I)
    if m:
        parts.append("цвет " + m.group(1).strip())
    for tag, pat in (("мох", r"мох"), ("цифра (ЕМР)", r"цифра|емр|пиксель"),
                     ("A-Tacs FG", r"a-?tacs"), ("мультикам", r"multicam|мультикам")):
        if re.search(pat, name, re.I) and norm(tag) not in norm(" ".join(parts)):
            parts.append(tag)
    sizes = sizes_of(name)
    if sizes:
        parts.append("размер " + ", ".join(sizes))
    return " · ".join(parts)


def sections_from_desc(desc: str):
    subtitle, feats, specs = split_description(desc)
    out = []
    if feats:
        out.append({"h": "ОСОБЕННОСТИ", "bullets": [short_fact(f, 190) for f in feats[:6]]})
    if specs:
        out.append({"h": "ХАРАКТЕРИСТИКИ", "bullets": [short_fact(s, 190) for s in specs[:8]]})
    return subtitle, out


def pick_row(args, rows, full):
    if args.code:
        for r in rows:
            if str(r.get("code")) == str(args.code):
                return r
        raise SystemExit(f"Код {args.code} не найден в каталоге.")
    if args.id:
        for r in rows:
            if r["id"] == args.id:
                return r
        raise SystemExit(f"id {args.id} не найден в каталоге.")
    hits = search(args.query, rows=rows, full=full)
    if not hits:
        raise SystemExit(f"По запросу «{args.query}» ничего не найдено.")
    fams = group_families(hits)
    return fams[0]["rows"][0]


def photos_for(row, limit=6, only_good=True):
    """Фото из заявки. По умолчанию — только годные для карточки (без полосок и превью)."""
    man = {m["id"]: m for m in store.photos_manifest()}
    entry = man.get(row["id"], {})
    files = entry.get("files") or []
    if not only_good:
        return files[:limit]
    details = entry.get("details") or []
    if details:
        good = [d["path"] for d in details if d.get("quality", "ok") == "ok"]
        return (good or files)[:limit]
    return files[:limit]


def build_payload(row, full_by_id, args):
    desc = (full_by_id.get(row["id"], {}) or {}).get("description", "")
    subtitle, sections = sections_from_desc(desc)
    photos = photos_for(row, args.photo_limit)
    fam = family_of(row["name"])
    name = args.title_name or fam
    sub = args.sub or sub_from_name(row["name"])
    payload = {
        "date": args.date,
        "title": args.card_title,
        "product": {
            "name": name, "sub": sub, "photos": photos, "sections": sections,
            "price_label": args.price_label, "price": args.price,
        },
    }
    if args.addon_code:
        arow = pick_row(argparse.Namespace(code=args.addon_code, id=None, query=None), *get_rows_full())
        adesc = (full_by_id.get(arow["id"], {}) or {}).get("description", "")
        asub = sub_from_name(arow["name"])
        aphotos = photos_for(arow, 1)
        if not aphotos:
            raise SystemExit(f"СТОП: у допродажи (код {args.addon_code}) нет фото от поставщика.")
        if args.addon_price is None:
            raise SystemExit("СТОП: для допродажи нужна цена владельца (--addon-price).")
        payload["addon"] = {
            "label": "ДОБАВИТЬ К ПОКУПКЕ",
            "name": family_of(arow["name"]),
            "sub": asub, "sub2": "",
            "photo": aphotos[0],
            "price": args.addon_price,
            "bundle_label": args.bundle_label,
        }
    return payload


def get_rows_full():
    rows, _ = store.load_index()
    return rows, store.full_by_id()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Карточка из каталога Димы")
    ap.add_argument("--code"); ap.add_argument("--id", dest="pid"); ap.add_argument("--query")
    ap.add_argument("--price", type=float, help="розничная цена ВЛАДЕЛЬЦА")
    ap.add_argument("--price-label", default="ЦЕНА")
    ap.add_argument("--addon-code"); ap.add_argument("--addon-price", type=float)
    ap.add_argument("--bundle-label", default="ИТОГО С ДОПОЛНЕНИЕМ")
    ap.add_argument("--card-title", default="ПОДБОР ПОД ЗАПРОС")
    ap.add_argument("--title-name", help="своё название в карточке (по умолчанию — из каталога)")
    ap.add_argument("--sub", help="своя подпись (цвет/размер)")
    ap.add_argument("--photo-limit", type=int, default=6)
    ap.add_argument("--date", default=__import__("datetime").date.today().strftime("%d.%m.%Y"))
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--json-out", default=os.path.join(HERE, "card_from_catalog.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "card_from_catalog.jpg"))
    args = ap.parse_args(argv)

    if not (args.code or args.pid or args.query):
        raise SystemExit("Нужен --code, --id или --query.")
    rows, full = get_rows_full()
    row = pick_row(args, rows, full)
    payload = build_payload(row, full, args)

    json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"JSON карточки: {args.json_out}")
    if not payload["product"]["photos"]:
        raise SystemExit(
            "СТОП: фото этой позиции не выкачаны.\n"
            f"  1) добавь id в catalog/requests/photos.json: {row['id']}\n"
            "  2) запусти workflow «Catalog fetch»\n"
            "  3) bash tools/catalog_pull.sh\n"
            "Или возьми фото у поставщика. Карточку без фото поставщика не собираем.")
    if args.price is None:
        raise SystemExit("СТОП: цены нет. Цены задаёт владелец — добавь --price (розница).")
    if args.json_only:
        return 0

    sys.path.insert(0, HERE)
    import card  # noqa: E402
    card.build(payload, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
