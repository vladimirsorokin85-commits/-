#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""QA-стенд каталога «В ОКОПЕ» × НПО «Киловатт».

Проверяет локальные (file://) страницы каталога через Chrome DevTools Protocol:
  runtime   — JS-исключения и console.error;
  network   — упавшие загрузки локальных файлов, битые изображения;
  layout    — горизонтальный overflow на 1440/1024/820/390;
  links     — относительные ссылки/ассеты/якоря указывают на существующие файлы/элементы;
  features  — грид, категории, «вне сайта», поиск, сортировка, модалка, корзина,
              форма заявки, телефон/QR, оба PDF, переключатель вариантов;
  typo      — двойные пробелы и непарные «ёлочки» = FAIL, остальное WARN
              (« - » вместо тире, "...", приклеенные единицы, ISO-даты);
  a11y      — prefers-reduced-motion: контент виден, JS без ошибок;
  shots     — 1440x900, 390x844 и секция каталога.

Запуск:
  python qa_check.py --sweep --out <dir> [--repeat 2] [--baseline]
  python qa_check.py --page <file.html> --out <dir>
  python qa_check.py --sweep --repeat 2 --baseline        # базовый прогон

Результат: <out>/report.json, <out>/report.md (+ QA_BASE.md при --baseline),
скриншоты в <out>/shots. Код возврата: 0 — PASS (WARN допустимы), 1 — есть FAIL.

Требования: websocket-client, Chrome. Chrome всегда гасится, профили удаляются.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request
import datetime as dt
from pathlib import Path

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    print("FATAL: нужен пакет websocket-client (pip install websocket-client)", file=sys.stderr)
    raise

# UTF-8 в консоли (PowerShell 5.1 + запуск из другого чата)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Пути / константы
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent            # kilowatt/catalog/_tools/qa
CATALOG = HERE.parents[1]                         # kilowatt/catalog
KILOWATT = CATALOG.parent                         # kilowatt
REDESIGN = KILOWATT / "redesign"                  # kilowatt/redesign

DEFAULT_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_PAGES = [
    CATALOG / "variant-2.html",
    CATALOG / "index.html",
]
SWEEP_NAMES = ["variant-2.html", "index.html"]

VIEWPORTS = [(1440, 900), (1024, 900), (820, 900), (390, 844)]
SHOT_1440 = (1440, 900)
SHOT_390 = (390, 844)

PY = sys.executable
PY_VERSION = "%d.%d.%d" % sys.version_info[:3]

HARNESS_VERSION = "1.0"

# JS-хук ставится до загрузки страницы: собирает ошибки даже без CDP-событий.
HOOK_SOURCE = r"""
(function () {
  if (window.__qa) return;
  var q = { errors: [], consoleErrors: [], warnings: [], resourceErrors: [] };
  window.__qa = q;
  window.addEventListener("error", function (e) {
    try {
      if (e && e.target && e.target.tagName && e.target !== window) {
        var src = e.target.src || e.target.href || e.target.tagName;
        q.resourceErrors.push(String(src));
        return;
      }
      q.errors.push(String((e && e.message) || "error") +
        (e && e.filename ? " @ " + e.filename + ":" + (e.lineno || 0) : ""));
    } catch (err) {}
  }, true);
  window.addEventListener("unhandledrejection", function (e) {
    try {
      var r = e.reason;
      q.errors.push("unhandledrejection: " + String((r && (r.stack || r.message)) || r));
    } catch (err) {}
  });
  if (window.console && console.error) {
    var oe = console.error;
    console.error = function () {
      try {
        q.consoleErrors.push(Array.prototype.map.call(arguments, function (a) {
          return String((a && (a.stack || a.message)) || a);
        }).join(" "));
      } catch (err) {}
      return oe.apply(console, arguments);
    };
  }
  if (window.console && console.warn) {
    var ow = console.warn;
    console.warn = function () {
      try {
        q.warnings.push(Array.prototype.map.call(arguments, function (a) {
          return String(a);
        }).join(" "));
      } catch (err) {}
      return ow.apply(console, arguments);
    };
  }
})();
"""


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def trunc(s, n=280):
    s = "" if s is None else str(s)
    s = s.replace("\r", " ").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def file_uri(path):
    return Path(path).resolve().as_uri()


def uri_to_path(uri):
    try:
        u = urllib.parse.urlsplit(uri)
    except Exception:
        return None
    if u.scheme != "file":
        return None
    p = urllib.parse.unquote(u.path)
    if re.match(r"^/[A-Za-z]:", p):
        p = p[1:]
    return Path(p)


def parse_count(text):
    if not text:
        return None
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None


def find_free_port(start=9441, end=9490):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("нет свободного порта в диапазоне %d-%d" % (start, end))


# ---------------------------------------------------------------------------
# CDP
# ---------------------------------------------------------------------------
class CDPError(RuntimeError):
    pass


class ScriptError(RuntimeError):
    pass


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30, max_size=256 * 1024 * 1024)
        self.i = 0
        self.events = []

    # -- низкий уровень ---------------------------------------------------
    def _take(self, raw):
        try:
            msg = json.loads(raw)
        except Exception:
            return None
        if "id" in msg:
            return msg
        self.events.append(msg)
        return None

    def cmd(self, method, params=None, timeout=30):
        self.i += 1
        mid = self.i
        try:
            self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        except Exception as exc:
            raise CDPError("send %s: %s" % (method, exc))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.settimeout(max(0.05, min(1.0, deadline - time.time())))
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as exc:
                raise CDPError("recv %s: %s" % (method, exc))
            if not raw:
                continue
            msg = self._take(raw)
            if msg is None:
                continue
            if msg.get("id") == mid:
                if "error" in msg:
                    raise CDPError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
        raise CDPError("timeout %s" % method)

    def pump(self, seconds=0.3):
        """Собирает события, приходящие от Chrome, в течение указанного времени."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.ws.settimeout(0.12)
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                return
            if raw:
                self._take(raw)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Chrome
# ---------------------------------------------------------------------------
def _run_ps(command, timeout=25):
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception:
        return None


def kill_profile_processes(profile):
    """Гасит любые процессы, запущенные с данным user-data-dir."""
    if not profile:
        return
    p = str(profile).replace("'", "''")
    ps = (
        "$needle = '%s'; $self = $PID; "
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ProcessId -ne $self -and $_.CommandLine -and $_.CommandLine.Contains($needle) } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        % p
    )
    _run_ps(ps, timeout=25)


def profile_process_count(profile):
    if not profile:
        return 0
    p = str(profile).replace("'", "''")
    ps = (
        "$needle = '%s'; $self = $PID; @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ProcessId -ne $self -and $_.CommandLine -and $_.CommandLine.Contains($needle) }).Count"
        % p
    )
    r = _run_ps(ps, timeout=25)
    if not r or r.returncode != 0:
        return -1
    try:
        return int((r.stdout or "0").strip().splitlines()[-1])
    except Exception:
        return -1


def chrome_version(port):
    try:
        raw = urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2).read()
        return json.loads(raw).get("Browser", "?")
    except Exception:
        return "?"


def launch_chrome(chrome_path, forced_port=0):
    if not Path(chrome_path).exists():
        raise RuntimeError("Chrome не найден: %s" % chrome_path)
    profile = tempfile.mkdtemp(prefix="qa-cdp-")
    last_err = None
    for _ in range(3):
        port = forced_port or find_free_port()
        args = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--remote-debugging-port=%d" % port,
            "--user-data-dir=%s" % profile,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-pings",
            "--mute-audio",
            "about:blank",
        ]
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            last_err = exc
            continue
        deadline = time.time() + 20
        version = None
        while time.time() < deadline:
            try:
                raw = urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1.5).read()
                version = json.loads(raw)
                break
            except Exception:
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
        if version:
            tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=3).read())
            page = next((t for t in tabs if t.get("type") == "page"), None)
            if page and page.get("webSocketDebuggerUrl"):
                return {
                    "proc": proc,
                    "profile": profile,
                    "port": port,
                    "ws_url": page["webSocketDebuggerUrl"],
                    "version": version.get("Browser", "?"),
                }
        last_err = "CDP не поднялся (port %d)" % port
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    shutil.rmtree(profile, ignore_errors=True)
    raise RuntimeError("не удалось запустить Chrome: %s" % last_err)


def shutdown_chrome(info, cdp=None):
    if cdp:
        try:
            cdp.close()
        except Exception:
            pass
    proc = info.get("proc")
    if proc is not None:
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
        except Exception:
            pass
    profile = info.get("profile")
    if profile:
        kill_profile_processes(profile)
        time.sleep(0.15)
        for _ in range(5):
            try:
                shutil.rmtree(profile)
                break
            except Exception:
                time.sleep(0.2)
        # профиль мог остаться из-за блокировки — добиваем процессы ещё раз
        if Path(profile).exists():
            kill_profile_processes(profile)
            shutil.rmtree(profile, ignore_errors=True)


# ---------------------------------------------------------------------------
# JS-помощники
# ---------------------------------------------------------------------------
def js_raw(cdp, expression, await_promise=False, timeout=30):
    params = {"expression": expression, "returnByValue": True, "awaitPromise": bool(await_promise)}
    res = cdp.cmd("Runtime.evaluate", params, timeout=timeout)
    if "exceptionDetails" in res:
        det = res["exceptionDetails"]
        raise ScriptError(trunc((det.get("exception") or {}).get("description") or det.get("text") or "JS error"))
    return res.get("result", {}).get("value")


def js(cdp, expression, await_promise=False):
    return js_raw(cdp, expression, await_promise=await_promise)


def eval_json(cdp, expression):
    """Вычисляет выражение и возвращает JSON-объект, ловя JS-ошибки внутри."""
    wrapped = (
        "JSON.stringify((function(){try{return (%s);}catch(e){return {__error:String((e&&(e.stack||e.message))||e)};}})())"
        % expression
    )
    raw = js(cdp, wrapped)
    if raw is None:
        return None
    data = json.loads(raw)
    if isinstance(data, dict) and "__error" in data:
        raise ScriptError(trunc(data["__error"]))
    return data


def set_viewport(cdp, width, height):
    cdp.cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 600,
    })


def scroll_to_sel(cdp, selector, offset=72):
    expr = (
        "(function(){var h=document.documentElement;var p=h.style.scrollBehavior;"
        "h.style.scrollBehavior='auto';var el=document.querySelector(%s);if(!el){h.style.scrollBehavior=p;return -1;}"
        "var y=el.getBoundingClientRect().top+window.pageYOffset-%d;window.scrollTo(0,Math.max(0,y));"
        "h.style.scrollBehavior=p;return Math.round(window.pageYOffset);})()"
        % (json.dumps(selector), offset)
    )
    return js(cdp, expr)


def scroll_top(cdp):
    js(cdp, "(function(){var h=document.documentElement;var p=h.style.scrollBehavior;"
            "h.style.scrollBehavior='auto';window.scrollTo(0,0);h.style.scrollBehavior=p;return 0;})()")


def wait_ready(cdp, timeout=20):
    """Ждёт complete + отрисованный грид (app.js рендерит карточки)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        cdp.pump(0.15)
        try:
            if js(cdp, "document.readyState") == "complete":
                n = js(cdp, "document.querySelectorAll('[data-grid] .card').length")
                if n and int(n) > 0:
                    break
        except (CDPError, ScriptError):
            pass
    # шрифты + первая отрисовка
    try:
        js(cdp, "document.fonts && document.fonts.ready ? document.fonts.ready.then(function(){return 1;}) : 1",
           await_promise=True)
    except (CDPError, ScriptError):
        pass
    cdp.pump(0.7)


