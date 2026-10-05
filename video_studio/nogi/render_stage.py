#!/usr/bin/env python3
"""Stage 2 — frame renderer for спецвыпуск «Ноги довезут или похоронят».

usage:
  render_stage.py preview t1 t2 ...      -> /tmp/smk4/prev_<t>.jpg
  render_stage.py part <idx> <nparts>    -> /tmp/smk4/part_<idx>.mp4 (video only, high quality)
"""
import json
import math
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

ROOT = Path("/home/user/-/video_studio")
sys.path.insert(0, str(ROOT / "nogi"))
sys.path.insert(0, str(ROOT / "toolkit"))
from storyboard import CHAPTERS, AMBER, RED, GREEN, CYAN, BRAND, BRAND_LINKS, N_CHAPTERS, NO_GRADE  # noqa: E402
import typo  # noqa: E402
import grade  # noqa: E402

TMP = Path("/tmp/nogi")
ASSETS = ROOT / "assets_nogi"
GRADED = TMP / "graded"
GRADED.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "fonts"
W, H, FPS = 1920, 1080, 30
BASE_W, BASE_H = 2400, 1350
TL = json.load(open(TMP / "timeline.json"))

# Source crops (x0, y0, x1, y1) on the 1376x768 originals — sanitising / reframing (filled in after review).
CROPS = {}


def font(weight, size):
    """Pro OFL fonts from toolkit: Montserrat variable (Cyrillic, ₽ №)."""
    w = {"black": 900, "bold": 760, "medium": 600, "regular": 450}[weight]
    return typo.font("montserrat", size, (("Weight", w),))


