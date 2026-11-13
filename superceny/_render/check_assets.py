# -*- coding: utf-8 -*-
"""Проверка ассетов перед рендером v5 (печатный дизайн).

1) Сканирует HTML в 03_HTML и CSS в 02_ДИЗАЙН на ссылки; проверяет, что файлы существуют.
2) Для duotone-ассетов `img/print/*_duo*.png` проверяет прозрачность (RGBA + реальные
   прозрачные пиксели) — иначе на бумаге будет белый/студийный ореол.
3) Печатает таблицу: сколько ссылок, битых, проблем с прозрачностью.

Использование: python _render/check_assets.py [--partial]
Коды выхода: 0 — OK; 1 — битые ссылки/ассеты; 2 — нет HTML.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import superlib as L

IMG_RE = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+\.(?:png|jpg|jpeg|webp|svg))["']""", re.I)
CSS_URL_RE = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)


def resolve(base: Path, ref: str) -> Path | None:
    ref = ref.strip()
    if ref.startswith(("data:", "http:", "https:", "//", "#", "%23")):
        return None
    ref = ref.replace("\\", "/")
    p = Path(ref)
    if p.is_absolute():
        return p
    return (base / ref).resolve()


def check_transparency(path: Path) -> tuple[bool, str]:
    """(ok, note): ожидаем PNG с прозрачностью для duotone-вырезок.

    Учитывает палитровые PNG (mode P) с tRNS — они тоже дают прозрачный фон.
    """
    try:
        from PIL import Image
        with Image.open(path) as im:
            mode = im.mode
            has_alpha = "A" in mode or mode in ("P", "PA") or "transparency" in im.info
            if not has_alpha:
                return False, f"mode={mode} (нет alpha)"
            rgba = im.convert("RGBA")
            alpha = rgba.getchannel("A")
            lo, hi = alpha.getextrema()
            if lo > 250:
                return False, f"{mode}→RGBA, alpha min={lo} (нет прозрачных пикселей)"
            return True, f"{mode}→RGBA, alpha {lo}..{hi}"
    except Exception as e:
        return False, f"не открывается: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", action="store_true")
    a = ap.parse_args()

    html_files = sorted(L.HTML_DIR.rglob("*.html")) if L.HTML_DIR.is_dir() else []
    if not html_files:
        print(f"Нет HTML в {L.HTML_DIR}")
        return 2
    css_files = sorted(L.DESIGN_DIR.rglob("*.css")) if L.DESIGN_DIR.is_dir() else []

    refs: list[tuple[Path, str, Path]] = []   # (источник, исходная ссылка, разрешённый путь)
    seen = set()
    for p in html_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in IMG_RE.finditer(text):
            rp = resolve(p.parent, m.group(1))
            if rp is None or rp in seen:
                continue
            seen.add(rp)
            refs.append((p, m.group(1), rp))
    for p in css_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in CSS_URL_RE.finditer(text):
            rp = resolve(p.parent, m.group(1))
            if rp is None or rp in seen:
                continue
            seen.add(rp)
            refs.append((p, m.group(1), rp))

    broken = [(src, ref, rp) for src, ref, rp in refs if not rp.is_file()]
    duo = [(src, ref, rp) for src, ref, rp in refs
           if rp.is_file() and rp.suffix.lower() == ".png" and "_duo" in rp.stem]
    alpha_bad = []
    for src, ref, rp in duo:
        ok, note = check_transparency(rp)
        if not ok:
            alpha_bad.append((ref, note))

    print(f"Ассеты: ссылок {len(refs)} (HTML {len(html_files)}, CSS {len(css_files)}) | "
          f"битых {len(broken)} | duo-проверка {len(duo)} (проблем {len(alpha_bad)})")
    for src, ref, rp in broken[:20]:
        print(f"  БИТАЯ: {ref}  (из {src.name})")
    for ref, note in alpha_bad[:20]:
        print(f"  ПРОЗРАЧНОСТЬ: {ref} — {note}")

    if broken:
        print("ПРОБЛЕМЫ: есть битые ссылки на ассеты", file=sys.stderr)
        return 0 if a.partial else 1
    if alpha_bad and not a.partial:
        print("ВНИМАНИЕ: duo-ассеты без прозрачности (возможен ореол)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
