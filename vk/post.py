#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПОСТЫ ДЛЯ ВК «В ОКОПЕ» — генератор из каталога Димы.

Принципы (нарушать нельзя):
  • факты — ТОЛЬКО из описания поставщика, ничего не выдумываем;
  • фото — только из каталога поставщика (catalog/photos/…), никаких картинок из интернета;
  • ЦЕНЫ В ПОСТАХ ВК НЕ УКАЗЫВАЕМ (правило владельца от 07.10.2026):
    в текст поста цена не попадает никогда. Флаг --price только сохраняет
    вашу розницу в JSON рядом с постом — для вашей же записи;
  • в ПУБЛИКУЕМЫЙ текст внутренние формулировки не попадают: наличие — «В наличии.»;
    «у Димы», «на складе», поставщик — только для внутренних отчётов владельцу.

Примеры:
  python3 -m vk.post --query "ботинки прабос greyman" --price 24900
  python3 -m vk.post --query "перчатки" --limit 3 --template collection
  python3 -m vk.post --code 00895 --template product --out vk/out
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from catalog import store
    from catalog.search import search, group_families, money, norm
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore
    from search import search, group_families, money, norm  # type: ignore

OUT_DIR = os.path.join(HERE, "out")

SHOP_TAGS = ["#вокопе", "#магазинброни", "#экипировка", "#тактика"]
CATEGORY_TAGS = {
    "обувь": ["#обувь", "#ботинки", "#берцы"],
    "бронежилет": ["#бронежилет", "#броня", "#плитоноска"],
    "шлем": ["#шлем", "#каска"],
    "подсум": ["#подсумок", "#разгрузка", "#снаряжение"],
    "разгруз": ["#разгрузка", "#рпс", "#снаряжение"],
    "наушник": ["#наушники", "#связь", "#тактические_наушники"],
    "аптеч": ["#аптечка", "#медицина", "#ifak"],
    "рюкзак": ["#рюкзак", "#снаряжение"],
    "перчат": ["#перчатки", "#экипировка"],
    "рац": ["#рация", "#связь"],
    "фонар": ["#фонарь", "#снаряжение"],
    "нож": ["#ножи", "#экипировка"],
    "термо": ["#термобельё", "#экипировка"],
    "носк": ["#носки", "#экипировка"],
}


def clean(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or ""))
    return re.sub(r"[ \t]+", " ", s).strip()


def split_description(desc: str):
    """Описание поставщика -> (подзаголовок, особенности[], характеристики[])."""
    lines = [clean(x) for x in str(desc or "").split("\n")]
    lines = [x for x in lines if x]
    if not lines:
        return "", [], []
    subtitle = lines[0] if len(lines[0]) < 160 else ""
    feats, specs, mode = [], [], None
    for ln in lines[1:]:
        low = re.sub(r"^[^\w«\"А-Яа-яЁё0-9]+", "", ln).lower().rstrip(":")
        if low.startswith(("особенност", "преимуществ", "плюсы", "ключевые")):
            mode = "f"
            continue
        if low.startswith(("характеристик", "спецификац", "техническ", "комплектац", "состав")):
            mode = "s"
            continue
        if low.startswith(("рекомендац", "внимание", "!!!", "важно")):
            mode = None
            continue
        # срезаем маркеры списков: *, -, •, 🔘, ▪️, ✔ и прочие символы/эмодзи в начале строки
        item = re.sub(r"^[^\w(«\"А-Яа-яЁё0-9]+", "", ln).strip()
        if not item or item.endswith(":"):
            continue
        (feats if mode == "f" else specs if mode == "s" else feats).append(item)
    # чистим дубли, сохраняем порядок
    def uniq(xs):
        seen, out = set(), []
        for x in xs:
            k = norm(x)[:80]
            if k and k not in seen:
                seen.add(k)
                out.append(x)
        return out
    return subtitle, uniq(feats)[:6], uniq(specs)[:6]


def short_fact(s: str, limit: int = 150) -> str:
    s = clean(s)
    s = re.sub(r"^(и|а|но)\s+", "", s, flags=re.I)
    return s if len(s) <= limit else s[: limit - 1].rstrip(" ,;.") + "…"


def hashtags(name: str, category: str, extra=()):
    base = list(SHOP_TAGS) + list(extra)
    tags_by_name = [t for key, tags in CATEGORY_TAGS.items() if key in norm(name) for t in tags]
    base += tags_by_name or [t for key, tags in CATEGORY_TAGS.items() if key in norm(category) for t in tags]
    out = []
    for t in base:
        if t not in out:
            out.append(t)
    return " ".join(out[:10])


def availability_phrase(stock: int) -> str:
    """Для внутреннего отчёта владельцу (в пост не идёт)."""
    return "на складе у Димы" if stock > 0 else "НЕТУ на складе у Димы"


def stock_line(rows):
    """Строка про размеры/остатки по позициям одной модели."""
    from catalog.search import sizes_of
    parts = []
    for r in sorted(rows, key=lambda r: r["name"]):
        n = int(r.get("stock") or 0)
        if n <= 0:
            continue
        sizes = sizes_of(r["name"])
        parts.append(f"{sizes[0]} — {n} шт" if sizes else f"{n} шт")
    return " · ".join(parts)


def _repeats(line: str, name: str) -> bool:
    """Первую строку описания часто дублирует название — в пост её не тащим."""
    a, b = norm(line), norm(name)
    if a in b:
        return True
    words = [w for w in a.split() if len(w) > 3]
    if not words:
        return True
    hits = sum(1 for w in words if w[:5] in b)
    return hits / len(words) >= 0.6


