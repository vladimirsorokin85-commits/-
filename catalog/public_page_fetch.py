#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Публичная страница каталога поставщика (b2b.moysklad.ru/public/<key>/catalog).

Запасной/диагностический канал: тянем выдачу поиска публичного каталога
(например, searchBy=Veles) и сохраняем сырые ответы в catalog/data/.
Зачем: если линейка есть на публичной странице, но не попадает в снапшот
desktop-api, по сырому HTML можно вытащить состав и id товаров.

Запускается из .github/workflows/catalog-fetch.yml шагом после remote_fetch.py.
Шаг помечен continue-on-error — диагностика не должна ронять основной fetch.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_fetch import BASE, DATA, http, log  # noqa: E402

KEY = BASE.rstrip("/").rsplit("/", 1)[-1]
PUB = f"https://b2b.moysklad.ru/public/{KEY}"

TARGETS = [
    ("public_search_veles.html", f"{PUB}/catalog?searchBy=Veles"),
    ("public_search_veles_ru.html", f"{PUB}/catalog?searchBy=%D0%92%D0%B5%D0%BB%D0%B5%D1%81"),
    ("public_catalog_root.html", f"{PUB}/catalog"),
    ("api_search_veles.json", f"{BASE}/products.json?search=Veles&limit=100"),
    ("api_search_veles_ru.json", f"{BASE}/products.json?search=%D0%92%D0%B5%D0%BB%D0%B5%D1%81&limit=100"),
]


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, url in TARGETS:
        st, txt = http(url, timeout=90)
        if st == 200 and txt:
            path = os.path.join(DATA, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt if isinstance(txt, str) else txt.decode("utf-8", "replace"))
            log(f"  {name}: ок, {len(txt)} символов")
        else:
            log(f"  {name}: status={st} — не сохранено")


if __name__ == "__main__":
    main()
