# -*- coding: utf-8 -*-
"""Печатная A4-версия каталога (PDF): два варианта оформления.
Читает собранные данные (_tools/out/catalog_build.json), фото из assets/img, пишет print-field.html / print-quiet.html.
"""
import html
import json
import os

K = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt"
CAT = os.path.join(K, "catalog")
BUILD = os.path.join(CAT, "_tools", "out", "catalog_build.json")
OUT_FIELD = os.path.join(CAT, "print-field.html")
OUT_QUIET = os.path.join(CAT, "print-quiet.html")

def esc(s):
    return html.escape(str(s), quote=True)

def money(v):
    if v is None or v == "":
        return "по запросу"
    try:
        return f"{int(v):,}".replace(",", " ") + " ₽"
    except Exception:
        return str(v)

def load():
    data = json.load(open(BUILD, encoding="utf-8"))
    prods = [p for p in data["products"]]
    prods.sort(key=lambda p: (0 if p.get("flagship") else 1, p.get("category", ""), p.get("name", "")))
    return prods

# ---------- фрагменты ----------
def product_card(p, idx):
    specs = (p.get("specs") or [])[:3]
    spec_html = "".join(
        f'<div class="pc__row"><span>{esc(s["label"])}</span><b>{esc(s["value"])}</b></div>'
        for s in specs
    )
    photo = p.get("photos") or []
    img = f'<img src="{esc(photo[0])}" alt="">' if photo else '<div class="pc__nophoto">фото уточняется</div>'
    return f"""
      <article class="pc">
        <div class="pc__media">{img}</div>
        <div class="pc__body">
          <div class="pc__cat">{esc(p.get("category",""))}</div>
          <h3 class="pc__name">{esc(p.get("name",""))}</h3>
          <div class="pc__specs">{spec_html}</div>
          <div class="pc__foot"><span class="pc__price">{money(p.get('price_dima'))}</span><span class="pc__idx">{idx:02d}</span></div>
        </div>
      </article>"""

def clip_text(s, limit):
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    dot = cut.rfind(". ")
    if dot > limit * 0.55:
        return cut[:dot + 1]
    sp = cut.rfind(" ")
    return cut[:sp] + "…" if sp > 0 else cut


def flagship_block(p, num):
    specs = (p.get("specs") or [])[:5]
    spec_html = "".join(
        f'<div class="fl__row"><span>{esc(s["label"])}</span><b>{esc(s["value"])}</b></div>' for s in specs
    )
    photo = p.get("photos") or []
    img = f'<img src="{esc(photo[0])}" alt="">' if photo else ""
    return f"""
      <section class="fl">
        <div class="fl__media">{img}</div>
        <div class="fl__body">
          <div class="fl__kicker">0{num} · ФЛАГМАН</div>
          <h2 class="fl__name">{esc(p.get('name',''))}</h2>
          <p class="fl__desc">{esc(clip_text(p.get('description'), 460))}</p>
          <div class="fl__specs">{spec_html}</div>
          <div class="fl__price">Ориентир цены: <b>{money(p.get('price_dima'))}</b></div>
        </div>
      </section>"""

def categories(prods):
    out = []
    for p in prods:
        c = p.get("category")
        if c not in out:
            out.append(c)
    return out

def catalog_pages(prods):
    """Раскладка товаров по страницам (по 8 на страницу) с заголовками категорий."""
    pages = []
    rest = [p for p in prods if not p.get("flagship")]
    per_page = 6
    while rest:
        chunk = rest[:per_page]
        rest = rest[per_page:]
        pages.append(chunk)
    return pages

