#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_claims.py — QA-линтер пакета «ДВА ГОРИЗОНТА» (роль qa).

Что делает:
  1) читает infographics/01_ФАКТЫ/claims.json (единственный источник цифр) и BANNED.md;
  2) читает постеры infographics/02_МАКЕТЫ/posters/**/*.html, извлекает видимый текст
     (html.parser; <script>/<style> исключены, SVG <text> включается, alt/aria-label тоже);
  3) ищет:
     а) запрещённые формулировки (BANNED.md + фолбэк из APPROVED_CLAIMS §5 / market_brief §6);
     б) числовые токены (диапазоны, МГц, ГГц, м, км, Вт, кВт, кг, А·ч, ч, мин, мес, %, ₽,
        м², каналы, генераторы, позиции, семейства, модели, станции, шаги, типы) и сверяет
        с числами из claims.json; выводит числа, которых нет в факт-базе;
     в) упоминания цен (₽, руб., «цена», «стоимость», «прайс») — отдельный блокер Б5,
        значения цен в отчёт НЕ копируются (цена не публикуется);
     г) CTA @vokope_ru и +7 999 136-71-42 в каждом постере (+ строка доставки/самовывоза);
     д) дисклеймер (market_brief §5.5) на P05/P06/P10;
  4) проверяет CSS/HTML: внешние ресурсы, градиенты/тени/неон, кегли < 13px, подмену
     шрифтов, отсутствующие font-face/картинки, шаблонные заглушки;
  5) проверяет факт-базу против первоисточников: файл из claim.source индексируется,
     числа claim ищутся в источнике (если source — локальный файл);
  6) пишет 03_QA/QA_АВТОПРОВЕРКА.md и 03_QA/QA_АВТОПРОВЕРКА.json.

Запуск:
  python check_claims.py                 # обычный прогон
  python check_claims.py --selftest      # самопроверка на синтетических фикстурах
  python check_claims.py --no-write      # только stdout
  python check_claims.py --posters P05   # один постер (по префиксу)

Коды дефектов: Б1 неподтверждённая цифра, Б2 запрещённая формулировка/военная риторика,
Б3 визуальный/CSS брак (кегль, шрифт, градиент, битая картинка), Б4 нет CTA/дисклеймера,
Б5 утечка цены, З замечание, И инфо.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

try:  # Pillow есть в бандле, но скрипт не должен падать без него
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
MASK = "·"
# разделитель склеиваемых текстов: не пробел, чтобы не появлялись «фальшивые» диапазоны 15–30
JOIN = " ; "

# ---------------------------------------------------------------- ожидаемые файлы
EXPECTED_POSTERS = {
    "P01": "P01_dva_gorizonta.html",
    "P02": "P02_karta_linejki.html",
    "P03": "P03_eshelon_zashchity.html",
    "P04": "P04_chto_zashchishchaem.html",
    "P05": "P05_b2b_pochemu_sejchas.html",
    "P06": "P06_pravovoj_kompas.html",
    "P07": "P07_roznica_kupol.html",
    "P08": "P08_sravnenie_modelej.html",
    "P09": "P09_kak_kupit.html",
    "P10": "P10_dokumenty_i_servis.html",
}
EXPECTED_WIDE = ["P01", "P02", "P03", "P07"]
EXPECTED_STORY = ["P01", "P07", "P09"]
DISCLAIMER_POSTERS = {"P05", "P06", "P10"}

PHONE_DIGITS = "79991367142"
CTA_TG_RE = re.compile(r"@\s*vokope[_\- ]?ru", re.I)
DELIVERY_RE = re.compile(r"доставк\w*\s+по\s+рф", re.I)
PICKUP_RE = re.compile(r"самовывоз", re.I)
PHONE_ANY_RE = re.compile(r"\+?\s*7[\s\-()]*9[\s\-()]*9[\s\-()]*9[\s\-()]*1[\s\-()]*3[\s\-()]*6[\s\-()]*7[\s\-()]*1[\s\-()]*4[\s\-()]*2", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
POSTER_ID_RE = re.compile(r"\bP\d{1,2}\b")
CLAIM_ID_RE = re.compile(r"\bC\d{2,4}\b")

DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b|\b\d{1,2}\.\d{4}\b")
ASPECT_RE = re.compile(r"(?<![\d.,])\d{1,2}:\d{1,2}(?![\d.,])")      # 16:9, 4:5, 9:16 (без пробелов)
DIM_RE = re.compile(r"\b\d{3,4}\s*[×x]\s*\d{3,4}\b")          # 1920×1080, 1080×1350
# год = 20xx, но НЕ когда за числом идёт единица измерения (2000 м = дальность, 2026 года = дата)
YEAR_RE = re.compile(
    r"\b(20\d{2})\b"
    r"(?!\s*(?:км|мм|см|кг|квт|мгц|ггц|а·ч|ач|мин|вт|м|г|ч|%|°|руб|₽)(?![А-Яа-яЁёA-Za-z]))",
    re.I,
)
# BANNED §1 (SPORY S24): «работает без оператора» / «не требует оператора» — запрещено
OPERATOR_BAN_RE = re.compile(r"без\s+(?:отдельного\s+)?оператора|не\s+требует\s+оператора", re.I)

MONEY_RE = re.compile(
    r"(\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"\s*(млрд|млн|тыс\.?)?\s*(?:₽|руб(?:\.|лей|ля)?|р\.)(?![А-Яа-яЁёA-Za-z])",
    re.I,
)
VOLT_RANGE_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*В(?![А-Яа-яЁёA-Za-z])")
VOLT_SINGLE_RE = re.compile(r"(?<=\d)\s*(\d+)\s*В(?![А-Яа-яЁёA-Za-z])")
TEMP_RANGE_RE = re.compile(r"([+\-−]?\d+)\s*[–—−…]\s*([+\-−]?\d+)\s*°\s*[CС]")
TEMP_SINGLE_RE = re.compile(r"([+\-−]?\d+)\s*°\s*[CС]")

LAW_RES = [
    re.compile(r"\b\d{2,3}\s?[-‑–]\s?ФЗ\b", re.I),
    re.compile(r"\bФЗ\s?[-‑–]?\s?\d+\b", re.I),
    re.compile(
        r"\b(?:ПП|ПП\s+РФ|Постановлени[ея]|постановлени[ея])\s*(?:РФ\s*)?(?:от\s*[\d.]+\s*)?(?:№|No\.?|N°)?\s*\d+\b",
        re.I,
    ),
    re.compile(r"(?:№|No\.?|N°)\s*[\d][\d.\-/]*", re.I),
    re.compile(r"\b\d{2}[-‑]\d{2}[-‑][\d./]+"),
    re.compile(r"\b\d+[-‑]\d+/\d+(?:\.\d+)*"),
    re.compile(r"\b(?:ст\.|стать[яи]|п\.|пункт|ч\.|част[ьи])\s*\d+[\d.]*", re.I),
]
LATIN_NO_RE = re.compile(r"(?<![A-Za-zА-Яа-яЁё])(?:No|N°)\s*\.?\s*\d", re.I)

MODEL_RE = re.compile(
    r"(?<![А-ЯЁA-Zа-яёa-z0-9])(?:"
    r"(?:Капюшон|Сигнал(?:[-‑ ]?[МM])?|Ребус|Поле|Штора(?:[-‑ ]?[МM])?|ФПВ|ТП|ИП)"
    r"[-‑ ]?\d+(?:[-‑/]\d+)*(?:[-‑]?[А-ЯЁA-Z]{1,3}(?:/[А-ЯЁA-Z]{1,3})?)?"
    r"|[КKТT]-?\d+(?:[-‑/]\d+)*(?:[-‑]?[А-ЯЁA-Z]{1,3}(?:/[А-ЯЁA-Z]{1,3})?)?"
    r")"
)
MODEL_RE = MODEL_RE
# «B2B», «P01», «360°» моделями не считаются: префиксы ограничены семействами изделий

NUMCELL = r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
UNIT_ALT = (
    r"мгц|ггц|км\s*/\s*ч|км|квт|вт|кг|мм|см|а\s*[·*]\s*ч|ач"
    r"|мес(?:яц(?:ев|а|ы)?)?|лет|год(?:а|ов)?|мин|час(?:ов|а|)?|сут(?:ки|ок)?|дн(?:я|ей)?|м²|м2|°\s*[CС]|°|%|ч|м|г"
    r"|канал(?:ов|а|ы)?|генератор(?:ов|а|ы)?|передатчик(?:ов|а|и)?"
    r"|моноблок(?:ов|а|и)?|позици(?:й|и|я|ях|ям)?|семейств(?:а|о|в)?"
    r"|модел(?:ей|и|ь|ями)?|станц(?:ий|ия|ии|ию)?|шаг(?:ов|а|и)?|тип(?:ов|а|ы)?"
)
FACT_RE = re.compile(
    rf"(?P<s1>[+\-−])?(?P<n1>{NUMCELL})"
    rf"(?:\s*[–—−…/‑-]\s*(?P<s2>[+\-−])?(?P<n2>{NUMCELL}))?"
    rf"\s*(?P<unit>{UNIT_ALT})(?![А-Яа-яЁёA-Za-z])",
    re.I,
)
MONEY_RANGE_RE = re.compile(
    rf"({NUMCELL})\s*[–—−‑-]\s*({NUMCELL})\s*(млрд|млн|тыс\.?)?\s*(?:₽|руб(?:\.|лей|ля)?|р\.)(?![А-Яа-яЁёA-Za-z])",
    re.I,
)

# числительные словами -> цифры (с сохранением длины строки!)
NUM_WORDS = {
    "два": 2, "две": 2, "двух": 2, "двум": 2, "двумя": 2,
    "три": 3, "трех": 3, "трем": 3, "тремя": 3,
    "четыре": 4, "четырех": 4, "четырем": 4,
    "пять": 5, "пяти": 5, "пятью": 5,
    "шесть": 6, "шести": 6, "шестью": 6,
    "семь": 7, "семи": 7, "семью": 7,
    "восемь": 8, "восьми": 8, "восемью": 8,
    "девять": 9, "девяти": 9, "девятью": 9,
    "десять": 10, "десяти": 10, "десятью": 10,
    "одиннадцать": 11, "двенадцать": 12, "двенадцати": 12,
    "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
    "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
    "двадцать": 20, "двадцати": 20, "тридцать": 30, "сорок": 40,
    "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400,
    "пятьсот": 500, "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
    "тысяча": 1000, "тысячи": 1000, "тысяч": 1000,
    "миллион": 1000000, "миллиард": 1000000000,
}
_NUM_WORD_NAMES = sorted(NUM_WORDS, key=len, reverse=True)
NUM_WORD_RE = re.compile(
    r"(?<![А-Яа-яЁёA-Za-z])(" + "|".join(map(re.escape, _NUM_WORD_NAMES)) + r")(?![А-Яа-яЁёA-Za-z])",
    re.I,
)


def numerize_words_same_len(text: str) -> str:
    """«пять семейств» -> «5    семейств»; длина строки сохраняется (если цифра короче слова),
    чтобы маски и индексы цитат не разъезжались."""
    def rep(mm):
        word = mm.group(0)
        key = word.lower().replace("ё", "е")
        val = NUM_WORDS.get(key)
        if val is None:
            return word
        s = str(val)
        if len(s) >= len(word):
            return s
        return s + " " * (len(word) - len(s))

    return NUM_WORD_RE.sub(rep, text)

COUNT_UNITS = [
    ("канал", "count_channel"),
    ("генератор", "count_generator"),
    ("передатчик", "count_transmitter"),
    ("моноблок", "count_monoblock"),
    ("позици", "count_position"),
    ("семейств", "count_family"),
    ("модел", "count_model"),
    ("станц", "count_station"),
    ("шаг", "count_step"),
    ("тип", "count_type"),
]

# canonical unit -> multiplier
UNIT_MAP = {
    "мгц": ("mhz", 1.0),
    "ггц": ("mhz", 1000.0),
    "км/ч": ("kmh", 1.0),
    "км": ("m", 1000.0),
    "м": ("m", 1.0),
    "мм": ("mm", 1.0),
    "см": ("cm", 1.0),
    "квт": ("w", 1000.0),
    "вт": ("w", 1.0),
    "кг": ("kg", 1.0),
    "г": ("g", 1.0),
    "а·ч": ("ah", 1.0),
    "ач": ("ah", 1.0),
    "ч": ("h", 1.0),
    "мин": ("min", 1.0),
    "час": ("h", 1.0),
    "часов": ("h", 1.0),
    "часа": ("h", 1.0),
    "сутки": ("h", 24.0),
    "суток": ("h", 24.0),
    "день": ("h", 24.0),
    "дня": ("h", 24.0),
    "дней": ("h", 24.0),
    "мес": ("month", 1.0),
    "месяц": ("month", 1.0),
    "месяцев": ("month", 1.0),
    "месяца": ("month", 1.0),
    "месяцы": ("month", 1.0),
    "лет": ("month", 12.0),
    "год": ("month", 12.0),
    "года": ("month", 12.0),
    "годов": ("month", 12.0),
    "%": ("pct", 1.0),
    "°": ("deg", 1.0),
    "м²": ("m2", 1.0),
    "м2": ("m2", 1.0),
}

# ---------------------------------------------------------------- эталонные дисклеймеры
DISCLAIMERS = {
    "D1": "оборудование является радиоэлектронным средством",
    "D2": "поставщик не оказывает юридических услуг",
    "D3": "технические характеристики — по паспорту изделия",
    "D4": "не является публичной офертой",
    "D5": "носят информационный характер",
    "D6": "возможность применения на конкретном объекте подтверждается заказчиком",
    "D7": "не гарантирует получение заказчиком разрешений",
}
LEGAL_DISCLAIMERS = {"D1", "D2", "D5", "D6", "D7"}
P10_DISCLAIMERS = {"D3", "D4", "D1", "D2"}

PRICE_WORD_RE = re.compile(r"\bцен[аыуеи]\b|\bстоимост\w*|\bпрайс\w*", re.I)
PRICE_OK_RE = re.compile(
    r"цена\s+по\s+запросу|по\s+запросу|кп\s+под\s+задачу|не\s+является\s+публичной\s+офертой"
    r"|информация\s+о\s+ценах",
    re.I,
)

# фолбэк, если BANNED.md ещё не написан (APPROVED_CLAIMS.md §5 + market_brief.md §6)
FALLBACK_BANNED = [
    "спасёт жизнь", "спасет жизнь", "спасём жизнь", "гарантированная защита",
    "100% защита", "100 % защита", "абсолютная невидимость", "полная невидимость",
    "дрон не пролетит", "лучший в мире", "№1", "номер один", "уникальный",
    "инновационный", "непревзойдённый", "непревзойденный",
    "работает в любых условиях", "пожизненная гарантия",
    "универсальное решение", "глушит всё", "глушит все",
    "сертифицировано как средство защиты", "разрешено к применению",
    "единственный производитель в россии", "полная защита",
    "гарантирует защиту", "гарантированный результат",
    "обучение бесплатно", "пнр бесплатно", "цена окончательная",
]

MILITARY_RES = [
    (re.compile(r"\bСВО\b"), "Б2", "аббревиатура СВО — военная риторика (бриф §3)"),
    (re.compile(r"зон[аеуы]\s+сво", re.I), "Б2", "«зона СВО» — военная риторика"),
    (re.compile(r"передов(?:ой|ая|ую|ые|ых)", re.I), "Б2", "«передовая» — военная риторика"),
    (re.compile(r"боев(?:ое|ого|ым|ых)\s+применени", re.I), "Б2", "«боевое применение»"),
    (re.compile(r"поражени(?:е|я|и)\s+(?:цели|бпла|дрона|дронов)", re.I), "Б2", "«поражение цели»"),
    (re.compile(r"уничтож(?:ить|ение|ать)\s+(?:дрон|бпла)", re.I), "Б2", "«уничтожить дрон»"),
    (re.compile(r"сбить\s+(?:дрон|бпла)", re.I), "Б2", "«сбить дрон»"),
    (re.compile(r"на\s+позици(?:и|ях)\b", re.I), "З", "«на позиции» — проверить контекст (военная риторика)"),
]

SLOP_RES = [
    (re.compile(r"в\s+современном\s+мире", re.I), "«в современном мире»"),
    (re.compile(r"динамично\s+развивающ", re.I), "«динамично развивающийся»"),
    (re.compile(r"не\s+имеет\s+аналогов", re.I), "«не имеет аналогов»"),
    (re.compile(r"широкий\s+спектр", re.I), "«широкий спектр»"),
    (re.compile(r"комплексное\s+решение", re.I), "«комплексное решение»"),
    (re.compile(r"лидер\s+рынка", re.I), "«лидер рынка»"),
    (re.compile(r"передовые\s+технологии", re.I), "«передовые технологии»"),
    (re.compile(r"высокое\s+качество", re.I), "«высокое качество»"),
    (re.compile(r"надёжный\s+партн[её]р", re.I), "«надёжный партнёр»"),
    (re.compile(r"команда\s+профессионалов", re.I), "«команда профессионалов»"),
    (re.compile(r"индивидуальный\s+подход", re.I), "«индивидуальный подход»"),
    (re.compile(r"гибк\w+\s+систем\w+\s+скидок", re.I), "«гибкая система скидок»"),
]

FORBIDDEN_CSS = [
    (re.compile(r"linear-gradient|radial-gradient|conic-gradient", re.I), "градиент"),
    (re.compile(r"box-shadow\s*:\s*(?!none)", re.I), "box-shadow (тень)"),
    (re.compile(r"text-shadow\s*:\s*(?!none)", re.I), "text-shadow (тень текста)"),
    (re.compile(r"backdrop-filter", re.I), "backdrop-filter (стекломорфизм)"),
    (re.compile(r"filter\s*:\s*blur", re.I), "filter: blur"),
    (re.compile(r"box-shadow\s*:\s*[^;]*0\s+0\s+\d+px", re.I), "неон (0 0 Npx)"),
]
EXTERNAL_RE = re.compile(
    r"(?:https?:)?//(?:fonts\.googleapis|fonts\.gstatic)[^\"'\s)]*"
    r"|(?:https?:)//[^\"'\s)]+\.(?:css|woff2?|ttf|otf|png|jpe?g|webp|svg)",
    re.I,
)
PLACEHOLDER_RE = re.compile(r"\{\{|\}\}|\bTODO\b|\bFIXME\b|lorem\s+ipsum|заглушк|placeholder|\bXXX\b", re.I)
EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F000-\U0001F2FF" "]"
)

