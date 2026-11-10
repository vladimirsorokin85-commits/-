#!/usr/bin/env python3
"""Vertical 9:16 (1080x1920 @ 30fps) Chorus-Only Reel Renderer for «ПОСТ-РОССИЯ».

Audio slice: 111.95s .. 157.56s (45.61s) of Пост-Россия.mp3:
  - 00.00 - 11.30s: Raw A Cappella Folk Choir Lament (Shots reel_01..reel_04)
  - 11.30 - 33.75s: Massive Sub-Bass Drop + Double Climax Folk Choir (Shots reel_05..reel_09)
  - 33.75 - 45.61s: Choir-to-Sea Outro & Warm Horizon Dawn Line (Shot reel_10)
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
import zipfile
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

THIS_DIR = Path(__file__).resolve().parent
PR_DIR = THIS_DIR.parent
REPO_ROOT = PR_DIR.parents[1]
if str(PR_DIR) not in sys.path:
    sys.path.insert(0, str(PR_DIR))

from grade_post_rossiya import apply_color_state  # noqa: E402

W, H, FPS = 1080, 1920, 30
BASE_W, BASE_H = 1296, 2304
AUDIO_START = 111.95
AUDIO_END = 157.56
REEL_DUR = round(AUDIO_END - AUDIO_START, 2)  # 45.61s

TMP_DIR = Path("/tmp/post_rossiya_reel")
OUT_DIR = PR_DIR / "output"
FRAMES_DIR = THIS_DIR / "frames"
AUDIO_SRC = PR_DIR / "audio" / "post_rossiya_song.mp3"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BLACK_FRAME = Image.new("RGB", (W, H), (0, 0, 0))

REEL_SHOTS = [
    {
        "num": 1, "id": "reel_01", "t0": 0.00, "t1": 2.85,
        "cue": "Хор (а капелла): «И стонет в лапах бессилия...»",
        "desc_ru": "Девятиэтажка в предрассветном тумане и одно тёплое окно",
        "color_state": "faded_memory", "move": "tilt_up", "focus": (0.50, 0.50), "fx": "fade_in_cold",
    },
    {
        "num": 2, "id": "reel_02", "t0": 2.85, "t1": 5.65,
        "cue": "Хор (а капелла): «Пост-Россия: прости меня...»",
        "desc_ru": "Пожилая женщина из хора смотрит прямо в объектив",
        "color_state": "faded_memory", "move": "slow_in", "focus": (0.50, 0.44), "fx": None,
    },
    {
        "num": 3, "id": "reel_03", "t0": 5.65, "t1": 8.45,
        "cue": "Хор (а капелла): «Так пахнет утро последнее...»",
        "desc_ru": "Красные гвоздики у дождевой лужи с отражением панелек",
        "color_state": "faded_memory", "move": "slow_in", "focus": (0.50, 0.54), "fx": "rain_streaks",
    },
    {
        "num": 4, "id": "reel_04", "t0": 8.45, "t1": 11.30,
        "cue": "Хор (а капелла): «Предосеннее, предрасстрельное...»",
        "desc_ru": "Пустая трасса и бетонная остановка в густом тумане",
        "color_state": "faded_memory", "move": "slow_in", "focus": (0.50, 0.52), "fx": "ground_mist",
    },
    {
        "num": 5, "id": "reel_05", "t0": 11.30, "t1": 15.05,
        "cue": "УДАР САБ-БАСА · Хор: «И стонет в лапах бессилия...»",
        "desc_ru": "Женский народный хор посреди пустой городской площади",
        "color_state": "colorless_predawn", "move": "slow_out", "focus": (0.50, 0.56), "fx": None,
    },
    {
        "num": 6, "id": "reel_06", "t0": 15.05, "t1": 18.80,
        "cue": "Кульминация хора: «Пост-Россия: прости меня...»",
        "desc_ru": "Слеза на щеке молодой женщины в поющем хоре",
        "color_state": "colorless_predawn", "move": "slow_in", "focus": (0.46, 0.44), "fx": None,
    },
    {
        "num": 7, "id": "reel_07", "t0": 18.80, "t1": 22.50,
        "cue": "Кульминация хора: «Так пахнет утро последнее...»",
        "desc_ru": "Главный герой молча стоит на мокрой площади перед хором",
        "color_state": "colorless_predawn", "move": "slow_in", "focus": (0.50, 0.48), "fx": None,
    },
    {
        "num": 8, "id": "reel_08", "t0": 22.50, "t1": 28.10,
        "cue": "Пиковый распев хора: «И стонет в лапах бессилия...»",
        "desc_ru": "Стая чёрных ворон взмывает над проводами и трубами окраины",
        "color_state": "colorless_predawn", "move": "tilt_up", "focus": (0.50, 0.50), "fx": None,
    },
    {
        "num": 9, "id": "reel_09", "t0": 28.10, "t1": 33.75,
        "cue": "Хор: «Предосеннее, предрасстрельное...» (до обрыва бита)",
        "desc_ru": "Герой медленно закрывает глаза, алые лепестки на ветру",
        "color_state": "colorless_predawn", "move": "slow_in", "focus": (0.50, 0.44), "fx": "red_petals_wind",
    },
    {
        "num": 10, "id": "reel_10", "t0": 33.75, "t1": REEL_DUR,
        "cue": "Кода хора: Холодное море и тёплая полоска света на горизонте",
        "desc_ru": "Холодное северное море и тонкая полоска рассвета на горизонте",
        "color_state": "predawn_horizon", "move": "static_live", "focus": (0.50, 0.50), "fx": "horizon_dawn",
    },
]


def ease_io(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def gate_weave(t: float, amp: float = 0.50) -> tuple[float, float]:
    dx = (math.sin(t * 1.7) * 0.9 + math.sin(t * 4.3 + 1.1) * 0.4) * amp
    dy = (math.cos(t * 1.3 + 0.7) * 0.8 + math.sin(t * 3.9 + 2.0) * 0.35) * amp
    return dx, dy


@lru_cache(maxsize=12)
def load_vertical_base(shot_id: str, color_state: str) -> Image.Image:
    im = Image.open(FRAMES_DIR / f"{shot_id}.jpg").convert("RGB")
    iw, ih = im.size
    target_w = int(ih * 9 / 16)
    if target_w <= iw:
        x0 = (iw - target_w) // 2
        im = im.crop((x0, 0, x0 + target_w, ih))
    else:
        target_h = int(iw * 16 / 9)
        y0 = (ih - target_h) // 2
        im = im.crop((0, y0, iw, y0 + target_h))
    im = im.resize((BASE_W, BASE_H), Image.LANCZOS)
    return apply_color_state(im, color_state, seed=29, with_grain=False)


def crop_vertical(base: Image.Image, z: float, cx: float, cy: float, dx: float = 0.0, dy: float = 0.0) -> Image.Image:
    bw, bh = base.size
    ww, wh = bw / z, bh / z
    x0 = min(max(0.0, cx * bw - ww / 2.0 + dx), bw - ww)
    y0 = min(max(0.0, cy * bh - wh / 2.0 + dy), bh - wh)
    return base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + wh))


@lru_cache(maxsize=2)
def _rain_tile_v(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (W + 240, H + 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(210):
        x = int(rng.integers(0, W + 220))
        y = int(rng.integers(0, H + 380))
        ln = int(rng.integers(32, 78))
        alpha = int(rng.integers(18, 46))
        d.line((x, y, x - ln // 6, y + ln), fill=(198, 212, 226, alpha), width=1)
    return im.filter(ImageFilter.GaussianBlur(0.7))


@lru_cache(maxsize=1)
def _mist_v() -> Image.Image:
    rng = np.random.default_rng(77)
    noise = rng.normal(0.5, 0.22, (140, 160)).clip(0.0, 1.0)
    cloud = Image.fromarray((noise * 255).astype(np.uint8)).resize((W * 2, H), Image.BICUBIC)
    cloud = cloud.filter(ImageFilter.GaussianBlur(30))
    arr = np.asarray(cloud, np.float32) / 255.0
    y = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    mask = np.exp(-((y - 0.56) / 0.22) ** 2) * 0.32
    alpha = (arr * mask * 255).clip(0, 90).astype(np.uint8)
    rgba = np.zeros((H, W * 2, 4), dtype=np.uint8)
    rgba[..., 0] = 205
    rgba[..., 1] = 212
    rgba[..., 2] = 220
    rgba[..., 3] = alpha
    return Image.fromarray(rgba)


@lru_cache(maxsize=1)
def _horizon_v() -> np.ndarray:
    y = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    x = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :, None]
    slit = np.exp(-((y - 0.495) / 0.013) ** 2) * np.exp(-(x / 0.85) ** 2)
    glow = np.exp(-((y - 0.492) / 0.065) ** 2) * np.exp(-(x / 0.95) ** 2)
    return slit * np.array([0.13, 0.085, 0.030], np.float32) + glow * np.array([0.045, 0.028, 0.008], np.float32)


def apply_fx_v(frame: Image.Image, fx: str | None, p: float, t: float) -> Image.Image:
    if not fx:
        return frame
    if fx == "fade_in_cold" and p < 0.22:
        return Image.blend(BLACK_FRAME, frame, ease_io(p / 0.22))
    if fx == "rain_streaks":
        tile = _rain_tile_v(1 if int(t * 24) % 2 == 0 else 2)
        ox = int((t * 85) % 200)
        oy = int((t * 410) % 360)
        out = frame.convert("RGBA")
        out.alpha_composite(tile.crop((ox, oy, ox + W, oy + H)))
        return out.convert("RGB")
    if fx == "ground_mist":
        mist = _mist_v()
        ox = int((t * 26) % W)
        out = frame.convert("RGBA")
        out.alpha_composite(mist.crop((ox, 0, ox + W, H)))
        return out.convert("RGB")
    if fx == "red_petals_wind":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        rng = np.random.default_rng(91)
        for _ in range(14):
            x0 = float(rng.uniform(-0.15, 1.05))
            y0 = float(rng.uniform(0.55, 0.95))
            spd = float(rng.uniform(0.20, 0.45))
            rw, rh = int(rng.integers(8, 17)), int(rng.integers(5, 11))
            px = ((x0 + p * spd * 1.4) % 1.2 - 0.1) * W
            py = (y0 + math.sin(t * 3.0 + x0 * 9.0) * 0.02) * H
            d.ellipse((px, py, px + rw, py + rh), fill=(162, 36, 40, 170))
        overlay = overlay.filter(ImageFilter.GaussianBlur(1.5))
        out = frame.convert("RGBA")
        out.alpha_composite(overlay)
        return out.convert("RGB")
    if fx == "horizon_dawn":
        a = np.asarray(frame, np.float32) / 255.0
        emerge = ease_io(min(1.0, p / 0.80))
        a = a + emerge * _horizon_v()
        out = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        if p > 0.88:
            out = Image.blend(out, BLACK_FRAME, ease_io((p - 0.88) / 0.12))
        return out
    return frame


def render_shot_v(sh: dict, t: float) -> Image.Image:
    base = load_vertical_base(sh["id"], sh["color_state"])
    dur = max(0.05, sh["t1"] - sh["t0"])
    p = min(1.0, max(0.0, (t - sh["t0"]) / dur))
    ep = ease_io(p)
    fx, fy = sh["focus"]
    z_base = 1.04
    mv = sh["move"]
    cx, cy = fx, fy
    if mv == "slow_in":
        z = z_base + 0.095 * ep
    elif mv == "slow_out":
        z = (z_base + 0.105) - 0.095 * ep
    elif mv == "tilt_up":
        z = max(z_base, 1.13)
        cy = min(0.57, fy + 0.06) - 0.12 * ep
    else:
        z = z_base + 0.022 * ep
    dx, dy = gate_weave(t, amp=0.45 if mv == "static_live" else 0.65)
    fr = crop_vertical(base, z, cx, cy, dx, dy)
    return apply_fx_v(fr, sh["fx"], p, t)


def frame_at_v(t: float) -> Image.Image:
    idx = len(REEL_SHOTS) - 1
    for i, s in enumerate(REEL_SHOTS):
        if s["t0"] <= t < s["t1"]:
            idx = i
            break
    sh = REEL_SHOTS[idx]
    fr = render_shot_v(sh, t)
    # Razor-sharp cut on Shot 5 (11.30s sub-bass drop!), flowing 0.45s dissolves on all other choir transitions
    if idx > 0 and sh["num"] != 5:
        diss = 0.45
        u = t - sh["t0"]
        if 0.0 <= u < diss:
            prev_sh = dict(REEL_SHOTS[idx - 1])
            prev_sh["t1"] = sh["t0"] + diss
            prev_fr = render_shot_v(prev_sh, t)
            fr = Image.blend(prev_fr, fr, ease_io(u / diss))
    return fr


def render_worker(part_idx: int, num_parts: int, out_path: Path) -> None:
    total_frames = int(round(REEL_DUR * FPS))
    f0 = total_frames * part_idx // num_parts
    f1 = total_frames * (part_idx + 1) // num_parts
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an",
        "-vf", "format=yuv420p,noise=c0s=4:c1s=2:c2s=2:allf=t",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-profile:v", "high",
        "-g", str(FPS * 2), "-movflags", "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    st = time.time()
    for fi in range(f0, f1):
        proc.stdin.write(frame_at_v(fi / FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"Reel worker {part_idx} failed")
    print(f"[reel worker {part_idx+1}/{num_parts}] {f1-f0} frames in {time.time()-st:.1f}s", flush=True)


def build_reel() -> dict:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    p0 = TMP_DIR / "reel_p0.mp4"
    p1 = TMP_DIR / "reel_p1.mp4"
    w0 = subprocess.Popen([sys.executable, __file__, "--worker", "0", "2", str(p0)])
    w1 = subprocess.Popen([sys.executable, __file__, "--worker", "1", "2", str(p1)])
    if w0.wait() != 0 or w1.wait() != 0:
        raise RuntimeError("Reel parallel render failed")

    concat_f = TMP_DIR / "reel_concat.txt"
    concat_f.write_text(f"file '{p0}'\nfile '{p1}'\n", encoding="utf-8")
    silent_reel = TMP_DIR / "reel_silent_hq.mp4"
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_f),
        "-c:v", "copy", "-an", "-movflags", "+faststart", str(silent_reel),
    ], check=True)

    # Mux exact chorus slice [111.95s .. 157.56s] with clean 0.35s fade-in and 0.70s fade-out
    out_reel = OUT_DIR / "post_rossiya_reel_chorus_1080x1920.mp4"
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(silent_reel),
        "-ss", f"{AUDIO_START:.2f}", "-t", f"{REEL_DUR:.2f}", "-i", str(AUDIO_SRC),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-maxrate", "3200k", "-bufsize", "6400k", "-pix_fmt", "yuv420p",
        "-af", f"afade=t=in:st=0:d=0.35,afade=t=out:st={REEL_DUR - 0.70:.2f}:d=0.70",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(out_reel),
    ], check=True)

    # Also pack the 10 new vertical images into a timecoded ZIP
    reel_zip = OUT_DIR / "post_rossiya_reel_10_vertical_frames.zip"
    with zipfile.ZipFile(reel_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        for sh in REEL_SHOTS:
            src = FRAMES_DIR / f"{sh['id']}.jpg"
            tc = f"00m{sh['t0']:05.2f}s-00m{sh['t1']:05.2f}s"
            zf.write(src, f"ПОСТ-РОССИЯ_РИЛС_ПРИПЕВ_9x16/{sh['num']:02d}__{tc}__{sh['id']}.jpg")

    meta = {
        "reel_video": str(out_reel.relative_to(REPO_ROOT)),
        "size_mb": round(out_reel.stat().st_size / 1e6, 2),
        "resolution": "1080x1920",
        "fps": FPS,
        "duration_sec": REEL_DUR,
        "song_slice_sec": [AUDIO_START, AUDIO_END],
        "shots": len(REEL_SHOTS),
        "frames_zip": str(reel_zip.relative_to(REPO_ROOT)),
    }
    (OUT_DIR / "reel_chorus_info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=3, metavar=("IDX", "NPARTS", "OUT"))
    args = ap.parse_args()
    if args.worker:
        render_worker(int(args.worker[0]), int(args.worker[1]), Path(args.worker[2]))
        return
    build_reel()


if __name__ == "__main__":
    main()
