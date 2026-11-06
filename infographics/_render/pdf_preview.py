# -*- coding: utf-8 -*-
"""Скриншот страниц готового PDF (проверка «PDF открывается и выглядит правильно»).

Открывает PDF в headless Chrome через его PDF-viewer (CDP) и снимает первые
N страниц в PNG. Если viewer в headless недоступен — честно сообщает FAIL,
и тогда визуальная проверка PDF идёт через print.html (см. build_pdf.ps1).

Использование:
  python _render/pdf_preview.py "05_ГОТОВОЕ/pdf/Информатика.pdf" --out _render/_qa/pdf_pages --pages 3
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CDP:
    def __init__(self, port: int):
        import websocket
        tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
        pages = [t for t in tabs if t.get("type") == "page"]
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=30,
                                              max_size=256 * 1024 * 1024)
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


def launch(profile: Path):
    port = free_port()
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
         "--no-default-browser-check", "--disable-extensions",
         f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            return proc, port
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("Chrome завершился")
            time.sleep(0.25)
    raise RuntimeError("CDP не поднялся")


def page_grab(cdp: CDP, pdf_uri: str, out_path: Path, page_no: int, tries: int = 4) -> bool:
    """Снимает страницу PDF; повторяет, если viewer не успел отрисовать страницу."""
    from PIL import Image
    for attempt in range(1, tries + 1):
        # сброс на about:blank, чтобы Chrome viewer перезагрузил PDF и применил #page=
        cdp.cmd("Page.navigate", {"url": "about:blank"})
        time.sleep(0.5)
        cdp.cmd("Page.navigate", {"url": f"{pdf_uri}#page={page_no}"})
        time.sleep(3.0 if attempt == 1 else 4.5)
        data = cdp.cmd("Page.captureScreenshot", {"format": "png"})["data"]
        out_path.write_bytes(base64.b64decode(data))
        try:
            with Image.open(out_path) as im:
                gray = im.convert("L")
                # центральная зона страницы: там должен быть светлый «лист» постера
                w, h = gray.size
                crop = gray.crop((int(w * 0.30), int(h * 0.18), int(w * 0.78), int(h * 0.90)))
                hist = crop.histogram()
                bright = sum(hist[180:])
                frac = bright / max(1, crop.size[0] * crop.size[1])
            print(f"  стр.{page_no} (попытка {attempt}): светлых пикселей {frac:.1%}, "
                  f"{out_path.stat().st_size} Б")
            if frac > 0.30:
                return True
        except Exception as e:
            print(f"  стр.{page_no} (попытка {attempt}): (Pillow: {e})")
        time.sleep(1.5)
    print(f"  ПРЕДУПРЕЖДЕНИЕ: стр.{page_no} не отрисовалась в PDF-viewer за {tries} попыток")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "_qa" / "pdf_pages"))
    ap.add_argument("--pages", default="1", help="номера страниц через запятую: 1,12")
    ap.add_argument("--width", type=int, default=1000)
    ap.add_argument("--height", type=int, default=1414)
    a = ap.parse_args()
    pdf = Path(a.pdf).resolve()
    if not pdf.is_file():
        print(f"FAIL: нет PDF {pdf}")
        return 2
    pages = [int(x) for x in a.pages.split(",") if x.strip()]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="dsh-pdfshot-"))
    proc = None
    worst = 0
    try:
        proc, port = launch(profile)
        cdp = CDP(port)
        cdp.cmd("Page.enable")
        cdp.cmd("Emulation.setDeviceMetricsOverride", {"width": a.width, "height": a.height,
                                                       "deviceScaleFactor": 1, "mobile": False})
        for page_no in pages:
            p = out / f"page_{page_no:02d}.png"
            ok = page_grab(cdp, pdf.as_uri(), p, page_no)
            print(f"shot: {p} ({p.stat().st_size} Б)")
            if not ok:
                worst = max(worst, 1)
        return worst
    finally:
        if proc is not None:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            except Exception:
                pass
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
