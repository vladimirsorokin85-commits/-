# -*- coding: utf-8 -*-
"""Генератор печатного A4-каталога «В ОКОПЕ» в стиле «ведомость» (светлый вариант).
Источник данных: kilowatt/catalog/_tools/out/catalog_build.json
Выход: kilowatt/print/print-light.html (ссылки ../catalog/assets/...)
"""
import html
import json
import os
import re

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)  # kilowatt/print
DATA = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt\catalog\_tools\out\catalog_build.json"
A = "../catalog/assets"
HERO = "_assets/hero.jpg"
ASSETS = os.path.join(OUT, "_assets")
ASSETS_PRODUCTS = os.path.join(ASSETS, "products")
PAPER = (244, 241, 234)
PAPER_HI = (250, 247, 240)
LOGO = A + "/img/brand/logo_w_emblem.png"
QR = A + "/img/qr-phone.svg"

TOTAL_PAGES = 11
PHONE = "+7 (999) 136-71-42"
PRICE_NOTE = "Цены поставщика — ориентир, не публичная оферта"

CATS = [
    dict(key="kupolnye", name="Купольные станции", short="Купольные",
         desc="Купол на крышу кабины, КУНГа или верхнюю точку техники: 8–12 каналов, до 240 Вт."),
    dict(key="staczionarnye", name="Стационарные", short="Стационарные",
         desc="Направленные и круговые комплексы для площадных объектов: до 2400 Вт, до 1000 м."),
    dict(key="perenosnye", name="Переносные (рюкзаки)", short="Переносные",
         desc="Тактические станции в рюкзаке: 20–100 Вт, Li-ion и LiFePO4, автономность до 5 часов."),
    dict(key="detektory", name="Детекторы БПЛА", short="Детекторы",
         desc="Пассивное обнаружение на 300–10000 МГц, 1000–5000 м по прямой видимости."),
    dict(key="moduli", name="Доп. модули", short="Модули",
         desc="Однодиапазонные модули 140–200 МГц и другие полосы — расширяют диапазон станции."),
    dict(key="aksessuary", name="Аксессуары", short="Аксессуары",
         desc="Питание, кронштейны, треноги, преобразователи, разветвители и РЭБ-тестер."),
]
CAT_BY_NAME = {c["name"]: c for c in CATS}


# ---------------------------------------------------------------------------
# данные
# ---------------------------------------------------------------------------
def _spec(p, *labels):
    for s in p.get("specs") or []:
        lab = (s.get("label") or "").strip().lower()
        for want in labels:
            if lab == want.lower():
                return (s.get("value") or "").strip()
    return None


def _clean(v):
    if not v:
        return None
    v = re.sub(r"\s*\([^)]*\)", "", v).strip().strip(" .;,")
    return v or None


def freq_span(p):
    v = _spec(p, "Диапазон частот")
    if not v:
        return None
    nums = [int(n) for n in re.findall(r"\d+", v)]
    if not nums:
        return None
    lo, hi = min(nums), max(nums)
    unit = "ГГц" if "ГГц" in v else "МГц"
    return ("%d %s" % (lo, unit)) if lo == hi else ("%d–%d %s" % (lo, hi, unit))


def power_short(p):
    v = _spec(p, "Мощность передатчиков", "Суммарная выходная мощность", "Мощность")
    if not v:
        return None
    m = re.search(r"(до|от|не более)?\s*([\d\s,.–-]*\d)\s*(кВт|Вт)", v)
    if not m:
        return None
    pre = (m.group(1) or "").strip()
    num = m.group(2).strip(" ,.")
    return ("%s %s %s" % (pre, num, m.group(3))).strip() if pre else ("%s %s" % (num, m.group(3)))


def range_short(p):
    v = _spec(p, "Дальность подавления", "Дальность обнаружения", "Дальность")
    if not v:
        return None
    v = _clean(v)
    return v.split(";")[0].strip() if v else None


def channels_short(p):
    v = _spec(p, "Каналов подавления", "Генераторов помех", "Каналов")
    m = re.search(r"\d+", v or "")
    return m.group(0) if m else None


def weight_short(p):
    v = _spec(p, "Вес", "Вес нетто", "Масса")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*кг", v or "")
    return m.group(1).replace(",", ".") + " кг" if m else None


def size_short(p):
    v = _spec(p, "Габариты", "Габариты моноблока", "Размер")
    v = _clean(v)
    if not v:
        return None
    v = v.split(";")[0].strip()
    return v.split(",")[0].strip() if len(v) > 24 and "," in v else v


def capacity_short(p):
    v = _spec(p, "Ёмкость / напряжение", "Ёмкость")
    return _clean(v)


def height_short(p):
    return _clean(_spec(p, "Высота в рабочем положении", "Высота"))


def mount_sizes(p):
    """Кронштейны 500/600/700: «500/600/700 мм» из полей «Размер под купол…»."""
    out = []
    for sp in p.get("specs") or []:
        lab = (sp.get("label") or "").lower()
        if "размер под купол" in lab:
            m = re.search(r"(\d{3})", sp.get("value") or "")
            if m:
                out.append(m.group(1))
    return ("/".join(out) + " мм") if out else None


def rub(v):
    if not v:
        return "по запросу"
    return "{:,}".format(int(v)).replace(",", "\u00a0") + "\u00a0₽"


def esc(s):
    return html.escape(s or "", quote=True)


def row_facts(p):
    access = p.get("category") == "Аксессуары"
    order = ([("Габариты", size_short), ("Вес", weight_short), ("АКБ", capacity_short),
              ("Высота", height_short), ("Под купол", mount_sizes), ("Диапазон", freq_span),
              ("Мощность", power_short)]
             if access else
             [("Диапазон", freq_span), ("Мощность", power_short), ("Дальность", range_short),
              ("Каналов", channels_short), ("Вес", weight_short), ("Габариты", size_short)])
    out = []
    for label, fn in order:
        try:
            v = fn(p)
        except Exception:
            v = None
        if v:
            out.append((label, v))
        if len(out) >= 3:
            break
    if not out and not p.get("on_site"):
        return []
    if not out:
        for sp in (p.get("specs") or []):
            v = _clean(sp.get("value") or "")
            if not v:
                continue
            v = v.split(";")[0].strip()
            if len(v) > 25:
                v = v[:24].rstrip() + "…"
            out.append(((sp.get("label") or "").strip(), v))
            if len(out) >= 3:
                break
    return out


def flag_specs(p):
    pref = ["Диапазон частот", "Каналов подавления", "Генераторов помех",
            "Мощность передатчиков", "Дальность подавления", "Питание",
            "Время работы", "Время непрерывной работы", "Вес", "Вес нетто"]
    rows = []
    for lab in pref:
        v = _spec(p, lab)
        if v:
            rows.append((lab, v))
        if len(rows) >= 6:
            break
    return rows


def cmp_value(p, label):
    if label == "Диапазон":
        v = _spec(p, "Диапазон частот")
    elif label == "Мощность":
        v = _spec(p, "Мощность передатчиков", "Суммарная выходная мощность")
    elif label == "Дальность":
        v = _spec(p, "Дальность подавления", "Дальность обнаружения")
    elif label == "Питание":
        v = _spec(p, "Питание")
    elif label == "Вес":
        v = _spec(p, "Вес", "Вес нетто", "Масса")
    elif label == "Гарантия":
        v = _spec(p, "Гарантия") or "12 месяцев"
    else:
        v = _spec(p, label)
    return _clean(v) or "—"


