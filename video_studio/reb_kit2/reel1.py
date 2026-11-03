# -*- coding: utf-8 -*-
"""Ролик 1 «ДВЕ СТАНЦИИ» — цена и срок. Комплект РЭБ «Капюшон» К-8М, 9:16.

Тайминги сцен приходят из timeline_r1.json (пишет build_audio.py) — они всегда
совпадают со стартами реплик voice-28.
"""
from PIL import Image, ImageDraw

import base as B
from base import (COND, DIM, H, KHAKI, MONO, OLV, OLV2, RUSSO, TXT, W, WARN, ac, chip,
                  chips_row, cl, c01, cover, eo, grid, plate, slam, stage, strip, tick_marks)

TITLE = "РЭБ «КАПЮШОН» К-8М // КОМПЛЕКТ ИЗ ДВУХ"


def _pair(cv, cy, w, dark=0.30, zoom=1.0, col=(7, 8, 6)):
    box = strip(cv, "pair_clean", cy, w, zoom=zoom, dark=dark)
    cover(cv, box, 1280, col)
    return box


def s_hook(cv, d, t, l):
    stage(cv, OLV, glow=c01(l / 1.2), t=t)
    _pair(cv, 1120, 1240, dark=0.16, zoom=1.12 + 0.05 * (1 - eo(l / 4.2)),
          col=(11, 12, 9))
    grid(d, 12)
    slam(cv, "ДВЕ СТАНЦИИ", RUSSO, 90, 540, 140, ac(TXT, 255), c01((l - .04) / .24), "ma", 30, maxw=960)
    slam(cv, "«КАПЮШОН»", RUSSO, 86, 540, 240, ac(OLV, 255), c01((l - .14) / .26), "ma", 30, maxw=960)
    slam(cv, "К-8М", COND, 124, 540, 356, ac(TXT, 250), c01((l - .32) / .26), "ma", 34, maxw=700)
    if l > .58:
        p = c01((l - .58) / .28)
        plate(cv, [96, 482, 984, 596], (9, 10, 8), 250, OLV, int(205 * p), 2, OLV)
        slam(cv, "КОМПЛЕКТ НА ДВА АВТОМОБИЛЯ", MONO, 31, 540, 506, ac(TXT, 250 * p), p, "ma", 14)
        slam(cv, "ИЛИ РЕЗЕРВ", MONO, 25, 540, 550, ac(OLV, 235 * p), p, "ma", 12)
    if l > 1.55:
        p = c01((l - 1.55) / .32)
        chips_row(d, 1480, [("8 КАНАЛОВ", OLV, False), ("400–5900 МГЦ", KHAKI, False),
                            ("ДО 300 М", OLV, False)], int(245 * p), size=25)
    tick_marks(d)


def s_price(cv, d, t, l):
    stage(cv, OLV, glow=.5, t=t)
    box = strip(cv, "pair_clean", 1120, 1180, zoom=1.0, dark=0.58)
    cover(cv, box, 1280, (7, 8, 6))
    grid(d, 10)
    slam(cv, "СТОИМОСТЬ КОМПЛЕКТА", MONO, 32, 540, 152, ac(DIM, 255), c01((l - .03) / .22), "ma", 16)
    p = c01((l - .08) / .32)
    k = 1 + .09 * (1 - eo(p))
    slam(cv, "600 000 ₽", COND, int(150 * k), 540, 216, ac(TXT, 255 * p), p, "ma", 42, maxw=1000)
    if l > .50:
        p2 = c01((l - .50) / .24)
        slam(cv, "ЗА ДВЕ СТАНЦИИ", MONO, 34, 540, 392, ac(OLV, 252 * p2), p2, "ma", 16)
    if l > 1.05:
        p3 = c01((l - 1.05) / .30)
        plate(cv, [130, 462, 950, 656], (9, 10, 8), int(245 * p3), OLV2, int(210 * p3), 2, OLV2)
        slam(cv, "300 000 ₽", COND, 92, 540, 480, ac(TXT, 252 * p3), p3, "ma", 24, maxw=780)
        slam(cv, "ЗА КАЖДУЮ СТАНЦИЮ ОТДЕЛЬНО", MONO, 24, 540, 600, ac(DIM, 242 * p3), p3, "ma", 12)
    if l > 1.95:
        p4 = c01((l - 1.95) / .32)
        plate(cv, [150, 706, 930, 820], (36, 26, 6), int(248 * p4), WARN, int(238 * p4), 3, WARN)
        slam(cv, "АКЦИЯ ДО 15 НОЯБРЯ", MONO, 33, 540, 736, ac(WARN, 252 * p4), p4, "ma", 16)
        slam(cv, "ПО ГУМАНИТАРНОЙ ПРОГРАММЕ", MONO, 23, 540, 782, ac(TXT, 240 * p4), p4, "ma", 10)
    if l > 2.75:
        p5 = c01((l - 2.75) / .28)
        chips_row(d, 1470, [("ЦЕНА КОМПЛЕКТА 600 000 ₽", OLV, True)], int(255 * p5), size=25)
    tick_marks(d)


