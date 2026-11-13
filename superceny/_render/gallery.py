# -*- coding: utf-8 -*-
"""Галерея-карусель «СУПЕРЦЕНЫ» v5 «СОРВАННЫЙ ЦЕННИК» — светлая бумага, печатный стиль.

20 серий по 4 слайда в ряд со стрелками; клик — открыть PNG. Плюс hero.
Офлайн, без внешних ресурсов. Использование: python _render/gallery.py [--partial]
"""
from __future__ import annotations

import argparse
import html
import time
from pathlib import Path

import superlib as L

SLIDES = ["01", "02", "03", "04"]


def scan() -> tuple[Path | None, list[dict]]:
    hero = L.OUT_DIR / "00_СУПЕРЦЕНЫ.png"
    hero = hero if hero.is_file() else None
    pos = L.positions()
    folders = []
    if L.OUT_DIR.is_dir():
        for d in sorted([p for p in L.OUT_DIR.iterdir() if p.is_dir()]):
            cards = []
            for code in SLIDES:
                p = d / (L.CARD_NAMES[code] + ".png")
                if p.is_file():
                    cards.append({"code": code, "path": p, "title": L.CARD_TITLES[code]})
            if cards:
                meta = pos.get(d.name, {})
                folders.append({"dir": d, "cards": cards,
                                "title": meta.get("name") or d.name,
                                "sub": meta.get("name_full") or meta.get("category") or "",
                                "n": len(cards)})
    return hero, folders


