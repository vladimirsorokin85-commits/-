#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Публичная страница каталога поставщика (b2b.moysklad.ru/public/<key>/catalog).

Задача: найти, откуда публичный каталог (SPA «Online order») берёт данные и
фото товаров — в частности, фото линейки VELES, которых нет в getFullImages.

Шаги:
  1. качаем поисковую выдачу и корень каталога (как раньше);
  2. качаем JS-бандл SPA и PWA-манифест, сохраняем;
  3. greп-эвристика по бандлу: api/image/catalog/item эндпоинты и URL — в findings-файл;
  4. качаем все JS-чанки, на которые ссылается бандл, и greп их тоже;
  5. пробуем эвристические эндпоинты (catalog.json, api/catalog, images-варианты
     desktop-api) — ответы сохраняем как есть.

Запускается из .github/workflows/catalog-fetch.yml шагом после remote_fetch.py
(тогда catalog/data/catalog_full.json уже свежий). Шаг continue-on-error.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_fetch import BASE, DATA, http, log  # noqa: E402

KEY = BASE.rstrip("/").rsplit("/", 1)[-1]
HOST = "https://b2b.moysklad.ru"
PUB = f"{HOST}/public/{KEY}"

BASIC_TARGETS = [
    ("public_search_veles.html", f"{PUB}/catalog?searchBy=Veles"),
    ("public_catalog_root.html", f"{PUB}/catalog"),
    ("api_search_veles.json", f"{BASE}/products.json?search=Veles&limit=100"),
]

GUESS_TARGETS = [
    ("guess_catalog_json.json", f"{PUB}/catalog.json?searchBy=Veles"),
    ("guess_api_catalog.json", f"{PUB}/api/catalog?searchBy=Veles"),
    ("guess_items.json", f"{PUB}/items?searchBy=Veles"),
]

PATTERNS = [
    r'"/api/[^"]{0,140}"',
    r'"/public/[^"]{0,140}"',
    r'https?://[a-z0-9.-]+[^"\'\s]{0,140}',
    r'"/[a-z0-9/_-]*image[a-z0-9/_-]*"',
    r'"/[a-z0-9/_-]*catalog[a-z0-9/_-]*"',
    r'"/[a-z0-9/_-]*item[a-z0-9/_-]*"',
    r'"/[a-z0-9/_-]*product[a-z0-9/_-]*"',
    r'"/[a-z0-9/_-]*search[a-z0-9/_-]*"',
]


def save(name, txt):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt if isinstance(txt, str) else txt.decode("utf-8", "replace"))
    return path


def fetch(url, timeout=30):
    st, txt = http(url, timeout=timeout)
    return st, txt


def grep_endpoints(js, findings, seen):
    for pat in PATTERNS:
        for x in re.findall(pat, js):
            x = x.strip('"')
            if x not in seen:
                seen.add(x)
                findings.append(x)


def main():
    os.makedirs(DATA, exist_ok=True)

    # 1) базовые страницы и api-поиск
    for name, url in BASIC_TARGETS:
        st, txt = fetch(url)
        if st == 200 and txt:
            save(name, txt)
            log(f"  {name}: ок, {len(txt)} символов")
        else:
            log(f"  {name}: status={st}")

    # 2) JS-бандл SPA
    st, shell = fetch(f"{PUB}/catalog?searchBy=Veles")
    bundle_urls = []
    if st == 200 and shell:
        m = re.search(r'src="(/assets/[^"]+\.js)"', shell)
        if m:
            bundle_urls.append(HOST + m.group(1))
        m = re.search(r'href="(/assets/manifest-[^"]+\.json)"', shell)
        if m:
            st2, mani = fetch(HOST + m.group(1))
            if st2 == 200 and mani:
                save("public_pwa_manifest.json", mani)
                log(f"  PWA-манифест: ок, {len(mani)} символов")
    findings, seen = [], set()
    chunks = []
    for burl in bundle_urls:
        st, js = fetch(burl, timeout=60)
        if st != 200 or not js:
            log(f"  бандл {burl}: status={st}")
            continue
        save("public_spa_bundle.js", js)
        log(f"  бандл: ок, {len(js)} символов → public_spa_bundle.js")
        grep_endpoints(js, findings, seen)
        for c in re.findall(r'["\'](/assets/[^"\']+\.js)["\']', js):
            c = HOST + c
            if c not in chunks and c not in bundle_urls:
                chunks.append(c)
    # 4) чанки (не больше 12 штук)
    for curl in chunks[:12]:
        st, js = fetch(curl, timeout=60)
        if st == 200 and js:
            save(f"public_spa_chunk_{len(os.listdir(DATA))}.js", js)
            grep_endpoints(js, findings, seen)
            log(f"  чанк {curl.rsplit('/', 1)[-1]}: ок, {len(js)} символов")
    save("public_spa_findings.txt", "\n".join(findings) + "\n")
    log(f"  findings: {len(findings)} строк → public_spa_findings.txt")

    # 3) эвристические эндпоинты
    for name, url in GUESS_TARGETS:
        st, txt = fetch(url)
        if st == 200 and txt:
            save(name, txt)
            log(f"  {name}: ок, {len(txt)} символов")
        else:
            log(f"  {name}: status={st}")

    # 5) image-эндпоинты desktop-api на примере одного товара VELES
    try:
        full = json.load(open(os.path.join(DATA, "catalog_full.json"), encoding="utf-8"))
        veles = next(p for p in full if "VELES" in (p.get("name") or ""))
        pid = veles["id"]
        log(f"  донор для image-эндпоинтов: {veles['name'][:50]} ({pid[:8]})")
        probes = [
            ("probe_getImages_put.txt", ("PUT", f"{BASE}/getImages", veles)),
            ("probe_images_json.txt", ("GET", f"{BASE}/images.json?id={pid}&limit=5", None)),
            ("probe_image_get.txt", ("GET", f"{BASE}/image?id={pid}", None)),
            ("probe_product_images.txt", ("GET", f"{BASE}/products/{pid}/images", None)),
            ("probe_getFullImages_put.txt", ("PUT", f"{BASE}/getFullImages", veles)),
        ]
        for name, (method, url, body) in probes:
            st, txt = fetch(url) if body is None else (lambda: http(url, method=method, body=body, timeout=60))()
            save(name, f"status={st}\n{str(txt)[:3000]}")
            log(f"  {name}: status={st}, {len(str(txt))} символов")
    except Exception as e:  # noqa: BLE001
        log(f"  image-пробы не удались: {e}")


if __name__ == "__main__":
    main()
