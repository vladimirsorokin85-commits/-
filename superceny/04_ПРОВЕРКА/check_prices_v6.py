#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_prices_v6.py — QA цен v6 «СУПЕРЦЕНЫ»: сверка с прайсом заказчика (xlsx).

Источник истины: D:\\zagruzki\\Входы_Завод_и_ЛО_2026-11-12.xlsx, лист «Входы»,
колонка «Розница, ₽». 18 позиций с ценой; 19 Сигнал-М2 и 20 РЭБ-тестер — без цены
(«Прайс по запросу»).

Проверяет:
  1) эталон: xlsx → 18 цен (суммы, разряды); сопоставление с позициями 01–18.
  2) positions.json: price_value / price_display / has_price.
  3) HTML 81: цена на 01/03/04, НЕТ цифры на 02, «Прайс по запросу» у 19/20,
     канонический формат «320 000 ₽» (группы по 3, без ₽₽/000-мусора),
     нет выдуманных скидок/старых цен, «розница, ноябрь 2026».
  4) Читаемость: кегль/одна строка/в кадре/без обрезки (Chrome-замер), 1080/390.
  5) Hero: «от 198 000 ₽» (минимальная розница), без ошибочных сумм.

Выход: superceny\\04_ПРОВЕРКА\\QA_ЦЕНЫ_АВТОПРОВЕРКА.md/.json
Запуск: python check_prices_v6.py [--selftest|--no-write|--stage data|html|measure|all]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
QA = Path(__file__).resolve().parent
SC = QA.parent
XLSX = Path(r"D:\zagruzki\Входы_Завод_и_ЛО_2026-11-12.xlsx")
POSITIONS = SC / "01_ДАННЫЕ" / "positions.json"
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
EXPECTED_JSON = QA / "_tmp" / "prices_expected.json"

# сопоставление позиции (folder) → номер строки xlsx «№»
XLSX_MAP = {
    "01_Муха-К-8": 1, "02_ФПВ-7-КОМПАКТ": 2, "03_К-8М": 7, "04_К-12М": 8,
    "05_К-12М-Багажный-бокс": 9, "06_К-15М": 10, "07_К-15М-ВИП": 11,
    "08_Изделие-135-Багажный-бокс": 12, "09_Штора-К-12-700": 14,
    "10_Штора-М-К-8-600": 13, "11_Поле-31": 17, "12_Ребус-4": 15,
    "13_ТП-4-28А": 18, "14_ТП-4-28Б": 19, "15_ТП-4-50А": 20,
    "16_ТП-4-50Б": 21, "17_ТП-7-100": 22, "18_ТП-8-100": 23,
    # 19_Сигнал-М2 и 20_РЭБ-тестер — в прайсе нет
}
PRICE_CANON = "Прайс по запросу"
PROCESSED_SLIDES = ("01", "03", "04")
PRICE_LABEL_RE = re.compile(r"розниц\w*[,\s]*ноябр\w*\s*2026", re.I)
SKIP_RE = re.compile(r"скидк|старая\s+цена|было\s*:|экономия|выгоднее\s+на|%", re.I)
# канонический формат: группы по 3 через пробел/NBSP/thin, затем ₽
DOUBLE_CUR_RE = re.compile(r"₽\s*₽|руб\w*\.?\s*₽", re.I)
SP = " \u00a0\u202f\u2009\u200a\u2007"
PRICE_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[" + SP + r"]\d{3})+|\d+)\s*(₽|руб\.?)(?![\d])", re.U | re.I)


