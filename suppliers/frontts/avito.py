#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПАКЕТ ОБЪЯВЛЕНИЙ ДЛЯ АВИТО — поставщик front-ts.ru.

  python3 suppliers/frontts/avito.py --list          # что и в каком разделе
  python3 suppliers/frontts/avito.py                 # собрать папки и архивы
  python3 suppliers/frontts/avito.py --only podsumok-dlya-ak,mup-malyj-universalnyj-podsumok

Что получается:
  suppliers/frontts/avito_out/<NN_Название>/
      1.jpg … N.jpg                 фото поставщика (≤1200 px), грузятся по порядку
      ОБЪЯВЛЕНИЕ.txt                заголовок, описание и что заполнить в форме
      ОПИСАНИЕ_копировать.txt       только текст описания — под вставку
  vk/dist/V_OKOPE_avito_frontts_<раздел>.zip — архивы по разделам
  vk/dist/V_OKOPE_avito_frontts_vsyo.zip     — всё одним архивом (если влезает)

Тексты берутся из avito_texts.py. Цены — только в блоке «ЧТО ЗАПОЛНИТЬ» (для формы Авито),
в самом описании их нет: правило владельца. Оплата не упоминается, доставка — СДЭК.
"""
import json
import os
import re
import shutil
import sys
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from avito_texts import TEXTS, GROUP_TITLES, GROUPS, RISKY, SKIP  # noqa: E402

CATALOG = os.path.join(HERE, "catalog.json")
PHOTOS = os.path.join(HERE, "photos")
OUT = os.path.join(HERE, "avito_out")
DIST = os.path.join(ROOT, "vk", "dist")

CLOSER = ("Отправка СДЭК по России. Напишите — подскажу по размеру, цвету и совместимости, "
          "помогу подобрать под задачу.")

FORBIDDEN = [
    ("цена в тексте", r"\d[\d\s]*(₽|руб)"),
    ("«у Димы»/имя", r"\bДим[аыуе]\b"),
    ("поставщик", r"поставщик"),
    ("склад", r"\b(на|со)\s+склад"),
    ("остатки", r"\b\d+\s*(шт|компл|пар)\b"),
    ("оплата при получении", r"при получении"),
    ("постоплата", r"постоплат"),
    ("предоплата", r"\bпредоплат"),
    ("ссылка", r"https?://"),
    ("телефон", r"\+7[\s()\d-]{9,}"),
]


def check_text(text, label):
    for name, rx in FORBIDDEN:
        m = re.search(rx, text, re.I)
        assert not m, f"{label}: запрещённое ({name}) → {m.group(0)!r}"
    n = len(text)
    assert n <= 3200, f"{label}: описание {n} знаков — для Авито много"


def norm_title(t):
    t = re.sub(r"\s+", " ", t).strip()
    return t


def prepare_photos(src_files, dest_dir, limit=8):
    os.makedirs(dest_dir, exist_ok=True)
    saved = []
    for i, rel in enumerate(src_files[:limit], 1):
        p = os.path.join(PHOTOS, rel)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        if max(im.size) > 1200:
            im.thumbnail((1200, 1200), Image.LANCZOS)
        dst = os.path.join(dest_dir, f"{i}.jpg")
        im.save(dst, quality=80, optimize=True)
        saved.append(dst)
    return saved


def main():
    cat = json.load(open(CATALOG, encoding="utf-8"))
    items = cat["items"]
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    if "--list" in sys.argv:
        for g in GROUPS:
            rows = [i for i in items if i["group"] == g]
            print(f"\n{GROUP_TITLES.get(g, g)} — {len(rows)}")
            for i in rows:
                t = TEXTS.get(i["slug"], {})
                print(f"   {i['slug'][:42]:44} фото {len(i['photos'])}  "
                      f"{'текст ✓' if t else 'НЕТ ТЕКСТА'}  {i['name'][:46]}")
        miss = [i["slug"] for i in items if i["slug"] not in TEXTS]
        print(f"\nвсего {len(items)} товаров, без текста: {len(miss)}")
        return

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    rows, idx = [], {}
    n = 0
    for g in GROUPS:
        for it in [x for x in items if x["group"] == g]:
            if it["slug"] in SKIP:
                print(f"  —  {it['slug']}: пропуск ({SKIP[it['slug']]})")
                continue
            if only and it["slug"] not in only:
                continue
            t = TEXTS.get(it["slug"])
            assert t, f"{it['slug']}: нет текста в avito_texts.py"
            n += 1
            label = f"{n:02d}_{re.sub(r'[^0-9A-Za-zА-Яа-яЁё]+', ' ', it['name']).strip()[:60]}"
            folder = os.path.join(OUT, label)
            photos = prepare_photos(it["photos"], folder)
            assert photos, f"{it['name']}: нет фото — объявление не собираем"
            desc = t["desc"].strip()
            check_text(desc, it["name"])
            price = it.get("price_rrc")
            body = f"""АВИТО · ОБЪЯВЛЕНИЕ

