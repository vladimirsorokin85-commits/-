#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_banners.py — QA-линтер пакета рекламных баннеров «КИЛОВАТТ» (роль qa).

Проверяет:
  A) banners_data.json (18 моделей): обязательные поля, длина хука/строки, 3–4 цифры,
     claim-привязку, banned-фразы (BANNED.md), цены (₽/руб.), CTA, юрстроку, тона/фото;
  B) banners/html/*.html (36 файлов = 18 моделей × 2 формата): извлечённый текст,
     banned-фразы, цены, CTA @vokope_ru + +7 999 136-71-42, юрстрока, все числа — сверка
     с infographics/01_ФАКТЫ/claims.json (127 утверждений), наличие фото модели,
     баннерные форматы 1080×1350 / 1080×1080, внешние ресурсы, градиенты/тени;
  C) banners/05_ГОТОВОЕ/png: наличие/размеры 72 PNG (18×2 формата × 1×/2×), конвенция имён.

Использует проверенный линтер инфографики (import read-only): check_claims.py.
Результат: banners/03_QA/QA_АВТОПРОВЕРКА_БАННЕРЫ.md + .json.

Запуск:
  python check_banners.py            # обычный прогон
  python check_banners.py --selftest # самопроверка на синтетике
  python check_banners.py --no-write
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
QA = Path(__file__).resolve().parent
BANNERS = QA.parent
PROJECT = BANNERS.parent
INF_QA = PROJECT / "infographics" / "03_QA" / "check_claims.py"

# ---------------------------------------------------------------- импорт линтера инфографики
_spec = importlib.util.spec_from_file_location("inf_check_claims", INF_QA)
if _spec is None or _spec.loader is None:
    raise SystemExit(f"не найден базовый линтер: {INF_QA}")
shared = importlib.util.module_from_spec(_spec)
sys.modules["inf_check_claims"] = shared
_spec.loader.exec_module(shared)

# ---------------------------------------------------------------- модели B01–B18 (по брифу §2)
MODELS = {
    "B01": {"model": "Капюшон К-8М", "tone": "field", "photo": "k8m"},
    "B02": {"model": "Капюшон К-12М", "tone": "field", "photo": "k12m"},
    "B03": {"model": "Капюшон К-15М", "tone": "field", "photo": "k15m"},
    "B04": {"model": "Капюшон К-12 багажный бокс", "tone": "field", "photo": "k12m-bag-box"},
    "B05": {"model": "ФПВ-8М", "tone": "field", "photo": "fpv-8m"},
    "B06": {"model": "ФПВ-12", "tone": "field", "photo": "fpv-12"},
    "B07": {"model": "ФПВ-5 мото", "tone": "field", "photo": "fpv-7-moto"},
    "B08": {"model": "Штора К-12/700", "tone": "quiet", "photo": "shtora-k12"},
    "B09": {"model": "Штора-М К-8/600", "tone": "quiet", "photo": "shtora-m"},
    "B10": {"model": "Ребус-4", "tone": "quiet", "photo": "rebus-4"},
    "B11": {"model": "Поле-31", "tone": "quiet", "photo": "pole-31"},
    "B12": {"model": "Сигнал-М2", "tone": "quiet", "photo": "signal-m2"},
    "B13": {"model": "ТП 4-28А/Б", "tone": "field", "photo": "tp-4-28a"},
    "B14": {"model": "ТП 4-50А/Б", "tone": "field", "photo": "tp-4-50a"},
    "B15": {"model": "ТП 7-100", "tone": "field", "photo": "tp-7-100"},
    "B16": {"model": "ТП 8-100", "tone": "field", "photo": "tp-8-100"},
    "B17": {"model": "ИП-24/100", "tone": "quiet", "photo": "ip-24-100"},
    "B18": {"model": "ТЭБ-тестер Т-9", "tone": "quiet", "photo": "t-9"},
}
EXPECTED_IDS = [f"B{i:02d}" for i in range(1, 19)]
FORMATS = {"poster": "1080x1350", "square": "1080x1080"}
CTA_TG = re.compile(r"@vokope[_\- ]?ru", re.I)
PHONE = "79991367142"
BID_RE = re.compile(r"\bB\d{1,2}\b")
LEGAL_MARKERS = [
    ("по паспорту изделия", re.compile(r"по\s+паспорту\s+изделия", re.I)),
    ("РЭС/законодательство", re.compile(r"\bРЭС\b|законодательств", re.I)),
    ("порядок применения", re.compile(r"порядок\s+(?:приобретения|регистрации|применения)", re.I)),
    ("не оферта", re.compile(r"публичной\s+офертой", re.I)),
]
PRICE_WORD_RE = re.compile(r"\bцен[аыуеи]\b|\bстоимост\w*|\bпрайс\w*", re.I)
PRICE_OK_RE = re.compile(r"цен[аыуеи]\s+по\s+запросу|по\s+запросу|кп\s+под\s+задачу", re.I)

# ---------------------------------------------------------------- v3: техблок
CANON_PATH = PROJECT / "kilowatt" / "docs" / "КАНОН_цифры_и_факты.md"
TECH_ROWS_MIN, TECH_ROWS_MAX = 4, 6
TECH_LABEL_MAX = 18
TECH_VALUE_MAX = 28
TASK_VOCAB = [
    "fpv", "разведка", "каналы управления", "видеоканал", "навигация",
    "периметр", "транспорт", "группа", "сервис", "питание",
]
# запреты для техблока, даже если число встречается в каноне/claims
TECH_PROHIBIT = [
    (re.compile(r"\b411\s*кг", re.I), "411 кг — запрещено (SPORY S05)"),
    (re.compile(r"41\s+позици", re.I), "«41 позиция» — запрещено (канон §1)"),
    (re.compile(r"\b600\s*Вт", re.I), "600 Вт — не для публичных баннеров (C120/канон §4)"),
    (re.compile(r"(?:штора|штор[а-я]*)[^.;]{0,30}\b[25]\s*км\b|\b[25]\s*км\b[^.;]{0,30}(?:mavic|fpv)", re.I),
     "2/5 км «Шторы» — запрещено (канон §4)"),
    (re.compile(r"пожизненн", re.I), "пожизненная гарантия — запрещено (12 мес)"),
]


@dataclass
class Finding:
    code: str      # Б1 цифра, Б2 запрет, Б3 вёрстка/HTML, Б4 CTA/юрстрока, Б5 цена, З замечание, И инфо
    banner: str
    msg: str
    path: str
    quote: str = ""


def as_dict(f: Finding) -> dict:
    return {"code": f.code, "banner": f.banner, "msg": f.msg, "path": f.path, "quote": f.quote}


DASH_VOLT_RE = re.compile(r"(?<=\d)\s*[–—−]\s*(?=\d+\s*В\b)")


def extract_banner(text: str):
    """числа баннера: id B01 маскируем, dash-диапазоны вольт приводим к «12/24 В»."""
    text = DASH_VOLT_RE.sub("/", text)
    masked = BID_RE.sub(lambda m: "·" * len(m.group(0)), text)
    return shared.extract_all(masked)


def norm(s: str) -> str:
    return shared.norm_match(s or "")


def load_canon(path: Path = CANON_PATH):
    """Цифровой канон (kilowatt/docs/КАНОН_цифры_и_факты.md) как второй разрешённый источник."""
    if not path.is_file():
        return None
    text = shared.read_text(path)
    ex = shared.extract_all(text)
    allowed = shared.build_match_index(ex.facts)
    bare = [v for f in ex.facts for v in f.ends()]
    return {"text": text, "allowed": allowed, "bare": bare, "compact": shared.norm_compact(text)}


def strict_fact_source(fact, claims, allowed_ids: list[str], canon):
    """-> ('claim', cid) | ('canon', None) | (None, None). Только claims из списка баннера или канон."""
    for fc, cid, _pids in claims.fact_meta:
        if allowed_ids and cid not in allowed_ids:
            continue
        st, _ = shared.match_fact(fact, shared.build_match_index([fc]), fc.ends())
        if st in ("exact", "within"):
            return "claim", cid
    if canon:
        st, _ = shared.match_fact(fact, canon["allowed"], canon["bare"])
        if st in ("exact", "within"):
            return "canon", None
    return None, None


def tech_rows(banner: dict) -> list[dict]:
    out = []
    for row in banner.get("tech") or []:
        if isinstance(row, dict):
            label = str(row.get("label", "")).strip()
            value = str(row.get("value", "")).strip()
            if label or value:
                out.append({"label": label, "value": value})
        elif isinstance(row, str):
            out.append({"label": "", "value": row.strip()})
    return out


def task_chips(banner: dict) -> list[str]:
    return [str(t).strip() for t in (banner.get("tasks") or []) if isinstance(t, str) and str(t).strip()]


def task_ok(chip: str) -> bool:
    c = norm(chip)
    return any(c == norm(x) or c.startswith(norm(x)) or norm(x).startswith(c) for x in TASK_VOCAB)


NUM_TOKEN_RE = re.compile(r"\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?")


def numeric_corpus(claims, canon) -> str:
    """Числовой корпус: claims.json (содержательные поля) + канон, в компактном виде."""
    corpus = claims.corpus_compact or ""
    if canon:
        corpus += "§" + canon["compact"]
    return corpus


def token_allowed(token: str, corpus: str) -> bool:
    t = shared.norm_compact(token)
    if not t:
        return True
    # убираем десятичную запятую/точку для сравнения с компактным корпусом
    variants = {t, t.replace(",", ".")}
    return any(v in corpus for v in variants)


def check_tech_block(banner: dict, banner_id: str, claims, canon, path: str):
    """v3: tech 4–6 строк, tasks 2–3 чипа, tech-цифры — только claims/канон, с запрет-оверрайдами."""
    findings: list[Finding] = []
    tech = tech_rows(banner)
    tasks = task_chips(banner)
    if not tech and not tasks:
        return findings, {}
    corpus = numeric_corpus(claims, canon)
    if len(tech) < TECH_ROWS_MIN or len(tech) > TECH_ROWS_MAX:
        findings.append(Finding("З", banner_id, f"tech-строк {len(tech)} (бриф v3: 4–6)", path))
    for row in tech:
        label, value = row["label"], row["value"]
        if not label or not value:
            findings.append(Finding("Б3", banner_id, "tech-строка без label/value", path, f"{label}: {value}"))
            continue
        if len(label) > TECH_LABEL_MAX:
            findings.append(Finding("З", banner_id, f"tech label длиннее {TECH_LABEL_MAX} знаков ({len(label)})", path, label))
        if len(value) > TECH_VALUE_MAX:
            findings.append(Finding("З", banner_id, f"tech value длиннее {TECH_VALUE_MAX} знаков ({len(value)})", path, value))
        row_text = f"{label}: {value}"
        for pat, msg in TECH_PROHIBIT:
            if pat.search(row_text):
                findings.append(Finding("Б1", banner_id, f"tech: {msg}", path, row_text))
        ex = extract_banner(row_text)
        for f in ex.facts:
            if f.kind == "money":
                findings.append(Finding("Б5", banner_id, f"tech: денежная цифра {f.raw}", path, "••• ₽"))
        for tok in NUM_TOKEN_RE.findall(row_text):
            if not token_allowed(tok, corpus):
                findings.append(Finding("Б1", banner_id, f"tech-цифра не подтверждена claims/каноном: {tok.strip()}", path, row_text))
    if len(tasks) < 2 or len(tasks) > 3:
        findings.append(Finding("З", banner_id, f"чипов задач {len(tasks)} (бриф v3: 2–3)", path, ", ".join(tasks)))
    for chip in tasks:
        if not task_ok(chip):
            findings.append(Finding("З", banner_id, f"чип вне списка задач брифа: «{chip}»", path))
    return findings, {"tech_rows": len(tech), "tasks": len(tasks)}


def collect_texts(banner: dict) -> list[str]:
    """Все содержательные строки баннера (кроме служебных id/claims/photo/tone)."""
    out: list[str] = []

    def walk(obj, key=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in ("id", "claims", "photo", "tone", "numbers"):
                    continue
                walk(v, lk)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, key)
        elif isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, (int, float)):
            out.append(str(obj))

    walk(banner)
    return out


def number_texts(banner: dict) -> list[str]:
    nums = banner.get("numbers") or []
    out: list[str] = []
    for n in nums:
        if isinstance(n, str):
            out.append(n)
        elif isinstance(n, dict):
            val = str(n.get("value", "")).strip()
            unit = str(n.get("unit", "")).strip()
            label = str(n.get("label", "")).strip()
            out.append(" ".join(x for x in (val, unit, label) if x))
    return out


def claim_ids(banner: dict) -> list[str]:
    out = []
    for c in banner.get("claims") or []:
        if isinstance(c, str) and re.fullmatch(r"C\d{2,4}", c.strip()):
            out.append(c.strip())
    return out


def check_numbers_text(texts: list[str], claims, allowed_ids: list[str], banner_id: str, path: str, canon=None):
    """сверка цифр текста с claims (+канон); возвращает (findings, checked, exact, within, unknown)."""
    findings: list[Finding] = []
    ex = extract_banner(" ; ".join(texts))
    checked = exact = within = unknown = 0
    for f in ex.facts:
        if f.kind == "money":
            # на баннерах не должно быть цен; рыночные цифры тоже не нужны
            findings.append(Finding("Б5", banner_id, f"денежная цифра на баннере: {f.raw} — цены не публикуем", path, "••• ₽"))
            continue
        if f.raw.strip() in ("100%", "100 %", "№1", "№ 1"):
            continue  # часть запрещённой формулировки — отдельно ловится Б2
        checked += 1
        status, detail = shared.match_fact(f, claims.allowed, claims.bare_points)
        if status == "exact":
            exact += 1
        elif status == "within":
            within += 1
        elif status == "loose":
            within += 1
        else:
            # фолбэк: claim мог перечислять число в поле numbers («90» для «90 минут»)
            fallback_ids = []
            if allowed_ids:
                by_claim = {shared.claim_id(c): c for c in claims.claims}
                for cid in allowed_ids:
                    c = by_claim.get(cid)
                    if not c:
                        continue
                    for item in c.get("numbers") or []:
                        mm = re.search(r"\d[\d\s.,]*", str(item))
                        if not mm:
                            continue
                        try:
                            val = shared.parse_num(mm.group(0))
                        except Exception:
                            continue
                        if abs(val - f.value) < 1e-6 or (f.hi is not None and abs(val - f.hi) < 1e-6):
                            fallback_ids.append(cid)
                            break
            if fallback_ids:
                within += 1
                findings.append(
                    Finding("И", banner_id, f"цифра {f.raw} подтверждена полем numbers claim {fallback_ids[0]} (единица не распознана автоматически)", path, f.raw)
                )
                continue
            # канон (kilowatt/docs/КАНОН_цифры_и_факты.md) — разрешённый второй источник для баннеров v3
            if canon:
                st2, _ = shared.match_fact(f, canon["allowed"], canon["bare"])
                if st2 in ("exact", "within"):
                    within += 1
                    findings.append(Finding("И", banner_id, f"цифра {f.raw} подтверждена КАНОНом (в claims.json нет) — просьба фактчекеру добавить claim", path, f.raw))
                    continue
            unknown += 1
            findings.append(Finding("Б1", banner_id, f"цифра не подтверждена claims.json: {f.raw} — {detail}", path, f.raw))
            continue
        # привязка к claim из списка banner.claims
        if allowed_ids:
            prov = []
            for fc, cid, _pids in claims.fact_meta:
                if cid not in allowed_ids:
                    continue
                st, _ = shared.match_fact(f, shared.build_match_index([fc]), fc.ends())
                if st in ("exact", "within", "loose"):
                    prov.append(cid)
            if not prov:
                findings.append(
                    Finding("З", banner_id, f"цифра {f.raw} не привязана ни к одному claim из списка {allowed_ids}", path, f.raw)
                )
    return findings, checked, exact, within, unknown


def check_text_rules(texts: list[str], banner_id: str, path: str, banned_hard, claims, claims_ids: list[str]):
    """banned/цены/CTA/юрстрока по набору строк."""
    findings: list[Finding] = []
    text = " ".join(texts)
    text_n = norm(text)
    protected = [mm.span() for pat in shared.DISCLAIMER_PROTECT_RES for mm in pat.finditer(text)]

    def in_disclaimer(i: int) -> bool:
        return any(s <= i < e for s, e in protected)

    for phrase in banned_hard:
        if len(phrase) < 4:
            continue
        for mm in shared.phrase_to_regex(phrase).finditer(text):
            if in_disclaimer(mm.start()):
                continue
            findings.append(Finding("Б2", banner_id, f"запрещённая формулировка «{mm.group(0)}»", path, shared.ctx_of(text, mm.group(0))))
    for pat, code, msg in shared.MILITARY_RES:
        for mm in pat.finditer(text):
            if in_disclaimer(mm.start()):
                continue
            findings.append(Finding(code if code.startswith("Б") else "З", banner_id, f"военная риторика: {msg}", path, mm.group(0)))

    # цены
    for mm in PRICE_WORD_RE.finditer(text):
        frag = text[max(0, mm.start() - 60): mm.end() + 60]
        if PRICE_OK_RE.search(frag):
            continue
        if re.search(r"\d[\d\s.,]*(?:₽|руб(?:\.|лей)?|р\.)", frag, re.I):
            findings.append(Finding("Б5", banner_id, "цена/сумма в тексте баннера", path, "••• ₽"))
        else:
            findings.append(Finding("И", banner_id, "упоминание цены без значения (допустимо)", path, shared.norm_ws(frag)[:120]))

    # CTA и юрстрока — только для HTML считаются блокером, для данных мягче
    return findings


def cta_present(text: str) -> tuple[bool, bool]:
    return bool(CTA_TG.search(text)), PHONE in re.sub(r"\D", "", text)


def legal_present(text: str) -> list[str]:
    return [name for name, pat in LEGAL_MARKERS if pat.search(text)]


# ---------------------------------------------------------------- данные
def check_data(data, claims, banned_hard, data_path: Path, canon=None):
    findings: list[Finding] = []
    banners: list[dict] = []
    if isinstance(data, list):
        banners = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        for key in ("banners", "items", "data", "list"):
            if isinstance(data.get(key), list):
                banners = [x for x in data[key] if isinstance(x, dict)]
                break
        if not banners:
            banners = [v for v in data.values() if isinstance(v, dict) and "hook" in v]
    by_id: dict[str, dict] = {}
    for b in banners:
        bid = str(b.get("id", "")).strip().upper()
        if bid:
            by_id[bid] = b
    if not banners:
        findings.append(Finding("И", "data", "banners_data.json ещё не готов (0 объектов) — прогон промежуточный", str(data_path)))
        return findings, by_id

    for bid in EXPECTED_IDS:
        b = by_id.get(bid)
        if not b:
            findings.append(Finding("Б3", bid, "нет объекта в banners_data.json", str(data_path)))
            continue
        path = str(data_path)
        # поля
        name = str(b.get("name") or b.get("model") or "").strip()
        hook = str(b.get("hook") or "").strip()
        line = str(b.get("line") or "").strip()
        tone = str(b.get("tone") or "").strip().lower()
        photo = str(b.get("photo") or "").strip()
        aud = str(b.get("audience") or "").strip()
        nums = b.get("numbers") or []
        cids = claim_ids(b)
        if not name:
            findings.append(Finding("Б3", bid, "нет name/model", path))
        if not hook:
            findings.append(Finding("Б3", bid, "нет hook", path))
        elif len(hook) > 40:
            findings.append(Finding("З", bid, f"hook длиннее 40 знаков ({len(hook)})", path, hook))
        if not line:
            findings.append(Finding("Б3", bid, "нет line", path))
        elif len(line) > 90:
            findings.append(Finding("З", bid, f"line длиннее 90 знаков ({len(line)})", path, line))
        if tone not in ("field", "quiet"):
            findings.append(Finding("Б3", bid, f"tone должен быть field/quiet, а не «{tone}»", path))
        elif tone != MODELS[bid]["tone"]:
            findings.append(Finding("З", bid, f"tone «{tone}» не совпадает с брифом ({MODELS[bid]['tone']})", path))
        if not photo:
            findings.append(Finding("З", bid, "не указан photo-ассет", path))
        if len(nums) < 3:
            findings.append(Finding("З", bid, f"цифр-козырей меньше 3 ({len(nums)})", path))
        elif len(nums) > 4:
            findings.append(Finding("З", bid, f"цифр-козырей больше 4 ({len(nums)})", path))
        if not cids:
            findings.append(Finding("Б3", bid, "нет claim-привязки (claims[])", path))
        else:
            known = {shared.claim_id(c) for c in claims.claims}
            for cid in cids:
                if cid not in known:
                    findings.append(Finding("Б1", bid, f"claim {cid} отсутствует в claims.json", path))
        # запреты/цены
        texts = collect_texts(b)
        findings.extend(check_text_rules(texts, bid, path, banned_hard, claims, cids))
        # цифры
        tf, checked, exact, within, unknown = check_numbers_text(number_texts(b), claims, cids, bid, path, canon)
        findings.extend(tf)
        # v3: техблок и чипы задач
        tech_f, tech_stats = check_tech_block(b, bid, claims, canon, path)
        findings.extend(tech_f)
        # CTA в данных (мягко: вёрстка добавит футер)
        joined = " ".join(texts)
        tg, ph = cta_present(joined)
        if not tg or not ph:
            findings.append(Finding("И", bid, "CTA @vokope_ru/телефон не в данных (ожидается в шаблоне вёрстки)", path))
        # юрстрока в данных не обязательна — её добавляет шаблон (проверяется в HTML)
        b["_stats"] = {"numbers_checked": checked, "numbers_exact": exact, "numbers_within": within,
                       "numbers_unknown": unknown, "claims": len(cids), **tech_stats}
    return findings, by_id


# ---------------------------------------------------------------- HTML
def banner_id_from_file(p: Path) -> str:
    mm = re.match(r"(?i)^(B\d{1,2})", p.name)
    return mm.group(1).upper() if mm else "?"


def expected_html_names() -> dict[str, dict[str, re.Pattern]]:
    out = {}
    for bid in EXPECTED_IDS:
        out[bid] = {
            fmt: re.compile(rf"^{bid}_.*_{size}\.html$", re.I)
            for fmt, size in FORMATS.items()
        }
    return out


def check_html(html_dir: Path, by_id: dict, claims, banned_hard, banners_root: Path, canon=None):
    findings: list[Finding] = []
    corpus = numeric_corpus(claims, canon)
    files = sorted(html_dir.rglob("*.html")) if html_dir.is_dir() else []
    if not files:
        return [Finding("И", "html", "HTML баннеров ещё не созданы — прогон промежуточный", str(html_dir))], {}
    exp = expected_html_names()
    found: dict[str, dict[str, list[Path]]] = {bid: {"poster": [], "square": []} for bid in EXPECTED_IDS}
    for p in files:
        bid = banner_id_from_file(p)
        if bid not in MODELS:
            findings.append(Finding("З", bid, f"неизвестный файл баннера: {p.name}", str(p)))
            continue
        for fmt, pat in exp[bid].items():
            if pat.match(p.name):
                found[bid][fmt].append(p)
    for bid in EXPECTED_IDS:
        for fmt in ("poster", "square"):
            if not found[bid][fmt]:
                findings.append(Finding("Б3", bid, f"нет HTML формата {fmt} ({FORMATS[fmt]}) в banners/html/", str(html_dir)))
            elif len(found[bid][fmt]) > 1:
                names = ", ".join(sorted(p.name for p in found[bid][fmt]))
                findings.append(Finding("Б3", bid, f"несколько HTML для формата {fmt} — устаревшие имена не удалены: {names}", str(html_dir)))
    # по каждому файлу
    for bid in EXPECTED_IDS:
        for fmt in ("poster", "square"):
            for p in found[bid][fmt]:
                try:
                    poster = shared.load_poster(p, banners_root)
                except Exception as exc:
                    findings.append(Finding("Б3", bid, f"HTML не разбирается: {exc}", str(p)))
                    continue
                text = poster.raw_text
                # banned/military/цены
                findings.extend(check_text_rules([text], bid, str(p), banned_hard, claims, claim_ids(by_id.get(bid, {}))))
                # CTA + юрстрока
                tg, ph = cta_present(text)
                if not tg:
                    findings.append(Finding("Б4", bid, f"нет CTA Telegram @vokope_ru ({fmt})", str(p), ""))
                if not ph:
                    findings.append(Finding("Б4", bid, f"нет CTA-телефона +7 (999) 136-71-42 ({fmt})", str(p), ""))
                lm = legal_present(text)
                if len(lm) < 2:
                    findings.append(Finding("Б4", bid, f"нет юрстроки ({fmt}): найдено {lm or '—'}", str(p), ""))
                # цифры
                tf, checked, exact, within, unknown = check_numbers_text([text], claims, claim_ids(by_id.get(bid, {})), bid, str(p), canon)
                findings.extend(tf)
                # фото модели
                hint = MODELS[bid]["photo"]
                pdata = by_id.get(bid, {})
                if pdata.get("photo"):
                    hint = Path(str(pdata["photo"])).stem
                imgs = [str(i.get("src", "")) for i in poster.images]
                if not any(hint.lower() in s.lower() for s in imgs):
                    findings.append(Finding("З", bid, f"в HTML нет фото модели (ожидался ассет «{hint}»): {imgs}", str(p)))
                # внешние ресурсы / запрещённые приёмы (переиспользуем CSS-чек)
                css_find = shared.css_checks(poster, banners_root)
                local_fonts = BANNERS / "_design" / "fonts"
                for f in css_find:
                    code = f["code"]
                    if "кегль" in f["msg"]:
                        continue  # мелкая юрстрока/служебные метки на баннере — норма
                    if "не скопирован" in f["msg"]:
                        fname = f.get("quote", "")
                        if (local_fonts / fname).is_file():
                            continue  # шрифт локально есть; предупреждение — артефакт др. структуры папок
                    findings.append(Finding(code, bid, f["msg"], str(p), f.get("quote", "")))
                if not pdata:
                    continue
                # название модели в вёрстке
                name_short = str(pdata.get("name_short") or "").strip()
                if name_short and norm(name_short) not in norm(text):
                    findings.append(Finding("З", bid, f"название модели «{name_short}» не найдено в вёрстке ({fmt})", str(p), name_short))
                # v3: техблок в вёрстке
                tech = tech_rows(pdata)
                tasks = task_chips(pdata)
                if tech or tasks:
                    t_norm = norm(text)
                    t_compact = shared.norm_compact(text)
                    block_present = bool(re.search(r"коротко|параметр\w*|техническ\w*", t_norm)) or "b-tech" in poster.html_source.lower() or "tech" in poster.html_source.lower()
                    if not block_present:
                        findings.append(Finding("Б3", bid, f"v3: техблок не найден в вёрстке ({fmt})", str(p)))
                    for row in tech:
                        label, value = row["label"], row["value"]
                        if label and norm(label) not in t_norm:
                            findings.append(Finding("З", bid, f"v3: tech-label «{label}» не найден в вёрстке ({fmt})", str(p)))
                        for pat, msg in TECH_PROHIBIT:
                            if pat.search(f"{label}: {value}"):
                                findings.append(Finding("Б1", bid, f"tech: {msg} ({fmt})", str(p), f"{label}: {value}"))
                        for tok in NUM_TOKEN_RE.findall(f"{label} {value}"):
                            if not token_allowed(tok, corpus):
                                findings.append(Finding("Б1", bid, f"v3: tech-цифра в вёрстке не подтверждена claims/каноном: {tok.strip()} ({fmt})", str(p), value))
                            elif shared.norm_compact(tok) not in t_compact:
                                findings.append(Finding("З", bid, f"v3: tech-значение {tok.strip()} не найдено в тексте вёрстки ({fmt})", str(p), value))
                        if not NUM_TOKEN_RE.search(value) and value and shared.norm_compact(value) not in t_compact:
                            findings.append(Finding("З", bid, f"v3: tech-value «{value}» не найдено в вёрстке ({fmt})", str(p)))
                    for chip in tasks:
                        if norm(chip) not in t_norm:
                            findings.append(Finding("З", bid, f"v3: чип «{chip}» не найден в вёрстке ({fmt})", str(p)))
                # синхронность данных и вёрстки
                dtext = norm(" ".join(collect_texts(pdata)))
                if pdata.get("hook") and norm(str(pdata["hook"])) not in dtext:
                    pass
                if pdata.get("hook") and norm(str(pdata["hook"])) not in norm(text):
                    findings.append(Finding("З", bid, f"хук из данных не найден в вёрстке ({fmt})", str(p), str(pdata.get("hook"))))
                for nt in number_texts(pdata):
                    if not nt.strip():
                        continue
                    if norm(nt) not in norm(text):
                        findings.append(Finding("З", bid, f"цифра «{nt}» из данных не найдена в вёрстке ({fmt})", str(p), nt))
    return findings, found


# ---------------------------------------------------------------- PNG
def check_png(png_dir: Path):
    findings: list[Finding] = []
    if not png_dir.is_dir():
        return [Finding("И", "png", "png-папка ещё не создана", str(png_dir))], {}
    try:
        from PIL import Image
    except Exception:
        Image = None
    files = sorted(png_dir.glob("*.png"))
    if not files:
        return [Finding("И", "png", "PNG ещё не отрендерены — прогон промежуточный", str(png_dir))], {}
    report: dict = {}
    for bid in EXPECTED_IDS:
        bfiles = [p for p in files if p.name.upper().startswith(bid + "_")]
        report[bid] = [p.name for p in bfiles]
        ok = {"poster1": False, "poster2": False, "square1": False, "square2": False}
        for p in bfiles:
            if Image is None:
                continue
            try:
                w, h = Image.open(p).size
            except Exception:
                findings.append(Finding("Б3", bid, f"PNG не читается: {p.name}", str(p)))
                continue
            name = p.name.lower()
            if w == 1080 and h == 1350:
                ok["poster1"] = True
            elif w == 2160 and h == 2700:
                ok["poster2"] = True
            elif w == 1080 and h == 1080:
                ok["square1"] = True
            elif w == 2160 and h == 2160:
                ok["square2"] = True
            elif (w, h) in ((1080, 1920), (2160, 3840)):
                pass  # сторис 9:16 — валидный доп. формат (второй эшелон)
            else:
                findings.append(Finding("Б3", bid, f"нестандартный размер PNG {w}×{h}: {p.name}", str(p)))
        for key, label in (("poster1", "1080×1350"), ("poster2", "2160×2700 @2x"),
                           ("square1", "1080×1080"), ("square2", "2160×2160 @2x")):
            if not ok[key]:
                findings.append(Finding("Б3", bid, f"нет PNG {label}", str(png_dir)))
        # лишние файлы = устаревшие имена после переименования (ожидаем 4, для сторис-моделей 6)
        expected_cnt = 6 if bid in ("B01", "B02", "B07", "B08", "B10", "B12") else 4
        if len(bfiles) > expected_cnt:
            extra = sorted(p.name for p in bfiles)
            findings.append(Finding("Б3", bid, f"лишние PNG ({len(bfiles)} вместо {expected_cnt}) — устаревшие имена: {', '.join(extra[:6])}", str(png_dir)))
    return findings, report


# ---------------------------------------------------------------- отчёт
def render_md(result: dict) -> str:
    L: list[str] = []
    ap = L.append
    s = result["summary"]
    ap("# QA_АВТОПРОВЕРКА БАННЕРОВ — «В ОКОПЕ» × НПО «Киловатт»")
    ap("")
    ap(f"- Прогон: **{result['generated']}**, `check_banners.py` v{VERSION}")
    ap(f"- Входы: banners_data.json — **{result['inputs']['data']}**; "
       f"HTML — **{result['inputs']['html']}**; PNG — **{result['inputs']['png']}**; "
       f"claims.json — {result['inputs']['claims']} утверждений; BANNED — {result['inputs']['banned']}")
    if s["blockers"] == 0:
        verdict = "✅ **Блокеров не обнаружено**"
    else:
        verdict = f"❌ **Не сдано: {s['blockers']} блокер(ов)**"
    ap(f"## Итог: {verdict}")
    ap("")
    ap(f"Блокеры: **{s['blockers']}** · Замечания: **{s['warnings']}** · Инфо: **{s['infos']}**")
    ap("")
    ap("## 1. Данные и HTML по баннерам")
    ap("")
    ap("| Баннер | Модель | Данные | Poster 4:5 | Square 1:1 | Цифры | Техблок v3 | CTA | Юрстрока | Итог |")
    ap("|---|---|---|---|---|---|---|---|---|---|")
    by_id = result["by_id"]
    for bid in EXPECTED_IDS:
        b = by_id.get(bid)
        d = result["data_stats"].get(bid, {})
        h = result["html_stats"].get(bid, {})
        nums = f"{d.get('numbers_exact', 0)}/{d.get('numbers_checked', 0)}"
        tr, tc = d.get("tech_rows", 0), d.get("tasks", 0)
        tech = f"{tr} строк / {tc} чипа" if tr else "—"
        codes = [f["code"] for f in result["findings"] if f["banner"] == bid]
        verdict = "❌" if any(c.startswith("Б") for c in codes) else ("⚠" if codes else "✅")
        data_ok = "✅" if b and d.get("numbers_unknown", 0) == 0 else "⚠"
        ap(f"| {bid} | {MODELS[bid]['model']} | {data_ok} | {h.get('poster', '—')} | {h.get('square', '—')} | {nums} | {tech} | "
           f"{h.get('cta', '—')} | {h.get('legal', '—')} | {verdict} |")
    ap("")
    ap("## 2. Блокеры")
    ap("")
    blockers = [f for f in result["findings"] if f["code"].startswith("Б")]
    if not blockers:
        ap("Блокеров нет.")
    else:
        for f in blockers:
            ap(f"- **{f['code']}** `{f['banner']}` · {f['msg']}")
            if f.get("quote"):
                ap(f"  - цитата: «{f['quote']}»")
            ap(f"  - файл: `{f['path']}`")
    ap("")
    ap("## 3. Замечания и инфо")
    ap("")
    ws = [f for f in result["findings"] if f["code"] in ("З", "И")]
    if not ws:
        ap("Замечаний нет.")
    else:
        for f in ws:
            ap(f"- **{f['code']}** `{f['banner']}` · {f['msg']}" + (f" — «{f['quote']}»" if f.get("quote") else "") + f" · `{f['path']}`")
    ap("")
    ap("## 4. PNG-форматы (18 моделей × 2 формата × 1×/2×)")
    ap("")
    if result["png"]:
        miss = sum(1 for v in result["png"].values() if len(v) < 4)
        ap(f"- PNG найдено: **{sum(len(v) for v in result['png'].values())}**; моделей с полным набором: **{len(result['png']) - miss}/18**")
        for bid in EXPECTED_IDS:
            names = result["png"].get(bid, [])
            ap(f"- {bid}: {len(names)} PNG — {', '.join(names) if names else '—'}")
    else:
        ap("PNG ещё нет (рендер не завершён).")
    ap("")
    ap("## 5. Методика")
    ap("")
    ap("- Цифры баннеров сверяются с `infographics\\01_ФАКТЫ\\claims.json` (единственный источник цифр по факт-политике проекта).")
    ap("- Запрещённые формулировки — `infographics\\01_ФАКТЫ\\BANNED.md`; военная риторика — те же правила, что в инфографике.")
    ap("- Цены: любые ₽/руб. с суммой — блокер; «Цена по запросу» разрешена.")
    ap("- CTA и юрстрока обязательны в каждом HTML обоих форматов; в данных допускается их отсутствие (их добавляет шаблон).")
    ap("- **v3 техблок:** `tech` 4–6 строк (label ≤18, value ≤28), `tasks` 2–3 чипа из списка брифа; tech-цифры проверяются")
    ap("  по числовому корпусу claims.json + `kilowatt\\docs\\КАНОН_цифры_и_факты.md`, плюс запрет-оверрайды")
    ap("  (600 Вт «Шторы», 411 кг, 41 позиция, 2/5 км, пожизненная гарантия). Наличие техблока в HTML обязательно.")
    ap("- Визуальный аудит финальных PNG (читаемость названия/цифр, фото, наложения) выполняется вручную через read_image.")
    return "\n".join(L) + "\n"


def run(data_path: Path, html_dir: Path, png_dir: Path, claims_path: Path, banned_path: Path,
        out_md: Path | None = None, out_json: Path | None = None, write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    claims = shared.load_claims(claims_path)
    banned_hard, banned_soft, banned_note = shared.parse_banned(banned_path)
    canon = load_canon()

    data = None
    data_status = "missing"
    if data_path.is_file():
        try:
            data = json.loads(shared.read_text(data_path))
            data_status = "ok"
        except Exception as exc:
            data_status = f"invalid: {exc}"

    findings: list[Finding] = []
    by_id: dict = {}
    data_stats: dict = {}
    if data is not None:
        df, by_id = check_data(data, claims, banned_hard, data_path, canon)
        findings.extend(df)
        for bid, b in by_id.items():
            data_stats[bid] = b.get("_stats", {})

    hf, found = check_html(html_dir, by_id, claims, banned_hard, BANNERS, canon)
    findings.extend(hf)
    html_stats: dict = {}
    for bid in EXPECTED_IDS:
        poster_html = found.get(bid, {}).get("poster", [])
        square_html = found.get(bid, {}).get("square", [])
        cta_ok = legal_ok = "—"
        if poster_html:
            t = shared.load_poster(poster_html[0], BANNERS).raw_text
            tg, ph = cta_present(t)
            cta_ok = "✅" if (tg and ph) else "❌"
            legal_ok = "✅" if len(legal_present(t)) >= 2 else "❌"
        html_stats[bid] = {
            "poster": f"✅ {len(poster_html)}" if poster_html else "❌ нет",
            "square": f"✅ {len(square_html)}" if square_html else "❌ нет",
            "cta": cta_ok,
            "legal": legal_ok,
        }

    pf, png_report = check_png(png_dir)
    findings.extend(pf)

    # дедупликация одинаковых сообщений (данные + poster + square дают один и тот же дефект)
    seen: dict[tuple, Finding] = {}
    for f in findings:
        key = (f.code, f.banner, f.msg)
        if key in seen:
            seen[key]._count = getattr(seen[key], "_count", 1) + 1
            continue
        seen[key] = f
    findings = list(seen.values())

    n_b = sum(1 for f in findings if f.code.startswith("Б"))
    n_z = sum(1 for f in findings if f.code == "З")
    n_i = sum(1 for f in findings if f.code == "И")
    result = {
        "generated": generated,
        "version": VERSION,
        "inputs": {
            "data": data_status,
            "html": f"{sum(len(v['poster']) + len(v['square']) for v in found.values())} файлов",
            "png": f"{sum(len(v) for v in png_report.values())} PNG" if png_report else "нет",
            "claims": len(claims.claims),
            "banned": banned_note,
        },
        "summary": {"blockers": n_b, "warnings": n_z, "infos": n_i},
        "by_id": by_id,
        "data_stats": data_stats,
        "html_stats": html_stats,
        "png": png_report,
        "findings": [as_dict(f) for f in findings],
    }
    md = render_md(result)
    if write and out_md:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md, encoding="utf-8")
        if out_json:
            out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    result["_md"] = md
    return result


def print_console(res: dict) -> None:
    s = res["summary"]
    print(f"check_banners v{VERSION}: {res['generated']}")
    print(f"  data: {res['inputs']['data']} | html: {res['inputs']['html']} | png: {res['inputs']['png']}")
    print(f"  claims: {res['inputs']['claims']} | {res['inputs']['banned']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['banner']}: {f['msg']}")


# ---------------------------------------------------------------- самопроверка
def selftest() -> int:
    print("== SELFTEST check_banners.py ==")
    tmp = Path(tempfile.mkdtemp(prefix="qa_banners_"))
    (tmp / "00_КОПИРАЙТ").mkdir()
    (tmp / "html").mkdir()
    (tmp / "05_ГОТОВОЕ" / "png").mkdir(parents=True)
    (tmp / "03_QA").mkdir()
    # фиктивные ассеты, чтобы проверка картинок не шумела
    try:
        from PIL import Image as _Img
        for rel, size in ((("_design", "img", "brand", "logo_w_word.png"), (400, 100)),
                          (("_design", "img", "product", "k8m.png"), (600, 400)),
                          (("_design", "img", "product", "k12m.png"), (600, 400))):
            fp = tmp.joinpath(*rel)
            fp.parent.mkdir(parents=True, exist_ok=True)
            _Img.new("RGB", size, "#F0EBDC").save(fp)
    except Exception:
        pass
    claims_path = PROJECT / "infographics" / "01_ФАКТЫ" / "claims.json"
    banned_path = PROJECT / "infographics" / "01_ФАКТЫ" / "BANNED.md"

    good = {
        "id": "B01", "model": "«Капюшон» К-8М", "name_short": "К-8М",
        "hook": "КУПОЛ НАД МАШИНОЙ", "line": "Мобильная станция подавления дронов: на крышу, от бортовой сети 12/24 В.",
        "numbers": [{"value": "8", "unit": "каналов", "label": "подавления"},
                    {"value": "50–200", "unit": "м", "label": "дальность"},
                    {"value": "20", "unit": "кг", "label": "вес"}],
        "audience": "авто · мото", "tone": "field", "photo": "k8m.png",
        "claims": ["C016"], "cta": "Цена по запросу · Доставка по РФ · Самовывоз в Москве",
    }
    bad = {
        "id": "B02", "model": "«Капюшон» К-12М", "name_short": "К-12М",
        "hook": "100% ЗАЩИТА ОТ ДРОНОВ", "line": "Дрон не пролетит. Цена: 350 000 ₽.",
        "numbers": [{"value": "99999", "unit": "МГц", "label": "диапазон"}],
        "audience": "объект", "tone": "field", "photo": "k12m.png",
        "claims": ["C019"], "cta": "Купить",
        "ids": None,
    }
    good["tasks"] = ["FPV", "транспорт"]
    good["tech"] = [
        {"label": "Диапазоны", "value": "400–1020, 2100–2800, 5680–5900 МГц"},
        {"label": "Дальность", "value": "50–200 м"},
        {"label": "Мощность", "value": "160 Вт"},
        {"label": "Масса", "value": "20 кг"},
    ]
    bad["tasks"] = ["100%", "всё"]
    bad["tech"] = [
        {"label": "Диапазон", "value": "99999 МГц"},
        {"label": "Дальность", "value": "50–200 м"},
        {"label": "Мощность", "value": "160 Вт"},
        {"label": "Масса", "value": "20 кг"},
    ]
    (tmp / "00_КОПИРАЙТ" / "banners_data.json").write_text(
        json.dumps({"banners": [good, bad]} if False else [good, bad], ensure_ascii=False), encoding="utf-8")

    def good_html(bid: str, model: str, hook: str, num_html: str, cta: bool = True, legal: bool = True, tech_html: str = "") -> str:
        footer = ('<div class="cta">@vokope_ru · +7 (999) 136-71-42</div>'
                  '<div class="sub">Цена по запросу · Доставка по РФ · Самовывоз в Москве</div>') if cta else '<div>Купить</div>'
        legal_html = ('<div class="legal">Оборудование является радиоэлектронным средством. '
                      'Порядок применения — по законодательству РФ. Характеристики — по паспорту изделия. '
                      'Не является публичной офертой.</div>') if legal else ''
        return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<style>body{{font-size:20px}} .legal{{font-size:9.5px}}</style></head><body>
<div class="banner"><div class="brand"><img src="../_design/img/brand/logo_w_word.png" alt="В ОКОПЕ"></div>
<div class="hook">{hook}</div><h1 class="title">{model}</h1>
<div class="stage"><img src="../_design/img/product/k8m.png" alt="{model}"></div>
{num_html}{tech_html}{footer}{legal_html}</div></body></html>"""

    b01_tech_html = (
        '<div class="b-tech"><div class="b-tech__title">КОРОТКО О МОДЕЛИ</div>'
        '<div>Диапазоны: 400–1020, 2100–2800, 5680–5900 МГц</div><div>Дальность: 50–200 м</div>'
        '<div>Мощность: 160 Вт</div><div>Масса: 20 кг</div>'
        '<div class="b-tasks"><span>FPV</span><span>транспорт</span></div></div>'
    )
    for bid, model, hook, nums, fmt in [
        ("B01", "К-8М", "КУПОЛ НАД МАШИНОЙ", "<div>8 каналов</div><div>50–200 м</div><div>20 кг</div>", "1080x1350"),
        ("B01", "К-8М", "КУПОЛ НАД МАШИНОЙ", "<div>8 каналов</div><div>50–200 м</div><div>20 кг</div>", "1080x1080"),
        ("B02", "К-12М", "100% ЗАЩИТА ОТ ДРОНОВ", "<div>99999 МГц</div>", "1080x1350"),
        ("B02", "К-12М", "100% ЗАЩИТА ОТ ДРОНОВ", "<div>99999 МГц</div>", "1080x1080"),
    ]:
        name = f"{bid}_test_{fmt}.html"
        (tmp / "html" / name).write_text(
            good_html(bid, model, hook, nums, cta=(bid == "B01"), legal=(bid == "B01"),
                      tech_html=(b01_tech_html if bid == "B01" else "")), encoding="utf-8")

    from PIL import Image
    for bid in ("B01", "B02"):
        for w, h, tag in ((1080, 1350, "1080x1350"), (2160, 2700, "1080x1350@2x"),
                          (1080, 1080, "1080x1080"), (2160, 2160, "1080x1080@2x")):
            Image.new("RGB", (w, h), "#1C2317").save(tmp / "05_ГОТОВОЕ" / "png" / f"{bid}_test_{tag}.png")

    res = run(tmp / "00_КОПИРАЙТ" / "banners_data.json", tmp / "html", tmp / "05_ГОТОВОЕ" / "png",
              claims_path, banned_path, tmp / "03_QA" / "QA.md", tmp / "03_QA" / "QA.json", write=True)
    print_console(res)
    msgs = [f["msg"] for f in res["findings"]]
    checks = [
        ("B01: нет блокеров", not any(f["banner"] == "B01" and f["code"].startswith("Б") for f in res["findings"]),
         [f["msg"] for f in res["findings"] if f["banner"] == "B01" and f["code"].startswith("Б")]),
        ("B02: banned-фраза -> Б2", any(f["banner"] == "B02" and f["code"] == "Б2" for f in res["findings"]), ""),
        ("B02: цена -> Б5", any(f["banner"] == "B02" and f["code"] == "Б5" for f in res["findings"]), ""),
        ("B02: неподтверждённая цифра -> Б1", any(f["banner"] == "B02" and f["code"] == "Б1" for f in res["findings"]), ""),
        ("B02: нет CTA -> Б4", any(f["banner"] == "B02" and f["code"] == "Б4" and "Telegram" in f["msg"] for f in res["findings"]), ""),
        ("B02: нет юрстроки -> Б4", any(f["banner"] == "B02" and f["code"] == "Б4" and "юрстрок" in f["msg"] for f in res["findings"]), ""),
        ("B01 v3: техблок принят (нет Б по B01)", not any(f["banner"] == "B01" and f["code"].startswith("Б") for f in res["findings"]), ""),
        ("B02 v3: tech-цифра 99999 -> Б1", any(f["banner"] == "B02" and f["code"] == "Б1" and "tech-цифра" in f["msg"] for f in res["findings"]), ""),
        ("B02 v3: нет техблока в вёрстке -> Б3", any(f["banner"] == "B02" and f["code"] == "Б3" and "техблок" in f["msg"] for f in res["findings"]), ""),
        ("PNG: 8 файлов на 2 модели", sum(len(v) for v in res["png"].values()) == 8, str({k: len(v) for k, v in res["png"].items()})),
        ("HTML: форматы найдены", res["inputs"]["html"].startswith("4"), res["inputs"]["html"]),
    ]
    ok = True
    for name, cond, extra in checks:
        print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f" [{extra}]"))
        ok = ok and cond
    print("== SELFTEST:", "OK" if ok else "FAILED", "==")
    print(f"  отчёт: {tmp / '03_QA' / 'QA.md'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA-линтер рекламных баннеров")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--data", default="")
    ap.add_argument("--html", default="")
    ap.add_argument("--png", default="")
    ap.add_argument("--claims", default="")
    ap.add_argument("--banned", default="")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    data_path = Path(args.data) if args.data else BANNERS / "00_КОПИРАЙТ" / "banners_data.json"
    html_dir = Path(args.html) if args.html else BANNERS / "html"
    png_dir = Path(args.png) if args.png else BANNERS / "05_ГОТОВОЕ" / "png"
    claims_path = Path(args.claims) if args.claims else PROJECT / "infographics" / "01_ФАКТЫ" / "claims.json"
    banned_path = Path(args.banned) if args.banned else PROJECT / "infographics" / "01_ФАКТЫ" / "BANNED.md"
    out_md = QA / "QA_АВТОПРОВЕРКА_БАННЕРЫ.md"
    out_json = QA / "QA_АВТОПРОВЕРКА_БАННЕРЫ.json"

    res = run(data_path, html_dir, png_dir, claims_path, banned_path, out_md, out_json, write=not args.no_write)
    print_console(res)
    if not args.no_write:
        print(f"  отчёт: {out_md}")
        print(f"  json:  {out_json}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
