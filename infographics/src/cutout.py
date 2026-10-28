"""Вырезает бандажи с серого фона и приводит к «студийному» свету."""
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

SRC = "/tmp/arena-coding-uploads/"
OUT = "/home/user/-/infographics/src/"


def cutout(path, dark_thresh=22, soft=34):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    lum = a.mean(axis=2)
    bg = float(np.percentile(lum, 94))
    diff = np.clip(bg - lum, 0, None)
    alpha = np.clip((diff - dark_thresh) / soft, 0, 1)
    mask = Image.fromarray((alpha * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    mask = mask.point(lambda v: int(min(255, v * 1.15)))
    bbox = mask.point(lambda v: 255 if v > 40 else 0).getbbox()
    return im.crop(bbox), mask.crop(bbox)


def studio_grade(rgb, lift=1.06, contrast=1.12, cool=1.03):
    im = ImageEnhance.Brightness(rgb).enhance(lift)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    im = ImageEnhance.Color(im).enhance(0.55)
    r, g, b = im.split()
    r = r.point(lambda v: int(v * (2 - cool) / 2 + v * 0.5 * 0.0 + v * (cool - 1) * 0.5))
    b = b.point(lambda v: min(255, int(v * cool)))
    return Image.merge("RGB", (r, g, b))


if __name__ == "__main__":
    for i in (1, 2, 3):
        rgb, mask = cutout(SRC + f"{i}.jpg")
        tc = studio_grade(rgb)
        tc.putalpha(mask)
        tc.save(OUT + f"bandage_{i}.png")
        prev = Image.new("RGB", tc.size, (14, 16, 19))
        prev.paste(tc, (0, 0), tc)
        prev.save(OUT + f"prev_{i}.png")
        print(i, tc.size)
