# -*- coding: utf-8 -*-
"""Приёмка файлов пакета рекламных баннеров: PNG 1×/2×, PDF A4 19 стр., галерея, превью.

Пишет banners/05_ГОТОВОЕ/ЧЕК_ЛИСТ_ФАЙЛОВ.md и banners/_render/_qa/files_report.json.
Ожидание: 18 моделей × 2 формата × 2 масштаба = 72 PNG; PDF = 1 + 18 = 19 страниц.
--partial: неполный набор — не FAIL (промежуточная сборка).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import bannerlib as L
from verify_pdf import verify as verify_pdf


def scan_pngs() -> dict[tuple[str, str, int], Path]:
    found: dict[tuple[str, str, int], Path] = {}
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        stem = p.stem
        scale = 2 if stem.endswith("@2x") else 1
        base = stem[:-3] if scale == 2 else stem
        _, fmt, pid = L.classify(base)
        if fmt and pid:
            found.setdefault((pid, fmt, scale), p)
    return found


def check_png(path: Path, fmt: str, scale: int) -> dict:
    r = {"file": path.name, "exists": path.is_file(), "dims": None, "bytes": 0,
         "mode": None, "status": "OK", "issues": [], "rendered_at": ""}
    if not path.is_file():
        r["status"] = "FAIL"
        r["issues"].append("нет файла")
        return r
    r["bytes"] = path.stat().st_size
    r["rendered_at"] = time.strftime("%d.%m %H:%M:%S", time.localtime(path.stat().st_mtime))
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            r["dims"] = im.size
            r["mode"] = im.mode
    except Exception as e:
        r["status"] = "FAIL"
        r["issues"].append(f"битый PNG: {e}")
        return r
    w, h = L.fmt_size(fmt)
    exp = (w * scale, h * scale)
    if r["dims"] != exp:
        r["status"] = "FAIL"
        r["issues"].append(f"размер {r['dims'][0]}×{r['dims'][1]}, ожидался {exp[0]}×{exp[1]}")
    if r["bytes"] < L.MIN_PNG_BYTES:
        r["status"] = "FAIL"
        r["issues"].append(f"вес {L.human_size(r['bytes'])} < 50 КБ")
    if r["mode"] != "RGB":
        r["status"] = "FAIL" if r["status"] == "FAIL" else "WARN"
        r["issues"].append(f"mode={r['mode']} (ожидался RGB)")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--json", default=str(L.QA_DIR / "files_report.json"))
    ap.add_argument("--md", default=str(L.OUT_DIR / "ЧЕК_ЛИСТ_ФАЙЛОВ.md"))
    a = ap.parse_args()

    fails = warns = 0
    data = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "png": {}, "issues": []}
    md = []

    def add(status: str, text: str):
        nonlocal fails, warns
        if status == "FAIL":
            fails += 1
        elif status == "WARN":
            warns += 1
        data["issues"].append({"status": status, "text": text})

    # --- PNG 1×/2× ---
    pngs = scan_pngs()
    expected_total = 72 + 12   # 18×(poster+square)×2 масштаба + 6 сторис×2
    # ожидаемые имена по текущим HTML (устаревшие/переименованные — из ignored_html.txt)
    ignored = L.ignored_html()
    expected_names = set()
    for d in (L.HTML_DIR, L.STORY_DIR):
        if not d.is_dir():
            continue
        for p in d.glob("*.html"):
            if p.name in ignored:
                continue
            base, fmt, pid = L.classify(p.stem)
            if fmt:
                for sc in (1, 2):
                    expected_names.add(L.output_name(p.stem, sc))
    extra = sorted(p.name for p in L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []
    extra = [n for n in extra if n not in expected_names]
    data["expected_png_names"] = len(expected_names)
    data["extra_png"] = extra
    if extra:
        add("FAIL", f"в 05_ГОТОВОЕ остались устаревшие/лишние PNG: {len(extra)} "
                    f"({', '.join(extra[:6])}{'…' if len(extra) > 6 else ''})")
    md.append("## PNG 1× и 2× по форматам\n")
    md.append(f"Ожидание: 18 моделей × 2 формата × 2 масштаба + 6 сторис × 2 = {expected_total} PNG. "
              f"Файлов по текущим HTML: {len(expected_names)}; лишних в папке: {len(extra)}.\n")
    counts = {}
    for fmt in ("poster", "square", "story"):
        ids = L.ORDER if fmt != "story" else L.STORY_IDS
        exp_n = len(ids)
        md.append(f"### {L.FMT_LABEL[fmt]}\n")
        md.append("| ID | 1× файл | размер | вес | рендер | 2× файл | размер | вес | рендер | статус |")
        md.append("|---|---|---|---|---|---|---|---|---|---|")
        n_ok = 0
        for pid in ids:
            r1 = check_png(pngs[(pid, fmt, 1)], fmt, 1) if (pid, fmt, 1) in pngs else {
                "file": "—", "bytes": 0, "dims": None, "status": "FAIL", "issues": ["не отрендерен"],
                "rendered_at": ""}
            r2 = check_png(pngs[(pid, fmt, 2)], fmt, 2) if (pid, fmt, 2) in pngs else {
                "file": "—", "bytes": 0, "dims": None, "status": "FAIL", "issues": ["не отрендерен"],
                "rendered_at": ""}
            st = "OK" if r1["status"] == "OK" and r2["status"] == "OK" else (
                "FAIL" if "FAIL" in (r1["status"], r2["status"]) else "WARN")
            for rr, scale in ((r1, 1), (r2, 2)):
                for iss in rr["issues"]:
                    if iss == "не отрендерен":
                        add("WARN" if a.partial else "FAIL", f"{pid} {fmt} {scale}×: не отрендерен")
                    else:
                        add(rr["status"], f"{pid} {fmt} {scale}× {rr['file']}: {iss}")
            if st == "OK":
                n_ok += 1
            d1 = f"{r1['dims'][0]}×{r1['dims'][1]}" if r1["dims"] else "—"
            d2 = f"{r2['dims'][0]}×{r2['dims'][1]}" if r2["dims"] else "—"
            md.append(f"| {pid} | {r1['file']} | {d1} | {L.human_size(r1['bytes']) if r1['bytes'] else '—'} | "
                      f"{r1.get('rendered_at') or '—'} | {r2['file']} | {d2} | "
                      f"{L.human_size(r2['bytes']) if r2['bytes'] else '—'} | {r2.get('rendered_at') or '—'} | {st} |")
            data["png"][f"{pid}_{fmt}"] = {"one": r1, "two": r2}
        counts[fmt] = n_ok
        md.append("")
    missing_total = expected_total - sum(2 * c for c in counts.values())
    md.append(f"**Готово пар 1×/2×: посты {counts['poster']}/18, квадраты {counts['square']}/18, "
              f"сторис {counts['story']}/6; PNG: {len(pngs)}/{expected_total}.**\n")

    # --- превью ---
    prevs = sorted(L.PREVIEW_DIR.glob("*.jpg")) if L.PREVIEW_DIR.is_dir() else []
    md.append("## Превью JPG (ширина 1080, q88)\n")
    exp_prev = 42
    st = "OK"
    if len(prevs) < exp_prev:
        st = "WARN" if a.partial else "FAIL"
        add(st, f"превью: {len(prevs)}/{exp_prev}")
    for p in prevs:
        try:
            from PIL import Image
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                im.load()
                dims = im.size
            # в превью важна ширина (1080), высота зависит от формата (1350/1080)
            if dims[0] > 1080 or p.stat().st_size < L.MIN_JPG_BYTES:
                st2 = "FAIL"
                add("FAIL", f"превью {p.name}: {dims[0]}×{dims[1]}, {L.human_size(p.stat().st_size)}")
            else:
                st2 = "OK"
        except Exception as e:
            st2 = "FAIL"
            add("FAIL", f"превью {p.name}: {e}")
    if prevs:
        md.append(f"- {len(prevs)} JPG (ширина ≤1080, q88) — {st}")
    else:
        md.append("- _нет_")
    md.append("")

    # --- PDF ---
    md.append("## PDF-альбом A4\n")
    n_poster = len([1 for (pid, fmt, sc) in pngs if fmt == "poster" and sc == 1])
    expect_pages = 1 + n_poster
    pdf = verify_pdf(L.PDF_PATH, expect_pages)
    data["pdf"] = pdf
    if not pdf["exists"]:
        add("WARN" if a.partial else "FAIL", "PDF не собран")
        md.append("_PDF не собран._")
    else:
        st = "OK" if pdf["ok"] else "FAIL"
        for iss in pdf["issues"]:
            add("FAIL", f"PDF: {iss}")
        mt = time.strftime("%d.%m %H:%M:%S", time.localtime(L.PDF_PATH.stat().st_mtime))
        md.append("| файл | страниц | вес | шрифты | собран | статус |")
        md.append("|---|---|---|---|---|---|")
        md.append(f"| {L.PDF_NAME} | {pdf['pages']} (ожидалось {expect_pages}) | {L.human_size(pdf['bytes'])} | "
                  f"Type3-контуры: {pdf['fonts_type3']}; встроенных: {pdf['fonts_embedded']} | {mt} | {st} |")
    md.append("")

    # --- галерея ---
    md.append("## Галерея\n")
    gal = L.GALLERY_DIR / "index.html"
    if gal.is_file():
        text = gal.read_text(encoding="utf-8", errors="replace")
        missing_ids = [pid for pid in L.ORDER if pid not in text]
        missing_story = [pid for pid in L.STORY_IDS if pid not in text]
        st = "OK"
        if missing_ids or missing_story:
            st = "FAIL" if not a.partial else "WARN"
            if missing_ids:
                add(st, f"галерея: нет моделей {', '.join(missing_ids)}")
            if missing_story:
                add(st, f"галерея: нет сторис {', '.join(missing_story)}")
        if "Сторис" not in text:
            add(st, "галерея: нет секции сторис")
        if gal.stat().st_size < 3000:
            add("FAIL", "галерея: подозрительно маленький index.html")
            st = "FAIL"
        md.append(f"- `05_ГОТОВОЕ/gallery/index.html` — {L.human_size(gal.stat().st_size)}, "
                  f"моделей: {18 - len(missing_ids)}/18, сторис: {6 - len(missing_story)}/6 — {st}")
        data["gallery"] = {"bytes": gal.stat().st_size, "status": st}
    else:
        add("FAIL", "галерея не собрана")
        md.append("- _нет_")
    md.append("")

    # --- QA-артефакты ---
    cs = L.QA_DIR / "contact_sheet.jpg"
    md.append("## QA-артефакты\n")
    if cs.is_file():
        md.append(f"- контактный лист: `_render/_qa/contact_sheet.jpg` ({L.human_size(cs.stat().st_size)})")
    else:
        add("WARN", "нет контактного листа")
        md.append("- _контактного листа нет_")
    md.append("- отчёт рендера: `_render/_qa/render_report.json`\n- отчёт PDF: `_render/_qa/pdf_report.json`\n"
              "- скриншоты PDF: `_render/_qa/pdf_pages/`\n")

    problems = [i for i in data["issues"] if i["status"] != "OK"]
    status_word = "OK" if fails == 0 else "ЕСТЬ ПРОБЛЕМЫ"
    head = [
        "# Чек-лист файлов пакета «Рекламные баннеры Киловатт»",
        "",
        f"**Дата проверки:** {time.strftime('%d.%m.%Y %H:%M')}  ",
        "**Пакет:** рекламные баннеры · НПО «Киловатт» × магазин «В ОКОПЕ» · ноябрь 2026  ",
        "**Проверено скриптом:** `banners/_render/check_files.py`  ",
        f"**Итог:** {status_word} · FAIL: {fails} · WARN: {warns}",
        "",
        "## Состав",
        "",
        f"- Посты 1080×1350: {counts['poster']}/18 (PNG 1× и 2×)",
        f"- Квадраты 1080×1080: {counts['square']}/18 (PNG 1× и 2×)",
        f"- Сторис 1080×1920: {counts['story']}/6 (PNG 1× и 2×)",
        f"- Всего PNG: {len(pngs)}/{expected_total}",
        f"- JPG-превью: {len(prevs)}/{exp_prev}",
        f"- PDF: {'есть, ' + str(pdf['pages']) + ' стр.' if pdf['exists'] else 'нет'}",
        f"- Галерея: {'есть' if gal.is_file() else 'нет'}",
        "",
    ]
    tail = ["## Что осталось / проблемы", ""]
    if problems:
        for i in problems:
            tail.append(f"- **{i['status']}** — {i['text']}")
    else:
        tail.append("- Проблем нет: все обязательные файлы на месте и валидны.")
    tail += ["", "## Как перерендерить", "",
             "```powershell",
             "powershell -NoProfile -ExecutionPolicy Bypass -File _render\\run_all.ps1",
             "# один баннер:",
             "& $py _render\\render_banners.py B01",
             "# PDF отдельно:",
             "powershell -NoProfile -ExecutionPolicy Bypass -File _render\\build_pdf.ps1",
             "```", "",
             "Источник правды: `banners/00_БРИФ_БАННЕРОВ.md` (§3 форматы, §6 сдача). Цены не публикуются.",
             ""]
    md_path = Path(a.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(head + md + tail), encoding="utf-8")
    json_path = Path(a.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Чек-лист: {md_path}")
    print(f"  PNG: {len(pngs)}/{expected_total} (посты {counts['poster']}/18, квадраты {counts['square']}/18, "
          f"сторис {counts['story']}/6), превью: {len(prevs)}/{exp_prev}")
    print(f"  PDF: {'есть, ' + str(pdf['pages']) + ' стр.' if pdf['exists'] else 'нет'}; галерея: {'есть' if gal.is_file() else 'нет'}")
    print(f"  ИТОГ: {'OK' if fails == 0 else 'ЕСТЬ ПРОБЛЕМЫ'} (FAIL {fails}, WARN {warns})")
    for i in problems:
        print(f"    [{i['status']}] {i['text']}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
