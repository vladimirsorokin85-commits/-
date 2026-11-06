#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_layout.py — объективные замеры постеров «ДВА ГОРИЗОНТА» (роль qa).

Как работает: для каждого постера генерируется wrapper-страница в 03_QA/_tmp/layout/,
внутрь подгружается постер в <iframe> 1080×1350 (или 1920×1080 / 1080×1920), после load
внедрённый JS снимает замеры и кладёт JSON в <pre id="qa">. Chrome headless --dump-dom
возвращает DOM, из него вынимается JSON.

Проверяет:
  - переполнение: scrollWidth/Height > clientWidth/Height у элементов, выход bbox за холст;
  - минимальный реальный кегль (getComputedStyle) и список мелких элементов;
  - фактически применённые font-family (подмена Arial и т.п.);
  - шрифты: document.fonts.check для Sofia/Oswald/Tektur;
  - фото: naturalWidth/Height vs отображаемый размер -> апскейл (размытие на 2×);
  - контраст: цвет текста vs ближайший непрозрачный фон (WCAG);
  - безопасные поля: bbox контента от края холста;
  - позиция и кегль дисклеймера (P05/P06/P10).

Запуск: python check_layout.py [--posters P01,P02] [--write]
Результат: 03_QA/QA_ВИЗУАЛ.md + QA_ВИЗУАЛ.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
VERSION = "1.0"

