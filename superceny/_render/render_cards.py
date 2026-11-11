# -*- coding: utf-8 -*-
"""Рендер карточек «СУПЕРЦЕНЫ»: superceny/03_HTML/**/*.html -> 05_ГОТОВОЕ/<folder>/*.png

Chrome DevTools Protocol: точный кадр 1080×1350, ожидание шрифтов/картинок,
диагностика битых фото, переполнений документа, текста за кадром и наложений
текстовых блоков. Большой прогон (173 карточки) идёт батчами — Chrome
перезапускается каждые N карточек, результаты пишутся в один JSON.

Использование:
  python _render\\render_cards.py --all
  python _render\\render_cards.py --all --batch-size 60
  python _render\\render_cards.py --folder 05_kw-05
  python _render\\render_cards.py --only 01,02 --only-new
  python _render\\render_cards.py "D:\\...\\03_HTML\\05_kw-05_...\\01_СУПЕРЦЕНА.html"
  python _render\\render_cards.py --all --2x        # опционально: 05_ГОТОВОЕ/<folder>/@2x/

Коды выхода: 0 — OK; 1 — есть FAIL; 2 — авария.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import superlib as L

CHROME = L.CHROME


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def file_uri(path: Path) -> str:
    return Path(path).resolve().as_uri()


class CDPError(RuntimeError):
    pass


class CDP:
    def __init__(self, port: int, timeout: float = 45.0):
        try:
            import websocket
        except Exception as e:  # pragma: no cover
            raise CDPError(f"нет websocket-client: {e}")
        tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
        pages = [t for t in tabs if t.get("type") == "page"]
        if not pages:
            raise CDPError("нет вкладки page в CDP")
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                              timeout=timeout, max_size=256 * 1024 * 1024)
        self.i = 0

    def cmd(self, method: str, params: dict | None = None) -> dict:
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            raw = self.ws.recv()
            if not raw:
                raise CDPError(f"{method}: соединение закрыто")
            msg = json.loads(raw)
            if msg.get("id") == mid:
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


def launch_chrome(profile: Path):
    port = free_port()
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--disable-background-networking", "--force-color-profile=srgb",
        "--allow-file-access-from-files",
        f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank",
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


def kill_chrome(proc, profile: Path) -> None:
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
  // декоративные элементы (ghost-цифры, орнамент, aria-hidden) могут намеренно
  // выходить за кадр — это не «текст за границей кадра»
  const isDecor = (el) => {
    const cls = String(el.className || '');
    if (/ghost|decor|ornament|bleed/i.test(cls)) return true;
    if (el.getAttribute && el.getAttribute('aria-hidden') === 'true') return true;
    return false;
  };
  const textOut = [], clipped = [], texts = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const hasText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (hasText && outR(r) && !isDecor(el)) {
      textOut.push({tag: el.tagName, cls: String(el.className || '').slice(0, 70),
                    t: el.textContent.trim().slice(0, 70),
                    r: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]});
    }
    if (hasText && r.width > 2 && r.height > 2 && !isDecor(el)) {
      texts.push({el, r, t: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60)});
    }
    if ((cs.overflow === 'hidden' || cs.overflowY === 'hidden' || cs.overflowX === 'hidden') &&
        (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)) {
      clipped.push({tag: el.tagName, cls: String(el.className || '').slice(0, 70),
                    t: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 48),
                    sh: el.scrollHeight, ch: el.clientHeight, sw: el.scrollWidth, cw: el.clientWidth});
    }
  }
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
    fontsError: fonts.filter(f => f.status === 'error').map(f => f.family),
    imgCount: imgs.length, broken: broken.slice(0, 10),
    textOut: textOut.slice(0, 10), textOutCount: textOut.length,
    clipped: clipped.slice(0, 10), clippedCount: clipped.length,
    overlaps: overlaps.slice(0, 10), overlapCount: overlaps.length,
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


def wait_ready(cdp: CDP, seconds: float = 20.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if cdp.eval(WAIT_JS):
                time.sleep(0.3)
                return True
        except CDPError:
            pass
        time.sleep(0.2)
    return False


def normalize_png(path: Path) -> tuple[bool, str]:
    try:
        from PIL import Image
    except Exception as e:
        return False, f"нет Pillow: {e}"
    try:
        with Image.open(path) as im:
            im.load()
            mode = im.mode
            if mode == "RGBA":
                alpha = im.getchannel("A")
                lo, _ = alpha.getextrema()
                im2 = im.convert("RGB") if lo == 255 else Image.new("RGB", im.size, (255, 255, 255))
                if lo != 255:
                    im2.paste(im, mask=alpha)
                im2.save(path, "PNG")
                return True, f"RGBA→RGB (alpha min={lo})"
            if mode not in ("RGB", "L"):
                im.convert("RGB").save(path, "PNG")
                return True, f"{mode}→RGB"
            return True, ""
    except Exception as e:
        return False, f"битый PNG: {e}"


def verify_png(path: Path, exp_w: int, exp_h: int, fail: list[str], warn: list[str]):
    if not path.is_file():
        fail.append("файл не создан")
        return None
    size = path.stat().st_size
    ok, note = normalize_png(path)
    if not ok:
        fail.append(note)
        return None
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
        warn.append(f"mode={mode}")
    if size < L.MIN_PNG_BYTES:
        fail.append(f"вес {L.human_size(size)} < 50 КБ")
    return size, (w, h)


def render_cdp(cdp: CDP, src: Path, out: Path, scale: int) -> dict:
    cdp.cmd("Emulation.setDeviceMetricsOverride",
            {"width": L.CARD_W, "height": L.CARD_H, "deviceScaleFactor": scale, "mobile": False})
    cdp.cmd("Page.navigate", {"url": file_uri(src)})
    ready = wait_ready(cdp)
    diag = cdp.eval(DIAG_JS)
    data = cdp.cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})["data"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(data))
    return {"ready": ready, "diag": diag}


def render_cli(src: Path, out: Path, scale: int) -> None:
    profile = Path(tempfile.mkdtemp(prefix="dsh-sup-"))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--force-color-profile=srgb", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=12000", "--force-device-scale-factor=%d" % scale,
        "--window-size=%d,%d" % (L.CARD_W, L.CARD_H), "--default-background-color=ffffffff",
        f"--user-data-dir={profile}", f"--screenshot={out}", file_uri(src),
    ]
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def resolve_path(f: str) -> Path:
    p = Path(f)
    if p.is_absolute():
        return p
    candidates = [Path.cwd() / p, L.HTML_DIR / p, L.ROOT / p]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def select_targets(args) -> list[dict]:
    if args.files:
        targets = []
        for f in args.files:
            p = resolve_path(f)
            c = L.card_of(p.stem)
            if not c:
                print(f"SKIP: не карточка: {p}", file=sys.stderr)
                continue
            targets.append({"src": p, "stem": p.stem, "card": c,
                            "folder": p.parent.name if p.parent != L.HTML_DIR else "",
                            "out_rel": L.output_rel(p), "out": L.OUT_DIR / L.output_rel(p)})
        return targets
    targets = L.scan_html()
    if args.folder:
        targets = [t for t in targets if args.folder in t["folder"]]
    if args.only:
        codes = {x.strip() for x in args.only.split(",") if x.strip()}
        targets = [t for t in targets if t["card"] in codes]
    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description="Рендер карточек «СУПЕРЦЕНЫ» в PNG")
    ap.add_argument("files", nargs="*", help="конкретные HTML")
    ap.add_argument("--all", action="store_true", help="все карточки (по умолчанию)")
    ap.add_argument("--folder", default="", help="фильтр по подстроке папки позиции")
    ap.add_argument("--only", default="", help="коды карточек: 01,02 (00 — hero)")
    ap.add_argument("--only-new", action="store_true", help="только HTML новее PNG")
    ap.add_argument("--2x", dest="two_x", action="store_true",
                    help="дополнительно 2× в <folder>/@2x/ (не входит в 81)")
    ap.add_argument("--batch-size", type=int, default=40, help="перезапуск Chrome каждые N карточек")
    ap.add_argument("--prune", action="store_true",
                    help="удалить из 05_ГОТОВОЕ PNG/папки, которых нет в текущем составе (старая версия)")
    ap.add_argument("--out", default="", help="каталог вывода (по умолчанию 05_ГОТОВОЕ)")
    ap.add_argument("--engine", default="cdp", choices=["cdp", "cli"])
    ap.add_argument("--json", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not Path(CHROME).is_file():
        print(f"FAIL: Chrome не найден: {CHROME}", file=sys.stderr)
        return 2

    targets = select_targets(args)
    if not targets:
        print("Нет HTML карточек (superceny/03_HTML пуст — ждём designer-a)")
        return 0
    if args.out:
        base = Path(args.out)
        for t in targets:
            t["out"] = base / t["out_rel"]

    jobs = []
    for t in targets:
        jobs.append({**t, "scale": 1, "out_scale": t["out"]})
        if args.two_x:
            two = t["out"].parent / "@2x" / t["out"].name
            jobs.append({**t, "scale": 2, "out_scale": two})

    if args.only_new:
        jobs = [j for j in jobs if not (j["out_scale"].is_file()
                                        and j["out_scale"].stat().st_mtime >= j["src"].stat().st_mtime)]
        if not jobs:
            print("Все PNG актуальны (--only-new)")
            return 0

    results = []
    started = time.time()
    batch_size = max(1, args.batch_size)
    total = len(jobs)
    print(f"Карточек: {len(targets)} | задач рендера: {total} | батч по {batch_size}"
          + (" (с @2x)" if args.two_x else ""))

    for bstart in range(0, total, batch_size):
        batch = jobs[bstart:bstart + batch_size]
        profile = Path(tempfile.mkdtemp(prefix="dsh-suprender-"))
        proc = cdp = None
        try:
            if args.engine == "cdp":
                proc, port = launch_chrome(profile)
                cdp = CDP(port)
                cdp.cmd("Page.enable")
                cdp.cmd("Runtime.enable")
            for j in batch:
                info = {"src": str(j["src"]), "out": str(j["out_scale"]), "card": j["card"],
                        "folder": j["folder"], "scale": j["scale"],
                        "expected": [L.CARD_W * j["scale"], L.CARD_H * j["scale"]],
                        "status": "OK", "fail": [], "warn": [], "bytes": 0,
                        "actual": None, "diagnostics": None}
                t0 = time.time()
                try:
                    if cdp is not None:
                        r = render_cdp(cdp, j["src"], j["out_scale"], j["scale"])
                        diag = r["diag"] or {}
                        info["diagnostics"] = diag
                        if not r["ready"]:
                            info["warn"].append("страница не догрузилась за 20 с")
                        if diag.get("broken"):
                            info["fail"].append(f"битых фото: {len(diag['broken'])}")
                        if diag.get("sw", 0) > L.CARD_W + 1 or diag.get("sh", 0) > L.CARD_H + 1:
                            info["fail"].append(
                                f"переполнение документа: {diag.get('sw')}×{diag.get('sh')} при кадре {L.CARD_W}×{L.CARD_H}")
                        if diag.get("textOutCount"):
                            info["fail"].append(f"текст за границей кадра: {diag['textOutCount']} эл.")
                        if diag.get("clippedCount"):
                            info["warn"].append(f"overflow:hidden с обрезанным содержимым: {diag['clippedCount']} эл.")
                        if diag.get("overlapCount"):
                            info["warn"].append(f"наложение текстовых блоков: {diag['overlapCount']} пар")
                        if diag.get("fontsStatus") not in ("loaded", "n/a"):
                            info["warn"].append(f"шрифты: {diag.get('fontsStatus')}")
                        if diag.get("fontsError"):
                            info["fail"].append(f"ошибки шрифтов: {diag['fontsError']}")
                    else:
                        render_cli(j["src"], j["out_scale"], j["scale"])
                        info["warn"].append("CLI-движок без диагностики")
                except Exception as e:
                    info["fail"].append(f"ошибка рендера: {e}")
                exp_w, exp_h = info["expected"]
                if not info["fail"]:
                    v = verify_png(j["out_scale"], exp_w, exp_h, info["fail"], info["warn"])
                    if v:
                        info["bytes"], info["actual"] = v
                elif j["out_scale"].is_file():
                    info["bytes"] = j["out_scale"].stat().st_size
                    info["actual"] = L.png_dims(j["out_scale"])
                info["ms"] = int((time.time() - t0) * 1000)
                if j["out_scale"].is_file():
                    info["rendered_at"] = time.strftime("%d.%m.%Y %H:%M:%S",
                                                        time.localtime(j["out_scale"].stat().st_mtime))
                info["status"] = "FAIL" if info["fail"] else ("WARN" if info["warn"] else "OK")
                results.append(info)
                n = len(results)
                if not args.quiet:
                    dims = f"{info['actual'][0]}×{info['actual'][1]}" if info["actual"] else "—"
                    rel = Path(info["out"]).relative_to(Path(args.out) if args.out else L.OUT_DIR)
                    print(f"[{n:03d}/{total}] {info['status']:<4} {str(rel):<62} {dims:<11} "
                          f"{L.human_size(info['bytes']) if info['bytes'] else '—':<8} {info['ms']} мс")
                    for w in info["warn"]:
                        print(f"        WARN: {w}")
        finally:
            if cdp is not None:
                cdp.close()
            if proc is not None:
                kill_chrome(proc, profile)
            else:
                shutil.rmtree(profile, ignore_errors=True)
        done = len(results)
        print(f"— батч {bstart + 1}..{bstart + len(batch)} готов, всего {done}/{total}, "
              f"{time.time() - started:.1f} с")

    ok = sum(1 for r in results if r["status"] == "OK")
    warn = sum(1 for r in results if r["status"] == "WARN")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    total_bytes = sum(r["bytes"] for r in results)
    ov = sum(int((r["diagnostics"] or {}).get("overlapCount") or 0) for r in results)
    to = sum(int((r["diagnostics"] or {}).get("textOutCount") or 0) for r in results)
    cl = sum(int((r["diagnostics"] or {}).get("clippedCount") or 0) for r in results)
    print("-" * 110)
    print(f"Итого: {len(results)} файл(ов) | OK: {ok} | WARN: {warn} | FAIL: {fail} | "
          f"{L.human_size(total_bytes)} за {time.time() - started:.1f} с")
    print(f"Детектор: наложений {ov}, текста за кадром {to}, overflow:hidden {cl}")

    pruned = []
    if args.prune and not args.out and (args.all or not args.files):
        expected = set()
        for t in targets:
            expected.add(t["out"].resolve())
            if args.two_x:
                expected.add((t["out"].parent / "@2x" / t["out"].name).resolve())
        for p in L.OUT_DIR.rglob("*.png"):
            if "gallery" in p.parts:
                continue
            if p.resolve() not in expected:
                pruned.append(p)
        for p in pruned:
            try:
                p.unlink()
            except OSError:
                pass
        # убрать опустевшие папки старых версий
        for d in sorted({p.parent for p in pruned}, key=lambda x: len(str(x)), reverse=True):
            try:
                if d != L.OUT_DIR and d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass
        if pruned:
            print(f"PRUNE: удалено устаревших PNG: {len(pruned)} "
                  f"({', '.join(p.name for p in pruned[:5])}{'…' if len(pruned) > 5 else ''})")
        else:
            print("PRUNE: устаревших PNG нет")

    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "engine": args.engine,
              "out_dir": str(L.OUT_DIR), "ok": ok, "warn": warn, "fail": fail,
              "total_bytes": total_bytes, "overlaps": ov, "text_out": to, "clipped": cl,
              "pruned": [str(p) for p in pruned], "results": results}
    json_path = Path(args.json) if args.json else (L.QA_DIR / "render_report.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчёт: {json_path}")
    if fail:
        print("\nПРОБЛЕМЫ:", file=sys.stderr)
        for r in results:
            if r["status"] == "FAIL":
                print(f"  {r['out']}: {'; '.join(r['fail'])}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
