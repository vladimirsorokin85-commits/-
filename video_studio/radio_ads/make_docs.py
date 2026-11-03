# -*- coding: utf-8 -*-
"""Обложки 1080×1920 для трёх анонсов радио «В ОКОПЕ»."""
from PIL import Image, ImageDraw

import base as B
from base import (AMBER, COND, DIM, H, KHAKI, MONO, OLV, RUSSO, TXT, W, ac, bg_photo, chips_row,
                  eq_bars, logo_mark, shade, slam, stage)

BASE = B.BASE


def thumb(out, kicker, big, big_size, sub, chips, photo=None, accent=OLV, dark=0.30, extras=None):
    cv = Image.new("RGBA", (W, H), ac(B.BG0, 255))
    stage(cv, accent, glow=.75, t=1.0)
    if photo:
        bg_photo(cv, photo, zoom=1.12, dark=dark)
        shade(cv, 0, 760, 60, 250)
        shade(cv, H - 700, H - 120, 0, 235)
    d = ImageDraw.Draw(cv)
    d.rectangle([0, 0, W, 10], fill=ac(accent, 255))
    d.text((48, 44), "«В ОКОПЕ»", font=B.F(RUSSO, 40), fill=ac(TXT, 255))
    d.text((48, 94), "РАДИО · 24/7", font=B.F(MONO, 22), fill=ac(DIM, 225))
    slam(cv, kicker, MONO, 34, 540, 210, ac(accent, 252), 1.0, "ma", 14)
    slam(cv, big, big_size[0], big_size[1], 540, 250, ac(TXT, 255), 1.0, "ma", 34, maxw=980)
    if sub:
        slam(cv, sub, COND, 62, 540, 250 + big_size[2], ac(accent, 252), 1.0, "ma", 20, maxw=960)
    if extras == "logo":
        logo_mark(cv, 540, 1020, 1.0, 1.0, accent, .9)
    elif extras == "eq":
        spec = B.spectrum("r30")
        eq_bars(cv, 110, 1080, W - 220, 190, 22, spec[400], accent, 235, True, 7, .95)
    chips_row(d, 1520, chips, 255, size=25)

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    dl.rectangle([0, H - 122, W, H], fill=(4, 5, 4, 250))
    dl.rectangle([0, H - 125, W, H - 121], fill=ac(accent, 110))
    dl.text((W // 2, H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus",
            font=B.F(MONO, 25), fill=ac(KHAKI, 240), anchor="ma")
    dl.text((W // 2, H - 52), "РАДИО «В ОКОПЕ» · ДВАДЦАТЬ ЧЕТЫРЕ НА СЕМЬ",
            font=B.F(RUSSO, 17), fill=ac(DIM, 215), anchor="ma")
    cv.alpha_composite(lay)
    B.scanlines(cv)
    B.grain(cv, .7)
    cv.convert("RGB").save(out, quality=93)
    print("thumb", out)


if __name__ == "__main__":
    thumb("thumb_05_1080x1920.jpg", "ОТБИВКА · 5 СЕКУНД", "24 / 7", (COND, 230, 250),
          "МЫ ТАМ, ГДЕ НАШИ", [("РАДИО «В ОКОПЕ»", OLV, True)],
          photo="bg_tower", accent=OLV, dark=0.55, extras="logo")
    thumb("thumb_15_1080x1920.jpg", "КОРОТКИЙ АНОНС · 15 СЕКУНД", "СВОЯ ВОЛНА", (RUSSO, 108, 200),
          "У КАЖДОГО СВОЯ ЧАСТОТА", [("24 / 7 · БЕЗ ОСТАНОВОК", OLV, True)],
          photo="bg_trench", accent=OLV, dark=0.45, extras="eq")
    thumb("thumb_30_1080x1920.jpg", "ОСНОВНОЙ АНОНС · 30 СЕКУНД", "РАДИО", (RUSSO, 150, 200),
          "«В ОКОПЕ» — 24/7", [("ПЕСНИ О ВОЙНЕ И О ПОБЕДЕ", AMBER, True)],
          photo="bg_kitchen", accent=AMBER, dark=0.40, extras="logo")