ACC_PRESET = {AMBER: "gold", RED: "blood", GREEN: "gold", CYAN: "chrome"}


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.7):
    x = min(1.0, max(0.0, x)) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_io(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


VIGNETTE = None


def vignette(size):
    w, h = size
    y, x = np.ogrid[-1:1:complex(0, h), -1:1:complex(0, w)]
    r = np.sqrt((x * 0.92) ** 2 + y ** 2)
    v = np.clip(1.0 - 0.55 * np.clip(r - 0.55, 0, None) ** 1.6, 0.35, 1.0)
    return v[..., None].astype(np.float32)


_AVAILABLE = sorted(int(p.stem.split("_")[1]) for p in ASSETS.glob("nogi_*.jpg"))


def asset_path(idx):
    if idx not in _AVAILABLE:  # preview fallback while the scene pool is still being generated
        idx = _AVAILABLE[(idx - 1) % len(_AVAILABLE)]
    src = ASSETS / f"nogi_{idx:02d}.jpg"
    if idx in NO_GRADE:
        return src
    dst = GRADED / src.name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        grade.look(Image.open(src).convert("RGB"), "frontline", seed=idx).save(dst, quality=95)
    return dst


@lru_cache(maxsize=10)
def base_image(idx):
    global VIGNETTE
    im = Image.open(asset_path(idx)).convert("RGB")
    if idx in CROPS:
        im = im.crop(CROPS[idx])
    w, h = im.size
    tw = int(h * 16 / 9)
    if tw <= w:
        x0 = (w - tw) // 2
        im = im.crop((x0, 0, x0 + tw, h))
    else:
        th = int(w * 9 / 16)
        y0 = (h - th) // 2
        im = im.crop((0, y0, w, y0 + th))
    im = im.resize((BASE_W, BASE_H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.06)
    if VIGNETTE is None:
        VIGNETTE = vignette((BASE_W, BASE_H))
    a = np.asarray(im).astype(np.float32) * VIGNETTE
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


@lru_cache(maxsize=6)
def blurred_bg(idx, dark=0.38):
    im = base_image(idx).resize((BASE_W // 2, BASE_H // 2), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(14))
    im = ImageEnhance.Color(im).enhance(0.55)
    im = ImageEnhance.Brightness(im).enhance(dark)
    return im.resize((BASE_W, BASE_H), Image.BILINEAR)


def view(base, z, cx, cy, dx=0.0, dy=0.0):
    bw, bh = base.size
    ww, wh = bw / z, bh / z
    x0 = min(max(0, cx * bw - ww / 2 + dx * ww / W), bw - ww)
    y0 = min(max(0, cy * bh - wh / 2 + dy * wh / H), bh - wh)
    return base.transform((W, H), Image.AFFINE, (ww / W, 0, x0, 0, wh / H, y0), resample=Image.BILINEAR)


def handheld(t, amp=1.0):
    dx = (math.sin(t * 1.3) * 5 + math.sin(t * 2.9 + 1) * 3 + math.sin(t * 7.1) * 1.2) * amp
    dy = (math.sin(t * 1.1 + 2) * 4 + math.sin(t * 3.7) * 2.5 + math.sin(t * 6.3 + 1) * 1.0) * amp
    return dx, dy


WHITE_FRAME = Image.new("RGB", (W, H), (255, 255, 255))
BLACK_FRAME = Image.new("RGB", (W, H), (0, 0, 0))


def shot_frame(sh, t):
    base = base_image(sh["img"])
    dur = sh["t1"] - sh["t0"]
    u = t - sh["t0"]
    p = min(1.0, max(0.0, u / max(dur, 0.01)))
    fx, fy = sh.get("focus", [0.5, 0.45])
    mv = sh["move"]
    amp = 1.0
    cx, cy = 0.5 + (fx - 0.5) * 0.35, 0.5 + (fy - 0.5) * 0.35
    if mv == "in":
        z = 1.04 + 0.13 * ease_io(p)
    elif mv == "out":
        z = 1.19 - 0.14 * ease_io(p)
    elif mv == "left":
        z, cx = 1.14, 0.57 - 0.14 * ease_io(p)
    elif mv == "right":
        z, cx = 1.14, 0.43 + 0.14 * ease_io(p)
    elif mv == "up":
        z, cy = 1.14, 0.58 - 0.16 * ease_io(p)
    elif mv == "shake":
        z, amp = 1.16 + 0.04 * p, 3.2
    else:  # punch
        s = ease_out(u / 0.22)
        z = 1.05 + 0.30 * s + 0.05 * p
        cx = 0.5 + (fx - 0.5) * (0.35 + 0.5 * s)
        cy = 0.5 + (fy - 0.5) * (0.35 + 0.5 * s)
    z *= 1 + 0.045 * (1 - ease_out(u / 0.25))
    dx, dy = handheld(t, amp)
    if mv == "shake" and u < 0.5:
        k = (0.5 - u) / 0.5
        dx += math.sin(u * 90) * 14 * k
        dy += math.cos(u * 77) * 10 * k
    fr = view(base, z, cx, cy, dx, dy)
    if sh.get("flash") and u < 0.13:
        fr = Image.blend(fr, WHITE_FRAME, 0.75 * (1 - u / 0.13))
    elif u < 0.07:
        fr = Image.blend(fr, BLACK_FRAME, 0.35 * (1 - u / 0.07))
    return fr


# ---------------------------------------------------------------- text helpers
def text_rgba(txt, fnt, fill, stroke=0, stroke_fill=(0, 0, 0), spacing=0, shadow=True):
    widths = [fnt.getlength(ch) for ch in txt] if spacing else None
    tw = int(sum(widths) + spacing * (len(txt) - 1)) if spacing else int(fnt.getlength(txt))
    asc, desc = fnt.getmetrics()
    pad = stroke + 14
    im = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))

    def draw(dd, ox, oy, col, sw):
        if spacing:
            x = ox
            for ch, wch in zip(txt, widths):
                dd.text((x, oy), ch, font=fnt, fill=col, stroke_width=sw, stroke_fill=stroke_fill if sw else None)
                x += wch + spacing
        else:
            dd.text((ox, oy), txt, font=fnt, fill=col, stroke_width=sw, stroke_fill=stroke_fill if sw else None)

    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), pad + 4, pad + 6, (0, 0, 0, 170), stroke)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    draw(ImageDraw.Draw(im), pad, pad, fill, stroke)
    return im


