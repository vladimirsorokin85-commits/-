# -*- coding: utf-8 -*-
"""Ролик A «КУПОЛ НА КРЫШУ» — что это и как ставится. 9:16, ~30 с."""
from PIL import Image, ImageDraw

import k8m as K
from k8m import (BG0, BG1, COND, DIM, H, LIME, PLATE, TEK, TXT, W, ac, c01, chips_row,
                 dome, grid, kicker, lplate, plate, scan_bar, slam, stage, tick_marks)

TITLE = "КУПОЛ НАД МАШИНОЙ · «КАПЮШОН» К-8М"
VAN = (96, 300, 856, 800)


def s_hook(cv, d, t, l):
    stage(cv, LIME, glow=0.30, t=t)
    grid(d, 9)
    kicker(d, "АВТО · ТРАНСПОРТ", 152, c01((l - .04) / .28), LIME, 28)
    y = 176
    for txt, size, col, t0 in (("КУПОЛ НАД", 100, TXT, .08),
                               ("МАШИНОЙ", 100, TXT, .15),
                               ("«КАПЮШОН» К-8М", 58, LIME, .26)):
        slam(cv, txt, COND, size, 540, y, ac(col, 255), c01((l - t0) / .26), "ma", maxw=940)
        y += int(size * 1.06)
    lplate(cv, "foto_van", [56, 500, 1024, 1140], zoom=1.0, p=c01((l - .34) / .30),
           caption="КУПОЛ НА КРЫШЕ · МАГНИТЫ", src=VAN)
    slam(cv, "8 КАНАЛОВ ПРОТИВ ДРОНОВ НА МАШИНЕ", TEK, 25, 540, 1176,
         ac(TXT, 245), c01((l - .60) / .26), "ma", maxw=980)
    slam(cv, "ДО 200 М · ПИТАНИЕ 12/24 В", TEK, 24, 540, 1224,
         ac(DIM, 240), c01((l - .70) / .26), "ma", maxw=940)
    tiles = [("8", "КАНАЛОВ"), ("160", "ВТ"), ("200", "М ДО")]
    if l > .80:
        bw = 300
        for i, (v, s2) in enumerate(tiles):
            p = c01((l - .80 - i * .07) / .26)
            if p <= 0:
                continue
            x = 78 + i * (bw + 14)
            d.rectangle([x, 1284, x + bw, 1452], fill=ac(BG1, int(238 * p)),
                        outline=ac(LIME, int(130 * p)))
            d.rectangle([x, 1284, x + bw, 1288], fill=ac(LIME, int(235 * p)))
            d.text((x + bw // 2, 1306), v, font=K.F(COND, 96), fill=ac(LIME, 252 * p), anchor="ma")
            d.text((x + bw // 2, 1414), s2, font=K.F(TEK, 19), fill=ac(DIM, 240 * p), anchor="ma")
    if l > 1.15:
        chips_row(d, 1500, [("FPV", LIME, False), ("РАЗВЕДКА", LIME, False),
                            ("ТРАНСПОРТ", LIME, False)], int(255 * c01((l - 1.15) / .3)))
    tick_marks(d)


def s_specs(cv, d, t, l):
    stage(cv, LIME, glow=.26, t=t)
    grid(d, 11)
    kicker(d, "КАНАЛОВ ПОМЕХ", 166, c01((l - .02) / .22), LIME, 27)
    if l > .05:
        p = c01((l - .05) / .28)
        k = 1 + .05 * (1 - K.eo(p))
        slam(cv, "8", TEK, int(230 * k), 88, 196, ac(LIME, 255 * p), p, "lt")
        slam(cv, "НЕЗАВИСИМЫХ КАНАЛА", TEK, 26, 96, 456, ac(TXT, 240), p, "lt", maxw=520)
    rows = [("400–1020", "МГЦ", .30), ("2100–2800", "МГЦ", .44), ("5680–5900", "МГЦ", .58)]
    for i, (val, unit, t0) in enumerate(rows):
        p = c01((l - t0) / .26)
        if p <= 0:
            continue
        y = 580 + i * 140
        d.rectangle([76, y, 100, y + 4], fill=ac(LIME, int(235 * p)))
        slam(cv, val, TEK, 56, 84, y + 6, ac(TXT, 250), p, "lt")
        slam(cv, unit, TEK, 25, 84 + int(K.F(TEK, 56).getlength(val)) + 20, y + 28,
             ac(DIM, 235), p, "lt")
        scan_bar(d, 76, 1004, y + 92, c01((l - t0 - .1) / .5), LIME, 3)
    if l > .76:
        p = c01((l - .76) / .26)
        plate(cv, [76, 1068, 1004, 1276], BG1, int(238 * p), LIME, int(130 * p), 2)
        d.rectangle([76, 1068, 1004, 1073], fill=ac(LIME, int(240 * p)))
        slam(cv, "МОЩНОСТЬ ПЕРЕДАТЧИКОВ", TEK, 22, 112, 1104, ac(DIM, 245 * p), p, "lt")
        slam(cv, "160 ВТ", COND, 116, 104, 1136, ac(LIME, 255 * p), p, "lt")
    if l > 1.10:
        p = c01((l - 1.10) / .3)
        chips_row(d, 1330, [("МАШИНА", LIME, False), ("КРЫША", LIME, False),
                            ("12/24 В", LIME, False)], int(250 * p), size=24)
        slam(cv, "ТТХ — ПО ДАННЫМ ПРОИЗВОДИТЕЛЯ", TEK, 20, 540, 1428,
             ac(DIM, 210), c01((l - 1.25) / .35), "ma", maxw=900)
    tick_marks(d)


def s_mount(cv, d, t, l):
    stage(cv, LIME, glow=.18, t=t)
    grid(d, 8)
    kicker(d, "КОМПЛЕКТ И УСТАНОВКА", 168, c01((l - .02) / .24), LIME, 25)
    lplate(cv, "foto_34", [64, 206, 1016, 846], zoom=1.02, p=c01((l - .06) / .32),
           caption="КУПОЛ · ПРЕОБРАЗОВАТЕЛЬ · ПУЛЬТ")
    rows = [("МАГНИТНЫЕ КРЕПЛЕНИЯ", "В КОМПЛЕКТЕ", .46),
            ("ПИТАНИЕ", "12/24 В, БОРТ", .62),
            ("ВЫНОСНОЙ ПУЛЬТ", "В КАБИНУ", .78),
            ("МАССА", "20 КГ", .94)]
    for i, (a, b, t0) in enumerate(rows):
        p = c01((l - t0) / .24)
        if p <= 0:
            continue
        y = 928 + i * 146
        d.rectangle([76, y, 1004, y + 1], fill=ac(LIME, int(58 * p)))
        d.rectangle([76, y + 26, 82, y + 80], fill=ac(LIME, int(240 * p)))
        slam(cv, a, TEK, 26, 108, y + 28, ac(TXT, 250), p, "lt", maxw=560)
        slam(cv, b, TEK, 23, 108, y + 72, ac(LIME, 250), p, "lt", maxw=700)
    if l > 1.42:
        p = c01((l - 1.42) / .3)
        slam(cv, "ПРОТИВОУДАРНЫЙ КУПОЛ · ЗАЩИТА БЛОКОВ", TEK, 21, 540, 1530,
             ac(DIM, 235), p, "ma", maxw=940)
        slam(cv, "ПРИМЕНЕНИЕ — В УСТАНОВЛЕННОМ ПОРЯДКЕ", TEK, 20, 540, 1572,
             ac(DIM, 200), c01((l - 1.55) / .3), "ma", maxw=940)
    tick_marks(d)


def s_outro(cv, d, t, l):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((13, 17, 11), 255)))
    dome(cv, 540, 560, 340, c01((l - .05) / 2.4), LIME)
    grid(d, 7)
    if l > .10:
        p = c01((l - .10) / .28)
        slam(cv, "«КАПЮШОН» К-8М", COND, 76, 540, 226, ac(TXT, 255), p, "ma", maxw=940)
    if l > .38:
        p = c01((l - .38) / .28)
        plate(cv, [86, 966, 994, 1150], BG1, int(240 * p), LIME, int(180 * p), 3, LIME)
        slam(cv, "ЦЕНА ПО ЗАПРОСУ", COND, 70, 540, 986, ac(LIME, 255), p, "ma", maxw=860)
        slam(cv, "В НАЛИЧИИ · ГАРАНТИЯ 12 МЕСЯЦЕВ", TEK, 23, 540, 1094,
             ac(TXT, 240), p, "ma", maxw=830)
    if l > .72:
        p = c01((l - .72) / .3)
        chips_row(d, 1200, [("8 КАНАЛОВ", LIME, True), ("160 ВТ", LIME, False),
                            ("ДО 200 М", LIME, False)], int(250 * p), size=24)
    if l > 1.02:
        p = c01((l - 1.02) / .3)
        slam(cv, "t.me/vokope_ru", TEK, 32, 540, 1326, ac(PLATE, 240), p, "ma")
        slam(cv, "+7 (999) 136-71-42", TEK, 28, 540, 1380, ac(PLATE, 220), p, "ma")
    if l > 1.30:
        p = c01((l - 1.30) / .4)
        f = K.F(TEK, 15)
        txt = ["Оборудование является радиоэлектронным средством.",
               "Порядок приобретения и применения — по законодательству РФ.",
               "ТТХ — по данным производителя. Не оферта."]
        for i, s in enumerate(txt):
            d.text((540, 1440 + i * 24), s, font=f, fill=ac(DIM, int(175 * p)), anchor="ma")
    tick_marks(d)


FN = {"hook": s_hook, "specs": s_specs, "mount": s_mount, "outro": s_outro}
