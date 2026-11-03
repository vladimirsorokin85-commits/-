# -*- coding: utf-8 -*-
"""Обложки, превью и субтитры для двух роликов «Рюкзак 7.62»."""
import json
import os
import re

from PIL import Image, ImageDraw

import base as B
from base import COY, DIM, KHAKI, MONO, RUSSO, TXT, W, H, ac, bag, stage

BASE = B.BASE

# реплики по блокам: (сцена, список фраз)
LINES = {
    "r1": {
        "hook": ["Семьдесят литров.", "Патрульный рюкзак 7.62."],
        "why": ["Делали для подразделений спецназа.",
                "Прочный, но лёгкий: три и четыре десятых килограмма."],
        "narrow": ["Ширина — сорок на двадцать.", "Узкий профиль: улицы, двери, лестницы."],
        "access": ["Открывается сверху и по центру."],
        "molle": ["Пять внешних карманов.", "Молле по всей площади."],
        "colors": ["Койот и хаки.", "В наличии.", "Это «В окопе»."],
    },
    "r2": {
        "lid": ["Разбор по отсекам.", "Крышка: карман на молнии, карта, крепление под шлем."],
        "zip": ["Центральная молния десятого размера — быстрый доступ сверху вниз.",
                "Боковые карманы с разделителями и резинкой."],
        "bottom": ["Внизу отсек под дождевик.", "Отдельный карман для мокрого, вкладыш снимается."],
        "harness": ["Подвес: пять положений, три-дэ сетка, съёмный пояс.",
                    "Койот и хаки.", "Это «В окопе»."],
    },
}


def tc(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return ("%02d:%02d:%06.3f" % (h, m, sec)).replace(".", ",")


def make_srt(tag):
    tl = json.load(open(os.path.join(BASE, "timeline_%s.json" % tag), encoding="utf-8"))
    scenes = tl["scenes"]
    vo = {c["scene"]: c for c in tl["vo"]}
    order = [s for s, _ in sorted(scenes.items(), key=lambda kv: kv[1]) if s in LINES[tag]]
    out, idx = [], 1
    for sc in order:
        c = vo[sc]
        phrases = LINES[tag][sc]
        weights = [len(p) for p in phrases]
        total_w = sum(weights)
        t = c["start"]
        span = c["dur"]
        for ph, wt in zip(phrases, weights):
            d = span * wt / total_w
            out.append("%d\n%s --> %s\n%s\n" % (idx, tc(t), tc(t + d), ph))
            idx += 1
            t += d
    path = os.path.join(BASE, "%s.srt" % tag.upper())
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("srt", path, idx - 1, "реплик")
    return path


def cover(tag, name_a, h_a, cx_a, name_b=None, h_b=0, cx_b=0, kicker="", big="", sub="",
          chip_txt="", accent=KHAKI, out="thumb_%s_1080x1920.jpg"):
    cv = Image.new("RGBA", (W, H), ac(B.BG0, 255))
    stage(cv, 0.0, accent, glow=.9)
    d = ImageDraw.Draw(cv)
    if name_b:
        bag(cv, name_a, cx_a, 1055, h_a, shadow=.9, bloom=.5, accent=COY)
        bag(cv, name_b, cx_b, 1055, h_b, shadow=.9, bloom=.4, accent=accent)
    else:
        bag(cv, name_a, cx_a, 1080, h_a, shadow=1.0, bloom=.6, accent=accent)
    d.rectangle([0, 0, W, 8], fill=ac(accent, 255))
    d.text((48, 44), "«В ОКОПЕ»", font=B.F(RUSSO, 42), fill=ac(TXT, 255))
    if kicker:
        d.text((50, 108), kicker, font=B.F(MONO, 27), fill=ac(accent, 240))
    B.slam(cv, big, RUSSO, 132, 540, 232, ac(TXT, 255), 1.0, "ma", 0, maxw=980)
    if sub:
        B.slam(cv, sub, MONO, 42, 540, 372, ac(accent, 250), 1.0, "ma", 0)
    if chip_txt:
        B.chips_row(d, 1780 - 60, [(chip_txt, COY, True)], 255, size=30)
    for (x, y, sx, sy) in ((44, H - 168, 1, -1), (W - 44, H - 168, -1, -1)):
        d.line([(x, y), (x + sx * 46, y)], fill=ac(accent, 120), width=3)
        d.line([(x, y), (x, y + sy * 46)], fill=ac(accent, 120), width=3)
    B.scanlines(cv)
    p = os.path.join(BASE, out % tag)
    cv.convert("RGB").save(p, quality=93)
    print("cover", p, cv.size)
    return p


def preview(src, dst, crop_top=0.0):
    im = Image.open(src).convert("RGB")
    p = os.path.join(BASE, dst)
    im.save(p, quality=90)
    print("preview", p)
    return p


if __name__ == "__main__":
    make_srt("r1")
    make_srt("r2")
    cover("r1", "coyote_side", 1000, 540, kicker="ПАТРУЛЬНЫЙ · 70 Л · 40 × 20 × 75 СМ",
          big="70 ЛИТРОВ", sub="РЮКЗАК 7.62 · КОЙОТ / ХАКИ", chip_txt="В НАЛИЧИИ",
          accent=COY, out="thumb_%s_1080x1920.jpg")
    preview(os.path.join(BASE, "thumb_r1_1080x1920.jpg"), "preview_r1_1080x1920.jpg")
    cover("r2", "khaki_back", 1010, 300, name_b="coyote_side", h_b=1000, cx_b=790,
          kicker="РАЗБОР ПО ОТСЕКАМ", big="5 ОТСЕКОВ", sub="КРЫШКА · ЦЕНТР · БОКА · НИЗ · ПОДВЕС",
          chip_txt="70 Л · MOLLE 1″", accent=KHAKI, out="thumb_%s_1080x1920.jpg")
    preview(os.path.join(BASE, "thumb_r2_1080x1920.jpg"), "preview_r2_1080x1920.jpg")