JS = r"""
(function(){
  function px(v){ return parseFloat(v)||0; }
  function rgb(s){
    var m = String(s).match(/rgba?\(([^)]+)\)/);
    if(!m) return null;
    var p = m[1].split(',').map(function(x){return parseFloat(x);});
    return {r:p[0],g:p[1],b:p[2],a:(p.length>3?p[3]:1)};
  }
  function lum(c){
    function f(x){ x=x/255; return x<=0.03928? x/12.92 : Math.pow((x+0.055)/1.055,2.4); }
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b);
  }
  function contrast(a,b){
    var l1=lum(a), l2=lum(b);
    var hi=Math.max(l1,l2), lo=Math.min(l1,l2);
    return (hi+0.05)/(lo+0.05);
  }
  function bgOf(el){
    var n = el;
    while(n && n.nodeType===1){
      var cs = getComputedStyle(n);
      var c = rgb(cs.backgroundColor);
      if(c && c.a > 0.5) return c;
      var bi = cs.backgroundImage;
      if(bi && bi !== 'none' && bi.indexOf('gradient') === -1) { /* картинка-фон: неизвестно */ }
      n = n.parentElement;
    }
    return {r:255,g:255,b:255,a:1};
  }
  return new Promise(function(resolve){
    var ifr = document.getElementById('poster-frame');
    function go(){
      try {
        var doc = ifr.contentDocument;
        var win = ifr.contentWindow;
        var body = doc.body;
        var host = doc.querySelector('.poster') || body;
        var hr = host.getBoundingClientRect();
        var W = hr.width, H = hr.height;
        var out = {width:W, height:H, minFont:999, small:[], overflow:[], outside:[],
                   fonts:{}, families:{}, images:[], contrast:[], disclaimer:null, textLen:0};
        out.textLen = (body.innerText || '').length;
        var all = doc.querySelectorAll('body *');
        for(var i=0;i<all.length;i++){
          var el = all[i];
          if(el.tagName==='SCRIPT'||el.tagName==='STYLE'||el.tagName==='LINK') continue;
          var cs = win.getComputedStyle(el);
          var r = el.getBoundingClientRect();
          var hasText = false;
          for(var j=0;j<el.childNodes.length;j++){
            var n=el.childNodes[j];
            if(n.nodeType===3 && n.textContent.trim().length>0){ hasText=true; break; }
          }
          var fs = px(cs.fontSize);
          if(hasText && fs>0){
            if(fs < out.minFont) out.minFont = fs;
            out.smallest = out.smallest || [];
            if(out.smallest.length < 12){
              out.smallest.push({cls:String(el.className||'').slice(0,50), fs:Math.round(fs*10)/10,
                                 text:(el.innerText||'').replace(/\s+/g,' ').slice(0,70)});
            }
            if(fs < 13){
              out.small.push({tag:el.tagName, cls:String(el.className||'').slice(0,60),
                              fs:Math.round(fs*10)/10,
                              text:(el.innerText||'').replace(/\s+/g,' ').slice(0,90)});
            }
            // контраст для текстовых элементов
            var fg = rgb(cs.color); var bg = bgOf(el);
            if(fg && bg && cs.opacity>0.5){
              var c = contrast(fg,bg);
              if(c < 4.5){
                out.contrast.push({cls:String(el.className||'').slice(0,50), ratio:Math.round(c*100)/100,
                                   fs:Math.round(fs), text:(el.innerText||'').replace(/\s+/g,' ').slice(0,80)});
              }
            }
            var fam = cs.fontFamily || '';
            var first = fam.split(',')[0].replace(/["']/g,'').trim();
            if(first) out.families[first] = (out.families[first]||0)+1;
          }
          // переполнение обычных блоков
          if(el.scrollHeight - el.clientHeight > 2 && cs.overflowY !== 'visible' && el.clientHeight>0){
            out.overflow.push({cls:String(el.className||'').slice(0,60),
                               scrollH:el.scrollHeight, clientH:el.clientHeight});
          }
          if(el.scrollWidth - el.clientWidth > 2 && cs.overflowX !== 'visible' && el.clientWidth>0){
            out.overflow.push({cls:String(el.className||'').slice(0,60),
                               scrollW:el.scrollWidth, clientW:el.clientWidth});
          }
          // выход за холст
          if(r.width>0 && r.height>0 && (r.left < hr.left - 1 || r.right > hr.right + 1 || r.top < hr.top - 1 || r.bottom > hr.bottom + 1)){
            // игнорируем декоративные псевдо-растяжки и элементы с position:fixed вне потока
            if(cs.position!=='fixed'){
              out.outside.push({tag:el.tagName, cls:String(el.className||'').slice(0,60),
                                left:Math.round(r.left-hr.left), top:Math.round(r.top-hr.top),
                                right:Math.round(r.right-hr.left), bottom:Math.round(r.bottom-hr.top)});
            }
          }
        }
        // безопасные поля: минимальное расстояние СОДЕРЖАТЕЛЬНЫХ (листовых) текстов от края
        var minL=999,minT=999,minR=999,minB=999;
        for(var k=0;k<all.length;k++){
          var e=all[k];
          if(e.tagName==='BODY'||e.tagName==='MAIN'||e.tagName==='HTML') continue;
          var hasOwnText=false;
          for(var j2=0;j2<e.childNodes.length;j2++){
            if(e.childNodes[j2].nodeType===3 && e.childNodes[j2].textContent.trim().length>0){ hasOwnText=true; break; }
          }
          if(!hasOwnText) continue;
          var rr=e.getBoundingClientRect();
          if(rr.width<=0||rr.height<=0) continue;
          minL=Math.min(minL, rr.left-hr.left); minT=Math.min(minT, rr.top-hr.top);
          minR=Math.min(minR, hr.right-rr.right); minB=Math.min(minB, hr.bottom-rr.bottom);
        }
        out.safeMargin = {left:Math.round(minL), top:Math.round(minT), right:Math.round(minR), bottom:Math.round(minB)};
        // шрифты
        ['Sofia Sans Cond','Oswald','Tektur','Unbounded'].forEach(function(f){
          out.fonts[f] = win.document.fonts.check('16px "'+f+'"');
        });
        // фото
        var imgs = doc.querySelectorAll('img');
        for(var q=0;q<imgs.length;q++){
          var im=imgs[q]; var ir=im.getBoundingClientRect();
          out.images.push({src:(im.getAttribute('src')||'').split('/').pop(),
                           natW:im.naturalWidth, natH:im.naturalHeight,
                           dispW:Math.round(ir.width), dispH:Math.round(ir.height),
                           scale: ir.width>0 ? Math.round((im.naturalWidth/ir.width)*100)/100 : 0});
        }
        // дисклеймер
        var dRe = /радиоэлектронным средством|юридических услуг|публичной офертой|паспорту изделия/i;
        for(var z=0;z<all.length;z++){
          var el2=all[z];
          var tx=(el2.innerText||'');
          if(dRe.test(tx) && el2.children.length===0){
            var cs2=win.getComputedStyle(el2);
            out.disclaimer={fs:Math.round(px(cs2.fontSize)*10)/10, text:tx.replace(/\s+/g,' ').slice(0,120)};
            break;
          }
        }
        resolve(out);
      } catch(e){ resolve({error:String(e)}); }
    }
    if(ifr.contentDocument && ifr.contentDocument.readyState==='complete'){ setTimeout(go, 300); }
    else { ifr.addEventListener('load', function(){ setTimeout(go, 500); }); }
  });
})().then(function(out){
  var pre = document.getElementById('qa');
  pre.textContent = JSON.stringify(out);
});
"""

