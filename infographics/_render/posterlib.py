# -*- coding: utf-8 -*-
"""Общие пути, метаданные и утилиты пайплайна «Два горизонта».

Пакет инфографики: infographics/ — корень. Скрипты лежат в infographics/_render/.
Готовые файлы — infographics/05_ГОТОВОЕ/.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# --- пути ------------------------------------------------------------------
RENDER_DIR = Path(__file__).resolve().parent          # infographics/_render
# INF_ROOT — для тестовых прогонов в песочнице (по умолчанию — infographics/)
_env_root = os.environ.get("INF_ROOT", "").strip()
ROOT = Path(_env_root).resolve() if _env_root else RENDER_DIR.parent
POSTERS_DIR = ROOT / "02_МАКЕТЫ" / "posters"
DESIGN_DIR = ROOT / "02_МАКЕТЫ" / "_design"
OUT_DIR = ROOT / "05_ГОТОВОЕ"
PNG_DIR = OUT_DIR / "png"
PREVIEW_DIR = OUT_DIR / "превью"
PREVIEW_TG_DIR = OUT_DIR / "превью_ТГ"
PDF_DIR = OUT_DIR / "pdf"
GALLERY_DIR = OUT_DIR / "gallery"
# QA-артефакты: в обычном режиме — _render/_qa; в песочнице (INF_ROOT) — внутри неё
QA_DIR = (ROOT / "_render" / "_qa") if _env_root else (RENDER_DIR / "_qa")

PDF_NAME = "Инфографика_Два_горизонта_2026.pdf"
PDF_PATH = PDF_DIR / PDF_NAME

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONTS_DIR = ROOT.parent / "kilowatt" / "design" / "fonts"
BRAND_DIR = ROOT.parent / "kilowatt" / "catalog" / "assets" / "img" / "brand"

# --- форматы (бриф §5) -----------------------------------------------------
MAIN = (1080, 1350)      # 4:5
WIDE = (1920, 1080)      # 16:9
STORY = (1080, 1920)     # 9:16
MIN_PNG_BYTES = 50 * 1024
MIN_JPG_BYTES = 20 * 1024

# --- порядок ---------------------------------------------------------------
ORDER_MAIN = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10"]
# порядок страниц PDF-альбома: обложка → P01 → P05 → P06 → P04 → P03 → P02 → P08
# → P07 → P09 → P10 → финальная страница (бриф §4)
ORDER_PDF = ["P01", "P05", "P06", "P04", "P03", "P02", "P08", "P07", "P09", "P10"]

TITLES = {
    "P01": "Два горизонта",
    "P02": "Карта линейки",
    "P03": "Эшелон защиты",
    "P04": "Что защищаем → что берём",
    "P05": "B2B: почему сейчас",
    "P06": "Правовой компас",
    "P07": "Купол на свой транспорт",
    "P08": "Сравнение моделей",
    "P09": "Как купить: 6 шагов",
    "P10": "Документы и сервис",
}

# ожидаемые имена (бриф §4) — только для подсказок/диагностики, не для ссылок
EXPECTED_STEMS = {
    "P01": "P01_dva_gorizonta",
    "P02": "P02_karta_linejki",
    "P03": "P03_eshelon_zashchity",
    "P04": "P04_chto_zashchishchaem",
    "P05": "P05_b2b_pochemu_sejchas",
    "P06": "P06_pravovoj_kompas",
    "P07": "P07_roznica_kupol",
    "P08": "P08_sravnenie_modelej",
    "P09": "P09_kak_kupit",
    "P10": "P10_dokumenty_i_servis",
}

KIND_LABEL = {"main": "основной 1080×1350", "wide": "широкий 1920×1080", "story": "история 1080×1920"}
KIND_SUFFIX = {"main": "", "wide": "_1920", "story": "_1080x1920"}
KIND_SIZE = {"main": MAIN, "wide": WIDE, "story": STORY}

_ID_RE = re.compile(r"^(P\d{2})(?:_|$)")
_WXH_RE = re.compile(r"_(\d{3,4})x(\d{3,4})$")
_PLAIN_W_RE = re.compile(r"_(\d{3,4})$")


def poster_id(text: str) -> str | None:
    """P01 из имени файла/заголовка."""
    m = _ID_RE.match(Path(text).stem if text.lower().endswith(".html") or text.lower().endswith(".png") else text)
    return m.group(1) if m else None


def title_for(stem: str) -> str:
    pid = poster_id(stem)
    return TITLES.get(pid, stem)


def canon_stem(stem: str) -> str:
    """P01_dva_gorizonta_1920 -> P01_dva_gorizonta (для выходных имён)."""
    s = stem
    if s.endswith("@2x"):
        s = s[:-3]
    m = _WXH_RE.search(s)
    if m:
        return s[: m.start()]
    m = _PLAIN_W_RE.search(s)
    if m and int(m.group(1)) in (1920, 1080, 1350, 2700):
        return s[: m.start()]
    for suf in ("_wide", "_story", "_16x9", "_9x16", "_1920x1080", "_1080x1920", "_desktop", "_desk"):
        if s.endswith(suf):
            return s[: -len(suf)]
    return s


def classify_png(filename: str) -> tuple[str, str, int]:
    """Имя PNG -> (stem без суффикса, kind, scale)."""
    stem = Path(filename).stem
    if stem.endswith("@2x"):
        return stem[:-3], "main", 2
    m = _WXH_RE.search(stem)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        kind = "wide" if w > h else "story"
        return stem[: m.start()], kind, 1
    m = _PLAIN_W_RE.search(stem)
    if m:
        return stem[: m.start()], "wide", 1
    return stem, "main", 1


def output_name(base: str, kind: str, scale: int) -> str:
    base = canon_stem(base)
    if kind == "main":
        return f"{base}.png" if scale == 1 else f"{base}@2x.png"
    return f"{base}{KIND_SUFFIX[kind]}.png"


def expected_dims(kind: str, scale: int = 1) -> tuple[int, int]:
    w, h = KIND_SIZE[kind]
    return w * scale, h * scale


def human_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} МБ"
    if n >= 1024:
        return f"{n / 1024:.0f} КБ"
    return f"{n} Б"


def main_pngs(stem_filter: str | None = None) -> list[Path]:
    """Основные PNG 1x по порядку P01..P10 (только реально существующие)."""
    found: dict[str, Path] = {}
    if PNG_DIR.is_dir():
        for p in PNG_DIR.glob("*.png"):
            stem, kind, scale = classify_png(p.name)
            if kind != "main" or scale != 1:
                continue
            pid = poster_id(stem)
            if pid and pid not in found:
                found[pid] = p
    result = []
    for pid in ORDER_MAIN:
        if pid in found:
            if stem_filter and pid not in stem_filter:
                continue
            result.append(found[pid])
    return result


def png_kind_dims(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
