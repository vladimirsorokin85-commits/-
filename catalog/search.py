#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УМНЫЙ ПОИСК по каталогу Димы (снапшот МойСклад).

Умеет:
  • синонимы из практики магазина (пиксель = цифра ЕМР, мох = A-Tacs FG Camo);
  • морфологию и опечатки («батинки» найдёт ботинки);
  • размеры («52-й» → р.2 (48-54));
  • фильтры: только в наличии, бюджет, категория, цвет, размер;
  • группировку «модель → доступные размеры/цвета», как в реальном ответе клиенту.

Примеры:
  python3 -m catalog.search "ботинки прабос 42"
  python3 -m catalog.search "бронежилет пиксель" --budget 85000 --in-stock
  python3 -m catalog.search "подсумок мох" --limit 5 --json
  python3 -m catalog.search --cat Обувь --in-stock
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from catalog import store
except ImportError:  # запуск как отдельного скрипта
    import store  # type: ignore

SYN_PATH = os.path.join(HERE, "synonyms.json")

# ------------------------------------------------------------------ нормализация

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).lower().replace("ё", "е")
    s = re.sub(r"[^0-9a-zа-я\-\.]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s: str):
    return [t for t in norm(s).split() if t not in ("-", ".")]


ENDINGS = ("ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими", "ых", "их", "ый", "ий", "ой",
           "ая", "яя", "ое", "ее", "ые", "ие", "ов", "ев", "ей", "ам", "ям", "ах", "ях",
           "у", "ю", "а", "я", "о", "е", "ы", "и", "й", "ь", "s", "es")


def stem(t: str) -> str:
    if len(t) <= 4:
        return t
    for e in ENDINGS:
        if t.endswith(e) and len(t) - len(e) >= 4:
            return t[:-len(e)]
    return t


def common_prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def sim(a: str, b: str) -> float:
    """0..1 — насколько токены похожи (точное совпадение, основа, опечатка)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if stem(a) == stem(b):
        return 0.95
    if min(len(a), len(b)) >= 5 and common_prefix(a, b) >= 5:
        return 0.9
    if min(len(a), len(b)) >= 5:
        r = SequenceMatcher(None, a, b).ratio()
        if r >= 0.8:
            return round(r * 0.9, 3)
    return 0.0


# ------------------------------------------------------------------ словари

def load_synonyms():
    if not os.path.exists(SYN_PATH):
        return {"groups": [], "colors": {}, "size_hint": {}, "stopwords": []}
    return json.load(open(SYN_PATH, encoding="utf-8"))


def color_terms(syn, color: str):
    """Варианты названия цвета для фильтра --color/--pattern."""
    colors = syn.get("colors", {})
    out = {norm(color)}
    for canon, alts in colors.items():
        group = {norm(canon)} | {norm(a) for a in alts}
        if any(sim(norm(color), g) >= 0.9 for g in group):
            out |= group
    return {t for t in out if t}


def build_groups(qtoks, syn):
    """Группы токенов: внутри группы — ИЛИ (синонимы), между группами — И."""
    stop = {norm(w) for w in syn.get("stopwords", [])}
    groups, used = [], set()
    for t in qtoks:
        if t in used or t in stop or len(t) < 2:
            continue
        g = None
        for grp in syn.get("groups", []):
            if any(sim(t, norm(m)) >= 0.9 for m in grp):
                g = [norm(m) for m in grp]
                break
        if g is None:
            g = [t]
        # размеры: «52» → «р.2 (48-54)»
        hint = syn.get("size_hint", {}).get(t)
        if hint:
            g = list(dict.fromkeys(g + [norm(h) for h in hint]))
        used.update(g)
        groups.append(g)
    return groups


# ------------------------------------------------------------------ размеры и модель

SIZE_PATTERNS = [
    re.compile(r"(?P<label>р\.\s*\d)\s*\((?P<range>\d{2}\s*[-–]\s*\d{2})\)", re.I),
    re.compile(r"\((?P<label>\d{2})\s*\((?P<range>\d{3}\s*[-–]\s*\d{3})\s*мм\)", re.I),
    re.compile(r"\((?P<label>\d{2})\)"),
    re.compile(r"\((?P<label>\d{2}\s*[-–]\s*\d{2})\)"),
    re.compile(r"(?P<label>размер\s*\d{2})", re.I),
]


def split_size(name: str):
    """('Ботинки PRABOS ..., цвет Dark Green', ['42', '44']) — модель и размеры."""
    fam, sizes = name.strip(), []
    for pat in SIZE_PATTERNS:
        for m in pat.finditer(fam):
            lab = m.group("label").strip()
            rng = (m.groupdict().get("range") or "").replace(" ", "")
            sizes.append(f"{lab} ({rng})" if rng else lab)
        fam = pat.sub(" ", fam)
    fam = re.sub(r"\s*\(\s*и?\s*$", " ", fam)          # хвостовая незакрытая скобка
    fam = re.sub(r"\s{2,}", " ", fam).strip(" ,;·—-")
    return fam or name, list(dict.fromkeys(sizes))


def family_of(name: str) -> str:
    return split_size(name)[0]


def sizes_of(name: str):
    return split_size(name)[1]


# ------------------------------------------------------------------ поиск

FIELD_WEIGHTS = {"name": 30.0, "category": 12.0, "code": 60.0, "desc": 3.0}


def match_field(qtok: str, hay: str) -> float:
    """Лучшее совпадение токена внутри строки."""
    if not qtok or not hay:
        return 0.0
    words = hay.split()
    best = 0.0
    for w in words:
        best = max(best, sim(qtok, w))
        if best == 1.0:
            break
    return best


def score_product(row, groups, desc_text="", use_desc=True):
    """(score, why) — score 0 значит «не подходит» (какую-то группу не нашли)."""
    name = norm(row.get("name"))
    cat = norm(row.get("category"))
    code = norm(str(row.get("code") or ""))
    art = norm(str(row.get("article") or ""))
    desc = norm(desc_text)[:4000] if use_desc else ""
    total, why = 0.0, []
    for g in groups:
        best, hit = 0.0, ""
        for qtok in g:
            s = match_field(qtok, name) * FIELD_WEIGHTS["name"]
            if s > best:
                best, hit = s, f"название:{qtok}"
            s = match_field(qtok, cat) * FIELD_WEIGHTS["category"]
            if s > best:
                best, hit = s, f"категория:{qtok}"
            if code and (qtok in code or code in qtok):
                s = FIELD_WEIGHTS["code"]
                if s > best:
                    best, hit = s, f"код:{qtok}"
            if art and qtok in art:
                s = FIELD_WEIGHTS["code"] * 0.8
                if s > best:
                    best, hit = s, f"артикул:{qtok}"
            if desc:
                s = match_field(qtok, desc) * FIELD_WEIGHTS["desc"]
                if s > best:
                    best, hit = s, f"описание:{qtok}"
        if best <= 0:
            return 0.0, []
        total += best
        why.append(hit)
    return round(total, 1), why


def filter_rows(rows, args, syn, full, photos):
    out = []
    color_set = color_terms(syn, args.color) if args.color else None
    for row in rows:
        if args.in_stock and int(row.get("stock") or 0) <= 0:
            continue
        if args.no_stock and int(row.get("stock") or 0) > 0:
            continue
        price = row.get("price")
        if args.budget is not None:
            if price is None or float(price) > args.budget:
                continue
        if args.min_budget is not None:
            if price is None or float(price) < args.min_budget:
                continue
        if args.cat and norm(args.cat) not in norm(row.get("category")):
            continue
        nm = norm(row.get("name"))
        if color_set and not any(t and t in nm for t in color_set):
            continue
        if args.size:
            sizes = " ".join(sizes_of(row.get("name") or ""))
            if norm(args.size) not in norm(sizes) and norm(args.size) not in nm:
                continue
        out.append(row)
    return out


def search(query, rows=None, args=None, syn=None, full=None, photos=None):
    rows = rows if rows is not None else store.load_index()[0]
    syn = syn or load_synonyms()
    full = full if full is not None else store.full_by_id()
    photos = photos if photos is not None else store.photos_by_id()
    q = norm(query or "")
    qtoks = toks(q)
    groups = build_groups(qtoks, syn) if qtoks else []
    scored = []
    for row in rows:
        desc = (full.get(row["id"], {}) or {}).get("description", "")
        sc, why = score_product(row, groups, desc)
        if groups and sc <= 0:
            continue
        if int(row.get("stock") or 0) > 0:
            sc += 8
        ph = photos.get(row["id"], {})
        if ph.get("files"):
            sc += 4
        scored.append({**row, "_score": round(sc, 1), "_why": why,
                       "_photos": ph.get("files", []), "_desc": desc})
    scored.sort(key=lambda r: (-r["_score"], r["name"]))
    return scored


def group_families(rows):
    """Схлопываем размеры одного товара в одну строку модели (правило магазина)."""
    fams = {}
    for r in rows:
        key = (family_of(r["name"]), norm(r.get("category")))
        f = fams.setdefault(key, {"family": key[0], "category": r["category"], "rows": []})
        f["rows"].append(r)
    out = list(fams.values())
    for f in out:
        f["total_stock"] = sum(int(r.get("stock") or 0) for r in f["rows"])
        prices = [r.get("price") for r in f["rows"] if r.get("price")]
        f["price_min"] = min(prices) if prices else None
        f["price_max"] = max(prices) if prices else None
        f["codes"] = [str(r.get("code")) for r in f["rows"] if r.get("code")]
        f["photos"] = sorted({p for r in f["rows"] for p in r.get("_photos", [])})
        f["score"] = max(r["_score"] for r in f["rows"])
        f["sizes"] = []
        for r in f["rows"]:
            for s in sizes_of(r["name"]):
                f["sizes"].append((s, int(r.get("stock") or 0)))
        f["sizes"] = list(dict.fromkeys(f["sizes"]))
    out.sort(key=lambda f: (-f["score"], -f["total_stock"]))
    return out


# ------------------------------------------------------------------ вывод

def money(v):
    if v is None:
        return "—"
    return f"{int(round(float(v))):,}".replace(",", " ") + " ₽"


def render(families, meta, args, total_positions):
    src = store.source_line(meta)
    head = [f"Источник: {src}", f"Найдено: {len(families)} модел(ей), позиций в каталоге: {total_positions}"]
    if args.budget:
        head.append(f"Бюджет (закуп): до {money(args.budget)}")
    lines = ["\n".join(head), ""]
    for i, f in enumerate(families, 1):
        stock_note = f"в наличии {f['total_stock']} шт" if f["total_stock"] else "НЕТ В НАЛИЧИИ"
        price = money(f["price_min"]) if f["price_min"] == f["price_max"] else f"{money(f['price_min'])}–{money(f['price_max'])}"
        lines.append(f"{i}) {f['family']}   ·  {f['category']}")
        sizes = " · ".join(f"{s} — {n} шт" for s, n in f["sizes"]) if f["sizes"] else "размер не указан в названии"
        lines.append(f"   {stock_note}  |  размеры: {sizes}")
        lines.append(f"   закуп Димы: {price}  |  коды: {', '.join(f['codes']) or '—'}"
                     f"  |  фото: {'есть (' + str(len(f['photos'])) + ')' if f['photos'] else 'нет в заявке'}")
        if args.why and f["rows"]:
            lines.append(f"   почему нашлось: {', '.join(f['rows'][0]['_why'])}")
        lines.append("")
    lines.append("Цены выше — ЗАКУП поставщика. Розницу для клиента назначает владелец.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Умный поиск по каталогу Димы")
    ap.add_argument("query", nargs="*", help="слова запроса (вольный текст)")
    ap.add_argument("--cat", help="фильтр по категории (подстрока)")
    ap.add_argument("--in-stock", action="store_true", help="только в наличии")
    ap.add_argument("--no-stock", action="store_true", help="только отсутствующее")
    ap.add_argument("--budget", type=float, help="не дороже (закуп)")
    ap.add_argument("--min-budget", type=float, help="не дешевле (закуп)")
    ap.add_argument("--color", help="цвет/камуфляж (мох, пиксель, койот…)")
    ap.add_argument("--size", help="размер (42, 52, р.2…)")
    ap.add_argument("--limit", type=int, default=12, help="сколько моделей показать")
    ap.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    ap.add_argument("--why", action="store_true", help="показать, почему позиция нашлась")
    ap.add_argument("--no-desc", action="store_true", help="не искать по описаниям (быстрее)")
    args = ap.parse_args(argv)

    rows, meta = store.load_index()
    full = store.full_by_id() if (not args.no_desc and store.full_by_id()) else {}
    rows = filter_rows(rows, args, load_synonyms(), full, store.photos_by_id())
    hits = search(" ".join(args.query), rows=rows, args=args, full=full)
    if not args.no_desc:
        hits.sort(key=lambda r: (-r["_score"], r["name"]))
    fams = group_families(hits)[: args.limit]

    if args.json:
        print(json.dumps({"source": store.source_line(meta), "meta": meta,
                          "families": fams, "flat": hits}, ensure_ascii=False, indent=1, default=str))
        return 0

    if not fams:
        print("НИЧЕГО НЕ НАЙДЕНО.\n"
              "Проверь слова запроса, сними фильтры или попроси фото/цену у поставщика.")
        return 1
    print(render(fams, meta, args, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
