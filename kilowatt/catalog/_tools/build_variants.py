# -*- coding: utf-8 -*-
"""Собирает variant-2.html из index.html (вариант 2 — «Зона защиты»).
Один движок/данные, два оформления. Запускать после правок index.html.
"""
import os

CAT = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt\catalog"
SRC = os.path.join(CAT, "index.html")
DST = os.path.join(CAT, "variant-2.html")

html = open(SRC, encoding="utf-8").read()

repl = [
    ('<link rel="stylesheet" href="assets/css/theme-field.css">',
     '<link rel="stylesheet" href="assets/css/theme-quiet.css">'),
    ('<body class="theme-field" data-theme="field" data-alt="variant-2.html">',
     '<body class="theme-quiet" data-theme="quiet" data-alt="index.html">'),
    ("Станции РЭБ «Капюшон» — каталог НПО «Киловатт» · «В ОКОПЕ»",
     "Станции РЭБ «Капюшон» — каталог НПО «Киловатт» · «В ОКОПЕ» · вариант 2"),
]
for a, b in repl:
    if a not in html:
        raise SystemExit("не найден фрагмент: " + a[:60])
    html = html.replace(a, b)

open(DST, "w", encoding="utf-8").write(html)
print("variant-2.html:", len(html), "байт")
