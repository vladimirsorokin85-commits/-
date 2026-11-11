# -*- coding: utf-8 -*-
"""Предпроверка «173 HTML готовы»: комплектность HTML до рендера.

Считает папки позиций, карточки 01–04, hero; находит неполные/лишние папки.
Использование: python _render/preflight.py [--expect-folders 43]
Коды выхода: 0 — комплект есть; 1 — неполный набор (можно -partial); 2 — нет HTML.
"""
from __future__ import annotations

import argparse
import sys
import time

import superlib as L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-folders", type=int, default=L.EXPECT_POSITIONS)
    ap.add_argument("--partial", action="store_true", help="неполный набор — не ошибка")
    a = ap.parse_args()

    if not L.HTML_DIR.is_dir():
        print(f"Нет каталога HTML: {L.HTML_DIR}")
        return 2
    items = L.scan_html()
    if not items:
        print("HTML карточек не найдено")
        return 2

    hero = [t for t in items if t["card"] == "00"]
    folders: dict[str, set[str]] = {}
    for t in items:
        if t["card"] != "00":
            folders.setdefault(t["folder"], set()).add(t["card"])

    full = [f for f, cs in folders.items() if cs == {"01", "02", "03", "04"}]
    incomplete = {f: sorted({"01", "02", "03", "04"} - cs) for f, cs in folders.items() if cs != {"01", "02", "03", "04"}}
    cards_total = sum(len(cs) for cs in folders.values())

    print(f"HTML: {len(items)} файлов | папок позиций: {len(folders)}/{a.expect_folders} | "
          f"карточек: {cards_total}/{a.expect_folders * 4} | hero: {'есть' if hero else 'НЕТ'}")
    if hero:
        print(f"  hero: {hero[0]['src'].name} ({time.strftime('%d.%m %H:%M:%S', time.localtime(hero[0]['src'].stat().st_mtime))})")
    if incomplete:
        print(f"  неполные папки ({len(incomplete)}):")
        for f, miss in sorted(incomplete.items()):
            print(f"    {f}: нет {', '.join(miss)}")
    mt = max(t["src"].stat().st_mtime for t in items)
    print(f"  последний mtime HTML: {time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(mt))}")

    # папки должны строго совпадать с positions.folder (бриф §9)
    expected_folders = set(L.positions().keys())
    if expected_folders:
        extra_folders = sorted(set(folders) - expected_folders)
        missing_folders = sorted(expected_folders - set(folders))
        if extra_folders:
            print(f"  ЛИШНИЕ папки (нет в positions.json): {', '.join(extra_folders)}")
        if missing_folders:
            print(f"  НЕТ папок из positions.json: {', '.join(missing_folders)}")
        if not extra_folders and not missing_folders:
            print(f"  папки совпадают с positions.json ({len(expected_folders)} шт.)")

    ok = (len(folders) == a.expect_folders and not incomplete and len(hero) == 1
          and cards_total == a.expect_folders * 4
          and (not expected_folders or set(folders) == expected_folders))
    if ok:
        print(f"КОМПЛЕКТ: {a.expect_folders * 4 + 1} HTML готовы ({a.expect_folders} папок × 4 + hero)")
        return 0
    print("КОМПЛЕКТ: НЕПОЛНЫЙ" + (" (partial — не ошибка)" if a.partial else ""))
    return 0 if a.partial else 1


if __name__ == "__main__":
    sys.exit(main())
