#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_banners_layout.py — замеры вёрстки баннеров v3 (роль qa).

Проверяет по каждому HTML (36 баннеров + 6 сторис), в реальном Chrome:
  - НАЗВАНИЕ МОДЕЛИ остаётся самым крупным текстом (кегль headline/model ≥ любого другого);
  - техблок читается: найден блок «КОРОТКО/тех…», кегль его значений ≥ 10px и меньше кегля модели;
  - нет переполнений/обрезки (scroll > client у текстовых блоков) и выхода за холст;
  - безопасные поля по краям;
  - (инфо) наложения текстовых bbox разных блоков — для ручной проверки.
Результат: banners/03_QA/QA_ВИЗУАЛ_БАННЕРЫ.md + .json

Запуск: python check_banners_layout.py [--limit N] [--write]
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
BANNERS = QA.parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

# общий линтер (для norm/данных)
_spec = importlib.util.spec_from_file_location("cb_layout", QA / "check_banners.py")
if _spec is None or _spec.loader is None:
    raise SystemExit("не найден check_banners.py рядом")
cb = importlib.util.module_from_spec(_spec)
sys.modules["cb_layout"] = cb
_spec.loader.exec_module(cb)

SIZES = {
    "1080x1350": (1080, 1350),
    "1080x1080": (1080, 1080),
    "1080x1920": (1080, 1920),
}

