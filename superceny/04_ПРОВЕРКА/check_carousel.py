#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_carousel.py — QA-линтер карусели «СУПЕРЦЕНЫ» (v4, бриф §10).

Карусель: на каждую из 20 позиций 4 слайда = единый сюжет
  01 КРЮЧОК → 02 ЦИФРЫ («Что внутри») → 03 СЦЕНАРИИ («А кому?») → 04 ФИНАЛ/CTA.
Каждый слайд 01–03 обрывается крючком/стрелкой «листай», 04 — цена/CTA.

Проверяет:
  1) ДАННЫЕ: поля s1…s4 в positions.json (или carousel_texts.json): наличие/длины,
     stats/points/bullets = 4, цифры из каталога/канона, «Прайс по запросу», banned,
     сцепку (крючки), отсутствие дословных дублей между слайдами, согласованность s1/s2.
  2) HTML: 81 файл (20×4 + hero): маркеры slide--01…04, номера «0X/04», прогресс,
     стрелки «листай» на 01–03, CTA/юрстрока, цена, отсутствие дублей, цифры.
  3) PNG/структура: 81 PNG 1080×1350 (имена 01_…04_ по префиксу), hero, gallery, ЧЕК_ЛИСТ.
  4) Контакт-листы серий: 04_ПРОВЕРКА\\карусели\\<позиция>.png|jpg (20).
  5) Читаемость: наличие копий 540/390 (`_render/_qa/readability/...`).

Результат: superceny\\04_ПРОВЕРКА\\QA_КАРУСЕЛЬ_АВТОПРОВЕРКА.md / .json
Запуск: python check_carousel.py [--selftest] [--no-write] [--stage all|data|html|png]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
QA = Path(__file__).resolve().parent
SC = QA.parent
DATA = SC / "01_ДАННЫЕ"
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
POSITIONS = DATA / "positions.json"
CAROUSEL_JSON = DATA / "carousel_texts.json"
STRIPS = QA / "карусели"
READABILITY = SC / "_render" / "_qa" / "readability"

_spec = importlib.util.spec_from_file_location("cs_carousel", QA / "check_superceny.py")
if _spec is None or _spec.loader is None:
    raise SystemExit("не найден check_superceny.py рядом")
cs = importlib.util.module_from_spec(_spec)
sys.modules["cs_carousel"] = cs
_spec.loader.exec_module(cs)

EXPECTED_POS = cs.EXPECTED_POS
PLACEHOLDER_ORDERS = cs.PLACEHOLDER_ORDERS
SLIDES = ["01", "02", "03", "04"]

# поля карусели: (ключ, макс. длина, обязательное)
TEXT_FIELDS = [
    ("s1_kicker", 18, True), ("s1_title", 40, True), ("s1_claim", 28, True),
    ("s1_sub", 80, True), ("s1_swipe", 30, True),
    ("s2_lead", 24, True), ("s2_tail", 34, True),
    ("s3_title", 18, True), ("s3_tail", 32, True),
    ("s4_title", 24, True), ("s4_offer", 20, True), ("s4_price", 20, True), ("s4_cta", 40, True),
]
LIST_FIELDS = [("s2_stats", 4, 4), ("s3_points", 4, 4), ("s4_bullets", 4, 4)]
SWIPE_RE = re.compile(r"лист|свайп|→|›|➜|👉|дальше", re.I)
CTA_RE = re.compile(r"напиш|звон|telegram|телеграм|@vokope|прайс|цен", re.I)
PRICE_CANON = "Прайс по запросу"
PRICE_RE = re.compile(r"прайс\s+по\s+запросу", re.I)
MONEY_RE = re.compile(r"\d[\d\s.,]*\s*(?:₽|руб\b\.?)", re.I)
DUP_MIN_LEN = 18
# общие строки, которые повторяются на всех слайдах намеренно — не считать дублем
SHARED_LINE_RES = [re.compile(r"прайс\s+по\s+запросу", re.I), re.compile(r"@vokope_ru", re.I),
                   re.compile(r"\+7\s*\(?999\)?[\s-]*136[-\s]?71[-\s]?42"), re.compile(r"доставк", re.I),
                   re.compile(r"самовывоз", re.I), re.compile(r"публичн\w*\s+оферт", re.I),
                   re.compile(r"паспорт", re.I), re.compile(r"законодательств", re.I),
                   re.compile(r"лос\s+«?в\s+окопе", re.I)]


def norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\u00a0", " ")).strip().lower()


def is_shared(s: str) -> bool:
    return any(r.search(s) for r in SHARED_LINE_RES)


