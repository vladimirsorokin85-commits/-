#!/usr/bin/env python3
"""typo.py — professional typography engine for thumbnails, titles and kinetic captions (PIL + numpy).

Pro OFL fonts with Cyrillic (toolkit/fonts) + a layered effect stack, like a Photoshop layer style:
    fill (solid / multi-stop gradient / texture)  ·  bevel & emboss with real lighting (distance-field
    normals -> Lambert + specular: gold, chrome, steel)  ·  N strokes  ·  3D extrude  ·  drop shadow
    ·  outer glow  ·  grunge erosion  ·  military stencil bridges  ·  skew / rotate  ·  tracking.

    from typo import Style, render, PRESETS
    layer = render("ХИТРОСТЬ №1", PRESETS["gold"], size=160)        # RGBA image
    canvas.alpha_composite(layer, (x, y))
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

FONTS = Path(__file__).parent / "fonts"

# family -> (file, default variation axes)
FAMILY = {
    "russo": ("RussoOne-Regular.ttf", None),            # военно-спортивный гротеск, заголовки
    "dela": ("DelaGothicOne-Regular.ttf", None),         # сверхжирный, плакатный удар
    "rubikmono": ("RubikMonoOne-Regular.ttf", None),     # широкий моноширинный блок
    "seymour": ("SeymourOne-Regular.ttf", None),         # круглый жирный, «жвачка»
    "unbounded": ("Unbounded-VF.ttf", {"Weight": 900}),  # широкий современный, 200–900
    "oswald": ("Oswald-VF.ttf", {"Weight": 700}),        # узкий новостной, 200–700
    "montserrat": ("Montserrat-VF.ttf", {"Weight": 900}),
    "tektur": ("Tektur-VF.ttf", {"Weight": 900, "Width": 100}),  # техно/милитари, 75–100 ширина
    "exo": ("Exo2-VF.ttf", {"Weight": 900}),
    "sofia": ("SofiaSansExtraCondensed-VF.ttf", {"Weight": 900}),  # сверхузкий для длинных фраз
    "fira": ("FiraSansExtraCondensed-Black.ttf", None),
    "dirt": ("RubikDirt-Regular.ttf", None),             # грязный/потёртый
    "distressed": ("RubikDistressed-Regular.ttf", None),
    "spray": ("RubikSprayPaint-Regular.ttf", None),      # баллончик
    "glitch": ("RubikGlitch-Regular.ttf", None),
    "stalinist": ("StalinistOne-Regular.ttf", None),     # советский конструктивизм
    "ruslan": ("RuslanDisplay-Regular.ttf", None),       # древнерусский
    "kelly": ("KellySlab-Regular.ttf", None),            # брусковый
    "pixel": ("PressStart2P-Regular.ttf", None),         # 8-bit / HUD
    "jura": ("Jura-VF.ttf", {"Weight": 700}),            # HUD / приборы
    "play": ("Play-Bold.ttf", None),
    "caveat": ("Caveat-VF.ttf", {"Weight": 700}),        # маркер от руки
    "marck": ("MarckScript-Regular.ttf", None),          # письменный
    "mono": ("JetBrainsMono-VF.ttf", {"Weight": 800}),
    "prosto": ("ProstoOne-Regular.ttf", None),
    "days": ("DaysOne-Regular.ttf", None),
}


@lru_cache(maxsize=256)
def font(family: str, size: int, axes: tuple | None = None) -> ImageFont.FreeTypeFont:
    fn, default = FAMILY[family]
    f = ImageFont.truetype(str(FONTS / fn), size)
    ax = dict(default or {})
    if axes:
        ax.update(dict(axes))
    if ax:
        try:
            names = [a["name"].decode() if isinstance(a["name"], bytes) else a["name"] for a in f.get_variation_axes()]
            vals = []
            for a, n in zip(f.get_variation_axes(), names):
                v = ax.get(n, a.get("default", a["minimum"]))
                vals.append(max(a["minimum"], min(a["maximum"], v)))
            f.set_variation_by_axes(vals)
        except OSError:
            pass
    return f


@lru_cache(maxsize=64)
def cmap(family: str) -> frozenset:
    from fontTools.ttLib import TTFont
    return frozenset(TTFont(str(FONTS / FAMILY[family][0])).getBestCmap())


FALLBACK = "unbounded"  # heavy font that has ₽ № « » and full Cyrillic


def runs(s: str, family: str):
    """Split text into (chunk, family) runs, swapping in FALLBACK for glyphs the font lacks."""
    cm = cmap(family)
    out = []
    for ch in s:
        fam = family if (ord(ch) in cm or ch == " ") else FALLBACK
        if out and out[-1][1] == fam:
            out[-1][0] += ch
        else:
            out.append([ch, fam])
    return out


def draw_text(d: ImageDraw.ImageDraw, xy, s, family, size, axes=None, fill=255, track=0.0):
    x, y = xy
    for chunk, fam in runs(s, family):
        f = font(fam, size, axes if fam == family else None)
        if track == 0:
            d.text((x, y), chunk, font=f, fill=fill)
            x += f.getlength(chunk)
        else:
            for ch in chunk:
                d.text((x, y), ch, font=f, fill=fill)
                x += f.getlength(ch) + track
    return x


def text_len(s, family, size, axes=None, track=0.0):
    return sum(font(fam, size, axes if fam == family else None).getlength(c) for c, fam in runs(s, family)) + track * max(0, len(s) - 1)


# ----------------------------------------------------------------------------- style
@dataclass
class Style:
    family: str = "russo"
    axes: tuple | None = None
    tracking: float = 0.0                 # letter spacing, fraction of size
    fill: list = field(default_factory=lambda: [(0.0, (255, 255, 255))])  # gradient stops top->bottom
    fill_angle: float = 90.0              # 90 = vertical
    texture: str | None = None            # image path multiplied into the fill
    bevel: float = 0.0                    # bevel depth in px (0 = off)
    bevel_light: float = 135.0            # light azimuth (deg, 0 = from right, 90 = from top)
    bevel_shine: float = 0.7              # specular strength
    bevel_dark: float = 0.55              # shadow strength
    strokes: list = field(default_factory=list)   # [(width_px, (r,g,b)), ...] inner -> outer
    extrude: int = 0                      # 3D depth px
    extrude_dir: float = 45.0             # degrees, 45 = down-right
    extrude_col: tuple = (40, 20, 0)
    shadow: tuple | None = (8, 12, 14, 170)  # dx, dy, blur, alpha
    glow: tuple | None = None             # (radius, (r,g,b), alpha)
    grunge: float = 0.0                   # 0..1 erosion amount
    stencil: float = 0.0                  # bridge thickness (fraction of size), 0 = off
    skew: float = 0.0                     # horizontal shear (e.g. -0.2 = italic)
    rotate: float = 0.0
    upper: bool = True


def _lerp_stops(stops, t):
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    xs = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], float)
    if len(stops) == 1:
        out[:] = cols[0]
        return out
    for c in range(3):
        out[..., c] = np.interp(t, xs, cols[:, c])
    return out


def text_mask(text: str, st: Style, size: int, pad: int) -> Image.Image:
    f = font(st.family, size, st.axes)
    s = text.upper() if st.upper else text
    track = st.tracking * size
    total = text_len(s, st.family, size, st.axes, track)
    asc, desc = f.getmetrics()
    W, H = int(total + 2 * pad), int(asc + desc + 2 * pad)
    m = Image.new("L", (W, H), 0)
    draw_text(ImageDraw.Draw(m), (pad, pad), s, st.family, size, st.axes, 255, track)
    return m


def _noise(h, w, scale, seed=0):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(4):
        sh = (max(2, h // (scale >> o or 1)), max(2, w // (scale >> o or 1)))
        n = rng.random(sh)
        acc += amp * np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)) / 255
        tot += amp
        amp *= 0.5
    return acc / tot


def render(text: str, st: Style, size: int = 140) -> Image.Image:
    """Return a tight RGBA layer with all effects applied."""
    maxstroke = sum(w for w, _ in st.strokes)
    glow_r = st.glow[0] if st.glow else 0
    pad = int(maxstroke + st.extrude + glow_r * 2 + (st.shadow[2] * 2 + abs(st.shadow[0]) + abs(st.shadow[1]) if st.shadow else 0) + 12)
    m = text_mask(text, st, size, pad)
    # shear / rotate on the mask (everything else derives from it)
    if st.skew:
        w, h = m.size
        extra = int(abs(st.skew) * h)
        m2 = Image.new("L", (w + extra, h), 0)
        m2.paste(m, (extra if st.skew > 0 else 0, 0))
        m = m2.transform(m2.size, Image.AFFINE, (1, st.skew, -st.skew * h if st.skew > 0 else 0, 0, 1, 0), Image.BICUBIC)
    if st.rotate:
        m = m.rotate(st.rotate, expand=True, resample=Image.BICUBIC)
    A = np.asarray(m).astype(float) / 255.0
    H, W = A.shape

    if st.stencil > 0:  # military stencil: horizontal bridges through every glyph
        th = max(2, int(st.stencil * size))
        ys, xs = np.nonzero(A > 0.5)
        if len(ys):
            y0, y1 = ys.min(), ys.max()
            lab, n = ndi.label(np.asarray(m) > 127)
            # vertical bridges in closed counters (О, А, Б...)
            filled = ndi.binary_fill_holes(np.asarray(m) > 127)
            holes = filled & ~(np.asarray(m) > 127)
            hl, hn = ndi.label(holes)
            for i in range(1, hn + 1):
                yy, xx = np.nonzero(hl == i)
                cx = int(xx.mean())
                A[yy.min() - int(size * 0.08): yy.max() + int(size * 0.08), cx - th // 2: cx + th // 2] = 0
    if st.grunge > 0:
        n1 = _noise(H, W, 64, 3)
        n2 = _noise(H, W, 8, 7)
        g = (n1 * 0.6 + n2 * 0.4)
        thr = np.percentile(g, st.grunge * 35)
        A = A * np.clip((g - thr) * 12, 0, 1)

    inside = A > 0.5
    out = np.zeros((H, W, 4))

    def comp(rgb, alpha):  # alpha-over onto out
        a = alpha[..., None]
        out[..., :3] = rgb * a + out[..., :3] * (1 - a)
        out[..., 3] = alpha + out[..., 3] * (1 - alpha)

    dist_out = ndi.distance_transform_edt(~inside)
    # shadow
    if st.shadow:
        dx, dy, bl, al = st.shadow
        base = np.clip(maxstroke + 1 - dist_out, 0, 1)
        sh = ndi.shift(base, (dy + st.extrude * 0.7, dx + st.extrude * 0.7), order=1)
        sh = ndi.gaussian_filter(sh, bl) * (al / 255)
        comp(np.zeros((H, W, 3)), sh)
    # glow
    if st.glow:
        r, col, al = st.glow
        base = np.clip(maxstroke + 1 - dist_out, 0, 1)
        gl = np.clip(ndi.gaussian_filter(base, r) * 2.2, 0, 1) * (al / 255)
        comp(np.ones((H, W, 3)) * np.array(col), gl)
    # extrude (3D): stack the outermost silhouette
    outer = np.clip(maxstroke + 1 - dist_out, 0, 1)
    if st.extrude:
        ang = math.radians(st.extrude_dir)
        ec = np.array(st.extrude_col, float)
        for k in range(st.extrude, 0, -1):
            sl = ndi.shift(outer, (k * math.sin(ang), k * math.cos(ang)), order=0)
            shade = 0.55 + 0.45 * (1 - k / st.extrude)
            comp(np.ones((H, W, 3)) * ec * shade, sl)
    # strokes outer -> inner
    acc = maxstroke
    for w, col in reversed(st.strokes):
        comp(np.ones((H, W, 3)) * np.array(col), np.clip(acc + 1 - dist_out, 0, 1))
        acc -= w
    # fill
    ys, xs = np.mgrid[0:H, 0:W]
    yy, xx = np.nonzero(inside)
    if len(yy):
        t0y, t1y, t0x, t1x = yy.min(), yy.max(), xx.min(), xx.max()
    else:
        t0y, t1y, t0x, t1x = 0, H, 0, W
    a = math.radians(st.fill_angle)
    proj = ((xs - t0x) * math.cos(a) + (ys - t0y) * math.sin(a))
    span = (t1x - t0x) * abs(math.cos(a)) + (t1y - t0y) * abs(math.sin(a)) + 1e-6
    rgb = _lerp_stops(st.fill, proj / span)
    if st.texture:
        tx = Image.open(st.texture).convert("L").resize((W, H))
        rgb *= (0.6 + 0.4 * np.asarray(tx)[..., None] / 255)
    # bevel & emboss with lighting
    if st.bevel > 0:
        din = ndi.distance_transform_edt(inside)
        hgt = np.clip(din / st.bevel, 0, 1)
        hgt = np.sin(hgt * math.pi / 2)  # rounded profile
        hgt = ndi.gaussian_filter(hgt, 0.8)
        gy, gx = np.gradient(hgt * st.bevel)
        nz = np.ones_like(gx)
        nrm = np.sqrt(gx ** 2 + gy ** 2 + nz ** 2)
        nx, ny, nz = -gx / nrm, -gy / nrm, nz / nrm
        la = math.radians(st.bevel_light)
        L = np.array([math.cos(la), -math.sin(la), 0.9])
        L /= np.linalg.norm(L)
        lam = nx * L[0] + ny * L[1] + nz * L[2]
        flat = L[2]
        shade = (lam - flat)  # >0 lit, <0 shadow
        Hh = L + np.array([0, 0, 1.0])
        Hh /= np.linalg.norm(Hh)
        spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 40
        light = np.clip(shade, 0, None)[..., None] * 255 * 1.6 + spec[..., None] * 255 * st.bevel_shine
        dark = np.clip(-shade, 0, None)[..., None] * 2.2 * st.bevel_dark
        rgb = rgb * (1 - np.clip(dark, 0, 0.9)) + light
    comp(np.clip(rgb, 0, 255), A)
    arr = np.dstack([out[..., :3], out[..., 3] * 255]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def fit(text, st: Style, max_w: int, size: int = 200, min_size: int = 30) -> int:
    """Largest size whose glyph run fits into max_w (ignores effects padding)."""
    s = text.upper() if st.upper else text
    while size > min_size:
        if text_len(s, st.family, size, st.axes, st.tracking * size) <= max_w:
            return size
        size -= 4
    return min_size


# ----------------------------------------------------------------------------- labels / tapes
def tape(text, size=54, bg=(225, 25, 35), fg=(255, 255, 255), family="russo", rot=-3, torn=True,
         border=(255, 255, 255)) -> Image.Image:
    """Torn-edge tape/sticker label."""
    s = text.upper()
    probe = Image.new("L", (10, 10))
    tw = text_len(s, family, size)
    f = font(family, size)
    asc, desc = f.getmetrics()
    bb0 = f.getbbox("ЖЙ")
    bb = (0, bb0[1], int(tw), bb0[3])
    w, h = bb[2] - bb[0] + int(size * 0.9), bb[3] - bb[1] + int(size * 0.55)
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    m = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(m)
    pts = []
    rng = np.random.default_rng(len(text))
    n = 18
    for i in range(n + 1):  # top edge
        pts.append((20 + w * i / n, 20 + (rng.uniform(-4, 4) if torn else 0)))
    for i in range(1, 6):
        pts.append((20 + w + (rng.uniform(-7, 3) if torn else 0), 20 + h * i / 6))
    for i in range(n, -1, -1):
        pts.append((20 + w * i / n, 20 + h + (rng.uniform(-4, 4) if torn else 0)))
    for i in range(5, 0, -1):
        pts.append((20 + (rng.uniform(-3, 7) if torn else 0), 20 + h * i / 6))
    d.polygon(pts, fill=255)
    if border:
        bm = m.filter(ImageFilter.MaxFilter(9))
        im.paste(Image.new("RGBA", im.size, border + (255,)), (0, 0), bm)
    im.paste(Image.new("RGBA", im.size, bg + (255,)), (0, 0), m)
    d2 = ImageDraw.Draw(im)
    draw_text(d2, (20 + (w - (bb[2] - bb[0])) / 2 - bb[0], 20 + (h - (bb[3] - bb[1])) / 2 - bb[1]), s, family, size, fill=fg)
    im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.6)))
    out = Image.new("RGBA", (im.width + 12, im.height + 14), (0, 0, 0, 0))
    out.alpha_composite(sh, (10, 12))
    out.alpha_composite(im, (0, 0))
    return out


# ----------------------------------------------------------------------------- presets
GOLD = [(0.0, (255, 246, 170)), (0.45, (255, 196, 40)), (0.55, (220, 130, 0)), (1.0, (255, 210, 80))]
CHROME = [(0.0, (255, 255, 255)), (0.45, (200, 210, 225)), (0.5, (90, 100, 120)), (0.62, (230, 235, 245)), (1.0, (150, 160, 175))]
FIRE = [(0.0, (255, 250, 190)), (0.4, (255, 190, 30)), (0.8, (240, 70, 0)), (1.0, (170, 20, 0))]
BLOOD = [(0.0, (255, 110, 100)), (0.5, (220, 20, 20)), (1.0, (120, 0, 0))]
STEEL = [(0.0, (225, 230, 230)), (0.5, (150, 160, 160)), (1.0, (90, 100, 100))]
KHAKI = [(0.0, (225, 220, 160)), (1.0, (150, 150, 90))]

PRESETS = {
    # тяжёлое золото с фаской и 3D — главный заголовок обложки
    "gold": Style("dela", fill=GOLD, bevel=7, strokes=[(7, (20, 10, 0)), (6, (255, 255, 255))],
                  extrude=12, extrude_col=(60, 25, 0), shadow=(6, 10, 12, 190)),
    # хром — вторая строка
    "chrome": Style("dela", fill=CHROME, bevel=6, bevel_shine=1.0, strokes=[(6, (10, 10, 20)), (5, (255, 255, 255))],
                    extrude=10, extrude_col=(20, 25, 40)),
    "fire": Style("dela", fill=FIRE, bevel=5, strokes=[(6, (30, 0, 0))], extrude=8, extrude_col=(70, 10, 0),
                  glow=(18, (255, 120, 0), 200)),
    "blood": Style("russo", fill=BLOOD, bevel=5, strokes=[(6, (20, 0, 0)), (5, (255, 255, 255))], extrude=8,
                   extrude_col=(60, 0, 0)),
    # армейский трафарет по хаки/стали с потёртостями
    "stencil": Style("russo", fill=KHAKI, stencil=0.05, grunge=0.22, strokes=[(5, (20, 25, 10))], shadow=(5, 7, 6, 160),
                     tracking=0.04),
    "steel": Style("tektur", fill=STEEL, bevel=6, bevel_shine=0.9, strokes=[(5, (15, 18, 18))], extrude=6,
                   extrude_col=(30, 35, 35)),
    # интерфейс прибора / дрона
    "hud": Style("jura", axes=(("Weight", 700),), fill=[(0, (120, 255, 240))], strokes=[], shadow=None,
                 glow=(10, (0, 220, 255), 230), tracking=0.12),
    # субтитры: белый на чёрной толстой обводке, хорошо читается на телефоне
    "caption": Style("montserrat", axes=(("Weight", 900),), fill=[(0, (255, 255, 255))], strokes=[(9, (0, 0, 0))],
                     shadow=(4, 6, 6, 200)),
    "caption_hot": Style("montserrat", axes=(("Weight", 900),), fill=[(0, (255, 214, 0))], strokes=[(9, (0, 0, 0))],
                         shadow=(4, 6, 6, 200)),
    "soviet": Style("stalinist", fill=[(0, (240, 30, 30)), (1, (160, 0, 0))], strokes=[(5, (255, 220, 120))],
                    extrude=8, extrude_col=(60, 0, 0), tracking=0.02),
    "spray": Style("spray", fill=[(0, (255, 255, 255))], upper=True, strokes=[], shadow=(3, 4, 3, 140)),
    "marker": Style("caveat", fill=[(0, (255, 225, 0))], upper=False, strokes=[(5, (0, 0, 0))], shadow=(3, 4, 3, 160)),
    "glitch": Style("glitch", fill=[(0, (255, 255, 255))], glow=(8, (255, 0, 80), 200), strokes=[(4, (0, 0, 0))]),
}


def glitch_split(layer: Image.Image, shift: int = 8) -> Image.Image:
    """RGB-split glitch for kinetic text."""
    r, g, b, a = layer.split()
    W, H = layer.size
    out = Image.new("RGBA", (W + 2 * shift, H), (0, 0, 0, 0))
    for ch, dx, col in ((r, 0, (255, 0, 60)), (b, 2 * shift, (0, 200, 255))):
        tint = Image.new("RGBA", layer.size, col + (0,))
        tint.putalpha(a.point(lambda v: int(v * 0.8)))
        out.alpha_composite(tint, (dx, 0))
    out.alpha_composite(layer, (shift, 0))
    return out
