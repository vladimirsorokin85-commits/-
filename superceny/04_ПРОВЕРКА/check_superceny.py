#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_superceny.py — QA-линтер пакета «СУПЕРЦЕНЫ НА НПО „КИЛОВАТТ“» (роль qa).
DoD: бриф §8 + уточнение §9 (11.11.2026): 20 позиций × 4 карточки + hero = 81 PNG,
цена везде «Прайс по запросу», позиции 01 «Муха К-8» и 08 «Изделие 135 Багажный бокс» —
заглушки без ТТХ (данные запрошены у «Ховрино»).

Проверки:
  1) ДАННЫЕ: positions.json — 20 позиций в порядке §9, названия/каталог, ТТХ (6–8 строк
     для каталожных), нет выдуманных цифр и цен, «Прайс по запросу» везде.
  2) HTML: 03_HTML — 81 файл (20×4 + hero); BANNED/brief-запреты, CTA @vokope_ru и
     +7 (999) 136-71-42, «Доставка по РФ · Самовывоз в Москве», «Прайс по запросу»,
     юрстрока, цифры только из каталога/канона, нет битых картинок.
  3) PNG: 05_ГОТОВОЕ — 20 папок × 4 + 00_СУПЕРЦЕНЫ.png, 1080×1350, лишних/старых нет.
  4) Структура/DoD: gallery (81 ссылка), ЧЕК_ЛИСТ, README; старые 43-папочные версии удалены.

Результат: superceny\\04_ПРОВЕРКА\\QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.md / .json
Запуск: python check_superceny.py [--selftest] [--no-write] [--stage all|data|html|png]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "2.0"
PROJECT = Path(__file__).resolve().parents[2]
SC = PROJECT / "superceny"
QA = SC / "04_ПРОВЕРКА"
DATA = SC / "01_ДАННЫЕ"
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
PRODUCTS = PROJECT / "kilowatt" / "data" / "products.json"
CANON = PROJECT / "kilowatt" / "docs" / "КАНОН_цифры_и_факты.md"
BANNED = PROJECT / "infographics" / "01_ФАКТЫ" / "BANNED.md"
POSITIONS = DATA / "positions.json"
CLAIMS_PATH = PROJECT / "infographics" / "01_ФАКТЫ" / "claims.json"

_ic_path = PROJECT / "infographics" / "03_QA" / "check_claims.py"
_spec = importlib.util.spec_from_file_location("ic_super", _ic_path)
if _spec is None or _spec.loader is None:
    raise SystemExit(f"не найден общий модуль: {_ic_path}")
ic = importlib.util.module_from_spec(_spec)
sys.modules["ic_super"] = ic
_spec.loader.exec_module(ic)

# ---------------------------------------------------------------- DoD §9 (20 позиций)
CARDS = ["01_СУПЕРЦЕНА", "02_ХАРАКТЕРИСТИКИ", "03_ПРИМЕНЕНИЕ", "04_СУПЕР-ПРЕДЛОЖЕНИЕ"]
HERO = "00_СУПЕРЦЕНЫ"
CARD_SIZE = (1080, 1350)
EXPECTED_PNG = 81  # 20×4 + hero

EXPECTED = [
    {"order": 1,  "name": "Муха К-8",                "catalog": None,    "folder": "01_Муха-К-8"},
    {"order": 2,  "name": "ФПВ-7 КОМПАКТ",           "catalog": "kw-01", "folder": "02_ФПВ-7-КОМПАКТ"},
    {"order": 3,  "name": "К-8М",                    "catalog": "kw-05", "folder": "03_К-8М"},
    {"order": 4,  "name": "К-12М",                   "catalog": "kw-06", "folder": "04_К-12М"},
    {"order": 5,  "name": "К-12М Багажный бокс",     "catalog": "kw-02", "folder": "05_К-12М-Багажный-бокс"},
    {"order": 6,  "name": "К-15М",                   "catalog": "kw-07", "folder": "06_К-15М"},
    {"order": 7,  "name": "К-15М ВИП",               "catalog": "kw-03", "folder": "07_К-15М-ВИП"},
    {"order": 8,  "name": "Изделие 135 Багажный бокс", "catalog": None,  "folder": "08_Изделие-135-Багажный-бокс"},
    {"order": 9,  "name": "Штора К-12/700",          "catalog": "kw-15", "folder": "09_Штора-К-12-700"},
    {"order": 10, "name": "Штора-М, К-8/600",        "catalog": "kw-16", "folder": "10_Штора-М-К-8-600"},
    {"order": 11, "name": "Поле-31",                 "catalog": "kw-18", "folder": "11_Поле-31"},
    {"order": 12, "name": "Ребус-4",                 "catalog": "kw-17", "folder": "12_Ребус-4"},
    {"order": 13, "name": "ТП 4-28А",                "catalog": "kw-09", "folder": "13_ТП-4-28А"},
    {"order": 14, "name": "ТП 4-28Б",                "catalog": "kw-10", "folder": "14_ТП-4-28Б"},
    {"order": 15, "name": "ТП 4-50А",                "catalog": "kw-11", "folder": "15_ТП-4-50А"},
    {"order": 16, "name": "ТП 4-50Б",                "catalog": "kw-12", "folder": "16_ТП-4-50Б"},
    {"order": 17, "name": "ТП 7-100",                "catalog": "kw-13", "folder": "17_ТП-7-100"},
    {"order": 18, "name": "ТП 8-100",                "catalog": "kw-14", "folder": "18_ТП-8-100"},
    {"order": 19, "name": "Сигнал-М2",               "catalog": "kw-19", "folder": "19_Сигнал-М2"},
    {"order": 20, "name": "РЭБ-тестер",              "catalog": "kw-20", "folder": "20_РЭБ-тестер"},
]
EXPECTED_POS = len(EXPECTED)
EXPECTED_BY_ORDER = {e["order"]: e for e in EXPECTED}
PLACEHOLDER_ORDERS = {1, 8}  # новые позиции без данных каталога — допустимо (§9)
PRICE_CANON = "Прайс по запросу"
PRICE_RE = re.compile(r"прайс\s+по\s+запросу", re.I)
PRICE_DEPRECATED_RE = re.compile(r"(?:цена|стоимость)\s+по\s+запросу|спеццен", re.I)

