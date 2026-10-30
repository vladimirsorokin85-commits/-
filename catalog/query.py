#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЖИВАЯ ПРОВЕРКА НАЛИЧИЯ у Димы (совместимо со старой привычкой: query.py <слова>).

Порядок работы:
  1) если сеть пускает b2b.moysklad.ru напрямую — тянет свежий каталог (live);
  2) иначе работает по последнему снапшоту из catalog/data/ и предупреждает о возрасте.

Примеры:
  python3 catalog/query.py                      # сводка по базе
  python3 catalog/query.py ботинки 42           # поиск по словам
  python3 catalog/query.py --cat Обувь          # всё в категории
  python3 catalog/query.py --in-stock --json    # только в наличии, машинно
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from catalog import store
    from catalog.search import search, load_synonyms, filter_rows, group_families, money, render
except ImportError:  # noqa: BLE001
    import store  # type: ignore
    from search import search, load_synonyms, filter_rows, group_families, money, render  # type: ignore


def summary(rows, meta):
    in_stock = [r for r in rows if int(r.get("stock") or 0) > 0]
    cats = {}
    for r in in_stock:
        cats[r.get("category")] = cats.get(r.get("category"), 0) + 1
    top = sorted(cats.items(), key=lambda kv: -kv[1])[:20]
    out = [
        f"Источник: {store.source_line(meta)}",
        f"Товаров в каталоге: {len(rows)}",
        f"В наличии: {len(in_stock)} позиций, {sum(int(r['stock']) for r in in_stock)} шт.",
        "",
        "Топ категорий (в наличии):",
    ]
    out += [f"  · {c}: {n}" for c, n in top]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Наличие у Димы: поиск и сводка")
    ap.add_argument("words", nargs="*")
    ap.add_argument("--cat", help="категория (подстрока)")
    ap.add_argument("--in-stock", action="store_true")
    ap.add_argument("--no-stock", action="store_true")
    ap.add_argument("--budget", type=float)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--desc", action="store_true", help="искать и в описаниях")
    ap.add_argument("--live", action="store_true", help="принудительно обновить снапшот из API")
    args = ap.parse_args(argv)

    if args.live:
        if store.can_reach_live():
            print("Тяну свежий каталог из API МойСклад…")
            store.refresh_live()
        else:
            print("Прямого доступа к МойСклад из этого окружения нет — "
                  "обновляй снапшот через GitHub Actions (docs/WORKFLOW.md).")

    rows, meta = store.load_index()
    if not args.words and not args.cat and not args.in_stock and not args.no_stock:
        print(summary(rows, meta))
        return 0

    full = store.full_by_id() if args.desc else {}
    rows = filter_rows(rows, args, load_synonyms(), full, store.photos_by_id())
    hits = search(" ".join(args.words), rows=rows, full=full)
    fams = group_families(hits)[: args.limit]
    if args.json:
        print(json.dumps({"source": store.source_line(meta), "families": fams},
                         ensure_ascii=False, indent=1, default=str))
        return 0
    print(render(fams, meta, args, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
