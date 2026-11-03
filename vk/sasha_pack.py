#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПАКЕТ ПО ПРАЙСУ САШИ (Багратионовский, 30.10.2026) — подборка 12 постов для ВК.

  PYTHONPATH=vendor python3 vk/sasha_pack.py vk/posts/sasha_selection.json

selection.json:
  {"title": "...", "items": [{"slug", "name", "category", "extra_tags", "headline",
                              "hook", "bullets": [...]}]}

Фото — подобраны в интернете (прямое разрешение владельца 30.10 ТОЛЬКО для постов
Саши), лежат в suppliers/sasha/photos/<slug>/NN.jpg (вне git).
Тексты: без цен (цена только в ЛС), без остатков, без внутренних формулировок
(жёсткая проверка check_public_text).
Выход: vk/posts/pack_sasha/ — папка на позицию (пост.txt + фото + обложка.jpg),
ВСЕ_ПОСТЫ.txt, ЧЕК-ЛИСТ.txt, README.txt, zip V_OKOPE_sasha_posts.zip → vk/out + vk/dist.
"""
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

from make_pack import (availability_line, check_public_text, make_cover, safe_slug, save_photos)
try:
    from vk.post import hashtags
except ImportError:  # noqa: BLE001
    sys.path.insert(0, HERE)
    from post import hashtags  # type: ignore

# CTA для подборки Саши: цена — только в ЛС (решение владельца 30.10)
SASHA_CTA = [
    "Отправляем СДЭК по России. Цена и наличие — в личных сообщениях.",
    "СДЭК по всей России. Цену и наличие напишу в ЛС.",
    "Доставка СДЭК. Пишите в сообщения — скажу цену и наличие.",
    "СДЭК по РФ. Вопросы, цена и наличие — в личку.",
]


def build_text(entry, n):
    body = [entry["headline"], "", entry["hook"].strip(), ""]
    bullets = [b.strip() for b in entry.get("bullets", []) if b.strip()]
    if bullets:
        body.append("Что важно:")
        body += [f"▪️ {b}" for b in bullets[:4]]
        body.append("")
    body.append(availability_line(None))  # просто «В наличии.»
    body.append("")
    body.append(SASHA_CTA[n % len(SASHA_CTA)])
    body.append("")
    body.append(hashtags(entry["name"], entry.get("category", ""), tuple(entry.get("extra_tags", ()))))
    text = "\n".join(body).strip() + "\n"
    check_public_text(text)
    return text


def main(argv=None):
    sel_path = argv[0] if argv else os.path.join(HERE, "posts", "sasha_selection.json")
    sel = json.load(open(sel_path, encoding="utf-8"))

    out_root = os.path.join(HERE, "posts", "pack_sasha")
    shutil.rmtree(out_root, ignore_errors=True)
    os.makedirs(out_root, exist_ok=True)

    report, all_texts, missing = [], [], []
    for n, entry in enumerate(sel["items"], 1):
        slug = entry["slug"]
        photo_dir = os.path.join(ROOT, "suppliers", "sasha", "photos", slug)
        files = sorted(
            os.path.relpath(os.path.join(photo_dir, f), ROOT)
            for f in os.listdir(photo_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ) if os.path.isdir(photo_dir) else []

        text = build_text(entry, n)
        folder = os.path.join(out_root, f"{n:02d}_{safe_slug(entry['name'])}")
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "пост.txt"), "w", encoding="utf-8").write(text)

        saved = save_photos(files, folder, limit=len(files)) if files else []
        if saved:
            make_cover(files[0], os.path.join(folder, "обложка.jpg"), entry["headline"])
        else:
            missing.append(f"{entry['name']}: нет фото в suppliers/sasha/photos/{slug}/")

        all_texts.append(f"{'=' * 68}\n{n:02d}. {entry['headline']}\n{'=' * 68}\n\n{text}\n")
        report.append({"n": n, "slug": slug, "name": entry["name"], "photos": len(saved), "chars": len(text)})

    open(os.path.join(out_root, "ВСЕ_ПОСТЫ.txt"), "w", encoding="utf-8").write("\n".join(all_texts))

    readme = [
        f"В ОКОПЕ — {sel['title']}",
        "=" * 40, "",
        "Что внутри",
        "----------",
        f"{len(report)} папок — по одной на позицию прайса. В папке: «пост.txt» + фото (1.jpg, 2.jpg, …) + «обложка.jpg».",
        "Файл «ВСЕ_ПОСТЫ.txt» — тексты всех постов сразу.",
        "",
        "Как выкладывать",
        "---------------",
        "1. Откройте папку позиции.",
        "2. Загрузите все фото в ВК по порядку (1.jpg — первым).",
        "3. Скопируйте текст из «пост.txt» целиком и опубликуйте.",
        "",
        "Правила, по которым собрано",
        "---------------------------",
        "• Фото подобраны в интернете — по прямому разрешению владельца (30.10) только для постов по прайсу Саши.",
        "• Цены в постах НЕ указываем — цена только в ЛС (решение владельца).",
        "• Остатки в постах не пишем; наличие — словом «В наличии.».",
        "• Характеристики — проверенные публичные данные производителей, ничего не выдумано.",
        "• Доставка — СДЭК по России, постоплаты нет.",
        "",
        "Позиции",
        "--------",
    ]
    for r in report:
        readme.append(f"  {r['n']:02d}. {r['name']} — фото: {r['photos']}")
    readme += ["", f"Всего позиций: {len(report)}. Всего фото: {sum(r['photos'] for r in report)}."]
    open(os.path.join(out_root, "README.txt"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    chk = ["ЧЕК-ЛИСТ ВЫКЛАДКИ — отмечайте, что уже выставлено", "=" * 50, ""]
    for r in report:
        chk.append(f"  [ ] {r['n']:02d}. {r['name']} ({r['photos']} фото)")
    open(os.path.join(out_root, "ЧЕК-ЛИСТ.txt"), "w", encoding="utf-8").write("\n".join(chk) + "\n")

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    zip_name = "V_OKOPE_sasha_posts.zip"
    zip_path = os.path.join(HERE, "out", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_root):
            for f in sorted(files):
                full_path = os.path.join(root, f)
                z.write(full_path, os.path.relpath(full_path, os.path.dirname(out_root)))
    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    shutil.copy2(zip_path, dist)

    print(f"Позиций собрано: {len(report)} из {len(sel['items'])}")
    print(f"Фото вложено: {sum(r['photos'] for r in report)}")
    print(f"ZIP: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)")
    if missing:
        print("\n⚠ ПРОБЛЕМЫ:")
        for m in missing:
            print("  ·", m)
    json.dump(report, open(os.path.join(HERE, "out", "report_sasha.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
