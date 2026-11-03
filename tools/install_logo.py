#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УСТАНОВКА ЛОГОТИПА «В ОКОПЕ» — из любого файла в готовые ассеты карточек.

  python3 tools/install_logo.py "<путь к файлу>"                # авто: герб в media/logo.png + полный в media/logo_full.png
  python3 tools/install_logo.py "<файл>" --variant emblem       # только герб (квадратный бейдж в шапке карточек)
  python3 tools/install_logo.py "<файл>" --variant full         # только полный логотип с надписью
  python3 tools/install_logo.py "<файл>" --no-transparent       # не убирать фон

Что делает:
  • обрезает однотонные поля;
  • белый фон делает прозрачным (для карточек на крафт-бумаге);
  • отделяет герб от надписи «В ОКОПЕ» по широкой пустой полосе и делает квадратный бейдж;
  • если фон тёмный (белый логотип на чёрном) — автоматически инвертирует под светлые карточки;
  • печатает, что получилось, и проверяет пригодность для шапки карточки.
"""
import argparse
import os
import sys

from PIL import Image, ImageChops, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "media")


def bg_color(img):
    """Цвет фона — по четырём углам."""
    w, h = img.size
    corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)), img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    if all(isinstance(c, int) for c in corners):
        return (sum(corners) // 4,) * 3
    return tuple(sum(c[i] for c in corners) // 4 for i in range(3))


def autocrop(img, bg, tol=12):
    """Обрезаем однотонные поля."""
    diff = ImageChops.difference(img.convert("RGB"), Image.new("RGB", img.size, bg))
    gray = diff.convert("L").point(lambda v: 255 if v > tol else 0)
    bbox = gray.getbbox()
    return img.crop(bbox) if bbox else img


def split_emblem(img):
    """Находим самую широкую пустую горизонтальную полосу ниже середины — это разрыв
    между гербом и надписью. Возвращаем (верх, низ)."""
    w, h = img.size
    alpha = img.getchannel("A") if "A" in img.getbands() else None
    lums = []
    for y in range(h):
        row = [img.getpixel((x, y)) for x in range(0, w, max(1, w // 160))]
        if alpha:
            ink = sum(1 for p in row if p[3] > 40)
        else:
            ink = sum(1 for p in row if sum(p[:3]) < 3 * 230)
        lums.append(ink)
    # ищем пустые строки в диапазоне 20–92% высоты (эмблема сверху, надпись снизу)
    lo, hi = int(h * 0.20), int(h * 0.92)
    best, cur = None, None
    for y in range(lo, hi):
        if lums[y] == 0:
            cur = (cur[0], y) if cur else (y, y)
            if best is None or (cur[1] - cur[0]) > (best[1] - best[0]):
                best = cur
        else:
            cur = None
    if not best or (best[1] - best[0]) < 3:
        return img, None
    cut = (best[0] + best[1]) // 2
    return img.crop((0, 0, w, cut)), img.crop((0, cut, w, h))


def square(img, size=900, pad_ratio=0.04):
    """Квадрат с полями, по центру."""
    img = autocrop(img, (0, 0, 0), tol=8) if "A" in img.getbands() else img
    w, h = img.size
    side = int(max(w, h) * (1 + pad_ratio * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img if "A" in img.getbands() else None)
    return canvas.resize((size, size), Image.LANCZOS)


def to_transparent(img, bg):
    """Белый фон -> прозрачный. Работает для однозначных логотипов «тёмное на светлом»."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # «чернильность»: насколько пиксель темнее фона
            ink = max(0, min(255, 255 - (r + g + b) // 3)) if sum(bg) > 3 * 128 else (r + g + b) // 3
            px[x, y] = (r, g, b, max(ink, 0) if a else ink)
    return img


def main(argv=None):
    ap = argparse.ArgumentParser(description="Установка логотипа «В ОКОПЕ»")
    ap.add_argument("source")
    ap.add_argument("--variant", choices=["auto", "emblem", "full"], default="auto")
    ap.add_argument("--no-transparent", action="store_true")
    ap.add_argument("--size", type=int, default=900)
    args = ap.parse_args(argv)

    if not os.path.exists(args.source):
        raise SystemExit(f"Файла нет: {args.source}")
    os.makedirs(MEDIA, exist_ok=True)

    src = Image.open(args.source)
    src = ImageOps.exif_transpose(src)
    has_alpha = src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info)
    img = src.convert("RGBA") if has_alpha else src.convert("RGB")

    bg = bg_color(img)
    img = autocrop(img, bg)
    print(f"исходник: {args.source}  ({src.size[0]}×{src.size[1]}, режим {src.mode})")
    print(f"фон: {bg}, после обрезки полей: {img.size[0]}×{img.size[1]}")

    # белый логотип на тёмном фоне -> инвертируем под светлые карточки
    if not has_alpha and sum(bg) < 3 * 120:
        img = ImageOps.invert(img.convert("RGB")).convert("RGBA")
        bg = (255, 255, 255)
        print("фон был тёмный — инвертировал (карточки светлые)")

    if not args.no_transparent and not has_alpha:
        img = to_transparent(img, bg)

    emblem, signature = img, None
    if args.variant in ("auto", "emblem"):
        emblem, signature = split_emblem(img)
        if signature is None:
            print("⚠ не нашёл пустой полосы между гербом и надписью — беру всё изображение целиком")
    if args.variant == "emblem" and signature is not None:
        pass  # уже отрезали

    written = []
    if args.variant in ("auto", "emblem"):
        sq = square(emblem, args.size)
        out = os.path.join(MEDIA, "logo.png")
        sq.save(out)
        written.append((out, sq.size))
    if args.variant in ("full",) or (args.variant == "auto" and signature is not None):
        full = img.copy()
        full.thumbnail((args.size * 2, args.size * 2), Image.LANCZOS)
        out = os.path.join(MEDIA, "logo_full.png")
        full.save(out)
        written.append((out, full.size))

    for path, size in written:
        print(f"✓ {os.path.relpath(path, ROOT)}  {size[0]}×{size[1]}")
    print("\nПроверить на карточке:")
    print('  PYTHONPATH=$PWD/vendor python3 media/blank/from_catalog.py --code 00477 --price 1500 --out /tmp/logo_check.jpg')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
