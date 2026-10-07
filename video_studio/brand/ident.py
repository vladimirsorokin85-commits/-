#!/usr/bin/env python3
"""Branded intro (заставка) for every «В Окопе» video.

usage:
  ident.py build [9x16|16x9]          -> /tmp/brand/ident_<fmt>.mp4 (~3 s, with audio)
  ident.py preview [9x16|16x9] t...   -> /tmp/brand/iprev_<t>.jpg
  ident.py prepend body.mp4 out.mp4 [9x16|16x9]  -> ident + body (re-encoded, seamless)

Logo: brand/logo.png (any of: white-on-black, dark-on-transparent, white-on-transparent).
It is converted to a clean white mask automatically.
Voice: brand/ident_voice.mp3 («Магазин «В Окопе» представляет. Окопная смекалка.»).
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops

ROOT = Path("/home/user/-/video_studio")
BR = ROOT / "brand"
TMP = Path("/tmp/brand")
TMP.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "toolkit"))
sys.path.insert(0, str(ROOT / "reel"))
FPS, SR = 30, 44100
YEL = (255, 204, 0)
SLAM = 0.30          # logo hits
VOICE_AT = 0.55      # voice starts
FFMPEG = str(Path.home() / ".local/bin/ffmpeg")
LOGO_RGB = None
import os
KIND = os.environ.get("IDENT", "short")  # short: «В Окопе». Окопная смекалка. | full: Магазин … представляет …


def dims(fmt):
    return (1080, 1920) if fmt == "9x16" else (1920, 1080)


# ------------------------------------------------------------------ logo
def logo_mask():
    """Return L-mode mask (255 = logo) cropped to content."""
    src = None
    for name in ("logo.png", "logo_white.png", "logo_dark.png"):
        if (BR / name).exists():
            src = BR / name
            break
    if src is None:  # any uploaded image in brand/ (e.g. «В окопе2 копия 2.png»)
        cands = sorted([p for p in BR.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                        and not p.name.startswith("ident")])
        src = cands[0] if cands else None
    if src is None:  # placeholder until the real logo is in the repo
        import typo
        im = typo.render("В ОКОПЕ", typo.PRESETS["chrome"], 200)
        return im.split()[3], True
    im = Image.open(src).convert("RGBA")
    global LOGO_RGB
    a = np.asarray(im).astype(np.float32)
    alpha = a[..., 3]
    lum = a[..., :3].mean(-1)
    if alpha.min() > 250:            # opaque: white on dark (or dark on white)
        m = lum if lum.mean() < 128 else 255 - lum
    else:                            # transparent: shape = alpha
        m = alpha
    m = np.clip((m - 20) * 255 / 215, 0, 255).astype(np.uint8)
    mask = Image.fromarray(m)
    bb = mask.getbbox()
    if alpha.min() <= 250:
        LOGO_RGB = im.convert("RGB").crop(bb)
    return mask.crop(bb), False


class Logo:
    def __init__(self, W, H):
        mask, self.placeholder = logo_mask()
        target_w = int(W * (0.78 if W < H else 0.42))
        target_h = int(H * (0.48 if W < H else 0.62))
        k = min(target_w / mask.width, target_h / mask.height)
        self.mask = mask.resize((int(mask.width * k), int(mask.height * k)), Image.LANCZOS)
        w, h = self.mask.size
        # metallic fill: soft vertical gradient (white -> light steel)
        g = np.linspace(0, 1, h)[:, None]
        base = np.stack([255 - 40 * g, 255 - 35 * g, 255 - 25 * g], -1).repeat(w, 1)
        self.fill = Image.fromarray(base.astype(np.uint8))
        if LOGO_RGB is not None:  # real logo: its own colours x subtle steel gradient
            own = np.asarray(LOGO_RGB.resize((w, h), Image.LANCZOS)).astype(np.float32)
            self.fill = Image.fromarray(np.clip(own * (base / 255.0), 0, 255).astype(np.uint8))
        self.glow = Image.new("RGB", self.mask.size, (255, 190, 60))
        self.glow_mask = self.mask.filter(ImageFilter.GaussianBlur(18))
        self.shadow = self.mask.filter(ImageFilter.GaussianBlur(10))

    def draw(self, frame, cx, cy, scale, shine_p, glow_a):
        m = self.mask
        if abs(scale - 1) > 1e-3:
            sz = (max(1, int(m.width * scale)), max(1, int(m.height * scale)))
            m, fill = m.resize(sz, Image.BILINEAR), self.fill.resize(sz, Image.BILINEAR)
            gm, sh = self.glow_mask.resize(sz, Image.BILINEAR), self.shadow.resize(sz, Image.BILINEAR)
        else:
            fill, gm, sh = self.fill, self.glow_mask, self.shadow
        x, y = int(cx - m.width / 2), int(cy - m.height / 2)
        # drop shadow + warm glow
        frame.paste((0, 0, 0), (x + 8, y + 12), sh.point(lambda v: int(v * 0.8)))
        if glow_a > 0:
            frame.paste((255, 180, 50), (x, y), gm.point(lambda v: int(v * glow_a)))
        fl = fill.copy()
        if 0 <= shine_p <= 1:  # diagonal light sweep across the logo
            w, h = fl.size
            band = Image.new("L", (w, h), 0)
            d = ImageDraw.Draw(band)
            bx = int(-0.4 * w + shine_p * 1.8 * w)
            d.polygon([(bx, 0), (bx + w * 0.16, 0), (bx + w * 0.16 - h * 0.5, h), (bx - h * 0.5, h)], fill=255)
            band = band.filter(ImageFilter.GaussianBlur(12))
            fl = Image.composite(Image.new("RGB", (w, h), (255, 236, 170)), fl, band)
        frame.paste(fl, (x, y), m)
        return (x, y, x + m.width, y + m.height)


# ------------------------------------------------------------------ background
def make_bg(W, H):
    src = ROOT / "assets_nogi" / "nogi_26.jpg"  # dark muddy trench, modern soldiers
    im = Image.open(src).convert("RGB")
    k = max(W / im.width, H / im.height) * 1.12
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.GaussianBlur(14))
    im = ImageEnhance.Color(im).enhance(0.35)
    im = ImageEnhance.Brightness(im).enhance(0.28)
    # vignette
    yy, xx = np.mgrid[0:im.height, 0:im.width]
    r = np.sqrt(((xx - im.width / 2) / (im.width / 2)) ** 2 + ((yy - im.height / 2) / (im.height / 2)) ** 2)
    v = np.clip(1.15 - 0.55 * r, 0.25, 1)[..., None]
    return Image.fromarray((np.asarray(im) * v).astype(np.uint8))


def ease_back(x, s=1.9):
    x = min(1, max(0, x)) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out(x):
    x = min(1, max(0, x))
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ audio
def load(path, tempo=1.0):
    af = ["-af", "adeclick=w=55:o=75:t=2" + (f",atempo={tempo}" if tempo != 1.0 else "")]
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR)] + af + ["-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def build_audio():
    from music_reel import load as sload, pitch, lp, hp, place
    import pyloudnorm as pyln
    from voice_level import level
    v = load(BR / ("ident_voice_short.mp3" if KIND == "short" else "ident_voice.mp3"), tempo=1.1)
    from reel import squeeze_pauses
    v = squeeze_pauses(v, max_pause=0.2, thr_db=-32)
    idx = np.where(np.abs(v) > 0.02)[0]
    v = v[max(0, idx[0] - int(.03 * SR)): idx[-1] + int(.1 * SR)]
    v = level(v, target_db=-17)
    dur = VOICE_AT + len(v) / SR + 0.45
    n = int(dur * SR)
    voice = np.zeros(n)
    place(voice, v, VOICE_AT)
    fx = np.zeros(n + SR * 3)
    boom = sload("misc/misc_cineboom.flac")
    kick = sload("drums/one-shots/kick/drum_heavy_kick.flac")
    splash = sload("drums/one-shots/other/drum_splash_hard.flac")
    rev = splash[::-1][-int(SLAM * SR):]
    place(fx, rev, 0.0, 0.5)                         # suck-in riser
    place(fx, boom, SLAM - 0.02, 1.0)                # logo slam
    place(fx, lp(pitch(kick, -5), 300), SLAM, 0.9)   # sub thump
    place(fx, lp(pitch(splash, -12), 4000), SLAM, 0.35)
    place(fx, hp(splash, 3000)[: int(0.4 * SR)], dur - 0.18, 0.25)  # tick into the cut
    fx = fx[:n]
    meter = pyln.Meter(SR)
    lv = meter.integrated_loudness(voice)
    voice *= 10 ** ((-16 - lv) / 20)
    fx *= 10 ** ((-21 - meter.integrated_loudness(fx)) / 20)
    mix = voice + fx
    mix *= 10 ** ((-14 - meter.integrated_loudness(mix)) / 20)
    lim = 10 ** (-1 / 20)
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    pk = maximum_filter1d(np.abs(mix), int(0.004 * SR))
    g = uniform_filter1d(np.minimum(1, lim / np.maximum(pk, 1e-9)), int(0.004 * SR))
    mix = np.clip(mix * g, -lim, lim)
    return mix, dur


# ------------------------------------------------------------------ frames
def renderer(fmt, dur):
    W, H = dims(fmt)
    bg = make_bg(W, H)
    logo = Logo(W, H)
    import typo
    fnt = typo.font("montserrat", 64 if W < H else 54, (("Weight", 900),))
    txt = "ОКОПНАЯ СМЕКАЛКА"
    bb = fnt.getbbox(txt)
    pw, ph = bb[2] - bb[0] + 56, bb[3] - bb[1] + 30
    tag = Image.new("RGBA", (pw + 10, ph + 12), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    td.rectangle((10, 12, pw + 10, ph + 12), fill=(0, 0, 0, 160))
    td.rectangle((0, 0, pw, ph), fill=YEL + (255,))
    td.text((28 - bb[0], 15 - bb[1]), txt, font=fnt, fill=(0, 0, 0, 255))
    rng = np.random.default_rng(3)
    grain = [rng.integers(-7, 8, (H // 4, W // 4, 1), dtype=np.int16).repeat(4, 0).repeat(4, 1) for _ in range(5)]
    # floating embers
    embers = rng.uniform(0, 1, (40, 4))

    def frame(t):
        # background slow push + parallax
        z = 1.0 + 0.05 * t / dur
        bw, bh = int(W * z), int(H * z)
        b = bg.resize((int(bg.width * z), int(bg.height * z)), Image.BILINEAR)
        ox, oy = (b.width - W) // 2, (b.height - H) // 2
        f = b.crop((ox, oy, ox + W, oy + H))
        d = ImageDraw.Draw(f)
        for ex, ey, es, ep in embers:
            yy = (ey - t * (0.04 + 0.05 * es)) % 1.0
            xx = ex + 0.01 * math.sin(t * 2 + ep * 6)
            r = 1 + 2.5 * es
            a = int(90 + 120 * es)
            d.ellipse((xx * W - r, yy * H - r, xx * W + r, yy * H + r), fill=(255, 150 + int(60 * es), 40, a))
        # shake after slam
        st = t - SLAM
        shake = 0
        if st > 0:
            shake = 14 * math.exp(-st * 7) * math.sin(st * 70)
        if t < SLAM:  # logo flying in from depth
            p = t / SLAM
            sc, ga = 2.4 - 1.4 * ease_out(p), 0
        else:
            sc = 1.0 + 0.06 * (1 - ease_back(st / 0.25)) + 0.025 * min(1, st / dur)
            ga = max(0.0, 0.75 * math.exp(-st * 2.2))
        cy = H * (0.44 if W < H else 0.42)
        shine = (t - 0.85) / 0.55
        box = logo.draw(f, W / 2 + shake, cy + shake * 0.6, sc, shine, ga)
        # tagline slides up under the logo
        if t > 0.9:
            p = ease_back((t - 0.9) / 0.3)
            ty = box[3] + int(70 if W < H else 40) + int(60 * (1 - p))
            tg = tag
            if p < 1:
                a = tg.split()[3].point(lambda v: int(v * min(1, (t - 0.9) / 0.2)))
                tg = tg.copy()
                tg.putalpha(a)
            f.paste(tg, (int(W / 2 - tg.width / 2), ty), tg)
        arr = np.asarray(f, dtype=np.int16)
        if t < 0.08:
            arr = arr * (t / 0.08)
        fl = max(0, 1 - abs(t - SLAM) / 0.10)            # flash on slam
        fl2 = max(0, 1 - (dur - t) / 0.12)               # flash into the cut
        arr = arr + int(200 * max(fl, fl2))
        arr = arr + grain[int(t * FPS) % len(grain)]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    return frame, logo.placeholder


def build(fmt="9x16"):
    mix, dur = build_audio()
    wav = TMP / "ident.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", str(wav)],
                   input=(mix * 32767).astype("<i2").tobytes(), check=True)
    frame, ph = renderer(fmt, dur)
    W, H = dims(fmt)
    out = TMP / f"ident_{fmt}_{KIND}.mp4"
    p = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", str(SR),
                          "-shortest", str(out)], stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("ident", out, round(dur, 2), "PLACEHOLDER LOGO" if ph else "real logo")
    return out


def prepend(body, out, fmt="9x16"):
    ident = TMP / f"ident_{fmt}_{KIND}.mp4"
    if not ident.exists():
        build(fmt)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(ident), "-i", str(body), "-filter_complex",
                    "[0:v]setsar=1,fps=30[v0];[1:v]setsar=1,fps=30[v1];"
                    "[0:a]aresample=44100,aformat=channel_layouts=mono[a0];[1:a]aresample=44100,aformat=channel_layouts=mono[a1];"
                    "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                    "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(out)], check=True)
    print("done", out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build(sys.argv[2] if len(sys.argv) > 2 else "9x16")
    elif cmd == "preview":
        fmt = sys.argv[2]
        _, dur = build_audio()
        fr, ph = renderer(fmt, dur)
        for ts in sys.argv[3:]:
            fr(float(ts)).save(TMP / f"iprev_{float(ts):04.2f}.jpg", quality=88)
        print("dur", round(dur, 2), "placeholder" if ph else "real")
    elif cmd == "prepend":
        prepend(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "9x16")
