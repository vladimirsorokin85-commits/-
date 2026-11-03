# -*- coding: utf-8 -*-
"""Сцены горизонтали 16:9 «Тепловизор 360°» (52 кадра)."""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render_horz_base import (A, BASE, BEAT, BG, key_img, DAYS, DIM, F, GRAIN, H, ICE, MONO, ORG, RED, RUSSO,
                              SCAN, SHOTS, TXT, VIGN, W, ac, arcf, beatshake, bg_set, card, c01,
                              chip, cl, cover_im, crop_photo, eo, grade, keyed, photo_on, put,
                              tag, text_lay, vframe_t, _VID)

# ─────────────── таблица визуала: shot → (вид, параметры)
VIS = {
    1: dict(kind="hero", seq="a", t0=0.0, ox=0.0, oy=0.05, sub="ПОВОРОТНЫЙ БЛОК · ДЕНЬ И НОЧЬ",
            label="ВИДЕО ЗАКАЗЧИКА"),
    2: dict(kind="media", photo="camera_back_close.jpg", h=720, rot=-1.6, sub="ВИДИТ БЕЗ ПОДСВЕТКИ",
            callouts=[(0.52, 0.52, "ТЕПЛО"), (0.74, 0.52, "ДЕНЬ"), (0.30, 0.52, "ЛАЗЕР")],
            chips=["360° ПО ГОРИЗОНТАЛИ", "НАКЛОН ПО ВЕРТИКАЛИ"], label="ФОТО"),
    3: dict(kind="media", seq="d", t0=0.0, sub="КАРТИНКА ИДЁТ В САЛОН", label="ВИДЕО ЗАКАЗЧИКА"),
    4: dict(kind="media", photo="camera_back.jpg", h=700, rot=1.4, sub="ТОЛЬКО БЛОК И ОДИН КАБЕЛЬ",
            callouts=[(0.86, 0.42, "КАБЕЛЬ 12 В")],
            chips=["МАГНИТНОЕ КРЕПЛЕНИЕ", "12 В ОТ ПРИКУРИВАТЕЛЯ"], label="ФОТО"),
    5: dict(kind="list", lines=["КОМПЛЕКТ", "УСТАНОВКА", "ДВА КАНАЛА", "ЛАЗЕР", "ФОКУС"]),
    6: dict(kind="media", photo="kit_wide.jpg", h=800, sub="ВСЁ В ОДНОЙ СУМКЕ", label="ФОТО"),
    7: dict(kind="media", photo="camera_back.jpg", h=780, rot=-2.2, sub="ПОВОРОТНАЯ ПЛАТФОРМА",
            callouts=[(0.50, 0.26, "ЧЕХОЛ «ПИКСЕЛЬ»"), (0.50, 0.84, "ПЛАТФОРМА")],
            chips=["ЧЕХОЛ «ПИКСЕЛЬ»", "МАГНИТНОЕ КРЕПЛЕНИЕ"], label="ФОТО"),
    8: dict(kind="media", box=("kit_screen.jpg", (0.30, 0.20, 0.78, 0.60)), sub="В САЛОНЕ — НА ПАНЕЛИ ИЛИ СТЕКЛЕ",
            label="ФОТО"),
    9: dict(kind="media", box=("kit_wide.jpg", (0.42, 0.60, 0.76, 0.84)), sub="ПИТАНИЕ И ПОВОРОТ", label="ФОТО"),
    10: dict(kind="media", box=("kit_wide.jpg", (0.45, 0.63, 0.60, 0.80)), sub="ТОЛЬКО ЛАЗЕР · КНОПКИ A И B",
             label="ФОТО"),
    11: dict(kind="media", box=("kit_wide.jpg", (0.30, 0.60, 0.80, 0.92)), sub="КЛЮЧ ФОКУСА И КАБЕЛЬ 12 В",
             label="ФОТО"),
    12: dict(kind="media", photo="kit_wide.jpg", h=760, sub="ДОКУПАТЬ НЕЧЕГО",
             chips=["БЛОК", "МОНИТОР", "ДВА ПУЛЬТА", "КЛЮЧ", "КАБЕЛЬ"], label="ФОТО"),
    13: dict(kind="numbers", big="1 МИНУТА", sub="ОТ СУМКИ ДО КАРТИНКИ", accent=ORG),
    14: dict(kind="media", photo="camera_back.jpg", h=820, oy=0.55, rot=0.8, sub="ЛЮБАЯ МЕТАЛЛИЧЕСКАЯ ПОВЕРХНОСТЬ",
            callouts=[(0.50, 0.86, "МАГНИТ")],
             chips=["КРЫША", "КАПОТ", "БОРТ КУЗОВА"], label="ФОТО"),
    15: dict(kind="media", photo="camera_back.jpg", h=860, rot=-1.0, sub="БЫСТРОСЪЁМНОЕ · БЕЗ ИНСТРУМЕНТА",
            callouts=[(0.50, 0.94, "СНЯТЬ ОДНИМ ДВИЖЕНИЕМ")],
             chips=["СНЯТЬ ОДНИМ ДВИЖЕНИЕМ"], label="ФОТО"),
    16: dict(kind="media", photo="kit_wide.jpg", h=780, sub="12 В ОТ ПРИКУРИВАТЕЛЯ",
             chips=["ПОСТОЯННЫЙ ТОК", "КАБЕЛЬ В КОМПЛЕКТЕ"], label="ФОТО"),
    17: dict(kind="axis", sub="И НА СТАЦИОНАРНУЮ ПОЗИЦИЮ"),
    18: dict(kind="media", seq="c", t0=0.0, sub="КНОПКА «ВКЛ» — ПИТАНИЕ", label="ВИДЕО ЗАКАЗЧИКА"),
    19: dict(kind="rot", mode="h", seq="c", t0=0.0, sub="ПОЛНЫЙ КРУГ"),
    20: dict(kind="rot", mode="v", seq="c", t0=0.0, sub="ПЛАТФОРМА ДВУХОСЕВАЯ"),
    21: dict(kind="list", lines=["ВЛЕВО", "ВПРАВО", "НАЗАД", "ВВЕРХ", "ВНИЗ"], sub="КНОПКАМИ С ПУЛЬТА"),
    22: dict(kind="media", seq="c", t0=0.0, sub="БЕЗ РУЧНОГО РАЗВОРОТА", label="ВИДЕО ЗАКАЗЧИКА"),
    23: dict(kind="split", a=("d", 0.0), b=("camera_back_close.jpg", None), sub="ТЕПЛОВИЗОР + ДНЕВНАЯ КАМЕРА"),
    24: dict(kind="media", seq="d", t0=0.0, sub="ТЕПЛОВОЙ КАНАЛ", chips=["VOx 12 МКМ"], label="ВИДЕО ЗАКАЗЧИКА"),
    25: dict(kind="specs", lines=["VOX · НЕОХЛАЖДАЕМЫЙ", "50 КАДР/С", "8–14 МКМ"], bg=("d", 0.0)),
    26: dict(kind="fov", sub="ОБЪЕКТИВ 9 ММ"),
    27: dict(kind="media", photo="camera_back_close.jpg", h=760, sub="ДНЕВНАЯ КАМЕРА", label="ФОТО"),
    28: dict(kind="specs", lines=["0,01 ЛЮКС", "2,8 ММ", "2 МП"], bg=("camera_back_close.jpg", None)),
    29: dict(kind="fov", compare=True, sub="ДЕНЬ ШИРЕ, ЧЕМ ТЕПЛО"),
    30: dict(kind="laser", sub="ЦЕЛЕУКАЗАТЕЛЬ"),
    31: dict(kind="media", box=("kit_wide.jpg", (0.45, 0.63, 0.60, 0.80)), sub="A — ВКЛ · B — ВЫКЛ",
             chips=["МАЛЫЙ ПУЛЬТ"], label="ФОТО"),
    32: dict(kind="media", box=("kit_wide.jpg", (0.57, 0.60, 0.75, 0.86)), sub="СНАЧАЛА ПИТАНИЕ",
             chips=["БЕЗ ПИТАНИЯ ЛАЗЕР НЕ ЗАПУСТИТСЯ"], label="ФОТО"),
    33: dict(kind="media", seq="d", t0=0.0, sub="МЕТКА ВИДНА В ОБЕИХ КАРТИНКАХ", reticle=True,
             label="ВИДЕО ЗАКАЗЧИКА"),
    34: dict(kind="media", photo="camera_back_close.jpg", h=740, zoom_lens=True, sub="НАСТРОЙКА ВРУЧНУЮ",
             label="ФОТО"),
    35: dict(kind="key", step=1),
    36: dict(kind="key", step=2),
    37: dict(kind="key", step=3),
    38: dict(kind="numbers", big="≤ 1 ММ", sub="СДВИГ КЛЮЧА", accent=ICE),
    39: dict(kind="volt", mode="warn", big="12 В"),
    40: dict(kind="volt", mode="ok", big="12 В ПОСТОЯННОГО ТОКА"),
    41: dict(kind="volt", mode="bad", big="24 В"),
    42: dict(kind="volt", mode="bad2", big="24 В"),
    43: dict(kind="list", lines=["12 В", "ПОСТОЯННЫЙ ТОК", "ДО ПОДКЛЮЧЕНИЯ"], sub="ПРОВЕРЬТЕ СЕТЬ МАШИНЫ"),
    44: dict(kind="numbers", big="ЦИФРЫ", sub="ВСЁ ПОД РУКОЙ", accent=ORG),
    45: dict(kind="axis", sub="ДВЕ ОСИ"),
    46: dict(kind="numbers", big="3,8 КГ", sub="ВЕС БЛОКА", accent=ICE),
    47: dict(kind="numbers", big="40×30×30", sub="САНТИМЕТРОВ", accent=ICE),
    48: dict(kind="media", photo="camera_back.jpg", h=800, rot=1.8, sub="ЧЕХОЛ «ПИКСЕЛЬ»",
            callouts=[(0.50, 0.28, "ЧЕХОЛ НА БЛОКЕ")],
             chips=["ИЗНОСОСТОЙКИЙ", "СНИМАЕТСЯ"], label="ФОТО"),
    49: dict(kind="list", lines=["ДЕНЬ И НОЧЬ", "С ТЕХНИКИ", "С ПОЗИЦИИ", "УПРАВЛЕНИЕ ИЗ УКРЫТИЯ"]),
    50: dict(kind="split", a=("d", 0.0), b=("camera_back_close.jpg", None), sub="ТЕПЛО И FULL HD"),
    51: dict(kind="split", a=("c", 0.0), b=("camera_back.jpg", None), sub="ТЕХНИКА И СТАЦИОНАРНАЯ ПОЗИЦИЯ"),
    52: dict(kind="outro"),
}


