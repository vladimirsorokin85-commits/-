#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Живой фетчер каталога поставщика (Дима, МойСклад B2B).

Запускается в двух местах:
  1) на GitHub Actions (.github/workflows/catalog-fetch.yml) — «мост» для окружений,
     где b2b.moysklad.ru недоступен напрямую;
  2) локально (`python3 catalog/remote_fetch.py`) — если есть прямой доступ в сеть.

Что пишет:
  catalog/data/catalog_full.json   — полный ответ API (все поля, все товары)
  catalog/data/catalog_index.json  — компактный индекс для поиска (быстро, без описаний)
  catalog/data/catalog_meta.json   — когда снят снапшот, сколько товаров, fingerprint
  catalog/data/report.md           — короткая сводка (читается человеком)
  catalog/data/diag_photos.txt     — диагностика по /getFullImages (сырые ответы)
  catalog/photos/<код>/NN.ext      — фото по заявкам из catalog/requests/photos.json
  catalog/photos/manifest.json     — карта: товар -> файлы фото

Заявка на фото (catalog/requests/photos.json):
  {"ids": ["<uuid>", "..."], "codes": ["00895"], "queries": ["ботинки prabos"],
   "limit_per_product": 4}
  Пусто/нет файла — фото не качаем, только каталог.

ВАЖНО: фото берём ТОЛЬКО у поставщика (getFullImages / прямая выдача API).
Никаких сторонних сайтов, маркетплейсов и поисковиков.
"""
import base64
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("MOYSKLAD_BASE") or "https://b2b.moysklad.ru/desktop-api/public/WDuXQTYGsuNZ"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "catalog", "data")
PHOTOS = os.path.join(ROOT, "catalog", "photos")
REQUESTS = os.path.join(ROOT, "catalog", "requests")
UA = "Mozilla/5.0 (compatible; VOkovke-catalog/1.0; +github-actions)"
PAGE = 100
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")

def log(*a):
    print(*a, flush=True)

def mkdirs():
    for p in (DATA, PHOTOS, REQUESTS):
        os.makedirs(p, exist_ok=True)

# ---------------------------------------------------------------- http

def http(url, method="GET", body=None, timeout=90, headers=None, raw=False):
    """Возвращает (status, bytes|str). Не бросает на HTTP-ошибках."""
    data = None
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return r.status, payload if raw else payload.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        payload = e.read()
        return e.code, payload if raw else payload.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — диагноз важнее типа
        return 0, f"ERR {type(e).__name__}: {e}"

def get_json(url, tries=4):
    for i in range(tries):
        st, txt = http(url)
        if st == 200:
            try:
                return json.loads(txt)
            except Exception as e:  # noqa: BLE001
                log(f"!! {url} -> 200, но не JSON: {e}; первые 200 симв.: {txt[:200]!r}")
        else:
            log(f"!! {url} -> status={st}, пробую снова ({i + 1}/{tries}); {str(txt)[:200]}")
        time.sleep(1.5 * (i + 1))
    return None

# ---------------------------------------------------------------- каталог

def fetch_catalog():
    first = get_json(f"{BASE}/products.json?limit={PAGE}&offset=0")
    if not first:
        raise SystemExit("НЕ УДАЛОСЬ получить каталог: products.json недоступен")
    total = int(first.get("size") or len(first.get("products", [])))
    prods = list(first.get("products", []))
    log(f"каталог: size={total}, первая страница {len(prods)}")
    off = PAGE
    while off < total:
        time.sleep(0.25)
        d = get_json(f"{BASE}/products.json?limit={PAGE}&offset={off}")
        if not d:
            log(f"!! страница offset={off} не получена — продолжаю")
            off += PAGE
            continue
        batch = d.get("products", [])
        if not batch:
            break
        prods.extend(batch)
        off += PAGE
        log(f"   ...{len(prods)}/{total}")

    # дедуп по id (страницы могут пересекаться, если поставщик менял каталог)
    seen, uniq = set(), []
    for p in prods:
        pid = p.get("id")
        if pid in seen:
            continue
        seen.add(pid)
        uniq.append(p)
    return uniq, total

INDEX_FIELDS = ("id", "name", "code", "article", "price", "stock", "category",
                "categoryId", "uom", "isKit")

def build_index(prods):
    idx = []
    for p in prods:
        row = {k: p.get(k) for k in INDEX_FIELDS}
        row["stock"] = int(p.get("stock") or 0)
        row["desc_len"] = len(p.get("description") or "")
        idx.append(row)
    return idx

def save_snapshot(prods, total):
    full_path = os.path.join(DATA, "catalog_full.json")
    json.dump(prods, open(full_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    idx = build_index(prods)
    json.dump(idx, open(os.path.join(DATA, "catalog_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    in_stock = [p for p in idx if p["stock"] > 0]
    fp = hashlib.sha1(json.dumps(sorted(p["id"] for p in idx)).encode()).hexdigest()[:12]
    meta = {
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": BASE,
        "total": len(idx),
        "reported_total": total,
        "in_stock_positions": len(in_stock),
        "in_stock_units": sum(p["stock"] for p in in_stock),
        "categories": len({p["category"] for p in idx}),
        "fingerprint": fp,
    }
    json.dump(meta, open(os.path.join(DATA, "catalog_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    cats = {}
    for p in in_stock:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
    top = sorted(cats.items(), key=lambda kv: -kv[1])[:25]
    rep = [
        "# Снапшот каталога «Дима» (МойСклад B2B)",
        "",
        f"- Снят: **{meta['fetched_at']}** (UTC)",
        f"- Источник: {BASE}",
        f"- Товаров всего: **{meta['total']}** (индекс), категорий: {meta['categories']}",
        f"- В наличии: **{meta['in_stock_positions']}** позиций, суммарно {meta['in_stock_units']} шт.",
        f"- Отпечаток: `{fp}`",
        "",
        "## В наличии по категориям (топ-25)",
        "",
    ]
    for c, n in top:
        rep.append(f"- {c}: {n}")
    open(os.path.join(DATA, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    log(f"снапшот сохранён: {len(idx)} товаров, в наличии {meta['in_stock_positions']} позиций")
    return idx, meta

# ---------------------------------------------------------------- фото

def looks_like_image_url(s, any_url=False):
    """Ссылка на фото. any_url=True — доверяем ответу поставщика
    (/getFullImages отдаёт подписанные ссылки S3 БЕЗ расширения файла)."""
    if not isinstance(s, str):
        return False
    low = s.split("?")[0].lower()
    if not low.startswith(("http://", "https://")):
        return False
    if low.endswith(IMG_EXT):
        return True
    return any_url

def collect_image_refs(obj, acc=None, depth=0, any_url=False):
    """Рекурсивно собираем всё, что похоже на фото: URL или data:base64."""
    if acc is None:
        acc = []
    if depth > 6:
        return acc
    if isinstance(obj, str):
        if looks_like_image_url(obj, any_url):
            acc.append(("url", obj))
        elif obj.startswith("data:image") and ";base64," in obj:
            acc.append(("b64", obj.split(";base64,", 1)[1]))
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_image_refs(v, acc, depth + 1, any_url)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            collect_image_refs(v, acc, depth + 1, any_url)
    return acc


def sniff_ext(blob: bytes, url: str = "") -> str:
    """Расширение по содержимому (надёжнее, чем по ссылке)."""
    if blob[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return ".webp"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    m = re.search(r"filename=([^&]+?)(?:\.(jpg|jpeg|png|webp))", url or "", re.I)
    if m:
        return "." + m.group(2).lower()
    ext = os.path.splitext((url or "").split("?")[0])[1].lower()
    return ext if ext in IMG_EXT else ".jpg"


def photo_quality(w: int, h: int, size_bytes: int) -> str:
    """ok | preview | strip — чтобы в карточки не попадали полоски и превью."""
    if not w or not h:
        return "preview"
    if min(w, h) < 400 and size_bytes < 40_000:
        return "preview"
    if max(w, h) / max(1, min(w, h)) >= 3.5:
        return "strip"            # длинная узкая полоса (размерная сетка, логотип-линейка)
    return "ok"


def image_size(blob: bytes):
    """(ширина, высота) без внешних библиотек. None, если не распознали."""
    try:
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(blob[16:20], "big"), int.from_bytes(blob[20:24], "big")
        if blob[:3] == b"\xff\xd8\xff":
            i = 2
            while i < len(blob) - 9:
                if blob[i] != 0xFF:
                    i += 1
                    continue
                marker = blob[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                    h = int.from_bytes(blob[i + 5:i + 7], "big")
                    w = int.from_bytes(blob[i + 7:i + 9], "big")
                    return w, h
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = int.from_bytes(blob[i + 2:i + 4], "big")
                i += 2 + max(seg, 2)
            return None
        if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
            fourcc = blob[12:16]
            if fourcc == b"VP8X":
                w = int.from_bytes(blob[24:27], "little") + 1
                h = int.from_bytes(blob[27:30], "little") + 1
                return w, h
            if fourcc == b"VP8 ":
                w = int.from_bytes(blob[26:28], "little") & 0x3FFF
                h = int.from_bytes(blob[28:30], "little") & 0x3FFF
                return w, h
    except Exception:  # noqa: BLE001
        return None
    return None

def save_image(ref, dest_dir, stem, diag, min_bytes=5_000):
    kind, payload = ref
    if kind == "url":
        st, blob = http(payload, timeout=120, raw=True)
        if st != 200 or not isinstance(blob, bytes) or len(blob) < 512:
            diag.append(f"{payload[:120]}… -> status={st}, bytes={len(blob) if isinstance(blob, bytes) else '?'}")
            return None
        url = payload
    else:
        try:
            blob = base64.b64decode(payload)
        except Exception as e:  # noqa: BLE001
            diag.append(f"b64 decode error: {e}")
            return None
        url = ""
    ext = sniff_ext(blob, url)
    size = image_size(blob)
    path = os.path.join(dest_dir, f"{stem}{ext}")
    open(path, "wb").write(blob)
    w, h = size if size else (0, 0)
    if len(blob) < min_bytes or (w and w < 400):
        diag.append(f"⚠ МЕЛКОЕ фото {path}: {len(blob)} байт, {w}×{h} — похоже на превью, а не на товарное фото")
    return {"path": path, "bytes": len(blob), "w": w, "h": h}

def resolve_targets(idx, req):
    """Заявка -> список товаров (полные объекты индекса)."""
    out, seen = [], set()
    for pid in req.get("ids", []):
        for row in idx:
            if row["id"] == pid and pid not in seen:
                seen.add(pid)
                out.append(row)
    for code in req.get("codes", []):
        for row in idx:
            if str(row.get("code")) == str(code) and row["id"] not in seen:
                seen.add(row["id"])
                out.append(row)
    for q in req.get("queries", []):
        words = str(q).lower().split()
        for row in idx:
            hay = f"{row['name']} {row['category']}".lower()
            if all(w in hay for w in words) and row["id"] not in seen:
                seen.add(row["id"])
                out.append(row)
    return out

def fetch_photos(idx, full_by_id):
    req_path = os.path.join(REQUESTS, "photos.json")
    if not os.path.exists(req_path):
        log("заявок на фото нет (catalog/requests/photos.json отсутствует)")
        return
    try:
        req = json.load(open(req_path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        log(f"!! заявка на фото битая: {e}")
        return

    targets = resolve_targets(idx, req)
    limit = int(req.get("limit_per_product") or 4)
    log(f"фото: заявка на {len(targets)} товар(ов), до {limit} фото на товар")
    if not targets:
        log("!! заявка не совпала ни с одним товаром — проверь ids/codes/queries")
        return

    diag = []
    manifest = []
    for row in targets:
        code = str(row.get("code") or row["id"])[:32]
        slug = re.sub(r"[^0-9A-Za-z_-]+", "_", code)
        dest = os.path.join(PHOTOS, slug)
        os.makedirs(dest, exist_ok=True)
        product = full_by_id.get(row["id"], row)
        refs = []
        calls = []
        # Штатный путь: PUT /getFullImages с полным JSON товара.
        # Ответ — массив ПОДПИСАННЫХ ссылок S3 (живут ~60 секунд), БЕЗ расширений в пути,
        # поэтому любые http(s)-ссылки из ответа считаем ссылками на фото.
        for method in ("PUT", "POST"):
            st, txt = http(f"{BASE}/getFullImages", method=method, body=product, timeout=120)
            calls.append(f"{method} /getFullImages -> status={st}; ответ[:700]: {str(txt)[:700]}")
            if st == 200 and txt:
                try:
                    refs = collect_image_refs(json.loads(txt), any_url=True)
                except Exception:  # noqa: BLE001
                    refs = collect_image_refs(txt, any_url=True)
                if refs:
                    break
        src = "getFullImages" if refs else ""
        if not refs:
            st, txt = http(f"{BASE}/getFullImages?id={row['id']}")
            calls.append(f"GET /getFullImages?id=... -> status={st}; ответ[:700]: {str(txt)[:700]}")
            if st == 200 and txt:
                try:
                    refs = collect_image_refs(json.loads(txt), any_url=True)
                except Exception:  # noqa: BLE001
                    refs = collect_image_refs(txt, any_url=True)
                if refs:
                    src = "getFullImages?id"
        if not refs:
            # запасной путь — только если у поставщика нет полных фото
            refs = collect_image_refs(product)
            src = "imageURL (превью, мусор)" if refs else ""
            if refs:
                diag.append(f"!! {row['name'][:60]}: /getFullImages пусто — беру только превью из API")

        files, details = [], []

        def download(refs_list):
            files_l, details_l = [], []
            for i, ref in enumerate(refs_list[:limit], 1):
                got = save_image(ref, dest, f"{slug}_{i}", diag)
                if got:
                    rel = os.path.relpath(got["path"], ROOT).replace(os.sep, "/")
                    q = photo_quality(got["w"], got["h"], got["bytes"])
                    if q != "ok":
                        diag.append(f"· {rel}: помечено «{q}» ({got['w']}×{got['h']}) — в карточки не пойдёт")
                    files_l.append(rel)
                    details_l.append({"path": rel, "bytes": got["bytes"], "w": got["w"], "h": got["h"],
                                      "quality": q})
            return files_l, details_l

        files, details = download(refs)
        if not files and refs and src.startswith("getFullImages"):
            # подписанные ссылки живут ~60 с — если не успели, берём свежие
            diag.append("!! ссылки протухли — перезапрашиваю /getFullImages")
            st, txt = http(f"{BASE}/getFullImages", method="PUT", body=product, timeout=120)
            if st == 200 and txt:
                try:
                    refs = collect_image_refs(json.loads(txt), any_url=True)
                except Exception:  # noqa: BLE001
                    pass
                files, details = download(refs)
        manifest.append({
            "id": row["id"], "code": row.get("code"), "name": row["name"],
            "category": row.get("category"), "stock": row.get("stock"),
            "files": files, "details": details, "source": src, "refs_found": len(refs),
        })
        best = max((d["w"] for d in details), default=0)
        log(f"   {row['name'][:60]}: фото {len(files)} (источник: {src or '—'}, "
            f"лучшее {best}px, ссылок {len(refs)})")
        diag.extend([f"--- {row['name'][:70]} (code={code})"] + calls)

    json.dump(manifest, open(os.path.join(PHOTOS, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(DATA, "diag_photos.txt"), "w", encoding="utf-8").write("\n".join(diag) + "\n")
    total_files = sum(len(m["files"]) for m in manifest)
    log(f"фото сохранено: {total_files} файл(ов) по {len(manifest)} товар(ам)")

# ---------------------------------------------------------------- main

def main():
    mkdirs()
    log(f"BASE={BASE}")
    prods, total = fetch_catalog()
    idx, meta = save_snapshot(prods, total)
    full_by_id = {p["id"]: p for p in prods}
    if "--catalog-only" not in sys.argv:
        fetch_photos(idx, full_by_id)
    log("готово")

if __name__ == "__main__":
    main()
