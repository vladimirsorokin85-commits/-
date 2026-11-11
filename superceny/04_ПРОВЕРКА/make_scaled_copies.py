#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_scaled_copies.py — уменьшенные копии карточек «СУПЕРЦЕНЫ» для QA-читаемости.

Критерий Lead: карточки смотрят с монитора и телефона; проверяем не только PNG 1080,
но и копии 540 и 390 px по ширине. Скрипт создаёт копии в QA-папке (сдачу не трогает):
  superceny\\04_ПРОВЕРКА\\_tmp\\scaled\\540\\<folder>\\<card>.png
  superceny\\04_ПРОВЕРКА\\_tmp\\scaled\\390\\...
Плюс контактные листы 02_ХАРАКТЕРИСТИКИ по 8 ключевым позициям (для быстрого визуального аудита).

Запуск: python make_scaled_copies.py [--widths 540,390]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QA = Path(__file__).resolve().parent
SC = QA.parent
READY = SC / "05_ГОТОВОЕ"
OUT = QA / "_tmp" / "scaled"

KEY_FOLDERS = [
    "01_Муха-К-8", "02_ФПВ-7-КОМПАКТ", "03_К-8М", "04_К-12М",
    "08_Изделие-135-Багажный-бокс", "09_Штора-К-12-700", "12_Ребус-4", "20_РЭБ-тестер",
]
CARDS = ["01_СУПЕРЦЕНА", "02_ХАРАКТЕРИСТИКИ", "03_ПРИМЕНЕНИЕ", "04_СУПЕР-ПРЕДЛОЖЕНИЕ"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--widths", default="540,390")
    args = ap.parse_args(argv)
    try:
        from PIL import Image
    except Exception as exc:
        print("Pillow недоступен:", exc)
        return 1
    widths = [int(w) for w in args.widths.split(",") if w.strip()]
    pngs = sorted(READY.rglob("*.png"))
    if not pngs:
        print("Нет PNG в 05_ГОТОВОЕ")
        return 1
    for width in widths:
        made = 0
        base = OUT / str(width)
        for f in pngs:
            rel = f.relative_to(READY)
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            im = Image.open(f).convert("RGB")
            h = round(im.height * width / im.width)
            im.resize((width, h), Image.LANCZOS).save(dst, optimize=True)
            made += 1
        print(f"  {width}px: {made} файлов -> {base}")
    # контактный лист 02-карточек 8 ключевых позиций (для быстрого просмотра)
    sheet_paths = []
    for folder in KEY_FOLDERS:
        for f in (READY / folder).glob("02_ХАРАКТЕРИСТИКИ.png"):
            sheet_paths.append(f)
    if sheet_paths:
        cols = 2
        cell_w = 540
        ims = [Image.open(f).convert("RGB").resize((cell_w, round(cell_w * 1350 / 1080)), Image.LANCZOS) for f in sheet_paths]
        rows = (len(ims) + cols - 1) // cols
        cell_h = ims[0].height
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#ddd")
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * cell_w, (i // cols) * cell_h))
        p = OUT / "contact_02.png"
        sheet.save(p, optimize=True)
        print("  контактный лист 02:", p)
    print("готово:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