def _media_img(v, t, l):
    """Возвращает (RGB-кадр, метка источника) для видео/фото внутри карточки."""
    if "seq" in v:
        im = vframe_t(v["seq"], t, v.get("t0", 0.0))
        return grade(im, .46, 1.18, .55, (255, 165, 90), .05).convert("RGB"), "ВИДЕО ЗАКАЗЧИКА"
    if "box" in v:
        name, box = v["box"]
        im = crop_photo(name, box)
        return key_img(im, 900), "ФОТО"
    return None, None


def _title(cv, d, sh, v, l, y=250):
    put(cv, sh["screen"], RUSSO, 104, 110, y, ac(TXT, 255), c01((l - .05) / .35), maxw=1000)
    if v.get("sub") and v["sub"].upper() != sh["screen"].upper():
        put(cv, v["sub"], MONO, 32, 112, y + 132, ac(ORG, 245), c01((l - .22) / .35), maxw=980)


def _chips(d, v, l, y=770, x=110):
    if not v.get("chips"):
        return
    p = c01((l - .55) / .4)
    cx = x
    for c in v["chips"]:
        w = chip(d, cx, y, c, ORG if cx == x else ICE, 26, 56, int(255 * p))
        cx += w + 16


def callouts(d, box, items, p):
    """Метки на фото: точка + тонкая линия + подпись в тёмной плашке."""
    if p <= 0:
        return
    x0, y0, w, h = box
    f = F(MONO, 22)
    for (fx, fy, txt) in items:
        cx, cy = int(x0 + w * fx), int(y0 + h * fy)
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=ac(ORG, int(240 * p)))
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=ac(ORG, int(120 * p)), width=2)
        tw = f.getlength(txt)
        lx = cx - int(tw / 2) - 14
        ly = cy + 26
        d.rectangle([lx, ly, lx + tw + 28, ly + 38], fill=ac((6, 7, 9), int(215 * p)),
                    outline=ac(ORG, int(150 * p)))
        d.text((lx + 14, ly + 8), txt, font=f, fill=ac(ORG, int(245 * p)))


