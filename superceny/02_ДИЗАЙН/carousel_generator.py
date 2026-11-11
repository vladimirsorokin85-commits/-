#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
КАРУСЕЛЬ «СУПЕРЦЕНЫ НА НПО „КИЛОВАТТ“» — генератор 4 слайдов на позицию.
Сюжет: 01 КРЮЧОК → 02 ЦИФРЫ → 03 СЦЕНАРИИ → 04 ФИНАЛ/CTA.

Тексты: поля s1_* … s4_* из positions.json (v6). Пока v6 нет — черновики
из _carousel_draft.json, затем обычные поля каталога.

  python carousel_generator.py --preview kw-05,kw-20   # образцовые серии в preview_carousel/
  python carousel_generator.py --clean                 # все 81 HTML в 03_HTML
"""

import argparse
import html
import importlib.util
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SUPER = os.path.dirname(HERE)
HTML_DIR = os.path.join(SUPER, "03_HTML")
POSITIONS = os.path.join(SUPER, "01_ДАННЫЕ", "positions.json")
DRAFT = os.path.join(HERE, "_carousel_draft.json")

SLIDES = ["01_ЛИСТАЙ.html", "02_ЦИФРЫ.html", "03_СЦЕНАРИИ.html", "04_CTA.html"]
LEGAL = ("Характеристики — по паспорту изделия. Не является публичной офертой. "
         "РЭС: порядок применения — по законодательству РФ.")
ASSET = "../../02_ДИЗАЙН/"


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=False)


def cls_by_len(text, xl="", l="", m="", s=""):
    n = len(text or "")
    if n <= 9:
        return xl
    if n <= 14:
        return l
    if n <= 22:
        return m
    return s


def load():
    spec = importlib.util.spec_from_file_location("kgen", os.path.join(HERE, "generator.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)

    raw = json.load(open(POSITIONS, encoding="utf-8-sig"))
    if isinstance(raw, dict):
        raw = raw.get("positions") or raw.get("items") or []
    draft = json.load(open(DRAFT, encoding="utf-8-sig")) if os.path.isfile(DRAFT) else {}

    out = []
    for idx, item in enumerate(raw, 1):
        pos = g.normalize(item, idx)
        car = dict(draft.get(item.get("id"), {}))
        for k, v in item.items():
            if len(k) > 2 and k[0] == "s" and k[1] in "1234" and v not in (None, "", []):
                car[k] = v
        pos["car"] = car
        # запасные 4 плитки из паспорта
        tiles = []
        if pos.get("specs"):
            tt, _ = g.pick_tiles(pos["specs"], 4)
            for s in tt:
                val, sub, _ = g.compact_tile(s)
                tiles.append({"value": val, "label": s["label"], "note": sub})
        pos["tiles"] = tiles
        out.append(pos)
    return out


def get(p, key, default=""):
    v = p["car"].get(key)
    return v if v not in (None, "", []) else default


def asset_prefix(p):
    return ASSET


def img_asset(p, kind):
    """Подготовленный ассет (zoom/detail/alt) из img, иначе main."""
    name = p["id"] + "_" + kind + ".png"
    if os.path.isfile(os.path.join(HERE, "img", name)):
        return ASSET + "img/" + name
    return p["photo"]


# --------------------------------------------------------------------------
# общий каркас
# --------------------------------------------------------------------------

def frame(p, idx, body, theme):
    dots = "".join('<span class="%s"></span>' % ("is-on" if i == idx else "") for i in range(1, 5))
    swipe = "" if idx == 4 else '<div class="k-swipe">ЛИСТАЙ ДАЛЬШЕ</div>'
    arrow = ('<div class="k-arrow"><span>%s</span><span class="k-arrow__g">→</span></div>'
             % ("ПИШИ" if idx == 4 else "ЛИСТАЙ"))
    progress = ("" if idx == 4 else
                '<div class="k-progress"><i style="width:%d%%"></i></div>' % (idx * 25))
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s · %(num)s · «В ОКОПЕ»</title>
<link rel="stylesheet" href="%(asset)stokens.css">
<link rel="stylesheet" href="%(asset)scarousel.css">
</head>
<body class="theme-%(theme)s">
<main class="slide slide--%(idx)02d theme-%(theme)s">
  <header class="k-top">
    <img class="k-top__logo" src="%(asset)simg/brand/%(logo)s" alt="В ОКОПЕ — магазин брони">
    <div class="k-top__series">Суперцены · НПО «Киловатт»</div>
    <div class="k-top__num"><span class="k-num__i">%(idx)02d</span>/04</div>
  </header>
%(body)s
  <div class="k-bottom">
    <div class="k-dots">%(dots)s</div>
    %(swipe)s
    %(arrow)s
  </div>
  %(progress)s
  <div class="k-legal">%(legal)s</div>
</main>
</body>
</html>
""" % {"title": esc(p["name_full"]), "num": "%02d" % idx, "asset": ASSET,
       "theme": theme, "idx": idx, "body": body, "dots": dots,
       "logo": "logo_w_word.png" if theme == "field" else "logo_d_full.png",
       "swipe": swipe, "arrow": arrow, "progress": progress, "legal": LEGAL}


