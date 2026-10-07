#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СБОРКА КОМПЛЕКТА: карточка + пост.

  python3 vk/kit.py vk/kits/shturmovik.json

Что делает:
  1) по id берёт из каталога название, фото (manifest) и описание;
  2) рисует карточку-комплект (media/blank/kit_card.py): основа + позиции к ней + итог;
  3) пишет пост: комплект целиком И каждая позиция отдельно — без цен.

Цены берём ТОЛЬКО из kit.json (там их ставит владелец). Нет цены → «по запросу».
В пост цена не попадает никогда — правило магазина.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from catalog import store
    from vk.post import split_description, hashtags, norm
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.join(ROOT, "catalog"))
    import store  # type: ignore
    from post import split_description, hashtags, norm  # type: ignore

sys.path.insert(0, os.path.join(ROOT, "media", "blank"))
from kit_card import build as build_card  # noqa: E402
from vk.slides import build as build_slides, build_spec  # noqa: E402

CTA = "СДЭК по России, оплата при получении. Напишите в личные сообщения — соберём под вашу задачу."


def load_catalog():
    idx = json.load(open(os.path.join(ROOT, "catalog", "data", "catalog_index.json"), encoding="utf-8"))
    full = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "catalog", "data", "catalog_full.json"), encoding="utf-8"))}
    manifest = {m["id"]: m for m in store.photos_manifest()}
    return idx, full, manifest


def resolve(node, idx, full, manifest):
    """id → название, описание, фото."""
    row = next((r for r in idx if r["id"] == node["id"]), None)
    if not row:
        raise SystemExit(f"СТОП: id {node['id']} не найден в каталоге (позиция пропала?)")
    if int(row.get("stock") or 0) <= 0:
        raise SystemExit(f"СТОП: «{row['name']}» — нет на складе, в комплект не ставим")
    files = (manifest.get(node["id"], {}) or {}).get("files") or []
    if not files:
        raise SystemExit(f"СТОП: у «{row['name']}» нет фото поставщика — карточку не собираем")
    desc = (full.get(node["id"], {}) or {}).get("description") or ""
    return {"row": row, "photos": files, "desc": desc}


def facts_for(node, res, limit=3):
    """Факты: сначала ручные из JSON, иначе — из описания поставщика."""
    if node.get("facts"):
        return list(node["facts"])[:limit]
    _sub, feats, specs = split_description(res["desc"])
    out = []
    for raw in list(feats) + list(specs):
        line = re.sub(r"^[^\w(«\"А-Яа-яЁё0-9]+", "", str(raw)).strip()
        line = re.sub(r"\s+", " ", line).rstrip(" ;,.")
        if 25 <= len(line) <= 160 and line not in out:
            out.append(line)
        if len(out) >= limit:
            break
    return out


def card_sections(node, res):
    facts = facts_for(node, res, limit=6)
    return [{"h": node.get("section_title", "ОСОБЕННОСТИ"), "bullets": facts}] if facts else []


def make_aliases(items):
    """Короткие имена позиций: «Плитник», «Шлем», «Наушники» — для строки состава."""
    return [it.get("short") or it["label"] for it in items]


def one_line_facts(node, res):
    f = facts_for(node, res, limit=2)
    return "; ".join(f[:2]) if f else ""


