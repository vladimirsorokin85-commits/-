"""Vertical 1080x1920 cover for the reel / Shorts, same style as THUMB v2."""
import os, numpy as np
import make_thumbs_v2 as m
from PIL import Image
m.W, m.H = 1080, 1920
im = m.bg("v2_bg1.jpg", 0.83)
# darken top and bottom for text
H = m.H
g = np.zeros(H)
g[:260] = np.linspace(120, 0, 260); g[950:] = np.linspace(0, 215, H - 950)
mask = Image.fromarray(np.tile(g[:, None], (1, m.W)).astype(np.uint8))
im = Image.composite(Image.new("RGB", (m.W, H)), im, mask)
m.mega(im, (40, 1080), "5 ХИТРОСТЕЙ", 170, maxw=960, rot=-5)
m.mega(im, (60, 1300), "ЗА КОПЕЙКИ", 150, top=(255, 255, 255), bot=(200, 220, 255), maxw=900, rot=-5)
m.sticker(im, (190, 1560), "СПАСАЮТ ЖИЗНЬ", 72, rot=4)
m.sticker(im, (210, 1760), "ПОЛНЫЙ ВЫПУСК — НА КАНАЛЕ", 40, bgc=(15, 15, 15), fg=(255, 204, 0), rot=0)
m.brand(im, (40, 40))
im.save(os.path.join(m.D, "REEL_COVER_vertical.jpg"), quality=93)
print("ok")
