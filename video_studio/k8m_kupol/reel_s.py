# -*- coding: utf-8 -*-
"""Ролик S «КАРТОЧКА» — 15 секунд, формат из QA.md: 2 реплики, 3 сцены."""
from PIL import Image, ImageDraw

import k8m as K
from k8m import (BG1, COND, DIM, H, LIME, PLATE, TEK, TXT, W, ac, c01, grid, kicker,
                 lplate, plate, slam, stage, tick_marks)

TITLE = "«КАПЮШОН» К-8М · КУПОЛ НА МАШИНУ"
VAN = (96, 330, 856, 800)


def s_hook(cv, d, t, l):
    stage(cv, LIME, glow=.30, t=t)
    grid(d, 9)
    kicker(d, "АВТО · ТРАНСПОРТ", 158, c01((l - .03) / .22), LIME, 27)
    y = 196
    for txt, size, col, t0 in (("КАПЮШОН", 116, TXT, .06), ("К-8М", 116, LIME, .16)):
        slam(cv, txt, COND, size, 540, y, ac(col, 255), c01((l - t0) / .22), "ma", maxw=900)
        y += int(size * 1.04)
    lplate(cv, "foto_van", [56, 520, 1024, 1230], zoom=1.0, p=c01((l - .24) / .26),
           caption="КУПОЛ НА КРЫШЕ · МАГНИТЫ", src=VAN)
    if l > .62:
        p = c01((l - .62) / .26)
        slam(cv, "8 КАНАЛОВ · ДО 200 М", COND, 62, 540, 1300, ac(TXT, 255), p, "ma", maxw=900)
        slam(cv, "ПИТАНИЕ 12/24 В · МАССА 20 КГ", TEK, 24, 540, 1368, ac(DIM, 240), p, "ma", maxw=900)
    tick_marks(d)


def s_specs(cv, d, t, l):
    stage(cv, LIME, glow=.24, t=t)
    grid(d, 10)
    kicker(d, "ДИАПАЗОНЫ, МГЦ", 176, c01((l - .02) / .20), LIME, 26)
    rows = [("400–1020", .10), ("2100–2800", .20), ("5680–5900", .30)]
    for i, (val, t0) in enumerate(rows):
        p = c01((l - t0) / .22)
        if p <= 0:
            continue
        y = 270 + i * 190
        d.rectangle([82, y, 106, y + 4], fill=ac(LIME, int(235 * p)))
        slam(cv, val, TEK, 78, 92, y + 10, ac(TXT, 252), p, "lt")
        slam(cv, "МГЦ", TEK, 26, 900, y + 46, ac(DIM, 240), p, "lt", maxw=140)
    if l > .48:
        p = c01((l - .48) / .24)
        plate(cv, [82, 900, 998, 1112], BG1, int(240 * p), LIME, int(150 * p), 2, LIME)
        d.rectangle([82, 900, 998, 905], fill=ac(LIME, int(240 * p)))
        slam(cv, "МОЩНОСТЬ", TEK, 22, 116, 936, ac(DIM, 245 * p), p, "lt")
        slam(cv, "160 ВТ", COND, 118, 108, 972, ac(LIME, 255 * p), p, "lt")
        slam(cv, "ТТХ — ПО ДАННЫМ ПРОИЗВОДИТЕЛЯ", TEK, 20, 540, 1170, ac(DIM, 220),
             c01((l - .60) / .3), "ma", maxw=900)
    if l > .78:
        p = c01((l - .78) / .3)
        lplate(cv, "foto_kit", [82, 1206, 998, 1560], zoom=0.80, ox=0.5, oy=0.42, p=p,
               caption="КУПОЛ · ПРЕОБРАЗОВАТЕЛЬ · ПУЛЬТ")
    tick_marks(d)


def s_outro(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((13, 17, 11), 255)))
    K.rings(cv, 540, 470, 260, c01((l - .02) / 1.6), LIME, 3)
    grid(d, 7)
    if l > .03:
        kicker(d, "МАГАЗИН «В ОКОПЕ»", 168, c01((l - .03) / .20), LIME, 26)
    if l > .06:
        p = c01((l - .06) / .22)
        slam(cv, "«КАПЮШОН» К-8М", COND, 84, 540, 218, ac(TXT, 255), p, "ma", maxw=940)
    if l > .26:
        p = c01((l - .26) / .24)
        plate(cv, [96, 880, 984, 1024], BG1, int(242 * p), LIME, int(200 * p), 3, LIME)
        slam(cv, "ЦЕНА ПО ЗАПРОСУ", COND, 68, 540, 902, ac(LIME, 255), p, "ma", maxw=840)
        slam(cv, "В НАЛИЧИИ · ГАРАНТИЯ 12 МЕСЯЦЕВ", TEK, 22, 540, 972, ac(TXT, 240), p, "ma", maxw=820)
    if l > .48:
        p = c01((l - .48) / .26)
        slam(cv, "+7 (999) 136-71-42", TEK, 44, 540, 1104, ac(PLATE, 250), p, "ma", maxw=900)
        slam(cv, "@vokope_ru", TEK, 30, 540, 1170, ac(LIME, 245), p, "ma")
    if l > .70:
        p = c01((l - .70) / .3)
        f = K.F(TEK, 16)
        for i, s in enumerate(["Применение — в установленном порядке.",
                               "Не является публичной офертой."]):
            d.text((540, 1250 + i * 26), s, font=f, fill=ac(DIM, int(180 * p)), anchor="ma")
    tick_marks(d)


FN = {"hook": s_hook, "specs": s_specs, "outro": s_outro}