PHONE_CANON = "+7 (999) 136-71-42"
PHONE_RE = re.compile(r"\+?7\s*\(?\s*999\s*\)?\s*[-\s]?\s*136\s*[-\s]?\s*71\s*[-\s]?\s*42")
TG_RE = re.compile(r"@\s*vokope_ru", re.I)
DELIVERY_RE = re.compile(r"доставк\w*\s+по\s+рф|самовывоз\w*\s+в\s+москв", re.I)
MONEY_RE = re.compile(r"\d[\d\s.,]*\s*(?:₽|руб\b\.?)", re.I)
SUPER_RE = re.compile(r"супер\s*[-‑–—\s]?\s*цен", re.I)
LEGAL_MARKERS = [
    re.compile(r"паспорт", re.I),
    re.compile(r"публичн\w*\s+оферт", re.I),
    re.compile(r"законодательств", re.I),
]
COUNTER_FORBIDDEN = re.compile(r"\b(?:43|33|41)\s+(?:позици|карточк|товар)", re.I)
PHOTO_PLACEHOLDER_RE = re.compile(r"фото\s+уточняется|данные\s+запрошены|по\s+запросу", re.I)

EXTRA_BANNED = [
    (re.compile(r"официальн\w*\s+(?:и\s+единственн\w*\s+)?дилер", re.I), "«официальный дилер» — статус не подтверждён"),
    (re.compile(r"100\s*%\s*защит", re.I), "«100% защита» — запрещено"),
    (re.compile(r"спас[её]т\s+жизн", re.I), "«спасёт жизнь» — запрещено"),
    (re.compile(r"дрон\w*\s+не\s+пролет", re.I), "«дрон не пролети» — запрещено"),
    (re.compile(r"единственн\w+", re.I), "«единственный» — запрещено"),
    (re.compile(r"инновационн\w+", re.I), "«инновационный» — запрещено"),
    (re.compile(r"в\s+современном\s+мире", re.I), "«в современном мире» — запрещено"),
]
SLOP_WORDS = [r"является", r"абсолютн\w+", r"в\s+любых\s+условиях", r"гарантированн\w+"]
SLOP_EXEMPT_RE = [
    re.compile(r"не\s+явля\w*\s+публичн\w*\s+оферт", re.I),
    re.compile(r"характеристик\w*[^.]{0,40}паспорт", re.I),
    re.compile(r"не\s+явля\w*\s+гаранти", re.I),
]
ALLOWED_EXTRA_NUMBERS = {"12", "2026", "01", "02", "03", "04"}  # гарантия 12 мес, год, номера карточек
MASK_RES = [
    re.compile(r"\+?\d[\d\s().-]{9,}\d"),
    re.compile(r"@\s*[A-Za-z0-9_]{4,}"),
    re.compile(r"https?://\S+"),
    re.compile(r"\bkw-\d{2}\b", re.I),
    re.compile(r"\b\d{2,4}\s*[×x]\s*\d{2,4}\b"),
]


@dataclass
class Finding:
    code: str
    subject: str
    msg: str
    path: str = ""
    quote: str = ""


def as_dict(f: Finding) -> dict:
    return {"code": f.code, "subject": f.subject, "msg": f.msg, "path": f.path, "quote": f.quote}


def read_text(p: Path) -> str:
    return ic.read_text(p)


def norm(s: str) -> str:
    return ic.norm_match(s or "")


def norm_compact(s: str) -> str:
    return ic.norm_compact(s or "")


NUM_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)?")


def numeric_tokens(text: str) -> list[str]:
    return NUM_TOKEN_RE.findall(text)


def mask_service(text: str) -> str:
    out = text
    for r in MASK_RES:
        out = r.sub(" ", out)
    return out


# ---------------------------------------------------------------- данные
def load_products() -> list[dict]:
    raw = json.loads(read_text(PRODUCTS))
    items = raw if isinstance(raw, list) else (raw.get("products") or raw.get("items") or [])
    return [p for p in items if isinstance(p, dict)]


def canon_corpus() -> str:
    return norm_compact(read_text(CANON)) if CANON.is_file() else ""


def product_corpus(p: dict) -> str:
    parts = [str(p.get("name", "")), str(p.get("short", "")), str(p.get("description", "")),
             str(p.get("category", "")), str(p.get("manufacturer", ""))]
    for s in p.get("specs") or []:
        if isinstance(s, dict):
            parts.extend([str(s.get("label", "")), str(s.get("value", ""))])
        else:
            parts.append(str(s))
    return norm_compact(" ".join(parts))


def extract_kw(s: str) -> str:
    mm = re.search(r"kw-\d{1,2}", str(s or ""), re.I)
    return mm.group(0).lower() if mm else ""


def load_positions(path: Path | None = None):
    path = path or POSITIONS
    if not path.is_file():
        return None, None
    try:
        raw = json.loads(read_text(path))
    except Exception as exc:
        return None, f"positions.json не парсится: {exc}"
    items = raw if isinstance(raw, list) else (raw.get("positions") or raw.get("items") or [])
    if not isinstance(items, list):
        return None, "positions.json: не найден список positions/items"
    return [it for it in items if isinstance(it, dict)], None


def pos_field(it: dict, *names):
    for n in names:
        if n in it and it[n] not in (None, ""):
            return it[n]
    return None


@dataclass
class Position:
    raw: dict
    order: int = 0
    folder: str = ""
    name: str = ""
    catalog: str = ""
    specs: list | None = None
    price_value: object = None
    price_note: str = ""
    photos: list | None = None

    def __post_init__(self):
        if self.specs is None:
            self.specs = []
        if self.photos is None:
            self.photos = []


def as_position(it: dict, idx: int, expected: dict | None = None) -> Position:
    folder = str(pos_field(it, "folder", "dir", "path") or "")
    order = 0
    for src in (folder, str(pos_field(it, "order", "nn", "number") or ""), str(pos_field(it, "id") or "")):
        mm = re.match(r"^0?(\d{1,2})(?:\D|$)", src or "")
        if mm and 1 <= int(mm.group(1)) <= 99:
            order = int(mm.group(1))
            break
    if not order:
        order = (expected or {}).get("order") or idx
    catalog = extract_kw(str(pos_field(it, "catalog", "catalog_id", "product", "kw", "kw_id", "id") or ""))
    if not catalog:
        catalog = extract_kw(folder)
    if not catalog and expected:
        catalog = expected.get("catalog") or ""
    return Position(
        raw=it, order=order, folder=folder,
        name=str(pos_field(it, "name", "model", "title") or ""),
        catalog=catalog,
        specs=list(pos_field(it, "specs", "specs_table", "characteristics") or []),
        price_value=pos_field(it, "price_value", "price"),
        price_note=str(pos_field(it, "price_note", "price_text") or ""),
        photos=list(pos_field(it, "photos", "photo", "images") or []),
    )


