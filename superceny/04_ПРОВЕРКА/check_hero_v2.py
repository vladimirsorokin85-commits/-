#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_hero_v2.py — быстрая QA-проверка ТОЛЬКО hero под новый прайс (HQ #3, ВК 16.11).

Проверяет:
  1) Текст hero: «24 позиции прайса» / «24 позиции · розница 12.11.2026» /
     «цены из прайса 12.11.2026» / «ОТ 120 000 руб.»; отрицает «20 позиций»/«ноябрь 2026»/«198 000».
  2) PNG: 00_СУПЕРЦЕНЫ.png, 1080×1350, RGB, новее «до»-снимка, хэш изменился.
  3) Стиль/композиция: палитра бумага/тушь/красный без оливы/посторонних; брендинг/CTA/футер на месте.
  4) 390: копия пересобрана после cutoff; читаемость (визуально).

Выход: superceny\\04_ПРОВЕРКА\\QA_HERO_V2.md/.json
Запуск: python check_hero_v2.py [--after "2026-11-13 11:30:00"] [--no-write]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QA = Path(__file__).resolve().parent
SC = QA.parent
HTML = SC / "03_HTML" / "00_СУПЕРЦЕНЫ.html"
PNG = SC / "05_ГОТОВОЕ" / "00_СУПЕРЦЕНЫ.png"
PNG390 = SC / "_render" / "_qa" / "readability" / "390" / "00_СУПЕРЦЕНЫ.png"
BASELINE = QA / "_tmp" / "hero_v2_baseline.json"
BEFORE = QA / "_tmp" / "hero_v1_before.png"
DEFAULT_CUTOFF = "2026-11-13 11:30:00"

_spec = importlib.util.spec_from_file_location("v5hero", QA / "check_v5_design.py")
v5 = importlib.util.module_from_spec(_spec)
sys.modules["v5hero"] = v5
_spec.loader.exec_module(v5)
cs = v5.cs


