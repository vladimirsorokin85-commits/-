# -*- coding: utf-8 -*-
"""Ролик B «КОМУ И ЧТО В КОМПЛЕКТЕ» — применения и состав. 9:16, ~30 с."""
from PIL import Image, ImageDraw

import k8m as K
from k8m import (BG0, BG1, COND, DIM, H, LIME, PLATE, TEK, TXT, W, ac, c01, chips_row,
                 dome, grid, kicker, lplate, photo_in, plate, slam, stage, tick_marks)

TITLE = "«КАПЮШОН» К-8М · КОМУ И ЧТО В КОМПЛЕКТЕ"

VAN = (96, 348, 856, 792)


def s_hook(cv, d, t, l):
    stage(cv, LIME, glow=.3, t=t)
    grid(d, 10)
    kicker(d, "СЕРИЯ РЭБ · 11.2026", 178, c01((l - .02) / .26), LIME, 26)
    slam(cv, "ЧТО В", COND, 132, 540, 228, ac(TXT, 255), c01((l - .05) / .26), "ma", maxw=940)
    slam(cv, "КОМПЛЕКТЕ", COND, 132, 540, 350, ac(TXT, 255), c01((l - .13) / .26), "ma", maxw=940)
    slam(cv, "«КАПЮШОН» К-8М", COND, 74, 540, 470, ac(LIME, 255), c01((l - .26) / .28), "ma", maxw=900)
    lplate(cv, "foto_kit", [56, 520, 1024, 1180], zoom=1.02, p=c01((l - .34) / .32),
           caption="КУПОЛ · ПРЕОБРАЗОВАТЕЛЬ · ПУЛЬТ")
    if l > 1.00:
        p = c01((l - 1.00) / .3)
        chips_row(d, 1230, [("8 КАНАЛОВ", LIME, True), ("160 ВТ", LIME, False),
                            ("12/24 В", LIME, False)], int(250 * p), size=25)
        slam(cv, "ВЕС 20 КГ · ГАРАНТИЯ 12 МЕС.", TEK, 23, 540, 1326, ac(DIM, 240),
             c01((l - 1.15) / .3), "ma", maxw=900)
        slam(cv, "ТТХ — ПО ДАННЫМ ПРОИЗВОДИТЕЛЯ", TEK, 20, 540, 1402, ac(DIM, 200),
             c01((l - 1.30) / .35), "ma", maxw=900)
    tick_marks(d)