def read_xlsx() -> dict:
    """Возвращает {№: {'model': str, 'retail': int|None, 'input_zavod': int|None, 'input_lo': int|None}}."""
    try:
        import openpyxl
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"нет openpyxl: {exc}")
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Входы"] if "Входы" in wb.sheetnames else wb.worksheets[0]
    rows: dict = {}
    header_seen = False
    for r in ws.iter_rows(values_only=True):
        if not header_seen:
            vals = [str(c or "").strip().lower() for c in r]
            if any("№" == v for v in vals) or any("розница" in v for v in vals):
                header_seen = True
            continue
        num, model = r[0], r[1]
        if num is None or model is None:
            continue
        try:
            n = int(float(str(num).replace(",", ".")))
        except Exception:
            continue
        def to_int(x):
            if x is None or str(x).strip() == "":
                return None
            s = str(x).replace("\u00a0", "").replace(" ", "").replace("₽", "").replace(",", ".").strip()
            try:
                return int(round(float(s)))
            except Exception:
                return None
        rows[n] = {"model": str(model).strip(), "retail": to_int(r[4]),
                   "input_zavod": to_int(r[2]), "input_lo": to_int(r[3])}
    return rows


def build_expected(rows: dict) -> dict:
    return {
        "source": str(XLSX),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": {
            folder: {"xlsx_no": no, "xlsx_model": rows.get(no, {}).get("model"),
                     "retail": rows.get(no, {}).get("retail")}
            for folder, no in XLSX_MAP.items()
        },
        "unpriced": {"19_Сигнал-М2": None, "20_РЭБ-тестер": None},
    }


def fmt_price(value: int) -> str:
    return f"{value:,}".replace(",", "\u00a0") + " ₽"


def fmt_variants(value: int) -> list[str]:
    e = fmt_price(value)
    return [e, e.replace("\u00a0", " "), e.replace("\u00a0", "\u202f"), e.replace("\u00a0", "\u2009"), e.replace("\u00a0", "\u200a")]


def groups_ok(raw: str, value: int) -> bool:
    groups = [len(g) for g in re.findall(r"\d+", raw)]
    if len(groups) == 1:
        return len(str(value)) <= 3
    head = len(str(value)) - 3 * (len(groups) - 1)
    return groups[0] == head and all(g == 3 for g in groups[1:])


def is_canon_display(display: str, value: int) -> bool:
    d = (display or "").replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ").replace("\u200a", " ").strip()
    mm = re.fullmatch(r"(\d[\d ]*)\s*₽", d)
    if not mm:
        return False
    digits = re.sub(r"[^\d]", "", mm.group(1))
    if digits != str(value):
        return False
    groups = re.findall(r"\d+", mm.group(1))
    if len(groups) == 1:
        return True
    return all(len(g) == 3 for g in groups[1:]) and len(groups[0]) <= 3


def load_positions() -> list[dict]:
    import importlib.util as iu
    spec = iu.spec_from_file_location("cs_prices", QA / "check_superceny.py")
    cs = iu.module_from_spec(spec)
    sys.modules["cs_prices"] = cs
    spec.loader.exec_module(cs)
    pos, err = cs.load_positions()
    if pos is None:
        raise SystemExit(f"positions.json: {err}")
    return pos


def check_data(expected: dict, positions: list[dict]) -> tuple[list, dict]:
    import importlib.util as iu
    cs = sys.modules.get("cs_prices")
    findings: list = []
    stats = {"priced": 0, "unpriced": 0}
    by_folder = {str(p.get("folder") or ""): p for p in positions}
    for folder, want in expected["positions"].items():
        p = by_folder.get(folder)
        if not p:
            findings.append(cs.Finding("Б3", folder, "нет позиции в positions.json", str(POSITIONS)))
            continue
        exp = want["retail"]
        stats["priced"] += 1
        pv, pd, hp = p.get("price_value"), p.get("price_display"), p.get("has_price")
        if pv is None:
            findings.append(cs.Finding("Б1", folder, f"price_value не заполнен (ожидается {exp} ₽)", str(POSITIONS)))
        elif int(pv) != int(exp):
            findings.append(cs.Finding("Б1", folder, f"price_value {pv} ≠ прайс {exp} ₽", str(POSITIONS)))
        if pd and not is_canon_display(str(pd), int(exp)):
            findings.append(cs.Finding("З", folder, f"price_display «{pd}» ≠ канону «{fmt_price(int(exp))}»", str(POSITIONS)))
        if hp is False:
            findings.append(cs.Finding("З", folder, "has_price=false при наличии цены", str(POSITIONS)))
    for folder in expected["unpriced"]:
        p = by_folder.get(folder)
        if not p:
            continue
        stats["unpriced"] += 1
        if p.get("price_value") not in (None, ""):
            findings.append(cs.Finding("Б1", folder, f"у позиции нет цены в прайсе, а price_value={p.get('price_value')}", str(POSITIONS)))
        note = str(p.get("price_note") or "")
        if PRICE_CANON.lower() not in note.lower():
            findings.append(cs.Finding("З", folder, f"price_note «{note}» ≠ «{PRICE_CANON}»", str(POSITIONS)))
    stats["xlsx_rows"] = len(expected["positions"]) + len(expected["unpriced"])
    return findings, stats


