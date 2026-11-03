#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разбор карточки товара front-ts.ru (WordPress + кастомная тема Front-TS).

Структура страницы (проверено на живых карточках):
  <h1 class="bigHeader mediumHeader">Название</h1>
  <div class="inStock">В наличии</div>
  <div class="price">9900&nbsp;<span class="rubSign">руб.</span></div>
  <div class="information"> <h2>Описание товара</h2> …текст… </div>
  галерея: <img src="…/wp-content/uploads/2016/07/1_Adapter-1024x683.jpg">
           (суффикс -WxH убираем, чтобы взять оригинал)

Модуль самодостаточный: только стандартная библиотека.
"""
import re
import json
import html as H

SIZE_SUFFIX = re.compile(r"-\d+x\d+(?=\.\w+$)")
UPLOADS = re.compile(
    r"""(?:src|href|data-src|data-large_image|data-original|content)=["']"""
    r"""([^"']+/wp-content/uploads/[^"']+\.(?:jpe?g|png|webp))["']""", re.I)


def html_to_text(frag):
    """HTML → текст: абзацы, списки, переносы."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", frag, flags=re.S | re.I)
    t = re.sub(r"<(br|hr)\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|h[1-6]|li|tr|section|td)\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<li[^>]*>", "• ", t, flags=re.I)
    t = re.sub(r"<td[^>]*>", " | ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = H.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    out, blank = [], 0
    for ln in (x.strip() for x in t.splitlines()):
        if not ln:
            blank += 1
            if blank == 1 and out:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def div_block(html, start_idx):
    """Содержимое div, начиная с позиции сразу после открывающего тега."""
    depth = 1
    for m in re.finditer(r"<(/?)div\b[^>]*>", html[start_idx:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[start_idx:start_idx + m.start()]
    return html[start_idx:]


def meta(html, keys):
    found = {}
    for m in re.finditer(r"<meta[^>]+>", html, re.I):
        tag = m.group(0)
        n = re.search(r'(?:name|property|itemprop)=["\']([^"\']+)["\']', tag, re.I)
        c = re.search(r'content=["\']([^"\']*)["\']', tag, re.I)
        if n and c and n.group(1).lower() in keys:
            found.setdefault(n.group(1).lower(), c.group(1).strip())
    return found


def jsonld(html):
    out = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:  # noqa: BLE001
            continue
        for it in (data if isinstance(data, list) else [data]):
            if isinstance(it, dict) and isinstance(it.get("@graph"), list):
                out += [x for x in it["@graph"] if isinstance(x, dict)]
            elif isinstance(it, dict):
                out.append(it)
    return out


def images_of(html, cut=None):
    """Фото товара: только /wp-content/uploads/ до блока описания, оригиналы."""
    frag = html[:cut] if cut and cut > 0 else html
    found, seen = [], set()
    for raw in UPLOADS.findall(frag):
        full = SIZE_SUFFIX.sub("", raw)
        if full.lower().endswith(".webp"):
            full = re.sub(r"\.webp$", ".jpg", full, flags=re.I)
        key = full.split("/uploads/")[-1].lower()
        if key in seen or re.search(r"(logo|icon|sprite|placeholder|no-photo|banner|sert|sertif)", key):
            continue
        seen.add(key)
        found.append(full)
    return found


def parse_product(html, url):
    it = {"url": url, "name": "", "price": None, "stock": None, "sku": "", "brand": "",
          "colors": [], "descr": "", "images": [], "has_jsonld": bool(jsonld(html))}

    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        it["name"] = html_to_text(m.group(1))
    if not it["name"]:
        it["name"] = re.sub(r"^\s*Купить\s+", "", meta(html, {"og:title"}).get("og:title", ""),
                            flags=re.I).strip()
    if not it["name"]:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        it["name"] = html_to_text(m.group(1) if m else "").split("|")[0].strip()

    m = re.search(r'class="price"[^>]*>\s*([\d\s\xa0.,]+)', html, re.I)
    if m:
        d = re.sub(r"\D", "", m.group(1))
        it["price"] = int(d) if d else None
    if it["price"] is None:
        m = re.search(r'"price"\s*:\s*"?([\d\s.,]+)', html)
        if m:
            try:
                it["price"] = int(float(re.sub(r"[^\d.]", "", m.group(1).replace(",", "."))))
            except ValueError:
                pass

    m = re.search(r'class="inStock"[^>]*>(.*?)</div>', html, re.S | re.I)
    if m:
        st = html_to_text(m.group(1)).lower()
        it["stock"] = True if "налич" in st else (False if ("нет" in st or "заказ" in st) else None)

    cut = html.find('class="information"')
    if cut > 0:
        m = re.search(r'class="information"[^>]*>', html[max(0, cut - 80):cut + 300])
        if m:
            inner = div_block(html, max(0, cut - 80) + m.end())
            inner = re.sub(r"<h2[^>]*>\s*Описание товара\s*</h2>", "", inner, flags=re.I)
            it["descr"] = html_to_text(inner)
    if len(it["descr"]) < 80:
        fallback = meta(html, {"og:description", "description"})
        it["descr"] = it["descr"] or html_to_text(fallback.get("og:description", "")) or \
            html_to_text(fallback.get("description", ""))

    m = re.search(r"артикул[:\s]*([A-Za-zА-Яа-я0-9\-]{2,20})", it["descr"], re.I)
    it["sku"] = m.group(1) if m else ""
    m = re.search(r"бренд[^A-Za-zА-Яа-я0-9]{0,3}([A-Za-zА-Яа-я0-9\- ]{2,30})", it["descr"], re.I)
    it["brand"] = m.group(1).strip(" ,.;") if m else ""
    m = re.search(r"цвет[а-яё]*[:\s]*([^.\n]{3,160})", it["descr"], re.I)
    if m:
        it["colors"] = [c.strip(" ,;") for c in re.split(r",|\sи\s", m.group(1)) if c.strip(" ,;")][:8]

    it["images"] = images_of(html, cut)
    return it


if __name__ == "__main__":
    import sys
    for path in sys.argv[1:]:
        page = open(path, encoding="utf-8").read()
        data = parse_product(page, path)
        print("=" * 90)
        print("название:", data["name"])
        print("цена:", data["price"], "| в наличии:", data["stock"], "| артикул:", data["sku"],
              "| бренд:", data["brand"])
        print("цвета:", data["colors"])
        print("фото:", len(data["images"]), [x.split("/")[-1] for x in data["images"]][:6])
        print("описание, знаков:", len(data["descr"]))
        print(re.sub(r"\s+", " ", data["descr"])[:300])
