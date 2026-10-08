#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мост для поставщика front-ts.ru (Фронт-ТС).

Песочница агента в интернет к front-ts.ru не ходит, поэтому страницы и картинки
тянет GitHub Actions (.github/workflows/frontts-fetch.yml) и публикует результат
в ветку `frontts-data`. Забрать: bash tools/frontts_pull.sh

Режимы (plan.json → "mode"):
  discovery — обход сайта «на разведку»: главная, robots, sitemap (+вложенные),
              до N страниц каталога; пишет data/discovery.json и сырые страницы.
  products  — разбор списка URL из data/urls.txt: карточки товаров + фото.
              Пишет data/products.json, data/summary.txt, photos/<slug>/NN.jpg

Запуск: FRONTTS_MODE=discovery python3 suppliers/frontts/crawl.py
"""
import gzip
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
PHOTOS = os.path.join(HERE, "photos")

PLAN_PATH = os.path.join(HERE, "plan.json")
PLAN = json.load(open(PLAN_PATH, encoding="utf-8")) if os.path.exists(PLAN_PATH) else {}
HOST = PLAN.get("host", "front-ts.ru")
MODE = os.environ.get("FRONTTS_MODE") or PLAN.get("mode") or "discovery"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

RAW_CAP = int(PLAN.get("raw_cap_bytes", 40_000_000))
PAGE_CAP = int(PLAN.get("page_cap_bytes", 4_000_000))
IMG_CAP = int(PLAN.get("image_cap_bytes", 2_500_000))
IMGS_PER_PRODUCT = int(PLAN.get("images_per_product", 8))
SLEEP = float(PLAN.get("sleep", 0.4))
STATS = {"ok": 0, "fail": 0, "bytes": 0, "pages": 0, "images": 0}


def log(*a):
    print(*a, flush=True)


def fetch(url, binary=False, referer=None):
    """Скачать URL. Возвращает (bytes|str, content_type) или (None, err)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        **({"Referer": referer} if referer else {}),
    })
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read(PAGE_CAP * 4)
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    raw = gzip.decompress(raw)
                elif "deflate" in enc:
                    try:
                        raw = zlib.decompress(raw)
                    except zlib.error:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                ctype = r.headers.get("Content-Type", "")
                STATS["ok"] += 1
                STATS["bytes"] += len(raw)
                return (raw if binary else raw.decode("utf-8", "replace")), ctype
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                STATS["fail"] += 1
                return None, f"{type(e).__name__}: {e}"
            time.sleep(2)
    return None, "unreachable"


def norm(url, base=None):
    u = urllib.parse.urljoin(base or f"https://{HOST}/", url)
    u, _ = urllib.parse.urldefrag(u)
    return u


def same_host(u):
    return urllib.parse.urlparse(u).netloc.lower().endswith(HOST)


def links(html, base):
    """Ссылки и картинки со страницы."""
    hrefs = [norm(m, base) for m in re.findall(r'''href=["']([^"'#]+)["']''', html, re.I)]
    srcs = [norm(m, base) for m in re.findall(r'''src=["']([^"'#]+)["']''', html, re.I)]
    lazy = [norm(m, base) for m in re.findall(r'''data-(?:src|original|lazy-src|bg)=["']([^"'#]+)["']''', html, re.I)]
    return [u for u in hrefs if same_host(u)], [u for u in srcs + lazy if same_host(u)]


def slugify(url):
    p = urllib.parse.urlparse(url).path.strip("/")
    p = re.sub(r"\.(html?|php|aspx?)$", "", p, flags=re.I)
    s = re.sub(r"[^a-z0-9а-яё]+", "-", p.lower().replace("/", "-")).strip("-")
    if not s:
        s = hashlib.md5(url.encode()).hexdigest()[:10]
    return s[:110] or "index"


def save_raw(html, url):
    if STATS["bytes"] > RAW_CAP:
        return None
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, slugify(url) + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- {url} -->\n{html}")
    return path