def s_hero(cv, d, t, l, sh, v):
    im = vframe_t(v["seq"], t, v.get("t0", 0.0))
    cv.alpha_composite(grade(cover_im(im, W, H, 1.06 + .10 * eo(l / max(1, sh["dur"])),
                                      v.get("ox", 0), v.get("oy", 0)), .40, 1.16, .50, (255, 150, 65), .06))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    for x in range(0, W, 4):
        k = x / W
        do.line([(x, 0), (x, H)], fill=(4, 5, 8, int(30 + 165 * cl((k - .30) / .70) ** 1.3)))
    cv.alpha_composite(ov)
    put(cv, sh["screen"], RUSSO, 124, 110, 300, ac(TXT, 255), c01((l - .05) / .35), maxw=1200)
    put(cv, v["sub"], DAYS, 62, 112, 452, ac(ORG, 255), c01((l - .22) / .35), maxw=1100)
    tag(d, v["label"], 110, 900, ICE, int(230 * c01((l - .3) / .4)))


def s_media(cv, d, t, l, sh, v):
    bg_set(cv, t)
    _title(cv, d, sh, v, l)
    _chips(d, v, l)
    im, label = _media_img(v, t, l)
    p = c01((l - .12) / .45)
    sh_ = beatshake(t)
    if im is not None and getattr(im, "mode", "") == "RGBA":
        st = min(720 / im.height, 820 / im.width)
        im2 = im.resize((int(im.width * st), int(im.height * st)), Image.LANCZOS)
        if p < 1:
            im2.putalpha(im2.getchannel("A").point(lambda x: int(x * p)))
        cv.alpha_composite(im2, (int(1400 - im2.width / 2), int(560 - im2.height / 2)))
        tag(d, label, 1150, 78, ORG, int(220 * c01((l - .4) / .4)))
    elif im is not None:
        card(cv, im, 1400 + sh_[0], 560 + sh_[1], 500, 890, ICE, int(255 * p))
        tag(d, label, 1150, 78, ICE, int(220 * c01((l - .4) / .4)))
    else:
        ph = v.get("photo")
        if v.get("zoom_lens"):
            key = keyed(ph, 1500)
            bb = key.getbbox()
            cx0 = bb[0] + int((bb[2] - bb[0]) * .46)
            cy0 = bb[1] + int((bb[3] - bb[1]) * .48)
            size = int(min(bb[2] - bb[0], bb[3] - bb[1]) * .55)
            crop = key.crop((cx0 - size // 2, cy0 - size // 2, cx0 + size // 2, cy0 + size // 2))
            card(cv, crop.convert("RGB"), 1400, 560, 720, 720, ORG, int(255 * p))
        else:
            rot = v.get("rot", 0.0)
            box = None
            if rot:
                im_k = keyed(ph, 1500)
                st = v.get("h", 760) / im_k.height
                im_r = im_k.resize((int(im_k.width * st), int(im_k.height * st)), Image.LANCZOS)
                im_r = im_r.rotate(rot, expand=True, resample=Image.BICUBIC)
                if p < 1:
                    im_r.putalpha(im_r.getchannel("A").point(lambda x: int(x * p)))
                cv.alpha_composite(im_r, (int(1400 - im_r.width / 2), int(560 - im_r.height / 2)))
                box = (int(1400 - im_r.width / 2), int(560 - im_r.height / 2), im_r.width, im_r.height)
            else:
                box = photo_on(cv, ph, 1400 + sh_[0], 560 + sh_[1], h=v.get("h", 760), alpha=int(255 * p))
            tag(d, v.get("label", "ФОТО"), 1150, 78, ORG, int(220 * c01((l - .4) / .4)))
            if v.get("callouts") and box and p > .6:
                callouts(d, box, v["callouts"], c01((l - .8) / .5))


def s_list(cv, d, t, l, sh, v):
    bg_set(cv, t, 620)
    _title(cv, d, sh, v, l, 210)
    for i, line in enumerate(v["lines"]):
        p = c01((l - .30 - i * .12) / .35)
        if p <= 0:
            continue
        y = 470 + i * 86
        d.rectangle([112, y + 14, 112 + int(10 * p), y + 60], fill=ac(ORG if i % 2 == 0 else ICE, 230))
        put(cv, line, RUSSO, 54, 150, y, ac(TXT, 250 * p), p, maxw=1100)
    if v.get("sub"):
        put(cv, v["sub"], MONO, 30, 112, 950, ac(DIM, 230), c01((l - .6) / .4))


def s_numbers(cv, d, t, l, sh, v):
    bg_set(cv, t, 700)
    put(cv, v["big"], DAYS, 190, 110, 330, ac(v.get("accent", ORG), 255), c01((l - .05) / .40), maxw=1400)
    if not sh["screen"].upper().startswith(v["big"].upper()):
        put(cv, sh["screen"], RUSSO, 74, 116, 590, ac(TXT, 255), c01((l - .25) / .35), maxw=1200)
    if v.get("sub"):
        put(cv, v["sub"], MONO, 34, 118, 690, ac(DIM, 235), c01((l - .45) / .35), maxw=1100)
    p = c01((l - .55) / .40)
    d.rectangle([110, 810, 110 + int(700 * eo(p)), 818], fill=ac(v.get("accent", ORG), 220))


def s_specs(cv, d, t, l, sh, v):
    src, t0 = v["bg"]
    if src in ("a", "b", "c", "d"):
        im = grade(cover_im(vframe_t(src, t, t0), W, H, 1.05, 0, 0), .30, 1.1, .35, (255, 150, 65), .05)
        cv.alpha_composite(im)
    else:
        cv.alpha_composite(Image.new("RGBA", (W, H), ac((10, 11, 14), 255)))
        photo_on(cv, src, 1480, 560, h=900, alpha=70, glow_a=0)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    for x in range(0, W, 4):
        do.line([(x, 0), (x, H)], fill=(5, 6, 9, 130))
    cv.alpha_composite(ov)
    _title(cv, d, sh, v, l, 230)
    for i, line in enumerate(v["lines"]):
        p = c01((l - .45 - i * .18) / .35)
        if p <= 0:
            continue
        y = 560 + i * 96
        d.rectangle([112, y + 8, 112 + int(44 * p), y + 14], fill=ac(ICE, 220))
        put(cv, line, MONO, 44, 180, y - 8, ac(TXT, 250 * p), p, maxw=1000)


def s_rot(cv, d, t, l, sh, v):
    bg_set(cv, t)
    _title(cv, d, sh, v, l, 220)
    im = vframe_t(v["seq"], t, v.get("t0", 0.0))
    card(cv, im, 1400, 540, 500, 890, ORG, 255)
    cx, cy = 1400, 540
    if v["mode"] == "h":
        arcf(d, cx, cy, 430, -t * 60, -t * 60 + 320, ORG, 7, 220, 28, 20)
        d.line([(cx, cy - 470), (cx, cy + 470)], fill=ac(ICE, 45), width=2)
        put(cv, "360°", DAYS, 120, cx, cy, ac(ORG, 235), c01((l - .5) / .4), anchor="ma")
    else:
        arcf(d, cx, cy, 300, 60 + t * 40, 60 + t * 40 + 70, ORG, 7, 220, 24, 18)
        d.line([(cx, cy - 470), (cx, cy + 470)], fill=ac(ICE, 45), width=2)
        for dy in (-1, 1):
            ay = cy + dy * 250
            d.polygon([(cx - 460, ay), (cx - 420, ay - 22), (cx - 420, ay + 22)], fill=ac(ORG, 190))
    tag(d, "МАКЕТ · СХЕМА ПОВОРОТА", 1150, 78, ORG, 210)


def s_laser(cv, d, t, l, sh, v):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((7, 10, 14), 255)))
    d2 = ImageDraw.Draw(cv)
    for i in range(-6, 30):
        x = i * 120
        d2.line([(W / 2 + (x - W / 2) * .2, 720), (x, H)], fill=ac(ICE, 18), width=2)
    for i in range(7):
        y = 720 + int((H - 720) * (i / 6.0) ** 2)
        d2.line([(0, y), (W, y)], fill=ac(ICE, 15), width=2)
    _title(cv, d, sh, v, l, 210)
    x0, y0 = 300, 790
    x1, y1 = 1560, 520
    p = eo(c01((l - .35) / 1.2))
    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(beam)
    db.line([(x0, y0), (xe, ye)], fill=ac(ORG, 240), width=26)
    db.line([(x0, y0), (xe, ye)], fill=ac((255, 205, 140), 200), width=10)
    cv.alpha_composite(beam.filter(ImageFilter.GaussianBlur(18)))
    d.line([(x0, y0), (xe, ye)], fill=ac((255, 232, 186), 245), width=6)
    for m in (250, 500, 750, 1000):
        q = m / 1000.0
        if p >= q:
            px, py = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
            d.line([(px - 14, py - 34), (px + 14, py + 34)], fill=ac(ICE, 225), width=4)
            d.text((px + 22, py + 28), "%d М" % m, font=F(MONO, 30), fill=ac(ICE, 235))
    if p > .97:
        q = c01((l - 1.6) / .4)
        arcf(d, x1, y1, 78, -t * 50, -t * 50 + 280, ORG, 5, int(220 * q), 20, 14)
        arcf(d, x1, y1, 118, t * 40, t * 40 + 250, ICE, 3, int(160 * q), 18, 14)
    chip(d, 112, 640, "КНОПКА A — ВКЛ", ORG, 27, 56, int(255 * c01((l - .7) / .4)), solid=True)
    chip(d, 470, 640, "КНОПКА B — ВЫКЛ", ICE, 27, 56, int(255 * c01((l - .9) / .4)))
    tag(d, "МАКЕТ · СХЕМА ЛУЧА", 112, 900, ORG, 210)


