# -*- coding: utf-8 -*-
"""Контактные листы карусели: 4 слайда подряд для каждой из 20 позиций.

Вход:  superceny/05_ГОТОВОЕ/<папка>/{01_ЛИСТАЙ,02_ЦИФРЫ,03_СЦЕНАРИИ,04_CTA}.png
Выход: superceny/04_ПРОВЕРКА/карусели/<папка>.png — полоса 2700 px (4 слайда подряд,
       подписи, номера, стрелки) — видно, что серия читается как история.

Использование: python _render/make_carousels.py [--width 2700]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import superlib as L

PAD = 28
GAP = 16
HEAD_H = 96
LABEL_H = 46
FOOT_H = 26
BG = (233, 229, 218)
CARD = (255, 255, 255)
INK = (29, 30, 26)
MUTED = (90, 90, 79)
ACCENT = (200, 69, 31)
LINE = (201, 196, 180)
SLIDES = ["01", "02", "03", "04"]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for c in ((r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
              (r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf")):
        if Path(c).is_file():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=2700, help="ширина листа (2700 = 4×675)")
    ap.add_argument("--out", default=str(L.CARR_DIR))
    ap.add_argument("--png-root", default="", help="альтернативный корень с папками PNG (для тестов)")
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pos_meta = L.positions()
    folders: dict[str, dict] = {}
    if a.png_root:
        root = Path(a.png_root)
        for d in sorted([p for p in root.iterdir() if p.is_dir()]) if root.is_dir() else []:
            cards = {}
            for code in SLIDES:
                p = d / (L.CARD_NAMES[code] + ".png")
                if p.is_file():
                    cards[code] = {"out": p, "folder": d.name}
            if cards:
                folders[d.name] = cards
    else:
        for it in L.scan_html():
            if it["card"] == "00":
                continue
            folders.setdefault(it["folder"], {})[it["card"]] = it

    if not folders:
        print(f"Нет папок с PNG: {a.png_root or L.OUT_DIR}")
        return 1

    slide_w = (a.width - 2 * PAD - 3 * GAP) // 4
    slide_h = round(slide_w * L.CARD_H / L.CARD_W)
    sheet_h = PAD + HEAD_H + slide_h + LABEL_H + FOOT_H + PAD
    f_head = font(30, True)
    f_sub = font(16)
    f_label = font(16, True)
    f_small = font(14)
    f_arrow = font(30, True)

    done, missing = [], []
    total_bytes = 0
    for folder in sorted(folders):
        items = folders[folder]
        miss = [c for c in SLIDES if c not in items]
        if miss:
            missing.append(f"{folder}: нет {', '.join(miss)}")
            continue
        meta = pos_meta.get(folder, {})
        name = meta.get("name") or folder
        sheet = Image.new("RGB", (a.width, sheet_h), BG)
        d = ImageDraw.Draw(sheet)

        # шапка
        d.text((PAD, PAD + 6), f"{folder.split('_')[0]} · {name}", font=f_head, fill=INK)
        right = f"КАРУСЕЛЬ · 4 слайда подряд · {len(folders)} позиций"
        rw = d.textlength(right, font=f_small)
        d.text((a.width - PAD - rw, PAD + 18), right, font=f_small, fill=MUTED)
        d.line((PAD, PAD + HEAD_H - 18, a.width - PAD, PAD + HEAD_H - 18), fill=LINE, width=2)

        # 4 слайда в ряд
        y = PAD + HEAD_H
        for i, code in enumerate(SLIDES):
            p = items[code]["out"]
            x = PAD + i * (slide_w + GAP)
            d.rectangle((x, y, x + slide_w, y + slide_h), fill=CARD, outline=LINE)
            try:
                with Image.open(p) as im:
                    im.load()
                    if im.mode != "RGB":
                        im = im.convert("RGB")
                    im = im.resize((slide_w, slide_h), Image.LANCZOS)
                    sheet.paste(im, (x, y))
            except Exception as e:
                missing.append(f"{folder}/{p.name}: {e}")
                d.text((x + 12, y + 12), "НЕТ PNG", font=f_sub, fill=ACCENT)
            # подпись слайда
            label = f"{code} · {L.CARD_TITLES[code].upper()}"
            d.text((x + 8, y + slide_h + 12), label, font=f_label, fill=INK)
            # стрелка «листай» между слайдами
            if i < 3:
                ax = x + slide_w + GAP // 2 - 6
                ay = y + slide_h // 2 - 14
                d.text((ax, ay), "›", font=f_arrow, fill=ACCENT)

        # футер
        foot = (f"Контактный лист карусели · superceny · {time.strftime('%d.%m.%Y')} · "
                f"слайды 1080×1350, лист {a.width}×{sheet_h}")
        d.text((PAD, sheet_h - PAD - FOOT_H + 6), foot, font=f_small, fill=MUTED)

        out = out_dir / f"{folder}.png"
        sheet.save(out, "PNG", optimize=True)
        total_bytes += out.stat().st_size
        done.append(out)
        print(f"  {out.name:<42} {a.width}×{sheet_h}  {L.human_size(out.stat().st_size)}")

    print(f"Контактные листы карусели: {len(done)}/20 · {L.human_size(total_bytes)} → {out_dir}")
    if missing:
        print("ПРОБЛЕМЫ:")
        for m in missing:
            print(f"  - {m}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