def load():
    prods = json.load(open(DATA, encoding="utf-8"))["products"]
    for p in prods:
        p["facts"] = row_facts(p)
        p["price"] = rub(p.get("price_dima"))
        p["archive"] = not bool(p.get("on_site"))
        p["status"] = "вне сайта" if p["archive"] else (p.get("availability") or "уточняется")
        p["photo"] = (A + "/" + p["photos"][0].replace("assets/", "", 1)) if p.get("photos") else None
        p["cat"] = CAT_BY_NAME[p["category"]]

    def order(p):
        return (0 if p.get("flagship") else 1, 0 if not p["archive"] else 1,
                0 if p["photo"] else 1, -(p.get("price_dima") or 0), p["name"])

    groups = {}
    for c in CATS:
        items = [p for p in prods if p["category"] == c["name"]]
        items.sort(key=order)
        groups[c["key"]] = items
    n = 0
    for c in CATS:
        for p in groups[c["key"]]:
            n += 1
            p["num"] = n
    flags = [p for p in prods if p.get("flagship")]
    flags.sort(key=lambda p: ["kw-06", "kw-17", "kw-15"].index(p["id"]))
    return dict(products=prods, groups=groups, flags=flags, total=len(prods),
                archived=sum(1 for p in prods if p["archive"]),
                priced=sum(1 for p in prods if p.get("price_dima")),
                counts={c["key"]: len(groups[c["key"]]) for c in CATS})


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = r"""
@page { size: A4; margin: 0; }
@font-face { font-family:"Oswald"; src:url("../catalog/assets/fonts/Oswald-VF.ttf") format("truetype"); font-weight:200 700; font-display:swap; }
@font-face { font-family:"Sofia"; src:url("../catalog/assets/fonts/SofiaSansExtraCondensed-VF.ttf") format("truetype"); font-weight:100 900; font-display:swap; }
@font-face { font-family:"Tektur"; src:url("../catalog/assets/fonts/Tektur-VF.ttf") format("truetype"); font-weight:400 900; font-display:swap; }
@font-face { font-family:"Unbounded"; src:url("../catalog/assets/fonts/Unbounded-VF.ttf") format("truetype"); font-weight:200 900; font-display:swap; }

:root{
  --paper:#f4f1ea; --paper-hi:#faf7f0; --paper-lo:#e9e2d1;
  --ink:#1d1e1a; --graphite:#2a2b26; --muted:#63665a;
  --accent:#c8451f; --accent-dim:rgba(200,69,31,.16);
  --line:rgba(29,30,26,.18); --line-hard:rgba(29,30,26,.46);
}
*{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}
html,body{margin:0;padding:0;background:var(--paper);color:var(--ink)}
body{font-family:"Sofia",Arial,sans-serif;font-size:8.2pt;line-height:1.32;-webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}
figure,dl,dd,dt{margin:0}
p{margin:0 0 2.2mm}
h1,h2,h3,h4{margin:0}
.page{position:relative;width:210mm;height:297mm;page-break-after:always;overflow:hidden;background:var(--paper);padding:14mm 15mm 16mm}
.page:last-child{page-break-after:auto}
.pg-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:0.4pt solid var(--line-hard);padding-bottom:2.4mm;margin-bottom:4.6mm}
.pg-head b{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;letter-spacing:.08em;font-size:8pt}
.pg-head span{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}
.pg-foot{position:absolute;left:15mm;right:15mm;bottom:7mm;display:flex;justify-content:space-between;align-items:baseline;border-top:0.4pt solid var(--line);padding-top:2mm;font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.sec-num{font-family:"Tektur",monospace;font-size:6pt;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.sec-title{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;line-height:1.0;font-size:28pt;letter-spacing:.005em}
.lead-osw{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:11pt;line-height:1.14;margin:0 0 3mm}
.tech{font-family:"Tektur",monospace;font-variant-numeric:tabular-nums}
.muted{color:var(--muted)}
.tiny{font-size:6.4pt;line-height:1.42;color:var(--muted)}
.hair{border-top:0.4pt solid var(--line)}
.hair-hard{border-top:0.9pt solid var(--line-hard)}
.stamp{display:inline-block;border:.5pt solid var(--accent);color:var(--accent);font-family:"Tektur",monospace;font-size:5.2pt;letter-spacing:.16em;padding:1.2mm 2mm;transform:rotate(-2deg);margin-top:2mm}

/* ---------- ОБЛОЖКА ---------- */
.page--cover{padding:15mm 16mm 13mm}
.cover__top{display:flex;justify-content:space-between;align-items:flex-start}
.cover__brand{display:flex;align-items:center;gap:3.2mm}
.cover__mark{width:11mm;height:11mm;background:var(--ink);display:flex;align-items:center;justify-content:center;flex:none}
.cover__mark img{height:8.4mm;width:auto}
.cover__brand b{display:block;font-family:"Oswald","Arial Narrow",sans-serif;font-weight:600;font-size:11.5pt;letter-spacing:.04em;text-transform:uppercase;line-height:1}
.cover__brand i{display:block;font-style:normal;font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-top:1mm}
.cover__meta{text-align:right;font-family:"Tektur",monospace;font-size:5.8pt;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);line-height:1.8}
.cover__kicker{display:flex;align-items:center;gap:3mm;margin-top:15mm;font-family:"Tektur",monospace;font-size:5.8pt;letter-spacing:.15em;text-transform:uppercase;color:var(--muted)}
.cover__kicker::before{content:"";width:22mm;height:0.7mm;background:var(--accent);flex:none}
.cover__title{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:55pt;line-height:.9;letter-spacing:-.012em;margin-top:4mm}
.cover__title span{display:block}
.cover__title .out{color:transparent;-webkit-text-stroke:.9pt var(--ink);text-stroke:.9pt var(--ink)}
.cover__title .mark{position:relative;z-index:0;white-space:nowrap;display:inline-block}
.cover__title .mark::after{content:"";position:absolute;left:.015em;right:-.02em;bottom:.055em;height:.13em;background:var(--accent);z-index:-1;transform:skewX(-12deg)}
.cover__lead{font-size:9.4pt;line-height:1.4;color:var(--graphite);max-width:96mm;margin-top:5.5mm}
.cover__aside{position:absolute;right:16mm;top:61mm;width:58mm;border-top:0.4pt solid var(--line-hard);padding-top:2.4mm}
.cover__aside div{display:flex;justify-content:space-between;align-items:baseline;border-bottom:0.4pt solid var(--line);padding:1.5mm 0}
.cover__aside span{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.6pt;letter-spacing:.09em;color:var(--muted)}
.cover__aside b{font-family:"Tektur",monospace;font-weight:500;font-size:9pt}
.cover__zone{margin-top:2mm}
.cover__zone .zone{width:170mm;height:auto;overflow:visible}
.zone .z-ground,.zone .z-arc{fill:none;stroke:var(--ink);stroke-width:.45pt}
.zone .z-tick{stroke:var(--ink);stroke-width:.4pt}
.zone .z-label{font-family:"Tektur",monospace;font-size:6pt;letter-spacing:.09em;fill:var(--muted)}
.zone .z-label--accent{fill:var(--accent);font-size:7.2pt;letter-spacing:.03em}
.cover__zone .cap{font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);margin-top:1mm}
.cover__foot{position:absolute;left:16mm;right:16mm;bottom:13mm;border-top:0.5pt solid var(--line-hard);padding-top:5mm;display:flex;justify-content:space-between;align-items:flex-end;gap:8mm}
.cover__stats{display:flex;gap:9mm}
.cover__stat b{display:block;font-family:"Tektur",monospace;font-weight:600;font-size:13.5pt;letter-spacing:-.01em;line-height:1.05;white-space:nowrap}
.cover__stat span{display:block;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.7pt;letter-spacing:.11em;color:var(--muted);margin-top:1.4mm;line-height:1.25}
.cover__note{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-align:right;line-height:1.7}

/* ---------- 01 ПРОИЗВОДИТЕЛЬ ---------- */
.about{display:grid;grid-template-columns:112mm 1fr;gap:10mm;align-items:start}
.about__main .sec-title{font-size:25pt;line-height:1.0;margin:2mm 0 3.4mm}
.about__main p{font-size:8pt;line-height:1.44;color:var(--graphite);max-width:104mm}
.about__main p.lead-osw{font-size:10.5pt;color:var(--ink);max-width:96mm}
.about__side{border-top:0.9pt solid var(--line-hard);padding-top:3mm}
.facts3{display:flex;flex-direction:column}
.fact3{display:flex;flex-direction:column;gap:.6mm;border-bottom:0.4pt solid var(--line);padding:2.8mm 0}
.fact3 b{font-family:"Tektur",monospace;font-weight:500;font-size:19pt;line-height:1;letter-spacing:-.01em}
.fact3 span{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.7pt;letter-spacing:.1em;color:var(--muted)}
.about__docs{margin-top:5mm;border-top:0.9pt solid var(--line-hard);padding-top:2.6mm}
.dl{display:flex;flex-direction:column}
.dl div{display:grid;grid-template-columns:22mm 1fr;gap:2.5mm;border-bottom:0.4pt solid var(--line);padding:1.7mm 0}
.dl b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:6.1pt;letter-spacing:.06em;color:var(--muted)}
.dl span{font-family:"Tektur",monospace;font-size:6pt;line-height:1.35;color:var(--graphite)}
.orig{display:grid;grid-template-columns:56mm 1fr;gap:7mm;margin-top:5mm;background:var(--paper-lo);padding:5mm}
.orig h3{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:11pt;line-height:1.05;margin:0;color:var(--accent)}
.orig p{font-size:7pt;line-height:1.42;color:var(--graphite);margin:0}
.orig--stack{display:block}
.orig--stack h3{margin-bottom:2.4mm}
.comp{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:5mm;border-top:0.9pt solid var(--line-hard)}
.comp div{padding:3.2mm 4mm 3.2mm 0;border-left:0.4pt solid var(--line);display:flex;flex-direction:column;gap:1mm}
.comp div:first-child{border-left:0;padding-left:0}
.comp div:not(:first-child){padding-left:4mm}
.comp i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.12em;color:var(--accent)}
.comp b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:8pt;line-height:1.1}
.comp span{font-size:6.5pt;line-height:1.38;color:var(--muted)}
.lineup{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:5mm;border-top:0.9pt solid var(--line-hard)}
.lineup div{padding:2.8mm 4mm 2.8mm 0;border-left:0.4pt solid var(--line);display:grid;grid-template-columns:12mm 1fr;gap:0 2mm;align-items:baseline}
.lineup div:nth-child(3n+1){border-left:0;padding-left:0}
.lineup b{font-family:"Tektur",monospace;font-weight:500;font-size:15pt;line-height:1;letter-spacing:-.01em}
.lineup span{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6.2pt;letter-spacing:.06em;line-height:1.2}
.lineup i{grid-column:2;font-style:normal;font-size:6.1pt;line-height:1.32;color:var(--muted);margin-top:.6mm}

/* ---------- 02 ФЛАГМАНЫ ---------- */
.flag{display:grid;grid-template-columns:72mm 1fr;gap:8mm;border-top:0.9pt solid var(--line-hard);border-bottom:0.4pt solid var(--line);padding:5.4mm 0;page-break-inside:avoid}
.flag__media{height:56mm;border:0.4pt solid var(--line);background:var(--paper-hi);display:flex;align-items:center;justify-content:center;padding:2.4mm;overflow:hidden}
.flag__media img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain}
.nophoto-text{font-family:"Tektur",monospace;font-size:4.8pt;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);text-align:center;line-height:1.35}
.flag__kick{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}
.flag__name{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:19.5pt;line-height:.98;letter-spacing:-.005em;margin:1.4mm 0 2mm}
.flag__desc{font-size:7.7pt;line-height:1.4;color:var(--graphite);max-width:96mm;margin:0 0 2.4mm}
.flag__specs{width:100%;border-collapse:collapse}
.flag__specs td{padding:1.3mm 0;border-top:0.4pt solid var(--line);vertical-align:top;font-size:6.4pt;line-height:1.35}
.flag__specs td:first-child{width:30mm;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.7pt;letter-spacing:.06em;color:var(--muted);padding-right:3mm}
.flag__specs td:last-child{font-family:"Tektur",monospace;font-size:6.1pt;color:var(--graphite)}
.flag__foot{display:flex;align-items:baseline;gap:4mm;margin-top:2.2mm}
.flag__price{font-family:"Tektur",monospace;font-size:13pt;font-weight:600;letter-spacing:-.01em}
.flag__status{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.8pt;letter-spacing:.09em;color:var(--muted)}
.section-note{margin-top:3mm;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:space-between;gap:4mm}

/* ---------- 02.1 СРАВНЕНИЕ ---------- */
.cmp{width:100%;border-collapse:collapse;margin-top:3.4mm}
.cmp th,.cmp td{text-align:left;vertical-align:top;border-top:0.4pt solid var(--line);padding:3.1mm 2.6mm}
.cmp thead th{border-top:0.9pt solid var(--line-hard);padding:3.4mm 2.6mm 2.8mm}
.cmp__lab{width:29mm;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:6pt;letter-spacing:.06em;color:var(--muted)}
.cmp__cat{display:block;font-family:"Tektur",monospace;font-size:5.2pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:1.2mm}
.cmp__photo{height:47mm;display:flex;align-items:flex-end;justify-content:flex-start;margin-bottom:1.6mm}
.cmp__photo img{max-height:100%;max-width:100%;width:auto;object-fit:contain}
.cmp__name{display:block;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:11.5pt;line-height:1.02}
.cmp td{font-family:"Tektur",monospace;font-size:6.4pt;line-height:1.42;color:var(--graphite)}
.cmp tbody td:first-child{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6pt;letter-spacing:.05em;color:var(--muted)}
.cmp tfoot td{border-top:0.9pt solid var(--line-hard);border-bottom:0.9pt solid var(--line-hard);padding-top:3.2mm;padding-bottom:3.2mm}
.cmp tfoot td:first-child{color:var(--accent);font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6pt;letter-spacing:.06em}
.cmp__price{font-family:"Tektur",monospace;font-size:14pt;font-weight:600;letter-spacing:-.01em;line-height:1.1;white-space:nowrap}
.cmp__price small{display:block;font-family:"Oswald","Arial Narrow",sans-serif;font-size:5.4pt;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400;margin-top:1mm}
.cmp-note{display:flex;justify-content:space-between;gap:5mm;margin-top:3mm;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
.cmp-foot{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:5mm;border-top:0.9pt solid var(--line-hard);border-bottom:0.4pt solid var(--line)}
.cmp-foot div{padding:3.2mm 4mm 3.2mm 0;border-left:0.4pt solid var(--line);display:flex;flex-direction:column;gap:1mm}
.cmp-foot div:first-child{border-left:0;padding-left:0}
.cmp-foot div:not(:first-child){padding-left:4mm}
.cmp-foot i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.cmp-foot b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:8pt;line-height:1.1}
.cmp-foot span{font-size:6.4pt;line-height:1.38;color:var(--muted)}

/* ---------- 03 КАТАЛОГ ---------- */
.opener{display:grid;grid-template-columns:1.1fr .9fr;gap:8mm;align-items:end;margin-bottom:3.4mm}
.opener .sec-title{font-size:27pt;line-height:.97;margin:0}
.opener p{font-size:7.3pt;line-height:1.42;color:var(--graphite);margin:0;max-width:74mm}
.opener .tech{font-size:5.8pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:1.6mm}
.catbar{display:flex;align-items:baseline;gap:2.6mm;border-top:0.9pt solid var(--ink);padding:2.2mm 0 1.8mm}
.catbar__tick{width:3.2mm;height:1.1mm;background:var(--accent);flex:none}
.catbar b{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:9pt;letter-spacing:.04em}
.catbar span{margin-left:auto;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.row{display:grid;grid-template-columns:7mm 19mm minmax(0,1fr) 58mm 28mm;gap:0 3mm;align-items:center;height:15.2mm;padding:1.2mm 0;border-top:0.4pt solid var(--line);overflow:hidden}
.row__n{font-family:"Tektur",monospace;font-size:5.5pt;letter-spacing:.06em;color:var(--muted)}
.row__thumb{width:19mm;height:12.2mm;display:flex;align-items:center;justify-content:center;border:0.4pt solid var(--line);background:var(--paper-hi);padding:1mm;overflow:hidden}
.row__thumb img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain}
.row__name{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:8.4pt;line-height:1.1;margin:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.row__badge{font-family:"Tektur",monospace;font-size:4.4pt;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);border:.4pt solid var(--accent-dim);padding:.2mm 1mm;margin-left:1.2mm;vertical-align:middle;white-space:nowrap}
.row__specs{display:flex;flex-direction:column;gap:.4mm;min-width:0;overflow:hidden}
.row__sp{font-family:"Tektur",monospace;font-size:6pt;color:var(--graphite);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;gap:1.4mm;align-items:baseline}
.row__sp i{font-style:normal;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.1pt;letter-spacing:.05em;color:var(--muted);width:11mm;flex:none}
.row__sp b{font-weight:400;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row__price{text-align:right;font-family:"Tektur",monospace;font-size:8.8pt;font-weight:600;letter-spacing:-.01em;line-height:1.05;white-space:nowrap}
.row__price small{display:block;font-family:"Oswald","Arial Narrow",sans-serif;font-size:4.9pt;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400;margin-top:.8mm}
.sum{margin-top:6mm;border-top:0.9pt solid var(--line-hard);padding-top:3mm;display:grid;grid-template-columns:1fr 74mm;gap:9mm;align-items:start}
.sum h3{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:13pt;margin:0 0 2.6mm}
.sumt{width:100%;border-collapse:collapse}
.sumt th,.sumt td{text-align:left;border-bottom:0.4pt solid var(--line);padding:1.6mm 1.6mm;font-size:6.3pt}
.sumt th{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.5pt;letter-spacing:.08em;color:var(--muted);font-weight:500;border-bottom:0.4pt solid var(--line-hard)}
.sumt td{font-family:"Tektur",monospace;color:var(--graphite)}
.sumt td:first-child{font-family:"Sofia",Arial,sans-serif;font-size:7.2pt;color:var(--ink)}
.sumt tr.total td{border-bottom:0.9pt solid var(--line-hard);font-weight:600}
.notes h4{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:8pt;margin:0 0 1.6mm}
.notes p{font-size:6.4pt;line-height:1.42;color:var(--muted);margin:0 0 1.8mm}
.notes p b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6pt;letter-spacing:.05em;color:var(--graphite);font-weight:500}

/* ---------- 04/05 ПРИМЕНЕНИЕ И ПОСТАВКА ---------- */
.block + .block{margin-top:7mm}
.block__head{display:flex;align-items:baseline;gap:4mm;border-bottom:0.4pt solid var(--line-hard);padding-bottom:2.2mm;margin-bottom:2.6mm}
.block__head .sec-title{font-size:20pt}
.block__head .sec-num{flex:none}
.block__head p{margin:0 0 0 auto;max-width:86mm;font-size:6.8pt;line-height:1.4;color:var(--muted);text-align:right}
.app{display:grid;grid-template-columns:7mm 38mm minmax(0,1fr) 31mm;gap:0 4mm;align-items:baseline;border-top:0.4pt solid var(--line);padding:2.8mm 0}
.app i{font-style:normal;font-family:"Tektur",monospace;font-size:5.2pt;color:var(--muted)}
.app b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:8.2pt;line-height:1.08}
.app p{margin:0;font-size:7pt;line-height:1.4;color:var(--graphite)}
.app span{font-family:"Tektur",monospace;font-size:5.2pt;line-height:1.4;color:var(--muted);text-align:right}
.steps{position:relative;margin-top:4mm;padding-top:1mm}
.steps__line{position:absolute;left:0;right:0;top:11.5mm;border-top:0.4pt solid var(--line-hard)}
.steps__list{display:grid;grid-template-columns:repeat(7,1fr);gap:0 2mm;position:relative;margin:0;padding:0;list-style:none}
.step{position:relative}
.step__n{position:relative;display:inline-block;background:var(--paper);padding-right:1.6mm;font-family:"Tektur",monospace;font-size:5.8pt;color:var(--accent);margin-top:7.4mm;line-height:1}
.step h4{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:7.6pt;line-height:1.1;margin:1.6mm 0 1mm;max-width:23mm}
.step p{margin:0;font-size:6pt;line-height:1.38;color:var(--muted);max-width:23mm}
.steps__foot{display:flex;justify-content:space-between;margin-top:3mm;font-family:"Tektur",monospace;font-size:5.2pt;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
.kit{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:6mm;border-top:0.9pt solid var(--line-hard)}
.kit div{padding:3mm 4mm 3mm 0;border-left:0.4pt solid var(--line);display:flex;flex-direction:column;gap:1mm}
.kit div:first-child{border-left:0;padding-left:0}
.kit div:not(:first-child){padding-left:4mm}
.kit i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.12em;color:var(--accent)}
.kit b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:7.6pt;line-height:1.1}
.kit span{font-size:6.2pt;line-height:1.36;color:var(--muted)}

/* ---------- 06 ДОКУМЕНТЫ ---------- */
.docs2{display:grid;grid-template-columns:1fr 66mm;gap:9mm;align-items:start;margin-top:1mm}
.doc2{border-top:0.9pt solid var(--line-hard)}
.doc2 > div{display:grid;grid-template-columns:7mm 1fr;gap:2.6mm;border-bottom:0.4pt solid var(--line);padding:2.1mm 0}
.doc2 i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;color:var(--muted)}
.doc2 b{display:block;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:7.4pt;line-height:1.1;margin-bottom:.7mm}
.doc2 p{margin:0;font-size:6.6pt;line-height:1.4;color:var(--graphite)}
.legal-block{margin-top:5.4mm;border-top:0.4pt solid var(--line-hard);padding-top:2.6mm}
.legal-block h3{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);margin:0 0 2.2mm;font-weight:500}
.legal-block__cols{columns:2;column-gap:8mm}
.legal-block p{font-size:6.2pt;line-height:1.44;color:var(--graphite);margin:0 0 2mm;break-inside:avoid}
.legal-block p b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:5.6pt;letter-spacing:.05em;color:var(--ink);font-weight:500}
.verify{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:5mm;border-top:0.9pt solid var(--line-hard);border-bottom:0.4pt solid var(--line)}
.verify div{padding:3.2mm 4mm 3.2mm 0;border-left:0.4pt solid var(--line);display:flex;flex-direction:column;gap:1mm}
.verify div:first-child{border-left:0;padding-left:0}
.verify div:not(:first-child){padding-left:4mm}
.verify i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.12em;color:var(--accent)}
.verify b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:7.8pt;line-height:1.1}
.verify span{font-size:6.3pt;line-height:1.38;color:var(--muted)}

/* ---------- КОНТАКТЫ ---------- */
.page--contacts{padding-bottom:0}
.contact-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:0.4pt solid var(--line-hard);padding-bottom:2.4mm;margin-bottom:7mm}
.contact-head b{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;letter-spacing:.08em;font-size:8pt}
.contact-head span{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}
.contact__title{font-family:"Oswald","Arial Narrow",sans-serif;font-weight:500;text-transform:uppercase;font-size:40pt;line-height:.94;letter-spacing:-.01em;margin:0 0 3mm}
.contact__title i{font-style:normal;color:var(--accent)}
.contact__lead{font-size:8.8pt;line-height:1.42;color:var(--graphite);max-width:100mm;margin:0 0 6mm}
.contact__grid{display:grid;grid-template-columns:104mm 1fr;gap:10mm;align-items:start}
.contact__phone{font-family:"Tektur",monospace;font-size:24pt;font-weight:500;letter-spacing:-.01em;line-height:1.05;display:block;margin:0 0 1.4mm;color:var(--ink)}
.contact__cap{font-family:"Tektur",monospace;font-size:5.6pt;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:4mm}
.contact__qr{display:flex;gap:5mm;align-items:center;border-top:0.4pt solid var(--line);padding-top:3.4mm}
.contact__qr img{width:31mm;height:31mm;background:var(--paper-hi);padding:1.2mm;flex:none}
.contact__qr span{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6.2pt;letter-spacing:.08em;line-height:1.5;color:var(--muted)}
.list__title{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:9pt;margin:0 0 2mm;border-bottom:0.9pt solid var(--line-hard);padding-bottom:1.6mm}
.checklist{display:flex;flex-direction:column}
.checklist div{display:grid;grid-template-columns:5.5mm 1fr;gap:2mm;border-bottom:0.4pt solid var(--line);padding:2mm 0;font-size:7.1pt;line-height:1.38;color:var(--graphite)}
.checklist i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;color:var(--accent);padding-top:.3mm}
.contact__note{font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:3mm;line-height:1.7}
.howto{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:7mm;border-top:0.9pt solid var(--line-hard)}
.howto div{padding:3.4mm 4mm 3.4mm 0;border-left:0.4pt solid var(--line);display:flex;flex-direction:column;gap:1mm}
.howto div:first-child{border-left:0;padding-left:0}
.howto div:not(:first-child){padding-left:4mm}
.howto i{font-style:normal;font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.12em;color:var(--accent)}
.howto b{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:8pt;line-height:1.1}
.howto span{font-size:6.4pt;line-height:1.4;color:var(--muted)}
.contact-band{position:absolute;left:0;right:0;bottom:0;height:58mm;background:var(--graphite);color:var(--paper);padding:8mm 16mm 9mm;display:flex;justify-content:space-between;align-items:center}
.contact-band__left b{display:block;font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-weight:500;font-size:8pt;letter-spacing:.1em;color:rgba(233,226,209,.62);margin-bottom:2mm}
.contact-band__phone{font-family:"Tektur",monospace;font-size:21pt;font-weight:500;letter-spacing:-.01em;color:var(--paper-hi);line-height:1}
.contact-band__note{font-family:"Tektur",monospace;font-size:5.4pt;letter-spacing:.12em;text-transform:uppercase;color:rgba(233,226,209,.5);margin-top:2.4mm}
.contact-band__right{display:flex;gap:5mm;align-items:center}
.contact-band__right img{width:26mm;height:26mm;background:var(--paper-hi);padding:1.2mm}
.contact-band__right span{font-family:"Oswald","Arial Narrow",sans-serif;text-transform:uppercase;font-size:6pt;letter-spacing:.08em;line-height:1.5;color:rgba(233,226,209,.62);max-width:32mm}
.contact-band__pno{position:absolute;right:16mm;bottom:3.2mm;font-family:"Tektur",monospace;font-size:5.2pt;letter-spacing:.12em;text-transform:uppercase;color:rgba(233,226,209,.4)}
"""


