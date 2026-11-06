# -*- coding: utf-8 -*-
"""Общие пути, форматы и утилиты пайплайна рекламных баннеров «Киловатт».

Пакет: banners/ — корень. Скрипты: banners/_render/. Готовое: banners/05_ГОТОВОЕ/.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

RENDER_DIR = Path(__file__).resolve().parent          # banners/_render
_env_root = os.environ.get("BAN_ROOT", "").strip()
ROOT = Path(_env_root).resolve() if _env_root else RENDER_DIR.parent   # banners
HTML_DIR = ROOT / "html"
STORY_DIR = ROOT / "story"
DESIGN_DIR = ROOT / "_design"
OUT_DIR = ROOT / "05_ГОТОВОЕ"
PNG_DIR = OUT_DIR / "png"
PDF_DIR = OUT_DIR / "pdf"
GALLERY_DIR = OUT_DIR / "gallery"
PREVIEW_DIR = OUT_DIR / "превью"
QA_DIR = (ROOT / "_render" / "_qa") if _env_root else (RENDER_DIR / "_qa")

PDF_NAME = "Рекламные_баннеры_Киловатт_2026.pdf"
PDF_PATH = PDF_DIR / PDF_NAME

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# --- форматы (бриф §3 + сторис 9:16) --------------------------------------
# fmt -> (css_w, css_h, suffix)
FORMATS = {
    "poster": (1080, 1350, "_1080x1350"),
    "square": (1080, 1080, "_1080x1080"),
    "story": (1080, 1920, "_1080x1920"),
}
FMT_LABEL = {"poster": "пост 1080×1350", "square": "квадрат 1080×1080",
             "story": "сторис 1080×1920"}
STORY_IDS = ["B01", "B02", "B07", "B08", "B10", "B12"]
MIN_PNG_BYTES = 50 * 1024
MIN_JPG_BYTES = 20 * 1024

# --- модели (бриф §2) ------------------------------------------------------
ORDER = [f"B{i:02d}" for i in range(1, 19)]
MODELS = {
    "B01": "«Капюшон» К-8М",
    "B02": "«Капюшон» К-12М",
    "B03": "«Капюшон» К-15М (и ВИП)",
    "B04": "«Капюшон» К-12 багажный бокс",
    "B05": "ФПВ-8М",
    "B06": "ФПВ-12",
    "B07": "ФПВ-5 мото",
    "B08": "«Штора» К-12/700",
    "B09": "«Штора-М» К-8/600",
    "B10": "«Ребус-4»",
    "B11": "«Поле-31»",
    "B12": "«Сигнал-М2»",
    "B13": "Рюкзак ТП 4-28А/Б",
    "B14": "Рюкзак ТП 4-50А/Б",
    "B15": "Рюкзак ТП 7-100",
    "B16": "Рюкзак ТП 8-100",
    "B17": "ИП-24/100",
    "B18": "РЭБ-тестер Т-9",
}
_ID_RE = re.compile(r"^(B\d{2})(?:_|$)")


def banner_id(text: str) -> str | None:
    stem = Path(text).stem if text.lower().endswith((".html", ".png", ".jpg")) else text
    m = _ID_RE.match(stem)
    return m.group(1) if m else None


def model_title(stem: str) -> str:
    pid = banner_id(stem)
    return MODELS.get(pid, stem)


def classify(filename: str) -> tuple[str, str, str]:
    """Имя файла -> (stem без формата, fmt, id). fmt = poster|square|''."""
    stem = Path(filename).stem
    for fmt, (_, _, suf) in FORMATS.items():
        if stem.endswith(suf):
            base = stem[: -len(suf)]
            return base, fmt, (banner_id(base) or "")
    # формата в имени нет — попробуем по «square»/«1080x1080» внутри
    if "1080x1080" in stem:
        return stem.replace("_1080x1080", ""), "square", (banner_id(stem) or "")
    if "1080x1350" in stem:
        return stem.replace("_1080x1350", ""), "poster", (banner_id(stem) or "")
    return stem, "", (banner_id(stem) or "")


def output_name(stem: str, scale: int = 1) -> str:
    return f"{stem}.png" if scale == 1 else f"{stem}@2x.png"


def fmt_size(fmt: str) -> tuple[int, int]:
    w, h, _ = FORMATS[fmt]
    return w, h


def human_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} МБ"
    if n >= 1024:
        return f"{n / 1024:.0f} КБ"
    return f"{n} Б"


def find_banner_pngs(fmt: str | None = None, scale: int = 1) -> dict[str, Path]:
    """id -> PNG (1x или @2x), для указанного формата. Первый по порядку B01..B18."""
    found: dict[str, Path] = {}
    if not PNG_DIR.is_dir():
        return found
    for p in sorted(PNG_DIR.glob("*.png")):
        stem = p.stem
        if stem.endswith("@2x"):
            if scale != 2:
                continue
            stem = stem[:-3]
        elif scale != 1:
            continue
        base, pfmt, pid = classify(stem)
        if fmt is not None and pfmt != fmt:
            continue
        if pid and pid not in found:
            found[pid] = p
    return found


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


IGNORE_FILE = RENDER_DIR / "ignored_html.txt"


def ignored_html() -> set[str]:
    """Устаревшие HTML (переименованные/удалённые), которые не индексируем."""
    if not IGNORE_FILE.is_file():
        return set()
    names = set()
    for line in IGNORE_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            names.add(Path(s).name)
    return names