def text_of(p: Path) -> str:
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", cs.read_text(p), flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", txt).strip()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(after_ts: float, write: bool = True) -> dict:
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.is_file() else {}
    findings: list = []
    stats: dict = {}
    txt = text_of(HTML) if HTML.is_file() else ""
    norm = txt.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    stats["text"] = txt[:800]
    # --- тексты ---
    checks = [
        ("24 позиции прайса", re.search(r"24\s+позиц\w*\s+прайса", norm, re.I) is not None),
        ("24 позиции · розница 12.11.2026", re.search(r"24\s+позиц\w*\s*[·•|]\s*розница\s+12\.11\.2026", norm, re.I) is not None),
        ("цены из прайса 12.11.2026", re.search(r"цены\s+из\s+прайса\s+12\.11\.2026", norm, re.I) is not None),
        ("ОТ 120 000 руб.", re.search(r"от\s+120\s*000\s*(?:руб\.?|₽)", norm, re.I) is not None),
        ("бренд/CTA @vokope_ru", "@vokope_ru" in norm),
        ("телефон +7 (999) 136-71-42", re.search(r"\+7\s*\(?999\)?\s*136[-\s]?71[-\s]?42", norm) is not None),
        ("«цены сорвали — спрашивай»", re.search(r"цену\s+сорвали", norm, re.I) is not None),
    ]
    for name, ok in checks:
        if not ok:
            findings.append(cs.Finding("З", "hero", f"нет/неверно: {name}", str(HTML)))
    bad_patterns = [
        (r"20\s+позиц", "устаревшее «20 позиций»"),
        (r"ноябр", "устаревшее «ноябрь 2026» (должно быть 12.11.2026)"),
        (r"198\s*000", "чужая сумма 198 000"),
    ]
    for pat, msg in bad_patterns:
        if re.search(pat, norm, re.I):
            findings.append(cs.Finding("З", "hero", f"в hero осталось {msg}", str(HTML)))
    # --- PNG ---
    try:
        from PIL import Image
        im = Image.open(PNG)
        stats["png_size"] = list(im.size)
        if im.size != (1080, 1350):
            findings.append(cs.Finding("Б3", "hero", f"PNG размер {im.size} ≠ 1080×1350", str(PNG)))
        if im.mode not in ("RGB", "RGBA"):
            findings.append(cs.Finding("З", "hero", f"PNG режим {im.mode}", str(PNG)))
    except Exception as exc:
        findings.append(cs.Finding("Б3", "hero", f"PNG не читается: {exc}", str(PNG)))
        return _finish(findings, stats, base, txt, write=False)
    stats["png_sha256"] = sha(PNG)
    stats["png_mtime"] = datetime.fromtimestamp(PNG.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    if base.get("png_sha256") and stats["png_sha256"] == base["png_sha256"]:
        findings.append(cs.Finding("З", "hero", "hero PNG не изменился (v2 не отрендерен?)", str(PNG)))
    if PNG.stat().st_mtime < after_ts:
        findings.append(cs.Finding("З", "hero", f"hero PNG старше cutoff ({stats['png_mtime']})", str(PNG)))
    # --- палитра / стиль ---
    try:
        pal_new = v5.classify_pixels(PNG)
        stats["palette_new"] = pal_new
        stats["palette_before"] = v5.classify_pixels(BEFORE) if BEFORE.is_file() else None
        if pal_new["olive"] > 0.03:
            findings.append(cs.Finding("Б2", "hero", f"олива {pal_new['olive']:.1%} >3%", str(PNG)))
        if pal_new["other"] > 0.09:
            findings.append(cs.Finding("З", "hero", f"посторонние цвета {pal_new['other']:.1%} >9%", str(PNG)))
        if pal_new["paper"] + pal_new["ink"] + pal_new["red"] < 0.70:
            findings.append(cs.Finding("З", "hero", f"покрытие 2 красок+бумаги {pal_new['paper'] + pal_new['ink'] + pal_new['red']:.0%} <70%", str(PNG)))
        b = stats["palette_before"]
        if b:
            diffs = {k: round(pal_new[k] - b[k], 4) for k in ("paper", "ink", "red", "olive", "other")}
            stats["palette_diff"] = diffs
            if abs(diffs["paper"]) > 0.08 or abs(diffs["red"]) > 0.06:
                findings.append(cs.Finding("И", "hero", f"палитра заметно сместилась: {diffs}", str(PNG)))
    except Exception as exc:
        findings.append(cs.Finding("И", "hero", f"палитра не посчиталась: {exc}", str(PNG)))
    # --- 390 ---
    stats["png390_exists"] = PNG390.is_file()
    if PNG390.is_file():
        stats["png390_mtime"] = datetime.fromtimestamp(PNG390.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if PNG390.stat().st_mtime < after_ts:
            findings.append(cs.Finding("И", "hero", f"390-копия не обновлена ({stats['png390_mtime']})", str(PNG390)))
    else:
        findings.append(cs.Finding("З", "hero", "нет 390-копии hero", str(PNG390)))
    return _finish(findings, stats, base, txt, write)


def _finish(findings: list, stats: dict, base: dict, txt: str, write: bool) -> dict:
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    res = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "summary": {"blockers": len(B), "warnings": len(Z), "infos": len(I)},
           "stats": stats, "findings": [cs.as_dict(f) for f in findings], "text": txt[:1200]}
    L = ["# QA HERO v2 — новый прайс (HQ #3)", "",
         f"**Сгенерировано:** {res['generated']} · проверяется только hero", "",
         f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}", ""]
    for f in findings:
        L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    if not findings:
        L.append("- Проблем нет.")
    L += ["", "## Текст hero", "", "```", txt[:1500], "```", "",
          "## Палитра", "",
          f"- новая: {stats.get('palette_new')}",
          f"- до: {stats.get('palette_before')}",
          f"- разница: {stats.get('palette_diff')}", "",
          "## PNG", "",
          f"- {stats.get('png_size')}, mtime {stats.get('png_mtime')}, sha {str(stats.get('png_sha256'))[:16]}…",
          f"- 390: {stats.get('png390_mtime', '—')}"]
    md = "\n".join(L) + "\n"
    if write:
        (QA / "QA_HERO_V2.md").write_text(md, encoding="utf-8")
        (QA / "QA_HERO_V2.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    res["_md"] = md
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA hero v2 (новый прайс)")
    ap.add_argument("--after", default=DEFAULT_CUTOFF)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    try:
        after_ts = datetime.strptime(args.after, "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        raise SystemExit(f"не понял --after: {args.after}")
    res = run(after_ts, write=not args.no_write)
    s = res["summary"]
    print(f"check_hero_v2: {res['generated']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    for f in res["findings"]:
        print(f"   [{f['code']}] {f['subject']}: {f['msg']}")
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_HERO_V2.md'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
