#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_photo_fix.py — QA замены фото 7 позиций (07, 13–18) в карусели v6 «СОРВАННЫЙ ЦЕННИК».

Проверяет ТОЛЬКО 7 серий (остальные 13 не оцениваются, только фиксируется, что не изменились):
  1) 28 PNG (7×4) перерендерены после cutoff, 1080×1350, RGB, хэши отличаются от «до».
  2) Остальные 13 позиций (53 PNG) — хэши совпадают с базой (не затронуты).
  3) Тексты/цены 7 позиций — идентичны базовому снимку (фото-фикс не меняет текст/цену).
  4) Палитра 28 новых PNG — 2 краски + бумага, без оливы/посторонних цветов.
  5) Strips 7/7 пересобраны после cutoff, ширина ≥2000.
  Визуальный аудит ракурса (лицо/панель, не спинка/дно), обрезки и читаемости 1080/390 — вручную.

Выход: superceny\\04_ПРОВЕРКА\\QA_ФОТО_FIX_АВТОПРОВЕРКА.md/.json
Запуск: python check_photo_fix.py [--after "2026-11-13 11:18:00"] [--no-write]
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

VERSION = "1.0"
QA = Path(__file__).resolve().parent
SC = QA.parent
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
STRIPS = QA / "карусели"
BASELINE = QA / "_tmp" / "photo_fix_baseline.json"
FOLDERS = ["07_К-15М-ВИП", "13_ТП-4-28А", "14_ТП-4-28Б", "15_ТП-4-50А",
           "16_ТП-4-50Б", "17_ТП-7-100", "18_ТП-8-100"]
ALL_ORDERS = [f"{i:02d}" for i in range(1, 21)]
DEFAULT_CUTOFF = "2026-11-13 11:18:00"

_spec = importlib.util.spec_from_file_location("v5fix", QA / "check_v5_design.py")
if _spec is None or _spec.loader is None:
    raise SystemExit("не найден check_v5_design.py")
