#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ГЕНЕРАТОР РЕКЛАМНЫХ БАННЕРОВ «В ОКОПЕ» × НПО «КИЛОВАТТ»

Читает banners/00_КОПИРАЙТ/banners_data.json и собирает 18×2 HTML:
  banners/html/B01_kapyushon_k8m_1080x1350.html
  banners/html/B01_kapyushon_k8m_1080x1080.html

Пока копирайта нет — берёт banners/_design/_demo_data.json (несколько моделей).

Запуск:
  python generator.py                       # автоданные: copy JSON, иначе demo
  python generator.py --data path.json      # указать JSON
  python generator.py --only B01,B08        # только модели
  python generator.py --layout-map ./_design/_demo_data.json  (не нужно)

Правила:
  — компановка по умолчанию: B01–B07 hero, B08–B12/B17/B18 split, B13–B16 numbers;
    можно переопределить полем "layout": "hero|split|numbers" в JSON;
  — размер заголовков/названия подбирается по длине текста автоматически;
  — экранирование HTML обязательное: копирайт может содержать «ёлочки» и &.
"""

import argparse
import html
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))          # banners/_design
BANNERS = os.path.dirname(ROOT)                             # banners
HTML_DIR = os.path.join(BANNERS, "html")
COPY_JSON = os.path.join(BANNERS, "00_КОПИРАЙТ", "banners_data.json")
DEMO_JSON = os.path.join(ROOT, "_demo_data.json")

THEMES = {"field", "quiet"}
FORMATS = [("1080x1350", "poster"), ("1080x1080", "square")]

# --- компановки по умолчанию -------------------------------------------------
LAYOUT_BY_ID = {}
for i in range(1, 8):
    LAYOUT_BY_ID["B%02d" % i] = "hero"      # транспорт: фото крупно по центру
for i in range(8, 13):
    LAYOUT_BY_ID["B%02d" % i] = "split"     # стационар / обнаружение: фото справа
for i in range(13, 19):
    LAYOUT_BY_ID["B%02d" % i] = "numbers"   # рюкзаки / питание / тестер: цифры в центре

LEGAL = ("Оборудование является радиоэлектронным средством. Порядок приобретения, "
         "регистрации и применения определяется законодательством РФ. Применение — "
         "только при наличии законного права. Характеристики — по паспорту изделия; "
         "дальность зависит от условий эксплуатации. Не является публичной офертой.")

TRANS = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text: str) -> str:
    out = []
    for ch in text.lower().replace("«", "").replace("»", ""):
        if ch in TRANS:
            out.append(TRANS[ch])
        elif ch.isalnum():
            out.append(ch)
        else:
            out.append("_")
    slug = re.sub(r"_+", "_", "".join(out)).strip("_")
    return slug or "banner"


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=False)


def pick_size(text: str, tiers):
    """tiers: [(max_len, class), ...] по возрастанию длины."""
    n = len(text or "")
    for max_len, cls in tiers:
        if n <= max_len:
            return cls
    return tiers[-1][1]


HEADLINE_TIERS = [(22, "b-headline--xl"), (30, "b-headline--l"),
                  (38, "b-headline--m"), (999, "b-headline--s")]
MODEL_TIERS = [(12, "b-model--xl"), (18, "b-model--l"),
               (26, "b-model--m"), (999, "b-model--s")]


def display_model(item) -> str:
    """Крупная акцентная строка: полное имя модели без «» и приписок в скобках.
    Если получается слишком длинно (>20 знаков) — берём name_short из копирайта."""
    model = str(item.get("model") or "").strip()
    short = str(item.get("name_short") or "").strip()
    clean = re.sub(r"\([^)]*\)", " ", model)
    clean = clean.replace("«", "").replace("»", "").replace("  ", " ").strip()
    clean = re.sub(r"\s+", " ", clean)
    if clean and len(clean) <= 20:
        return clean
    return short or clean or model


def resolve_photo(photo: str) -> str:
    """Ищет файл в _design/img: как есть, в cut/, в product/. Возвращает путь от html/."""
    img_root = os.path.join(ROOT, "img")
    photo = (photo or "").replace("\\", "/").lstrip("/")
    candidates = [photo]
    base = os.path.basename(photo)
    candidates += ["cut/" + base, "product/" + base]
    for rel in candidates:
        if os.path.isfile(os.path.join(img_root, rel)):
            return "../_design/img/" + rel
    raise FileNotFoundError("фото не найдено: %r (искал в %s)" % (photo, img_root))


def png_size(path):
    """Ширина/высота PNG без сторонних библиотек (IHDR)."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return None


