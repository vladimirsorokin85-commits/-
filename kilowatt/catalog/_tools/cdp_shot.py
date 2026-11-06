# -*- coding: utf-8 -*-
"""Скриншоты каталога через Chrome DevTools Protocol (надёжно, с прокруткой и полной страницей).

Использование:
  python cdp_shot.py --url file:///.../index.html --out DIR [--sections about,flags,...] [--full] [--width 1440] [--height 900]
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def launch(port=9333):
    prof = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "dsh-cdp-%d" % int(time.time() * 1000))
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--remote-debugging-port=%d" % port,
        "--user-data-dir=" + prof,
        "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "about:blank",
    ]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # ждём порт
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1).read()
            return p, prof, port
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("CDP не поднялся")


class CDP:
    def __init__(self, port):
        self.port = port
        tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port).read())
        page = [t for t in tabs if t.get("type") == "page"][0]
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30, max_size=200 * 1024 * 1024)
        self.i = 0

    def cmd(self, method, params=None):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.i:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})


def shot(cdp, url, out_path, width, height, scroll_to=None, full=False):
    cdp.cmd("Page.enable")
    cdp.cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 600,
    })
    cdp.cmd("Page.navigate", {"url": url})
    time.sleep(1.6)  # загрузка + шрифты
    if scroll_to:
        js = ("(function(){var el=document.querySelector(%r);if(!el)return 'none';"
              "var y=el.getBoundingClientRect().top+window.pageYOffset-62;"
              "document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,y);"
              "return String(y);})()" % scroll_to)
        cdp.cmd("Runtime.evaluate", {"expression": js, "returnByValue": True})
        time.sleep(0.6)
    params = {"format": "png", "captureBeyondViewport": bool(full)}
    if full:
        metrics = cdp.cmd("Page.getLayoutMetrics")
        cs = metrics.get("cssContentSize") or metrics.get("contentSize")
        params["clip"] = {"x": 0, "y": 0, "width": width, "height": min(cs["height"], 20000), "scale": 1}
    data = cdp.cmd("Page.captureScreenshot", params)["data"]
    open(out_path, "wb").write(base64.b64decode(data))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sections", default="")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    proc, prof, port = launch()
    try:
        cdp = CDP(port)
        if a.full:
            shot(cdp, a.url, os.path.join(a.out, "full.png"), a.width, a.height, full=True)
            print("full.png")
        for sec in [s for s in a.sections.split(",") if s]:
            path = os.path.join(a.out, f"sec-{sec}.png")
            shot(cdp, a.url, path, a.width, a.height, scroll_to="#" + sec)
            print("sec:", sec, os.path.getsize(path))
        if not a.full and not a.sections:
            shot(cdp, a.url, os.path.join(a.out, "top.png"), a.width, a.height)
            print("top.png")
    finally:
        proc.terminate()
        time.sleep(0.4)
        import shutil
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
