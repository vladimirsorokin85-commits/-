# -*- coding: utf-8 -*-
"""Прайс-ролики «РЭБ по ценам производителя» — данные с карточек заказчика.

Только розничные цены (колонка «НАЛИЧИЕ» на карточках). Цены с НДС 22 %
в кадр не идут — о них говорится голосом, без цифр.
"""
import os
import sys

sys.path.insert(0, "/home/user/-/video_studio/k8m_kupol")
import k8m as K  # noqa: E402
from k8m import (BG0, BG1, COND, DIM, H, INK, LIME, MONT, PLATE, TEK, TXT, W,  # noqa: E402
                 ac, c01, chip, chips_row, eo, grid, kicker, plate, slam, stage,
                 tick_marks)

OSW = "Oswald-VF.ttf"   # заголовки: у Sofia Sans/Tektur кириллическая «Д» без ножек

BASE = os.path.dirname(os.path.abspath(__file__))
FF = "/home/user/.local/bin/ffmpeg"

TITLE_HUD = "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ"
FOOT = "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ · РОЗНИЦА"
CONTACT = "@VES_nn  ·  Москва и Липецк"

# три «ходовые» позиции для заставки категории
HILITE = {
    "auto": [("К-8М", "320 000"), ("К-12М", "699 000"), ("К-15М", "900 000")],
    "port": [("ТП 4-28А", "120 000"), ("ТП 7-100", "308 000"), ("ТП 8-100", "389 000")],
    "stat": [("Штора-М К-8/600", "840 000"), ("Штора К-12/700", "1 620 000"), ("Ребус-4", "5 600 000")],
    "moto": [("ФПВ-7 мото", "220 000"), ("ФПВ-5 мото", "354 500")],
}

# (модель, розничная цена) — ровно как на карточках, колонка «НАЛИЧИЕ»
CATS = {
    "auto": ("АВТОМОБИЛЬНЫЕ", [
        ("ФПВ-3", "205 200"),
        ("ФПВ-8М", "513 000"),
        ("ФПВ-12", "746 200"),
        ("К-8М", "320 000"),
        ("К-12М", "699 000"),
        ("К-12М Багажный бокс (Автобокс)", "770 000"),
        ("К-15М", "900 000"),
        ("К-15М ВИП", "1 000 000"),
        ("Изделие 135 (багажный бокс, премиум)", "1 180 000"),
        ("Поле-31", "700 000"),
    ]),
    "port": ("ПЕРЕНОСНЫЕ", [
        ("ТП 4-28А", "120 000"),
        ("ТП 4-28Б", "120 000"),
        ("ТП 4-50А", "180 000"),
        ("ТП 4-50Б", "180 000"),
        ("ТП 7-100", "308 000"),
        ("ТП 8-100", "389 000"),
        ("ТП 10-100", "336 900"),
    ]),
    "stat": ("СТАЦИОНАРНЫЕ", [
        ("Штора-М К-8/600", "840 000"),
        ("Штора К-12/700", "1 620 000"),
        ("Ребус-4", "5 600 000"),
        ("Ребус-2", "3 358 100"),
    ]),
    "moto": ("МОТО", [
        ("ФПВ-7 мото (КОМПАКТ)", "220 000"),
        ("ФПВ-5 мото", "354 500"),
    ]),
}


def fit(s, fn, size, maxw, minsize=24):
    """Подбирает кегль так, чтобы строка влезла в maxw."""
    while size > minsize and K.F(fn, size).getlength(s) > maxw:
        size -= 2
    return size


def wrap2(s, fn, size, maxw):
    """Делит длинное название на две строки по словам."""
    words = s.split()
    best, bl, br = None, 1e9, ""
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        d = abs(K.F(fn, size).getlength(a) - K.F(fn, size).getlength(b))
        if d < bl and K.F(fn, size).getlength(a) <= maxw:
            best, bl, br = (a, b), d, ""
    return best


def head(cv, d, l, cat, sub="РОЗНИЧНЫЕ ЦЕНЫ · С НДС — ПО ЗАПРОСУ", t0=0.02):
    kicker(d, "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ", 158, c01((l - t0) / .22), LIME, 24)
    slam(cv, cat, OSW, 62, 540, 170, ac(TXT, 255), c01((l - t0 - .04) / .24), "ma", maxw=980)
    if sub:
        slam(cv, sub, TEK, 19, 540, 284, ac(DIM, 235), c01((l - t0 - .12) / .26), "ma", maxw=960)