# ---------------------------------------------------------------------------
# общие блоки
# ---------------------------------------------------------------------------
def pg_head(left):
    return '<div class="pg-head"><b>%s</b><span>В ОКОПЕ · каталог изделий · 2026</span></div>' % left


def pg_foot(note, no):
    return ('<div class="pg-foot"><span>%s</span><span>%s</span></div>'
            % (note, "%02d / %02d" % (no, TOTAL_PAGES)))


def page(body, no, left, note=PRICE_NOTE, cls=""):
    return '\n<section class="page %s">%s\n%s\n%s</section>' % (cls, pg_head(left), body, pg_foot(note, no))


def media(p, cls, big=False):
    src = p.get("photo_big") if big else p.get("photo_row")
    if src:
        return '<img class="%s" src="%s" alt="%s">' % (cls, esc(src), esc(p["name"]))
    return '<span class="nophoto-text">ФОТО<br>УТОЧНЯЕТСЯ</span>'


# ---------------------------------------------------------------------------
# 01 обложка
# ---------------------------------------------------------------------------
def cover():
    stats = [("300–5900", "МГц диапазон"), ("до 2400", "Вт мощность передатчиков"),
             ("43", "позиции в каталоге"), ("12", "месяцев гарантии")]
    stat_html = "".join('<div class="cover__stat"><b>%s</b><span>%s</span></div>' % s for s in stats)
    aside = [("Изделий в линейке", "43"), ("Категорий", "6"),
             ("Позиций сайта", "33"), ("Архивных", "10")]
    aside_html = "".join('<div><span>%s</span><b>%s</b></div>' % a for a in aside)
    zone = """
      <svg class="zone" viewBox="0 0 800 560" preserveAspectRatio="xMidYMid meet">
        <defs><path id="zoneArc" d="M 100 420 A 300 300 0 0 1 700 420"/></defs>
        <line class="z-ground" x1="20" y1="420" x2="780" y2="420"/>
        <path class="z-arc" d="M 100 420 A 300 300 0 0 1 700 420"/>
        <text class="z-label"><textPath href="#zoneArc" startOffset="31%%">ЗОНА ПРОТИВОДЕЙСТВИЯ БПЛА</textPath></text>
        <image href="%s" x="325" y="330" width="150" height="90" preserveAspectRatio="xMidYMax meet"/>
        <line class="z-tick" x1="475" y1="420" x2="475" y2="404"/>
        <line class="z-tick" x1="605" y1="420" x2="605" y2="404"/>
        <line class="z-tick" x1="475" y1="410" x2="605" y2="410"/>
        <text class="z-label z-label--accent" x="540" y="396" text-anchor="middle">50–200 М</text>
        <line class="z-tick" x1="100" y1="420" x2="100" y2="462"/>
        <line class="z-tick" x1="700" y1="420" x2="700" y2="462"/>
        <line class="z-tick" x1="100" y1="454" x2="700" y2="454"/>
        <text class="z-label z-label--accent" x="400" y="480" text-anchor="middle">2000–3000 М</text>
        <text class="z-label" x="400" y="498" text-anchor="middle">ОПЕРАТОР В УКРЫТИИ</text>
        <text class="z-label" x="24" y="444">— ЗЕМЛЯ</text>
        <text class="z-label" x="400" y="322" text-anchor="middle">СТАНЦИЯ К-12М</text>
      </svg>
      <div class="cap">Схема по паспорту изделия · дальность зависит от рельефа, помеховой обстановки и погоды</div>""" % HERO
    return """
<section class="page page--cover">
  <div class="cover__top">
    <div class="cover__brand"><span class="cover__mark"><img src="%s" alt=""></span><span><b>В ОКОПЕ</b><i>каталог · НПО «Киловатт»</i></span></div>
    <div class="cover__meta">НПО «КИЛОВАТТ» · ЛИПЕЦК<br>КАТАЛОГ ИЗДЕЛИЙ · 2026<br>РЕД. 01 · НОЯБРЬ 2026</div>
  </div>
  <div class="cover__aside">%s</div>
  <div class="cover__kicker">СТАНЦИИ РАДИОЭЛЕКТРОННОЙ БОРЬБЫ</div>
  <h1 class="cover__title"><span>Станции</span><span class="out">РЭБ</span><span class="mark">«Капюшон»</span></h1>
  <p class="cover__lead">Купольные, переносные и стационарные комплексы защиты объектов от БПЛА. Официальная линейка производителя — в самостоятельном каталоге «В ОКОПЕ».</p>
  <div class="cover__zone">%s
  </div>
  <div class="cover__foot">
    <div class="cover__stats">%s</div>
    <div class="cover__note">Цены поставщика — ориентир,<br>не публичная оферта<br>данные — ноябрь 2026</div>
  </div>
</section>""" % (LOGO, aside_html, zone, stat_html)