def photo_url(p, name=None):
    photo = p["photo"]
    if not photo:
        return None
    if name:
        base = os.path.dirname(photo).replace("\\", "/")
        cand = base + "/" + name
        if os.path.isfile(os.path.join(HERE, "img", name)):
            cand = ASSET + "img/" + name
        return cand
    return photo


# --------------------------------------------------------------------------
# SLIDE 01 · КРЮЧОК
# --------------------------------------------------------------------------

def slide01(p):
    name = get(p, "s1_title", p["name"])
    kicker = get(p, "s1_kicker", p["hook"])
    claim = get(p, "s1_claim")
    sub = get(p, "s1_sub", p["line"])
    if not claim:
        facts = p.get("key_facts") or []
        claim = " · ".join(facts[:2]).upper() if facts else p["name"]
    photo = p["photo"]
    if photo:
        photo_html = ('<div class="k1-photo"><img src="%s" alt="%s">'
                      '<span class="k1-photo__cap">%s</span></div>'
                      % (photo, esc(p["name_full"]), esc(p["name_full"])))
    else:
        photo_html = ('<div class="k1-photo k1-photo--stub"><div class="k1-photo__stub">'
                      '<b>ФОТО УТОЧНЯЕТСЯ</b><span>НОВАЯ ПОЗИЦИЯ · ПОД ЗАКАЗ</span></div></div>')
    body = """  <div class="k1-head">
    <p class="k1-kicker">%s</p>
    <span class="k1-badge">СУПЕРЦЕНА</span>
    <h1 class="k1-title%s">%s</h1>
    <p class="k1-claim%s">%s</p>
    <p class="k1-sub">%s</p>
  </div>
  <div class="k1-swipe-strip"></div>
  <div class="k-ghost k1-ghost">01</div>
  %s""" % (esc(kicker),
              cls_by_len(name, "", " k1-title--l", " k1-title--m", " k1-title--s"), esc(name),
              "" if len(claim) <= 20 else (" k1-claim--l" if len(claim) <= 30 else " k1-claim--m"),
              esc(claim), esc(sub), photo_html)
    return frame(p, 1, body, "field")


# --------------------------------------------------------------------------
# SLIDE 02 · ЦИФРЫ
# --------------------------------------------------------------------------

def slide02(p):
    lead = get(p, "s2_lead", "ВНУТРИ —")
    stats = get(p, "s2_stats") or p["tiles"] or [{"value": "—", "label": "характеристики"}]
    grid = "\n".join(
        '      <div class="k2-stat"><span class="k2-stat__v%s">%s</span>'
        '<span class="k2-stat__k">%s</span>%s</div>'
        % ("" if len(str(s.get("value", ""))) <= 6 else
           (" k2-stat__v--l" if len(str(s.get("value", ""))) <= 7 else
            (" k2-stat__v--m" if len(str(s.get("value", ""))) <= 9 else
             (" k2-stat__v--s" if len(str(s.get("value", ""))) <= 11 else " k2-stat__v--xs"))),
           esc(s.get("value", "")), esc(s.get("label", "")),
           ('<span class="k2-stat__n">%s</span>' % esc(s["note"])) if s.get("note") else "")
        for s in stats[:4])
    tail = get(p, "s2_tail", "И ЭТО ЕЩЁ НЕ ВСЁ. КОМУ? →")
    detail = img_asset(p, "detail") if p["photo"] else None
    detail_html = ('<div class="k2-detail"><img src="%s" alt="%s"><span class="k2-detail__cap">%s</span></div>'
                   % (detail, esc(p["name_full"]), esc(p["name_full"]))) if detail else ""
    body = """  <div class="k2-head">
    <p class="k2-lead">%s</p>
    <h1 class="k2-title%s">%s</h1>
  </div>
  <div class="k2-main">
    <div class="k2-grid">
%s
    </div>
    %s
  </div>
  <p class="k2-tail">%s</p>
  <p class="k2-note">%s</p>
  <div class="k-ghost k2-ghost">02</div>""" % (
        esc(lead), cls_by_len(p["name"], "", " k2-title--m", " k2-title--s", " k2-title--s"),
        esc(p["name"]), grid, detail_html, esc(tail), esc(p["line"]))
    return frame(p, 2, body, "field")


def facts_html(p):
    facts = p.get("key_facts") or []
    if not facts:
        return ""
    cells = "".join('<span class="k3-fact">%s</span>' % esc(f) for f in facts[:4])
    return '<div class="k3-facts">%s</div>' % cells


