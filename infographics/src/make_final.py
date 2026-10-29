#!/usr/bin/env python3
"""gen/*.png (сгенерированные слайды) -> out/*.jpg 1080x1350 (4:5) + PDF.

Использование:
    python infographics/src/make_final.py           # все слайды
    python infographics/src/make_final.py sidewinder_   # только фонарь
    python infographics/src/make_final.py slide_        # только бандаж
Префикс задаёт и имя PDF: <префикс>infographic.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
GEN, OUT = ROOT / "gen", ROOT / "out"
OUT.mkdir(exist_ok=True)
TW, TH, TARGET = 1080, 1350, 4 / 5

prefix = sys.argv[1] if len(sys.argv) > 1 else ""
files = sorted(p for p in GEN.glob("*.png") if p.name.startswith(prefix))
if not files:
    sys.exit(f"нет слайдов с префиксом {prefix!r} в {GEN}")

made = []
for f in files:
    im = Image.open(f).convert("RGB")
    w, h = im.size
    if w / h > TARGET:
        nw = int(h * TARGET)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w / h < TARGET:
        nh = int(w / TARGET)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((TW * 2, TH * 2), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=55, threshold=2))
    out = OUT / f.name.replace(".png", ".jpg")
    im.resize((TW, TH), Image.LANCZOS).save(out, quality=94, subsampling=1)
    made.append(out)
    print("ok", out)

imgs = [Image.open(p).convert("RGB") for p in made]
pdf = OUT / f"{prefix}infographic.pdf"
imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=150.0)
print("ok", pdf)