def split_lines(text: str) -> list[str]:
    parts = re.split(r"[\n•·|]+|(?<=[.!?])\s+", text or "")
    out = []
    for p in parts:
        n = norm_line(p)
        if len(n) >= DUP_MIN_LEN and not is_shared(n):
            out.append(n)
    return out


def load_data():
    pos, err = cs.load_positions()
    if err:
        return None, None, err
    if pos is None:
        return None, None, "positions.json ещё не создан"
    merged = pos
    if CAROUSEL_JSON.is_file():
        try:
            raw = json.loads(cs.read_text(CAROUSEL_JSON))
            # поддержка двух форматов: список объектов или «колоночный» dict {поле: [...]}.
            # Колоночный: скалярные поля по 20, списочные (s2_stats/s3_points/s4_bullets) — по 80 (20×4).
            if isinstance(raw, dict) and raw and all(isinstance(v, list) for v in raw.values()):
                n = len(raw.get("folder") or next(iter(raw.values()), []))
                items = []
                for i in range(n):
                    item = {}
                    for k, v in raw.items():
                        if not isinstance(v, list):
                            item[k] = v
                        elif len(v) == n:
                            item[k] = v[i]
                        elif len(v) == n * 4 and k in ("s2_stats", "s3_points", "s4_bullets", "s4_adv"):
                            item[k] = v[i * 4:(i + 1) * 4]
                        elif v and i < len(v):
                            item[k] = v[i]
                    items.append(item)
            elif isinstance(raw, list):
                items = raw
            else:
                items = raw.get("positions") or raw.get("items") or []
            by = {}
            for it in items:
                if not isinstance(it, dict):
                    continue
                folder = str(it.get("folder") or "")
                fid = str(it.get("id") or it.get("catalog_id") or "")
                key = folder[:2] if folder[:2].isdigit() else fid
                by[key] = it
            for it in merged:
                folder = str(it.get("folder") or "")
                key = folder[:2] if folder[:2].isdigit() else str(it.get("id") or "")
                if key in by:
                    for k, v in by[key].items():
                        it.setdefault(k, v)
        except Exception:
            pass
    return merged, None, None


