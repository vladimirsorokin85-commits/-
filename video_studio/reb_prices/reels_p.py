# -*- coding: utf-8 -*-
"""Пять прайс-роликов: общий + по четырём категориям."""
from PIL import Image, ImageDraw

import price_lib as P
from price_lib import CATS, CONTACT, FOOT, OSW, TITLE_HUD  # noqa: F401
from k8m import (BG1, DIM, H, LIME, PLATE, TEK, TXT, W, ac, c01, chips_row,
                 grid, kicker, lplate, plate, slam, stage, tick_marks)


def _nums(rows):
    v = [int(x[1].replace(" ", "")) for x in rows]
    return rows[v.index(min(v))][1], rows[v.index(max(v))][1]


def _outro(cv, d, l, cat_label, accent=LIME):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((13, 17, 11), 255)))
    grid(d, 7)
    if l > .03:
        kicker(d, "МАГАЗИН «В ОКОПЕ»", 300, c01((l - .03) / .22), LIME, 26)
    if l > .10:
        p = c01((l - .10) / .26)
        slam(cv, "ЦЕНЫ ЗАВОДСКИЕ", OSW, 96, 540, 372, ac(TXT, 255), p, "ma", maxw=940)
        slam(cv, cat_label, TEK, 24, 540, 470, ac(LIME, 245), c01((l - .20) / .26), "ma", maxw=900)
    if l > .34:
        p = c01((l - .34) / .28)
        plate(cv, [86, 720, 994, 900], BG1, int(240 * p), LIME, int(180 * p), 3, LIME)
        slam(cv, "РОЗНИЦА — В КАДРЕ", OSW, 54, 540, 752, ac(LIME, 255), p, "ma", maxw=860)
        slam(cv, "С НДС — ПО ЗАПРОСУ", TEK, 24, 540, 826, ac(TXT, 240), p, "ma", maxw=820)
    if l > .62:
        p = c01((l - .62) / .28)
        slam(cv, "В наличии · Москва и Липецк", TEK, 24, 540, 990, ac(DIM, 240), p, "ma", maxw=900)
        slam(cv, "Доставка по России", TEK, 24, 540, 1032, ac(DIM, 240), p, "ma", maxw=900)
    if l > .86:
        p = c01((l - .86) / .28)
        slam(cv, "@VES_nn", OSW, 96, 540, 1152, ac(LIME, 255), p, "ma", maxw=800)
        slam(cv, "Telegram · напишите, подберём под задачу", TEK, 21, 540, 1230,
             ac(TXT, 235), c01((l - .96) / .28), "ma", maxw=900)
    if l > 1.10:
        p = c01((l - 1.10) / .4)
        f = P.K.F(TEK, 15)
        for i, s in enumerate(["Применение — в установленном порядке.",
                               "Цены розничные, не являются публичной офертой."]):
            d.text((540, 1330 + i * 26), s, font=f, fill=ac(DIM, int(180 * p)), anchor="ma")


# ─────────────────────────── общий
def g_hook(cv, d, t, l):
    stage(cv, LIME, glow=.32, t=t)
    grid(d, 9)
    kicker(d, "СПЕЦДОГОВОР С ПРОИЗВОДСТВОМ", 156, c01((l - .03) / .24), LIME, 25)
    y = 190
    for txt, size, col, t0 in (("ЦЕНЫ", 118, TXT, .06), ("ПРОИЗВОДИТЕЛЯ", 96, LIME, .16)):
        slam(cv, txt, OSW, size, 540, y, ac(col, 255), c01((l - t0) / .24), "ma", maxw=980)
        y += int(size * 1.06)
    lplate(cv, "foto_van", [56, 452, 1024, 1058], zoom=1.0, p=c01((l - .30) / .30),
           caption="РАБОТАЕМ НАПРЯМУЮ", src=(96, 300, 856, 800))
    if l > .62:
        p = c01((l - .62) / .26)
        slam(cv, "БЕЗ НАЦЕНКИ ПОСРЕДНИКОВ", OSW, 58, 540, 1108, ac(TXT, 255), p, "ma", maxw=960)
        slam(cv, "РОЗНИЧНЫЕ ЦЕНЫ · С НДС — ПО ЗАПРОСУ", TEK, 22, 540, 1170,
             ac(DIM, 240), c01((l - .74) / .26), "ma", maxw=960)
    if l > .95:
        chips_row(d, 1236, [("АВТО", LIME, False), ("ПЕРЕНОСНЫЕ", LIME, False)],
                  int(250 * c01((l - .95) / .26)), size=23)
        chips_row(d, 1306, [("СТАЦИОНАРНЫЕ", LIME, False), ("МОТО", LIME, False)],
                  int(250 * c01((l - 1.05) / .26)), size=23)
    tick_marks(d)