ALLOWED_FONT_FAMILIES = ("sofia sans", "oswald", "tektur", "unbounded", "segoe ui")
BAD_FONT_FAMILIES = ("arial", "helvetica", "times new roman", "times", "courier", "verdana", "roboto", "calibri")

FONT_SIZE_DECL_RE = re.compile(r"font-size\s*:\s*([^;{}]+)", re.I)
FONT_SIZE_PX_RE = re.compile(r"([\d.]+)\s*px", re.I)
FONT_SIZE_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*\)", re.I)
CSS_VAR_DEF_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+)", re.I)
FONT_FACE_RE = re.compile(r"@font-face\s*\{(.*?)\}", re.I | re.S)
URL_IN_CSS_RE = re.compile(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", re.I)


# ================================================================ утилиты
def norm_ws(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    s = s.replace("ё", "е").replace("Ё", "Е")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm_ws_raw(s: str) -> str:
    """Как norm_ws, но БЕЗ NFKC: NFKC превращает «№» в «No» и ломает проверку типографики."""
    s = s.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm_match(s: str) -> str:
    """Нормализация для поиска эталонных фраз: кавычки/дефисы/регистр/пробелы."""
    s = norm_ws(s).lower()
    s = s.replace("«", "").replace("»", "").replace("“", "").replace("”", "").replace('"', "")
    s = re.sub(r"[–—−‑]", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_compact(s: str) -> str:
    """Без пробелов/дефисов — для моделей/законов/дат."""
    s = norm_match(s)
    return re.sub(r"[\s\-]+", "", s)


TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def translit(s: str) -> str:
    return "".join(TRANSLIT.get(ch, ch) for ch in s.lower())


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def mask_spans(text: str, spans) -> str:
    if not spans:
        return text
    chars = list(text)
    n = len(chars)
    for s, e in spans:
        for i in range(max(0, s), min(n, e)):
            chars[i] = MASK
    return "".join(chars)


def parse_num(raw: str) -> float:
    c = raw.replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    c = c.replace(",", ".")
    try:
        return float(c)
    except ValueError:
        return 0.0


def unit_canon(raw: str):
    """-> (canonical_unit, multiplier). Пустая строка unit, если не распознано."""
    u = raw.lower().replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    if u in UNIT_MAP:
        return UNIT_MAP[u]
    for prefix, canon in COUNT_UNITS:
        if u.startswith(prefix):
            return canon, 1.0
    return "", 1.0


@dataclass
class Fact:
    value: float
    unit: str
    raw: str
    hi: float | None = None
    kind: str = "single"  # single|range|money|volt|temp

    def ends(self) -> list[float]:
        return [self.value] if self.hi is None else [self.value, self.hi]

    def label(self) -> str:
        if self.hi is not None:
            return f"{fmt(self.value)}–{fmt(self.hi)} {self.unit or ''}".strip()
        return f"{fmt(self.value)} {self.unit or ''}".strip()


def fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".")


@dataclass
class Extracted:
    facts: list[Fact] = field(default_factory=list)
    bare_numbers: list[tuple[float, str]] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    years: list[str] = field(default_factory=list)
    laws: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    price_hits: list[str] = field(default_factory=list)
    masked: str = ""
    normalized: str = ""


def extract_all(text: str) -> Extracted:
    """Извлекает факты/ссылки из текста; masked — текст с замаскированными спец-токенами
    (та же длина, индексы совпадают с исходным текстом)."""
    ex = Extracted()
    ex.normalized = numerize_words_same_len(text)
    m = ex.normalized

    # 1. телефон / URL / e-mail / id / пропорции и размеры холста
    spans = []
    for pat in (PHONE_ANY_RE, URL_RE, EMAIL_RE, POSTER_ID_RE, CLAIM_ID_RE, ASPECT_RE, DIM_RE):
        spans.extend(mm.span() for mm in pat.finditer(m))
    m = mask_spans(m, spans)

    # 2. даты
    spans = []
    for mm in DATE_RE.finditer(m):
        ex.dates.append(mm.group(0))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 3. годы
    spans = []
    for mm in YEAR_RE.finditer(m):
        ex.years.append(mm.group(1))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 4. деньги-диапазоны (30 000–60 000 ₽), затем одиночные суммы
    spans = []
    for mm in MONEY_RANGE_RE.finditer(m):
        mult = {"млрд": 1e9, "млн": 1e6, "тыс": 1e3, "тыс.": 1e3}.get((mm.group(3) or "").lower(), 1.0)
        lo, hi = parse_num(mm.group(1)) * mult, parse_num(mm.group(2)) * mult
        if lo > hi:
            lo, hi = hi, lo
        ex.facts.append(Fact(lo, "rub", mm.group(0).strip(), hi=hi, kind="money"))
        spans.append(mm.span())
    m = mask_spans(m, spans)
    spans = []
    for mm in MONEY_RE.finditer(m):
        val = parse_num(mm.group(1))
        mult = {"млрд": 1e9, "млн": 1e6, "тыс": 1e3, "тыс.": 1e3}.get((mm.group(2) or "").lower(), 1.0)
        ex.facts.append(Fact(val * mult, "rub", mm.group(0).strip(), kind="money"))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 5. вольты (uppercase В, чтобы не путать с предлогом «в»)
    spans = []
    for mm in VOLT_RANGE_RE.finditer(m):
        ex.facts.append(Fact(parse_num(mm.group(1)), "v", mm.group(0).strip(), hi=parse_num(mm.group(2)), kind="volt"))
        spans.append(mm.span())
    m = mask_spans(m, spans)
    spans = []
    for mm in VOLT_SINGLE_RE.finditer(m):
        ex.facts.append(Fact(parse_num(mm.group(1)), "v", mm.group(0).strip(), kind="volt"))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 6. температуры
    spans = []
    for mm in TEMP_RANGE_RE.finditer(m):
        lo = parse_num(mm.group(1).replace("−", "-"))
        hi = parse_num(mm.group(2).replace("−", "-").replace("+", ""))
        ex.facts.append(Fact(lo, "c", mm.group(0).strip(), hi=hi, kind="temp"))
        spans.append(mm.span())
    m = mask_spans(m, spans)
    spans = []
    for mm in TEMP_SINGLE_RE.finditer(m):
        ex.facts.append(Fact(parse_num(mm.group(1).replace("−", "-")), "c", mm.group(0).strip(), kind="temp"))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 7. ссылки на законы / решения
    spans = []
    for pat in LAW_RES:
        for mm in pat.finditer(m):
            ex.laws.append(mm.group(0))
            spans.append(mm.span())
    m = mask_spans(m, spans)

    # 8. модельные коды (К-12М, ИП-24/100, ТП 7-100, B2B, P01 …)
    spans = []
    for mm in MODEL_RE.finditer(m):
        ex.models.append(mm.group(0))
        spans.append(mm.span())
    m = mask_spans(m, spans)

    # 9. общие числовые факты
    fact_spans = []
    for mm in FACT_RE.finditer(m):
        try:
            n1 = parse_num(mm.group("n1"))
        except Exception:
            continue
        s1 = -1.0 if mm.group("s1") in ("-", "−") else 1.0
        n2raw = mm.group("n2")
        unit_raw = mm.group("unit")
        unit, mult = unit_canon(unit_raw)
        if not unit:
            continue
        value = s1 * n1 * mult
        hi = None
        if n2raw:
            s2 = -1.0 if mm.group("s2") in ("-", "−") else 1.0
            hi = s2 * parse_num(n2raw) * mult
            if hi < value:
                value, hi = hi, value
        ex.facts.append(
            Fact(value, unit, text[mm.start():mm.end()].strip(), hi=hi, kind="range" if hi is not None else "single")
        )
        fact_spans.append(mm.span())
    m = mask_spans(m, fact_spans)

    # 10. числа без единицы (например «8000+», «41») — только предупреждение
    bare_spans = []
    for mm in re.finditer(r"\d+(?:[.,]\d+)?", m):
        raw = mm.group(0)
        try:
            val = parse_num(raw)
        except ValueError:
            continue
        ex.bare_numbers.append((val, text[mm.start():mm.end()].strip()))
        bare_spans.append(mm.span())
    m = mask_spans(m, bare_spans)

    # 11. «цена/стоимость/прайс» — слова, даже без цифр
    for mm in PRICE_WORD_RE.finditer(m):
        ex.price_hits.append(m[max(0, mm.start() - 80): mm.end() + 80])

    ex.masked = m
    return ex


# ================================================================ парсер постера
class PosterParser(HTMLParser):
    SKIP_TEXT = {"script", "style", "title", "template", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.css_parts: list[str] = []
        self.images: list[dict] = []
        self.stylesheets: list[str] = []
        self._skip_depth = 0
        self._in_style = False
        self._style_buf: list[str] = []
        self.title = ""
        self.lang = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style":
            self._in_style = True
            self._style_buf = []
        elif tag in self.SKIP_TEXT:
            self._skip_depth += 1
            if tag == "title":
                self._in_title = True
        elif tag == "img":
            self.images.append(
                {
                    "src": a.get("src", ""),
                    "alt": a.get("alt", ""),
                    "width": a.get("width", ""),
                    "height": a.get("height", ""),
                }
            )
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href") or ""
            if "stylesheet" in rel and href:
                self.stylesheets.append(href)
        elif tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        if a.get("style"):
            self.css_parts.append(a["style"])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in self.SKIP_TEXT:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "style":
            self._in_style = False

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
            self.css_parts.append("\n".join(self._style_buf))
            self._style_buf = []
        elif tag in self.SKIP_TEXT:
            self._skip_depth = max(0, self._skip_depth - 1)
            if tag == "title":
                self._in_title = False

    def handle_data(self, data):
        if self._in_style:
            self._style_buf.append(data)
        elif self._skip_depth == 0:
            if self._in_title:
                self.title += data
            else:
                self.text_parts.append(data)


@dataclass
class Poster:
    path: Path
    rel: str
    pid: str
    raw_text: str
    raw_original: str
    html_source: str
    css: str
    images: list[dict]
    stylesheets: list[str]
    title: str
    lang: str


def poster_id_from_name(name: str) -> str:
    mm = re.match(r"(?i)^P(\d{1,2})", name)
    if not mm:
        return "?"
    return f"P{int(mm.group(1)):02d}"


def pid_with_variant(path: Path) -> str:
    """P03 для вертикали; P03-wide / P03-story для вариантов (чтобы не дублировать замечания)."""
    pid = poster_id_from_name(path.name)
    parts = [p.lower() for p in path.parts]
    if "wide" in parts:
        return pid + "-wide"
    if "story" in parts:
        return pid + "-story"
    return pid


def load_poster(path: Path, root: Path) -> Poster:
    html = read_text(path)
    parser = PosterParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # битый HTML
        raise RuntimeError(f"HTML не разбирается: {exc}") from exc
    raw = norm_ws(" ".join(parser.text_parts))
    raw_original = norm_ws_raw(" ".join(parser.text_parts))
    css = "\n".join(parser.css_parts)
    # подтянуть локальные css-файлы (для проверки шрифтов/градиентов/кеглей)
    for href in parser.stylesheets:
        if re.match(r"(?i)^(https?:)?//", href):
            continue
        css_path = (path.parent / href.split("?")[0]).resolve()
        if css_path.is_file():
            css += "\n" + read_text(css_path)
    return Poster(
        path=path,
        rel=str(path.relative_to(root)) if root in path.parents else str(path),
        pid=poster_id_from_name(path.name),
        raw_text=raw,
        raw_original=raw_original,
        html_source=html,
        css=css,
        images=parser.images,
        stylesheets=parser.stylesheets,
        title=norm_ws(parser.title),
        lang=parser.lang,
    )


# ================================================================ claims.json
EXCLUDE_KEYS = {
    "id", "claim_id", "code", "source", "sources", "url", "urls", "notes", "note",
    "comment", "comments", "do_not_use", "forbidden", "ban", "banned", "spory",
    "risk", "poster_ids", "topic", "section", "date", "author", "status", "title",
    "name", "slug", "img", "image", "photo", "file", "files", "path", "paths",
}
CHECKABLE_KEYS = {
    "allowed_text", "text", "statement", "formulation", "numbers", "figures",
    "value", "values", "allowed", "claim", "wording", "message", "copy", "summary",
}


@dataclass
class ClaimsData:
    raw: object
    claims: list[dict]
    status: str
    error: str = ""
    facts: list[Fact] = field(default_factory=list)
    fact_meta: list[tuple[Fact, str, list[str]]] = field(default_factory=list)
    allowed: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    bare_points: list[float] = field(default_factory=list)
    corpus_compact: str = ""
    refs: dict = field(default_factory=dict)
    by_poster: dict[str, list[str]] = field(default_factory=dict)


def claim_texts(claim: dict) -> list[str]:
    """Тексты claim для проверки: только содержательные поля (не id/source/notes)."""
    out: list[str] = []

    def walk(obj, key=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in EXCLUDE_KEYS:
                    continue
                if lk in CHECKABLE_KEYS or not key:
                    walk(v, lk)
                else:
                    walk(v, lk)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, key)
        elif isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, (int, float)):
            out.append(str(obj))

    walk(claim)
    return out


def claim_id(claim: dict) -> str:
    for k in ("id", "claim_id", "code", "cid"):
        v = claim.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "?"


def claim_source_text(claim: dict) -> str:
    parts: list[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in ("source", "sources", "url", "urls", "doc", "docs", "based_on", "basis"):
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, (int, float)):
            parts.append(str(obj))

    walk(claim)
    return " ".join(parts)


def load_claims(path: Path) -> ClaimsData:
    if not path.is_file():
        return ClaimsData(raw=None, claims=[], status="missing", error=f"нет файла {path}")
    try:
        raw = json.loads(read_text(path))
    except Exception as exc:
        return ClaimsData(raw=None, claims=[], status="invalid", error=f"невалидный JSON: {exc}")

    if isinstance(raw, list):
        claims = [c for c in raw if isinstance(c, dict)]
    elif isinstance(raw, dict):
        claims = []
        for key in ("claims", "items", "data", "facts", "list"):
            v = raw.get(key)
            if isinstance(v, list):
                claims = [c for c in v if isinstance(c, dict)]
                break
        if not claims:
            # dict of id -> claim
            vals = [v for v in raw.values() if isinstance(v, dict)]
            if vals and all("allowed_text" in v or "text" in v for v in vals):
                claims = vals
    else:
        claims = []

    cd = ClaimsData(raw=raw, claims=claims, status="ok" if claims else "empty")
    if not claims:
        cd.status = "empty"
        cd.error = "в JSON нет массива утверждений (ожидались claims/items/data)"
        return cd

    corpus_parts: list[str] = []
    for c in claims:
        texts = claim_texts(c)
        corpus_parts.extend(texts)
        ex = extract_all(JOIN.join(texts))
        cd.facts.extend(ex.facts)
        cid = claim_id(c)
        pids: list[str] = []
        for pid in c.get("poster_ids") or c.get("posters") or []:
            if isinstance(pid, str):
                p = pid.strip().upper()
                if re.match(r"^P\d{1,2}$", p):
                    p = f"P{int(p[1:]):02d}"
                    pids.append(p)
                    cd.by_poster.setdefault(p, []).append(cid)
        for f in ex.facts:
            cd.fact_meta.append((f, cid, pids))
    for f in cd.facts:
        cd.allowed.setdefault(f.unit, [])
        if f.hi is not None:
            lo, hi = min(f.value, f.hi), max(f.value, f.hi)
            cd.allowed[f.unit].append((lo, hi))
            cd.bare_points.extend([lo, hi])
        else:
            cd.allowed[f.unit].append((f.value, f.value))
            cd.bare_points.append(f.value)
    corpus = JOIN.join(corpus_parts)
    cd.corpus_compact = norm_compact(corpus)
    ex_all = extract_all(corpus)
    # числа без единицы из claims тоже считаем «подтверждёнными точечно»
    cd.bare_points.extend(v for v, _raw in ex_all.bare_numbers)
    cd.refs = {
        "dates": ex_all.dates,
        "years": ex_all.years,
        "laws": ex_all.laws,
        "models": ex_all.models,
    }
    return cd


# ================================================================ BANNED.md
QUOTE_RES = (
    re.compile(r"«([^»]{2,160})»"),
    re.compile(r"„([^“”]{2,160})[“”]"),
    re.compile(r"“([^”]{2,160})”"),
    re.compile(r'"([^"\n]{2,160})"'),
)
BRAND_ONLY = {
    "киловатт", "мегаватт", "нпо киловатт", "в окопе", "штора", "штора-м", "капюшон",
    "ребус", "поле", "сигнал", "сигнал-м", "в окопе × нпо киловатт", "нпо",
}
CANCELERIT = {"является", "являются", "данный", "данная", "данные", "данных"}
NUMERIC_BAN_RE = re.compile(r"^\d[\d\s.,]*(?:км|м|вт|квт|мгц|ггц|кг|час\w*|ч|%|₽|руб\.?)$", re.I)

# фразы, внутри которых запрещённая лексика допустима (утверждённые дисклеймеры)
DISCLAIMER_PROTECT_RES = [
    re.compile(r"оборудование\s+является\s+радиоэлектронным\s+средством", re.I),
    re.compile(r"поставщик\s+не\s+оказывает\s+юридических\s+услуг", re.I),
    re.compile(r"не\s+явля(?:ется|ются)\s+гарантией(?:\s+поражения)?(?:\s+[А-Яа-яЁё\-]+){0,3}", re.I),
    re.compile(r"не\s+является\s+публичной\s+офертой", re.I),
    re.compile(r"информация\s+о\s+ценах\s+и\s+наличии", re.I),
    re.compile(r"технические\s+характеристики\s*[—–-]\s*по\s+паспорту", re.I),
    re.compile(r"сведения\s+о\s+правовом\s+статусе", re.I),
    re.compile(r"ответственность\s+за\s+соблюдение\s+условий\s+применения", re.I),
]


def _section(text: str, marker: str) -> str:
    """Текст секции от заголовка с marker до следующего заголовка «## »."""
    mm = re.search(re.escape(marker), text)
    if not mm:
        return ""
    start = text.rfind("\n", 0, mm.start()) + 1
    nxt = re.search(r"\n##\s", text[mm.end():])
    end = mm.end() + nxt.start() if nxt else len(text)
    return text[start:end]


def _clean_phrase(p: str) -> str:
    p = unicodedata.normalize("NFKD", p)
    p = "".join(ch for ch in p if not unicodedata.combining(ch))
    p = re.sub(r"\*\*|`|__", "", p).strip(" .;:—-–")
    return norm_match(p)


def _keep_phrase(p: str) -> bool:
    if len(p) < 3:
        return False
    if p in BRAND_ONLY:
        return False
    if NUMERIC_BAN_RE.match(p.replace(" ", "")):
        return False
    if re.fullmatch(r"\d+\s+позици\w*", p):
        return False
    try:
        if MODEL_RE_I.fullmatch(p):
            return False
    except Exception:
        pass
    return True


def parse_banned(path: Path):
    """-> (hard, soft, note). hard — запрещённые формулировки (Б2), soft — стоп-слова
    нейрослопа/канцелярита (З). Источник: BANNED.md §1/§2/§4, иначе фолбэк."""
    fallback = [norm_match(p) for p in FALLBACK_BANNED]
    if not path.is_file():
        return fallback, [], "BANNED.md отсутствует — использован фолбэк APPROVED_CLAIMS §5"
    text = read_text(path)
    sec1 = _section(text, "§1")
    sec2 = _section(text, "§2")
    sec4 = _section(text, "§4")
    hard: set[str] = set()
    soft: set[str] = set()

    table_secs = [s for s in (sec1, sec4) if s]
    if table_secs:
        # в таблицах «Нельзя | Почему | Можно вместо» берём ТОЛЬКО первую колонку
        for sec in table_secs:
            for line in sec.splitlines():
                raw = line.strip()
                if not raw.startswith("|"):
                    continue
                cells = raw.strip("|").split("|")
                first = cells[0].strip() if cells else ""
                if not first or re.match(r"^[-: ]+$", first):
                    continue
                for pat in QUOTE_RES:
                    for mm in pat.finditer(first):
                        hard.add(_clean_phrase(mm.group(1)))
    else:  # запасной путь для нестандартного формата
        for pat in QUOTE_RES:
            for mm in pat.finditer(text):
                hard.add(_clean_phrase(mm.group(1)))

    # §2: стоп-лист нейрослопа (бэктики, разделитель « · » и « / »)
    if sec2:
        for mm in re.finditer(r"`([^`\n]{2,120})`", sec2):
            for part in re.split(r"\s*/\s*", mm.group(1)):
                soft.add(_clean_phrase(part))

    # фолбэк-фразы добавляем, если их нет в BANNED (страховка от неполного парсинга)
    covered = " | ".join(hard | soft)
    for p in fallback:
        if p and p not in covered:
            hard.add(p)

    hard = {p for p in hard if _keep_phrase(p)}
    soft = {p for p in soft if _keep_phrase(p)}
    # канцелярит/слоп — в мягкую категорию (в §1 он тоже есть, но это не «обещание»)
    for w in CANCELERIT:
        if w in hard:
            hard.discard(w)
            soft.add(w)
    hard = sorted(hard, key=len, reverse=True)
    soft = sorted(soft - set(hard), key=len, reverse=True)
    if not hard and not soft:
        return fallback, [], "BANNED.md не распознан — использован фолбэк"
    note = f"BANNED.md: {len(hard)} запрещённых + {len(soft)} стоп-слов нейрослопа"
    return hard, soft, note


def phrase_to_regex(phrase: str) -> re.Pattern:
    toks = [re.escape(t) for t in phrase.split(" ") if t]
    if not toks:
        return re.compile(re.escape(phrase))
    body = r"[\s\-–—−‑]*".join(toks)
    return re.compile(rf"(?<![А-Яа-яЁёA-Za-z0-9]){body}(?![А-Яа-яЁёA-Za-z0-9])", re.I)


MODEL_RE_I = re.compile(MODEL_RE.pattern, re.I)


# ================================================================ проверка чисел
def build_match_index(facts: list[Fact]):
    allowed: dict[str, list[tuple[float, float]]] = {}
    for f in facts:
        if f.hi is not None:
            allowed.setdefault(f.unit, []).append((min(f.value, f.hi), max(f.value, f.hi)))
        else:
            allowed.setdefault(f.unit, []).append((f.value, f.value))
    return allowed


def match_fact(fact: Fact, allowed: dict[str, list[tuple[float, float]]], bare_points: list[float]):
    """-> (status, detail): exact | within | loose | unknown.
    exact/within — только для факта с единицей и только в пределах этой же единицы.
    loose — число без единицы, совпавшее с «точечным» значением факт-базы."""
    eps = 1e-6
    ends = fact.ends()
    ranges = allowed.get(fact.unit) if fact.unit else None

    if fact.unit:
        def end_status(v: float):
            if not ranges:
                return "unknown"
            exact = any(abs(lo - v) < eps or abs(hi - v) < eps for lo, hi in ranges)
            if exact:
                return "exact"
            if any(lo - eps <= v <= hi + eps for lo, hi in ranges):
                return "within"
            return "unknown"

        statuses = [end_status(v) for v in ends]
        if all(s == "exact" for s in statuses):
            return "exact", ""
        if all(s in ("exact", "within") for s in statuses):
            return "within", ""
        # счётные единицы: «8–12 Модели» из склейки блоков — проверим другие count-единицы
        if fact.unit.startswith("count_"):
            other = {"count_channel", "count_generator", "count_transmitter", "count_monoblock",
                     "count_position", "count_family", "count_model", "count_station",
                     "count_step", "count_type"} - {fact.unit}
            for u in other:
                rng = allowed.get(u) or []
                if all(any(lo - eps <= v <= hi + eps for lo, hi in rng) for v in ends):
                    return "loose", "единица счёта уточняется по контексту"
        missing = [fmt(v) for v, s in zip(ends, statuses) if s == "unknown"]
        return "unknown", "нет в claims: " + ", ".join(missing)

    # без единицы — только более осторожное «loose» по точечным значениям
    for v in ends:
        if any(abs(p - v) < eps for p in bare_points):
            return "loose", "цифра без единицы"
    return "unknown", "нет в claims"


# ================================================================ CSS/HTML проверки
def css_checks(poster: Poster, root: Path) -> list[dict]:
    out: list[dict] = []
    css = re.sub(r"/\*.*?\*/", " ", poster.css or "", flags=re.S)  # без комментариев
    # латинское «No» вместо «№» — типографика (проверяем ДО NFKC: NFKC превращает № в No)
    for mm in LATIN_NO_RE.finditer(poster.raw_original):
        out.append({"code": "З", "msg": "латинское «No» вместо «№» — типографика", "quote": norm_ws(poster.raw_original[max(0, mm.start() - 40): mm.end() + 40])[:160]})

    for pat, label in FORBIDDEN_CSS:
        for mm in pat.finditer(css):
            out.append(
                {
                    "code": "Б3",
                    "msg": f"запрещённый визуальный приём: {label}",
                    "quote": norm_ws(css[max(0, mm.start() - 40): mm.end() + 40])[:160],
                }
            )

    for mm in EXTERNAL_RE.finditer(css):
        out.append({"code": "Б3", "msg": "внешний ресурс (шрифт/картинка/стиль) — офлайн запрещён", "quote": mm.group(0)[:160]})
    for mm in re.finditer(r"(?i)@import\s+(?:url\()?['\"]?(https?:)?//", css):
        out.append({"code": "Б3", "msg": "внешний @import", "quote": mm.group(0)[:160]})

    # переменные (размеры + шрифтовые цепочки)
    var_defs: dict[str, str] = {}
    for mm in CSS_VAR_DEF_RE.finditer(css):
        var_defs[mm.group(1)] = mm.group(2).strip()

    def resolve_vars(value: str, depth: int = 0) -> str:
        if depth > 4:
            return value

        def rep(m):
            name = m.group(1)
            if name in var_defs:
                return resolve_vars(var_defs[name], depth + 1)
            return m.group(0)

        return FONT_SIZE_VAR_RE.sub(rep, value)

    # кегли
    for mm in FONT_SIZE_DECL_RE.finditer(css):
        val_raw = resolve_vars(mm.group(1).strip())
        px = FONT_SIZE_PX_RE.search(val_raw)
        if not px:
            continue
        try:
            value = float(px.group(1))
        except ValueError:
            continue
        if value < 13:
            start = css.rfind("}", 0, mm.start()) + 1
            brace = css.find("{", start)
            sel = norm_ws(css[start:brace])[:70] if brace != -1 else ""
            # микро-типографика дизайн-системы (.label и техметки) — не «подписи», см. правило Lead
            if re.search(r"\.(?:label|micro|meta|kicker|colophon|service|tech|badge|tag)\b", sel, re.I):
                continue
            # правило из общего CSS не используется в этом постере -> не шумим
            classes = re.findall(r"\.([A-Za-z][\w-]{2,})", sel)
            if classes and not any(c in poster.html_source for c in classes):
                continue
            if "disclaimer" in sel.lower():
                out.append(
                    {
                        "code": "З" if value < 12 else "И",
                        "msg": f"юридическая мелкая печать {fmt(value)}px (Lead: норма для сносок 12px)",
                        "quote": (sel + " { font-size:" if sel else "font-size:") + f" {fmt(value)}px",
                    }
                )
                continue
            out.append(
                {
                    "code": "Б3" if value < 11 else "З",
                    "msg": f"кегль {fmt(value)}px меньше нормы 13px для содержательных подписей (бриф §5)",
                    "quote": (sel + " { font-size:" if sel else "font-size:") + f" {fmt(value)}px",
                }
            )

    # шрифтовые цепочки (с раскрытием var())
    referenced_chains: list[str] = []
    for mm in re.finditer(r"font-family\s*:\s*([^;}]+)", css, re.I):
        chain = norm_ws(resolve_vars(mm.group(1))).lower()
        referenced_chains.append(chain)
        first = chain.split(",")[0].strip().strip("'\"")
        if any(bad in first for bad in BAD_FONT_FAMILIES):
            out.append({"code": "Б3", "msg": f"подмена шрифта: первым в цепочке стоит «{first}»", "quote": norm_ws(mm.group(0))[:160]})
        elif not any(ok in chain for ok in ALLOWED_FONT_FAMILIES):
            out.append({"code": "З", "msg": f"в font-family нет разрешённых шрифтов пакета: «{first}»", "quote": norm_ws(mm.group(0))[:160]})
    for name, val in var_defs.items():
        if "font" in name or "family" in name:
            referenced_chains.append(norm_ws(val).lower())
    referenced_text = " ".join(referenced_chains)

    # @font-face -> файлы шрифтов
    base = poster.path.parent
    kw_fonts = root.parent / "kilowatt" / "design" / "fonts"
    for block in FONT_FACE_RE.finditer(css):
        fam_m = re.search(r"font-family\s*:\s*([^;}]+)", block.group(1), re.I)
        fam = norm_ws(fam_m.group(1)).strip("'\"").lower() if fam_m else ""
        used = bool(fam) and fam in referenced_text
        for um in URL_IN_CSS_RE.finditer(block.group(1)):
            u = um.group(1).strip().strip("'\"")
            if u.startswith(("data:", "http:", "https:", "//")):
                continue
            fname = Path(u.split("?")[0]).name
            fp = (base / u.split("?")[0]).resolve()
            if fp.is_file():
                continue
            alt = None
            for sub in (root / "02_МАКЕТЫ" / "_design", root / "02_МАКЕТЫ"):
                cand = (sub / u.split("?")[0]).resolve()
                if cand.is_file():
                    alt = cand
                    break
            if alt:
                continue
            if (kw_fonts / fname).is_file():
                out.append(
                    {
                        "code": "З",
                        "msg": f"шрифт «{fam or fname}» есть в kilowatt/design/fonts, но не скопирован в _design/fonts — при офлайн-рендере подменится фолбэком",
                        "quote": fname,
                    }
                )
            elif used:
                out.append({"code": "Б3", "msg": f"файл шрифта не найден, шрифт используется: «{fam}» ({u})", "quote": fname})
            else:
                out.append({"code": "З", "msg": f"@font-face ссылается на отсутствующий файл шрифта: «{fam or fname}» ({u})", "quote": fname})

    # картинки
    for img in poster.images:
        src = (img.get("src") or "").strip()
        if not src or src.startswith(("data:", "http:", "https:", "//")):
            if src.startswith(("http:", "https:", "//")):
                out.append({"code": "Б3", "msg": "внешняя картинка (офлайн запрещено)", "quote": src[:160]})
            continue
        fp = (base / src.split("?")[0]).resolve()
        if not fp.is_file():
            alt = (root / "02_МАКЕТЫ" / src.split("?")[0]).resolve()
            if not alt.is_file():
                out.append({"code": "Б3", "msg": f"битая ссылка на фото: {src}", "quote": str(fp)})
                continue
            fp = alt
        if Image is not None:
            try:
                with Image.open(fp) as im:
                    w, h = im.size
                if w < 200 or h < 200:
                    out.append({"code": "З", "msg": f"очень маленькое фото {w}×{h}: {src}", "quote": str(fp)})
            except Exception:
                out.append({"code": "З", "msg": f"файл фото не читается: {src}", "quote": str(fp)})
        if not (img.get("alt") or "").strip():
            out.append({"code": "З", "msg": f"у фото нет alt: {src}", "quote": str(fp)})

    # шаблонные заглушки / заглушечный контент
    for mm in PLACEHOLDER_RE.finditer(poster.raw_text):
        out.append({"code": "Б3", "msg": "незаполненная заглушка/шаблон в тексте", "quote": poster.raw_text[max(0, mm.start() - 40): mm.end() + 40]})

    # эмодзи в печатном макете
    for mm in EMOJI_RE.finditer(poster.raw_text):
        out.append({"code": "З", "msg": "эмодзи в печатном макете", "quote": poster.raw_text[max(0, mm.start() - 30): mm.end() + 30]})

    return out


def photo_text_match(poster: Poster, root: Path) -> list[dict]:
    """Эвристика «фото соответствует модели»: имя файла фото должно читаться в тексте постера
    (с транслитерацией). Если нет — И: проверить вручную."""
    out: list[dict] = []
    text_t = re.sub(r"[^a-z0-9]", "", translit(poster.raw_text))
    for img in poster.images:
        src = (img.get("src") or "").strip()
        if not src or src.startswith(("data:", "http")):
            continue
        stem = Path(src.split("?")[0]).stem.lower()
        if "brand" in src.lower() or "logo" in stem or stem in {"grain", "noise", "texture"}:
            continue  # логотипы/текстуры не товарные фото
        cand = re.sub(r"[^a-z0-9]", "", stem)
        tokens = [t for t in re.split(r"[^a-z0-9]+", stem) if len(t) >= 3]
        hit = (len(cand) >= 4 and cand in text_t) or any(t in text_t for t in tokens)
        if not hit:
            out.append({"code": "И", "msg": f"фото {stem}: модель/слово не найдено в тексте постера — сверить вручную", "quote": src})
    return out


MODEL_IGNORE = {
    "b2b", "b2c", "b2g", "b2b2c", "b2b-", "d2c", "smtp", "http", "https", "rgb", "srgb",
    "pdf", "png", "jpg", "html", "css", "p01", "p02", "p03", "p04", "p05", "p06", "p07",
    "p08", "p09", "p10",
}


def ref_in_corpus(ref: str, corpus_compact: str) -> bool:
    """Проверка правовой/датной ссылки: сначала точная подстрока, затем цифровые группы."""
    if norm_compact(ref) and norm_compact(ref) in corpus_compact:
        return True
    digits = re.findall(r"\d+", ref)
    if digits:
        return any(len(d) >= 2 and d in corpus_compact for d in digits)
    return False


def ctx_both(text: str, normalized: str, needle: str) -> str:
    return ctx_of(text, needle) or ctx_of(normalized, needle)


# ================================================================ проверка постера
def claim_provenance(fact: Fact, claims: ClaimsData, pid: str):
    """-> (approved_ids, other_poster_ids, reference_ids) для цифры факта."""
    approved: list[str] = []
    other: list[str] = []
    ref: list[str] = []
    for fc, cid, pids in claims.fact_meta:
        st, _ = match_fact(fact, build_match_index([fc]), fc.ends())
        if st not in ("exact", "within"):
            continue
        if not pids:
            ref.append(cid)
        elif pid in pids:
            approved.append(cid)
        else:
            other.append(cid)
    return approved, other, ref


def check_poster(poster: Poster, claims: ClaimsData, banned_hard: list[str], banned_soft: list[str], root: Path):
    findings: list[dict] = []
    stats: dict = {}
    text = poster.raw_text
    ex = extract_all(text)

    # --- Б1/цифры
    exact = within = loose = 0
    unverified: list[Fact] = []
    loose_facts: list[Fact] = []
    within_facts: list[Fact] = []
    for f in ex.facts:
        if f.kind == "money":
            mst, _ = match_fact(f, claims.allowed, claims.bare_points)
            if mst != "unknown":
                continue
            before = text[: text.find(f.raw)] if f.raw and f.raw in text else ""
            if re.search(r"(?:\d+\s+){2,}$", before):
                findings.append(
                    {
                        "code": "И",
                        "msg": f"₽-число «{f.raw}» похоже на деление шкалы графика, а не на факт",
                        "quote": ctx_both(text, ex.normalized, f.raw),
                    }
                )
                continue
            if f.value >= 1e8:
                findings.append(
                    {
                        "code": "З",
                        "msg": f"крупная ₽-цифра «{f.raw}» вне факт-базы (рыночный объём?) — сверить с claims",
                        "quote": ctx_both(text, ex.normalized, f.raw),
                    }
                )
            else:
                findings.append(
                    {
                        "code": "Б5",
                        "msg": "цена/сумма в постере — цены не публикуются; значение не процитировано",
                        "quote": "••• ₽ (значение скрыто)",
                    }
                )
            continue
        status, detail = match_fact(f, claims.allowed, claims.bare_points)
        if status in ("exact", "within"):
            # происхождение цифры: claim должен быть привязан К ЭТОМУ постеру
            appr, oth, ref = claim_provenance(f, claims, poster.pid)
            if not appr and ref:
                findings.append(
                    {
                        "code": "Б1",
                        "msg": f"параметр из справочного claim {', '.join(ref[:3])} (poster_ids []) — не для постеров: {f.raw}",
                        "quote": ctx_both(text, ex.normalized, f.raw),
                    }
                )
            elif not appr and oth and False:  # poster_ids у factchecker частичные — не шумим
                findings.append(
                    {
                        "code": "З",
                        "msg": f"цифра подтверждена claim'ом, привязанным к другим постерам ({', '.join(oth[:4])}): {f.raw}",
                        "quote": ctx_both(text, ex.normalized, f.raw),
                    }
                )
        if status == "exact":
            exact += 1
        elif status == "within":
            within += 1
            within_facts.append(f)
        elif status == "loose":
            loose += 1
            loose_facts.append(f)
        else:
            unverified.append(f)
            findings.append(
                {
                    "code": "Б1",
                    "msg": f"неподтверждённая цифра: {f.raw} — {detail}",
                    "quote": ctx_both(text, ex.normalized, f.raw),
                }
            )
    stats["numbers_checked"] = len(ex.facts)
    stats["numbers_exact"] = exact
    stats["numbers_within"] = within
    stats["numbers_loose"] = loose
    stats["numbers_unknown"] = len(unverified)
    stats["numbers_verified"] = exact
    for f in within_facts:
        findings.append(
            {
                "code": "З",
                "msg": f"цифра внутри подтверждённого диапазона факт-базы ({f.raw}) — сверить привязку к модели вручную",
                "quote": ctx_both(text, ex.normalized, f.raw),
            }
        )
    for f in loose_facts:
        code = "И" if f.unit.startswith("count_") else "З"
        findings.append({"code": code, "msg": f"единица счёта уточняется по контексту (распознано как «{f.raw}»)", "quote": ctx_both(text, ex.normalized, f.raw)})

    # числа без единицы (например «8000+», «41») — замечание, ручная сверка
    bare_unknown = []
    for val, raw in ex.bare_numbers:
        if raw.startswith("0") or abs(val) < 10:  # 01/02/11.2026 — служебная нумерация
            continue
        if any(abs(val - p) < 1e-6 for p in claims.bare_points):
            continue
        bare_unknown.append((val, raw))
    stats["bare_numbers"] = len(ex.bare_numbers)
    stats["bare_unknown"] = len(bare_unknown)
    for _val, raw in bare_unknown:
        findings.append(
            {
                "code": "З",
                "msg": f"число без единицы не найдено в факт-базе: {raw}",
                "quote": ctx_both(text, ex.normalized, raw),
            }
        )

    # --- даты/годы/законы/модели
    cur_year = str(datetime.now().year)
    for d in set(ex.dates):
        if d.split(".")[-1] == cur_year:  # служебная дата выпуска, не факт
            continue
        if not ref_in_corpus(d, claims.corpus_compact):
            findings.append({"code": "З", "msg": f"дата вне факт-базы: {d}", "quote": ctx_both(text, ex.normalized, d)})
    for y in set(ex.years):
        if norm_compact(y) not in claims.corpus_compact:
            findings.append({"code": "З", "msg": f"год вне факт-базы: {y}", "quote": ctx_both(text, ex.normalized, y)})
    for law in set(ex.laws):
        if not ref_in_corpus(law, claims.corpus_compact):
            findings.append({"code": "З", "msg": f"правовая ссылка вне факт-базы: {law}", "quote": ctx_both(text, ex.normalized, law)})
    for mdl in set(ex.models):
        if norm_compact(mdl) in MODEL_IGNORE:
            continue
        if norm_compact(mdl) not in claims.corpus_compact:
            findings.append({"code": "З", "msg": f"модель/маркировка вне факт-базы: {mdl}", "quote": ctx_both(text, ex.normalized, mdl)})

    # --- Б2/антислоп
    protected: list[tuple[int, int]] = []
    for pat in DISCLAIMER_PROTECT_RES:
        protected.extend(mm.span() for mm in pat.finditer(text))

    def in_disclaimer(idx: int) -> bool:
        return any(s <= idx < e for s, e in protected)

    banned_hits = 0
    for phrase in banned_hard:
        if len(phrase) < 4:
            continue
        for mm in phrase_to_regex(phrase).finditer(text):
            if in_disclaimer(mm.start()):
                findings.append(
                    {
                        "code": "И",
                        "msg": f"«{mm.group(0)}» — внутри утверждённого дисклеймера, допустимо",
                        "quote": ctx_both(text, ex.normalized, mm.group(0)),
                    }
                )
                continue
            banned_hits += 1
            findings.append(
                {
                    "code": "Б2",
                    "msg": f"запрещённая формулировка: «{mm.group(0)}»",
                    "quote": ctx_both(text, ex.normalized, mm.group(0)),
                }
            )
    for phrase in banned_soft:
        if len(phrase) < 4:
            continue
        for mm in phrase_to_regex(phrase).finditer(text):
            if in_disclaimer(mm.start()):
                continue
            findings.append(
                {
                    "code": "З",
                    "msg": f"нейрослоп/канцелярит: «{mm.group(0)}» (BANNED.md §2)",
                    "quote": ctx_both(text, ex.normalized, mm.group(0)),
                }
            )
    for pat, code, msg in MILITARY_RES:
        for mm in pat.finditer(text):
            if in_disclaimer(mm.start()):
                continue
            banned_hits += 1
            findings.append({"code": code, "msg": msg, "quote": ctx_both(text, ex.normalized, mm.group(0))})
    for pat, msg in SLOP_RES:
        for mm in pat.finditer(text):
            if in_disclaimer(mm.start()):
                continue
            findings.append({"code": "З", "msg": f"нейрослоп: {msg}", "quote": ctx_both(text, ex.normalized, mm.group(0))})
    for mm in OPERATOR_BAN_RE.finditer(text):
        banned_hits += 1
        findings.append(
            {
                "code": "Б2",
                "msg": "BANNED §1 (SPORY S24): «работает без оператора» / «не требует оператора» — заменить на «включается из кабины, питание от бортовой сети» (C088)",
                "quote": ctx_both(text, ex.normalized, mm.group(0)),
            }
        )
    stats["banned_hits"] = banned_hits

    # --- Б5/цены
    price_hits = 0
    for hit in ex.price_hits:
        if PRICE_OK_RE.search(hit):
            findings.append({"code": "И", "msg": "допустимая формулировка про цену («по запросу»/оферта)", "quote": norm_ws(hit)[:160]})
            continue
        if not re.search(r"\d[\d\s.,]*(?:₽|руб(?:\.|лей)?|р\.)", hit, re.I):
            findings.append({"code": "И", "msg": "упоминание цены/стоимости без значения — не публикация цены", "quote": norm_ws(hit)[:160]})
            continue
        price_hits += 1
        findings.append({"code": "Б5", "msg": "цена/сумма в постере — цены не публикуются; значение не процитировано", "quote": "••• ₽ (значение скрыто)"})
    stats["price_hits"] = price_hits

    # --- CTA
    cta_tg = bool(CTA_TG_RE.search(text))
    phone_present = PHONE_DIGITS in re.sub(r"\D", "", text)
    if not cta_tg:
        findings.append({"code": "Б4", "msg": "нет CTA Telegram @vokope_ru", "quote": ctx_of(text, "Telegram")})
    if not phone_present:
        findings.append({"code": "Б4", "msg": "нет CTA-телефона +7 999 136-71-42", "quote": ctx_of(text, "телефон")})
    if not DELIVERY_RE.search(text):
        findings.append({"code": "З", "msg": "нет строки «Доставка по РФ» (бриф §5, CTA строго)", "quote": ""})
    if not PICKUP_RE.search(text):
        findings.append({"code": "З", "msg": "нет строки «Самовывоз в Москве» (бриф §5, CTA строго)", "quote": ""})
    stats["cta"] = cta_tg and phone_present

    # --- дисклеймеры
    text_n = norm_match(text)
    found_disclaimers: list[str] = []
    for key, phrase in DISCLAIMERS.items():
        if norm_match(phrase) in text_n:
            found_disclaimers.append(key)
    need = None
    if poster.pid in ("P05", "P06"):
        need = LEGAL_DISCLAIMERS
    elif poster.pid == "P10":
        need = P10_DISCLAIMERS
    if need is not None:
        if not (set(found_disclaimers) & need):
            findings.append(
                {
                    "code": "Б4",
                    "msg": f"нет дисклеймера (market_brief §5.5) — ожидался один из {sorted(need)}",
                    "quote": "P05/P06/P10 обязаны иметь дисклеймер",
                }
            )
        stats["disclaimer"] = sorted(found_disclaimers)
    else:
        stats["disclaimer"] = "n/a"

    # --- логотип/служебная строка
    if "в окопе" not in text.lower():
        findings.append({"code": "З", "msg": "нет wordmark «В ОКОПЕ» в тексте (бриф §6)", "quote": ""})
    if "киловатт" not in text.lower():
        findings.append({"code": "З", "msg": "нет строки «НПО „Киловатт“ · производитель» (бриф §6)", "quote": ""})
    if not re.search(r"\bP\d{1,2}\b", text):
        findings.append({"code": "З", "msg": "нет номера постера в служебной строке (бриф §6)", "quote": ""})
    if not re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", text) and "2026" not in text:
        findings.append({"code": "З", "msg": "нет даты в служебной строке (бриф §6)", "quote": ""})

    # --- CSS/HTML
    css_findings = css_checks(poster, root)
    findings.extend(css_findings)

    # --- эвристика фото
    findings.extend(photo_text_match(poster, root))

    # --- привязка claims
    linked = claims.by_poster.get(poster.pid, [])
    stats["claims_linked"] = len(linked)
    if claims.status == "ok" and not linked:
        findings.append({"code": "З", "msg": f"в claims.json нет утверждений с poster_ids, включающим {poster.pid}", "quote": ""})

    stats["text_len"] = len(text)

    # дедупликация одинаковых замечаний (например, один и тот же var(--font-*) в CSS)
    seen: set[tuple] = set()
    dedup: list[dict] = []
    for f in findings:
        key = (f.get("code"), f.get("msg"), f.get("quote", ""))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(f)
    return dedup, stats


def ctx_of(text: str, needle: str, width: int = 70) -> str:
    if not needle:
        return ""
    i = text.find(needle)
    if i < 0:
        return ""
    s, e = max(0, i - width), i + len(needle) + width
    frag = text[s:e]
    frag = norm_ws(frag)
    if s > 0:
        frag = "…" + frag
    if e < len(text):
        frag = frag + "…"
    return frag


# ================================================================ claims vs источники
def build_file_index(roots: list[Path]) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = {}
    exts = (".md", ".json", ".js", ".html", ".txt", ".css")
    skip_dirs = {"node_modules", "__pycache__", ".git", ".venv", "venv", "_evidence"}
    for root in roots:
        if not root or not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
            for fn in filenames:
                if fn.lower().endswith(exts):
                    idx.setdefault(fn.lower(), []).append(Path(dirpath) / fn)
    return idx


SRC_NAME_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_\-]+\.(?:md|json|js|html|txt)", re.I)


def check_claims_against_sources(claims: ClaimsData, index: dict[str, list[Path]]) -> list[dict]:
    audit: list[dict] = []
    cache: dict[Path, Extracted] = {}
    for claim in claims.claims:
        cid = claim_id(claim)
        src = claim_source_text(claim)
        names = []
        for mm in SRC_NAME_RE.finditer(src):
            n = os.path.basename(mm.group(0)).lower()
            if n not in names and n in index:
                names.append(n)
        entry = {"id": cid, "sources": [], "missing_numbers": [], "missing_refs": [], "status": ""}
        if not names:
            entry["status"] = "no_local_source"
            audit.append(entry)
            continue
        ex_claim = extract_all(JOIN.join(claim_texts(claim)))
        src_facts: list[Fact] = []
        src_texts: list[str] = []
        for n in names:
            for fp in index[n][:3]:
                entry["sources"].append(str(fp))
                if fp not in cache:
                    cache[fp] = extract_all(read_text(fp))
                src_facts.extend(cache[fp].facts)
                src_texts.append(read_text(fp))
        allowed = build_match_index(src_facts)
        bare = [x for f in src_facts for x in ([f.value] if f.hi is None else [f.value, f.hi])]
        for f in ex_claim.facts:
            st, _ = match_fact(f, allowed, bare)
            if st == "unknown":
                entry["missing_numbers"].append(f.raw)
        src_compact = norm_compact(JOIN.join(src_texts))
        for ref in ex_claim.dates:
            if norm_compact(ref) in src_compact:
                continue
            if ref.split(".")[-1] in src_compact:  # хотя бы год
                continue
            entry["missing_refs"].append(ref)
        for ref in ex_claim.years + ex_claim.laws:
            if not ref_in_corpus(ref, src_compact):
                entry["missing_refs"].append(ref)
        if entry["missing_numbers"] or entry["missing_refs"]:
            entry["status"] = "mismatch"
        else:
            entry["status"] = "ok"
        audit.append(entry)
    return audit


# ================================================================ отчёт
def redact_prices(text: str) -> str:
    """Не выносить в отчёт значения цен: цифры рядом с ₽/руб. заменяются."""
    return re.sub(
        r"(\d[\d\s.,]*)\s*(₽|руб(?:\.|лей)?|р\.)",
        "••• ₽",
        text,
        flags=re.I,
    )


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render_md(result: dict) -> str:
    L: list[str] = []
    ap = L.append
    s = result["summary"]
    ap("# QA_АВТОПРОВЕРКА — пакет «ДВА ГОРИЗОНТА»")
    ap("")
    ap(f"- Прогон: **{result['generated']}**, скрипт `check_claims.py` v{VERSION}")
    ap(f"- Входы: claims.json — **{result['inputs']['claims']}**; BANNED.md — **{result['inputs']['banned']}**; постеров найдено — **{result['inputs']['posters_found']}**")
    ap(f"- Источник цифр: `infographics\\01_ФАКТЫ\\claims.json` (единственный по брифу §7.1)")
    ap("")
    if s["blockers"] == 0 and result["inputs"]["claims"] == "ok" and result["inputs"]["posters_found"] >= 10:
        verdict = "✅ **Блокеров не обнаружено** (автопроверка). Требуется визуальный аудит PNG — см. `QA_ОТЧЁТ.md`."
    elif s["blockers"] == 0:
        verdict = "ℹ️ Блокеров нет, но пакет ещё не полон (не все входы на месте) — прогон **промежуточный**."
    else:
        verdict = f"❌ **Не сдано: {s['blockers']} блокер(ов)** (автопроверка). Перечень ниже."
    ap(f"## Итог: {verdict}")
    ap("")
    ap(f"Блокеры: **{s['blockers']}** · Замечания: **{s['warnings']}** · Инфо: **{s['infos']}** · "
       f"Цифры: проверено {s['numbers_checked']}, точное совпадение {s['numbers_exact']}, "
       f"внутри диапазона (ручная сверка) {s['numbers_within']}, не подтверждено {s['numbers_unknown']}")
    ap("")

    # таблица по постерам
    ap("## 1. Таблица по постерам")
    ap("")
    ap("| Постер | Файл | Цифры точно/всего (в диапазоне) | Б1 | Б2 | Б3 | Б4 | Б5 | З | Вердикт |")
    ap("|---|---|---|---|---|---|---|---|---|---|")
    for pid in sorted(result["posters"].keys()):
        p = result["posters"][pid]
        f = p["findings"]
        cnt = {c: sum(1 for x in f if x["code"] == c) for c in ("Б1", "Б2", "Б3", "Б4", "Б5", "З")}
        st = p["stats"]
        num = f"{st.get('numbers_exact', 0)}/{st.get('numbers_checked', 0)} ({st.get('numbers_within', 0)})"
        verdict = "❌ не сдано" if any(cnt[c] for c in ("Б1", "Б2", "Б3", "Б4", "Б5")) else ("⚠ замечания" if cnt["З"] else "✅")
        ap(f"| {pid} | `{md_escape(p['rel'])}` | {num} | {cnt['Б1']} | {cnt['Б2']} | {cnt['Б3']} | {cnt['Б4']} | {cnt['Б5']} | {cnt['З']} | {verdict} |")
    for pid, path in result["missing_posters"].items():
        ap(f"| {pid} | `{md_escape(path)}` | — | — | — | — | — | — | — | ❌ нет файла |")
    ap("")

    # блокеры
    blockers = [x for x in result["findings"] if x["code"].startswith("Б")]
    ap("## 2. Блокеры")
    ap("")
    if not blockers:
        ap("Блокеров нет.")
    else:
        for b in blockers:
            ap(f"- **{b['code']}** `{md_escape(b['poster'])}` · {redact_prices(b['msg'])}")
            if b.get("quote"):
                ap(f"  - цитата: «{redact_prices(b['quote'])}»")
            ap(f"  - файл: `{md_escape(b['path'])}`")
    ap("")

    # замечания
    warns = [x for x in result["findings"] if x["code"] in ("З", "И")]
    ap("## 3. Замечания и информация")
    ap("")
    if not warns:
        ap("Замечаний нет.")
    else:
        for w in warns:
            ap(f"- **{w['code']}** `{md_escape(w['poster'])}` · {redact_prices(w['msg'])}"
               + (f" — «{redact_prices(w['quote'])}»" if w.get("quote") else "")
               + f" · `{md_escape(w['path'])}`")
    ap("")

    # claims audit
    ap("## 4. Факт-база: claims.json против первоисточников")
    ap("")
    if claims_audit := result["claims_audit"]:
        no_src = sum(1 for c in claims_audit if c["status"] == "no_local_source")
        ok = sum(1 for c in claims_audit if c["status"] == "ok")
        bad = [c for c in claims_audit if c["status"] == "mismatch"]
        ap(f"- Утверждений в claims.json: **{len(claims_audit)}**")
        ap(f"- Найдено в локальном первоисточнике: **{ok}** · источника нет локально (посты TG/URL): **{no_src}** · расхождений: **{len(bad)}**")
        if bad:
            ap("")
            ap("| claim_id | источники | цифры не найдены | ссылки не найдены |")
            ap("|---|---|---|---|")
            for c in bad:
                ap(f"| {c['id']} | {md_escape('; '.join(c['sources']) or '—')} | {md_escape(', '.join(c['missing_numbers']) or '—')} | {md_escape(', '.join(c['missing_refs']) or '—')} |")
    else:
        ap("Проверка не выполнялась: claims.json отсутствует или пуст.")
    ap("")

    # покрытие
    ap("## 5. Покрытие постеров утверждениями")
    ap("")
    ap("| Постер | claims_linked |")
    ap("|---|---|")
    for pid in sorted(result["posters"].keys()) + sorted(result["missing_posters"].keys()):
        if pid in result["posters"]:
            ap(f"| {pid} | {result['posters'][pid]['stats'].get('claims_linked', 0)} |")
        else:
            ap(f"| {pid} | — |")
    ap("")

    # входы
    ap("## 6. Входы и файлы")
    ap("")
    ap("| Что | Статус |")
    ap("|---|---|")
    ap(f"| `01_ФАКТЫ\\claims.json` | {result['inputs']['claims']} |")
    ap(f"| `01_ФАКТЫ\\BANNED.md` | {result['inputs']['banned']} |")
    for pf in result["posters_order"]:
        ap(f"| `{md_escape(pf['rel'])}` | {'✅ проверен' if pf.get('parsed') else '❌ ошибка разбора'} |")
    for pid, path in result["missing_posters"].items():
        ap(f"| `{md_escape(path)}` | ❌ нет файла |")
    ap("")

    ap("## 7. Методика и ограничения")
    ap("")
    ap("- Текст извлечён из HTML без тегов; SVG-подписи включены; `<style>`/`<script>` исключены.")
    ap("- Числа сверяются с числами из содержательных полей claims.json (allowed_text/numbers/…); "
       "поля id/source/notes/risk/forbidden исключены, чтобы спорные цифры не «легализовались».")
    ap("- Статус «within» (внутри подтверждённого диапазона той же единицы) — **не** доказывает привязку "
       "к конкретной модели: посмодельная сверка выполняется вручную в `QA_ОТЧЁТ.md`.")
    ap("- Автопроверка не заменяет визуальный аудит PNG: контраст, обрезка фото, «поплывшие» шрифты "
       "проверяются на финальных PNG через `read_image`.")
    ap("- Значения цен намеренно не выводятся в отчёт (бриф §5: цены не публикуем).")
    ap("")
    ap("_Отчёт сгенерирован автоматически; ручные правки запрещены — перезапустите скрипт._")
    return "\n".join(L) + "\n"


# ================================================================ основной прогон
@dataclass
class Paths:
    root: Path
    claims: Path
    banned: Path
    posters: Path
    qa: Path
    out_md: Path
    out_json: Path
    source_roots: list[Path]
    poster_filter: str = ""


def run(paths: Paths, write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    claims = load_claims(paths.claims)
    banned_hard, banned_soft, banned_note = parse_banned(paths.banned)

    poster_files: list[Path] = []
    if paths.posters.exists():
        poster_files = sorted(paths.posters.rglob("*.html"))
    poster_files = [p for p in poster_files if not any(part.startswith("_") for part in p.relative_to(paths.posters).parts[:-1])]
    if paths.poster_filter:
        flt = paths.poster_filter.upper()
        poster_files = [p for p in poster_files if pid_with_variant(p) == flt or p.name.upper().startswith(flt)]

    # соответствие ожидаемым именам — только для вертикальных постеров
    vertical_files = [p for p in poster_files if p.parent == paths.posters]
    found_ids = {poster_id_from_name(p.name) for p in vertical_files}
    missing: dict[str, str] = {}
    for pid, fname in EXPECTED_POSTERS.items():
        if pid not in found_ids:
            missing[pid] = fname

    posters: dict[str, dict] = {}
    findings: list[dict] = []
    posters_order: list[dict] = []
    for path in poster_files:
        pid = pid_with_variant(path)
        try:
            poster = load_poster(path, paths.root)
        except Exception as exc:
            f = {"code": "Б3", "poster": pid, "msg": f"постер не разбирается: {exc}", "quote": "", "path": str(path)}
            findings.append(f)
            posters_order.append({"rel": str(path.relative_to(paths.root)), "parsed": False})
            continue
        posters_order.append({"rel": poster.rel, "parsed": True})
        pf, stats = check_poster(poster, claims, banned_hard, banned_soft, paths.root)
        for f in pf:
            f["poster"] = pid
            f["path"] = str(path)
        posters[pid] = {"rel": poster.rel, "path": str(path), "findings": pf, "stats": stats}
        findings.extend(pf)

    claims_audit: list[dict] = []
    if claims.status == "ok":
        index = build_file_index(paths.source_roots)
        claims_audit = check_claims_against_sources(claims, index)

    n_b = sum(1 for x in findings if x["code"].startswith("Б"))
    n_z = sum(1 for x in findings if x["code"] == "З")
    n_i = sum(1 for x in findings if x["code"] == "И")
    summary = {
        "blockers": n_b,
        "warnings": n_z,
        "infos": n_i,
        "numbers_checked": sum(p["stats"].get("numbers_checked", 0) for p in posters.values()),
        "numbers_exact": sum(p["stats"].get("numbers_exact", 0) for p in posters.values()),
        "numbers_within": sum(p["stats"].get("numbers_within", 0) for p in posters.values()),
        "numbers_unknown": sum(p["stats"].get("numbers_unknown", 0) for p in posters.values()),
        "numbers_verified": sum(p["stats"].get("numbers_exact", 0) for p in posters.values()),
        "claims_count": len(claims.claims),
        "claims_mismatch": sum(1 for c in claims_audit if c["status"] == "mismatch"),
        "banned_phrases": len(banned_hard),
        "banned_hard": len(banned_hard),
        "banned_soft": len(banned_soft),
        "banned_note": banned_note,
    }
    result = {
        "generated": generated,
        "version": VERSION,
        "inputs": {
            "claims": claims.status,
            "claims_error": claims.error,
            "banned": banned_note,
            "banned_note": banned_note,
            "posters_found": len(poster_files),
        },
        "summary": summary,
        "posters": posters,
        "posters_order": posters_order,
        "missing_posters": missing,
        "findings": findings,
        "claims_audit": claims_audit,
    }

    md = render_md(result)
    if write:
        paths.qa.mkdir(parents=True, exist_ok=True)
        paths.out_md.write_text(md, encoding="utf-8")
        paths.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def default_paths() -> Paths:
    qa = Path(__file__).resolve().parent
    root = qa.parent
    facts = root / "01_ФАКТЫ"
    return Paths(
        root=root,
        claims=facts / "claims.json",
        banned=facts / "BANNED.md",
        posters=root / "02_МАКЕТЫ" / "posters",
        qa=qa,
        out_md=qa / "QA_АВТОПРОВЕРКА.md",
        out_json=qa / "QA_АВТОПРОВЕРКА.json",
        source_roots=[root, root.parent],
    )


def print_console(result: dict) -> None:
    s = result["summary"]
    print(f"QA-линтер v{VERSION}: {result['generated']}")
    print(f"  claims.json: {result['inputs']['claims']} ({result['inputs']['claims_error'] or 'ok'})")
    print(f"  BANNED.md: {result['inputs']['banned']}")
    print(f"  постеров: {result['inputs']['posters_found']} из 10; нет: {', '.join(sorted(result['missing_posters'])) or '—'}")
    print(f"  цифры: проверено {s['numbers_checked']}, точно {s['numbers_exact']}, "
          f"в диапазоне {s['numbers_within']}, не подтверждено {s['numbers_unknown']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']} | claims-расхождений: {s['claims_mismatch']}")
    for b in result["findings"]:
        if b["code"].startswith("Б"):
            print(f"   [{b['code']}] {b['poster']}: {b['msg']}")


# ================================================================ самопроверка
def selftest() -> int:
    print("== SELFTEST check_claims.py ==")
    tmp = Path(tempfile.mkdtemp(prefix="qa_selftest_"))
    (tmp / "facts").mkdir()
    (tmp / "posters").mkdir()
    (tmp / "qa").mkdir()
    (tmp / "src").mkdir()

    (tmp / "src" / "test_source.md").write_text(
        "# Тестовый источник\n"
        "Произведено и поставлено более 8000 станций с августа 2023 года.\n"
        "«Капюшон» К-8М: дальность подавления 50–200 м, питание 12/24 В.\n"
        "«Сигнал-М2»: обнаружение 300–10 000 МГц; 1000–5000 м прямой видимости.\n"
        "Гарантия 12 месяцев.\n",
        encoding="utf-8",
    )
    claims = {
        "claims": [
            {
                "id": "C001", "topic": "company",
                "allowed_text": "Произведено и поставлено более 8000 станций с августа 2023 года",
                "numbers": ["8000", "2023"], "source": "src/test_source.md",
                "risk": "low", "poster_ids": ["P01"],
            },
            {
                "id": "C002", "topic": "product",
                "allowed_text": "«Капюшон» К-8М: дальность подавления 50–200 м, питание 12/24 В",
                "numbers": ["50–200 м", "12/24 В"], "source": "src/test_source.md",
                "risk": "med", "poster_ids": ["P01", "P07"],
            },
            {
                "id": "C003", "topic": "product",
                "allowed_text": "«Сигнал-М2»: обнаружение 300–10 000 МГц; 1000–5000 м прямой видимости",
                "numbers": ["300–10000 МГц", "1000–5000 м"], "source": "src/test_source.md",
                "risk": "med", "poster_ids": ["P03"],
            },
            {
                "id": "C004", "topic": "warranty",
                "allowed_text": "Гарантия 12 месяцев", "numbers": ["12 месяцев"],
                "source": "src/test_source.md", "risk": "low", "poster_ids": ["P10"],
            },
        ]
    }
    (tmp / "facts" / "claims.json").write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    (tmp / "facts" / "BANNED.md").write_text(
        "# Запрещено\n\n- «100% защита», «дрон не пролетит»\n- запрещено: «лучший в мире»\n",
        encoding="utf-8",
    )

    good_footer = (
        '<footer>@vokope_ru · +7 999 136-71-42 · Доставка по РФ · Самовывоз в Москве · '
        'В ОКОПЕ · НПО «Киловатт» · производитель · P01 · 06.11.2026</footer>'
    )
    (tmp / "posters" / "P01_dva_gorizonta.html").write_text(
        "<html lang=ru><head><style>body{font-size:15px}</style></head><body>"
        "<h1>ДВА ГОРИЗОНТА</h1>"
        "<p>Более 8000 станций с августа 2023 года</p>"
        "<p>Капюшон К-8М: 50–200 м, питание 12/24 В</p>"
        "<p>99999 МГц — этой цифры нет в факт-базе</p>"
        "<p>до 7 км по дальности</p>"
        "<p>до 2 км — внутри подтверждённого диапазона, но сверить модель руками</p>"
        "<p>100% защита и дрон не пролетит</p>"
        "<p>Цена: 350 000 ₽</p>"
        "</body></html>",
        encoding="utf-8",
    )
    # P05 без дисклеймера + запрещённый CSS + мелкий кегль
    (tmp / "posters" / "P05_b2b_pochemu_sejchas.html").write_text(
        "<html lang=ru><head><style>"
        ".x{background:linear-gradient(#fff,#000)} .y{font-size:9px} .z{box-shadow:0 2px 4px #000}"
        "@font-face{font-family:Sofia Sans Cond;src:url(missing.woff2)}"
        "</style></head><body><h1>ПОЧЕМУ СЕЙЧАС</h1>"
        + good_footer +
        "</body></html>",
        encoding="utf-8",
    )
    (tmp / "posters" / "P10_dokumenty_i_servis.html").write_text(
        "<html lang=ru><head><style>body{font-size:15px}</style></head><body>"
        "<h1>ДОКУМЕНТЫ</h1><p>Гарантия 12 месяцев</p>"
        "<p>Технические характеристики — по паспорту изделия; значения дальности зависят от условий эксплуатации</p>"
        + good_footer +
        "</body></html>",
        encoding="utf-8",
    )

    paths = Paths(
        root=tmp,
        claims=tmp / "facts" / "claims.json",
        banned=tmp / "facts" / "BANNED.md",
        posters=tmp / "posters",
        qa=tmp / "qa",
        out_md=tmp / "qa" / "QA_АВТОПРОВЕРКА.md",
        out_json=tmp / "qa" / "QA_АВТОПРОВЕРКА.json",
        source_roots=[tmp],
    )
    res = run(paths, write=True)
    print_console(res)

    checks: list[tuple[str, bool, str]] = []
    p01 = [f for f in res["findings"] if f["poster"] == "P01"]
    p05 = [f for f in res["findings"] if f["poster"] == "P05"]
    b1 = [f["msg"] for f in p01 if f["code"] == "Б1"]
    z = [f["msg"] for f in p01 if f["code"] == "З"]
    checks.append(("P01: «99999 МГц» вне факт-базы -> Б1", any("99999" in m for m in b1), "; ".join(b1)))
    checks.append(("P01: «7 км» вне факт-базы -> Б1", any("7 " in m and "км" in m for m in b1), "; ".join(b1)))
    checks.append(("P01: «2 км» внутри диапазона -> З (ручная сверка)", any("2 " in m and "внутри" in m for m in z), "; ".join(z)))
    checks.append(("P01: подтверждённые 50–200 м / 12/24 В не дали Б1", not any("50" in m or "200" in m for m in b1), "; ".join(b1)))
    checks.append(("P01: запрещённые фразы -> Б2", any(f["code"] == "Б2" for f in p01), ""))
    checks.append(("P01: цена -> Б5", any(f["code"] == "Б5" for f in p01), ""))
    checks.append(("P05: нет дисклеймера -> Б4", any(f["code"] == "Б4" and "дисклеймер" in f["msg"] for f in p05), ""))
    checks.append(("P05: градиент/тень/кегль/шрифт -> Б3", sum(1 for f in p05 if f["code"] == "Б3") >= 3, f"{sum(1 for f in p05 if f['code'] == 'Б3')} Б3"))
    checks.append(("P10: дисклеймер найден -> нет Б4 по дисклеймеру", not any(f["poster"] == "P10" and f["code"] == "Б4" and "дисклеймер" in f["msg"] for f in res["findings"]), ""))
    checks.append(("claims audit: 4 утверждения проверены", len(res["claims_audit"]) == 4, str(len(res["claims_audit"]))))
    checks.append(("claims audit: расхождений 0", res["summary"]["claims_mismatch"] == 0, str([c for c in res["claims_audit"] if c["status"] == "mismatch"])))

    ok = True
    for name, cond, extra in checks:
        print(("  PASS " if cond else "  FAIL ") + name + (f" [{extra}]" if not cond else ""))
        ok = ok and cond
    print("== SELFTEST:", "OK" if ok else "FAILED", "==")
    print(f"  отчёт: {paths.out_md}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="QA-линтер пакета «ДВА ГОРИЗОНТА»")
    ap.add_argument("--selftest", action="store_true", help="прогнать на синтетических фикстурах")
    ap.add_argument("--no-write", action="store_true", help="не писать файлы отчёта")
    ap.add_argument("--posters", default="", help="фильтр постеров, например P05")
    ap.add_argument("--claims", default="", help="путь к claims.json")
    ap.add_argument("--banned", default="", help="путь к BANNED.md")
    ap.add_argument("--out-md", default="", help="путь к QA_АВТОПРОВЕРКА.md")
    ap.add_argument("--out-json", default="", help="путь к QA_АВТОПРОВЕРКА.json")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    paths = default_paths()
    if args.claims:
        paths.claims = Path(args.claims)
    if args.banned:
        paths.banned = Path(args.banned)
    if args.out_md:
        paths.out_md = Path(args.out_md)
    if args.out_json:
        paths.out_json = Path(args.out_json)
    paths.poster_filter = args.posters

    res = run(paths, write=not args.no_write)
    print_console(res)
    if args.no_write:
        return 0
    print(f"  отчёт: {paths.out_md}")
    print(f"  json:  {paths.out_json}")
    s = res["summary"]
    if res["inputs"]["claims"] not in ("ok",):
        return 3
    return 1 if s["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
