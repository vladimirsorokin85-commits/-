#!/usr/bin/env python3
"""smartcrop.py — subject-aware reframing (16:9 -> 9:16 / 4:5 / 1:1) with OpenCV.

focus_point(img)   faces (Haar frontal+profile) -> else saliency (spectral residual) -> centre
crop_to(img, aspect, focus=None, headroom=0.33)  crop around the subject, face on the upper third
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


_hog = cv2.HOGDescriptor()
_hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def faces(img: Image.Image):
    """Faces >= 4% of frame width, strict neighbours (rejects mirrors/textures)."""
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    m = max(40, int(img.width * 0.04))
    f = list(_face.detectMultiScale(g, 1.08, 8, minSize=(m, m)))
    if not f:
        f = list(_prof.detectMultiScale(g, 1.08, 8, minSize=(m, m)))
    rgb = np.asarray(img.convert("RGB"))
    ycc = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    ok = []
    for (x, y, w, h) in f:
        roi = ycc[y + h // 5: y + h * 4 // 5, x + w // 5: x + w * 4 // 5]
        skin = ((roi[..., 1] > 135) & (roi[..., 1] < 180) & (roi[..., 2] > 85) & (roi[..., 2] < 135)).mean()
        if skin > 0.3 and (y + h / 2) / img.height < 0.8:   # real skin, not at the very bottom
            ok.append((x, y, w, h))
    return sorted(ok, key=lambda r: -r[2] * r[3])


def people(img: Image.Image):
    s = 640 / img.width
    a = cv2.cvtColor(np.asarray(img.convert("RGB").resize((640, int(img.height * s)))), cv2.COLOR_RGB2BGR)
    rects, w = _hog.detectMultiScale(a, winStride=(8, 8), padding=(8, 8), scale=1.05)
    out = [(r / s, float(wi)) for r, wi in zip(rects, np.ravel(w)) if wi > 0.5]
    return sorted(out, key=lambda t: -t[0][2] * t[0][3] * t[1])


def saliency_point(img: Image.Image):
    a = cv2.cvtColor(np.asarray(img.convert("RGB").resize((256, int(256 * img.height / img.width)))), cv2.COLOR_RGB2GRAY)
    a = np.float32(a)
    F = np.fft.fft2(a)
    logA = np.log(np.abs(F) + 1e-9)
    res = logA - cv2.blur(logA, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(res + 1j * np.angle(F)))) ** 2
    sal = cv2.GaussianBlur(sal, (0, 0), 10)
    h, w = sal.shape
    yy, xx = np.mgrid[0:h, 0:w]
    sal *= np.exp(-(((xx - w / 2) / (w * 0.45)) ** 2 + ((yy - h / 2) / (h * 0.6)) ** 2))  # centre bias
    y, x = np.unravel_index(np.argmax(sal), sal.shape)
    return x / sal.shape[1], y / sal.shape[0]


def focus_point(img: Image.Image):
    f = faces(img)
    if f:
        x, y, w, h = f[0]
        return (x + w / 2) / img.width, (y + h / 2) / img.height, "face"
    p = people(img)
    if p:
        x, y, w, h = p[0][0]
        return (x + w / 2) / img.width, (y + h * 0.3) / img.height, "person"
    sx, sy = saliency_point(img)
    return sx, sy, "saliency"


def crop_to(img: Image.Image, aspect: float, focus=None, headroom=0.33):
    """aspect = w/h (9/16 for Reels). Keeps max height, places focus on upper third if face."""
    fx, fy, kind = focus or focus_point(img)
    W, H = img.size
    if W / H > aspect:
        cw, ch = int(H * aspect), H
    else:
        cw, ch = W, int(W / aspect)
    x0 = int(np.clip(fx * W - cw / 2, 0, W - cw))
    y0 = int(np.clip(fy * H - ch * (headroom if kind in ("face", "person") else 0.5), 0, H - ch))
    return img.crop((x0, y0, x0 + cw, y0 + ch))


def blur_fit(img: Image.Image, size=(1080, 1920), blur=40, dim=0.55, scale=1.0):
    """Safe vertical: whole 16:9 frame in the middle, blurred+darkened copy fills the rest.
    Never cuts the subject — use when focus_point() is unsure (kind == 'saliency')."""
    from PIL import ImageFilter, ImageEnhance
    W, H = size
    bg = crop_to(img, W / H, (0.5, 0.5, "centre")).resize(size, Image.LANCZOS)
    bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(blur))).enhance(dim)
    fw = int(W * scale)
    fg = img.resize((fw, int(img.height * fw / img.width)), Image.LANCZOS)
    bg.paste(fg, ((W - fw) // 2, (H - fg.height) // 2))
    return bg


def vertical(img: Image.Image, size=(1080, 1920), focus=None):
    """Auto: confident subject (face/person or manual focus) -> smart crop; otherwise blur_fit."""
    fp = focus or focus_point(img)
    if fp[2] in ("face", "person", "manual"):
        return crop_to(img, size[0] / size[1], fp).resize(size, Image.LANCZOS)
    return blur_fit(img, size)