def build(theme, prods):
    field = theme == "field"
    cats = categories(prods)
    flags = [p for p in prods if p.get("flagship")][:3]
    cats_n = ", ".join(cats)
    pages = catalog_pages(prods)

    # ---------- стили ----------
    if field:
        root = """
        --paper:#20261b; --paper2:#272e21; --ink:#ede8d7; --graphic:#d6d0be;
        --olive:#a9b39b; --soft:#8b937f; --accent:#c9f24b; --line:rgba(237,232,215,.18);
        """
    else:
        root = """
        --paper:#f4f1ea; --paper2:#faf7f0; --ink:#1d1e1a; --graphic:#2a2b26;
        --olive:#5b5f52; --soft:#74786a; --accent:#c8451f; --line:rgba(29,30,26,.16);
        """
    body_bg = "#20261b" if field else "#f4f1ea"
    dark = "#15190f" if field else "#e9e2d1"

    html_doc = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Каталог НПО «Киловатт» — вариант {theme}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  @font-face {{ font-family:"Oswald"; src:url("assets/fonts/Oswald-VF.ttf"); font-weight:200 700; }}
  @font-face {{ font-family:"Sofia"; src:url("assets/fonts/SofiaSansExtraCondensed-VF.ttf"); font-weight:100 900; }}
  @font-face {{ font-family:"Tektur"; src:url("assets/fonts/Tektur-VF.ttf"); font-weight:400 900; }}
  @font-face {{ font-family:"Unbounded"; src:url("assets/fonts/Unbounded-VF.ttf"); font-weight:200 900; }}
  :root {{ {root} }}
  * {{ box-sizing:border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ margin:0; background:{body_bg}; color:var(--ink); font-family:"Sofia",Arial,sans-serif; font-size:9.4pt; line-height:1.35; }}
  .page {{ position:relative; width:210mm; height:297mm; page-break-after:always; overflow:hidden; background:var(--paper); padding:14mm 15mm 12mm; }}
  .page:last-child {{ page-break-after:auto; }}
  .rule {{ height:1px; background:var(--line); }}
  .mono {{ font-family:"Tektur",monospace; }}
  .small {{ font-family:"Oswald",sans-serif; text-transform:uppercase; letter-spacing:.18em; font-size:6.6pt; color:var(--soft); }}
  .pg-num {{ position:absolute; right:15mm; bottom:7mm; font-family:"Tektur",monospace; font-size:6.8pt; color:var(--soft); }}
  .pg-head {{ display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px solid var(--line); padding-bottom:3mm; margin-bottom:6mm; }}
  .pg-head b {{ font-family:"Oswald",sans-serif; font-weight:500; text-transform:uppercase; letter-spacing:.06em; font-size:9pt; }}
  h1,h2,h3 {{ font-family:"Oswald",sans-serif; font-weight:500; text-transform:uppercase; margin:0; }}

  /* обложка */
  .cover {{ background:{"#15190f" if field else "#f4f1ea"}; }}
  .cover .top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
  .cover .brand {{ display:flex; gap:4mm; align-items:center; }}
  .cover .brand img {{ height:13mm; }}
  .cover .brand b {{ font-family:"Unbounded",sans-serif; font-weight:800; font-size:12pt; letter-spacing:-.02em; display:block; }}
  .cover .brand span {{ font-family:"Tektur",monospace; font-size:5.6pt; letter-spacing:.16em; color:var(--soft); text-transform:uppercase; }}
  .cover .meta {{ text-align:right; font-family:"Tektur",monospace; font-size:6pt; letter-spacing:.1em; color:var(--soft); line-height:1.7; text-transform:uppercase; }}
  .cover h1 {{ font-size:58pt; line-height:.92; letter-spacing:-.03em; margin-top:22mm; }}
  .cover h1 .out {{ color:transparent; -webkit-text-stroke:1.2pt var(--ink); }}
  .cover h1 .accent {{ position:relative; }}
  .cover h1 .accent::after {{ content:""; position:absolute; left:0; right:-1%; bottom:2%; height:8%; background:var(--accent); z-index:-1; }}
  .cover .lead {{ font-size:11pt; line-height:1.4; color:var(--graphic); max-width:88mm; margin-top:10mm; }}
  .cover .foot {{ position:absolute; left:15mm; right:15mm; bottom:12mm; display:flex; justify-content:space-between; align-items:flex-end; border-top:1px solid var(--line); padding-top:5mm; }}
  .cover .stats {{ display:flex; gap:9mm; }}
  .cover .stat b {{ display:block; font-family:"Tektur",monospace; font-size:13pt; font-weight:600; }}
  .cover .stat span {{ font-family:"Oswald",sans-serif; font-size:5.8pt; letter-spacing:.12em; text-transform:uppercase; color:var(--soft); }}
  .cover .price-note {{ font-family:"Tektur",monospace; font-size:5.8pt; letter-spacing:.1em; color:var(--soft); text-align:right; line-height:1.6; }}
  .cover .hero-img {{ position:absolute; right:-18mm; bottom:34mm; width:150mm; opacity:.98; }}
  .cover .hero-img img {{ width:100%; filter:drop-shadow(0 14mm 16mm rgba(0,0,0,{"0.55" if field else "0.18"})); }}
  /* тихая обложка: схема */
  .cover .zone-wrap {{ margin-top:16mm; }}
  .cover .zone {{ width:100%; }}
  .zone .zg, .zone .za {{ fill:none; stroke:var(--ink); stroke-width:.8; }}
  .zone .zt {{ stroke:var(--ink); stroke-width:.7; }}
  .zone .zl {{ font-family:"Tektur",monospace; font-size:7pt; letter-spacing:.08em; fill:var(--soft); }}
  .zone .zla {{ font-family:"Tektur",monospace; font-size:9pt; fill:var(--accent); }}
  .zone .zarc {{ font-family:"Oswald",sans-serif; font-size:7pt; letter-spacing:.2em; fill:var(--olive); }}

  /* секции */
  .sec-title {{ font-size:22pt; line-height:1; letter-spacing:-.01em; margin-bottom:5mm; }}
  .sec-num {{ font-family:"Tektur",monospace; font-size:6.4pt; letter-spacing:.14em; color:var(--soft); margin-bottom:2mm; }}
  .two {{ display:grid; grid-template-columns: 1.15fr .85fr; gap:7mm; }}
  .facts {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--line); border:1px solid var(--line); }}
  .fact {{ background:var(--paper2); padding:4.5mm; }}
  .fact b {{ display:block; font-family:"Tektur",monospace; font-size:14pt; }}
  .fact span {{ font-family:"Oswald",sans-serif; font-size:6pt; letter-spacing:.12em; text-transform:uppercase; color:var(--soft); }}
  .txt p {{ margin:0 0 3mm; }}
  .txt .lead {{ font-family:"Oswald",sans-serif; text-transform:uppercase; font-size:13pt; line-height:1.15; }}
  .docs-list {{ border-top:1px solid var(--line); }}
  .docs-list div {{ display:flex; gap:4mm; border-bottom:1px solid var(--line); padding:2.6mm 0; }}
  .docs-list b {{ min-width:26mm; font-family:"Oswald",sans-serif; font-weight:500; text-transform:uppercase; font-size:7pt; letter-spacing:.08em; color:var(--olive); }}
  .note {{ background:{dark}; color:{'var(--paper)' if field else 'var(--ink)'}; padding:5mm; font-size:8.4pt; }}
  .note b {{ color:var(--accent); font-family:"Oswald",sans-serif; text-transform:uppercase; letter-spacing:.06em; }}

  /* флагманы */
  .fl {{ display:grid; grid-template-columns: 70mm 1fr; gap:7mm; border-top:1px solid var(--line); padding:4.2mm 0; page-break-inside:avoid; }}
  .fl__media {{ height:48mm; display:flex; align-items:center; justify-content:center; background:var(--paper2); }}
  .fl__media img {{ max-width:88%; max-height:88%; object-fit:contain; filter: drop-shadow(0 5mm 5mm rgba(0,0,0,{'0.5' if field else '0.15'})); }}
  .fl__kicker {{ font-family:"Tektur",monospace; font-size:6.4pt; letter-spacing:.14em; color:var(--accent); }}
  .fl__name {{ font-size:17pt; line-height:1.02; margin:1.5mm 0 2mm; }}
  .fl__desc {{ font-size:8.6pt; color:var(--graphic); margin:0 0 3mm; }}
  .fl__row {{ display:flex; justify-content:space-between; gap:5mm; border-top:1px solid var(--line); padding:1.4mm 0; font-size:7.6pt; }}
  .fl__row span {{ color:var(--soft); }}
  .fl__row b {{ font-family:"Tektur",monospace; font-weight:400; font-size:7pt; text-align:right; }}
  .fl__price {{ margin-top:2.5mm; font-family:"Tektur",monospace; font-size:7.4pt; color:var(--soft); }}
  .fl__price b {{ font-size:11pt; color:var(--ink); font-weight:600; }}

  /* карточки каталога */
  .grid4 {{ display:grid; grid-template-columns:1fr 1fr; gap:6mm 7mm; }}
  .pc {{ display:flex; flex-direction:column; border-top:1px solid var(--line); padding-top:3mm; page-break-inside:avoid; }}
  .pc__media {{ height:44mm; display:flex; align-items:center; justify-content:center; background:var(--paper2); }}
  .pc__media img {{ max-width:86%; max-height:86%; object-fit:contain; filter: drop-shadow(0 3mm 3.4mm rgba(0,0,0,{'0.45' if field else '0.12'})); }}
  .pc__nophoto {{ font-family:"Tektur",monospace; font-size:5.6pt; color:var(--soft); }}
  .pc__cat {{ font-family:"Tektur",monospace; font-size:5.6pt; letter-spacing:.14em; color:var(--soft); text-transform:uppercase; margin:2mm 0 1mm; }}
  .pc__name {{ font-size:10.2pt; line-height:1.05; }}
  .pc__row {{ display:flex; justify-content:space-between; gap:4mm; border-top:1px solid var(--line); padding:1.1mm 0; font-size:6.6pt; }}
  .pc__row span {{ color:var(--soft); }}
  .pc__row b {{ font-family:"Tektur",monospace; font-weight:400; font-size:6.2pt; text-align:right; max-width:60mm; }}
  .pc__foot {{ margin-top:auto; display:flex; justify-content:space-between; align-items:baseline; padding-top:2.4mm; }}
  .pc__price {{ font-family:"Tektur",monospace; font-size:9pt; }}
  .pc__idx {{ font-family:"Tektur",monospace; font-size:6pt; color:var(--soft); }}
  .cat-label {{ font-family:"Oswald",sans-serif; text-transform:uppercase; letter-spacing:.08em; font-size:8pt; color:var(--accent); margin:6mm 0 2mm; }}

  /* применение/поставка */
  .apps {{ border-top:1px solid var(--line); }}
  .app {{ display:grid; grid-template-columns:8mm 40mm 1fr 24mm; gap:4mm; border-bottom:1px solid var(--line); padding:2.8mm 0; }}
  .app i {{ font-family:"Tektur",monospace; font-style:normal; font-size:6.2pt; color:var(--soft); }}
  .app b {{ font-family:"Oswald",sans-serif; font-weight:500; text-transform:uppercase; font-size:9pt; line-height:1.1; }}
  .app p {{ margin:0; font-size:7.6pt; color:var(--graphic); }}
  .app span {{ font-family:"Tektur",monospace; font-size:5.4pt; color:var(--soft); text-align:right; }}
  .steps7 {{ display:grid; grid-template-columns:repeat(2,1fr); gap:3mm; }}
  .step {{ border:1px solid var(--line); padding:3.4mm; }}
  .step b {{ font-family:"Tektur",monospace; font-size:6.4pt; color:var(--accent); }}
  .step h4 {{ font-family:"Oswald",sans-serif; font-weight:500; text-transform:uppercase; font-size:9pt; margin:1mm 0; }}
  .step p {{ margin:0; font-size:7pt; color:var(--graphic); }}

  /* дисклеймеры и контакты */
  .legal p {{ font-size:6.9pt; line-height:1.4; color:var(--graphic); margin:0 0 2.2mm; }}
  .legal p b {{ font-family:"Oswald",sans-serif; text-transform:uppercase; font-size:6.4pt; letter-spacing:.06em; color:var(--ink); }}
  .contacts {{ display:grid; grid-template-columns:1fr 1fr; gap:8mm; }}
  .contact-box {{ border:1px solid var(--line); padding:5mm; }}
  .contact-box b {{ font-family:"Tektur",monospace; font-size:10pt; }}
  .contact-box span {{ display:block; font-family:"Oswald",sans-serif; text-transform:uppercase; font-size:6.2pt; letter-spacing:.12em; color:var(--soft); margin-bottom:1.4mm; }}
