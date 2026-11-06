#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сборка самодостаточного single-file HTML каталога «В ОКОПЕ» (вариант 2).

Из catalog/variant-2.html собирается ОДИН файл, в который встроены:
  • все CSS (catalog.css, theme-quiet.css, light.css, motion.css) — инлайн <style>;
  • JS (config.js, data.js, app-light.js, motion.js) — инлайн <script>;
  • шрифты @font-face (TTF) — data:font/ttf;base64;
  • все изображения: 100 фото товаров, hero, логотип, favicon, QR, no-photo — data: URI;
  • фото товаров перекодируются: resize max 900 px, WebP q75 (hero — PNG 1200 px).

Правки для single-file:
  • удалён переключатель «Вариант 1/2» (в одиночном файле не нужен);
  • ссылки на PDF в подвале заменены текстом «PDF-каталог — отдельным файлом»;
  • не остаётся ни одной ссылки на локальные папки assets/ и redesign/.

Запуск (воспроизводимая сборка):
  python catalog/_tools/build_singlefile.py
  python catalog/_tools/build_singlefile.py --out "D:\\...\\catalog.html"
  python catalog/_tools/build_singlefile.py --max-side 900 --quality 75 --quiet

Зависимости: Pillow (PIL). Результат: kilowatt/dist/Каталог_Киловатт_2026_В_ОКОПЕ.html
(+ kilowatt/dist/_build.json — манифест сборки: хэши, размеры, количество ресурсов).
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from PIL import Image
except Exception:  # pragma: no cover
    print("FATAL: нужен Pillow (pip install pillow)", file=sys.stderr)
    raise

HERE = Path(__file__).resolve().parent          # catalog/_tools
CATALOG = HERE.parent                           # catalog
KILOWATT = CATALOG.parent                       # kilowatt
SRC_HTML = CATALOG / "variant-2.html"
DIST = KILOWATT / "dist"
OUT_NAME = "Каталог_Киловатт_2026_В_ОКОПЕ.html"

# ассеты, которые обязаны попасть в single-file (для отчёта/самопроверки)
REQUIRED_IMAGES = [
    "assets/img/hero-k12m.png",
    "assets/img/brand/logo_w_emblem.png",
    "assets/img/brand/favicon.png",
    "assets/img/qr-phone.svg",
    "assets/img/no-photo.svg",
]

ASSET_RE = re.compile(r"assets/img/[A-Za-z0-9_./\-]+")
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")
SCRIPT_SRC_RE = re.compile(r"<script\b[^>]*\bsrc=\"([^\"]+)\"[^>]*>\s*</script>")
STYLE_LINK_RE = re.compile(r"<link\b[^>]*\brel=\"stylesheet\"[^>]*\bhref=\"([^\"]+)\"[^>]*>")
VARIANT_SWITCH_RE = re.compile(r"<a\b[^>]*data-variant-switch[^>]*>.*?</a>", re.S)
PDF_BLOCK_RE = re.compile(r'<span class="footer__pdf">.*?</span>', re.S)
BODY_ALT_RE = re.compile(r'\s+data-alt="[^"]*"')

MIME = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def to_data_uri(path, mime=None):
    m = mime or MIME.get(path.suffix.lower(), "application/octet-stream")
    data = path.read_bytes()
    return "data:%s;base64,%s" % (m, base64.b64encode(data).decode("ascii"))