def table(cv, d, l, rows, t_start=0.30, per=0.14, y0=330, y1=1560):
    n = len(rows)
    h = min(174, int((y1 - y0) / max(n, 1)))
    block = n * h
    top = y0 + max(0, min(180, int(((y1 - y0) - block) / 2)))
    # шапка таблицы
    p = c01((l - t_start * .5) / .2)
    d.text((76, top - 40), "МОДЕЛЬ", font=K.F(TEK, 20), fill=ac(DIM, int(220 * p)))
    d.text((1004, top - 40), "ЦЕНА, ₽", font=K.F(TEK, 20), fill=ac(DIM, int(220 * p)), anchor="ra")
    d.rectangle([76, top - 8, 1004, top - 6], fill=ac(LIME, int(90 * p)))

    pf = 52 if n <= 7 else 46
    for i, (model, price) in enumerate(rows):
        q = c01((l - t_start - i * per) / .26)
        if q <= 0:
            continue
        y = top + i * h
        # подложка строки-«полосы»
        if i % 2 == 0:
            lay_a = int(16 * q)
            d.rectangle([68, y + 2, 1012, y + h - 2], fill=(255, 255, 255, lay_a))
        d.rectangle([76, y + h - 1, 1004, y + h], fill=ac(LIME, int(46 * q)))
        # маркер
        d.rectangle([76, y + int(h * .30), 82, y + int(h * .70)], fill=ac(LIME, int(240 * q)))
        # модель
        ms = fit(model, OSW, 42, 590)
        if K.F(OSW, ms).getlength(model) > 590 and ms <= 30:
            two = wrap2(model, OSW, 30, 580)
            if two:
                slam(cv, two[0], OSW, 30, 104, y + int(h * .16), ac(TXT, 250), q, "lt", maxw=590)
                slam(cv, two[1], OSW, 30, 104, y + int(h * .16) + 38, ac(TXT, 250), q, "lt", maxw=590)
            else:
                slam(cv, model, OSW, 30, 104, y + int(h * .26), ac(TXT, 250), q, "lt", maxw=590)
        else:
            slam(cv, model, OSW, ms, 104, y + int(h * .5) - int(ms * .66), ac(TXT, 252), q, "lt", maxw=590)
        # цена
        slam(cv, price, OSW, pf, 1004, y + int(h * .5) - int(pf * .68), ac(TXT, 255), q, "rt", maxw=380)
    return top, h


def foot(cv, d, l, t0=0.0, note="Цены розничные · не оферта"):
    p = c01((l - t0) / .3)
    if p <= 0:
        return
    d.rectangle([76, 1590, 1004, 1592], fill=ac(LIME, int(80 * p)))
    d.text((76, 1606), "Отгрузка: Москва и Липецк · Доставка по России", font=K.F(TEK, 22),
           fill=ac(DIM, int(235 * p)))
    d.text((76, 1644), "В наличии · Пишите в Telegram", font=K.F(TEK, 22), fill=ac(DIM, int(235 * p)))
    d.text((76, 1698), "@VES_nn", font=K.F(OSW, 50), fill=ac(LIME, int(250 * p)))
    d.text((1004, 1712), note, font=K.F(TEK, 18), fill=ac(DIM, int(200 * p)), anchor="ra")


def tiles4(cv, d, l, items, y=560, bw=452, bh=250, t_start=0.0, per=0.10):
    for i, (name, cnt) in enumerate(items):
        q = c01((l - t_start - i * per) / .26)
        if q <= 0:
            continue
        x = 76 + (i % 2) * (bw + 24)
        yy = y + (i // 2) * (bh + 24)
        d.rectangle([x, yy, x + bw, yy + bh], fill=ac(BG1, int(238 * q)), outline=ac(LIME, int(140 * q)))
        d.rectangle([x, yy, x + bw, yy + 5], fill=ac(LIME, int(240 * q)))
        d.text((x + 28, yy + 34), name, font=K.F(OSW, 44), fill=ac(TXT, 252 * q))
        d.text((x + 28, yy + 100), cnt, font=K.F(TEK, 34), fill=ac(LIME, 250 * q))