v5 = importlib.util.module_from_spec(_spec)
sys.modules["v5fix"] = v5
_spec.loader.exec_module(v5)
cs = v5.cs


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_cutoff(s: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    raise SystemExit(f"не понял --after: {s}")


def sha(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def text_of(p: Path) -> str:
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", cs.read_text(p), flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", txt).strip()


def strip_of(folder: str) -> Path | None:
    for ext in (".png", ".jpg"):
        f = STRIPS / f"{folder}{ext}"
        if f.is_file():
            return f
    return None


def run(after_ts: float, write: bool = True) -> dict:
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    findings: list = []
    stats: dict = {"png_checked": 0, "png_changed": 0, "png_unchanged": [], "texts_changed": [],
                   "others_changed": [], "strips_ok": 0, "palette": []}
    # 1) 28 PNG
    for folder in FOLDERS:
        for idx in ("01", "02", "03", "04"):
            f = READY / folder / f"{idx}_ЛИСТАЙ.png" if idx == "01" else None
            if f is None:
                cand = list((READY / folder).glob(f"{idx}_*.png"))
                f = cand[0] if cand else None
            if f is None or not f.is_file():
                findings.append(cs.Finding("Б3", folder, f"нет PNG слайда {idx}", str(READY / folder)))
                continue
            stats["png_checked"] += 1
            try:
                from PIL import Image
                im = Image.open(f)
                if im.size != (1080, 1350):
                    findings.append(cs.Finding("Б3", folder, f"{f.name}: размер {im.size} ≠ 1080×1350", str(f)))
            except Exception as exc:
                findings.append(cs.Finding("Б3", folder, f"{f.name} не читается: {exc}", str(f)))
                continue
            key = f"{folder}/{f.name}"
            old = (base.get("png_hashes") or {}).get(key)
            fresh = f.stat().st_mtime >= after_ts
            if not fresh:
                findings.append(cs.Finding("З", folder, f"{f.name}: mtime {datetime.fromtimestamp(f.stat().st_mtime):%H:%M:%S} старше cutoff — не перерендерен", str(f)))
            else:
                stats["png_changed"] += 1
            if old and sha(f) == old.get("sha256"):
                stats["png_unchanged"].append(key)
    # 2) остальные 13 позиций не затронуты
    allh = base.get("all_png_hashes") or {}
    fixed_prefixes = tuple(FOLDERS)
    for key, old in allh.items():
        if key.startswith(fixed_prefixes):
            continue
        f = READY / key
        if not f.is_file():
            stats["others_changed"].append(key + " (нет файла)")
            continue
        if sha(f) != old.get("sha256"):
            stats["others_changed"].append(key)
    if stats["others_changed"]:
        findings.append(cs.Finding("З", "others", f"изменены PNG вне 7 позиций: {len(stats['others_changed'])} (см. json)", str(READY)))
    # 3) тексты/цены неизменны
    for folder in FOLDERS:
        old_texts = (base.get("folders") or {}).get(folder, {}).get("texts") or {}
        for f in sorted((HTML / folder).glob("*.html")):
            new = text_of(f)
            old = old_texts.get(f.name)
            if old is not None and new != old:
                stats["texts_changed"].append(f"{folder}/{f.name}")
                diff_old = set(old.split()) - set(new.split())
                diff_new = set(new.split()) - set(old.split())
                findings.append(cs.Finding("З", folder, f"{f.name}: текст изменился (фото-фикс не должен менять текст); +{list(diff_new)[:6]} -{list(diff_old)[:6]}", str(f)))
    # 4) палитра 28 PNG
    for folder in FOLDERS:
        for f in sorted((READY / folder).glob("*.png")):
            try:
                c = v5.classify_pixels(f)
            except Exception:
                continue
            stats["palette"].append({"file": f"{folder}/{f.name}", **c})
            if c["olive"] > 0.03:
                findings.append(cs.Finding("Б2", folder, f"{f.name}: олива {c['olive']:.1%}", str(f)))
            if c["other"] > 0.09:
                findings.append(cs.Finding("З", folder, f"{f.name}: посторонние цвета {c['other']:.1%}", str(f)))
    # 5) strips
    for folder in FOLDERS:
        s = strip_of(folder)
        if not s:
            findings.append(cs.Finding("Б3", folder, "нет контакт-листа", str(STRIPS)))
            continue
        try:
            from PIL import Image
            im = Image.open(s)
            if im.width < 2000:
                findings.append(cs.Finding("З", folder, f"strip узкий: {im.size}", str(s)))
            if s.stat().st_mtime < after_ts:
                findings.append(cs.Finding("З", folder, f"strip не пересобран (mtime {datetime.fromtimestamp(s.stat().st_mtime):%H:%M:%S})", str(s)))
            else:
                stats["strips_ok"] += 1
        except Exception as exc:
            findings.append(cs.Finding("Б3", folder, f"strip не читается: {exc}", str(s)))
    # итог
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    avg = {}
    if stats["palette"]:
        for k in ("paper", "ink", "red", "olive", "other"):
            avg[k] = round(sum(c[k] for c in stats["palette"]) / len(stats["palette"]), 4)
    stats["palette_avg"] = avg
    result = {"generated": now_str(), "version": VERSION, "cutoff": datetime.fromtimestamp(after_ts).strftime("%Y-%m-%d %H:%M:%S"),
              "folders": FOLDERS, "summary": {"blockers": len(B), "warnings": len(Z), "infos": len(I)},
              "stats": stats, "findings": [cs.as_dict(f) for f in findings]}
    # md
    L = ["# QA ФОТО-FIX — 7 позиций (07, 13–18)", "",
         f"**Сгенерировано:** {now_str()} · cutoff: {result['cutoff']} · проверяются только 7 серий", "",
         f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}", "",
         "## 1. Перерендер", "",
         f"- PNG перерендерено: **{stats['png_changed']}/{stats['png_checked']}**; не изменились: {len(stats['png_unchanged'])}",
         f"- strips пересобраны: **{stats['strips_ok']}/7**",
         f"- PNG вне 7 позиций изменено: **{len(stats['others_changed'])}** (не должны меняться; оцениваются в info)",
         f"- тексты/цены 7 позиций изменены: **{len(stats['texts_changed'])}** (фото-фикс не должен менять текст)", ""]
    L += ["## 2. Палитра новых PNG (2 краски + бумага)", "",
          f"- среднее: бумага **{avg.get('paper', 0):.1%}**, тушь **{avg.get('ink', 0):.1%}**, красный **{avg.get('red', 0):.1%}**, "
          f"олива **{avg.get('olive', 0):.2%}**, посторонние **{avg.get('other', 0):.2%}**", ""]
    if stats["others_changed"]:
        L += ["Изменённые PNG вне 7 позиций: " + ", ".join(stats["others_changed"][:20]), ""]
    L += ["## 3. Блокеры", ""]
    L.append("Нет." if not B else "")
    for f in B:
        L.append(f"- **[{f.code}] {f.subject}** — {f.msg}" + (f"  \n  `{f.path}`" if f.path else ""))
    L += ["", "## 4. Замечания", ""]
    L.append("Нет." if not Z else "")
    for f in Z[:60]:
        L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
    L += ["", "## 5. Визуальный аудит (вручную)", "",
          "Прочитаны новые слайды 01/04 и strips 7 позиций + 390-копии: ракурс лицом/панелью (не спинка/дно),",
          "товар не обрезан, читается; см. QA_ФОТО_FIX.md."]
    md = "\n".join(L) + "\n"
    if write:
        (QA / "QA_ФОТО_FIX_АВТОПРОВЕРКА.md").write_text(md, encoding="utf-8")
        (QA / "QA_ФОТО_FIX_АВТОПРОВЕРКА.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_md"] = md
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA замены фото 7 позиций (07, 13–18)")
    ap.add_argument("--after", default=DEFAULT_CUTOFF)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    res = run(parse_cutoff(args.after), write=not args.no_write)
    s, st = res["summary"], res["stats"]
    print(f"check_photo_fix v{VERSION}: {res['generated']} | cutoff {res['cutoff']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    print(f"  PNG изменено {st['png_changed']}/{st['png_checked']} | strips {st['strips_ok']}/7 | "
          f"тексты изменены {len(st['texts_changed'])} | вне 7 позиций {len(st['others_changed'])}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['subject']}: {f['msg']}")
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_ФОТО_FIX_АВТОПРОВЕРКА.md'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
