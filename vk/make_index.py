#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИТРИНА vk/dist — одна страница со всем, что готово к выкладке.

  python3 vk/make_index.py

Собирает index.html: комплекты (карточка + пост + позиции по отдельности) и
недельные/дневные архивы постов. Владелец открывает страницу на планшете
и качает нужное одним тапом.
"""
import glob
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(HERE, "dist")

KIT_TITLES = {
    "shturmovik": ("Комплект «ШТУРМОВИК»", "Плитник + шлем + наушники + аптечка, подсумок, перчатки, пояс"),
    "medik": ("Комплект «МЕДИК»", "Сумка-фельдшерская + аптечка + жгут + бинт + турникет + носилки"),
    "zima": ("Комплект «ЗИМА»", "Ботинки -40°, термобельё, термоноски, балаклава, шапка, перчатки"),
}


def day_title(name):
    m = re.match(r"V_OKOPE_(\d{2}\.\d{2})_(.+)\.zip$", name)
    if m:
        return f"{m.group(1)} ({m.group(2)})"
    return name


def card(href, title, sub, size_mb, badge=""):
    b = f'<span class="badge">{html.escape(badge)}</span>' if badge else ""
    return (f'<a class="card" href="{html.escape(href)}">{b}'
            f'<span class="t">{html.escape(title)}</span>'
            f'<span class="s">{html.escape(sub)}</span>'
            f'<span class="z">{size_mb:.1f} МБ</span></a>')


def main():
    os.makedirs(DIST, exist_ok=True)
    files = {os.path.basename(p): os.path.getsize(p) for p in glob.glob(os.path.join(DIST, "*"))}

    kits = [f for f in sorted(files) if f.startswith("V_OKOPE_kit_")]
    week = [f for f in sorted(files) if f.startswith("V_OKOPE_posts_")]
    days = [f for f in sorted(files) if re.match(r"V_OKOPE_\d{2}\.\d{2}_", f)]

    tuning = [f for f in sorted(files) if f.startswith("V_OKOPE_mgultra_")]
    kit_cards = ""
    for f in kits:
        slug = f[len("V_OKOPE_kit_"):-4]
        title, sub = KIT_TITLES.get(slug, (slug, "карточка + пост + позиции по отдельности"))
        kit_cards += card(f, title, sub, files[f] / 1024 / 1024, badge="слайды")
    tuning_cards = "".join(card(f, "Тюнинг: ДТКП MG Ultra — 5 постов",
                                "дульные тормоза-компенсаторы закрытого типа, фото поставщика",
                                files[f] / 1024 / 1024, badge="новое") for f in tuning)
    day_cards = "".join(card(f, day_title(f), "6 постов: фото + текст + чек-лист",
                             files[f] / 1024 / 1024) for f in days)
    week_cards = "".join(card(f, "Вся неделя 08–14.10", "42 поста одним архивом",
                              files[f] / 1024 / 1024, badge="всё сразу") for f in week)

    page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>В ОКОПЕ — материалы для выкладки</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0f1115;color:#eaeaea;margin:0;padding:20px;max-width:900px}}
 h1{{font-size:23px;margin:0 0 4px}} h2{{font-size:16px;color:#cbd5e1;margin:26px 0 10px;font-weight:600}}
 p.sub{{color:#9aa0a6;margin:0 0 6px;font-size:14px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}}
 a.card{{display:block;background:#1a1d24;border:1px solid #2a2f3a;border-radius:12px;
   padding:14px;text-decoration:none;color:#eaeaea;position:relative}}
 a.card span{{display:block}} .t{{font-weight:600;font-size:15px}} .s{{color:#9aa0a6;font-size:13px;margin-top:4px}}
 .z{{color:#6b7280;font-size:12px;margin-top:6px}}
 .badge{{position:absolute;top:12px;right:12px;background:#2b6cb0;color:#fff;font-size:11px;
   padding:2px 8px;border-radius:9px}}
 .note{{margin-top:24px;color:#9aa0a6;font-size:13px;line-height:1.55}}
</style></head><body>
<h1>В ОКОПЕ — материалы для выкладки</h1>
<p class="sub">Скачивайте нужное и публикуйте. Внутри — фото поставщика и готовый текст.</p>
<h2>Комплекты (слайды для карусели + карточка + пост)</h2>
<div class="grid">{kit_cards or '<p class="sub">Пока пусто</p>'}</div>
<h2>Тюнинг (MG Ultra — ДТКП)</h2>
<div class="grid">{tuning_cards or '<p class="sub">Пока пусто</p>'}</div>
<h2>Посты по дням</h2>
<div class="grid">{week_cards}{day_cards or '<p class="sub">Пока пусто</p>'}</div>
<div class="note">В архивах комплектов: папка «слайды» — готовая карусель (01…10.jpg, листайте по порядку),
«карточка.jpg» (один визуал, если удобнее им), «пост.txt» (текст про комплект),
папка «по_отдельности» (тексты по каждой позиции) и «карточка.json».
В архивах дней: папки постов с фото, обложкой и текстом, плюс чек-лист.<br>
Цены в текстах не публикуются; на карточках стоят те, что дали вы.</div>
</body></html>"""
    out = os.path.join(DIST, "index.html")
    open(out, "w", encoding="utf-8").write(page)
    print("витрина:", out)
    print("  комплектов:", len(kits), "| дневных архивов:", len(days), "| недельных:", len(week))


if __name__ == "__main__":
    main()