def navigate(cdp, url, width, height):
    set_viewport(cdp, width, height)
    cdp.cmd("Page.navigate", {"url": url})
    wait_ready(cdp)


def capture(cdp, path):
    data = cdp.cmd("Page.captureScreenshot", {"format": "png"})["data"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))


def press_escape(cdp):
    for t in ("keyDown", "keyUp"):
        try:
            cdp.cmd("Input.dispatchKeyEvent", {
                "type": t, "key": "Escape", "code": "Escape",
                "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27,
            })
        except CDPError:
            pass


# ---------------------------------------------------------------------------
# Модель проверок
# ---------------------------------------------------------------------------
def make_check(cid, name, status, details="", evidence=None):
    return {
        "id": cid,
        "name": name,
        "status": status,  # PASS | FAIL | WARN | SKIP
        "details": details,
        "evidence": list(evidence or []),
    }


def page_verdict(checks):
    return "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"


def summarize(checks):
    out = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    for c in checks:
        out[c["status"]] = out.get(c["status"], 0) + 1
    return out


# ---------------------------------------------------------------------------
# Анализ событий CDP
# ---------------------------------------------------------------------------
def analyze_events(events, start_index=0):
    js_errors, console_errors, console_warnings = [], [], []
    failed, req_urls = [], {}
    for ev in events[start_index:]:
        method = ev.get("method")
        params = ev.get("params") or {}
        if method == "Network.requestWillBeSent":
            req_urls[params.get("requestId")] = (params.get("request") or {}).get("url", "")
        elif method == "Network.loadingFailed":
            if params.get("canceled"):
                continue
            rid = params.get("requestId")
            url = req_urls.get(rid, "")
            err = params.get("errorText") or params.get("blockedReason") or "failed"
            failed.append({"url": url, "error": err, "type": params.get("type", "")})
        elif method == "Runtime.exceptionThrown":
            det = params.get("exceptionDetails") or {}
            desc = (det.get("exception") or {}).get("description") or det.get("text") or "exception"
            js_errors.append({
                "message": trunc(desc, 500),
                "url": det.get("url", ""),
                "line": det.get("lineNumber"),
            })
        elif method == "Runtime.consoleAPICalled":
            args = [a.get("value") if "value" in a else (a.get("description") or "") for a in params.get("args", [])]
            msg = trunc(" ".join(str(a) for a in args), 500)
            if params.get("type") == "error":
                console_errors.append({"message": msg})
            elif params.get("type") == "warning":
                console_warnings.append({"message": msg})
        elif method == "Log.entryAdded":
            entry = params.get("entry") or {}
            if entry.get("level") != "error":
                continue
            text = trunc(entry.get("text", ""), 500)
            src = entry.get("source", "")
            if src == "network" or "Failed to load resource" in text:
                failed.append({"url": entry.get("url", ""), "error": text, "type": "network(log)"})
            else:
                js_errors.append({"message": text, "url": entry.get("url", ""), "line": entry.get("lineNumber")})
    return {
        "js_errors": js_errors,
        "console_errors": console_errors,
        "console_warnings": console_warnings,
        "failed": failed,
    }