def html_tree() -> tuple[dict, dict, list]:
    import importlib.util as iu
    spec = iu.spec_from_file_location("cs_html", QA / "check_superceny.py")
    cs = iu.module_from_spec(spec)
    sys.modules["cs_html"] = cs
    spec.loader.exec_module(cs)
    return cs.html_tree()


def check_html(expected: dict, positions: list[dict]) -> tuple[list, dict]:
    cs = sys.modules.get("cs_html")
    if cs is None:
        cards, hero, struct = html_tree()
        cs = sys.modules.get("cs_html")
    else:
        cards, hero, struct = cs.html_tree()
    findings: list = []
    findings.extend(struct)
    stats = {"html": 0, "price_occurrences": 0}
    by_folder = {str(p.get("folder") or ""): p for p in positions}
    folder_order = {}
    for folder in by_folder:
        mm = re.match(r"(\d{2})_", folder)
        if mm:
            folder_order[int(mm.group(1))] = folder
    exp_by_order = {int(folder[:2]): w for folder, w in expected["positions"].items()}
    unpriced_orders = {int(folder[:2]) for folder in expected["unpriced"]}
    for order in sorted(cards):
        folder = folder_order.get(order, "")
        name = cs.EXPECTED_BY_ORDER.get(order, {}).get("name", str(order))
        subj = f"{order:02d} {name}"
        slides = cards[order]
        texts = {idx: cs.card_text(p) for idx, p in slides.items()}
        stats["html"] += len(slides)
        want = exp_by_order.get(order)
        exp_price = int(want["retail"]) if want and want.get("retail") is not None else None
        # 19/20 — только «Прайс по запросу»
        if order in unpriced_orders:
            for idx in ("01", "04"):
                t = texts.get(idx, "")
                if idx == "04" and not cs.PRICE_RE.search(t):
                    findings.append(cs.Finding("Б4", f"{subj} {idx}", f"нет «{PRICE_CANON}»", str(slides.get(idx))))
                if idx == "01" and not cs.PRICE_RE.search(t):
                    findings.append(cs.Finding("З", f"{subj} {idx}", f"нет «{PRICE_CANON}» (позиция без цены)", str(slides.get(idx))))
            # цифр цены быть не должно
            for idx, t in texts.items():
                mm = PRICE_RE.search(t)
                if mm:
                    findings.append(cs.Finding("Б1", f"{subj} {idx}", f"цена {mm.group(0)} у позиции без цены", str(slides.get(idx))))
            continue
        if exp_price is None:
            continue
        # цена на 01/03/04
        for idx in PROCESSED_SLIDES:
            t = texts.get(idx, "")
            found = [m.group(0) for m in PRICE_RE.finditer(t)]
            nums = [re.sub(r"[^\d]", "", m.group(1)) for m in PRICE_RE.finditer(t)]
            if not found:
                lvl = "Б1" if idx in ("01", "04") else "З"
                findings.append(cs.Finding(lvl, f"{subj} {idx}", f"нет цены {fmt_price(exp_price)}", str(slides.get(idx))))
                continue
            if str(exp_price) not in nums:
                findings.append(cs.Finding("Б1", f"{subj} {idx}",
                                           f"цена {found[0]} ≠ прайс {fmt_price(exp_price)}", str(slides.get(idx))))
            else:
                stats["price_occurrences"] += 1
            # формат: разряды по 3 (тип пробела любой — NBSP/thin/обычный)
            for mm in PRICE_RE.finditer(t):
                raw = mm.group(1)
                if re.sub(r"[^0-9]", "", raw) == str(exp_price) and not groups_ok(raw, exp_price):
                    findings.append(cs.Finding("З", f"{subj} {idx}", f"неканонические разряды: «{raw}»", str(slides.get(idx))))
        # двойной знак валюты / опечатки
        for idx, t in texts.items():
            mm = DOUBLE_CUR_RE.search(t)
            if mm:
                findings.append(cs.Finding("Б2", f"{subj} {idx}", f"опечатка валюты: «{mm.group(0)}»", str(slides.get(idx))))
        # 02 — без цифры цены
        t2 = texts.get("02", "")
        if PRICE_RE.search(t2):
            findings.append(cs.Finding("Б1", f"{subj} 02", f"на 02 есть цифра цены {PRICE_RE.search(t2).group(0)} — обрывок должен быть без цифры", str(slides.get("02"))))
        t4 = texts.get("04", "")
        if not PRICE_LABEL_RE.search(t4):
            findings.append(cs.Finding("З", subj, "на 04 нет «розница, ноябрь 2026»", str(slides.get("04"))))
        # выдуманные скидки
        for idx, t in texts.items():
            m = SKIP_RE.search(t)
            if m:
                findings.append(cs.Finding("Б2", f"{subj} {idx}", f"выдуманная скидка/акция: «{m.group(0)}»", str(slides.get(idx))))
    # hero: «от 198 000 ₽» (минимум) и без чужих сумм
    hero_min = min(int(w["retail"]) for w in expected["positions"].values() if w.get("retail"))
    for key, p in hero.items():
        t = cs.card_text(p)
        nums = [re.sub(r"[^\d]", "", m.group(1)) for m in PRICE_RE.finditer(t)]
        if not nums:
            findings.append(cs.Finding("Б4", "hero", "нет цены/«от … ₽» в hero", str(p)))
        elif str(hero_min) not in nums:
            findings.append(cs.Finding("Б1", "hero", f"в hero нет минимальной розницы {fmt_price(hero_min)} (найдено {nums})", str(p)))
        else:
            extra = "" if nums[0] == str(hero_min) else f" (выбранная «от» = {nums[0]}, фактический минимум = {hero_min})"
            findings.append(cs.Finding("И", "hero", f"цена «от {nums[0]}» в hero подтверждена{extra}", str(p)))
        for n in nums:
            if int(n) != hero_min and int(n) not in {int(w["retail"]) for w in expected["positions"].values() if w.get("retail")}:
                findings.append(cs.Finding("Б1", "hero", f"посторонняя сумма в hero: {n}", str(p)))
        if not re.search(r"от\s", cs.norm(t)):
            findings.append(cs.Finding("З", "hero", "нет слова «от» перед ценой", str(p)))
    return findings, stats


