#!/usr/bin/env python3
"""Cinematic 4-state colour dramaturgy for «ПОСТ-РОССИЯ», built on video_studio/toolkit/grade.py LUTs.

Color states defined by the director's treatment:
1. dirty_modern       (0:00–0:52, Куплет 1 / Акты I–III):
   Холодный синий, асфальтовый серый, болезненный зелёный, жёлтый свет старых ламп.
2. faded_memory       (0:52–1:17, Первый припев — Хор в поле):
   Бледно-серое небо, чёрная земля, тусклые лица, холодный туман.
3. reality_decay      (1:17–2:04, Второй куплет — Разложение реальности):
   Грязно-коричневый, болотный, землистый.
4. colorless_predawn  (2:04–2:26, Финальный припев — Хор в пустом городе):
   Почти монохромное изображение в бесцветном утреннем свете.
5. predawn_horizon    (2:26–2:38, Финал у холодного моря):
   Почти монохромное изображение с едва заметным тёплым светом на горизонте.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

STUDIO_ROOT = Path(__file__).resolve().parents[1]
if str(STUDIO_ROOT / "toolkit") not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT / "toolkit"))

import grade as tk_grade  # noqa: E402


def _sodium_halation(img: Image.Image, thr: float = 0.78, radius: int = 16, amt: float = 0.32) -> Image.Image:
    """Warm sickly-yellow sodium-vapor lamp bloom around highlights."""
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    lum = a.max(-1)
    m = np.clip((lum - thr) / max(1e-4, 1.0 - thr), 0.0, 1.0)
    glow = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    g = np.asarray(glow, np.float32)[..., None] / 255.0 * np.array([1.0, 0.82, 0.28], np.float32)
    a = 1.0 - (1.0 - a) * (1.0 - g * amt)
    return Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))


def apply_color_state(img: Image.Image, state: str, seed: int = 0, with_grain: bool = True) -> Image.Image:
    """Apply one of the film's colour states using real .cube film stocks."""
    if state == "dirty_modern":
        # Cold slate blue + asphalt grey + sickly fluorescent green shadows + warm old lamp glow
        im = tk_grade.apply_lut(img, "fuji_xtrans_iii_classic_chrome", 0.72)
        im = ImageEnhance.Color(im).enhance(0.78)
        a = np.asarray(im, np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        sh = (1.0 - lum)[..., None] ** 1.8
        mid = (1.0 - np.abs(lum - 0.45) * 1.8).clip(0.0, 1.0)[..., None]
        hi = (lum ** 2.2)[..., None]
        # Shadows: cold slate blue; Midtones: subtle sickly green-grey; Highlights: faint sodium yellow
        a = a + sh * np.array([-0.035, 0.008, 0.048], np.float32)
        a = a + mid * np.array([-0.015, 0.018, -0.005], np.float32)
        a = a + hi * np.array([0.040, 0.026, -0.035], np.float32)
        im = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        im = _sodium_halation(im, thr=0.80, radius=14, amt=0.28)
        im = tk_grade.vignette(im, 0.30)
        return tk_grade.grain(im, 0.032, seed=seed) if with_grain else im

    if state == "faded_memory":
        # Pale grey sky, black wet earth, muted faces, cold mist
        im = tk_grade.apply_lut(img, "fuji_xtrans_iii_pro_neg_hi", 0.75)
        im = ImageEnhance.Color(im).enhance(0.46)
        a = np.asarray(im, np.float32) / 255.0
        # Crush earth blacks slightly while lifting misty upper midtones
        a = np.where(a < 0.25, a * 0.90, 0.225 + (a - 0.25) * 0.93)
        a = a * np.array([0.96, 0.99, 1.04], np.float32) + np.array([0.015, 0.020, 0.030], np.float32)
        im = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        im = tk_grade.vignette(im, 0.26)
        return tk_grade.grain(im, 0.036, seed=seed) if with_grain else im

    if state == "reality_decay":
        # Dirty brown, swampy olive, earthy ochre
        im = tk_grade.apply_lut(img, "fuji_3513_constlmap", 0.58)
        im = ImageEnhance.Color(im).enhance(0.66)
        a = np.asarray(im, np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        sh = (1.0 - lum)[..., None] ** 1.6
        mid = (1.0 - np.abs(lum - 0.42) * 1.7).clip(0.0, 1.0)[..., None]
        # Swampy olive-brown shadows & earthy dirty-ochre midtones
        a = a * np.array([1.03, 0.99, 0.86], np.float32)
        a = a + sh * np.array([0.018, 0.022, -0.028], np.float32)
        a = a + mid * np.array([0.032, 0.018, -0.036], np.float32)
        im = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        im = tk_grade.vignette(im, 0.38)
        return tk_grade.grain(im, 0.044, seed=seed) if with_grain else im

    if state in ("colorless_predawn", "predawn_horizon"):
        # Nearly monochrome pre-dawn, with optional faint warm light on horizon
        mono = tk_grade.apply_lut(img, "kodak_tri-x_400", 0.90)
        orig = ImageEnhance.Color(img.convert("RGB")).enhance(0.22)
        a_mono = np.asarray(mono, np.float32) / 255.0
        a_orig = np.asarray(orig, np.float32) / 255.0
        a = a_mono * 0.78 + a_orig * 0.22
        # Subtle cold steel pre-dawn cast
        a = a * np.array([0.96, 0.98, 1.03], np.float32)
        if state == "predawn_horizon":
            h, w = a.shape[:2]
            y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
            band = np.exp(-((y - 0.53) / 0.11) ** 2)
            a = a + band * np.array([0.048, 0.028, -0.010], np.float32)
        im = Image.fromarray((a.clip(0.0, 1.0) * 255).astype(np.uint8))
        im = tk_grade.vignette(im, 0.30)
        return tk_grade.grain(im, 0.034, seed=seed) if with_grain else im

    raise KeyError(f"Unknown color state: {state}")


def make_specimen(out_path: Path) -> Path:
    """Render a 2x2 comparison board showing the 4 colour states of «ПОСТ-РОССИЯ»."""
    refs_dir = Path(__file__).resolve().parent / "refs"
    samples = [
        ("1. ГРЯЗНАЯ СОВРЕМЕННОСТЬ (0:00–0:52)", refs_dir / "ref_04_color.jpg", "dirty_modern"),
        ("2. ВЫЦВЕТШАЯ ПАМЯТЬ (0:52–1:17)", refs_dir / "ref_03_choir.jpg", "faded_memory"),
        ("3. РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ (1:17–2:04)", refs_dir / "ref_02_city.jpg", "reality_decay"),
        ("4. БЕСЦВЕТНОЕ ПРЕДУТРО (2:04–2:38)", refs_dir / "ref_01_hero.jpg", "predawn_horizon"),
    ]
    from PIL import ImageDraw, ImageFont
    font_path = STUDIO_ROOT / "toolkit" / "fonts" / "Oswald-VF.ttf"
    fnt = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
    tw, th = 960, 540
    canvas = Image.new("RGB", (tw * 2, th * 2), (12, 13, 14))
    for i, (label, path, st) in enumerate(samples):
        im = Image.open(path).convert("RGB").resize((tw, th), Image.LANCZOS)
        graded = apply_color_state(im, st, seed=42 + i, with_grain=True)
        d = ImageDraw.Draw(graded)
        d.rectangle((20, th - 58, 20 + int(d.textlength(label, font=fnt)) + 28, th - 18), fill=(10, 12, 14))
        d.text((34, th - 53), label, font=fnt, fill=(228, 228, 224))
        canvas.paste(graded, ((i % 2) * tw, (i // 2) * th))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=90)
    return out_path


if __name__ == "__main__":
    p = Path(__file__).resolve().parent / "output" / "specimen_post_rossiya_grades.jpg"
    make_specimen(p)
    print(f"Saved colour specimen: {p}")