# ---------------------------------------------------------------------------
# 02 производитель
# ---------------------------------------------------------------------------
ABOUT_P = [
    "В линейке более 20 моделей: компактные купольные станции для транспорта, стационарные направленные комплексы для площадных объектов, переносные рюкзаки, автоматические обнаружители дронов и аксессуары.",
    "«Капюшон» — зарегистрированный товарный знак производителя (свидетельство № 1086620 от 14.02.2025); на внешний вид станции получен патент RU 145992 S. На изделия оформлены сертификат соответствия № РОСС RU.32001.04ИБФ1.ОСП28.81271 и декларация о соответствии ЕАЭС № RU Д-RU.PA07.B.24906/25. Гарантия — 12 месяцев; сервис и техническую поддержку обеспечивают производитель и его представители.",
]
DOCS = [
    ("Товарный знак", "«Капюшон» — свидетельство № 1086620 от 14.02.2025"),
    ("Патент", "RU 145992 S на внешний вид станции от 06.02.2025"),
    ("Сертификат", "соответствия № РОСС RU.32001.04ИБФ1.ОСП28.81271"),
    ("Декларация", "о соответствии ЕАЭС № RU Д-RU.PA07.B.24906/25"),
    ("Гарантия", "12 месяцев с даты реализации; паспорт с отметками заводских проверок"),
    ("Изготовитель", "по паспорту: К-12М — НПО «КИЛОВАТТ»; «Ребус-4», «Штора» — НПО «МЕГАВАТТ»"),
]