def build_kit(kit_path):
    kit = json.load(open(kit_path, encoding="utf-8"))
    idx, full, manifest = load_catalog()
    slug = kit["slug"]
    out_dir = os.path.join(HERE, "posts", "kits", slug)
    os.makedirs(out_dir, exist_ok=True)

    main = kit["main"]
    main_res = resolve(main, idx, full, manifest)
    items = kit["items"]
    resol = {it["id"]: resolve(it, idx, full, manifest) for it in items}

    # ---------- карточка ----------
    hide_prices = bool(kit.get("hide_prices"))
    _main_price = None if hide_prices else main.get("price")
    card = {
        "hide_prices": hide_prices,
        "date": kit.get("date", ""),
        "title": kit["title"],
        "subtitle": kit.get("subtitle", "Собрано из наличия"),
        "product": {
            "name": main_res["row"]["name"],
            "sub": main.get("sub") or kit.get("main_sub", ""),
            "photos": main_res["photos"][:3],
            "sections": card_sections(main, main_res),
            "price_label": main.get("label", "ОСНОВА"),
            "price": _main_price,
        },
        "options": {
            "label": kit.get("options_label", "К НЕМУ — НА ВЫБОР"),
            "items": [{
                "name": it.get("short") or resol[it["id"]]["row"]["name"],
                "sub": it.get("card_sub") or one_line_facts(it, resol[it["id"]]),
                "sub2": it.get("card_sub2") or "",
                "photo": resol[it["id"]]["photos"][0],
                "price": None if hide_prices else it.get("price"),
            } for it in items],
        },
    }
    if kit.get("kit"):
        card["kit"] = {"label": kit["kit"]["label"],
                       "price": None if hide_prices else kit["kit"].get("price")}
    json.dump(card, open(os.path.join(out_dir, "карточка.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    card_path = os.path.join(out_dir, "карточка.jpg")
    build_card(card, card_path)

    # ---------- слайды-карусель (пост-история) ----------
    slides_dir = os.path.join(out_dir, "слайды")
    spec = build_spec(kit, card, resol, story=kit.get("story"))
    build_slides(spec, slides_dir)
    open(os.path.join(out_dir, "слайды.txt"), "w", encoding="utf-8").write(
        "\n".join(f"{i:02d}. {s['type']}: {s.get('title', s.get('name', ''))}"
                   for i, s in enumerate(spec, 1)) + "\n")

    # ---------- пост ----------
    post_cfg = kit.get("post", {})
    L = []
    L.append(post_cfg.get("headline", f"🪖 Собрали комплект «{kit.get('kit_name', slug)}»"))
    L.append("")
    if post_cfg.get("hook"):
        L.append(post_cfg["hook"])
        L.append("")
    L.append("Что входит в комплект:")
    for it in [main] + items:
        res = main_res if it is main else resol[it["id"]]
        short = it.get("short") or it["label"]
        variant = it.get("variant") or ""
        line = f"▪️ {short}" + (f" — {variant}" if variant else "")
        L.append(line)
        for f in facts_for(it, res, limit=2):
            L.append(f"   {f}")
    L.append("")
    if post_cfg.get("why"):
        L.append(post_cfg["why"])
        L.append("")
    if kit.get("kit", {}).get("label"):
        L.append(kit["kit"]["label"].replace("КОМПЛЕКТ:", "Комплект:").strip() + ".")
        L.append("")
    L.append("Каждую позицию можно взять и отдельно — подберём по размеру.")
    L.append("")
    offer_lines = []
    of = kit.get("offer")
    if of:
        offer_lines = [f"🎁 {of.get('title', 'СКИДКА ЗА РЕПОСТ')} — {of.get('value_label', '').lstrip('−-')}".strip(), ""]
        for i, st in enumerate(of.get("steps", []), 1):
            offer_lines.append(f"{i}. {st}.")
        offer_lines.append("")
        if of.get("note"):
            offer_lines += [of["note"] + ".", ""]
        L += offer_lines
    L.append(post_cfg.get("cta", CTA))
    L.append("")
    names = " ".join(it.get("short_hashtag") or it.get("short") or "" for it in [main] + items)
    L.append(hashtags(names, kit.get("category", ""), extra=kit.get("hashtags") or ()))
    text = "\n".join(L).strip() + "\n"

    # страховка: в публикуемом тексте не должно быть цен и внутренних слов.
    # скидка по акции (её дал владелец) из проверки исключается — это не цена товара
    guard_text = text
    for ln in [ln for ln in offer_lines if ln]:
        guard_text = guard_text.replace(ln, "")
    for label, rx in (("цена", r"\d[\d\s]*(₽|руб)"), ("«у Димы»", r"\bДимы?\b"),
                      ("поставщик", r"поставщик"), ("склад", r"\b(на|со)\s+склад"),
                      ("остаток", r"\b\d+\s*(шт|компл|пар)\b")):
        m = re.search(rx, guard_text, re.I)
        assert not m, f"в тексте комплекта запрещённое: {label} → {m.group(0)!r}"

    open(os.path.join(out_dir, "пост.txt"), "w", encoding="utf-8").write(text)

    # отдельные посты по позициям комплекта (владелец просил: и комплект, и по отдельности)
    single_dir = os.path.join(out_dir, "по_отдельности")
    os.makedirs(single_dir, exist_ok=True)
    for it in items:
        res = resol[it["id"]]
        short = it.get("short") or it["label"]
        variant = it.get("variant") or ""
        head = f"🪖 {short}" + (f" — {variant}" if variant else "")
        body = [head, ""]
        if it.get("single_hook"):
            body += [it["single_hook"], ""]
        fs = facts_for(it, res, limit=4)
        if fs:
            body.append("Что важно:")
            body += [f"▪️ {f}" for f in fs]
            body.append("")
        body += ["В наличии.", "", post_cfg.get("cta", CTA), "",
                 hashtags(res["row"]["name"], res["row"].get("category", ""))]
        safe = re.sub(r"[^\w\sА-Яа-яЁё-]", "", short).strip()[:40]
        open(os.path.join(single_dir, f"{safe}.txt"), "w", encoding="utf-8").write("\n".join(body) + "\n")

    # архив комплекта в раздачу
    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    import zipfile
    zip_name = f"V_OKOPE_kit_{slug}.zip"
    zip_path = os.path.join(dist, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_dir):
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, os.path.dirname(out_dir)))
    print(f"Комплект «{kit.get('kit_name', slug)}»: {card_path}")
    print(f"  архив: {os.path.relpath(zip_path, ROOT)} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} МБ)")
    print(f"  пост: {os.path.join(out_dir, 'пост.txt')}")
    print(f"  по отдельности: {len(items)} шт → {single_dir}")
    print(f"  слайды-карусель: {len(spec)} шт → {slides_dir}")
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Использование: python3 vk/kit.py vk/kits/<slug>.json")
    print(build_kit(sys.argv[1]))
