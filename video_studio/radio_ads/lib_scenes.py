# -*- coding: utf-8 -*-
"""Общие сцены анонсов: места, волна, эфир, рубрики, площадки."""
import math

from PIL import Image, ImageDraw

import base as B
from base import (AMBER, COND, DIM, H, KHAKI, MONO, OLV, OLV2, RED, RUSSO, TXT, W, ac,
                  bg_photo, chip, chips_row, cl, c01, dial, eo, eq_bars, interference,
                  logo_mark, onair, plate, shade, slam, stage, tick_marks, waveform)


def place(cv, d, t, l, name, word, label, num, accent=OLV, hold=2.4):
    """Кадр-место: фото + крупное слово."""
    z = 1.045 + 0.055 * (l / hold)
    bg_photo(cv, name, zoom=z, dx=0, dy=int(-10 * l), dark=0.30)
    shade(cv, 0, 560, 40, 235)
    shade(cv, H - 760, H - 120, 0, 225)
    d.text((70, 150), num, font=B.F(MONO, 30), fill=ac(accent, 240))
    d.rectangle([70, 196, 170, 201], fill=ac(accent, 220))
    slam(cv, label, MONO, 30, 70, 214, ac(DIM, 240), c01((l - .02) / .22), "lt", 12)
    p = c01((l - .05) / .30)
    slam(cv, word, RUSSO, 104, 540, 1230, ac(TXT, 255), p, "ma", 30, maxw=980)
    if l > .30:
        q = c01((l - .30) / .30)
        d.rectangle([70, 1352, 70 + int(940 * eo(q)), 1359], fill=ac(accent, 210))
    interference(cv, t, 0.25, seed=3)


def wave(cv, d, t, l, tag, head="СВОЯ ВОЛНА", sub="ЭТО ТВОЙ ЭФИР"):
    """Эквалайзер по реальному спектру + заголовок."""
    stage(cv, OLV, glow=.55, t=t)
    spec = B.spectrum(tag)
    frame = spec[min(len(spec) - 1, int(t * B.FPS))]
    p = c01(l / .26)
    slam(cv, head, RUSSO, 96, 540, 250, ac(TXT, 255), p, "ma", 32, maxw=940)
    if l > .10:
        q = c01((l - .10) / .26)
        slam(cv, sub, MONO, 28, 540, 372, ac(OLV, 250 * q), q, "ma", 14)
    eq_bars(cv, 70, 1040, W - 140, 240, 24, frame, OLV, 246, True, 6, 1.0)
    if l > .16:
        q = c01((l - .16) / .28)
        dial(cv, 540, 1330, 112, (math.sin(t * 1.5) * .5 + .5), q, AMBER)
    if l > .34:
        q = c01((l - .34) / .26)
        chips_row(d, 1500, [("24 / 7", OLV, True), ("БЕЗ ОСТАНОВОК", OLV, False)], int(250 * q), size=25)
    tick_marks(d)


def logo_scene(cv, d, t, l, tag, kicker="РАДИО"):
    stage(cv, OLV, glow=.9, t=t)
    B.vinyl_ring(cv, 540, 900, 420, t, OLV, 1.0)
    p = c01((l - .02) / .30)
    if l > 0:
        slam(cv, kicker, MONO, 34, 540, 300, ac(OLV, 250 * p), p, "ma", 16)
    logo_mark(cv, 540, 800, 1.0, c01((l - .06) / .34), OLV, 1.0)
    if l > .55:
        q = c01((l - .55) / .30)
        slam(cv, "КРУГЛЫЕ СУТКИ", RUSSO, 44, 540, 1080, ac(TXT, 245 * q), q, "ma", 18, maxw=900)
        slam(cv, "СТАРЫЕ И НОВЫЕ ПЕСНИ О ВОЙНЕ, О ПОБЕДЕ, О НАШИХ",
             MONO, 22, 540, 1150, ac(DIM, 235 * q), q, "ma", 10, maxw=940)
    interference(cv, t, .18, seed=5)


