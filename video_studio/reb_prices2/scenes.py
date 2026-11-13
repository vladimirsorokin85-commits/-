# -*- coding: utf-8 -*-
"""Сцены прайс-роликов. Версия 2: строгая сетка, без фото, без наложений."""
from PIL import Image, ImageDraw

import layout as L
from layout import (BOT, BG1, DIM, H, LIME, MARGIN, OSW, TEK, TOP, TXT, W,
                    ac, badge, c01, eo, grid, icon, reg, rule, stage, text)

KICKER = "КАТЕГОРИЯ · RETAIL"

FEATS = {
    "auto": ["Для машин и пикапов", "Крепление на крышу и борт"],
    "port": ["Носится за спиной", "Ставится на позиции и в окопе"],
    "stat": ["Для объекта и периметра", "Стационарная установка"],
    "moto": ["Для мото и лёгкой техники", "Штатное крепление на борт"],
}

DATA = {
    "auto": ("АВТОМОБИЛЬНЫЕ", "van", [
        ("ФПВ-3", "205 200"), ("ФПВ-8М", "513 000"), ("ФПВ-12", "746 200"),
        ("К-8М", "320 000"), ("К-12М", "699 000"),
        ("К-12М Автобокс", "770 000"),
        ("К-15М", "900 000"), ("К-15М ВИП", "1 000 000"),
        ("Изделие 135 · автобокс", "1 180 000"),
        ("Поле-31", "700 000"),
    ]),
    "port": ("ПЕРЕНОСНЫЕ", "pack", [
        ("ТП 4-28А", "120 000"), ("ТП 4-28Б", "120 000"),
        ("ТП 4-50А", "180 000"), ("ТП 4-50Б", "180 000"),
        ("ТП 7-100", "308 000"), ("ТП 8-100", "389 000"),
        ("ТП 10-100", "336 900"),
    ]),
    "stat": ("СТАЦИОНАРНЫЕ", "tower", [
        ("Штора-М К-8/600", "840 000"), ("Штора К-12/700", "1 620 000"),
        ("Ребус-4", "5 600 000"), ("Ребус-2", "3 358 100"),
    ]),
    "moto": ("МОТО", "moto", [
        ("ФПВ-7 мото (КОМПАКТ)", "220 000"),
        ("ФПВ-5 мото", "354 500"),
    ]),
}

GROUPS = [("auto", "АВТОМОБИЛЬНЫЕ", "van", 10),
          ("port", "ПЕРЕНОСНЫЕ", "pack", 7),
          ("stat", "СТАЦИОНАРНЫЕ", "tower", 4),
          ("moto", "МОТО", "moto", 2)]


def _head(cv, d, l, title, ico, sub="РОЗНИЧНЫЕ ЦЕНЫ · ЗАВОДСКИЕ", t0=.04):
    """Шапка категории. Всё ставится по фактической высоте строки."""
    y = TOP + 10
    text(d, KICKER, TEK, 21, MARGIN, y, LIME, name="kicker",
         alpha=int(255 * c01((l - t0) / .2)))
    icon(d, ico, W - MARGIN - 88, y - 14, 88, LIME, int(240 * c01((l - t0 - .05) / .3)), "ico-head")
    y += 30
    y += text(d, title, OSW, 68, MARGIN, y, TXT, maxw=W - 2 * MARGIN - 100, name="title",
              alpha=int(255 * c01((l - t0 - .06) / .24))) + 18
    y += text(d, sub, TEK, 19, MARGIN, y, DIM, name="sub",
              alpha=int(240 * c01((l - t0 - .14) / .24))) + 20
    rule(d, y, alpha=int(70 * c01((l - t0 - .2) / .3)))
    return y + 24