def g_cats(cv, d, t, l):
    stage(cv, LIME, glow=.22, t=t)
    grid(d, 10)
    kicker(d, "ЧЕТЫРЕ ГРУППЫ · 23 МОДЕЛИ", 158, c01((l - .02) / .22), LIME, 24)
    slam(cv, "ВСЁ В НАЛИЧИИ", OSW, 74, 540, 198, ac(TXT, 255), c01((l - .05) / .24), "ma", maxw=960)
    P.tiles4(cv, d, l, [("АВТО", "10 моделей"), ("ПЕРЕНОСНЫЕ", "7 моделей"),
                        ("СТАЦИОНАРНЫЕ", "4 модели"), ("МОТО", "2 модели")],
             y=500, t_start=.22, per=.10)
    if l > .95:
        p = c01((l - .95) / .28)
        plate(cv, [76, 1096, 1004, 1296], BG1, int(240 * p), LIME, int(170 * p), 3, LIME)
        slam(cv, "С НДС И БЕЗ НДС", OSW, 62, 540, 1118, ac(LIME, 255), p, "ma", maxw=880)
        slam(cv, "КАК УДОБНЕЕ ПОКУПАТЕЛЮ", TEK, 21, 540, 1198, ac(TXT, 240), p, "ma", maxw=880)
        slam(cv, "ЦЕНУ С НДС СЧИТАЕМ ПО ЗАПРОСУ", TEK, 20, 540, 1242, ac(DIM, 235), p, "ma", maxw=880)
    if l > 1.25:
        p = c01((l - 1.25) / .3)
        slam(cv, "Отгрузка: Москва и Липецк", TEK, 23, 540, 1360, ac(DIM, 240), p, "ma", maxw=900)
        slam(cv, "Доставка по России", TEK, 23, 540, 1400, ac(DIM, 235), p, "ma", maxw=900)
    tick_marks(d)


# ─────────────────────────── категория
def c_hook(cv, d, t, l, cat):
    name, rows = CATS[cat]
    lo, hi = _nums(rows)
    stage(cv, LIME, glow=.30, t=t)
    grid(d, 9)
    kicker(d, "РЭБ · ЦЕНЫ ПРОИЗВОДИТЕЛЯ", 156, c01((l - .03) / .22), LIME, 24)
    slam(cv, name, OSW, 88, 540, 204, ac(TXT, 255), c01((l - .06) / .24), "ma", maxw=980)
    slam(cv, "РОЗНИЧНЫЕ ЦЕНЫ", TEK, 24, 540, 292, ac(DIM, 240), c01((l - .16) / .24), "ma", maxw=900)
    if l > .20:
        p = c01((l - .20) / .28)
        plate(cv, [76, 372, 1004, 632], BG1, int(240 * p), LIME, int(170 * p), 3, LIME)
        slam(cv, "ОТ", TEK, 24, 112, 402, ac(DIM, 245 * p), p, "lt")
        slam(cv, lo, OSW, 88, 104, 434, ac(LIME, 255 * p), p, "lt", maxw=480)
        slam(cv, "ДО", TEK, 24, 968, 402, ac(DIM, 245 * p), p, "rt")
        slam(cv, hi, OSW, 58, 968, 438, ac(TXT, 250 * p), p, "rt", maxw=420)
        d.rectangle([560, 420, 562, 588], fill=ac(LIME, int(70 * p)))
    if l > .50:
        p = c01((l - .50) / .26)
        slam(cv, "БЕЗ НАЦЕНКИ ПОСРЕДНИКОВ", OSW, 54, 540, 676, ac(TXT, 255), p, "ma", maxw=960)
        slam(cv, "СПЕЦДОГОВОР С ПРОИЗВОДСТВОМ", TEK, 22, 540, 744, ac(LIME, 245),
             c01((l - .60) / .26), "ma", maxw=960)
    if l > .78:
        p = c01((l - .78) / .28)
        d.rectangle([76, 830, 1004, 832], fill=ac(LIME, int(90 * p)))
        d.text((76, 852), "ХОДОВЫЕ ПОЗИЦИИ", font=P.K.F(TEK, 20), fill=ac(DIM, int(225 * p)))
        for i, (m, price) in enumerate(P.HILITE[cat]):
            q = c01((l - .86 - i * .08) / .26)
            if q <= 0:
                continue
            y = 898 + i * 190
            d.rectangle([76, y, 1004, y + 168], fill=ac(BG1, int(230 * q)), outline=ac(LIME, int(120 * q)))
            d.rectangle([76, y, 82, y + 168], fill=ac(LIME, int(240 * q)))
            slam(cv, m, OSW, 34, 112, y + 30, ac(TXT, 252), q, "lt", maxw=560)
            slam(cv, price, OSW, 72, 968, y + 62, ac(LIME, 255), q, "rt", maxw=400)
    tick_marks(d)


def c_table(cv, d, t, l, cat):
    name, rows = CATS[cat]
    stage(cv, LIME, glow=.16, t=t)
    grid(d, 7)
    P.head(cv, d, l, name)
    top, h = P.table(cv, d, l, rows, t_start=.10, per=.11, y0=352, y1=1556 if len(rows) > 5 else 980)
    if len(rows) <= 4:
        bottom = top + len(rows) * h + 40
        y2 = min(1560, bottom + 470)
        lplate(cv, "foto_kit", [76, bottom, 1004, y2], zoom=1.0, ox=.5, oy=.42,
               p=c01((l - .55) / .3), caption="КУПОЛ · ПРЕОБРАЗОВАТЕЛЬ · ПУЛЬТ")
    P.foot(cv, d, l, t0=.55)
    tick_marks(d)


def c_outro(cv, d, t, l, cat):
    _outro(cv, d, l, CATS[cat][0])


def build_scenes(tag):
    """Возвращает {имя: функция(d, t, l)} для конкретного ролика."""
    if tag == "g":
        return {"hook": g_hook, "cats": g_cats, "outro": lambda cv, d, t, l: _outro(cv, d, l, "23 МОДЕЛИ · 4 ГРУППЫ")}
    cat = {"auto": "auto", "port": "port", "stat": "stat", "moto": "moto"}[tag]
    return {
        "hook": lambda cv, d, t, l: c_hook(cv, d, t, l, cat),
        "table": lambda cv, d, t, l: c_table(cv, d, t, l, cat),
        "outro": lambda cv, d, t, l: c_outro(cv, d, t, l, cat),
    }