def songs(cv, d, t, l, tag, head="СТАРЫЕ И НОВЫЕ", head2="ПЕСНИ", items=None):
    stage(cv, AMBER, glow=.5, t=t)
    bg_photo(cv, "bg_kitchen", zoom=1.12, dy=int(-14 * l), dark=0.62)
    p = c01(l / .26)
    slam(cv, head, RUSSO, 76, 540, 240, ac(TXT, 255), p, "ma", 28, maxw=960)
    if l > .06:
        slam(cv, head2, RUSSO, 62, 540, 340, ac(AMBER, 255), c01((l - .06) / .26), "ma", 24, maxw=960)
    items = items or ["О ВОЙНЕ", "О ПОБЕДЕ", "О НАШИХ"]
    y = 540
    for i, s in enumerate(items):
        q = c01((l - .26 - i * .18) / .26)
        if q <= 0:
            y += 112
            continue
        plate(cv, [150, y, 930, y + 92], (9, 9, 7), int(232 * q), AMBER, int(190 * q), 2)
        d.rectangle([150, y, 158, y + 92], fill=ac(AMBER, int(245 * q)))
        slam(cv, s, RUSSO, 44, 540, y + 18, ac(TXT, 250 * q), q, "ma", 16, maxw=740)
        y += 112
    if l > .70:
        q = c01((l - .70) / .28)
        spec = B.spectrum(tag)
        fr = spec[min(len(spec) - 1, int(t * B.FPS))]
        eq_bars(cv, 120, 1010, W - 240, 110, 22, fr, AMBER, int(230 * q), True, 7, .9)
        chips_row(d, 1150, [("БЕЗ ОСТАНОВОК", AMBER, False)], int(240 * q), size=24)
    tick_marks(d, AMBER)