def check_data(positions_raw: list[dict], products: list[dict], canon: str) -> tuple[list, dict]:
    findings: list = []
    by_id = {str(p.get("id", "")).lower(): p for p in products}
    orig_by_order = {p.order: p for p in [cs.as_position(it, i, cs.EXPECTED_BY_ORDER.get(i)) for i, it in enumerate(positions_raw, 1)]}
    stats = {"positions": 0, "placeholder": 0}
    for it in positions_raw:
        order = 0
        folder = str(it.get("folder") or "")
        mm = re.match(r"(\d{2})_", folder)
        if mm:
            order = int(mm.group(1))
        if not (1 <= order <= EXPECTED_POS):
            continue
        stats["positions"] += 1
        exp = cs.EXPECTED_BY_ORDER[order]
        sid = f"{order:02d} {exp['name']}"
        placeholder = order in PLACEHOLDER_ORDERS
        if placeholder:
            stats["placeholder"] += 1
        # обязательные текстовые поля
        missing = []
        for key, limit, required in TEXT_FIELDS:
            val = it.get(key)
            if required and (val is None or str(val).strip() == ""):
                missing.append(key)
                continue
            if val is None:
                continue
            s = str(val).strip()
            if len(s) > limit:
                findings.append(cs.Finding("З", sid, f"{key} длиннее {limit} знаков ({len(s)}): «{s[:60]}»", str(POSITIONS)))
        if missing:
            findings.append(cs.Finding("Б3", sid, f"нет полей карусели: {', '.join(missing)}", str(POSITIONS)))
        # списочные поля
        for key, minimum, maximum in LIST_FIELDS:
            v = it.get(key)
            if not isinstance(v, list):
                findings.append(cs.Finding("Б3", sid, f"{key} должен быть списком из {maximum}", str(POSITIONS)))
                continue
            if not (minimum <= len(v) <= maximum):
                findings.append(cs.Finding("З", sid, f"{key}: {len(v)} (нужно ровно {maximum})", str(POSITIONS)))
            if key == "s2_stats":
                for j, st in enumerate(v):
                    if not isinstance(st, dict):
                        findings.append(cs.Finding("Б3", sid, f"s2_stats[{j}] не объект value/label/note", str(POSITIONS)))
                        continue
                    for f in ("value", "label"):
                        if not str(st.get(f, "")).strip():
                            findings.append(cs.Finding("Б3", sid, f"s2_stats[{j}] без {f}", str(POSITIONS)))
        # цена / banned / выдуманные цифры
        all_texts = []
        for key, limit, required in TEXT_FIELDS:
            if it.get(key):
                all_texts.append(str(it[key]))
        for key, _mn, _mx in LIST_FIELDS:
            v = it.get(key) or []
            for item in v:
                if isinstance(item, dict):
                    all_texts.extend(str(item.get(x, "")) for x in ("value", "label", "note"))
                else:
                    all_texts.append(str(item))
        blob = " ".join(all_texts)
        if not PRICE_RE.search(str(it.get("s4_price", ""))):
            findings.append(cs.Finding("Б4", sid, f"s4_price ≠ «{PRICE_CANON}»: «{it.get('s4_price')}»", str(POSITIONS)))
        mmoney = MONEY_RE.search(blob)
        if mmoney:
            findings.append(cs.Finding("Б5", sid, f"конкретная цена в текстах карусели: {mmoney.group(0)}", str(POSITIONS), "••• ₽"))
        findings.extend(cs.check_banned(blob, sid, str(POSITIONS), soft=False))
        # цифры stats/claim: только каталог/канон
        prod = by_id.get(str(it.get("catalog_id") or exp["catalog"] or ""))
        corpus = (cs.product_corpus(prod) if prod else "") + "§" + canon
        allowed = cs.ALLOWED_EXTRA_NUMBERS | {"01", "02", "03", "04", f"{order:02d}"}
        for nm in (exp["name"], str(it.get("name") or "")):
            for tok in cs.numeric_tokens(nm):
                allowed.add(cs.norm_compact(tok))
        for tok in cs.numeric_tokens(cs.mask_service(blob)):
            t = cs.norm_compact(tok)
            if not t:
                continue
            if t in corpus or t in allowed:
                continue
            parts = re.split(r"[/.–—−]", tok)
            if parts and all(cs.norm_compact(p) in corpus for p in parts if p.strip()):
                continue
            if placeholder:
                findings.append(cs.Finding("И", sid, f"заглушка: цифра «{tok}» вне каталога (допустимо, данные запрошены)", str(POSITIONS)))
            else:
                findings.append(cs.Finding("Б1", sid, f"цифра карусели не подтверждена каталогом/каноном: {tok}", str(POSITIONS)))
        # сцепка/крючки
        s1_swipe = str(it.get("s1_swipe", ""))
        s2_lead = str(it.get("s2_lead", ""))
        s2_tail = str(it.get("s2_tail", ""))
        s3_tail = str(it.get("s3_tail", ""))
        s4_cta = str(it.get("s4_cta", ""))
        s4_title = str(it.get("s4_title", ""))
        if not SWIPE_RE.search(s1_swipe):
            findings.append(cs.Finding("З", sid, f"s1_swipe без призыва листнуть: «{s1_swipe}»", str(POSITIONS)))
        if "внутри" not in cs.norm(s2_lead):
            findings.append(cs.Finding("З", sid, f"s2_lead не продолжает 01 («внутри»): «{s2_lead}»", str(POSITIONS)))
        if "кому" not in cs.norm(s2_tail) and "?" not in s2_tail:
            findings.append(cs.Finding("З", sid, f"s2_tail не ведёт к 03 («кому?»): «{s2_tail}»", str(POSITIONS)))
        if not re.search(r"цен|главн", cs.norm(s3_tail)):
            findings.append(cs.Finding("З", sid, f"s3_tail не ведёт к 04 («цена»): «{s3_tail}»", str(POSITIONS)))
        if not CTA_RE.search(s4_cta):
            findings.append(cs.Finding("З", sid, f"s4_cta без призыва/цены: «{s4_cta}»", str(POSITIONS)))
        model_head = re.sub(r"[^a-zа-яё0-9\-]+", "", cs.norm(exp["name"]).split()[0]) if exp["name"] else ""
        if model_head and model_head not in re.sub(r"[^a-zа-яё0-9\-]+", "", cs.norm(s4_title)):
            findings.append(cs.Finding("З", sid, f"s4_title не отсылает к модели «{exp['name']}»: «{s4_title}»", str(POSITIONS)))
        # дословные дубли текстов между слайдами (без общих футерных строк)
        seen = {}
        for key, limit, required in TEXT_FIELDS:
            v = norm_line(str(it.get(key, "")))
            if len(v) >= DUP_MIN_LEN:
                if v in seen:
                    findings.append(cs.Finding("З", sid, f"дословный дубль: {seen[v]} = {key} («{v[:40]}»)", str(POSITIONS)))
                else:
                    seen[v] = key
        # согласованность s1 ↔ s2
        s2blob = " ".join(str(v) for st in (it.get("s2_stats") or []) if isinstance(st, dict) for v in st.values())
        for tok in cs.numeric_tokens(str(it.get("s1_claim", ""))):
            t = cs.norm_compact(tok)
            if t and t not in cs.norm_compact(s2blob) and t not in corpus:
                findings.append(cs.Finding("З", sid, f"цифра s1_claim «{tok}» не повторяется в s2 и не в каталоге", str(POSITIONS)))
    return findings, stats