def _table(cv, d, l, rows, y0, y1, t_start=.3, per=.10, big=False):
    """Таблица: шапка колонок + строки. Сама считает высоту строки."""
    n = len(rows)
    cap = 210 if n <= 2 else (176 if n <= 4 else (150 if n <= 7 else 126))
    h = min(cap, int((y1 - y0 - 60) / n))
    top = y0 + 42

    text(d, "МОДЕЛЬ", TEK, 19, MARGIN, top - 34, DIM, name="th1",
         alpha=int(225 * c01((l - t_start * .6) / .18)))
    text(d, "ЦЕНА, ₽", TEK, 19, W - MARGIN, top - 34, DIM, anchor="rt", name="th2",
         alpha=int(225 * c01((l - t_start * .6) / .18)))
    rule(d, top - 6, alpha=int(80 * c01((l - t_start * .6) / .18)))

    name_sz = 64 if big else (42 if n <= 7 else 38)
    price_sz = 86 if big else (58 if n <= 7 else 52)

    for i, (model, price) in enumerate(rows):
        q = c01((l - t_start - i * per) / .24)
        if q <= 0:
            continue
        y = top + i * h
        if i % 2 == 0:
            d.rectangle([MARGIN - 8, y + 3, W - MARGIN + 8, y + h - 3], fill=(255, 255, 255, int(14 * q)))
        d.rectangle([MARGIN, y + int(h * .30), MARGIN + 5, y + int(h * .70)], fill=ac(LIME, int(240 * q)))
        rule(d, y + h - 1, alpha=int(38 * q), width=1, name="rowline%d" % i)

        sz = name_sz
        while sz > 20 and L.F(OSW, sz).getlength(model) > 600:
            sz -= 3
        text(d, model, OSW, sz, MARGIN + 26, y + h / 2 - (sz * .62), TXT,
             name="m%d" % i, alpha=int(252 * q))
        text(d, price, OSW, price_sz, W - MARGIN, y + h / 2 - (price_sz * .62), TXT,
             anchor="rt", name="p%d" % i, alpha=int(255 * q))


def _foot(d, l, t0=.55):
    p = c01((l - t0) / .3)
    if p <= 0:
        return
    rule(d, 1588, alpha=int(80 * p))
    text(d, "Москва и Липецк · розничные цены", TEK, 21, MARGIN, 1604, DIM,
         name="f1", alpha=int(235 * p))
    text(d, "Наличие и НДС — уточняйте в Telegram", TEK, 21, MARGIN, 1642, DIM, name="f2",
         alpha=int(235 * p))
    text(d, "@VES_nn", OSW, 52, MARGIN, 1686, LIME, name="f3", alpha=int(250 * p))
    text(d, "Цены розничные · не оферта", TEK, 17, W - MARGIN, 1698, DIM,
         anchor="rt", name="f4", alpha=int(195 * p))


def _outro(cv, d, l, line2):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((13, 17, 11), 255)))
    grid(d, 7)
    y = 596
    y += text(d, "МАГАЗИН «В ОКОПЕ»", TEK, 22, W / 2, y, LIME, anchor="mt", name="o-kick",
              alpha=int(250 * c01((l - .04) / .22))) + 30
    y += text(d, "ЦЕНЫ ЗАВОДСКИЕ", OSW, 92, W / 2, y, TXT, anchor="mt", maxw=980, name="o-t1",
              alpha=int(255 * c01((l - .10) / .26))) + 34
    y += text(d, line2, TEK, 23, W / 2, y, LIME, anchor="mt", maxw=900, name="o-t2",
              alpha=int(245 * c01((l - .18) / .26))) + 64

    if l > .32:
        p = c01((l - .32) / .28)
        d.rectangle([MARGIN + 10, y, W - MARGIN - 10, y + 5], fill=ac(LIME, int(230 * p)))
        y += 46
        y += text(d, "РОЗНИЧНЫЕ ЦЕНЫ", OSW, 44, W / 2, y, LIME, anchor="mt", name="o-t3",
                  alpha=int(250 * p)) + 22
        y += text(d, "С НДС — ПО ЗАПРОСУ", TEK, 21, W / 2, y, DIM, anchor="mt", name="o-t4",
                  alpha=int(235 * p)) + 62

    if l > .58:
        p = c01((l - .58) / .28)
        y += text(d, "Москва и Липецк", TEK, 22, W / 2, y, TXT, anchor="mt",
                  name="o-t5", alpha=int(240 * p)) + 16
        y += text(d, "Наличие и форма оплаты — в переписке", TEK, 19, W / 2, y, DIM, anchor="mt",
                  name="o-t6", alpha=int(230 * p)) + 54

    if l > .84:
        p = c01((l - .84) / .28)
        y += text(d, "@VES_nn", OSW, 90, W / 2, y, LIME, anchor="mt", maxw=760, name="o-t7",
                  alpha=int(255 * p)) + 26
        y += text(d, "Telegram · подберём под задачу", TEK, 20, W / 2, y, TXT, anchor="mt",
                  maxw=900, name="o-t8", alpha=int(230 * p)) + 52

    if l > 1.10:
        p = c01((l - 1.10) / .4)
        y += text(d, "Применение — в установленном порядке.", TEK, 15, W / 2, y, DIM,
                  anchor="mt", maxw=900, name="o-j1", alpha=int(175 * p)) + 8
        text(d, "Цены розничные, не являются публичной офертой.", TEK, 15, W / 2, y, DIM,
             anchor="mt", maxw=900, name="o-j2", alpha=int(175 * p))


