#!/usr/bin/env python3
"""
MORDOR BROTHERHOOD × MODERN SVO — LYRIC-SYNCED 51-UNIQUE-FRAME MASTER FILM (02:28.7 @ 1920x1080 30fps, 134 BPM)
100% Audited Clean Roster (ZERO Batch-1 NATO helmets, ZERO 90s helmets/coats, ZERO human faces, ZERO bears!)
Mapped directly to the lyrics of «АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele)»:
  - Припев 1: «Только бам, бам, бам... Ищу твой сигнал антенной по полям... У тебя бабки — у меня дроны, пушки, танки!»
  - Куплет 1: «Руки околели от холодной зимы... Вышла из луча, в мониторе нету... Я разнёс частоты твои... Антенной по полям»
  - Припев 2: «Бам, бам, бам — По полям! Дроны, пушки, танки!»
  - Куплет 2: «Этот лютый холод, минус сорок, лес, лес, лес... Где-то потерялась и нужно тебя найти!»
  - Припев 3: Разгром «бабок» эльфов, штурм Цитадели и капитуляция перед Устами Саурона
  - Финал:    «Всё будет хорошо, плохое в прошлом — Весна придёт, тяну к небу ладошки!» («НОВАЯ ИЗЕНГАРДОВКА»)
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
M3_DIR = ROOT / "mordor_svo_part3"
M4_DIR = ROOT / "mordor_svo_part4"
M5_DIR = ROOT / "mordor_svo_part5_song"
MOD_DIR = ROOT / "modern_frames"
B2_DIR = ROOT / "batch2_frames"
AUDIO_DIR = ROOT / "audio"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FPS = 30
BPM = 134.0
BEAT = 60.0 / BPM  # 0.44776119s


def load_img_wh(path: Path, tw: int, th: int, x_bias: float = 0.5) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Missing audited frame: {path}")
    im = Image.open(path).convert("RGB")
    sr, dr = im.width / im.height, tw / th
    if sr > dr:
        nw = int(im.height * dr)
        max_x = max(0, im.width - nw)
        x0 = int(round(max_x * np.clip(x_bias, 0.0, 1.0)))
        im = im.crop((x0, 0, x0 + nw, im.height))
    else:
        nh = int(im.width / dr)
        y0 = (im.height - nh) // 2
        im = im.crop((0, y0, im.width, y0 + nh))
    return np.asarray(im.resize((tw, th), Image.LANCZOS), dtype=np.uint8)


class FastCombatVFX:
    def __init__(self, out_w: int, out_h: int, seed: int = 2026):
        self.w = out_w
        self.h = out_h
        self.hw = out_w // 2
        self.hh = out_h // 2
        self.rng = np.random.default_rng(seed)

        sh, sw = 270, 640
        smoke = np.zeros((sh, sw), dtype=np.float32)
        for sig, wt in [(34, 0.50), (15, 0.30), (7, 0.20)]:
            n = self.rng.standard_normal((sh, sw)).astype(np.float32)
            pad = sig * 3
            f = gaussian_filter(np.pad(n, ((0, 0), (pad, pad)), mode="wrap"), sigma=sig)[:, pad:-pad]
            f = (f - f.min()) / (f.max() - f.min() + 1e-6)
            smoke += wt * f
        self.smoke_tex = np.clip((smoke - 0.38) * 1.65, 0.0, 1.0)
        self.vert_mask = np.linspace(0.18, 0.94, self.hh, dtype=np.float32)[:, None]

        kl = 17
        self.rain_kern = np.zeros((kl, kl), dtype=np.float32)
        for i in range(kl):
            cx = int(round((kl - 1) * 0.65 - i * 0.26))
            if 0 <= cx < kl:
                self.rain_kern[i, cx] = 1.0 / kl

        # Fire embers
        self.ne = 135
        self.ex = self.rng.uniform(0, self.hw, self.ne)
        self.ey = self.rng.uniform(0, self.hh, self.ne)
        self.evx = self.rng.uniform(-40, 70, self.ne)
        self.evy = self.rng.uniform(-165, -50, self.ne)
        self.ebr = self.rng.uniform(0.5, 1.0, self.ne)

        # Mud spray
        self.nd = 95
        self.dx = self.rng.uniform(0, self.hw, self.nd)
        self.dy = self.rng.uniform(self.hh * 0.48, self.hh, self.nd)
        self.dvx = self.rng.uniform(-145, 145, self.nd)
        self.dvy = self.rng.uniform(-80, 45, self.nd)
        self.drad = self.rng.uniform(1.5, 4.0, self.nd)

        # Winter blizzard snowflakes (for -40C snow verses!)
        self.ns = 180
        self.sx_p = self.rng.uniform(0, self.hw, self.ns)
        self.sy_p = self.rng.uniform(0, self.hh, self.ns)
        self.svx = self.rng.uniform(-95, -25, self.ns)
        self.svy = self.rng.uniform(55, 145, self.ns)
        self.srad = self.rng.uniform(1.2, 3.2, self.ns)

    def render(self, base_u8: np.ndarray, f_idx: int, zoom: float, px: float, py: float, shake: float,
               rain_i: float, smoke_i: float, mud_i: float, fire_i: float, flash: float = 0.0) -> np.ndarray:
        """Note: negative rain_i encodes winter snow intensity (-rain_i); negative mud_i encodes warm spring sun-glow!"""
        dt = 1.0 / FPS
        W, H, HW, HH = self.w, self.h, self.hw, self.hh
        sx = math.sin(f_idx * 1.9) * shake + math.cos(f_idx * 3.7) * (shake * 0.6)
        sy = math.cos(f_idx * 2.3) * shake + math.sin(f_idx * 4.3) * (shake * 0.5)
        cw, ch = W / zoom, H / zoom
        x0 = float(np.clip(W * 0.5 + px + sx - cw * 0.5, 0, max(0.0, W - cw)))
        y0 = float(np.clip(H * 0.5 + py + sy - ch * 0.5, 0, max(0.0, H - ch)))

        M = np.array([[zoom, 0.0, -x0 * zoom], [0.0, zoom, -y0 * zoom]], dtype=np.float32)
        cropped = cv2.warpAffine(base_u8, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        add_h = np.zeros((HH, HW, 3), dtype=np.float32)
        att_h = np.ones((HH, HW, 3), dtype=np.float32)

        if smoke_i > 0.01:
            s1 = (f_idx * 3) % self.smoke_tex.shape[1]
            s2 = (f_idx * 5 + 210) % self.smoke_tex.shape[1]
            sm = 0.58 * np.roll(self.smoke_tex, s1, axis=1) + 0.42 * np.roll(self.smoke_tex, -s2, axis=1)
            sm_hh = cv2.resize(sm, (HW, HH), interpolation=cv2.INTER_LINEAR)
            al = np.clip(sm_hh * self.vert_mask * smoke_i * 0.38, 0.0, 0.44)[..., None]
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
                cv2.ellipse(mud_mask, (int(self.dx[i]), int(self.dy[i])),
                            (max(2, int(self.drad[i] * 2)), max(1, int(self.drad[i]))), -18, 0, 360, 185, -1)
            mal = (cv2.GaussianBlur(mud_mask, (5, 5), 1.0).astype(np.float32) / 255.0 * 0.52 * mud_i)[..., None]
            att_h *= (1.0 - mal)
            add_h += np.array([58.0, 46.0, 34.0], dtype=np.float32) * mal
        elif mud_i < -0.01:
            # Warm golden spring sunlight bloom («Весна придёт — тяну к небу ладошки!»)
            sun_i = -mud_i
            gy = np.linspace(1.0, 0.05, HH, dtype=np.float32)[:, None]
            gx = np.linspace(0.85, 0.25, HW, dtype=np.float32)[None, :]
            beam = (gy * gx)[..., None] * sun_i * (0.88 + 0.12 * math.sin(f_idx * 0.08))
            add_h += np.array([255.0, 218.0, 135.0], dtype=np.float32) * (0.22 * beam)

        if fire_i > 0.01:
            curl = np.sin(f_idx * 0.21 + np.arange(self.ne) * 0.7) * 42.0
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
            add_h += (tmp.astype(np.float32) + glow * 1.30) * (0.78 * fire_i)

        if rain_i > 0.01:
            sf = (self.rng.random((HH // 2, HW // 2), dtype=np.float32) > (1.0 - 0.0026 * rain_i)).astype(np.float32) * 255.0
            sn = (self.rng.random((HH, HW), dtype=np.float32) > (1.0 - 0.0009 * rain_i)).astype(np.float32) * 255.0
            rf = cv2.resize(cv2.filter2D(sf, -1, self.rain_kern), (HW, HH), interpolation=cv2.INTER_LINEAR)
            rn = cv2.filter2D(sn, -1, self.rain_kern)
            r_tot = np.clip((rf * 0.50 + rn * 1.08) / 36.0, 0.0, 1.0)[..., None]
            add_h += r_tot * np.array([204.0, 214.0, 224.0], dtype=np.float32) * (0.36 * rain_i)
        elif rain_i < -0.01:
            # Swirling winter snowflakes («От холодной зимы / Минус сорок, лес, лес, лес!»)
            snow_i = -rain_i
            swirl = np.sin(f_idx * 0.14 + np.arange(self.ns) * 0.5) * 35.0
            self.sx_p = (self.sx_p + (self.svx + swirl) * dt * (0.7 + 0.5 * snow_i)) % HW
            self.sy_p = (self.sy_p + self.svy * dt * (0.7 + 0.5 * snow_i)) % HH
            smask = np.zeros((HH, HW), dtype=np.uint8)
            for i in range(int(self.ns * min(1.0, snow_i))):
                cv2.circle(smask, (int(self.sx_p[i]), int(self.sy_p[i])), max(1, int(self.srad[i])), 235, -1, cv2.LINE_AA)
            s_blur = (cv2.GaussianBlur(smask, (5, 5), 1.1).astype(np.float32) / 255.0)[..., None]
            add_h += s_blur * np.array([228.0, 238.0, 252.0], dtype=np.float32) * (0.72 * snow_i)

        if flash > 0.005:
            att_h *= (1.0 + 0.62 * flash)
            add_h += np.array([255.0, 200.0, 140.0], dtype=np.float32) * (0.28 * flash)

        add_h += self.rng.standard_normal((HH, HW, 1)).astype(np.float32) * 3.2

        att_full = cv2.resize(att_h, (W, H), interpolation=cv2.INTER_LINEAR)
        add_full = cv2.resize(add_h, (W, H), interpolation=cv2.INTER_LINEAR)
        out = cropped.astype(np.float32) * att_full + add_full
        return np.clip(out, 0, 255).astype(np.uint8)


def synthesize_audio(wav_path: Path, total_dur: float, events: list[tuple[float, str]]):
    """Lyric-structured 134 BPM Audio Score matching Chorus -> Winter Verse 1 -> Chorus 2 -> -40C Verse 2 -> Chorus 3 -> Spring Outro."""
    sr = 44100
    n = int(total_dur * sr)
    rng = np.random.default_rng(707)
    mix_l = np.zeros(n, dtype=np.float32)
    mix_r = np.zeros(n, dtype=np.float32)

    w = rng.standard_normal(n).astype(np.float32)
    r_lp = np.convolve(w, np.ones(9, dtype=np.float32) / 9.0, mode="same")
    r_bed = 0.022 * r_lp + 0.012 * (w - r_lp)
    mix_l += r_bed
    mix_r += np.roll(r_bed, 29)

    riffs = [
        [293.66, 293.66, 349.23, 293.66, 440.00, 392.00, 349.23, 261.63],  # Chorus hook («По полям!»)
        [220.00, 261.63, 293.66, 349.23, 293.66, 261.63, 220.00, 196.00],  # Winter melancholic radio-search verse
        [293.66, 349.23, 440.00, 523.25, 466.16, 440.00, 392.00, 349.23],  # Heavy attack chorus
        [349.23, 440.00, 523.25, 587.33, 523.25, 440.00, 392.00, 440.00],  # Warm Spring major/minor lift («Весна придёт!»)
    ]
    bass_roots = [73.42, 58.27, 65.41, 73.42]

    n_eighths = int(total_dur / (BEAT * 0.5))
    for b in range(n_eighths):
        t0 = b * (BEAT * 0.5)
        i0 = int(t0 * sr)
        if i0 >= n:
            break
        bar = b // 8
        step = b % 8
        # Match actual song form:
        # Bars 0..14: Chorus 1 | 15..32: Winter Verse 1 | 33..47: Chorus 2 | 48..62: -40C Verse 2 | 63..74: Chorus 3 | 75..83: Spring Finale
        is_chorus = (bar < 15) or (33 <= bar < 48) or (63 <= bar < 75)
        is_spring = bar >= 75
        riff = riffs[3] if is_spring else (riffs[0 if bar < 33 else 2] if is_chorus else riffs[1])
        b_freq = bass_roots[(bar // 2) % 4]

        if step in (0, 4):
            bl = min(int(0.42 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            sub = np.tanh(np.sin(2 * np.pi * b_freq * bt) * 2.2) * np.exp(-bt * 3.8) * (0.29 if is_chorus else 0.18)
            mix_l[i0:i0 + bl] += sub
            mix_r[i0:i0 + bl] += sub

        if bar % 4 == 0 and step == 0:
            hl = min(int(1.65 * sr), n - i0)
            ht = np.arange(hl, dtype=np.float32) / sr
            env = np.minimum(ht / 0.18, 1.0) * np.exp(-ht * 1.4)
            horn = np.tanh((np.sin(2 * np.pi * b_freq * 2.0 * ht) +
                            0.65 * np.sin(2 * np.pi * b_freq * 3.0 * ht) +
                            0.35 * np.sin(2 * np.pi * b_freq * 4.0 * ht)) * 1.8) * env * 0.16
            mix_l[i0:i0 + hl] += horn * 0.95
            mix_r[i0:i0 + hl] += horn * 1.05

        if (step in (0, 3, 4, 6) and is_chorus) or (step in (0, 4) and not is_chorus):
            kl = min(int(0.35 * sr), n - i0)
            kt = np.arange(kl, dtype=np.float32) / sr
            ph = 2.0 * np.pi * np.cumsum(50.0 + 120.0 * np.exp(-kt * 36.0)) / sr
            kick = np.tanh(np.sin(ph) * 2.5) * np.exp(-kt * 7.4) * (0.47 if is_chorus else 0.31)
            mix_l[i0:i0 + kl] += kick
            mix_r[i0:i0 + kl] += kick

        if step in (2, 6):
            sl = min(int(0.20 * sr), n - i0)
            st = np.arange(sl, dtype=np.float32) / sr
            sn = (rng.standard_normal(sl).astype(np.float32) * np.exp(-st * 22.0) * 0.25 +
                  np.sin(2 * np.pi * 190.0 * st) * np.exp(-st * 30.0) * 0.18)
            mix_l[i0:i0 + sl] += sn
            mix_r[i0:i0 + sl] += sn

        cl = min(int(0.20 * sr), n - i0)
        ct = np.arange(cl, dtype=np.float32) / sr
        f1 = riff[step] * 2.0
        cb = np.tanh((np.sin(2 * np.pi * f1 * ct) + 0.72 * np.sin(2 * np.pi * f1 * 1.481 * ct)) * 2.1) * np.exp(-ct * 14.0) * (0.135 if is_chorus else 0.085)
        mix_l[i0:i0 + cl] += cb * 0.92
        mix_r[i0:i0 + cl] += cb * 1.08

    for ev_t, ev_type in events:
        i0 = max(0, int(ev_t * sr))
        if i0 >= n:
            continue
        if ev_type == "warg_growl":
            gl = min(int(1.4 * sr), n - i0)
            gt = np.arange(gl, dtype=np.float32) / sr
            gr = np.tanh((np.sin(2 * np.pi * 74.0 * gt) + 0.8 * np.sin(2 * np.pi * 111.0 * gt) + rng.standard_normal(gl) * 0.35) * 2.4) * np.exp(-gt * 1.9) * 0.21
            mix_l[i0:i0 + gl] += gr
            mix_r[i0:i0 + gl] += gr
        elif ev_type == "radio_scan":
            # Authentic radio/antenna frequency sweep («Ищу твой сигнал / Разнёс частоты твои»)
            rl = min(int(1.8 * sr), n - i0)
            rt = np.arange(rl, dtype=np.float32) / sr
            swp = np.sin(2 * np.pi * np.cumsum(680.0 + 520.0 * np.sin(2 * np.pi * 2.2 * rt)) / sr) * np.exp(-rt * 1.5) * 0.09
            st_n = rng.standard_normal(rl).astype(np.float32) * np.exp(-rt * 2.2) * 0.08
            mix_l[i0:i0 + rl] += swp + st_n
            mix_r[i0:i0 + rl] += np.roll(swp, 18) + st_n
        elif ev_type == "geran_buzz":
            bl = min(int(2.0 * sr), n - i0)
            bt = np.arange(bl, dtype=np.float32) / sr
            ph = 2.0 * np.pi * np.cumsum(115.0 + 42.0 * (bt / 2.0)) / sr
            bz = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph)) * 0.12
            mix_l[i0:i0 + bl] += bz * 1.1
            mix_r[i0:i0 + bl] += bz * 0.9
        elif ev_type == "salvo":
            for r_i in range(4):
                ri0 = i0 + int(r_i * 0.22 * sr)
                if ri0 >= n:
                    break
                rl = min(int(0.95 * sr), n - ri0)
                rt = np.arange(rl, dtype=np.float32) / sr
                wh = np.tanh(rng.standard_normal(rl).astype(np.float32) * 2.1) * np.exp(-rt * 2.5) * 0.32
                mix_l[ri0:ri0 + rl] += wh
                mix_r[ri0:ri0 + rl] += np.roll(wh, 30)
        elif ev_type == "heavy_mg":
            ml = min(int(0.95 * sr), n - i0)
            mt = np.arange(ml, dtype=np.float32) / sr
            mg = rng.standard_normal(ml).astype(np.float32) * (np.sin(2 * np.pi * 9.5 * mt) > 0.4) * 0.31
            mix_l[i0:i0 + ml] += mg
            mix_r[i0:i0 + ml] += mg
        elif ev_type == "explosion":
            el = min(int(2.2 * sr), n - i0)
            et = np.arange(el, dtype=np.float32) / sr
            bm = np.tanh(np.sin(2 * np.pi * (40.0 * np.exp(-et * 2.2) + 23.0) * et) * 3.5) * np.exp(-et * 2.0) * 0.58
            cr = rng.standard_normal(el).astype(np.float32) * np.exp(-et * 4.2) * 0.40
            mix_l[i0:i0 + el] += bm + cr
            mix_r[i0:i0 + el] += bm + np.roll(cr, 33)

    fade_len = min(int(2.0 * sr), n)
    fade = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    mix_l[-fade_len:] *= fade
    mix_r[-fade_len:] *= fade

    stereo = np.tanh(np.stack([mix_l, mix_r], axis=1) * 1.32)
    stereo = (stereo / (np.max(np.abs(stereo)) + 1e-6) * 0.89 * 32767.0).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def render_timeline(shots: list[tuple], out_mp4: Path, out_w: int, out_h: int,
                    crf: str = "24", maxrate: str = "1260k", audio_br: str = "128k", seed: int = 999) -> list[float]:
    t0 = time.time()
    imgs = [load_img_wh(s[0], out_w, out_h, x_bias=s[14] if len(s) > 14 else 0.5) for s in shots]
    durs = [s[1] * BEAT for s in shots]
    starts = np.cumsum([0.0] + durs[:-1]).tolist()
    total_dur = float(sum(durs))
    total_frames = int(round(total_dur * FPS))

    uploaded_mp3 = AUDIO_DIR / "latest_track.mp3"
    sfx_events = [(starts[idx] + 0.08, s[13]) for idx, s in enumerate(shots) if s[13]]
    wav_path = Path(f"/tmp/mordor51_audio_{out_w}x{out_h}.wav")
    synthesize_audio(wav_path, total_dur, sfx_events)

    bufsize = f"{int(maxrate.rstrip('k')) * 2}k"
    if uploaded_mp3.is_file():
        audio_inputs = [
            "-i", str(uploaded_mp3), "-i", str(wav_path),
            "-filter_complex", "[1:a]volume=1.0[a0];[2:a]volume=0.18[a1];[a0][a1]amix=inputs=2:duration=shortest[aout]",
            "-map", "0:v", "-map", "[aout]",
        ]
    else:
        audio_inputs = ["-i", str(wav_path)]

    cmd = [
        "/usr/local/bin/ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{out_w}x{out_h}", "-r", str(FPS), "-i", "-",
        *audio_inputs,
        "-c:v", "libx264", "-preset", "fast", "-crf", crf,
        "-maxrate", maxrate, "-bufsize", bufsize, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", audio_br, "-movflags", "+faststart",
        "-shortest", str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vfx = FastCombatVFX(out_w, out_h, seed=seed)

    s_idx = 0
    for f in range(total_frames):
        t = f / FPS
        while s_idx + 1 < len(shots) and t >= starts[s_idx + 1]:
            s_idx += 1
        u = np.clip((t - starts[s_idx]) / max(1e-6, durs[s_idx]), 0.0, 1.0)
        _, _, z0, z1, px0, px1, py0, py1, shk, rn, sm, md, fr, sfx = shots[s_idx][:14]

        ue = 1.0 - (1.0 - u) ** 1.6
        zoom = z0 + (z1 - z0) * ue
        px = px0 + (px1 - px0) * ue
        py = py0 + (py1 - py0) * ue

        beat_phase = (t % BEAT) / BEAT
        beat_zoom = 1.0 + 0.008 * math.exp(-beat_phase * 7.0)
        flash = (1.0 - u / 0.14) * 0.72 if (sfx in ("explosion", "salvo", "heavy_mg") and u < 0.14) else 0.0
        cur_shk = shk * (1.75 * math.exp(-u * 3.0) + 0.55) if sfx in ("explosion", "salvo") else shk

        rgb = vfx.render(imgs[s_idx], f, zoom * beat_zoom, px, py, cur_shk, rn, sm, md, fr, flash=flash)
        proc.stdin.write(rgb.tobytes())
        if (f + 1) % 750 == 0 or (f + 1) == total_frames:
            print(f"  [{out_w}x{out_h}] Rendered {f + 1}/{total_frames} frames ({time.time() - t0:.1f}s)...", flush=True)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed ({rc}):\n{stderr_out[-1200:]}")
    print(f"  -> Saved {out_mp4.name} ({total_dur:.2f}s, {out_mp4.stat().st_size / 1e6:.2f} MB) in {time.time() - t0:.1f}s!", flush=True)
    return starts


def main():
    t_start = time.time()

    # =========================================================================
    # 51 STRICTLY UNIQUE, 100%-AUDITED CLEAN FRAMES ACROSS 332 BEATS = 148.66s
    # Mapped line-by-line to the lyrics of «АЗБУКА — ПО ПОЛЯМ»!
    # Note: rain_i < 0 => Winter Blizzard Snow; mud_i < 0 => Golden Spring Sun!
    # =========================================================================
    full_shots = [
        # --- ПРИПЕВ 1 (60 beats = 26.87s): «Только бам, бам, бам, бам, бам! Ищу твой сигнал антенной по полям! У тебя бабки — у меня дроны, пушки, танки!» ---
        (M3_DIR / "mordor_22_balrog_iskander_missile_launch.jpg",         5, 1.02, 1.13, -12,  12,  10, -14, 10.0, 0.45, 0.85, 0.35, 0.95, "explosion"),
        (M2_DIR / "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg",       5, 1.03, 1.12, -14,  18,   6, -10, 10.5, 0.75, 0.85, 0.55, 0.95, "salvo"),
        (M3_DIR / "mordor_23_gothmog_general_grad_tornado_salvo.jpg",     5, 1.02, 1.11, -16,  16,   6,  -8,  8.5, 0.60, 0.80, 0.45, 0.85, "salvo"),
        (M4_DIR / "mordor_35_black_numenorean_2s19_msta_s_krasnopol.jpg", 5, 1.03, 1.11, -12,  14,   6,  -8,  9.0, 0.55, 0.80, 0.40, 0.75, "explosion"),
        (B2_DIR / "s07_geran_f3_strike.jpg",                              6, 1.04, 1.13,   0,   0,  10, -12, 11.0, 0.80, 0.85, 0.30, 0.95, "explosion"),
        (M5_DIR / "mordor_41_antenna_po_polyam_orc_goblin_signal.jpg",    8, 1.02, 1.11, -14,  14,   6,  -8,  2.8, 0.55, 0.35, 0.25, 0.05, "radio_scan"),
        (M5_DIR / "mordor_42_elves_babki_dollars_nato_luxury.jpg",        8, 1.02, 1.12,  12, -12,   4,  -8,  3.5, 0.25, 0.45, 0.00, 0.20, "geran_buzz"),
        (M1_DIR / "mordor_02_goblins_fiber_fpv_lancet_team.jpg",          6, 1.02, 1.10, -12,  16,   6,  -8,  3.2, 0.55, 0.35, 0.15, 0.05, "geran_buzz"),
        (M2_DIR / "mordor_17_saruman_tactical_pantsir_air_defense.jpg",   6, 1.02, 1.11, -14,  14,   6,  -8,  6.0, 0.55, 0.55, 0.20, 0.65, "salvo"),
        (MOD_DIR / "modern_06_t90m_proryv_nakidka_breach.jpg",            6, 1.03, 1.11, -16,  18,   4,  -6,  8.0, 0.50, 0.80, 0.65, 0.45, "explosion"),

        # --- КУПЛЕТ 1 (72 beats = 32.24s): «Руки околели от холодной зимы... Вышла из луча, в мониторе нету... Я разнёс частоты твои... Антенной по полям» ---
        (M5_DIR / "mordor_43_cold_winter_hands_orc_frozen_trench.jpg",    8, 1.02, 1.10, -10,  10,   6,  -6,  1.8,-0.85, 0.30, 0.00, 0.00, None),
        (M2_DIR / "mordor_11_sauron_command_bunker_streams.jpg",          6, 1.02, 1.10,   0,   0,   8, -10,  2.0, 0.00, 0.20, 0.00, 0.15, "radio_scan"),
        (M4_DIR / "mordor_33_goblin_fpv_workshop_dugout_soldering.jpg",   6, 1.02, 1.10,  10, -12,   6,  -6,  2.0, 0.00, 0.25, 0.00, 0.25, None),
        (MOD_DIR / "modern_03_lancet_and_fiber_fpv_team.jpg",             6, 1.02, 1.10,  14, -14,   4,  -6,  3.0, 0.50, 0.40, 0.15, 0.05, None),
        (M5_DIR / "mordor_44_no_signal_monitor_vyshla_iz_lucha.jpg",      8, 1.02, 1.12,  -8,   8,   6, -10,  4.0,-0.75, 0.35, 0.00, 0.05, "radio_scan"),
        (M5_DIR / "mordor_45_frequency_hopping_spectrum_orc_ew.jpg",      8, 1.02, 1.11, -12,  12,   4,  -6,  2.5, 0.00, 0.20, 0.00, 0.10, "radio_scan"),
        (M3_DIR / "mordor_25_shelob_spider_fiber_optic_ambush.jpg",       6, 1.02, 1.12, -14,  14,   6,  -8,  4.5, 0.55, 0.60, 0.25, 0.35, "warg_growl"),
        (M5_DIR / "mordor_48_buhanka_snow_antenna_mast_po_polyam.jpg",    6, 1.02, 1.10, -14,  14,   6,  -6,  2.8,-0.55, 0.35, 0.25, 0.05, "radio_scan"),
        (M1_DIR / "mordor_06_geran_swarm_goblin_techs_night.jpg",         6, 1.03, 1.10, -10,  18,   8, -12,  7.0, 0.80, 0.70, 0.20, 0.85, "geran_buzz"),
        (MOD_DIR / "modern_04_geran_black_swarm_night_pickup.jpg",        6, 1.03, 1.11,  12, -16,   6, -10,  7.0, 0.75, 0.70, 0.20, 0.80, "geran_buzz"),
        (B2_DIR / "s06_geran_f2_swarm.jpg",                               6, 1.03, 1.12, -16,  16,  -8,   8,  5.5, 0.85, 0.65, 0.00, 0.40, "geran_buzz"),

        # --- ПРИПЕВ 2 (60 beats = 26.87s): «Только бам, бам, бам — По полям! Дроны, пушки, танки!» ---
        (M4_DIR / "mordor_34_smaug_drake_tu95_kh101_strategic_launch.jpg",6, 1.02, 1.12, -18,  18,   6, -10,  7.5, 0.70, 0.70, 0.10, 0.85, "salvo"),
        (M2_DIR / "mordor_15_fell_beast_umpk_fab_drop.jpg",               6, 1.03, 1.12, -18,  20,  -8,  12,  5.5, 0.45, 0.65, 0.00, 0.45, "geran_buzz"),
        (M4_DIR / "mordor_32_witch_king_ka52_alligator_vihr_strike.jpg",  6, 1.03, 1.12, -18,  18,   4,  -8,  7.5, 0.75, 0.65, 0.70, 0.65, "salvo"),
        (M3_DIR / "mordor_26_olog_hai_troll_sapper_ur77_zmej_gorynych.jpg",6,1.02, 1.12, -16,  18,   6, -10,  9.5, 0.55, 0.80, 0.65, 0.85, "explosion"),
        (M4_DIR / "mordor_37_haradrim_oliphaunt_column_po_polyam_march.jpg",6,1.02,1.11, -20,  20,   4,  -6,  4.5, 0.70, 0.60, 0.75, 0.20, "warg_growl"),
        (M1_DIR / "mordor_01_warg_riders_desertcross_charge.jpg",         6, 1.04, 1.12, -24,  24,   4,  -4,  6.5, 0.75, 0.55, 0.95, 0.25, "warg_growl"),
        (M2_DIR / "mordor_14_uruk_hai_white_hand_enduro_assault.jpg",     6, 1.03, 1.12,  18, -18,   4,  -6,  6.5, 0.70, 0.45, 0.90, 0.15, "warg_growl"),
        (M2_DIR / "mordor_16_goblin_sappers_ground_robot_kurier.jpg",     6, 1.02, 1.10, -12,  14,   6,  -6,  4.0, 0.45, 0.55, 0.25, 0.25, "heavy_mg"),
        (M4_DIR / "mordor_31_azog_pale_orc_bmpt_terminator_assault.jpg",  6, 1.03, 1.12, -16,  16,   6,  -8,  8.0, 0.65, 0.70, 0.85, 0.65, "heavy_mg"),
        (M2_DIR / "mordor_12_grond_jet_battering_ram_reb.jpg",            6, 1.02, 1.12, -16,  16,   8,  -8,  8.0, 0.65, 0.75, 0.75, 0.50, "explosion"),

        # --- КУПЛЕТ 2 (60 beats = 26.87s): «Этот лютый холод, где-то минус сорок / Лес, лес, лес — нужно тебя найти!» ---
        (M5_DIR / "mordor_46_minus_forty_snow_forest_search_wargs.jpg",   8, 1.02, 1.11, -14,  14,   6,  -8,  2.5,-0.95, 0.35, 0.00, 0.00, "warg_growl"),
        (M5_DIR / "mordor_47_bird_rescued_orc_hugs_fpv_snow.jpg",         8, 1.02, 1.10, -10,  10,   4,  -6,  2.0,-0.75, 0.25, 0.00, 0.00, "radio_scan"),
        (M3_DIR / "mordor_24_lurtz_uruk_sniper_svd_thermal_pair.jpg",     6, 1.02, 1.11,  10, -12,   4,  -6,  2.5, 0.65, 0.40, 0.05, 0.05, None),
        (MOD_DIR / "modern_01_orc_storm_squad_vkpo_moss.jpg",             6, 1.02, 1.10, -14,  14,   4,  -6,  3.5, 0.65, 0.35, 0.35, 0.05, None),
        (MOD_DIR / "modern_02_desertcross_buggy_enduro_po_polyam.jpg",    6, 1.03, 1.11,  20, -20,   0,  -6,  6.0, 0.75, 0.50, 0.90, 0.15, None),
        (M1_DIR / "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg",          6, 1.02, 1.10, -20,  22,   6,  -8,  5.5, 0.70, 0.60, 0.75, 0.20, "explosion"),
        (M3_DIR / "mordor_28_corsairs_umbar_raptor_boat_amphibious_orcs.jpg",6,1.02,1.11,-22,  22,   4,  -6,  5.0, 0.75, 0.55, 0.20, 0.15, "heavy_mg"),
        (M1_DIR / "mordor_05_nazgul_fell_beast_ka52_airbase.jpg",         7, 1.02, 1.09,  16, -16,   4,  -8,  4.0, 0.60, 0.65, 0.15, 0.20, "warg_growl"),
        (M4_DIR / "mordor_36_orc_medevac_armored_linza_warg_medic.jpg",   7, 1.02, 1.09, -10,  10,   4,  -6,  2.5, 0.45, 0.35, 0.20, 0.05, None),

        # --- ПРИПЕВ 3 (46 beats = 20.60s): Падение Белой Крепости, разгром эльфийских «бабок» и капитуляция ---
        (M1_DIR / "mordor_03_armored_cave_troll_kontakt1_breach.jpg",     6, 1.04, 1.13,   0,   0,  12, -12,  8.5, 0.45, 0.75, 0.60, 0.50, "heavy_mg"),
        (M2_DIR / "mordor_18_warg_cavalry_pursuit_fleeing_elves.jpg",     6, 1.03, 1.12, -20,  20,   4,  -6,  6.5, 0.65, 0.65, 0.85, 0.35, "warg_growl"),
        (M1_DIR / "mordor_07_cqb_wargs_orcs_capture_elves.jpg",           6, 1.02, 1.09, -14,  14,   6,  -6,  3.5, 0.55, 0.45, 0.15, 0.10, None),
        (M3_DIR / "mordor_21_mouth_of_sauron_capitulation_elves.jpg",     8, 1.02, 1.10, -14,  14,   6,  -8,  3.0, 0.60, 0.50, 0.20, 0.10, "warg_growl"),
        (M1_DIR / "mordor_09_tricolor_mordor_flag_bare_orcs.jpg",         7, 1.02, 1.11,   0,   0,  10, -14,  3.0, 0.40, 0.55, 0.05, 0.35, "explosion"),
        (MOD_DIR / "modern_08_novaya_izengardovka_sign_svo.jpg",          6, 1.02, 1.09, -10,  10,   4,  -6,  2.5, 0.40, 0.35, 0.15, 0.05, None),
        (M1_DIR / "mordor_08_novaya_izengardovka_warg_svo.jpg",           7, 1.02, 1.10,  10, -10,   6,  -8,  2.5, 0.40, 0.35, 0.15, 0.10, "warg_growl"),

        # --- ФИНАЛ-КОДА (34 beats = 15.22s): «Всё будет хорошо, плохое в прошлом / Весна придёт — тяну к небу ладошки!» ---
        (M4_DIR / "mordor_39_orc_banya_samovar_harmony_izengardovka.jpg", 8, 1.02, 1.10,  12, -12,   4,  -6,  1.8, 0.00, 0.28, 0.00, 0.15, None),
        (M2_DIR / "mordor_20_grand_parade_victory_novaya_izengardovka.jpg",8,1.02, 1.11,   0,   0,  10, -10,  2.8, 0.15, 0.40, 0.00, 0.30, "explosion"),
        (M5_DIR / "mordor_49_spring_comes_orc_palms_to_sky.jpg",          9, 1.02, 1.11,  -8,   8,   8, -10,  1.6, 0.00, 0.10,-0.95, 0.15, None),
        (M5_DIR / "mordor_50_spring_victory_citadel_radar_eye_clean.jpg", 9, 1.09, 1.01,   8,  -8,  -6,   6,  1.8, 0.00, 0.15,-0.75, 0.25, "warg_growl"),
    ]

    unique_paths = {s[0].resolve() for s in full_shots}
    assert len(full_shots) == 51 and len(unique_paths) == 51, (
        f"Expected 51 strictly unique audited shots, got {len(full_shots)} total / {len(unique_paths)} unique!"
    )
    total_beats = sum(s[1] for s in full_shots)
    assert total_beats == 332, f"Expected 332 beats (148.66s), got {total_beats}"
    print(f"Verified: {len(full_shots)} STRICTLY UNIQUE CLEAN frames, {total_beats} beats ({total_beats * BEAT:.2f}s)!", flush=True)

    full_mp4 = OUT_DIR / "mordor_svo_clean_51shots_2m28s_1080p.mp4"
    starts = render_timeline(full_shots, full_mp4, 1920, 1080, crf="24", maxrate="1260k", audio_br="128k", seed=999)

    # =========================================================================
    # 2. 20-SHOT LYRIC-SYNCED VERTICAL 9:16 REEL (72 beats = 32.24s)
    # =========================================================================
    reel_shots = [
        (M3_DIR / "mordor_22_balrog_iskander_missile_launch.jpg",         3.6, 1.03, 1.13,  -8,   8,  12, -16, 9.0, 0.45, 0.85, 0.25, 0.95, "explosion", 0.62),
        (M2_DIR / "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg",       3.6, 1.03, 1.12, -10,  10,   6, -10, 9.5, 0.70, 0.85, 0.50, 0.95, "salvo",     0.52),
        (M5_DIR / "mordor_41_antenna_po_polyam_orc_goblin_signal.jpg",    3.6, 1.03, 1.11,  -8,   8,   6,  -8, 2.8, 0.55, 0.35, 0.20, 0.05, "radio_scan",0.58),
        (M5_DIR / "mordor_42_elves_babki_dollars_nato_luxury.jpg",        3.6, 1.03, 1.12,  -6,   6,   4,  -8, 3.5, 0.25, 0.45, 0.00, 0.20, "geran_buzz",0.55),
        (M1_DIR / "mordor_02_goblins_fiber_fpv_lancet_team.jpg",          3.6, 1.03, 1.11,  -8,   8,   6,  -6, 3.2, 0.50, 0.35, 0.15, 0.05, None,        0.55),
        (M4_DIR / "mordor_31_azog_pale_orc_bmpt_terminator_assault.jpg",  3.6, 1.03, 1.12, -10,  10,   6,  -8, 8.0, 0.65, 0.70, 0.85, 0.65, "heavy_mg",  0.35),
        (M5_DIR / "mordor_43_cold_winter_hands_orc_frozen_trench.jpg",    3.6, 1.02, 1.10,  -6,   6,   6,  -6, 1.8,-0.85, 0.30, 0.00, 0.00, None,        0.44),
        (M5_DIR / "mordor_44_no_signal_monitor_vyshla_iz_lucha.jpg",      3.6, 1.02, 1.12,  -6,   6,   6, -10, 4.0,-0.75, 0.35, 0.00, 0.05, "radio_scan",0.60),
        (M5_DIR / "mordor_45_frequency_hopping_spectrum_orc_ew.jpg",      3.6, 1.02, 1.11,  -8,   8,   4,  -6, 2.5, 0.00, 0.20, 0.00, 0.10, "radio_scan",0.48),
        (M5_DIR / "mordor_46_minus_forty_snow_forest_search_wargs.jpg",   3.6, 1.02, 1.11,  -8,   8,   6,  -8, 2.5,-0.95, 0.35, 0.00, 0.00, "warg_growl",0.52),
        (M5_DIR / "mordor_47_bird_rescued_orc_hugs_fpv_snow.jpg",         3.6, 1.02, 1.10,  -6,   6,   4,  -6, 2.0,-0.75, 0.25, 0.00, 0.00, None,        0.48),
        (M3_DIR / "mordor_25_shelob_spider_fiber_optic_ambush.jpg",       3.6, 1.03, 1.12,  -8,   8,   6,  -8, 4.5, 0.55, 0.55, 0.20, 0.35, "geran_buzz",0.46),
        (M4_DIR / "mordor_37_haradrim_oliphaunt_column_po_polyam_march.jpg",3.6,1.03,1.11, -12,  12,   4,  -6, 4.5, 0.65, 0.55, 0.70, 0.20, "warg_growl",0.35),
        (M1_DIR / "mordor_01_warg_riders_desertcross_charge.jpg",         3.6, 1.04, 1.13, -14,  14,   4,  -6, 6.5, 0.75, 0.55, 0.90, 0.25, "warg_growl",0.50),
        (M2_DIR / "mordor_12_grond_jet_battering_ram_reb.jpg",            3.6, 1.03, 1.12,  -8,   8,   8, -10, 8.0, 0.60, 0.75, 0.70, 0.50, "explosion", 0.50),
        (M3_DIR / "mordor_21_mouth_of_sauron_capitulation_elves.jpg",     3.6, 1.03, 1.11,  -8,   8,   6,  -8, 3.0, 0.55, 0.50, 0.20, 0.10, None,        0.32),
        (M5_DIR / "mordor_48_buhanka_snow_antenna_mast_po_polyam.jpg",    3.6, 1.02, 1.10,  -8,   8,   4,  -6, 2.5,-0.50, 0.30, 0.20, 0.05, None,        0.48),
        (M4_DIR / "mordor_39_orc_banya_samovar_harmony_izengardovka.jpg", 3.6, 1.02, 1.10,  -6,   6,   4,  -6, 1.8, 0.00, 0.25, 0.00, 0.15, None,        0.48),
        (M5_DIR / "mordor_49_spring_comes_orc_palms_to_sky.jpg",          3.6, 1.02, 1.11,  -6,   6,   8, -10, 1.6, 0.00, 0.10,-0.95, 0.15, None,        0.48),
        (M5_DIR / "mordor_50_spring_victory_citadel_radar_eye_clean.jpg", 3.6, 1.08, 1.01,   6,  -6,  -6,   6, 1.8, 0.00, 0.15,-0.75, 0.25, "explosion", 0.56),
    ]

    reel_mp4 = OUT_DIR / "mordor_svo_reel_9x16.mp4"
    render_timeline(reel_shots, reel_mp4, 1080, 1920, crf="23", maxrate="2100k", audio_br="160k", seed=777)

    # =========================================================================
    # 3. ZIP PACKAGES: 51-CLEAN-FRAME TIMECODED MASTER ZIP + 10-SONG-FRAME ZIP
    # =========================================================================
    p5_zip = OUT_DIR / "mordor_svo_song_10_frames.zip"
    with zipfile.ZipFile(p5_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(M5_DIR.glob("*.jpg")):
            zf.write(p, arcname=p.name)

    all51_zip = OUT_DIR / "mordor_svo_clean_51_frames.zip"
    with zipfile.ZipFile(all51_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, (s, st) in enumerate(zip(full_shots, starts), start=1):
            mm = int(st) // 60
            ss = int(st) % 60
            arc = f"{idx:02d}_{mm:02d}m{ss:02d}s_{s[0].name}"
            zf.write(s[0], arcname=arc)

    print(f"\nALL DONE in {time.time() - t_start:.1f}s!")
    print(f"  16:9 CLEAN 51-SHOT MP4: {full_mp4} ({full_mp4.stat().st_size / 1e6:.2f} MB)")
    print(f"  9:16 SONG REEL MP4:     {reel_mp4} ({reel_mp4.stat().st_size / 1e6:.2f} MB)")
    print(f"  SONG 10-ZIP:            {p5_zip} ({p5_zip.stat().st_size / 1e6:.2f} MB)")
    print(f"  CLEAN 51-TIMECODE ZIP:  {all51_zip} ({all51_zip.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