def check_html(positions_raw: list[dict], products: list[dict], canon: str) -> tuple[list, dict]:
    findings: list = []
    by_id = {str(p.get("id", "")).lower(): p for p in products}
    cards, hero, struct_f = cs.html_tree()
    findings.extend(struct_f)
    n_html = sum(len(v) for v in cards.values()) + len(hero)
    partial = n_html < EXPECTED_POS * 4 + 1
    if partial:
        findings.append(cs.Finding("И", "html", f"HTML {n_html} из {EXPECTED_POS * 4 + 1} — промежуточный прогон", str(HTML)))
    for it in positions_raw:
        folder = str(it.get("folder") or "")
        mm = re.match(r"(\d{2})_", folder)
        if not mm:
            continue
        order = int(mm.group(1))
        exp = cs.EXPECTED_BY_ORDER.get(order)
        if not exp:
            continue
        sid = f"{order:02d} {exp['name']}"
        got = cards.get(order)
        if not got:
            if not partial:
                findings.append(cs.Finding("Б3", sid, "нет HTML-папки", str(HTML)))
            continue
        holder = next(iter(got.values())).parent
        prod = by_id.get(str(it.get("catalog_id") or exp["catalog"] or ""))
        corpus = (cs.product_corpus(prod) if prod else "") + "§" + canon
        allowed = cs.ALLOWED_EXTRA_NUMBERS | {"01", "02", "03", "04", f"{order:02d}"}
        for nm in (exp["name"], str(it.get("name") or "")):
            for tok in cs.numeric_tokens(nm):
                allowed.add(cs.norm_compact(tok))
        body_lines: dict[str, int] = {}
        slide_texts = {}
        for idx in SLIDES:
            path = got.get(idx)
            if not path:
                if not partial:
                    findings.append(cs.Finding("Б3", sid, f"нет слайда {idx}_*.html", str(holder)))
                continue
            subject = f"{order:02d} {idx}"
            src = ""
            try:
                src = cs.read_text(path)
            except Exception:
                pass
            text = cs.card_text(path)
            slide_texts[idx] = text
            # разные композиции: класс slide--01…04
            cls_mark = re.search(rf"slide--{idx}\b", src) or re.search(rf"slide--{idx}\b", text)
            if not cls_mark:
                findings.append(cs.Finding("З", subject, f"нет класса slide--{idx} (одинаковые раскладки?)", str(path)))
            # номер слайда + прогресс
            if not re.search(rf"{idx}\s*/\s*04", text):
                findings.append(cs.Finding("З", subject, f"нет маркера «{idx}/04»", str(path)))
            if not re.search(r"progress|dots|dot\b|bar\b|шкал", src, re.I) and not re.search(r"[●○◦•]{2,}", text):
                findings.append(cs.Finding("И", subject, "не найден прогресс-элемент (проверить визуально)", str(path)))
            # цена: обязательна на финальном слайде; на 01–03 — если упомянута, то только канонично
            if idx == "04" and not PRICE_RE.search(text):
                findings.append(cs.Finding("Б4", subject, f"нет «{PRICE_CANON}» в финальном слайде", str(path)))
            if idx != "04" and re.search(r"(?:цена|стоимость)\s+по\s+запросу|спеццен", cs.norm(text)) and not PRICE_RE.search(text):
                findings.append(cs.Finding("З", subject, "неканоничная ценовая формулировка на слайде сюжета", str(path)))
            if idx != "04":
                if not SWIPE_RE.search(text):
                    findings.append(cs.Finding("З", subject, "нет призыва/стрелки листнуть дальше", str(path)))
            else:
                if not cs.TG_RE.search(text) or not cs.PHONE_RE.search(text):
                    findings.append(cs.Finding("Б4", subject, "в финальном слайде нет CTA @vokope_ru/телефона", str(path)))
                if not CTA_RE.search(text):
                    findings.append(cs.Finding("З", subject, "в финальном слайде нет призыва «напиши/звони»", str(path)))
            if cs.MONEY_RE.search(text):
                mm2 = cs.MONEY_RE.search(text)
                findings.append(cs.Finding("Б5", subject, f"конкретная цена в слайде: {mm2.group(0)}", str(path), "••• ₽"))
            if sum(1 for r in cs.LEGAL_MARKERS if r.search(text)) < 2:
                findings.append(cs.Finding("Б4", subject, "юрстрока неполная", str(path)))
            # banned + цифры
            findings.extend(cs.check_banned(text, subject, str(path), soft=False))
            for tok in cs.numeric_tokens(cs.mask_service(text)):
                t = cs.norm_compact(tok)
                if not t or t in corpus or t in allowed:
                    continue
                parts = re.split(r"[/.–—−]", tok)
                if parts and all(cs.norm_compact(p) in corpus for p in parts if p.strip()):
                    continue
                findings.append(cs.Finding("Б1", subject, f"цифра не подтверждена каталогом/каноном: {tok}", str(path)))
            # дубли текста между слайдами
            for line in split_lines(text):
                if line in body_lines and body_lines[line] != idx:
                    findings.append(cs.Finding("З", subject, f"дословный дубль строки со слайдом {body_lines[line]}: «{line[:45]}»", str(path)))
                elif line not in body_lines:
                    body_lines[line] = idx
    # hero
    for key, path in hero.items():
        text = cs.card_text(path)
        if not cs.SUPER_RE.search(text):
            findings.append(cs.Finding("Б3", "hero", "в hero нет «СУПЕРЦЕНЫ»", str(path)))
        if not cs.TG_RE.search(text) or not cs.PHONE_RE.search(text):
            findings.append(cs.Finding("Б4", "hero", "в hero нет CTA", str(path)))
        if not PRICE_RE.search(text):
            findings.append(cs.Finding("Б4", "hero", f"в hero нет «{PRICE_CANON}»", str(path)))
    return findings, {"html": n_html, "folders": len(cards), "hero": len(hero)}


