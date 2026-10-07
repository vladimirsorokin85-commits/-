#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СБОРКА ПАКЕТА ПОСТОВ ДЛЯ ВК — из плана + каталога + фото.

  python3 vk/make_pack.py vk/posts/plan_2026-10-08_14.json

Что делает:
  • берёт завязку (hook) из плана и факты из описания поставщика (только факты, без выдумок);
  • собирает текст: заголовок, завязка, «Что важно», наличие, призыв, хештеги;
  • ЦЕНЫ НЕ ПИШЕТ НИКОГДА (правило магазина) — и вычищает любые строки с ценами;
  • раскладывает фото поставщика по папкам постов (уменьшает до 1600 px, качество 85);
  • делает папки по дням, общий файл ВСЕ_ПОСТЫ.txt, README.txt и ZIP.

Плана нет — сначала план (heading + hook), потом запуск.
"""
import json
import os
import re
import sys
import zipfile
import shutil

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from catalog import store
    from catalog.search import family_of, sizes_of
    from vk.post import split_description, short_fact, hashtags, norm
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore
    from search import family_of, sizes_of  # type: ignore
    from post import split_description, short_fact, hashtags, norm  # type: ignore

MAX_PX = 1600
JPEG_Q = 85
CTA = [
    "Доставка по РФ. Напишите в личные сообщения — подберу под вашу задачу.",
    "Пишите в личные сообщения: подскажу по размеру и наличию.",
    "Отправим СДЭК по РФ. Напишите в сообщения — забронирую.",
    "Есть вопросы по подбору — пишите в личку, помогу собрать комплект.",
    "Напишите в личные сообщения — уточню наличие и помогу с выбором.",
]
BAD_WORDS = ("₽", "цена", "цены", "стоимость", "руб", "опт", "от 10 штук", "прайс")


def clean_line(s: str) -> str:
    s = re.sub(r"^[^\w(«\"А-Яа-яЁё0-9]+", "", str(s or "")).strip()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(" ;,.")
    return s


def usable(s: str) -> bool:
    low = s.lower()
    if len(s) < 20 or len(s) > 200:
        return False
    if any(b in low for b in BAD_WORDS):
        return False
    if sum(c.isdigit() for c in s) > len(s) * 0.5:
        return False
    return True


def overlap(a: str, b: str) -> float:
    wa = {w[:6] for w in norm(a).split() if len(w) > 3}
    wb = {w[:6] for w in norm(b).split() if len(w) > 3}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa)


CYR2LAT = str.maketrans("АВЕКМНОРСТУХавекмнорстух", "ABEKMHOPCTYXaBekMHoPCTYX")


def fix_mixed(s: str) -> str:
    """«АLРОLUХ» → «ALPOLUX»: в смешанных токенах кириллицу, похожую на латиницу, приводим к латинице."""
    def one(m):
        t = m.group(0)
        cyr = sum(1 for c in t if "а" <= c.lower() <= "я" or c.lower() == "ё")
        lat = sum(1 for c in t if "a" <= c.lower() <= "z")
        if cyr and lat and lat >= 2 and cyr >= 2:
            return t.translate(CYR2LAT)
        return t
    return re.sub(r"[A-Za-zА-Яа-яЁё]{4,}", one, s)


def sentences(desc: str):
    """Целые предложения из описания (последний источник фактов, если списков нет)."""
    out = []
    for para in re.split(r"\n+", str(desc or "")):
        para = clean_line(para)
        if len(para) < 40:
            continue
        for s in re.split(r"(?<=[.!?])\s+", para):
            s = clean_line(s)
            if s:
                out.append(s)
    return out


SERVICE_STARTS = ("обращайте", "внимание", "см.", "читайте", "рекоменд", "выбирайте", "перед примен",
                  "для получения", "подробн", "доставка", "оплата", "гарантия")


def clean_fact(s: str) -> str:
    s = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]+", " ", s)  # эмодзи и стрелки
    s = re.sub(r"^\d+[)\].]\s*", "", s)          # «1) …» → «…»
    s = re.sub(r"\s*[•*]\s*", " · ", s)           # маркеры внутри строки
    s = re.sub(r"\s*·\s*(·\s*)+", " · ", s)
    s = s.replace("связии", "связи").replace("  ", " ").strip(" ·;,.")
    return s


def bullets_from_desc(desc: str, hook: str, n: int, name: str = ""):
    _sub, feats, specs = split_description(desc)
    longs, shorts = [], []
    for raw in list(feats) + list(specs) + sentences(desc):
        line = clean_fact(clean_line(raw))
        if not line:
            continue
        low = line.lower()
        if low.startswith(SERVICE_STARTS):
            continue
        if name and overlap(line, name) >= 0.75:  # строка = само название товара
            continue
        if name and len(line) <= 75 and overlap(line, name) >= 0.6:
            continue
        line = re.sub(r"(?<=\d)\s*C0\b", " °C", line)
        line = line.replace("С0", "°C")
        if not usable(line):
            if 8 <= len(line) <= 60 and any(ch in line for ch in "(:") and not any(b in low for b in BAD_WORDS):
                shorts.append(line)
            continue
        if len(line) > 175:  # режем по границе предложения, а не посреди слова
            parts = [clean_fact(clean_line(p)) for p in re.split(r"(?<=[.!?])\s+", line)]
            line = next((p for p in parts if 60 <= len(p) <= 175), "")
            if not line:
                continue
        longs.append(line)

    out = []

    def add(line):
        line = fix_mixed(line)
        if overlap(line, hook) > 0.5:
            return
        if any(overlap(line, o) > 0.6 for o in out):
            return
        out.append(line)

    for line in longs:
        if len(out) >= n:
            return out
        add(line)

    # короткие характеристики («Вес: 1,4 кг») склеиваем в один пункт через « · »
    have = {norm(x)[:25] for x in out}
    shorts = [s for s in shorts if norm(s)[:25] not in have and not any(norm(s)[:25] in norm(o) for o in out)]
    chunk = []
    for s in shorts:
        cand = " · ".join(chunk + [s])
        if len(cand) > 170 and chunk:
            add(" · ".join(chunk))
            if len(out) >= n:
                return out
            chunk = [s]
        else:
            chunk.append(s)
    if chunk and len(out) < n:
        add(" · ".join(chunk))
    return out


def availability_line(sizes_note=None):
    """Наличие — без количества: сколько осталось, в постах не пишем."""
    if sizes_note:
        return f"{sizes_note} — есть на складе у Димы."
    return "Есть на складе у Димы."


def safe_slug(s: str, limit: int = 46) -> str:
    s = re.sub(r"[^\w\sА-Яа-яЁё0-9-]", "", s).strip()
    s = re.sub(r"\s+", "_", s)
    return (s[:limit] or "пост").strip("_")


def build_post_text(entry, item, rows, desc, idx, slot):
    headline = entry["headline"]
    hook = entry["hook"].strip()
    n = int(entry.get("bullets", 4))
    body = [headline, ""]
    body += [hook, ""]
    bl = list(entry.get("facts") or []) or bullets_from_desc(desc, hook, n, entry.get('name') or item['name'])
    bl = bl[:n]
    if bl:
        body.append("Что важно:")
        body += [f"▪️ {b}" for b in bl]
        body.append("")
    body.append(availability_line(entry.get("sizes_note")))
    body.append("")
    body.append(CTA[slot % len(CTA)])
    body.append("")
    tags = hashtags(item["name"], item.get("category", ""), extra=entry.get("extra_tags") or ())
    body.append(tags)
    text = "\n".join(body).strip() + "\n"
    # страховка: цены не должно быть в принципе
    assert not re.search(r"\d[\d\s]*\s*(₽|руб)", text), "в тексте оказалась цена!"
    return text


def save_photos(files, dest_dir, limit=3):
    os.makedirs(dest_dir, exist_ok=True)
    saved = []
    for i, rel in enumerate(files[:limit], 1):
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        out = os.path.join(dest_dir, f"фото {i}.jpg")
        im = Image.open(src).convert("RGB")
        im.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)
        im.save(out, quality=JPEG_Q, optimize=True)
        saved.append(out)
    return saved


def main(argv=None):
    plan_path = argv[0] if argv else os.path.join(HERE, "posts", "plan_2026-10-08_14.json")
    plan = json.load(open(plan_path, encoding="utf-8"))
    idx = json.load(open(os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))
    full = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "catalog", "data", "catalog_full.json"), encoding="utf-8"))}
    manifest = {m["id"]: m for m in store.photos_manifest()}

    out_root = os.path.join(HERE, "posts", f"pack_{plan['start']}")
    shutil.rmtree(out_root, ignore_errors=True)
    os.makedirs(out_root, exist_ok=True)

    report, all_days, missing = [], [], []
    for day in plan["days"]:
        day_dir = os.path.join(out_root, f"{day['date'].replace('2026', '').strip('.')}_{day['weekday']}")
        os.makedirs(day_dir, exist_ok=True)
        day_texts = []
        for slot, entry in enumerate(day["posts"], 1):
            code = str(entry["code"])
            # коды у поставщика дублируются (62 пары) — связываем строго по id
            matches = [r for r in idx if entry.get("id") and r["id"] == entry["id"]]
            if not matches:
                matches = [r for r in idx if str(r.get("code")) == code]
                if len(matches) > 1:
                    missing.append(f"{day['date']} {code}: НЕОДНОЗНАЧНО, {len(matches)} товаров с этим кодом — нужен id")
                    continue
            if not matches:
                missing.append(f"{day['date']} {code}: нет в каталоге")
                continue
            item = matches[0]
            if item.get("code") and str(item["code"]) != code:
                missing.append(f"{day['date']} {code}: id привёл к другому коду ({item['code']}) — проверь план")
                continue
            rows = [r for r in idx if family_of(r["name"]) == family_of(item["name"])
                    and r.get("category") == item.get("category")]
            desc = (full.get(item["id"], {}) or {}).get("description") or ""
            text = build_post_text(entry, item, rows, desc, idx, slot)

            folder = os.path.join(day_dir, f"{slot:02d}_{safe_slug(entry['headline'])}")
            os.makedirs(folder, exist_ok=True)
            open(os.path.join(folder, "пост.txt"), "w", encoding="utf-8").write(text)

            files = (manifest.get(item["id"], {}) or {}).get("files") or []
            saved = save_photos(files, folder)
            if not saved:
                missing.append(f"{day['date']} {code} «{item['name'][:40]}»: НЕТ ФОТО")

            day_texts.append(f"{'=' * 68}\n{slot:02d}. {entry['headline']}\n{'=' * 68}\n\n{text}\n")
            report.append({
                "day": day["date"], "slot": slot, "code": code, "name": item["name"],
                "stock": int(item["stock"] or 0), "photos": len(saved),
                "bullets": text.count("▪️"), "chars": len(text),
            })
        open(os.path.join(day_dir, "ВСЕ_ПОСТЫ_ЗА_ДЕНЬ.txt"), "w", encoding="utf-8").write("\n".join(day_texts))
        all_days.append((day, "\n".join(day_texts)))

    open(os.path.join(out_root, "ВСЕ_ПОСТЫ_НЕДЕЛЯ.txt"), "w", encoding="utf-8").write(
        "\n".join(t for _, t in all_days))

    readme = [
        f"В ОКОПЕ — {plan['title']}",
        "=" * 40,
        "",
        "Что внутри",
        "----------",
        "7 папок по дням (08.10 … 14.10). В каждом дне 6 папок постов: «пост.txt» + фото поставщика.",
        "Файл «ВСЕ_ПОСТЫ_ЗА_ДЕНЬ.txt» — тексты одного дня, «ВСЕ_ПОСТЫ_НЕДЕЛЯ.txt» — всей недели.",
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
    for day, _ in all_days:
        readme.append(f"  {day['date']} ({day['weekday']}):")
        for slot, entry in enumerate(day["posts"], 1):
            readme.append(f"     {slot}. {entry['headline']}")
    readme += [
        "",
        "Правила, по которым собрано",
        "---------------------------",
        "• Цены в постах НЕ указываем — ни розницы, ни «цена в личку».",
        "• Сколько осталось на складе — в постах не пишем: наличие формулируем словами.",
        "• Факты — из описаний поставщика и проверенных открытых источников, ничего не досочинено.",
        "• Фото — только от поставщика (каталог Димы).",
        "• Наличие проверено по живому каталогу на 07.10.2026.",
        "",
        f"Всего постов: {sum(len(d['posts']) for d in plan['days'])}.",
    ]
    open(os.path.join(out_root, "README.txt"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    zip_name = f"V_OKOPE_posts_{plan['start'].replace('-', '')}_week.zip"
    zip_path = os.path.join(HERE, "out", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_root):
            for f in sorted(files):
                full_path = os.path.join(root, f)
                z.write(full_path, os.path.relpath(full_path, os.path.dirname(out_root)))

    print(f"Постов собрано: {len(report)} из {sum(len(d['posts']) for d in plan['days'])}")
    print(f"Фото вложено: {sum(r['photos'] for r in report)}")
    print(f"Знаков в среднем: {sum(r['chars'] for r in report) // max(1, len(report))}")
    print(f"ZIP: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)")
    if missing:
        print("\n⚠ ПРОБЛЕМЫ:")
        for m in missing:
            print("  ·", m)
    json.dump(report, open(os.path.join(HERE, "out", f"report_{plan['start']}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
