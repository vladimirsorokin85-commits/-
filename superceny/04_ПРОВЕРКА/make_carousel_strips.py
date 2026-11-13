#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_carousel_strips.py — fallback: собрать контакт-листы карусели «4 слайда подряд» для QA.

Берёт PNG из superceny\\05_ГОТОВОЕ\\<папка>\\ (4 слайда по префиксам 01–04) и собирает:
  superceny\\04_ПРОВЕРКА\\_tmp\\strips\\<папка>.png    (4×1080 = 4320×1350)
  superceny\\04_ПРОВЕРКА\\_tmp\\strips390\\<папка>.png (4×390  = 1560×488)
Если renderer уже сделал 04_ПРОВЕРКА\\карусели\\ — скрипт их не перезаписывает (пишет в _tmp).

Запуск: python make_carousel_strips.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QA = Path(__file__).resolve().parent
SC = QA.parent
READY = SC / "05_ГОТОВОЕ"
OUT = QA / "_tmp" / "strips"
OUT390 = QA / "_tmp" / "strips390"


def main() -> int:
    try:
        from PIL import Image
    except Exception as exc:
        print("Pillow недоступен:", exc)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    OUT390.mkdir(parents=True, exist_ok=True)
    folders = [d for d in sorted(READY.iterdir()) if d.is_dir() and d.name != "gallery"]
    made = 0
    for d in folders:
        slides = []
        for idx in ("01", "02", "03", "04"):
            f = next(iter(sorted(d.glob(f"{idx}_*.png"))), None)
            if f:
                slides.append(f)
        if len(slides) < 4:
            print(f"  {d.name}: слайдов {len(slides)}/4 — пропуск")
            continue
        ims = [Image.open(f).convert("RGB") for f in slides]
        w = sum(im.width for im in ims)
        h = max(im.height for im in ims)
        strip = Image.new("RGB", (w, h), "#000")
        x = 0
        for im in ims:
            strip.paste(im, (x, 0))
            x += im.width
        strip.save(OUT / f"{d.name}.png", optimize=True)
        # 390-версия (для проверки читаемости серии на телефоне)
        ims390 = [im.resize((390, round(390 * im.height / im.width)), Image.LANCZOS) for im in ims]
        w390 = 390 * 4
        h390 = max(i.height for i in ims390)
        s390 = Image.new("RGB", (w390, h390), "#000")
        for i, im in enumerate(ims390):
            s390.paste(im, (i * 390, 0))
        s390.save(OUT390 / f"{d.name}.png", optimize=True)
        made += 1
        print(f"  {d.name}: ok")
    print(f"готово: {made} серий -> {OUT} | 390: {OUT390}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