def page_about():
    facts = [("20+", "моделей в линейке"), ("ГКРЧ", "решения на серийные изделия"),
             ("12 мес", "гарантия по паспорту"), ("Липецк", "производство полного цикла")]
    fact_html = "".join('<div class="fact3"><b>%s</b><span>%s</span></div>' % f for f in facts)
    docs_html = "".join('<div><b>%s</b><span>%s</span></div>' % (esc(t), esc(v)) for t, v in DOCS)
    p_html = "".join("<p>%s</p>" % esc(t) for t in ABOUT_P)
    comps = [("01", "Собственное КБ", "Корпус, антенны и электроника — разработка и производство на одной площадке."),
             ("02", "Заводские испытания", "Каждое изделие проверяется на заводе; отметки проверок — в паспорте."),
             ("03", "Сервис и поддержка", "Гарантия 12 месяцев, ремонт и техническая поддержка производителя.")]
    comp_html = "".join('<div><i>%s</i><b>%s</b><span>%s</span></div>' % c for c in comps)
    body = """
<div class="about">
  <div class="about__main">
    <div class="sec-num">01.1 / КТО ДЕЛАЕТ ЛИНЕЙКУ</div>
    <h2 class="sec-title">Собственное<br>производство<br>полного цикла</h2>
    <p class="lead-osw">НПО «Киловатт» — российский разработчик и производитель станций РЭБ для защиты объектов от БПЛА.</p>
    %s
    <p class="tiny">Сведения об изготовителе: для «Капюшон» К-12М в паспорте — ООО «НПО „КИЛОВАТТ“»; для «Ребус-4», «Штора» К-12/700, «Штора-М» К-8/600 — ООО «НПО „МЕГАВАТТ“» (Липецк).</p>
  </div>
  <aside class="about__side">
    <div class="sec-num" style="margin-bottom:2mm">ФАКТЫ</div>
    <div class="facts3">%s</div>
    <div class="about__docs">
      <div class="sec-num" style="margin-bottom:2mm">ДОКУМЕНТЫ</div>
      <div class="dl">%s</div>
    </div>
  </aside>
</div>
<div class="orig">
  <h3>Оригинальность:<br>паспорт решает</h3>
  <p>Паспорт изделия обязателен: в нём указаны изготовитель, характеристики, правила эксплуатации и отметки заводских проверок. На металлических шильдиках — модель и QR-код на производителя. Оригинальные изделия поставляются в полной комплектации: станция, кабели, пульт, источник питания, тренога или кронштейн, паспорт. Подделки под названиями «Капюшон», «Штора», «Ребус», «Рюкзак» на рынке встречаются — оригинальную продукцию рекомендуем приобретать у представителей производителя.</p>
</div>
<div class="comp">%s</div>""" % (p_html, fact_html, docs_html, comp_html)
    return page(body, 2, "01 / ПРОИЗВОДИТЕЛЬ И ДОКУМЕНТЫ")


