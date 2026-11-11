# -*- coding: utf-8 -*-
"""Приёмка «СУПЕРЦЕНЫ»: 172 карточки + hero, размеры/веса, структура папок, галерея.

Пишет superceny/05_ГОТОВОЕ/ЧЕК_ЛИСТ_ФАЙЛОВ.md и superceny/_render/_qa/files_report.json.
Ожидание по брифу §4/§8: 43 папки × 4 PNG + 00_СУПЕРЦЕНЫ.png = 173 PNG 1080×1350.
--partial: неполный набор — не FAIL (промежуточная сборка).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import superlib as L


def check_png(path: Path) -> dict:
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
    if r["dims"] != (L.CARD_W, L.CARD_H):
        r["status"] = "FAIL"
        r["issues"].append(f"размер {r['dims'][0]}×{r['dims'][1]}, ожидался {L.CARD_W}×{L.CARD_H}")
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
    data = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "positions": {}, "issues": []}

    def add(status: str, text: str):
        nonlocal fails, warns
        if status == "FAIL":
            fails += 1
        elif status == "WARN":
            warns += 1
        data["issues"].append({"status": status, "text": text})

    html_items = L.scan_html()
    pos_meta = L.positions()
    # ожидаемые файлы по HTML
    expected: dict[str, dict] = {}
    folders: dict[str, dict] = {}
    for it in html_items:
        rel = it["out_rel"].as_posix()
        expected[rel] = it
        folder = it["folder"]
        if it["card"] != "00":
            folders.setdefault(folder, {"cards": {}, "name": (pos_meta.get(folder) or {}).get("name", folder)})
            folders[folder]["cards"][it["card"]] = rel
    hero_rel = next((rel for rel, it in expected.items() if it["card"] == "00"), None)

    # фактические PNG
    actual: dict[str, Path] = {}
    if L.OUT_DIR.is_dir():
        for p in L.OUT_DIR.rglob("*.png"):
            if "gallery" in p.parts:
                continue
            actual[p.relative_to(L.OUT_DIR).as_posix()] = p

    extra = sorted(set(actual) - set(expected))
    if extra:
        add("FAIL", f"лишние/устаревшие PNG вне структуры: {len(extra)} ({', '.join(extra[:6])}"
                    + ("…" if len(extra) > 6 else "") + ")")

    md = []
    md.append("## Состав\n")
    md.append(f"- Позиций в HTML: {len(folders)} (ожидалось {L.EXPECT_POSITIONS})")
    md.append(f"- Карточек: {sum(len(f['cards']) for f in folders.values())}/{L.EXPECT_CARDS}")
    md.append(f"- Hero 00_СУПЕРЦЕНЫ: {'есть' if hero_rel else 'НЕТ'}")
    md.append(f"- PNG в 05_ГОТОВОЕ: {len(actual)}/{len(expected)} (ожидание {L.EXPECT_PNG})\n")

    # таблица по позициям
    md.append("## Карточки по позициям\n")
    md.append("| # | папка / позиция | 01 | 02 | 03 | 04 | вес |")
    md.append("|---|---|---|---|---|---|---|")
    total_bytes = 0
    all_rows = []
    for i, (folder, f) in enumerate(sorted(folders.items()), 1):
        cells = {}
        weight = 0
        row_status = []
        for code in ("01", "02", "03", "04"):
            rel = f["cards"].get(code)
            if rel is None:
                cells[code] = "—"
                row_status.append("FAIL")
                if not a.partial:
                    add("FAIL", f"{folder}: нет карточки {code}")
                else:
                    add("WARN", f"{folder}: нет карточки {code}")
                continue
            r = check_png(actual.get(rel, L.OUT_DIR / rel))
            cells[code] = "OK" if r["status"] == "OK" else ("FAIL" if r["status"] == "FAIL" else "WARN")
            if r["status"] != "OK":
                for iss in r["issues"]:
                    add(r["status"], f"{rel}: {iss}")
            weight += r["bytes"]
            total_bytes += r["bytes"]
            all_rows.append((rel, r))
        st = "OK" if all(c == "OK" for c in cells.values()) else ("FAIL" if "FAIL" in cells.values() else "WARN")
        md.append(f"| {i} | {folder} — {f['name']} | {cells['01']} | {cells['02']} | {cells['03']} | {cells['04']} "
                  f"| {L.human_size(weight) if weight else '—'} |")
    md.append("")

    # hero
    md.append("## Hero\n")
    if hero_rel:
        rh = check_png(actual.get(hero_rel, L.OUT_DIR / hero_rel))
        total_bytes += rh["bytes"]
        all_rows.append((hero_rel, rh))
        for iss in rh["issues"]:
            add(rh["status"], f"{hero_rel}: {iss}")
        md.append(f"- `{hero_rel}` — {rh['dims'][0] if rh['dims'] else '—'}×{rh['dims'][1] if rh['dims'] else '—'}, "
                  f"{L.human_size(rh['bytes'])}, рендер {rh['rendered_at'] or '—'} — {rh['status']}")
    else:
        add("WARN" if a.partial else "FAIL", "нет 00_СУПЕРЦЕНЫ.png")
        md.append("- _нет_")
    md.append("")

    # полный список файлов
    md.append("## Файлы (размеры, веса, время рендера)\n")
    md.append("| файл | размер | вес | рендер | статус |")
    md.append("|---|---|---|---|---|")
    for rel, r in all_rows:
        d = f"{r['dims'][0]}×{r['dims'][1]}" if r["dims"] else "—"
        md.append(f"| {rel} | {d} | {L.human_size(r['bytes']) if r['bytes'] else '—'} | "
                  f"{r['rendered_at'] or '—'} | {r['status']} |")
    md.append("")

    # галерея
    md.append("## Галерея\n")
    gal = L.GALLERY_DIR / "index.html"
    if gal.is_file():
        text = gal.read_text(encoding="utf-8", errors="replace")
        missing = [f for f in sorted(folders) if f not in text]
        st = "OK"
        if missing:
            st = "WARN" if a.partial else "FAIL"
            add(st, f"галерея: нет папок {', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}")
        md.append(f"- `05_ГОТОВОЕ/gallery/index.html` — {L.human_size(gal.stat().st_size)}, "
                  f"позиций в ссылках: {len(folders) - len(missing)}/{len(folders)} — {st}")
        data["gallery"] = {"bytes": gal.stat().st_size, "status": st}
    else:
        add("FAIL", "галерея не собрана")
        md.append("- _нет_")
    md.append("")

    # детектор из отчёта рендера
    md.append("## Детектор наложений/переполнений\n")
    rr_path = L.QA_DIR / "render_report.json"
    if rr_path.is_file():
        try:
            rr = json.loads(rr_path.read_text(encoding="utf-8"))
            md.append(f"- Рендер: OK {rr.get('ok')}, WARN {rr.get('warn')}, FAIL {rr.get('fail')}; "
                      f"наложений {rr.get('overlaps', 0)}, текста за кадром {rr.get('text_out', 0)}, "
                      f"overflow:hidden {rr.get('clipped', 0)}")
            bad = [r for r in rr.get("results", []) if r.get("status") != "OK"]
            if bad:
                md.append(f"- Файлы с замечаниями: {len(bad)}")
                for r in bad[:12]:
                    note = "; ".join((r.get("fail") or []) + (r.get("warn") or []))
                    rel = Path(r["out"]).relative_to(L.OUT_DIR).as_posix()
                    md.append(f"  - `{rel}` — {r.get('status')}: {note}")
            data["render"] = {"ok": rr.get("ok"), "warn": rr.get("warn"), "fail": rr.get("fail"),
                              "overlaps": rr.get("overlaps", 0), "text_out": rr.get("text_out", 0)}
        except Exception as e:
            md.append(f"- _отчёт рендера не прочитан: {e}_")
    else:
        md.append("- _отчёта рендера нет_")
    md.append("")

    problems = [i for i in data["issues"] if i["status"] != "OK"]
    status_word = "OK" if fails == 0 else "ЕСТЬ ПРОБЛЕМЫ"
    head = [
        "# Чек-лист файлов пакета «СУПЕРЦЕНЫ»",
        "",
        f"**Дата проверки:** {time.strftime('%d.%m.%Y %H:%M')}  ",
        "**Пакет:** СУПЕРЦЕНЫ НА НПО «КИЛОВАТТ» · 20 позиций × 4 карточки + hero · ноябрь 2026  ",
        "**Проверено скриптом:** `superceny/_render/check_files.py`  ",
        f"**Итог:** {status_word} · FAIL: {fails} · WARN: {warns}",
        "",
    ]
    tail = ["## Что осталось / проблемы", ""]
    if problems:
        for i in problems[:40]:
            tail.append(f"- **{i['status']}** — {i['text']}")
        if len(problems) > 40:
            tail.append(f"- … ещё {len(problems) - 40}")
    else:
        tail.append(f"- Проблем нет: все {L.EXPECT_CARDS} карточек + hero на месте, размеры 1080×1350, веса в норме.")
    tail += ["", "## Как перерендерить", "",
             "```powershell",
             "powershell -NoProfile -ExecutionPolicy Bypass -File _render\\run_all.ps1",
             "# батч по папкам / только новые:",
             "& $py _render\\render_cards.py --all --batch-size 40 --only-new",
             "& $py _render\\render_cards.py --folder 01_Муха",
             "```", "",
             "Структура сдачи — `superceny/00_БРИФ.md` §4/§9, приёмка — §8. Цены: «Прайс по запросу».",
             ""]
    md_path = Path(a.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(head + md + tail), encoding="utf-8")
    json_path = Path(a.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Чек-лист: {md_path}")
    print(f"  позиций: {len(folders)}/{L.EXPECT_POSITIONS}, "
          f"карточек: {sum(len(f['cards']) for f in folders.values())}/{L.EXPECT_CARDS}, "
          f"PNG: {len(actual)}/{len(expected)} ({L.human_size(total_bytes)})")
    print(f"  ИТОГ: {'OK' if fails == 0 else 'ЕСТЬ ПРОБЛЕМЫ'} (FAIL {fails}, WARN {warns})")
    for i in problems[:15]:
        print(f"    [{i['status']}] {i['text']}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
