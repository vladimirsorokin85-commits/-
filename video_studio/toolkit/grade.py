#!/usr/bin/env python3
"""grade.py — cinematic colour pipeline for stills/frames.

apply_lut(img, "kodak_2383_constlmap", strength)   real .cube film LUTs (toolkit/luts, MIT)
teal_orange(img, amt)                              blockbuster split-tone (shadows teal / skin orange)
halation(img)                                      film highlight bloom (red-orange glow around lights)
grain(img, amt, seed)                              luminance film grain
vignette(img, amt)
look(img, name)                                    presets: "frontline", "night_ops", "thermal", "archive"
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import map_coordinates

LUTS = Path(__file__).parent / "luts"


@lru_cache(maxsize=16)
def load_cube(name):
    size, rows = None, []
    for line in open(LUTS / f"{name}.cube"):
        t = line.strip().split()
        if not t or t[0].startswith("#"):
            continue
        if t[0] == "LUT_3D_SIZE":
            size = int(t[1])
        elif len(t) == 3:
            try:
                rows.append([float(v) for v in t])
            except ValueError:
                pass
    lut = np.array(rows, np.float32).reshape(size, size, size, 3)  # [b][g][r]
    return lut


def apply_lut(img: Image.Image, name: str, strength: float = 1.0) -> Image.Image:
    lut = load_cube(name)
    n = lut.shape[0]
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    idx = a * (n - 1)
    coords = [idx[..., 2].ravel(), idx[..., 1].ravel(), idx[..., 0].ravel()]
    out = np.stack([map_coordinates(lut[..., c], coords, order=1, mode="nearest") for c in range(3)], -1)
    out = out.reshape(a.shape)
    res = a * (1 - strength) + out * strength
    return Image.fromarray((res.clip(0, 1) * 255).astype(np.uint8))


def teal_orange(img, amt=0.35):
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114])
    sh = (1 - lum)[..., None] ** 2
    hi = lum[..., None] ** 2
    a = a + amt * (sh * np.array([-0.06, 0.03, 0.08]) + hi * np.array([0.08, 0.02, -0.07]))
    return Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8))


def halation(img, thr=0.82, radius=18, amt=0.45):
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    lum = a.max(-1)
    m = np.clip((lum - thr) / (1 - thr), 0, 1)
    glow = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    g = np.asarray(glow, np.float32)[..., None] / 255 * np.array([1.0, 0.45, 0.2])
    a = 1 - (1 - a) * (1 - g * amt)
    return Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8))


def grain(img, amt=0.05, seed=0, size=1.4):
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    h, w = a.shape[:2]
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (int(h / size), int(w / size))).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 0.18 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255 - 0.5
    lum = a.mean(-1, keepdims=True)
    a = a + n[..., None] * amt * 2 * (0.4 + 0.6 * (1 - np.abs(lum - 0.5) * 2))
    return Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8))


def vignette(img, amt=0.35):
    a = np.asarray(img.convert("RGB"), np.float32)
    h, w = a.shape[:2]
    y, x = np.mgrid[0:h, 0:w]
    r = ((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2
    a *= (1 - amt * np.clip(r - 0.25, 0, 1.5) / 1.5)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def thermal(img):
    """Ironbow thermal-camera look."""
    lum = np.asarray(img.convert("L"), np.float32) / 255
    stops = np.array([0, .25, .5, .75, 1.0])
    cols = np.array([[0, 0, 20], [80, 0, 140], [220, 40, 60], [255, 170, 0], [255, 255, 230]], np.float32)
    out = np.stack([np.interp(lum, stops, cols[:, c]) for c in range(3)], -1)
    return Image.fromarray(out.astype(np.uint8))


def look(img, name="frontline", seed=0):
    if name == "frontline":   # плёнка Kodak 2383 + лёгкий teal/orange, ореолы, зерно
        img = apply_lut(img, "kodak_2383_constlmap", 0.5)
        img = teal_orange(img, 0.22)
        img = halation(img, amt=0.35)
        img = vignette(img, 0.3)
        return grain(img, 0.035, seed)
    if name == "night_ops":
        img = apply_lut(img, "fuji_xtrans_iii_classic_chrome", 0.8)
        a = np.asarray(img, np.float32) * np.array([0.8, 0.95, 1.1])
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8))
        return grain(vignette(img, 0.45), 0.05, seed)
    if name == "thermal":
        return grain(thermal(img), 0.03, seed)
    if name == "archive":
        img = apply_lut(img, "kodak_tri-x_400", 1.0)
        return grain(vignette(img, 0.5), 0.08, seed)
    raise KeyError(name)
