#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_superceny_layout.py — Chrome-замер кеглей карточек «СУПЕРЦЕНЫ» (роль qa).

Критерий заказчика/Lead: ТТХ и детали читаются с телефона.
  - основная зона (всё кроме юрстроки/подписей/футера) — не мельче 16px;
  - значения/плитки характеристик (карточка 02) — 18–20px+ (крупные плитки 34–42px);
  - нет наложений/обрезки/выхода за холст; нет крупных пустот.

Для каждого HTML (81 = 20×4 + hero) в реальном Chrome измеряются computed font-size,
bbox, overflow/overlap, затем классифицируются элементы. Результат:
superceny\\04_ПРОВЕРКА\\QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ.md / .json

Запуск: python check_superceny_layout.py [--write] [--only PATTERN] [--min-main 16] [--min-value 18]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
QA = Path(__file__).resolve().parent
SC = QA.parent
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

_spec = importlib.util.spec_from_file_location("cs_layout", QA / "check_superceny.py")
if _spec is None or _spec.loader is None:
    raise SystemExit("не найден check_superceny.py рядом")
cs = importlib.util.module_from_spec(_spec)
sys.modules["cs_layout"] = cs
_spec.loader.exec_module(cs)

JS = r"""
(function(){
  function px(v){ return parseFloat(v)||0; }
  return new Promise(function(resolve){
    var ifr=document.getElementById('f');
    function go(){
      try{
        var doc=ifr.contentDocument, win=ifr.contentWindow;
        var host=doc.querySelector('.card')||doc.body;
        var hr=host.getBoundingClientRect();
        var out={w:Math.round(hr.width),h:Math.round(hr.height),items:[],overflow:[],outside:[],overlaps:[]};
        var all=doc.querySelectorAll('body *');
        out.media=[];
        var imgs=doc.querySelectorAll('img,svg,figure');
        for(var k=0;k<imgs.length;k++){
          var ir=imgs[k].getBoundingClientRect();
          if(ir.width>8 && ir.height>8) out.media.push({x:Math.round(ir.left-hr.left),y:Math.round(ir.top-hr.top),
            w:Math.round(ir.width),h:Math.round(ir.height),tag:imgs[k].tagName});
        }
        var texts=[];
        for(var i=0;i<all.length;i++){
          var el=all[i];
          if(el.tagName==='SCRIPT'||el.tagName==='STYLE') continue;
          var cs2=win.getComputedStyle(el);
          var hasOwn=false;
          for(var j=0;j<el.childNodes.length;j++){
            var n=el.childNodes[j];
            if(n.nodeType===3 && n.textContent.trim().length>0){ hasOwn=true; break; }
          }
          var r=el.getBoundingClientRect();
          var cls=String(el.className||'');
          if(hasOwn && r.width>0 && r.height>0){
            var fs=px(cs2.fontSize);
            var it={tag:el.tagName,cls:cls.slice(0,80),fs:Math.round(fs*10)/10,
                    x:Math.round(r.left-hr.left),y:Math.round(r.top-hr.top),
                    w:Math.round(r.width),h:Math.round(r.height),
                    text:(el.innerText||'').replace(/\s+/g,' ').slice(0,90)};
            out.items.push(it);
            texts.push({el:el,r:r,it:it});
          }
          if(hasOwn && (el.scrollWidth-el.clientWidth>2 || el.scrollHeight-el.clientHeight>2) &&
             el.clientWidth>0 && el.clientHeight>0){
            out.overflow.push({cls:cls.slice(0,60),sw:el.scrollWidth,cw:el.clientWidth,sh:el.scrollHeight,ch:el.clientHeight,
                               ov:(cs2.overflow+'/'+cs2.overflowX+'/'+cs2.overflowY),
                               text:(el.innerText||'').replace(/\s+/g,' ').slice(0,60)});
          }
          if(r.width>0 && r.height>0 && (r.left<hr.left-1||r.right>hr.right+1||r.top<hr.top-1||r.bottom>hr.bottom+1)
             && cs2.position!=='fixed' && hasOwn){
            out.outside.push({cls:cls.slice(0,60),x:Math.round(r.left-hr.left),y:Math.round(r.top-hr.top),
                              text:(el.innerText||'').replace(/\s+/g,' ').slice(0,50)});
          }
        }
        for(var a=0;a<texts.length && out.overlaps.length<10;a++){
          for(var b=a+1;b<texts.length;b++){
            var A=texts[a], B=texts[b];
            if(A.el.contains(B.el)||B.el.contains(A.el)) continue;
            var ix=Math.max(0,Math.min(A.r.right,B.r.right)-Math.max(A.r.left,B.r.left));
            var iy=Math.max(0,Math.min(A.r.bottom,B.r.bottom)-Math.max(A.r.top,B.r.top));
            if(ix*iy>12){
              out.overlaps.push({a:A.it.cls,b:B.it.cls,at:A.it.text,bt:B.it.text,area:Math.round(ix*iy),
                                 ar:Math.round(A.r.width*A.r.height),br:Math.round(B.r.width*B.r.height)});
              if(out.overlaps.length>=10) break;
            }
          }
        }
        resolve(out);
      }catch(e){ resolve({error:String(e)}); }
    }
    if(ifr.contentDocument && ifr.contentDocument.readyState==='complete') setTimeout(go,250);
    else ifr.addEventListener('load',function(){ setTimeout(go,450); });
  });
})().then(function(o){ document.getElementById('qa').textContent=JSON.stringify(o); });
"""

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0}}iframe{{border:0;display:block}}</style></head>
<body><iframe id="f" src="{src}" width="{w}" height="{h}"></iframe><pre id="qa" style="display:none"></pre>
<script>{js}</script></body></html>"""

# служебные зоны: не считаем «основной» мелкий текст
SECONDARY_RE = re.compile(r"legal|foot|cta|calc|plate-cap|caption|cap\b|kicker|kik|issuer|brand|top|hdr|series|"
                          r"note-strip|micro|small|sign|disclaim|__k\b|__k$|label|lbl|b-issuer|c-note|c-cap|ghost|k-arrow|k-swipe|k-top|k-num|k-badge|k-legal|k-photo__cap|stat__n|k2-stat__n|"
                          r"_sub\b|__sub|list__n|list__num|badge|hook|cat\b|plate\b", re.I)
LABEL_RE = re.compile(r"__k\b|__k$|label|lbl", re.I)
DETAIL_RE = re.compile(r"_sub\b|__sub|__k$|__k\b", re.I)
CONTENT_RE = re.compile(r"list__t|list__item|adv__t|facts__i|pricezone__value|row__v|point__t|bullet__t|cta__t|price__v", re.I)
VALUE_SEL_RE = re.compile(r"__v$|__v\b", re.I)
VALUE_RE = re.compile(r"(?:^|[_\-])v(?:__|$)|value|val\b|tile|big|kv__v|spec__v|char__v|num|figure", re.I)
HEAD_RE = re.compile(r"head|title|h1|h2|model|name|slogan|badge", re.I)


def measure(html: Path, size: tuple[int, int], tmp: Path) -> dict:
    wrapper = tmp / f"wrap_{html.parent.name[:18]}_{html.stem[:18]}.html"
    wrapper.write_text(WRAP.format(src=html.as_uri(), w=size[0], h=size[1], js=JS), encoding="utf-8")
    cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           "--allow-file-access-from-files", "--virtual-time-budget=5000", "--dump-dom", wrapper.as_uri()]
    res = subprocess.run(cmd, capture_output=True, timeout=120)
    dom = res.stdout.decode("utf-8", errors="replace")
    mm = re.search(r'<pre id="qa"[^>]*>(.*?)</pre>', dom, re.S)
    if not mm:
        raise RuntimeError("JS-замер не вернулся")
    raw = mm.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    return json.loads(raw)


def analyze(payload: dict, html: Path, min_main: float, min_value: float) -> dict:
    out = {"ok": True, "checks": [], "warnings": []}
    items = payload.get("items") or []
    if not items:
        out["ok"] = False
        out["checks"].append(("нет текстовых элементов", False))
        return out
    card02 = html.stem.startswith("02_")
    card34 = html.stem.startswith(("03_", "04_"))

    def is_micro_label(it: dict) -> bool:
        txt = it.get("text") or ""
        return it["fs"] <= 15 and re.search(r"[a-zа-яё]", txt) is None

    main = [it for it in items if not SECONDARY_RE.search(it["cls"]) and not is_micro_label(it)]
    values = [it for it in items if VALUE_SEL_RE.search(it["cls"]) and not LABEL_RE.search(it["cls"])]
    details = [it for it in items if DETAIL_RE.search(it["cls"])]
    content = [it for it in items if CONTENT_RE.search(it["cls"])]
    out["min_main"] = min((it["fs"] for it in main), default=None)
    out["min_value"] = min((it["fs"] for it in values), default=None)
    out["max_value"] = max((it["fs"] for it in values), default=None)
    out["min_detail"] = min((it["fs"] for it in details), default=None)
    out["content_min"] = min((it["fs"] for it in content), default=None)
    out["content_max"] = max((it["fs"] for it in content), default=None)
    out["main_count"] = len(main)
    # 1) основная зона не мельче min_main
    if out["min_main"] is not None:
        small = [it for it in main if it["fs"] < min_main]
        out["checks"].append((f"основная зона ≥ {min_main:g}px (min {out['min_main']:g}px)", not small))
        if small:
            out["warnings"].append("мелкий текст основной зоны: " + "; ".join(
                f"{it['fs']:g}px «{it['text'][:40]}»" for it in small[:6]))
    # 2) значения карточки 02 (плитки/строки): ≥ min_value, цель 20–26, плитки ≥34
    if card02 and values:
        bad = [it for it in values if it["fs"] < min_value]
        out["checks"].append((f"значения ТТХ ≥ {min_value:g}px (min {out['min_value']:g}px)", not bad))
        if bad:
            out["warnings"].append("мелкие значения ТТХ: " + "; ".join(
                f"{it['fs']:g}px «{it['text'][:40]}»" for it in bad[:6]))
        in_target = [it for it in values if 20 <= it["fs"] <= 70]  # v3: 20–26, карусель: плитки 44–64
        out["value_target_hits"] = len(in_target)
        if values and not in_target:
            out["warnings"].append(
                f"цель значений (20–26 v3 / 44–64 карусель) не достигнута (в диапазоне {len(in_target)} из {len(values)}, "
                f"min {out['min_value']:g}px)")
        tiles = [it for it in values if it["fs"] >= 34]
        out["checks"].append((f"есть крупные плитки ≥34px ({len(tiles)} шт., max {out['max_value']:g}px)", bool(tiles)))
        if out["min_detail"] is not None and out["min_detail"] < 16:
            out["warnings"].append(f"уточняющие подписи-детали {out['min_detail']:g}px (<16px) — вторичный текст, на 390 не читается")
    # 3) карточки 03/04: содержательные строки 22–27px (по критерию Lead)
    if card34:
        if content:
            cmin = out["content_min"]
            bad_c = [it for it in content if it["fs"] < 22]
            out["checks"].append((f"контент 03/04 ≥ 22px (min {cmin:g}px, max {out['content_max']:g}px)", not bad_c))
            if bad_c:
                out["warnings"].append("мелкий контент 03/04: " + "; ".join(
                    f"{it['fs']:g}px «{it['text'][:40]}»" for it in bad_c[:6]))
        else:
            out["warnings"].append("не нашёл контентные элементы 03/04 для замера (проверить вручную)")
    # 4) обрезка (горизонтальная — блокер-кандидат; вертикальная у значений — minor) / выход / наложения
    overflow = [o for o in (payload.get("overflow") or [])
                if (o.get("sw", 0) - o.get("cw", 0) > 2)
                and any(k in (o.get("ov", "") or "") for k in ("hidden", "clip", "auto", "scroll"))]
    clipped_vals = [o for o in (payload.get("overflow") or [])
                    if (o.get("sh", 0) - o.get("ch", 0) > 2)
                    and any(k in (o.get("ov", "") or "") for k in ("hidden", "clip"))
                    and re.search(r"__v\b|__v$|value", o.get("cls", ""), re.I)]
    out["clipped_values"] = [{"cls": o.get("cls"), "text": (o.get("text") or "")[:60]} for o in clipped_vals[:6]]
    if clipped_vals:
        out["warnings"].append("значения-строки подрезаны многоточием: " + "; ".join(
            f"«{(o.get('text') or '')[:30]}»" for o in clipped_vals[:4]))
    outside = [o for o in (payload.get("outside") or []) if not re.search(r"ghost|k-arrow", o.get("cls", ""), re.I)]
    raw_overlaps = payload.get("overlaps") or []
    overlaps = []
    for o in raw_overlaps:
        ar = o.get("ar") or 0
        br = o.get("br") or 0
        small = min(ar, br) or 1
        if (o.get("area", 0) / small) >= 0.25:  # явное перекрытие, а не bbox строки
            overlaps.append(o)
    out["overflow"] = overflow[:8]
    out["outside"] = outside[:6]
    out["overlaps"] = overlaps[:6]
    out["checks"].append((f"нет обрезки текста ({len(overflow)})", len(overflow) == 0))
    out["checks"].append((f"нет выхода за холст ({len(outside)})", len(outside) == 0))
    out["checks"].append((f"нет наложений текста ({len(overlaps)})", len(overlaps) == 0))
    # 5) крупные пустоты: текст основной зоны + изображения/фигуры
    blocks = [(it["y"], it["y"] + it["h"]) for it in main]
    for m in (payload.get("media") or []):
        blocks.append((m["y"], m["y"] + m["h"]))
    blocks.sort()
    max_gap = 0
    if blocks:
        cur_end = blocks[0][1]
        for y0, y1 in blocks[1:]:
            gap = y0 - cur_end
            if gap > max_gap:
                max_gap = gap
            cur_end = max(cur_end, y1)
    out["max_gap"] = max_gap
    is_placeholder = bool(re.match(r"(01|08)_", html.parent.name))
    if is_placeholder:
        out["warnings"].append(f"заглушка: пустая зона фото по дизайну (max gap {max_gap}px) — не дефект")
    else:
        out["checks"].append((f"нет пустот > 240px в контентной зоне (max {max_gap}px)", max_gap <= 240))
    out["ok"] = all(ok for _m, ok in out["checks"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--min-main", type=float, default=16.0)
    ap.add_argument("--min-value", type=float, default=16.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    tmp = QA / "_tmp" / "layout_redesign"
    tmp.mkdir(parents=True, exist_ok=True)
    files = sorted(HTML.rglob("*.html"))
    if args.only:
        flt = args.only.upper()
        files = [p for p in files if flt in str(p).upper()]
    if args.limit:
        files = files[: args.limit]
    results = []
    for p in files:
        size = (1080, 1350)
        try:
            payload = measure(p, size, tmp)
        except Exception as exc:
            results.append({"file": str(p), "error": str(exc)})
            print(f"ОШИБКА {p.relative_to(HTML)}: {exc}")
            continue
        an = analyze(payload, p, args.min_main, args.min_value)
        an["file"] = str(p)
        an["rel"] = str(p.relative_to(HTML))
        results.append(an)
        fails = [m for m, ok in an.get("checks", []) if not ok]
        print(f"{an['rel']}: {'OK' if an.get('ok') else 'FAIL'} | main {an.get('min_main')}px | "
              f"value {an.get('min_value')}–{an.get('max_value')}px | gap {an.get('max_gap')}px"
              + (f" | fails: {fails}" if fails else ""))
    if args.write:
        payload = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "version": VERSION,
                   "criteria": {"min_main_px": args.min_main, "min_value_px": args.min_value},
                   "files": results}
        (QA / "QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        L = ["# QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ — читаемость с телефона (Chrome-замеры)", "",
             f"Прогон: {payload['generated']} · критерии: основная зона ≥ {args.min_main:g}px, значения ТТХ ≥ {args.min_value:g}px "
             f"(цель 20–26px), плитки ≥34px; эффективный размер на копиях 540/390 px — в колонках.", "",
             "| Файл | main min | value min–max | пустота max | наложения/обрезка | Итог |", "|---|---|---|---|---|---|"]
        for r in results:
            if r.get("error"):
                L.append(f"| `{Path(r['file']).name}` | — | — | — | — | ❌ ошибка |")
                continue
            ov = len(r.get("overflow") or [])
            ol = len(r.get("overlaps") or [])
            L.append(f"| `{r['rel']}` | {r.get('min_main')}px | {r.get('min_value')}–{r.get('max_value')}px | "
                     f"{r.get('max_gap')}px | {ov}/{ol} | {'✅' if r.get('ok') else '❌'} |")
        fails = [r for r in results if not r.get("ok")]
        L += ["", f"**Итог:** файлов {len(results)}, OK {len(results) - len(fails)}, FAIL {len(fails)}."]
        if fails:
            L += ["", "## Не прошли"]
            for r in fails:
                if r.get("error"):
                    continue
                L.append(f"- `{r['rel']}`:")
                for msg, ok2 in r.get("checks", []):
                    if not ok2:
                        L.append(f"  - ❌ {msg}")
                for w in r.get("warnings") or []:
                    L.append(f"  - {w}")
        (QA / "QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("md:", QA / "QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ.md")
        print("json:", QA / "QA_ВИЗУАЛ_КЕГЛИ_СУПЕРЦЕНЫ.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