def slide03(p):
    eyebrow = get(p, "s3_eyebrow", "ПРИМЕНЕНИЕ")
    title = get(p, "s3_title", "КОМУ ЭТО НАДО")
    points = get(p, "s3_points") or p["tasks"]
    tail = get(p, "s3_tail", "ОСТАЛОСЬ ГЛАВНОЕ — ЦЕНА →")
    rows = "\n".join(
        '    <li class="k3-point"><span class="k3-point__n">%02d</span>'
        '<p class="k3-point__t">%s</p></li>' % (i, esc(t))
        for i, t in enumerate(points[:4], 1))
    tail_html = esc(tail)
    if "—" in tail:
        a, b = tail.split("—", 1)
        tail_html = esc(a) + "— <em>" + esc(b.strip()) + "</em>"
    photo = p["photo"]
    photo_html = ('<div class="k3-photo"><img src="%s" alt="%s">'
                  '<span class="k3-photo__cap">%s</span></div>'
                  % (photo, esc(p["name_full"]), esc(p["name_full"]))) if photo else ""
    detail = img_asset(p, "detail") if p["photo"] else None
    detail_html = ('<div class="k3-detail"><img src="%s" alt="%s"></div>'
                   % (detail, esc(p["name_full"]))) if detail else ""
    body = """  <div class="k3-head">
    <p class="k3-eyebrow">%s</p>
    <h1 class="k3-title%s">%s</h1>
  </div>
  <ul class="k3-points">
%s
  </ul>
  <p class="k3-note">%s</p>
  %s
  <p class="k3-tail">%s</p>
  <div class="k-ghost k3-ghost">03</div>
  %s
  %s""" % (esc(eyebrow), cls_by_len(title, "", " k3-title--m", " k3-title--s", " k3-title--s"),
              esc(title), rows, esc(p["line"]), facts_html(p), tail_html, photo_html, detail_html)
    return frame(p, 3, body, "quiet")


# --------------------------------------------------------------------------
# SLIDE 04 · ФИНАЛ / CTA
# --------------------------------------------------------------------------

def slide04(p):
    title = get(p, "s4_title", p["name"])
    offer = get(p, "s4_offer", "СУПЕРЦЕНА")
    bullets = get(p, "s4_bullets") or p["benefits"]
    price = get(p, "s4_price", p["price_note"])
    cta = get(p, "s4_cta", "Напиши в Telegram — пришлём цену")
    bullets_html = "\n".join('      <div class="k4-bullet">%s</div>' % esc(b) for b in bullets[:4])
    photo = p["photo"]
    photo_html = ('<div class="k4-photo"><img src="%s" alt="%s"></div>'
                  % (photo, esc(p["name_full"]))) if photo else ""
    body = """  <div class="k4-head">
    <span class="k4-badge">%s</span>
    <h1 class="k4-title%s">%s</h1>
  </div>
  <div class="k4-price">
    <span class="k4-price__k">Цена</span>
    <span class="k4-price__v">%s</span>
    <span class="k4-price__n">%s</span>
  </div>
  <div class="k4-bullets">
%s
  </div>
  <div class="k4-cta">
    <div>
      <span class="k4-cta__t">Напиши в Telegram</span>
      <span class="k4-cta__s">@vokope_ru · +7 (999) 136-71-42</span>
    </div>
    <span class="k4-cta__arrow">→</span>
  </div>
  <div class="k4-end">Конец серии · 04/04</div>
  <div class="k-ghost k4-ghost">04</div>
  %s""" % (esc(offer), cls_by_len(title, "", " k4-title--m", " k4-title--s", " k4-title--s"),
              esc(title), esc(price), esc(cta), bullets_html, photo_html)
    return frame(p, 4, body, "field")


BUILDERS = [slide01, slide02, slide03, slide04]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HTML_DIR)
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", default="")
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()

    positions = load()
    only = {x.strip().lower() for x in (args.preview or args.only).split(",") if x.strip()}
    selected = [p for p in positions if not only or p["id"].lower() in only]
    preview = bool(args.preview)
    out = os.path.join(HERE, "preview_carousel") if preview else args.out

    global ASSET
    if preview:
        ASSET = "../../../02_ДИЗАЙН/"
        for p in positions:
            if p.get("photo"):
                p["photo"] = (p["photo"].replace("../../02_ДИЗАЙН/", "../../../02_ДИЗАЙН/")
                              .replace("../../../kilowatt/", "../../../../kilowatt/"))

    if args.clean and os.path.isdir(out):
        for name in os.listdir(out):
            path = os.path.join(out, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)

    made = 0
    for p in selected:
        folder = os.path.join(out, p["folder"])
        os.makedirs(folder, exist_ok=True)
        for fname, builder in zip(SLIDES, BUILDERS):
            html_out = builder(p)
            with open(os.path.join(folder, fname), "w", encoding="utf-8", newline="\n") as f:
                f.write(html_out)
            made += 1
        print("  %-6s %-36s %s" % (p["id"], p["name"][:36], p["folder"]))
    print("Готово: %d слайдов в %s" % (made, out))


if __name__ == "__main__":
    main()