def check_measure(expected: dict, positions: list[dict]) -> tuple[list, dict]:
    """Chrome-замер: цена одна строка, в кадре, не обрезана; 04 крупно; 390 масштаб читаем."""
    import importlib.util as iu
    findings: list = []
    stats: dict = {}
    try:
        spec = iu.spec_from_file_location("cl_prices", QA / "check_superceny_layout.py")
        cl = iu.module_from_spec(spec)
        sys.modules["cl_prices"] = cl
        spec.loader.exec_module(cl)
    except Exception as exc:
        return [sys.modules["cs_html"].Finding("И", "measure", f"замер недоступен: {exc}", str(QA))], {}
    tmp = QA / "_tmp" / "layout_prices"
    tmp.mkdir(parents=True, exist_ok=True)
    cards, hero, _ = sys.modules["cs_html"].html_tree() if "cs_html" in sys.modules else html_tree()
    exp_by_folder = expected["positions"]
    min_widths = {}
    for order, slides in sorted(cards.items()):
        folder = next((f for f in exp_by_folder if f.startswith(f"{order:02d}_")), None)
        if not folder:
            continue
        want = exp_by_folder[folder]
        price = want.get("retail")
        if price is None:
            continue
        canon = fmt_price(int(price)).split(" ₽")[0]
        for idx in ("01", "04"):
            p = slides.get(idx)
            if not p:
                continue
            try:
                payload = cl.measure(p, (1080, 1350), tmp)
            except Exception as exc:
                findings.append(sys.modules["cs_html"].Finding("И", f"{order:02d} {idx}", f"замер: {exc}", str(p)))
                continue
            items = payload.get("items") or []
            def price_in(text):
                for mm in PRICE_RE.finditer(text or ""):
                    if re.sub(r"[^0-9]", "", mm.group(1)) == str(price):
                        return True
                return False
            hits = [it for it in items if price_in(it.get("text") or "")]
            if not hits:
                findings.append(sys.modules["cs_html"].Finding("Б1", f"{order:02d} {idx}", f"в замере нет элемента с ценой «{canon}» (возможна обрезка/перенос)", str(p)))
                continue
            it = max(hits, key=lambda x: x["fs"])
            fs = it["fs"]
            box = it.get("bbox") or {}
            w = box.get("w") or 0
            x = box.get("x") or 0
            stats.setdefault("prices", []).append({"order": order, "slide": idx, "fs": fs, "text": it.get("text")})
            need_fs = 44 if idx == "04" else 20
            if fs < need_fs:
                findings.append(sys.modules["cs_html"].Finding("З", f"{order:02d} {idx}", f"цена {fs:.0f}px < {need_fs}px", str(p)))
            if x + w > 1082 or x < -2:
                findings.append(sys.modules["cs_html"].Finding("Б3", f"{order:02d} {idx}", f"цена выходит за кадр: x={x:.0f}, w={w:.0f}", str(p)))
            # одна строка: высота bbox ≈ кегль*1.4
            h = box.get("h") or 0
            if h > fs * 1.9:
                findings.append(sys.modules["cs_html"].Finding("Б3", f"{order:02d} {idx}", f"цена в 2+ строки (h={h:.0f}, fs={fs:.0f})", str(p)))
            # 390-читаемость: масштаб
            scaled = fs * 390 / 1080
            if idx == "04" and scaled < 16:
                findings.append(sys.modules["cs_html"].Finding("З", f"{order:02d} {idx}", f"на 390 цена {scaled:.0f}px (<16)", str(p)))
            min_widths.setdefault(idx, []).append(w)
    stats["min_price_width"] = {k: min(v) for k, v in min_widths.items() if v}
    return findings, stats


