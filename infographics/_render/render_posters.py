# -*- coding: utf-8 -*-
"""Рендер постеров «Два горизонта» в PNG.

Основной движок — Chrome DevTools Protocol (CDP): точный размер кадра,
deviceScaleFactor 1/2, ожидание загрузки шрифтов/картинок, диагностика
переполнений и битых фото. Резервный движок — CLI `chrome --screenshot`
(поддерживает --force-device-scale-factor).

Использование (из любого каталога, Python с Pillow):
  python _render\\render_posters.py --all
  python _render\\render_posters.py P01 P05
  python _render\\render_posters.py --kind wide --all
  python _render\\render_posters.py "D:\\...\\_design\\template.html" --out _render\\_qa --scale 1
  python _render\\render_posters.py --all --scale 1,2 --only-new

Коды выхода: 0 — всё OK; 1 — есть FAIL; 2 — авария (Chrome/файлы).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import posterlib as L

CHROME = L.CHROME


# ---------------------------------------------------------------------------
# Вспомогательное
# ---------------------------------------------------------------------------
def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def file_uri(path: Path) -> str:
    return Path(path).resolve().as_uri()


class CDPError(RuntimeError):
    pass


class CDP:
    """Минимальный клиент Chrome DevTools Protocol (без внешних зависимостей,
    кроме websocket-client, который уже стоит в runtime)."""

    def __init__(self, port: int, timeout: float = 40.0):
        try:
            import websocket  # websocket-client
        except Exception as e:  # pragma: no cover
            raise CDPError(f"нет websocket-client: {e}")
        self._wsmod = websocket
        tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
        pages = [t for t in tabs if t.get("type") == "page"]
        if not pages:
            raise CDPError("нет вкладки page в CDP")
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                              timeout=timeout, max_size=256 * 1024 * 1024)
        self.i = 0

    def cmd(self, method: str, params: dict | None = None) -> dict:
        self.i += 1
        msg_id = self.i
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            raw = self.ws.recv()
            if not raw:
                raise CDPError(f"{method}: соединение закрыто")
            msg = json.loads(raw)
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise CDPError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expr: str):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if r.get("exceptionDetails"):
            raise CDPError(f"JS: {r['exceptionDetails'].get('text')}")
        return r.get("result", {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def launch_chrome(profile: Path) -> tuple[subprocess.Popen, int]:
    port = free_port()
    args = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--force-color-profile=srgb",
        "--allow-file-access-from-files",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            return proc, port
        except Exception:
            if proc.poll() is not None:
                raise CDPError("Chrome завершился при запуске")
            time.sleep(0.25)
    raise CDPError("CDP не поднялся за 30 с")


def kill_chrome(proc: subprocess.Popen, profile: Path) -> None:
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    time.sleep(0.2)
    shutil.rmtree(profile, ignore_errors=True)


# ---------------------------------------------------------------------------
# Диагностика страницы
# ---------------------------------------------------------------------------
DIAG_JS = r"""
(() => {
  const de = document.documentElement, b = document.body;
  const vw = window.innerWidth, vh = window.innerHeight;
  const sw = Math.max(de ? de.scrollWidth : 0, b ? b.scrollWidth : 0);
  const sh = Math.max(de ? de.scrollHeight : 0, b ? b.scrollHeight : 0);
  const imgs = Array.from(document.images).map(im => ({
    src: (im.currentSrc || im.src || '').split('/').slice(-2).join('/'),
    nw: im.naturalWidth, nh: im.naturalHeight,
    w: Math.round(im.getBoundingClientRect().width),
    h: Math.round(im.getBoundingClientRect().height)
  }));
  const broken = imgs.filter(i => i.nw === 0 || i.nh === 0);
  const outR = (r) => r.right > vw + 1 || r.bottom > vh + 1 || r.left < -1 || r.top < -1;
  const textOut = [], clipped = [], texts = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const hasText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (hasText && outR(r)) {
      textOut.push({tag: el.tagName, cls: String(el.className || '').slice(0, 70),
                    t: el.textContent.trim().slice(0, 70),
                    r: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]});
    }
    if (hasText && r.width > 2 && r.height > 2) {
      texts.push({el, r, t: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60)});
    }
    if ((cs.overflow === 'hidden' || cs.overflowY === 'hidden' || cs.overflowX === 'hidden') &&
        (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)) {
      clipped.push({tag: el.tagName, cls: String(el.className || '').slice(0, 70),
                    sh: el.scrollHeight, ch: el.clientHeight, sw: el.scrollWidth, cw: el.clientWidth});
    }
  }
  // пересечения текстовых блоков (не вложенных) — обычно признак наложения
  const overlaps = [];
  for (let i = 0; i < texts.length; i++) {
    for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i], b = texts[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const ix = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const iy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (ix <= 0 || iy <= 0) continue;
      const minArea = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
      if (minArea < 4) continue;
      const frac = (ix * iy) / minArea;
      if (frac > 0.35) overlaps.push({a: a.t, b: b.t, frac: Math.round(frac * 100) / 100,
        ar: [Math.round(a.r.left), Math.round(a.r.top), Math.round(a.r.right), Math.round(a.r.bottom)],
        br: [Math.round(b.r.left), Math.round(b.r.top), Math.round(b.r.right), Math.round(b.r.bottom)]});
    }
  }
  const fonts = Array.from(document.fonts || []);
  return {
    vw, vh, sw, sh, dpr: window.devicePixelRatio,
    fontsStatus: document.fonts ? document.fonts.status : 'n/a',
    fontsLoaded: [...new Set(fonts.filter(f => f.status === 'loaded' || f.status === 'loaded').map(f => f.family))],
    fontsError: fonts.filter(f => f.status === 'error').map(f => f.family),
    imgCount: imgs.length, broken: broken.slice(0, 10),
    textOut: textOut.slice(0, 10), textOutCount: textOut.length,
    clipped: clipped.slice(0, 10), clippedCount: clipped.length,
    overlaps: overlaps.slice(0, 10), overlapCount: overlaps.length,
    fontsUsed: (() => {
      const s = new Set(); const els = document.querySelectorAll('h1,h2,h3,p,li,td,th,span,b,strong,small,div');
      for (const el of els) { const ff = getComputedStyle(el).fontFamily; if (ff) s.add(ff.split(',')[0].trim()); }
      return [...s].slice(0, 12);
    })(),
  };
})()
"""

WAIT_JS = r"""
(() => {
  if (document.readyState !== 'complete') return false;
  if (document.fonts && document.fonts.status !== 'loaded') return false;
  return !Array.from(document.images).some(im => !im.complete);
})()
"""


def wait_ready(cdp: CDP, seconds: float = 15.0) -> bool:
    """Ждём complete + шрифты + все картинки. Возвращает True, если дождались."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if cdp.eval(WAIT_JS):
                time.sleep(0.35)  # финальный кадр/краска
                return True
        except CDPError:
            pass
        time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Постобработка PNG
