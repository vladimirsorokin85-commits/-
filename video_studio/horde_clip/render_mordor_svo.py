#!/usr/bin/env python3
"""
MORDOR BROTHERHOOD × MODERN SVO — FULL 24-SHOT CAMPAIGN MOVIE (01:04.5 @ 1920x1080 30fps, 134 BPM)
5-Act Dramatic Structure from Sauron's Command Bunker & Grond/Troll Siege to the Novaya Izengardovka Victory Parade!
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
M1_DIR = ROOT / "mordor_svo_frames"
M2_DIR = ROOT / "mordor_svo_part2"
MOD_DIR = ROOT / "modern_frames"
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


class FastCombatVFX:
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
        self.vert_mask = np.linspace(0.18, 0.94, HH, dtype=np.float32)[:, None]

        kl = 17
        self.rain_kern = np.zeros((kl, kl), dtype=np.float32)
        for i in range(kl):
            cx = int(round((kl - 1) * 0.65 - i * 0.26))
            if 0 <= cx < kl:
                self.rain_kern[i, cx] = 1.0 / kl

        self.ne = 140
        self.ex = self.rng.uniform(0, HW, self.ne)
        self.ey = self.rng.uniform(0, HH, self.ne)
        self.evx = self.rng.uniform(-40, 70, self.ne)
        self.evy = self.rng.uniform(-165, -50, self.ne)
        self.ebr = self.rng.uniform(0.5, 1.0, self.ne)

        self.nd = 100
        self.dx = self.rng.uniform(0, HW, self.nd)
        self.dy = self.rng.uniform(HH * 0.48, HH, self.nd)
        self.dvx = self.rng.uniform(-145, 145, self.nd)
        self.dvy = self.rng.uniform(-80, 45, self.nd)
        self.drad = self.rng.uniform(1.5, 4.0, self.nd)

    def render(self, base_u8: np.ndarray, f_idx: int, zoom: float, px: float, py: float, shake: float,
               rain_i: float, smoke_i: float, mud_i: float, fire_i: float, flash: float = 0.0) -> np.ndarray:
        dt = 1.0 / FPS
        sx = math.sin(f_idx * 1.9) * shake + math.cos(f_idx * 3.7) * (shake * 0.6)
        sy = math.cos(f_idx * 2.3) * shake + math.sin(f_idx * 4.3) * (shake * 0.5)
        cw, ch = W / zoom, H / zoom
        x0 = float(np.clip(W * 0.5 + px + sx - cw * 0.5, 0, W - cw))
        y0 = float(np.clip(H * 0.5 + py + sy - ch * 0.5, 0, H - ch))
        cropped = np.asarray(
            Image.fromarray(base_u8).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)),
            dtype=np.uint8,
        )

        add_h = np.zeros((HH, HW, 3), dtype=np.float32)
        att_h = np.ones((HH, HW, 3), dtype=np.float32)

        if smoke_i > 0.01:
            s1 = (f_idx * 3) % self.smoke_tex.shape[1]
            s2 = (f_idx * 5 + 220) % self.smoke_tex.shape[1]
            sm = 0.58 * np.roll(self.smoke_tex, s1, axis=1) + 0.42 * np.roll(self.smoke_tex, -s2, axis=1)
            sm_hh = cv2.resize(sm, (HW, HH), interpolation=cv2.INTER_LINEAR)
            al = np.clip(sm_hh * self.vert_mask * smoke_i * 0.40, 0.0, 0.45)[..., None]
            att_h *= (1.0 - al)
            add_h += np.array([70.0, 72.0, 75.0], dtype=np.float32) * al

        if mud_i > 0.01:
            self.dx = (self.dx + self.dvx * dt * (0.6 + mud_i)) % HW
            self.dy = self.dy + self.dvy * dt * (0.6 + mud_i)
            rst = (self.dy < HH * 0.28) | (self.dy >= HH)
            if np.any(rst):
                self.dy[rst] = self.rng.uniform(HH * 0.60, HH * 0.98, int(rst.sum()))
                self.dx[rst] = self.rng.uniform(HW * 0.12, HW * 0.88, int(rst.sum()))
            mud_mask = np.zeros((HH, HW), dtype=np.uint8)
            for i in range(int(self.nd * min(1.0, mud_i))):
                cv2.ellipse(mud_mask, (int(self.dx[i]), int(self.dy[i])), (max(2, int(self.drad[i] * 2)), max(1, int(self.drad[i]))), -18, 0, 360, 190, -1)
            mal = (cv2.GaussianBlur(mud_mask, (5, 5), 1.0).astype(np.float32) / 255.0 * 0.55 * mud_i)[..., None]
            att_h *= (1.0 - mal)
            add_h += np.array([58.0, 46.0, 34.0], dtype=np.float32) * mal

        if fire_i > 0.01:
            curl = np.sin(f_idx * 0.21 + np.arange(self.ne) * 0.7) * 45.0
            self.ex = (self.ex + (self.evx + curl) * dt * (0.6 + fire_i)) % HW
            self.ey = self.ey + self.evy * dt * (0.6 + fire_i)
            dead = self.ey < -10
            if np.any(dead):
                self.ey[dead] = self.rng.uniform(HH * 0.52, HH + 8, int(dead.sum()))
                self.ex[dead] = self.rng.uniform(0, HW, int(dead.sum()))
            tmp = np.zeros((HH, HW, 3), dtype=np.uint8)
            for i in range(int(self.ne * min(1.0, fire_i))):
                xa, ya = int(self.ex[i]), int(self.ey[i])
                xb, yb = int(xa - self.evx[i] * 0.035), int(ya - self.evy[i] * 0.035)
                b = self.ebr[i]
                cv2.line(tmp, (xa, ya), (xb, yb), (255, int(145 + 95 * b), int(40 + 70 * b)), 1, cv2.LINE_AA)
            glow = cv2.GaussianBlur(tmp.astype(np.float32), (9, 9), 2.4)
            add_h += (tmp.astype(np.float32) + glow * 1.35) * (0.80 * fire_i)

        if rain_i > 0.01:
            sf = (self.rng.random((HH // 2, HW // 2), dtype=np.float32) > (1.0 - 0.0028 * rain_i)).astype(np.float32) * 255.0
            sn = (self.rng.random((HH, HW), dtype=np.float32) > (1.0 - 0.0010 * rain_i)).astype(np.float32) * 255.0
            rf = cv2.resize(cv2.filter2D(sf, -1, self.rain_kern), (HW, HH), interpolation=cv2.INTER_LINEAR)
            rn = cv2.filter2D(sn, -1, self.rain_kern)
            r_tot = np.clip((rf * 0.50 + rn * 1.10) / 36.0, 0.0, 1.0)[..., None]
            add_h += r_tot * np.array([204.0, 214.0, 224.0], dtype=np.float32) * (0.38 * rain_i)

        if flash > 0.005:
            att_h *= (1.0 + 0.65 * flash)
            add_h += np.array([255.0, 200.0, 140.0], dtype=np.float32) * (0.30 * flash)

        add_h += self.rng.standard_normal((HH, HW, 1)).astype(np.float32) * 3.5

        att_full = cv2.resize(att_h, (W, H), interpolation=cv2.INTER_LINEAR)
        add_full = cv2.resize(add_h, (W, H), interpolation=cv2.INTER_LINEAR)
        out = cropped.astype(np.float32) * att_full + add_full
        return np.clip(out, 0, 255).astype(np.uint8)


def synthesize_audio(wav_path: Path, total_dur: float, events: list[tuple[float, str]]):
    sr = 44100
    n = int(total_dur * sr)
    rng = np.random.default_rng(404)
    mix_l = np.zeros(n, dtype=np.float32)
    mix_r = np.zeros(n, dtype=np.float32)

    w = rng.standard_normal(n).astype(np.float32)
    r_lp = np.convolve(w, np.ones(9, dtype=np.float32) / 9.0, mode="same")
    r_bed = 0.030 * r_lp + 0.016 * (w - r_lp)
    mix_l += r_bed
    mix_r += np.roll(r_bed, 29)

    riff_a = [293.66, 293.66, 349.23, 293.66, 440.00, 392.00, 349.23, 261.63]
    riff_b = [293.66, 349.23, 440.00, 523.25, 466.16, 440.00, 392.00, 349.23]
    n_eighths = int(total_dur / (BEAT * 0.5))
    for b in range(n_eighths):
        t0 = b * (BEAT * 0.5)
        i0 = int(t0 * sr)
        if i0 >= n:
            break
        step = b % 8
        bar_group = (b // 32) % 2
        riff = riff_a if bar_group == 0 else riff_b

        if step in (0, 3, 4, 6):
            kl = min(int(0.36 * sr), n - i0)
            kt = np.arange(kl, dtype=np.float32) / sr
            ph = 2.0 * np.pi * np.cumsum(50.0 + 120.0 * np.exp(-kt * 36.0)) / sr
            kick = np.tanh(np.sin(ph) * 2.5) * np.exp(-kt * 7.2) * 0.48
            mix_l[i0:i0 + kl] += kick
            mix_r[i0:i0 + kl] += kick
        if step in (2, 6):
            sl = min(int(0.20 * sr), n - i0)
            st = np.arange(sl, dtype=np.float32) / sr
            sn = rng.standard_normal(sl).astype(np.float32) * np.exp(-st * 22.0) * 0.28 + np.sin(2 * np.pi * 190.0 * st) * np.exp(-st * 30.0) * 0.20
            mix_l[i0:i0 + sl] += sn
            mix_r[i0:i0 + sl] += sn
        cl = min(int(0.20 * sr), n - i0)
        ct = np.arange(cl, dtype=np.float32) / sr
        f1 = riff[step] * 2.0
        cb = np.tanh((np.sin(2 * np.pi * f1 * ct) + 0.72 * np.sin(2 * np.pi * f1 * 1.481 * ct)) * 2.2) * np.exp(-ct * 15.0) * 0.13
        mix_l[i0:i0 + cl] += cb * 0.92
        mix_r[i0:i0 + cl] += cb * 1.08

    for ev_t, ev_type in events:
        i0 = max(0, int(ev_t * sr))
        if i0 >= n:
            continue
        if ev_type == "warg_growl":
            gl = min(int(1.6 * sr), n - i0)
            gt = np.arange(gl, dtype=np.float32) / sr
            gr = np.tanh((np.sin(2 * np.pi * 74.0 * gt) + 0.8 * np.sin(2 * np.pi * 111.0 * gt) + rng.standard_normal(gl) * 0.35) * 2.4) * np.exp(-gt * 1.9) * 0.24
            mix_l[i0:i0 + gl] += gr
            mix_r[i0:i0 + gl] += gr
        elif ev_type == "geran_buzz":
            bl = min(int(2.4 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            ph = 2.0 * np.pi * np.cumsum(115.0 + 42.0 * (bt / 2.4)) / sr
            bz = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph)) * 0.13
            mix_l[i0:i0 + bl] += bz * 1.1
            mix_r[i0:i0 + bl] += bz * 0.9
        elif ev_type == "salvo":
            for r_i in range(4):
                ri0 = i0 + int(r_i * 0.25 * sr)
                if ri0 >= n:
                    break
                rl = min(int(1.1 * sr), n - ri0)
                rt = np.arange(rl, dtype=np.float32) / sr
                wh = np.tanh(rng.standard_normal(rl).astype(np.float32) * 2.1) * np.exp(-rt * 2.5) * 0.35
                mix_l[ri0:ri0 + rl] += wh
                mix_r[ri0:ri0 + rl] += np.roll(wh, 30)
        elif ev_type == "heavy_mg":
            ml = min(int(1.1 * sr), n - i0)
            mt = np.arange(ml, dtype=np.float32) / sr
            mg = rng.standard_normal(ml).astype(np.float32) * (np.sin(2 * np.pi * 9.5 * mt) > 0.4) * 0.35
            mix_l[i0:i0 + ml] += mg
            mix_r[i0:i0 + ml] += mg
        elif ev_type == "explosion":
            el = min(int(2.5 * sr), n - i0)
            et = np.arange(el, dtype=np.float32) / sr
            bm = np.tanh(np.sin(2 * np.pi * (40.0 * np.exp(-et * 2.2) + 23.0) * et) * 3.5) * np.exp(-et * 2.0) * 0.64
            cr = rng.standard_normal(el).astype(np.float32) * np.exp(-et * 4.2) * 0.45
            mix_l[i0:i0 + el] += bm + cr
            mix_r[i0:i0 + el] += bm + np.roll(cr, 33)

    stereo = np.tanh(np.stack([mix_l, mix_r], axis=1) * 1.35)
    stereo = (stereo / (np.max(np.abs(stereo)) + 1e-6) * 0.89 * 32767.0).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def main():
    t0 = time.time()
    shots = [
        # ACT I: SAURON KSP, SARUMAN EW/PANTSIR & DRONE OPS (1..5)
        (M2_DIR / "mordor_11_sauron_command_bunker_streams.jpg",          1.02, 1.11,   0,   0,   8, -10, 2.0, 0.00, 0.20, 0.00, 0.15, None),
        (M2_DIR / "mordor_17_saruman_tactical_pantsir_air_defense.jpg",   1.02, 1.10, -14,  14,   6,  -8, 5.5, 0.55, 0.55, 0.20, 0.65, "salvo"),
        (M1_DIR / "mordor_02_goblins_fiber_fpv_lancet_team.jpg",          1.02, 1.09, -12,  16,   6,  -8, 3.0, 0.55, 0.35, 0.15, 0.05, None),
        (M1_DIR / "mordor_06_geran_swarm_goblin_techs_night.jpg",         1.03, 1.10, -10,  18,   8, -12, 7.5, 0.80, 0.70, 0.20, 0.85, "geran_buzz"),
        (M1_DIR / "mordor_05_nazgul_fell_beast_ka52_airbase.jpg",         1.02, 1.09,  16, -16,   4,  -8, 4.0, 0.60, 0.65, 0.15, 0.20, "warg_growl"),

        # ACT II: FELL BEAST + SU-34 UMPK GLIDE BOMBS & SOLNTSEPEK (6..8)
        (M2_DIR / "mordor_15_fell_beast_umpk_fab_drop.jpg",               1.03, 1.12, -18,  20,  -8,  12, 5.5, 0.45, 0.65, 0.00, 0.45, "geran_buzz"),
        (MOD_DIR / "modern_05_su34_umpk_glide_bombs_citadel.jpg",         1.07, 1.02,  -8,  14,  -6,   4, 13.0,0.55, 0.85, 0.40, 0.65, "explosion"),
        (M2_DIR / "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg",       1.03, 1.11, -14,  18,   6, -10, 11.0,0.75, 0.85, 0.55, 0.95, "salvo"),

        # ACT III: 'PO POLYAM' — URUK ENDUROS, WARG CAVALRY, BUGGIES & OLIPHAUNT (9..13)
        (MOD_DIR / "modern_01_orc_storm_squad_vkpo_moss.jpg",             1.02, 1.10, -14,  14,   4,  -6, 3.5, 0.65, 0.35, 0.35, 0.05, None),
        (M2_DIR / "mordor_14_uruk_hai_white_hand_enduro_assault.jpg",     1.03, 1.12,  18, -18,   4,  -6, 6.5, 0.70, 0.45, 0.90, 0.15, "warg_growl"),
        (M1_DIR / "mordor_01_warg_riders_desertcross_charge.jpg",         1.04, 1.12, -24,  24,   4,  -4, 6.5, 0.75, 0.55, 0.95, 0.25, "warg_growl"),
        (MOD_DIR / "modern_02_desertcross_buggy_enduro_po_polyam.jpg",    1.03, 1.11,  20, -20,   0,  -6, 6.0, 0.75, 0.50, 0.90, 0.15, None),
        (M1_DIR / "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg",          1.02, 1.10, -20,  22,   6,  -8, 5.5, 0.70, 0.60, 0.75, 0.20, "explosion"),

        # ACT IV: GROND, T-90M, CAVE TROLL, GOBLIN UGV & WARG PURSUIT (14..19)
        (M2_DIR / "mordor_12_grond_jet_battering_ram_reb.jpg",            1.02, 1.11, -16,  16,   8,  -8, 7.0, 0.65, 0.75, 0.75, 0.30, "warg_growl"),
        (MOD_DIR / "modern_06_t90m_proryv_nakidka_breach.jpg",            1.03, 1.11, -16,  18,   4,  -6, 8.0, 0.50, 0.80, 0.65, 0.45, "explosion"),
        (M1_DIR / "mordor_03_armored_cave_troll_kontakt1_breach.jpg",     1.04, 1.13,   0,   0,  12, -12, 8.5, 0.45, 0.75, 0.60, 0.50, "heavy_mg"),
        (M2_DIR / "mordor_16_goblin_sappers_ground_robot_kurier.jpg",     1.02, 1.10, -12,  14,   6,  -6, 4.0, 0.45, 0.55, 0.25, 0.25, "heavy_mg"),
        (M2_DIR / "mordor_18_warg_cavalry_pursuit_fleeing_elves.jpg",     1.03, 1.12, -20,  20,   4,  -6, 6.5, 0.65, 0.65, 0.85, 0.35, "warg_growl"),
        (M1_DIR / "mordor_07_cqb_wargs_orcs_capture_elves.jpg",           1.02, 1.09, -14,  14,   6,  -6, 3.5, 0.55, 0.45, 0.15, 0.10, None),

        # ACT V: NOVAYA IZENGARDOVKA, TRICOLOR & VICTORY PARADE (20..24)
        (M1_DIR / "mordor_08_novaya_izengardovka_warg_svo.jpg",           1.02, 1.10, -10,  10,   6,  -8, 2.5, 0.50, 0.45, 0.20, 0.10, None),
        (M2_DIR / "mordor_19_buhanka_svo_goblin_checkpoint_izengardovka.jpg", 1.02, 1.09, 14,-14,  4,  -6, 2.5, 0.50, 0.35, 0.20, 0.05, None),
        (M1_DIR / "mordor_09_tricolor_mordor_flag_bare_orcs.jpg",         1.02, 1.11,   0,   0,  10, -14, 3.0, 0.40, 0.55, 0.05, 0.35, "explosion"),
        (M2_DIR / "mordor_20_grand_parade_victory_novaya_izengardovka.jpg", 1.02, 1.11,  0,   0,  10, -10, 3.0, 0.30, 0.45, 0.10, 0.35, "warg_growl"),
        (M1_DIR / "mordor_10_throne_hall_orc_goblin_warg_pack.jpg",       1.08, 1.01,  12, -12,  -4,   4, 2.0, 0.00, 0.30, 0.00, 0.20, None),
    ]
    imgs = [load_img(s[0]) for s in shots]
    shot_dur = 6 * BEAT  # 2.6866s per shot -> 24 * 2.6866 = 64.48s!
    total_dur = len(shots) * shot_dur
    total_frames = int(round(total_dur * FPS))

    sfx_events = [(idx * shot_dur + 0.08, s[12]) for idx, s in enumerate(shots) if s[12]]
    wav_path = Path("/tmp/mordor_svo_24.wav")
    synthesize_audio(wav_path, total_dur, sfx_events)

    out_mp4 = OUT_DIR / "mordor_svo_full_24shots_1080p.mp4"
    cmd = [
        "/usr/local/bin/ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-maxrate", "2900k", "-bufsize", "5800k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vfx = FastCombatVFX(seed=999)

    for f in range(total_frames):
        t = f / FPS
        idx = min(len(shots) - 1, int(t / shot_dur))
        u = (t - idx * shot_dur) / shot_dur
        _, z0, z1, px0, px1, py0, py1, shk, rn, sm, md, fr, sfx = shots[idx]

        ue = 1.0 - (1.0 - u) ** 1.6
        zoom = z0 + (z1 - z0) * ue
        px = px0 + (px1 - px0) * ue
        py = py0 + (py1 - py0) * ue

        beat_phase = (t % BEAT) / BEAT
        beat_zoom = 1.0 + 0.008 * math.exp(-beat_phase * 7.0)
        flash = (1.0 - u / 0.14) * 0.75 if (sfx in ("explosion", "salvo", "heavy_mg") and u < 0.14) else 0.0
        cur_shk = shk * (1.8 * math.exp(-u * 3.0) + 0.55) if sfx in ("explosion", "salvo") else shk

        rgb = vfx.render(imgs[idx], f, zoom * beat_zoom, px, py, cur_shk, rn, sm, md, fr, flash=flash)
        proc.stdin.write(rgb.tobytes())
        if (f + 1) % 360 == 0 or (f + 1) == total_frames:
            print(f"  Rendered {f + 1}/{total_frames} frames ({time.time() - t0:.1f}s)...", flush=True)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed ({rc}):\n{stderr_out[-1200:]}")

    # Pack Part-2 10-frame ZIP & Complete 26-frame Master Mordor-SVO ZIP
    p2_zip = OUT_DIR / "mordor_svo_part2_10_frames.zip"
    with zipfile.ZipFile(p2_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(M2_DIR.glob("*.jpg")):
            zf.write(p, arcname=p.name)

    all26_zip = OUT_DIR / "mordor_svo_master_26_frames.zip"
    pure_mod = [
        "modern_01_orc_storm_squad_vkpo_moss.jpg",
        "modern_02_desertcross_buggy_enduro_po_polyam.jpg",
        "modern_03_lancet_and_fiber_fpv_team.jpg",
        "modern_04_geran_black_swarm_night_pickup.jpg",
        "modern_05_su34_umpk_glide_bombs_citadel.jpg",
        "modern_06_t90m_proryv_nakidka_breach.jpg",
    ]
    with zipfile.ZipFile(all26_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(M1_DIR.glob("*.jpg")):
            zf.write(p, arcname=f"part1_mordor_svo/{p.name}")
        for p in sorted(M2_DIR.glob("*.jpg")):
            zf.write(p, arcname=f"part2_sauron_grond_parade/{p.name}")
        for name in pure_mod:
            p = MOD_DIR / name
            if p.is_file():
                zf.write(p, arcname=f"part0_storm_units/{name}")

    print(f"DONE in {time.time() - t0:.1f}s!")
    print(f"  FULL 24-SHOT MP4: {out_mp4} ({out_mp4.stat().st_size / 1e6:.2f} MB)")
    print(f"  PART-2 10-ZIP:    {p2_zip} ({p2_zip.stat().st_size / 1e6:.2f} MB)")
    print(f"  MASTER 26-ZIP:    {all26_zip} ({all26_zip.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
