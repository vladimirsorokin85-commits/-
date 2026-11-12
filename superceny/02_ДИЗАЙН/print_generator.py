#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
«СОРВАННЫЙ ЦЕННИК» — генератор печатной спецпрайс-листовки v5.
4 страницы: 01 ЛИСТАЙ · 02 ЦИФРЫ · 03 СЦЕНАРИИ · 04 CTA.

Тексты — positions.json v6 (s1…s4). Фото — вырезки без фона, duotone через
инлайн SVG-фильтр; при наличии img/print/<id>_duo.png используется он.

  python print_generator.py --preview kw-05,kw-20,kw-09   # 3 образцовые серии
  python print_generator.py --clean                        # все 81 HTML
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
PRINT_IMG = os.path.join(HERE, "img", "print")
DRAFT_PRICES = {}
try:
    DRAFT_PRICES = json.load(open(os.path.join(HERE, "_prices_draft.json"), encoding="utf-8"))
except Exception:
    DRAFT_PRICES = {}

SLIDES = ["01_ЛИСТАЙ.html", "02_ЦИФРЫ.html", "03_СЦЕНАРИИ.html", "04_CTA.html"]
LEGAL = ("Характеристики — по паспорту изделия. Не является публичной офертой. "
         "РЭС: порядок применения — по законодательству РФ.")
ASSET = "../../02_ДИЗАЙН/"
TEL = "+7 (999) 136-71-42"
TG = "@vokope_ru"


def esc(x):
    return html.escape(str(x if x is not None else ""), quote=False)


