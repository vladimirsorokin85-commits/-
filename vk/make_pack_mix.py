#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СБОРКА МИКС-ПАКЕТА ПОСТОВ ВК — несколько поставщиков: Дима + front-ts + MG Ultra.

  python3 vk/make_pack_mix.py vk/posts/plan_2026-10-22_28.json

План: days → posts; у поста source: dima | frontts | mgultra, ref (id / slug / model id),
headline, hook, bullets, sizes_note.
Фото — только от поставщиков (каталог Димы / front-ts / MG Ultra).
Цены и остатки в постах не пишем (правило магазина), жёсткая проверка check_public_text.
"""
import glob
import json
import os
import re
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

MG_CTA = "СДЭК по России. Напишите в личные сообщения — подберём под ваш карабин и резьбу."
MG_ABOUT = ("ДТКП закрытого типа — не глушитель: снижает отдачу, гасит вспышку, "
            "бесшумной стрельбы не будет.")
MG_SKIP = ("отгрузка", "закажите", "технический специалист", "свяжется с вами", "консультацию по телефону")

SASHA_CTA = [
    "Отправляем СДЭК по России. Цена и наличие — в личных сообщениях.",
    "СДЭК по всей России. Цену и наличие напишу в ЛС.",
    "Доставка СДЭК. Пишите в сообщения — скажу цену и наличие.",
    "СДЭК по РФ. Вопросы, цена и наличие — в личку.",
]

FT_GROUP = {"odezhda": "одежда", "ragruzka": "разгрузка", "podacha": "подача",
            "med": "медицина", "ryukzaki": "рюкзаки", "instrument": "инструмент",
            "tunning": "тюнинг"}


def mg_slug(name):
    s = re.sub(r"[^\w\s-]", "", name.lower().replace("ё", "е"), flags=re.UNICODE)
    return re.sub(r"[\s_]+", "-", s).strip("-")[:40]


def mg_facts(m):
    out = [MG_ABOUT]
    for k, v in (m.get("specs") or {}).items():
        out.append(f"{str(k).strip(':')}: {v}")
    for t in (m.get("texts") or []):
        t = (t or "").strip()
        if not t or t.startswith("+"):
            continue
        if any(t.lower().startswith(s) for s in MG_SKIP):
            continue
        out.append(t)
    return out


def build_text(entry, name, category, bullets, slot):
    body = [entry["headline"], "", entry["hook"].strip(), ""]
    n = int(entry.get("bullets", 4))
    if bullets:
        body.append("Что важно:")
        body += [f"▪️ {b}" for b in bullets[:n]]
        body.append("")
    body.append(availability_line(entry.get("sizes_note")))
    body.append("")
    if entry["source"] == "mgultra":
        cta = MG_CTA
    elif entry["source"] == "sasha":
        cta = SASHA_CTA[slot % len(SASHA_CTA)]
    else:
        cta = CTA[slot % len(CTA)]
    body.append(cta)
    body.append("")
    body.append(hashtags(name, category, tuple(entry.get("extra_tags") or ())))
    text = "\n".join(body).strip() + "\n"
    check_public_text(text)
    return text


def main(argv=None):
    plan_path = argv[0] if argv else os.path.join(HERE, "posts", "plan_2026-10-22_28.json")
    plan = json.load(open(plan_path, encoding="utf-8"))

    idx = {r["id"]: r for r in json.load(open(
        os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))}
    full = {p["id"]: p for p in json.load(open(
        os.path.join(ROOT, "catalog", "data", "catalog_full.json"), encoding="utf-8"))}
    man = {m["id"]: m for m in store.photos_manifest()}

    ft_cat_all = json.load(open(os.path.join(ROOT, "suppliers", "frontts", "catalog.json"), encoding="utf-8"))
    ft_items = {i["slug"]: i for i in ft_cat_all["items"]}
    ft_groups = json.load(open(os.path.join(ROOT, "suppliers", "frontts", "groups.json"), encoding="utf-8"))
    ft_cat = {}
    for g, slugs in ft_groups.items():
        for s in slugs:
            ft_cat[s] = FT_GROUP.get(g, g)

    mg_cat = json.load(open(os.path.join(ROOT, "suppliers", "mgultra", "catalog.json"), encoding="utf-8"))
    mg_models = {m["id"]: m for m in mg_cat["models"]}

    sasha_sel = {i["slug"]: i for i in json.load(open(
        os.path.join(HERE, "posts", "sasha_selection.json"), encoding="utf-8"))["items"]}

    out_root = os.path.join(HERE, "posts", f"pack_{plan['start']}")
    shutil.rmtree(out_root, ignore_errors=True)
    os.makedirs(out_root, exist_ok=True)

    report, all_days, missing = [], [], []
    for day in plan["days"]:
        day_dir = os.path.join(out_root, f"{day['date'].replace('2026', '').strip('.')}_{day['weekday']}")
        os.makedirs(day_dir, exist_ok=True)
        day_texts = []
        for slot, entry in enumerate(day["posts"], 1):
            src = entry["source"]
            # --- источник: товар, описание, фото, факты, категория
            if src == "dima":
                item = idx.get(entry["id"])
                if not item:
                    missing.append(f"{day['date']} {entry.get('code')}: нет в каталоге Димы")
                    continue
                name, category = item["name"], item.get("category", "")
                descr = (full.get(item["id"], {}) or {}).get("description") or ""
                files = (man.get(item["id"], {}) or {}).get("files") or []
                bl = bullets_from_desc(descr, entry["hook"], int(entry.get("bullets", 4)), name)
            elif src == "frontts":
                it = ft_items.get(entry["ref"])
                if not it:
                    missing.append(f"{day['date']} frontts/{entry['ref']}: нет в каталоге")
                    continue
                name, category = it["name"], ft_cat.get(entry["ref"], "экипировка")
                descr = it.get("descr") or ""
                fdir = os.path.join(ROOT, "suppliers", "frontts", "photos", f"item-{entry['ref']}")
                files = [os.path.relpath(p, ROOT) for p in sorted(glob.glob(os.path.join(fdir, "*")))]
                bl = bullets_from_desc(descr, entry["hook"], int(entry.get("bullets", 3)), name)
            elif src == "sasha":
                sel = sasha_sel.get(entry["ref"])
                if not sel:
                    missing.append(f"{day['date']} sasha/{entry['ref']}: нет в sasha_selection.json")
                    continue
                name, category = sel["name"], sel.get("category", "экипировка")
                fdir = os.path.join(ROOT, "suppliers", "sasha", "photos", entry["ref"])
                files = [os.path.relpath(p, ROOT) for p in sorted(glob.glob(os.path.join(fdir, "*")))
                         if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
                bl = [b.strip() for b in (entry.get("facts") or sel.get("bullets") or []) if b.strip()] or [entry["hook"]]
                entry.setdefault("extra_tags", sel.get("extra_tags", []))
            else:  # mgultra
                m = mg_models.get(entry["ref"])
                if not m:
                    missing.append(f"{day['date']} mgultra/{entry['ref']}: нет модели")
                    continue
                name, category = m["name"], "тюнинг"
                files = list(m.get("photos_local") or [])
                bl = mg_facts(m)

            if not files:
                missing.append(f"{day['date']} {src}/{entry.get('ref') or entry.get('code')} «{name[:40]}»: НЕТ ФОТО")

            text = build_text(entry, name, category, bl, slot)
            folder = os.path.join(day_dir, f"{slot:02d}_{safe_slug(entry['headline'])}")
            os.makedirs(folder, exist_ok=True)
            open(os.path.join(folder, "пост.txt"), "w", encoding="utf-8").write(text)
            saved = save_photos(files, folder)
            if saved:
                make_cover(files[0], os.path.join(folder, "обложка.jpg"), entry["headline"])

            day_texts.append(f"{'=' * 68}\n{slot:02d}. [{src}] {entry['headline']}\n{'=' * 68}\n\n{text}\n")
            report.append({"day": day["date"], "slot": slot, "source": src,
                           "name": name, "photos": len(saved), "chars": len(text)})
        open(os.path.join(day_dir, "ВСЕ_ПОСТЫ_ЗА_ДЕНЬ.txt"), "w", encoding="utf-8").write("\n".join(day_texts))
        day_chk = [f"{day['date']} ({day['weekday']}) — чек-лист", "=" * 40, ""]
        for slot, entry in enumerate(day["posts"], 1):
            day_chk.append(f"  [ ] {slot:02d}. [{entry['source']}] {entry['headline']}")
        open(os.path.join(day_dir, "ЧЕК-ЛИСТ_ДНЯ.txt"), "w", encoding="utf-8").write("\n".join(day_chk) + "\n")
        all_days.append((day, day_dir, "\n".join(day_texts)))

    open(os.path.join(out_root, "ВСЕ_ПОСТЫ_НЕДЕЛЯ.txt"), "w", encoding="utf-8").write(
        "\n".join(t for _, _d, t in all_days))

    by_src = {}
    for r in report:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    readme = [
        f"В ОКОПЕ — {plan['title']}",
        "=" * 40, "",
        "Что внутри",
        "----------",
        f"7 папок по дням ({plan['days'][0]['date'][:5]} … "
        f"{plan['days'][-1]['date'][:5]}). "
        f"В каждом дне {len(plan['days'][0]['posts'])} папок постов: «пост.txt» + фото поставщика.",
        "Файл «ВСЕ_ПОСТЫ_ЗА_ДЕНЬ.txt» — тексты одного дня, «ВСЕ_ПОСТЫ_НЕДЕЛЯ.txt» — всей недели.",
        "",
        "Источники (микс): " + ", ".join(f"{k}: {v}" for k, v in sorted(by_src.items())),
        "  · dima — основной каталог (обувь, одежда, защита, оптика, связь, медицина, РЭБ);",
        "  · frontts — тактическая одежда «Голиаф»/«Страж», разгрузка, медицина RHINO RESCUE, рюкзаки, штурмовой инструмент, тюнинг;",
        "  · sasha — прайс Багратионовского 30.10 (дроны, электростанции, генераторы, прицелы, рации):",
        "    фото подобраны в интернете по прямому разрешению владельца; цены в постах нет — только в ЛС;",
        "  · mgultra (ДТКП) — не используем (решение владельца).",
        "",
        "Как выкладывать",
        "---------------",
        "1. Откройте папку дня, затем папку поста.",
        "2. Загрузите фото в ВК (по порядку: фото 1, фото 2, фото 3).",
        "3. Скопируйте текст из «пост.txt» целиком и опубликуйте.",
        "",
        "График на неделю",
        "----------------",
    ]
    for day, _dir, _t in all_days:
        readme.append(f"  {day['date']} ({day['weekday']}):")
        for slot, entry in enumerate(day["posts"], 1):
            readme.append(f"     {slot}. [{entry['source']}] {entry['headline']}")
    readme += [
        "",
        "Правила, по которым собрано",
        "---------------------------",
        "• Цены в постах НЕ указываем — ни розницы, ни «цена в личку».",
        "• Сколько осталось — в постах не пишем: наличие формулируем словами.",
        "• Факты — из описаний поставщиков, ничего не досочинено.",
        "• Фото — от поставщиков (Дима / front-ts); для позиций Саши — подобранные в интернете фото (разрешение владельца 30.10, только Саша).",
        "• ДТКП — не глушитель; подбор по карабину и резьбе — в ЛС.",
        "",
        f"Всего постов: {sum(len(d['posts']) for d in plan['days'])}.",
    ]
    readme += [
        "",
        "Файлы в каждой папке поста",
        "--------------------------",
        "  1.jpg, 2.jpg … — фото поставщика в порядке загрузки (1 — первым);",
        "  обложка.jpg    — та же фотография с нашим логотипом и заголовком, по желанию;",
        "  пост.txt       — текст, копируется целиком.",
    ]
    open(os.path.join(out_root, "README.txt"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    chk = ["ЧЕК-ЛИСТ ВЫКЛАДКИ — отмечайте, что уже выставлено", "=" * 50, ""]
    for day, _dir, _t in all_days:
        chk.append(f"{day['date']} ({day['weekday']})")
        for slot, entry in enumerate(day["posts"], 1):
            chk.append(f"  [ ] {slot:02d}. [{entry['source']}] {entry['headline']}")
        chk.append("")
    open(os.path.join(out_root, "ЧЕК-ЛИСТ.txt"), "w", encoding="utf-8").write("\n".join(chk))

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    zip_name = f"V_OKOPE_posts_{plan['start'].replace('-', '')}_week.zip"
    zip_path = os.path.join(HERE, "out", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_root):
            for f in sorted(files):
                full_path = os.path.join(root, f)
                z.write(full_path, os.path.relpath(full_path, os.path.dirname(out_root)))

    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    shutil.copy2(zip_path, dist)

    day_zips = []
    for day, day_dir, _t in all_days:
        name = f"V_OKOPE_{day['date'][:5]}_{day['weekday']}.zip"
        path = os.path.join(HERE, "out", name)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(day_dir):
                for f in sorted(files):
                    full_path = os.path.join(root, f)
                    z.write(full_path, os.path.relpath(full_path, os.path.dirname(day_dir)))
        day_zips.append(path)
    for path in day_zips:
        shutil.copy2(path, dist)

    print(f"Постов собрано: {len(report)} из {sum(len(d['posts']) for d in plan['days'])}")
    print("По источникам: " + ", ".join(f"{k}={v}" for k, v in sorted(by_src.items())))
    print(f"Фото вложено: {sum(r['photos'] for r in report)}")
    print(f"ZIP недели: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)")
    for path in day_zips:
        print(f"ZIP дня:    {os.path.basename(path)} ({os.path.getsize(path) / 1024 / 1024:.1f} МБ)")
    if missing:
        print("\n⚠ ПРОБЛЕМЫ:")
        for m in missing:
            print("  ·", m)
    json.dump(report, open(os.path.join(HERE, "out", f"report_{plan['start']}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