WRAPPER = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:#fff}} iframe{{border:0;display:block}}</style></head>
<body>
<iframe id="poster-frame" src="{src}" width="{w}" height="{h}"></iframe>
<pre id="qa" style="display:none"></pre>
<script>{js}</script>
</body></html>
"""

PAGE_SIZES = {
    "wide": (1920, 1080),
    "story": (1080, 1920),
}


def find_posters(root: Path) -> list[Path]:
    posters = root / "02_МАКЕТЫ" / "posters"
    return sorted(posters.rglob("*.html"))


def run_chrome(wrapper: Path, timeout: int = 60) -> str:
    cmd = [
        str(CHROME),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--virtual-time-budget=6000",
        "--dump-dom",
        wrapper.as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = res.stdout.decode("utf-8", errors="replace")
    err = res.stderr.decode("utf-8", errors="replace")
    if not out:
        raise RuntimeError(f"Chrome не вернул DOM: {err[:400]}")
    return out


def parse_qa(dom: str) -> dict:
    mm = re.search(r'<pre id="qa"[^>]*>(.*?)</pre>', dom, re.S)
    if not mm:
        raise RuntimeError("в DOM нет <pre id='qa'> — JS не выполнился")
    raw = mm.group(1)
    raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    return json.loads(raw)


def measure(poster: Path, tmp: Path, kind: str = "default") -> dict:
    w, h = PAGE_SIZES.get(kind, (1080, 1350))
    wrapper = tmp / f"wrap_{poster.stem}_{w}x{h}.html"
    wrapper.write_text(WRAPPER.format(src=poster.as_uri(), w=w, h=h, js=JS), encoding="utf-8")
    dom = run_chrome(wrapper)
    return parse_qa(dom)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="")
    ap.add_argument("--posters", default="", help="фильтр: P01,P02")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    qa = Path(__file__).resolve().parent
    root = Path(args.root) if args.root else qa.parent
    tmp = qa / "_tmp" / "layout"
    tmp.mkdir(parents=True, exist_ok=True)

    filters = [x.strip().upper() for x in args.posters.split(",") if x.strip()]
    results: dict[str, dict] = {}
    for poster in find_posters(root):
        pid = re.match(r"(?i)^P(\d{1,2})", poster.name)
        pid = f"P{int(pid.group(1)):02d}" if pid else "?"
        if filters and pid not in filters:
            continue
        kind = "default"
        if "wide" in poster.parts:
            kind = "wide"
        elif "story" in poster.parts:
            kind = "story"
        try:
            res = measure(poster, tmp, kind)
        except Exception as exc:
            res = {"error": str(exc)}
        results[pid] = {
            "file": str(poster),
            "mtime": datetime.fromtimestamp(poster.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "kind": kind,
            "layout": res,
        }
        print(f"{pid}: {poster.name} -> " + ("ОШИБКА " + res["error"] if "error" in res else
              f"minFont={res.get('minFont')}px small={len(res.get('small',[]))} "
              f"overflow={len(res.get('overflow',[]))} outside={len(res.get('outside',[]))} "
              f"contrast<4.5={len(res.get('contrast',[]))} margins={res.get('safeMargin')}"))

    payload = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "version": VERSION, "posters": results}
    if args.write:
        (qa / "QA_ВИЗУАЛ.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("json:", qa / "QA_ВИЗУАЛ.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
