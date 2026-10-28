#!/usr/bin/env python3
"""Parallel 1080p 30fps silent cinema renderer for «ПОСТ-РОССИЯ».

Outputs:
  1. video_studio/post_rossiya/output/post_rossiya_master_1080p.mp4
     Full 2:38 (158.0s) silent H.264 1920x1080@30fps video base (all 88 shots; uses dedicated
     shot_XXX.jpg wherever generated and art-directed graded anchor plates for queued slots).
  2. video_studio/post_rossiya/output/post_rossiya_ready_1080p.mp4
     Pure chronological assembly of all consecutive 100%-generated AI shots so far.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[1]
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from grade_post_rossiya import apply_color_state, make_specimen  # noqa: E402
from storyboard_data import export_manifests, get_broll_shots, get_main_shots  # noqa: E402

W, H, FPS = 1920, 1080, 30
BASE_W, BASE_H = 2304, 1296
TMP_DIR = Path("/tmp/post_rossiya")
OUT_DIR = THIS_DIR / "output"

BLACK_FRAME = Image.new("RGB", (W, H), (0, 0, 0))


def ease_io(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def gate_weave(t: float, amp: float = 0.45) -> tuple[float, float]:
    """Subtle 35mm film gate micro-movement (prevents frozen digital look on static shots)."""
    dx = (math.sin(t * 1.7) * 0.9 + math.sin(t * 4.3 + 1.1) * 0.4) * amp
    dy = (math.cos(t * 1.3 + 0.7) * 0.8 + math.sin(t * 3.9 + 2.0) * 0.35) * amp
    return dx, dy


@lru_cache(maxsize=36)
def load_graded_base(rel_path: str, color_state: str, is_fallback: bool) -> Image.Image:
    full_path = REPO_ROOT / rel_path
    if not full_path.exists():
        full_path = REPO_ROOT / "video_studio/post_rossiya/refs/ref_04_color.jpg"
    im = Image.open(full_path).convert("RGB")
    iw, ih = im.size
    target_w = int(ih * 16 / 9)
    if target_w <= iw:
        x0 = (iw - target_w) // 2
        im = im.crop((x0, 0, x0 + target_w, ih))
    else:
        target_h = int(iw * 9 / 16)
        y0 = (ih - target_h) // 2
        im = im.crop((0, y0, iw, y0 + target_h))
    im = im.resize((BASE_W, BASE_H), Image.LANCZOS)
    if is_fallback:
        # Subtle tonal differentiation for animatic placeholder plates until their dedicated AI shot arrives
        im = ImageEnhance.Brightness(im).enhance(0.93)
    graded = apply_color_state(im, color_state, seed=17, with_grain=False)
    return graded


def crop_view(base: Image.Image, z: float, cx: float, cy: float, dx: float = 0.0, dy: float = 0.0) -> Image.Image:
    bw, bh = base.size
    ww, wh = bw / z, bh / z
    x0 = min(max(0.0, cx * bw - ww / 2.0 + dx), bw - ww)
    y0 = min(max(0.0, cy * bh - wh / 2.0 + dy), bh - wh)
    return base.transform(
        (W, H),
        Image.AFFINE,
        (ww / W, 0.0, x0, 0.0, wh / H, y0),
        resample=Image.BILINEAR,
    )


# ------------------------------------------------------------------
# Pre-baked lightweight procedural atmospheric layers
# ------------------------------------------------------------------
@lru_cache(maxsize=2)
def _rain_tile(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (W + 300, H + 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(190):
        x = int(rng.integers(0, W + 260))
        y = int(rng.integers(0, H + 360))
        length = int(rng.integers(26, 68))
        alpha = int(rng.integers(16, 44))
        d.line((x, y, x - length // 5, y + length), fill=(195, 210, 225, alpha), width=1)
    return im.filter(ImageFilter.GaussianBlur(0.7))


@lru_cache(maxsize=1)
def _mist_band() -> Image.Image:
    rng = np.random.default_rng(108)
    noise = rng.normal(0.5, 0.22, (90, 240)).clip(0.0, 1.0)
    cloud = Image.fromarray((noise * 255).astype(np.uint8)).resize((W * 2, H), Image.BICUBIC)
    cloud = cloud.filter(ImageFilter.GaussianBlur(28))
    arr = np.asarray(cloud, np.float32) / 255.0
    y = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    # Concentrated in lower-middle horizon (0.45..0.92)
    mask = np.exp(-((y - 0.68) / 0.20) ** 2) * 0.34
    alpha = (arr * mask * 255).clip(0, 95).astype(np.uint8)
    rgba = np.zeros((H, W * 2, 4), dtype=np.uint8)
    rgba[..., 0] = 205
    rgba[..., 1] = 212
    rgba[..., 2] = 220
    rgba[..., 3] = alpha
    return Image.fromarray(rgba)


@lru_cache(maxsize=1)
def _petals_sprite() -> list[tuple[float, float, float, int, int]]:
    rng = np.random.default_rng(84)
    out = []
    for _ in range(22):
        out.append((
            float(rng.uniform(-0.15, 1.05)),
            float(rng.uniform(0.35, 0.94)),
            float(rng.uniform(0.16, 0.42)),
            int(rng.integers(7, 16)),
            int(rng.integers(4, 10)),
        ))
    return out


def apply_live_fx(frame: Image.Image, fx: str | None, p: float, t: float, shot_meta: dict) -> Image.Image:
    if not fx:
        return frame

    if fx == "phone_emerge":
        # 0:00–0:01.2: pitch black -> faint glowing smartphone rectangle -> reveal table
        if p < 0.26:
            return BLACK_FRAME.copy()
        if p < 0.72:
            k = ease_io((p - 0.26) / 0.46)
            base_reveal = Image.blend(BLACK_FRAME, frame, k * 0.82)
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(glow)
            alpha = int(85 * math.sin(k * math.pi))
            poly = [(810, 560), (1055, 455), (1160, 515), (915, 630)]
            d.polygon(poly, fill=(175, 205, 235, alpha))
            glow = glow.filter(ImageFilter.GaussianBlur(18))
            out = base_reveal.convert("RGBA")
            out.alpha_composite(glow)
            return out.convert("RGB")
        k2 = ease_io((p - 0.72) / 0.28)
        return Image.blend(Image.blend(BLACK_FRAME, frame, 0.82), frame, k2)

    if fx in ("rain_streaks", "rain_window_transition"):
        tile = _rain_tile(1 if int(t * 24) % 2 == 0 else 2)
        ox = int((t * 95) % 240)
        oy = int((t * 380) % 340)
        crop = tile.crop((ox, oy, ox + W, oy + H))
        out = frame.convert("RGBA")
        out.alpha_composite(crop)
        res = out.convert("RGB")
        if fx == "rain_window_transition" and p > 0.68:
            # Soft rain-blur transition at 0:19 into Act II
            blur_amt = ease_io((p - 0.68) / 0.32) * 5.5
            res = res.filter(ImageFilter.GaussianBlur(blur_amt))
        return res

    if fx == "ground_mist":
        mist = _mist_band()
        ox = int((t * 28) % W)
        sub = mist.crop((ox, 0, ox + W, H))
        out = frame.convert("RGBA")
        out.alpha_composite(sub)
        return out.convert("RGB")

    if fx == "crows_drift":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for i in range(14):
            bx = ((0.08 * i + p * (0.22 + 0.015 * (i % 4))) % 1.15 - 0.07) * W
            by = (0.14 + 0.022 * ((i * 7) % 9) - p * 0.05) * H + math.sin(t * 5.0 + i) * 3.0
            wing = math.sin(t * 9.5 + i * 1.7) * 5.0
            d.line((bx - 8, by - wing, bx, by, bx + 8, by - wing), fill=(18, 20, 22, 165), width=2)
        overlay = overlay.filter(ImageFilter.GaussianBlur(0.6))
        out = frame.convert("RGBA")
        out.alpha_composite(overlay)
        return out.convert("RGB")

    if fx == "windows_extinguish":
        # Gradually extinguish warm glowing apartment windows one by one across p in 0..1
        a = np.asarray(frame, np.float32)
        warmth = (a[..., 0] - a[..., 2]) * (a.mean(-1) / 255.0)
        if warmth.max() > 8.0:
            # Divide width into 6 vertical sectors that turn off sequentially
            xs = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]
            thresholds = np.floor(xs * 6.0) / 6.0 + 0.12
            off_mask = np.clip((p - thresholds) / 0.10, 0.0, 1.0)[:, :, None] if False else np.clip((p - thresholds) / 0.10, 0.0, 1.0)
            win_mask = np.clip((warmth - 7.0) / 18.0, 0.0, 1.0) * off_mask
            darken = 1.0 - 0.72 * win_mask[..., None]
            a = a * darken
            return Image.fromarray(a.clip(0, 255).astype(np.uint8))
        return frame

    if fx == "red_petals_wind":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for x0, y0, spd, rw, rh in _petals_sprite():
            px = ((x0 + p * spd * 1.4) % 1.2 - 0.1) * W
            py = (y0 + math.sin(t * 3.2 + x0 * 10.0) * 0.025) * H
            d.ellipse((px, py, px + rw, py + rh), fill=(158, 34, 38, 175))
        overlay = overlay.filter(ImageFilter.GaussianBlur(1.4))
        out = frame.convert("RGBA")
        out.alpha_composite(overlay)
        return out.convert("RGB")

    if fx == "horizon_dawn_line":
        # 6-second final hold: faint warm slit of dawn slowly emerges on the sea horizon, then fades to black
        a = np.asarray(frame, np.float32) / 255.0
        emerge = ease_io(min(1.0, p / 0.82))
        y = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
        x = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :, None]
        slit = np.exp(-((y - 0.52) / 0.018) ** 2) * np.exp(-(x / 0.78) ** 2)
        soft_glow = np.exp(-((y - 0.51) / 0.085) ** 2) * np.exp(-(x / 0.90) ** 2)
        warm = slit * np.array([0.13, 0.085, 0.032], np.float32) + soft_glow * np.array([0.045, 0.028, 0.008], np.float32)
        a = a + emerge * warm
        out = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        if p > 0.88:
            fade = ease_io((p - 0.88) / 0.12)
            out = Image.blend(out, BLACK_FRAME, fade)
        return out

    return frame


def render_single_shot_frame(sh: dict, t: float) -> Image.Image:
    is_fb = not sh["generated"]
    src = sh["file"] if sh["generated"] else sh["fallback_source"]
    base = load_graded_base(src, sh["color_state"], is_fb)

    dur = max(0.05, sh["t1"] - sh["t0"])
    u = min(dur, max(0.0, t - sh["t0"]))
    p = u / dur
    ep = ease_io(p)

    if is_fb:
        fx, fy, z_base = sh["fallback_crop"]
    else:
        fx, fy = sh["focus"]
        z_base = 1.04

    mv = sh["move"]
    cx, cy = fx, fy
    if mv == "slow_in":
        z = z_base + 0.10 * ep
    elif mv == "slow_out":
        z = (z_base + 0.11) - 0.10 * ep
    elif mv == "pan_left":
        z = max(z_base, 1.13)
        cx = min(0.58, fx + 0.06) - 0.12 * ep
    elif mv == "pan_right":
        z = max(z_base, 1.13)
        cx = max(0.42, fx - 0.06) + 0.12 * ep
    elif mv == "tilt_up":
        z = max(z_base, 1.14)
        cy = min(0.58, fy + 0.07) - 0.14 * ep
    else:  # static_live
        z = z_base + 0.018 * ep

    dx, dy = gate_weave(t, amp=0.50 if mv == "static_live" else 0.70)
    fr = crop_view(base, z, cx, cy, dx, dy)
    fr = apply_live_fx(fr, sh.get("live_fx"), p, t, sh)
    return fr


def should_soft_dissolve(prev_sh: dict, cur_sh: dict) -> float:
    """Return dissolve duration in seconds (0.0 for hard documentary cuts)."""
    if cur_sh["num"] == 13:
        return 0.45  # Rain transition into Act II
    if cur_sh["num"] == 33:
        return 0.0   # Sharp cut to state queue!
    if "ПРИПЕВ" in cur_sh["act"] or "ФИНАЛ" in cur_sh["act"]:
        return 0.48  # Flowing dream-like dissolves during Choir & Finale
    return 0.0


def frame_at(shots: list[dict], t: float) -> Image.Image:
    idx = len(shots) - 1
    for i, s in enumerate(shots):
        if s["t0"] <= t < s["t1"]:
            idx = i
            break
    sh = shots[idx]
    fr = render_single_shot_frame(sh, t)
    if idx > 0:
        diss = should_soft_dissolve(shots[idx - 1], sh)
        u = t - sh["t0"]
        if diss > 0.0 and 0.0 <= u < diss:
            # Hold outgoing shot slightly past its end for smooth cross-dissolve
            prev_sh = dict(shots[idx - 1])
            prev_sh["t1"] = sh["t0"] + diss
            prev_fr = render_single_shot_frame(prev_sh, t)
            fr = Image.blend(prev_fr, fr, ease_io(u / diss))
    return fr


def render_part(shots: list[dict], total_dur: float, part_idx: int, num_parts: int, out_path: Path) -> None:
    total_frames = int(round(total_dur * FPS))
    f0 = total_frames * part_idx // num_parts
    f1 = total_frames * (part_idx + 1) // num_parts
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an",
        "-vf", "format=yuv420p,noise=c0s=4:c1s=2:c2s=2:allf=t",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high",
        "-g", str(FPS * 2), "-movflags", "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    t_start = time.time()
    for fi in range(f0, f1):
        img = frame_at(shots, fi / FPS)
        proc.stdin.write(img.tobytes())
        if (fi - f0 + 1) % 600 == 0 or fi == f1 - 1:
            done = fi - f0 + 1
            el = max(1e-3, time.time() - t_start)
            print(f"[part {part_idx+1}/{num_parts}] {done}/{f1-f0} frames ({done/el:.1f} fps)", flush=True)
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg part {part_idx} exited with {rc}")


def build_videos() -> dict:
    export_manifests()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    make_specimen(OUT_DIR / "specimen_post_rossiya_grades.jpg")

    shots = get_main_shots()
    total_dur = shots[-1]["t1"]

    # Render full 2:38 master in 2 parallel worker processes
    p0 = TMP_DIR / "master_part0.mp4"
    p1 = TMP_DIR / "master_part1.mp4"
    w0 = subprocess.Popen([sys.executable, __file__, "--worker", "0", "2", str(p0)])
    w1 = subprocess.Popen([sys.executable, __file__, "--worker", "1", "2", str(p1)])
    if w0.wait() != 0 or w1.wait() != 0:
        raise RuntimeError("Parallel render worker failed")

    concat_txt = TMP_DIR / "concat_master.txt"
    concat_txt.write_text(f"file '{p0}'\nfile '{p1}'\n", encoding="utf-8")
    master_out = OUT_DIR / "post_rossiya_master_1080p.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c:v", "copy", "-an", "-movflags", "+faststart", str(master_out),
    ], check=True)

    # Also slice the ready consecutive AI-generated prefix into its own clean clip
    ready_prefix = []
    for s in shots:
        if s["generated"]:
            ready_prefix.append(s)
        else:
            break
    ready_out = OUT_DIR / "post_rossiya_ready_1080p.mp4"
    if ready_prefix:
        ready_dur = ready_prefix[-1]["t1"]
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(master_out), "-t", f"{ready_dur:.3f}",
            "-c:v", "copy", "-an", "-movflags", "+faststart", str(ready_out),
        ], check=True)

    # Render any generated B-roll cutaways into individual 4.5s clips
    broll_done = 0
    for b in get_broll_shots():
        if b["generated"]:
            b_clip = OUT_DIR / f"{b['id']}_1080p.mp4"
            fake_shot = [{
                "num": 900 + b["num"],
                "id": b["id"],
                "file": b["file"],
                "generated": True,
                "t0": 0.0,
                "t1": b["duration"],
                "act": "B-ROLL",
                "color_state": b["color_state"],
                "move": b["move"],
                "focus": [0.5, 0.5],
                "live_fx": None,
                "fallback_source": b["file"],
                "fallback_crop": [0.5, 0.5, 1.05],
            }]
            render_part(fake_shot, b["duration"], 0, 1, b_clip)
            broll_done += 1

    timeline_summary = {
        "master_video": str(master_out.relative_to(REPO_ROOT)),
        "master_size_mb": round(master_out.stat().st_size / 1e6, 2),
        "ready_prefix_video": str(ready_out.relative_to(REPO_ROOT)) if ready_prefix else None,
        "ready_prefix_seconds": ready_prefix[-1]["t1"] if ready_prefix else 0.0,
        "ready_prefix_shots": len(ready_prefix),
        "main_generated": sum(1 for s in shots if s["generated"]),
        "main_total": len(shots),
        "broll_generated": broll_done,
        "broll_total": 12,
    }
    (OUT_DIR / "build_status.json").write_text(json.dumps(timeline_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(timeline_summary, ensure_ascii=False, indent=2))
    return timeline_summary


def render_time_window(shots: list[dict], t_start_sec: float, t_end_sec: float, out_path: Path) -> None:
    """Render an arbitrary [t_start_sec, t_end_sec) window at 1080p30 for fast incremental turn updates."""
    f0 = int(round(t_start_sec * FPS))
    f1 = int(round(t_end_sec * FPS))
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an",
        "-vf", "format=yuv420p,noise=c0s=4:c1s=2:c2s=2:allf=t",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high",
        "-g", str(FPS * 2), "-movflags", "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    st = time.time()
    for fi in range(f0, f1):
        proc.stdin.write(frame_at(shots, fi / FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("Window render failed")
    print(f"Rendered window {t_start_sec:.1f}s..{t_end_sec:.1f}s ({f1-f0} frames) in {time.time()-st:.1f}s", flush=True)


def splice_window(t_a: float, t_b: float) -> dict:
    """Fast incremental update: re-render [t_a, t_b) in 2 parallel halves and splice into HQ & workspace masters."""
    export_manifests()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    shots = get_main_shots()
    total_dur = shots[-1]["t1"]
    hq_path = TMP_DIR / "post_rossiya_hq_1080p.mp4"
    if not hq_path.exists():
        return build_videos()

    # Snap window to 2-second GOP boundaries for clean stream-copy splicing
    gop_s = 2.0
    t0 = max(0.0, math.floor(t_a / gop_s) * gop_s)
    t1 = min(total_dur, math.ceil(t_b / gop_s) * gop_s)
    mid = round(((t0 + t1) / 2.0) * FPS) / FPS

    w_a = TMP_DIR / "win_a.mp4"
    w_b = TMP_DIR / "win_b.mp4"
    p_a = subprocess.Popen([sys.executable, __file__, "--window-worker", str(t0), str(mid), str(w_a)])
    p_b = subprocess.Popen([sys.executable, __file__, "--window-worker", str(mid), str(t1), str(w_b)])
    if p_a.wait() != 0 or p_b.wait() != 0:
        raise RuntimeError("Parallel window worker failed")

    parts = []
    if t0 > 0.05:
        head = TMP_DIR / "splice_head.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(hq_path), "-t", f"{t0:.3f}", "-c:v", "copy", "-an", str(head)
        ], check=True)
        parts.append(head)
    parts.extend([w_a, w_b])
    if t1 < total_dur - 0.05:
        tail = TMP_DIR / "splice_tail.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{t1:.3f}", "-i", str(hq_path), "-c:v", "copy", "-an", str(tail)
        ], check=True)
        parts.append(tail)

    concat_f = TMP_DIR / "splice_concat.txt"
    concat_f.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    hq_new = TMP_DIR / "post_rossiya_hq_new.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_f),
        "-c:v", "copy", "-an", "-movflags", "+faststart", str(hq_new)
    ], check=True)
    hq_new.replace(hq_path)

    master_out = OUT_DIR / "post_rossiya_master_1080p.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(hq_path),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-maxrate", "2100k", "-bufsize", "4200k", "-pix_fmt", "yuv420p",
        "-an", "-movflags", "+faststart", str(master_out)
    ], check=True)

    ready_prefix = []
    for s in shots:
        if s["generated"]:
            ready_prefix.append(s)
        else:
            break
    ready_out = OUT_DIR / "post_rossiya_ready_1080p.mp4"
    if ready_prefix:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(hq_path), "-t", f"{ready_prefix[-1]['t1']:.3f}",
            "-c:v", "copy", "-an", "-movflags", "+faststart", str(ready_out)
        ], check=True)

    summary = {
        "master_video": str(master_out.relative_to(REPO_ROOT)),
        "master_size_mb": round(master_out.stat().st_size / 1e6, 2),
        "ready_prefix_video": str(ready_out.relative_to(REPO_ROOT)) if ready_prefix else None,
        "ready_prefix_seconds": ready_prefix[-1]["t1"] if ready_prefix else 0.0,
        "ready_prefix_shots": len(ready_prefix),
        "main_generated": sum(1 for s in shots if s["generated"]),
        "main_total": len(shots),
        "broll_generated": sum(1 for b in get_broll_shots() if b["generated"]),
        "broll_total": 12,
    }
    (OUT_DIR / "build_status.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=3, metavar=("IDX", "NPARTS", "OUT"))
    ap.add_argument("--window-worker", nargs=3, metavar=("T0", "T1", "OUT"))
    ap.add_argument("--splice", nargs=2, type=float, metavar=("T0", "T1"))
    args = ap.parse_args()
    if args.worker:
        idx, nparts, out_p = int(args.worker[0]), int(args.worker[1]), Path(args.worker[2])
        shots = get_main_shots()
        render_part(shots, shots[-1]["t1"], idx, nparts, out_p)
        return
    if args.window_worker:
        t0, t1, out_p = float(args.window_worker[0]), float(args.window_worker[1]), Path(args.window_worker[2])
        render_time_window(get_main_shots(), t0, t1, out_p)
        return
    if args.splice:
        splice_window(args.splice[0], args.splice[1])
        return
    build_videos()


if __name__ == "__main__":
    main()