def check_assets(positions_raw: list[dict]) -> tuple[list, dict]:
    findings: list = []
    stats: dict = {}
    # PNG/структура через общий линтер (index-based)
    pf, pstats = cs.check_png()
    findings.extend(pf)
    stats["png"] = pstats.get("png_count", 0)
    stats["gallery_refs"] = pstats.get("gallery_refs", 0)
    # контакт-листы 4-в-ряд
    strips = sorted(STRIPS.glob("*.png")) + sorted(STRIPS.glob("*.jpg")) if STRIPS.is_dir() else []
    stats["strips"] = len(strips)
    if len(strips) < EXPECTED_POS:
        findings.append(cs.Finding("Б3", "strips", f"контакт-листов серий {len(strips)}/20 в {STRIPS}", str(STRIPS)))
    try:
        from PIL import Image
        for f in strips:
            im = Image.open(f)
            if im.width < 2000:
                findings.append(cs.Finding("З", "strips", f"контакт-лист {f.name} узкий: {im.size} (ожидается 4 слайда подряд)", str(f)))
    except Exception:
        pass
    # читаемость 540/390
    for w in ("390", "540"):
        d = READABILITY / w
        n = len(list(d.rglob("*.png"))) if d.is_dir() else 0
        stats[f"readability_{w}"] = n
        if d.is_dir() and n < EXPECTED_POS * 4 + 1:
            findings.append(cs.Finding("З", "readability", f"копий {w}px: {n} (<81)", str(d)))
    return findings, stats


