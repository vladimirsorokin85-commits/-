# -*- coding: utf-8 -*-
"""Контактный лист всех баннеров (Pillow) для QA: banners/_render/_qa/contact_sheet.jpg.

Посты 1080×1350 и квадраты 1080×1080 — двумя секциями по 6 колонок.
Использование: python _render/contact_sheet.py
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import bannerlib as L

CELL_W = 400
GAP = 18
PAD = 28
CAP_H = 48
BG = (233, 229, 218)
CARD = (255, 255, 255)
INK = (29, 30, 26)
MUTED = (90, 90, 79)
ACCENT = (200, 69, 31)


def font(size: int, bold: bool = False):
    for c in ((r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
              (r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf")):
        if Path(c).is_file():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def collect() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {"poster": [], "square": [], "story": []}
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        if p.stem.endswith("@2x"):
            continue
        base, fmt, pid = L.classify(p.stem)
        if fmt in groups and pid:
            groups[fmt].append(p)

    def key(p: Path):
        _, _, pid = L.classify(p.stem)
        return L.ORDER.index(pid) if pid in L.ORDER else 99
    for v in groups.values():
        v.sort(key=key)
    return groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.QA_DIR / "contact_sheet.jpg"))
    a = ap.parse_args()
    L.ensure_dirs(L.QA_DIR)
    groups = collect()
    total = sum(len(v) for v in groups.values())
    fonts = {"title": font(32, True), "sub": font(16), "id": font(16, True),
             "cap": font(13), "small": font(12)}

    cols_map = {"poster": 6, "square": 6, "story": 4}
    cols = 6
    sheet_w = PAD * 2 + cols * CELL_W + (cols - 1) * GAP
    blocks = []
    y = 116
    for fmt in ("poster", "square", "story"):
        items = groups[fmt]
        if not items:
            continue
        fcols = cols_map[fmt]
        rows = [items[i:i + fcols] for i in range(0, len(items), fcols)]
        blocks.append(("section", fmt, len(items), y, 0, 0))
        y += 34
        for row in rows:
            cells = []
            rh = 0
            for p in row:
                dims = L.png_dims(p) or (0, 0)
                w = dims[0]
                ih = round(dims[1] * CELL_W / w) if w else 400
                cells.append((p, ih, dims))
                rh = max(rh, ih)
            blocks.append(("row", cells, rh, y, 0, 0))
            y += rh + CAP_H + GAP
        y += 14
    sheet_h = y + PAD - GAP + 28

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, PAD - 8), "РЕКЛАМНЫЕ БАННЕРЫ «КИЛОВАТТ» · контактный лист", font=fonts["title"], fill=INK)
    d.text((PAD, PAD + 36),
           f"В ОКОПЕ × НПО «Киловатт» · ноябрь 2026 · PNG 1×: {total} "
           f"(посты {len(groups['poster'])}/18, квадраты {len(groups['square'])}/18, "
           f"сторис {len(groups['story'])}/6) · собрано {time.strftime('%d.%m.%Y %H:%M')}",
           font=fonts["sub"], fill=MUTED)
    d.line((PAD, 96, sheet_w - PAD, 96), fill=(201, 196, 180), width=2)

    broken = []
    for b in blocks:
        if b[0] == "section":
            _, fmt, n, yy, _, _ = b
            title = {"poster": "ПОСТЫ · 1080×1350", "square": "КВАДРАТЫ · 1080×1080",
                     "story": "СТОРИС · 1080×1920"}[fmt]
            color = {"poster": ACCENT, "square": (60, 74, 40), "story": (40, 62, 92)}[fmt]
            d.text((PAD, yy), title, font=fonts["sub"], fill=color)
            d.text((PAD + int(d.textlength(title, font=fonts["sub"])) + 12, yy + 1), f"{n} шт.",
                   font=fonts["small"], fill=MUTED)
        else:
            _, cells, rh, yy, _, _ = b
            for i, (p, ih, dims) in enumerate(cells):
                x = PAD + i * (CELL_W + GAP)
                d.rectangle((x, yy, x + CELL_W, yy + rh + CAP_H), fill=CARD, outline=(201, 196, 180))
                try:
                    with Image.open(p) as im:
                        im.load()
                        if im.mode != "RGB":
                            im = im.convert("RGB")
                        im.thumbnail((CELL_W, rh), Image.LANCZOS)
                        sheet.paste(im, (x + (CELL_W - im.size[0]) // 2, yy + (rh - im.size[1]) // 2))
                except Exception as e:
                    broken.append(f"{p.name}: {e}")
                    d.text((x + 10, yy + 10), "БИТЫЙ PNG", font=fonts["id"], fill=ACCENT)
                cy = yy + rh
                d.line((x, cy, x + CELL_W, cy), fill=(201, 196, 180), width=1)
                pid = L.banner_id(p.stem) or "—"
                d.text((x + 10, cy + 7), pid, font=fonts["id"], fill=ACCENT)
                d.text((x + 48, cy + 8), L.MODELS.get(pid, "")[:34], font=fonts["cap"], fill=INK)
                d.text((x + 10, cy + 27), f"{dims[0]}×{dims[1]} px · {L.human_size(p.stat().st_size)}",
                       font=fonts["small"], fill=MUTED)

    if broken:
        d.text((PAD, sheet_h - 24), "БИТЫЕ: " + "; ".join(broken)[:180], font=fonts["small"], fill=ACCENT)
    else:
        d.text((PAD, sheet_h - 24), "Все файлы открылись · QA: обрезка текста, читаемость названия, наложения, CTA",
               font=fonts["small"], fill=MUTED)
    out = Path(a.out)
    sheet.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"Контактный лист: {out} ({sheet.size[0]}×{sheet.size[1]} px, {L.human_size(out.stat().st_size)})")
    print(f"  PNG 1×: {total} (посты {len(groups['poster'])}/18, квадраты {len(groups['square'])}/18, "
          f"сторис {len(groups['story'])}/6)")
    if broken:
        for b in broken:
            print(f"  БИТЫЙ: {b}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