def is_page(u):
    path = urllib.parse.urlparse(u).path
    if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|css|js|ico|woff2?|ttf|zip|pdf|mp4|xml|txt)$", path, re.I):
        return False
    return True


# ---------------------------------------------------------------- discovery
def sitemap_urls(xml, base):
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml, re.I)
    return [norm(x, base) for x in locs]


def parse_robots(txt):
    sm = [norm(l.split(":", 1)[1].strip()) for l in txt.splitlines()
          if l.lower().startswith("sitemap:")]
    dis = [l.split(":", 1)[1].strip() for l in txt.splitlines()
           if l.lower().startswith("disallow:") and len(l.split(":", 1)[1].strip()) > 1]
    return sm, dis


def discovery():
    os.makedirs(DATA, exist_ok=True)
    report = {"host": HOST, "mode": "discovery", "fetched": {}, "sitemaps": {}, "patterns": {},
              "samples": {}, "robots_disallow": [], "listing_pages": [], "notes": []}

    # 1) главная
    home, ct = fetch(f"https://{HOST}/")
    report["fetched"]["home"] = {"bytes": len(home or ""), "ctype": ct}
    if home:
        save_raw(home, f"https://{HOST}/")

    # 2) robots
    robots, _ = fetch(f"https://{HOST}/robots.txt")
    sm_urls, dis = parse_robots(robots or "")
    report["robots_disallow"] = dis[:40]
    report["fetched"]["robots"] = {"bytes": len(robots or ""), "sitemaps": sm_urls}
    if robots:
        os.makedirs(DATA, exist_ok=True)
        open(os.path.join(DATA, "robots.txt"), "w", encoding="utf-8").write(robots)

    # 3) sitemap'ы (с вложенными)
    queue = list(dict.fromkeys(sm_urls + [f"https://{HOST}/sitemap.xml", f"https://{HOST}/sitemap_index.xml"]))
    seen_sm, product_urls, page_urls = set(), set(), set()
    while queue:
        sm = queue.pop(0)
        if sm in seen_sm:
            continue
        seen_sm.add(sm)
        xml, ct = fetch(sm)
        if not xml or "<" not in xml[:200]:
            continue
        urls = sitemap_urls(xml, sm)
        kids = [u for u in urls if re.search(r"sitemap.*\.xml", u, re.I)]
        report["sitemaps"][sm] = {"total": len(urls), "children": len(kids)}
        queue.extend(kids)
        for u in urls:
            (product_urls if looks_product(u) else page_urls).add(u)
        if STATS["pages"] < 5:
            save_raw(xml, sm)
        log(f"  sitemap {sm}: {len(urls)} ссылок, детей {len(kids)}")

    # 4) обходим страницы каталога (не товары) — ищем разделы и структуру
    base_pages = [u for u in (page_urls | {norm(u) for u in (links(home or "", f"https://{HOST}/")[0])})
                  if is_page(u)]
    listing = [u for u in base_pages if re.search(r"(catalog|katalog|shop|tovar|product|goods|razdel|category)", u, re.I)]
    listing = sorted(set(listing))[: int(PLAN.get("listing_limit", 25))]
    report["listing_pages"] = listing
    for u in listing:
        html, ct = fetch(u, referer=f"https://{HOST}/")
        if not html:
            log(f"  ✗ {u}")
            continue
        save_raw(html, u)
        hrefs, imgs = links(html, u)
        for h in hrefs:
            (product_urls if looks_product(h) else page_urls).add(h)
        log(f"  ✓ {u} → {len(hrefs)} ссылок")
        time.sleep(SLEEP)

    # 5) сводка по шаблонам URL
    def pattern(u):
        p = urllib.parse.urlparse(u).path.strip("/")
        parts = p.split("/")
        seg = parts[0] if parts and parts[0] else "(корень)"
        if len(parts) > 1:
            seg += "/" + parts[1][:24]
        return seg

    for u in sorted(product_urls | page_urls):
        pat = pattern(u)
        report["patterns"][pat] = report["patterns"].get(pat, 0) + 1
        report["samples"].setdefault(pat, []).append(u)
    for k in report["samples"]:
        report["samples"][k] = sorted(set(report["samples"][k]))[:6]

    report["found"] = {"product_like": len(product_urls), "other_pages": len(page_urls)}
    report["product_urls_sample"] = sorted(product_urls)[:40]
    report["stats"] = STATS
    os.makedirs(DATA, exist_ok=True)
    json.dump(report, open(os.path.join(DATA, "discovery.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(DATA, "urls.txt"), "w", encoding="utf-8").write(
        "\n".join(sorted(product_urls)) + "\n")
    log(f"\nразведка: товаров «на вид» {len(product_urls)}, других страниц {len(page_urls)}, "
        f"скачано {STATS['ok']} страниц, сбоев {STATS['fail']}")
    log("топ шаблонов:")
    for k, v in sorted(report["patterns"].items(), key=lambda kv: -kv[1])[:15]:
        log(f"   {v:>5}  {k}")


def looks_product(u):
    p = urllib.parse.urlparse(u).path.lower()
    return bool(re.search(r"/(product|tovar|goods|item|p)/|/(catalog|shop)/.*\d", p)) or \
        bool(re.search(r"\d{3,}", p)) and not re.search(r"/(page|tag|category|razdel)/", p)


# ----------------------------------------------------------------- products
def jsonld_products(html):
    out = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@graph"):
                items.extend(it["@graph"])
            if isinstance(it, dict) and str(it.get("@type", "")).lower() in (
                    "product", "individualproduct", "offer", "itempage"):
                out.append(it)
    return out


def meta(html, keys):
    """meta по name/property; keys — список имён в порядке приоритета."""
    found = {}
    for m in re.finditer(r'<meta[^>]+>', html, re.I):
        tag = m.group(0)
        name = re.search(r'(?:name|property|itemprop)=["\']([^"\']+)["\']', tag, re.I)
        cont = re.search(r'content=["\']([^"\']*)["\']', tag, re.I)
        if name and cont:
            k = name.group(1).lower()
            if k in keys and k not in found:
                found[k] = cont.group(1).strip()
    return found


def strip_tags(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|tr|h\d)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as _h
    t = _h.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def parse_price(html):
    pats = [r'itemprop=["\']price["\'][^>]*content=["\']([\d\s\u00a0.,]+)',
            r'content=["\']([\d\s\u00a0.,]+)["\'][^>]*itemprop=["\']price["\']',
            r'"price"\s*:\s*"?([\d\s.,]+)',
            r'([\d]{3,7}(?:[.,]\d{2})?)\s*(?:₽|руб)']
    for p in pats:
        m = re.search(p, html, re.I)
        if m:
            v = re.sub(r"[^\d.,]", "", m.group(1)).replace(",", ".")
            try:
                return float(v)
            except ValueError:
                pass
    return None


def parse_product(html, url):
    ld = jsonld_products(html)
    m = meta(html, {"og:title", "og:description", "og:image", "description", "keywords",
                    "product:price:amount", "og:price:amount"})
    name = (ld[0].get("name") if ld else None) or m.get("og:title") or \
        (re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I) or [None, ""])[1]
    name = strip_tags(name or "").split("|")[0].strip()
    brand = ""
    if ld:
        b = ld[0].get("brand")
        brand = b if isinstance(b, str) else (b or {}).get("name", "") if isinstance(b, dict) else ""
    descr = (ld[0].get("description") if ld else "") or m.get("og:description") or m.get("description") or ""
    descr = strip_tags(descr)
    price = None
    if ld:
        off = ld[0].get("offers") or {}
        if isinstance(off, list):
            off = off[0] if off else {}
        if isinstance(off, dict):
            p = off.get("price") or off.get("lowPrice")
            try:
                price = float(str(p).replace(",", ".").replace(" ", ""))
            except (TypeError, ValueError):
                price = None
    if price is None:
        price = parse_price(html)
    sku = ""
    if ld:
        sku = str(ld[0].get("sku") or ld[0].get("mpn") or "")
    imgs = []
    if ld and ld[0].get("image"):
        im = ld[0]["image"]
        imgs += im if isinstance(im, list) else [im]
    if m.get("og:image"):
        imgs.insert(0, m["og:image"])
    hrefs, srcs = links(html, url)
    imgs += [s for s in srcs if re.search(r"(upload|product|tovar|goods|catalog|images?)/.*\.(jpe?g|png|webp)", s, re.I)]
    clean, seen = [], set()
    for i in imgs:
        i = norm(i, url)
        if i in seen or re.search(r"(logo|icon|sprite|placeholder|no-photo|badge)", i, re.I):
            continue
        seen.add(i)
        clean.append(i)
    # текст с страницы (если описания мало) — код встроенный блок «Описание»
    body = strip_tags(html)
    extra = ""
    mm = re.search(r"(Описание|Характеристики)[:\s]*(.{80,3000})", body, re.S)
    if mm and len(descr) < 200:
        extra = mm.group(2).strip()
    return {"url": url, "name": name, "brand": brand, "sku": sku, "price": price,
            "descr_short": descr, "descr_extra": extra, "images": clean[:IMGS_PER_PRODUCT],
            "jsonld": bool(ld)}


def download_image(url, path, referer):
    raw, ct = fetch(url, binary=True, referer=referer)
    if not raw or len(raw) > IMG_CAP:
        return None
    with open(path, "wb") as f:
        f.write(raw)
    STATS["images"] += 1
    return path


def products():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(PHOTOS, exist_ok=True)
    urls_file = os.path.join(DATA, "urls.txt")
    if not os.path.exists(urls_file):
        log("!! нет suppliers/frontts/data/urls.txt")
        return
    urls = [u.strip() for u in open(urls_file, encoding="utf-8") if u.strip().startswith("http")]
    limit = int(os.environ.get("FRONTTS_LIMIT", PLAN.get("limit", 0)) or 0)
    if limit:
        urls = urls[:limit]
    log(f"разбираю карточек: {len(urls)}")
    out, fails = [], []
    for n, u in enumerate(urls, 1):
        html, ct = fetch(u, referer=f"https://{HOST}/")
        if not html:
            fails.append({"url": u, "err": ct})
            continue
        if n <= 3:
            save_raw(html, u)
        it = parse_product(html, u)
        slug = slugify(u)
        d = os.path.join(PHOTOS, slug)
        saved = []
        for i, img in enumerate(it["images"], 1):
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, f"{i}.jpg")
            if download_image(img, p, u):
                saved.append(f"{slug}/{i}.jpg")
        it["slug"] = slug
        it["photos"] = saved
        out.append(it)
        if n % 10 == 0 or n == len(urls):
            log(f"  {n}/{len(urls)}  {it['name'][:50]:52} фото {len(saved)}")
        time.sleep(SLEEP)
    json.dump(out, open(os.path.join(DATA, "products.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(fails, open(os.path.join(DATA, "fails.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(f"front-ts.ru: разобрано {len(out)} карточек, сбоев {len(fails)}, "
                f"фото {sum(len(x['photos']) for x in out)}\n")
        f.write(f"без описания: {sum(1 for x in out if not x['descr_short'] and not x['descr_extra'])}\n")
        f.write(f"без цены: {sum(1 for x in out if not x['price'])}\n")
        f.write(f"без фото: {sum(1 for x in out if not x['photos'])}\n")
    log(open(os.path.join(DATA, "summary.txt"), encoding="utf-8").read())


if __name__ == "__main__":
    log(f"=== front-ts.ru · режим {MODE} ===")
    if MODE == "products":
        products()
    else:
        discovery()
    log(f"готово: скачано {STATS['ok']} (сбоев {STATS['fail']}), {STATS['bytes'] / 1e6:.1f} МБ, "
        f"фото {STATS['images']}")