# ─────────────────────────── общий ролик
def g_hook(cv, d, t, l):
    stage(cv, .3, t)
    grid(d, 9)
    y = TOP + 12
    y += text(d, "СПЕЦДОГОВОР С ПРОИЗВОДСТВОМ", TEK, 21, MARGIN, y, LIME, name="g-kick",
              alpha=int(250 * c01((l - .04) / .2))) + 16
    y += text(d, "ЦЕНЫ", OSW, 118, MARGIN, y - 16, TXT, name="g-t1",
              alpha=int(255 * c01((l - .08) / .24))) + 2
    y += text(d, "ПРОИЗВОДИТЕЛЯ", OSW, 96, MARGIN, y - 18, LIME, maxw=W - 2 * MARGIN, name="g-t2",
              alpha=int(255 * c01((l - .16) / .24))) + 10
    y += text(d, "Без наценки посредников", OSW, 44, MARGIN, y, TXT, maxw=W - 2 * MARGIN, name="g-t3",
              alpha=int(250 * c01((l - .30) / .24))) + 16
    y += text(d, "Розничные цены · с НДС — по запросу", TEK, 21, MARGIN, y, DIM,
              maxw=W - 2 * MARGIN, name="g-t4", alpha=int(235 * c01((l - .42) / .26))) + 34
    rule(d, y, alpha=int(80 * c01((l - .5) / .3)))
    y += 36

    facts = [("23", "МОДЕЛИ"), ("4", "ГРУППЫ"), ("2", "ФОРМЫ НДС")]
    bw = (W - 2 * MARGIN - 2 * 14) // 3
    for i, (v, s2) in enumerate(facts):
        q = c01((l - .56 - i * .08) / .26)
        if q <= 0:
            continue
        x = MARGIN + i * (bw + 14)
        d.rectangle([x, y, x + bw, y + 206], fill=ac(BG1, int(232 * q)), outline=ac(LIME, int(120 * q)))
        text(d, v, OSW, 76, x + bw / 2, y + 22, LIME, anchor="mt", name="gf%d" % i, alpha=int(252 * q))
        text(d, s2, TEK, 17, x + bw / 2, y + 152, DIM, anchor="mt", name="gl%d" % i, alpha=int(232 * q))

    # что даёт спецдоговор — три строки, чтобы кадр держал внимание
    yy = y + 286
    for i, t3 in enumerate(["Цена как у завода, без посредника",
                            "Счёт и документы — на любую форму",
                            "Помогаем подобрать под задачу"]):
        q = c01((l - .72 - i * .08) / .28)
        if q <= 0:
            continue
        d.rectangle([MARGIN, yy + 16, MARGIN + 5, yy + 72], fill=ac(LIME, int(228 * q)))
        yy += text(d, t3, OSW, 33, MARGIN + 26, yy + 20, TXT, maxw=W - 2 * MARGIN - 40,
                   name="g-f%d" % i, alpha=int(248 * q)) + 42

    icon(d, "van", W - MARGIN - 190, yy + 40, 170, LIME, int(120 * c01((l - .9) / .4)), "g-ico")


