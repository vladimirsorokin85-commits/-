# -*- coding: utf-8 -*-
"""Ролик 2 «Разбор по отсекам» — рюкзак 7.62, вертикаль 9:16."""
import math

from PIL import Image, ImageDraw

import base as B
from base import (COY, DIM, ICE, KHAKI, MONO, RUSSO, TXT, W, ac, arrow, bag, callout,
                  chip, chips_row, cl, c01, dim_h, eo, ghost, slam, stage, tick_marks)

TAG = "r2"
TOTAL = 31.19
TITLE = "РЮКЗАК 7.62 // РАЗБОР ПО ОТСЕКАМ"


def s_lid(cv, d, t, l):
    stage(cv, t, KHAKI, glow=c01(l / 1.2))
    ui = ImageDraw.Draw(cv)
    bag(cv, "khaki_front", 540, 1010, 1105, shadow=1.0, bloom=.85 * c01(l / .8))
    slam(cv, "РАЗБОР", RUSSO, 92, 540, 176, ac(TXT, 255), c01((l - .05) / .28), "ma", 34, maxw=900)
    slam(cv, "ПО ОТСЕКАМ", RUSSO, 78, 540, 278, ac(KHAKI, 255), c01((l - .18) / .30), "ma", 30, maxw=900)
    if l > 1.0:
        p = c01((l - 1.0) / .40)
        callout(ui, 700, 610, "КАРМАН НА МОЛНИИ", p, COY, 1)
    if l > 1.6:
        p = c01((l - 1.6) / .40)
        callout(ui, 392, 840, "КАРТА", p, KHAKI, -1)
    if l > 2.2:
        p = c01((l - 2.2) / .40)
        callout(ui, 690, 1080, "ПОД ШЛЕМ", p, ICE, 1)
    if l > 2.9:
        p = c01((l - 2.9) / .35)
        chips_row(ui, 1618, [("КРЫШКА", COY, True), ("КАРТА", KHAKI, False), ("ШЛЕМ", ICE, False)],
                  int(255 * p), size=24)
    tick_marks(d)


def s_zip(cv, d, t, l):
    stage(cv, t, COY, glow=.55)
    ui = ImageDraw.Draw(cv)
    if l < 3.55:
        k = 1 - c01((l - 3.3) / .25)
        bag(cv, "coyote_front", 540, 1010, 1090, shadow=.95, alpha=int(255 * k), bloom=.45, accent=COY)
        slam(cv, "МОЛНИЯ №10", RUSSO, 88, 540, 176, ac(TXT, 255 * k), c01((l - .03) / .26) * k, "ma", 30, maxw=900)
        if l > .35:
            p = c01((l - .35) / .45)
            slam(cv, "БЫСТРЫЙ ДОСТУП", MONO, 32, 540, 288, ac(COY, 245 * k), p * k, "ma", 16)
        if l > .8:
            p = c01((l - .8) / .70)
            arrow(ui, 700, 520, 640, 1290, p, COY, 9)
        if l > 1.9:
            p = c01((l - 1.9) / .35)
            callout(ui, 420, 700, "СВЕРХУ ВНИЗ", p, COY, -1)
        if l > 2.4:
            p = c01((l - 2.4) / .35)
            chips_row(ui, 1600, [("ДВУСТОРОННИЙ ХОД", COY, True)], int(255 * p * k), size=25)
    else:
        k = c01((l - 3.55) / .35)
        bag(cv, "khaki_side", 540, 1010, 1080, shadow=.95, alpha=int(255 * k), bloom=.45)
        slam(cv, "БОКОВЫЕ", RUSSO, 88, 540, 176, ac(TXT, 255 * k), k, "ma", 30, maxw=900)
        slam(cv, "КАРМАНЫ", RUSSO, 88, 540, 272, ac(KHAKI, 255 * k), c01((l - 3.7) / .3) * k, "ma", 30, maxw=900)
        if l > 4.1:
            p = c01((l - 4.1) / .40) * k
            callout(ui, 690, 760, "РАЗДЕЛИТЕЛИ", p, KHAKI, 1)
        if l > 4.6:
            p = c01((l - 4.6) / .40) * k
            callout(ui, 380, 1180, "РЕЗИНКА", p, COY, -1)
        if l > 4.9:
            p = c01((l - 4.9) / .35) * k
            chips_row(ui, 1618, [("2 БОКОВЫХ КАРМАНА", KHAKI, True)], int(255 * p), size=25)
    tick_marks(d)


