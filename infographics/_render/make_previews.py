# -*- coding: utf-8 -*-
"""JPG-превью для Telegram/GitHub: ширина 1080, качество 88, sRGB.

Берёт готовые PNG из 05_ГОТОВОЕ/png (1× основной серии, широкие, истории;
@2x пропускает) и кладёт JPG в 05_ГОТОВОЕ/превью/ с тем же именем.
Устаревшие JPG (без PNG) удаляются.

Использование:
  python _render/make_previews.py [--width 1080] [--quality 88]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

import posterlib as L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--quality", type=int, default=88)
    a = ap.parse_args()

    L.ensure_dirs(L.PREVIEW_DIR)
    rows = []
    made = 0
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        stem, kind, scale = L.classify_png(p.name)
        if scale != 1:
            continue
        out = L.PREVIEW_DIR / (p.stem + ".jpg")
        try:
            with Image.open(p) as im:
                im.load()
                src_w, src_h = im.size
                if im.mode != "RGB":
                    im = im.convert("RGB")
                if src_w > a.width:
                    h = round(src_h * a.width / src_w)
                    im = im.resize((a.width, h), Image.LANCZOS)
                else:
                    h = src_h
                im.save(out, "JPEG", quality=a.quality, optimize=True, progressive=True)
            rows.append((out.name, (a.width if src_w > a.width else src_w, h), out.stat().st_size))
            made += 1
        except Exception as e:
            print(f"FAIL: {p.name}: {e}")

    # убрать устаревшие превью
    live = {L.PREVIEW_DIR / r[0] for r in rows}
    removed = 0
    for f in L.PREVIEW_DIR.glob("*.jpg"):
        if f not in live:
            f.unlink()
            removed += 1

    for name, dims, size in rows:
        print(f"  {name:<44} {dims[0]}×{dims[1]:<5} {L.human_size(size)}")
    print(f"Превью: {made} JPG ({a.width}px, q{a.quality}) в {L.PREVIEW_DIR}"
          + (f"; удалено устаревших: {removed}" if removed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