def post_product(fam, price=None, sizes_show=True) -> str:
    rows = fam["rows"]
    row = rows[0]
    desc = row.get("_desc") or ""
    subtitle, feats, specs = split_description(desc)
    name = fam["family"] or row["name"]

    head = name
    body = []
    if subtitle and not _repeats(subtitle, name):
        body.append(subtitle)

    facts = [short_fact(f) for f in feats[:5]] or [short_fact(s) for s in specs[:5]]
    if facts:
        body.append("")
        body.append("Что важно:")
        for f in facts:
            body.append(f"▪️ {f}")

    if sizes_show:
        st = stock_line(rows)
        if st:
            body.append("")
            body.append(f"В наличии: {st}")

    body.append("")
    body.append("Доставка по РФ. Пишите в личные сообщения — подберём под вашу задачу.")
    body.append("")
    body.append(hashtags(name, row.get("category", "")))
    return f"🪖 {head}\n" + "\n".join(body)


def post_collection(fams, price_map=None) -> str:
    lines = ["🪖 Подборка из наличия", ""]
    for i, fam in enumerate(fams, 1):
        rows = fam["rows"]
        st = stock_line(rows)
        lines.append(f"{i}. {fam['family']}")
        if st:
            lines.append(f"   в наличии: {st}")
    lines += ["", "Всё в наличии. Пишите в личку — забронирую и отправим СДЭК.",
              "", hashtags(" ".join(f["family"] for f in fams), " ".join(f["category"] for f in fams))]
    return "\n".join(lines)


def post_stock(fams) -> str:
    lines = ["🪖 Что есть в наличии сейчас", ""]
    for fam in fams:
        st = stock_line(fam["rows"])
        if st:
            lines.append(f"▪️ {fam['family']}: {st}")
    lines += ["", "Всё в наличии. Пишите в личку — подскажу по размеру.",
              "", hashtags(" ".join(f["family"] for f in fams), " ".join(f["category"] for f in fams))]
    return "\n".join(lines)


def slugify(s: str, limit: int = 48) -> str:
    s = norm(s)
    s = re.sub(r"[^0-9a-zа-я]+", "-", s).strip("-")
    return (s[:limit] or "post")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Генератор постов для ВК из каталога «В ОКОПЕ»")
    ap.add_argument("--query", default="", help="слова запроса по каталогу")
    ap.add_argument("--code", help="код товара у поставщика")
    ap.add_argument("--id", dest="pid", help="id товара")
    ap.add_argument("--price", type=float,
                    help="розница ВЛАДЕЛЬЦА — только для вашей записи в JSON; в текст поста НЕ попадает")
    ap.add_argument("--limit", type=int, default=1, help="сколько позиций (для подборки)")
    ap.add_argument("--template", choices=["product", "collection", "stock"], default="product")
    ap.add_argument("--photo-limit", type=int, default=3, help="сколько фото приложить")
    ap.add_argument("--out", default=OUT_DIR, help="куда писать результат")
    args = ap.parse_args(argv)

    rows, meta = store.load_index()
    full = store.full_by_id()
    photos = store.photos_by_id()

    if args.code or args.pid:
        rows = [r for r in rows if (r["id"] == args.pid or str(r.get("code")) == str(args.code))]
        if not rows:
            print("Товар не найден по коду/id."); return 1
        hits = search("", rows=rows, full=full)
    else:
        if not args.query:
            print("Нужен --query, --code или --id."); return 2
        hits = search(args.query, rows=rows, full=full, photos=photos)

    fams = group_families(hits)[: args.limit]
    if not fams:
        print("НИЧЕГО НЕ НАЙДЕНО — уточни запрос."); return 1

    if args.template == "collection":
        text = post_collection(fams)
    elif args.template == "stock":
        text = post_stock(fams)
    else:
        text = post_product(fams[0], price=args.price)

    # фото для поста: только годные (без полосок-сеток и превью)
    man = {m["id"]: m for m in store.photos_manifest()}
    photo_files, poor = [], []
    for fam in fams:
        for r in fam["rows"]:
            for f in r.get("_photos", []):
                det = next((d for d in (man.get(r["id"], {}).get("details") or []) if d["path"] == f), None)
                if det and det.get("quality", "ok") != "ok":
                    poor.append(f)
                    continue
                if f not in photo_files:
                    photo_files.append(f)
    photo_files = photo_files[: args.photo_limit]

    os.makedirs(args.out, exist_ok=True)
    base = slugify(fams[0]["family"] if args.template == "product" else (args.query or "подборка"))
    txt_path = os.path.join(args.out, f"{base}.txt")
    json_path = os.path.join(args.out, f"{base}.json")
    open(txt_path, "w", encoding="utf-8").write(text + "\n")
    payload = {
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "template": args.template,
        "source": store.source_line(meta),
        "text": text,
        "photos": photo_files,
        "price": args.price,
        "products": [{"name": f["family"], "codes": f["codes"], "category": f["category"],
                      "stock": f["total_stock"], "purchase": f["price_min"]} for f in fams],
    }
    json.dump(payload, open(json_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

    print(text)
    print("\n" + "—" * 40)
    print(f"Источник: {store.source_line(meta)}")
    print(f"Текст: {txt_path}")
    if poor:
        print(f"Отброшено {len(poor)} фото как непригодные (полоски/превью): " + ", ".join(poor))
    if photo_files:
        print("Фото для поста (загрузи в ВК):")
        for p in photo_files:
            print(f"  · {p}")
    else:
        print("⚠ Фото по этой позиции не выкачаны. Добавь товар в catalog/requests/photos.json "
              "(или укажи его код) — workflow притянет фото поставщика, потом повтори пост.")
    if args.price:
        print("ℹ Цена записана только в JSON (для вашей записи). В текст поста она не попала — "
              "правило магазина: в постах ВК цены не указываем.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
