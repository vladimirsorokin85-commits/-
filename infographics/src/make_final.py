#!/usr/bin/env python3
"""gen/*.png (сгенерированные слайды) -> out/*.jpg 1080x1350 (4:5) + PDF + ZIP."""
from pathlib import Path
import glob, os
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
GEN, OUT = ROOT / "gen", ROOT / "out"
OUT.mkdir(exist_ok=True)
TW, TH, TARGET = 1080, 1350, 4 / 5

for f in sorted(glob.glob(str(GEN / "*.png"))):
    im = Image.open(f).convert("RGB")
    w, h = im.size
    if w / h > TARGET:
        nw = int(h * TARGET); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    elif w / h < TARGET:
        nh = int(w / TARGET); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    im = im.resize((TW * 2, TH * 2), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=55, threshold=2))
    out = OUT / os.path.basename(f).replace(".png", ".jpg")
    im.resize((TW, TH), Image.LANCZOS).save(out, quality=94, subsampling=1)
    print("ok", out)

files = sorted(OUT.glob("*.jpg"))
imgs = [Image.open(p).convert("RGB") for p in files]
imgs[0].save(OUT / "bandage_infographic.pdf", save_all=True, append_images=imgs[1:], resolution=150.0)
print("ok", OUT / "bandage_infographic.pdf")