def nostop(cv, d, t, l, tag, head="БЕЗ ОСТАНОВОК", sub="ВКЛЮЧАЙ И СЛУШАЙ"):
    stage(cv, OLV, glow=.6, t=t)
    spec = B.spectrum(tag)
    fr = spec[min(len(spec) - 1, int(t * B.FPS))]
    p = c01(l / .24)
    slam(cv, head, RUSSO, 94, 540, 360, ac(TXT, 255), p, "ma", 30, maxw=960)
    if l > .10:
        slam(cv, sub, MONO, 32, 540, 500, ac(OLV, 250 * c01((l - .10) / .26)),
             c01((l - .10) / .26), "ma", 16)
    # круглые сутки: полоса 24 часа
    if l > .20:
        q = c01((l - .20) / .40)
        y = 760
        d.rectangle([80, y, W - 80, y + 4], fill=ac((60, 66, 44), 200))
        d.rectangle([80, y, 80 + int((W - 160) * eo(q)), y + 4], fill=ac(OLV, 240))
        for i in range(25):
            x = 80 + (W - 160) * i / 24
            hh = 14 if i % 6 else 26
            d.rectangle([x - 1, y - hh // 2, x + 1, y + hh // 2], fill=ac(OLV, 170))
        d.text((80, y + 26), "00:00", font=B.F(MONO, 20), fill=ac(DIM, 220))
        d.text((W - 80, y + 26), "24:00", font=B.F(MONO, 20), fill=ac(DIM, 220), anchor="ra")
        onair(cv, 540, 900, t, q)
    eq_bars(cv, 90, 1120, W - 180, 220, 24, fr, OLV, 235, True, 6, 1.0)
    if l > .55:
        q = c01((l - .55) / .30)
        chips_row(d, 1400, [("ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ", OLV, True)], int(250 * q), size=25)
    tick_marks(d)


def brief(cv, d, t, l, tag):
    """Что мы делаем для фронта: связь, РЭБ, тепловизоры, тактика."""
    stage(cv, OLV, glow=.45, t=t)
    p = c01(l / .22)
    slam(cv, "КАЖДЫЕ ПОЛЧАСА", RUSSO, 72, 540, 210, ac(TXT, 255), p, "ma", 26, maxw=960)
    if l > .08:
        q = c01((l - .08) / .24)
        slam(cv, "КОРОТКО О ТОМ, ЧТО МЫ ДЕЛАЕМ ДЛЯ ФРОНТА", MONO, 23, 540, 300,
             ac(DIM, 240 * q), q, "ma", 10, maxw=920)
    items = [("СВЯЗЬ", OLV), ("РЭБ", OLV), ("ТЕПЛОВИЗОРЫ", AMBER), ("ТАКТИКА", AMBER)]
    box_w, box_h = 424, 232
    cy0, gap = 560, 264
    for i, (s, col) in enumerate(items):
        q = c01((l - .20 - i * .12) / .24)
        if q <= 0:
            continue
        cx = 296 if i % 2 == 0 else 784
        cy = cy0 if i < 2 else cy0 + gap
        plate(cv, [cx - box_w // 2, cy - box_h // 2, cx + box_w // 2, cy + box_h // 2],
              (9, 10, 8), int(240 * q), col, int(205 * q), 3, col)
        size = 60 if len(s) < 9 else 44
        slam(cv, s, COND, size, cx, cy - size // 2 - 10, ac(col, 252 * q), q, "ma", 14, maxw=box_w - 44)
    if l > 1.00:
        q = c01((l - 1.00) / .26)
        onair(cv, 540, 1080, t, q, "КАЖДЫЕ 30 МИНУТ")
    if l > 1.25:
        q = c01((l - 1.25) / .28)
        spec = B.spectrum(tag)
        fr = spec[min(len(spec) - 1, int(t * B.FPS))]
        eq_bars(cv, 110, 1250, W - 220, 190, 22, fr, OLV, int(225 * q), True, 7, .95)
        chips_row(d, 1470, [("ВСЁ ДЛЯ СВОИХ", OLV, True)], int(245 * q), size=25)
    tick_marks(d)


def all_ours(cv, d, t, l, tag, head="ВСЁ ДЛЯ СВОИХ"):
    stage(cv, OLV, glow=1.0, t=t)
    bg_photo(cv, "bg_tower", zoom=1.10, dy=int(16 * l), dark=0.66)
    p = c01(l / .26)
    slam(cv, head, RUSSO, 96, 540, 760, ac(TXT, 255), p, "ma", 32, maxw=980)
    if l > .18:
        q = c01((l - .18) / .30)
        d.rectangle([540 - int(300 * eo(q)), 900, 540 + int(300 * eo(q)), 907], fill=ac(OLV, 220))
        slam(cv, "ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ", MONO, 30, 540, 940, ac(OLV, 245 * q), q, "ma", 16)
    tick_marks(d)


def platforms(cv, d, t, l):
    stage(cv, OLV, glow=.5, t=t)
    p = c01(l / .24)
    slam(cv, "СЛУШАЙ", RUSSO, 84, 540, 300, ac(TXT, 255), p, "ma", 28, maxw=900)
    p2 = c01((l - .10) / .28)
    if p2 > 0:
        plate(cv, [110, 430, 970, 610], (8, 10, 12), int(240 * p2), (95, 150, 220), int(210 * p2), 3)
        slam(cv, "ВКОНТАКТЕ", RUSSO, 56, 540, 470, ac(TXT, 250 * p2), p2, "ma", 18)
        slam(cv, "vk.com/vokope_rus", MONO, 30, 540, 546, ac((150, 190, 240), 245 * p2), p2, "ma", 12)
    p3 = c01((l - .34) / .28)
    if p3 > 0:
        plate(cv, [110, 660, 970, 840], (8, 10, 12), int(240 * p3), (110, 175, 235), int(210 * p3), 3)
        slam(cv, "TELEGRAM", RUSSO, 56, 540, 700, ac(TXT, 250 * p3), p3, "ma", 18)
        slam(cv, "t.me/vokope_ru", MONO, 30, 540, 776, ac((170, 205, 245), 245 * p3), p3, "ma", 12)
    if l > .70:
        q = c01((l - .70) / .30)
        chips_row(d, 960, [("КРУГЛЫЕ СУТКИ · БЕЗ ОСТАНОВОК", OLV, True)], int(250 * q), size=24)
    tick_marks(d)


def request(cv, d, t, l, tag):
    stage(cv, AMBER, glow=.6, t=t)
    bg_photo(cv, "bg_trench", zoom=1.14, dy=int(-12 * l), dark=0.70)
    p = c01(l / .24)
    slam(cv, "ПРИСЫЛАЙ", RUSSO, 78, 540, 260, ac(TXT, 255), p, "ma", 28, maxw=940)
    if l > .08:
        slam(cv, "СВОЮ ПЕСНЮ", RUSSO, 96, 540, 356, ac(AMBER, 255), c01((l - .08) / .26), "ma", 30, maxw=960)
    if l > .28:
        q = c01((l - .28) / .28)
        plate(cv, [150, 520, 930, 616], (9, 9, 7), int(238 * q), AMBER, int(205 * q), 2, AMBER)
        slam(cv, "В ПРЕДЛОЖКУ", MONO, 40, 540, 546, ac(TXT, 250 * q), q, "ma", 16)
    if l > .52:
        q = c01((l - .52) / .30)
        slam(cv, "МОЖЕТ, ИМЕННО ОНА", MONO, 28, 540, 700, ac(TXT, 245 * q), q, "ma", 14)
        slam(cv, "ПРОЗВУЧИТ СЛЕДУЮЩЕЙ", MONO, 28, 540, 748, ac(AMBER, 250 * q), q, "ma", 14)
    if l > .82:
        q = c01((l - .82) / .30)
        chips_row(d, 900, [("ПРЕДЛОЖКА В КАНАЛЕ", AMBER, True)], int(248 * q), size=26)
    tick_marks(d, AMBER)


def final_card(cv, d, t, l, tag):
    B.end_card(cv, d, l, OLV, tag)
