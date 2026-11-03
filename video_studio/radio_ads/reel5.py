# -*- coding: utf-8 -*-
"""Отбивка 5 с: «Радио „В ОКОПЕ“. Двадцать четыре на семь. Мы там, где наши.»"""
from PIL import Image, ImageDraw

import base as B
import lib_scenes as L
from base import AMBER, COND, DIM, H, MONO, OLV, RUSSO, TXT, W, ac, bg_photo, chips_row, cl, c01, \
    eo, interference, logo_mark, onair, plate, shade, slam, stage, tick_marks

VO = "a5.mp3"
LEAD = 0.22
TITLE = "РАДИО «В ОКОПЕ» · ОТБИВКА"

# доли от длительности реплики — задаются по смыслу фраз
SCENES_FRAC = [("boom", 0.00), ("logo", 0.28), ("slogan", 0.58), ("end", 0.84)]
FX = [("impact_deep", 0.00, 0.62), ("riser_tension", 0.30, 0.30),
      ("logo_sting", 0.58, 0.50), ("cut_tick", 0.84, 0.34)]


def s_boom(cv, d, t, l):
    """Удар: помехи, разряд, знак собирается из шума."""
    stage(cv, OLV, glow=1.2, t=t)
    bg_photo(cv, "bg_tower", zoom=1.16 + 0.03 * l, dark=0.55)
    interference(cv, t, 1.0, seed=1)
    p = c01(l / .12)
    lx = 540 + int((1 - eo(p)) * 240)
    logo_mark(cv, lx, 880, 1.05, c01(l / .16), OLV, 1.0)
    if l > .28:
        q = c01((l - .28) / .22)
        onair(cv, 540, 1120, t, q)
    tick_marks(d)


def s_logo(cv, d, t, l):
    """Крупный знак + «24/7»."""
    stage(cv, OLV, glow=.8, t=t)
    bg_photo(cv, "bg_cab", zoom=1.18, dark=0.74)
    B.vinyl_ring(cv, 540, 900, 430, t, OLV, 1.0)
    logo_mark(cv, 540, 760, 1.0, c01(l / .16), OLV, 1.0)
    if l > .22:
        q = c01((l - .22) / .26)
        slam(cv, "24 / 7", COND, 150, 540, 1040, ac(TXT, 250 * q), q, "ma", 30, maxw=760)
    if l > .44:
        q = c01((l - .44) / .30)
        chips_row(d, 1240, [("БЕЗ ОСТАНОВОК", OLV, False)], int(245 * q), size=24)
    tick_marks(d)


def s_slogan(cv, d, t, l):
    stage(cv, OLV, glow=1.1, t=t)
    bg_photo(cv, "bg_trench", zoom=1.10, dy=int(-18 * l), dark=0.66)
    p = c01(l / .20)
    slam(cv, "МЫ ТАМ,", RUSSO, 108, 540, 700, ac(TXT, 255), p, "ma", 32, maxw=960)
    if l > .10:
        slam(cv, "ГДЕ НАШИ", RUSSO, 108, 540, 826, ac(OLV, 255), c01((l - .10) / .24), "ma", 32, maxw=960)
    if l > .34:
        q = c01((l - .34) / .26)
        d.rectangle([540 - int(280 * eo(q)), 966, 540 + int(280 * eo(q)), 973], fill=ac(OLV, 225))
    tick_marks(d)


def s_end(cv, d, t, l):
    """Финальный кадр: знак, слоган, эквалайзер эфира."""
    stage(cv, OLV, glow=.8, t=t)
    logo_mark(cv, 540, 620, .92, c01(l / .14), OLV, 1.0)
    if l > .10:
        q = c01((l - .10) / .24)
        slam(cv, "МЫ ТАМ, ГДЕ НАШИ", RUSSO, 48, 540, 990, ac(TXT, 246 * q), q, "ma", 18, maxw=900)
    if l > .22:
        q = c01((l - .22) / .24)
        slam(cv, "t.me/vokope_ru  ·  vk.com/vokope_rus", MONO, 24, 540, 1072, ac(DIM, 236 * q), q, "ma", 10)
    if l > .34:
        q = c01((l - .34) / .26)
        chips_row(d, 1150, [("ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ", OLV, True)], int(250 * q), size=23)
    tick_marks(d)


FN = {"boom": s_boom, "logo": s_logo, "slogan": s_slogan, "end": s_end}
