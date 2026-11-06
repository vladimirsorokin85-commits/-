# -*- coding: utf-8 -*-
"""Скриншоты нескольких локальных HTML через CDP."""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def launch(port):
    prof = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "dsh-cdp-%d" % int(time.time() * 1000))
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                          "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof,
                          "--no-first-run", "--no-default-browser-check", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1).read()
            return p, prof
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("CDP fail")


class CDP:
    def __init__(self, port):
        tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port).read())
        page = [t for t in tabs if t.get("type") == "page"][0]
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30, max_size=200 * 1024 * 1024)
        self.i = 0

    def cmd(self, m, params=None):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": m, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.i:
                if "error" in msg:
                    raise RuntimeError(f"{m}: {msg['error']}")
                return msg.get("result", {})


def main():
    files = sys.argv[1:]
    port = 9344
    proc, prof = launch(port)
    try:
        cdp = CDP(port)
        cdp.cmd("Page.enable")
        for f in files:
            base = os.path.splitext(f)[0]
            uri = "file:///" + os.path.abspath(f).replace("\\", "/")
            for w, h, tag in ((1440, 900, "desk"), (390, 844, "mob")):
                cdp.cmd("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": w < 600})
                cdp.cmd("Page.navigate", {"url": uri})
                time.sleep(1.8)
                data = cdp.cmd("Page.captureScreenshot", {"format": "png"})["data"]
                out = base + "." + tag + ".png"
                open(out, "wb").write(base64.b64decode(data))
                print("shot:", out, os.path.getsize(out))
    finally:
        proc.terminate()
        time.sleep(0.4)
        import shutil
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
