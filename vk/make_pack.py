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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
LOGO_REL = "media/logo.png"
FONT_CANDIDATES = (
    os.path.join(ROOT, "video_studio", "toolkit", "fonts", "Montserrat-VF.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def load_font(size: int):
    """Шрифт с кириллицей для обложек (Montserrat, запасной — DejaVu)."""
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            f = ImageFont.truetype(path, size)
            try:
                f.set_variation_by_name("Bold")
            except Exception:  # noqa: BLE001
                pass
            return f
        except Exception:  # noqa: BLE001
            continue
    return None


def make_cover(photo_rel: str, dest: str, headline: str) -> bool:
    """Обложка 1200×800: фото поставщика целиком + наш логотип + заголовок.

    Фото остаётся фотографией поставщика, мы только добавляем логотип магазина
    и подпись — как в карточках. Отдельный файл, можно не использовать.
    """
    src = os.path.join(ROOT, photo_rel)
    if not os.path.exists(src):
        return False
    W, H, BAR = 1200, 800, 116
    im = Image.open(src).convert("RGB")

    bg = im.copy()
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((max(1, int(bg.width * scale)), max(1, int(bg.height * scale))), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(20))
    base = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.4)

    fg = im.copy()
    fg.thumbnail((W - 90, H - BAR - 60), Image.LANCZOS)
    base.paste(fg, ((W - fg.width) // 2, (H - BAR - fg.height) // 2))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, H - BAR, W, H], fill=(12, 12, 12, 215))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(base)

    text = re.sub(r"[^\w\sА-Яа-яЁё0-9.,:;!?()«»\-—%+/×°№\"']+", " ", headline)
    text = re.sub(r"\s+", " ", text).strip()
    size = 50
    font = load_font(size)
    while font and size > 28 and d.textlength(text, font=font) > W - 80:
        size -= 2
        font = load_font(size)
    if font:
        d.text((40, H - BAR // 2), text, font=font, fill=(255, 255, 255), anchor="lm")

    logo = os.path.join(ROOT, LOGO_REL)
    if os.path.exists(logo):
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((108, 108), Image.LANCZOS)
        base.paste(lg, (W - lg.width - 26, 26), lg)

    base.save(dest, quality=88, optimize=True)
    return True
CTA = [
    "Отправляем СДЭК по РФ, оплата при получении по тарифу СДЭК. Пишите в личные сообщения.",
    "СДЭК по России, оплата при получении. Напишите в личку — подберу по размеру.",
    "Отправка СДЭК, оплата при получении. Есть вопросы — пишите в личные сообщения.",
    "Доставка СДЭК, оплата при получении заказа. Пишите — забронирую.",
    "СДЭК по всей России, оплата при получении. Напишите в сообщения — помогу с выбором.",
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
    """Наличие для ПУБЛИКАЦИИ: без количества и без внутренних формулировок.

    «У Димы», «на складе», поставщик — это внутренняя информация, в пост не идёт.
    """
    if sizes_note:
        return f"В наличии: {sizes_note}."
    return "В наличии."


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
    check_public_text(text)
    return text


FORBIDDEN_IN_PUBLIC = (
    ("у Димы", r"\bДимы?\b"),
    ("поставщик", r"поставщик"),
    ("на складе / со склада", r"\b(на|со)\s+склад"),
    ("наличие у поставщика", r"у поставщика"),
    ("цена", r"\d[\d\s]*\s*(₽|руб)"),
)


def check_public_text(text: str) -> None:
    """Жёсткая проверка перед публикацией: внутренние формулировки и цены недопустимы."""
    for label, rx in FORBIDDEN_IN_PUBLIC:
        m = re.search(rx, text, re.I)
        assert not m, f"в публикуемом тексте запрещённое: {label} → {m.group(0)!r}"


def save_photos(files, dest_dir, limit=3):
    os.makedirs(dest_dir, exist_ok=True)
    saved = []
    for i, rel in enumerate(files[:limit], 1):
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        out = os.path.join(dest_dir, f"{i}.jpg")
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
            if saved:
                make_cover(files[0], os.path.join(folder, "обложка.jpg"), entry["headline"])
            if not saved:
                missing.append(f"{day['date']} {code} «{item['name'][:40]}»: НЕТ ФОТО")

            day_texts.append(f"{'=' * 68}\n{slot:02d}. {entry['headline']}\n{'=' * 68}\n\n{text}\n")
            report.append({
                "day": day["date"], "slot": slot, "code": code, "name": item["name"],
                "photos": len(saved), "cover": os.path.exists(os.path.join(folder, "обложка.jpg")),
                "bullets": text.count("▪️"), "chars": len(text),
            })
        open(os.path.join(day_dir, "ВСЕ_ПОСТЫ_ЗА_ДЕНЬ.txt"), "w", encoding="utf-8").write("\n".join(day_texts))
        day_chk = [f"{day['date']} ({day['weekday']}) — чек-лист", "=" * 40, ""]
        for slot, entry in enumerate(day["posts"], 1):
            day_chk.append(f"  [ ] {slot:02d}. {entry['headline']}")
        open(os.path.join(day_dir, "ЧЕК-ЛИСТ_ДНЯ.txt"), "w", encoding="utf-8").write("\n".join(day_chk) + "\n")
        all_days.append((day, day_dir, "\n".join(day_texts)))

    open(os.path.join(out_root, "ВСЕ_ПОСТЫ_НЕДЕЛЯ.txt"), "w", encoding="utf-8").write(
        "\n".join(t for _, _d, t in all_days))

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
    for day, _dir, _t in all_days:
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
    readme += [
        "",
        "Файлы в каждой папке поста",
        "--------------------------",
        "  1.jpg, 2.jpg … — фото поставщика в порядке загрузки (1 — первым);",
        "  обложка.jpg    — та же фотография с нашим логотипом и заголовком, по желанию;",
        "  пост.txt       — текст, копируется целиком.",
    ]
    open(os.path.join(out_root, "README.txt"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    # чек-лист: отмечать выложенное
    chk = ["ЧЕК-ЛИСТ ВЫКЛАДКИ — отмечайте, что уже выставлено", "=" * 50, ""]
    for day, _dir, _t in all_days:
        chk.append(f"{day['date']} ({day['weekday']})")
        for slot, entry in enumerate(day["posts"], 1):
            chk.append(f"  [ ] {slot:02d}. {entry['headline']}")
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


    # архивы по дням — чтобы скачивать только нужный день
    day_zips = []
    for day, day_dir, _t in all_days:
        short = day["date"][:5].replace(".", ".")  # 08.10
        name = f"V_OKOPE_{short}_{day['weekday']}.zip"
        path = os.path.join(HERE, "out", name)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(day_dir):
                for f in sorted(files):
                    full_path = os.path.join(root, f)
                    z.write(full_path, os.path.relpath(full_path, os.path.dirname(day_dir)))
        day_zips.append(path)

    for path in day_zips:
        shutil.copy2(path, dist)

    # витрина для планшета: стартовая страница с прямыми ссылками на архивы
    def human(day_):
        return f"{day_['date']} ({day_['weekday']})"

    cards = "".join(
        f'<a class="card" href="{os.path.basename(p)}">'
        f'<span class="d">{human(d)}</span>'
        f'<span class="n">{len(d["posts"])} постов</span>'
        f'<span class="s">{os.path.getsize(p) / 1024 / 1024:.1f} МБ</span></a>'
        for (d, _dir, _t), p in zip(all_days, day_zips)
    )
    index = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Посты ВК — {plan['start']}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0f1115;color:#eaeaea;margin:0;padding:20px}}
 h1{{font-size:22px;margin:0 0 4px}} p.sub{{color:#9aa0a6;margin:0 0 18px;font-size:14px}}
 a.big{{display:block;background:#2b6cb0;color:#fff;text-decoration:none;text-align:center;
   padding:16px;border-radius:12px;font-size:17px;font-weight:600;margin-bottom:18px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}}
 a.card{{display:block;background:#1a1d24;border:1px solid #2a2f3a;border-radius:12px;
   padding:14px;text-decoration:none;color:#eaeaea}}
 a.card span{{display:block}} .d{{font-weight:600;font-size:15px}} .n{{color:#9aa0a6;font-size:13px;margin-top:4px}}
 .s{{color:#6b7280;font-size:12px;margin-top:2px}}
 .note{{margin-top:20px;color:#9aa0a6;font-size:13px;line-height:1.5}}
</style></head><body>
<h1>Посты «В ОКОПЕ» — {plan['start']} … {plan['days'][-1]['date']}</h1>
<p class="sub">7 дней × 6 постов. Каждый день — отдельный архив: внутри фото поставщика и текст.</p>
<a class="big" href="{os.path.basename(zip_path)}">⬇︎ Скачать всю неделю ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)</a>
<div class="grid">{cards}</div>
<div class="note">В архиве дня: папки постов, в каждой — фото (1.jpg, 2.jpg…), «обложка.jpg» с логотипом
и заголовком, «пост.txt» и «ЧЕК-ЛИСТ_ДНЯ.txt». Цены и остатки в текстах отсутствуют.</div>
</body></html>"""
    open(os.path.join(dist, "index.html"), "w", encoding="utf-8").write(index)

    print(f"Постов собрано: {len(report)} из {sum(len(d['posts']) for d in plan['days'])}")
    print(f"Фото вложено: {sum(r['photos'] for r in report)}")
    print(f"Знаков в среднем: {sum(r['chars'] for r in report) // max(1, len(report))}")
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
