# -*- coding: utf-8 -*-
"""Ролик 30 с: основной анонс радио «В ОКОПЕ»."""
import base as B
import lib_scenes as L
from base import (AMBER, COND, DIM, MONO, OLV, RUSSO, TXT, W, ac, bg_photo, chips_row, c01,
                  eo, logo_mark, plate, shade, slam, stage, tick_marks)

VO = "a30.mp3"
LEAD = 0.38
TITLE = "РАДИО «В ОКОПЕ» · 30 СЕКУНД"

SCENES_FRAC = [("front", 0.00), ("road", 0.07), ("home", 0.14), ("wave", 0.20),
               ("logo", 0.245), ("clock", 0.29), ("songs", 0.38), ("ours", 0.49),
               ("brief", 0.57), ("allours", 0.75), ("logo2", 0.78),
               ("platforms", 0.85), ("request", 0.90), ("end", 0.97)]

FX = [("impact_deep", 0.00, 0.55), ("whoosh_transition", 0.14, 0.30),
      ("cut_tick", 0.20, 0.32), ("riser_tension", 0.29, 0.24),
      ("whoosh_transition", 0.49, 0.30), ("impact_bright", 0.57, 0.34),
      ("cut_tick", 0.75, 0.30), ("riser_tension", 0.85, 0.26),
      ("logo_sting", 0.97, 0.46)]


def s_front(cv, d, t, l):
    L.place(cv, d, t, l, "bg_trench", "НА ПЕРЕДКЕ", "ГДЕ БЫ ТЫ НИ БЫЛ", "01", OLV, 2.2)


def s_road(cv, d, t, l):
    L.place(cv, d, t, l, "bg_cab", "В ДОРОГЕ", "ГДЕ БЫ ТЫ НИ БЫЛ", "02", OLV, 2.2)


def s_home(cv, d, t, l):
    L.place(cv, d, t, l, "bg_kitchen", "ДОМА", "ГДЕ БЫ ТЫ НИ БЫЛ", "03", OLV, 2.0)


def s_wave(cv, d, t, l):
    L.wave(cv, d, t, l, "r30", "СВОЯ ВОЛНА", "ЭТО ТВОЙ ЭФИР")


def s_logo(cv, d, t, l):
    L.logo_scene(cv, d, t, l, "r30", "РАДИО")


def s_clock(cv, d, t, l):
    """24/7 без остановок и без повторов."""
    stage(cv, OLV, glow=.7, t=t)
    bg_photo(cv, "bg_tower", zoom=1.14, dark=0.80)
    shade(cv, 140, 700, 120, 0)
    p = c01(l / .22)
    slam(cv, "24 / 7", COND, 200, 540, 300, ac(TXT, 255), p, "ma", 40, maxw=820)
    if l > .14:
        q = c01((l - .14) / .26)
        plate(cv, [96, 500, 984, 660], (7, 8, 6), int(226 * q), OLV, int(190 * q), 2, OLV)
        slam(cv, "БЕЗ ОСТАНОВОК", RUSSO, 56, 540, 522, ac(TXT, 252 * q), q, "ma", 20, maxw=860)
        slam(cv, "И БЕЗ ПОВТОРОВ", RUSSO, 56, 540, 596, ac(OLV, 252 * q), q, "ma", 20, maxw=860)
    if l > .40:
        q = c01((l - .40) / .30)
        d.rectangle([90, 760, W - 90, 764], fill=ac((60, 66, 44), 210))
        d.rectangle([90, 760, 90 + int((W - 180) * eo(q)), 764], fill=ac(OLV, 240))
        for i in range(25):
            x = 90 + (W - 180) * i / 24
            hh = 12 if i % 6 else 24
            d.rectangle([x - 1, 760 - hh // 2, x + 1, 760 + hh // 2], fill=ac(OLV, 165))
        L.onair(cv, 540, 900, t, q, "В ЭФИРЕ КРУГЛЫЕ СУТКИ")
    if l > .70:
        q = c01((l - .70) / .28)
        chips_row(d, 1040, [("КАЖДЫЙ ЧАС · КАЖДЫЙ ДЕНЬ", OLV, False)], int(245 * q), size=24)
    tick_marks(d)


def s_songs(cv, d, t, l):
    L.songs(cv, d, t, l, "r30", "СТАРЫЕ И НОВЫЕ", "ПЕСНИ",
            ["О ВОЙНЕ", "О ПОБЕДЕ", "О НАШИХ РЕБЯТАХ"])


def s_ours(cv, d, t, l):
    """Те, что поют в окопах. Те, что поют для своих."""
    stage(cv, AMBER, glow=.7, t=t)
    bg_photo(cv, "bg_trench", zoom=1.16, dy=int(-20 * l), dark=0.72)
    p = c01(l / .20)
    slam(cv, "ТЕ, ЧТО ПОЮТ", RUSSO, 66, 540, 640, ac(TXT, 255), p, "ma", 24, maxw=940)
    if l > .10:
        slam(cv, "В ОКОПАХ", RUSSO, 100, 540, 740, ac(AMBER, 255), c01((l - .10) / .24), "ma", 30, maxw=940)
    if l > .38:
        q = c01((l - .38) / .26)
        plate(cv, [120, 880, 960, 976], (9, 9, 7), int(238 * q), AMBER, int(200 * q), 2, AMBER)
        slam(cv, "ТЕ, ЧТО ПОЮТ ДЛЯ СВОИХ", MONO, 30, 540, 906, ac(TXT, 248 * q), q, "ma", 14)
    tick_marks(d, AMBER)


def s_brief(cv, d, t, l):
    L.brief(cv, d, t, l, "r30")


def s_allours(cv, d, t, l):
    L.all_ours(cv, d, t, l, "r30")


def s_logo2(cv, d, t, l):
    stage(cv, OLV, glow=1.0, t=t)
    B.vinyl_ring(cv, 540, 860, 440, t, OLV, 1.0)
    logo_mark(cv, 540, 800, 1.0, c01(l / .16), OLV, 1.0)
    if l > .20:
        q = c01((l - .20) / .26)
        slam(cv, "ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ", MONO, 30, 540, 1080, ac(OLV, 250 * q), q, "ma", 14)
    tick_marks(d)


def s_platforms(cv, d, t, l):
    L.platforms(cv, d, t, l)


def s_request(cv, d, t, l):
    L.request(cv, d, t, l, "r30")


def s_end(cv, d, t, l):
    """Финальная плашка — короткая, лого и адреса."""
    stage(cv, OLV, glow=.7, t=t)
    logo_mark(cv, 540, 640, .86, c01(l / .12), OLV, 1.0)
    if l > .10:
        q = c01((l - .10) / .24)
        slam(cv, "МЫ ТАМ, ГДЕ НАШИ", RUSSO, 44, 540, 870, ac(TXT, 245 * q), q, "ma", 18, maxw=900)
    if l > .22:
        q = c01((l - .22) / .24)
        slam(cv, "t.me/vokope_ru  ·  vk.com/vokope_rus", MONO, 24, 540, 942, ac(DIM, 235 * q), q, "ma", 10)
    tick_marks(d)


FN = {"front": s_front, "road": s_road, "home": s_home, "wave": s_wave, "logo": s_logo,
      "clock": s_clock, "songs": s_songs, "ours": s_ours, "brief": s_brief,
      "allours": s_allours, "logo2": s_logo2, "platforms": s_platforms,
      "request": s_request, "end": s_end}
