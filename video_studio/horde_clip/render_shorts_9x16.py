#!/usr/bin/env python3
"""
NATIVE 9:16 VERTICAL SHORTS RENDERER (1080x1920 @ 30fps)
Track: «АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele).mp3» — Full Chorus Drop (71.15s -> 96.30s = 25.15s)

STRICT GUARANTEES:
1. 100% NATIVE VERTICAL FRAMES ONLY (`assert im.height > im.width` on every single shot) —
   ZERO cropped horizontal 16:9 images!
2. Dynamic beat-locked Hollywood trailer cuts synced to the real 160-BPM Chorus:
   - Rapid cuts + optical tungsten flashes on «Только БАМ! БАМ! БАМ! БАМ-БАМ!» (71.15s..75.05s)
   - Exact vocal sync on «антенной, по полям», «только дуракам» (2-beat close-up -> towering reveal),
     «бабки, бабки, бабки», rapid 1.00s hits on «ДРОНЫ! ПУШКИ! ТАНКИ!»,
     «Всё будет хорошо, плохое в прошлом» (campaign medal «ЗА ВЗЯТИЕ НОВОЙ ИЗЕНГАРДОВКИ»),
     and «Весна придёт — тяну к небу ладошки!» (frost-rimed Orc reaching hand up to meltwater drop).
3. Silk-smooth Steadicam / vertical Technocrane cosine camera glides — ZERO nauseating camera jitter
   or high-frequency wobble, ZERO cheap PIL text overlays.
"""
import math
import subprocess
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
SHORTS_DIR = ROOT / "shorts_9x16"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_W, OUT_H = 1080, 1920
FPS = 30


def find_master_mp3() -> Path:
    for p in sorted(REPO_ROOT.iterdir()):
        if p.is_file() and p.suffix.lower() == ".mp3" and p.stat().st_size > 5_000_000:
            return p
    raise FileNotFoundError("Master MP3 not found in repo root!")


def apply_vertical_arri_grade(rgb_u8: np.ndarray, subtle_only: bool = False) -> np.ndarray:
    """Cohesive ARRI Alexa Anamorphic winter-steel & tungsten-fire grade for 1080x1920 Shorts."""
    f = rgb_u8.astype(np.float32) / 255.0
    if not subtle_only:
        luma = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
        sat_mix = 0.88
        f = luma[..., None] * (1.0 - sat_mix) + f * sat_mix
        # Crisp S-curve punch for mobile OLED screens
        f = np.clip((f - 0.5) * 1.08 + 0.495, 0.0, 1.0)
        sh_w = np.clip(1.0 - luma * 1.85, 0.0, 1.0)
        hi_w = np.clip((luma - 0.55) * 2.0, 0.0, 1.0)
        f[..., 0] = f[..., 0] - 0.020 * sh_w + 0.024 * hi_w
        f[..., 1] = f[..., 1] - 0.005 * sh_w + 0.005 * hi_w
        f[..., 2] = f[..., 2] + 0.028 * sh_w - 0.018 * hi_w

    h, w, _ = f.shape
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r2 = xx * xx * 1.05 + yy * yy * 0.72
    vig = np.clip(1.0 - 0.20 * np.maximum(0.0, r2 - 0.28), 0.75, 1.0)[..., None]
    f = np.clip(f * vig, 0.0, 1.0)
    return (f * 255.0 + 0.5).astype(np.uint8)