def photo_orient(photo_rel):
    size = png_size(os.path.join(ROOT, "img", photo_rel))
    if not size or not size[1]:
        return "square", "1.4"
    w, h = size
    ar = w / h
    if ar > 1.22:
        orient = "land"
    elif ar < 0.82:
        orient = "port"
    else:
        orient = "square"
    return orient, ("%.3f" % ar)


def clean_stat_label(unit: str, label: str) -> str:
    """Убирает дублирование единицы в подписи: «8 каналов / каналов помех» → «8 каналов / помех»."""
    unit = (unit or "").strip()
    label = (label or "").strip()
    if not unit or not label:
        return label
    u = unit.lower()
    l = label.lower()
    if l == u:
        return ""
    if l.startswith(u):
        rest = label[len(unit):].strip(" ·—-—,:;")
        if rest:
            return rest
    return label


def tasks_html(tasks):
    """Чипы «ЗАДАЧИ» рядом с рекламной строкой (2–3 штуки)."""
    items = [str(t).strip() for t in (tasks or []) if str(t).strip()][:3]
    if not items:
        return ""
    chips = "".join('<span class="b-task">%s</span>' % esc(t) for t in items)
    return '<p class="b-tasks">%s</p>' % chips


def tech_html(tech):
    """Компактный техблок «КОРОТКО О МОДЕЛИ»: 4–6 строк ПАРАМЕТР → значение."""
    rows = []
    for it in (tech or [])[:6]:
        if not isinstance(it, dict):
            continue
        label = str(it.get("label") or "").strip()
        value = str(it.get("value") or "").strip()
        if not label or not value:
            continue
        row_cls = " b-tech__row--inline" if len(value) <= 4 else ""
        rows.append(
            '        <div class="b-tech__row%s">'
            '<span class="b-tech__k">%s</span>'
            '<span class="b-tech__v">%s</span>'
            "</div>" % (row_cls, esc(label), esc(value))
        )
    if not rows:
        return ""
    return (
        '    <section class="b-tech">\n'
        '      <p class="b-tech__head">Коротко о модели</p>\n'
        '      <div class="b-tech__grid">\n%s\n      </div>\n'
        "    </section>" % "\n".join(rows)
    )


def numbers_html(numbers):
    items = [n for n in (numbers or []) if str(n.get("value", "")).strip()][:4]
    if not items:
        raise ValueError("у баннера нет цифр-козырей (numbers)")
    if len(items) < 3:
        print("  ! предупреждение: цифр %d, лучше 3–4" % len(items), file=sys.stderr)
    n_class = "b-stats--4" if len(items) == 4 else "b-stats--3"
    rows = []
    for it in items:
        unit = str(it.get("unit") or "").strip()
        value = str(it.get("value") or "").strip()
        unit_html = "<em>%s</em>" % esc(unit) if unit else ""
        if any(ch.isdigit() for ch in value):
            long_cls = " b-stat__v--long" if len(value) >= 8 else ""
        else:
            long_cls = " b-stat__v--text"  # текстовый чип («АВТО») — не цифра
        rows.append(
            '      <div class="b-stat">\n'
            '        <span class="b-stat__v%s">%s%s</span>\n'
            '        <span class="b-stat__l">%s</span>\n'
            "      </div>" % (long_cls, esc(value), unit_html, esc(clean_stat_label(it.get("unit"), it.get("label"))))
        )
    return '<div class="b-stats %s">\n%s\n    </div>' % (n_class, "\n".join(rows))


PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<!--
  Рекламный баннер {bid} · {model}
  Формат: {fmt} · тема: .theme-{tone} · компоновка: {layout}
  Сгенерировано {gen} из {source}. Руками не править — менять JSON и перегенерировать.
-->
<link rel="stylesheet" href="../_design/tokens.css">
<link rel="stylesheet" href="../_design/banner.css">
</head>

<body class="theme-{tone}">