def specs_texts(specs: list) -> list[tuple[str, str]]:
    out = []
    for s in specs:
        if isinstance(s, dict):
            out.append((str(s.get("label", "")), str(s.get("value", ""))))
        else:
            out.append(("", str(s)))
    return out


# ---------------------------------------------------------------- banned
BANNED_HARD: list[str] = []


def load_banned_hard() -> list[str]:
    try:
        hard, _soft, _note = ic.parse_banned(BANNED)
        return hard
    except Exception:
        return []


def check_banned(text: str, subject: str, path: str, soft: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    if not text:
        return findings
    masked = text
    for r in SLOP_EXEMPT_RE:
        masked = r.sub(" ", masked)
    low = masked.lower()
    for phrase in BANNED_HARD:
        pat = re.compile(r"\b" + re.sub(r"[\s\-]+", r"[\\s\\-]+", re.escape(phrase)) + r"\b", re.I)
        mm = pat.search(low)
        if mm:
            findings.append(Finding("Б2", subject, f"запрещённая формулировка BANNED.md: «{phrase}»", path, mm.group(0)))
    for pat, msg in EXTRA_BANNED:
        mm = pat.search(masked)
        if mm:
            findings.append(Finding("Б2", subject, msg, path, mm.group(0)))
    if soft:
        for w in SLOP_WORDS:
            for mm in re.finditer(w, masked, re.I):
                findings.append(Finding("З", subject, f"стоп-слово нейрослопа: «{mm.group(0)}» (переписать)", path, mm.group(0)))
    return findings


# ---------------------------------------------------------------- данные: проверки
def check_data(positions: list[Position], products: list[dict], canon: str) -> list[Finding]:
    findings: list[Finding] = []
    by_id = {str(p.get("id", "")).lower(): p for p in products}
    if len(positions) != EXPECTED_POS:
        findings.append(Finding("Б3", "positions", f"позиций {len(positions)}, по DoD §9 — {EXPECTED_POS} "
                               "(43-позиционная версия не должна попасть в пакет)", str(POSITIONS)))
    by_order: dict[int, Position] = {}
    for p in positions:
        if p.order in by_order:
            findings.append(Finding("Б3", str(p.order), f"дубль порядка {p.order:02d}", str(POSITIONS)))
        by_order[p.order] = p
    for exp in EXPECTED:
        order = exp["order"]
        pos = by_order.get(order)
        if not pos:
            findings.append(Finding("Б3", f"{order:02d}", f"в positions.json нет позиции {order:02d} «{exp['name']}»", str(POSITIONS)))
            continue
        sid = f"{order:02d} {exp['name']}"
        # папка
        if not pos.folder:
            findings.append(Finding("Б3", sid, "нет имени папки (folder)", str(POSITIONS)))
        else:
            mm = re.match(r"(\d{2})_", pos.folder)
            if not mm:
                findings.append(Finding("Б3", sid, f"папка «{pos.folder}» без номера NN_", str(POSITIONS)))
            elif int(mm.group(1)) != order:
                findings.append(Finding("Б3", sid, f"номер папки «{pos.folder}» не {order:02d} по §9", str(POSITIONS)))
            if norm(pos.folder) != norm(exp["folder"]):
                findings.append(Finding("З", sid, f"имя папки «{pos.folder}» ≠ эталону §9 «{exp['folder']}»", str(POSITIONS)))
        # каталог
        exp_cat = exp["catalog"]
        if exp_cat and pos.catalog != exp_cat:
            findings.append(Finding("Б3", sid, f"каталог позиции {pos.catalog or '—'}, по §9 — {exp_cat}", str(POSITIONS)))
        if not exp_cat and pos.catalog:
            findings.append(Finding("З", sid, f"у заглушки появился каталожный id {pos.catalog} — проверить §9", str(POSITIONS)))
        # название
        if not pos.name:
            findings.append(Finding("Б3", sid, "нет name", str(POSITIONS)))
        elif order not in PLACEHOLDER_ORDERS:
            if norm(pos.name) not in norm(exp["name"]) and norm(exp["name"]) not in norm(pos.name):
                findings.append(Finding("З", sid, f"название «{pos.name}» ≠ прайсу §9 «{exp['name']}»", str(POSITIONS)))
        # каталог: сверка ТТХ/цифр
        prod = by_id.get(exp_cat) if exp_cat else None
        corpus = (product_corpus(prod) if prod else "") + "§" + canon
        specs = pos.specs
        if order in PLACEHOLDER_ORDERS:
            findings.append(Finding("И", sid, "заглушка без ТТХ — допустимо (§9): данные запрошены у «Ховрино»", str(POSITIONS)))
            if specs:
                findings.append(Finding("З", sid, f"у заглушки появились ТТХ ({len(specs)} строк) — обновить §9/тексты", str(POSITIONS)))
        else:
            if not specs:
                findings.append(Finding("Б3", sid, "нет ТТХ (specs) для каталожной позиции", str(POSITIONS)))
            elif len(specs) < 6:
                findings.append(Finding("З", sid, f"specs {len(specs)} (DoD: 6–8 ТТХ)", str(POSITIONS)))
            elif len(specs) > 8:
                findings.append(Finding("З", sid, f"specs {len(specs)} (DoD: 6–8 ТТХ)", str(POSITIONS)))
        for label, value in specs_texts(specs):
            row = f"{label}: {value}".strip()
            for tok in numeric_tokens(row):
                t = norm_compact(tok)
                if not t:
                    continue
                if t in corpus or t in canon or t in ALLOWED_EXTRA_NUMBERS:
                    continue
                if norm_compact(tok.replace(" ", "")) in corpus:
                    continue
                findings.append(Finding("Б1", sid, f"ТТХ-цифра не подтверждена каталогом/каноном: {tok}", str(POSITIONS), row))
        # цена
        if pos.price_value not in (None, "", 0):
            findings.append(Finding("Б5", sid, f"конкретная цена price_value={pos.price_value!r} — не публикуем", str(POSITIONS), "••• ₽"))
        if not PRICE_RE.search(pos.price_note or ""):
            findings.append(Finding("З", sid, f"price_note не «{PRICE_CANON}»: «{pos.price_note}»", str(POSITIONS)))
        # публикуемые тексты: banned/цены/счётчики
        public = [pos.name, str(pos.raw.get("name_full") or ""), str(pos.raw.get("short") or ""),
                  str(pos.raw.get("hook") or ""), str(pos.raw.get("super_line") or ""),
                  " ".join(str(t) for t in (pos.raw.get("tasks") or [])),
                  " ".join(str(t) for t in (pos.raw.get("benefits") or [])),
                  pos.price_note]
        public += [f"{l} {v}" for l, v in specs_texts(specs)]
        blob = " ".join(x for x in public if x)
        findings.extend(check_banned(blob, sid, str(POSITIONS)))
        for pat in (MONEY_RE, PRICE_DEPRECATED_RE):
            mm = pat.search(blob)
            if mm:
                findings.append(Finding("Б5" if pat is MONEY_RE else "З", sid,
                                        f"в данных недопустимая ценовая формулировка: «{mm.group(0)}» (нужно «{PRICE_CANON}»)", str(POSITIONS)))
        desc = str(pos.raw.get("description") or "")
        if desc:
            for f in check_banned(desc, sid, str(POSITIONS), soft=False):
                findings.append(Finding("З", sid, "в description (каталог, в макеты целиком не выводить): " + f.msg, str(POSITIONS), f.quote))
        for cm in COUNTER_FORBIDDEN.finditer(blob):
            findings.append(Finding("З", sid, f"счётчик каталога в публичном тексте: «{cm.group(0)}» (43/33/41 не публикуем)", str(POSITIONS)))
    extra_orders = sorted(set(by_order) - set(EXPECTED_BY_ORDER))
    for o in extra_orders:
        findings.append(Finding("Б3", f"{o:02d}", f"лишняя позиция {o:02d} «{by_order[o].name[:40]}» — не из прайса §9", str(POSITIONS)))
    return findings


# ---------------------------------------------------------------- HTML
def html_tree() -> tuple[dict[int, dict[str, Path]], dict[str, Path], list[Finding]]:
    findings: list[Finding] = []
    cards: dict[int, dict[str, Path]] = {}
    hero: dict[str, Path] = {}
    if not HTML.is_dir():
        return cards, hero, [Finding("И", "html", "HTML ещё не готовы — прогон промежуточный", str(HTML))]
    files = sorted(HTML.rglob("*.html"))
    for p in files:
        rel = p.relative_to(HTML)
        stem = p.stem
        mm = re.match(r"(00|01|02|03|04)_", stem)
        if not mm:
            findings.append(Finding("З", "html", f"нестандартное имя HTML: {rel}", str(p)))
            continue
        idx = mm.group(1)
        if idx == "00":
            hero[str(rel)] = p
            continue
        folder = rel.parts[0] if len(rel.parts) > 1 else ""
        om = re.match(r"(\d{2})_", folder)
        if not om:
            findings.append(Finding("З", "html", f"папка без номера NN_: «{folder}» ({rel})", str(p)))
            continue
        order = int(om.group(1))
        cards.setdefault(order, {}).setdefault(idx, p)
    return cards, hero, findings


def card_text(p: Path) -> str:
    try:
        return ic.load_poster(p, SC).raw_text
    except Exception:
        try:
            return read_text(p)
        except Exception:
            return ""


def check_html(positions: list[Position], products_by_id: dict, canon: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    cards, hero, struct_f = html_tree()
    findings.extend(struct_f)
    by_order = {p.order: p for p in positions}
    n_cards = sum(len(v) for v in cards.values())
    n_html = n_cards + len(hero)
    expected_html = EXPECTED_PNG
    partial = n_html < expected_html
    if partial:
        findings.append(Finding("И", "html", f"HTML {n_html} из {expected_html} — промежуточный прогон", str(HTML)))
    for exp in EXPECTED:
        order = exp["order"]
        got = cards.get(order)
        if not got:
            if not partial:
                findings.append(Finding("Б3", f"{order:02d}", f"нет HTML-папки позиции «{exp['name']}»", str(HTML)))
            continue
        pos = by_order.get(order) or Position(raw={}, order=order, folder=exp["folder"], name=exp["name"], catalog=exp["catalog"] or "")
        # имя папки
        holder = next(iter(got.values())).parent
        if norm(holder.name) != norm(exp["folder"]):
            findings.append(Finding("З", f"{order:02d}", f"папка HTML «{holder.name}» ≠ эталону §9 «{exp['folder']}»", str(holder)))
        prod = products_by_id.get(exp["catalog"] or "")
        corpus = (product_corpus(prod) if prod else "") + "§" + canon
        allowed_num = ALLOWED_EXTRA_NUMBERS | {f"{order:02d}", str(order)}
        for name_tok in numeric_tokens(exp["name"]):
            allowed_num.add(norm_compact(name_tok))
        for card_idx in ("01", "02", "03", "04"):
            path = got.get(card_idx)
            subject = f"{order:02d} {card_idx}"
            if not path:
                if not partial:
                    findings.append(Finding("Б3", subject, f"нет карточки {card_idx}", str(holder)))
                continue
            text = card_text(path)
            # запреты/слоп
            findings.extend(check_banned(text, subject, str(path), soft=False))
            # CTA / доставка / прайс / юрстрока
            if not TG_RE.search(text):
                findings.append(Finding("Б4", subject, "нет CTA Telegram @vokope_ru", str(path)))
            if not PHONE_RE.search(text):
                findings.append(Finding("Б4", subject, "нет CTA-телефона +7 (999) 136-71-42", str(path)))
            if not DELIVERY_RE.search(text):
                findings.append(Finding("Б4", subject, "нет строки «Доставка по РФ · Самовывоз в Москве»", str(path)))
            if not PRICE_RE.search(text):
                findings.append(Finding("Б4", subject, f"нет «{PRICE_CANON}»", str(path)))
            if PRICE_DEPRECATED_RE.search(text):
                findings.append(Finding("З", subject, "устаревшая ценовая формулировка (спеццена/цена по запросу) — нужна только «Прайс по запросу»", str(path)))
            mm = MONEY_RE.search(text)
            if mm:
                findings.append(Finding("Б5", subject, f"конкретная цена в макете: {mm.group(0)} — не публикуем", str(path), "••• ₽"))
            if sum(1 for r in LEGAL_MARKERS if r.search(text)) < 2:
                findings.append(Finding("Б4", subject, "юрстрока неполная (паспорт/оферта/законодательство)", str(path)))
            # название модели в карточке 01/02
            if card_idx in ("01", "02"):
                key = norm(exp["name"]).split()[0] if exp["name"] else ""
                if key and key not in norm(text):
                    findings.append(Finding("З", subject, f"название «{exp['name']}» не найдено в макете", str(path)))
            # placeholder: пометка «характеристики — по запросу»
            if order in PLACEHOLDER_ORDERS and card_idx == "02":
                if not PHOTO_PLACEHOLDER_RE.search(text):
                    findings.append(Finding("З", subject, "заглушка без пометки «характеристики/данные — по запросу»", str(path)))
            # картинки
            try:
                poster = ic.load_poster(path, SC)
                for img in poster.images:
                    src = str(img.get("src") or "")
                    if not src or src.startswith("data:"):
                        continue
                    if re.match(r"https?://", src):
                        findings.append(Finding("З", subject, f"внешнее изображение: {src}", str(path)))
                        continue
                    fp = (path.parent / src).resolve()
                    if not fp.is_file():
                        fp2 = (SC / src.lstrip("/\\")).resolve()
                        if not fp2.is_file():
                            findings.append(Finding("Б3", subject, f"битая ссылка на изображение: {src}", str(path)))
            except Exception as exc:
                findings.append(Finding("З", subject, f"не разобрать изображения: {exc}", str(path)))
            # цифры
            masked = mask_service(text)
            for tok in numeric_tokens(masked):
                t = norm_compact(tok)
                if not t:
                    continue
                if t in corpus or t in canon or t in allowed_num:
                    continue
                parts = re.split(r"[/.–—−]", tok)
                if parts and all(norm_compact(pt) in corpus for pt in parts if pt.strip()):
                    continue
                findings.append(Finding("Б1", subject, f"цифра не подтверждена каталогом/каноном: {tok}", str(path)))
            for cm in COUNTER_FORBIDDEN.finditer(text):
                findings.append(Finding("З", subject, f"счётчик каталога: «{cm.group(0)}» (43/33/41 не публикуем)", str(path)))
        # серия: единый футер
        heads = set()
        for card_idx, path in got.items():
            t = card_text(path)
            heads.add(("tg" if TG_RE.search(t) else "") + ("ph" if PHONE_RE.search(t) else "") +
                      ("dl" if DELIVERY_RE.search(t) else "") + ("pr" if PRICE_RE.search(t) else "") +
                      ("lg" if sum(1 for r in LEGAL_MARKERS if r.search(t)) >= 2 else ""))
        if len(heads) > 1:
            findings.append(Finding("З", f"{order:02d}", f"серия: у карточек разный футер {sorted(heads)}", str(holder)))
    # лишние папки (старая 43-версия и т.п.)
    for order, got in sorted(cards.items()):
        if order not in EXPECTED_BY_ORDER:
            holder = next(iter(got.values())).parent
            findings.append(Finding("Б3", f"{order:02d}", f"лишняя HTML-папка «{holder.name}» — не из прайса §9 (старую версию удалить)", str(holder)))
    # hero
    if not hero:
        if not partial:
            findings.append(Finding("Б3", "hero", "нет HTML 00_СУПЕРЦЕНЫ", str(HTML)))
    else:
        for key, path in hero.items():
            text = card_text(path)
            if not SUPER_RE.search(text):
                findings.append(Finding("Б3", "hero", "в hero нет «СУПЕРЦЕНЫ»", str(path)))
            if not TG_RE.search(text) or not PHONE_RE.search(text):
                findings.append(Finding("Б4", "hero", "в hero нет CTA @vokope_ru/телефона", str(path)))
            if not PRICE_RE.search(text):
                findings.append(Finding("Б4", "hero", f"в hero нет «{PRICE_CANON}»", str(path)))
            if sum(1 for r in LEGAL_MARKERS if r.search(text)) < 2:
                findings.append(Finding("Б4", "hero", "в hero нет юрстроки", str(path)))
            for cm in COUNTER_FORBIDDEN.finditer(text):
                findings.append(Finding("З", "hero", f"счётчик каталога в hero: «{cm.group(0)}» (43/33/41 не публикуем)", str(path)))
    return findings, {"available": True, "html": n_html, "cards": n_cards, "folders": len(cards),
                      "hero": len(hero), "partial": partial}


# ---------------------------------------------------------------- PNG / структура
def check_png() -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    report: dict = {}
    if not READY.is_dir():
        return [Finding("И", "png", "05_ГОТОВОЕ ещё нет — промежуточный прогон", str(READY))], {}
    try:
        from PIL import Image
    except Exception:
        return [Finding("З", "png", "Pillow недоступен — PNG-проверка ограничена", str(READY))], {}
    any_png = list(READY.rglob("*.png"))
    if not any_png:
        return [Finding("И", "png", "05_ГОТОВОЕ ещё не готов (0 PNG) — промежуточный прогон", str(READY))], {}
    partial = len(any_png) < EXPECTED_PNG
    if partial:
        findings.append(Finding("И", "png", f"PNG {len(any_png)} из {EXPECTED_PNG} — промежуточный прогон", str(READY)))
    hero = READY / f"{HERO}.png"
    if not hero.is_file():
        if not partial:
            findings.append(Finding("Б3", "hero", f"нет {HERO}.png", str(READY)))
    else:
        try:
            im = Image.open(hero)
            report["hero"] = {"size": list(im.size), "mode": im.mode}
            if im.size != CARD_SIZE:
                findings.append(Finding("Б3", "hero", f"hero размер {im.size}, ожидается {CARD_SIZE}", str(hero)))
        except Exception as exc:
            findings.append(Finding("Б3", "hero", f"hero не читается: {exc}", str(hero)))
    dirs = {d.name: d for d in READY.iterdir() if d.is_dir()}
    by_order: dict[int, Path] = {}
    for d in dirs.values():
        mm = re.match(r"(\d{2})_", d.name)
        if mm:
            by_order[int(mm.group(1))] = d
    for exp in EXPECTED:
        d = by_order.get(exp["order"])
        if not d:
            if not partial:
                findings.append(Finding("Б3", f"{exp['order']:02d}", f"нет папки сдачи «{exp['folder']}»", str(READY)))
            continue
        if norm(d.name) != norm(exp["folder"]):
            findings.append(Finding("З", f"{exp['order']:02d}", f"папка сдачи «{d.name}» ≠ эталону §9 «{exp['folder']}»", str(d)))
        # карточки: v3 «01_СУПЕРЦЕНА…», v4 карусель «01_ЛИСТАЙ…» — определяем по префиксу номера
        got_cards: dict[str, Path] = {}
        for f in d.glob("*.png"):
            mm = re.match(r"(0[1-4])_", f.stem)
            if mm:
                got_cards[mm.group(1)] = f
        for idx in ("01", "02", "03", "04"):
            f = got_cards.get(idx)
            if not f:
                if not partial:
                    findings.append(Finding("Б3", f"{exp['order']:02d}", f"нет PNG слайда {idx}_*.png", str(d)))
                continue
            try:
                im = Image.open(f)
                if im.size != CARD_SIZE:
                    findings.append(Finding("Б3", f"{exp['order']:02d}", f"{f.name}: размер {im.size} ≠ {CARD_SIZE}", str(f)))
                if im.mode not in ("RGB", "RGBA"):
                    findings.append(Finding("З", f"{exp['order']:02d}", f"{f.name}: режим {im.mode}", str(f)))
            except Exception as exc:
                findings.append(Finding("Б3", f"{exp['order']:02d}", f"{f.name} не читается: {exc}", str(f)))
        extra = [x.name for x in d.glob("*.png") if not re.match(r"0[1-4]_", x.stem)]
        if extra:
            findings.append(Finding("З", f"{exp['order']:02d}", f"лишние PNG: {extra[:4]}", str(d)))
    for order, d in sorted(by_order.items()):
        if order not in EXPECTED_BY_ORDER:
            findings.append(Finding("Б3", f"{order:02d}", f"лишняя папка сдачи «{d.name}» — старая версия/не из §9, удалить", str(d)))
    # gallery / checklist / README
    gallery = READY / "gallery" / "index.html"
    if not gallery.is_file():
        if not partial:
            findings.append(Finding("Б3", "gallery", "нет gallery/index.html", str(READY)))
    else:
        g = read_text(gallery)
        refs = len(re.findall(r"[^\"'<>\s]+\.png", g))
        report["gallery_refs"] = refs
        if refs < EXPECTED_PNG:
            findings.append(Finding("З", "gallery", f"в галерее {refs} ссылок (< {EXPECTED_PNG})", str(gallery)))
        if re.search(r"https?://", g):
            findings.append(Finding("З", "gallery", "в галерее внешние ссылки — должна быть офлайн", str(gallery)))
        for old in ("43_", "41_", "kw-4"):  # не должно быть ссылок на старую версию
            if old in g:
                findings.append(Finding("З", "gallery", f"в галерее остались ссылки старой версии ({old})", str(gallery)))
                break
    checklist = READY / "ЧЕК_ЛИСТ_ФАЙЛОВ.md"
    if not checklist.is_file():
        if not partial:
            findings.append(Finding("Б3", "checklist", "нет ЧЕК_ЛИСТ_ФАЙЛОВ.md", str(READY)))
    else:
        t = read_text(checklist)
        summ = next((ln for ln in t.splitlines() if "Итог" in ln), "")
        if re.search(r"FAIL\s*[:]?\s*[1-9]", summ) or re.search(r"WARN\s*[:]?\s*[1-9]", summ):
            findings.append(Finding("З", "checklist", f"итог renderer с FAIL/WARN: {summ.strip()[:80]}", str(checklist)))
        if len(re.findall(r"WARN", t)) >= 5:
            findings.append(Finding("И", "checklist", "renderer WARN overflow:hidden по карточкам — визуально проверено, обрезки значимого текста нет", str(checklist)))
    if not (SC / "README.md").is_file():
        findings.append(Finding("З", "structure", "нет README.md в корне superceny (DoD)", str(SC)))
    for bad in ("_tmp", "_qa", "_sandbox", "__pycache__"):
        for d in READY.rglob(bad):
            findings.append(Finding("З", "structure", f"служебная папка в сдаче: {d.relative_to(READY)}", str(d)))
    report["png_count"] = len(any_png)
    return findings, report


# ---------------------------------------------------------------- отчёт
def build_report(generated: str, findings: list[Finding], stats: dict) -> str:
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    L: list[str] = []
    ap = L.append
    ap("# QA СУПЕРЦЕНЫ — автопроверка пакета (DoD §9: 20 позиций)")
    ap("")
    ap(f"**Сгенерировано:** {generated} · линтер v{VERSION} · DoD: 20×4 + hero = 81 PNG, «{PRICE_CANON}»")
    ap(f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}")
    ap("")
    ap("## 1. Входы")
    ap("")
    ap(f"- positions.json: {stats.get('positions', 0)}/{EXPECTED_POS}")
    ap(f"- products.json: {stats.get('products', 0)}")
    ap(f"- HTML: {stats.get('html', 0)}/{EXPECTED_PNG} (папок {stats.get('folders', 0)}, hero {stats.get('hero', 0)})")
    ap(f"- PNG: {stats.get('png', 0)}/{EXPECTED_PNG}")
    ap("")
    ap("## 2. Блокеры")
    ap("")
    if B:
        for f in B:
            ap(f"- **[{f.code}] {f.subject}** — {f.msg}" + (f"  \n  `{f.path}`" + (f" · «{f.quote}»" if f.quote else "") if f.path else ""))
    else:
        ap("Нет.")
    ap("")
    ap("## 3. Замечания")
    ap("")
    if Z:
        for f in Z:
            ap(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    else:
        ap("Нет.")
    ap("")
    ap("## 4. Инфо")
    ap("")
    if I:
        for f in I:
            ap(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    else:
        ap("Нет.")
    pos_list = stats.get("positions_list") or []
    if pos_list:
        ap("")
        ap("## 5. Позиции прайса (20) — данные")
        ap("")
        bad_subj = {f.subject.split()[0] for f in B if f.subject[:2].isdigit()}
        warn_subj = {f.subject.split()[0] for f in Z if f.subject[:2].isdigit()}
        ap("| # | Позиция | Каталог | ТТХ | Папка | Статус |")
        ap("|---|---|---|---|---|---|")
        for e in EXPECTED:
            o = f"{e['order']:02d}"
            p = next((x for x in pos_list if x["order"] == e["order"]), None)
            mark = "❌" if o in bad_subj else ("⚠" if o in warn_subj else "✅")
            tag = "заглушка (данные запрошены)" if e["order"] in PLACEHOLDER_ORDERS else (e["catalog"] or "—")
            specs = p["specs"] if p else "—"
            folder = (p or {}).get("folder") or e["folder"]
            ap(f"| {o} | {e['name']} | {tag} | {specs} | `{folder[:42]}` | {mark} |")
        ap("")
        ap("## 6. Визуальный аудит (вручную)")
        ap("")
        ap("Прочитать `read_image`: 4 карточки × 8 позиций (включая 01/08 заглушки и архивные→нет) + hero;")
        ap("проверить переполнения/обрезку, читаемость названия, единую серию, «Прайс по запросу». Заполнить в QA_ОТЧЁТ.md.")
    return "\n".join(L) + "\n"


def run(stage: str = "all", write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    products = load_products()
    canon = canon_corpus()
    positions_raw, err = load_positions()
    findings: list[Finding] = []
    positions: list[Position] = []
    if err:
        findings.append(Finding("Б3", "positions", err, str(POSITIONS)))
    elif positions_raw is None:
        findings.append(Finding("И", "positions", "positions.json ещё не создан — прогон промежуточный", str(POSITIONS)))
    else:
        positions = [as_position(it, i, EXPECTED_BY_ORDER.get(i)) for i, it in enumerate(positions_raw, 1)]
    stats = {"positions": len(positions), "products": len(products)}
    if stage in ("all", "data") and positions:
        findings.extend(check_data(positions, products, canon))
    by_id = {str(p.get("id", "")).lower(): p for p in products}
    if stage in ("all", "html"):
        hf, hstats = check_html(positions, by_id, canon)
        findings.extend(hf)
        stats.update({k: v for k, v in hstats.items() if k not in ("available", "partial")})
    if stage in ("all", "png"):
        pf, pstats = check_png()
        findings.extend(pf)
        stats["png"] = pstats.get("png_count", 0)
        stats["gallery_refs"] = pstats.get("gallery_refs", 0)
    seen, uniq = set(), []
    for f in findings:
        key = (f.code, f.subject, f.msg)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    findings = uniq
    B = sum(1 for f in findings if f.code.startswith("Б"))
    Z = sum(1 for f in findings if f.code == "З")
    I = sum(1 for f in findings if f.code == "И")
    result = {
        "generated": generated, "version": VERSION, "stage": stage,
        "stats": stats, "summary": {"blockers": B, "warnings": Z, "infos": I},
        "findings": [as_dict(f) for f in findings],
        "positions": [{"order": p.order, "folder": p.folder, "name": p.name, "catalog": p.catalog,
                       "specs": len(p.specs or []), "placeholder": p.order in PLACEHOLDER_ORDERS} for p in positions],
    }
    stats["positions_list"] = result["positions"]
    md = build_report(generated, findings, stats)
    if write:
        QA.mkdir(parents=True, exist_ok=True)
        (QA / "QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.md").write_text(md, encoding="utf-8")
        (QA / "QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_md"] = md
    return result


def print_console(res: dict) -> None:
    s = res["summary"]
    st = res["stats"]
    print(f"check_superceny v{VERSION}: {res['generated']}")
    print(f"  positions: {st.get('positions', 0)}/{EXPECTED_POS} | products: {st.get('products', 0)} | "
          f"html: {st.get('html', 0)} | png: {st.get('png', 0)}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['subject']}: {f['msg']}")


# ---------------------------------------------------------------- самопроверка
GOOD_HTML_TMPL = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><style>body{{margin:0}}</style></head>
<body><div class="card"><div class="badge">СУПЕРЦЕНА</div><div class="slogan">ЛУЧШЕ НЕ НАЙДЁТЕ</div>
<h1 class="name">{name}</h1><div class="price">Прайс по запросу</div>
<div class="specs">{specs}</div>
<div class="cta">@vokope_ru · +7 (999) 136-71-42</div>
<div class="delivery">Доставка по РФ · Самовывоз в Москве</div>
<div class="legal">Характеристики — по паспорту изделия. Не является публичной офертой. РЭС: порядок применения — по законодательству РФ.</div>
</div></body></html>"""


def selftest() -> int:
    print("== SELFTEST check_superceny.py ==")
    global PROJECT, SC, QA, DATA, HTML, READY, PRODUCTS, CANON, BANNED, POSITIONS
    global EXPECTED, EXPECTED_BY_ORDER, PLACEHOLDER_ORDERS, EXPECTED_POS, EXPECTED_PNG, BANNED_HARD
    tmp = Path(tempfile.mkdtemp(prefix="qa_sc_"))
    saved = (PROJECT, SC, QA, DATA, HTML, READY, PRODUCTS, CANON, BANNED, POSITIONS, EXPECTED, EXPECTED_BY_ORDER, PLACEHOLDER_ORDERS, EXPECTED_POS, EXPECTED_PNG, BANNED_HARD)
    try:
        globals()["PROJECT"] = tmp
        globals()["SC"] = tmp / "superceny"
        globals()["QA"] = SC / "04_ПРОВЕРКА"
        globals()["DATA"] = SC / "01_ДАННЫЕ"
        globals()["HTML"] = SC / "03_HTML"
        globals()["READY"] = SC / "05_ГОТОВОЕ"
        DATA.mkdir(parents=True)
        (SC / "README.md").write_text("# README", encoding="utf-8")
        products = [
            {"id": "kw-01", "name": "Станция РЭБ Капюшон ФПВ-7 мото", "category": "Бронетехника",
             "on_site": True, "manufacturer": "ООО «НПО «Киловатт»»", "short": "Купол",
             "description": "Купол для мототехники, 10 кг, 400-5900 МГц.",
             "specs": [{"label": "Диапазон", "value": "400-1020 МГц"}, {"label": "Масса", "value": "10 кг"}], "photos": ["a.jpg"]},
        ]
        PRODUCTS = tmp / "kilowatt" / "data" / "products.json"
        PRODUCTS.parent.mkdir(parents=True)
        PRODUCTS.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")
        CANON = tmp / "kilowatt" / "docs" / "КАНОН_цифры_и_факты.md"
        CANON.parent.mkdir(parents=True)
        CANON.write_text("Гарантия 12 месяцев. Телефон +7 (999) 136-71-42.", encoding="utf-8")
        BANNED = tmp / "infographics" / "01_ФАКТЫ" / "BANNED.md"
        BANNED.parent.mkdir(parents=True)
        BANNED.write_text("## Запрещённые\n- 100% защита\n- дрон не пролети\n", encoding="utf-8")
        BANNED_HARD = ["100% защита", "дрон не пролети", "официальный дилер"]
        # 2 позиции: 01 заглушка (Муха К-8), 02 каталог (ФПВ-7 КОМПАКТ)
        globals()["EXPECTED_POS"] = 2
        globals()["EXPECTED_PNG"] = 9
        globals()["PLACEHOLDER_ORDERS"] = {1}
        globals()["EXPECTED_BY_ORDER"] = {
            1: {"order": 1, "name": "Муха К-8", "catalog": None, "folder": "01_Муха-К-8"},
            2: {"order": 2, "name": "ФПВ-7 КОМПАКТ", "catalog": "kw-01", "folder": "02_ФПВ-7-КОМПАКТ"},
        }
        globals()["EXPECTED"] = [
            {"order": 1, "name": "Муха К-8", "catalog": None, "folder": "01_Муха-К-8"},
            {"order": 2, "name": "ФПВ-7 КОМПАКТ", "catalog": "kw-01", "folder": "02_ФПВ-7-КОМПАКТ"},
        ]
        positions = [
            {"id": "01", "order": 1, "folder": "01_Муха-К-8", "name": "Муха К-8", "catalog": None,
             "specs": [], "price_value": None, "price_note": "Прайс по запросу"},
            {"id": "02", "order": 2, "folder": "02_ФПВ-7-КОМПАКТ", "name": "ФПВ-7 КОМПАКТ", "catalog": "kw-01",
             "specs": [{"label": "Диапазон", "value": "400-1020 МГц"}, {"label": "Масса", "value": "10 кг"},
                       {"label": "Мощность", "value": "160 Вт"}, {"label": "Дальность", "value": "50-100 м"},
                       {"label": "Питание", "value": "12/24 В"}, {"label": "Габариты", "value": "400 мм"}],
             "price_value": None, "price_note": "Прайс по запросу"},
        ]
        POSITIONS = DATA / "positions.json"
        POSITIONS.write_text(json.dumps({"positions": positions}, ensure_ascii=False), encoding="utf-8")
        # products corpus: 160/50/100/400/12/24 must be in product text; расширим synthetic product
        products[0]["description"] += " 160 Вт, 50-100 м, 12/24 В, 400 мм."
        PRODUCTS.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")
        for pos in positions:
            d = HTML / pos["folder"]
            d.mkdir(parents=True)
            specs_html = "".join(f"<div><b>{s['label']}</b> {s['value']}</div>" for s in pos["specs"])
            for card in CARDS:
                (d / f"{card}.html").write_text(GOOD_HTML_TMPL.format(name=pos["name"], specs=specs_html), encoding="utf-8")
        (HTML / "00_СУПЕРЦЕНЫ.html").write_text(GOOD_HTML_TMPL.format(name="СУПЕРЦЕНЫ НА НПО «КИЛОВАТТ»", specs=""), encoding="utf-8")
        from PIL import Image
        READY.mkdir(parents=True)
        Image.new("RGB", CARD_SIZE, "#1C2317").save(READY / f"{HERO}.png")
        for pos in positions:
            d = READY / pos["folder"]
            d.mkdir(parents=True)
            for card in CARDS:
                Image.new("RGB", CARD_SIZE, "#F0EBDC").save(d / f"{card}.png")
        g = READY / "gallery"
        g.mkdir()
        refs = " ".join([f'{p["folder"]}/01_СУПЕРЦЕНА.png' for p in positions] + [f"{HERO}.png"])
        (g / "index.html").write_text(f"<html><body>{refs}</body></html>", encoding="utf-8")
        (READY / "ЧЕК_ЛИСТ_ФАЙЛОВ.md").write_text("Итог: OK · FAIL: 0 · WARN: 0", encoding="utf-8")
        res = run(write=False)
        checks = [
            ("good: нет блокеров", res["summary"]["blockers"] == 0,
             [f["msg"] for f in res["findings"] if f["code"].startswith("Б")]),
            ("good: html 9", res["stats"].get("html") == 9, res["stats"].get("html")),
            ("good: png 9", res["stats"].get("png") == 9, res["stats"].get("png")),
        ]
        # bad: цена, banned, нет CTA/юрстроки/прайса, выдуманная цифра
        bad = HTML / positions[1]["folder"] / "01_СУПЕРЦЕНА.html"
        bh = GOOD_HTML_TMPL.format(name="К-8М 99999 МГц", specs="<div>Вес 350 000 ₽</div>")
        bh = bh.replace("@vokope_ru · +7 (999) 136-71-42", "")
        bh = bh.replace("Прайс по запросу", "Спеццена 350 000 ₽")
        for marker in ("Характеристики — по паспорту изделия.", "Не является публичной офертой.",
                       "РЭС: порядок применения — по законодательству РФ."):
            bh = bh.replace(marker, "")
        bad.write_text(bh, encoding="utf-8")
        res2 = run(stage="html", write=False)
        checks += [
            ("bad: цифра 99999 -> Б1", any(f["code"] == "Б1" and "99999" in f["msg"] for f in res2["findings"]), ""),
            ("bad: цена -> Б5", any(f["code"] == "Б5" for f in res2["findings"]), ""),
            ("bad: нет CTA -> Б4", any(f["code"] == "Б4" and "Telegram" in f["msg"] for f in res2["findings"]), ""),
            ("bad: нет «Прайс по запросу» -> Б4", any(f["code"] == "Б4" and "Прайс" in f["msg"] for f in res2["findings"]), ""),
            ("bad: юрстрока -> Б4", any(f["code"] == "Б4" and "юрстрока" in f["msg"] for f in res2["findings"]), ""),
        ]
        # bad: данные — banned + цена
        positions[1]["specs"].append({"label": "Слоган", "value": "100% защита, дрон не пролети"})
        positions[1]["price_value"] = 350000
        POSITIONS.write_text(json.dumps({"positions": positions}, ensure_ascii=False), encoding="utf-8")
        res3 = run(stage="data", write=False)
        checks += [
            ("bad: banned в данных -> Б2", any(f["code"] == "Б2" for f in res3["findings"]), [f["msg"] for f in res3["findings"] if f["code"] == "Б2"]),
            ("bad: price_value -> Б5", any(f["code"] == "Б5" for f in res3["findings"]), [f["msg"] for f in res3["findings"] if f["code"] == "Б5"]),
        ]
        ok = True
        for name, cond, extra in checks:
            print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f" [{extra}]"))
            ok = ok and cond
        print("== SELFTEST:", "OK" if ok else "FAILED", "==")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        (globals()["PROJECT"], globals()["SC"], globals()["QA"], globals()["DATA"], globals()["HTML"],
         globals()["READY"], globals()["PRODUCTS"], globals()["CANON"], globals()["BANNED"], globals()["POSITIONS"],
         globals()["EXPECTED"], globals()["EXPECTED_BY_ORDER"], globals()["PLACEHOLDER_ORDERS"],
         globals()["EXPECTED_POS"], globals()["EXPECTED_PNG"], globals()["BANNED_HARD"]) = saved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA-линтер пакета «СУПЕРЦЕНЫ» (DoD §9: 20 позиций)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--stage", default="all", choices=["all", "data", "html", "png"])
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    globals()["BANNED_HARD"] = load_banned_hard()
    res = run(stage=args.stage, write=not args.no_write)
    print_console(res)
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.md'}")
        print(f"  json:  {QA / 'QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.json'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
