# -*- coding: utf-8 -*-
"""Ролик 1 «70 литров» — патрульный рюкзак 7.62, вертикаль 9:16."""
import math

from PIL import Image, ImageDraw

import base as B
from base import (COY, DIM, ICE, KHAKI, MONO, RUSSO, TXT, W, ac, arrow, bag, callout,
                  chip, chips_row, cl, c01, dim_h, dim_v, eo, ghost, plate, slam, stage, tick_marks)

TAG = "r1"
TOTAL = 30.65
TITLE = "РЮКЗАК 7.62 // 70 Л // ПАТРУЛЬНЫЙ"


def s_hook(cv, d, t, l):
    stage(cv, t, KHAKI, glow=c01(l / 1.2))
    ghost(cv, "70", B.COND, 400, 300, 1330, KHAKI, int(48 * c01((l - .7) / .6)))
    z = 1.0 + 0.04 * (1 - eo(l / 3.4)) + 0.006 * math.sin(l * 2)
    bag(cv, "coyote_side", 540, 1150, int(980 * z), shadow=1.0, bloom=0.9 * c01(l / .8))
    slam(cv, "РЮКЗАК", RUSSO, 88, 540, 150, ac(TXT, 255), c01((l - .05) / .28), "ma", 34, maxw=900)
    slam(cv, "7.62", B.COND, 176, 540, 214, ac(KHAKI, 255), c01((l - .18) / .30), "ma", 42, maxw=900)
    if l > .55:
        p = c01((l - .55) / .30)
        slam(cv, "70 ЛИТРОВ", RUSSO, 76, 540, 368, ac(TXT, 250 * p), p, "ma", 26, maxw=860)
        d.rectangle([540 - int(200 * eo(p)), 452, 540 + int(200 * eo(p)), 459], fill=ac(COY, 235))
    if l > 1.15:
        p = c01((l - 1.15) / .35)
        chips_row(d, 1626, [("ПАТРУЛЬНЫЙ", COY, True), ("СРЕДНЯЯ / БОЛЬШАЯ ДАЛЬНОСТЬ", KHAKI, False)],
                  int(255 * p), size=22)
    tick_marks(d)


def s_why(cv, d, t, l):
    stage(cv, t, KHAKI, glow=.5)
    bag(cv, "khaki_front", 540, 1030, 1040, shadow=.95, bloom=.45, accent=KHAKI)
    slam(cv, "ДЕЛАЛИ ДЛЯ", RUSSO, 66, 540, 196, ac(DIM, 255), c01((l - .05) / .28), "ma", 24, maxw=880)
    slam(cv, "СПЕЦНАЗА", RUSSO, 104, 540, 262, ac(TXT, 255), c01((l - .16) / .30), "ma", 34, maxw=920)
    if l > 1.2:
        p = c01((l - 1.2) / .35)
        slam(cv, "ПРОЧНЫЙ. ЛЁГКИЙ.", B.COND, 104, 540, 372, ac(KHAKI, 250 * p), p, "ma", 26, maxw=880)
    # две плашки-характеристики
    for i, (big, small, col) in enumerate((("3,4", "КГ ВЕС", COY), ("70", "ЛИТРОВ", KHAKI))):
        p = c01((l - .55 - i * .35) / .40)
        if p <= 0:
            continue
        x = 120 if i == 0 else 566
        y = 1478
        plate(cv, [x, y, x + 394, y + 244], (12, 13, 16), int(240 * p),
              col, int(220 * p), 2, col)
        slam(cv, big, B.COND, 128, x + 26, y + 30, ac(col, 255 * p), p, "lt", 16, maxw=330)
        slam(cv, small, MONO, 25, x + 28, y + 182, ac(DIM, 245 * p), p, "lt", 10, maxw=330)
    tick_marks(d)


