#!/usr/bin/env python3
"""
Multi-threaded HTTP preview server for New_Video_bilder bound to 0.0.0.0:8080
with full RFC 7233 Byte-Range (206 Partial Content) support for instant 60fps MP4 scrubbing & MP3 voice auditioning.
"""
import mimetypes
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8080"))

mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("application/json", ".json")


class StudioRangeHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean in ("/", "/index.html"):
            return str(ROOT / "studio" / "index.html")
        rel = clean.lstrip("/")
        candidate = (ROOT / rel).resolve()
        if str(candidate).startswith(str(ROOT)):
            return str(candidate)
        return str(ROOT / "studio" / "index.html")

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None

        file_size = os.path.getsize(path)
        ctype = self.guess_type(path)
        range_header = self.headers.get("Range")

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else file_size - 1
                end = min(end, file_size - 1)
                if start <= end < file_size:
                    length = end - start + 1
                    f = open(path, "rb")
                    f.seek(start)
                    self.send_response(206)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    self._range_len = length
                    return f

        self._range_len = None
        f = open(path, "rb")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_len", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        buf_size = 65536
        while remaining > 0:
            chunk = source.read(min(buf_size, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StudioRangeHandler)
    print(f"New_Video_bilder Studio running on http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()
