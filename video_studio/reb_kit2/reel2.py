# -*- coding: utf-8 -*-
"""Ролик 2 «ЧТО УМЕЕТ» — характеристики и применения. Комплект РЭБ «Капюшон» К-8М.

Тайминги сцен — из timeline_r2.json (пишет build_audio.py).
"""
import base as B
from base import (COND, DIM, KHAKI, MONO, OLV, OLV2, RUSSO, TXT, W, WARN, ac, chip,
                  chips_row, cl, c01, cover, dome_scheme, eo, grid, plate, rings, slam,
                  stage, strip, tick_marks)

TITLE = "РЭБ «КАПЮШОН» К-8М // ХАРАКТЕРИСТИКИ"
TICKER = "600 000 ₽ ЗА ДВЕ · АКЦИЯ ДО 15 НОЯБРЯ"


def ticker(cv, p, col=WARN):
    """Нижняя строка с ценой и сроком — держим в каждом кадре."""
    if p <= 0:
        return
    plate(cv, [56, 1630, W - 56, 1706], (36, 26, 6), int(244 * p), col, int(230 * p), 3, col)
    slam(cv, TICKER, MONO, 25, 540, 1652, ac(col, 252 * p), p, "ma", 12)


def s_specs1(cv, d, t, l):
    stage(cv, OLV, glow=.45, t=t)
    grid(d, 12)
    box = strip(cv, "left_clean", 1520, 700, zoom=1.06, dark=0.50, alpha=230)
    cover(cv, box, 610, (7, 8, 6))
    slam(cv, "ХАРАКТЕРИСТИКИ", RUSSO, 66, 540, 150, ac(TXT, 255), c01((l - .03) / .22), "ma", 28, maxw=980)
    rows = [("8", "НЕЗАВИСИМЫХ КАНАЛОВ", OLV),
            ("400–5900", "МГЦ, ДИАПАЗОН", KHAKI),
            ("20 ВТ", "НА КАЖДЫЙ КАНАЛ", OLV),
            ("360°", "КУПОЛЬНАЯ ЗАЩИТА", WARN)]
    y = 262
    for i, (big, small, col) in enumerate(rows):
        p = c01((l - .26 - i * .48) / .28)
        if p <= 0:
            y += 164
            continue
        plate(cv, [92, y, 988, y + 148], (10, 11, 9), int(238 * p), col, int(170 * p), 2, col)
        slam(cv, big, COND, 96 if big in ("8", "20 ВТ", "360°") else 84, 124, y + 6, ac(col, 255 * p), p, "lt", 18, maxw=600)
        slam(cv, small, MONO, 26, 124, y + 104, ac(DIM, 242 * p), p, "lt", 12, maxw=600)
        y += 172
    if l > 2.20:
        p = c01((l - 2.20) / .38)
        dome_scheme(cv, 540, 1140, 176, p, OLV)
        chip(d, 426, 1304, "СХЕМА КУПОЛА 360°", OLV2, 22, 46, int(230 * p))
    if l > 3.05:
        ticker(cv, c01((l - 3.05) / .32))
    tick_marks(d)


def s_specs2(cv, d, t, l):
    stage(cv, OLV, glow=.45, t=t)
    grid(d, 12)
    slam(cv, "УСТАНОВКА", RUSSO, 74, 540, 150, ac(TXT, 255), c01((l - .03) / .22), "ma", 30, maxw=900)
    if l > .16:
        p = c01((l - .16) / .48)
        rings(cv, 540, 470, 300, p, OLV)
        dome_scheme(cv, 540, 470, 138, c01((l - .16) / .68), KHAKI)
        chip(d, 424, 616, "ЗОНА ПОДАВЛЕНИЯ", OLV2, 22, 46, int(232 * p))
        if l > .60:
            q = c01((l - .60) / .26)
            plate(cv, [300, 700, 780, 806], (9, 10, 8), int(246 * q), OLV, int(215 * q), 2, OLV)
            slam(cv, "ДО 300 М", COND, 74, 540, 712, ac(OLV, 252 * q), q, "ma", 18)
    rows = [("МАГНИТЫ", "крепление на крышу"),
            ("12 / 24 В", "питание от бортовой сети"),
            ("ВЫНОСНОЙ ПУЛЬТ", "управление из кабины")]
    y = 880
    for i, (big, small) in enumerate(rows):
        p = c01((l - 1.16 - i * .52) / .30)
        if p <= 0:
            y += 168
            continue
        d.rectangle([92, y + 10, 92 + int(8 * p), y + 120], fill=ac(OLV, int(234 * p)))
        slam(cv, big, COND, 62, 128, y, ac(TXT, 252 * p), p, "lt", 18, maxw=780)
        slam(cv, small, MONO, 25, 128, y + 74, ac(DIM, 238 * p), p, "lt", 12, maxw=780)
        y += 168
    if l > 3.05:
        ticker(cv, c01((l - 3.05) / .32))
    tick_marks(d)


def s_use(cv, d, t, l):
    stage(cv, OLV, glow=.4, t=t)
    grid(d, 12)
    box = strip(cv, "pair_clean", 1540, 1080, zoom=1.0, dark=0.55)
    cover(cv, box, 1280, (7, 8, 6))
    slam(cv, "ДЛЯ ЗАЩИТЫ", RUSSO, 78, 540, 150, ac(TXT, 255), c01((l - .03) / .22), "ma", 30, maxw=900)
    items = ["АВТОМОБИЛЕЙ СНАБЖЕНИЯ", "ГУМАНИТАРНЫХ КОНВОЕВ", "ГРУЗОПЕРЕВОЗОК",
             "СЛУЖЕБНОГО ТРАНСПОРТА", "КОЛОНН СОПРОВОЖДЕНИЯ", "БЕНЗОВОЗОВ",
             "ТЕХНИКИ ОБЕСПЕЧЕНИЯ"]
    y = 292
    for i, s in enumerate(items):
        p = c01((l - .22 - i * .23) / .24)
        if p <= 0:
            y += 74
            continue
        d.rectangle([132, y + 14, 132 + int(14 * eo(p)), y + 48], fill=ac(OLV, int(238 * p)))
        slam(cv, s, MONO, 32, 168, y + 8, ac(TXT, 246 * p), p, "lt", 12, maxw=800)
        y += 76
    if l > 1.55:
        p = c01((l - 1.55) / .30)
        plate(cv, [70, 826, 1010, 936], (9, 10, 8), int(242 * p), OLV, int(200 * p), 2, OLV)
        slam(cv, "ДВЕ СТАНЦИИ —", MONO, 27, 540, 844, ac(TXT, 248 * p), p, "ma", 12)
        slam(cv, "ЗАЩИТА КОЛОННЫ С ДВУХ СТОРОН", MONO, 27, 540, 886, ac(OLV, 250 * p), p, "ma", 12)
    if l > 1.95:
        ticker(cv, c01((l - 1.95) / .32))
    tick_marks(d)


def s_outro(cv, d, t, l):
    B.outro_card(cv, d, l, OLV, "КОМПЛЕКТ ИЗ ДВУХ СТАНЦИЙ",
                 "8 КАНАЛОВ · 400–5900 МГЦ · ДО 300 М", True, "pair_clean", 380)


FN = {"specs1": s_specs1, "specs2": s_specs2, "use": s_use, "outro": s_outro}
