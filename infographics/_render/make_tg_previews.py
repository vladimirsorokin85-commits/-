# -*- coding: utf-8 -*-
"""3 лучших превью для Telegram владельца: 05_ГОТОВОЕ/превью_ТГ/.

Берёт финальные PNG 1× основной серии (по умолчанию P01, P02, P07),
делает JPG шириной 1080, q88, именем без @2x: P01_dva_gorizonta.jpg.
Устаревшие JPG из папки удаляются.

Использование:
  python _render/make_tg_previews.py [--ids P01,P02,P07] [--strict]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image

import posterlib as L

DEFAULT_IDS = ["P01", "P02", "P07"]


def find_main_one(pid: str) -> Path | None:
    if not L.PNG_DIR.is_dir():
        return None
    for p in sorted(L.PNG_DIR.glob(f"{pid}_*.png")):
        stem, kind, scale = L.classify_png(p.name)
        if kind == "main" and scale == 1:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=",".join(DEFAULT_IDS), help="ID через запятую (по умолчанию P01,P02,P07)")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--strict", action="store_true", help="падать, если какого-то постера нет")
    a = ap.parse_args()
    ids = [x.strip().upper() for x in a.ids.split(",") if x.strip()]

    L.ensure_dirs(L.PREVIEW_TG_DIR)
    made = []
    missing = []
    for pid in ids:
        src = find_main_one(pid)
        if src is None:
            missing.append(pid)
            continue
        out = L.PREVIEW_TG_DIR / (src.stem + ".jpg")
        try:
            with Image.open(src) as im:
                im.load()
                if im.mode != "RGB":
                    im = im.convert("RGB")
                if im.size[0] > a.width:
                    im = im.resize((a.width, round(im.size[1] * a.width / im.size[0])), Image.LANCZOS)
                im.save(out, "JPEG", quality=a.quality, optimize=True, progressive=True)
            made.append((out, out.stat().st_size))
        except Exception as e:
            print(f"FAIL: {src.name}: {e}")
            return 1

    live = {o.name for o, _ in made}
    removed = 0
    for f in L.PREVIEW_TG_DIR.glob("*.jpg"):
        if f.name not in live:
            f.unlink()
            removed += 1

    for out, size in made:
        print(f"  {out.name:<40} 1080×… {L.human_size(size)}")
    print(f"Превью для Telegram: {len(made)} JPG (1080 px, q{a.quality}) в {L.PREVIEW_TG_DIR}"
          + (f"; удалено устаревших: {removed}" if removed else ""))
    if missing:
        print(f"  ВНИМАНИЕ: нет готовых PNG для: {', '.join(missing)} — папка неполная", file=sys.stderr)
        if a.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