</style>
</head>
<body>

<!-- ОБЛОЖКА -->
<section class="page cover">
  <div class="top">
    <div class="brand">
      <img src="assets/img/brand/logo_w_emblem.png" alt="" style="{'filter:none' if field else 'filter:invert(1) brightness(.1)'}">
      <div><b>В ОКОПЕ</b><span>каталог · НПО «Киловатт»</span></div>
    </div>
    <div class="meta">НПО «Киловатт» · Липецк<br>каталог изделий · 2026<br>E-mail / Telegram — по заявке</div>
  </div>
  <h1>СТАНЦИИ<br><span class="out">РЭБ</span><br><span class="accent">«КАПЮШОН»</span></h1>
  <p class="lead">Купольные, переносные и стационарные комплексы защиты объектов от БПЛА. Официальная линейка производителя в самостоятельном каталоге «В ОКОПЕ».</p>
  {'<div class="hero-img"><img src="assets/img/hero-k12m.png" alt=""></div>' if field else ''}
  {'' if field else '''<div class="zone-wrap"><svg class="zone" viewBox="0 0 800 560">
    <defs><path id="arcP" d="M 100 420 A 300 300 0 0 1 700 420"/></defs>
    <line class="zg" x1="20" y1="420" x2="780" y2="420"/>
    <path class="za" d="M 100 420 A 300 300 0 0 1 700 420"/>
    <text class="zarc"><textPath href="#arcP" startOffset="31%">ЗОНА ПРОТИВОДЕЙСТВИЯ БПЛА</textPath></text>
    <image href="assets/img/hero-k12m.png" x="325" y="330" width="150" height="90" preserveAspectRatio="xMidYMax meet"/>
    <line class="zt" x1="475" y1="420" x2="475" y2="404"/><line class="zt" x1="605" y1="420" x2="605" y2="404"/><line class="zt" x1="475" y1="410" x2="605" y2="410"/>
    <text class="zla" x="540" y="396" text-anchor="middle">50–200 М</text>
    <line class="zt" x1="100" y1="420" x2="100" y2="462"/><line class="zt" x1="700" y1="420" x2="700" y2="462"/><line class="zt" x1="100" y1="454" x2="700" y2="454"/>
    <text class="zla" x="400" y="480" text-anchor="middle">2000–3000 М</text>
    <text class="zl" x="400" y="498" text-anchor="middle">ОПЕРАТОР В УКРЫТИИ</text>
    <text class="zl" x="24" y="444">— ЗЕМЛЯ</text>
    <text class="zl" x="400" y="322" text-anchor="middle">СТАНЦИЯ К-12М</text>
  </svg></div>'''}
  <div class="foot">
    <div class="stats">
      <div class="stat"><b>300–5900</b><span>МГц диапазон</span></div>
      <div class="stat"><b>до 2400</b><span>Вт мощность</span></div>
      <div class="stat"><b>43</b><span>позиции</span></div>
      <div class="stat"><b>12</b><span>мес гарантия</span></div>
    </div>
    <div class="price-note">Цены поставщика без наценки ·<br>не публичная оферта · ноябрь 2026</div>
  </div>
