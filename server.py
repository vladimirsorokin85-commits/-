#!/usr/bin/env python3
"""Live Preview, Video Player, Photo Gallery & Audio Dropzone Server for HORDE / ПО ПОЛЯМ Studio."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
B2_DIR = HORDE_DIR / "batch2_frames"
B1_DIR = HORDE_DIR / "frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

B2_CAPTIONS = {
    "s01_buhanka_f1.jpg": "Анимация Буханки [Кадр 1/4] · УАЗ «Буханка» с мангалом и шипами Мордора заходит в грязевую воронку под ливнем и «Геранями»",
    "s02_buhanka_f2.jpg": "Анимация Буханки [Кадр 2/4] · Удар в лужу! Стена чернозёма, Король-чародей с АК-74М на синей изоленте, орк в шлемофоне и тельняшке за ПКМ",
    "s03_buhanka_f3.jpg": "Анимация Буханки [Кадр 3/4] · Выход из ямы в упор на камеру + очередь трассерами с крыши сквозь дождь и дизельный дым",
    "s04_buhanka_f4.jpg": "Анимация Буханки [Кадр 4/4] · Пролёт в метре от объектива в комьях грязи и чёрном выхлопе",
    "s05_geran_f1_launch.jpg": "Рой «Гераней» [Кадр 1/3] · Залп «Герани» с «Урала» у берёз в искрах ускорителя; орки в «Горках», тельняшках и «Алтынах» у кипящего самовара",
    "s06_geran_f2_swarm.jpg": "Рой «Гераней» [Кадр 2/3] · Семь дельтавидных «Гераней» пикируют сквозь грозовой ливень на Белую Цитадель эльфов и западную РЛС",
    "s07_geran_f3_strike.jpg": "Рой «Гераней» [Кадр 3/3] · Прямой прилёт! Огненный гриб и ударная волна сносят центральный шпиль и радар эльфийской крепости",
    "s08_tank_f1_charge.jpg": "Штурм Царь-Мангала [Кадр 1/2] · Т-90 в «Контакт-1» с бревном и шипастым «Царь-мангалом», десант в ушанках + боевой медведь в латах Мордора и Ка-52",
    "s09_tank_f2_blast.jpg": "Штурм Царь-Мангала [Кадр 2/2] · Залп 125-мм в упор с ударным кольцом в ливне и прыжок бронированного медведя на бегущих эльфов в мультикаме",
}


class StudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename, Range")
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/upload_audio"):
            length = int(self.headers.get("Content-Length", "0"))
            raw_name = unquote(self.headers.get("X-Filename", "track.mp3"))
            safe_name = re.sub(r"[^\w.\- ()а-яА-ЯёЁ]", "_", os.path.basename(raw_name)) or "track.mp3"
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            data = self.rfile.read(length)
            dst = AUDIO_DIR / safe_name
            dst.write_bytes(data)
            (AUDIO_DIR / "latest_track.mp3").write_bytes(data)
            payload = json.dumps({
                "ok": True,
                "filename": safe_name,
                "size_mb": round(len(data) / 1e6, 2),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path in ("/", "/index.html"):
            self.serve_index()
            return
        if path == "/video/horde_batch2_anim_vfx_1080p.mp4":
            vpath = OUTPUT_DIR / "horde_batch2_anim_vfx_1080p.mp4"
            if vpath.is_file():
                self.serve_range_file(vpath, "video/mp4")
                return
        if path == "/download/horde_batch2_anim_vfx_1080p.mp4":
            vpath = OUTPUT_DIR / "horde_batch2_anim_vfx_1080p.mp4"
            if vpath.is_file():
                self.serve_range_file(vpath, "video/mp4", attachment=vpath.name)
                return
        if path == "/download/horde_batch2_stereotypes_9_frames.zip":
            zpath = OUTPUT_DIR / "horde_batch2_stereotypes_9_frames.zip"
            if zpath.is_file():
                self.serve_range_file(zpath, "application/zip", attachment=zpath.name)
                return
        if path == "/download/horde_po_polyam_batch1_10_photos.zip":
            zpath = OUTPUT_DIR / "horde_po_polyam_batch1_10_photos.zip"
            if zpath.is_file():
                self.serve_range_file(zpath, "application/zip", attachment=zpath.name)
                return
        if path.startswith("/b2/"):
            fpath = B2_DIR / os.path.basename(path)
            if fpath.is_file():
                self.serve_range_file(fpath, "image/jpeg")
                return
        if path.startswith("/b1/"):
            fpath = B1_DIR / os.path.basename(path)
            if fpath.is_file():
                self.serve_range_file(fpath, "image/jpeg")
                return
        super().do_GET()

    def serve_range_file(self, fpath: Path, ctype: str, attachment: str | None = None):
        size = fpath.stat().st_size
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            parts = rng.replace("bytes=", "").split("-", 1)
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else size - 1
            end = min(end, size - 1)
            length = max(0, end - start + 1)
            with fpath.open("rb") as fp:
                fp.seek(start)
                chunk = fp.read(length)
            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(len(chunk)))
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(chunk)
            return

        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(data)

    def serve_index(self):
        b2_frames = sorted(B2_DIR.glob("*.jpg"))
        audio_files = [p.name for p in sorted(AUDIO_DIR.glob("*")) if p.is_file() and p.name != "latest_track.mp3"]
        audio_status = (
            f"✅ Трек в студии: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⏳ Скиньте сюда MP3 «АЗБУКА - ПО ПОЛЯМ (Prod. by scaryele).mp3», чтобы в следующем прогоне лечь прямо на вокал и слова!"
        )
        cards = []
        for f in b2_frames:
            cap = html.escape(B2_CAPTIONS.get(f.name, f.name))
            cards.append(f"""
            <div class="card">
              <a href="/b2/{html.escape(f.name)}" target="_blank">
                <img src="/b2/{html.escape(f.name)}" loading="lazy" alt="{cap}">
              </a>
              <div class="meta">
                <span>{cap}</span>
                <a class="dl-mini" href="/b2/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a>
              </div>
            </div>""")

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ОРДА · ПОКАДРОВАЯ АНИМАЦИЯ + VFX (Буханка, Герани, Царь-Мангал, Медведь)</title>
<style>
  :root {{
    --bg: #10120f; --panel: #191d16; --border: #2f3729;
    --text: #ece9e0; --muted: #9da491; --accent: #95b557; --fire: #e07c38;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 22px; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; }}
  .wrap {{ max-width: 1380px; margin: 0 auto; }}
  header {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between; padding-bottom: 16px; border-bottom: 1px solid var(--border); }}
  h1 {{ margin: 0; font-size: 23px; letter-spacing: 0.02em; }}
  .sub {{ color: var(--muted); font-size: 14px; margin-top: 4px; }}
  .btns {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .btn {{ display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: #10130c; font-weight: 700; padding: 11px 16px; border-radius: 7px; text-decoration: none; border: none; cursor: pointer; font-size: 14px; }}
  .btn.fire {{ background: var(--fire); color: #140b04; }}
  .hero {{ margin: 20px 0; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
  video {{ width: 100%; display: block; max-height: 74vh; background: #000; }}
  .hero-bar {{ padding: 12px 16px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; font-size: 14px; color: var(--muted); }}
  .dropzone {{ margin: 18px 0 24px; padding: 18px; background: var(--panel); border: 2px dashed var(--accent); border-radius: 10px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(560px, 1fr)); gap: 16px; }}
  @media (max-width: 680px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  .card img {{ width: 100%; display: block; aspect-ratio: 1376/768; object-fit: cover; }}
  .meta {{ padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 13px; }}
  .dl-mini {{ color: var(--accent); text-decoration: none; font-weight: 700; white-space: nowrap; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>🔥 ОРДА · ПОКАДРОВЫЙ ПРОГОН №2 (Буханка · Герани · Царь-Мангал · Боевой Медведь)</h1>
      <div class="sub">1080p @ 30fps · Optical-Flow движение техники + живой ливень, грязь, искры огня, дым и 134 BPM бит со звуком «мопеда» Герани</div>
    </div>
    <div class="btns">
      <a class="btn fire" href="/download/horde_batch2_anim_vfx_1080p.mp4">🎬 Скачать видео MP4 (9.9 МБ)</a>
      <a class="btn" href="/download/horde_batch2_stereotypes_9_frames.zip">📦 Скачать 9 кадров (ZIP · 2.5 МБ)</a>
    </div>
  </header>

  <div class="hero">
    <video controls autoplay loop playsinline src="/video/horde_batch2_anim_vfx_1080p.mp4"></video>
    <div class="hero-bar">
      <span>▶ Нажмите звук в плеере: 134 BPM фонк-марш + дизель «Буханки» по грязи + жужжание пикирующих «Гераней» + залп 125-мм Т-90</span>
      <a class="dl-mini" href="/download/horde_po_polyam_batch1_10_photos.zip">Архив Партии №1 (10 фото)</a>
    </div>
  </div>

  <div class="dropzone" id="dropzone">
    <div>
      <div style="font-weight:700;font-size:15px;">🎵 Загрузка оригинального трека «АЗБУКА — ПО ПОЛЯМ (.mp3)»</div>
      <div style="font-size:13px;color:#e0b252;margin-top:4px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Закинуть MP3 в студию</button>
    </div>
  </div>

  <div class="grid">
    {''.join(cards)}
  </div>
</div>
<script>
const input = document.getElementById('audioInput');
const statusEl = document.getElementById('uploadStatus');
async function uploadFile(file) {{
  if (!file) return;
  statusEl.textContent = '⏳ Загружаем ' + file.name + ' ...';
  try {{
    const res = await fetch('/upload_audio', {{
      method: 'POST',
      headers: {{ 'X-Filename': encodeURIComponent(file.name) }},
      body: file
    }});
    const data = await res.json();
    if (data.ok) {{
      statusEl.textContent = '✅ Загружен: ' + data.filename + ' (' + data.size_mb + ' МБ)! Напишите в чат «продолжай»!';
    }}
  }} catch (e) {{
    statusEl.textContent = '❌ Ошибка: ' + e;
  }}
}}
input.addEventListener('change', e => uploadFile(e.target.files[0]));
</script>
</body>
</html>"""
        payload = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    os.chdir(ROOT)
    srv = HTTPServer(("0.0.0.0", 8000), StudioHandler)
    print("Serving Horde Studio v2 on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