def s_volt(cv, d, t, l, sh, v):
    mode = v["mode"]
    base = (18, 8, 8) if mode in ("bad", "bad2") else (10, 12, 15)
    cv.alpha_composite(Image.new("RGBA", (W, H), ac(base, 255)))
    if mode in ("bad", "bad2"):
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(st)
        for i in range(-10, 30):
            x = i * 140 + int((t * 50) % 140)
            ds.polygon([(x, 0), (x + 52, 0), (x + 52 - 420, H), (x - 420, H)], fill=ac(RED, 18))
        cv.alpha_composite(st)
    else:
        bg_set(cv, t, 640)
    put(cv, v["big"], DAYS, 150 if len(v["big"]) < 14 else 96, 110, 250,
        ac(RED if mode.startswith("bad") else ORG, 255), c01((l - .05) / .35), maxw=1300)
    if sh["screen"].upper() != v["big"].upper():
        put(cv, sh["screen"], RUSSO, 78, 116, 560, ac(TXT, 255), c01((l - .25) / .35), maxw=1250)
    p = c01((l - .55) / .45)
    if mode == "bad":
        d.line([(150, 300), (150 + 520 * eo(p), 300 + 170 * eo(p))], fill=ac(TXT, 240), width=16)
        d.line([(670, 300), (670 - 520 * eo(p), 300 + 170 * eo(p))], fill=ac(TXT, 240), width=16)
        put(cv, "МГНОВЕННОЕ ВЫГОРАНИЕ ЭЛЕКТРОНИКИ", MONO, 40, 116, 750, ac(TXT, 240 * p), p, maxw=1250)
    elif mode == "bad2":
        put(cv, "ТОЛЬКО 12 В ПОСТОЯННОГО ТОКА", MONO, 40, 116, 750, ac(TXT, 240 * p), p, maxw=1250)
    elif mode == "ok":
        chip(d, 116, 700, "ПОСТОЯННЫЙ ТОК", ICE, 30, 64, int(255 * p))
        chip(d, 470, 700, "ОТ ПРИКУРИВАТЕЛЯ", ORG, 30, 64, int(255 * p))
    else:
        put(cv, "ГЛАВНОЕ В КОМПЛЕКТЕ", MONO, 40, 116, 700, ac(TXT, 240 * p), p, maxw=1250)
    tag(d, "МАКЕТ", 116, 900, RED if mode.startswith("bad") else ORG, 210)


