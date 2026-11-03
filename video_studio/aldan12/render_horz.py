# -*- coding: utf-8 -*-
"""«Алдан-12» — горизонталь 1920×1080, 30 fps.

Один кадр = одна реплика VO (тайминги из horizontal_timeline.json).
Шаблоны: карточка, шаг, функция, ошибка, чек-лист, план, финал + векторные схемы
(QR, антенны, USB, файлы A2/A1, LED, спектр Ascent, макет приложения).
Всё рисованное помечается «МАКЕТ» — это не выдаётся за реальный экран прибора.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = "/home/user/-/video_studio/aldan12"
A = os.path.join(BASE, "assets")
FONTS = "/home/user/-/video_studio/toolkit/fonts"
W, H = 1920, 1080
FPS = 30

BG = (8, 9, 10)
INK = (16, 18, 21)
TXT = (242, 243, 245)
DIM = (139, 146, 156)
ORG = (255, 122, 46)
TEA = (46, 200, 190)
RED = (226, 74, 62)

RUSSO = os.path.join(FONTS, "RussoOne-Regular.ttf")
DAYS = os.path.join(FONTS, "DaysOne-Regular.ttf")
MONO = os.path.join(FONTS, "JetBrainsMono-VF.ttf")
MONO_R = MONO

_cache = {}


def F(path, size):
    k = (path, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(path, size)
    return _cache[k]


def ac(c, a):
    return (c[0], c[1], c[2], int(max(0, min(255, a))))


def c01(x):
    return max(0.0, min(1.0, x))


def eo(x):
    return 1 - (1 - x) ** 3


# ── фоны ────────────────────────────────────────────────────────────────────
_BG_SRC = {}


REAL = {"hero_kit.jpg", "antennas.jpg", "watch_set.jpg", "watch_close.jpg"}


def pick_photo(name, block):
    if "ЧАС" in name:
        return "watch_set.jpg"
    if "КЕЙС" in name or "КОМПЛЕКТ" in name or "РУКОВОДСТВ" in name:
        return "hero_kit.jpg"
    if "АНТЕНН" in name:
        return "antennas.jpg"
    if "КАНАЛ" in name or "QR" in name or "ПРИЛОЖЕНИЕ" in name or "ВЕРСИЯ" in name:
        return "hands_phone.jpg"
    if "ASCENT" in name or "5800" in name or "CHANNEL" in name or "СИГНАЛ" in name:
        return "spectrum.jpg"
    if "LED" in name or "СВЕТОДИОД" in name or "ЯРКОСТ" in name:
        return "hero_kit.jpg"
    if "ЗАРЯД" in name or "КНОПК" in name or "ПРИБОР" in name:
        return "hero_kit.jpg"
    if "ДРОН" in name or "СРАБОТК" in name:
        return "drone_night.jpg"
    if "ПРОШИВК" in name or "ОБНОВЛЕНИ" in name or "СБРОС" in name:
        return "hands_phone.jpg"
    return {"7": "spectrum.jpg", "8": "watch_set.jpg", "6": "dark_table.jpg",
            "3": "hands_phone.jpg", "4": "roof_antenna.jpg", "5": "firmware_drop.jpg",
            "9": "firmware_drop.jpg", "10": "hands_phone.jpg",
            "11": "drone_night.jpg", "2": "drone_night.jpg", "1": "hero_kit.jpg"}.get(str(block), "dark_table.jpg")


def bg_src(name, w=2400):
    k = (name, w)
    if k not in _BG_SRC:
        im = Image.open(os.path.join(A, name)).convert("RGB")
        h = int(im.height * w / im.width)
        _BG_SRC[k] = im.resize((w, h), Image.LANCZOS)
    return _BG_SRC[k]


def grade(im, dark=0.45, contrast=1.18, tint=(30, 60, 70), amt=0.07):
    a = np.asarray(im).astype(np.float32)
    a[:, :, 0] = a[:, :, 0] * (1 - amt) + tint[0] * amt
    a[:, :, 1] = a[:, :, 1] * (1 - amt) + tint[1] * amt
    a[:, :, 2] = a[:, :, 2] * (1 - amt) + tint[2] * amt
    a = (a - 110) * contrast + 96
    a *= dark
    a = np.clip(a, 0, 255) ** 1.10
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def background(name, z=1.06, ox=0.0, oy=0.0, dark=0.42, tint=(30, 60, 70), amt=0.07):
    """Кроп из подготовленного фото → 1920×1080 (Ken Burns без ресайза каждый кадр)."""
    src = bg_src(name)
    sw, sh = src.size
    cw, ch = sw / z, sh / z
    cx = sw / 2 + ox * (sw - cw) / 2
    cy = sh / 2 + oy * (sh - ch) / 2
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    im = src.resize((W, H), Image.BILINEAR, box=box)
    return grade(im, dark, 1.18, tint, amt)


# ── текст ───────────────────────────────────────────────────────────────────
def fit(text, font_path, size, max_w, min_size=22):
    while size > min_size:
        f = F(font_path, size)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= max_w:
            return f
        size -= 2
    return F(font_path, min_size)


def title(d, x, y, text, size=96, color=TXT, font=RUSSO, max_w=1560, anchor="la",
          accent=None, accent_color=ORG):
    """Крупный титр; часть после «·» — акцентным цветом (если помечено «|»)."""
    if "|" in text:
        head, tail = text.split("|", 1)
        head, tail = head.strip(), tail.strip()
    else:
        head, tail = text, ""
    f1 = fit(head, font, size, max_w)
    d.text((x, y), head, font=f1, fill=color, anchor=anchor)
    if tail:
        f2 = fit(tail, font, int(size * 0.92), max_w)
        off = (f1.getbbox(head)[3] - f1.getbbox(head)[1]) + 16
        yy = y + (off if anchor.startswith("l") else 0)
        d.text((x, yy), tail, font=f2, fill=accent_color, anchor="la")
    return y


def chip(d, x, y, text, color=ORG, size=26, pad=18, alpha=255, fill_box=True, anchor="la"):
    f = F(MONO, size)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    hh = th + pad * 2
    if fill_box:
        d.rectangle([x, y, x + tw + pad * 2 + 8, y + hh], fill=ac((10, 12, 15), int(200 * alpha / 255)),
                    outline=ac(color, int(200 * alpha / 255)))
        d.rectangle([x, y, x + 6, y + hh], fill=ac(color, alpha))
    d.text((x + pad + 12, y + pad - bb[1] + 2), text, font=f, fill=ac(color, alpha))
    return x + tw + pad * 2 + 8


def wrap(text, font, max_w, max_lines=3):
    words, lines, cur = text.split(), [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        if font.getbbox(probe)[2] - font.getbbox(probe)[0] <= max_w or not cur:
            cur = probe
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines


def vo_echo(d, text, y, alpha=255, x=92, max_w=800, color=DIM, size=31):
    """Строка-эхо речи слева: 2–3 строки моно, чтобы кадр не пустовал."""
    f = F(MONO, size)
    ls = wrap(text, f, max_w, 3)
    if len(ls) == 3 and text.split()[-1] not in " ".join(ls):
        ls[-1] = ls[-1].rstrip(" ,.—-") + "…"
    for n, ln in enumerate(ls):
        d.text((x, y + n * (size + 12)), ln, font=f, fill=ac(color, int(alpha * 0.92)))


def number_block(d, x, y, num, label, color=ORG):
    d.text((x, y), num, font=F(RUSSO, 260), fill=ac(color, 235), anchor="la")
    d.text((x + 8, y + 300), label, font=F(MONO, 30), fill=ac(DIM, 235), anchor="la")


# ── векторная графика ───────────────────────────────────────────────────────
def art_qr(cv, x, y, s=300, alpha=255, t=0.0):
    d = ImageDraw.Draw(cv)
    step = s / 21
    for i in range(21):
        for j in range(21):
            corner = (i < 7 and j < 7) or (i < 7 and j > 13) or (i > 13 and j < 7)
            on = corner or random.Random(i * 31 + j * 17).random() > 0.52
            if on:
                d.rectangle([x + j * step, y + i * step, x + (j + 1) * step - 1.2,
                             y + (i + 1) * step - 1.2], fill=ac((235, 238, 242), alpha))
    for (ox, oy) in ((0, 0), (14, 0), (0, 14)):
        d.rectangle([x + ox * step, y + oy * step, x + (ox + 7) * step, y + (oy + 7) * step],
                    outline=ac(ORG, alpha), width=5)
    sweep = (t * 0.8) % 1.0
    d.rectangle([x, y + s * sweep, x + s, y + s * sweep + 6], fill=ac(ORG, int(120 * alpha / 255)))


def art_antenna(cv, cx, cy, alpha=255, t=0.0):
    d = ImageDraw.Draw(cv)
    d.rounded_rectangle([cx - 90, cy + 40, cx + 90, cy + 330], 24, fill=ac((28, 31, 37), alpha),
                        outline=ac(ORG, int(200 * alpha / 255)), width=4)
    for i in range(3):
        d.rounded_rectangle([cx - 66 + i * 46, cy + 250, cx - 26 + i * 46, cy + 300], 8,
                            fill=ac((60, 64, 72), alpha))
    for (dx, hh, wd) in ((-150, 300, 34), (0, 210, 26), (150, 300, 34)):
        pulse = 0.6 + 0.4 * math.sin(t * 3 + dx)
        d.rounded_rectangle([cx + dx - wd, cy + 40 - hh, cx + dx + wd, cy + 40], wd,
                            fill=ac((34, 38, 44), alpha), outline=ac(TEA, int(160 * pulse * alpha / 255)), width=3)


def art_usb(cv, x, y, alpha=255, t=0.0):
    d = ImageDraw.Draw(cv)
    d.rounded_rectangle([x, y, x + 420, y + 130], 26, fill=ac((24, 27, 33), alpha),
                        outline=ac(TEA, int(200 * alpha / 255)), width=4)
    d.rounded_rectangle([x + 30, y + 32, x + 250, y + 98], 16, outline=ac((170, 178, 188), alpha), width=4)
    d.rounded_rectangle([x + 300, y + 46, x + 392, y + 84], 10, fill=ac(ORG, alpha))
    d.text((x + 30, y + 146), "USB TYPE-C", font=F(MONO, 28), fill=ac(DIM, alpha))


def art_files(cv, x, y, alpha=255):
    d = ImageDraw.Draw(cv)
    for i, (nm, model, col) in enumerate((("A2", "«АЛДАН-12»", ORG), ("A1", "«АЛДАН-8»", TEA))):
        bx = x + i * 330
        d.rounded_rectangle([bx, y, bx + 290, y + 250], 22, fill=ac((18, 21, 26), alpha),
                            outline=ac(col, int(210 * alpha / 255)), width=4)
        d.text((bx + 26, y + 26), nm, font=F(RUSSO, 96), fill=ac(col, alpha))
        d.text((bx + 28, y + 146), "ФАЙЛ ПРОШИВКИ", font=F(MONO, 22), fill=ac(DIM, alpha))
        d.text((bx + 28, y + 186), model, font=F(MONO, 28), fill=ac(TXT, alpha))


def art_led(cv, cx, cy, on, alpha=255, t=0.0):
    d = ImageDraw.Draw(cv)
    d.rounded_rectangle([cx - 120, cy - 120, cx + 120, cy + 120], 26, fill=ac((20, 22, 27), alpha),
                        outline=ac(DIM, int(120 * alpha / 255)), width=3)
    r = 34 + (8 * math.sin(t * 6) if on else 0)
    col = (ORG if on else (60, 64, 70))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ac(col, alpha))
    d.text((cx, cy + 150), "ВКЛ" if on else "ВЫКЛ", font=F(MONO, 28),
           fill=ac(ORG if on else DIM, alpha), anchor="ma")


def art_spectrum(cv, x, y, w, h, alpha=255, t=0.0, label="5800 МГЦ"):
    d = ImageDraw.Draw(cv)
    n = 44
    for i in range(n):
        hh = (0.25 + 0.75 * abs(math.sin(i * 0.7 + t * 2.4))) * h
        xx = x + i * (w / n)
        d.rectangle([xx, y + h - hh, xx + w / n - 5, y + h],
                    fill=ac(TEA if i % 5 else ORG, int(alpha * (0.5 + 0.5 * hh / h))))
    d.text((x, y - 44), label, font=F(MONO, 30), fill=ac(TXT, alpha))


def art_phone(cv, x, y, alpha=255, t=0.0, screen="update"):
    """Макет телефона: подпись «МАКЕТ» обязательна."""
    d = ImageDraw.Draw(cv)
    pw, ph = 300, 600
    d.rounded_rectangle([x, y, x + pw, y + ph], 34, fill=ac((14, 16, 20), alpha),
                        outline=ac(ORG, int(220 * alpha / 255)), width=4)
    d.rectangle([x + 16, y + 58, x + pw - 16, y + ph - 20], fill=ac((8, 10, 13), alpha))
    d.rounded_rectangle([x + 110, y + 24, x + pw - 110, y + 42], 10, fill=ac((40, 44, 52), alpha))
    rows = [("МЕСТНАЯ ПРОШИВКА", ORG), ("ПОМОЩНИК ОБНОВЛЕНИЯ", TEA),
            ("ПРОВЕРИТЬ ВЕРСИЮ ПО", DIM), ("ФАЙЛ: A2", DIM)]
    for i, (txt, col) in enumerate(rows):
        yy = y + 90 + i * 92
        d.rectangle([x + 32, yy, x + pw - 32, yy + 70], fill=ac((20, 24, 30), alpha),
                    outline=ac(col, int(120 * alpha / 255)))
        d.text((x + 46, yy + 24), txt, font=F(MONO, 17), fill=ac(col, alpha))
    if screen == "progress":
        k = (t * 0.5) % 1.0
        d.rectangle([x + 32, y + 470, x + pw - 32, y + 500], fill=ac((30, 34, 40), alpha))
        d.rectangle([x + 32, y + 470, x + 32 + (pw - 64) * k, y + 500], fill=ac(ORG, alpha))
    d.text((x + pw / 2, y + ph + 14), "МАКЕТ · НЕ ЭКРАН ПРИБОРА", font=F(MONO, 20),
           fill=ac(RED, int(230 * alpha / 255)), anchor="ma")


def art_buttons(cv, cx, cy, alpha=255, t=0.0):
    d = ImageDraw.Draw(cv)
    bw, bh = 260, 420
    d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 28,
                        fill=ac((22, 25, 31), alpha), outline=ac(ORG, int(200 * alpha / 255)), width=4)
    d.rounded_rectangle([cx - bw / 2 + 34, cy - bh / 2 + 44, cx + bw / 2 - 34, cy - bh / 2 + 190], 14,
                        fill=ac((8, 10, 13), alpha), outline=ac(DIM, int(100 * alpha / 255)))
    d.text((cx, cy - bh / 2 + 118), "АЛДАН-12", font=F(MONO, 26), fill=ac(DIM, alpha), anchor="mm")
    for ky, lab, ph in ((cy - bh / 2 + 40, "ВЕРХНЯЯ", 0.0), (cy - bh / 2 + 210, "НИЖНЯЯ", 0.5)):
        pulse = 0.55 + 0.45 * math.sin(t * 3.2 - ph * 6.28)
        d.rounded_rectangle([cx - bw / 2 - 30, ky, cx - bw / 2 + 14, ky + 96], 12,
                            fill=ac(ORG, int((150 + 100 * pulse) * alpha / 255)))
        d.text((cx + bw / 2 + 34, ky + 44), lab, font=F(MONO, 24), fill=ac(TEA, alpha), anchor="lm")


# ── слои поверх всего ───────────────────────────────────────────────────────
def make_scan():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, 20))
    return im


def make_vign():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(90):
        k = i / 90
        ins = int(-260 + k * 420)
        d.ellipse([ins, ins * 0.62, W - ins, H - ins * 0.62], outline=(0, 0, 0, int(3 + k * 2)), width=6)
    return im.filter(ImageFilter.GaussianBlur(24))


SCAN = make_scan()
VIGN = make_vign()
SCANVIGN = Image.alpha_composite(SCAN, VIGN)
_r = np.random.default_rng(11)
GRAIN = []
for _ in range(4):
    n = _r.integers(0, 26, (H // 3, W // 3), dtype=np.uint8)
    g = Image.fromarray(n).resize((W, H), Image.NEAREST)
    GRAIN.append(Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 14))))

# ── HUD ─────────────────────────────────────────────────────────────────────
BLOCKS_T = {1: "ХУК", 2: "РАМКА", 3: "ШАГИ 1–2", 4: "ШАГИ 3–5", 5: "ШАГИ 6–8",
            6: "ФАЙЛЫ A2 / A1", 7: "ПЯТЬ ФУНКЦИЙ", 8: "«АЛДАН-8» И ЧАСЫ",
            9: "ОШИБКИ", 10: "ЧЕК-ЛИСТ", 11: "ПЛАНЫ"}


def hud(d, t, total, block, shot_no):
    d.rectangle([0, 0, W, 4], fill=ac(ORG, 235))
    d.text((64, 26), "«В ОКОПЕ»", font=F(RUSSO, 34), fill=ac(TXT, 245))
    d.text((300, 40), "АЛДАН-12  //  ПРОШИВКА 1.6", font=F(MONO, 22), fill=ac(DIM, 235))
    lab = f"{block:02d} · {BLOCKS_T.get(block, '')}"
    d.text((W - 64, 40), lab, font=F(MONO, 24), fill=ac(ORG, 235), anchor="ra")
    d.text((W - 64, 74), f"КАДР {shot_no:02d}/90", font=F(MONO, 18), fill=ac(DIM, 200), anchor="ra")
    # прогресс
    k = c01(t / total)
    d.rectangle([0, H - 8, W, H], fill=(20, 22, 26, 255))
    d.rectangle([0, H - 8, W * k, H], fill=ac(ORG, 255))
    # нижняя строка
    d.text((64, H - 52), "t.me/vokope_ru", font=F(MONO, 22), fill=ac(DIM, 210))
    d.text((300, H - 52), "•  vk.com/vokope_rus", font=F(MONO, 22), fill=ac(DIM, 210))
    d.text((W - 64, H - 52), "АЛДАН-12 · ОБНОВЛЕНИЕ ПРОШИВКИ", font=F(MONO, 20),
           fill=ac(DIM, 190), anchor="ra")


# ── определение шаблона ─────────────────────────────────────────────────────
def kind_of(name, block):
    if name.startswith("ШАГ "):
        return "step"
    if name.startswith("ФУНКЦИЯ "):
        return "feature"
    if name.startswith("ОШИБКА "):
        return "error"
    if name.startswith("ЧЕК-ЛИСТ"):
        return "check"
    if name.startswith("ПЛАН "):
        return "plan"
    return "card"


BG_BY_BLOCK = {1: "drone_night.jpg", 2: "dark_table.jpg", 3: "hands_phone.jpg",
               4: "roof_antenna.jpg", 5: "firmware_drop.jpg", 6: "dark_table.jpg",
               7: "spectrum.jpg", 8: "roof_antenna.jpg", 9: "firmware_drop.jpg",
               10: "hands_phone.jpg", 11: "drone_night.jpg"}


_BASECACHE = {}
_CACHE_ORDER = []


def base_layer(i, block):
    """Фон сцены + левая плашка. Внутри сцены не меняется — кэшируем (LRU 3)."""
    if i in _BASECACHE:
        return _BASECACHE[i].copy()
    z = 1.07 + 0.03 * math.sin(i * 0.7)
    ox = 0.35 * math.sin(i * 1.7)
    bgname = BG_BY_BLOCK.get(block, "dark_table.jpg")
    cv = Image.new("RGBA", (W, H), ac(BG, 255))
    cv.paste(background(bgname, z, ox, 0.0, 0.40, (30, 60, 70), 0.07), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    dd.rectangle([0, 0, 980, H], fill=(6, 7, 9, 212))          # левая плашка под текст
    dd.rectangle([940, 0, 980, H], fill=ac(ORG, 90))
    cv.alpha_composite(ov)
    _BASECACHE[i] = cv
    _CACHE_ORDER.append(i)
    while len(_CACHE_ORDER) > 3:
        _BASECACHE.pop(_CACHE_ORDER.pop(0), None)
    return cv.copy()


def shot_image(i, name, block, lt, total_d, vo_text=""):
    """Один кадр сцены (без HUD/эффектов склейки)."""
    cv = base_layer(i, block)

    k = kind_of(name, block)
    a1 = eo(c01(lt / 0.34))
    a2 = eo(c01((lt - 0.16) / 0.34))
    # текст рисуем в отдельный слой и поднимаем при появлении
    tlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(tlay)

    # ── правый визуальный блок: всегда что-то живое
    rx, ry = 1180, 300
    if "QR" in name:
        art_qr(cv, rx + 60, ry - 40, 300, int(250 * a2), lt)
        chip(d, rx + 60, ry + 300, "QR → «АЛДАН-ИНФОРМАЦИЯ»", TEA, 22, 14, int(235 * a2))
    elif "АНТЕНН" in name:
        art_antenna(cv, rx + 250, ry + 120, int(250 * a2), lt)
        chip(d, rx + 60, ry + 500, "МАЛАЯ В ЦЕНТРЕ · ДВЕ ПО КРАЯМ", TEA, 20, 14, int(235 * a2))
    elif "USB" in name or "OTG" in name or "РАЗЪЁМ" in name:
        art_usb(cv, rx + 20, ry + 60, int(250 * a2), lt)
        if "РЕЖИМ" in name or "КНОПК" in name:
            art_buttons(cv, rx + 250, ry + 420, int(240 * a1), lt)
    elif "A2" in name or "A1" in name or "ФАЙЛ" in name or (
            block == 6 and "ПРИЛОЖЕНИЕ" not in name and "КАНАЛ" not in name):
        art_files(cv, rx + 20, ry + 130, int(250 * a2))
        chip(d, rx + 20, ry + 400, "A2 — 12 · A1 — 8", ORG, 22, 14, int(235 * a2))
    elif "LED" in name or "СВЕТОДИОД" in name:
        art_led(cv, rx + 240, ry + 230, on=("ВЫКЛ" not in name and "выкл" not in name), alpha=int(250 * a2), t=lt)
    elif "ASCENT" in name or "5800" in name or "CHANNEL" in name:
        art_spectrum(cv, rx + 20, ry + 250, 560, 220, int(250 * a2), lt, "5800 МГЦ · CHANNEL 5")
    elif "ПРИЛОЖЕНИЕ" in name or "ЭКРАН" in name or "ВЕРСИЯ" in name or "ПОМОЩНИК" in name:
        art_phone(cv, rx + 130, ry - 30, int(250 * a2), lt, "progress" if "ПРОГРЕСС" in name else "update")
    elif "ЧАСЫ" in name:
        d.rounded_rectangle([rx + 40, ry + 60, rx + 560, ry + 560], 24, fill=ac((10, 12, 16), 220),
                            outline=ac(TEA, int(200 * a2)), width=4)
        cv.alpha_composite(_photo("watch_close.jpg", (rx + 56, ry + 76), 488, int(240 * a2)))
        d.text((rx + 300, ry + 580), "ЧАСЫ ОПОВЕЩЕНИЯ · 5T", font=F(MONO, 22),
               fill=ac(TEA, int(235 * a2)), anchor="ma")
    elif "КЕЙС" in name or "РУКОВОДСТВ" in name or "КОМПЛЕКТ" in name:
        cv.alpha_composite(_photo("hero_kit.jpg", (rx + 60, ry + 40), 520, int(245 * a2)))
        chip(d, rx + 60, ry + 600, "«АЛДАН-12» · КОМПЛЕКТ", ORG, 22, 14, int(235 * a2))
    else:
        ph = pick_photo(name, block)
        pw = 600
        phh = int(Image.open(os.path.join(A, ph)).height * pw / Image.open(os.path.join(A, ph)).width)
        phh = min(phh, 640)
        cv.alpha_composite(_photo(ph, (rx + 40, ry + 40), pw, int(240 * a2)))
        real = ph in REAL
        chip(d, rx + 40, ry + 40 + phh + 22,
             "«АЛДАН-12» · ФОТО" if real else "ИЛЛЮСТРАЦИЯ", ORG if real else TEA,
             22, 14, int(230 * a2))

    # ── левая колонка: текст (въезд снизу)
    if k == "step":
        num = name.split()[1]
        d.text((90, 210), num, font=F(RUSSO, 250), fill=ac(ORG, int(240 * a1)), anchor="la")
        rest = name.split("·", 1)[1].strip() if "·" in name else ""
        f = fit(rest, RUSSO, 84, 780)
        d.text((92, 480), rest, font=f, fill=ac(TXT, int(255 * a2)))
        d.text((92, 200), "ШАГ", font=F(MONO, 30), fill=ac(DIM, int(230 * a1)))
    elif k in ("feature", "error", "plan"):
        head = name.split("·")[0].strip()
        rest = name.split("·", 1)[1].strip() if "·" in name else ""
        col = RED if k == "error" else (TEA if k == "feature" else ORG)
        d.text((92, 236), head, font=fit(head, MONO, 34, 760), fill=ac(col, int(245 * a1)))
        d.text((92, 300), rest, font=fit(rest, RUSSO, 92, 800), fill=ac(TXT, int(255 * a2)))
        d.rectangle([92, 300 + 130, 92 + 180, 300 + 136], fill=ac(col, int(240 * a2)))
        d.text((92, 470), f"ABLДАН-12" if False else "ПРОШИВКА 1.6 · ФАКТБАЗА ПРОИЗВОДИТЕЛЯ",
               font=F(MONO, 24), fill=ac(DIM, int(220 * a2)))
    elif k == "check":
        d.text((92, 210), name, font=fit(name, RUSSO, 84, 800), fill=ac(TXT, int(255 * a1)))
        items = (["ЗАРЯД ≥ 1 ДЕЛЕНИЯ", "АНТЕННЫ НА МЕСТЕ", "ДРОН РЯДОМ ВЫКЛЮЧЕН",
                  "ЗАГЛУШКА ОТКРЫТА, КАБЕЛЬ ПОД РУКОЙ"] if "1–4" in name else
                 ["OTG ВКЛЮЧЁН", "ПРИЛОЖЕНИЕ 1.2.6", "ФАЙЛ A2 СКАЧАН", "ТЕЛЕФОН ЗАРЯЖЕН"])
        for n, it in enumerate(items):
            yy = 350 + n * 86
            q = c01((lt - 0.2 - n * 0.12) / 0.3)
            d.rectangle([92, yy, 136, yy + 44], outline=ac(TEA, int(220 * q)), width=3)
            if q > 0.5:
                d.line([(100, yy + 22), (112, yy + 34), (130, yy + 10)], fill=ac(TEA, int(255 * q)), width=5)
            d.text((160, yy + 4), it, font=F(MONO, 30), fill=ac(TXT, int(245 * q)))
    else:
        ttl = name if name else "АЛДАН-12"
        size = 108 if len(ttl) <= 20 else 82
        f = fit(ttl, RUSSO, size, 800)
        d.text((92, 300), ttl, font=f, fill=ac(TXT, int(255 * a1)))
        d.rectangle([92, 300 + (f.getbbox(ttl)[3] - f.getbbox(ttl)[1]) + 40,
                     92 + 220, 300 + (f.getbbox(ttl)[3] - f.getbbox(ttl)[1]) + 48],
                    fill=ac(ORG, int(240 * a1)))
        d.text((92, 210), f"БЛОК {block:02d} · {BLOCKS_T.get(block, '')}", font=F(MONO, 26),
               fill=ac(ORG, int(240 * a1)))
        cy = 300 + (f.getbbox(ttl)[3] - f.getbbox(ttl)[1]) + 96
        chip(d, 92, cy, "ИСТОЧНИК · ПРОИЗВОДИТЕЛЬ", TEA, 22, 14, int(225 * a2))
        chip(d, 92, cy + 62, "БЕЗ ТТХ · БЕЗ ЦЕН", DIM, 22, 14, int(215 * a2))
        d.text((92, H - 150), "ПРОШИВКА 1.6  ·  ФАЙЛ A2  ·  8 ШАГОВ  ·  5 ФУНКЦИЙ",
               font=F(MONO, 24), fill=ac(DIM, int(190 * a2)))

    # эхо реплики (кроме чек-листа, где уже есть список)
    if k != "check" and vo_text:
        vo_echo(d, vo_text, 640 if k == "card" else 700, int(240 * a2))

    rise = int(26 * (1 - a1))
    cv.alpha_composite(tlay, (0, rise))
    return cv


def _photo(name, xy, w, alpha=255):
    src = Image.open(os.path.join(A, name)).convert("RGB")
    h = int(src.height * w / src.width)
    im = grade(src.resize((w, h), Image.LANCZOS), 0.62, 1.2, (30, 60, 70), 0.05)
    im = im.convert("RGBA")
    im.putalpha(alpha)
    lay = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    lay.alpha_composite(im, (1, 1))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, w + 1, h + 1], outline=ac(ORG, int(200 * alpha / 255)), width=3)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(lay, xy)
    return out


def endcard(t, alpha):
    cv = Image.new("RGBA", (W, H), ac((5, 6, 8), 255))
    d = ImageDraw.Draw(cv)
    d.rectangle([0, 0, W, 6], fill=ac(ORG, 255))
    d.text((W // 2, 300), "«В ОКОПЕ»", font=F(RUSSO, 128), fill=ac(TXT, int(255 * alpha)), anchor="ma")
    d.text((W // 2, 460), "АЛДАН-12 · ОБНОВЛЕНИЕ ПРОШИВКИ", font=F(MONO, 32),
           fill=ac(ORG, int(245 * alpha)), anchor="ma")
    for i, txt in enumerate(("t.me/vokope_ru", "vk.com/vokope_rus", "avito.ru/brands/…")):
        q = c01((alpha - 0.15 - i * 0.14) / 0.6)
        d.text((W // 2, 600 + i * 90), txt, font=F(MONO, 44), fill=ac(TXT, int(250 * q)), anchor="ma")
    blink = 0.82 + 0.18 * math.sin(t * 5)
    d.text((W // 2, 940), "ПОДПИСЫВАЙТЕСЬ", font=F(RUSSO, 54),
           fill=ac(ORG, int(255 * blink * alpha)), anchor="ma")
    return cv


# ── финальный рендер кадра ─────────────────────────────────────────────────
def render(i, name, block, t, t0, dur, total, last=False, vo_text=""):
    lt = t - t0
    mid = dur > 4.4 and lt > dur * 0.52
    cv = shot_image(i, name, block, lt, dur, vo_text)
    if last and lt > max(0.6, dur - 3.6):
        k = eo(c01((lt - max(0.6, dur - 3.6)) / 0.45))
        cv = Image.composite(endcard(t, k), cv, Image.new("L", (W, H), int(255 * k)))
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not (last and lt > max(0.6, dur - 3.6) + 0.45):
        hud(ImageDraw.Draw(ui), t, total, block, i)
    out = Image.alpha_composite(cv, ui)
    out = Image.alpha_composite(out, SCANVIGN)
    out = Image.alpha_composite(out, GRAIN[int(t * 15) % 4])
    out = out.convert("RGB")

    # зум-панч на склейке
    dd = lt
    if dd < 0.16:
        kk = 1 - dd / 0.16
        z = 1 + 0.045 * kk
        cw, ch = int(W / z), int(H / z)
        out = out.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)) \
                 .resize((W, H), Image.BILINEAR)
    if mid:
        # микро-джампкат: другая крупность, эффект «нового плана» без новой сцены
        z = 1.028
        cw, ch = int(W / z), int(H / z)
        out = out.crop(((W - cw) // 2, (H - ch) // 2 + 6, (W + cw) // 2, (H + ch) // 2 + 6)) \
                 .resize((W, H), Image.BILINEAR)
    arr = np.asarray(out).astype(np.float32)
    beat = (t / (60 / 120)) % 1.0
    arr *= 1.0 + 0.016 * math.exp(-beat * 7)
    if lt < 0.12:
        fl = (1 - lt / 0.12) * 0.22
        arr = arr * (1 - fl) + np.array([255, 255, 255], np.float32) * fl
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def load_plan():
    tl = os.path.join(BASE, "horizontal_timeline.json")
    if os.path.exists(tl):
        data = json.load(open(tl, encoding="utf-8"))
        lines = data["lines"]
        total = data["total"]
    else:
        sys.path.insert(0, BASE)
        import shots
        t, lines = 0.55, []
        prev = None
        acc = 0.0
        for n, (blk, nm, vo, vis, sfx, d) in enumerate(shots.SHOTS, 1):
            gap = 0.62 if prev not in (None, blk) else (0.0 if prev is None else 0.26)
            t += gap
            lines.append({"n": n, "block": blk, "name": nm, "start": round(t, 3), "dur": d, "text": vo})
            t += d
            prev = blk
        total = round(t + 1.15, 2)
    sys.path.insert(0, BASE)
    import shots
    for n, it in enumerate(lines):
        it["name"] = shots.SHOTS[n][1]
        it["block"] = shots.SHOTS[n][0]
        nxt = lines[n + 1]["start"] if n + 1 < len(lines) else total
        it["end"] = nxt
    return lines, total


def at(t, lines):
    cur = lines[0]
    for it in lines:
        if t >= it["start"] - 1e-6:
            cur = it
    return cur


if __name__ == "__main__":
    os.makedirs("/tmp/chk", exist_ok=True)
    lines, total = load_plan()
    print(f"кадров {len(lines)} · итог {total:.2f}s = {int(total // 60):02d}:{total % 60:04.1f}")
    for a in sys.argv[1:]:
        tt = float(a)
        it = at(tt, lines)
        im = render(it["n"], it["name"], it["block"], tt, it["start"], it["end"] - it["start"], total,
                    last=(it["n"] == len(lines)), vo_text=it.get("text", ""))
        im.save(f"/tmp/chk/hz_{tt:06.2f}.jpg", quality=90)
        print("saved", tt, "кадр", it["n"], it["name"])
