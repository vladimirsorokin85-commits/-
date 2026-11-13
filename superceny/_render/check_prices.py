# -*- coding: utf-8 -*-
"""Сверка цен в HTML с positions.json (v6, розница).

Проверяет в `<позиция>/{01_ЛИСТАЙ,03_СЦЕНАРИИ,04_CTA}.html`:
- для позиций с ценой (has_price) присутствует цена из `price_value`/`price_display`
  (валюта может быть «₽» или «руб.» — сверяем цифры);
- для позиций без цены — «Прайс по запросу» и нет ценника с числом+валютой.

Использование: python _render/check_prices.py [--partial]
Коды выхода: 0 — OK; 1 — расхождения; 2 — нет данных в positions.json.
"""
from __future__ import annotations

import argparse
import html as html_mod
import re
import sys

import superlib as L

PRICE_TOKEN_RE = re.compile(r"(?<!\d)\d{1,3}(?:[\s\u00a0\u202f]\d{3})*\s*(?:₽|руб\.?)", re.I)


def norm(s: str) -> str:
    return re.sub(r"[\s\u00a0\u202f]+", " ", s).strip().casefold()


def plain_text(raw: str) -> str:
    """HTML -> текст: убираем теги/сущности, чтобы цена, разбитая спанами, стала «198 000 руб.»."""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_mod.unescape(s)
    return norm(s)


def price_digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", action="store_true")
    a = ap.parse_args()

    pos = L.positions()
    if not any(isinstance(v, dict) and v.get("price_display") for v in pos.values()):
        print("Нет цен в positions.json (ожидаются price_display/has_price) — проверка пропущена")
        return 2

    checked = bad = 0
    for folder, meta in sorted(pos.items()):
        if not isinstance(meta, dict):
            continue
        has = bool(meta.get("has_price")) and meta.get("price_value") is not None
        want = str(meta.get("price_value") or "") if has else ""
        for code in ("01", "03", "04"):
            p = L.HTML_DIR / folder / (L.CARD_NAMES[code] + ".html")
            if not p.is_file():
                if not a.partial:
                    print(f"  НЕТ HTML: {folder}/{p.name}")
                    bad += 1
                continue
            raw = p.read_text(encoding="utf-8", errors="replace")
            txt = plain_text(raw)
            checked += 1
            prices = [price_digits(m.group(0)) for m in PRICE_TOKEN_RE.finditer(txt)]
            if has:
                if want not in prices:
                    print(f"  НЕТ ЦЕНЫ: {folder}/{p.name} — ожидали «{meta.get('price_display')}» "
                          f"(найдено: {prices[:6]})")
                    bad += 1
            else:
                if "прайс по запросу" not in txt:
                    print(f"  НЕТ «ПРАЙС ПО ЗАПРОСУ»: {folder}/{p.name}")
                    bad += 1
                elif prices:
                    print(f"  ЛИШНЯЯ ЦЕНА без прайса: {folder}/{p.name} ({prices[:4]})")
                    bad += 1

    print(f"Проверка цен: {checked} файлов, расхождений {bad}")
    if bad:
        print("ПРОБЛЕМЫ: цены в HTML не совпадают с positions.json", file=sys.stderr)
        return 0 if a.partial else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