def build_report(generated: str, findings: list, stats: dict) -> str:
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    L = ["# QA КАРУСЕЛЬ — автопроверка пакета «СУПЕРЦЕНЫ» v4", "",
         f"**Сгенерировано:** {generated} · линтер v{VERSION} · 20 позиций × 4 слайда + hero (81 PNG)", "",
         f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}", ""]
    L += ["## 1. Входы", "",
          f"- positions.json: {stats.get('positions', 0)}/{EXPECTED_POS} (заглушек {stats.get('placeholder', 0)})",
          f"- HTML: {stats.get('html', 0)}/81 (папок {stats.get('folders', 0)}, hero {stats.get('hero', 0)})",
          f"- PNG: {stats.get('png', 0)}/81 · gallery refs: {stats.get('gallery_refs', 0)}",
          f"- контакт-листы серий: {stats.get('strips', 0)}/20 · копии 390: {stats.get('readability_390', 0)}, 540: {stats.get('readability_540', 0)}", ""]
    L += ["## 2. Блокеры", ""]
    if B:
        for f in B:
            L.append(f"- **[{f.code}] {f.subject}** — {f.msg}" + (f"  \n  `{f.path}`" if f.path else ""))
    else:
        L.append("Нет.")
    L += ["", "## 3. Замечания", ""]
    if Z:
        for f in Z:
            L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    else:
        L.append("Нет.")
    L += ["", "## 4. Инфо", ""]
    if I:
        for f in I:
            L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    else:
        L.append("Нет.")
    L += ["", "## 5. Визуальный аудит (вручную)", "",
          "Прочитать контакт-листы `04_ПРОВЕРКА\\карусели\\<позиция>.png` (4 слайда подряд) + отдельные слайды и 390-копии:",
          "сцепка (01 → 02 → 03 → 04), стрелки/номера/прогресс, отсутствие 4 одинаковых картинок. Заполнить в QA_ОТЧЁТ_КАРУСЕЛЬ.md."]
    return "\n".join(L) + "\n"


def run(stage: str = "all", write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    products = cs.load_products()
    canon = cs.canon_corpus()
    raw, _, err = load_data()
    findings: list = []
    stats: dict = {}
    if err:
        findings.append(cs.Finding("И", "positions", err + " — промежуточный прогон", str(POSITIONS)))
        raw = []
    global BANNED_HARD
    BANNED_HARD = cs.load_banned_hard()
    cs.BANNED_HARD = BANNED_HARD
    if raw and stage in ("all", "data"):
        df, dstats = check_data(raw, products, canon)
        findings.extend(df)
        stats.update(dstats)
    if raw and stage in ("all", "html"):
        hf, hstats = check_html(raw, products, canon)
        findings.extend(hf)
        stats.update(hstats)
    if stage in ("all", "png"):
        af, astats = check_assets(raw)
        findings.extend(af)
        stats.update(astats)
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
    result = {"generated": generated, "version": VERSION, "stage": stage, "stats": stats,
              "summary": {"blockers": B, "warnings": Z, "infos": I},
              "findings": [cs.as_dict(f) for f in findings]}
    md = build_report(generated, findings, stats)
    if write:
        QA.mkdir(parents=True, exist_ok=True)
        (QA / "QA_КАРУСЕЛЬ_АВТОПРОВЕРКА.md").write_text(md, encoding="utf-8")
        (QA / "QA_КАРУСЕЛЬ_АВТОПРОВЕРКА.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_md"] = md
    return result


def print_console(res: dict) -> None:
    s, st = res["summary"], res["stats"]
    print(f"check_carousel v{VERSION}: {res['generated']}")
    print(f"  positions: {st.get('positions', 0)}/{EXPECTED_POS} | html: {st.get('html', 0)} | png: {st.get('png', 0)} | "
          f"strips: {st.get('strips', 0)}/20")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['subject']}: {f['msg']}")


BANNED_HARD: list = []

# ---------------------------------------------------------------- самопроверка
GOOD = {
    "s1_kicker": "БРОНЕТЕХНИКА", "s1_title": "К-8М", "s1_claim": "8 каналов. 400–5900 МГц.",
    "s1_sub": "Рабочая станция для техники: купол 600 мм, магниты, борт 12/24 В.",
    "s1_swipe": "Листай — покажем, что внутри →",
    "s2_lead": "Что внутри", "s2_tail": "И это ещё не всё. Кому?",
    "s2_stats": [{"value": "8", "label": "каналов", "note": "помех"},
                 {"value": "160 Вт", "label": "мощность", "note": "передатчиков"},
                 {"value": "50–200 м", "label": "дальность", "note": "подавления"},
                 {"value": "20 кг", "label": "масса", "note": "станции"}],
    "s3_title": "Кому это надо", "s3_tail": "Осталось главное — цена",
    "s3_points": ["Транспорт и техника", "ББМ и спецтехника", "Мобильные группы", "Патрулирование"],
    "s4_title": "Тот самый К-8М", "s4_offer": "СУПЕРЦЕНА", "s4_price": "Прайс по запросу",
    "s4_bullets": ["Оригинал производителя", "Гарантия 12 месяцев", "Доставка по РФ", "Самовывоз в Москве"],
    "s4_cta": "Напиши в Telegram — пришлём цену",
}