# ---------------------------------------------------------------------------
def normalize_png(path: Path) -> tuple[bool, str]:
    """PNG без прозрачности (бриф §5: sRGB, без alpha). Возвращает (ok, note)."""
    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        return False, f"нет Pillow: {e}"
    try:
        with Image.open(path) as im:
            im.load()
            mode = im.mode
            if mode == "RGBA":
                alpha = im.getchannel("A")
                lo, hi = alpha.getextrema()
                if lo == 255:
                    im = im.convert("RGB")
                    im.save(path, "PNG")
                    return True, "RGBA→RGB (alpha=255)"
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=alpha)
                bg.save(path, "PNG")
                return True, f"RGBA→RGB (снят alpha, min={lo})"
            if mode not in ("RGB", "L"):
                im = im.convert("RGB")
                im.save(path, "PNG")
                return True, f"{mode}→RGB"
            return True, ""
    except Exception as e:
        return False, f"битый PNG: {e}"


def verify_png(path: Path, exp_w: int, exp_h: int, fail: list[str], warn: list[str],
               notes: list[str]) -> tuple[int, int] | None:
    if not path.is_file():
        fail.append("файл не создан")
        return None
    size = path.stat().st_size
    ok, note = normalize_png(path)
    if not ok:
        fail.append(note)
        return None
    if note:
        notes.append(note)
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            mode = im.mode
            im.verify()
    except Exception as e:
        fail.append(f"PNG невалиден: {e}")
        return None
    if (w, h) != (exp_w, exp_h):
        fail.append(f"размер {w}×{h}, ожидался {exp_w}×{exp_h}")
    if mode != "RGB":
        warn.append(f"mode={mode} (ожидался RGB)")
    if size < L.MIN_PNG_BYTES:
        fail.append(f"вес {L.human_size(size)} < 50 КБ (пустой/битый?)")
    return size, (w, h)


