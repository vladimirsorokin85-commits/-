#!/usr/bin/env python3
"""
Horde 'Po Polyam' FULL CAMPAIGN Animated VFX Movie (18 Chained Frames: Batch 2 + Batch 3)
6 Seamless Chapters (32.24s @ 1920x1080 30fps, 134 BPM):
  Ch.1 (00.0–05.4s): UAZ Buhanka 4-frame mud charge & lens flyby (s01->s02->s03->s04)
  Ch.2 (05.4–10.7s): Geran Ural booster launch, 7-drone dive & Citadel spire blast (s05->s06->s07)
  Ch.3 (10.7–16.1s): TOS-1A Solntsepek 3-frame thermobaric ripple salvo (s10->s11->s12)
  Ch.4 (16.1–21.5s): T-90 Tsar-Mangal + Armored Mordor Bear + Ka-52 charge & 125mm blast (s08->s09)
  Ch.5 (21.5–26.9s): Ural Sidecar w/ Red Carpet, Ushanka Orc & Nazgul palace drift & flyby (s13->s14->s15)
  Ch.6 (26.9–32.2s): Horde Banner + Animated Samovar/Boot/Pickles/Garmon/Balalaika/Roaring Bear Feast (s17->s18<->s19)
"""
import math
import subprocess
import time
import wave
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent
B1_DIR = ROOT / "frames"
B2_DIR = ROOT / "batch2_frames"
B3_DIR = ROOT / "batch3_frames"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1920, 1080, 30
HW, HH = W // 2, H // 2
BPM = 134.0
BEAT = 60.0 / BPM  # 0.447761s


def load_img(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    sr, dr = im.width / im.height, W / H
    if sr > dr:
        nw = int(im.height * dr)
        im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
    else:
        nh = int(im.width / dr)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
    return np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.uint8)


