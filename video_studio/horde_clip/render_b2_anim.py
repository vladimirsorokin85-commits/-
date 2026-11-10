#!/usr/bin/env python3
"""
Horde 'Po Polyam' Batch 2 — Stop-Motion + Optical-Flow Vehicle Animation & Live VFX Engine
Renders 1920x1080 @ 30fps MP4 with:
  - Chained stop-motion + DIS Optical-Flow vehicle/action interpolation (s01->s04, s05->s07, s08->s09)
  - Live 30fps multi-layer slanted rain, drifting volumetric smoke & mud-dust, rising fire sparks & shockwave camera shake
  - Synced 134 BPM dark phonk/industrial beat + rain, diesel roar, iconic Geran moped buzz, and cannon/explosion SFX
"""
import math
import subprocess
import wave
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent
FRAMES_DIR = ROOT / "batch2_frames"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1920, 1080, 30
BPM = 134.0
BEAT = 60.0 / BPM  # 0.44776s per beat (matches АЗБУКА - ПО ПОЛЯМ 134 BPM)


def load_frame(name: str) -> np.ndarray:
    """Load JPG and upscale cleanly to 1920x1080 RGB float32 [0..255]."""
    p = FRAMES_DIR / name
    im = Image.open(p).convert("RGB")
    # Crop/scale preserving aspect ratio to 1920x1080
    src_ratio = im.width / im.height
    dst_ratio = W / H
    if src_ratio > dst_ratio:
        new_w = int(im.height * dst_ratio)
        x0 = (im.width - new_w) // 2
        im = im.crop((x0, 0, x0 + new_w, im.height))
    else:
        new_h = int(im.width / dst_ratio)
        y0 = (im.height - new_h) // 2
        im = im.crop((0, y0, im.width, y0 + new_h))
    im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def compute_dis_flow(img_a: np.ndarray, img_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute forward and backward optical flow at half-res and upscale to 1080p for fast, smooth warping."""
    hw, hh = W // 2, H // 2
    ga = cv2.cvtColor(cv2.resize(img_a.astype(np.uint8), (hw, hh)), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(cv2.resize(img_b.astype(np.uint8), (hw, hh)), cv2.COLOR_RGB2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flow_ab = dis.calc(ga, gb, None)
    flow_ba = dis.calc(gb, ga, None)
    # Smooth flow slightly so background birch/fortress stays rock-solid while moving vehicles warp cleanly
    flow_ab = cv2.GaussianBlur(flow_ab, (0, 0), 3.0) * 2.0
    flow_ba = cv2.GaussianBlur(flow_ba, (0, 0), 3.0) * 2.0
    flow_ab_full = cv2.resize(flow_ab, (W, H), interpolation=cv2.INTER_LINEAR)
    flow_ba_full = cv2.resize(flow_ba, (W, H), interpolation=cv2.INTER_LINEAR)
    return flow_ab_full, flow_ba_full


GRID_X, GRID_Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))


def warp_blend(img_a: np.ndarray, img_b: np.ndarray, flow_ab: np.ndarray, flow_ba: np.ndarray, alpha: float, clamp_px: float = 48.0) -> np.ndarray:
    """Bidirectional optical-flow morph with displacement clamp to prevent tearing on extreme explosions."""
    fab = np.clip(flow_ab, -clamp_px, clamp_px)
    fba = np.clip(flow_ba, -clamp_px, clamp_px)
    wa = cv2.remap(
        img_a,
        GRID_X - alpha * fab[..., 0],
        GRID_Y - alpha * fab[..., 1],
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    wb = cv2.remap(
        img_b,
        GRID_X - (1.0 - alpha) * fba[..., 0],
        GRID_Y - (1.0 - alpha) * fba[..., 1],
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    return (1.0 - alpha) * wa + alpha * wb


class LiveVFX:
    """Real-time 30fps procedural Rain, Volumetric Smoke/Dust, Fire Embers & Camera Shake."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        # Pre-build tileable multi-octave smoke/dust texture (512x1024)
        sh, sw = 360, 1280
        smoke = np.zeros((sh, sw), dtype=np.float32)
        for sigma, weight in [(48, 0.50), (22, 0.30), (9, 0.20)]:
            n = self.rng.standard_normal((sh, sw)).astype(np.float32)
            # Make horizontally tileable via circular wrap
            pad = sigma * 3
            npad = np.pad(n, ((0, 0), (pad, pad)), mode="wrap")
            f = gaussian_filter(npad, sigma=sigma)[:, pad:-pad]
            f = (f - f.min()) / (f.max() - f.min() + 1e-6)
            smoke += weight * f
        self.smoke_tex = np.clip((smoke - 0.38) * 1.65, 0.0, 1.0)

        # Persistent fire embers state
        self.n_embers = 180
        self.ex = self.rng.uniform(0, W, self.n_embers)
        self.ey = self.rng.uniform(0, H, self.n_embers)
        self.evx = self.rng.uniform(-90, 140, self.n_embers)
        self.evy = self.rng.uniform(-340, -110, self.n_embers)
        self.esize = self.rng.uniform(1.5, 4.2, self.n_embers)
        self.ebright = self.rng.uniform(0.5, 1.0, self.n_embers)

        # Persistent mud/dust particles
        self.n_dust = 140
        self.dx = self.rng.uniform(0, W, self.n_dust)
        self.dy = self.rng.uniform(H * 0.42, H, self.n_dust)
        self.dvx = self.rng.uniform(-260, 260, self.n_dust)
        self.dvy = self.rng.uniform(-160, 90, self.n_dust)
        self.drad = self.rng.uniform(2.0, 7.5, self.n_dust)

    def apply_camera(self, img: np.ndarray, zoom: float, pan_x: float, pan_y: float, shake_amp: float, frame_idx: int) -> np.ndarray:
        sx = math.sin(frame_idx * 1.9) * shake_amp + math.cos(frame_idx * 3.7) * (shake_amp * 0.6)
        sy = math.cos(frame_idx * 2.3) * shake_amp + math.sin(frame_idx * 4.3) * (shake_amp * 0.5)
        cw = W / zoom
        ch = H / zoom
        cx = W * 0.5 + pan_x + sx
        cy = H * 0.5 + pan_y + sy
        x0 = np.clip(cx - cw * 0.5, 0, W - cw)
        y0 = np.clip(cy - ch * 0.5, 0, H - ch)
        pil_im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        out = pil_im.resize((W, H), Image.BILINEAR, box=(float(x0), float(y0), float(x0 + cw), float(y0 + ch)))
        return np.asarray(out, dtype=np.float32)

    def add_rain(self, img: np.ndarray, intensity: float) -> np.ndarray:
        if intensity <= 0.01:
            return img
        # Fast vectorized diagonal motion-blurred rain sheets (near + far)
        seeds_far = (self.rng.random((H // 2, W // 2), dtype=np.float32) > (1.0 - 0.0028 * intensity)).astype(np.float32) * 255.0
        seeds_near = (self.rng.random((H // 3, W // 3), dtype=np.float32) > (1.0 - 0.0014 * intensity)).astype(np.float32) * 255.0
        k_len = 23
        kern = np.zeros((k_len, k_len), dtype=np.float32)
        for i in range(k_len):
            cx = int(round((k_len - 1) * 0.65 - i * 0.28))
            if 0 <= cx < k_len:
                kern[i, cx] = 1.0 / k_len
        far = cv2.resize(cv2.filter2D(seeds_far, -1, kern), (W, H), interpolation=cv2.INTER_LINEAR)
        near = cv2.resize(cv2.filter2D(seeds_near, -1, kern), (W, H), interpolation=cv2.INTER_LINEAR)
        rain_f = np.clip((far * 0.55 + near * 1.15) / 36.0, 0.0, 1.0)[..., None]
        rain_col = np.array([202.0, 214.0, 226.0], dtype=np.float32)
        return img + rain_f * rain_col * (0.46 * intensity)

    def add_smoke_and_dust(self, img: np.ndarray, frame_idx: int, smoke_amt: float, mud_amt: float, warm_smoke: float = 0.0) -> np.ndarray:
        dt = 1.0 / FPS
        if smoke_amt > 0.01:
            shift1 = (frame_idx * 5) % self.smoke_tex.shape[1]
            shift2 = (frame_idx * 9 + 410) % self.smoke_tex.shape[1]
            layer1 = np.roll(self.smoke_tex, shift1, axis=1)
            layer2 = np.roll(self.smoke_tex, -shift2, axis=1)
            sm = 0.58 * layer1 + 0.42 * layer2
            sm_full = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
            # Concentrate smoke in lower 65% and horizon
            vert_mask = np.linspace(0.22, 0.95, H, dtype=np.float32)[:, None]
            alpha = np.clip(sm_full * vert_mask * smoke_amt * 0.48, 0.0, 0.55)[..., None]
            base_col = (1.0 - warm_smoke) * np.array([62.0, 64.0, 66.0], dtype=np.float32) + warm_smoke * np.array([115.0, 74.0, 48.0], dtype=np.float32)
            img = img * (1.0 - alpha) + base_col * alpha

        if mud_amt > 0.01:
            mud_layer = np.zeros((H, W, 3), dtype=np.uint8)
            self.dx = (self.dx + self.dvx * dt * (0.6 + mud_amt)) % W
            self.dy = self.dy + self.dvy * dt * (0.6 + mud_amt)
            reset = (self.dy < H * 0.25) | (self.dy >= H)
            if np.any(reset):
                self.dy[reset] = self.rng.uniform(H * 0.58, H * 0.98, int(reset.sum()))
                self.dx[reset] = self.rng.uniform(W * 0.15, W * 0.85, int(reset.sum()))
            count = int(self.n_dust * min(1.0, mud_amt))
            for i in range(count):
                x, y, r = int(self.dx[i]), int(self.dy[i]), max(1, int(self.drad[i]))
                # Flying mud clots & dirt spray
                cv2.ellipse(mud_layer, (x, y), (r * 2, r), -18, 0, 360, (44, 58, 74), -1, cv2.LINE_AA)
            mud_f = cv2.GaussianBlur(mud_layer.astype(np.float32), (5, 5), 1.2)
            m_alpha = np.clip(mud_f.max(axis=2, keepdims=True) / 80.0 * 0.65 * mud_amt, 0.0, 0.65)
            # BGR->RGB mud color (dark wet chernozem brown)
            mud_rgb = np.array([68.0, 52.0, 38.0], dtype=np.float32)
            img = img * (1.0 - m_alpha) + mud_rgb * m_alpha
        return img

    def add_fire_and_sparks(self, img: np.ndarray, frame_idx: int, fire_amt: float, flash_amt: float = 0.0) -> np.ndarray:
        dt = 1.0 / FPS
        if fire_amt > 0.01:
            spark_canvas = np.zeros((H, W, 3), dtype=np.float32)
            # Update turbulent rising embers
            curl = np.sin(frame_idx * 0.21 + np.arange(self.n_embers) * 0.7) * 95.0
            self.ex = (self.ex + (self.evx + curl) * dt * (0.6 + fire_amt)) % W
            self.ey = self.ey + self.evy * dt * (0.6 + fire_amt)
            dead = self.ey < -20
            if np.any(dead):
                self.ey[dead] = self.rng.uniform(H * 0.55, H + 15, int(dead.sum()))
                self.ex[dead] = self.rng.uniform(0, W, int(dead.sum()))
            n_draw = int(self.n_embers * min(1.0, fire_amt))
            tmp = np.zeros((H, W, 3), dtype=np.uint8)
            for i in range(n_draw):
                x0, y0 = int(self.ex[i]), int(self.ey[i])
                x1 = int(x0 - (self.evx[i] * 0.03))
                y1 = int(y0 - (self.evy[i] * 0.03))
                th = max(1, int(self.esize[i]))
                b = self.ebright[i]
                col = (int(255), int(145 + 95 * b), int(40 + 70 * b))  # RGB hot orange-yellow
                cv2.line(tmp, (x0, y0), (x1, y1), col, th, cv2.LINE_AA)
            glow = cv2.GaussianBlur(tmp.astype(np.float32), (13, 13), 4.2)
            spark_canvas = tmp.astype(np.float32) * 0.95 + glow * 1.35
            # Flickering warm horizon firelight
            flicker = 0.85 + 0.15 * math.sin(frame_idx * 1.7) * math.cos(frame_idx * 2.9)
            img = img + spark_canvas * (0.85 * fire_amt * flicker)
            # Subtle warm orange lift in shadows/lower frame
            warm_grad = np.linspace(0.05, 0.35, H, dtype=np.float32)[:, None, None]
            img = img + warm_grad * np.array([48.0, 18.0, 2.0], dtype=np.float32) * (fire_amt * 0.35 * flicker)

        if flash_amt > 0.005:
            # Explosive shockwave exposure flash + radial halation
            img = img * (1.0 + 0.85 * flash_amt) + np.array([255.0, 195.0, 125.0], dtype=np.float32) * (0.38 * flash_amt)
        return img

    def add_film_grain_and_grade(self, img: np.ndarray, frame_idx: int) -> np.ndarray:
        # Gritty 35mm Portra 800 grain (fast downsampled grain upscaled to 2x2 halide clumps)
        g = self.rng.standard_normal((H // 2, W // 2)).astype(np.float32) * 5.5
        g_full = cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
        out = img + g_full
        # Subtle vignette
        return np.clip(out, 0, 255).astype(np.uint8)


def synthesize_audio(wav_path: Path, total_dur: float, events: list[tuple[float, str]]):
    """Synthesize synced 134 BPM dark-phonk rhythm + pouring rain + diesel engine + Geran 2-stroke moped buzz + explosions."""
    sr = 44100
    n = int(total_dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(77)

    mix_l = np.zeros(n, dtype=np.float32)
    mix_r = np.zeros(n, dtype=np.float32)

    # 1. Continuous heavy rain + distant thunder rumble
    white = rng.standard_normal(n).astype(np.float32)
    # Simple moving-average bandpass for rain hiss
    rain = np.convolve(white, np.ones(7, dtype=np.float32) / 7.0, mode="same")
    rain_hi = white - rain
    rain_bed = (0.045 * rain + 0.03 * rain_hi)
    mix_l += rain_bed
    mix_r += np.roll(rain_bed, 29)

    # 2. 134 BPM Hard Phonk / War-March Beat (Kick + Distorted 808 Sub + Phonk Cowbell/Snare)
    n_beats = int(total_dur / BEAT)
    cowbell_notes = [587.33, 587.33, 698.46, 587.33, 783.99, 739.99, 587.33, 523.25]  # D minor aggressive motif
    for b in range(n_beats * 2):  # 8th notes
        t0 = b * (BEAT * 0.5)
        i0 = int(t0 * sr)
        if i0 >= n:
            break
        # Kick + 808 on beats 0, 2, 3.5, 4, 6
        step = b % 8
        if step in (0, 3, 4, 6):
            kl = min(int(0.36 * sr), n - i0)
            kt = np.arange(kl, dtype=np.float32) / sr
            freq_env = 52.0 + 115.0 * np.exp(-kt * 36.0)
            phase = 2.0 * np.pi * np.cumsum(freq_env) / sr
            kick = np.tanh(np.sin(phase) * 2.4) * np.exp(-kt * 7.5) * 0.48
            mix_l[i0:i0 + kl] += kick
            mix_r[i0:i0 + kl] += kick
        # Snare/clap on beats 2 & 6 (steps 2, 6)
        if step in (2, 6):
            sl = min(int(0.20 * sr), n - i0)
            st = np.arange(sl, dtype=np.float32) / sr
            sn = (rng.standard_normal(sl).astype(np.float32) * np.exp(-st * 22.0) * 0.30
                  + np.sin(2 * np.pi * 195.0 * st) * np.exp(-st * 30.0) * 0.22)
            mix_l[i0:i0 + sl] += sn
            mix_r[i0:i0 + sl] += sn
        # Iconic TR-808 distorted Phonk Cowbell (540Hz + 800Hz dual square-ish)
        cl = min(int(0.18 * sr), n - i0)
        ct = np.arange(cl, dtype=np.float32) / sr
        f1 = cowbell_notes[step]
        f2 = f1 * 1.481
        cb = np.tanh((np.sin(2 * np.pi * f1 * ct) + 0.7 * np.sin(2 * np.pi * f2 * ct)) * 2.2) * np.exp(-ct * 16.0) * 0.14
        mix_l[i0:i0 + cl] += cb * 0.9
        mix_r[i0:i0 + cl] += cb * 1.1

    # 3. Synced Action SFX Events!
    for ev_t, ev_type in events:
        i0 = max(0, int(ev_t * sr))
        if i0 >= n:
            continue
        if ev_type == "diesel_pass":
            dl = min(int(5.4 * sr), n - i0)
            dt_arr = np.arange(dl, dtype=np.float32) / sr
            # Roaring UAZ / V8 mud throttle + Doppler pass + water splash
            doppler = 1.18 - 0.32 * (dt_arr / 5.4)
            eng = np.tanh((np.sin(2 * np.pi * 68.0 * doppler * dt_arr) + 0.6 * np.sin(2 * np.pi * 136.0 * doppler * dt_arr)) * 2.5)
            splash = rng.standard_normal(dl).astype(np.float32) * np.exp(-((dt_arr - 1.5) ** 2) / 0.35) * 0.28
            env = np.sin(np.pi * np.clip(dt_arr / 5.4, 0, 1)) * 0.22
            mix_l[i0:i0 + dl] += eng * env + splash
            mix_r[i0:i0 + dl] += eng * env * 1.05 + splash
        elif ev_type == "pkm_burst":
            bl = min(int(0.9 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            # 10 rounds/sec PKM burst
            pulses = (np.sin(2 * np.pi * 11.0 * bt) > 0.45).astype(np.float32)
            gun = rng.standard_normal(bl).astype(np.float32) * pulses * 0.35
            mix_l[i0:i0 + bl] += gun
            mix_r[i0:i0 + bl] += gun
        elif ev_type == "rocket_launch":
            rl = min(int(2.4 * sr), n - i0)
            rt = np.arange(rl, dtype=np.float32) / sr
            roar = np.tanh(rng.standard_normal(rl).astype(np.float32) * 1.8) * np.exp(-rt * 1.3) * 0.42
            mix_l[i0:i0 + rl] += roar
            mix_r[i0:i0 + rl] += np.roll(roar, 45)
        elif ev_type == "geran_moped_dive":
            # Iconic 2-stroke "moped" propeller drone dive buzz!
            gl = min(int(2.8 * sr), n - i0)
            gt = np.arange(gl, dtype=np.float32) / sr
            f_moped = 112.0 + 48.0 * (gt / 2.8) ** 1.4  # Pitch rises as swarm dives!
            ph = 2.0 * np.pi * np.cumsum(f_moped) / sr
            # Sawtooth/buzz harmonics
            buzz = (np.sin(ph) + 0.65 * np.sin(2 * ph) + 0.45 * np.sin(3 * ph) + 0.3 * np.sin(4 * ph)) * 0.14
            env = np.clip(gt / 0.3, 0, 1) * np.clip((2.8 - gt) / 0.12, 0, 1)
            mix_l[i0:i0 + gl] += buzz * env * 1.1
            mix_r[i0:i0 + gl] += buzz * env * 0.9
        elif ev_type == "big_explosion":
            el = min(int(2.8 * sr), n - i0)
            et = np.arange(el, dtype=np.float32) / sr
            sub_boom = np.tanh(np.sin(2 * np.pi * (42.0 * np.exp(-et * 2.2) + 24.0) * et) * 3.5) * np.exp(-et * 2.0) * 0.68
            crack = rng.standard_normal(el).astype(np.float32) * np.exp(-et * 4.2) * 0.52
            mix_l[i0:i0 + el] += sub_boom + crack
            mix_r[i0:i0 + el] += sub_boom + np.roll(crack, 37)

    # Master soft-clipper & normalize to -1.2 dBFS
    stereo = np.stack([mix_l, mix_r], axis=1)
    stereo = np.tanh(stereo * 1.35)
    peak = np.max(np.abs(stereo)) + 1e-6
    stereo = (stereo / peak * 0.88 * 32767.0).astype(np.int16)

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def main():
    print("Loading 9 Batch-2 frames and computing DIS Optical Flow bridges...", flush=True)
    names = [
        "s01_buhanka_f1.jpg",
        "s02_buhanka_f2.jpg",
        "s03_buhanka_f3.jpg",
        "s04_buhanka_f4.jpg",
        "s05_geran_f1_launch.jpg",
        "s06_geran_f2_swarm.jpg",
        "s07_geran_f3_strike.jpg",
        "s08_tank_f1_charge.jpg",
        "s09_tank_f2_blast.jpg",
    ]
    imgs = [load_frame(n) for n in names]

    # Precompute DIS optical flow ONLY between sequential chained pairs of the same camera setup:
    # Sequence A: 0->1, 1->2, 2->3 (Buhanka charging through mud & past lens)
    # Sequence B: 5->6 (Geran swarm diving -> Citadel fireball)
    # Sequence C: 7->8 (T-90 Tsar-Mangal + Armored Bear charging -> 125mm cannon blast!)
    flows = {}
    for a, b in [(0, 1), (1, 2), (2, 3), (5, 6), (7, 8)]:
        flows[(a, b)] = compute_dis_flow(imgs[a], imgs[b])
        print(f"  Optical flow ready: {names[a]} -> {names[b]}", flush=True)

    # Beat-synced timeline (36 beats @ 134 BPM = 16.12s total @ 30fps = 484 frames)
    # Sequence A (0..12 beats = 0.00..5.37s): 4-step Buhanka mud charge & flyby!
    # Sequence B (12..24 beats = 5.37..10.75s): Geran Ural rocket launch -> Swarm dive -> Citadel explosion!
    # Sequence C (24..36 beats = 10.75..16.12s): T-90 Tsar-Mangal + Armored Bear charge -> 125mm Blast + replay slow-push!
    total_dur = 36 * BEAT  # 16.12 seconds
    total_frames = int(round(total_dur * FPS))

    t_buh1 = 0 * BEAT
    t_buh2 = 3 * BEAT    # 1.34s: splash into mud crater!
    t_buh3 = 6 * BEAT    # 2.69s: surging closer + PKM burst!
    t_buh4 = 9 * BEAT    # 4.03s: roaring right past camera lens!
    t_ger1 = 12 * BEAT   # 5.37s: Ural Geran booster launch!
    t_ger2 = 16 * BEAT   # 7.16s: 7 Geran swarm diving!
    t_ger3 = 20 * BEAT   # 8.96s: Citadel tower + radar obliterated!
    t_tnk1 = 24 * BEAT   # 10.75s: T-90 Tsar-Mangal + Armored Bear + Ka-52 charge!
    t_tnk2 = 29 * BEAT   # 12.99s: BOOM! 125mm main gun blast + leaping Bear!

    sfx_events = [
        (t_buh1, "diesel_pass"),
        (t_buh2, "big_explosion"),  # mud crash thud
        (t_buh3 + 0.1, "pkm_burst"),
        (t_ger1, "rocket_launch"),
        (t_ger2, "geran_moped_dive"),
        (t_ger3, "big_explosion"),
        (t_tnk1, "diesel_pass"),
        (t_tnk2, "big_explosion"),
    ]
    wav_path = Path("/tmp/horde_b2_audio.wav")
    synthesize_audio(wav_path, total_dur, sfx_events)
    print(f"Audio synthesized: {wav_path} ({total_dur:.2f}s)", flush=True)

    out_mp4 = OUT_DIR / "horde_batch2_anim_vfx_1080p.mp4"
    cmd = [
        "/usr/local/bin/ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-maxrate", "4500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vfx = LiveVFX(seed=2026)

    for f in range(total_frames):
        t = f / FPS

        # Determine active scene, optical-flow bridge, camera motion, and VFX intensities
        flash = 0.0
        warm_smoke = 0.0

        if t < t_ger1:
            # SEQUENCE A: BUHANKA 4-STEP MUD CHARGE (s01 -> s02 -> s03 -> s04)
            rain_i, smoke_i, mud_i, fire_i = 0.95, 0.55, 0.75, 0.35
            if t < t_buh2:
                u = (t - t_buh1) / (t_buh2 - t_buh1)
                if u > 0.88:
                    a = (u - 0.88) / 0.12
                    base = warp_blend(imgs[0], imgs[1], *flows[(0, 1)], a, clamp_px=38.0)
                else:
                    base = imgs[0]
                zoom = 1.03 + 0.05 * u
                pan_x, pan_y = -14 * (1 - u), -6 * u
                shake = 3.5 + 4.0 * u
            elif t < t_buh3:
                u = (t - t_buh2) / (t_buh3 - t_buh2)
                mud_i = 1.0
                if u < 0.14:
                    flash = (1.0 - u / 0.14) * 0.25
                if u > 0.88:
                    a = (u - 0.88) / 0.12
                    base = warp_blend(imgs[1], imgs[2], *flows[(1, 2)], a, clamp_px=38.0)
                else:
                    base = imgs[1]
                zoom = 1.04 + 0.06 * u
                pan_x, pan_y = 6 * u, 4 * math.sin(u * 6.0)
                shake = 9.5 * math.exp(-u * 1.5) + 4.5
            elif t < t_buh4:
                u = (t - t_buh3) / (t_buh4 - t_buh3)
                fire_i = 0.65  # PKM tracer sparks!
                mud_i = 0.95
                if u > 0.88:
                    a = (u - 0.88) / 0.12
                    base = warp_blend(imgs[2], imgs[3], *flows[(2, 3)], a, clamp_px=48.0)
                else:
                    base = imgs[2]
                zoom = 1.05 + 0.07 * u
                pan_x, pan_y = 14 * u, -4 * u
                shake = 7.5
            else:
                u = (t - t_buh4) / (t_ger1 - t_buh4)
                mud_i = 1.0
                smoke_i = 0.85
                base = imgs[3]
                zoom = 1.04 + 0.10 * u
                pan_x, pan_y = 28 * u, 6 * u
                shake = 11.0 * (1.0 - 0.4 * u)

        elif t < t_tnk1:
            # SEQUENCE B: GERAN LAUNCH -> SWARM DIVE -> CITADEL TOWER EXPLOSION
            if t < t_ger2:
                u = (t - t_ger1) / (t_ger2 - t_ger1)
                base = imgs[4]  # s05 Ural rocket launch
                rain_i, smoke_i, mud_i, fire_i = 0.85, 0.85, 0.20, 1.0
                warm_smoke = 0.55
                if u < 0.18:
                    flash = (1.0 - u / 0.18) * 0.75
                zoom = 1.03 + 0.08 * u
                pan_x, pan_y = 18 * u, -14 * u  # Follow rocket trajectory up-right!
                shake = 13.0 * math.exp(-u * 2.2) + 3.5
            elif t < t_ger3:
                u = (t - t_ger2) / (t_ger3 - t_ger2)
                rain_i, smoke_i, mud_i, fire_i = 0.90, 0.60, 0.0, 0.25
                if u > 0.72:
                    a = (u - 0.72) / 0.28
                    base = warp_blend(imgs[5], imgs[6], *flows[(5, 6)], a, clamp_px=40.0)
                else:
                    base = imgs[5]  # s06 Geran swarm
                zoom = 1.02 + 0.09 * u
                pan_x, pan_y = 20 * u, 16 * u  # Dive down-right with the swarm!
                shake = 4.0 + 5.0 * u
            else:
                u = (t - t_ger3) / (t_tnk1 - t_ger3)
                base = imgs[6]  # s07 Citadel explosion!
                rain_i, smoke_i, mud_i, fire_i = 0.85, 0.95, 0.35, 1.0
                warm_smoke = 0.65
                if u < 0.22:
                    flash = (1.0 - u / 0.22) * 0.95
                zoom = 1.08 - 0.04 * u  # Shockwave punch-out!
                pan_x, pan_y = 0.0, -8 * u
                shake = 18.0 * math.exp(-u * 2.4) + 3.5

        else:
            # SEQUENCE C: T-90 TSAR-MANGAL + ARMORED BEAR CHARGE -> 125MM BLAST!
            if t < t_tnk2:
                u = (t - t_tnk1) / (t_tnk2 - t_tnk1)
                rain_i, smoke_i, mud_i, fire_i = 0.85, 0.75, 0.85, 0.55
                if u > 0.68:
                    a = (u - 0.68) / 0.32
                    base = warp_blend(imgs[7], imgs[8], *flows[(7, 8)], a, clamp_px=46.0)
                else:
                    base = imgs[7]
                zoom = 1.03 + 0.07 * u
                pan_x, pan_y = 22 * u, 3 * math.sin(u * 8.0)  # Track right with charging tank & bear!
                shake = 6.0 + 4.0 * u
            else:
                u = (t - t_tnk2) / (total_dur - t_tnk2)
                base = imgs[8]  # s09 125mm fireball + leaping armored bear!
                rain_i, smoke_i, mud_i, fire_i = 0.85, 0.95, 1.0, 1.0
                warm_smoke = 0.60
                if u < 0.16:
                    flash = (1.0 - u / 0.16) * 1.0
                zoom = 1.09 - 0.03 * min(1.0, u * 2.0) + 0.04 * u
                pan_x, pan_y = 12 * u, -4 * u
                shake = 20.0 * math.exp(-u * 2.6) + 4.0

        # Beat pulse micro-kick on every 134 BPM quarter note
        beat_phase = (t % BEAT) / BEAT
        beat_zoom = 1.0 + 0.008 * math.exp(-beat_phase * 7.0)

        frame = vfx.apply_camera(base, zoom * beat_zoom, pan_x, pan_y, shake, f)
        frame = vfx.add_smoke_and_dust(frame, f, smoke_i, mud_i, warm_smoke=warm_smoke)
        frame = vfx.add_fire_and_sparks(frame, f, fire_i, flash_amt=flash)
        frame = vfx.add_rain(frame, rain_i)
        out_rgb = vfx.add_film_grain_and_grade(frame, f)

        proc.stdin.write(out_rgb.tobytes())
        if (f + 1) % 120 == 0 or (f + 1) == total_frames:
            print(f"  Rendered {f + 1}/{total_frames} frames...", flush=True)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed ({rc}):\n{stderr_out[-1200:]}")

    # Also pack all 9 Batch-2 frames into a clean ZIP
    zip_path = OUT_DIR / "horde_batch2_stereotypes_9_frames.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for n in names:
            zf.write(FRAMES_DIR / n, arcname=n)

    print(f"SUCCESS: {out_mp4} ({out_mp4.stat().st_size / 1e6:.2f} MB)")
    print(f"ZIP:     {zip_path} ({zip_path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
