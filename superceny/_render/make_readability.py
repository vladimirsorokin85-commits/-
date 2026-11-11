# -*- coding: utf-8 -*-
"""Уменьшенные копии карточек для QA читаемости (не входят в сдачу).

Для каждого PNG из 05_ГОТОВОЕ делает копии шириной 540 и 390 px
(пропорционально) в superceny/_render/_qa/readability/<width>/<folder>/<card>.png

Использование: python _render/make_readability.py [--widths 540,390]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

import superlib as L

DEFAULT_WIDTHS = (540, 390)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS))
    ap.add_argument("--out", default=str(L.QA_DIR / "readability"))
    args = ap.parse_args()
    widths = [int(x) for x in args.widths.split(",") if x.strip()]
    out_root = Path(args.out)
    if out_root.exists():
        shutil.rmtree(out_root, ignore_errors=True)
    out_root.mkdir(parents=True, exist_ok=True)

    made = {w: 0 for w in widths}
    bytes_total = {w: 0 for w in widths}
    for p in sorted(L.OUT_DIR.rglob("*.png")) if L.OUT_DIR.is_dir() else []:
        if "gallery" in p.parts or "@2x" in p.parts:
            continue
        rel = p.relative_to(L.OUT_DIR)
        try:
            with Image.open(p) as im:
                im.load()
                if im.mode != "RGB":
                    im = im.convert("RGB")
                for w in widths:
                    if im.size[0] <= w:
                        continue
                    h = round(im.size[1] * w / im.size[0])
                    small = im.resize((w, h), Image.LANCZOS)
                    dst = out_root / str(w) / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    small.save(dst, "PNG", optimize=True)
                    made[w] += 1
                    bytes_total[w] += dst.stat().st_size
        except Exception as e:
            print(f"FAIL: {rel}: {e}")
            return 1

    print(f"Копии для QA читаемости: {out_root}")
    for w in widths:
        print(f"  {w} px: {made[w]} PNG, {L.human_size(bytes_total[w])} → {out_root / str(w)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