# ---------------------------------------------------------------------------
# Рендер одного файла
# ---------------------------------------------------------------------------
def render_cdp(cdp: CDP, src: Path, out: Path, w: int, h: int, scale: int) -> dict:
    cdp.cmd("Emulation.setDeviceMetricsOverride",
            {"width": w, "height": h, "deviceScaleFactor": scale, "mobile": False})
    cdp.cmd("Page.navigate", {"url": file_uri(src)})
    ready = wait_ready(cdp)
    diag = cdp.eval(DIAG_JS)
    data = cdp.cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})["data"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(data))
    return {
        "ready": ready,
        "diag": diag,
    }


def render_cli(src: Path, out: Path, w: int, h: int, scale: int) -> dict:
    profile = Path(tempfile.mkdtemp(prefix="dsh-shot-"))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--disable-background-networking", "--force-color-profile=srgb",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=12000",
        "--force-device-scale-factor=%d" % scale,
        "--window-size=%d,%d" % (w, h),
        "--default-background-color=ffffffff",
        "--user-data-dir=%s" % profile,
        "--screenshot=%s" % out,
        file_uri(src),
    ]
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return {"ready": True, "diag": None}


# ---------------------------------------------------------------------------
# Сбор целей
# ---------------------------------------------------------------------------
def discover(kinds: list[str], only: set[str] | None) -> list[dict]:
    targets: list[dict] = []
    if "main" in kinds:
        if L.POSTERS_DIR.is_dir():
            for p in sorted(L.POSTERS_DIR.glob("*.html")):
                if p.name.startswith(("_", ".")) or p.name.lower() == "index.html":
                    continue
                targets.append({"src": p, "base": p.stem, "kind": "main"})
    if "wide" in kinds:
        d = L.POSTERS_DIR / "wide"
        if d.is_dir():
            for p in sorted(d.glob("*.html")):
                if p.name.startswith(("_", ".")):
                    continue
                targets.append({"src": p, "base": L.canon_stem(p.stem), "kind": "wide"})
    if "story" in kinds:
        d = L.POSTERS_DIR / "story"
        if d.is_dir():
            for p in sorted(d.glob("*.html")):
                if p.name.startswith(("_", ".")):
                    continue
                targets.append({"src": p, "base": L.canon_stem(p.stem), "kind": "story"})
    if only:
        targets = [t for t in targets if (L.poster_id(t["base"]) in only)]
    return targets


def explicit_targets(files: list[str]) -> list[dict]:
    targets = []
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            cand = L.POSTERS_DIR / f
            p = cand if cand.exists() else (Path.cwd() / f)
        kind = "main"
        parent = p.parent.name.lower()
        if parent == "wide":
            kind = "wide"
        elif parent == "story":
            kind = "story"
        targets.append({"src": p, "base": p.stem, "kind": kind})
    return targets


