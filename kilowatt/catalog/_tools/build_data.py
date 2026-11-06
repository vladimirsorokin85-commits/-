# -*- coding: utf-8 -*-
"""Сборка данных для HTML-каталога: products.json -> catalog/assets/js/data.js + фото."""
import json
import os
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageFilter

K = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt"
CAT = os.path.join(K, "catalog")
DATA = os.path.join(K, "data")
SITE = os.path.join(K, "_tools", "out", "site")
OUT_JS = os.path.join(CAT, "assets", "js", "data.js")
PHOTO_DIR = os.path.join(CAT, "assets", "img", "products")

CATEGORY_ORDER = [
    "Купольные станции", "Переносные (рюкзаки)", "Стационарные",
    "Детекторы БПЛА", "Доп. модули", "Аксессуары",
]

SITE_CAT_MAP = {
    "legkovye": "Купольные · легковые",
    "gruzovye": "Купольные · грузовые",
    "bronetehnika": "Купольные · бронетехника",
    "perenosnye": "Переносные (рюкзаки)",
    "staczionarny": "Стационарные",
    "aksessuary": "Аксессуары",
    "dop_modul": "Доп. модули",
}

FLAGSHIP_SLUGS = ("k-12m", "rebus-4", "shtora-k12-700", "shtora-k-12-700")
FLAGSHIP_IDS = ("stancziya-reb-kapyushon-k-12m", "kompleks-reb-rebus-4", "stancziya-reb-shtora-k12-700")


def js_safe(obj):
    s = json.dumps(obj, ensure_ascii=False, indent=1)
    # защита от </script>
    return s.replace("</", "<\\/")


