# -*- coding: utf-8 -*-
"""Приёмка файлов пакета «Два горизонта»: PNG, превью, PDF, галерея.
Пишет 05_ГОТОВОЕ/ЧЕК_ЛИСТ_ФАЙЛОВ.md и JSON _render/_qa/files_report.json.

Проверяет:
  · PNG основной серии 1×/2×: наличие, точные размеры, вес > 50 КБ, целостность, режим RGB;
  · широкие 1920×1080 и истории 1080×1920;
  · JPG-превью: ширина 1080, вес, открываются;
  · PDF: вес, число страниц (cover + постеры + финал), A4, вшитые шрифты, непустые страницы;
  · галерея: index.html существует, ссылается на все постеры, размер;
  · контактный лист QA (в _render/_qa).

Коды выхода: 0 — всё OK; 1 — есть FAIL; 2 — авария.
--partial: отсутствующие постеры считаются WARN (промежуточная сборка).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import posterlib as L
from verify_pdf import verify as verify_pdf


def check_png(path: Path, kind: str, scale: int) -> dict:
    r = {"file": path.name, "exists": path.is_file(), "dims": None, "bytes": 0,
         "status": "OK", "issues": []}
    if not path.is_file():
        r["status"] = "FAIL"
        r["issues"].append("нет файла")
        return r
    r["bytes"] = path.stat().st_size
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()          # verify — строго сразу после open
        with Image.open(path) as im:
            im.load()
            r["dims"] = im.size
            r["mode"] = im.mode
    except Exception as e:
        r["status"] = "FAIL"
        r["issues"].append(f"битый PNG: {e}")
        return r
    exp = L.expected_dims(kind, scale)
    if r["dims"] != exp:
        r["status"] = "FAIL"
        r["issues"].append(f"размер {r['dims'][0]}×{r['dims'][1]}, ожидался {exp[0]}×{exp[1]}")
    if r["bytes"] < L.MIN_PNG_BYTES:
        r["status"] = "FAIL"
        r["issues"].append(f"вес {L.human_size(r['bytes'])} < 50 КБ")
    if r.get("mode") != "RGB":
        r["status"] = "FAIL" if r["status"] == "FAIL" else "WARN"
        r["issues"].append(f"режим {r.get('mode')} (ожидался RGB, без alpha)")
    return r


def find_source_html(pid: str) -> Path | None:
    if not L.POSTERS_DIR.is_dir():
        return None
    for p in sorted(L.POSTERS_DIR.glob(f"{pid}_*.html")):
        return p
    return None


def find_main(scale: int) -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not L.PNG_DIR.is_dir():
        return found
    for p in L.PNG_DIR.glob("*.png"):
        stem, kind, sc = L.classify_png(p.name)
        if kind != "main" or sc != scale:
            continue
        pid = L.poster_id(stem)
        if pid and pid not in found:
            found[pid] = p
    return found


def find_extras() -> dict[str, Path]:
    found = {}
    if not L.PNG_DIR.is_dir():
        return found
    for p in L.PNG_DIR.glob("*.png"):
        stem, kind, sc = L.classify_png(p.name)
        if kind == "main":
            continue
        found[p.name] = p
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", action="store_true", help="промежуточная сборка: неполный набор — не FAIL")
    ap.add_argument("--json", default=str(L.QA_DIR / "files_report.json"))
    ap.add_argument("--md", default=str(L.OUT_DIR / "ЧЕК_ЛИСТ_ФАЙЛОВ.md"))
    a = ap.parse_args()

    fails = 0
    warns = 0
    md = []
    data = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "png": {}, "previews": [],
            "pdf": None, "gallery": None, "contact_sheet": None, "issues": []}

    def add(status: str, text: str):
        nonlocal fails, warns
        if status == "FAIL":
            fails += 1
        elif status == "WARN":
            warns += 1
        data["issues"].append({"status": status, "text": text})

    # ---------------- PNG основная серия ----------------
    one = find_main(1)
    two = find_main(2)
    md.append("## Основная серия 1080×1350 (PNG 1× и 2×)\n")
    md.append("| ID | 1× файл | размер | вес | рендер 1× | 2× файл | размер | вес | рендер 2× | статус |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for pid in L.ORDER_MAIN:
        r1 = check_png(one[pid], "main", 1) if pid in one else {
            "file": "—", "dims": None, "bytes": 0, "status": "FAIL", "issues": ["не отрендерен"]}
        r2 = check_png(two[pid], "main", 2) if pid in two else {
            "file": "—", "dims": None, "bytes": 0, "status": "FAIL", "issues": ["не отрендерен"]}
        st = "OK" if r1["status"] == "OK" and r2["status"] == "OK" else (
            "FAIL" if "FAIL" in (r1["status"], r2["status"]) else "WARN")
        if "не отрендерен" in r1["issues"]:
            add("FAIL", f"{pid}: 1× PNG не отрендерен")
        # устарел ли рендер относительно исходника
        src = find_source_html(pid)
        if src is not None and pid in one and src.stat().st_mtime > one[pid].stat().st_mtime + 1:
            add("WARN", f"{pid}: HTML новее PNG — нужен повторный рендер "
                        f"({src.name} {time.strftime('%d.%m %H:%M:%S', time.localtime(src.stat().st_mtime))})")
            if st == "OK":
                st = "WARN"
        for rr in (r1, r2):
            for iss in rr["issues"]:
                if iss != "не отрендерен":
                    add(rr["status"], f"{pid} {rr['file']}: {iss}")
        t1 = time.strftime("%d.%m %H:%M:%S", time.localtime(one[pid].stat().st_mtime)) if pid in one else "—"
        t2 = time.strftime("%d.%m %H:%M:%S", time.localtime(two[pid].stat().st_mtime)) if pid in two else "—"
        r1["rendered_at"], r2["rendered_at"] = t1, t2
        data["png"][pid] = {"one": r1, "two": r2}
        d1 = f"{r1['dims'][0]}×{r1['dims'][1]}" if r1["dims"] else "—"
        d2 = f"{r2['dims'][0]}×{r2['dims'][1]}" if r2["dims"] else "—"
        md.append(f"| {pid} | {r1['file']} | {d1} | {L.human_size(r1['bytes']) if r1['bytes'] else '—'} | {t1} | "
                  f"{r2['file']} | {d2} | {L.human_size(r2['bytes']) if r2['bytes'] else '—'} | {t2} | "
                  f"{'нет (ожидается)' if (a.partial and not r1['file'].endswith('.png')) else st} |")
    md.append("")

    # ---------------- широкие / истории ----------------
    extras = find_extras()
    wide = {n: p for n, p in extras.items() if "_1080x1920" not in n and "_1920" in n and "@2x" not in n}
    story = {n: p for n, p in extras.items() if "_1080x1920" in n}
    md.append("## Широкие 1920×1080 и истории 1080×1920\n")
    if wide or story:
        md.append("| файл | размер | вес | рендер | статус |")
        md.append("|---|---|---|---|---|")
        for kind, mapping in (("wide", wide), ("story", story)):
            for name, p in sorted(mapping.items()):
                rr = check_png(p, kind, 1)
                rr["rendered_at"] = time.strftime("%d.%m %H:%M:%S", time.localtime(p.stat().st_mtime))
                data["png"][name] = rr
                for iss in rr["issues"]:
                    add(rr["status"], f"{name}: {iss}")
                md.append(f"| {name} | {rr['dims'][0]}×{rr['dims'][1] if rr['dims'] else '—'} | "
                          f"{L.human_size(rr['bytes']) if rr['bytes'] else '—'} | {rr['rendered_at']} | {rr['status']} |")
    else:
        md.append("_Пока нет: широкие/истории — второй эшелон (бриф §4)._")
    md.append("")

    # ---------------- превью ----------------
    md.append("## Превью JPG (Telegram/GitHub, ширина 1080, q88)\n")
    prevs = sorted(L.PREVIEW_DIR.glob("*.jpg")) if L.PREVIEW_DIR.is_dir() else []
    if prevs:
        md.append("| файл | размер | вес | статус |")
        md.append("|---|---|---|---|")
    for p in prevs:
        st = "OK"
        issues = []
        try:
            from PIL import Image
            with Image.open(p) as im:
                im.verify()      # verify — строго сразу после open
            with Image.open(p) as im:
                im.load()
                dims = im.size
        except Exception as e:
            dims = (0, 0)
            st = "FAIL"
            issues.append(f"битый JPG: {e}")
        if st == "OK":
            if dims[0] != 1080:
                st = "FAIL"
                issues.append(f"ширина {dims[0]}, ожидалась 1080")
            if p.stat().st_size < L.MIN_JPG_BYTES:
                st = "FAIL"
                issues.append(f"вес {L.human_size(p.stat().st_size)} < 20 КБ")
        for iss in issues:
            add(st, f"превью {p.name}: {iss}")
        data["previews"].append({"file": p.name, "dims": dims, "bytes": p.stat().st_size,
                                 "status": st, "issues": issues})
        md.append(f"| {p.name} | {dims[0]}×{dims[1]} | {L.human_size(p.stat().st_size)} | {st} |")
    if not prevs:
        add("FAIL", "превью JPG не собраны")
        md.append("_Нет превью._")
    md.append("")

    # ---------------- превью для Telegram ----------------
    md.append("## Превью для Telegram владельца (`05_ГОТОВОЕ/превью_ТГ/`)\n")
    tg_expected = ["P01", "P02", "P07"]
    tg_files = []
    for pid in tg_expected:
        hits = sorted(L.PREVIEW_TG_DIR.glob(f"{pid}_*.jpg")) if L.PREVIEW_TG_DIR.is_dir() else []
        tg_files.append((pid, hits[0] if hits else None))
    tg_md = []
    if tg_files and any(f for _, f in tg_files):
        md.append("| ID | файл | размер | вес | статус |")
        md.append("|---|---|---|---|---|")
    for pid, p in tg_files:
        if p is None:
            st = "WARN" if len(one) < 10 else "FAIL"
            if st == "FAIL":
                add("FAIL", f"превью_ТГ: нет JPG для {pid}")
            else:
                add("WARN", f"превью_ТГ: пока нет {pid}")
            md.append(f"| {pid} | — | — | — | {st} |")
            data["tg_previews"] = data.get("tg_previews", []) + [{"id": pid, "file": None, "status": st}]
            continue
        st = "OK"
        issues = []
        try:
            from PIL import Image
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                im.load()
                dims = im.size
        except Exception as e:
            dims = (0, 0)
            st = "FAIL"
            issues.append(f"битый JPG: {e}")
        if st == "OK" and dims[0] != 1080:
            st = "FAIL"
            issues.append(f"ширина {dims[0]}, ожидалась 1080")
        if st == "OK" and p.stat().st_size < L.MIN_JPG_BYTES:
            st = "FAIL"
            issues.append(f"вес {L.human_size(p.stat().st_size)} < 20 КБ")
        for iss in issues:
            add(st, f"превью_ТГ {p.name}: {iss}")
        data["tg_previews"] = data.get("tg_previews", []) + [
            {"id": pid, "file": p.name, "dims": dims, "bytes": p.stat().st_size, "status": st}]
        md.append(f"| {pid} | {p.name} | {dims[0]}×{dims[1]} | {L.human_size(p.stat().st_size)} | {st} |")
        tg_md.append(p.name)
    if not any(f for _, f in tg_files):
        add("FAIL" if len(one) >= 10 else "WARN", "превью_ТГ не собраны (P01/P02/P07)")
        md.append("_Папка превью_ТГ пуста._")
    md.append("")

    # ---------------- PDF ----------------
    md.append("## PDF-альбом A4\n")
    n_main = len(one)
    expect_pages = 2 + n_main
    pdf = verify_pdf(L.PDF_PATH, expect_pages)
    data["pdf"] = pdf
    if not pdf["exists"]:
        add("WARN" if a.partial else "FAIL", "PDF не собран")
        md.append("_PDF не собран._")
    else:
        st = "OK" if pdf["ok"] else "FAIL"
        for iss in pdf["issues"]:
            add("FAIL", f"PDF: {iss}")
        md.append("| файл | страниц | вес | шрифты | собран | статус |")
        md.append("|---|---|---|---|---|---|")
        pdf_mtime = time.strftime("%d.%m %H:%M:%S", time.localtime(L.PDF_PATH.stat().st_mtime))
        md.append(f"| {L.PDF_NAME} | {pdf['pages']} (ожидалось {expect_pages}) | "
                  f"{L.human_size(pdf['bytes'])} | Type3-контуры: {pdf['fonts_type3']}; "
                  f"встроенных: {pdf['fonts_embedded']} | {pdf_mtime} | {st} |")
    md.append("")

    # ---------------- галерея ----------------
    md.append("## Галерея\n")
    gal = L.GALLERY_DIR / "index.html"
    if gal.is_file():
        text = gal.read_text(encoding="utf-8", errors="replace")
        missing_links = [pid for pid in L.ORDER_MAIN if pid not in text]
        st = "OK"
        issues = []
        if missing_links:
            st = "WARN"
            issues.append(f"в галерее нет постеров: {', '.join(missing_links)}")
        if gal.stat().st_size < 2000:
            st = "FAIL"
            issues.append("подозрительно маленький index.html")
        for iss in issues:
            add(st, f"галерея: {iss}")
        data["gallery"] = {"file": str(gal), "bytes": gal.stat().st_size, "status": st}
        md.append(f"- `05_ГОТОВОЕ/gallery/index.html` — {L.human_size(gal.stat().st_size)}, "
                  f"постеров в ссылках: {10 - len(missing_links)}/10 — {st}")
    else:
        add("FAIL", "галерея не собрана (05_ГОТОВОЕ/gallery/index.html)")
        md.append("- _Галерея не собрана._")
    md.append("")

    # ---------------- контактный лист ----------------
    cs = L.QA_DIR / "contact_sheet.jpg"
    if cs.is_file():
        data["contact_sheet"] = {"file": str(cs), "bytes": cs.stat().st_size}
        md.append(f"## QA-артефакты\n- контактный лист: `_render/_qa/contact_sheet.jpg` ({L.human_size(cs.stat().st_size)})\n"
                  f"- отчёт рендера: `_render/_qa/render_report.json`\n- отчёт PDF: `_render/_qa/pdf_report.json`\n"
                  f"- скриншоты PDF: `_render/_qa/pdf_pages/`\n")
    else:
        add("WARN", "нет контактного листа QA")
        md.append("## QA-артефакты\n_Контактный лист ещё не собран._\n")

    # ---------------- промежуточный режим ----------------
    if a.partial:
        # отсутствующие постеры — не блокер для промежуточной сборки
        for pid in L.ORDER_MAIN:
            if pid not in one:
                md_is = f"{pid}: 1× PNG не отрендерен"
                data["issues"] = [i for i in data["issues"] if not (i["status"] == "FAIL" and i["text"] == md_is)]
        fails = sum(1 for i in data["issues"] if i["status"] == "FAIL")
        warns = sum(1 for i in data["issues"] if i["status"] == "WARN")

    status_word = "OK" if fails == 0 else "ЕСТЬ ПРОБЛЕМЫ"
    head = [
        "# Чек-лист файлов пакета «Два горизонта»",
        "",
        f"**Дата проверки:** {time.strftime('%d.%m.%Y %H:%M')}  ",
        "**Пакет:** инфографика «Два горизонта» · НПО «Киловатт» × магазин «В ОКОПЕ» · ноябрь 2026  ",
        f"**Проверено скриптом:** `_render/check_files.py`  ",
        f"**Итог:** {status_word} · FAIL: {fails} · WARN: {warns}",
        "",
        "## Состав",
        "",
        f"- PNG основной серии 1×: {len(one)}/10",
        f"- PNG основной серии 2×: {len(two)}/10",
        f"- Широкие 1920×1080: {len(wide)} (бриф: P01, P02, P03, P07)",
        f"- Истории 1080×1920: {len(story)} (бриф: P01, P07, P09)",
        f"- JPG-превью: {len(prevs)}",
        f"- Превью для Telegram: {sum(1 for _, f in tg_files if f)}/3 (P01, P02, P07)",
        f"- PDF: {'есть, ' + str(pdf['pages']) + ' стр.' if pdf['exists'] else 'нет'}",
        f"- Галерея: {'есть' if gal.is_file() else 'нет'}",
        "",
    ]
    problems = [i for i in data["issues"] if i["status"] != "OK"]
    tail = ["## Что осталось / проблемы", ""]
    if problems:
        for i in problems:
            tail.append(f"- **{i['status']}** — {i['text']}")
    else:
        tail.append("- Проблем нет: все обязательные файлы на месте и валидны.")
    tail += [
        "",
        "## Как перерендерить",
        "",
        "```powershell",
        "powershell -NoProfile -ExecutionPolicy Bypass -File _render\\run_all.ps1",
        "# только один постер:",
        "& $py _render\\render_posters.py P01",
        "# PDF отдельно:",
        "powershell -NoProfile -ExecutionPolicy Bypass -File _render\\build_pdf.ps1",
        "```",
        "",
        "Источник правды: `00_БРИФ_ИНФОГРАФИКИ.md` (§5 форматы, §9 приёмка). Цены не публикуются.",
        "",
    ]

    md_path = Path(a.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(head + md + tail), encoding="utf-8")
    json_path = Path(a.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Чек-лист: {md_path}")
    print(f"  PNG 1×: {len(one)}/10, 2×: {len(two)}/10, широкие: {len(wide)}, истории: {len(story)}, превью: {len(prevs)}")
    print(f"  PDF: {'есть, ' + str(pdf['pages']) + ' стр.' if pdf['exists'] else 'нет'}; галерея: {'есть' if gal.is_file() else 'нет'}")
    print(f"  ИТОГ: {'OK' if fails == 0 else 'ЕСТЬ ПРОБЛЕМЫ'} (FAIL {fails}, WARN {warns})")
    for i in problems:
        print(f"    [{i['status']}] {i['text']}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
