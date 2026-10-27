#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПАКЕТ ПОД ЛИНЕЙКУ ОБУВИ VELES (Велес) — подборка на постинг.

  PYTHONPATH=vendor python3 vk/veles_pack.py vk/posts/veles_selection.json

selection.json:
  {"title": "...", "items": [{"id": "<uuid>", "headline": "...", "hook": "...",
                              "sizes_note": "..." (необязательно)}]}

Фото — ВСЕ, что есть у поставщика (manifest с all_photos, без лимита «3 как обычно»).
Тексты: без цен, без остатков, без внутренних формулировок (жёсткая проверка).
Выход: vk/posts/pack_veles/ — папка на модель (пост.txt + все фото + обложка.jpg),
ВСЕ_ПОСТЫ.txt, ЧЕК-ЛИСТ.txt, README.txt, zip V_OKOPE_veles_posts.zip → vk/out + vk/dist.
"""
import glob
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from make_pack import (bullets_from_desc, availability_line, safe_slug, check_public_text,
                       save_photos, make_cover, CTA)
try:
    from vk.post import hashtags
except ImportError:  # noqa: BLE001
    sys.path.insert(0, HERE)
    from post import hashtags  # type: ignore
try:
    from catalog import store
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore


def build_text(entry, name, bullets):
    body = [entry["headline"], "", entry["hook"].strip(), ""]
    n = int(entry.get("bullets", 4))
    if bullets:
        body.append("Что важно:")
        body += [f"▪️ {b}" for b in bullets[:n]]
        body.append("")
    body.append(availability_line(entry.get("sizes_note")))
    body.append("")
    body.append(CTA[hash(entry["id"]) % len(CTA)])
    body.append("")
    body.append(hashtags(name, "обувь"))
    text = "\n".join(body).strip() + "\n"
    check_public_text(text)
    return text


def main(argv=None):
    sel_path = argv[0] if argv else os.path.join(HERE, "posts", "veles_selection.json")
    sel = json.load(open(sel_path, encoding="utf-8"))

    idx = {r["id"]: r for r in json.load(open(
        os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))}
    full = {p["id"]: p for p in json.load(open(
        os.path.join(ROOT, "catalog", "data", "catalog_full.json"), encoding="utf-8"))}
    man = {m["id"]: m for m in store.photos_manifest()}

    out_root = os.path.join(HERE, "posts", "pack_veles")
    shutil.rmtree(out_root, ignore_errors=True)
    os.makedirs(out_root, exist_ok=True)

    report, all_texts, missing = [], [], []
    for n, entry in enumerate(sel["items"], 1):
        pid = entry["id"]
        item = idx.get(pid)
        if not item:
            missing.append(f"{pid}: нет в каталоге")
            continue
        name = item["name"]
        descr = (full.get(pid, {}) or {}).get("description") or ""
        files = (man.get(pid, {}) or {}).get("files") or []
        if not files:
            missing.append(f"«{name[:45]}»: НЕТ ФОТО")
            continue
        bl = bullets_from_desc(descr, entry["hook"], int(entry.get("bullets", 4)), name)
        text = build_text(entry, name, bl)
        folder = os.path.join(out_root, f"{n:02d}_{safe_slug(entry['headline'])}")
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "пост.txt"), "w", encoding="utf-8").write(text)
        # ВСЕ фото, без ограничения «тройки»
        saved = save_photos(files, folder, limit=len(files))
        if saved:
            make_cover(files[0], os.path.join(folder, "обложка.jpg"), entry["headline"])
        all_texts.append(f"{'=' * 68}\n{n:02d}. {entry['headline']}\n{'=' * 68}\n\n{text}\n")
        report.append({"n": n, "name": name, "photos": len(saved), "chars": len(text)})

    open(os.path.join(out_root, "ВСЕ_ПОСТЫ.txt"), "w", encoding="utf-8").write("\n".join(all_texts))

    readme = [
        f"В ОКОПЕ — {sel['title']}",
        "=" * 40, "",
        "Что внутри",
        "----------",
        f"{len(report)} папок — по одной на модель обуви. В папке: «пост.txt» + ВСЕ фото модели (1.jpg, 2.jpg, …) + «обложка.jpg».",
        "Файл «ВСЕ_ПОСТЫ.txt» — тексты всех постов сразу.",
        "",
        "Как выкладывать",
        "---------------",
        "1. Откройте папку модели.",
        "2. Загрузите все фото в ВК по порядку (1.jpg — первым).",
        "3. Скопируйте текст из «пост.txt» целиком и опубликуйте.",
        "",
        "Правила, по которым собрано",
        "---------------------------",
        "• Фото — все, что есть у поставщика, без отбора «тройки».",
        "• Цены в постах НЕ указываем — ни розницы, ни «цена в личку».",
        "• Сколько осталось — в постах не пишем: наличие формулируем словами.",
        "• Факты — из описаний поставщика, ничего не досочинено.",
        "• Доставка — СДЭК по России, постоплаты нет.",
        "",
        "Модели",
        "-------",
    ]
    for r in report:
        readme.append(f"  {r['n']:02d}. {r['name']} — фото: {r['photos']}")
    readme += ["", f"Всего моделей: {len(report)}. Всего фото: {sum(r['photos'] for r in report)}."]
    open(os.path.join(out_root, "README.txt"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    chk = ["ЧЕК-ЛИСТ ВЫКЛАДКИ — отмечайте, что уже выставлено", "=" * 50, ""]
    for r in report:
        chk.append(f"  [ ] {r['n']:02d}. {r['name']} ({r['photos']} фото)")
    open(os.path.join(out_root, "ЧЕК-ЛИСТ.txt"), "w", encoding="utf-8").write("\n".join(chk) + "\n")

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    zip_name = "V_OKOPE_veles_posts.zip"
    zip_path = os.path.join(HERE, "out", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_root):
            for f in sorted(files):
                full_path = os.path.join(root, f)
                z.write(full_path, os.path.relpath(full_path, os.path.dirname(out_root)))
    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    shutil.copy2(zip_path, dist)

    print(f"Моделей собрано: {len(report)} из {len(sel['items'])}")
    print(f"Фото вложено: {sum(r['photos'] for r in report)} (все фото поставщика)")
    print(f"ZIP: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)")
    if missing:
        print("\n⚠ ПРОБЛЕМЫ:")
        for m in missing:
            print("  ·", m)
    json.dump(report, open(os.path.join(HERE, "out", "report_veles.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
