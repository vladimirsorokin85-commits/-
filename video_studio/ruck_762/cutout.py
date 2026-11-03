# -*- coding: utf-8 -*-
"""Рюкзак с фото заказчика → чистый PNG + отдельная карта тени.

Фон — светло-серая студийная заливка (≈ RGB 210/208/212). Что делаем:
1. «Фон» — пиксели, близкие к заливке по цвету, плюс нейтральные светлые
   (это ореол и мягкая тень). Объект — связная область от центра кадра.
2. Внутри объекта отдельно отделяем **тень**: нейтральные (насыщенность < 0.12)
   и не слишком тёмные пиксели. Тёмная стропа и сетка остаются в объекте.
3. На выходе два слоя: `assets/cut/<имя>.png` — сам рюкзак с альфой,
   `assets/shadow/<имя>.png` — чёрная карта тени с альфой. Тень кладётся на фон
   в композиции, поэтому рюкзак «стоит» на любой подложке без светлого ореола.
"""
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "assets")
DST = os.path.join(BASE, "assets", "cut")
SHA = os.path.join(BASE, "assets", "shadow")

NAMES = ["coyote_side", "coyote_front", "coyote_back", "coyote_cover",
         "khaki_side", "khaki_front", "khaki_back", "khaki_cover"]


def split(path, tol=26.0, shadow_max=0.55):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    bg = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
    bg_lum = float(bg.max())
    dist = np.sqrt(((a - bg) ** 2).sum(2))

    near = (dist < tol) | ((sat < 0.10) & (mx > 150))
    lab, _ = ndimage.label(~near)
    c = lab[a.shape[0] // 2, a.shape[1] // 2]
    if c == 0:  # центр попал в фон — берём самую крупную область
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        c = int(sizes.argmax())
    obj = lab == c
    obj = ndimage.binary_opening(obj, np.ones((3, 3)))
    obj = ndimage.binary_closing(obj, np.ones((9, 9)))
    lab2, k = ndimage.label(obj)
    if k > 1:
        sizes = ndimage.sum(obj, lab2, range(1, k + 1))
        obj = np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s > 400])

    # тень: нейтральная и не чёрная
    shadow = obj & (sat < 0.13) & (mx > 100) & (dist > tol)
    solid = obj & ~ndimage.binary_dilation(shadow, np.ones((3, 3)))
    # просветы фона внутри силуэта (между стропой и корпусом) — тоже прозрачные
    inner_bg = obj & (sat < 0.10) & (mx > 185)
    solid &= ~inner_bg
    lab3, k3 = ndimage.label(solid)
    if k3 > 1:  # мелкие «искры» после вырезания
        sizes = ndimage.sum(solid, lab3, range(1, k3 + 1))
        solid = np.isin(lab3, [i + 1 for i, sz in enumerate(sizes) if sz > 250])

    # «деспилл»: убираем серый ореол от фона внутри силуэта —
    # нейтральные светлые пиксели перекрашиваем в цвет ближайшей ткани
    fringe = solid & (sat < 0.16) & (mx > 118)
    if fringe.any():
        src_idx = ndimage.distance_transform_edt(fringe, return_distances=False, return_indices=True)
        a = a.copy()
        a[fringe] = a[src_idx[0][fringe], src_idx[1][fringe]]

    # мягкая альфа рюкзака
    al = Image.fromarray((solid * 255).astype(np.uint8), "L")
    al = al.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    bag = im.convert("RGBA")
    bag.putalpha(al)

    # карта тени: чем темнее пиксель, тем плотнее тень
    strength = np.clip((bg_lum - mx) / max(1.0, bg_lum - 90.0), 0, shadow_max)
    strength = np.where(shadow, strength, 0).astype(np.float32)
    sa = Image.fromarray((strength * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(6))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.putalpha(sa)

    box = al.getbbox()
    print("  %-14s рюкзак %.1f%%  тень %.1f%%" % (os.path.basename(path),
                                                   100 * solid.mean(), 100 * shadow.mean()))
    return bag.crop(box), sh.crop(box)


def main():
    os.makedirs(DST, exist_ok=True)
    os.makedirs(SHA, exist_ok=True)
    for n in NAMES:
        src = os.path.join(SRC, n + ".jpg")
        if not os.path.exists(src):
            continue
        bag, sh = split(src)
        bag.save(os.path.join(DST, n + ".png"))
        sh.save(os.path.join(SHA, n + ".png"))
        print("%-14s %s" % (n, bag.size))


if __name__ == "__main__":
    main()