def s_narrow(cv, d, t, l):
    stage(cv, t, COY, glow=.55)
    ui = ImageDraw.Draw(cv)
    # сетка «чертёж»
    for i in range(0, W + 1, 90):
        ui.line([(i, 118), (i, B.H - 126)], fill=ac(KHAKI, 16), width=1)
    for j in range(120, B.H - 120, 90):
        ui.line([(0, j), (W, j)], fill=ac(KHAKI, 16), width=1)
    bb = bag(cv, "coyote_side", 470, 960, 1010, shadow=.9, bloom=.5)
    slam(cv, "УЗКИЙ", RUSSO, 108, 540, 186, ac(TXT, 255), c01((l - .05) / .28), "ma", 36, maxw=900)
    slam(cv, "ПРОФИЛЬ", RUSSO, 108, 540, 292, ac(COY, 255), c01((l - .18) / .30), "ma", 36, maxw=900)
    # размеры
    dim_v(ui, 940, 500, 1440, "75 СМ", c01((l - .55) / .75), KHAKI, 1)
    dim_h(ui, 1560, 120, 620, "20 СМ", c01((l - 1.0) / .55), KHAKI)
    if l > 1.8:
        p = c01((l - 1.8) / .40)
        chips_row(ui, 402, [("УЛИЦЫ", KHAKI, False), ("ДВЕРИ", KHAKI, False), ("ЛЕСТНИЦЫ", KHAKI, False)],
                  int(255 * p), size=24)
    if l > 3.0:
        p = c01((l - 3.0) / .40)
        slam(cv, "40 × 20 × 75 СМ", MONO, 30, 540, 1608, ac(DIM, 235 * p), p, "ma", 14)
    tick_marks(d)


def s_access(cv, d, t, l):
    stage(cv, t, KHAKI, glow=.6)
    ui = ImageDraw.Draw(cv)
    bag(cv, "khaki_front", 540, 1000, 1080, shadow=.95, bloom=.4)
    slam(cv, "ДОСТУП", RUSSO, 96, 540, 180, ac(TXT, 255), c01((l - .03) / .25), "ma", 32, maxw=900)
    if l > .3:
        p = c01((l - .3) / .55)
        arrow(ui, 250, 560, 452, 660, p, COY, 8)
        plate(cv, [96, 486, 336, 542], (8, 9, 11), int(215 * p), COY, int(170 * p), 2)
        slam(cv, "СВЕРХУ", MONO, 30, 216, 496, ac(COY, 250 * p), c01((l - .45) / .3), "lt", 12)
    if l > .75:
        p = c01((l - .75) / .60)
        arrow(ui, 846, 600, 628, 1130, p, ICE, 8)
        plate(cv, [744, 526, 1006, 582], (8, 9, 11), int(215 * p), ICE, int(170 * p), 2)
        slam(cv, "ПО ЦЕНТРУ", MONO, 30, 762, 536, ac(ICE, 250 * p), c01((l - .9) / .3), "lt", 12)
    if l > 1.5:
        p = c01((l - 1.5) / .35)
        chips_row(ui, 1618, [("КРЫШКА", COY, True), ("ЦЕНТРАЛЬНАЯ МОЛНИЯ", ICE, False)], int(255 * p), size=23)
    tick_marks(d)