def s_bottom(cv, d, t, l):
    stage(cv, t, ICE, glow=.4)
    ui = ImageDraw.Draw(cv)
    if l < 3.1:
        k = 1 - c01((l - 2.85) / .25)
        bag(cv, "coyote_front", 540, 1010, 1090, shadow=.95, alpha=int(255 * k), bloom=.4, accent=ICE)
        slam(cv, "НИЗ", RUSSO, 110, 540, 176, ac(TXT, 255 * k), c01((l - .03) / .26) * k, "ma", 34, maxw=900)
        if l > .4:
            p = c01((l - .4) / .40) * k
            slam(cv, "ОТСЕК ПОД ДОЖДЕВИК", MONO, 32, 540, 300, ac(ICE, 245 * k), p, "ma", 16)
        if l > 1.0:
            p = c01((l - 1.0) / .55) * k
            callout(ui, 540, 1300, "МОЛНИЯ ВНИЗУ", p, ICE, 1)
        if l > 1.7:
            p = c01((l - 1.7) / .40) * k
            callout(ui, 400, 1180, "СЪЁМНЫЙ ВКЛАДЫШ", p, COY, -1)
    else:
        k = c01((l - 3.1) / .35)
        bag(cv, "khaki_cover", 540, 960, 1120, shadow=.9, alpha=int(255 * k), bloom=.5, accent=KHAKI)
        slam(cv, "ДОЖДЕВИК", RUSSO, 96, 540, 176, ac(TXT, 255 * k), k, "ma", 32, maxw=920)
        if l > 3.6:
            p = c01((l - 3.6) / .35) * k
            slam(cv, "В ДЕЛЕ", MONO, 34, 540, 296, ac(KHAKI, 245 * k), p, "ma", 16)
        if l > 4.0:
            p = c01((l - 4.0) / .35) * k
            chips_row(ui, 1608, [("ДОЖДЕВИК", KHAKI, True), ("МОКРОЕ — ОТДЕЛЬНО", ICE, False)],
                      int(255 * p), size=23)
    tick_marks(d)


def s_harness(cv, d, t, l):
    stage(cv, t, KHAKI, glow=.5)
    ui = ImageDraw.Draw(cv)
    if l < 4.6:
        k = 1 - c01((l - 4.35) / .25)
        bag(cv, "khaki_back", 540, 1010, 1100, shadow=.95, alpha=int(255 * k), bloom=.45)
        slam(cv, "ПОДВЕС", RUSSO, 96, 540, 176, ac(TXT, 255 * k), c01((l - .03) / .26) * k, "ma", 32, maxw=900)
        if l > .5:
            p = c01((l - .5) / .40) * k
            callout(ui, 542, 706, "5 ПОЛОЖЕНИЙ", p, COY, 1)
        if l > 1.1:
            p = c01((l - 1.1) / .40) * k
            callout(ui, 322, 880, "3D-СЕТКА", p, KHAKI, -1)
        if l > 1.8:
            p = c01((l - 1.8) / .40) * k
            callout(ui, 690, 1270, "СЪЁМНЫЙ ПОЯС", p, ICE, 1)
        if l > 2.5:
            p = c01((l - 2.5) / .35) * k
            chips_row(ui, 1618, [("3,4 КГ", COY, True), ("ПОД ЛЮБОЙ РОСТ", KHAKI, False)],
                      int(255 * p), size=24)
    else:
        k = c01((l - 4.6) / .35)
        p1 = c01((l - 4.6) / .40) * k
        p2 = c01((l - 4.85) / .40) * k
        if p1 > 0:
            bag(cv, "coyote_side", 300, 930, 840, shadow=.85, alpha=int(255 * p1), bloom=.3, accent=COY)
        if p2 > 0:
            bag(cv, "khaki_side", 780, 930, 840, shadow=.85, alpha=int(255 * p2), bloom=.3)
        slam(cv, "КОЙОТ · ХАКИ", RUSSO, 82, 540, 186, ac(TXT, 255 * k), k, "ma", 30, maxw=940)
        if l > 5.3:
            p = c01((l - 5.3) / .35) * k
            chips_row(ui, 1560, [("В НАЛИЧИИ", COY, True)], int(255 * p), size=27)
    tick_marks(d)


def s_outro(cv, d, t, l):
    B.outro_card(cv, d, l, KHAKI, "РЮКЗАК 7.62 · РАЗБОР", "70 Л · 5 ОТСЕКОВ · MOLLE 1″",
                 bags=(("khaki_back", 540, 500, KHAKI),))


SCENES = [("lid", 0.00), ("zip", 7.15), ("bottom", 14.90), ("harness", 20.80), ("outro", 28.24)]

FN = {"lid": s_lid, "zip": s_zip, "bottom": s_bottom, "harness": s_harness, "outro": s_outro}