class Optimizer:
    """Перекодирование изображений во временную папку + data: URI."""

    def __init__(self, tmpdir, max_side, quality, hero_max, passthrough=False):
        self.tmpdir = Path(tmpdir)
        self.max_side = max_side
        self.quality = quality
        self.hero_max = hero_max
        self.passthrough = passthrough
        self.stats = {"product": [0, 0], "hero": [0, 0], "png": [0, 0], "svg": [0, 0]}

    def _save_webp(self, im, key):
        out = self.tmpdir / (key.replace("/", "_") + ".webp")
        im.save(str(out), "WEBP", quality=self.quality, method=6)
        return out

    def product(self, src, rel):
        if self.passthrough:
            self.stats["product"][0] += 1
            self.stats["product"][1] += src.stat().st_size
            return to_data_uri(src, "image/webp")
        im = Image.open(src)
        if im.mode == "P":
            im = im.convert("RGBA" if "transparency" in im.info else "RGB")
        elif im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        im.thumbnail((self.max_side, self.max_side), Image.LANCZOS)
        out = self._save_webp(im, rel)
        self.stats["product"][0] += 1
        self.stats["product"][1] += out.stat().st_size
        return to_data_uri(out, "image/webp")

    def hero(self, src, rel):
        if self.passthrough:
            self.stats["hero"][0] += 1
            self.stats["hero"][1] += src.stat().st_size
            return to_data_uri(src, "image/png")
        im = Image.open(src)
        if im.mode == "P":
            im = im.convert("RGBA" if "transparency" in im.info else "RGB")
        im.thumbnail((self.hero_max, self.hero_max), Image.LANCZOS)
        out = self.tmpdir / (rel.replace("/", "_") + ".png")
        im.save(str(out), "PNG", optimize=True)
        self.stats["hero"][0] += 1
        self.stats["hero"][1] += out.stat().st_size
        return to_data_uri(out, "image/png")

    def png(self, src, rel):
        if self.passthrough:
            self.stats["png"][0] += 1
            self.stats["png"][1] += src.stat().st_size
            return to_data_uri(src, "image/png")
        im = Image.open(src)
        im.thumbnail((240, 240), Image.LANCZOS)
        out = self.tmpdir / (rel.replace("/", "_") + ".png")
        im.save(str(out), "PNG", optimize=True)
        self.stats["png"][0] += 1
        self.stats["png"][1] += out.stat().st_size
        return to_data_uri(out, "image/png")

    def svg(self, src):
        self.stats["svg"][0] += 1
        self.stats["svg"][1] += src.stat().st_size
        return to_data_uri(src, "image/svg+xml")

    def embed(self, rel):
        src = CATALOG / rel
        if not src.exists():
            raise FileNotFoundError("нет ассета: %s" % src)
        low = rel.lower()
        if low.endswith(".webp") and "/products/" in rel:
            return self.product(src, rel)
        if rel == "assets/img/hero-k12m.png":
            return self.hero(src, rel)
        if low.endswith(".svg"):
            return self.svg(src)
        if low.endswith(".png"):
            return self.png(src, rel)
        return to_data_uri(src)


def collect_styles(html):
    """Все <link rel="stylesheet"> по порядку, с содержимым."""
    styles = []
    for m in STYLE_LINK_RE.finditer(html):
        href = m.group(1)
        if href.startswith(("http://", "https://", "data:")):
            continue
        path = (CATALOG / href).resolve()
        if not path.exists():
            raise FileNotFoundError("нет CSS: %s" % path)
        styles.append((href, path))
    return styles


def collect_scripts(html):
    scripts = []
    for m in SCRIPT_SRC_RE.finditer(html):
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            continue
        path = (CATALOG / src).resolve()
        if not path.exists():
            raise FileNotFoundError("нет JS: %s" % path)
        scripts.append((src, path))
    return scripts


def inline_css_urls(css, css_path, embedder):
    """Заменить url(...) в CSS на data: URI (шрифты/картинки относительные)."""
    count = [0]

    def repl(m):
        raw = m.group(2).strip()
        if raw.startswith(("data:", "http://", "https://", "#")):
            return m.group(0)
        # внутренние url(...) из data:image/svg+xml (например, filter='url(%23n)')
        if "." not in raw or raw.startswith("%"):
            return m.group(0)
        target = (css_path.parent / raw).resolve()
        try:
            rel = str(target.relative_to(CATALOG)).replace("\\", "/")
        except ValueError:
            return m.group(0)
        if not target.exists():
            print("WARN: url() не найден: %s" % raw, file=sys.stderr)
            return m.group(0)
        uri = embedder(rel)
        count[0] += 1
        return 'url("%s")' % uri

    out = CSS_URL_RE.sub(repl, css)
    return out, count[0]


def replace_assets(text, mapping):
    if not mapping:
        return text
    pat = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
    return pat.sub(lambda m: mapping[m.group(0)], text)


def neutralize_inline(text):
    """Не дать комментариям-инструкциям (motion.js/motion.css) сломать inline-контекст.

    В шапке motion-кита есть строки вида <link rel="stylesheet" ...> и
    <script src="..."></script> — внутри инлайн-<script> последовательность
    </script> завершила бы скрипт. Слегка «разбираем» такие строки: смысл
    комментария сохраняется, HTML-парсер их больше не видит.
    """
    text = text.replace("</script", "<\\/script")
    text = text.replace("</style", "<\\/style")
    text = text.replace('rel="stylesheet"', "rel=stylesheet")
    text = text.replace("<script src=", "<script src =")
    return text