def build_report(generated: str, findings: list, stats: dict, expected: dict) -> str:
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    L = ["# QA ЦЕНЫ v6 — сверка с прайсом заказчика", "",
         f"**Сгенерировано:** {generated} · чекер v{VERSION} · источник: `{expected['source']}`", "",
         f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}", ""]
    L += ["## 1. Эталон (xlsx «Розница, ₽»)", "",
          "| № | Позиция | Модель в прайсе | Розница, ₽ |", "|---|---|---|---|"]
    for folder, w in expected["positions"].items():
        L.append(f"| {folder[:2]} | {folder[3:]} | {w.get('xlsx_model')} | {fmt_price(int(w['retail'])) if w.get('retail') is not None else '—'} |")
    for folder in expected["unpriced"]:
        L.append(f"| {folder[:2]} | {folder[3:]} | нет в прайсе | «{PRICE_CANON}» |")
    L += ["", "## 2. Блокеры", ""]
    if B:
        for f in B:
            L.append(f"- **[{f.code}] {f.subject}** — {f.msg}" + (f"  \n  `{f.path}`" if f.path else ""))
    else:
        L.append("Нет.")
    L += ["", "## 3. Замечания", ""]
    if Z:
        for f in Z[:80]:
            L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
        if len(Z) > 80:
            L.append(f"- … ещё {len(Z) - 80} (см. json)")
    else:
        L.append("Нет.")
    L += ["", "## 4. Инфо", ""]
    for f in I:
        L.append(f"- [{f.code}] {f.subject} — {f.msg}")
    w = stats.get("min_price_width") or {}
    L += ["", "## 5. Замер цен (Chrome)", "",
          f"- проверено вхождений: {stats.get('price_occurrences', 0)}; замеров 01/04: {len(stats.get('prices') or [])}",
          f"- минимальная ширина блока цены: 01 — {w.get('01', '—')}px, 04 — {w.get('04', '—')}px (порог 1080 — в кадре)", ""]
    L += ["## 6. Как воспроизвести", "",
          "```powershell",
          "$py = \"C:\\Users\\TitanPC\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe\"",
          "cd \"D:\\Проекты Дипсик\\В ОКОПЕ\\superceny\\04_ПРОВЕРКА\"",
          "& $py check_prices_v6.py --selftest",
          "& $py check_prices_v6.py",
          "```"]
    return "\n".join(L) + "\n"