</section>

<!-- О ПРОИЗВОДИТЕЛЕ + ДОКУМЕНТЫ -->
<section class="page">
  <div class="pg-head"><b>О производителе и документах</b><span class="small">01 / ПРОИЗВОДИТЕЛЬ</span></div>
  <div class="two">
    <div class="txt">
      <div class="sec-num">01.1 / КТО ДЕЛАЕТ ЛИНЕЙКУ</div>
      <h2 class="sec-title">НПО «Киловатт», Липецк</h2>
      <p class="lead">Российский разработчик и производитель станций РЭБ для защиты объектов от БПЛА.</p>
      <p style="margin-top:4mm">Собственное конструкторское бюро и производство полного цикла: от корпуса и антенн до сборки и заводских испытаний. В линейке более 20 моделей: купольные станции для транспорта, стационарные направленные комплексы, переносные рюкзаки, обнаружители дронов и аксессуары.</p>
      <p>«Капюшон» — зарегистрированный товарный знак производителя (свидетельство № 1086620 от 14.02.2025); на внешний вид станции получен патент RU 145992 S. На изделия оформлены сертификат соответствия и декларация о соответствии ЕАЭС. Гарантия — 12 месяцев; сервис и техническую поддержку обеспечивают производитель и его представители.</p>
      <p style="font-size:7pt;color:var(--soft)">Сведения об изготовителе: для «Капюшон» К-12М в паспорте — ООО «НПО «КИЛОВАТТ»»; для «Ребус-4», «Штора» К-12/700, «Штора-М» К-8/600 — ООО «НПО «МЕГАВАТТ»» (Липецк).</p>
    </div>
    <div>
      <div class="facts">
        <div class="fact"><b>20+</b><span>моделей в линейке</span></div>
        <div class="fact"><b>2015*</b><span>группа компаний</span></div>
        <div class="fact"><b>12 мес</b><span>гарантия по паспорту</span></div>
        <div class="fact"><b>Липецк</b><span>производство полного цикла</span></div>
      </div>
      <div class="sec-num" style="margin-top:6mm">01.2 / ДОКУМЕНТЫ</div>
      <div class="docs-list">
        <div><b>Товарный знак</b><span>«Капюшон», свид. № 1086620 от 14.02.2025</span></div>
        <div><b>Патент</b><span>RU 145992 S на внешний вид, 06.02.2025</span></div>
        <div><b>Сертификат</b><span>РОСС RU.32001.04ИБФ1.ОСП28.81271</span></div>
        <div><b>Декларация</b><span>ЕАЭС № RU Д-RU.PA07.B.24906/25</span></div>
        <div><b>Гарантия</b><span>12 месяцев, сервис производителя</span></div>
      </div>
      <div class="note" style="margin-top:6mm"><b>Оригинальность.</b> Паспорт изделия обязателен: изготовитель, характеристики, отметки заводских проверок. На шильдиках — модель и QR-код. Подделки под названиями «Капюшон», «Штора», «Ребус» на рынке встречаются.</div>
    </div>
  </div>
  <div class="pg-num">02</div>