def s_promo(cv, d, t, l):
    stage(cv, WARN, glow=.5, t=t)
    grid(d, 12, WARN)
    slam(cv, "АКЦИЯ", RUSSO, 108, 540, 140, ac(WARN, 255), c01((l - .03) / .24), "ma", 34, maxw=900)
    if l > .18:
        p = c01((l - .18) / .26)
        slam(cv, "ОГРАНИЧЕНИЕ ПО СРОКУ,", MONO, 27, 540, 262, ac(TXT, 245 * p), p, "ma", 14)
        slam(cv, "А НЕ ПО КОЛИЧЕСТВУ", MONO, 27, 540, 302, ac(TXT, 245 * p), p, "ma", 14)
    if l > .45:
        p = c01((l - .45) / .40)
        cx, cy, r = 540, 590, 205
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        dl.arc([cx - r, cy - r, cx + r, cy + r], -90, 270, fill=(30, 26, 14, 255), width=14)
        dl.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * eo(p), fill=ac(WARN, 252), width=14)
        cv.alpha_composite(lay)
        slam(cv, "ДО", MONO, 36, 540, 508, ac(DIM, 250 * p), p, "ma", 12)
        slam(cv, "15", COND, 172, 540, 546, ac(WARN, 255 * p), p, "ma", 34)
        slam(cv, "НОЯБРЯ", RUSSO, 56, 540, 788, ac(TXT, 250 * p), p, "ma", 20)
    if l > 1.70:
        p = c01((l - 1.70) / .32)
        plate(cv, [80, 878, 1000, 1016], (36, 26, 6), int(246 * p), WARN, int(228 * p), 3, WARN)
        slam(cv, "СРОК ПРОДЛЁН", MONO, 34, 540, 900, ac(WARN, 252 * p), p, "ma", 16)
        slam(cv, "ПОСЛЕ 15 НОЯБРЯ ЦЕНА ПО АКЦИИ НЕ ДЕЙСТВУЕТ",
             MONO, 22, 540, 952, ac(TXT, 242 * p), p, "ma", 10, maxw=880)
    if l > 2.35:
        p = c01((l - 2.35) / .30)
        _pair(cv, 1330, 1240, dark=0.28, zoom=1.10, col=(12, 13, 10))
        plate(cv, [232, 1076, 848, 1158], (9, 10, 8), int(246 * p), OLV, int(215 * p), 2, OLV)
        slam(cv, "ЦЕНА 600 000 ₽ ЗА ДВЕ", MONO, 27, 540, 1096, ac(OLV, 252 * p), p, "ma", 12)
    if l > 3.05:
        p = c01((l - 3.05) / .28)
        chips_row(d, 1570, [("ДО 15 НОЯБРЯ", WARN, True)], int(255 * p), size=26)
    tick_marks(d, WARN)


def s_outro(cv, d, t, l):
    B.outro_card(cv, d, l, OLV, "КОМПЛЕКТ ИЗ ДВУХ СТАНЦИЙ",
                 "600 000 ₽ ЗА ДВЕ · 300 000 ₽ ЗА КАЖДУЮ", True, "pair_clean", 380)


FN = {"hook": s_hook, "price": s_price, "promo": s_promo, "outro": s_outro}