def compute_dis_flow(img_a: np.ndarray, img_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ga = cv2.cvtColor(cv2.resize(img_a, (HW, HH)), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(cv2.resize(img_b, (HW, HH)), cv2.COLOR_RGB2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    fab = cv2.GaussianBlur(dis.calc(ga, gb, None), (0, 0), 3.0) * 2.0
    fba = cv2.GaussianBlur(dis.calc(gb, ga, None), (0, 0), 3.0) * 2.0
    return (
        cv2.resize(fab, (W, H), interpolation=cv2.INTER_LINEAR),
        cv2.resize(fba, (W, H), interpolation=cv2.INTER_LINEAR),
    )


GRID_X, GRID_Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))


def warp_blend_u8(img_a: np.ndarray, img_b: np.ndarray, fab: np.ndarray, fba: np.ndarray, alpha: float, clamp_px: float = 40.0) -> np.ndarray:
    ca = np.clip(fab, -clamp_px, clamp_px)
    cb = np.clip(fba, -clamp_px, clamp_px)
    wa = cv2.remap(img_a, GRID_X - alpha * ca[..., 0], GRID_Y - alpha * ca[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    wb = cv2.remap(img_b, GRID_X - (1.0 - alpha) * cb[..., 0], GRID_Y - (1.0 - alpha) * cb[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    return cv2.addWeighted(wa, 1.0 - alpha, wb, alpha, 0.0)


class FastVFX:
    """High-speed half-res atmospheric solver + full-1080p sharp base composite."""

    def __init__(self, seed: int = 2026):
        self.rng = np.random.default_rng(seed)
        sh, sw = 270, 960
        smoke = np.zeros((sh, sw), dtype=np.float32)
        for sig, wt in [(36, 0.50), (16, 0.30), (7, 0.20)]:
            n = self.rng.standard_normal((sh, sw)).astype(np.float32)
            pad = sig * 3
            f = gaussian_filter(np.pad(n, ((0, 0), (pad, pad)), mode="wrap"), sigma=sig)[:, pad:-pad]
            f = (f - f.min()) / (f.max() - f.min() + 1e-6)
            smoke += wt * f
        self.smoke_tex = np.clip((smoke - 0.38) * 1.65, 0.0, 1.0)
        self.vert_mask = np.linspace(0.20, 0.95, HH, dtype=np.float32)[:, None]

        # Diagonal rain motion kernel (at 960x540)
        kl = 19
        self.rain_kern = np.zeros((kl, kl), dtype=np.float32)
        for i in range(kl):
            cx = int(round((kl - 1) * 0.65 - i * 0.27))
            if 0 <= cx < kl:
                self.rain_kern[i, cx] = 1.0 / kl

        # Embers at half-res (960x540)
        self.ne = 160
        self.ex = self.rng.uniform(0, HW, self.ne)
        self.ey = self.rng.uniform(0, HH, self.ne)
        self.evx = self.rng.uniform(-45, 75, self.ne)
        self.evy = self.rng.uniform(-175, -55, self.ne)
        self.ebr = self.rng.uniform(0.5, 1.0, self.ne)

        # Mud clots at half-res
        self.nd = 110
        self.dx = self.rng.uniform(0, HW, self.nd)
        self.dy = self.rng.uniform(HH * 0.45, HH, self.nd)
        self.dvx = self.rng.uniform(-140, 140, self.nd)
        self.dvy = self.rng.uniform(-85, 50, self.nd)
        self.drad = self.rng.uniform(1.5, 4.5, self.nd)

    def render_frame(
        self,
        base_u8: np.ndarray,
        f_idx: int,
        zoom: float,
        pan_x: float,
        pan_y: float,
        shake: float,
        rain_i: float,
        smoke_i: float,
        mud_i: float,
        fire_i: float,
        warm_smoke: float = 0.0,
        flash: float = 0.0,
    ) -> np.ndarray:
        dt = 1.0 / FPS
        sx = math.sin(f_idx * 1.9) * shake + math.cos(f_idx * 3.7) * (shake * 0.6)
        sy = math.cos(f_idx * 2.3) * shake + math.sin(f_idx * 4.3) * (shake * 0.5)
        cw, ch = W / zoom, H / zoom
        x0 = float(np.clip(W * 0.5 + pan_x + sx - cw * 0.5, 0, W - cw))
        y0 = float(np.clip(H * 0.5 + pan_y + sy - ch * 0.5, 0, H - ch))
        cropped = np.asarray(
            Image.fromarray(base_u8).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)),
            dtype=np.uint8,
        )

        # Build half-res (960x540) atmospheric alpha + additive light buffers
        add_h = np.zeros((HH, HW, 3), dtype=np.float32)
        att_h = np.ones((HH, HW, 3), dtype=np.float32)

        if smoke_i > 0.01:
            s1 = (f_idx * 3) % self.smoke_tex.shape[1]
            s2 = (f_idx * 5 + 220) % self.smoke_tex.shape[1]
            sm = 0.58 * np.roll(self.smoke_tex, s1, axis=1) + 0.42 * np.roll(self.smoke_tex, -s2, axis=1)
            sm_hh = cv2.resize(sm, (HW, HH), interpolation=cv2.INTER_LINEAR)
            al = np.clip(sm_hh * self.vert_mask * smoke_i * 0.46, 0.0, 0.52)[..., None]
            scol = (1.0 - warm_smoke) * np.array([64.0, 66.0, 68.0], dtype=np.float32) + warm_smoke * np.array([120.0, 76.0, 46.0], dtype=np.float32)
            att_h *= (1.0 - al)
            add_h += scol * al

        if mud_i > 0.01:
            self.dx = (self.dx + self.dvx * dt * (0.6 + mud_i)) % HW
            self.dy = self.dy + self.dvy * dt * (0.6 + mud_i)
            rst = (self.dy < HH * 0.25) | (self.dy >= HH)
            if np.any(rst):
                self.dy[rst] = self.rng.uniform(HH * 0.58, HH * 0.98, int(rst.sum()))
                self.dx[rst] = self.rng.uniform(HW * 0.12, HW * 0.88, int(rst.sum()))
            mud_mask = np.zeros((HH, HW), dtype=np.uint8)
            cnt = int(self.nd * min(1.0, mud_i))
            for i in range(cnt):
                cv2.ellipse(mud_mask, (int(self.dx[i]), int(self.dy[i])), (max(2, int(self.drad[i] * 2)), max(1, int(self.drad[i]))), -18, 0, 360, 200, -1)
            mal = (cv2.GaussianBlur(mud_mask, (5, 5), 1.0).astype(np.float32) / 255.0 * 0.62 * mud_i)[..., None]
            att_h *= (1.0 - mal)
            add_h += np.array([66.0, 50.0, 36.0], dtype=np.float32) * mal

        if fire_i > 0.01:
            curl = np.sin(f_idx * 0.21 + np.arange(self.ne) * 0.7) * 48.0
            self.ex = (self.ex + (self.evx + curl) * dt * (0.6 + fire_i)) % HW
            self.ey = self.ey + self.evy * dt * (0.6 + fire_i)
            dead = self.ey < -10
            if np.any(dead):
                self.ey[dead] = self.rng.uniform(HH * 0.52, HH + 8, int(dead.sum()))
                self.ex[dead] = self.rng.uniform(0, HW, int(dead.sum()))
            tmp = np.zeros((HH, HW, 3), dtype=np.uint8)
            ndraw = int(self.ne * min(1.0, fire_i))
            for i in range(ndraw):
                x_a, y_a = int(self.ex[i]), int(self.ey[i])
                x_b, y_b = int(x_a - self.evx[i] * 0.035), int(y_a - self.evy[i] * 0.035)
                b = self.ebr[i]
                cv2.line(tmp, (x_a, y_a), (x_b, y_b), (255, int(145 + 95 * b), int(40 + 70 * b)), 1, cv2.LINE_AA)
            glow = cv2.GaussianBlur(tmp.astype(np.float32), (9, 9), 2.5)
            flick = 0.86 + 0.14 * math.sin(f_idx * 1.7) * math.cos(f_idx * 2.9)
            add_h += (tmp.astype(np.float32) + glow * 1.45) * (0.88 * fire_i * flick)

        if rain_i > 0.01:
            sf = (self.rng.random((HH // 2, HW // 2), dtype=np.float32) > (1.0 - 0.0032 * rain_i)).astype(np.float32) * 255.0
            sn = (self.rng.random((HH, HW), dtype=np.float32) > (1.0 - 0.0012 * rain_i)).astype(np.float32) * 255.0
            rf = cv2.resize(cv2.filter2D(sf, -1, self.rain_kern), (HW, HH), interpolation=cv2.INTER_LINEAR)
            rn = cv2.filter2D(sn, -1, self.rain_kern)
            r_tot = np.clip((rf * 0.55 + rn * 1.15) / 34.0, 0.0, 1.0)[..., None]
            add_h += r_tot * np.array([202.0, 214.0, 226.0], dtype=np.float32) * (0.46 * rain_i)

        if flash > 0.005:
            att_h *= (1.0 + 0.75 * flash)
            add_h += np.array([255.0, 195.0, 125.0], dtype=np.float32) * (0.36 * flash)

        # Add 35mm halide film grain directly into add_h at 960x540 (2x2 grain clumps at 1080p!)
        add_h += self.rng.standard_normal((HH, HW, 1)).astype(np.float32) * 5.0

        att_full = cv2.resize(att_h, (W, H), interpolation=cv2.INTER_LINEAR)
        add_full = cv2.resize(add_h, (W, H), interpolation=cv2.INTER_LINEAR)
        out = cropped.astype(np.float32) * att_full + add_full
        return np.clip(out, 0, 255).astype(np.uint8)


def synthesize_full_audio(wav_path: Path, total_dur: float, events: list[tuple[float, str]], folk_start: float):
    """Synthesize 32.24s 134 BPM Phonk + Synced Combat SFX + Finale Garmon/Balalaika Victory Hook!"""
    sr = 44100
    n = int(total_dur * sr)
    rng = np.random.default_rng(108)
    mix_l = np.zeros(n, dtype=np.float32)
    mix_r = np.zeros(n, dtype=np.float32)

    # 1. Rain bed
    w = rng.standard_normal(n).astype(np.float32)
    r_lp = np.convolve(w, np.ones(7, dtype=np.float32) / 7.0, mode="same")
    r_bed = 0.04 * r_lp + 0.025 * (w - r_lp)
    mix_l += r_bed
    mix_r += np.roll(r_bed, 31)

    # 2. 134 BPM Hard Phonk Beat + Finale Folk-Phonk Accordion/Balalaika Riff (from folk_start onward!)
    cowbell_notes = [293.66, 293.66, 349.23, 293.66, 392.00, 369.99, 293.66, 261.63]  # D minor
    # Spirited D-minor folk-dance hook ("Барыня / Калинка" interval feel) for Garmon + Balalaika in Ch.6!
    folk_melody = [
        587.33, 698.46, 880.00, 880.00, 783.99, 698.46, 659.25, 587.33,
        587.33, 698.46, 880.00, 1046.50, 880.00, 783.99, 698.46, 587.33,
    ]

    n_eighths = int(total_dur / (BEAT * 0.5))
    for b in range(n_eighths):
        t0 = b * (BEAT * 0.5)
        i0 = int(t0 * sr)
        if i0 >= n:
            break
        step = b % 8
        # Kick + 808 Sub
        if step in (0, 3, 4, 6):
            kl = min(int(0.36 * sr), n - i0)
            kt = np.arange(kl, dtype=np.float32) / sr
            f_env = 52.0 + 115.0 * np.exp(-kt * 36.0)
            ph = 2.0 * np.pi * np.cumsum(f_env) / sr
            kick = np.tanh(np.sin(ph) * 2.4) * np.exp(-kt * 7.5) * 0.46
            mix_l[i0:i0 + kl] += kick
            mix_r[i0:i0 + kl] += kick
        # Snare
        if step in (2, 6):
            sl = min(int(0.20 * sr), n - i0)
            st = np.arange(sl, dtype=np.float32) / sr
            sn = rng.standard_normal(sl).astype(np.float32) * np.exp(-st * 22.0) * 0.28 + np.sin(2 * np.pi * 195.0 * st) * np.exp(-st * 30.0) * 0.20
            mix_l[i0:i0 + sl] += sn
            mix_r[i0:i0 + sl] += sn

        if t0 < folk_start:
            # Dark Phonk Cowbell
            cl = min(int(0.18 * sr), n - i0)
            ct = np.arange(cl, dtype=np.float32) / sr
            f1 = cowbell_notes[step] * 2.0
            cb = np.tanh((np.sin(2 * np.pi * f1 * ct) + 0.7 * np.sin(2 * np.pi * f1 * 1.481 * ct)) * 2.2) * np.exp(-ct * 16.0) * 0.13
            mix_l[i0:i0 + cl] += cb * 0.9
            mix_r[i0:i0 + cl] += cb * 1.1
        else:
            # Victory Garmon Accordion (detuned dual-reed harmonics) + Plucked Balalaika!
            ml = min(int(0.24 * sr), n - i0)
            mt = np.arange(ml, dtype=np.float32) / sr
            fn = folk_melody[b % len(folk_melody)]
            # Garmon reed warmth (slightly detuned chorus reeds)
            reed = (
                np.sin(2 * np.pi * fn * mt)
                + np.sin(2 * np.pi * (fn * 1.004) * mt) * 0.8
                + 0.55 * np.sin(4 * np.pi * fn * mt)
                + 0.35 * np.sin(6 * np.pi * fn * mt)
            ) * np.exp(-mt * 4.5) * 0.11
            # Balalaika crisp 16th double-strum!
            strum_env = np.exp(-mt * 18.0) + 0.75 * np.exp(-np.maximum(0.0, mt - BEAT * 0.25) * 22.0) * (mt >= BEAT * 0.25)
            bala = (np.sin(2 * np.pi * fn * 2.0 * mt) + 0.5 * np.sin(4 * np.pi * fn * 2.0 * mt)) * strum_env * 0.09
            mix_l[i0:i0 + ml] += reed * 1.15 + bala * 0.75
            mix_r[i0:i0 + ml] += reed * 0.80 + bala * 1.20

    # 3. Synced Action SFX
    for ev_t, ev_type in events:
        i0 = max(0, int(ev_t * sr))
        if i0 >= n:
            continue
        if ev_type == "diesel_pass":
            dl = min(int(5.2 * sr), n - i0)
            dt_a = np.arange(dl, dtype=np.float32) / sr
            dop = 1.18 - 0.30 * (dt_a / 5.2)
            eng = np.tanh((np.sin(2 * np.pi * 68.0 * dop * dt_a) + 0.6 * np.sin(2 * np.pi * 136.0 * dop * dt_a)) * 2.4)
            env = np.sin(np.pi * np.clip(dt_a / 5.2, 0, 1)) * 0.20
            mix_l[i0:i0 + dl] += eng * env
            mix_r[i0:i0 + dl] += eng * env * 1.05
        elif ev_type == "pkm_burst":
            bl = min(int(0.85 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            gun = rng.standard_normal(bl).astype(np.float32) * (np.sin(2 * np.pi * 11.0 * bt) > 0.45) * 0.34
            mix_l[i0:i0 + bl] += gun
            mix_r[i0:i0 + bl] += gun
        elif ev_type == "rocket_launch":
            rl = min(int(2.2 * sr), n - i0)
            rt = np.arange(rl, dtype=np.float32) / sr
            roar = np.tanh(rng.standard_normal(rl).astype(np.float32) * 1.8) * np.exp(-rt * 1.4) * 0.40
            mix_l[i0:i0 + rl] += roar
            mix_r[i0:i0 + rl] += np.roll(roar, 45)
        elif ev_type == "solntsepek_salvo":
            # Ripple whoosh-whoosh-whoosh of multiple thermobaric rockets!
            for r_i in range(5):
                ri0 = i0 + int(r_i * 0.24 * sr)
                if ri0 >= n:
                    break
                rl = min(int(1.2 * sr), n - ri0)
                rt = np.arange(rl, dtype=np.float32) / sr
                wh = np.tanh(rng.standard_normal(rl).astype(np.float32) * 2.1) * np.exp(-rt * 2.4) * 0.36
                mix_l[ri0:ri0 + rl] += wh * (1.0 - 0.1 * r_i)
                mix_r[ri0:ri0 + rl] += np.roll(wh, 30)
        elif ev_type == "geran_moped_dive":
            gl = min(int(2.6 * sr), n - i0)
            gt = np.arange(gl, dtype=np.float32) / sr
            fm = 112.0 + 50.0 * (gt / 2.6) ** 1.4
            ph = 2.0 * np.pi * np.cumsum(fm) / sr
            buzz = (np.sin(ph) + 0.65 * np.sin(2 * ph) + 0.45 * np.sin(3 * ph)) * 0.14
            env = np.clip(gt / 0.25, 0, 1) * np.clip((2.6 - gt) / 0.12, 0, 1)
            mix_l[i0:i0 + gl] += buzz * env * 1.1
            mix_r[i0:i0 + gl] += buzz * env * 0.9
        elif ev_type == "ural_moto":
            ml = min(int(5.0 * sr), n - i0)
            mt = np.arange(ml, dtype=np.float32) / sr
            # Boxer twin-cylinder Ural motorcycle throttle rev & pass!
            f_boxer = 92.0 + 55.0 * np.sin(np.pi * np.clip(mt / 4.2, 0, 1))
            ph = 2.0 * np.pi * np.cumsum(f_boxer) / sr
            moto = np.tanh((np.sin(ph) + 0.8 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph)) * 2.2) * 0.20
            mix_l[i0:i0 + ml] += moto
            mix_r[i0:i0 + ml] += moto * 1.1
        elif ev_type == "bear_roar_and_glass":
            bl = min(int(1.8 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            # Clink of podstakannik glass + deep growling bear roar!
            clink = (np.sin(2 * np.pi * 2480.0 * bt) + 0.6 * np.sin(2 * np.pi * 3710.0 * bt)) * np.exp(-bt * 14.0) * 0.22
            growl = np.tanh((np.sin(2 * np.pi * 82.0 * bt) + 0.7 * np.sin(2 * np.pi * 121.0 * bt) + rng.standard_normal(bl) * 0.4) * 2.5) * np.exp(-bt * 1.8) * 0.26
            mix_l[i0:i0 + bl] += clink + growl
            mix_r[i0:i0 + bl] += clink + growl
        elif ev_type == "big_explosion":
            el = min(int(2.6 * sr), n - i0)
            et = np.arange(el, dtype=np.float32) / sr
            boom = np.tanh(np.sin(2 * np.pi * (42.0 * np.exp(-et * 2.2) + 24.0) * et) * 3.5) * np.exp(-et * 2.0) * 0.65
            crack = rng.standard_normal(el).astype(np.float32) * np.exp(-et * 4.2) * 0.48
            mix_l[i0:i0 + el] += boom + crack
            mix_r[i0:i0 + el] += boom + np.roll(crack, 35)

    stereo = np.tanh(np.stack([mix_l, mix_r], axis=1) * 1.35)
    stereo = (stereo / (np.max(np.abs(stereo)) + 1e-6) * 0.89 * 32767.0).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def main():
    t_start = time.time()
    frame_paths = [
        # Ch.1 Buhanka (0..3)
        B2_DIR / "s01_buhanka_f1.jpg",
        B2_DIR / "s02_buhanka_f2.jpg",
        B2_DIR / "s03_buhanka_f3.jpg",
        B2_DIR / "s04_buhanka_f4.jpg",
        # Ch.2 Gerans (4..6)
        B2_DIR / "s05_geran_f1_launch.jpg",
        B2_DIR / "s06_geran_f2_swarm.jpg",
        B2_DIR / "s07_geran_f3_strike.jpg",
        # Ch.3 Solntsepek (7..9)
        B3_DIR / "s10_solntsepek_f1_aim.jpg",
        B3_DIR / "s11_solntsepek_f2_salvo1.jpg",
        B3_DIR / "s12_solntsepek_f3_salvo_full.jpg",
        # Ch.4 Tsar-Mangal + Bear (10..11)
        B2_DIR / "s08_tank_f1_charge.jpg",
        B2_DIR / "s09_tank_f2_blast.jpg",
        # Ch.5 Ural Sidecar w/ Red Carpet (12..14)
        B3_DIR / "s13_ural_f1_enter.jpg",
        B3_DIR / "s14_ural_f2_drift.jpg",
        B3_DIR / "s15_ural_f3_flyby.jpg",
        # Ch.6 Victory Banner + Samovar/Garmon/Balalaika/Bear Feast (15..17)
        B3_DIR / "s17_victory_f1_banner.jpg",
        B3_DIR / "s18_victory_f2_samovar_feast.jpg",
        B3_DIR / "s19_victory_f3_toast_anim.jpg",
    ]
    imgs = [load_img(p) for p in frame_paths]
    print(f"Loaded {len(imgs)} 1080p keyframes in {time.time() - t_start:.1f}s", flush=True)

    # Precompute DIS optical flow between sequential same-camera frames
    chained_pairs = [
        (0, 1), (1, 2), (2, 3),     # Buhanka 4-step
        (5, 6),                     # Geran dive -> strike
        (7, 8), (8, 9),             # Solntsepek aim -> ignition -> ripple salvo
        (10, 11),                   # Tsar-Mangal charge -> 125mm blast
        (12, 13), (13, 14),         # Ural sidecar enter -> spark drift -> lens flyby
        (16, 17), (17, 16),         # Samovar/Garmon/Bear living celebration loop!
    ]
    flows = {}
    for a, b in chained_pairs:
        flows[(a, b)] = compute_dis_flow(imgs[a], imgs[b])
    print(f"DIS Optical Flow ready ({len(flows)} pairs) in {time.time() - t_start:.1f}s", flush=True)

    # 72 beats @ 134 BPM = 32.24s (12 beats = 5.373s per chapter!)
    total_dur = 72 * BEAT
    total_frames = int(round(total_dur * FPS))
    ch_dur = 12 * BEAT  # 5.373s per chapter

    sfx_events = [
        (0 * BEAT, "diesel_pass"),
        (3 * BEAT, "big_explosion"),
        (6 * BEAT + 0.1, "pkm_burst"),
        (12 * BEAT, "rocket_launch"),
        (16 * BEAT, "geran_moped_dive"),
        (20 * BEAT, "big_explosion"),
        (27 * BEAT, "rocket_launch"),
        (30 * BEAT, "solntsepek_salvo"),
        (36 * BEAT, "diesel_pass"),
        (41 * BEAT, "big_explosion"),
        (48 * BEAT, "ural_moto"),
        (52 * BEAT, "big_explosion"),
        (64 * BEAT, "bear_roar_and_glass"),
        (68 * BEAT, "bear_roar_and_glass"),
    ]
    wav_path = Path("/tmp/horde_full_campaign.wav")
    synthesize_full_audio(wav_path, total_dur, sfx_events, folk_start=60 * BEAT)

    out_mp4 = OUT_DIR / "horde_full_campaign_18frames_vfx_1080p.mp4"
    cmd = [
        "/usr/local/bin/ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-maxrate", "3800k", "-bufsize", "7600k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vfx = FastVFX(seed=2026)

    def step_seq(seq_indices: list[int], local_t: float, dur: float, br: float = 0.86) -> tuple[np.ndarray, int, float]:
        """Step cleanly across chained keyframes with crisp optical-flow shutter bridge."""
        k = len(seq_indices)
        seg = dur / k
        idx_pos = min(k - 1, int(local_t / seg))
        u = (local_t - idx_pos * seg) / seg
        ia = seq_indices[idx_pos]
        if idx_pos < k - 1 and u > br:
            ib = seq_indices[idx_pos + 1]
            if (ia, ib) in flows:
                a = (u - br) / (1.0 - br)
                return warp_blend_u8(imgs[ia], imgs[ib], *flows[(ia, ib)], a, clamp_px=38.0), idx_pos, u
        return imgs[ia], idx_pos, u

    for f in range(total_frames):
        t = f / FPS
        ch = min(5, int(t / ch_dur))
        lt = t - ch * ch_dur
        flash, warm_smoke = 0.0, 0.0

        if ch == 0:
            # Ch.1: UAZ Buhanka 4-frame mud charge
            base, sub, u = step_seq([0, 1, 2, 3], lt, ch_dur, br=0.88)
            rain_i, smoke_i, mud_i, fire_i = 0.95, 0.55 + 0.1 * sub, 0.80 + 0.07 * sub, 0.30 + (0.35 if sub == 2 else 0.0)
            if sub == 1 and u < 0.15:
                flash = (1.0 - u / 0.15) * 0.25
            zoom = 1.03 + 0.06 * u
            pan_x, pan_y = (-12 + 12 * sub) * u, 3 * math.sin(lt * 4.0)
            shake = 4.5 + 3.0 * sub
        elif ch == 1:
            # Ch.2: Gerans launch -> dive -> strike
            base, sub, u = step_seq([4, 5, 6], lt, ch_dur, br=0.86)
            if sub == 0:
                rain_i, smoke_i, mud_i, fire_i, warm_smoke = 0.85, 0.85, 0.15, 1.0, 0.55
                if u < 0.18:
                    flash = (1.0 - u / 0.18) * 0.75
                zoom, pan_x, pan_y, shake = 1.03 + 0.07 * u, 18 * u, -14 * u, 12.0 * math.exp(-u * 2.0) + 3.5
            elif sub == 1:
                rain_i, smoke_i, mud_i, fire_i = 0.90, 0.55, 0.0, 0.25
                zoom, pan_x, pan_y, shake = 1.02 + 0.08 * u, 20 * u, 15 * u, 4.5 + 4.0 * u
            else:
                rain_i, smoke_i, mud_i, fire_i, warm_smoke = 0.85, 0.95, 0.35, 1.0, 0.65
                if u < 0.22:
                    flash = (1.0 - u / 0.22) * 0.95
                zoom, pan_x, pan_y, shake = 1.08 - 0.04 * u, 0.0, -8 * u, 17.0 * math.exp(-u * 2.3) + 3.5
        elif ch == 2:
            # Ch.3: TOS-1A Solntsepek 3-frame thermobaric salvo!
            base, sub, u = step_seq([7, 8, 9], lt, ch_dur, br=0.84)
            rain_i = 0.88
            mud_i = 0.25 + 0.35 * sub
            smoke_i = 0.45 + 0.25 * sub
            fire_i = 0.15 if sub == 0 else 1.0
            warm_smoke = 0.0 if sub == 0 else 0.65
            if sub in (1, 2) and u < 0.20:
                flash = (1.0 - u / 0.20) * (0.75 if sub == 1 else 0.95)
            zoom = 1.02 + 0.05 * u + 0.02 * sub
            pan_x, pan_y = 14 * u * sub, -8 * u * sub
            shake = 3.0 if sub == 0 else (15.0 * math.exp(-u * 1.8) + 6.0)
        elif ch == 3:
            # Ch.4: T-90 Tsar-Mangal + Armored Bear charge & 125mm blast!
            base, sub, u = step_seq([10, 11], lt, ch_dur, br=0.88)
            rain_i, smoke_i, mud_i = 0.85, 0.78 + 0.18 * sub, 0.88 + 0.12 * sub
            fire_i = 0.55 if sub == 0 else 1.0
            warm_smoke = 0.20 if sub == 0 else 0.65
            if sub == 1 and u < 0.16:
                flash = (1.0 - u / 0.16) * 1.0
            zoom = 1.03 + 0.06 * u
            pan_x, pan_y = 20 * u, 3 * math.sin(lt * 6.0)
            shake = 6.5 if sub == 0 else (19.0 * math.exp(-u * 2.4) + 4.5)
        elif ch == 4:
            # Ch.5: Ural Sidecar w/ Red Carpet drift & lens flyby inside Citadel!
            base, sub, u = step_seq([12, 13, 14], lt, ch_dur, br=0.86)
            rain_i = 0.92
            smoke_i = 0.65 + 0.12 * sub
            mud_i = 0.40 + 0.30 * sub
            fire_i = 0.30 if sub == 0 else 0.95  # Massive wheel sparks!
            if sub == 1 and u < 0.16:
                flash = (1.0 - u / 0.16) * 0.45
            zoom = 1.03 + 0.07 * u
            pan_x, pan_y = -18 * u * sub, 4 * math.sin(lt * 7.0)
            shake = 5.0 + 4.0 * sub
        else:
            # Ch.6: Victory Banner (first 4 beats) -> Animated Samovar/Garmon/Balalaika/Bear Feast (8 beats back-and-forth!)
            banner_dur = 4 * BEAT
            if lt < banner_dur:
                u = lt / banner_dur
                base = imgs[15]
                rain_i, smoke_i, mud_i, fire_i, warm_smoke = 0.60, 0.70, 0.10, 0.75, 0.45
                zoom, pan_x, pan_y, shake = 1.02 + 0.06 * u, 0.0, -14 * u, 3.0
            else:
                # Living rhythmic accordion/toast/bear-roar dance synced to 134 BPM!
                ft = lt - banner_dur
                # Oscillate smoothly between s18 (16) and s19 (17) every 2 beats so accordion pumps & Witch-king toasts!
                cycle = (ft / (2.0 * BEAT)) % 2.0
                alpha = 0.5 - 0.5 * math.cos(math.pi * min(1.0, cycle)) if cycle < 1.0 else 0.5 + 0.5 * math.cos(math.pi * (cycle - 1.0))
                base = warp_blend_u8(imgs[16], imgs[17], *flows[(16, 17)], alpha, clamp_px=34.0)
                rain_i, smoke_i, mud_i, fire_i, warm_smoke = 0.40, 0.62, 0.0, 0.78, 0.35
                zoom = 1.03 + 0.03 * math.sin(ft * 2.2)
                pan_x, pan_y = 8.0 * math.sin(ft * 1.5), -4.0 * alpha
                shake = 2.5

        beat_phase = (t % BEAT) / BEAT
        beat_zoom = 1.0 + 0.008 * math.exp(-beat_phase * 7.0)
        out_rgb = vfx.render_frame(base, f, zoom * beat_zoom, pan_x, pan_y, shake, rain_i, smoke_i, mud_i, fire_i, warm_smoke, flash)
        proc.stdin.write(out_rgb.tobytes())
        if (f + 1) % 240 == 0 or (f + 1) == total_frames:
            print(f"  Rendered {f + 1}/{total_frames} frames ({time.time() - t_start:.1f}s)...", flush=True)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed ({rc}):\n{stderr_out[-1200:]}")

    # Pack Batch-3 ZIP & Master 28-Photo Pack ZIP
    b3_zip = OUT_DIR / "horde_batch3_9_frames.zip"
    with zipfile.ZipFile(b3_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(B3_DIR.glob("*.jpg")):
            zf.write(p, arcname=p.name)

    all_zip = OUT_DIR / "horde_all_28_photos_pack.zip"
    with zipfile.ZipFile(all_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for folder, prefix in [(B1_DIR, "batch1_recon"), (B2_DIR, "batch2_breakthrough"), (B3_DIR, "batch3_victory")]:
            for p in sorted(folder.glob("*.jpg")):
                zf.write(p, arcname=f"{prefix}/{p.name}")

    print(f"DONE in {time.time() - t_start:.1f}s!")
    print(f"  FULL MP4: {out_mp4} ({out_mp4.stat().st_size / 1e6:.2f} MB)")
    print(f"  B3 ZIP:   {b3_zip} ({b3_zip.stat().st_size / 1e6:.2f} MB)")
    print(f"  ALL ZIP:  {all_zip} ({all_zip.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
