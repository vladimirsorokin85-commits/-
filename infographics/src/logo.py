#!/usr/bin/env python3
"""Логотип-патч «В ОКОПЕ» (как на обложках Reels) -> assets/logo_vokope.png + logo_vokope_small.png.

Рисуется кодом, поэтому всегда одинаковый и доступен в любом разрешении.
Патч: олива, стежки по краю, потёртости, тиснение букв.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT.parent / "video_studio" / "toolkit" / "fonts"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

OLIVE = (74, 84, 60)
OLIVE_HI = (96, 107, 78)
OLIVE_LO = (48, 55, 39)
KHAKI = (188, 176, 132)
TEXT = (232, 228, 210)


def noise(w, h, scale, seed, octaves=3):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        gw, gh = max(2, w // scale), max(2, h // scale)
        g = rng.random((gh, gw)).astype(np.float32)
        g = np.array(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                     dtype=np.float32) / 255.0
        out += g * amp
        total += amp
        amp *= 0.5
        scale = max(2, scale // 2)
    return out / total


def rounded_mask(w, h, r, inset=0):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([inset, inset, w - 1 - inset, h - 1 - inset],
                                        radius=r, fill=255)
    return m


def worn_edges(mask, seed=5, amount=0.35):
    """Слегка «съедает» край, чтобы патч не выглядел как векторный прямоугольник."""
    w, h = mask.size
    n = noise(w, h, 26, seed)
    arr = np.asarray(mask, dtype=np.float32) / 255.0
    edge = np.asarray(Image.fromarray((arr * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)),
                      dtype=np.float32) / 255.0
    bite = np.clip((n - 0.62) / 0.38, 0, 1) * amount
    arr = np.clip(arr - (1 - edge) * 0 - bite * (arr > 0.5), 0, 1)
    arr = np.clip(np.where(arr > 0.5, 1.0, arr), 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8))


def build(size=(1800, 700), text="В ОКОПЕ", star=True, stitch_c=True):
    W, H = size
    r = int(H * 0.16)

    # ---------- корпус патча ----------
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    body = Image.new("RGB", (W, H), OLIVE)
    # вертикальный градиент + тканевая фактура
    yy = np.linspace(0, 1, H)[:, None, None]
    arr = np.asarray(body, dtype=np.float32)
    grad = (1 - yy) * 1.06 + yy * 0.9
    arr = arr * grad
    fab = (noise(W, H, 5, 11, octaves=4)[..., None] - 0.5) * 26
    weave = (np.sin(np.arange(W)[None, :] * 1.4) * 3.0)[..., None]
    arr = np.clip(arr + fab + weave, 0, 255)
    body = Image.fromarray(arr.astype(np.uint8))

    mask = rounded_mask(W, H, r)
    mask = worn_edges(mask, seed=9, amount=0.55)
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))

    # внутренняя тень по краю (объём)
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(int(H * 0.05))), dtype=np.float32) / 255.0
    shade = (1 - inner)[..., None] * 70
    body = Image.fromarray(np.clip(np.asarray(body, dtype=np.float32) - shade, 0, 255).astype(np.uint8))
    body.putalpha(mask)
    base.alpha_composite(body)

    d = ImageDraw.Draw(base)

    # ---------- стежки ----------
    if stitch_c:
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        pad = int(H * (0.115 if star else 0.075))
        box = [pad, pad, W - 1 - pad, H - 1 - pad]
        # рваный пунктир по периметру скруглённого прямоугольника
        per = 2 * ((box[2] - box[0]) + (box[3] - box[1]))
        step = int(H * 0.072)
        dash = int(step * 0.56)
        n = int(per // step)
        for i in range(n):
            t0 = i * step / per
            t1 = (i * step + dash) / per
            for a, b in ((t0, t1),):
                # идём по периметру скруглённого прямоугольника
                for tt in np.linspace(a, b, 6):
                    x, y = point_on_rrect(box, int(H * 0.10), tt)
                    sd.ellipse([x - H * 0.011, y - H * 0.011, x + H * 0.011, y + H * 0.011],
                               fill=KHAKI + (215,))
        st = st.filter(ImageFilter.GaussianBlur(0.6))
        st.putalpha(Image.composite(st.getchannel("A"), Image.new("L", (W, H), 0), mask))
        base.alpha_composite(st)

    # ---------- текст ----------
    # автоподбор кегля: текст всегда влезает с полями
    fs = int(H * (0.46 if star else 0.40))
    while True:
        f = ImageFont.truetype(str(FONTS / "RussoOne-Regular.ttf"), fs)
        tw = d.textlength(text, font=f)
        if tw <= W * (0.84 if star else 0.80) or fs <= 12:
            break
        fs = int(fs * 0.94)
    tx = (W - tw) / 2
    ty = (H * 0.64 if star else H / 2) - fs * 0.62

    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    td.text((tx, ty), text, font=f, fill=TEXT + (255,))

    # тиснение: тёмная тень снизу-справа, светлый блик сверху-слева
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", (W, H), (26, 30, 20, 235)), (0, 0), txt.getchannel("A"))
    sh = sh.filter(ImageFilter.GaussianBlur(H * 0.006))
    base.alpha_composite(sh, (int(H * 0.006), int(H * 0.010)))

    hi = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hi.paste(Image.new("RGBA", (W, H), (196, 206, 160, 120)), (0, 0), txt.getchannel("A"))
    hi = hi.filter(ImageFilter.GaussianBlur(H * 0.005))
    base.alpha_composite(hi, (-int(H * 0.004), -int(H * 0.008)))

    # сама заливка с лёгким градиентом + фактура ткани внутри букв
    fill = Image.new("RGB", (W, H), TEXT)
    yy2 = np.linspace(0, 1, H)[:, None, None]
    fa = np.asarray(fill, dtype=np.float32) * ((1 - yy2) * 1.0 + yy2 * 0.86)
    fa += (noise(W, H, 4, 21)[..., None] - 0.5) * 14
    fill = Image.fromarray(np.clip(fa, 0, 255).astype(np.uint8)).convert("RGBA")
    fill.putalpha(txt.getchannel("A"))
    base.alpha_composite(fill)

    # ---------- звёздочка ----------
    if star:
        cx, cy = W / 2, H * 0.215
        rr = H * 0.085
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = rr if k % 2 == 0 else rr * 0.44
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        star_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(star_layer).polygon(pts, fill=KHAKI + (230,))
        base.alpha_composite(star_layer.filter(ImageFilter.GaussianBlur(0.4)))

    # финальный шум-грязь поверх всего патча
    grain = (noise(W, H, 3, 33, octaves=3) - 0.5) * 12
    ga = np.asarray(base, dtype=np.float32)
    ga[..., :3] = np.clip(ga[..., :3] + grain[..., None], 0, 255)
    return Image.fromarray(ga.astype(np.uint8))


def point_on_rrect(box, r, t):
    """Точка на периметре скруглённого прямоугольника, t в [0,1)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    straight_w = max(1, w - 2 * r)
    straight_h = max(1, h - 2 * r)
    arc = math.pi * r / 2
    per = 2 * straight_w + 2 * straight_h + 4 * arc
    s = t * per
    # верх
    if s < straight_w:
        return x0 + r + s, y0
    s -= straight_w
    if s < arc:
        a = -math.pi / 2 + (s / arc) * (math.pi / 2)
        return x1 - r + math.cos(a) * r, y0 + r + math.sin(a) * r
    s -= arc
    if s < straight_h:
        return x1, y0 + r + s
    s -= straight_h
    if s < arc:
        a = (s / arc) * (math.pi / 2)
        return x1 - r + math.cos(a) * r, y1 - r + math.sin(a) * r
    s -= arc
    if s < straight_w:
        return x1 - r - s, y1
    s -= straight_w
    if s < arc:
        a = math.pi / 2 + (s / arc) * (math.pi / 2)
        return x0 + r + math.cos(a) * r, y1 - r + math.sin(a) * r
    s -= arc
    if s < straight_h:
        return x0, y1 - r - s
    s -= straight_h
    a = math.pi + (s / arc) * (math.pi / 2)
    return x0 + r + math.cos(a) * r, y0 + r + math.sin(a) * r


if __name__ == "__main__":
    big = build((1800, 660), text="«В ОКОПЕ»", star=False)
    big.save(ASSETS / "logo_vokope.png")
    print("ok", ASSETS / "logo_vokope.png", big.size)

    # компактный вариант для футера/уголка
    small = build((1200, 440), text="«В ОКОПЕ»", star=False)
    small.save(ASSETS / "logo_vokope_small.png")
    print("ok", ASSETS / "logo_vokope_small.png", small.size)

    # вариант с эмблемой-звездой над текстом (для вертикальных макетов)
    emb = build((900, 900), text="«В ОКОПЕ»", star=True)
    emb.save(ASSETS / "logo_vokope_emblem.png")
    print("ok", ASSETS / "logo_vokope_emblem.png", emb.size)

    # превью на тёмном
    prev = Image.new("RGB", (big.width + 120, big.height + 120), (16, 18, 20))
    prev.paste(big, (60, 60), big)
    prev.save(ASSETS / "logo_preview.png")
