#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ГЕНЕРАТОР «СУПЕРЦЕНЫ НА НПО „КИЛОВАТТ“» — 20 позиций прайса × 4 карточки + hero.

Вход:  superceny/01_ДАННЫЕ/positions.json
       (id, folder, name, name_full, category, manufacturer, short, specs[],
        tasks[], benefits[], hook, super_line, price_note, price_value, photos[],
        archive, on_site, availability).
Фото:  superceny/02_ДИЗАЙН/img/* (подготовленные вырезки designer-b);
       пока их нет — исходный JPG каталога kilowatt/data/photos (только чтение).
Выход: superceny/03_HTML/<folder>/01_СУПЕРЦЕНА.html … 04_СУПЕР-ПРЕДЛОЖЕНИЕ.html
       superceny/03_HTML/00_СУПЕРЦЕНЫ.html

Запуск:
  python generator.py                # все 173 (43×4 + hero)
  python generator.py --only kw-05,kw-42
  python generator.py --clean        # очистить 03_HTML перед генерацией
"""

import argparse
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))        # superceny/02_ДИЗАЙН
SUPER = os.path.dirname(HERE)                             # superceny
HTML_DIR = os.path.join(SUPER, "03_HTML")
POSITIONS = os.path.join(SUPER, "01_ДАННЫЕ", "positions.json")
IMG = os.path.join(HERE, "img")
KILO_PHOTOS = os.path.abspath(os.path.join(SUPER, "..", "kilowatt", "data", "photos"))

LEGAL = ("Характеристики — по паспорту изделия. Не является публичной офертой. "
         "РЭС: порядок применения — по законодательству РФ.")
DEFAULT_BENEFITS = ["Суперцена", "Гарантия 12 месяцев", "Доставка по РФ", "Самовывоз в Москве"]
DEFAULT_BENEFIT_SUBS = ["спецпредложение на позицию", "отметка в паспорте изделия",
                        "отправка по всей стране", "забрать со склада"]


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=False)


def sanitize(text) -> str:
    """Убирает цены (₽/руб.) из текстов — цены не публикуем."""
    s = str(text or "")
    s = re.sub(r"[^.!?]*\d[\d\s.,]*\u20bd[^.!?]*[.!?]?", "", s)
    s = re.sub(r"[^.!?]*\bруб\w*\b[^.!?]*[.!?]?", "", s)
    return re.sub(r"\s+", " ", s.replace("\u20bd", "")).strip()


def capitalize(s: str) -> str:
    s = str(s or "").strip()
    return (s[0].upper() + s[1:]) if s else s


def name_class(name: str) -> str:
    n = len(name or "")
    return ("c-name--xl" if n <= 12 else "c-name--l" if n <= 18
            else "c-name--m" if n <= 26 else "c-name--s")


def money(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return "{:,}".format(int(value)).replace(",", " ") + " ₽"
    return str(value).strip() or None


def clean_specs(specs, limit=8):
    out = []
    for s in (specs or []):
        if not isinstance(s, dict):
            continue
        label = str(s.get("label") or "").strip()
        value = str(s.get("value") or "").strip()
        if label and value:
            out.append({"label": label, "value": value})
        if len(out) >= limit:
            break
    return out


def derive_key_facts(specs, limit=4):
    """Короткие значения из паспорта для полосы ключевых ТТХ (без разрыва дробей)."""
    picks = []
    unit_re = re.compile(
        r"(\d+(?:[.,]\d+)?(?:\s*[/–-]\s*\d+(?:[.,]\d+)?)?\s*"
        r"(?:МГц|ГГц|кГц|кг|г|мм|см|м|ч|мин|В|Вт|кВт|А·ч|А|%))", re.I)
    for s in (specs or []):
        value = str(s.get("value") or "")
        for tok in value.split(";"):
            tok = re.sub(r"\s+", " ", tok.strip(" ."))
            if not tok or not any(ch.isdigit() for ch in tok):
                continue
            # вес: «Брутто 0,5 кг, нетто 0,2 кг» -> «0,5 кг» (дробь не рвём)
            m_net = re.search(r"[Нн]етто\s*(\d+(?:[.,]\d+)?\s*кг)", tok)
            m_br = re.search(r"[Бб]рутто\s*(\d+(?:[.,]\d+)?\s*кг)", tok)
            if m_net:
                tok = re.sub(r"\s+", " ", m_net.group(1));  # для рекламы — нетто
            elif m_br:
                tok = re.sub(r"\s+", " ", m_br.group(1))
            elif len(tok) > 20:
                m2 = unit_re.search(tok)
                if not m2:
                    continue
                tok = re.sub(r"\s+", " ", m2.group(1))
            if 2 <= len(tok) <= 24 and tok not in picks:
                picks.append(tok)
            if len(picks) >= limit:
                return picks
    return picks


def resolve_photo(item):
    """Сначала подготовленная вырезка в 02_ДИЗАЙН/img, затем исходный JPG каталога."""
    pid = str(item.get("id") or "")
    cands = []
    for key in ("photo", "photo_main", "img"):
        v = item.get(key)
        if v:
            cands.append(str(v).strip().lstrip("/").replace("\\", "/"))
    cands += [pid + "_main.png", pid + ".png"]
    for c in cands:
        rel = c.replace(os.sep, "/")
        if os.path.isfile(os.path.join(IMG, rel)):
            return "../../02_ДИЗАЙН/img/" + rel
    for photo in (item.get("photos") or []):
        rel = str(photo).replace("\\", "/")
        if os.path.isfile(os.path.join(KILO_PHOTOS, rel)):
            return "../../../kilowatt/data/photos/" + rel
    return None


def normalize(item, idx):
    pid = str(item.get("id") or "kw-%02d" % idx)
    folder = str(item.get("folder") or "").strip() or "%02d_%s" % (idx, pid)
    folder = re.sub(r'[\\/:*?"<>|]', "", folder).strip().rstrip(".")
    name = str(item.get("name") or item.get("name_full") or "").strip()
    specs = clean_specs(item.get("specs"), 8)
    tasks = [sanitize(t) for t in (item.get("tasks") or []) if str(t).strip()][:4]
    if not tasks:
        tasks = ["Подбор под задачу", "Поставка и сервис"]
    benefits = [sanitize(b) for b in (item.get("benefits") or DEFAULT_BENEFITS) if str(b).strip()][:4]
    while len(benefits) < 4:
        benefits.append(DEFAULT_BENEFITS[len(benefits)])
    archive = bool(item.get("archive"))
    new_pos = bool(item.get("missing")) or str(item.get("data_status") or "").lower() == "requested"
    price_note = capitalize(item.get("price_note") or "Прайс по запросу")
    if new_pos and "новая позиция" not in price_note.lower():
        price_note = "Новая позиция · " + price_note[0].lower() + price_note[1:]
    return {
        "id": pid, "num": idx, "folder": folder,
        "name": name,
        "name_full": str(item.get("name_full") or name).strip(),
        "category": str(item.get("category") or "").strip(),
        "manufacturer": str(item.get("manufacturer") or "ООО «НПО «Киловатт»»").strip(),
        "hook": sanitize(item.get("hook") or "").upper(),
        "line": sanitize(item.get("super_line") or item.get("short") or ""),
        "specs": specs,
        "tasks": tasks,
        "benefits": benefits,
        "key_facts": derive_key_facts(specs, 4),
        "price": money(item.get("price_value")),
        "price_note": price_note,
        "archive": archive,
        "new_pos": new_pos,
        "availability": str(item.get("availability") or "").strip(),
        "photo": resolve_photo(item),
        "name_cls": name_class(name),
    }


# --------------------------------------------------------------------------
# общие блоки разметки
# --------------------------------------------------------------------------

def header(p, label, counter):
    return """  <i class="b-tick b-tick--tl" aria-hidden="true"></i>
  <i class="b-tick b-tick--tr" aria-hidden="true"></i>
  <i class="b-tick b-tick--bl" aria-hidden="true"></i>
  <i class="b-tick b-tick--br" aria-hidden="true"></i>
  <header class="b-top">
    <div class="b-brand"><img src="../../02_ДИЗАЙН/img/brand/logo_w_word.png" alt="В ОКОПЕ — магазин брони"></div>
    <div class="b-issuer"><b>НПО «Киловатт»</b>производитель<br>%02d · %s · %s</div>
  </header>
""" % (p["num"], counter, label)


def plate(p, height=None):
    style = ' style="height:%dpx"' % height if height else ""
    if p["photo"]:
        return """    <figure class="c-stage"%s>
      <div class="c-plate"><img src="%s" alt="%s"></div>
      <figcaption class="c-cap">%s</figcaption>
    </figure>""" % (style, p["photo"], esc(p["name_full"]), esc(p["name_full"]))
    note = ("НОВАЯ ПОЗИЦИЯ · ПОД ЗАКАЗ" if p.get("new_pos")
            else "АРХИВ · ПОД ЗАКАЗ" if p["archive"] else "ЗАПРОСИТЕ У МЕНЕДЖЕРА")
    return """    <figure class="c-stage c-stage--empty"%s>
      <div class="c-plate c-plate--empty"><div class="c-plate__stub"><b>ФОТО УТОЧНЯЕТСЯ</b>%s</div></div>
      <figcaption class="c-cap">%s</figcaption>
    </figure>""" % (style, note, esc(p["name_full"]))


def footer():
    return """  <footer class="b-foot" style="padding-top:14px">
    <div>
      <div class="b-cta-main"><span class="b-tg">@vokope_ru</span> <span>+7 (999) 136-71-42</span></div>
      <div class="b-cta-sub">Прайс по запросу · Доставка по РФ · Самовывоз в Москве</div>
    </div>
    <div class="b-calc"><b>В ОКОПЕ</b>магазин брони<br>подбор и поставка</div>
  </footer>
  <p class="b-legal">%s</p>
""" % LEGAL


def price_value(p):
    return esc(p["price"]) if p["price"] else esc(p["price_note"])


def page(title, theme, main_html):
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="../../02_ДИЗАЙН/tokens.css">
<link rel="stylesheet" href="../../02_ДИЗАЙН/super.css">
</head>
<body class="theme-%s">
%s
</body>
</html>
""" % (esc(title), theme, main_html)


# --------------------------------------------------------------------------
# CARD 01 · СУПЕРЦЕНА
# --------------------------------------------------------------------------

def card01(p):
    main = """<main class="banner banner--poster card card--01 theme-field grain">
%s
  <div class="c-body">
    <span class="c-badge">Суперцена</span>
    <p class="c-hook">%s</p>
    <p class="c-cat">%s</p>
    <h1 class="c-name %s">%s</h1>
    <p class="c-line">%s</p>
%s
    <div class="c-slogan">Лучше не найдёте</div>
    <div class="c-price">
      <div class="c-price__main">%s</div>
      <div class="c-price__note">Прайс и наличие<br>уточняются в КП</div>
    </div>
  </div>
%s
</main>""" % (header(p, "СУПЕРЦЕНА", "01/04"), esc(p["hook"]), esc(p["category"]),
              p["name_cls"], esc(p["name"]), esc(p["line"]), plate(p), price_value(p), footer())
    return page(p["name_full"] + " · СУПЕРЦЕНА · «В ОКОПЕ»", "field", main)


# --------------------------------------------------------------------------
# CARD 02 · ХАРАКТЕРИСТИКИ
# --------------------------------------------------------------------------



def specs_block(p):
    if not p["specs"]:
        return ('    <div class="c-specs c-specs--empty">'
                '<b>Характеристики по запросу</b>'
                '<span>Позиция прайса — данные уточняются у поставщика; запросите КП.</span></div>')
    return '    <div class="c-specs">\n' + specs_rows(p) + '\n    </div>'


TILE_PRIORITY = ("диапазон", "частот", "мощност", "дальност", "канал",
                 "вес", "масса", "размер", "габарит", "время", "питани",
                 "назначени", "температур", "гаранти")


def spec_rank(s):
    label = str(s.get("label") or "").lower()
    for i, key in enumerate(TILE_PRIORITY):
        if key in label:
            return i
    return 99


def pick_tiles(specs, n=4):
    order = sorted(range(len(specs)), key=lambda i: (spec_rank(specs[i]), i))
    idx = set(order[:n])
    tiles = [specs[i] for i in sorted(idx)]
    rest = [s for i, s in enumerate(specs) if i not in idx][:3]
    return tiles, rest


def tile_size_class(text):
    n = len(text)
    if n <= 6:
        return ""
    if n <= 10:
        return " c2-tile__v--56"
    if n <= 18:
        return " c2-tile__v--48"
    if n <= 28:
        return " c2-tile__v--44"
    if n <= 40:
        return " c2-tile__v--34"
    return " c2-tile__v--28"


def plural_freq(n):
    if n % 10 == 1 and n % 100 != 11:
        return "частота"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "частоты"
    return "частот"


def compact_tile(spec):
    """-> (значение, подпись-подсказка или '', css-класс кегля).
    Крупное осмысленное значение из паспортной строки; полная строка — в подсказке.
    """
    label = str(spec.get("label") or "").lower()
    value = str(spec.get("value") or "").strip()
    sub = ""

    def done(main, extra=""):
        return main, extra or "", tile_size_class(main)

    # --- вес: нетто (или брутто), иначе первое «число кг»
    if "вес" in label or "масса" in label:
        m_net = re.search(r"[Нн]етто\s*(\d+(?:[.,]\d+)?\s*кг)", value)
        m_br = re.search(r"[Бб]рутто\s*(\d+(?:[.,]\d+)?\s*кг)", value)
        m_any = re.search(r"(\d+(?:[.,]\d+)?\s*кг)", value)
        if m_net:
            return done(re.sub(r"\s+", " ", m_net.group(1)), ("брутто " + m_br.group(1)) if m_br else "")
        if m_br:
            return done(re.sub(r"\s+", " ", m_br.group(1)))
        if m_any:
            main = re.sub(r"\s+", " ", m_any.group(1))
            return done(main, value if main != value else "")

    # --- диапазон частот: общий размах крупно, полный перечень подсказкой
    if "диапазон" in label and "частот" in label:
        nums = re.findall(r"\d+", value)
        if len(nums) >= 2:
            unit = "МГц" if "МГц" in value else ""
            main = "%s–%s %s" % (nums[0], nums[-1], unit)
            sep = " · " if ";" in value else ", "
            parts = [p.strip() for p in re.split(r"[;,]", value) if p.strip()]
            sub = sep.join(p.replace(" МГц", "") for p in parts) + (" МГц" if unit else "")
            return done(main, sub)

    # --- перечень частот: количество (правильный падеж) + диапазон подсказкой
    if "частот" in label:
        nums = re.findall(r"\d+", value)
        if len(nums) >= 4:
            unit = "МГц" if "МГц" in value else ""
            main = "%d %s" % (len(nums), plural_freq(len(nums)))
            return done(main, "%s…%s %s" % (nums[0], nums[-1], unit))

    # --- дальность: диапазон или «до/не менее N м»
    if "дальност" in label:
        m = re.search(r"(\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*м)", value)
        if m:
            main = re.sub(r"\s+", " ", m.group(1))
            par = re.search(r"\(([^)]*)\)", value)
            return done(main, re.sub(r"^при\s+удалении\s+", "", par.group(1)).strip() if par else (value if main != value else ""))
        unit_re = re.compile(r"((?:до|не менее|не более)\s+\d+(?:[.,]\d+)?\s*(?:м|км))", re.I)
        mu = unit_re.search(value)
        if mu:
            main = re.sub(r"\s+", " ", mu.group(1))
            return done(main, value if main != value else "")

    # --- прочие длинные значения: короткий токен с единицей, полное — подсказкой
    if len(value) > 28:
        unit_re = re.compile(r"(\d+(?:[.,]\d+)?(?:\s*[-–х×x]\s*\d+(?:[.,]\d+)?)*\s*(?:МГц|ГГц|кг|г|мм|см|м|ч|мин|В|Вт|кВт|А·ч|А|%|°C|°С))", re.I)
        mu = unit_re.search(value)
        if mu:
            main = re.sub(r"\s+", " ", mu.group(1))
            return done(main, value if main != value else "")
    return done(value)


def photo_v2(p, klass="c2-photo"):
    if p["photo"]:
        return ("<figure class=\"%s\"><div class=\"c-plate\"><img src=\"%s\" alt=\"%s\"></div>"
                "<figcaption class=\"c-cap\">%s</figcaption></figure>"
                % (klass, p["photo"], esc(p["name_full"]), esc(p["name_full"])))
    note = ("НОВАЯ ПОЗИЦИЯ · ПОД ЗАКАЗ" if p.get("new_pos")
            else "АРХИВ · ПОД ЗАКАЗ" if p["archive"] else "ЗАПРОСИТЕ У МЕНЕДЖЕРА")
    return ("<figure class=\"%s\"><div class=\"c-plate c-plate--empty\">"
            "<div class=\"c-plate__stub\"><b>ФОТО УТОЧНЯЕТСЯ</b>%s</div></div>"
            "<figcaption class=\"c-cap\">%s</figcaption></figure>"
            % (klass, note, esc(p["name_full"])))


def extras_html(p):
    return """      <div class="c2-extra"><span class="c2-extra__k">Изготовитель</span><span class="c2-extra__v">%s</span></div>
      <div class="c2-extra"><span class="c2-extra__k">Наличие</span><span class="c2-extra__v">%s</span></div>
      <div class="c2-extra"><span class="c2-extra__k">Комплект</span><span class="c2-extra__v">по запросу; подбор — в КП</span></div>
      <div class="c2-extra"><span class="c2-extra__k">Поставка</span><span class="c2-extra__v">Доставка по РФ · самовывоз в Москве</span></div>""" % (
        esc(p["manufacturer"]), esc(p["availability"] or "уточняется"))


def card02(p):
    if p["specs"]:
        tiles, rest = pick_tiles(p["specs"], 4)
        tiles_html = "\n".join(
            '      <div class="c2-tile"><span class="c2-tile__k">%s</span>'
            '<span class="c2-tile__v%s">%s</span>%s</div>'
            % (esc(s["label"]), cls, esc(val), ('<span class="c2-tile__sub">%s</span>' % esc(sub)) if sub else "")
            for s in tiles for val, sub, cls in [compact_tile(s)])
        def row_html(s):
            value = str(s["value"]).strip()
            short = value
            sub = ""
            if len(value) > 26:
                if ";" in value:
                    short = value.split(";")[0].strip()
                elif "," in value and value.find(",") < 30:
                    short = value.split(",")[0].strip()
                else:
                    cut = value[:24].rsplit(" ", 1)[0].rstrip(" ,;.")
                    short = cut + "…"
                sub = '<span class="c2-row__sub">%s</span>' % esc(value)
            return ('        <div class="c2-row"><span class="c2-row__k">%s</span>'
                    '<span class="c2-row__v">%s</span>%s</div>'
                    % (esc(s["label"]), esc(short), sub))
        rest_html = "\n".join(row_html(s) for s in rest)
        top_right = photo_v2(p)
        bottom = """    <div class="c2-bottom">
      <div class="c2-list">
%s
      </div>
      <div class="c2-extras">
%s
      </div>
    </div>""" % (rest_html, extras_html(p))
        tiles_block = "    <div class=\"c2-tiles\">\n%s\n    </div>" % tiles_html
    else:
        top_right = photo_v2(p)
        tiles_block = ''
        bottom = """    <div class="c2-bottom">
      <div class="c2-empty"><b>Характеристики по запросу</b><span>Позиция прайса — данные уточняются у поставщика; запросите КП.</span></div>
      <div class="c2-extras">
%s
      </div>
    </div>""" % extras_html(p)

    tasks_line = " · ".join(p["tasks"])
    strip = """    <div class="c2-strip">
      <div class="c2-strip__cell"><span class="c2-strip__k">В комплекте</span><span class="c2-strip__v">по запросу; подбор под задачу — в КП</span></div>
      <div class="c2-strip__cell"><span class="c2-strip__k">Применение</span><span class="c2-strip__v">%s</span></div>
    </div>""" % esc(tasks_line)
    main = """<main class="banner banner--poster card card--02v2 theme-quiet grain">
%s
  <div class="c2-body">
    <div class="c2-top">
      <div class="c2-head">
        <span class="c-badge">Характеристики</span>
        <p class="c-hook">%s</p>
        <p class="c-cat">%s</p>
        <h1 class="c-name %s">%s</h1>
      </div>
      %s
    </div>
%s
%s
%s
  </div>
%s
</main>""" % (header(p, "ХАРАКТЕРИСТИКИ", "02/04"), esc(p["hook"]), esc(p["category"]),
              p["name_cls"], esc(p["name"]), top_right, tiles_block, bottom, strip, footer())
    return page(p["name_full"] + " · ХАРАКТЕРИСТИКИ · «В ОКОПЕ»", "quiet", main)


def card03(p):
    tasks = "\n".join('      <li class="c-list__item"><span class="c-list__n">%02d</span>'
                      '<p class="c-list__t">%s</p></li>' % (i, esc(t))
                      for i, t in enumerate(p["tasks"], 1))
    facts = ""
    if p["key_facts"]:
        def fact_span(v):
            cls = " c-facts__i--s" if len(v) > 14 else ""
            return '      <span class="c-facts__i%s">%s</span>' % (cls, esc(v))
        facts = '    <div class="c-facts">\n%s\n    </div>' % "\n".join(
            fact_span(v) for v in p["key_facts"])
    main = """<main class="banner banner--poster card card--03 card--03v2 theme-field grain">
%s
  <div class="c-body">
    <div class="c-head">
      <span class="c-badge">Кому подходит</span>
      <p class="c-hook">%s</p>
      <p class="c-cat">%s</p>
      <h1 class="c-name %s">%s</h1>
    </div>
    <ul class="c-list">
%s
    </ul>
%s
%s
    <div class="c-slogan">Лучше не найдёте</div>
  </div>
%s
</main>""" % (header(p, "ПРИМЕНЕНИЕ", "03/04"), esc(p["hook"]), esc(p["category"]),
              p["name_cls"], esc(p["name"]), tasks, facts, plate(p), footer())
    return page(p["name_full"] + " · ПРИМЕНЕНИЕ · «В ОКОПЕ»", "field", main)


# --------------------------------------------------------------------------
# CARD 04 · СУПЕР-ПРЕДЛОЖЕНИЕ
# --------------------------------------------------------------------------

def advantages(p):
    return "\n".join(
        '      <div class="c-adv__item"><span class="c-adv__mark"></span>'
        '<p class="c-adv__t"><b>%s</b>%s</p></div>' % (esc(b), esc(DEFAULT_BENEFIT_SUBS[i]))
        for i, b in enumerate(p["benefits"][:4]))


def card04(p):
    main = """<main class="banner banner--poster card card--04 card--04v2 theme-quiet grain">
%s
  <div class="c-body">
    <span class="c-badge c-badge--big">СУПЕРЦЕНА</span>
    <p class="c-hook">%s</p>
    <p class="c-cat">%s</p>
    <h1 class="c-name %s">%s</h1>
    <div class="c-adv">
%s
    </div>
    <p class="c-kit"><b>Комплект.</b> Комплект и аксессуары — по запросу; подбор под задачу — в КП.</p>
%s
    <div class="c-pricezone">
      <div>
        <span class="c-pricezone__label">Прайс по запросу</span>
        <span class="c-pricezone__value">%s</span>
      </div>
      <div class="c-pricezone__meta">КП в течение дня<br>доставка по РФ</div>
    </div>
  </div>
%s
</main>""" % (header(p, "СУПЕР-ПРЕДЛОЖЕНИЕ", "04/04"), esc(p["hook"]), esc(p["category"]),
              p["name_cls"], esc(p["name"]), advantages(p), plate(p), price_value(p), footer())
    return page(p["name_full"] + " · СУПЕР-ПРЕДЛОЖЕНИЕ · «В ОКОПЕ»", "quiet", main)


# --------------------------------------------------------------------------
# HERO · 00_СУПЕРЦЕНЫ
# --------------------------------------------------------------------------

def hero(positions):
    picks = [p for p in positions if p["photo"]][:8]
    cells = []
    for p in picks:
        src = p["photo"].replace("../../02_ДИЗАЙН/", "../02_ДИЗАЙН/").replace(
            "../../../kilowatt/", "../../kilowatt/")
        cells.append('<img src="%s" alt="%s">' % (src, esc(p["name"])))
    while len(cells) < 8:
        cells.append("<span></span>")
    main = """<main class="banner banner--poster hero-card theme-field grain">
  <i class="b-tick b-tick--tl" aria-hidden="true"></i>
  <i class="b-tick b-tick--tr" aria-hidden="true"></i>
  <i class="b-tick b-tick--bl" aria-hidden="true"></i>
  <i class="b-tick b-tick--br" aria-hidden="true"></i>
  <header class="b-top">
    <div class="b-brand"><img src="../02_ДИЗАЙН/img/brand/logo_w_word.png" alt="В ОКОПЕ — магазин брони"></div>
    <div class="b-issuer"><b>НПО «Киловатт»</b>производитель<br>20 позиций прайса · 11.2026</div>
  </header>
  <div class="h-body">
    <p class="h-kicker">Магазин «В ОКОПЕ» · спецпредложение</p>
    <h1 class="h-title">СУПЕР<em>ЦЕНЫ</em></h1>
    <p class="h-sub"><b>Весь прайс НПО «Киловатт».</b> 20 позиций прайса, 4 карточки на каждую:
      витрина, характеристики, применение и супер-предложение.</p>
    <div class="h-collage">
    %s
    </div>
    <p class="h-slogan">Лучше не найдёте</p>
    <div class="h-adv">
      <div><b>20 позиций</b>весь прайс</div>
      <div><b>4 карточки</b>на каждую модель</div>
      <div><b>Прайс по запросу</b>КП в течение дня</div>
    </div>
  </div>
%s
</main>""" % ("\n    ".join(cells), footer())
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>СУПЕРЦЕНЫ НА НПО «КИЛОВАТТ» · «В ОКОПЕ»</title>
<link rel="stylesheet" href="../02_ДИЗАЙН/tokens.css">
<link rel="stylesheet" href="../02_ДИЗАЙН/super.css">
</head>
<body class="theme-field">
%s
</body>
</html>
""" % main


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=POSITIONS)
    ap.add_argument("--out", default=HTML_DIR)
    ap.add_argument("--only", default="")
    ap.add_argument("--no-hero", action="store_true")
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        sys.exit("Нет positions.json: %s" % args.data)
    with open(args.data, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        raw = raw.get("positions") or raw.get("items") or []
    if not isinstance(raw, list) or not raw:
        sys.exit("positions.json пуст")

    positions = [normalize(it, i) for i, it in enumerate(raw, 1) if isinstance(it, dict)]

    if args.clean and os.path.isdir(args.out):
        for name in os.listdir(args.out):
            path = os.path.join(args.out, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        print("03_HTML очищен")

    only = {x.strip().lower() for x in args.only.split(",") if x.strip()}
    selected = [p for p in positions if not only or p["id"].lower() in only]
    os.makedirs(args.out, exist_ok=True)
    made = 0
    for p in selected:
        folder = os.path.join(args.out, p["folder"])
        os.makedirs(folder, exist_ok=True)
        for fname, content in (
            ("01_СУПЕРЦЕНА.html", card01(p)),
            ("02_ХАРАКТЕРИСТИКИ.html", card02(p)),
            ("03_ПРИМЕНЕНИЕ.html", card03(p)),
            ("04_СУПЕР-ПРЕДЛОЖЕНИЕ.html", card04(p)),
        ):
            with open(os.path.join(folder, fname), "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            made += 1
        print("  %-6s %-40s %s" % (p["id"], p["name"][:40], p["folder"]))

    if not args.no_hero and not only:
        with open(os.path.join(args.out, "00_СУПЕРЦЕНЫ.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(hero(positions))
        made += 1
        print("  HERO 00_СУПЕРЦЕНЫ.html")

    print("Готово: %d HTML в %s" % (made, args.out))


if __name__ == "__main__":
    main()