def load():
    spec = importlib.util.spec_from_file_location("kgen", os.path.join(HERE, "generator.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    raw = json.load(open(POSITIONS, encoding="utf-8-sig"))
    if isinstance(raw, dict):
        raw = raw.get("positions") or raw.get("items") or []
    out = []
    for idx, item in enumerate(raw, 1):
        p = g.normalize(item, idx)
        car = {}
        for k, v in item.items():
            if len(k) > 2 and k[0] == "s" and k[1] in "1234" and v not in (None, "", []):
                car[k] = v
        p["car"] = car
        pid = p["id"]
        p["price_value"] = item.get("price_value")
        p["price_display"] = item.get("price_display")
        p["has_price"] = item.get("has_price")
        p["price_note"] = item.get("price_note") or "розница, ноябрь 2026"
        if p["price_value"] in (None, "") and DRAFT_PRICES.get(pid) is not None:
            p["price_value"] = DRAFT_PRICES[pid]
            p["price_display"] = "{:,}".format(int(DRAFT_PRICES[pid])).replace(",", " ") + " ₽"
            p["has_price"] = True
        main = os.path.join(HERE, "img", pid + "_main.png")
        duo = os.path.join(PRINT_IMG, pid + "_duo.png")
        duo_zoom = os.path.join(PRINT_IMG, pid + "_duo_zoom.png")
        if os.path.isfile(duo):
            p["photo"] = "../../02_ДИЗАЙН/img/print/" + pid + "_duo.png"
            p["photo_zoom"] = p["photo"]
        out.append(p)
    return out


def get(p, key, default=""):
    v = p["car"].get(key)
    return v if v not in (None, "", []) else default


# --------------------------------------------------------------------------
# служебные элементы страницы
# --------------------------------------------------------------------------

def page_head(asset):
    return """  <svg class="filters" width="0" height="0" aria-hidden="true" focusable="false">
    <filter id="duo" color-interpolation-filters="sRGB">
      <feColorMatrix type="saturate" values="0"/>
      <feComponentTransfer>
        <feFuncR type="linear" slope="0.84" intercept="0.13"/>
        <feFuncG type="linear" slope="0.21" intercept="0.10"/>
        <feFuncB type="linear" slope="0.18" intercept="0.08"/>
      </feComponentTransfer>
    </filter>
  </svg>""" % {}


def photo(p, cls=None, style=""):
    photo = p["photo"]
    if not photo:
        return ""
    is_print = "/img/print/" in photo
    cls = cls or ("duo-print" if is_print else "duo")
    return '<img class="%s" src="%s" alt="%s" style="%s">' % (
        cls, photo, esc(p["name_full"]), style)


def photo_zoom(p, cls=None, style=""):
    photo = p.get("photo_zoom") or p["photo"]
    if not photo:
        return ""
    is_print = "/img/print/" in photo
    cls = cls or ("duo-print" if is_print else "duo")
    return '<img class="%s" src="%s" alt="%s" style="%s">' % (
        cls, photo, esc(p["name_full"]), style)


def reg_marks():
    return """  <i class="reg reg--tl"></i><i class="reg reg--tr"></i>
  <i class="reg reg--bl"></i><i class="reg reg--br"></i>
  <i class="reg-dot" style="left:300px;top:26px"></i>
  <i class="reg-dot" style="right:260px;top:26px"></i>"""


def thread(perf_h=22):
    return """  <i class="perf-edge" style="height:%d%%"></i>
  <i class="thread"></i>""" % perf_h


def tag_frag(p, mode="price"):
    if mode == "plain":
        return """  <div class="tag tag--frag tag-frag" aria-hidden="true">
    <span class="tag__k">СУПЕРЦЕНА</span>
    <span class="tag__v" style="font-size:38px;line-height:0.95">ЦЕНА<br>НА 4-Й</span>
    <span class="tag__note">смотри финал →</span>
  </div>"""
    if mode == "med":
        if p.get("has_price") and p.get("price_display"):
            num = price_num(p)
            fs = min(price_font(price_display(p)), 54)
            inner = ('<span class="tag__v" style="font-size:%dpx;line-height:0.95">%s <i class="rub">руб.</i></span>'
                     '<span class="tag__note">оторви купон на 4-й</span>' % (fs, esc(num)))
        else:
            inner = ('<span class="tag__v" style="font-size:34px;line-height:1.02">ПРАЙС<br>ПО ЗАПРОСУ</span>'
                     '<span class="tag__note">цена — на 4-й</span>')
        return """  <div class="tag tag--frag tag-frag" aria-hidden="true">
    <span class="tag__k">СУПЕРЦЕНА</span>
    %s
  </div>""" % inner
    return """  <div class="tag tag--frag tag-frag" aria-hidden="true">
    %s
  </div>""" % price_tag_html(p)


def price_font_frag(text):
    n = len(text)
    if n <= 7:
        return 70
    if n <= 9:
        return 56
    if n <= 12:
        return 44
    return 36


def price_tag_html(p, note_prefix="розница"):
    if not (p.get("has_price") and p.get("price_display")):
        return ('<span class="tag__k">СУПЕРЦЕНА · НПО «КИЛОВАТТ»</span>'
                '<span class="tag__v" style="font-size:34px;line-height:1.02">ПРАЙС<br>ПО ЗАПРОСУ</span>'
                '<span class="tag__note">прайс по запросу</span>')
    num = price_num(p)
    fs = price_font_frag(price_display(p))
    return ('<span class="tag__k">СУПЕРЦЕНА · НПО «КИЛОВАТТ»</span>'
            '<span class="tag__v" style="font-size:%dpx;line-height:0.92">%s <i class="rub">руб.</i></span>'
            % (fs, esc(num)))


def price_display(p):
    if p.get("has_price") and p.get("price_display"):
        return str(p["price_display"]).replace("\u00a0", " ").replace("\u202f", " ").strip()
    return "ПРАЙС ПО ЗАПРОСУ"


def price_num(p):
    if p.get("has_price") and p.get("price_display"):
        return price_display(p).replace("₽", "").replace("руб.", "").strip()
    return None


def price_font(text):
    n = len(text or "")
    if n <= 7:
        return 96
    if n <= 9:
        return 84
    if n <= 12:
        return 64
    return 52


def stamp(text="СУПЕРЦЕНА"):
    return """  <div class="stamp" aria-hidden="true"><span>%s</span><b>НПО «КИЛОВАТТ»</b></div>""" % esc(text)


def page_num(idx):
    return """  <div class="pnum"><span class="stencil">0%d</span><em>/</em>04</div>""" % idx


def foot(has_price=False):
    line = ("Розничные цены · доставка по РФ · самовывоз в Москве" if has_price
            else "Прайс по запросу · доставка по РФ · самовывоз в Москве")
    return """  <div class="foot"><span>%s</span><span>%s</span><span>%s</span></div>
  <div class="legal">%s</div>""" % (TG, TEL, line, LEGAL)


def nav_hint(text, arrow=True):
    arrow_svg = ""
    if arrow:
        arrow_svg = ('<svg width="72" height="30" viewBox="0 0 72 30" fill="none">'
                     '<path d="M2 22 C22 6, 44 4, 66 13" stroke="#E23B2E" stroke-width="4" stroke-linecap="round"/>'
                     '<path d="M56 4 L68 13 L54 20" stroke="#E23B2E" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
                     '</svg>')
    return '  <div class="nav-hint"><span>%s</span>%s</div>' % (esc(text), arrow_svg)


def html_page(p, idx, title, body, extra_class=""):
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s · %(num)02d/04 · «В ОКОПЕ»</title>
<link rel="stylesheet" href="%(asset)stokens.css">
<link rel="stylesheet" href="%(asset)sprint.css">
<style>
  .perf-edge { position:absolute; right:22px; top:0; width:0; border-left:2px dashed rgba(23,21,15,.45); z-index:42; }
</style>
</head>
<body class="theme-quiet">
<main class="pg pg--%(idx)02d %(cls)s">
%(head)s
%(reg)s
%(thread)s
%(body)s
  <div class="safe-zone"></div>
%(pnum)s
%(foot)s
</main>
</body>
</html>
""" % {"title": esc(title), "num": idx, "asset": ASSET, "idx": idx, "cls": extra_class,
       "head": page_head(ASSET), "reg": reg_marks(), "thread": thread(18 + idx * 20),
       "body": body, "pnum": page_num(idx), "foot": foot(bool(p.get("has_price")))}


# --------------------------------------------------------------------------
# 01 · ЛИСТАЙ
# --------------------------------------------------------------------------

def page01(p):
    name = get(p, "s1_title", p["name"]).upper()
    kicker = get(p, "s1_kicker", p["hook"])
    claim = get(p, "s1_claim", "")
    sub = get(p, "s1_sub", p["line"])
    ncls = "t-giant"
    if len(name) > 9:
        ncls = "t-giant"
    body = """  <p class="kick cover-kick">%s <span style="color:var(--red)">· спецпрайс-листовка</span></p>
  <div class="cover-title"><h1 class="%s" style="font-size:%dpx">%s</h1></div>
  <p class="cover-claim">%s</p>
  <p class="sub cover-sub">%s</p>
  <p class="cover-fullname">%s</p>
  %s
  %s
  %s
  %s
  %s""" % (esc(kicker), ncls, (300 if len(name) <= 6 else 250 if len(name) <= 8 else 200 if len(name) <= 10 else 160 if len(name) <= 13 else 132),
              esc(name), esc(claim), esc(sub), esc(p["name_full"].upper()), photo_zoom(p), tag_frag(p, "price"), stamp("СУПЕРЦЕНА"),
              nav_hint("ЛИСТАЙ"), "")
    return html_page(p, 1, p["name"], body)


# --------------------------------------------------------------------------
# 02 · ЦИФРЫ
# --------------------------------------------------------------------------

def stat_font(value):
    n = len(str(value))
    if n <= 4:
        return 176
    if n <= 6:
        return 148
    if n <= 8:
        return 118
    if n <= 11:
        return 92
    return 72


def page02(p):
    lead = get(p, "s2_lead", "ВНУТРИ —")
    stats = get(p, "s2_stats") or [{"value": "—", "label": "характеристики", "note": ""}]
    rows = []
    for s in stats[:4]:
        value = str(s.get("value", ""))
        rows.append("""  <div class="stat-print">
    <span class="num stencil" style="font-size:%dpx">%s</span>%s
    <span class="meta"><b>%s</b><span>%s</span></span>
  </div>""" % (stat_font(value), esc(value),
               ('<span class="num-plain">%s</span>' % esc(value)) if value.isdigit() and len(value) <= 2 else "",
               esc(s.get("label", "")), esc(s.get("note", ""))))
    body = """  <div class="lead"><p class="kick">Внутри —</p>
    <span class="lead-sub">%s</span></div>
  <div class="stats">
%s
  </div>
  %s
  %s
  %s
  %s""" % (esc(lead), "\n".join(rows), photo_zoom(p), tag_frag(p, "plain"),
           nav_hint("КОМУ?"), stamp("СУПЕРЦЕНА"))
    return html_page(p, 2, p["name"] + " · цифры", body)


# --------------------------------------------------------------------------
# 03 · СЦЕНАРИИ
# --------------------------------------------------------------------------

def page03(p):
    title = get(p, "s3_title", "КОМУ ЭТО НАДО").upper()
    points = get(p, "s3_points") or p["tasks"]
    tail = get(p, "s3_tail", "ОСТАЛОСЬ ГЛАВНОЕ — ЦЕНА")
    words = []
    for i, w in enumerate(points[:4], 1):
        words.append("""  <div class="word"><span class="n">0%d</span><span class="w">%s</span></div>""" % (i, esc(w)))
    tail_html = esc(tail).replace("—", "<em>—").replace("<em>", "<em>", )
    if "—" in tail:
        a, b = tail.split("—", 1)
        tail_html = esc(a) + "<em>— " + esc(b.strip()) + "</em>"
    body = """  <div class="head"><p class="kick">Применение</p>
    <h1 class="t-big">%s</h1></div>
  <div class="words">
%s
  </div>
  <p class="tail">%s</p>
  %s
  %s
  %s
  %s""" % (esc(title), "\n".join(words), tail_html, photo(p), tag_frag(p, "med"),
           nav_hint("ЦЕНА"), stamp("СУПЕРЦЕНА"))
    return html_page(p, 3, p["name"] + " · сценарии", body)


# --------------------------------------------------------------------------
# 04 · CTA
# --------------------------------------------------------------------------

def page04(p):
    offer = get(p, "s4_offer", "СУПЕРЦЕНА")
    tag_k = offer + (" · розница, ноябрь 2026" if p.get("has_price") else " · прайс по запросу")
    has_price = bool(p.get("has_price") and p.get("price_display"))
    if has_price:
        price = ('<span class="price-big" style="font-size:%dpx">%s <i class="rub">руб.</i></span>'
                 % (price_font(price_num(p)) + 8 + 6, esc(price_num(p))))
    else:
        price = '<span class="price-big" style="font-size:62px">ПРАЙС ПО ЗАПРОСУ</span>' 
    bullets = get(p, "s4_bullets") or p["benefits"]
    bullets_line = " · ".join(str(b) for b in bullets[:4])
    if p.get("has_price"):
        cta = "Напиши в Telegram — забронируем и пришлём КП"
        coupon_note = "цена розница — @vokope_ru"
        contact_note = "цена и бронь в ответ"
    else:
        cta = get(p, "s4_cta", "Напиши — пришлём цену")
        coupon_note = "прайс по запросу — @vokope_ru"
        contact_note = "прайс по запросу в ответ"
    body = """  <p class="kick end-kick">Конец серии · 04/04</p>
  <div class="tag tag--full" aria-hidden="true">
    <span class="tag__k">%s</span>
    <span class="tag__v">%s</span>
    <span class="tag__note">%s</span>
    <span class="tag__note" style="margin-top:14px">%s</span>
    <i class="tag__perf"></i>
    <i class="tag__hole"></i>
  </div>
  <div class="tag tag--coupon" aria-hidden="true">
    <span class="tag__k">отрывной купон</span>
    <span class="tag__v">ОТОРВИ<br>И НАПИШИ</span>
    <span class="tag__note">%s</span>
    <i class="tag__perf"></i>
    <i class="tag__hole"></i>
  </div>
  %s
  %s
  <div class="contact">Telegram: <b>@vokope_ru</b><small>+7 (999) 136-71-42 · %s</small></div>
  %s""" % (esc(tag_k), price, esc(bullets_line), esc(cta), esc(coupon_note),
           photo(p), stamp("ПИШИ"), esc(contact_note), nav_hint("ПИШИ"))
    return html_page(p, 4, p["name"] + " · прайс", body)




# --------------------------------------------------------------------------
# HERO · 00_СУПЕРЦЕНЫ (обложка всей серии)
# --------------------------------------------------------------------------

def hero(positions):
    hasset = ASSET.replace("../", "", 1)
    picks = [p for p in positions if p.get("photo")][:5]
    imgs = []
    geo = [(14, 760, 250, 8), (230, 735, 270, -6), (470, 770, 240, 5), (680, 740, 255, -9), (900, 775, 220, 3)]
    for p, (x, y, w, rot) in zip(picks, geo):
        src = p["photo"].replace("../../", "../", 1)
        imgs.append('<img class="hero-prod" src="%s" alt="%s" style="left:%dpx;top:%dpx;width:%dpx;transform:rotate(%ddeg)">'
                    % (src, esc(p["name_full"]), x, y, w, rot))
    collage = "\n  ".join(imgs)
    nums = []
    for p in positions:
        try:
            if p.get("has_price") and p.get("price_value"):
                nums.append(int(p["price_value"]))
        except Exception:
            pass
    if nums:
        hero_price = "ОТ {:,}".format(min(nums)).replace(",", " ") + ' <i class="rub">руб.</i>'
        hero_note = "20 позиций · розница, ноябрь 2026"
        hero_foot = "Розничные цены · доставка по РФ · самовывоз в Москве"
    else:
        hero_price = "ПРАЙС<br>ПО ЗАПРОСУ"
        hero_note = "20 позиций · цены в карточках"
        hero_foot = "Прайс по запросу · доставка по РФ · самовывоз в Москве"
    body = """  <p class="kick hero-kick">Магазин «В ОКОПЕ» · спецпрайс 11.2026</p>
  <h1 class="hero-title">СУПЕР<span>ЦЕНЫ</span></h1>
  <p class="hero-sub">на всю линейку НПО «Киловатт» · 20 позиций прайса · 4 страницы на модель</p>
  <h2 class="hero-sub2">цену сорвали — спрашивай</h2>
  <div class="hero-tag tag" aria-hidden="true">
    <span class="tag__k">спецпрайс-листовка · 20 позиций</span>
    <span class="tag__v" style="font-size:64px">%s</span>
    <span class="tag__note">%s</span>
    <i class="tag__perf"></i>
    <i class="tag__hole"></i>
  </div>
  %s
  <div class="stamp" style="left:64px;bottom:250px"><span>СУПЕРЦЕНА</span><b>НПО «КИЛОВАТТ»</b></div>
  <div class="contact" style="bottom:170px">Telegram: <b>@vokope_ru</b><small>+7 (999) 136-71-42 · прайс по запросу</small></div>
  <div class="nav-hint" style="right:66px;bottom:170px"><span>СМОТРИ</span>
    <svg width="72" height="30" viewBox="0 0 72 30" fill="none"><path d="M2 22 C22 6, 44 4, 66 13" stroke="#E23B2E" stroke-width="4" stroke-linecap="round"/><path d="M56 4 L68 13 L54 20" stroke="#E23B2E" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
  </div>""" % (hero_price, hero_note, collage)
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>СУПЕРЦЕНЫ НА НПО «КИЛОВАТТ» · печатная спецпрайс-листовка</title>
<link rel="stylesheet" href="%(asset)stokens.css">
<link rel="stylesheet" href="%(asset)sprint.css">
<style>
  .perf-edge { position:absolute; right:22px; top:0; width:0; border-left:2px dashed rgba(23,21,15,.45); z-index:42; }
</style>
</head>
<body class="theme-quiet">
<main class="pg pg--hero">
  <i class="reg reg--tl"></i><i class="reg reg--tr"></i><i class="reg reg--bl"></i><i class="reg reg--br"></i>
  <i class="perf-edge" style="height:90%%"></i>
  <i class="thread"></i>
  %(body)s
  <div class="safe-zone"></div>
  <div class="foot"><span>@vokope_ru</span><span>+7 (999) 136-71-42</span><span>%(footline)s</span></div>
  <div class="legal">%(legal)s</div>
</main>
</body>
</html>
""" % {"asset": hasset, "body": body, "legal": LEGAL, "footline": hero_foot}


BUILDERS = [page01, page02, page03, page04]


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    global ASSET
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
    out = os.path.join(HERE, "preview_print") if preview else args.out

    if preview:
        ASSET = "../../../02_ДИЗАЙН/"
        for p in positions:
            for key in ("photo", "photo_zoom"):
                if p.get(key):
                    p[key] = (p[key].replace("../../02_ДИЗАЙН/", "../../../02_ДИЗАЙН/")
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
            with open(os.path.join(folder, fname), "w", encoding="utf-8", newline="\n") as f:
                f.write(builder(p))
            made += 1
        print("  %-6s %-36s %s" % (p["id"], p["name"][:36], p["folder"]))
    if not only:
        with open(os.path.join(out, "00_СУПЕРЦЕНЫ.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(hero(selected))
        made += 1
        print("  HERO 00_СУПЕРЦЕНЫ.html")
    print("Готово: %d страниц в %s" % (made, out))


if __name__ == "__main__":
    main()
