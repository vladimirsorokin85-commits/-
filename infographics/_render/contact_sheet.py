# -*- coding: utf-8 -*-
"""Контактный лист всех готовых PNG (Pillow, сетка) — для визуального QA.

Собирает 1× PNG (основная серия, широкие, истории) в один JPG:
  _render/_qa/contact_sheet.jpg   (q88)
Подписи: ID · заголовок · размер px · вес. Битые/отсутствующие файлы
помечаются в шапке.

Использование:
  python _render/contact_sheet.py [--dark]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import posterlib as L

CELL_W = 420
GAP = 20
PAD = 30
CAP_H = 52
BG = (233, 229, 218)
CARD = (255, 255, 255)
INK = (29, 30, 26)
MUTED = (90, 90, 79)
ACCENT = (200, 69, 31)
LIME = (142, 174, 40)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        if Path(c).is_file():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def collect() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {"main": [], "wide": [], "story": []}
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        stem, kind, scale = L.classify_png(p.name)
        if scale != 1:
            continue
        groups[kind].append(p)

    def key(p: Path):
        pid = L.poster_id(p.stem)
        return (L.ORDER_MAIN.index(pid) if pid in L.ORDER_MAIN else 99, p.name)

    groups["main"].sort(key=key)
    groups["wide"].sort(key=lambda p: p.name)
    groups["story"].sort(key=lambda p: p.name)
    return groups


def section_meta(kind: str) -> tuple[str, int]:
    return {
        "main": ("ОСНОВНАЯ СЕРИЯ · 1080×1350", 5),
        "wide": ("ШИРОКИЕ · 1920×1080", 4),
        "story": ("ИСТОРИИ · 1080×1920", 3),
    }[kind]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.QA_DIR / "contact_sheet.jpg"))
    a = ap.parse_args()
    L.ensure_dirs(L.QA_DIR)
    groups = collect()
    total = sum(len(v) for v in groups.values())

    font_title = load_font(34, bold=True)
    font_sub = load_font(17)
    font_id = load_font(17, bold=True)
    font_cap = load_font(14)

    # предрасчёт ширины: максимальная секция
    max_cols = max([5] + [section_meta(k)[1] for k, v in groups.items() if v])
    sheet_w = PAD * 2 + max_cols * CELL_W + (max_cols - 1) * GAP

    # сначала соберём «строки» по секциям, чтобы знать высоту
    blocks = []  # (section_title, [row_items], cols)
    for kind in ("main", "wide", "story"):
        items = groups[kind]
        if not items:
            continue
        title, cols = section_meta(kind)
        rows = [items[i:i + cols] for i in range(0, len(items), cols)]
        blocks.append((title, kind, rows, cols, len(items)))

    head_h = 118
    y = head_h
    layout = []
    for title, kind, rows, cols, n in blocks:
        layout.append(("section", title, kind, n, y, cols))
        y += 20 + 12
        for row in rows:
            row_h = 0
            cells = []
            for p in row:
                try:
                    with Image.open(p) as im:
                        w, h = im.size
                        im.verify()
                except Exception:
                    w, h = 0, 0
                ih = round(h * CELL_W / w) if w else 300
                cells.append({"path": p, "ih": ih, "dims": (w, h), "size": p.stat().st_size})
                row_h = max(row_h, ih)
            layout.append(("row", cells, row_h, cols, y))
            y += row_h + CAP_H + GAP
        y += 14
    sheet_h = y + PAD - GAP + 30

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    d = ImageDraw.Draw(sheet)

    # шапка
    d.text((PAD, PAD - 6), "ДВА ГОРИЗОНТА · контактный лист", font=font_title, fill=INK)
    d.text((PAD, PAD + 44),
           f"НПО «Киловатт» × «В ОКОПЕ» · ноябрь 2026 · PNG: {total} шт. "
           f"(основная {len(groups['main'])}/10, широкие {len(groups['wide'])}, истории {len(groups['story'])}) · "
           f"собрано {time.strftime('%d.%m.%Y %H:%M')}",
           font=font_sub, fill=MUTED)
    d.line((PAD, head_h - 22, sheet_w - PAD, head_h - 22), fill=(201, 196, 180), width=2)

    broken = []
    for block in layout:
        if block[0] == "section":
            _, title, kind, n, yy, cols = block
            d.text((PAD, yy), title, font=font_sub, fill=ACCENT if kind == "main" else (60, 74, 40))
            xx = PAD + int(d.textlength(title, font=font_sub)) + 14
            d.text((xx, yy + 1), f"{n} шт.", font=font_cap, fill=MUTED)
        else:
            _, cells, row_h, cols, yy = block
            for i, c in enumerate(cells):
                x = PAD + i * (CELL_W + GAP)
                d.rectangle((x, yy, x + CELL_W, yy + row_h + CAP_H), fill=CARD, outline=(201, 196, 180))
                try:
                    with Image.open(c["path"]) as im:
                        im.load()
                        if im.mode != "RGB":
                            im = im.convert("RGB")
                        im.thumbnail((CELL_W, row_h), Image.LANCZOS)
                        sheet.paste(im, (x + (CELL_W - im.size[0]) // 2, yy + (row_h - im.size[1]) // 2))
                except Exception as e:
                    broken.append(f"{c['path'].name}: {e}")
                    d.text((x + 12, yy + 12), "БИТЫЙ PNG", font=font_id, fill=ACCENT)
                # подпись
                cy = yy + row_h
                d.line((x, cy, x + CELL_W, cy), fill=(201, 196, 180), width=1)
                pid = L.poster_id(c["path"].stem) or "—"
                d.text((x + 12, cy + 8), pid, font=font_id, fill=ACCENT)
                d.text((x + 52, cy + 8), L.title_for(c["path"].stem)[:34], font=font_cap, fill=INK)
                d.text((x + 12, cy + 30),
                       f"{c['dims'][0]}×{c['dims'][1]} px · {L.human_size(c['size'])}",
                       font=font_cap, fill=MUTED)

    if broken:
        d.text((PAD, sheet_h - 26), "БИТЫЕ: " + "; ".join(broken)[:180], font=font_cap, fill=ACCENT)
    else:
        d.text((PAD, sheet_h - 26),
               "Все файлы открылись · сетка для QA: проверить обрезку текста, читаемость, пустоты",
               font=font_cap, fill=MUTED)

    out = Path(a.out)
    sheet.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"Контактный лист: {out} ({sheet.size[0]}×{sheet.size[1]} px, {L.human_size(out.stat().st_size)})")
    print(f"  PNG 1×: {total} (основная {len(groups['main'])}/10, широкие {len(groups['wide'])}, истории {len(groups['story'])})")
    if broken:
        print("  БИТЫЕ ФАЙЛЫ:")
        for b in broken:
            print(f"    - {b}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