def s_key(cv, d, t, l, sh, v):
    bg_set(cv, t)
    _title(cv, d, sh, v, l, 200)
    step = v["step"]
    key = keyed("camera_back_close.jpg", 1300)
    bb = key.getbbox()
    cx0 = bb[0] + int((bb[2] - bb[0]) * .46)
    cy0 = bb[1] + int((bb[3] - bb[1]) * .48)
    size = int(min(bb[2] - bb[0], bb[3] - bb[1]) * .62)
    crop = key.crop((cx0 - size // 2, cy0 - size // 2, cx0 + size // 2, cy0 + size // 2))
    card(cv, crop.convert("RGB"), 1480, 560, 700, 700, ORG, 255)
    cx, cy = 1480, 560
    p = eo(c01((l - .25) / .9))
    if step == 1:
        for dx in (-70, 70):
            d.ellipse([cx + dx - 26, cy - 26, cx + dx + 26, cy + 26], outline=ac(ICE, 235), width=5)
        kx = int(cx + 420 * (1 - p))
        d.line([(kx, cy + 240 - 120 * p), (kx + 96, cy + 240 - 160 * p)], fill=ac(ICE, 240), width=8)
        d.ellipse([kx - 20, cy + 220 - 120 * p, kx + 20, cy + 260 - 120 * p], outline=ac(ICE, 240), width=6)
        d.text((cx, cy + 420), "ДВА ЗУБА — В ОТВЕРСТИЯ", font=F(MONO, 28), fill=ac(ICE, 235), anchor="ma")
    elif step == 2:
        for dx in (-70, 70):
            d.ellipse([cx + dx - 26, cy - 26, cx + dx + 26, cy + 26], outline=ac(ORG, 240), width=5)
        for i in range(3):
            ay = cy + 120 + i * 44
            d.line([(cx - 60 - i * 10, ay), (cx + 60 + i * 10, ay)], fill=ac(ORG, int(90 + 60 * p)), width=5)
        d.text((cx, cy + 420), "СЛЕГКА ПРИЖАТЬ", font=F(MONO, 28), fill=ac(ORG, 240), anchor="ma")
    else:
        arc_r = 150
        arcf(d, cx, cy, arc_r, -t * 90, -t * 90 + 260, ORG, 7, 240, 24, 18)
        d.text((cx, cy + 420), "КРУТИТЬ ДО РЕЗКОСТИ", font=F(MONO, 28), fill=ac(ORG, 240), anchor="ma")
    tag(d, "ФОТО + МАКЕТ", 1150, 78, ORG, 210)


def s_fov(cv, d, t, l, sh, v):
    bg_set(cv, t, 720)
    _title(cv, d, sh, v, l, 200)
    ox, oy = 300, 800
    p = eo(c01((l - .3) / 1.0))
    if v.get("compare"):
        for ang, col, lbl, r in ((51.0, ORG, "ТЕПЛО 51,4°", 620), (102.0, ICE, "ДЕНЬ 102°", 900)):
            a = math.radians(ang * p)
            d.polygon([(ox, oy), (ox + r * math.cos(-a / 2), oy + r * math.sin(-a / 2)),
                       (ox + r * math.cos(a / 2), oy + r * math.sin(a / 2))],
                      fill=ac(col, 26), outline=ac(col, 200))
            d.text((ox + 40, oy - r * math.sin(a / 2) - 34), lbl, font=F(MONO, 30), fill=ac(col, 235))
        d.ellipse([ox - 22, oy - 22, ox + 22, oy + 22], fill=ac(TXT, 240))
    else:
        a = math.radians(41.1 * p)
        L = 900
        d.polygon([(ox, oy), (ox + L * math.cos(-a / 2), oy + L * math.sin(-a / 2)),
                   (ox + L * math.cos(a / 2), oy + L * math.sin(a / 2))],
                  fill=ac(ORG, 30), outline=ac(ORG, 210))
        d.ellipse([ox - 20, oy - 20, ox + 20, oy + 20], fill=ac(TXT, 240))
        put(cv, "51,4° × 41,1°", MONO, 46, 940, 520, ac(ORG, 245), c01((l - .6) / .4), maxw=900)
        put(cv, "ОБЪЕКТИВ 9 ММ", MONO, 34, 940, 610, ac(TXT, 235), c01((l - .8) / .4), maxw=900)
        put(cv, "640×512 · 50 КАДР/С", MONO, 34, 940, 670, ac(DIM, 235), c01((l - 1.0) / .4), maxw=900)
    tag(d, "МАКЕТ · УГЛЫ ОБЗОРА", 112, 900, ORG, 210)


def s_axis(cv, d, t, l, sh, v):
    bg_set(cv, t, 640)
    _title(cv, d, sh, v, l, 200)
    cx, cy = 1180, 620
    d.ellipse([cx - 210, cy - 210, cx + 210, cy + 210], outline=ac(ICE, 90), width=3)
    arcf(d, cx, cy, 210, -t * 55, -t * 55 + 290, ORG, 7, 235, 26, 18)
    arcf(d, cx, cy, 140, 40 + t * 45, 40 + t * 45 + 90, ICE, 6, 210, 20, 16)
    d.line([(cx, cy - 300), (cx, cy + 300)], fill=ac(ICE, 60), width=2)
    d.line([(cx - 300, cy), (cx + 300, cy)], fill=ac(ICE, 60), width=2)
    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=ac((30, 32, 38), 255), outline=ac(ORG, 220), width=4)
    d.text((cx, cy - 330), "360°", font=F(DAYS, 54), fill=ac(ORG, 235), anchor="ma")
    d.text((cx + 330, cy + 40), "НАКЛОН", font=F(MONO, 30), fill=ac(ICE, 235), anchor="la")
    tag(d, "МАКЕТ · ДВЕ ОСИ", 112, 900, ORG, 210)


def s_split(cv, d, t, l, sh, v):
    bg_set(cv, t)
    _title(cv, d, sh, v, l, 190)
    for i, (src, t0) in enumerate((v["a"], v["b"])):
        p = c01((l - .12 - i * .15) / .45)
        cx = 900 + i * 470
        if src in ("a", "b", "c", "d"):
            im = vframe_t(src, t, t0 or 0.0)
            im = grade(im, .55, 1.14, .62, (255, 165, 90), .04).convert("RGB")
            card(cv, im, cx, 640, 420, 750, ICE if i else ORG, int(255 * p))
        else:
            key = keyed(src, 1200)
            bb = key.getbbox()
            size = int(min(bb[2] - bb[0], bb[3] - bb[1]) * .8)
            cx0 = bb[0] + int((bb[2] - bb[0]) * .46)
            cy0 = bb[1] + int((bb[3] - bb[1]) * .48)
            crop = key.crop((cx0 - size // 2, cy0 - size // 2, cx0 + size // 2, cy0 + size // 2))
            card(cv, crop.convert("RGB"), cx, 640, 620, 620, ICE if i else ORG, int(255 * p))
    tag(d, "ТЕПЛО / ДЕНЬ", 112, 900, ORG, 200)


def s_outro(cv, d, t, l, sh, v):
    cv.alpha_composite(Image.new("RGBA", (W, H), ac((8, 9, 12), 255)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for y in range(0, H, 3):
        k = abs(y / H - .5) * 2
        dg.line([(0, y), (W, y)], fill=ac(ORG, int(34 * (1 - k) ** 2)))
    cv.alpha_composite(g)
    sw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sw)
    x = int(-500 + (l / max(1, sh["dur"])) * (W + 1000))
    ds.polygon([(x, 0), (x + 240, 0), (x + 240 - 380, H), (x - 380, H)], fill=ac(ORG, 24))
    cv.alpha_composite(sw.filter(ImageFilter.GaussianBlur(18)))
    put(cv, "«В ОКОПЕ»", RUSSO, 168, W // 2, 300, ac(TXT, 255), c01((l - .05) / .35), anchor="ma", maxw=1500)
    put(cv, "ТЕПЛОВИЗОР 360° · ПОВОРОТНЫЙ БЛОК", MONO, 40, W // 2, 470, ac(ORG, 250),
        c01((l - .3) / .35), anchor="ma", maxw=1400)
    p = c01((l - .7) / .4)
    d.rectangle([W // 2 - 320, 560, W // 2 - 320 + int(640 * eo(p)), 568], fill=ac(ORG, 220))
    put(cv, "ВОПРОСЫ — В КОММЕНТАРИЯХ", RUSSO, 56, W // 2, 640, ac(TXT, 245),
        c01((l - .9) / .35), anchor="ma", maxw=1300)
    put(cv, "t.me/vokope_ru   •   vk.com/vokope_rus", MONO, 38, W // 2, 760, ac(ICE, 240),
        c01((l - 1.2) / .4), anchor="ma", maxw=1200)
    q = c01((l - 1.6) / .45)
    chip(d, W // 2 - 150, 840, "ПОДПИСАТЬСЯ", ORG, 34, 70, int(255 * q), solid=True)
    d.rectangle([60, 96, W - 60, H - 96], outline=ac(ORG, int(60 + 30 * math.sin(t * 3))), width=4)


FN = {"hero": s_hero, "media": s_media, "list": s_list, "numbers": s_numbers, "specs": s_specs,
      "rot": s_rot, "laser": s_laser, "volt": s_volt, "key": s_key, "fov": s_fov,
      "axis": s_axis, "split": s_split, "outro": s_outro}


def render_frame(t):
    sh = SHOTS[0]
    for s in SHOTS:
        if t >= s["t0"] - 1e-6:
            sh = s
    l = t - sh["t0"]
    v = VIS[sh["n"]]
    cv = Image.new("RGBA", (W, H), ac(BG, 255))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    FN[v["kind"]](cv, d, t, l, sh, v)
    out = Image.alpha_composite(cv, ui)
    hud_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    from render_horz_base import hud
    hud(ImageDraw.Draw(hud_l), t, sh["block_name"])
    out = Image.alpha_composite(out, hud_l)
    out = Image.alpha_composite(out, SCAN)
    out = Image.alpha_composite(out, VIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 15) % 4])
    out = out.convert("RGB")
    # зум-панч на склейке
    for s in SHOTS[1:]:
        dd = t - s["t0"]
        if 0 <= dd < .16:
            k = 1 - dd / .16
            z = 1 + .035 * k
            cw, ch = int(W / z), int(H / z)
            out = out.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
    arr = np.asarray(out).astype(np.float32)
    beat = (t / BEAT) % 1.0
    arr *= 1.0 + .016 * math.exp(-beat * 7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    import sys
    os_dir = "/tmp/hc"
    os.makedirs(os_dir, exist_ok=True)
    for a in sys.argv[1:]:
        tt = float(a)
        render_frame(tt).save("%s/h_%05.2f.jpg" % (os_dir, tt), quality=90)
        print("saved", tt, flush=True)
