# -*- coding: utf-8 -*-
"""Сцены «СВОДКИ». Все параметры приходят из script.json — движок не знает текста."""
from PIL import Image, ImageDraw

import gfx as G
from gfx import (DIM, GOLD, GOLD2, H, MONO, OLV, RED, RUSSO, COND, TXT, W, ac, chip, chips_row,
                 counter, plate, slam, subtitle, text)


def _head(cv, s, p, y=150, size=64, col=TXT):
    if s:
        slam(cv, s, RUSSO, size, W // 2, y, ac(col, 255), p, "ma", maxw=W - 200)


def s_title(cv, d, t, l, sc):
    p = G.c01(l / 0.35)
    text(cv, sc.get("kicker", "ЕЖЕДНЕВНАЯ ПЕРЕДАЧА"), MONO, 20, W // 2, 150,
         ac(GOLD, 250 * p), p, "ma")
    slam(cv, sc.get("title", "СВОДКА"), RUSSO, 132, W // 2, 186, ac(TXT, 255), p, "ma", maxw=W - 160)
    if l > .22:
        q = G.c01((l - .22) / .30)
        b = sc.get("badge", "")
        if b:
            f = G.F(MONO, 22)
            wd = int(f.getlength(b)) + 56
            plate(cv, [W // 2 - wd // 2, 348, W // 2 + wd // 2, 398], (10, 14, 10),
                  int(235 * q), GOLD, int(200 * q), 2)
            text(cv, b, MONO, 22, W // 2, 356, ac(GOLD, 250 * q), q, "mt")
    if l > .40:
        q = G.c01((l - .40) / .30)
        text(cv, sc.get("date", ""), RUSSO, 44, W // 2, 424, ac(TXT, 250 * q), q, "ma")
    subtitle(cv, sc.get("sub", ""), G.c01((l - .55) / .25))


def s_flow(cv, d, t, l, sc):
    """Порядок передачи: цепочка шагов."""
    _head(cv, sc.get("head", ""), G.c01(l / .26))
    items = sc.get("items", [])
    y = 300
    step = 54 if len(items) > 4 else 62
    for i, it in enumerate(items):
        p = G.c01((l - .22 - i * .12) / .26)
        if p <= 0:
            continue
        yy = y + i * step
        num = "%02d" % (i + 1)
        text(cv, num, MONO, 20, 150, yy + 10, ac(GOLD, 240 * p), p)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle([196, yy + 22, 196 + int(14 * G.eo(p)), yy + 25],
                                      fill=ac(GOLD, 220))
        cv.alpha_composite(lay)
        text(cv, it, COND, 32 if step < 60 else 34, 226, yy, ac(TXT, 250 * p), p, maxw=W - 360)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .5) / .3))


def s_cards(cv, d, t, l, sc):
    """Что берём в сводку — плитки."""
    _head(cv, sc.get("head", ""), G.c01(l / .26))
    items = sc.get("items", [])
    cols = 3 if len(items) > 4 else 2
    cw, ch = 348, 84
    gap = 16
    total_w = cols * cw + (cols - 1) * gap
    x0 = (W - total_w) // 2
    y0 = 288
    for i, it in enumerate(items):
        p = G.c01((l - .20 - i * .09) / .24)
        if p <= 0:
            continue
        cx = x0 + (i % cols) * (cw + gap)
        cy = y0 + (i // cols) * (ch + gap)
        plate(cv, [cx, cy, cx + cw, cy + ch], (10, 14, 10), int(232 * p), GOLD, int(170 * p), 2, GOLD)
        text(cv, it, COND, 26 if len(it) > 18 else 30, cx + cw // 2, cy + 22,
             ac(TXT, 250 * p), p, "mt", maxw=cw - 34)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .55) / .3))


def s_rules(cv, d, t, l, sc):
    """Запреты: список с крестиками."""
    _head(cv, sc.get("head", ""), G.c01(l / .26), size=58)
    items = sc.get("items", [])
    y = 296
    for i, it in enumerate(items):
        p = G.c01((l - .18 - i * .16) / .26)
        if p <= 0:
            continue
        yy = y + i * 74
        plate(cv, [130, yy, W - 130, yy + 62], (12, 10, 9), int(228 * p), RED, int(150 * p), 2)
        # крестик — рисуем линиями: глифа ✕ в наборе нет
        cr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cr)
        k = 9 * G.eo(p)
        cx, cy = 172, yy + 31
        cd.line([(cx - k, cy - k), (cx + k, cy + k)], fill=ac(RED, 245), width=4)
        cd.line([(cx - k, cy + k), (cx + k, cy - k)], fill=ac(RED, 245), width=4)
        cv.alpha_composite(cr)
        text(cv, it, COND, 34, 208, yy + 10, ac(TXT, 250 * p), p, maxw=W - 380)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .6) / .3))


def s_rule(cv, d, t, l, sc):
    """Одно жёсткое правило крупно."""
    p = G.c01(l / .30)
    text(cv, sc.get("kicker", "ЖЁСТКОЕ ПРАВИЛО"), MONO, 18, W // 2, 200, ac(RED, 240 * p), p, "ma")
    _head(cv, sc.get("head", ""), G.c01((l - .10) / .30), y=238, size=60)
    if l > .30:
        q = G.c01((l - .30) / .30)
        plate(cv, [140, 352, W - 140, 444], (12, 14, 10), int(225 * q), GOLD, int(140 * q), 1)
        G.lines_center(cv, sc.get("note", ""), COND, 32, 372, ac(GOLD, 245 * q), q,
                       maxw=W - 360)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .45) / .3))