def build(args):
    t0 = time.time()
    if not SRC_HTML.exists():
        raise SystemExit("нет исходника: %s" % SRC_HTML)

    html_src = read_text(SRC_HTML)
    # --- single-file чистка ДО инлайна JS: только HTML-разметка ---
    html_src, n_switch = VARIANT_SWITCH_RE.subn("", html_src)
    html_src = BODY_ALT_RE.sub("", html_src)
    html_src, n_pdf = PDF_BLOCK_RE.subn('<span class="footer__pdf">PDF-каталог — отдельным файлом</span>', html_src)
    styles = collect_styles(html_src)
    scripts = collect_scripts(html_src)
    if len(styles) != 4:
        raise SystemExit("ожидалось 4 CSS, найдено %d" % len(styles))
    if len(scripts) != 4:
        raise SystemExit("ожидалось 4 JS, найдено %d" % len(scripts))

    css_texts = [(rel, read_text(path)) for rel, path in styles]
    js_texts = [(rel, read_text(path)) for rel, path in scripts]

    # --- какие img-ассеты вообще нужны (HTML + CSS + JS) ---
    blob = "\n".join([html_src] + [c for _, c in css_texts] + [j for _, j in js_texts])
    assets = set(ASSET_RE.findall(blob))
    for req in REQUIRED_IMAGES:
        assets.add(req)
    assets = sorted(assets)
    missing = [a for a in assets if not (CATALOG / a).exists()]
    if missing:
        raise SystemExit("битые пути в исходниках:\n  " + "\n  ".join(missing))

    tmpdir = tempfile.mkdtemp(prefix="vokope-single-")
    try:
        opt = Optimizer(tmpdir, args.max_side, args.quality, args.hero_max, passthrough=args.passthrough)

        # --- картинки (кроме шрифтов) ---
        mapping = {}
        for rel in assets:
            mapping[rel] = opt.embed(rel)

        # --- CSS: инлайн шрифтов (@font-face) + общая замена картинок ---
        css_inlined = []
        font_count = 0
        for rel, css in css_texts:
            css2, n = inline_css_urls(css, CATALOG / rel, opt.embed)
            font_count += n
            css2 = replace_assets(css2, mapping)
            css_inlined.append((rel, neutralize_inline(css2)))

        # --- JS: замена путей фото на data: URI ---
        js_inlined = [(rel, neutralize_inline(replace_assets(js, mapping))) for rel, js in js_texts]

        for _, css in css_inlined:
            if "</style" in css.lower():
                raise SystemExit("CSS содержит </style> — инлайн невозможен")
        for _, js in js_inlined:
            if "</script" in js.lower():
                raise SystemExit("JS содержит </script> — инлайн невозможен")

        # --- HTML: инлайн CSS/JS, чистка single-file ---
        html = html_src
        css_by_src = dict(css_inlined)

        def style_repl(m):
            rel = m.group(1)
            if rel not in css_by_src:
                return m.group(0)
            return "<style>\n/* inlined CSS: %s */\n%s\n</style>" % (Path(rel).name, css_by_src[rel])

        html = STYLE_LINK_RE.sub(style_repl, html)
        if html.count("<style>") != 4:
            raise SystemExit("не удалось встроить <style> (найдено %d)" % html.count("<style>"))

        js_by_src = dict(js_inlined)

        def script_repl(m):
            src = m.group(1)
            if src not in js_by_src:
                return m.group(0)
            return "<script>\n/* inlined JS: %s */\n%s\n</script>" % (Path(src).name, js_by_src[src])

        html = SCRIPT_SRC_RE.sub(script_repl, html)
        if html.count("<script>") != 4:
            raise SystemExit("не удалось встроить <script> (найдено %d)" % html.count("<script>"))

        # картинки в HTML
        html = replace_assets(html, mapping)
        # комментарий-маркер сборки (детерминированный, без даты)
        marker = ("<!-- Единый файл каталога «В ОКОПЕ» (вариант 2): CSS, JS, шрифты и изображения\n"
                  "     встроены внутрь. Сборка: catalog/_tools/build_singlefile.py — без папок, работает офлайн. -->\n")
        html = html.replace("<head>", "<head>\n" + marker, 1)

        # абсолютная чистота от локальных папок (даже в комментариях CSS/JS)
        leftovers = sorted(set(re.findall(r"(?:assets|redesign)/[A-Za-z0-9_./\-]*", html)))
        if leftovers:
            # ссылок быть не должно даже в комментариях: убираем слэш-путь,
            # слово остаётся читаемым («catalog/assets js/app.js»)
            html = html.replace("assets/", "assets ").replace("redesign/", "redesign ")
            leftovers = sorted(set(re.findall(r"(?:assets|redesign)/[A-Za-z0-9_./\-]*", html)))
            if leftovers:
                raise SystemExit("в файле остались локальные пути: %s" % leftovers[:5])

        out_dir = Path(args.out).resolve().parent if args.out else DIST
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = Path(args.out).resolve() if args.out else (DIST / OUT_NAME)
        out_path.write_text(html, encoding="utf-8", newline="\n")

        # --- финальные самопроверки ---
        final = out_path.read_text(encoding="utf-8")
        checks = {
            "no_assets_ref": ("assets/" not in final),
            "no_redesign_ref": ("redesign/" not in final),
            "no_stylesheet_link": ('rel="stylesheet"' not in final),
            "no_script_src": ("<script src=" not in final),
            "no_variant_switch_element": ('class="cart-btn variant-switch"' not in final),
            "no_pdf_links": ("href=\"pdf/" not in final and "catalog-v1-field.pdf" not in final),
            "no_variant2_href": ("variant-2.html" not in final),
            "pdf_footer_text": ("PDF-каталог — отдельным файлом" in final),
        }
        bad = [k for k, ok in checks.items() if not ok]
        if bad:
            raise SystemExit("проверка single-file не прошла: %s" % ", ".join(bad))

        size = out_path.stat().st_size
        image_count = len(mapping)
        data_uri_count = final.count("data:")
        manifest = {
            "built_by": "catalog/_tools/build_singlefile.py",
            "source": "catalog/variant-2.html",
            "output": out_path.name,
            "size_bytes": size,
            "size_mb": round(size / 1024.0 / 1024.0, 2),
            "sha256": sha256_file(out_path),
            "params": {
                "max_side": args.max_side,
                "quality": args.quality,
                "hero_max": args.hero_max,
            },
            "sources_sha256": {
                "catalog/variant-2.html": sha256_file(SRC_HTML),
                "assets/css/light.css": sha256_file(CATALOG / "assets/css/light.css"),
                "assets/js/app-light.js": sha256_file(CATALOG / "assets/js/app-light.js"),
            },
            "inline": {
                "styles": [rel for rel, _ in css_inlined],
                "scripts": [rel for rel, _ in js_inlined],
                "fonts": font_count,
                "images": image_count,
                "product_images": opt.stats["product"][0],
                "hero_images": opt.stats["hero"][0],
                "png_images": opt.stats["png"][0],
                "svg_images": opt.stats["svg"][0],
                "data_uri_total": data_uri_count,
            },
            "bytes": {
                "product_images": opt.stats["product"][1],
                "hero_images": opt.stats["hero"][1],
                "png_images": opt.stats["png"][1],
                "svg_images": opt.stats["svg"][1],
            },
            "checks": checks,
            "removed": {"variant_switch": n_switch},
            "pdf_footer_replaced": n_pdf,
        }
        (out_dir / "_build.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )

        if not args.quiet:
            print("=" * 78)
            print("SINGLE-FILE каталог собран за %.1f c" % (time.time() - t0))
            print("  файл:        %s" % out_path)
            print("  размер:      %.2f МБ (%d байт)" % (size / 1024.0 / 1024.0, size))
            print("  sha256:      %s" % manifest["sha256"][:16] + "…")
            print("  встроено:    CSS %d · JS %d · шрифты %d · картинки %d · data: URI %d"
                  % (len(css_inlined), len(js_inlined), font_count, image_count, data_uri_count))
            print("  картинки:    товары %d (%.2f МБ) · hero %d · png %d · svg %d"
                  % (opt.stats["product"][0], opt.stats["product"][1] / 1024.0 / 1024.0,
                     opt.stats["hero"][0], opt.stats["png"][0], opt.stats["svg"][0]))
            print("  проверки:    " + ", ".join("%s=%s" % (k, "OK" if v else "FAIL") for k, v in checks.items()))
            print("  манифест:    %s" % (out_dir / "_build.json"))
            print("=" * 78)
        return manifest
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Сборка single-file HTML каталога «В ОКОПЕ» (вариант 2)")
    ap.add_argument("--out", default="", help="путь к итоговому HTML (по умолчанию kilowatt/dist/%s)" % OUT_NAME)
    ap.add_argument("--max-side", type=int, default=900, help="макс. сторона фото товара, px (по умолчанию 900)")
    ap.add_argument("--quality", type=int, default=75, help="качество WebP (по умолчанию 75)")
    ap.add_argument("--hero-max", type=int, default=1200, help="макс. сторона hero PNG, px (по умолчанию 1200)")
    ap.add_argument("--passthrough", action="store_true", help="не перекодировать фото, встраивать готовые WebP как есть (быстро)")
    ap.add_argument("--quiet", action="store_true", help="только ошибки")
    args = ap.parse_args()
    build(args)


if __name__ == "__main__":
    main()