def run(stage: str = "all", write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    findings: list = []
    stats: dict = {}
    rows = read_xlsx()
    expected = build_expected(rows)
    stats["xlsx_rows_total"] = len(rows)
    if stage in ("all", "data"):
        df, ds = check_data(expected, load_positions())
        findings.extend(df)
        stats.update(ds)
        EXPECTED_JSON.parent.mkdir(parents=True, exist_ok=True)
        EXPECTED_JSON.write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    if stage in ("all", "html"):
        hf, hs = check_html(expected, load_positions())
        findings.extend(hf)
        stats.update(hs)
    if stage in ("all", "measure"):
        mf, ms = check_measure(expected, load_positions())
        findings.extend(mf)
        stats.update(ms)
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
              "findings": [{"code": f.code, "subject": f.subject, "msg": f.msg, "path": f.path} for f in findings]}
    md = build_report(generated, findings, stats, expected)
    if write:
        QA.mkdir(parents=True, exist_ok=True)
        (QA / "QA_ЦЕНЫ_АВТОПРОВЕРКА.md").write_text(md, encoding="utf-8")
        (QA / "QA_ЦЕНЫ_АВТОПРОВЕРКА.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_md"] = md
    return result


def selftest() -> int:
    print("== SELFTEST check_prices_v6.py ==")
    ok = True
    # эталон: xlsx читается, 18 позиций, суммы
    rows = read_xlsx()
    exp = build_expected(rows)
    checks = [
        ("xlsx: 24 модели", len(rows) == 24),
        ("18 позиций с ценой", len(exp["positions"]) == 18),
        ("К-8М = 320 000", rows[7]["retail"] == 320000),
        ("Ребус-4 = 5 600 000", rows[15]["retail"] == 5600000),
        ("Муха К-8 = 198 000 (мин)", rows[1]["retail"] == 198000),
        ("ТП 4-28Б = 120 000", rows[19]["retail"] == 120000),
        ("формат 320 000 ₽", fmt_price(320000).startswith("320\u00a0000")),
        ("варианты пробелов", len(fmt_variants(5600000)) >= 3),
    ]
    # формат-чеки
    checks += [
        ("regex ловит канон", bool(PRICE_RE.search("320\u00a0000 ₽"))),
        ("regex ловит обычный пробел", bool(PRICE_RE.search("5 600 000 ₽"))),
        ("regex ловит двойной ₽", bool(DOUBLE_CUR_RE.search("320000₽₽"))),
        ("нет скидок в эталоне", not SKIP_RE.search("розница, ноябрь 2026")),
    ]
    for name, cond in checks:
        print(("  PASS " if cond else "  FAIL ") + name)
        ok = ok and cond
    print("== SELFTEST:", "OK" if ok else "FAILED", "==")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA цен v6: сверка с прайсом заказчика")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--stage", default="all", choices=["all", "data", "html", "measure"])
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    res = run(stage=args.stage, write=not args.no_write)
    s = res["summary"]
    print(f"check_prices_v6 v{VERSION}: {res['generated']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    print(f"  эталон: {res['stats'].get('priced', 0)} с ценой, {res['stats'].get('unpriced', 0)} без цены; "
          f"HTML {res['stats'].get('html', 0)}, вхождений цены {res['stats'].get('price_occurrences', 0)}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['subject']}: {f['msg']}")
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_ЦЕНЫ_АВТОПРОВЕРКА.md'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