def s_molle(cv, d, t, l):
    stage(cv, t, KHAKI, glow=.5)
    ui = ImageDraw.Draw(cv)
    bag(cv, "coyote_front", 540, 1030, 1080, shadow=.95, bloom=.45, accent=COY)
    slam(cv, "MOLLE", RUSSO, 108, 540, 182, ac(TXT, 255), c01((l - .03) / .26), "ma", 36, maxw=900)
    if l > .3:
        p = c01((l - .3) / .35)
        slam(cv, "ПО ВСЕЙ ПЛОЩАДИ", MONO, 33, 540, 300, ac(KHAKI, 245 * p), p, "ma", 18)
    if l > .6:
        p = eo(c01((l - .6) / .8))
        for (x0, y0, x1, y1) in ((300, 640, 780, 700), (300, 712, 780, 772),
                                 (300, 784, 780, 844), (300, 856, 780, 916)):
            ui.line([(x0, y0), (int(x0 + (x1 - x0) * p), y0)], fill=ac(KHAKI, 120), width=3)
            ui.line([(x0, y1), (int(x0 + (x1 - x0) * p), y1)], fill=ac(KHAKI, 120), width=3)
        ui.line([(int(x0 + (x1 - x0) * p), y0), (int(x0 + (x1 - x0) * p), y1)], fill=ac(KHAKI, 120), width=3)
    if l > 1.5:
        p = c01((l - 1.5) / .45)
        for i, (bx, by) in enumerate(((330, 690), (770, 760), (330, 1200), (770, 1290), (540, 1390))):
            pp = c01((l - 1.5 - i * .10) / .30)
            if pp <= 0:
                continue
            ui.ellipse([bx - 20, by - 20, bx + 20, by + 20], fill=ac((8, 9, 11), int(230 * pp)),
                       outline=ac(COY, int(240 * pp)), width=3)
            ui.text((bx, by), str(i + 1), font=B.F(MONO, 24), fill=ac(COY, int(245 * pp)), anchor="mm")
        callout(ui, 760, 960, "5 ВНЕШНИХ КАРМАНОВ", p, COY, 1)
    if l > 2.2:
        p = c01((l - 2.2) / .35)
        callout(ui, 360, 620, "MOLLE 1″", p, KHAKI, -1)
    if l > 2.6:
        p = c01((l - 2.6) / .35)
        chips_row(ui, 1618, [("5 КАРМАНОВ", COY, True), ("MOLLE 1″", KHAKI, False)], int(255 * p), size=24)
    tick_marks(d)


def s_colors(cv, d, t, l):
    stage(cv, t, COY, glow=.5)
    ui = ImageDraw.Draw(cv)
    p1 = c01((l - .05) / .40)
    p2 = c01((l - .35) / .40)
    if p1 > 0:
        bag(cv, "coyote_side", 300, 930, 860, shadow=.85, alpha=int(255 * p1), bloom=.3, accent=COY)
    if p2 > 0:
        bag(cv, "khaki_side", 790, 930, 860, shadow=.85, alpha=int(255 * p2), bloom=.3, accent=KHAKI)
    slam(cv, "ДВА ЦВЕТА", RUSSO, 92, 540, 186, ac(TXT, 255), c01((l - .05) / .28), "ma", 32, maxw=900)
    if l > .7:
        p = c01((l - .7) / .35)
        ui.rectangle([150, 1370, 470, 1378], fill=ac(COY, int(240 * p)))
        slam(cv, "КОЙОТ", RUSSO, 60, 150, 1396, ac(COY, 250 * p), p, "lt", 20)
        slam(cv, "tan", MONO, 28, 152, 1472, ac(DIM, 230 * p), p, "lt", 10)
    if l > 1.0:
        p = c01((l - 1.0) / .35)
        ui.rectangle([620, 1370, 940, 1378], fill=ac(KHAKI, int(240 * p)))
        slam(cv, "ХАКИ", RUSSO, 60, 620, 1396, ac(KHAKI, 250 * p), p, "lt", 20)
        slam(cv, "khaki", MONO, 28, 622, 1472, ac(DIM, 230 * p), p, "lt", 10)
    if l > 1.5:
        p = c01((l - 1.5) / .35)
        chips_row(ui, 1570, [("В НАЛИЧИИ", COY, True)], int(255 * p), size=28)
    tick_marks(d)


def s_outro(cv, d, t, l):
    B.outro_card(cv, d, l, KHAKI, "РЮКЗАК 7.62", "70 Л · 40 × 20 × 75 СМ · 3,4 КГ",
                 bags=(("coyote_side", 352, 470, COY), ("khaki_front", 730, 470, KHAKI)))


SCENES = [("hook", 0.00), ("why", 4.51), ("narrow", 11.23), ("access", 17.26),
          ("molle", 20.11), ("colors", 24.03), ("outro", 27.80)]

FN = {"hook": s_hook, "why": s_why, "narrow": s_narrow, "access": s_access,
      "molle": s_molle, "colors": s_colors, "outro": s_outro}
