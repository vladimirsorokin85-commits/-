#!/usr/bin/env python3
"""Vertical promo reel 1080x1920 for «Окопная смекалка» (shop «В Окопе»).
usage: reel.py [preview t1 t2 ...]   -> renders /tmp/reel/reel.mp4 (or preview jpgs)
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

ROOT = Path("/home/user/-/video_studio")
REEL = ROOT / "reel"
A = ROOT / "assets"
TMP = Path("/tmp/reel")
TMP.mkdir(parents=True, exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
TEMPO = 1.2
SPLASH = 1.1  # music-only opening splash before the voice
GAP = 0.18
YEL, RED, WHT, BLK, GRN = (255, 204, 0), (235, 40, 40), (255, 255, 255), (0, 0, 0), (132, 204, 22)

# segment: heading, image plan [(img, focus_x)], subtitle chunks
SEGS = [
    (None, [(9, .55), (12, .62), (27, .62), (1, .45), (29, .62)],
     ["МАГАЗИН «В ОКОПЕ»", "ПРЕДСТАВЛЯЕТ", "ОКОПНАЯ СМЕКАЛКА", "5 КОПЕЕЧНЫХ ХИТРОСТЕЙ", "СПАСАЮТ ЖИЗНЬ"]),
    ("ЧУЛОК НА ПРИЦЕЛЕ", [(11, .42), (13, .32), (2, .5)],
     ["ЖЕНСКИЙ ЧУЛОК", "НА ПРИЦЕЛЕ", "БЛИКА НЕТ", "СНАЙПЕР НЕ ВИДИТ!"]),
    ("ПЕНОФОЛ В БЛИНДАЖЕ", [(15, .62), (17, .5), (16, .5)],
     ["ПЕНОФОЛ", "ВНУТРИ БЛИНДАЖА", "ТЕПЛОВИЗОР СЛЕПНЕТ!"]),
    ("УДОЧКА ЗА 500 ₽", [(20, .5), (5, .42), (21, .3), (22, .5)],
     ["УДОЧКА ЗА 500 ₽", "МАЧТА ДЛЯ АНТЕННЫ", "САПЁРНЫЙ ЩУП", "ЛОЖНАЯ ЦЕЛЬ!"]),
    ("ЗЕРКАЛО ЗА УГОЛ", [(23, .58), (24, .58), (26, .5)],
     ["АВТОЗЕРКАЛО", "НА ПАЛКЕ", "ЗАГЛЯНИ ЗА УГОЛ", "БЕЗ ПУЛИ!"]),
    ("РАБИЦА ПРОТИВ FPV", [(27, .6), (28, .62), (29, .62), (9, .55)],
     ["РАБИЦА", "+ МИКРОВОЛНОВКА", "FPV ВЗРЫВАЕТСЯ", "ДО КРЫШИ!"]),
    ("OUTRO", [(30, .5)], ["ПОЛНЫЙ ВЫПУСК", "ПО ССЫЛКЕ В ПРОФИЛЕ", "ПОДПИШИСЬ!"]),
]


def font(w, s):
    return ImageFont.truetype(str(ROOT / "fonts" / f"Roboto-{w}.woff"), s)


# ---------------------------------------------------------------- audio
def load(path, tempo=1.0):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR)]
    if tempo != 1.0:
        cmd += ["-af", f"atempo={tempo}"]
    raw = subprocess.run(cmd + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def trim(x, thr=0.02):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    return x[max(0, idx[0] - int(.03 * SR)): idx[-1] + int(.08 * SR)]


def build_audio():
    voices = [trim(load(REEL / f"r{i}.mp3", TEMPO)) for i in range(7)]
    starts, t = [], SPLASH
    for v in voices:
        starts.append(t)
        t += len(v) / SR + GAP
    total = t + 2.2
    n = int(total * SR)
    voice = np.zeros(n, np.float32)
    for s, v in zip(starts, voices):
        voice[int(s * SR): int(s * SR) + len(v)] += v
    voice /= np.percentile(np.abs(voice), 99.9) + 1e-9
    music = load(ROOT / "music_catalog" / "jungle_hoover_174.ogg")
    off = int(22.0 * SR)
    music = np.resize(music[off:], n)
    music /= np.percentile(np.abs(music), 99.9) + 1e-9
    # ducking envelope from voice activity
    env = np.abs(voice)
    k = int(.12 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    act = np.clip(env / 0.05, 0, 1)
    duck = 1.0 - 0.72 * act
    # sidechain smoothing
    s = int(.08 * SR)
    duck = np.convolve(duck, np.ones(s) / s, "same")
    mus = music * duck * 0.55
    # impacts: boom + noise whoosh at each segment start
    rng = np.random.default_rng(3)
    for i, st in enumerate([0.0] + starts[1:]):
        p = int(max(0, st - 0.06) * SR)
        L = int(.6 * SR)
        tt = np.arange(L) / SR
        boom = np.sin(2 * np.pi * (55 * tt + 40 * np.exp(-tt * 18) / 18 * 0)) * np.exp(-tt * 7) * 0.9
        nz = rng.standard_normal(L) * np.exp(-tt * 14) * 0.25
        seg = (boom + nz)[: max(0, min(L, n - p))]
        mus[p: p + len(seg)] += seg
        if i:  # whoosh rising into the cut
            L2 = int(.35 * SR)
            q = max(0, p - L2)
            w = rng.standard_normal(p - q) * np.linspace(0, 1, p - q) ** 2 * 0.18
            mus[q:p] += w
    # end tail fade
    fade = int(1.5 * SR)
    mus[-fade:] *= np.linspace(1, 0, fade)
    mix = voice * 0.95 + mus
    mix = np.tanh(mix / np.percentile(np.abs(mix), 99.95) * 1.1) * 0.92
    pcm = (mix * 32767).astype("<i2")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    str(TMP / "mix.wav")], input=pcm.tobytes(), check=True)
    ends = [s + len(v) / SR for s, v in zip(starts, voices)]
    return starts, ends, total


# ---------------------------------------------------------------- visuals
IMG_W, IMG_H, IMG_Y = 1080, 1350, 300


class Shot:
    _cache = {}

    def __init__(self, img, fx):
        key = (img, fx)
        if key not in Shot._cache:
            im = Image.open(A / f"smekalka_{img:02d}.jpg").convert("RGB")
            if img == 3:
                im = im.crop((400, 0, 1376, 549))
            im = ImageEnhance.Contrast(im).enhance(1.1)
            im = ImageEnhance.Color(im).enhance(1.12)
            # crop for 1080x1350 at 1.25x headroom
            ar = IMG_W / IMG_H
            cw = im.height * ar
            x0 = int(min(max(0, fx * im.width - cw / 2), im.width - cw))
            big = im.crop((x0, 0, x0 + int(cw), im.height)).resize((int(IMG_W * 1.25), int(IMG_H * 1.25)), Image.LANCZOS)
            bg = im.resize((W, int(W / im.width * im.height))).crop((0, 0, W, int(W / im.width * im.height)))
            bg = bg.resize((int(H * im.width / im.height), H)).filter(ImageFilter.GaussianBlur(30))
            bx = (bg.width - W) // 2
            bg = ImageEnhance.Brightness(bg.crop((bx, 0, bx + W, H))).enhance(0.45)
            Shot._cache[key] = (big, bg)
        self.big, self.bg = Shot._cache[key]

    def frame(self, p, kind):
        # p 0..1 progress inside shot; punch-in at start then slow drift
        z = 1.0 + 0.10 * p + 0.12 * max(0, 1 - p * 6) ** 2
        z = min(z, 1.25)
        cw, ch = IMG_W * 1.25 / z, IMG_H * 1.25 / z
        mx, my = self.big.width - cw, self.big.height - ch
        dx = (0.5 + (0.25 if kind % 2 else -0.25) * (p - 0.5)) * mx
        box = (dx, my * 0.5, dx + cw, my * 0.5 + ch)
        return self.big.resize((IMG_W, IMG_H), Image.BILINEAR, box=box)


def plate(d, xy, s, f, bgc, fg, pad=(20, 8), anchor="l"):
    bb = d.textbbox((0, 0), s, font=f)
    w, h = bb[2] - bb[0] + 2 * pad[0], bb[3] - bb[1] + 2 * pad[1]
    x = xy[0] - (w // 2 if anchor == "c" else 0)
    d.rectangle((x, xy[1], x + w, xy[1] + h), fill=bgc)
    d.text((x + pad[0] - bb[0], xy[1] + pad[1] - bb[1]), s, font=f, fill=fg)
    return x, xy[1], x + w, xy[1] + h


def fit(s, w_max, start, wt="Black"):
    sz = start
    while font(wt, sz).getlength(s) > w_max and sz > 30:
        sz -= 4
    return font(wt, sz)


def ease_back(x, s=2.0):
    x = min(1, max(0, x)) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def stroke_text(im, center, s, f, fill, scale=1.0, stroke=8):
    if scale != 1.0:
        f = font("Black", max(10, int(f.size * scale)))
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), s, font=f, stroke_width=stroke)
    x = center[0] - (bb[2] - bb[0]) // 2 - bb[0]
    y = center[1] - (bb[3] - bb[1]) // 2 - bb[1]
    d.text((x + 6, y + 8), s, font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
    d.text((x, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=BLK)


def make_timeline(starts, ends, total):
    segs = []
    for i, (head, plan, subs) in enumerate(SEGS):
        s0 = 0.0 if i == 0 else starts[i] - 0.05
        s1 = starts[i + 1] - 0.05 if i + 1 < len(SEGS) else total
        segs.append((s0, s1, starts[i], ends[i]))
    return segs


def render(t, segs, total, grain):
    i = max(k for k, s in enumerate(segs) if s[0] <= t)
    s0, s1, v0, v1 = segs[i]
    head, plan, subs = SEGS[i]
    seg_t = t - s0
    # shots evenly across the segment (intro: faster)
    dur = s1 - s0
    n = len(plan)
    k = min(n - 1, int(seg_t / dur * n))
    sh_p = (seg_t - k * dur / n) / (dur / n)
    img, fx = plan[k]
    shot = Shot(img, fx)
    frame = shot.bg.copy()
    pic = shot.frame(sh_p, k + i)
    frame.paste(pic, (0, IMG_Y))
    d = ImageDraw.Draw(frame)
    # top brand bar
    d.rectangle((0, 0, W, IMG_Y), fill=(12, 13, 12))
    plate(d, (W // 2, 46), "«В ОКОПЕ»", font("Black", 64), YEL, BLK, pad=(26, 10), anchor="c")
    d.text((W // 2, 176), "ОКОПНАЯ СМЕКАЛКА · СПЕЦВЫПУСК", font=font("Black", 40), fill=WHT, anchor="mm")
    # chapter heading (slams in)
    if head and head != "OUTRO":
        a = ease_back((t - s0) / 0.35)
        hx = int(-W * (1 - a))
        f1 = font("Black", 54)
        bb = plate(d, (40 + hx, 222), f"ХИТРОСТЬ №{i}", f1, RED, WHT, pad=(18, 6))
        f2 = fit(head, W - 80, 60)
        stroke_text(frame, (W // 2 + hx, IMG_Y + 92), head, f2, YEL, stroke=6)
    elif head is None:
        # intro splash: big logo over the first image before voice
        if t < SPLASH + 0.4:
            a = ease_back(t / 0.4)
            sc = 0.4 + 0.6 * a
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int(140 * min(1, t / 0.2))))
            frame.paste(ov, (0, 0), ov)
            stroke_text(frame, (W // 2, 860), "ОКОПНАЯ", font("Black", 150), WHT, sc, 10)
            stroke_text(frame, (W // 2, 1020), "СМЕКАЛКА", font("Black", 150), YEL, sc, 10)
            stroke_text(frame, (W // 2, 1180), "5 ХИТРОСТЕЙ ЗА КОПЕЙКИ", font("Black", 66), WHT, sc, 6)
    # subtitles — chunks evenly over the voice span, pop-in
    if t >= v0 - 0.05 and not (head is None and t < SPLASH + 0.4):
        span = max(0.1, v1 - v0)
        weights = [len(c) + 6 for c in subs]
        cum = np.cumsum([0] + weights) / sum(weights)
        r = min(0.999, max(0, (t - v0) / span))
        c = int(np.searchsorted(cum, r, side="right") - 1)
        c = min(c, len(subs) - 1)
        c_t = (t - v0) - cum[c] * span
        txt = subs[c]
        hot = any(ch.isdigit() for ch in txt) or txt.endswith("!")
        f = fit(txt, W - 90, 104)
        sc = 0.75 + 0.25 * ease_back(c_t / 0.18)
        stroke_text(frame, (W // 2, 1460), txt, f, YEL if hot else WHT, sc, 9)
    # outro card
    if head == "OUTRO":
        a = ease_back((t - s0) / 0.4)
        f = font("Black", 50)
        y0 = 1190
        plate(d, (W // 2, y0 - int(60 * (1 - a))), "t.me/vokope_ru", f, (20, 20, 20), YEL, pad=(26, 12), anchor="c")
        plate(d, (W // 2, y0 + 96), "vk.com/vokope_rus", f, (20, 20, 20), WHT, pad=(26, 12), anchor="c")
        # bouncing arrow
        by = 1800 + int(14 * math.sin(t * 9))
        d.polygon([(W // 2 - 50, by), (W // 2 + 50, by), (W // 2, by + 60)], fill=YEL)
    # bottom progress: 5 pills
    by = IMG_Y + IMG_H + 40
    for j in range(1, 6):
        x = W // 2 + (j - 3) * 170 - 70
        done = (head is not None) and (head == "OUTRO" or j <= i)
        cur = j == i and head not in (None, "OUTRO")
        col = RED if cur else (YEL if done else (70, 70, 70))
        d.rounded_rectangle((x, by, x + 140, by + 64), 14, fill=col)
        d.text((x + 70, by + 32), f"№{j}", font=font("Black", 36), fill=BLK if (cur or done) else (170, 170, 170), anchor="mm")
    if head != "OUTRO":
        d.text((W // 2, by + 140), "ПОЛНЫЙ ВЫПУСК — В ПРОФИЛЕ", font=font("Bold", 38), fill=(200, 200, 200), anchor="mm")
    # white flash on segment change + shake
    arr = np.asarray(frame, dtype=np.int16)
    fl = max(0, 1 - (t - s0) / 0.12) if i else 0
    if fl:
        arr = arr + int(160 * fl)
    arr = arr + grain[int(t * FPS) % len(grain)]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main():
    starts, ends, total = build_audio()
    segs = make_timeline(starts, ends, total)
    rng = np.random.default_rng(1)
    grain = [rng.integers(-6, 7, (H // 4, W // 4, 1), dtype=np.int16).repeat(4, 0).repeat(4, 1) for _ in range(6)]
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for ts in sys.argv[2:]:
            render(float(ts), segs, total, grain).save(TMP / f"prev_{float(ts):05.1f}.jpg", quality=85)
        print("total", round(total, 2), "starts", [round(s, 2) for s in starts])
        return
    out = TMP / "reel.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", str(TMP / "mix.wav"),
                          "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                          "-shortest", str(out)], stdin=subprocess.PIPE)
    nfr = int(total * FPS)
    for fi in range(nfr):
        p.stdin.write(render(fi / FPS, segs, total, grain).tobytes())
        if fi % 150 == 0:
            print(f"{fi}/{nfr}", flush=True)
    p.stdin.close()
    p.wait()
    print("done", out, round(total, 2))


if __name__ == "__main__":
    main()