# ---------------------------------------------------------------------------
# 03 флагманы
# ---------------------------------------------------------------------------
def page_flags(flags):
    rows = []
    for i, p in enumerate(flags, 1):
        specs = "".join("<tr><td>%s</td><td>%s</td></tr>" % (esc(l), esc(v)) for l, v in flag_specs(p))
        rows.append("""
<article class="flag">
  <figure class="flag__media">%s</figure>
  <div class="flag__body">
    <div class="flag__kick">0%d · ФЛАГМАН · %s</div>
    <h3 class="flag__name">%s</h3>
    <p class="flag__desc">%s</p>
    <table class="flag__specs">%s</table>
    <div class="flag__foot"><span class="flag__price">%s</span><span class="flag__status">%s</span></div>
  </div>
</article>""" % (media(p, "flag__img", True), i, esc(p["category"]), esc(p["name"]), esc(p["short"]),
                 specs, esc(p["price"]), esc(p["status"])))
    body = """
<h2 class="sec-title" style="font-size:24pt;margin:0 0 4mm">Три позиции, с которых начинают</h2>
%s
<div class="section-note"><span>Купольная станция на технику · стационарный комплекс на площадь · направленная станция на объект</span><span>%s</span></div>""" % ("".join(rows), PRICE_NOTE.lower())
    return page(body, 3, "02 / ФЛАГМАНЫ")


# ---------------------------------------------------------------------------
# 04 сравнение
# ---------------------------------------------------------------------------
CMP_ROWS = ["Диапазон", "Мощность", "Дальность", "Питание", "Вес", "Гарантия"]


def page_compare(flags):
    head = ['<tr><th class="cmp__lab">Характеристика<br>по паспорту</th>']
    for p in flags:
        head.append("""<th><span class="cmp__cat">%s</span><div class="cmp__photo">%s</div><span class="cmp__name">%s</span></th>"""
                    % (esc(p["category"]), media(p, "cmp__img", True), esc(p["name"])))
    head.append("</tr>")
    body_rows = []
    for r in CMP_ROWS:
        cells = "".join("<td>%s</td>" % esc(cmp_value(p, r)) for p in flags)
        body_rows.append('<tr><td class="cmp__lab">%s</td>%s</tr>' % (esc(r), cells))
    price = ['<tr>']
    price.append('<td class="cmp__lab">Цена поставщика</td>')
    for p in flags:
        price.append('<td><span class="cmp__price">%s<small>%s</small></span></td>' % (esc(p["price"]), esc(p["status"])))
    price.append('</tr>')
    foot = [("01 · На технику", "К-12М", "Крепление на крышу кабины, КУНГа или верхнюю точку техники."),
            ("02 · На площадь", "«Ребус-4»", "Круговое прикрытие площадного объекта четырьмя моноблоками."),
            ("03 · На объект", "«Штора» К-12/700", "Направленное подавление на вероятном направлении подлёта.")]
    foot_html = "".join('<div><i>%s</i><b>%s</b><span>%s</span></div>' % f for f in foot)
    body = """
<h2 class="sec-title" style="font-size:24pt;margin:0 0 1.6mm">Флагманы в цифрах</h2>
<p class="tiny" style="max-width:124mm;margin-bottom:1mm">Три модели рядом — что выбрать под объект. Данные приведены по паспортам изделий; цены — поставщика (ориентиры), подтверждаются в КП.</p>
<table class="cmp">
  <thead>%s</thead>
  <tbody>%s</tbody>
  <tfoot>%s</tfoot>
</table>
<div class="cmp-note"><span>данные — по паспортам изделий</span><span>дальность зависит от условий эксплуатации</span><span>%s</span></div>
<div class="cmp-foot">%s</div>""" % ("".join(head), "".join(body_rows), "".join(price), PRICE_NOTE.lower(), foot_html)
    return page(body, 4, "02.1 / СРАВНЕНИЕ")


# ---------------------------------------------------------------------------
# 05-08 каталог
# ---------------------------------------------------------------------------
def catbar(c, count, cont=False):
    name = esc(c["name"]) + (" · продолжение" if cont else "")
    return ('<div class="catbar"><span class="catbar__tick"></span><b>%s</b>'
            '<span>%d %s</span></div>' % (name, count, "позиция" if count == 1 else "позиций"))


def row_html(p):
    esc_badge = ('<span class="row__badge">вне сайта</span>' if p["archive"] else "")
    specs = "".join('<span class="row__sp"><i>%s</i><b>%s</b></span>' % (esc(l), esc(v)) for l, v in p["facts"][:3])
    return """
<div class="row">
  <span class="row__n">%02d</span>
  <figure class="row__thumb">%s</figure>
  <div><h3 class="row__name">%s%s</h3></div>
  <div class="row__specs">%s</div>
  <div class="row__price">%s<small>%s</small></div>
</div>""" % (p["num"], media(p, "row__img"), esc(p["name"]), esc_badge,
            specs, esc(p["price"]), esc(p["status"]))


def catalog_pages(groups, counts):
    pages = []
    # 05: открывашка + купольные (14)
    opener = """
<div class="opener">
  <h2 class="sec-title">Вся линейка<br>по номерам</h2>
  <div>
    <span class="tech">43 позиции · 6 категорий · ведомость</span>
    <p>33 актуальные позиции сайта и 10 архивных. Ведомость по категориям: номер, изделие, ключевые ТТХ, цена поставщика. Позиции «вне сайта» — архивные, наличие уточняется. Цены поставщика — ориентир, не публичная оферта.</p>
  </div>
</div>"""
    body = opener + catbar(CATS[0], len(groups["kupolnye"])) + "".join(row_html(p) for p in groups["kupolnye"])
    pages.append(page(body, 5, "03 / КАТАЛОГ — ВЕДОМОСТЬ", cls="cat-page"))
    # 06: стационарные (5) + переносные (7) + детекторы (2) = 14
    body = catbar(CATS[1], len(groups["staczionarnye"])) + "".join(row_html(p) for p in groups["staczionarnye"])
    body += catbar(CATS[2], len(groups["perenosnye"])) + "".join(row_html(p) for p in groups["perenosnye"])
    body += catbar(CATS[3], len(groups["detektory"])) + "".join(row_html(p) for p in groups["detektory"])
    pages.append(page(body, 6, "03 / КАТАЛОГ — ВЕДОМОСТЬ", cls="cat-page"))
    # 07: доп. модули (4) + аксессуары первые 10 = 14
    acc = groups["aksessuary"]
    body = catbar(CATS[4], len(groups["moduli"])) + "".join(row_html(p) for p in groups["moduli"])
    body += catbar(CATS[5], len(acc)) + "".join(row_html(p) for p in acc[:10])
    pages.append(page(body, 7, "03 / КАТАЛОГ — ВЕДОМОСТЬ", cls="cat-page"))
    # 08: последняя позиция + итоги + состав
    rest = acc[10:]
    body = catbar(CATS[5], len(rest), cont=True) + "".join(row_html(p) for p in rest)
    body += summary(groups, counts)
    pages.append(page(body, 8, "03 / КАТАЛОГ — ВЕДОМОСТЬ", cls="cat-page"))
    return pages


