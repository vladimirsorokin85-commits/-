# -*- coding: utf-8 -*-
"""Готовит служебные ассеты каталога: hero-фото, заглушку, favicon."""
import os
import shutil

from PIL import Image, ImageDraw

K = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt"
CAT = os.path.join(K, "catalog")
IMGDIR = os.path.join(CAT, "assets", "img")
BRAND = os.path.join(IMGDIR, "brand")
os.makedirs(IMGDIR, exist_ok=True)

# 1) hero: официальное фото К-12М
src = os.path.join(K, "data", "photos", "stancziya-reb-kapyushon-k-12m", "01.jpg")
dst = os.path.join(IMGDIR, "hero-k12m.jpg")
if os.path.exists(src):
    im = Image.open(src).convert("RGBA")
    # убираем почти-белый фон в прозрачность (фото товара на белом)
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 243 and g > 243 and b > 243:
                px[x, y] = (r, g, b, 0)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    im.save(dst, "PNG")  # сохраняем как png-с-прозрачностью, но с именем .jpg? нет:
    os.remove(dst)
    dst = os.path.join(IMGDIR, "hero-k12m.png")
    im.save(dst, "PNG")
    print("hero:", dst, im.size)
else:
    print("НЕТ фото К-12М:", src)

# 2) заглушка «нет фото»
svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
<rect width="400" height="300" fill="#f3eee2"/>
<rect x="0.5" y="0.5" width="399" height="299" fill="none" stroke="#17180f" stroke-opacity="0.25"/>
<g stroke="#17180f" stroke-opacity="0.22">
<path d="M0 75H400M0 150H400M0 225H400M100 0V300M200 0V300M300 0V300"/>
</g>
<circle cx="200" cy="150" r="52" fill="none" stroke="#17180f" stroke-opacity="0.45"/>
<path d="M200 118v52M174 150h52" stroke="#17180f" stroke-opacity="0.45"/>
<text x="200" y="238" text-anchor="middle" font-family="Arial" font-size="11" letter-spacing="3" fill="#17180f" fill-opacity="0.5">ФОТО УТОЧНЯЕТСЯ</text>
</svg>"""
open(os.path.join(IMGDIR, "no-photo.svg"), "w", encoding="utf-8").write(svg)

# 3) favicon: тёмный квадрат + эмблема
emb = os.path.join(BRAND, "logo_w_emblem.png")
ico = Image.new("RGBA", (64, 64), (23, 24, 15, 255))
if os.path.exists(emb):
    e = Image.open(emb).convert("RGBA")
    e.thumbnail((50, 50), Image.LANCZOS)
    ico.paste(e, ((64 - e.width) // 2, (64 - e.height) // 2), e)
ico.save(os.path.join(BRAND, "favicon.png"), "PNG")
print("favicon ok")