ЗАГОЛОВОК (в поле «Название»):
{t['title']}

ОПИСАНИЕ (в поле «Описание»):
{desc}

{CLOSER}

ЧТО ЗАПОЛНИТЬ В ФОРМЕ АВИТО:
· Категория: {t['category']}
· Состояние: Новое
· Цена: {"РРЦ " + format(price, ",d").replace(",", " ") + " ₽" if price else "ваша"} — ставится в поле «Цена», в описании её нет
· Фото: загрузите по порядку 1.jpg → {len(photos)}.jpg
· Доставка: СДЭК по России
· Из описания убраны цена и условия оплаты — они обсуждаются в переписке
"""
            # в блоке «что заполнить» цена допустима (она идёт в поле формы) — из проверки строку убираем
            check_text(re.sub(r"^· Цена:.*$", "", body, flags=re.M), it["name"] + " (файл)")
            open(os.path.join(folder, "ОБЪЯВЛЕНИЕ.txt"), "w", encoding="utf-8").write(body)
            open(os.path.join(folder, "ОПИСАНИЕ_копировать.txt"), "w", encoding="utf-8").write(
                desc + "\n\n" + CLOSER + "\n")
            idx[it["slug"]] = label
            rows.append({"slug": it["slug"], "label": label, "group": g, "title": t["title"],
                         "photos": len(photos), "price": price, "chars": len(desc)})
            print(f"  {n:>3}. {t['title'][:52]:54} фото {len(photos)} | {len(desc)} зн.")

    # README
    readme = ["АВИТО · ОБЪЯВЛЕНИЯ «В ОКОПЕ» — поставщик «Фронт-ТС» (front-ts.ru)", "",
              "Папки по номерам. В каждой:",
              "  · 1.jpg…N.jpg — фото поставщика, грузятся в объявление по порядку;",
              "  · ОПИСАНИЕ_копировать.txt — только текст описания, под вставку;",
              "  · ОБЪЯВЛЕНИЕ.txt — заголовок, описание и что заполнить в форме Авито.", "",
              "В описаниях цены нет: она ставится в поле «Цена» (РРЦ указана в файле ОБЪЯВЛЕНИЕ.txt).",
              "Оплата в текстах не упоминается. Доставка — СДЭК по России.", ""]
    for g in GROUPS:
        gr = [r for r in rows if r["group"] == g]
        if not gr:
            continue
        readme.append(f"{GROUP_TITLES.get(g, g)} — {len(gr)}:")
        for r in gr:
            readme.append(f"  {r['label']}")
        readme.append("")
    risky = [r for r in rows if r["slug"] in RISKY]
    if risky:
        readme += ["", "ПРОВЕРИТЬ ПЕРЕД ВЫКЛАДКОЙ (Авито может не пропустить):"]
        for r in risky:
            readme.append(f"  {r['label'][:52]} — {RISKY[r['slug']]}")
    readme += ["", "Цены в описаниях не указаны. РРЦ по каждой позиции — в файле ОБЪЯВЛЕНИЕ.txt."]
    open(os.path.join(OUT, "README_КАК_ВЫКЛАДЫВАТЬ.txt"), "w", encoding="utf-8").write("\n".join(readme))

    # архивы по разделам
    made = []
    for g in GROUPS:
        gr = [r for r in rows if r["group"] == g]
        if not gr:
            continue
        zp = os.path.join(DIST, f"V_OKOPE_avito_frontts_{g}.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for r in gr:
                base = os.path.join(OUT, r["label"])
                for root, _, files in os.walk(base):
                    for f in sorted(files):
                        p = os.path.join(root, f)
                        z.write(p, os.path.join("V_OKOPE_Avito", os.path.relpath(p, OUT)))
            z.write(os.path.join(OUT, "README_КАК_ВЫКЛАДЫВАТЬ.txt"), "V_OKOPE_Avito/README_КАК_ВЫКЛАДЫВАТЬ.txt")
        made.append((zp, len(gr)))
        print(f"\nархив: {os.path.basename(zp)} — {len(gr)} товаров, "
              f"{os.path.getsize(zp) / 1e6:.1f} МБ")

    if not only:
        zp = os.path.join(DIST, "V_OKOPE_avito_frontts_vsyo.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(OUT):
                for f in sorted(files):
                    p = os.path.join(root, f)
                    z.write(p, os.path.join("V_OKOPE_Avito", os.path.relpath(p, OUT)))
        print(f"архив: {os.path.basename(zp)} — {len(rows)} товаров, "
              f"{os.path.getsize(zp) / 1e6:.1f} МБ")

    json.dump(rows, open(os.path.join(HERE, "avito_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nпапок: {len(rows)}")


if __name__ == "__main__":
    main()