<main class="banner banner--{fmt_class} layout-{layout} theme-{tone} grain">

  <i class="b-tick b-tick--tl" aria-hidden="true"></i>
  <i class="b-tick b-tick--tr" aria-hidden="true"></i>
  <i class="b-tick b-tick--bl" aria-hidden="true"></i>
  <i class="b-tick b-tick--br" aria-hidden="true"></i>

  <header class="b-top">
    <div class="b-brand">
      <img src="../_design/img/brand/logo_w_word.png" alt="В ОКОПЕ — магазин брони">
    </div>
    <div class="b-issuer"><b>НПО «Киловатт»</b>производитель<br>{bid} · 11.2026</div>
  </header>

  <div class="b-body">

    <div class="b-intro">
      <p class="b-eyebrow">{audience}</p>
      <h1 class="b-headline {headline_cls}">{hook}</h1>
      <p class="b-model {model_cls}">{name_short}</p>
      <p class="b-line">{line}</p>
      {tasks}
    </div>

    <figure class="b-stage b-stage--{orient}" style="--photo-ar:{photo_ar}">
      <div class="b-plate">
        <img src="{photo}" alt="{model}">
      </div>
      <figcaption class="b-plate-cap">{caption}</figcaption>
      <div class="b-side">{side}</div>
    </figure>

    {numbers}

    {tech}

  </div>

  <footer class="b-foot">
    <div>
      <div class="b-cta-main"><span class="b-tg">@vokope_ru</span> <span>+7 (999) 136-71-42</span></div>
      <div class="b-cta-sub">Цена по запросу · Доставка по РФ · Самовывоз в Москве</div>
    </div>
    <div class="b-calc"><b>В ОКОПЕ</b>магазин брони<br>подбор и поставка</div>
  </footer>

  <p class="b-legal">{legal}</p>

</main>

</body>
</html>
"""


def build_item_html(item, fmt, fmt_class, source):
    tone = (item.get("tone") or "field").strip().lower()
    if tone not in THEMES:
        tone = "field"
    layout = (item.get("layout") or LAYOUT_BY_ID.get(item.get("id"), "hero")).strip().lower()
    if layout not in ("hero", "split", "numbers"):
        layout = "hero"
    hook = item.get("hook") or item.get("model") or ""
    name_short = display_model(item)
    model = item.get("model") or name_short
    bid = item.get("id") or "B00"
    title = "%s · %s · %s — «В ОКОПЕ»" % (bid, model, fmt)
    photo_rel = resolve_photo(item.get("photo")).replace("../_design/img/", "")
    orient, ar = photo_orient(photo_rel)
    return PAGE.format(
        orient=orient,
        photo_ar=ar,
        title=esc(title),
        bid=esc(bid),
        model=esc(model),
        tone=tone,
        layout=layout,
        fmt=fmt,
        fmt_class=fmt_class,
        audience=esc(item.get("audience") or ""),
        hook=esc(hook),
        name_short=esc(name_short),
        headline_cls=pick_size(hook, HEADLINE_TIERS),
        model_cls=pick_size(name_short, MODEL_TIERS),
        line=esc(item.get("line") or ""),
        photo=resolve_photo(item.get("photo")),
        caption=esc(item.get("caption") or model),
        side=esc(item.get("side") or "паспортные ТТХ · реальное фото"),
        numbers=numbers_html(item.get("numbers")),
        tasks=tasks_html(item.get("tasks")),
        tech=tech_html(item.get("tech")),
        legal=esc(LEGAL),
        gen="generator.py",
        source=os.path.basename(source),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="", help="JSON копирайта (по умолчанию — copy, иначе demo)")
    ap.add_argument("--out", default=HTML_DIR)
    ap.add_argument("--only", default="", help="через запятую: B01,B02")
    args = ap.parse_args()

    source = args.data
    if not source:
        source = COPY_JSON if os.path.isfile(COPY_JSON) else DEMO_JSON
    if not os.path.isfile(source):
        sys.exit("Нет JSON: %s" % source)

    with open(source, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("banners") or data.get("models") or data.get("items") or []
    if not isinstance(data, list) or not data:
        sys.exit("JSON пустой или не массив: %s" % source)

    only = {x.strip().upper() for x in args.only.split(",") if x.strip()}
    os.makedirs(args.out, exist_ok=True)

    made = 0
    expected = set()
    for item in data:
        bid = (item.get("id") or "").upper()
        if only and bid not in only:
            continue
        slug = item.get("slug") or slugify(item.get("model") or bid)
        for fmt, fmt_class in FORMATS:
            fname = "%s_%s_%s.html" % (bid, slug, fmt)
            expected.add(fname)
            path = os.path.join(args.out, fname)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(build_item_html(item, fmt, fmt_class, source))
            made += 1
        print("  %s · %-24s · %s -> 2 HTML" % (bid, item.get("model"), item.get("tone", "field")))

    # чистим устаревшие файлы от прежних slug-ов (например, «…_4_28a_b_…»
    # после переименования модели) — иначе в пакет попадут дубли
    removed = 0
    if os.path.isdir(args.out):
        for fname in sorted(os.listdir(args.out)):
            if not fname.lower().endswith(".html"):
                continue
            if re.match(r"^B\d{2}_", fname) and fname not in expected:
                os.remove(os.path.join(args.out, fname))
                removed += 1

    print("Готово: %d HTML в %s (данные: %s)%s"
          % (made, args.out, os.path.basename(source),
             (", удалено устаревших: %d" % removed) if removed else ""))


if __name__ == "__main__":
    main()