def selftest() -> int:
    print("== SELFTEST check_carousel.py ==")
    global DATA, HTML, READY, POSITIONS, CAROUSEL_JSON, STRIPS, READABILITY
    global EXPECTED_POS, PLACEHOLDER_ORDERS
    tmp = Path(tempfile.mkdtemp(prefix="qa_krl_"))
    saved = (DATA, HTML, READY, POSITIONS, CAROUSEL_JSON, STRIPS, READABILITY, cs.POSITIONS, cs.HTML, cs.READY, cs.PROJECT)
    try:
        globals()["DATA"] = tmp / "superceny" / "01_ДАННЫЕ"
        globals()["HTML"] = tmp / "superceny" / "03_HTML"
        globals()["READY"] = tmp / "superceny" / "05_ГОТОВОЕ"
        globals()["POSITIONS"] = DATA / "positions.json"
        globals()["CAROUSEL_JSON"] = DATA / "carousel_texts.json"
        globals()["STRIPS"] = tmp / "superceny" / "04_ПРОВЕРКА" / "карусели"
        globals()["READABILITY"] = tmp / "superceny" / "_render" / "_qa" / "readability"
        data = tmp / "superceny" / "01_ДАННЫЕ"
        html = tmp / "superceny" / "03_HTML"
        ready = tmp / "superceny" / "05_ГОТОВОЕ"
        strips = tmp / "superceny" / "04_ПРОВЕРКА" / "карусели"
        cs.POSITIONS = POSITIONS
        cs.HTML = HTML
        cs.READY = READY
        cs.PROJECT = tmp
        for d in (data, html, ready, strips, READABILITY / "390", READABILITY / "540"):
            d.mkdir(parents=True, exist_ok=True)
        (tmp / "superceny" / "README.md").write_text("readme", encoding="utf-8")
        # products / canon / banned через общий пакет
        products = [{"id": "kw-05", "name": "Станция РЭБ Капюшон К-8М", "category": "Бронетехника", "on_site": True,
                     "manufacturer": "ООО «НПО «Киловатт»»", "short": "", "description": "8 каналов, 160 Вт, 50-200 м, 20 кг, 12/24 В, 400-5900 МГц, купол 600 мм.",
                     "specs": [{"label": "Каналов", "value": "8"}], "photos": ["a.jpg"]}]
        prods = tmp / "kilowatt" / "data" / "products.json"
        prods.parent.mkdir(parents=True)
        prods.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")
        cs.PRODUCTS = prods
        canon = tmp / "kilowatt" / "docs" / "КАНОН_цифры_и_факты.md"
        canon.parent.mkdir(parents=True)
        canon.write_text("Гарантия 12 месяцев. Питание 12/24 В.", encoding="utf-8")
        cs.CANON = canon
        banned = tmp / "infographics" / "01_ФАКТЫ" / "BANNED.md"
        banned.parent.mkdir(parents=True)
        banned.write_text("- 100% защита\n- дрон не пролети\n", encoding="utf-8")
        cs.BANNED = banned
        cs.BANNED_HARD = ["100% защита", "дрон не пролети", "официальный дилер"]
        pos = [{"id": "kw-05", "folder": "01_К-8М", "name": "К-8М", "catalog_id": "kw-05",
                "specs": [{"label": "Каналов", "value": "8"}], "price_value": None, "price_note": "Прайс по запросу"}]
        pos[0].update(GOOD)
        globals()["POSITIONS"].write_text(json.dumps({"positions": pos}, ensure_ascii=False), encoding="utf-8")
        # ограничим ожидания до одной позиции
        cs.EXPECTED_POS = 1
        cs.EXPECTED_BY_ORDER = {1: {"order": 1, "name": "К-8М", "catalog": "kw-05", "folder": "01_К-8М"}}
        cs.EXPECTED = [{"order": 1, "name": "К-8М", "catalog": "kw-05", "folder": "01_К-8М"}]
        cs.EXPECTED_PNG = 5
        globals()["EXPECTED_POS"] = 1
        globals()["PLACEHOLDER_ORDERS"] = set()
        from PIL import Image
        Image.new("RGB", (1080, 1350), "#fff").save(ready / "00_СУПЕРЦЕНЫ.png")
        d = ready / "01_К-8М"
        d.mkdir()
        for nm in ("01_ЛИСТАЙ", "02_ЦИФРЫ", "03_СЦЕНАРИИ", "04_CTA"):
            Image.new("RGB", (1080, 1350), "#111").save(d / f"{nm}.png")
        Image.new("RGB", (4320, 1350), "#222").save(strips / "01_К-8М.png")
        for w in ("390", "540"):
            Image.new("RGB", (390, 488), "#333").save(READABILITY / w / "x.png")
        # html
        def slide(idx, body):
            return (f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
                    f'<main class="banner slide--{idx}"><div class="num">{idx}/04</div>'
                    f'<div class="progress"><i></i><i></i><i></i><i></i></div>{body}'
                    f'<div class="cta">@vokope_ru +7 (999) 136-71-42</div>'
                    f'<div class="price">Прайс по запросу</div>'
                    f'<div class="legal">Характеристики — по паспорту изделия. Не является публичной офертой. РЭС — по законодательству РФ.</div>'
                    f'</main></body></html>')
        hd = html / "01_К-8М"
        hd.mkdir()
        hd.joinpath("01_ЛИСТАЙ.html").write_text(slide("01", "<h1>К-8М</h1><p>8 каналов. 400–5900 МГц.</p><p>Листай — что внутри →</p>"), encoding="utf-8")
        hd.joinpath("02_ЦИФРЫ.html").write_text(slide("02", "<h2>Что внутри</h2><p>160 Вт · 50–200 м · 20 кг</p><p>Кому?</p>"), encoding="utf-8")
        hd.joinpath("03_СЦЕНАРИИ.html").write_text(slide("03", "<h2>Кому это надо</h2><p>Транспорт и техника · ББМ · Патрули</p><p>Листай — цена</p>"), encoding="utf-8")
        hd.joinpath("04_CTA.html").write_text(slide("04", "<h2>Тот самый К-8М</h2><p>Напиши в Telegram — пришлём цену</p>"), encoding="utf-8")
        html.joinpath("00_СУПЕРЦЕНЫ.html").write_text(slide("00", "<h1>СУПЕРЦЕНЫ</h1>"), encoding="utf-8")
        (ready / "gallery").mkdir()
        (ready / "gallery" / "index.html").write_text("<html>" + " ".join([f"../01_К-8М/{n}.png" for n in ("01_ЛИСТАЙ", "02_ЦИФРЫ", "03_СЦЕНАРИИ", "04_CTA")]) + "../00_СУПЕРЦЕНЫ.png</html>", encoding="utf-8")
        (ready / "ЧЕК_ЛИСТ_ФАЙЛОВ.md").write_text("Итог: OK · FAIL: 0 · WARN: 0", encoding="utf-8")
        res = run(write=False)
        checks = [
            ("good: нет блокеров", res["summary"]["blockers"] == 0,
             [f["msg"] for f in res["findings"] if f["code"].startswith("Б")]),
        ]
        # bad data: нет крючка, дубль, banned, цифра
        bad = dict(GOOD)
        bad.update({"s1_swipe": "Смотрите", "s2_lead": "Подробнее", "s4_price": "Цена: 300 000 ₽",
                    "s1_sub": "100% защита", "s4_title": "К-8М навсегда"})
        bad_pos = dict(pos[0]); bad_pos.update(bad)
        globals()["POSITIONS"].write_text(json.dumps({"positions": [bad_pos]}, ensure_ascii=False), encoding="utf-8")
        res2 = run(stage="data", write=False)
        checks += [
            ("bad: нет листай -> З", any(f["code"] == "З" and "s1_swipe" in f["msg"] for f in res2["findings"]), ""),
            ("bad: нет «внутри» -> З", any(f["code"] == "З" and "s2_lead" in f["msg"] for f in res2["findings"]), ""),
            ("bad: цена -> Б5", any(f["code"] == "Б5" for f in res2["findings"]), ""),
            ("bad: s4_price -> Б4", any(f["code"] == "Б4" for f in res2["findings"]), ""),
            ("bad: banned -> Б2", any(f["code"] == "Б2" for f in res2["findings"]), ""),
        ]
        ok = True
        for name, cond, extra in checks:
            print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f" [{extra}]"))
            ok = ok and cond
        print("== SELFTEST:", "OK" if ok else "FAILED", "==")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        (DATA, HTML, READY, POSITIONS, CAROUSEL_JSON, STRIPS, READABILITY, cs.POSITIONS, cs.HTML, cs.READY, cs.PROJECT) = saved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA-линтер карусели «СУПЕРЦЕНЫ»")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--stage", default="all", choices=["all", "data", "html", "png"])
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    res = run(stage=args.stage, write=not args.no_write)
    print_console(res)
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_КАРУСЕЛЬ_АВТОПРОВЕРКА.md'}")
        print(f"  json:  {QA / 'QA_КАРУСЕЛЬ_АВТОПРОВЕРКА.json'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
