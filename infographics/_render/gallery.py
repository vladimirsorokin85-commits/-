# -*- coding: utf-8 -*-
"""Галерея готовых постеров: 05_ГОТОВОЕ/gallery/index.html (офлайн, без внешних ресурсов).

Сетка превью с подписями P01…P10, клик — открыть PNG в новом окне.
Использует JPG-превью из 05_ГОТОВОЕ/превью (если есть), иначе сами PNG.

Использование:
  python _render/gallery.py [--out DIR] [--open]
"""
from __future__ import annotations

import argparse
import html
import time
from pathlib import Path

import posterlib as L


def card_html(item: dict, png_rel: str) -> str:
    title = html.escape(L.title_for(item["stem"]))
    pid = html.escape(L.poster_id(item["stem"]) or "—")
    dims = f"{item['dims'][0]}×{item['dims'][1]}"
    weight = L.human_size(item["bytes"])
    thumb = item["thumb"].replace("\\", "/")
    src = f"../{thumb}"
    extra = ""
    if item.get("twox"):
        extra = f' · <a href="../png/{html.escape(item["twox"])}" target="_blank" rel="noopener">PNG 2×</a>'
    return f"""      <figure class="card">
        <a class="shot" href="../png/{html.escape(item["png"])}" target="_blank" rel="noopener">
          <img src="{html.escape(src)}" alt="{pid} {title}" loading="lazy">
        </a>
        <figcaption>
          <div class="cap"><b>{pid}</b> {title}</div>
          <div class="meta">{dims} px · {weight}{extra}</div>
        </figcaption>
      </figure>"""


def build_section(title: str, items: list[dict]) -> str:
    if not items:
        return ""
    cards = "\n".join(card_html(it, it["png"]) for it in items)
    return f"""    <h2>{html.escape(title)}</h2>
    <div class="grid">
{cards}
    </div>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.GALLERY_DIR))
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    groups: dict[str, list[dict]] = {"main": [], "wide": [], "story": []}
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        stem, kind, scale = L.classify_png(p.name)
        if scale != 1:
            continue
        dims = L.png_kind_dims(p) or (0, 0)
        preview = L.PREVIEW_DIR / (p.stem + ".jpg")
        thumb = f"превью/{preview.name}" if preview.is_file() else f"png/{p.name}"
        twox = L.PNG_DIR / (L.canon_stem(stem) + "@2x.png")
        groups[kind].append({
            "stem": stem, "png": p.name, "dims": dims, "bytes": p.stat().st_size,
            "thumb": thumb,
            "twox": twox.name if (kind == "main" and twox.is_file()) else "",
        })

    def sort_main(items):
        def key(it):
            pid = L.poster_id(it["stem"])
            return (L.ORDER_MAIN.index(pid) if pid in L.ORDER_MAIN else 99, it["stem"])
        return sorted(items, key=key)

    groups["main"] = sort_main(groups["main"])
    groups["wide"] = sorted(groups["wide"], key=lambda x: x["stem"])
    groups["story"] = sorted(groups["story"], key=lambda x: x["stem"])

    have_main = len(groups["main"])
    pdf_rel = f"../pdf/{L.PDF_NAME}"
    pdf_exists = L.PDF_PATH.is_file()
    pdf_block = ""
    if pdf_exists:
        pdf_block = (f'<p class="pdf">PDF-альбом A4: <a href="{html.escape(pdf_rel)}" target="_blank" '
                     f'rel="noopener">{html.escape(L.PDF_NAME)}</a> · {L.human_size(L.PDF_PATH.stat().st_size)}</p>')
    else:
        pdf_block = '<p class="pdf muted">PDF-альбом ещё не собран.</p>'

    total_extras = len(groups["wide"]) + len(groups["story"])
    body_sections = "\n".join(s for s in [
        build_section("Основная серия · 1080×1350", groups["main"]),
        build_section("Широкие · 1920×1080", groups["wide"]),
        build_section("Истории · 1080×1920", groups["story"]),
    ] if s)

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>«Два горизонта» — галерея постеров · НПО «Киловатт» × «В ОКОПЕ»</title>
<style>
  :root {{ --bg:#14150F; --panel:#1C2317; --line:#333A2B; --paper:#EDE8D7; --lime:#C9F24B; --muted:#9A9F8C; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--paper);
         font-family:"Segoe UI", system-ui, -apple-system, Arial, sans-serif; }}
  .wrap {{ max-width:1560px; margin:0 auto; padding:34px 26px 70px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:18px; }}
  h1 {{ margin:0; font-size:clamp(24px, 3.2vw, 38px); letter-spacing:.04em; text-transform:uppercase; }}
  h1 span {{ color:var(--lime); }}
  .sub {{ margin-top:8px; color:var(--muted); font-size:14px; }}
  .pdf {{ margin:16px 0 0; font-size:14px; }}
  .pdf a {{ color:var(--lime); }}
  .muted {{ color:var(--muted); }}
  h2 {{ margin:38px 0 14px; font-size:14px; letter-spacing:.18em; text-transform:uppercase;
        color:var(--lime); border-bottom:1px solid var(--line); padding-bottom:9px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr)); gap:20px; }}
  .card {{ margin:0; background:var(--panel); border:1px solid var(--line); display:flex; flex-direction:column; }}
  .card .shot {{ display:block; background:#F4F1EA; }}
  .card img {{ display:block; width:100%; height:auto; }}
  .card figcaption {{ padding:10px 12px 12px; }}
  .card .cap {{ font-size:14px; line-height:1.35; }}
  .card .cap b {{ color:var(--lime); font-weight:700; margin-right:4px; }}
  .card .meta {{ margin-top:5px; color:var(--muted); font-size:12px; }}
  .card .meta a {{ color:var(--lime); }}
  .card:hover {{ border-color:#4C563C; }}
  footer {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--line); color:#7C816F; font-size:12px; line-height:1.6; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Два горизонта <span>·</span> галерея</h1>
    <div class="sub">НПО «Киловатт» × магазин «В ОКОПЕ» · инфографика · ноябрь 2026 ·
      постеров: {have_main} (основная серия){f', дополнительно: {total_extras}' if total_extras else ''}</div>
    {pdf_block}
    <div class="sub">Клик по постеру — открыть PNG в новом окне. Галерея работает локально, без интернета.</div>
  </header>
{body_sections}
  <footer>
    Пакет: infographics/05_ГОТОВОЕ · основная серия 1080×1350 (PNG 1× и 2×), широкие 1920×1080, истории 1080×1920.<br>
    Цены в материалах не публикуются: «Цена по запросу», «КП под задачу». CTA: Telegram @vokope_ru · +7 999 136-71-42 ·
    Доставка по РФ · Самовывоз в Москве.<br>
    Собрано: {time.strftime('%d.%m.%Y %H:%M')} · renderer (DSH), пакет «Два горизонта».
  </footer>
</div>
</body>
</html>
"""
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"Галерея: {index} ({L.human_size(index.stat().st_size)})")
    print(f"  основная серия: {have_main}, широкие: {len(groups['wide'])}, истории: {len(groups['story'])}")
    if have_main < 10:
        print(f"  ВНИМАНИЕ: основной серии {have_main}/10 — постеры ещё не все отрендерены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