def slide_html(c: dict) -> str:
    p = c["path"]
    rel = p.relative_to(L.OUT_DIR).as_posix()
    dims = L.png_dims(p) or (0, 0)
    code = c["code"]
    title = html.escape(c["title"])
    return f"""        <a class="slide" href="../{html.escape(rel)}" target="_blank" rel="noopener">
          <img src="../{html.escape(rel)}" alt="{code} · {title}" loading="lazy">
          <span class="cap"><b>{code}/04</b> {title} · {dims[0]}×{dims[1]} · {L.human_size(p.stat().st_size)}</span>
        </a>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.GALLERY_DIR))
    ap.add_argument("--partial", action="store_true")
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    hero, folders = scan()
    n_cards = sum(f["n"] for f in folders)
    n_full = sum(1 for f in folders if f["n"] == 4)

    hero_html = ""
    if hero is not None:
        dims = L.png_dims(hero) or (0, 0)
        hero_html = f"""<section class="hero">
      <a href="../00_СУПЕРЦЕНЫ.png" target="_blank" rel="noopener">
        <img src="../00_СУПЕРЦЕНЫ.png" alt="СУПЕРЦЕНЫ — общая карточка" loading="lazy">
      </a>
      <div class="hero-cap"><b>00 · СУПЕРЦЕНЫ</b> — обложка прайс-листовки · {dims[0]}×{dims[1]} · {L.human_size(hero.stat().st_size)}</div>
    </section>"""

    sections = []
    for f in folders:
        slides = "\n".join(slide_html(c) for c in f["cards"])
        sub = f'<span class="sub">{html.escape(f["sub"])}</span>' if f["sub"] else ""
        num = html.escape(f["dir"].name.split("_")[0])
        sections.append(f"""<section class="pos">
      <h2><b class="num">{num}</b> {html.escape(f["title"])}<span class="dir">{html.escape(f["dir"].name)}</span>{sub}</h2>
      <div class="carousel">
        <button class="nav prev" aria-label="Предыдущий слайд">‹</button>
        <div class="track">
{slides}
        </div>
        <button class="nav next" aria-label="Следующий слайд">›</button>
      </div>
      <div class="strip">01 ЛИСТАЙ → 02 ЦИФРЫ → 03 СЦЕНАРИИ → 04 CTA</div>
    </section>""")

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>СУПЕРЦЕНЫ · СОРВАННЫЙ ЦЕННИК — карусели v5 · В ОКОПЕ × НПО «Киловатт»</title>
<style>
  :root {{ --paper:#F1E8D6; --ink:#17150F; --red:#E23B2E; --muted:#6E6556; --line:#C6BAA4; --card:#FBF7EE; }}
  * {{ box-sizing:border-box; }}
  html {{ background:var(--paper); }}
  body {{ margin:0; background:
        repeating-linear-gradient(0deg, rgba(23,21,15,.018) 0 1px, transparent 1px 3px),
        var(--paper);
        color:var(--ink); font-family:"Segoe UI", system-ui, -apple-system, Arial, sans-serif; }}
  .wrap {{ max-width:1560px; margin:0 auto; padding:34px 26px 80px; }}
  header {{ border-bottom:2px solid var(--ink); padding-bottom:18px; }}
  h1 {{ margin:0; font-family:"Arial Black","Segoe UI",sans-serif; font-weight:900;
        font-size:clamp(28px, 4vw, 52px); line-height:.92; letter-spacing:-.02em; text-transform:uppercase; }}
  h1 span {{ color:var(--red); }}
  .subline {{ margin-top:10px; color:var(--muted); font-size:14px; max-width:1000px; }}
  .kicker {{ display:inline-block; margin-top:14px; padding:4px 10px; border:2px solid var(--red);
             color:var(--red); font-size:13px; letter-spacing:.16em; text-transform:uppercase;
             transform:rotate(-1.2deg); }}
  .hero {{ margin:28px 0 10px; max-width:720px; }}
  .hero img {{ display:block; width:100%; height:auto; border:1px solid var(--line); background:var(--paper); }}
  .hero-cap {{ margin-top:8px; color:var(--muted); font-size:13px; }}
  .hero-cap b {{ color:var(--red); }}
  .pos {{ margin-top:42px; }}
  .pos h2 {{ margin:0 0 12px; font-size:18px; line-height:1.3; display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }}
  .pos h2 .num {{ color:var(--red); font-family:"Arial Black","Segoe UI",sans-serif; font-size:26px; }}
  .pos h2 .dir {{ color:var(--muted); font-size:12px; font-weight:400; letter-spacing:.06em; }}
  .pos h2 .sub {{ color:var(--muted); font-size:12px; font-weight:400; width:100%; }}
  .carousel {{ position:relative; }}
  .track {{ display:flex; gap:16px; overflow-x:auto; scroll-snap-type:x mandatory;
            scrollbar-width:thin; padding-bottom:6px; scroll-behavior:smooth; }}
  .slide {{ flex:0 0 calc((100% - 48px) / 4); scroll-snap-align:start; position:relative;
            background:var(--card); border:1px solid var(--line); text-decoration:none; color:inherit; }}
  .slide img {{ display:block; width:100%; height:auto; background:var(--paper); }}
  .slide .cap {{ display:block; padding:8px 10px 10px; font-size:12px; line-height:1.3;
                 border-top:1px solid var(--line); }}
  .slide .cap b {{ color:var(--red); margin-right:3px; }}
  .slide:hover {{ border-color:var(--ink); }}
  .nav {{ position:absolute; top:42%; z-index:2; width:40px; height:66px; border:2px solid var(--ink);
          background:var(--paper); color:var(--ink); font-size:28px; line-height:1; cursor:pointer; padding:0; }}
  .nav:hover {{ background:var(--red); border-color:var(--red); color:var(--paper); }}
  .nav.prev {{ left:-16px; }}
  .nav.next {{ right:-16px; }}
  .strip {{ margin-top:8px; color:var(--muted); font-size:12px; letter-spacing:.06em; text-transform:uppercase; }}
  @media (max-width:1100px) {{ .slide {{ flex-basis: calc((100% - 16px) / 2); }} }}
  @media (max-width:640px) {{ .slide {{ flex-basis:86%; }} }}
  footer {{ margin-top:48px; padding-top:16px; border-top:2px solid var(--ink); color:var(--muted); font-size:12px; line-height:1.6; }}
  footer b {{ color:var(--ink); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>СУПЕРЦЕНЫ <span>/</span> сорванный ценник</h1>
    <span class="kicker">карусель v5 · печатный плакат</span>
    <div class="subline">НПО «Киловатт» × магазин «В ОКОПЕ» · 20 позиций × 4 страницы прайс-листовки ·
      готово слайдов: {n_cards}/{L.EXPECT_CARDS}, полных серий: {n_full}/{L.EXPECT_POSITIONS} · ноябрь 2026</div>
    <div class="subline">Страницы идут подряд как история: 01 ЛИСТАЙ → 02 ЦИФРЫ → 03 СЦЕНАРИИ → 04 CTA.
      Стрелки листают серию; клик по слайду — PNG 1080×1350 в новом окне. Галерея работает локально.</div>
  </header>
  {hero_html}
{chr(10).join(sections)}
  <footer>
    Механизм серии: <b>цену не напечатали — настолько она спец</b>. Обрывок ценника летит через все
    страницы, на 04 — целый ценник «ПРАЙС ПО ЗАПРОСУ» с перфорацией и контактом.<br>
    Две краски: бумага #F1E8D6, тушь #17150F, сигнальный #E23B2E. CTA: Telegram @vokope_ru ·
    +7 (999) 136-71-42 · Доставка по РФ · Самовывоз в Москве.<br>
    Собрано: {time.strftime('%d.%m.%Y %H:%M')} · renderer (DSH), пакет «СУПЕРЦЕНЫ» (карусель v5).
  </footer>
</div>
<script>
(function () {{
  document.querySelectorAll('.carousel').forEach(function (c) {{
    var track = c.querySelector('.track');
    c.querySelectorAll('.nav').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        var step = track.clientWidth * (btn.classList.contains('next') ? 0.55 : -0.55);
        track.scrollBy({{ left: step, behavior: 'smooth' }});
      }});
    }});
  }});
}})();
</script>
</body>
</html>
"""
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"Галерея-карусель v5: {index} ({L.human_size(index.stat().st_size)})")
    print(f"  слайдов: {n_cards}/{L.EXPECT_CARDS}, серий: {len(folders)}/{L.EXPECT_POSITIONS} "
          f"(полных: {n_full}), hero: {'есть' if hero else 'НЕТ'}")
    if (n_cards < L.EXPECT_CARDS or len(folders) < L.EXPECT_POSITIONS or hero is None) and not a.partial:
        print("  ВНИМАНИЕ: пакет неполный")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