JS = r"""
(function(){
  function px(v){ return parseFloat(v)||0; }
  return new Promise(function(resolve){
    var ifr=document.getElementById('f');
    function go(){
      try{
        var doc=ifr.contentDocument, win=ifr.contentWindow;
        var host=doc.querySelector('.banner')||doc.body;
        var hr=host.getBoundingClientRect();
        var out={w:Math.round(hr.width),h:Math.round(hr.height),items:[],overflow:[],outside:[],
                 safe:{l:999,t:999,r:999,b:999},techFound:false};
        var all=doc.querySelectorAll('body *');
        for(var i=0;i<all.length;i++){
          var el=all[i];
          if(el.tagName==='SCRIPT'||el.tagName==='STYLE') continue;
          var cs=win.getComputedStyle(el);
          var hasOwn=false;
          for(var j=0;j<el.childNodes.length;j++){
            var n=el.childNodes[j];
            if(n.nodeType===3 && n.textContent.trim().length>0){ hasOwn=true; break; }
          }
          var r=el.getBoundingClientRect();
          var cls=String(el.className||'');
          if(hasOwn && r.width>0 && r.height>0){
            var fs=px(cs.fontSize);
            out.items.push({tag:el.tagName,cls:cls.slice(0,70),fs:Math.round(fs*10)/10,
                            x:Math.round(r.left-hr.left),y:Math.round(r.top-hr.top),
                            w:Math.round(r.width),h:Math.round(r.height),
                            text:(el.innerText||'').replace(/\s+/g,' ').slice(0,80)});
            out.safe.l=Math.min(out.safe.l,Math.round(r.left-hr.left));
            out.safe.t=Math.min(out.safe.t,Math.round(r.top-hr.top));
            out.safe.r=Math.min(out.safe.r,Math.round(hr.right-r.right));
            out.safe.b=Math.min(out.safe.b,Math.round(hr.bottom-r.bottom));
          }
          if(cls.indexOf('tech')>=0 || cls.indexOf('spec')>=0 || cls.indexOf('brief')>=0 || cls.indexOf('task')>=0) out.techFound=true;
          if(/КОРОТКО|ТЕХНИЧЕСК|ПАРАМЕТР/i.test(el.innerText||'') && (el.children.length<=2)) out.techFound=true;
          if(hasOwn && (el.scrollWidth-el.clientWidth>2 || el.scrollHeight-el.clientHeight>2) &&
             el.clientWidth>0 && el.clientHeight>0){
            out.overflow.push({cls:cls.slice(0,60),sw:el.scrollWidth,cw:el.clientWidth,sh:el.scrollHeight,ch:el.clientHeight,
                               ov:(cs.overflow+'/'+cs.overflowX+'/'+cs.overflowY),
                               text:(el.innerText||'').replace(/\s+/g,' ').slice(0,60)});
          }
          if(r.width>0 && r.height>0 && (r.left<hr.left-1||r.right>hr.right+1||r.top<hr.top-1||r.bottom>hr.bottom+1) && cs.position!=='fixed' && hasOwn){
            out.outside.push({cls:cls.slice(0,60),x:Math.round(r.left-hr.left),y:Math.round(r.top-hr.top),
                              text:(el.innerText||'').replace(/\s+/g,' ').slice(0,50)});
          }
        }
        // наложения текстовых боксов (разные элементы, ни один не содержит другой)
        var texts=[];
        for(var t=0;t<all.length;t++){
          var e2=all[t];
          var hasT=false;
          for(var j3=0;j3<e2.childNodes.length;j3++){
            if(e2.childNodes[j3].nodeType===3 && e2.childNodes[j3].textContent.trim().length>0){ hasT=true; break; }
          }
          if(!hasT) continue;
          var r2=e2.getBoundingClientRect();
          if(r2.width<3||r2.height<3) continue;
          texts.push({el:e2,r:r2,cls:String(e2.className||'').slice(0,50),
                      text:(e2.innerText||'').replace(/\s+/g,' ').slice(0,50)});
        }
        out.overlaps=[];
        for(var a=0;a<texts.length && out.overlaps.length<12;a++){
          for(var b=a+1;b<texts.length;b++){
            var A=texts[a], B=texts[b];
            if(A.el.contains(B.el)||B.el.contains(A.el)) continue;
            var ix=Math.max(0,Math.min(A.r.right,B.r.right)-Math.max(A.r.left,B.r.left));
            var iy=Math.max(0,Math.min(A.r.bottom,B.r.bottom)-Math.max(A.r.top,B.r.top));
            if(ix*iy>12){
              out.overlaps.push({a:A.cls,b:B.cls,at:A.text,bt:B.text,area:Math.round(ix*iy)});
              if(out.overlaps.length>=12) break;
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


def measure(html: Path, size: tuple[int, int], tmp: Path) -> dict:
    wrapper = tmp / f"wrap_{html.stem}.html"
    wrapper.write_text(WRAP.format(src=html.as_uri(), w=size[0], h=size[1], js=JS), encoding="utf-8")
    cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           "--allow-file-access-from-files", "--virtual-time-budget=5000", "--dump-dom", wrapper.as_uri()]
    res = subprocess.run(cmd, capture_output=True, timeout=90)
    dom = res.stdout.decode("utf-8", errors="replace")
    mm = re.search(r'<pre id="qa"[^>]*>(.*?)</pre>', dom, re.S)
    if not mm:
        raise RuntimeError("JS-замер не вернулся")
    raw = mm.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    return json.loads(raw)


def norm_text(s: str) -> str:
    s = cb.shared.norm_match(s or "")
    return re.sub(r"[\s\-–—]+", "", s)


def analyze(payload: dict, data: dict | None, bid: str) -> dict:
    out = {"ok": True, "checks": [], "notes": []}
    items = payload.get("items") or []
    if not items:
        out["ok"] = False
        out["checks"].append(("нет текстовых элементов", False))
        return out
    max_item = max(items, key=lambda x: x["fs"])
    model_name = str((data or {}).get("model") or (data or {}).get("name_short") or "").strip()
    name_short = str((data or {}).get("name_short") or "").strip()
    # элемент «название модели»
    model_item = None
    for it in items:
        t = norm_text(it["text"])
        for cand in (name_short, model_name):
            nc = norm_text(cand)
            if nc and nc in t:
                model_item = it
                break
        if model_item:
            break
    if model_item is None:
        # fallback: headline/title класс
        for it in items:
            if re.search(r"headline|title|model", it["cls"], re.I):
                model_item = it
                break
    if model_item is None:
        out["ok"] = False
        out["checks"].append(("название модели не найдено в вёрстке", False))
        model_item = max_item
    else:
        out["checks"].append(("название модели найдено", True))
    model_fs = model_item["fs"]
    out["model"] = {"fs": model_fs, "text": model_item["text"], "cls": model_item["cls"]}
    out["max"] = {"fs": max_item["fs"], "text": max_item["text"], "cls": max_item["cls"]}
    out["checks"].append((f"название модели — самый крупный текст (model {model_fs}px, max {max_item['fs']}px)",
                          model_fs >= max_item["fs"] - 0.6))
    # техблок
    tech_items = [it for it in items if re.search(r"tech|spec|brief|param|short|task", it["cls"], re.I)]
    out["tech"] = {"found": bool(payload.get("techFound") or tech_items), "items": len(tech_items)}
    if tech_items:
        tfs = [it["fs"] for it in tech_items]
        tvals = [it["fs"] for it in tech_items if re.search(r"__v|value", it["cls"], re.I)]
        out["tech"]["min_fs"] = min(tfs)
        out["tech"]["max_fs"] = max(tfs)
        out["checks"].append((f"техблок найден ({len(tech_items)} элементов, labels {min(tfs)}px)", True))
        out["checks"].append((f"техблок читается: значения ≥ 12px (min {min(tvals) if tvals else '—'}px.",
                              "в quiet-квадратах 12px — minor, принято Lead)" if False else
                              ((min(tvals) >= 12) if tvals else True)))
        out["checks"].append((f"техблок не перебивает название ({max(tfs)}px < {model_fs}px)", max(tfs) < model_fs))
    # переполнения/выходы: только при реальном обрезании (overflow hidden/clip/auto/scroll)
    overflow_all = payload.get("overflow") or []
    overflow = [o for o in overflow_all
                if any(k in (o.get("ov", "") or "") for k in ("hidden", "clip", "auto", "scroll"))]
    outside = payload.get("outside") or []
    overlaps = payload.get("overlaps") or []
    out["overflow"] = overflow[:12]
    out["overflow_soft"] = [o for o in overflow_all if o not in overflow][:8]
    out["outside"] = outside[:8]
    out["overlaps"] = overlaps[:10]
    out["checks"].append((f"нет наложений текста ({len(overlaps)} пересечений)", len(overlaps) == 0))
    out["checks"].append((f"нет обрезки текста ({len(overflow)} переполнений)", len(overflow) == 0))
    out["checks"].append((f"нет выхода за холст ({len(outside)} элементов)", len(outside) == 0))
    safe = payload.get("safe") or {}
    if safe.get("l") is not None:
        out["checks"].append((f"безопасные поля ≥ 20px (L{safe['l']}/T{safe['t']}/R{safe['r']}/B{safe['b']}; 20px у декор-подписи — minor)",
                              min(safe["l"], safe["t"], safe["r"], safe["b"]) >= 20))
    out["safe"] = safe
    out["ok"] = all(ok for _n, ok in out["checks"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)
    tmp = QA / "_tmp" / "layout_v3"
    tmp.mkdir(parents=True, exist_ok=True)

    data_path = BANNERS / "00_КОПИРАЙТ" / "banners_data.json"
    data_by: dict[str, dict] = {}
    try:
        raw = json.loads(cb.shared.read_text(data_path))
        arr = raw if isinstance(raw, list) else (raw.get("banners") or raw.get("items") or [])
        data_by = {str(b.get("id", "")).upper(): b for b in arr if isinstance(b, dict)}
    except Exception:
        pass

    files: list[Path] = []
    for d in (BANNERS / "html", BANNERS / "story"):
        if d.is_dir():
            files.extend(sorted(d.rglob("*.html")))
    if args.only:
        flt = args.only.upper()
        files = [p for p in files if flt in p.name.upper()]
    if args.limit:
        files = files[: args.limit]

    results = []
    for p in files:
        mm = re.search(r"(1080x1350|1080x1080|1080x1920)", p.name)
        size = SIZES.get(mm.group(1)) if mm else (1080, 1350)
        bid = p.name[:3].upper() if re.match(r"^B\d\d", p.name, re.I) else "?"
        try:
            payload = measure(p, size, tmp)
        except Exception as exc:
            results.append({"file": str(p), "bid": bid, "error": str(exc)})
            print(f"{bid} {p.name}: ОШИБКА {exc}")
            continue
        an = analyze(payload, data_by.get(bid), bid)
        an.update({"file": str(p), "bid": bid, "size": [payload.get("w"), payload.get("h")]})
        results.append(an)
        fails = [msg for msg, ok in an.get("checks", []) if not ok]
        print(f"{bid} {p.name}: {'OK' if an.get('ok') else 'FAIL'} | model={an.get('model', {}).get('fs')}px "
              f"max={an.get('max', {}).get('fs')}px tech={an.get('tech', {}).get('min_fs', '—')}px "
              f"overflow={len(an.get('overflow', []))} outside={len(an.get('outside', []))}"
              + (f" | fails: {fails}" if fails else ""))

    if args.write:
        payload = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "version": VERSION, "files": results}
        (QA / "QA_ВИЗУАЛ_БАННЕРЫ.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        L = ["# QA_ВИЗУАЛ_БАННЕРЫ — замеры вёрстки v3", "",
             f"Прогон: {payload['generated']}, файлов: **{len(results)}** "
             f"(36 баннеров + 6 сторис), Chrome-замеры вёрстки.", "",
             "| Файл | Формат | Модель (кегль) | Max кегль | Техблок min кегль | Переполнения | Вне холста | Итог |",
             "|---|---|---|---|---|---|---|---|"]
        for r in results:
            if r.get("error"):
                L.append(f"| `{Path(r['file']).name}` | — | — | — | — | — | — | ❌ ошибка: {r['error']} |")
                continue
            m = r.get("model") or {}
            mx = r.get("max") or {}
            t = r.get("tech") or {}
            L.append(f"| `{Path(r['file']).name}` | {r.get('size')} | {m.get('fs')}px «{m.get('text', '')[:28]}» | "
                     f"{mx.get('fs')}px | {t.get('min_fs', '—')}px | {len(r.get('overflow', []))} | "
                     f"{len(r.get('outside', []))} | {'✅' if r.get('ok') else '❌'} |")
        fails = [r for r in results if not r.get("ok")]
        L += ["", f"**Итог:** файлов {len(results)}, без замечаний {len(results) - len(fails)}, с замечаниями {len(fails)}."]
        if fails:
            L += ["", "## Замечания"]
            for r in fails:
                L.append(f"- `{Path(r['file']).name}`:")
                for msg, ok in r.get("checks", []):
                    if not ok:
                        L.append(f"  - ❌ {msg}")
        (QA / "QA_ВИЗУАЛ_БАННЕРЫ.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("md:", QA / "QA_ВИЗУАЛ_БАННЕРЫ.md")
        print("json:", QA / "QA_ВИЗУАЛ_БАННЕРЫ.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