def summary(groups, counts):
    rows = []
    tot = arch = 0
    for c in CATS:
        items = groups[c["key"]]
        prices = [i["price_dima"] for i in items if i["price_dima"]]
        a = sum(1 for i in items if i["archive"])
        rows.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%s</td></tr>" % (
            esc(c["name"]), len(items), a, ("от %s" % rub(min(prices))) if prices else "по запросу"))
        tot += len(items)
        arch += a
    rows.append('<tr class="total"><td>Всего</td><td>%d</td><td>%d</td><td>—</td></tr>' % (tot, arch))
    priced = sum(1 for p in D["products"] if p["price_dima"])
    lineup = "".join('<div><b>%d</b><span>%s</span><i>%s</i></div>' % (counts[c["key"]], esc(c["name"]), esc(c["desc"])) for c in CATS)
    body = """
<div class="sum">
  <div>
    <h3>Итоги по категориям</h3>
    <table class="sumt">
      <thead><tr><th>Категория</th><th>Позиций</th><th>Вне сайта</th><th>Цена от</th></tr></thead>
      <tbody>%s</tbody>
    </table>
  </div>
  <div class="notes">
    <h4>Примечания к ведомости</h4>
    <p><b>Архив.</b> 10 позиций сняты с сайта производителя — в ведомости помечены «вне сайта»; наличие, комплектация и цена уточняются по запросу.</p>
    <p><b>Цены.</b> %d позиций с ценой поставщика, %d — «по запросу». Цены указаны без наценки «В ОКОПЕ», не являются публичной офертой и подтверждаются в КП.</p>
    <p><b>ТТХ.</b> Приведены по паспортам изделий. Дальность зависит от рельефа, помеховой обстановки и погоды; производитель вправе вносить изменения в конструкцию.</p>
    <p><b>Ведомость.</b> Номер — сквозная позиция каталога; в строке — ключевые параметры и цена. Полные ТТХ, фотографии и описание — в паспорте изделия и в электронном каталоге.</p>
  </div>
</div>
<div class="lineup">%s</div>""" % ("".join(rows), priced, 43 - priced, lineup)
    return body


# ---------------------------------------------------------------------------
# 09 применение + поставка
# ---------------------------------------------------------------------------
APPS = [
    ("01", "Завод / промышленная площадка", "«Ребус-4» для кругового прикрытия площадки и «Сигнал-М2» для раннего обнаружения; на периметр и подъезды — «Штора» К-12/700. Контур закрывает и разведку, и заход ударных дронов.", "Ребус-4 · Сигнал-М2 · Штора К-12/700", "купольные / стационарные"),
    ("02", "Склад / логистический хаб", "Начать с обнаружения и поставить направленную «Штору» на вероятное направление подлёта. При расширении — купольные «Капюшон» К-8М/К-12М на технику и погрузчики.", "Штора К-12/700 · Капюшон К-8М/К-12М", "обнаружение / направленные"),
    ("03", "Охрана периметра", "Задача — вовремя увидеть и точечно закрыть участок. Сначала обнаружение, затем направленные станции на углах периметра; связка «детектор + станция» работает по факту.", "Сигнал-М2 · Штора К-12/700", "детектор + станция"),
    ("04", "Инфраструктура: ТЭК, ЛЭП, трубопроводы", "Протяжённые объекты защищают комбинацией: «Поле-31» против дронов по спутниковой навигации плюс «Ребус-4» для локальных площадок. Для мобильных бригад — станции на транспорт и рюкзаки ТП.", "Поле-31 · Ребус-4 · рюкзаки ТП", "площадные / мобильные"),
    ("05", "АЗС / топливная инфраструктура", "Компактные решения для небольшой площадки: «Штора-М» К-8/600 или «Капюшон» К-8М. Важны быстрый монтаж и работа от штатного питания; при сети АЗС — типовое решение.", "Штора-М К-8/600 · Капюшон К-8М", "компактные"),
    ("06", "Аэропорт / приаэродромная территория", "Технически задачи закрывают «Ребус-4» и «Штора» К-12/700, но применение на приаэродромных территориях регулируется отдельно. Такие проекты ведём только с уполномоченными подразделениями.", "Ребус-4 · Штора К-12/700", "по согласованию"),
    ("07", "Сельхозпредприятие", "На поля и открытые площадки — «Штора» К-12/700, на тракторы и комбайны — купольные «Капюшон»; детектор помогает не держать станции включёнными впустую.", "Штора К-12/700 · Капюшон К-8М · Сигнал-М2", "площадные / купольные"),
]
STEPS = [
    ("01", "Заявка", "Объект, площадь, задачи, транспорт, питание, сроки."),
    ("02", "Подбор", "Состав контура: обнаружение → станции → питание → аксессуары → монтаж."),
    ("03", "КП", "Конфигурация, цена, сроки и состав документов."),
    ("04", "Договор", "Комплектация, сроки, условия поставки, гарантия, ПНР."),
    ("05", "Поставка", "Отгрузка со склада или под заказ с понятным сроком."),
    ("06", "ПНР и обучение", "Монтаж, подключение, проверка РЭБ-тестером, инструктаж."),
    ("07", "Гарантия и сервис", "12 месяцев, гарантийный ремонт, поддержка и модернизация."),
]
KIT = [
    ("01", "Изделие", "Станция или комплекс в заводской упаковке, шильдик с моделью и QR-кодом."),
    ("02", "Управление", "Пульт, кабели, коммутатор или разветвитель — по комплектации изделия."),
    ("03", "Питание и монтаж", "Источник питания, преобразователь, тренога или кронштейн."),
    ("04", "Документы", "Паспорт с отметками заводских проверок и документы по КП."),
]


def page_apps_supply():
    apps = []
    for n, name, desc, models, tag in APPS:
        apps.append("""<div class="app"><i>%s</i><b>%s</b><p>%s</p><span>%s<br>%s</span></div>"""
                    % (n, esc(name), esc(desc), esc(models), esc(tag)))
    steps = []
    for n, name, desc in STEPS:
        steps.append("""<li class="step"><span class="step__n">%s</span><h4>%s</h4><p>%s</p></li>"""
                     % (n, esc(name), esc(desc)))
    kit = "".join('<div><i>%s</i><b>%s</b><span>%s</span></div>' % (n, esc(t), esc(d)) for n, t, d in KIT)
    body = """
<div class="block">
  <div class="block__head"><span class="sec-num">04 / ПРИМЕНЕНИЕ</span><h2 class="sec-title">Где это работает</h2></div>
  <div class="apps" style="border-top:0">%s</div>
</div>
<div class="block">
  <div class="block__head"><span class="sec-num">05 / ПОСТАВКА</span><h2 class="sec-title">Порядок сделки</h2></div>
  <div class="steps">
    <div class="steps__line"></div>
    <ol class="steps__list">%s</ol>
  </div>
  <div class="steps__foot"><span>Заявка → подбор → КП → договор → поставка → ПНР → сервис</span><span>сроки и состав — в КП</span></div>
  <div class="kit">%s</div>
</div>""" % ("".join(apps), "".join(steps), kit)
    return page(body, 9, "ПРИМЕНЕНИЕ И ПОСТАВКА")


# ---------------------------------------------------------------------------
# 10 документы и правовой блок
# ---------------------------------------------------------------------------
LEGAL = [
    ("Правовой статус.", "Оборудование является радиоэлектронным средством. Порядок приобретения, регистрации и применения определяется законодательством Российской Федерации, в том числе Федеральным законом от 07.07.2003 № 126-ФЗ «О связи», постановлениями Правительства РФ от 20.10.2021 № 1800 и от 10.10.2026 № 1331, решениями ГКРЧ. Возможность применения на конкретном объекте подтверждается заказчиком в установленном порядке до ввода оборудования в эксплуатацию. Поставщик не оказывает юридических услуг и не гарантирует получение заказчиком разрешений и регистрации; ответственность за соблюдение условий применения несёт владелец (эксплуатант) оборудования."),
    ("Технические характеристики.", "Приведены по паспортам изделий. Значения дальности зависят от условий эксплуатации (рельеф, помеховая обстановка, погодные условия) и не являются гарантией нейтрализации конкретного беспилотного аппарата. Производитель вправе вносить изменения в конструкцию и характеристики."),
    ("Цены и наличие.", "Информация актуальна на дату публикации и не является публичной офертой. Цены указаны по данным поставщика без наценки «В ОКОПЕ»; итоговая стоимость фиксируется в коммерческом предложении и договоре."),
    ("Эксплуатация.", "Запрещается вскрывать корпус, самостоятельно ремонтировать и вмешиваться в конструкцию — это прекращает гарантийные обязательства. При включённом изделии не рекомендуется находиться ближе 5 м (К-12М) или ближе 15 м в створе направленности («Штора», «Ребус-4»); точные требования — в паспорте конкретного изделия."),
    ("Ограничение по применению.", "Не допускается применение в местах, где это может создать угрозу безопасности полётов, связи, работе экстренных служб или жизни людей. Отдельные объекты (приаэродромные территории, объекты ТЭК, транспортная инфраструктура) имеют специальный правовой режим."),
]


