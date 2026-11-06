# -*- coding: utf-8 -*-
"""JPG-превью баннеров: ширина 1080, качество 88 → banners/05_ГОТОВОЕ/превью/.

Берёт все PNG 1× (посты и квадраты), @2x пропускает. Устаревшие JPG удаляет.
Использование: python _render/make_previews.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

import bannerlib as L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--quality", type=int, default=88)
    a = ap.parse_args()
    L.ensure_dirs(L.PREVIEW_DIR)
    rows, made = [], 0
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        if p.stem.endswith("@2x"):
            continue
        base, fmt, pid = L.classify(p.stem)
        if not fmt:
            continue
        out = L.PREVIEW_DIR / (p.stem + ".jpg")
        try:
            with Image.open(p) as im:
                im.load()
                if im.mode != "RGB":
                    im = im.convert("RGB")
                if im.size[0] > a.width:
                    h = round(im.size[1] * a.width / im.size[0])
                    im = im.resize((a.width, h), Image.LANCZOS)
                im.save(out, "JPEG", quality=a.quality, optimize=True, progressive=True)
            rows.append((out.name, out.stat().st_size))
            made += 1
        except Exception as e:
            print(f"FAIL: {p.name}: {e}")
    live = {L.PREVIEW_DIR / r[0] for r in rows}
    removed = 0
    for f in L.PREVIEW_DIR.glob("*.jpg"):
        if f not in live:
            f.unlink()
            removed += 1
    for name, size in rows:
        print(f"  {name:<46} {L.human_size(size)}")
    print(f"Превью: {made} JPG ({a.width}px, q{a.quality}) в {L.PREVIEW_DIR}"
          + (f"; удалено устаревших: {removed}" if removed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
