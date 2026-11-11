# -*- coding: utf-8 -*-
"""Общие пути, раскладка и утилиты пайплайна «СУПЕРЦЕНЫ».

Пакет: superceny/ — корень. Скрипты: superceny/_render/. Готовое: superceny/05_ГОТОВОЕ/.
HTML: superceny/03_HTML/<folder>/<card>.html + hero 00_СУПЕРЦЕНЫ.html.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

RENDER_DIR = Path(__file__).resolve().parent
_env_root = os.environ.get("SUP_ROOT", "").strip()
ROOT = Path(_env_root).resolve() if _env_root else RENDER_DIR.parent
HTML_DIR = ROOT / "03_HTML"
DATA_DIR = ROOT / "01_ДАННЫЕ"
DESIGN_DIR = ROOT / "02_ДИЗАЙН"
OUT_DIR = ROOT / "05_ГОТОВОЕ"
GALLERY_DIR = OUT_DIR / "gallery"
QA_DIR = (ROOT / "_render" / "_qa") if _env_root else (RENDER_DIR / "_qa")
POSITIONS_JSON = DATA_DIR / "positions.json"

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CARD_W, CARD_H = 1080, 1350
MIN_PNG_BYTES = 50 * 1024

# состав пакета по брифу §9 (уточнение заказчика 11.11.2026): 20 позиций
EXPECT_POSITIONS = 20
EXPECT_CARDS = EXPECT_POSITIONS * 4      # 80
EXPECT_PNG = EXPECT_CARDS + 1            # + hero 00_СУПЕРЦЕНЫ.png = 81

# карточка: префикс имени HTML -> каноническое имя PNG (бриф §4)
CARD_NAMES = {
    "00": "00_СУПЕРЦЕНЫ",
    "01": "01_СУПЕРЦЕНА",
    "02": "02_ХАРАКТЕРИСТИКИ",
    "03": "03_ПРИМЕНЕНИЕ",
    "04": "04_СУПЕР-ПРЕДЛОЖЕНИЕ",
}
CARD_TITLES = {
    "00": "Общая карточка «СУПЕРЦЕНЫ»",
    "01": "Суперцена",
    "02": "Характеристики",
    "03": "Применение / кому",
    "04": "Супер-предложение",
}
HERO_ID = "00"


def card_of(stem: str) -> str | None:
    """Имя HTML -> код карточки 00..04 (по номеру в начале имени)."""
    m = re.match(r"^(0[0-4])(?:_|$)", stem)
    return m.group(1) if m else None


def canon_stem(stem: str) -> str:
    """Любое имя карточки -> каноническое (00_СУПЕРЦЕНЫ … 04_СУПЕР-ПРЕДЛОЖЕНИЕ)."""
    c = card_of(stem)
    return CARD_NAMES[c] if c else stem


def output_rel(html_path: Path) -> Path:
    """HTML -> относительный путь PNG в 05_ГОТОВОЕ (hero — в корень)."""
    html_path = Path(html_path)
    stem = html_path.stem
    c = card_of(stem)
    name = canon_stem(stem) + ".png"
    if c == HERO_ID:
        return Path(name)
    try:
        rel_parent = html_path.parent.relative_to(HTML_DIR)
    except ValueError:
        # HTML вне 03_HTML (напр. передан путём) — папка по имени родителя
        rel_parent = Path(html_path.parent.name) if html_path.parent.name else Path("")
    return rel_parent / name


def scan_html() -> list[dict]:
    """Все HTML пакета: [{src, folder, card, out_rel, out}]."""
    items = []
    if not HTML_DIR.is_dir():
        return items
    for p in sorted(HTML_DIR.rglob("*.html")):
        if p.name.startswith(("_", ".")):
            continue
        c = card_of(p.stem)
        if not c:
            continue
        rel = output_rel(p)
        items.append({"src": p, "stem": p.stem, "card": c,
                      "folder": str(p.parent.relative_to(HTML_DIR)) if p.parent != HTML_DIR else "",
                      "out_rel": rel, "out": OUT_DIR / rel})
    return items


def positions() -> dict[str, dict]:
    """folder -> позиция из positions.json (если файл есть)."""
    if not POSITIONS_JSON.is_file():
        return {}
    try:
        data = json.loads(POSITIONS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    arr = data if isinstance(data, list) else data.get("positions", data.get("items", []))
    res = {}
    for it in arr:
        if isinstance(it, dict) and it.get("folder"):
            res[str(it["folder"])] = it
    return res


def human_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} МБ"
    if n >= 1024:
        return f"{n / 1024:.0f} КБ"
    return f"{n} Б"


def png_dims(path: Path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