def s_use(cv, d, t, l):
    stage(cv, LIME, glow=.15, t=t)
    photo_in(cv, "foto_van", VAN, [0, 300, W, 880], p=c01(l / .5), dark=.55)
    grid(d, 8)
    kicker(d, "КОМУ НУЖНО", 174, c01((l - .02) / .26), LIME, 27)
    lines = [("МАШИНА И ОБЪЕКТ", "НА ХОДУ", .30),
             ("УСТАНОВКА НА КРЫШУ", "НА МАГНИТАХ", .55),
             ("ЗАЩИТА ОТ FPV", "И ДРОНОВ РАЗВЕДКИ", .80)]
    for i, (a, b, t0) in enumerate(lines):
        p = c01((l - t0) / .28)
        if p <= 0:
            continue
        y = 960 + i * 196
        d.rectangle([76, y, 1004, y + 1], fill=ac(LIME, int(70 * p)))
        slam(cv, a, COND, 84, 96, y + 24, ac(TXT, 255), p, "lt", maxw=900)
        slam(cv, b, TEK, 25, 100, y + 122, ac(LIME, 250), p, "lt", maxw=880)
    if l > 1.35:
        p = c01((l - 1.35) / .3)
        plates = [("20 КГ", "ВЕС"), ("360°", "КУПОЛ"), ("12/24 В", "БОРТ")]
        bw = 296
        for i, (v, s) in enumerate(plates):
            x = 76 + i * (bw + 16)
            d.rectangle([x, 1580, x + bw, 1668], fill=ac(BG1, int(236 * p)),
                        outline=ac(LIME, int(120 * p)))
            d.rectangle([x, 1580, x + bw, 1584], fill=ac(LIME, int(240 * p)))
            d.text((x + bw // 2, 1598), v, font=K.F(COND, 46), fill=ac(LIME, 250 * p), anchor="ma")
            d.text((x + bw // 2, 1642), s, font=K.F(TEK, 18), fill=ac(DIM, 235 * p), anchor="ma")
    tick_marks(d)


def s_kit(cv, d, t, l):
    stage(cv, LIME, glow=.2, t=t)
    grid(d, 9)
    kicker(d, "ИСПОЛНЕНИЕ И СОСТАВ", 172, c01((l - .02) / .24), LIME, 26)
    slam(cv, "ПРОТИВОУДАРНЫЙ КУПОЛ", COND, 66, 540, 214, ac(TXT, 255),
         c01((l - .05) / .28), "ma", maxw=980)
    lplate(cv, "foto_bottom", [64, 300, 1016, 980], zoom=1.0, p=c01((l - .14) / .34),
           caption="КУПОЛ · РАДИАТОРЫ · ПАСПОРТ")
    rows = [("КУПОЛ", "ЗАЩИТА ОТ МЕХАНИКИ И ПОГОДЫ", .62),
            ("ПРЕОБРАЗОВАТЕЛЬ", "12/24 В", .80),
            ("ПУЛЬТ", "ВЫНОСНОЙ, В КАБИНУ", .98),
            ("КАБЕЛИ И КРЕПЁЖ", "В КОМПЛЕКТЕ", 1.16)]
    for i, (a, b, t0) in enumerate(rows):
        p = c01((l - t0) / .26)
        if p <= 0:
            continue
        y = 1040 + i * 148
        d.rectangle([76, y, 1004, y + 1], fill=ac(LIME, int(56 * p)))
        d.rectangle([76, y + 24, 82, y + 78], fill=ac(LIME, int(240 * p)))
        slam(cv, a, TEK, 27, 108, y + 26, ac(TXT, 250), p, "lt", maxw=560)
        slam(cv, b, TEK, 22, 108, y + 72, ac(LIME, 250), p, "lt", maxw=760)
    tick_marks(d)


def s_outro(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((13, 17, 11), 255)))
    K.rings(cv, 540, 560, 300, c01((l - .05) / 3.0), LIME, 3)
    grid(d, 8)
    if l > .10:
        p = c01((l - .10) / .28)
        slam(cv, "КОРОТКО", TEK, 26, 540, 214, ac(DIM, 245), p, "ma")
        tiles = [("8", "КАНАЛОВ"), ("160", "ВТ"), ("200", "М ДО")]
        bw = 300
        for i, (v, s) in enumerate(tiles):
            q = c01((l - .10 - i * .10) / .26)
            x = 78 + i * (bw + 14)
            d.rectangle([x, 260, x + bw, 442], fill=ac(BG1, int(238 * q)),
                        outline=ac(LIME, int(140 * q)))
            d.text((x + bw // 2, 286), v, font=K.F(COND, 108), fill=ac(LIME, 252 * q), anchor="ma")
            d.text((x + bw // 2, 404), s, font=K.F(TEK, 20), fill=ac(DIM, 240 * q), anchor="ma")
    if l > .62:
        p = c01((l - .62) / .30)
        plate(cv, [86, 884, 994, 1072], BG1, int(242 * p), LIME, int(190 * p), 3, LIME)
        slam(cv, "ЦЕНА ПО ЗАПРОСУ", COND, 70, 540, 906, ac(LIME, 255), p, "ma", maxw=860)
        slam(cv, "В НАЛИЧИИ · ГАРАНТИЯ 12 МЕСЯЦЕВ", TEK, 23, 540, 1012, ac(TXT, 240), p, "ma", maxw=830)
    if l > 1.15:
        p = c01((l - 1.25) / .3)
        chips_row(d, 1200, [("ДОСТАВКА ПО РФ", LIME, False), ("САМОВЫВОЗ В МОСКВЕ", LIME, False)],
                  int(250 * p), size=24)
    if l > 1.55:
        p = c01((l - 1.55) / .3)
        slam(cv, "t.me/vokope_ru", TEK, 30, 540, 1388, ac(PLATE, 240), p, "ma")
        slam(cv, "+7 (999) 136-71-42", TEK, 26, 540, 1438, ac(PLATE, 220), p, "ma")
    if l > 1.80:
        p = c01((l - 1.80) / .4)
        f = K.F(TEK, 15)
        txt = ["Оборудование является радиоэлектронным средством.",
               "Порядок приобретения и применения — по законодательству РФ.",
               "Дальность зависит от условий эксплуатации. Не оферта."]
        for i, s in enumerate(txt):
            d.text((540, 1520 + i * 24), s, font=f, fill=ac(DIM, int(175 * p)), anchor="ma")
    tick_marks(d)


FN = {"hook": s_hook, "use": s_use, "kit": s_kit, "outro": s_outro}