def load_native_vertical_9x16(path: Path, y_bias: float = 0.5, subtle_grade: bool = False) -> np.ndarray:
    """Load ONLY native vertical images (height > width) into oversampled 1240x2204 canvas for crisp zooms."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing frame: {path}")
    im = Image.open(path).convert("RGB")
    assert im.height > im.width, (
        f"FORBIDDEN HORIZONTAL IMAGE DETECTED: {path.name} is {im.width}x{im.height}! "
        f"Only native vertical images are allowed."
    )
    cw, ch = 1242, 2208  # 1.15x supersampled 9:16 canvas for razor-sharp Steadicam push-ins
    sr, dr = im.width / im.height, cw / ch
    if sr > dr:
        nw = int(round(im.height * dr))
        x0 = (im.width - nw) // 2
        im = im.crop((x0, 0, x0 + nw, im.height))
    else:
        nh = int(round(im.width / dr))
        max_y = max(0, im.height - nh)
        y0 = int(round(max_y * np.clip(y_bias, 0.0, 1.0)))
        im = im.crop((0, y0, im.width, y0 + nh))
    resized = np.asarray(im.resize((cw, ch), Image.LANCZOS), dtype=np.uint8)
    return apply_vertical_arri_grade(resized, subtle_only=subtle_grade)


class VerticalShortsVFX:
    def __init__(self, out_w: int = OUT_W, out_h: int = OUT_H, seed: int = 2026):
        self.w = out_w
        self.h = out_h
        self.hw = out_w // 2   # 540
        self.hh = out_h // 2   # 960
        self.rng = np.random.default_rng(seed)

        sh, sw = 480, 270
        smoke = np.zeros((sh, sw), dtype=np.float32)
        for sig, wt in [(32, 0.50), (14, 0.30), (6, 0.20)]:
            n = self.rng.standard_normal((sh, sw)).astype(np.float32)
            pad = sig * 3
            f = gaussian_filter(np.pad(n, ((pad, pad), (pad, pad)), mode="wrap"), sigma=sig)[pad:-pad, pad:-pad]
            f = (f - f.min()) / (f.max() - f.min() + 1e-6)
            smoke += wt * f
        self.smoke_tex = np.clip((smoke - 0.40) * 1.60, 0.0, 1.0)
        self.vert_mask = np.linspace(0.14, 0.88, self.hh, dtype=np.float32)[:, None]

        # Rising vertical embers (optimized for tall 9:16 frame)
        self.ne = 150
        self.ex = self.rng.uniform(0, self.hw, self.ne)
        self.ey = self.rng.uniform(0, self.hh, self.ne)
        self.evx = self.rng.uniform(-35, 45, self.ne)
        self.evy = self.rng.uniform(-240, -85, self.ne)
        self.ebr = self.rng.uniform(0.5, 1.0, self.ne)

        # Falling snow / ash particles
        self.ns = 170
        self.sx_p = self.rng.uniform(0, self.hw, self.ns)
        self.sy_p = self.rng.uniform(0, self.hh, self.ns)
        self.svx = self.rng.uniform(-65, 25, self.ns)
        self.svy = self.rng.uniform(85, 210, self.ns)
        self.srad = self.rng.uniform(1.1, 2.8, self.ns)

    def render(self, base_sup: np.ndarray, f_idx: int, zoom: float, px: float, py: float,
               snow_i: float, smoke_i: float, fire_i: float,
               flash: float = 0.0, fpv_glitch: float = 0.0, fade_mul: float = 1.0) -> np.ndarray:
        """Steadicam vertical Technocrane camera: silk-smooth motion, ZERO nauseating shake."""
        dt = 1.0 / FPS
        W, H, HW, HH = self.w, self.h, self.hw, self.hh
        SW, SH = base_sup.shape[1], base_sup.shape[0]

        cw = SW / zoom
        ch = SH / zoom
        max_dx = max(0.0, (SW - cw) * 0.48)
        max_dy = max(0.0, (SH - ch) * 0.48)
        safe_px = float(np.clip(px, -max_dx, max_dx))
        safe_py = float(np.clip(py, -max_dy, max_dy))

        x0 = float(np.clip(SW * 0.5 + safe_px - cw * 0.5, 0.0, max(0.0, SW - cw)))
        y0 = float(np.clip(SH * 0.5 + safe_py - ch * 0.5, 0.0, max(0.0, SH - ch)))

        sx_scale = W / cw
        sy_scale = H / ch
        M = np.array([[sx_scale, 0.0, -x0 * sx_scale], [0.0, sy_scale, -y0 * sy_scale]], dtype=np.float32)
        cropped = cv2.warpAffine(base_sup, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        if fpv_glitch > 0.01:
            # Authentic single analog FPV scanline tear (zero full-frame shake)
            gy = int((f_idx * 37) % (H - 18))
            shift = int(math.sin(f_idx * 1.2) * 10 * fpv_glitch)
            cropped[gy:gy + 6] = np.roll(cropped[gy:gy + 6], shift, axis=1)

        add_h = np.zeros((HH, HW, 3), dtype=np.float32)
        att_h = np.ones((HH, HW, 3), dtype=np.float32)

        if smoke_i > 0.01:
            s1 = (f_idx * 2) % self.smoke_tex.shape[0]
            s2 = (f_idx * 3 + 90) % self.smoke_tex.shape[1]
            sm = np.roll(np.roll(self.smoke_tex, -s1, axis=0), s2, axis=1)
            sm_hh = cv2.resize(sm, (HW, HH), interpolation=cv2.INTER_LINEAR)
            al = np.clip(sm_hh * self.vert_mask * smoke_i * 0.28, 0.0, 0.34)[..., None]
            att_h *= (1.0 - al)
            add_h += np.array([62.0, 68.0, 76.0], dtype=np.float32) * al

        if fire_i > 0.01:
            curl = np.sin(f_idx * 0.22 + np.arange(self.ne) * 0.7) * 32.0
            self.ex = (self.ex + (self.evx + curl) * dt * (0.65 + fire_i)) % HW
            self.ey = self.ey + self.evy * dt * (0.65 + fire_i)
            dead = self.ey < -12
            if np.any(dead):
                self.ey[dead] = self.rng.uniform(HH * 0.62, HH + 10, int(dead.sum()))
                self.ex[dead] = self.rng.uniform(0, HW, int(dead.sum()))
            tmp = np.zeros((HH, HW, 3), dtype=np.uint8)
            for i in range(int(self.ne * min(1.0, fire_i))):
                xa, ya = int(self.ex[i]), int(self.ey[i])
                xb, yb = int(xa - self.evx[i] * 0.032), int(ya - self.evy[i] * 0.032)
                b = self.ebr[i]
                cv2.line(tmp, (xa, ya), (xb, yb), (255, int(142 + 95 * b), int(40 + 60 * b)), 1, cv2.LINE_AA)
            glow = cv2.GaussianBlur(tmp.astype(np.float32), (9, 9), 2.3)
            add_h += (tmp.astype(np.float32) + glow * 1.25) * (0.72 * fire_i)

        if snow_i > 0.01:
            swirl = np.sin(f_idx * 0.15 + np.arange(self.ns) * 0.5) * 28.0
            self.sx_p = (self.sx_p + (self.svx + swirl) * dt * (0.65 + 0.45 * snow_i)) % HW
            self.sy_p = (self.sy_p + self.svy * dt * (0.65 + 0.45 * snow_i)) % HH
            smask = np.zeros((HH, HW), dtype=np.uint8)
            for i in range(int(self.ns * min(1.0, snow_i))):
                cv2.circle(smask, (int(self.sx_p[i]), int(self.sy_p[i])), max(1, int(self.srad[i])), 235, -1, cv2.LINE_AA)
            s_blur = (cv2.GaussianBlur(smask, (5, 5), 1.1).astype(np.float32) / 255.0)[..., None]
            add_h += s_blur * np.array([222.0, 236.0, 252.0], dtype=np.float32) * (0.56 * snow_i)

        if flash > 0.005:
            att_h *= (1.0 + 0.65 * flash)
            add_h += np.array([255.0, 188.0, 118.0], dtype=np.float32) * (0.30 * flash)

        # Crisp 35mm cinema grain
        add_h += self.rng.standard_normal((HH, HW, 1)).astype(np.float32) * 2.6

        att_full = cv2.resize(att_h, (W, H), interpolation=cv2.INTER_LINEAR)
        add_full = cv2.resize(add_h, (W, H), interpolation=cv2.INTER_LINEAR)
        out = (cropped.astype(np.float32) * att_full + add_full) * fade_mul
        return np.clip(out, 0, 255).astype(np.uint8)


def main():
    t0_all = time.time()
    mp3_path = find_master_mp3()

    audio_start = 71.15
    audio_end = 96.30
    total_dur = round(audio_end - audio_start, 3)  # 25.150s

    # =========================================================================
    # 12 BEAT-LOCKED SHOTS USING STRICTLY 100% NATIVE VERTICAL 9:16 ASSETS
    # Zero cropped horizontal images!
    # Columns:
    #   (path, song_t0, song_t1, z0, z1, px0, px1, py0, py1, snow_i, smoke_i, fire_i, cut_flash, fpv_glitch, subtle_grade, cue)
    # =========================================================================
    raw_shots = [
        # 1. 71.15 - 72.05s (0.90s): «...по полям — Только...» -> High vertical FPV dive approach
        (SHORTS_DIR / "v_shorts_01_fpv_vertical_dive_9x16.jpg",       71.15, 72.05, 1.01, 1.10,   0,   0, -35,  20, 0.25, 0.20, 0.25, False, 0.7, False, "71.15s «Только...» — вертикальное пике FPV с высоты"),
        # 2. 72.05 - 73.18s (1.13s): «БАМ! БАМ!» -> Bass drop punch-in right into the burning gate!
        (SHORTS_DIR / "v_shorts_01_fpv_vertical_dive_9x16.jpg",       72.05, 73.18, 1.24, 1.38,   0,   0, 120, 185, 0.20, 0.35, 0.75, True,  1.0, False, "72.05s «БАМ! БАМ!» — терминальный удар в горящие врата"),
        # 3. 73.18 - 75.05s (1.87s): «БАМ! БАМ-БАМ!» -> Vertical crane tilt UP along Iskander + Balrog fire pillar
        (SHORTS_DIR / "v_shorts_02_iskander_balrog_pillar_9x16.jpg",  73.18, 75.05, 1.03, 1.11,   0,   0,  75, -75, 0.15, 0.45, 0.95, True,  0.0, False, "73.18s «БАМ! БАМ-БАМ!» — огненный столб Искандера и Балрог"),
        # 4. 75.05 - 78.05s (3.00s): «А я ищу твой сигнал антенной, по полям!» -> Warg-rider with whip antenna + S-70 drone
        (SHORTS_DIR / "v_shorts_04_warg_cavalry_charge_9x16.jpg",     75.05, 78.05, 1.02, 1.11,  22, -22,  25, -25, 0.55, 0.35, 0.35, True,  0.0, False, "75.05s «А я ищу твой сигнал антенной, по полям!»"),
        # 5. 78.05 - 81.05s (3.00s): «Всё так легко и понятно только дуракам!» (Beat 1: tight detail on bound Multicam Elves in mud)
        (SHORTS_DIR / "v_shorts_05_sauron_troll_elves_9x16.jpg",      78.05, 81.05, 1.36, 1.44, -18,  18, 315, 275, 0.35, 0.30, 0.05, False, 0.0, False, "78.05s «...только дуракам» (пленные эльфы в грязи)"),
        # 6. 81.05 - 84.05s (3.00s): «Всё так легко и понятно только дуракам!» (Beat 2: towering vertical reveal of Sauron + Cave Troll + Orthanc!)
        (SHORTS_DIR / "v_shorts_05_sauron_troll_elves_9x16.jpg",      81.05, 84.05, 1.02, 1.09,   0,   0,  35, -55, 0.35, 0.35, 0.10, True,  0.0, False, "81.05s «...только дуракам» (Саурон и Пещерный Тролль)"),
        # 7. 84.05 - 87.05s (3.00s): «У тебя бабки, бабки, бабки —» -> Falling singed $100 bills onto crushed Elven helmet under Uruk boot
        (SHORTS_DIR / "v_shorts_06_babki_falling_dollars_boot_9x16.jpg", 84.05, 87.05, 1.02, 1.11, -14, 14, -45, 55, 0.30, 0.35, 0.65, True,  0.0, False, "84.05s «У тебя бабки, бабки, бабки» — горящие доллары под берцем"),
        # 8. 87.05 - 88.05s (1.00s): «— А у меня тут ДРОНЫ...» -> Rapid cut #1: Lancet + Geran-2 vertical swarm launch!
        (SHORTS_DIR / "v_shorts_07_drony_vertical_swarm_9x16.jpg",    87.05, 88.05, 1.03, 1.12,   0,   0,  55, -55, 0.25, 0.25, 0.75, True,  0.0, False, "87.05s «ДРОНЫ!» — рой Гераней и Ланцет в вертикальном небе"),
        # 9. 88.05 - 89.05s (1.00s): «...ПУШКИ...» -> Rapid cut #2: Scarred Orc artilleryman + 20m vertical 152mm fireball!
        (SHORTS_DIR / "v_shorts_08_pushki_orc_howitzer_blast_9x16.jpg", 88.05, 89.05, 1.04, 1.13, -10,  10,  40, -45, 0.30, 0.45, 1.00, True,  0.0, False, "88.05s «ПУШКИ!» — залп 152-мм гаубицы орка-артиллериста"),
        # 10. 89.05 - 90.05s (1.00s): «...ТАНКИ!» -> Rapid cut #3: T-90M crushing white marble blocks firing upward!
        (SHORTS_DIR / "v_shorts_09_tanki_t90m_vertical_breach_9x16.jpg", 89.05, 90.05, 1.04, 1.13, -18, 18,  30, -30, 0.25, 0.50, 0.65, True,  0.0, False, "89.05s «ТАНКИ!» — прорыв Т-90М сквозь мрамор цитадели"),
        # 11. 90.05 - 93.05s (3.00s): «Всё будет хорошо, плохое в прошлом!» -> Native vertical macro medal «ЗА ВЗЯТИЕ НОВОЙ ИЗЕНГАРДОВКИ»
        (OUT_DIR    / "medal_za_vzyatie_novoy_izengardovki.jpg",      90.05, 93.05, 1.01, 1.08,   0,   0,  20, -20, 0.20, 0.12, 0.15, True,  0.0, True,  "90.05s «Всё будет хорошо, плохое в прошлом» — медаль Новой Изенгардовки"),
        # 12. 93.05 - 96.30s (3.25s): «Весна придёт — тяну к небу ладошки!» -> Orc reaching hand up tall dawn sky to meltwater drop + green sprout
        (SHORTS_DIR / "v_shorts_10_vesna_hand_to_sky_9x16.jpg",       93.05, 96.30, 1.08, 1.01,   0,   0,  35, -35, 0.18, 0.10, 0.00, False, 0.0, True,  "93.05s «Весна придёт — тяну к небу ладошки!»"),
    ]

    # Extra beat-locked optical flash accents inside multi-hit bars (72.80s & 74.30s «БАМ!»)
    extra_flash_song_times = [72.80, 74.30]

    # Preload & strictly verify native vertical geometry
    cache: dict[tuple[Path, bool], np.ndarray] = {}
    shots = []
    for s in raw_shots:
        p, st0, st1, *rest = s
        sub_g = rest[-2]
        key = (p.resolve(), sub_g)
        if key not in cache:
            cache[key] = load_native_vertical_9x16(p, y_bias=0.5, subtle_grade=sub_g)
        shots.append((cache[key], round(st0 - audio_start, 4), round(st1 - audio_start, 4), *rest))

    print(f"Verified {len(cache)} strictly native vertical assets across {len(shots)} beat-locked cuts ({total_dur:.2f}s)!", flush=True)

    out_mp4 = OUT_DIR / "azbuka_po_polyam_shorts_native_9x16_1080p.mp4"
    total_frames = int(round(total_dur * FPS))

    cmd = [
        "/usr/local/bin/ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
        "-ss", f"{audio_start:.3f}", "-t", f"{total_dur:.3f}", "-i", str(mp3_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-crf", "20",
        "-maxrate", "4800k", "-bufsize", "9600k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"afade=t=in:st=0:d=0.35,afade=t=out:st={total_dur - 1.15:.3f}:d=1.15",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vfx = VerticalShortsVFX(OUT_W, OUT_H, seed=2026)

    s_idx = 0
    for f in range(total_frames):
        t = f / FPS
        song_t = audio_start + t
        while s_idx + 1 < len(shots) and t >= shots[s_idx + 1][1]:
            s_idx += 1

        img_sup, st0, st1, z0, z1, px0, px1, py0, py1, snw, smk, fir, cfl, fpv, _sub, _cue = shots[s_idx]
        dur = max(1e-4, st1 - st0)
        u = float(np.clip((t - st0) / dur, 0.0, 1.0))

        # Silk-smooth cosine Steadicam / vertical Technocrane glide (ZERO wobble!)
        ue = 0.5 - 0.5 * math.cos(math.pi * u)
        zoom = z0 + (z1 - z0) * ue
        px = px0 + (px1 - px0) * ue
        py = py0 + (py1 - py0) * ue

        # Crisp optical tungsten flash on beat cuts + inner «БАМ!» hits
        flash = 0.0
        if cfl and (t - st0) < 0.16:
            flash = max(flash, (1.0 - (t - st0) / 0.16) * 0.72)
        for eft in extra_flash_song_times:
            dt_fl = song_t - eft
            if 0.0 <= dt_fl < 0.16:
                flash = max(flash, (1.0 - dt_fl / 0.16) * 0.68)

        # Clean cinema fade-in (0.35s) and fade-out (1.15s)
        fade = 1.0
        if t < 0.35:
            fade = min(1.0, (t / 0.35) ** 0.75)
        elif total_dur - t < 1.15:
            fade = max(0.0, (total_dur - t) / 1.15)

        rgb = vfx.render(
            img_sup, f, zoom, px, py,
            snow_i=snw, smoke_i=smk, fire_i=fir,
            flash=flash, fpv_glitch=fpv, fade_mul=fade,
        )
        proc.stdin.write(rgb.tobytes())
        if (f + 1) % 250 == 0 or (f + 1) == total_frames:
            print(f"  [1080x1920 NATIVE 9:16] {f + 1}/{total_frames} frames ({time.time() - t0_all:.1f}s)...", flush=True)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed ({rc}):\n{stderr_out[-1200:]}")

    # Pack all 10 native vertical frames into a clean downloadable ZIP
    zip_out = OUT_DIR / "azbuka_po_polyam_shorts_9x16_frames.zip"
    native_files = sorted(SHORTS_DIR.glob("v_shorts_*.jpg")) + [OUT_DIR / "medal_za_vzyatie_novoy_izengardovki.jpg"]
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, nf in enumerate(native_files, start=1):
            zf.write(nf, arcname=f"{idx:02d}_{nf.name}")

    print(f"\nDONE in {time.time() - t0_all:.1f}s!", flush=True)
    print(f"  SHORTS MP4: {out_mp4} ({out_mp4.stat().st_size / 1e6:.2f} MB)", flush=True)
    print(f"  FRAMES ZIP: {zip_out} ({zip_out.stat().st_size / 1e6:.2f} MB)", flush=True)


if __name__ == "__main__":
    main()