def page_docs():
    docs = "".join('<div><i>%02d</i><div><b>%s</b><p>%s</p></div></div>' % (i, esc(t), esc(v))
                   for i, (t, v) in enumerate(DOCS, 1))
    legal = "".join("<p><b>%s</b> %s</p>" % (esc(t), esc(v)) for t, v in LEGAL)
    verify = [("01", "Паспорт", "Изготовитель, характеристики, правила эксплуатации и отметки заводских проверок."),
              ("02", "Шильдик", "Модель и QR-код на производителя на металлическом шильдике изделия."),
              ("03", "Комплектация", "Полный комплект и документы, перечисленные в КП и паспорте.")]
    verify_html = "".join('<div><i>%s</i><b>%s</b><span>%s</span></div>' % v for v in verify)
    body = """
<h2 class="sec-title" style="font-size:24pt;margin:0 0 3mm">Статус и документы</h2>
<div class="docs2">
  <div class="doc2">%s</div>
  <aside class="orig orig--stack">
    <h3>Оригинальность</h3>
    <p>Паспорт изделия обязателен: изготовитель, характеристики, правила эксплуатации и отметки заводских проверок. На шильдиках — модель и QR-код на производителя. Оригинал поставляется в полной комплектации: станция, кабели, пульт, питание, тренога или кронштейн, паспорт.</p>
    <p style="margin-top:2.4mm">Подделки под названиями «Капюшон», «Штора», «Ребус», «Рюкзак» встречаются. Оригинальную продукцию рекомендуем приобретать у представителей производителя.</p>
    <span class="stamp">ДОКУМЕНТЫ — В КП</span>
  </aside>
</div>
<div class="legal-block">
  <h3>Правовой статус оборудования — обязательная информация</h3>
  <div class="legal-block__cols">%s</div>
</div>
<div class="verify">%s</div>""" % (docs, legal, verify_html)
    return page(body, 10, "06 / ДОКУМЕНТЫ И ПРАВОВОЙ СТАТУС")


# ---------------------------------------------------------------------------
# 11 контакты
# ---------------------------------------------------------------------------
def page_contacts():
    checks = [
        ("01", "Объект, площадь, регион, режим работы"),
        ("02", "Задачи: обнаружение, подавление, прикрытие техники"),
        ("03", "Транспорт, питание, монтаж, ограничения по размещению"),
        ("04", "Требования к документам, срокам и форме поставки"),
    ]
    chk = "".join('<div><i>%s</i><span>%s</span></div>' % (n, esc(t)) for n, t in checks)
    howto = [("01", "Заявка", "Телефон, WhatsApp или представитель «В ОКОПЕ»: объект, задачи, сроки."),
             ("02", "Подбор и КП", "Конфигурация контура, состав документов, сроки и цена — в КП."),
             ("03", "Договор и поставка", "Отгрузка, монтаж и обучение операторов — по согласованному плану.")]
    howto_html = "".join('<div><i>%s</i><b>%s</b><span>%s</span></div>' % h for h in howto)
    body = """
<div class="contact-head"><b>КОНТАКТЫ · ЗАЯВКА</b><span>В ОКОПЕ · каталог изделий · 2026</span></div>
<h2 class="contact__title">Собрать<br>контур<i>.</i></h2>
<p class="contact__lead">Опишите объект — вернёмся с конфигурацией, составом документов, сроками и ценой. Правовой режим применения проверяем до сделки.</p>
<div class="contact__grid">
  <div>
    <span class="contact__cap">Телефон · WhatsApp</span>
    <span class="contact__phone">%s</span>
    <span class="contact__cap" style="margin-top:3mm">Подбор и поставка — «В ОКОПЕ»; производитель — НПО «Киловатт», Липецк</span>
    <div class="contact__qr"><img src="%s" alt="QR-код: телефон каталога"><span>Наведите камеру<br>телефона — позвонить</span></div>
  </div>
  <div>
    <div class="list__title">Что прислать для расчёта</div>
    <div class="checklist">%s</div>
    <div class="contact__note">Коммерческое предложение — в течение рабочего дня после получения вводных.<br>Цены — поставщика, без наценки «В ОКОПЕ»; не публичная оферта.</div>
  </div>
</div>
<div class="howto">%s</div>
<div class="contact-band">
  <div class="contact-band__left">
    <b>Связаться напрямую</b>
    <span class="contact-band__phone">%s</span>
    <div class="contact-band__note">«В ОКОПЕ» · подбор и поставка · каталог изделий НПО «Киловатт» · 2026</div>
  </div>
  <div class="contact-band__right"><img src="%s" alt="QR-код: телефон каталога"><span>Наведите камеру<br>телефона — позвонить</span></div>
  <span class="contact-band__pno">стр. 11 / 11 · ноябрь 2026</span>
</div>""" % (PHONE, QR, chk, howto_html, PHONE, QR)
    return """
<section class="page page--contacts">
%s
</section>""" % body


# ---------------------------------------------------------------------------
# оптимизация изображений для PDF
# ---------------------------------------------------------------------------
def _flatten_resize(src, dst, max_side, quality, bg):
    im = Image.open(src).convert("RGBA")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    canvas = Image.new("RGB", im.size, bg)
    canvas.paste(im, (0, 0), im)
    # JPEG: Chrome встраивает его в PDF как есть (DCTDecode) без раздутия в PNG,
    # в отличие от WebP, который при печати растеризуется в PNG.
    canvas.save(dst, "JPEG", quality=quality, optimize=True, progressive=False)


def prepare_assets():
    os.makedirs(ASSETS_PRODUCTS, exist_ok=True)
    for name in os.listdir(ASSETS_PRODUCTS):
        os.remove(os.path.join(ASSETS_PRODUCTS, name))
    for name in os.listdir(ASSETS):
        fp = os.path.join(ASSETS, name)
        if os.path.isfile(fp):
            os.remove(fp)
    made = 0
    raw_total = 0
    for p in D["products"]:
        if not p.get("photo"):
            p["photo_row"] = p["photo_big"] = None
            continue
        slug = p.get("slug") or p["id"]
        src = os.path.normpath(os.path.join(OUT, p["photo"]))
        row_path = os.path.join(ASSETS_PRODUCTS, slug + "-400.jpg")
        big_path = os.path.join(ASSETS_PRODUCTS, slug + "-800.jpg")
        _flatten_resize(src, row_path, 400, 80, PAPER_HI)
        _flatten_resize(src, big_path, 800, 82, PAPER_HI)
        p["photo_row"] = "_assets/products/" + slug + "-400.jpg"
        p["photo_big"] = "_assets/products/" + slug + "-800.jpg"
        made += 2
    hero_src = os.path.normpath(os.path.join(OUT, A, "img/hero-k12m.png"))
    hero_dst = os.path.join(ASSETS, "hero.jpg")
    im = Image.open(hero_src).convert("RGBA")
    if max(im.size) > 1200:
        im.thumbnail((1200, 1200), Image.LANCZOS)
    canvas = Image.new("RGB", im.size, PAPER)
    canvas.paste(im, (0, 0), im)
    canvas.save(hero_dst, "JPEG", quality=86, optimize=True)
    made += 1
    size = sum(os.path.getsize(os.path.join(ASSETS, f)) for f in os.listdir(ASSETS) if os.path.isfile(os.path.join(ASSETS, f)))
    size += sum(os.path.getsize(os.path.join(ASSETS_PRODUCTS, f)) for f in os.listdir(ASSETS_PRODUCTS))
    print("assets:", made, "files,", round(size / 1024), "KB")


# ---------------------------------------------------------------------------
# сборка
# ---------------------------------------------------------------------------
D = load()


def build():
    prepare_assets()
    pages = [cover(), page_about(), page_flags(D["flags"]), page_compare(D["flags"])]
    pages += catalog_pages(D["groups"], D["counts"])
    pages += [page_apps_supply(), page_docs(), page_contacts()]
    doc = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>В ОКОПЕ — каталог изделий НПО «Киловатт» · 2026 · печатная версия</title>
<style>
%s
</style>
</head>
<body>
%s
</body>
</html>""" % (CSS, "\n".join(pages))
    path = os.path.join(OUT, "print-light.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print("built:", path)
    print("pages:", len(pages))


if __name__ == "__main__":
    build()
