# -*- coding: utf-8 -*-
"""Галерея баннеров: banners/05_ГОТОВОЕ/gallery/index.html (офлайн).

18 моделей × 2 формата; клик — открыть PNG, ссылки на @2x и PDF.
Использование: python _render/gallery.py
"""
from __future__ import annotations

import argparse
import html
import time
from pathlib import Path

import bannerlib as L


def collect() -> dict[str, dict[str, dict]]:
    """fmt -> id -> {png, dims, bytes, thumb, twox}"""
    groups: dict[str, dict[str, dict]] = {"poster": {}, "square": {}, "story": {}}
    for p in sorted(L.PNG_DIR.glob("*.png")) if L.PNG_DIR.is_dir() else []:
        stem = p.stem
        if stem.endswith("@2x"):
            continue
        base, fmt, pid = L.classify(stem)
        if fmt not in groups or not pid:
            continue
        dims = L.png_dims(p) or (0, 0)
        preview = L.PREVIEW_DIR / (stem + ".jpg")
        thumb = f"превью/{preview.name}" if preview.is_file() else f"png/{p.name}"
        twox = L.PNG_DIR / (stem + "@2x.png")
        groups[fmt][pid] = {"stem": stem, "png": p.name, "dims": dims,
                            "bytes": p.stat().st_size, "thumb": thumb,
                            "twox": twox.name if twox.is_file() else ""}
    return groups


def card(pid: str, item: dict) -> str:
    title = html.escape(L.MODELS.get(pid, item["stem"]))
    dims = f"{item['dims'][0]}×{item['dims'][1]}"
    twox = (f' · <a href="../png/{html.escape(item["twox"])}" target="_blank" rel="noopener">2×</a>'
            if item["twox"] else "")
    return f"""      <figure class="card">
        <a class="shot" href="../png/{html.escape(item['png'])}" target="_blank" rel="noopener">
          <img src="../{html.escape(item['thumb'])}" alt="{pid} {title}" loading="lazy">
        </a>
        <figcaption>
          <div class="cap"><b>{pid}</b> {title}</div>
          <div class="meta">{dims} px · {L.human_size(item['bytes'])}{twox}</div>
        </figcaption>
      </figure>"""


def section(title: str, items: dict[str, dict], order: list[str]) -> str:
    if not items:
        return ""
    cards = "\n".join(card(pid, items[pid]) for pid in order if pid in items)
    return f'    <h2>{html.escape(title)}</h2>\n    <div class="grid">\n{cards}\n    </div>'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.GALLERY_DIR))
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = collect()
    n_poster, n_square = len(groups["poster"]), len(groups["square"])
    n_story = len(groups["story"])
    pdf_block = (f'<p class="pdf">PDF-альбом A4 (19 стр.): <a href="../pdf/{html.escape(L.PDF_NAME)}" '
                 f'target="_blank" rel="noopener">{html.escape(L.PDF_NAME)}</a> · '
                 f'{L.human_size(L.PDF_PATH.stat().st_size)}</p>'
                 if L.PDF_PATH.is_file() else '<p class="pdf muted">PDF-альбом ещё не собран.</p>')
    body = "\n".join(s for s in [
        section("Посты · 1080×1350", groups["poster"], L.ORDER),
        section("Квадраты · 1080×1080", groups["square"], L.ORDER),
        section("Сторис · 1080×1920", groups["story"], L.STORY_IDS),
    ] if s)
    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Рекламные баннеры «Киловатт» — галерея · В ОКОПЕ</title>
<style>
  :root {{ --bg:#14150F; --panel:#1C2317; --line:#333A2B; --paper:#EDE8D7; --lime:#C9F24B; --muted:#9A9F8C; }}
  * {{ box-sizing:border-box; }}
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
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:20px; }}
  .card {{ margin:0; background:var(--panel); border:1px solid var(--line); display:flex; flex-direction:column; }}
  .shot {{ display:block; background:#F4F1EA; }}
  .card img {{ display:block; width:100%; height:auto; }}
  .card figcaption {{ padding:10px 12px 12px; }}
  .cap {{ font-size:14px; line-height:1.35; }}
  .cap b {{ color:var(--lime); font-weight:700; margin-right:4px; }}
  .meta {{ margin-top:5px; color:var(--muted); font-size:12px; }}
  .meta a {{ color:var(--lime); }}
  .card:hover {{ border-color:#4C563C; }}
  footer {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--line); color:#7C816F; font-size:12px; line-height:1.6; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Рекламные баннеры <span>·</span> галерея</h1>
    <div class="sub">НПО «Киловатт» × магазин «В ОКОПЕ» · 18 моделей · посты, квадраты и сторис ·
      постов: {n_poster}, квадратов: {n_square}, сторис: {n_story} · ноябрь 2026</div>
    {pdf_block}
    <div class="sub">Клик по баннеру — открыть PNG в новом окне. Галерея работает локально, без интернета.</div>
  </header>
{body}
  <footer>
    Пост 1080×1350 (VK/Telegram/Авито) · Квадрат 1080×1080 (VK-лента/Авито/превью) ·
    Сторис 1080×1920 (6 топ-моделей) · PNG 1× и 2×.<br>
    Цены не публикуются: «Цена по запросу». CTA: Telegram @vokope_ru · +7 (999) 136-71-42 ·
    Доставка по РФ · Самовывоз в Москве.<br>
    Собрано: {time.strftime('%d.%m.%Y %H:%M')} · renderer (DSH), пакет «Рекламные баннеры».
  </footer>
</div>
</body>
</html>
"""
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"Галерея: {index} ({L.human_size(index.stat().st_size)})")
    print(f"  посты: {n_poster}/18, квадраты: {n_square}/18, сторис: {n_story}/6")
    if n_poster < 18 or n_square < 18 or n_story < 6:
        print("  ВНИМАНИЕ: баннеры ещё не все отрендерены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