def white_to_alpha(img, threshold=238):
    """Убирает фон, связанный с краями (студийное фото на белом/светлом), сохраняя светлое внутри изделия.
    Тон фона берётся по углам, поэтому работает и на слегка сером/бежевом фоне."""
    im = img.convert("RGB")
    w, h = im.size
    scale = min(1.0, 360.0 / max(w, h))
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    small = np.asarray(im.resize((sw, sh), Image.BILINEAR)).astype(np.int16)
    # цвет фона — медиана по четырём углам
    corners = np.array([small[0, 0], small[0, -1], small[-1, 0], small[-1, -1]])
    bgcol = np.median(corners, axis=0)
    diff = np.abs(small - bgcol).max(axis=2)
    light = small.min(axis=2) >= 226
    near_bg = (diff <= 24) | light
    seed = np.zeros_like(near_bg)
    seed[0, :] = near_bg[0, :]
    seed[-1, :] = near_bg[-1, :]
    seed[:, 0] = near_bg[:, 0]
    seed[:, -1] = near_bg[:, -1]
    bg = seed.copy()
    for _ in range(max(sw, sh) + 4):
        grown = bg.copy()
        grown[1:, :] |= bg[:-1, :]
        grown[:-1, :] |= bg[1:, :]
        grown[:, 1:] |= bg[:, :-1]
        grown[:, :-1] |= bg[:, 1:]
        grown &= near_bg
        if np.array_equal(grown, bg):
            break
        bg = grown
    mask_small = Image.fromarray((bg * 255).astype(np.uint8), "L")
    mask = mask_small.resize((w, h), Image.BILINEAR)
    # убираем 1px белый ореол по краю (дефринж), потом мягко размываем
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    rgba = img.convert("RGBA")
    alpha = np.asarray(mask).astype(np.int16)
    arr = np.asarray(rgba).copy()
    arr[:, :, 3] = np.clip(255 - alpha, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getbbox()
    return out.crop(bbox) if bbox else out


def copy_photos(products):
    """Копирует фото из data/photos в catalog/assets/img/products: resize, белый фон -> альфа, WebP."""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    result = {}
    for p in products:
        slug = p["slug"]
        src_dir = os.path.join(DATA, "photos", slug)
        dst_dir = os.path.join(PHOTO_DIR, slug)
        rel = []
        if os.path.isdir(src_dir):
            os.makedirs(dst_dir, exist_ok=True)
            files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
            for i, f in enumerate(files, 1):
                dst = os.path.join(dst_dir, f"{i:02d}.webp")
                try:
                    im = Image.open(os.path.join(src_dir, f))
                    im.thumbnail((1200, 1200), Image.LANCZOS)
                    if im.mode in ("RGBA", "LA") and im.getextrema()[3][0] < 250:
                        out = im.convert("RGBA")
                    else:
                        out = white_to_alpha(im)
                    out.save(dst, "WEBP", quality=86, method=6)
                    rel.append(f"assets/img/products/{slug}/{i:02d}.webp")
                except Exception as e:  # noqa
                    print("фото не обработано:", slug, f, e)
        result[slug] = rel
    return result


def normalize_from_data():
    p = os.path.join(DATA, "products.json")
    if not os.path.exists(p):
        return None
    raw = json.load(open(p, encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("products") or raw.get("items") or []
    out = []
    for i, it in enumerate(raw):
        slug = (it.get("slug") or it.get("id") or f"item-{i}").strip()
        name = (it.get("name") or it.get("title") or "").strip()
        if not name:
            continue
        cat = it.get("category") or "Без категории"
        out.append({
            "id": it.get("id") or slug,
            "slug": re.sub(r"[^a-z0-9\-]+", "-", slug.lower()).strip("-") or f"item-{i}",
            "name": name,
            "category": cat,
            "on_site": it.get("on_site", True),
            "flagship": bool(it.get("flagship")),
            "manufacturer": it.get("manufacturer") or "НПО «Киловатт»",
            "price_dima": it.get("price_dima"),
            "price_variants": it.get("price_variants") or [],
            "price_source": it.get("price_source") or "Ховрино / Дима, ноябрь 2026",
            "availability": it.get("availability") or "уточняется",
            "short": it.get("short") or "",
            "description": it.get("description") or "",
            "specs": [s for s in (it.get("specs") or []) if s.get("label") or s.get("value")],
            "photos": [],
            "source_urls": it.get("source_urls") or [],
            "warnings": it.get("warnings") or [],
        })
    return out


def normalize_from_site():
    """Запасной вариант: официальный каталог сайта без цен (для проверки вёрстки)."""
    raw = json.load(open(os.path.join(SITE, "products.json"), encoding="utf-8"))
    out = []
    for slug, p in raw.items():
        cats = p.get("categories") or []
        cat = "Детекторы БПЛА" if "signal" in slug else (SITE_CAT_MAP.get(cats[0], "Без категории") if cats else "Без категории")
        desc = (p.get("description") or "").replace("\r", "").strip()
        short = ""
        for line in desc.split("\n"):
            line = line.strip()
            if 40 < len(line) < 220 and not line.lower().startswith(("характеристик", "техническ", "комплект", "описан")):
                short = line
                break
        specs = []
        for line in desc.split("\n"):
            line = line.strip(" •\t")
            m = re.match(r"^([А-Яа-яЁёA-Za-z][^:]{2,44}):\s*(.+)$", line)
            if m and len(specs) < 12:
                specs.append({"label": m.group(1).strip(), "value": m.group(2).strip()[:180]})
        if not specs:
            for kw in ("диапазон", "мощност", "дальност", "частот", "питани", "вес", "габарит", "время работ"):
                pass
        out.append({
            "id": slug, "slug": slug, "name": p.get("title") or slug, "category": cat,
            "flagship": any(f in slug for f in FLAGSHIP_SLUGS),
            "manufacturer": "НПО «Киловатт»",
            "price_dima": None, "price_variants": [],
            "price_source": "уточняется у поставщика",
            "availability": "уточняется",
            "short": short, "description": desc[:1600], "specs": specs,
            "photos": [], "source_urls": [p.get("url", "")], "warnings": [],
        })
    return out


def apply_overrides(products):
    """Накладывает ручные правки (паспортные ТТХ, ориентиры цен, тексты флагманов)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overrides.json")
    if not os.path.exists(p):
        return products
    ov = json.load(open(p, encoding="utf-8"))
    flags = set(ov.get("flagships") or [])
    per = ov.get("products") or {}
    for it in products:
        slug = it["slug"]
        if slug in per:
            patch = per[slug]
            for k, v in patch.items():
                if k == "specs":
                    it["specs"] = v
                elif k == "warnings":
                    it.setdefault("warnings", [])
                    for w in v:
                        if w not in it["warnings"]:
                            it["warnings"].append(w)
                else:
                    it[k] = v
        if flags:
            it["flagship"] = slug in flags
    return products


def remap_categories(products):
    """Единая таксономия каталога вместо «категорий сайта» (которые пересекаются)."""
    for p in products:
        s = p["slug"].lower()
        if "ryukzak" in s or "tp-4" in s or "tp-7" in s or "tp-8" in s or "tp-10" in s:
            p["category"] = "Переносные (рюкзаки)"
        elif "modul-fpv" in s:
            p["category"] = "Доп. модули"
        elif "signal" in s:
            p["category"] = "Детекторы БПЛА"
        elif "rebus" in s or "shtora" in s or "pole-31" in s:
            p["category"] = "Стационарные"
        elif any(k in s for k in ("blok-", "istochnik", "kronshtejn", "preobrazovatel",
                                  "razvetvitel", "stojka", "pribor-", "bur-", "kommutator")):
            p["category"] = "Аксессуары"
        elif "kapyushon" in s or "fpv-" in s:
            p["category"] = "Купольные станции"
    return products


def main():
    products = normalize_from_data()
    mode = "data/products.json"
    if products is None:
        products = normalize_from_site()
        mode = "site fallback (без цен)"
        print("ВНИМАНИЕ: data/products.json ещё нет — запасной режим с сайта.")
    products = apply_overrides(products)
    products = remap_categories(products)
    # фото
    if os.path.isdir(PHOTO_DIR):
        shutil.rmtree(PHOTO_DIR)
    photo_map = copy_photos(products)
    for p in products:
        p["photos"] = photo_map.get(p["slug"], [])
    # порядок категорий
    def cat_key(p):
        try:
            return CATEGORY_ORDER.index(p["category"])
        except ValueError:
            return 99
    products.sort(key=lambda p: (0 if p["flagship"] else 1, cat_key(p), p["name"]))
    # hero-фото К-12М
    hero_src = None
    for p in products:
        if "k-12m" in p["slug"] and p["photos"]:
            hero_src = p["photos"][0]
            break
    if hero_src:
        src = os.path.join(CAT, "assets", "img", hero_src.split("assets/img/")[-1])
        dst = os.path.join(CAT, "assets", "img", "hero-k12m.png")
        try:
            Image.open(src).convert("RGBA").save(dst, "PNG", optimize=True)
            print("hero:", dst)
        except Exception as e:  # noqa
            print("hero не скопирован:", e)
    # заявки: у флагманов точно есть цена
    stats = {
        "total": len(products),
        "with_price": sum(1 for p in products if p["price_dima"]),
        "with_photo": sum(1 for p in products if p["photos"]),
        "flagships": sum(1 for p in products if p["flagship"]),
    }
    payload = {
        "generated": "06.11.2026",
        "mode": mode,
        "stats": stats,
        "products": products,
    }
    os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("/* АВТОГЕНЕРАЦИЯ: build_data.py. Не редактировать вручную. */\n")
        f.write("window.CATALOG = " + js_safe(payload) + ";\n")
    # промежуточный JSON для печатной версии и других сборок
    build_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "catalog_build.json")
    os.makedirs(os.path.dirname(build_path), exist_ok=True)
    json.dump(payload, open(build_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # корректорские правки типографики не должны теряться при пересборке
    try:
        import apply_copy_edits as tp
        tp.apply_to_file(OUT_JS, "data.js")
    except Exception as e:  # noqa
        print("[typography] пропущено:", e)
    print("data.js:", OUT_JS)
    print("catalog_build.json:", build_path)
    print("stats:", stats)


if __name__ == "__main__":
    main()
