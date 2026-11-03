# -*- coding: utf-8 -*-
"""Обложки 1080×1920 для двух роликов про комплект РЭБ."""
import os

from PIL import Image, ImageDraw

import base as B
from base import (COND, DIM, KHAKI, MONO, OLV, RUSSO, TXT, W, WARN, ac, chip, cover, plate,
                  slam, stage, strip)

BASE = B.BASE


def thumb(tag, out, kicker, big, big_size, sub, chips, photo="pair_clean", src_w=1280,
          cy=1000, w=1240, dark=0.34, accent=OLV):
    cv = Image.new("RGBA", (W, B.H), ac(B.BG0, 255))
    stage(cv, accent, glow=.7, t=1.0)
    box = strip(cv, photo, cy, w, zoom=1.02, dark=dark)
    cover(cv, box, src_w, (7, 8, 6))
    d = ImageDraw.Draw(cv)

    d.rectangle([0, 0, W, 10], fill=ac(accent, 255))
    d.text((48, 46), "«В ОКОПЕ»", font=B.F(RUSSO, 40), fill=ac(TXT, 255))
    d.text((48, 96), "РЭБ · КОМПЛЕКТ · 9:16", font=B.F(MONO, 22), fill=ac(DIM, 210))
    slam(cv, kicker, MONO, 34, 540, 210, ac(accent, 250), 1.0, "ma", 14)
    slam(cv, big, big_size[0], big_size[1], 540, 262, ac(TXT, 255), 1.0, "ma", 34, maxw=980)
    if sub:
        slam(cv, sub, COND, 58, 540, 262 + big_size[2], ac(accent, 252), 1.0, "ma", 20, maxw=960)
    y = 1640
    xs = [int(B.F(MONO, 26).getlength(s)) + 44 for s, _, _ in chips]
    total = sum(xs) + 16 * (len(chips) - 1)
    x = int((W - total) / 2)
    for (s, col, solid), ww in zip(chips, xs):
        chip(d, x, y, s, col, 26, 58, 255, solid)
        x += ww + 16

    lay = Image.new("RGBA", (W, B.H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    dl.rectangle([0, B.H - 122, W, B.H], fill=(5, 6, 4, 248))
    dl.rectangle([0, B.H - 125, W, B.H - 121], fill=ac(accent, 110))
    dl.text((W // 2, B.H - 92), "t.me/vokope_ru   •   vk.com/vokope_rus",
            font=B.F(MONO, 25), fill=ac(KHAKI, 240), anchor="ma")
    dl.text((W // 2, B.H - 52), "СТАНЦИИ РЭБ «КАПЮШОН» · КОМПЛЕКТ ИЗ ДВУХ",
            font=B.F(RUSSO, 18), fill=ac(DIM, 215), anchor="ma")
    cv.alpha_composite(lay)
    B.scanlines(cv)
    B.grain(cv, 0.7)
    cv.convert("RGB").save(os.path.join(BASE, out), quality=93)
    print("thumb", out)


if __name__ == "__main__":
    thumb("r1", "thumb_r1_1080x1920.jpg", "КОМПЛЕКТ ИЗ ДВУХ СТАНЦИЙ",
          "600 000 ₽", (COND, 190, 240), "ЗА ДВЕ · 300 000 ₽ ЗА КАЖДУЮ",
          [("АКЦИЯ ДО 15 НОЯБРЯ", WARN, True)])
    thumb("r2", "thumb_r2_1080x1920.jpg", "8 КАНАЛОВ · ДО 300 М",
          "360°", (COND, 220, 240), "КУПОЛЬНАЯ ЗАЩИТА",
          [("600 000 ₽ ЗА ДВЕ · ДО 15 НОЯБРЯ", OLV, True)])
