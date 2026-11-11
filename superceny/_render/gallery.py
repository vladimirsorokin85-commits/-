# -*- coding: utf-8 -*-
"""Галерея «СУПЕРЦЕНЫ»: superceny/05_ГОТОВОЕ/gallery/index.html (офлайн).

43 позиции × 4 карточки + hero. Клик — открыть PNG в новом окне.
Использование: python _render/gallery.py [--partial]
"""
from __future__ import annotations

import argparse
import html
import time
from pathlib import Path

import superlib as L


def scan() -> tuple[Path | None, list[dict]]:
    hero = L.OUT_DIR / "00_СУПЕРЦЕНЫ.png"
    hero = hero if hero.is_file() else None
    pos = L.positions()
    folders = []
    if L.OUT_DIR.is_dir():
        for d in sorted([p for p in L.OUT_DIR.iterdir() if p.is_dir()]):
            cards = []
            for code in ("01", "02", "03", "04"):
                p = d / (L.CARD_NAMES[code] + ".png")
                if p.is_file():
                    cards.append({"code": code, "path": p, "title": L.CARD_TITLES[code]})
            if cards:
                meta = pos.get(d.name, {})
                title = meta.get("name") or d.name
                sub = meta.get("name_full") or meta.get("category") or ""
                folders.append({"dir": d, "cards": cards, "title": title, "sub": sub,
                                "meta": meta, "n": len(cards)})
    return hero, folders


def card_html(c: dict, folder: Path) -> str:
    p = c["path"]
    dims = L.png_dims(p) or (0, 0)
    rel = p.relative_to(L.OUT_DIR).as_posix()
    title = html.escape(c["title"])
    code = c["code"]
    return f"""        <figure class="card">
          <a href="../{html.escape(rel)}" target="_blank" rel="noopener">
            <img src="../{html.escape(rel)}" alt="{code} · {title}" loading="lazy">
          </a>
          <figcaption><b>{code}</b> {title}<span class="meta">{dims[0]}×{dims[1]} · {L.human_size(p.stat().st_size)}</span></figcaption>
        </figure>"""


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
      <div class="hero-cap"><b>00 · СУПЕРЦЕНЫ</b> — общая карточка · {dims[0]}×{dims[1]} · {L.human_size(hero.stat().st_size)}</div>
    </section>"""

    sections = []
    for f in folders:
        cards = "\n".join(card_html(c, f["dir"]) for c in f["cards"])
        sub = f'<span class="sub">{html.escape(f["sub"])}</span>' if f["sub"] else ""
        sections.append(f"""<section class="pos">
      <h2>{html.escape(f["title"])} <span class="dir">{html.escape(f["dir"].name)}</span>{sub}</h2>
      <div class="grid">
{cards}
      </div>
    </section>""")

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>СУПЕРЦЕНЫ НА НПО «КИЛОВАТТ» — галерея карточек</title>
<style>
  :root {{ --bg:#14150F; --panel:#1C2317; --line:#333A2B; --paper:#EDE8D7; --lime:#C9F24B; --muted:#9A9F8C; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--paper);
         font-family:"Segoe UI", system-ui, -apple-system, Arial, sans-serif; }}
  .wrap {{ max-width:1560px; margin:0 auto; padding:32px 24px 70px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:18px; }}
  h1 {{ margin:0; font-size:clamp(24px, 3vw, 36px); letter-spacing:.04em; text-transform:uppercase; }}
  h1 span {{ color:var(--lime); }}
  .subline {{ margin-top:8px; color:var(--muted); font-size:14px; }}
  .hero {{ margin:26px 0 10px; max-width:760px; }}
  .hero img {{ display:block; width:100%; height:auto; border:1px solid var(--line); background:#F4F1EA; }}
  .hero-cap {{ margin-top:8px; color:var(--muted); font-size:13px; }}
  .hero-cap b {{ color:var(--lime); }}
  .pos {{ margin-top:34px; }}
  .pos h2 {{ margin:0 0 12px; font-size:17px; line-height:1.3; letter-spacing:.02em; }}
  .pos h2 .dir {{ display:block; margin-top:3px; color:var(--muted); font-size:12px; font-weight:400; letter-spacing:.06em; }}
  .pos h2 .sub {{ display:block; margin-top:2px; color:var(--muted); font-size:12px; font-weight:400; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:18px; }}
  .card {{ margin:0; background:var(--panel); border:1px solid var(--line); }}
  .card a {{ display:block; background:#F4F1EA; }}
  .card img {{ display:block; width:100%; height:auto; }}
  .card figcaption {{ padding:9px 11px 11px; font-size:13px; line-height:1.35; }}
  .card figcaption b {{ color:var(--lime); margin-right:3px; }}
  .card .meta {{ display:block; margin-top:3px; color:var(--muted); font-size:11px; }}
  .card:hover {{ border-color:#4C563C; }}
  footer {{ margin-top:44px; padding-top:14px; border-top:1px solid var(--line); color:#7C816F; font-size:12px; line-height:1.6; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>СУПЕРЦЕНЫ <span>·</span> галерея карточек</h1>
    <div class="subline">НПО «Киловатт» × магазин «В ОКОПЕ» · 20 позиций × 4 карточки + общая ·
      готово карточек: {n_cards}/{L.EXPECT_CARDS}, позиций с полным набором: {n_full}/{L.EXPECT_POSITIONS} · ноябрь 2026</div>
    <div class="subline">Клик по карточке — открыть PNG 1080×1350 в новом окне. Галерея работает локально, без интернета.</div>
  </header>
  {hero_html}
{chr(10).join(sections)}
  <footer>
    СУПЕРЦЕНЫ · каждая позиция — 4 карточки: 01 СУПЕРЦЕНА · 02 ХАРАКТЕРИСТИКИ · 03 ПРИМЕНЕНИЕ · 04 СУПЕР-ПРЕДЛОЖЕНИЕ.<br>
    Цены не публикуются числами: «Прайс по запросу». CTA: Telegram @vokope_ru · +7 (999) 136-71-42 ·
    Доставка по РФ · Самовывоз в Москве.<br>
    Собрано: {time.strftime('%d.%m.%Y %H:%M')} · renderer (DSH), пакет «СУПЕРЦЕНЫ».
  </footer>
</div>
</body>
</html>
"""
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"Галерея: {index} ({L.human_size(index.stat().st_size)})")
    print(f"  карточек: {n_cards}/{L.EXPECT_CARDS}, позиций: {len(folders)}/{L.EXPECT_POSITIONS} "
          f"(полных: {n_full}), hero: {'есть' if hero else 'НЕТ'}")
    if (n_cards < L.EXPECT_CARDS or len(folders) < L.EXPECT_POSITIONS or hero is None) and not a.partial:
        print("  ВНИМАНИЕ: пакет неполный")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
