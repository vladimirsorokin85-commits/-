#!/usr/bin/env python3
"""Preview server: video player + YouTube title/description. Supports HTTP Range (seeking)."""
import html, os, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
VIDEO = next((c for c in (os.path.join(ROOT, "smekalka_video.mp4"), "/tmp/smk4/smekalka_video.mp4") if os.path.exists(c)), "/tmp/smk4/smekalka_video.mp4")
DESC = os.path.join(ROOT, "youtube_smekalka_description.md")


def page():
    md = open(DESC, encoding="utf-8").read() if os.path.exists(DESC) else ""
    title = re.search(r"\*\*(.+?)\*\*", md.split("## Название (основное)")[-1])
    title = title.group(1) if title else "Окопная смекалка"
    global VIDEO
    VIDEO = next((c for c in (os.path.join(ROOT, "smekalka_video.mp4"), "/tmp/smk4/smekalka_video.mp4") if os.path.exists(c)), VIDEO)
    size = os.path.getsize(VIDEO) / 1e6 if os.path.exists(VIDEO) else 0
    player = ('<video src="/video.mp4" controls preload="metadata" poster="/poster.jpg"></video>' if os.path.exists(VIDEO)
              else '<div style="padding:80px;text-align:center;background:#181b19;border-radius:10px">⏳ Видео рендерится — обновите страницу через несколько минут</div>')
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{margin:0;background:#0f1110;color:#e8e8e8;font:16px/1.5 system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
.brand{{color:#f59e0b;font-weight:800;letter-spacing:.12em;font-size:13px}}
h1{{font-size:24px;margin:6px 0 16px}}
video{{width:100%;border-radius:10px;background:#000;box-shadow:0 10px 40px #0008}}
.meta{{color:#9a9a9a;font-size:14px;margin:8px 0 20px}}
a.btn{{display:inline-block;background:#f59e0b;color:#111;padding:8px 16px;border-radius:6px;
text-decoration:none;font-weight:700;margin-right:8px}}
pre{{white-space:pre-wrap;background:#181b19;border:1px solid #2a2f2c;border-radius:10px;
padding:18px;font:14px/1.55 ui-monospace,monospace;color:#d6d6d6}}
</style></head><body><div class="wrap">
<div class="brand">МАГАЗИН «В ОКОПЕ» · СПЕЦВЫПУСК</div>
<h1>{html.escape(title)}</h1>
{player}
<div class="meta">7:26 · 1280×720 · {size:.1f} МБ</div>
<a class="btn" href="/video.mp4" download>Скачать видео</a>
<h2>Рилс 9:16 (44 с)</h2>
<video src="/reel.mp4" controls preload="metadata" style="max-width:360px;display:block"></video>
<a class="btn" href="/reel.mp4" download style="margin-top:10px">Скачать рилс</a>
<h2>Название, описание, теги</h2>
<pre>{html.escape(md)}</pre>
</div></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _file(self, path, ctype):
        if not os.path.exists(path):
            return self.send_error(404)
        size = os.path.getsize(path)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
            elif m.group(2):
                start = size - int(m.group(2))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            body = page().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif p == "/video.mp4":
            page(); self._file(VIDEO, "video/mp4")
        elif p == "/reel.mp4":
            self._file(os.path.join(ROOT, "reel_vokope.mp4"), "video/mp4")
        elif p == "/poster.jpg":
            self._file(os.path.join(ROOT, "video_studio/assets/smekalka_01.jpg"), "image/jpeg")
        else:
            self.send_error(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"serving on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