def g_cats(cv, d, t, l):
    stage(cv, .18, t)
    grid(d, 7)
    y = TOP + 12
    text(d, "ЧЕТЫРЕ ГРУППЫ · 23 МОДЕЛИ", TEK, 21, MARGIN, y, LIME, name="gc-kick",
         alpha=int(250 * c01((l - .02) / .2)))
    y += 42
    text(d, "ВСЁ В НАЛИЧИИ", OSW, 66, MARGIN, y, TXT, maxw=W - 2 * MARGIN, name="gc-t1",
         alpha=int(255 * c01((l - .06) / .24)))
    y += 108

    bw = (W - 2 * MARGIN - 22) // 2
    bh = 292
    for i, (tag, name, ico, cnt) in enumerate(GROUPS):
        q = c01((l - .18 - i * .10) / .28)
        if q <= 0:
            continue
        x = MARGIN + (i % 2) * (bw + 22)
        yy = y + (i // 2) * (bh + 22)
        d.rectangle([x, yy, x + bw, yy + bh], fill=ac(BG1, int(234 * q)), outline=ac(LIME, int(120 * q)))
        d.rectangle([x, yy, x + bw, yy + 4], fill=ac(LIME, int(225 * q)))
        icon(d, ico, x + 26, yy + 40, 96, LIME, int(240 * q), "gci%d" % i)
        hn = text(d, name, OSW, 40, x + 26, yy + 168, TXT, maxw=bw - 52, name="gcn%d" % i,
                  alpha=int(252 * q))
        text(d, "%d моделей" % cnt, TEK, 19, x + 26, yy + 168 + hn + 10, LIME, name="gcc%d" % i,
             alpha=int(245 * q))

    y += 2 * bh + 22 + 46
    if l > .95:
        p = c01((l - .95) / .28)
        d.rectangle([MARGIN, y, W - MARGIN, y + 236], fill=ac(BG1, int(236 * p)),
                    outline=ac(LIME, int(170 * p)))
        d.rectangle([MARGIN, y, W - MARGIN, y + 5], fill=ac(LIME, int(235 * p)))
        h2 = text(d, "С НДС И БЕЗ НДС", OSW, 54, W / 2, y + 30, LIME, anchor="mt",
                  maxw=W - 2 * MARGIN - 40, name="gc-t2", alpha=int(255 * p))
        y2 = y + 30 + h2 + 26
        y2 += text(d, "Как удобнее покупателю", TEK, 20, W / 2, y2, TXT, anchor="mt",
                   name="gc-t3", alpha=int(240 * p)) + 14
        text(d, "Цену с НДС считаем по запросу", TEK, 19, W / 2, y2, DIM, anchor="mt",
             name="gc-t4", alpha=int(230 * p))
        y += 236 + 30

    if l > 1.22:
        p = c01((l - 1.22) / .3)
        text(d, "РОЗНИЦА · ОПТ — СПЕЦДОГОВОР С ПРОИЗВОДСТВОМ", TEK, 19, W / 2, y + 24, DIM,
             anchor="mt", maxw=W - 2 * MARGIN, name="gc-note", alpha=int(220 * p))
        rule(d, y + 78, alpha=int(70 * p))


# ─────────────────────────── категорийный ролик
def c_hook(cv, d, t, l, cat):
    name, ico, rows = DATA[cat]
    vals = sorted(int(p.replace(" ", "")) for _, p in rows)
    lo, hi = vals[0], vals[-1]
    stage(cv, .3, t)
    grid(d, 9)
    y = _head(cv, d, l, name, ico, sub="РОЗНИЧНЫЕ ЦЕНЫ · ЗАВОДСКИЕ")

    y += text(d, "СПЕЦДОГОВОР С ПРОИЗВОДСТВОМ", OSW, 44, MARGIN, y + 2, TXT,
              maxw=W - 2 * MARGIN, name="c-l1", alpha=int(255 * c01((l - .30) / .26))) + 14
    y += text(d, "Без наценки посредников", OSW, 38, MARGIN, y, LIME, maxw=W - 2 * MARGIN,
              name="c-l2", alpha=int(250 * c01((l - .42) / .26))) + 12
    y += text(d, "Ниже, чем у перекупов", TEK, 21, MARGIN, y, DIM, maxw=W - 2 * MARGIN,
              name="c-l3", alpha=int(235 * c01((l - .52) / .26))) + 44

    # витрина диапазона
    if l > .58:
        p = c01((l - .58) / .30)
        bh = 300
        d.rectangle([MARGIN, y, W - MARGIN, y + bh], fill=ac(BG1, int(236 * p)),
                    outline=ac(LIME, int(165 * p)))
        d.rectangle([MARGIN, y, W - MARGIN, y + 5], fill=ac(LIME, int(240 * p)))
        text(d, "ВСЕ %d ПОЗИЦИЙ · ОТ" % len(rows), TEK, 19, MARGIN + 28, y + 26, DIM,
             name="c-p1", alpha=int(235 * p))
        yy = y + 58
        yy += text(d, "%s ₽" % _fmt(lo), OSW, 86, MARGIN + 24, yy, LIME, maxw=520,
                   name="c-p2", alpha=int(255 * p)) + 8
        yy += text(d, "до %s ₽" % _fmt(hi), OSW, 52, MARGIN + 24, yy, TXT, maxw=520,
                   name="c-p3", alpha=int(250 * p))
        text(d, "розница", TEK, 17, W - MARGIN - 28, y + 28, DIM, anchor="rt",
             name="c-p4", alpha=int(220 * p))
        text(d, "НДС — по запросу", TEK, 17, W - MARGIN - 28, y + bh - 44, DIM,
             anchor="rt", name="c-p5", alpha=int(220 * p))
        y += bh + 34

    if l > .80:
        p = c01((l - .80) / .3)
        badge(d, "РОЗНИЦА · НДС ПО ЗАПРОСУ", MARGIN, y, LIME, int(235 * p), 24)
        y += 76

    # чем хороша категория — две строки, чтобы кадр не пустовал
    feats = FEATS[cat]
    for i, f in enumerate(feats):
        q = c01((l - .92 - i * .08) / .28)
        if q <= 0:
            continue
        d.rectangle([MARGIN, y + 24, MARGIN + 5, y + 92], fill=ac(LIME, int(235 * q)))
        text(d, f, OSW, 34, MARGIN + 26, y + 30, TXT, maxw=W - 2 * MARGIN - 30,
             name="c-f%d" % i, alpha=int(250 * q))
        y += 96

    if l > 1.1:
        p = c01((l - 1.1) / .32)
        icon(d, ico, MARGIN + 24, y + 20, 110, LIME, int(120 * p), "c-ico2")


def _fmt(v):
    return "{:,}".format(v).replace(",", " ")


def c_table(cv, d, t, l, cat):
    name, ico, rows = DATA[cat]
    stage(cv, .12, t)
    grid(d, 6)
    y = _head(cv, d, l, name, ico, t0=.02)
    big = len(rows) <= 2
    _table(cv, d, l, rows, y + 8, 1540, t_start=.16, per=.12 if len(rows) > 4 else .34, big=big)
    if len(rows) <= 4 and l > .8:
        p = c01((l - .8) / .3)
        text(d, "Только розничные цены · наличие уточняйте", TEK, 19, W / 2, 1520, DIM,
             anchor="mt", maxw=900, name="c-note", alpha=int(230 * p))
    _foot(d, l, t0=.5)


def c_outro(cv, d, t, l, cat):
    _outro(cv, d, l, DATA[cat][0])


def g_outro(cv, d, t, l):
    _outro(cv, d, l, "23 МОДЕЛИ · 4 ГРУППЫ")


def scenes(tag):
    if tag == "g":
        return {"hook": g_hook, "cats": g_cats, "outro": g_outro}
    return {
        "hook": lambda cv, d, t, l: c_hook(cv, d, t, l, tag),
        "table": lambda cv, d, t, l: c_table(cv, d, t, l, tag),
        "outro": lambda cv, d, t, l: c_outro(cv, d, t, l, tag),
    }
