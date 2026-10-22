#!/usr/bin/env python3
"""
Extract clean RGBA PNG cutouts with intact shadow-side silhouettes and anti-aliased edges
from #000000 studio product shots, verified on BOTH dark and light backgrounds per image-continuity.md.
"""
import os
import numpy as np
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    binary_fill_holes,
    gaussian_filter,
    label,
)
from PIL import Image, ImageDraw

IMAGES_DIR = "/home/user/-/New_Video_bilder/assets/images"
OUT_DIR = "/home/user/-/New_Video_bilder/assets/cutouts"
os.makedirs(OUT_DIR, exist_ok=True)

ITEMS = [
    "gear_reb_dome.png",
    "gear_reb_array.png",
    "gear_detector_radar.png",
    "gear_radio_encrypted.png",
    "gear_fpv_vtx.png",
]

sheet = Image.new("RGB", (1800, 760), (20, 24, 28))
draw = ImageDraw.Draw(sheet)

for idx, fname in enumerate(ITEMS):
    im = Image.open(f"{IMAGES_DIR}/{fname}").convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    lum = np.max(arr, axis=2)

    # Pure #000000 studio background is <= 0.011; matte black plastic in deep shadow is 0.012..0.030.
    fg_raw = lum > 0.011
    # Bridge small shadow dips along object contours without merging separated antenna gaps
    fg_closed = binary_closing(fg_raw, structure=np.ones((9, 9), dtype=bool))
    lbl, _ = label(fg_closed)
    sizes = np.bincount(lbl.ravel())
    keep = np.isin(lbl, np.where(sizes > 800)[0])
    keep[lbl == 0] = False
    # Flood-fill only true exterior background connected to the 4 outer edges of the frame
    filled = binary_fill_holes(keep)

    eroded = binary_erosion(filled, iterations=1)
    alpha = gaussian_filter(eroded.astype(np.float32), sigma=1.15)
    alpha = np.clip((alpha - 0.14) / 0.80, 0.0, 1.0)

    denom = np.maximum(alpha[:, :, None], 0.22)
    edge_zone = (alpha > 0.01) & (alpha < 0.90)
    clean_rgb = arr.copy()
    clean_rgb[edge_zone] = np.clip(arr[edge_zone] / denom[edge_zone], 0.0, 1.0)

    ys, xs = np.where(alpha > 0.02)
    pad = 24
    x0, x1 = max(0, int(xs.min()) - pad), min(arr.shape[1], int(xs.max()) + pad)
    y0, y1 = max(0, int(ys.min()) - pad), min(arr.shape[0], int(ys.max()) + pad)

    rgba = np.zeros((y1 - y0, x1 - x0, 4), dtype=np.uint8)
    rgba[:, :, :3] = (clean_rgb[y0:y1, x0:x1] * 255.0).astype(np.uint8)
    rgba[:, :, 3] = (alpha[y0:y1, x0:x1] * 255.0).astype(np.uint8)

    out_im = Image.fromarray(rgba, mode="RGBA")
    out_im.thumbnail((960, 960), Image.Resampling.LANCZOS)
    out_name = fname.replace(".png", "_rgba.png")
    out_im.save(f"{OUT_DIR}/{out_name}", optimize=True)
    print(f"Saved {out_name}: {out_im.size}")

    col_x = idx * 360
    draw.rectangle([col_x, 0, col_x + 359, 379], fill=(15, 20, 26))
    draw.rectangle([col_x, 380, col_x + 359, 759], fill=(232, 236, 240))
    prev = out_im.copy()
    prev.thumbnail((310, 320), Image.Resampling.LANCZOS)
    ox = col_x + (360 - prev.width) // 2
    sheet.paste(prev, (ox, (380 - prev.height) // 2), prev)
    sheet.paste(prev, (ox, 380 + (380 - prev.height) // 2), prev)

sheet.save(f"{OUT_DIR}/_alpha_qa_sheet.jpg", quality=92)
print("Updated Alpha QA sheet written.")