def scales_for(kind: str, scales: list[int]) -> list[int]:
    if kind == "main":
        return scales
    return [s for s in scales if s == 1] or [1]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Рендер постеров «Два горизонта» в PNG")
    ap.add_argument("files", nargs="*", help="конкретные HTML (иначе — по --kind/--all)")
    ap.add_argument("--all", action="store_true", help="все постеры (эквивалент --kind all)")
    ap.add_argument("--kind", default="", choices=["", "main", "wide", "story", "all"],
                    help="какие серии рендерить (по умолчанию main)")
    ap.add_argument("--only", default="", help="ID через запятую: P01,P05")
    ap.add_argument("--scale", default="", help="масштабы: 1, 1,2 (по умолчанию main: 1,2)")
    ap.add_argument("--out", default="", help="каталог вывода (по умолчанию 05_ГОТОВОЕ/png)")
    ap.add_argument("--engine", default="cdp", choices=["cdp", "cli"], help="движок рендера")
    ap.add_argument("--only-new", action="store_true", help="пропускать, если PNG новее HTML")
    ap.add_argument("--allow-missing", action="store_true", help="не падать, если HTML нет")
    ap.add_argument("--json", default="", help="куда писать JSON-отчёт (по умолчанию _render/_qa/render_report.json)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not Path(CHROME).is_file():
        print(f"FAIL: Chrome не найден: {CHROME}", file=sys.stderr)
        return 2

    # цели
    if args.files:
        targets = explicit_targets(args.files)
        if not targets:
            print("FAIL: не нашёл ни одного HTML", file=sys.stderr)
            return 2
    else:
        kinds = ["main", "wide", "story"] if (args.all or args.kind == "all") else [args.kind or "main"]
        targets = discover(kinds, set(x.strip().upper() for x in args.only.split(",") if x.strip()) or None)

    missing = [t["src"] for t in targets if not t["src"].is_file()]
    if missing:
        for m in missing:
            if args.allow_missing:
                print(f"SKIP: нет файла {m}")
            else:
                print(f"FAIL: нет файла {m}", file=sys.stderr)
        if not args.allow_missing:
            return 2
        targets = [t for t in targets if t["src"].is_file()]

    if not targets:
        print("Нет HTML для рендера (постеры ещё не опубликованы?)")
        return 0

    out_dir = Path(args.out) if args.out else L.PNG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    scales_req = [int(x) for x in args.scale.split(",") if x.strip()] or [1, 2]

    # план работ
    jobs = []
    for t in targets:
        for scale in scales_for(t["kind"], scales_req):
            w, h = L.KIND_SIZE[t["kind"]]
            out = out_dir / L.output_name(t["base"], t["kind"], scale)
            jobs.append({**t, "scale": scale, "w": w, "h": h, "out": out})
        if t["kind"] != "main" and 2 in scales_req:
            print(f"NOTE: {t['src'].name}: для серии {t['kind']} рендерится только 1×")

    if args.only_new:
        jobs = [j for j in jobs if not (j["out"].is_file() and j["out"].stat().st_mtime >= j["src"].stat().st_mtime)]
        if not jobs:
            print("Все PNG актуальны (--only-new): рендер не нужен")
            return 0

    profile = Path(tempfile.mkdtemp(prefix="dsh-render-"))
    proc = None
    cdp = None
    results = []
    started = time.time()
    try:
        if args.engine == "cdp":
            proc, port = launch_chrome(profile)
            cdp = CDP(port)
            cdp.cmd("Page.enable")
            cdp.cmd("Runtime.enable")
        for n, j in enumerate(jobs, 1):
            src = j["src"]
            info = {"src": str(src), "out": str(j["out"]), "kind": j["kind"], "scale": j["scale"],
                    "expected": [j["w"] * j["scale"], j["h"] * j["scale"]],
                    "status": "OK", "fail": [], "warn": [], "notes": [], "bytes": 0,
                    "actual": None, "diagnostics": None}
            t0 = time.time()
            try:
                if cdp is not None:
                    r = render_cdp(cdp, src, j["out"], j["w"], j["h"], j["scale"])
                    diag = r["diag"] or {}
                    info["diagnostics"] = diag
                    if not r["ready"]:
                        info["warn"].append("страница не догрузилась за 15 с")
                    if diag.get("broken"):
                        info["fail"].append(f"битых фото: {len(diag['broken'])}")
                    if diag.get("sw", 0) > j["w"] + 1 or diag.get("sh", 0) > j["h"] + 1:
                        info["fail"].append(
                            f"переполнение документа: {diag.get('sw')}×{diag.get('sh')} при кадре {j['w']}×{j['h']}")
                    if diag.get("textOutCount"):
                        info["fail"].append(f"текст за границей кадра: {diag['textOutCount']} эл.")
                    if diag.get("clippedCount"):
                        info["warn"].append(f"overflow:hidden с обрезанным содержимым: {diag['clippedCount']} эл.")
                    if diag.get("overlapCount"):
                        info["warn"].append(f"наложение текстовых блоков: {diag['overlapCount']} пар")
                    if diag.get("fontsStatus") not in ("loaded", "n/a"):
                        info["warn"].append(f"шрифты: {diag.get('fontsStatus')}")
                    if diag.get("fontsError"):
                        info["fail"].append(f"ошибки загрузки шрифтов: {diag['fontsError']}")
                else:
                    render_cli(src, j["out"], j["w"], j["h"], j["scale"])
                    info["warn"].append("CLI-движок: без диагностики переполнений")
            except Exception as e:
                info["fail"].append(f"ошибка рендера: {e}")
            # проверка результата
            exp_w, exp_h = info["expected"]
            if not info["fail"]:
                v = verify_png(j["out"], exp_w, exp_h, info["fail"], info["warn"], info["notes"])
                if v:
                    info["bytes"], info["actual"] = v
            elif j["out"].is_file():
                info["bytes"] = j["out"].stat().st_size
                info["actual"] = L.png_kind_dims(j["out"])
            info["ms"] = int((time.time() - t0) * 1000)
            if j["out"].is_file():
                info["rendered_at"] = time.strftime(
                    "%d.%m.%Y %H:%M:%S", time.localtime(j["out"].stat().st_mtime))
            if info["fail"]:
                info["status"] = "FAIL"
            elif info["warn"]:
                info["status"] = "WARN"
            results.append(info)
            if not args.quiet:
                mark = {"OK": "OK  ", "WARN": "WARN", "FAIL": "FAIL"}[info["status"]]
                name = j["out"].name
                size_txt = L.human_size(info["bytes"]) if info["bytes"] else "—"
                dims = f"{info['actual'][0]}×{info['actual'][1]}" if info["actual"] else "—"
                print(f"[{n:02d}/{len(jobs)}] {mark} {name:<42} {dims:<11} {size_txt:<8} {info['ms']} мс")
                for w in info["warn"]:
                    print(f"        WARN: {w}")
    finally:
        if cdp is not None:
            cdp.close()
        if proc is not None:
            kill_chrome(proc, profile)
        else:
            shutil.rmtree(profile, ignore_errors=True)

    # --- сводка ---------------------------------------------------------
    ok = sum(1 for r in results if r["status"] == "OK")
    warn = sum(1 for r in results if r["status"] == "WARN")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    total_bytes = sum(r["bytes"] for r in results)
    elapsed = time.time() - started
    print("-" * 96)
    print(f"Итого: {len(results)} файл(ов) | OK: {ok} | WARN: {warn} | FAIL: {fail} | "
          f"суммарно {L.human_size(total_bytes)} за {elapsed:.1f} с")

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "engine": args.engine,
        "out_dir": str(out_dir),
        "ok": ok, "warn": warn, "fail": fail,
        "total_bytes": total_bytes,
        "results": results,
    }
    json_path = Path(args.json) if args.json else (L.QA_DIR / "render_report.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчёт: {json_path}")

    if fail:
        print("\nПРОБЛЕМЫ:", file=sys.stderr)
        for r in results:
            if r["status"] != "OK":
                print(f"  {Path(r['out']).name}: {'; '.join(r['fail'] or r['warn'])}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