def paste(fr, im, x, y, alpha=1.0, scale=1.0, anchor="lt"):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if anchor == "c":
        x, y = x - im.width // 2, y - im.height // 2
    elif anchor == "ct":
        x = x - im.width // 2
    elif anchor == "rt":
        x = x - im.width
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * max(0.0, alpha)))
        im = im.copy()
        im.putalpha(a)
    fr.paste(im, (int(x), int(y)), im)


# ---------------------------------------------------------------- overlays
COLORS = {"w": (255, 255, 255), "num": AMBER, "hot": (255, 214, 102), "red": (255, 92, 92)}


@lru_cache(maxsize=64)
def sub_rgba(key):
    words = json.loads(key)
    fnt = font("black", 64)
    space = fnt.getlength(" ")
    widths = [fnt.getlength(w) for w, _ in words]
    tw = int(sum(widths) + space * (len(words) - 1))
    asc, desc = fnt.getmetrics()
    pad = 22
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    x = pad
    for (w, c), wd in zip(words, widths):
        ds.text((x + 3, pad + 5), w, font=fnt, fill=(0, 0, 0, 200), stroke_width=7, stroke_fill=(0, 0, 0, 200))
        x += wd + space
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(5)))
    d = ImageDraw.Draw(im)
    x = pad
    for (w, c), wd in zip(words, widths):
        d.text((x, pad), w, font=fnt, fill=COLORS[c], stroke_width=6, stroke_fill=(10, 10, 10))
        x += wd + space
    return im


@lru_cache(maxsize=64)
def badge_rgba(text, color):
    color = tuple(color)
    fnt = font("black", 56)
    tw = int(fnt.getlength(text))
    asc, desc = fnt.getmetrics()
    h = asc + desc + 30
    wbox = tw + 70
    im = Image.new("RGBA", (wbox + 30, h + 30), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((10, 14, wbox + 10, h + 14), fill=(0, 0, 0, 150))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, wbox, h), fill=(14, 16, 14, 228))
    d.rectangle((0, 0, 16, h), fill=color + (255,))
    d.rectangle((16, h - 5, wbox, h), fill=color + (255,))
    d.text((40, 12), text, font=fnt, fill=(255, 255, 255))
    return im


@lru_cache(maxsize=8)
def chapter_tag(k):
    ch = CHAPTERS[k]
    acc = ch["accent"]
    f1, f2 = font("black", 34), font("bold", 34)
    a = ch.get("label") or f"ГЛАВА {k}/{N_CHAPTERS - 1}"
    b = "  ·  " + ch["short"] if not ch.get("label") else ""
    w1, w2 = f1.getlength(a), f2.getlength(b)
    wbox = int(w1 + w2 + 56)
    im = Image.new("RGBA", (wbox, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, wbox, 64), fill=(10, 12, 10, 190))
    d.rectangle((0, 0, 10, 64), fill=acc + (255,))
    d.text((28, 12), a, font=f1, fill=acc)
    d.text((28 + w1, 12), b, font=f2, fill=(235, 235, 235))
    return im


@lru_cache(maxsize=1)
def watermark():
    """Persistent brand bug, top-right: «В ОКОПЕ» + series name."""
    f1, f2 = font("black", 34), font("bold", 22)
    a, b = "«В ОКОПЕ»", "ОКОПНАЯ СМЕКАЛКА · СПЕЦВЫПУСК"
    w = int(max(f1.getlength(a), f2.getlength(b))) + 44
    im = Image.new("RGBA", (w, 84), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 84), fill=(10, 12, 10, 170))
    d.rectangle((w - 8, 0, w, 84), fill=RED + (255,))
    d.text((w - 22 - f1.getlength(a), 6), a, font=f1, fill=(255, 255, 255))
    d.text((w - 22 - f2.getlength(b), 50), b, font=f2, fill=AMBER)
    return im