</section>

<!-- ФЛАГМАНЫ -->
<section class="page">
  <div class="pg-head"><b>Три позиции, с которых начинают</b><span class="small">02 / ФЛАГМАНЫ</span></div>
  {''.join(flagship_block(p, i+1) for i, p in enumerate(flags))}
  <div class="pg-num">03</div>
</section>

<!-- КАТАЛОГ -->
{''.join(f'''
<section class="page">
  <div class="pg-head"><b>Каталог изделий</b><span class="small">03 / КАТАЛОГ · стр. {n+1}</span></div>
  <div class="grid4">
    {''.join(product_card(p, (n*8)+j+1) for j, p in enumerate(chunk))}
  </div>
  <div class="pg-num">{n+4:02d}</div>
</section>''' for n, chunk in enumerate(pages))}

<!-- ПРИМЕНЕНИЕ + ПОСТАВКА -->
<section class="page">
  <div class="pg-head"><b>Где это работает</b><span class="small">04 / ПРИМЕНЕНИЕ</span></div>
  <p style="margin:0 0 4mm;font-size:8.6pt">Собираем контур под объект: обнаружение → подавление → документы → сервис. Правовой режим применения проверяем до сделки.</p>
  <div class="apps">
    <div class="app"><i>01</i><b>Завод / промышленная площадка</b><p>«Ребус-4» для кругового прикрытия и «Сигнал-М2» для обнаружения; «Штора» К-12/700 на периметр и подъезды.</p><span>купольные / стационарные</span></div>
    <div class="app"><i>02</i><b>Склад / логистический хаб</b><p>Обнаружение + направленная «Штора» на вероятное направление подлёта; купольные станции на технику.</p><span>обнаружение</span></div>
    <div class="app"><i>03</i><b>Охрана периметра</b><p>Сначала обнаружение, затем направленные станции на углах; связка «детектор + станция» работает по факту.</p><span>детектор + станция</span></div>
    <div class="app"><i>04</i><b>Инфраструктура: ТЭК, ЛЭП</b><p>«Поле-31» против дронов по спутниковой навигации плюс «Ребус-4» для локальных площадок; для бригад — станции на транспорт и рюкзаки ТП.</p><span>площадные / мобильные</span></div>
    <div class="app"><i>05</i><b>АЗС / топливная инфраструктура</b><p>Компактные решения для небольшой площадки: «Штора-М» К-8/600 или «Капюшон» К-8М.</p><span>компактные</span></div>
    <div class="app"><i>06</i><b>Аэропорт / приаэродромная</b><p>Технически — «Ребус-4» и «Штора», но применение регулируется отдельно; только с уполномоченными подразделениями.</p><span>по согласованию</span></div>
    <div class="app"><i>07</i><b>Сельхозпредприятие</b><p>«Штора» К-12/700 на поля, купольные «Капюшон» на технику; детектор помогает не держать станции включёнными впустую.</p><span>площадные / купольные</span></div>
  </div>
  <div class="pg-head" style="margin-top:9mm"><b>Как проходит сделка</b><span class="small">05 / ПОСТАВКА</span></div>
  <div class="steps7">
    <div class="step"><b>01</b><h4>Заявка</h4><p>Объект, площадь, задачи, транспорт, питание, сроки.</p></div>
    <div class="step"><b>02</b><h4>Подбор</h4><p>Состав контура: обнаружение → станции → питание → монтаж.</p></div>
    <div class="step"><b>03</b><h4>КП</h4><p>Конфигурация, цена, сроки, состав документов.</p></div>
    <div class="step"><b>04</b><h4>Договор</h4><p>Комплектация, сроки, поставка, гарантия, ПНР.</p></div>
    <div class="step"><b>05</b><h4>Поставка</h4><p>Отгрузка со склада или под заказ с понятным сроком.</p></div>
    <div class="step"><b>06</b><h4>ПНР и обучение</h4><p>Монтаж, подключение, проверка РЭБ-тестером, инструктаж.</p></div>
    <div class="step"><b>07</b><h4>Гарантия и сервис</h4><p>12 месяцев, ремонт, поддержка и модернизация.</p></div>
  </div>
  <div class="pg-num">{len(pages)+4:02d}</div>