def s_line(cv, d, t, l, sc):
    """Одна строка — направления."""
    p = G.c01(l / .28)
    text(cv, sc.get("kicker", ""), MONO, 19, W // 2, 196, ac(GOLD, 245 * p), p, "ma")
    _head(cv, sc.get("head", ""), G.c01((l - .10) / .28), y=232, size=56)
    if l > .34:
        q = G.c01((l - .34) / .30)
        G.chips_block(d, 352, sc.get("items", []), int(245 * q), size=26, h=58)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .5) / .3))


def s_thanks(cv, d, t, l, sc):
    p = G.c01(l / .28)
    text(cv, sc.get("kicker", "СПАСИБО"), MONO, 19, W // 2, 190, ac(GOLD, 245 * p), p, "ma")
    _head(cv, sc.get("head", ""), G.c01((l - .08) / .28), y=226, size=54)
    items = sc.get("items", [])
    y = 322
    step = 42 if len(items) > 5 else (48 if len(items) > 4 else 56)
    for i, it in enumerate(items):
        q = G.c01((l - .30 - i * .12) / .26)
        if q <= 0:
            continue
        yy = y + i * step
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle([430, yy + 12, 430 + int(10 * G.eo(q)), yy + 30],
                                      fill=ac(GOLD, 230))
        cv.alpha_composite(lay)
        text(cv, it, COND, 30, 462, yy, ac(TXT, 250 * q), q, maxw=W - 560)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .55) / .3))


def s_cta(cv, d, t, l, sc):
    p = G.c01(l / .26)
    text(cv, sc.get("kicker", "КУДА ИДТИ"), MONO, 19, W // 2, 214, ac(GOLD, 245 * p), p, "ma")
    _head(cv, sc.get("head", ""), G.c01((l - .08) / .28), y=252, size=58)
    if l > .30:
        q = G.c01((l - .30) / .30)
        G.lines_center(cv, sc.get("note", ""), COND, 36, 366, ac(TXT, 245 * q), q,
                       maxw=W - 280)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .5) / .3))


def s_outro(cv, d, t, l, sc):
    p = G.c01(l / .34)
    G.logo_at(cv, W // 2, 128, 118, p)
    if l > .18:
        slam(cv, "СВОИХ НЕ БРОСАЕМ", RUSSO, 72, W // 2, 300, ac(TXT, 255), G.c01((l - .18) / .30),
             "ma", maxw=W - 200)
    if l > .40:
        q = G.c01((l - .40) / .30)
        text(cv, "РАДИО «В ОКОПЕ» · 24/7", MONO, 24, W // 2, 400, ac(GOLD, 250 * q), q, "ma")
    subtitle(cv, sc.get("sub", ""), G.c01((l - .55) / .3))


def s_fact(cv, d, t, l, sc):
    """Факт выпуска: номер, тезис крупно, пояснение, пипсы прогресса."""
    n = int(sc.get("n", 6))
    idx = int(sc.get("idx", 1))
    p = G.c01(l / .30)
    if p <= 0:
        return
    text(cv, "%02d" % idx, RUSSO, 150, W - 64, 92, ac(GOLD, int(34 * p)), p, "rt")
    text(cv, "ФАКТ %d ИЗ %d" % (idx, n), MONO, 20, 130, 116, ac(GOLD, 245 * p), p)
    for i in range(n):
        x = 130 + i * 30
        on = i < idx
        d.rectangle([x, 150, x + 20, 154], fill=ac(GOLD if on else DIM, 220 if on else 90))

    maxw = W - 300
    head = sc.get("head", "")
    rows, size = G.pick_size(head, COND, maxw)
    note = sc.get("note", "")
    nrows = G.wrap(note, COND, 34, maxw, 2)[0] if note else []
    head_h = int(size * 1.10) * len(rows)
    block = head_h + (26 + 40 + int(34 * 1.16) * len(nrows) if nrows else 0)
    y = max(168, int(392 - block / 2))

    yy = y
    for r in rows:
        text(cv, r, COND, size, 130, yy, ac(TXT, 252), p, "lt")
        yy += int(size * 1.10)
    if l > .26:
        q = G.c01((l - .26) / .28)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle([130, yy + 14, 130 + int(120 * G.eo(q)), yy + 18],
                                      fill=ac(GOLD, 230))
        cv.alpha_composite(lay)
        ny = yy + 36
        for r in nrows:
            text(cv, r, COND, 34, 130, ny, ac(GOLD2, 240 * q), q, "lt")
            ny += int(34 * 1.16)
    subtitle(cv, sc.get("sub", ""), G.c01((l - .55) / .30))


FN = {
    "title": s_title, "flow": s_flow, "cards": s_cards, "rules": s_rules,
    "rule": s_rule, "line": s_line, "thanks": s_thanks, "cta": s_cta, "outro": s_outro,
    "fact": s_fact,
}
