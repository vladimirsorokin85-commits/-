#!/usr/bin/env python3
"""Specimen sheets: all fonts + all effect presets (toolkit/specimen_*.jpg)."""
import time
from pathlib import Path
from PIL import Image, ImageDraw
from typo import FAMILY, font, render, PRESETS, tape, Style, glitch_split

D = Path(__file__).parent
# 1) font specimen
fams = list(FAMILY)
W, rowh = 1800, 92
im = Image.new("RGB", (W, rowh * len(fams) + 30), (18, 20, 18))
d = ImageDraw.Draw(im)
for i, k in enumerate(fams):
    y = 15 + i * rowh
    d.text((20, y + 30), k, font=font("mono", 26), fill=(255, 204, 0))
    d.text((230, y + 6), "Окопная смекалка — ХИТРОСТЬ №1 · 500 ₽", font=font(k, 58), fill=(240, 240, 240))
    d.line((20, y + rowh - 4, W - 20, y + rowh - 4), fill=(45, 50, 45))
im.save(D / "specimen_fonts.jpg", quality=88)

# 2) effects over a real frame
bg = Image.open(D.parent / "assets" / "smekalka_12.jpg").convert("RGB").resize((1800, 1006)).point(lambda v: int(v * 0.55))
c = bg.convert("RGBA")
t = time.time()
items = [("gold", "ХИТРОСТЬ №1"), ("chrome", "ЗА КОПЕЙКИ"), ("fire", "НЕ ПРОЙДЁТ!"), ("blood", "СНАЙПЕР"),
         ("stencil", "ОКОПНАЯ СМЕКАЛКА"), ("steel", "БЛИНДАЖ"), ("soviet", "В ОКОПЕ"), ("hud", "ЦЕЛЬ ЗАХВАЧЕНА"),
         ("caption", "и блика больше нет"), ("caption_hot", "0 РУБЛЕЙ"), ("spray", "ВЫХОД"), ("marker", "смотри сюда!"),
         ("glitch", "ТЕПЛОВИЗОР")]
x, y, colw = 30, 20, 900
for n, (p, txt) in enumerate(items):
    lay = render(txt, PRESETS[p], size=96 if p not in ("caption", "caption_hot", "hud", "marker") else 70)
    if p == "glitch":
        lay = glitch_split(lay, 7)
    if lay.width > colw - 40:
        lay = lay.resize((colw - 40, int(lay.height * (colw - 40) / lay.width)))
    col, row = n % 2, n // 2
    px, py = 30 + col * colw, 20 + row * 140
    c.alpha_composite(lay, (px, py))
    ImageDraw.Draw(c).text((px + 4, py + 112), p, font=font("mono", 22), fill=(255, 204, 0))
c.alpha_composite(tape("СПАСАЮТ ЖИЗНЬ", 50), (950, 870))
c.alpha_composite(tape("0 ₽", 50, bg=(30, 160, 40), rot=5), (1500, 860))
c.convert("RGB").save(D / "specimen_effects.jpg", quality=90)
print("render time", round(time.time() - t, 1), "s")