</section>

<!-- ДИСКЛЕЙМЕРЫ + КОНТАКТЫ -->
<section class="page">
  <div class="pg-head"><b>Правовой статус и контакты</b><span class="small">06 / ВАЖНО</span></div>
  <div class="legal">
    <p><b>Правовой статус.</b> Оборудование является радиоэлектронным средством. Порядок приобретения, регистрации и применения определяется законодательством РФ, в т.ч. 126-ФЗ «О связи», постановлениями Правительства РФ от 20.10.2021 № 1800 и от 10.10.2026 № 1331, решениями ГКРЧ. Возможность применения на конкретном объекте подтверждается заказчиком до ввода в эксплуатацию. Поставщик не оказывает юридических услуг и не гарантирует получение разрешений; ответственность за соблюдение условий применения несёт владелец (эксплуатант).</p>
    <p><b>Технические характеристики.</b> Приведены по паспортам изделий. Дальность зависит от рельефа, помеховой обстановки и погоды и не является гарантией нейтрализации конкретного аппарата. Производитель вправе вносить изменения.</p>
    <p><b>Цены и наличие.</b> Актуальны на дату публикации, не являются публичной офертой. Цены — по данным поставщика без наценки «В ОКОПЕ»; итоговая стоимость — в КП и договоре.</p>
    <p><b>Эксплуатация.</b> Запрещается вскрывать корпус и вмешиваться в конструкцию. При включённом изделии не рекомендуется находиться ближе 5 м (К-12М) или 15 м в створе направленности («Штора», «Ребус-4»); точные требования — в паспорте.</p>
    <p><b>Ограничение по применению.</b> Не допускается применение в местах угрозы безопасности полётов, связи, работе экстренных служб или жизни людей. Отдельные объекты (приаэродромные территории, ТЭК, транспорт) имеют специальный правовой режим.</p>
    <p><b>Сведения об изготовителе.</b> Для «Ребус-4», «Штора» К-12/700, «Штора-М» К-8/600 изготовитель в паспорте — ООО «НПО «МЕГАВАТТ»»; для «Капюшон» К-12М — ООО «НПО «КИЛОВАТТ»». Наименование в договоре должно соответствовать паспорту изделия.</p>
  </div>
  <div class="contacts" style="margin-top:9mm">
    <div class="contact-box"><span>Заявка и подбор</span><b>+7 (999) 136-71-42</b><p style="margin:3mm 0 0;font-size:7.6pt">«В ОКОПЕ» · подбор контура, документы, поставка, КП</p></div>
    <div class="contact-box"><span>Производитель</span><b>НПО «Киловатт» / «МегаВатт»</b><p style="margin:3mm 0 0;font-size:7.6pt">Липецк · сервис и техническая поддержка по паспорту изделия</p></div>
  </div>
  <div class="pg-num">{len(pages)+5:02d}</div>
</section>

</body>
</html>"""
    return html_doc


def main():
    if not os.path.exists(BUILD):
        raise SystemExit("нет catalog_build.json — сначала build_data.py")
    prods = load()
    for theme, out in (("field", OUT_FIELD), ("quiet", OUT_QUIET)):
        doc = build(theme, prods)
        open(out, "w", encoding="utf-8").write(doc)
        print(theme, "->", out, len(doc), "байт")


if __name__ == "__main__":
    main()