def dedupe(items, key_field="message"):
    seen = set()
    out = []
    for it in items:
        key = str(it.get(key_field, "")) + "|" + str(it.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def is_local_url(url):
    return bool(url) and url.startswith("file:")


# ---------------------------------------------------------------------------
# Проверки страницы
# ---------------------------------------------------------------------------
def check_runtime(cdp, events, start_index, injected):
    data = analyze_events(events, start_index)
    js_errors = dedupe(data["js_errors"])
    console_errors = [
        e for e in dedupe(data["console_errors"])
        if "Failed to load resource" not in e.get("message", "") and "net::ERR" not in e.get("message", "")
    ]
    warnings = dedupe(data["console_warnings"])
    qa = injected or {}
    for msg in qa.get("errors") or []:
        js_errors.append({"message": trunc(msg, 500), "source": "window.error"})
    for msg in qa.get("consoleErrors") or []:
        if "Failed to load resource" not in str(msg):
            console_errors.append({"message": trunc(msg, 500), "source": "console.error"})
    js_errors = dedupe(js_errors)

    checks = []
    checks.append(make_check(
        "runtime.js_errors", "JS-исключения", "FAIL" if js_errors else "PASS",
        "ошибок: %d" % len(js_errors) if js_errors else "JS-исключений нет",
        [trunc(json.dumps(e, ensure_ascii=False), 400) for e in js_errors[:10]],
    ))
    checks.append(make_check(
        "runtime.console_errors", "console.error", "FAIL" if console_errors else "PASS",
        "ошибок: %d" % len(console_errors) if console_errors else "console.error не вызывался",
        [trunc(e.get("message"), 400) for e in console_errors[:10]],
    ))
    checks.append(make_check(
        "runtime.console_warnings", "console.warn (инфо)", "PASS",
        "предупреждений: %d" % len(warnings),
        [trunc(e.get("message"), 300) for e in warnings[:5]],
    ))
    return checks, dedupe(data["failed"])


def check_network(failed, broken_images, pending_images):
    local = []
    external = []
    seen = set()
    for f in failed:
        url = f.get("url") or ""
        key = url + "|" + str(f.get("error"))
        if key in seen:
            continue
        seen.add(key)
        if not url:
            continue
        if is_local_url(url):
            local.append(f)
        elif url.startswith("http"):
            external.append(f)
    checks = []
    checks.append(make_check(
        "network.failed_local", "Загрузка локальных ресурсов",
        "FAIL" if local else "PASS",
        ("не загрузилось: %d" % len(local)) if local else "все локальные ресурсы загрузились",
        [trunc("%s — %s" % (f.get("url"), f.get("error")), 400) for f in local[:10]],
    ))
    checks.append(make_check(
        "network.failed_external", "Внешние запросы (инфо)",
        "WARN" if external else "PASS",
        "упало внешних: %d" % len(external) if external else "внешних падений нет",
        [trunc("%s — %s" % (f.get("url"), f.get("error")), 300) for f in external[:5]],
    ))
    checks.append(make_check(
        "network.images", "Битые изображения (naturalWidth)",
        "FAIL" if broken_images else ("WARN" if pending_images else "PASS"),
        ("битых: %d" % len(broken_images)) if broken_images else "все изображения загружены",
        [trunc(x, 300) for x in broken_images[:10]] +
        ([trunc("не догрузились (lazy): %d" % pending_images, 200)] if pending_images else []),
    ))
    return checks


def check_images(cdp):
    js(cdp, "(function(){var imgs=document.images;for(var i=0;i<imgs.length;i++){imgs[i].loading='eager';}return imgs.length;})()")
    pending = 0
    for _ in range(3):
        cdp.pump(0.8)
        state = eval_json(
            cdp,
            "(function(){var broken=[],pending=0;for(var i=0;i<document.images.length;i++){var im=document.images[i];"
            "if(!im.complete){pending++;continue;}if(im.naturalWidth===0){broken.push(im.currentSrc||im.src);}}"
            "return {total:document.images.length,broken:broken,pending:pending};})()",
        )
        pending = state.get("pending", 0)
        if pending == 0:
            break
    return state.get("broken", []), pending


def check_links(cdp):
    data = eval_json(cdp, r"""(function(){
      var out=[], seen={};
      function add(tag, attr, el){
        var raw = el.getAttribute(attr);
        if (!raw) return;
        var key = tag + '|' + raw;
        if (seen[key]) return;
        seen[key] = 1;
        var abs = raw;
        try { abs = new URL(raw, document.baseURI).href; } catch(e){}
        out.push({tag:tag, raw:raw, abs:abs, text:(el.textContent||'').trim().slice(0,60)});
      }
      var q = document.querySelectorAll('a[href]');
      for (var i=0;i<q.length;i++) add('a','href',q[i]);
      q = document.querySelectorAll('img[src]');
      for (var j=0;j<q.length;j++) add('img','src',q[j]);
      q = document.querySelectorAll('script[src]');
      for (var k=0;k<q.length;k++) add('script','src',q[k]);
      q = document.querySelectorAll('link[href]');
      for (var l=0;l<q.length;l++) add('link','href',q[l]);
      q = document.querySelectorAll('source[src]');
      for (var m=0;m<q.length;m++) add('source','src',q[m]);
      return out;
    })()""")
    missing_files, missing_anchors, external, anchors_ok, skip = [], [], [], 0, 0
    checked_files = set()
    for item in data:
        raw = item.get("raw", "")
        abs = item.get("abs", "")
        if raw.startswith("#"):
            anchor = raw[1:]
            if not anchor:
                missing_anchors.append({"raw": raw, "reason": "пустой якорь #"})
            else:
                ok = eval_json(cdp, "!!document.getElementById(%s)" % json.dumps(anchor))
                if ok:
                    anchors_ok += 1
                else:
                    missing_anchors.append({"raw": raw, "reason": "нет элемента id=%s" % anchor})
            continue
        scheme = urllib.parse.urlsplit(abs).scheme if abs else ""
        if scheme in ("http", "https"):
            external.append(raw)
            continue
        if scheme not in ("file", ""):
            skip += 1
            continue
        path = uri_to_path(abs) if abs else None
        if path is None:
            skip += 1
            continue
        key = str(path)
        if key in checked_files:
            continue
        checked_files.add(key)
        if not path.exists():
            missing_files.append({"raw": raw, "path": str(path)})
        elif path.is_dir():
            missing_files.append({"raw": raw, "path": str(path) + " (каталог)"})
    checks = []
    checks.append(make_check(
        "links.local_files", "Локальные ссылки и ассеты",
        "FAIL" if missing_files else "PASS",
        ("не найдено файлов: %d из %d" % (len(missing_files), len(checked_files)))
        if missing_files else "проверено файлов: %d — все существуют" % len(checked_files),
        [trunc("%s → %s" % (m["raw"], m["path"]), 400) for m in missing_files[:15]],
    ))
    checks.append(make_check(
        "links.anchors", "Якоря на существующие элементы",
        "FAIL" if missing_anchors else "PASS",
        ("битых якорей: %d" % len(missing_anchors)) if missing_anchors
        else "якорей проверено: %d — все существуют" % anchors_ok,
        [trunc("%s (%s)" % (m["raw"], m["reason"]), 300) for m in missing_anchors[:15]],
    ))
    checks.append(make_check(
        "links.external", "Внешние ссылки (не проверяются)", "PASS",
        "локальных: %d, внешних: %d, пропущено: %d" % (len(checked_files), len(external), skip),
        [trunc(u, 160) for u in external[:8]],
    ))
    return checks


def check_overflow(cdp):
    checks = []
    for width, height in VIEWPORTS:
        set_viewport(cdp, width, height)
        cdp.pump(0.8)
        state = eval_json(cdp, r"""(function(){
          var iw = window.innerWidth;
          var offenders = [];
          // элемент внутри контейнера с собственной прокруткой/клипом —
          // это не overflow страницы (например, лента чипов или таблица сравнения)
          function inScrollBox(el) {
            var p = el.parentElement;
            while (p && p !== document.body && p !== document.documentElement) {
              var pcs = getComputedStyle(p);
              var ox = pcs.overflowX;
              if ((ox === 'auto' || ox === 'scroll' || ox === 'hidden') &&
                  p.scrollWidth > p.clientWidth + 2) return true;
              p = p.parentElement;
            }
            return false;
          }
          var nodes = document.querySelectorAll('body *');
          for (var i = 0; i < nodes.length; i++) {
            var el = nodes[i];
            if (el.closest('[data-modal],[data-cart],[data-overlay],.modal,.cart,.cmp__scroll')) continue;
            var cs = getComputedStyle(el);
            if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed') continue;
            var r = el.getBoundingClientRect();
            if (r.width <= 1) continue;
            if (r.right > iw + 2) {
              if (inScrollBox(el)) continue;
              offenders.push({
                tag: el.tagName.toLowerCase(),
                cls: String(el.className || '').slice(0, 70),
                right: Math.round(r.right)
              });
              if (offenders.length >= 8) break;
            }
          }
          return {
            iw: iw,
            scrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            offenders: offenders
          };
        })()""")
        over = max(0, state.get("scrollWidth", width) - width)
        offenders = state.get("offenders", [])
        bad = bool(offenders)
        if over > 1:
            detail = "горизонтальная прокрутка: scrollWidth %d > viewport %d на %dpx" % (
                state.get("scrollWidth", width), width, over)
        elif bad:
            detail = ("прокрутки нет (body overflow-x: hidden), но %d элем. выходят за viewport "
                      "и обрезаны (например, шапка)" % len(offenders))
        else:
            detail = "ширина страницы = viewport (scrollWidth %d)" % state.get("scrollWidth", width)
        checks.append(make_check(
            "layout.overflow_%d" % width, "Overflow при %dpx" % width,
            "FAIL" if (over > 1 or bad) else "PASS",
            detail,
            ["%s.%s right=%s" % (o["tag"], o["cls"], o["right"]) for o in offenders],
        ))
    set_viewport(cdp, *SHOT_1440)
    cdp.pump(0.4)
    return checks


def _read_state(cdp):
    return eval_json(cdp, r"""(function(){
      var q = function(s){ return document.querySelector(s); };
      var countText = q('[data-count]') ? q('[data-count]').textContent.trim() : null;
      var cards = document.querySelectorAll('[data-grid] .card').length;
      return {
        cards: cards,
        countText: countText,
        count: (function(){ var m = /(\d+)/.exec(countText || ''); return m ? parseInt(m[1], 10) : null; })(),
        cartBadge: q('[data-cart-badge]') ? q('[data-cart-badge]').textContent.trim() : null,
        cartItems: document.querySelectorAll('.cart__item').length
      };
    })()""")


def check_features(cdp, page_path):
    checks = []
    meta = eval_json(cdp, r"""(function(){
      return {
        lang: document.documentElement.getAttribute('lang') || '',
        title: (document.title || '').trim(),
        viewport: !!document.querySelector('meta[name="viewport"]'),
        description: !!document.querySelector('meta[name="description"]')
      };
    })()""")
    meta_ok = (meta.get("lang") or "").lower().startswith("ru") and bool(meta.get("title")) \
        and meta.get("viewport") and meta.get("description")
    checks.append(make_check(
        "features.meta", "Базовая разметка документа",
        "PASS" if meta_ok else "WARN",
        "lang=%s, title=%s, viewport=%s, description=%s" % (
            meta.get("lang"), "есть" if meta.get("title") else "НЕТ",
            "есть" if meta.get("viewport") else "НЕТ",
            "есть" if meta.get("description") else "НЕТ"),
        [] if meta_ok else ["проверьте lang/title/meta"],
    ))

    total = eval_json(cdp, "document.querySelectorAll('[data-grid] .card').length")
    grid_open = eval_json(cdp, "document.querySelectorAll('[data-grid] [data-open]').length")
    all_open = eval_json(cdp, "document.querySelectorAll('[data-open]').length")
    checks.append(make_check(
        "features.grid", "Грид каталога отрисован", "PASS" if total >= 33 else "FAIL",
        "карточек: %d, [data-open] в гриде: %d, всего [data-open]: %d" % (total, grid_open, all_open),
    ))

    # --- чипы категорий ---
    try:
        cats = eval_json(cdp, "Array.prototype.slice.call(document.querySelectorAll('[data-cat]')).map(function(b){return b.getAttribute('data-cat');})")
        first_cat = next((c for c in cats if c != "all"), None)
        base = _read_state(cdp)
        eval_json(cdp, "(function(){var b=document.querySelector('[data-cat=%s]');if(b)b.click();return 1;})()" % json.dumps(first_cat))
        cdp.pump(0.6)
        filtered = _read_state(cdp)
        chips_ok = (
            first_cat is not None
            and filtered["cards"] > 0
            and filtered["count"] is not None
            and filtered["cards"] == filtered["count"]
            and filtered["cards"] < base["cards"]
        )
        eval_json(cdp, "(function(){var b=document.querySelector('[data-cat=\"all\"]');if(b)b.click();return 1;})()")
        cdp.pump(0.6)
        restored = _read_state(cdp)
        chips_ok = chips_ok and restored["cards"] == base["cards"]
        checks.append(make_check(
            "features.chips", "Фильтр категорий меняет счётчик",
            "PASS" if chips_ok else "FAIL",
            "категорий: %d; «%s» → карточек %s, счётчик «%s»; «Все» → %s"
            % (len(cats), first_cat, filtered["cards"], filtered["countText"], restored["cards"]),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.chips", "Фильтр категорий меняет счётчик", "FAIL", trunc(str(exc))))

    # --- «вне сайта» ---
    try:
        eval_json(cdp, "(function(){var b=document.querySelector('[data-archive]');if(b)b.click();return !!b;})()")
        cdp.pump(0.6)
        archive = _read_state(cdp)
        eval_json(cdp, "(function(){var b=document.querySelector('[data-archive]');if(b)b.click();return 1;})()")
        cdp.pump(0.6)
        back = _read_state(cdp)
        archive_ok = archive["count"] == 10 and archive["cards"] == 10 and back["cards"] == total
        checks.append(make_check(
            "features.archive", "Фильтр «Вне сайта» → 10",
            "PASS" if archive_ok else "FAIL",
            "«вне сайта»: карточек %s, счётчик «%s»; после снятия: %s"
            % (archive["cards"], archive["countText"], back["cards"]),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.archive", "Фильтр «Вне сайта» → 10", "FAIL", trunc(str(exc))))

    # --- поиск ---
    try:
        eval_json(cdp, "(function(){var i=document.querySelector('[data-search]');if(!i)return null;i.value='Штора';i.dispatchEvent(new Event('input',{bubbles:true}));return i.value;})()")
        cdp.pump(0.8)
        search = _read_state(cdp)
        eval_json(cdp, "(function(){var i=document.querySelector('[data-search]');if(!i)return null;i.value='';i.dispatchEvent(new Event('input',{bubbles:true}));return i.value;})()")
        cdp.pump(0.7)
        reset = _read_state(cdp)
        search_ok = (
            search["count"] is not None and search["count"] > 0
            and search["cards"] == search["count"]
            and reset["cards"] == total
        )
        checks.append(make_check(
            "features.search", "Поиск «Штора» → >0",
            "PASS" if search_ok else "FAIL",
            "найдено карточек: %s, счётчик «%s»; после сброса: %s"
            % (search["cards"], search["countText"], reset["cards"]),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.search", "Поиск «Штора» → >0", "FAIL", trunc(str(exc))))

    # --- сортировка ---
    try:
        sort_results = {}
        for value in ("price-asc", "price-desc", "default"):
            eval_json(cdp, "(function(){var s=document.querySelector('[data-sort]');if(!s)return null;s.value=%s;"
                          "s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()" % json.dumps(value))
            cdp.pump(0.5)
            sort_results[value] = _read_state(cdp)
        sort_ok = all(
            st["cards"] == total and st["count"] == total
            for st in sort_results.values()
        )
        checks.append(make_check(
            "features.sort", "Сортировка не ломает число",
            "PASS" if sort_ok else "FAIL",
            "asc: %s/«%s», desc: %s/«%s», default: %s/«%s»" % (
                sort_results["price-asc"]["cards"], sort_results["price-asc"]["countText"],
                sort_results["price-desc"]["cards"], sort_results["price-desc"]["countText"],
                sort_results["default"]["cards"], sort_results["default"]["countText"],
            ),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.sort", "Сортировка не ломает число", "FAIL", trunc(str(exc))))

    # --- модалка ---
    try:
        eval_json(cdp, "(function(){var c=document.querySelector('[data-grid] .card');if(!c)return null;c.click();return 1;})()")
        cdp.pump(0.7)
        opened = eval_json(cdp, r"""(function(){
          var m = document.querySelector('[data-modal]');
          var body = document.querySelector('[data-modal-body]');
          return {
            open: !!(m && m.classList.contains('is-open')),
            hasBody: !!(body && body.innerHTML.trim().length > 50),
            locked: document.body.classList.contains('is-locked')
          };
        })()""")
        press_escape(cdp)
        cdp.pump(0.7)
        closed = eval_json(cdp, r"""(function(){
          var m = document.querySelector('[data-modal]');
          return {
            open: !!(m && m.classList.contains('is-open')),
            locked: document.body.classList.contains('is-locked')
          };
        })()""")
        modal_ok = opened.get("open") and opened.get("hasBody") and not closed.get("open") and not closed.get("locked")
        checks.append(make_check(
            "features.modal", "Модалка: открыть / Escape",
            "PASS" if modal_ok else "FAIL",
            "открыта: %s, контент: %s, закрыта: %s, body lock снят: %s"
            % (opened.get("open"), opened.get("hasBody"), not closed.get("open"), not closed.get("locked")),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.modal", "Модалка: открыть / Escape", "FAIL", trunc(str(exc))))

    # --- корзина ---
    try:
        badge0 = _read_state(cdp)["cartBadge"]
        eval_json(cdp, "(function(){var c=document.querySelector('[data-grid] .card');if(!c)return null;c.click();return 1;})()")
        cdp.pump(0.7)
        added = eval_json(cdp, r"""(function(){
          var btn = document.querySelector('.modal__buy [data-add]');
          if (btn) btn.click();
          return 1;
        })()""")
        cdp.pump(0.8)
        cart_open = eval_json(cdp, r"""(function(){
          var c = document.querySelector('[data-cart]');
          var ov = document.querySelector('[data-overlay]');
          return {
            open: !!(c && c.classList.contains('is-open')),
            overlay: !!(ov && ov.classList.contains('is-on')),
            items: document.querySelectorAll('.cart__item').length,
            badge: document.querySelector('[data-cart-badge]') ? document.querySelector('[data-cart-badge]').textContent.trim() : null
          };
        })()""")
        eval_json(cdp, "(function(){var b=document.querySelector('[data-cart-close]');if(b)b.click();return 1;})()")
        cdp.pump(0.5)
        press_escape(cdp)
        cdp.pump(0.5)
        # очистка корзины, чтобы не влиять на повторный прогон/состояние
        eval_json(cdp, "(function(){var b=document.querySelector('[data-cart-toggle]');if(b)b.click();return 1;})()")
        cdp.pump(0.4)
        eval_json(cdp, "(function(){var d=document.querySelector('[data-del]');if(d)d.click();return 1;})()")
        cdp.pump(0.4)
        eval_json(cdp, "(function(){var b=document.querySelector('[data-cart-close]');if(b)b.click();return 1;})()")
        cdp.pump(0.4)
        after = _read_state(cdp)
        cart_ok = (
            cart_open.get("open") and cart_open.get("overlay")
            and cart_open.get("items") == 1
            and parse_count(cart_open.get("badge")) == 1
            and parse_count(after["cartBadge"]) == 0
            and after["cartItems"] == 0
        )
        checks.append(make_check(
            "features.cart", "Корзина инкрементит бейдж",
            "PASS" if cart_ok else "FAIL",
            "бейдж %s → %s, позиций: %s, оверлей: %s; очистка → %s"
            % (badge0, cart_open.get("badge"), cart_open.get("items"), cart_open.get("overlay"), after["cartBadge"]),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.cart", "Корзина инкрементит бейдж", "FAIL", trunc(str(exc))))

    # --- форма заявки ---
    try:
        form = eval_json(cdp, r"""(function(){
          var f = document.querySelector('[data-request-form]');
          return {
            exists: !!f,
            fields: f ? f.querySelectorAll('input,textarea,select').length : 0,
            submit: !!document.querySelector('[data-submit-request]'),
            copy: !!document.querySelector('[data-copy-request]'),
            note: !!document.querySelector('[data-request-note]')
          };
        })()""")
        form_ok = form.get("exists") and form.get("fields", 0) >= 4 and form.get("submit")
        checks.append(make_check(
            "features.form", "Форма заявки", "PASS" if form_ok else "FAIL",
            "форма: %s, полей: %s, «Отправить»: %s, «Скопировать»: %s, примечание: %s"
            % (form.get("exists"), form.get("fields"), form.get("submit"), form.get("copy"), form.get("note")),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.form", "Форма заявки", "FAIL", trunc(str(exc))))

    # --- телефон / QR ---
    try:
        contacts = eval_json(cdp, r"""(function(){
          var tel = document.querySelector('[data-contact-phone] a[href^="tel:"]') || document.querySelector('a[href^="tel:"]');
          var qr = document.querySelector('.order__qr img') || document.querySelector('img[src*="qr"]');
          return {
            tel: tel ? tel.getAttribute('href') : null,
            telText: tel ? tel.textContent.trim() : null,
            qr: qr ? { src: qr.getAttribute('src'), ok: qr.complete && qr.naturalWidth > 0 } : null
          };
        })()""")
        contacts_ok = bool(contacts.get("tel")) and bool(contacts.get("qr") and contacts["qr"].get("ok"))
        checks.append(make_check(
            "features.contacts", "Телефон tel: и QR",
            "PASS" if contacts_ok else "FAIL",
            "tel: %s (%s), QR: %s" % (
                contacts.get("tel"), contacts.get("telText"),
                (contacts.get("qr") or {}).get("src"),
            ),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.contacts", "Телефон tel: и QR", "FAIL", trunc(str(exc))))

    # --- PDF ---
    try:
        pdfs = eval_json(cdp, r"""(function(){
          function info(sel){
            var a = document.querySelector(sel);
            if (!a) return null;
            return {href: a.getAttribute('href'), abs: a.href};
          }
          return {field: info('[data-pdf-field]'), quiet: info('[data-pdf-quiet]')};
        })()""")
        pdf_issues = []
        pdf_meta = []
        for key, label in (("field", "вариант 1 (field)"), ("quiet", "вариант 2 (quiet)")):
            item = pdfs.get(key)
            if not item or not item.get("href"):
                pdf_issues.append("%s: ссылка отсутствует" % label)
                continue
            path = uri_to_path(item.get("abs") or "")
            if path is None or not path.exists():
                pdf_issues.append("%s: файл не найден (%s)" % (label, item.get("href")))
            else:
                pdf_meta.append("%s: %s (%.1f МБ)" % (label, path.name, path.stat().st_size / 1048576.0))
        checks.append(make_check(
            "features.pdfs", "Ссылки на оба PDF",
            "FAIL" if pdf_issues else "PASS",
            "; ".join(pdf_issues) if pdf_issues else "; ".join(pdf_meta),
            pdf_issues[:5],
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.pdfs", "Ссылки на оба PDF", "FAIL", trunc(str(exc))))

    # --- переключатель вариантов ---
    try:
        vs = eval_json(cdp, r"""(function(){
          var a = document.querySelector('[data-variant-switch]');
          return a ? {href: a.getAttribute('href'), abs: a.href, text: a.textContent.trim()} : null;
        })()""")
        vs_issues = []
        if not vs or not vs.get("href"):
            vs_issues.append("переключатель не найден")
        else:
            path = uri_to_path(vs.get("abs") or "")
            if path is None or not path.exists():
                vs_issues.append("файл варианта не найден: %s" % vs.get("href"))
            else:
                page_name = Path(page_path).name
                expected = "index.html" if page_name == "variant-2.html" else "variant-2.html"
                if path.name != expected:
                    vs_issues.append("ожидался %s, получен %s" % (expected, path.name))
        checks.append(make_check(
            "features.variant_switch", "Переключатель «Вариант 1/2»",
            "FAIL" if vs_issues else "PASS",
            "; ".join(vs_issues) if vs_issues
            else "ссылка «%s» → %s" % ((vs or {}).get("href"), uri_to_path((vs or {}).get("abs", "")) or "?"),
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("features.variant_switch", "Переключатель «Вариант 1/2»", "FAIL", trunc(str(exc))))

    return checks


GLUED_UNIT = re.compile(
    r"(?<![\d\-/.,])\d(?:[.,]\d+)?(?:кВт|МВт|ГГц|МГц|кГц|Гц|Вт|Ач|мА|дБ|мм|см|км|кг|кПа|м²|м|В|А|ч|мес)"
    r"(?![а-яёa-zA-ZА-ЯЁ0-9])"
)


def check_typography(cdp):
    text = js(cdp, "document.body.innerText || ''") or ""
    lines = [ln.strip() for ln in text.splitlines()]
    fail_dbl, warn_hyphen, warn_ellipsis, warn_glued, warn_iso = [], [], [], [], []
    for ln in lines:
        if not ln:
            continue
        m = re.search(r"\S[ \u00a0]{2,}\S", ln)
        if m:
            fail_dbl.append(trunc(ln[max(0, m.start() - 40): m.end() + 40], 160))
        if " - " in ln:
            warn_hyphen.append(trunc(ln, 160))
        if "..." in ln:
            warn_ellipsis.append(trunc(ln, 160))
        mg = GLUED_UNIT.search(ln)
        if mg:
            warn_glued.append(trunc(ln[max(0, mg.start() - 40): mg.end() + 40], 160))
        if re.search(r"\b\d{4}-\d{2}-\d{2}\b", ln):
            warn_iso.append(trunc(ln, 160))
    quotes_open = text.count("«")
    quotes_close = text.count("»")
    quotes_ok = quotes_open == quotes_close
    quotes_detail = "« = %d, » = %d" % (quotes_open, quotes_close)

    typo_fail = bool(fail_dbl) or not quotes_ok
    warns = bool(warn_hyphen or warn_ellipsis or warn_glued or warn_iso)
    if typo_fail:
        status = "FAIL"
    elif warns:
        status = "WARN"
    else:
        status = "PASS"

    detail = "строк: %d; двойных пробелов: %d; ёлочки: %s" % (
        len(lines), len(fail_dbl), quotes_detail,
    )
    evidence = []
    if fail_dbl:
        evidence.append("двойные пробелы (FAIL):")
        evidence.extend(fail_dbl[:8])
    if not quotes_ok:
        evidence.append("непарные ёлочки (FAIL): %s" % quotes_detail)
    if warn_hyphen:
        evidence.append("« - » вместо тире (WARN): %d, примеры:" % len(warn_hyphen))
        evidence.extend(warn_hyphen[:5])
    if warn_ellipsis:
        evidence.append("«...» вместо «…» (WARN): %d, примеры:" % len(warn_ellipsis))
        evidence.extend(warn_ellipsis[:5])
    if warn_glued:
        evidence.append("приклеенные единицы (WARN): %d, примеры:" % len(warn_glued))
        evidence.extend(warn_glued[:5])
    if warn_iso:
        evidence.append("ISO-даты (WARN): %d, примеры:" % len(warn_iso))
        evidence.extend(warn_iso[:5])
    checks = [make_check("typography.text", "Типографика видимого текста", status, detail, evidence)]
    # отдельные инфо-проверки по WARN, чтобы их было видно в таблице
    for cid, name, items in (
        ("typography.hyphen", "« - » вместо тире", warn_hyphen),
        ("typography.ellipsis", "«...» вместо «…»", warn_ellipsis),
        ("typography.glued_units", "Приклеенные единицы (24В, 50А)", warn_glued),
        ("typography.iso_dates", "ISO-даты", warn_iso),
    ):
        checks.append(make_check(
            cid, name, "WARN" if items else "PASS",
            "найдено: %d" % len(items) if items else "не найдено",
            [trunc(x, 200) for x in items[:6]],
        ))
    return checks


def check_reduced_motion(cdp, events_start):
    checks = []
    try:
        cdp.cmd("Emulation.setEmulatedMedia", {"features": [
            {"name": "prefers-reduced-motion", "value": "reduce"},
        ]})
        navigate(cdp, cdp.page_url, *SHOT_1440)
        state = eval_json(cdp, r"""(function(){
          var q = function(s){ var e = document.querySelector(s); return e ? getComputedStyle(e) : null; };
          var card = document.querySelector('[data-grid] .card');
          var hero = q('.hero h1');
          var cardStyle = card ? getComputedStyle(card) : null;
          return {
            mq: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
            cards: document.querySelectorAll('[data-grid] .card').length,
            heroOpacity: hero ? hero.opacity : null,
            cardOpacity: cardStyle ? cardStyle.opacity : null,
            docHeight: document.documentElement.scrollHeight,
            scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior
          };
        })()""")
        cdp.pump(0.4)
        errors = eval_json(cdp, "(function(){return (window.__qa && window.__qa.errors) ? window.__qa.errors : [];})()")
        ok = (
            state.get("mq") and state.get("cards", 0) >= 33
            and state.get("heroOpacity") in (None, "1")
            and state.get("cardOpacity") in (None, "1")
            and state.get("docHeight", 0) > 1000
            and not errors
        )
        checks.append(make_check(
            "a11y.reduced_motion", "prefers-reduced-motion: контент виден",
            "PASS" if ok else "FAIL",
            "mq=%s, карточек=%s, h1.opacity=%s, card.opacity=%s, высота=%s, JS-ошибок=%d"
            % (state.get("mq"), state.get("cards"), state.get("heroOpacity"),
               state.get("cardOpacity"), state.get("docHeight"), len(errors or [])),
            [trunc(str(e), 300) for e in (errors or [])[:5]],
        ))
    except (CDPError, ScriptError) as exc:
        checks.append(make_check("a11y.reduced_motion", "prefers-reduced-motion: контент виден", "FAIL", trunc(str(exc))))
    finally:
        try:
            cdp.cmd("Emulation.setEmulatedMedia", {"features": []})
        except Exception:
            pass
    return checks


# ---------------------------------------------------------------------------
# Прогон страницы
# ---------------------------------------------------------------------------
def collect_deps_hashes(page_path):
    """Хэши CSS/JS, на которые напрямую ссылается страница (для базового прогона)."""
    out = {}
    try:
        html = Path(page_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for m in re.finditer(r'(?:href|src)="([^"#?]+\.(?:css|js))"', html):
        rel = m.group(1)
        if rel.startswith(("http:", "https:", "//", "data:")):
            continue
        p = (Path(page_path).parent / rel).resolve()
        if p.exists():
            out[str(p.relative_to(KILOWATT))] = {"sha256": sha256_file(p), "size": p.stat().st_size}
    return out


def run_page(cdp, page_path, args, shots_dir, page_index):
    url = file_uri(page_path)
    page_name = Path(page_path).name
    slug = Path(page_path).stem
    started = time.time()
    mark = len(cdp.events)
    deps_before = collect_deps_hashes(page_path)
    page_sha_before = sha256_file(page_path)
    result = {
        "page": page_name,
        "path": str(page_path),
        "url": url,
        "sha256": page_sha_before,
        "mtime": dt.datetime.fromtimestamp(Path(page_path).stat().st_mtime).isoformat(timespec="seconds"),
        "verdict": "FAIL",
        "checks": [],
        "screenshots": [],
        "deps": deps_before,
        "deps_changed_during_run": [],
        "duration_s": 0,
    }
    screenshots = []
    shot_names = []

    def add_shot(name):
        path = Path(shots_dir) / name
        shot_names.append(name)
        try:
            capture(cdp, path)
            screenshots.append(str(path.relative_to(Path(args.out))) if _is_under(path, Path(args.out)) else str(path))
            return True
        except Exception as exc:
            result.setdefault("harness_notes", []).append("скриншот %s: %s" % (name, trunc(str(exc), 160)))
            return False

    try:
        navigate(cdp, url, *SHOT_1440)
        result["title"] = js(cdp, "document.title") or ""
        if not args.skip_shots:
            add_shot(slug + "-1440.png")
            scroll_to_sel(cdp, "#catalog", 72)
            cdp.pump(0.7)
            add_shot(slug + "-catalog-1440.png")
            set_viewport(cdp, *SHOT_390)
            scroll_top(cdp)
            cdp.pump(1.0)
            add_shot(slug + "-390.png")
            scroll_to_sel(cdp, "#catalog", 64)
            cdp.pump(0.6)
            add_shot(slug + "-catalog-390.png")
            set_viewport(cdp, *SHOT_1440)
            scroll_top(cdp)
            cdp.pump(0.5)

        # --- ссылки/ассеты/якоря ---
        result["checks"].extend(check_links(cdp))

        # --- типографика ---
        result["checks"].extend(check_typography(cdp))

        # --- фичи каталога (открывают модалку: галерея догружается здесь) ---
        result["checks"].extend(check_features(cdp, page_path))

        # --- битые изображения (включая галерею модалки после открытия) ---
        broken, pending = check_images(cdp)

        # --- overflow ---
        result["checks"].extend(check_overflow(cdp))

        # --- reduced motion (перезагрузка страницы) ---
        result["checks"].extend(check_reduced_motion(cdp, mark))

        # --- runtime / network по всем событиям (включая reload) ---
        injected = eval_json(cdp, "(function(){return window.__qa || {};})()") or {}
        runtime_checks, failed = check_runtime(cdp, cdp.events, mark, injected)
        result["checks"] = runtime_checks + result["checks"]
        result["checks"].extend(check_network(failed, broken, pending))

        # --- скриншоты ---
        if args.skip_shots:
            result["checks"].append(make_check("harness.screenshots", "Скриншоты", "SKIP", "отключены флагом --skip-shots"))
        else:
            missing = []
            small = []
            for name in shot_names:
                p = Path(shots_dir) / name
                if not p.exists():
                    missing.append(name)
                elif p.stat().st_size < 5000:
                    small.append("%s (%d байт)" % (name, p.stat().st_size))
            result["checks"].append(make_check(
                "harness.screenshots", "Скриншоты 1440/390/каталог",
                "FAIL" if (missing or small) else "PASS",
                ("нет: %s; мелкие: %s" % (", ".join(missing), ", ".join(small))) if (missing or small)
                else "снято: %s" % ", ".join(shot_names),
                missing + small,
            ))

        result["screenshots"] = screenshots
        # --- не менялись ли файлы во время прогона (важно для эталона) ---
        deps_after = collect_deps_hashes(page_path)
        changed = []
        for dep, meta in deps_before.items():
            now_meta = deps_after.get(dep)
            if not now_meta or now_meta.get("sha256") != meta.get("sha256"):
                changed.append(str(dep))
        for dep in deps_after:
            if dep not in deps_before:
                changed.append(str(dep))
        if sha256_file(page_path) != page_sha_before:
            changed.append(Path(page_path).name)
        result["deps_changed_during_run"] = sorted(set(changed))
        result["checks"].append(make_check(
            "harness.files_stable", "Файлы не менялись во время прогона",
            "PASS" if not changed else "WARN",
            "стабильны" if not changed else "изменены во время прогона: %s" % ", ".join(sorted(set(changed))),
            sorted(set(changed)),
        ))
        result["verdict"] = page_verdict(result["checks"])
    except (CDPError, ScriptError, RuntimeError) as exc:
        result["checks"].append(make_check(
            "harness.page", "Прогон страницы", "FAIL",
            "сбой прогона: %s" % trunc(str(exc), 300),
            [trunc(traceback.format_exc(), 900)],
        ))
        result["verdict"] = "FAIL"
    finally:
        result["duration_s"] = round(time.time() - started, 1)
        result["summary"] = summarize(result["checks"])
        result["verdict"] = page_verdict(result["checks"])
    return result


def _is_under(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False


def run_once(pages, args):
    """Один прогон (один браузер) по всем страницам."""
    info = launch_chrome(args.chrome, forced_port=args.port)
    cdp = None
    results = []
    run_started = time.time()
    try:
        cdp = CDP(info["ws_url"])
        cdp.page_url = ""
        for cmd_name in ("Page.enable", "Runtime.enable", "Network.enable", "Log.enable"):
            cdp.cmd(cmd_name)
        cdp.cmd("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK_SOURCE})
        for idx, page in enumerate(pages):
            cdp.page_url = file_uri(page)
            print("[qa] %s ..." % Path(page).name, flush=True)
            res = run_page(cdp, page, args, args.shots, idx)
            print("[qa] %s -> %s (%s)" % (Path(page).name, res["verdict"], res.get("summary")), flush=True)
            results.append(res)
            # память событий не должна расти бесконечно между страницами
            cdp.events = cdp.events[-4000:]
    finally:
        shutdown_chrome(info, cdp)
    # проверяем, что после закрытия не осталось процессов нашего профиля
    leftovers = profile_process_count(info.get("profile"))
    return results, {
        "port": info.get("port"),
        "chrome": info.get("version"),
        "leftover_chrome": leftovers,
        "duration_s": round(time.time() - run_started, 1),
    }


# ---------------------------------------------------------------------------
# Отчёт
# ---------------------------------------------------------------------------
def check_status_icon(status):
    return {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "WARN": "⚠️ WARN", "SKIP": "— SKIP"}.get(status, status)


def md_escape(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_md(report, baseline=False):
    pages = report["pages"]
    s = report["summary"]
    out = []
    title = "Базовый QA-прогон каталога «В ОКОПЕ»" if baseline else "QA-отчёт каталога «В ОКОПЕ»"
    out.append("# %s" % title)
    out.append("")
    out.append("Дата: **%s**  " % report["generated"])
    out.append("Chrome: `%s` · Python: `%s` · harness: `qa_check.py %s`"
               % (report["harness"].get("chrome", "?"), report["python"], report["tool_version"]))
    out.append("")
    if baseline:
        out.append("> Это эталонный снимок состояния каталога. Хэши файлов зафиксированы ниже — ")
        out.append("> повторный прогон нового `variant-2.html` сравнивается именно с этим отчётом.")
        out.append("")
    out.append("**Итог: %s** — страниц: %d, PASS: %d, FAIL: %d, WARN: %d, SKIP: %d"
               % ("PASS ✅" if report["verdict"] == "PASS" else "FAIL ❌",
                  s["pages"], s["pass"], s["fail"], s["warn"], s["skip"]))
    out.append("")
    out.append("| Страница | Вердикт | PASS | FAIL | WARN | Длительность |")
    out.append("|---|---|---|---|---|---|")
    for p in pages:
        ps = p.get("summary", {})
        out.append("| `%s` | %s | %d | %d | %d | %.1f с |" % (
            p["page"], "PASS ✅" if p["verdict"] == "PASS" else "FAIL ❌",
            ps.get("PASS", 0), ps.get("FAIL", 0), ps.get("WARN", 0), p.get("duration_s", 0)))
    out.append("")

    problems = report.get("problems") or []
    if problems:
        out.append("## Проблемы (FAIL)")
        out.append("")
        for i, pr in enumerate(problems, 1):
            out.append("%d. **%s** — `%s` — %s" % (
                i, pr.get("name"), pr.get("page"), md_escape(trunc(pr.get("details", ""), 320))))
            for ev in (pr.get("evidence") or [])[:6]:
                out.append("   - `%s`" % md_escape(trunc(ev, 240)))
        out.append("")
    else:
        out.append("Проблем уровня FAIL не найдено.")
        out.append("")

    for p in pages:
        out.append("## %s — %s" % (p["page"], "PASS ✅" if p["verdict"] == "PASS" else "FAIL ❌"))
        out.append("")
        out.append("- URL: `%s`" % p["url"])
        out.append("- SHA-256: `%s`" % p.get("sha256"))
        out.append("- Изменён: `%s`" % p.get("mtime"))
        if p.get("title"):
            out.append("- Title: %s" % trunc(p["title"], 160))
        if p.get("deps_changed_during_run"):
            out.append("- ⚠️ во время прогона изменялись: `%s` — эталон мог захватить промежуточную версию"
                       % "`, `".join(p["deps_changed_during_run"]))
        if p.get("harness_notes"):
            out.append("- Примечания harness: %s" % "; ".join(p["harness_notes"]))
        out.append("")
        if p.get("deps"):
            out.append("**Зависимости (CSS/JS) на момент прогона**")
            out.append("")
            out.append("| Файл | Размер | SHA-256 |")
            out.append("|---|---|---|")
            for dep, meta in sorted(p["deps"].items()):
                out.append("| `%s` | %d | `%s` |" % (md_escape(dep), meta.get("size", 0), (meta.get("sha256") or "")[:16] + "…"))
            out.append("")
        fails = [c for c in p["checks"] if c["status"] == "FAIL"]
        if fails:
            out.append("### FAIL")
            out.append("")
            for c in fails:
                out.append("- **%s** — %s" % (c["name"], md_escape(trunc(c["details"], 300))))
                for ev in c.get("evidence", [])[:6]:
                    out.append("  - `%s`" % md_escape(trunc(ev, 260)))
            out.append("")
        warns = [c for c in p["checks"] if c["status"] == "WARN"]
        if warns:
            out.append("### WARN")
            out.append("")
            for c in warns:
                out.append("- **%s** — %s" % (c["name"], md_escape(trunc(c["details"], 300))))
                for ev in c.get("evidence", [])[:4]:
                    out.append("  - `%s`" % md_escape(trunc(ev, 240)))
            out.append("")
        out.append("### Все проверки")
        out.append("")
        out.append("| # | Проверка | Статус | Детали |")
        out.append("|---|---|---|---|")
        for i, c in enumerate(p["checks"], 1):
            out.append("| %d | %s | %s | %s |" % (i, md_escape(c["name"]), check_status_icon(c["status"]),
                                                  md_escape(trunc(c["details"], 260))))
        out.append("")
        if p.get("screenshots"):
            out.append("### Скриншоты")
            out.append("")
            for shot in p["screenshots"]:
                out.append("- `%s`" % shot)
            out.append("")

    if report.get("stability") and report["stability"].get("runs", 1) > 1:
        st = report["stability"]
        out.append("## Стабильность")
        out.append("")
        out.append("- Прогонов подряд: **%d**" % st.get("runs", 1))
        out.append("- Одинаковый вердикт: **%s**" % ("да ✅" if st.get("same_verdict") else "нет ❌"))
        out.append("- Одинаковые статусы проверок: **%s**" % ("да ✅" if st.get("same_checks") else "нет ❌"))
        if st.get("mismatches"):
            out.append("- Расхождения:")
            for m in st["mismatches"][:20]:
                out.append("  - `%s`" % md_escape(trunc(m, 240)))
        out.append("")

    h = report["harness"]
    out.append("## Harness")
    out.append("")
    out.append("- Chrome: `%s`" % h.get("chrome", "?"))
    out.append("- Порты CDP: `%s`" % ", ".join(str(p) for p in h.get("ports", [])))
    out.append("- Зависших процессов Chrome после прогона: **%s**" % h.get("leftover_chrome", "?"))
    out.append("- Временные профили удалены: %s" % ("да" if h.get("profiles_cleaned") else "см. примечания"))
    out.append("- Команда: `%s`" % h.get("command", ""))
    out.append("")
    out.append("---")
    out.append("")
    out.append("Перезапуск: `python kilowatt/catalog/_tools/qa/qa_check.py --sweep --repeat 2 --out kilowatt/redesign/qa`")
    out.append("")
    return "\n".join(out)


def write_reports(report, args, baseline=False):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    md = render_md(report, baseline=baseline)
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    if baseline:
        base_path = out_dir / "QA_BASE.md"
        with open(base_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv):
    ap = argparse.ArgumentParser(
        description="QA-стенд каталога «В ОКОПЕ» (CDP + Chrome headless)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--page", action="append", default=[], metavar="PATH",
                    help="страница каталога (file.html); можно несколько")
    ap.add_argument("--sweep", action="store_true",
                    help="прогнать оба варианта: catalog/variant-2.html и catalog/index.html")
    ap.add_argument("--out", default=str(REDESIGN / "qa"), metavar="DIR",
                    help="каталог отчёта (по умолчанию kilowatt/redesign/qa)")
    ap.add_argument("--shots", default=None, metavar="DIR",
                    help="каталог скриншотов (по умолчанию <out>/shots)")
    ap.add_argument("--repeat", type=int, default=1, metavar="N",
                    help="сколько прогонов подряд для проверки стабильности (по умолчанию 1)")
    ap.add_argument("--baseline", action="store_true",
                    help="эталонный прогон: дополнительно пишет QA_BASE.md")
    ap.add_argument("--skip-shots", action="store_true", help="не снимать скриншоты")
    ap.add_argument("--chrome", default=DEFAULT_CHROME, help="путь к chrome.exe")
    ap.add_argument("--port", type=int, default=0, help="фиксированный порт CDP (по умолчанию 9441+)")
    ap.add_argument("--quiet", action="store_true", help="меньше вывода")
    return ap.parse_args(argv)


def resolve_pages(args):
    pages = []
    if args.page:
        for p in args.page:
            if p.startswith(("file://", "http://", "https://")):
                if not p.startswith("file://"):
                    raise SystemExit("QA поддерживает только file:// (получено %s)" % p)
                path = uri_to_path(p)
                if path is None:
                    raise SystemExit("не разобрать URL: %s" % p)
                pages.append(path)
            else:
                pages.append(Path(p).resolve())
    elif args.sweep:
        for name in SWEEP_NAMES:
            pages.append((CATALOG / name).resolve())
    else:
        pages.append((CATALOG / SWEEP_NAMES[0]).resolve())
    for p in pages:
        if not p.exists():
            raise SystemExit("страница не найдена: %s" % p)
    return pages


def compare_runs(runs):
    """Сравнивает статусы проверок между прогонами (одинаковый вердикт)."""
    signatures = []
    for run in runs:
        sig = {}
        for page in run:
            sig[page["page"]] = {c["id"]: c["status"] for c in page["checks"]}
        signatures.append(sig)
    same_verdict = True
    same_checks = True
    mismatches = []
    if len(runs) > 1:
        first = signatures[0]
        for idx, sig in enumerate(signatures[1:], 2):
            for page_name, checks in first.items():
                other = sig.get(page_name, {})
                if set(checks) != set(other):
                    same_checks = False
                    mismatches.append("%s: разный набор проверок в прогоне %d" % (page_name, idx))
                    continue
                for cid, status in checks.items():
                    if other.get(cid) != status:
                        same_checks = False
                        mismatches.append("%s/%s: %s → %s (прогон %d)" % (page_name, cid, status, other.get(cid), idx))
        # вердикты страниц
        for run in runs[1:]:
            for page in run:
                base = next((p for p in runs[0] if p["page"] == page["page"]), None)
                if base and base["verdict"] != page["verdict"]:
                    same_verdict = False
    return {
        "runs": len(runs),
        "same_verdict": same_verdict and len(runs) > 1,
        "same_checks": same_checks and len(runs) > 1,
        "mismatches": mismatches[:30],
    }


def main(argv=None):
    args = parse_args(argv)
    args.out = str(Path(args.out).resolve())
    args.shots = str(Path(args.shots).resolve()) if args.shots else str(Path(args.out) / "shots")
    Path(args.shots).mkdir(parents=True, exist_ok=True)
    pages = resolve_pages(args)
    repeat = max(1, args.repeat)
    ports = []
    all_runs = []
    harness_runs = []
    global_started = time.time()

    if not args.quiet:
        print("[qa] страницы: %s" % ", ".join(str(p.name) for p in pages))
        print("[qa] повтор: %d" % repeat)

    for r in range(repeat):
        if not args.quiet:
            print("[qa] прогон %d/%d" % (r + 1, repeat))
        try:
            results, harness = run_once(pages, args)
        except Exception:
            tb = traceback.format_exc()
            print("[qa] FATAL:\n%s" % tb, file=sys.stderr)
            results = []
            for page in pages:
                results.append({
                    "page": page.name, "path": str(page), "url": file_uri(page),
                    "sha256": sha256_file(page), "mtime": "", "verdict": "FAIL",
                    "checks": [make_check("harness.fatal", "Запуск harness", "FAIL", trunc(tb, 600), [trunc(tb, 900)])],
                    "screenshots": [], "summary": {"PASS": 0, "FAIL": 1, "WARN": 0, "SKIP": 0},
                    "duration_s": 0, "deps": collect_deps_hashes(page),
                })
            harness = {"port": None, "chrome": "?", "leftover_chrome": -1, "duration_s": 0}
        if harness.get("port"):
            ports.append(harness["port"])
        harness_runs.append(harness)
        all_runs.append(results)
        # краткий человекочитаемый прогресс
        for page in results:
            if not args.quiet:
                print("[qa]   %s → %s" % (page["page"], page["verdict"]))

    primary = all_runs[0]
    stability = compare_runs(all_runs) if repeat > 1 else {
        "runs": 1, "same_verdict": None, "same_checks": None, "mismatches": [],
    }

    # при повторных прогонах добавляем проверку стабильности в каждую страницу
    if repeat > 1:
        st_status = "PASS" if (stability["same_verdict"] and stability["same_checks"]) else "FAIL"
        st_detail = "%d прогона: вердикт %s, статусы проверок %s" % (
            repeat,
            "совпал" if stability["same_verdict"] else "разошёлся",
            "совпали" if stability["same_checks"] else "разошлись",
        )
        for page in primary:
            page["checks"].append(make_check("stability.repeat", "Стабильность: %d прогона" % repeat,
                                             st_status, st_detail, stability["mismatches"][:10]))
            page["summary"] = summarize(page["checks"])
            page["verdict"] = page_verdict(page["checks"])

    totals = {"pages": len(primary), "pass": 0, "fail": 0, "warn": 0, "skip": 0}
    for page in primary:
        if page["verdict"] == "PASS":
            totals["pass"] += 1
        else:
            totals["fail"] += 1
        for c in page["checks"]:
            if c["status"] == "WARN":
                totals["warn"] += 1
            elif c["status"] == "SKIP":
                totals["skip"] += 1
    leftovers = [h.get("leftover_chrome") for h in harness_runs]
    harness_agg = {
        "chrome": harness_runs[0].get("chrome", "?") if harness_runs else "?",
        "ports": ports,
        "leftover_chrome": max(leftovers) if leftovers else -1,
        "profiles_cleaned": all((h.get("leftover_chrome") == 0) for h in harness_runs) if harness_runs else False,
        "command": " ".join([Path(PY).name] + [str(a) for a in (argv if argv is not None else [])]) if argv else "",
    }
    # команда для отчёта — собираем из sys.argv
    harness_agg["command"] = " ".join([Path(PY).name] + sys.argv[1:])

    report = {
        "tool": "qa_check.py",
        "tool_version": HARNESS_VERSION,
        "generated": now_iso(),
        "python": PY_VERSION,
        "pages": primary,
        "summary": totals,
        "problems": [
            {
                "page": page["page"],
                "id": c["id"],
                "name": c["name"],
                "details": c["details"],
                "evidence": (c.get("evidence") or [])[:8],
            }
            for page in primary
            for c in page["checks"]
            if c["status"] == "FAIL"
        ],
        "stability": stability,
        "harness": harness_agg,
        "runs": [
            {"run": i + 1, "harness": h, "pages": [{"page": p["page"], "verdict": p["verdict"]} for p in run]}
            for i, (run, h) in enumerate(zip(all_runs, harness_runs))
        ],
    }
    report["verdict"] = "PASS" if (totals["fail"] == 0 and harness_agg["leftover_chrome"] in (0, -1)) else "FAIL"
    if repeat > 1 and not (stability["same_verdict"] and stability["same_checks"]):
        report["verdict"] = "FAIL"

    json_path, md_path = write_reports(report, args, baseline=args.baseline)
    print("")
    print("[qa] вердикт: %s" % ("PASS" if report["verdict"] == "PASS" else "FAIL"))
    for page in primary:
        ps = page.get("summary", {})
        print("[qa]   %-14s %-6s PASS=%s FAIL=%s WARN=%s" % (
            page["page"], page["verdict"], ps.get("PASS", 0), ps.get("FAIL", 0), ps.get("WARN", 0)))
    print("[qa] отчёт: %s" % json_path)
    print("[qa] markdown: %s" % md_path)
    if args.baseline:
        print("[qa] эталон: %s" % (Path(args.out) / "QA_BASE.md"))
    print("[qa] chrome leftovers: %s" % harness_agg["leftover_chrome"])
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[qa] прервано", file=sys.stderr)
        sys.exit(130)
