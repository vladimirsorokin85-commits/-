#!/usr/bin/env python3
"""Beat-locked & lyric-locked 1080p30 master renderer for «ПОСТ-РОССИЯ» synced to Пост-Россия.mp3.

Song analysis parameters (verified via HPSS + Chroma Chorus Cross-Correlation + Beat Grid):
  - Audio file: video_studio/post_rossiya/audio/post_rossiya_song.mp3
  - Exact duration: 157.56s (02:37.56), 48 kHz stereo
  - Tempo: 85.66 BPM (1 beat = 0.70044s, 1 bar = 2.80177s, downbeat anchor = 0.007s)
  - Musical structure:
      M01       (  0.00 -   2.81s): Cold dark intro -> phone screen emerge (Shots 001-003)
      M02 - M08 (  2.81 -  22.42s): Opening Folk Choir Lament + M08 bass pickup (8 B-Roll overture shots)
      M09 - M12 ( 22.42 -  33.63s): Verse 1 · Act I   «Я плакал, смотря на чужой инстаграм...» (Shots 004-012)
      M13 - M16 ( 33.63 -  44.84s): Verse 1 · Act II  «Клали искусственные цветы к могилам...» (Shots 013-023)
      M17 - M20 ( 44.84 -  56.04s): Verse 1 · Act III «Все думали, самые умные, гордые...» (Shots 024-033)
      M21 - M28 ( 56.04 -  78.46s): First Chorus x2   «И стонет в лапах бессилия...» (Shots 034-044)
      M29 - M40 ( 78.46 - 112.08s): Verse 2 (12 bars = 12 rap lines, 1 bar/line) (Shots 045-076)
      M41 - M44 (112.08 - 123.29s): Pre-Final A Cappella Choir Lament (4 B-Roll pre-dawn cutaways)
      M45 - M52 (123.29 - 145.70s): Final Chorus Climax (Choir + Sub-Bass) in City Square (Shots 077-085)
      M53 - M57 (145.70 - 157.56s): Outro Choir-to-Noise Sea Ending & Warm Horizon Line (Shots 086-088)
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

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[1]
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from grade_post_rossiya import apply_color_state  # noqa: E402
from storyboard_data import get_broll_shots, get_main_shots  # noqa: E402

W, H, FPS = 1920, 1080, 30
BASE_W, BASE_H = 2304, 1296
SONG_DUR = 157.56
TMP_DIR = Path("/tmp/post_rossiya")
OUT_DIR = THIS_DIR / "output"
AUDIO_PATH = THIS_DIR / "audio" / "post_rossiya_song.mp3"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BLACK_FRAME = Image.new("RGB", (W, H), (0, 0, 0))


def build_synced_timeline() -> list[dict]:
    """Construct the 100-clip (88 main + 12 B-roll) timeline locked to 85.66 BPM & exact vocal sections."""
    main_by_num = {s["num"]: dict(s) for s in get_main_shots()}
    broll_by_num = {b["num"]: dict(b) for b in get_broll_shots()}

    def m_clip(num: int, t0: float, t1: float, cue_override: str | None = None, act_override: str | None = None) -> dict:
        s = dict(main_by_num[num])
        s["t0"] = round(t0, 3)
        s["t1"] = round(t1, 3)
        s["duration"] = round(t1 - t0, 3)
        if cue_override:
            s["cue"] = cue_override
        if act_override:
            s["act"] = act_override
        return s

    def b_clip(bnum: int, t0: float, t1: float, act: str, cue: str, color_state: str, live_fx: str | None = None) -> dict:
        b = broll_by_num[bnum]
        return {
            "num": 100 + bnum,
            "display_code": f"B{bnum:02d}",
            "id": b["id"],
            "file": b["file"],
            "generated": True,
            "t0": round(t0, 3),
            "t1": round(t1, 3),
            "duration": round(t1 - t0, 3),
            "act": act,
            "cue": cue,
            "desc_ru": b["desc_ru"],
            "color_state": color_state,
            "move": b["move"],
            "focus": [0.50, 0.50],
            "live_fx": live_fx,
        }

    tl: list[dict] = []

    # ==================== ПРОЛОГ + ВСТУПИТЕЛЬНЫЙ ХОР (0.00 - 22.42s, M01-M08) ====================
    tl += [
        m_clip(1, 0.00, 1.06, "0:00–0:02.8 · Вступление из темноты", "ПРОЛОГ · ХОЛОДНЫЙ РАССВЕТ"),
        m_clip(2, 1.06, 1.94, "0:00–0:02.8 · Треснувшее стекло", "ПРОЛОГ · ХОЛОДНЫЙ РАССВЕТ"),
        m_clip(3, 1.94, 2.81, "0:00–0:02.8 · Отражение глаза в экране", "ПРОЛОГ · ХОЛОДНЫЙ РАССВЕТ"),
        # Opening Folk Choir Lament (M02-M07: 2.81 - 19.62s) + M08 Beat Pickup (19.62 - 22.42s)
        b_clip(12, 2.81, 5.61, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «И стонет в лапах бессилия...»", "faded_memory"),
        b_clip(1,  5.61, 8.41, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «Пост-Россия: прости меня...»", "faded_memory"),
        b_clip(4,  8.41, 11.21, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «Так пахнет утро последнее...»", "faded_memory"),
        b_clip(7,  11.21, 14.02, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «Предосеннее, предрасстрельное...»", "faded_memory"),
        b_clip(5,  14.02, 16.82, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «И стонет в лапах бессилия...»", "dirty_modern"),
        b_clip(6,  16.82, 18.92, "ВСТУПИТЕЛЬНЫЙ ХОР · УВЕРТЮРА", "Хор: «Пост-Россия: прости меня...»", "dirty_modern"),
        b_clip(2,  18.92, 20.67, "ВСТУПЛЕНИЕ БИТА · НОЧНОЙ ДОМ", "Нарастание пульса перед 1-м куплетом", "dirty_modern"),
        b_clip(9,  20.67, 22.42, "ВСТУПЛЕНИЕ БИТА · НОЧНАЯ КУХНЯ", "Герой курит у ночного окна перед куплетом", "dirty_modern"),
    ]

    # ==================== КУПЛЕТ 1 · АКТ I: ЧУЖАЯ БОЛЬ (22.42 - 33.63s, M09-M12) ====================
    tl += [
        m_clip(4,  22.42, 23.47, "«Я плакал, смотря на чужой инстаграм»"),
        m_clip(5,  23.47, 24.52, "«Я плакал, смотря на чужой инстаграм»"),
        m_clip(6,  24.52, 25.22, "«Я плакал, смотря на чужой инстаграм»"),
        m_clip(7,  25.22, 26.27, "«Там кто-то вернулся с войны»"),
        m_clip(8,  26.27, 27.32, "«Там кто-то вернулся с войны»"),
        m_clip(9,  27.32, 28.02, "«Там кто-то вернулся с войны»"),
        m_clip(10, 28.02, 29.78, "«Принеся в ноге свинца пару грамм»"),
        m_clip(11, 29.78, 31.53, "«Теперь будет ныть до зимы»"),
        m_clip(12, 31.53, 33.63, "«Теперь будет ныть до зимы»"),
    ]

    # ==================== КУПЛЕТ 1 · АКТ II: ПОЗДНЕЕ ПРОЩЕНИЕ (33.63 - 44.84s, M13-M16) ====================
    tl += [
        m_clip(13, 33.63, 34.33, "«Клали искусственные цветы к могилам»"),
        m_clip(14, 34.33, 35.03, "«Клали искусственные цветы к могилам»"),
        m_clip(15, 35.03, 35.73, "«Клали искусственные цветы к могилам»"),
        m_clip(16, 35.73, 36.43, "«Клали искусственные цветы к могилам»"),
        m_clip(17, 36.43, 37.48, "«И просили простить постфактум»"),
        m_clip(18, 37.48, 38.53, "«И просили простить постфактум»"),
        m_clip(19, 38.53, 39.23, "«И просили простить постфактум»"),
        m_clip(20, 39.23, 40.63, "«Мы были такие красивые»"),
        m_clip(21, 40.63, 42.03, "«Мы были такие красивые»"),
        m_clip(22, 42.03, 43.43, "«Пока жизнь нас ставила раком»"),
        m_clip(23, 43.43, 44.84, "«Пока жизнь нас ставила раком»"),
    ]

    # ==================== КУПЛЕТ 1 · АКТ III: ЦЕНА САМОУВЕРЕННОСТИ (44.84 - 56.04s, M17-M20) ====================
    tl += [
        m_clip(24, 44.84, 45.89, "«Все думали, самые умные, гордые»"),
        m_clip(25, 45.89, 46.94, "«Все думали, самые умные, гордые»"),
        m_clip(26, 46.94, 47.64, "«Все думали, самые умные, гордые»"),
        m_clip(27, 47.64, 48.69, "«Оказалось, вывезли за долги»"),
        m_clip(28, 48.69, 49.74, "«Оказалось, вывезли за долги»"),
        m_clip(29, 49.74, 50.44, "«Оказалось, вывезли за долги»"),
        m_clip(30, 50.44, 51.49, "«Там и оставили модные и холодные»"),
        m_clip(31, 51.49, 52.54, "«Там и оставили модные и холодные»"),
        m_clip(32, 52.54, 53.24, "«Там и оставили модные и холодные»"),
        m_clip(33, 53.24, 56.04, "«Плати налоги и включай мозги» (обрыв бита → очередь)"),
    ]

    # ==================== ПЕРВЫЙ ПРИПЕВ · ХОР В ПОЛЕ (56.04 - 78.46s, M21-M28) ====================
    tl += [
        m_clip(34, 56.04, 58.14, "Хор: «И стонет в лапах бессилия»"),
        m_clip(35, 58.14, 60.24, "Хор: «Пост-Россия: прости меня»"),
        m_clip(36, 60.24, 62.35, "Хор: «Пост-Россия: прости меня»"),
        m_clip(37, 62.35, 64.45, "Хор: «Так пахнет утро последнее»"),
        m_clip(38, 64.45, 66.55, "Хор: «Предосеннее, предрасстрельное»"),
        m_clip(39, 66.55, 68.65, "Хор: «И стонет в лапах бессилия»"),
        m_clip(40, 68.65, 70.60, "Хор: «Пост-Россия: прости меня»"),
        m_clip(41, 70.60, 72.30, "Хор: «Пост-Россия: прости меня»"),
        m_clip(42, 72.30, 74.26, "Хор: «Так пахнет утро последнее»"),
        m_clip(43, 74.26, 76.36, "Хор: «Предосеннее, предрасстрельное»"),
        m_clip(44, 76.36, 78.46, "Хор: «Предосеннее, предрасстрельное» (дальний план поля)"),
    ]

    # ==================== ВТОРОЙ КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ (78.46 - 112.08s, M29-M40) ====================
    tl += [
        # M29: Рукомойник наполнить густыми мыслями
        m_clip(45, 78.46, 79.51, "«Рукомойник наполнить густыми мыслями»"),
        m_clip(46, 79.51, 80.56, "«Рукомойник наполнить густыми мыслями»"),
        m_clip(47, 80.56, 81.26, "«Рукомойник наполнить густыми мыслями»"),
        # M30: Умыть ключевое лицо
        m_clip(48, 81.26, 82.31, "«Умыть ключевое лицо»"),
        m_clip(49, 82.31, 83.36, "«Умыть ключевое лицо»"),
        m_clip(50, 83.36, 84.06, "«Умыть ключевое лицо»"),
        # M31: Паразиты, харам, нечистые
        m_clip(51, 84.06, 85.11, "«Паразиты, харам, нечистые»"),
        m_clip(52, 85.11, 85.81, "«Паразиты, харам, нечистые»"),
        m_clip(53, 85.81, 86.86, "«Паразиты, харам, нечистые»"),
        # M32: Раньше курицы было яйцо
        m_clip(54, 86.86, 88.26, "«Раньше курицы было яйцо»"),
        m_clip(55, 88.26, 89.66, "«Раньше курицы было яйцо»"),
        # M33: Мы куражимся, нужные, босые
        m_clip(56, 89.66, 90.71, "«Мы куражимся, нужные, босые»"),
        m_clip(57, 90.71, 91.77, "«Мы куражимся, нужные, босые»"),
        m_clip(58, 91.77, 92.47, "«Мы куражимся, нужные, босые»"),
        # M34: Улыбаемся милым вам
        m_clip(59, 92.47, 93.87, "«Улыбаемся милым вам»"),
        m_clip(60, 93.87, 95.27, "«Улыбаемся милым вам»"),
        # M35: Но расквасят носы курносые
        m_clip(61, 95.27, 96.32, "«Но расквасят носы курносые»"),
        m_clip(62, 96.32, 97.37, "«Но расквасят носы курносые»"),
        m_clip(63, 97.37, 98.07, "«Но расквасят носы курносые»"),
        # M36: За стабильность любимых дам
        m_clip(64, 98.07, 99.12, "«За стабильность любимых дам»"),
        m_clip(65, 99.12, 100.17, "«За стабильность любимых дам»"),
        m_clip(66, 100.17, 100.87, "«За стабильность любимых дам»"),
        # M37: Мы же им позавидуем тихонько
        m_clip(67, 100.87, 102.27, "«Мы же им позавидуем тихонько»"),
        m_clip(68, 102.27, 103.67, "«Мы же им позавидуем тихонько»"),
        # M38: В лес уйдем собирать падальё
        m_clip(69, 103.67, 104.72, "«В лес уйдем собирать падальё»"),
        m_clip(70, 104.72, 105.77, "«В лес уйдем собирать падальё»"),
        m_clip(71, 105.77, 106.47, "«В лес уйдем собирать падальё»"),
        # M39: И весна уже не воротится
        m_clip(72, 106.47, 107.88, "«И весна уже не воротится»"),
        m_clip(73, 107.88, 109.28, "«И весна уже не воротится»"),
        # M40: Про нее нам споет вороньё
        m_clip(74, 109.28, 110.18, "«Про нее нам споет вороньё»"),
        m_clip(75, 110.18, 111.13, "«Про нее нам споет вороньё»"),
        m_clip(76, 111.13, 112.08, "«Про нее нам споет вороньё»"),
    ]

    # ==================== МОСТ · ХОР А КАПЕЛЛА ПЕРЕД ФИНАЛОМ (112.08 - 123.29s, M41-M44) ====================
    tl += [
        b_clip(3,  112.08, 114.88, "ПРЕДРАССВЕТНЫЙ ПЛАЧ · ХОР А КАПЕЛЛА", "Хор без ударных: «И стонет в лапах бессилия...»", "colorless_predawn", "rain_streaks"),
        b_clip(10, 114.88, 117.68, "ПРЕДРАССВЕТНЫЙ ПЛАЧ · ХОР А КАПЕЛЛА", "Хор без ударных: «Пост-Россия: прости меня...»", "colorless_predawn"),
        b_clip(11, 117.68, 120.48, "ПРЕДРАССВЕТНЫЙ ПЛАЧ · ХОР А КАПЕЛЛА", "Хор без ударных: «Так пахнет утро последнее...»", "colorless_predawn"),
        b_clip(8,  120.48, 123.29, "ПРЕДРАССВЕТНЫЙ ПЛАЧ · ХОР А КАПЕЛЛА", "Хор без ударных: «Предосеннее, предрасстрельное...»", "colorless_predawn"),
    ]

    # ==================== ФИНАЛЬНЫЙ ПРИПЕВ В ГОРОДЕ + МОРЕ (123.29 - 157.56s, M45-M57) ====================
    tl += [
        m_clip(77, 123.29, 126.09, "Кульминация хора: «И стонет в лапах бессилия»"),
        m_clip(78, 126.09, 128.89, "Кульминация хора: «Пост-Россия: прости меня»"),
        m_clip(79, 128.89, 131.34, "Кульминация хора: «Так пахнет утро последнее»"),
        m_clip(80, 131.34, 133.79, "Кульминация хора: «Предосеннее, предрасстрельное»"),
        m_clip(81, 133.79, 136.24, "Кульминация хора: «И стонет в лапах бессилия»"),
        m_clip(82, 136.24, 138.70, "Кульминация хора: «Пост-Россия: прости меня» (гаснут окна)"),
        m_clip(83, 138.70, 141.15, "Кульминация хора: «Так пахнет утро последнее»"),
        m_clip(84, 141.15, 143.60, "Кульминация хора: «Предосеннее, предрасстрельное»"),
        m_clip(85, 143.60, 145.70, "Герой медленно закрывает глаза (обрыв ударных)"),
        # Outro: Folk Choir Fades Into Industrial Noise -> Sea & Horizon Dawn
        m_clip(86, 145.70, 149.00, "Кода: Холодное утреннее море"),
        m_clip(87, 149.00, 152.20, "Кода: Главный герой один на берегу спиной к камере"),
        m_clip(88, 152.20, SONG_DUR, "Финал: Тёплая полоска света на горизонте (без титров)"),
    ]

    for idx, item in enumerate(tl, 1):
        item["seq"] = idx
        if "display_code" not in item:
            item["display_code"] = f"{item['num']:03d}"
    return tl


def ease_io(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def gate_weave(t: float, amp: float = 0.45) -> tuple[float, float]:
    dx = (math.sin(t * 1.7) * 0.9 + math.sin(t * 4.3 + 1.1) * 0.4) * amp
    dy = (math.cos(t * 1.3 + 0.7) * 0.8 + math.sin(t * 3.9 + 2.0) * 0.35) * amp
    return dx, dy


@lru_cache(maxsize=24)
def load_graded_base(rel_path: str, color_state: str) -> Image.Image:
    full_path = REPO_ROOT / rel_path
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
    return apply_color_state(im, color_state, seed=17, with_grain=False)


def crop_view_fast(base: Image.Image, z: float, cx: float, cy: float, dx: float = 0.0, dy: float = 0.0) -> Image.Image:
    """SIMD-accelerated subpixel crop+scale using Pillow resize(box=...)."""
    bw, bh = base.size
    ww, wh = bw / z, bh / z
    x0 = min(max(0.0, cx * bw - ww / 2.0 + dx), bw - ww)
    y0 = min(max(0.0, cy * bh - wh / 2.0 + dy), bh - wh)
    return base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + wh))


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
    return [
        (
            float(rng.uniform(-0.15, 1.05)),
            float(rng.uniform(0.35, 0.94)),
            float(rng.uniform(0.16, 0.42)),
            int(rng.integers(7, 16)),
            int(rng.integers(4, 10)),
        )
        for _ in range(22)
    ]


@lru_cache(maxsize=1)
def _horizon_warm_layers() -> tuple[np.ndarray, np.ndarray]:
    y = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    x = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :, None]
    slit = np.exp(-((y - 0.495) / 0.016) ** 2) * np.exp(-(x / 0.80) ** 2)
    soft_glow = np.exp(-((y - 0.490) / 0.080) ** 2) * np.exp(-(x / 0.92) ** 2)
    warm = slit * np.array([0.13, 0.085, 0.032], np.float32) + soft_glow * np.array([0.045, 0.028, 0.008], np.float32)
    return warm, slit


def apply_live_fx(frame: Image.Image, fx: str | None, p: float, t: float) -> Image.Image:
    if not fx:
        return frame
    if fx == "phone_emerge":
        if p < 0.24:
            return BLACK_FRAME.copy()
        if p < 0.72:
            k = ease_io((p - 0.24) / 0.48)
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
            blur_amt = ease_io((p - 0.68) / 0.32) * 5.2
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
        a = np.asarray(frame, np.float32)
        warmth = (a[..., 0] - a[..., 2]) * (a.mean(-1) / 255.0)
        if warmth.max() > 8.0:
            xs = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]
            thresholds = np.floor(xs * 6.0) / 6.0 + 0.12
            off_mask = np.clip((p - thresholds) / 0.10, 0.0, 1.0)
            win_mask = np.clip((warmth - 7.0) / 18.0, 0.0, 1.0) * off_mask
            a = a * (1.0 - 0.72 * win_mask[..., None])
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
        a = np.asarray(frame, np.float32) / 255.0
        emerge = ease_io(min(1.0, p / 0.80))
        warm, _ = _horizon_warm_layers()
        a = a + emerge * warm
        out = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        if p > 0.86:
            fade = ease_io((p - 0.86) / 0.14)
            out = Image.blend(out, BLACK_FRAME, fade)
        return out

    return frame


def render_single_shot_frame(sh: dict, t: float) -> Image.Image:
    base = load_graded_base(sh["file"], sh["color_state"])
    dur = max(0.05, sh["t1"] - sh["t0"])
    u = min(dur, max(0.0, t - sh["t0"]))
    p = u / dur
    ep = ease_io(p)

    fx, fy = sh["focus"]
    z_base = 1.04
    mv = sh["move"]
    cx, cy = fx, fy
    if mv == "slow_in":
        z = z_base + 0.095 * ep
    elif mv == "slow_out":
        z = (z_base + 0.105) - 0.095 * ep
    elif mv == "pan_left":
        z = max(z_base, 1.13)
        cx = min(0.58, fx + 0.055) - 0.11 * ep
    elif mv == "pan_right":
        z = max(z_base, 1.13)
        cx = max(0.42, fx - 0.055) + 0.11 * ep
    elif mv == "tilt_up":
        z = max(z_base, 1.14)
        cy = min(0.58, fy + 0.065) - 0.13 * ep
    else:
        z = z_base + 0.018 * ep

    dx, dy = gate_weave(t, amp=0.45 if mv == "static_live" else 0.65)
    fr = crop_view_fast(base, z, cx, cy, dx, dy)
    return apply_live_fx(fr, sh.get("live_fx"), p, t)


def should_dissolve(prev_sh: dict, cur_sh: dict) -> float:
    """Hard cuts on boom-bap rap beats; soft filmic dissolves on Folk Choir & Sea sections."""
    if cur_sh["num"] in (4, 33, 45, 77):
        return 0.0  # Razor-sharp musical drop cuts!
    if cur_sh["num"] == 13:
        return 0.42  # Rain blur dissolve into Act II
    act = cur_sh["act"]
    if any(k in act for k in ("ХОР", "ПРИПЕВ", "ФИНАЛ", "УВЕРТЮРА")):
        return 0.45
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
        diss = should_dissolve(shots[idx - 1], sh)
        u = t - sh["t0"]
        if diss > 0.0 and 0.0 <= u < diss:
            prev_sh = dict(shots[idx - 1])
            prev_sh["t1"] = sh["t0"] + diss
            prev_fr = render_single_shot_frame(prev_sh, t)
            fr = Image.blend(prev_fr, fr, ease_io(u / diss))
    return fr


def render_worker(part_idx: int, num_parts: int, out_path: Path) -> None:
    shots = build_synced_timeline()
    total_frames = int(round(SONG_DUR * FPS))
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
    t_start = time.time()
    for fi in range(f0, f1):
        img = frame_at(shots, fi / FPS)
        proc.stdin.write(img.tobytes())
        if (fi - f0 + 1) % 600 == 0 or fi == f1 - 1:
            done = fi - f0 + 1
            el = max(1e-3, time.time() - t_start)
            print(f"[worker {part_idx+1}/{num_parts}] {done}/{f1-f0} frames ({done/el:.1f} fps)", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"Worker {part_idx} failed")


def export_synced_docs(shots: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "title": "ПОСТ-РОССИЯ — Монтажный лист под оригинальную песню",
        "audio_file": "video_studio/post_rossiya/audio/post_rossiya_song.mp3",
        "duration_sec": SONG_DUR,
        "bpm": 85.66,
        "bar_sec": 2.8018,
        "total_clips": len(shots),
        "shots": shots,
    }
    (OUT_DIR / "synced_timeline_100.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# «ПОСТ-РОССИЯ» — Синхронная монтажная карта под песню (0:00.00 – 2:37.56)",
        "",
        f"- **Аудиодорожка:** `Пост-Россия.mp3` (`02:37.56`, `48 000 Гц`, стерео)",
        "- **Темп и сетка:** `85.66 BPM` (`1 доля = 0.700 с`, `1 такт 4/4 = 2.802 с`)",
        f"- **Всего планов в монтаже:** `{len(shots)}` (`88` основных сюжетных + `12` документальных перебивок B-Roll)",
        "",
        "| № п/п | Код кадра | Тайм-код | Длит. | Раздел / Музыкальная строка | Визуальный план | Цвет |",
        "|---:|:---:|:---:|---:|---|---|:---:|",
    ]
    for s in shots:
        m0, s0 = int(s["t0"] // 60), s["t0"] % 60
        m1, s1 = int(s["t1"] // 60), s["t1"] % 60
        tc = f"`{m0}:{s0:05.2f}–{m1}:{s1:05.2f}`"
        md.append(
            f"| {s['seq']} | `{s['display_code']}` | {tc} | {s['duration']:.2f}с | "
            f"**{s['act']}** — {s['cue']} | {s['desc_ru']} | `{s['color_state']}` |"
        )
    (OUT_DIR / "ТАЙМКОДЫ_ПОД_ПЕСНЮ.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def build_all() -> dict:
    shots = build_synced_timeline()
    export_synced_docs(shots)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    p0 = TMP_DIR / "sync_part0.mp4"
    p1 = TMP_DIR / "sync_part1.mp4"
    t0 = time.time()
    w0 = subprocess.Popen([sys.executable, __file__, "--worker", "0", "2", str(p0)])
    w1 = subprocess.Popen([sys.executable, __file__, "--worker", "1", "2", str(p1)])
    if w0.wait() != 0 or w1.wait() != 0:
        raise RuntimeError("Parallel render workers failed")
    print(f"Both video halves rendered in {time.time() - t0:.1f}s", flush=True)

    concat_f = TMP_DIR / "sync_concat.txt"
    concat_f.write_text(f"file '{p0}'\nfile '{p1}'\n", encoding="utf-8")
    silent_hq = TMP_DIR / "post_rossiya_silent_hq_1080p.mp4"
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_f),
        "-c:v", "copy", "-an", "-movflags", "+faststart", str(silent_hq),
    ], check=True)

    # 1. Ultra-HQ Master WITH SONG in /tmp (served instantaneously by Studio Preview)
    hq_with_song = TMP_DIR / "post_rossiya_hq_1080p.mp4"
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(silent_hq),
        "-i", str(AUDIO_PATH),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-af", f"afade=t=out:st={SONG_DUR - 0.70:.2f}:d=0.70",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(hq_with_song),
    ], check=True)

    # 2. Persisted Full HD 1080p30 Master WITH SONG inside workspace (~44 MB, snapshot-safe)
    persisted_with_song = OUT_DIR / "post_rossiya_master_1080p.mp4"
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(silent_hq),
        "-i", str(AUDIO_PATH),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-maxrate", "2500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p",
        "-af", f"afade=t=out:st={SONG_DUR - 0.70:.2f}:d=0.70",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(persisted_with_song),
    ], check=True)

    status = {
        "master_video": str(persisted_with_song.relative_to(REPO_ROOT)),
        "master_size_mb": round(persisted_with_song.stat().st_size / 1e6, 2),
        "hq_size_mb": round(hq_with_song.stat().st_size / 1e6, 2),
        "duration_sec": SONG_DUR,
        "bpm": 85.66,
        "total_clips": len(shots),
        "with_audio": True,
        "main_generated": 88,
        "main_total": 88,
        "broll_generated": 12,
        "broll_total": 12,
    }
    (OUT_DIR / "build_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    return status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=3, metavar=("IDX", "NPARTS", "OUT"))
    args = ap.parse_args()
    if args.worker:
        render_worker(int(args.worker[0]), int(args.worker[1]), Path(args.worker[2]))
        return
    build_all()


if __name__ == "__main__":
    main()