def draw_progress(fr, k, frac):
    d = ImageDraw.Draw(fr)
    x0, y0, gap = 60, 34, 10
    seg = (W - 2 * x0 - (N_CHAPTERS - 1) * gap) / N_CHAPTERS
    for i in range(1, N_CHAPTERS + 1):
        xa = x0 + (i - 1) * (seg + gap)
        d.rectangle((xa, y0, xa + seg, y0 + 6), fill=(70, 70, 70))
        if i < k:
            d.rectangle((xa, y0, xa + seg, y0 + 6), fill=(200, 200, 200))
        elif i == k:
            d.rectangle((xa, y0, xa + seg * frac, y0 + 6), fill=CHAPTERS[k]["accent"])


# ---------------------------------------------------------------- title card
@lru_cache(maxsize=2)
def title_assets(k):
    ch = CHAPTERS[k]
    acc = ch["accent"]
    label = ch.get("label")
    A = {"label": typo.render("ГЛАВА" if not label else "", typo.PRESETS["steel"], 86) if not label else
         typo.render(" ", typo.PRESETS["steel"], 20),
         "num": typo.render(f"№{k}" if not label else label, typo.PRESETS[ACC_PRESET[tuple(acc)]], 250 if not label else 210)}
    st = typo.PRESETS["chrome"]
    lines, cur = [], ""
    for w in ch["title"].split():
        tr = (cur + " " + w).strip()
        if typo.text_len(tr, st.family, 92) > 1050 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = tr
    lines.append(cur)
    tsize = 92 if len(lines) <= 2 else 76
    A["title"] = [typo.render(l, st, tsize) for l in lines]
    A["lh"] = 104 if len(lines) <= 2 else 86
    A["sub"] = text_rgba(ch["sub"], font("black", 46), acc)
    th = base_image(ch["hero"]).resize((640, 360), Image.LANCZOS).convert("RGBA")
    frm = Image.new("RGBA", (656, 376), (255, 255, 255, 255))
    frm.paste(th, (8, 8))
    frm = frm.rotate(-2.5, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", (frm.width + 60, frm.height + 60), (0, 0, 0, 0))
    blk = Image.new("RGBA", frm.size, (0, 0, 0, 255))
    blk.putalpha(frm.getchannel("A").point(lambda v: int(v * 0.6)))
    shadow.paste(blk, (40, 46), blk)
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    shadow.paste(frm, (20, 20), frm)
    A["thumb"] = shadow
    big = text_rgba(str(k) if not label else "!", font("black", 900), (255, 255, 255), shadow=False)
    big.putalpha(big.getchannel("A").point(lambda v: int(v * 0.07)))
    A["big"] = big
    pills = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(pills)
    f = font("bold", 16)
    pw = (W - 120 - (N_CHAPTERS - 1) * 12) // N_CHAPTERS
    x0 = (W - (N_CHAPTERS * pw + (N_CHAPTERS - 1) * 12)) // 2
    for i in range(1, N_CHAPTERS + 1):
        xa = x0 + (i - 1) * (pw + 12)
        col = acc if i == k else ((150, 150, 150) if i < k else (80, 80, 80))
        d.rectangle((xa, 20, xa + pw, 26), fill=col)
        lab = CHAPTERS[i]["short"] if CHAPTERS[i].get("label") else f"{i}. {CHAPTERS[i]['short']}"
        d.text((xa, 38), lab, font=f, fill=(255, 255, 255) if i == k else (140, 140, 140))
    A["pills"] = pills
    A["brand"] = text_rgba(BRAND + "  ·  ОКОПНАЯ СМЕКАЛКА", font("black", 34), (230, 230, 230), spacing=3)
    A["label_is_final"] = bool(label)
    return A


def title_frame(sh, t):
    k = sh["chapter"]
    ch = CHAPTERS[k]
    acc = ch["accent"]
    A = title_assets(k)
    u = t - sh["t0"]
    dur = sh["t1"] - sh["t0"]
    slam = sh["slam_t"] - sh["t0"]
    p2 = sh["phrase2_t"] - sh["t0"]
    dx, dy = handheld(t, 0.8)
    if slam <= u < slam + 0.35:
        kk = 1 - (u - slam) / 0.35
        dx += math.sin(u * 95) * 22 * kk
        dy += math.cos(u * 80) * 16 * kk
    fr = view(blurred_bg(ch["hero"]), 1.06 + 0.05 * u / dur, 0.5, 0.5, dx, dy)
    slab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    e = ease_out(u / 0.3)
    xr = -900 + 1900 * e
    ImageDraw.Draw(slab).polygon([(xr - 700, 0), (xr, 0), (xr - 420, H), (xr - 1120, H)], fill=acc + (38,))
    fr.paste(slab, (0, 0), slab)
    paste(fr, A["big"], W - A["big"].width + 60 + int(40 * u), H // 2 - A["big"].height // 2 - 30)
    paste(fr, A["brand"], 110, 70, alpha=ease_out(u / 0.3))
    e = ease_out((u - 0.05) / 0.3)
    if e > 0:
        paste(fr, A["label"], 110 - 300 * (1 - e), 205, alpha=e)
    if u >= slam - 0.02:
        s = ease_out((u - slam) / 0.16)
        paste(fr, A["num"], 110 + A["num"].width / 2 - 20, 300 + A["num"].height / 2,
              scale=2.3 - 1.3 * s, alpha=min(1.0, 0.3 + s), anchor="c")
    e = ease_out((u - 0.15) / 0.4)
    if e > 0:
        paste(fr, A["thumb"], W - A["thumb"].width - 50 + 700 * (1 - e), 200)
    y = 815 - A["lh"] * len(A["title"])
    rev = ease_out((u - p2 + 0.05) / 0.35)
    for ln in A["title"]:
        if rev > 0:
            paste(fr, ln.crop((0, 0, max(1, int(ln.width * rev)), ln.height)), 80, y - 30)
        y += A["lh"]
    if rev > 0:
        bw = int(560 * ease_out((u - p2 - 0.1) / 0.4))
        if bw > 0:
            ImageDraw.Draw(fr).rectangle((120, y + 26, 120 + bw, y + 36), fill=acc)
    e = ease_out((u - p2 - 0.35) / 0.35)
    if e > 0:
        paste(fr, A["sub"], 106, y + 52, alpha=e)
    paste(fr, A["pills"], 0, H - 125, alpha=ease_out(u / 0.4))
    if slam <= u < slam + 0.1:
        fr = Image.blend(fr, WHITE_FRAME, 0.55 * (1 - (u - slam) / 0.1))
    if u < 0.08:
        fr = Image.blend(fr, BLACK_FRAME, 1 - u / 0.08)
    if u > dur - 0.12:
        fr = Image.blend(fr, WHITE_FRAME, min(1.0, (u - (dur - 0.12)) / 0.12) * 0.85)
    return fr


# ---------------------------------------------------------------- intro / outro
INTRO_CUTS = [(2, ""), (11, "МОЗОЛИ"), (14, "ШЕРСТЬ"), (19, "ПОРТЯНКА"), (24, "МЕМБРАНА"), (28, "ОКОПНАЯ СТОПА"),
              (33, "ОБМОРОЖЕНИЕ"), (38, "ПРИВАЛ")]


@lru_cache(maxsize=1)
def intro_assets():
    A = {"words": {w: text_rgba(w, font("black", 170), (255, 255, 255), stroke=8) for _, w in INTRO_CUTS if w}}
    A["l1"] = typo.render("НОГИ ДОВЕЗУТ", typo.PRESETS["chrome"], 190)
    A["l2"] = typo.render("ИЛИ ПОХОРОНЯТ", typo.PRESETS["blood"], 190)
    A["sub"] = text_rgba("СПЕЦВЫПУСК «ОКОПНАЯ СМЕКАЛКА» · 8 ГЛАВ", font("black", 50), AMBER, spacing=4)
    A["tag"] = text_rgba(BRAND + " ПРЕДСТАВЛЯЕТ", font("black", 40), (230, 230, 230), spacing=8)
    return A


def intro_frame(t):
    A = intro_assets()
    if t < 2.4:
        c = min(7, int(t / 0.3))
        img, word = INTRO_CUTS[c]
        u = t - c * 0.3
        dx, dy = handheld(t * 3, 2.0)
        fr = view(base_image(img), 1.28 - 0.14 * ease_out(u / 0.3), 0.5, 0.48, dx, dy)
        fr = ImageEnhance.Contrast(fr).enhance(1.15)
        if word:
            s = ease_out(u / 0.12)
            paste(fr, A["words"][word], W // 2, H // 2, scale=1.4 - 0.4 * s, anchor="c")
        if u < 0.07:
            fr = Image.blend(fr, WHITE_FRAME, 0.8 * (1 - u / 0.07))
        return fr
    u = t - 2.4
    dx, dy = handheld(t, 1.0)
    for slam in (0.0, 0.35):
        if slam <= u < slam + 0.3:
            kk = 1 - (u - slam) / 0.3
            dx += math.sin(u * 100) * 26 * kk
            dy += math.cos(u * 85) * 18 * kk
    fr = view(blurred_bg(1, 0.42), 1.08 + 0.05 * u, 0.5, 0.5, dx, dy)
    s1 = ease_out(u / 0.15)
    paste(fr, A["l1"], W // 2 + dx, 400 + dy, scale=2.2 - 1.2 * s1, alpha=min(1, 0.2 + s1), anchor="c")
    if u >= 0.35:
        s2 = ease_out((u - 0.35) / 0.15)
        paste(fr, A["l2"], W // 2 + dx, 610 + dy, scale=2.2 - 1.2 * s2, alpha=min(1, 0.2 + s2), anchor="c")
    e = ease_out((u - 0.6) / 0.35)
    if e > 0:
        hw = int(560 * e)
        ImageDraw.Draw(fr).rectangle((W // 2 - hw, 742, W // 2 + hw, 750), fill=RED)
        paste(fr, A["sub"], W // 2, 790, alpha=e, anchor="ct")
    e = ease_out((u - 0.0) / 0.3)
    paste(fr, A["tag"], W // 2, 190, alpha=e, anchor="ct")
    for slam in (0.0, 0.35):
        if slam <= u < slam + 0.08:
            fr = Image.blend(fr, WHITE_FRAME, 0.6 * (1 - (u - slam) / 0.08))
    if t > TL["intro"] - 0.14:
        fr = Image.blend(fr, WHITE_FRAME, min(1.0, (t - (TL["intro"] - 0.14)) / 0.14) * 0.9)
    return fr


@lru_cache(maxsize=1)
def outro_assets():
    return {
        "l1": typo.render("ОКОПНАЯ СМЕКАЛКА", typo.PRESETS["gold"], 120),
        "l0": text_rgba("СПЕЦВЫПУСК ОТ МАГАЗИНА «В ОКОПЕ»", font("black", 50), AMBER, spacing=5),
        "l2": text_rgba("БЕРЕГИТЕ СЕБЯ", font("black", 64), RED, spacing=6),
        "l3": text_rgba(BRAND_LINKS, font("bold", 46), (235, 235, 235), spacing=2),
        "l4": text_rgba("ДО ВСТРЕЧИ В СЛЕДУЮЩЕМ ВЫПУСКЕ", font("bold", 36), (200, 200, 200), spacing=3),
    }


def outro_frame(sh, t):
    A = outro_assets()
    u = t - sh["t0"]
    dur = sh["t1"] - sh["t0"]
    dx, dy = handheld(t, 0.6)
    fr = view(base_image(45), 1.08 + 0.05 * u / dur, 0.5, 0.5, dx, dy)
    fr = Image.blend(fr, BLACK_FRAME, 0.5)
    e = ease_out((u - 0.05) / 0.35)
    paste(fr, A["l0"], W // 2, 250, alpha=e, anchor="ct")
    e1 = ease_out((u - 0.2) / 0.4)
    paste(fr, A["l1"], W // 2, 330, alpha=e1, scale=1.15 - 0.15 * e1, anchor="ct")
    e2 = ease_out((u - 0.6) / 0.4)
    if e2 > 0:
        ImageDraw.Draw(fr).rectangle((W // 2 - int(460 * e2), 500, W // 2 + int(460 * e2), 507), fill=RED)
        paste(fr, A["l2"], W // 2, 540, alpha=e2, anchor="ct")
    e3 = ease_out((u - 1.0) / 0.4)
    if e3 > 0:
        paste(fr, A["l3"], W // 2, 660, alpha=e3, anchor="ct")
        paste(fr, A["l4"], W // 2, 760, alpha=e3, anchor="ct")
    if u > dur - 1.3:
        fr = Image.blend(fr, BLACK_FRAME, min(1.0, (u - (dur - 1.3)) / 1.3))
    return fr


# ---------------------------------------------------------------- compose
SHOTS, BADGES, SUBS = TL["shots"], TL["badges"], TL["subs"]
CHAP = {c["chapter"]: c for c in TL["chapters"]}


def find_shot(t):
    for sh in SHOTS:
        if sh["t0"] <= t < sh["t1"]:
            return sh
    return SHOTS[-1]


def chapter_at(t):
    for k, c in CHAP.items():
        if c["body_t0"] <= t < c["body_t1"]:
            return k
    return None


def frame_at(t):
    sh = find_shot(t)
    if sh["kind"] == "intro":
        return intro_frame(t)
    if sh["kind"] == "title":
        return title_frame(sh, t)
    if sh["kind"] == "outro":
        return outro_frame(sh, t)
    fr = shot_frame(sh, t)
    k = chapter_at(t)
    if k:
        c = CHAP[k]
        draw_progress(fr, k, (t - c["body_t0"]) / (c["body_t1"] - c["body_t0"]))
        e = ease_out((t - c["body_t0"] - 0.2) / 0.35)
        paste(fr, chapter_tag(k), 60 - 400 * (1 - e), 62, alpha=e)
    paste(fr, watermark(), W - 60, 62 if k else 40, alpha=0.92, anchor="rt")
    for b in BADGES:
        if b["t0"] <= t < b["t1"]:
            u, rem = t - b["t0"], b["t1"] - t
            e = ease_out_back(u / 0.22)
            paste(fr, badge_rgba(b["text"], tuple(b["color"])), 60 - 120 * (1 - e), 150,
                  alpha=min(1.0, u / 0.08, rem / 0.15))
            break
    for s in SUBS:
        if s["t0"] <= t < s["t1"]:
            sc = 1.0 + 0.10 * (1 - ease_out((t - s["t0"]) / 0.12))
            paste(fr, sub_rgba(json.dumps(s["words"], ensure_ascii=False)), W // 2, 905, scale=sc, anchor="c")
            break
    return fr




def main():
    mode = sys.argv[1]
    if mode == "preview":
        for ts in sys.argv[2:]:
            t = float(ts)
            frame_at(t).save(TMP / f"prev_{t:07.2f}.jpg", quality=85)
        return
    idx, n = int(sys.argv[2]), int(sys.argv[3])
    total = int(TL["total"] * FPS)
    f0, f1 = total * idx // n, total * (idx + 1) // n
    out = TMP / f"part_{idx}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-threads", "1", "-g", "60", str(out)], stdin=subprocess.PIPE)
    st = time.time()
    for i in range(f0, f1):
        ff.stdin.write(frame_at(i / FPS).tobytes())
        if (i - f0) % 600 == 0:
            done = i - f0 + 1
            el = time.time() - st
            print(f"part {idx}: {done}/{f1-f0} frames, {done/el:.1f} fps, eta {(f1-f0-done)/(done/el)/60:.1f} min", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"part {idx} done in {(time.time()-st)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
