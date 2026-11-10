#!/usr/bin/env python3
"""Live Preview, Full Campaign Video Player, Gallery & Audio Dropzone for HORDE Studio."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
B3_DIR = HORDE_DIR / "batch3_frames"
B2_DIR = HORDE_DIR / "batch2_frames"
B1_DIR = HORDE_DIR / "frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS = {
    "s10_solntsepek_f1_aim.jpg": "Солнцепёк [Кадр 1/3] · ТОС-1А в «Контакт-1» с бревном и шипами наводится у берёз; орки в ватниках и шлемофонах рядом с тушёнкой и подстаканником",
    "s11_solntsepek_f2_salvo1.jpg": "Солнцепёк [Кадр 2/3] · Сход первых термобарических ракет в снопе пламени и искр!",
    "s12_solntsepek_f3_salvo_full.jpg": "Солнцепёк [Кадр 3/3] · Полный пакет уходит в ливень — огненные шары накрывают стены Белой Цитадели",
    "s13_ural_f1_enter.jpg": "Мотоцикл «Урал» [Кадр 1/3] · Оливковый «Урал» с коляской, красным ковром, назгулом, ушанкой и балалайкой врывается в мраморную галерею дворца",
    "s14_ural_f2_drift.jpg": "Мотоцикл «Урал» [Кадр 2/3] · Дрифт по мокрой брусчатке в веере брызг и искр!",
    "s15_ural_f3_flyby.jpg": "Мотоцикл «Урал» [Кадр 3/3] · Пролёт в двух метрах от объектива с комьями грязи на линзе!",
    "s17_victory_f1_banner.jpg": "Победа [Кадр 1/3] · Т-90 «Царь-Мангал» на парадной мраморной лестнице эльфов над грудой щитов + Ка-52 и чёрное знамя Мордора",
    "s18_victory_f2_samovar_feast.jpg": "Застолье Орды [Кадр 2/3] · Ковёр, самовар с сапогом, банка огурцов, чёрный хлеб, тушёнка, подстаканник у Короля-чародея, гармонь, балалайка и медведь",
    "s19_victory_f3_toast_anim.jpg": "Застолье Орды [Кадр 3/3] · Анимация тоста: Король-чародей поднимает подстаканник, гармонь рвёт меха, сапог взлетает на пару, медведь ревёт!",
    "s01_buhanka_f1.jpg": "Буханка [Кадр 1/4] · УАЗ «Буханка» с мангалом и шипами заходит в грязевую воронку под «Геранями»",
    "s02_buhanka_f2.jpg": "Буханка [Кадр 2/4] · Удар в чернозёмную лужу, Король-чародей с АК на синей изоленте, орк в тельняшке за ПКМ",
    "s03_buhanka_f3.jpg": "Буханка [Кадр 3/4] · Выход из ямы в упор + трассеры с крыши",
    "s04_buhanka_f4.jpg": "Буханка [Кадр 4/4] · Пролёт мимо камеры в грязи и выхлопе",
    "s05_geran_f1_launch.jpg": "Герани [Кадр 1/3] · Старт «Герани» с «Урала» у берёз рядом с кипящим самоваром",
    "s06_geran_f2_swarm.jpg": "Герани [Кадр 2/3] · Рой из 7 «Гераней» пикирует на Белую Цитадель",
    "s07_geran_f3_strike.jpg": "Герани [Кадр 3/3] · Огненный гриб и ударная волна сносят шпиль и западный радар",
    "s08_tank_f1_charge.jpg": "Царь-Мангал [Кадр 1/2] · Т-90 с боевым медведем в латах Мордора и Ка-52",
    "s09_tank_f2_blast.jpg": "Царь-Мангал [Кадр 2/2] · Залп 125-мм в упор и прыжок бронированного медведя",
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
            payload = json.dumps({"ok": True, "filename": safe_name, "size_mb": round(len(data) / 1e6, 2)}).encode("utf-8")
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
        routes = {
            "/video/full.mp4": (OUTPUT_DIR / "horde_full_campaign_18frames_vfx_1080p.mp4", "video/mp4", None),
            "/download/horde_full_campaign_18frames_vfx_1080p.mp4": (OUTPUT_DIR / "horde_full_campaign_18frames_vfx_1080p.mp4", "video/mp4", "horde_full_campaign_18frames_vfx_1080p.mp4"),
            "/download/horde_all_28_photos_pack.zip": (OUTPUT_DIR / "horde_all_28_photos_pack.zip", "application/zip", "horde_all_28_photos_pack.zip"),
            "/download/horde_batch3_9_frames.zip": (OUTPUT_DIR / "horde_batch3_9_frames.zip", "application/zip", "horde_batch3_9_frames.zip"),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        if path.startswith("/b3/"):
            fpath = B3_DIR / os.path.basename(path)
            if fpath.is_file():
                self.serve_range_file(fpath, "image/jpeg")
                return
        if path.startswith("/b2/"):
            fpath = B2_DIR / os.path.basename(path)
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
            end = min(int(parts[1]) if parts[1] else size - 1, size - 1)
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
        audio_files = [p.name for p in sorted(AUDIO_DIR.glob("*")) if p.is_file() and p.name != "latest_track.mp3"]
        audio_status = (
            f"✅ Трек в студии: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⏳ При желании закиньте сюда MP3 «АЗБУКА - ПО ПОЛЯМ», чтобы наложить оригинальный вокал прямо поверх нашего видеоряда!"
        )
        cards_b3 = []
        for f in sorted(B3_DIR.glob("*.jpg")):
            cap = html.escape(CAPTIONS.get(f.name, f.name))
            cards_b3.append(f"""
            <div class="card">
              <a href="/b3/{html.escape(f.name)}" target="_blank"><img src="/b3/{html.escape(f.name)}" loading="lazy" alt="{cap}"></a>
              <div class="meta"><span>{cap}</span><a class="dl-mini" href="/b3/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a></div>
            </div>""")
        cards_b2 = []
        for f in sorted(B2_DIR.glob("*.jpg")):
            cap = html.escape(CAPTIONS.get(f.name, f.name))
            cards_b2.append(f"""
            <div class="card">
              <a href="/b2/{html.escape(f.name)}" target="_blank"><img src="/b2/{html.escape(f.name)}" loading="lazy" alt="{cap}"></a>
              <div class="meta"><span>{cap}</span><a class="dl-mini" href="/b2/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a></div>
            </div>""")

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ОРДА · ПОЛНЫЙ ПРОГОН КАМПАНИИ (18 кадров · 6 сцен · 1080p VFX)</title>
<style>
  :root {{ --bg:#10120f; --panel:#191d16; --border:#2f3729; --text:#ece9e0; --muted:#9da491; --accent:#95b557; --fire:#e07c38; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:22px; background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,sans-serif; }}
  .wrap {{ max-width:1380px; margin:0 auto; }}
  header {{ display:flex; flex-wrap:wrap; gap:14px; align-items:center; justify-content:space-between; padding-bottom:16px; border-bottom:1px solid var(--border); }}
  h1 {{ margin:0; font-size:22px; }}
  h2 {{ margin:28px 0 14px; font-size:18px; color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:14px; margin-top:4px; }}
  .btns {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .btn {{ display:inline-flex; align-items:center; gap:8px; background:var(--accent); color:#10130c; font-weight:700; padding:11px 16px; border-radius:7px; text-decoration:none; border:none; cursor:pointer; font-size:14px; }}
  .btn.fire {{ background:var(--fire); color:#140b04; }}
  .hero {{ margin:20px 0; background:var(--panel); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
  video {{ width:100%; display:block; max-height:74vh; background:#000; }}
  .hero-bar {{ padding:12px 16px; display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:12px; font-size:13px; color:var(--muted); }}
  .dropzone {{ margin:18px 0 24px; padding:18px; background:var(--panel); border:2px dashed var(--accent); border-radius:10px; display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(560px,1fr)); gap:16px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  .card img {{ width:100%; display:block; aspect-ratio:1376/768; object-fit:cover; }}
  .meta {{ padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:13px; }}
  .dl-mini {{ color:var(--accent); text-decoration:none; font-weight:700; white-space:nowrap; padding:4px 8px; border:1px solid var(--border); border-radius:4px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>🔥 ОРДА · ПОЛНЫЙ БОЕВОЙ ФИЛЬМ (32.2 сек · 18 связанных стоп-моушен кадров · 1080p VFX)</h1>
      <div class="sub">Буханка → Герани → ТОС «Солнцепёк» → Т-90 «Царь-Мангал» + Медведь → Урал с ковром → Самовар, огурцы, гармонь и балалайка!</div>
    </div>
    <div class="btns">
      <a class="btn fire" href="/download/horde_full_campaign_18frames_vfx_1080p.mp4">🎬 Скачать полный фильм MP4 (16.5 МБ)</a>
      <a class="btn" href="/download/horde_all_28_photos_pack.zip">📦 Скачать ВСЕ 28 фото (ZIP · 7.5 МБ)</a>
      <a class="btn" href="/download/horde_batch3_9_frames.zip">📦 Новые 9 фото Партии №3 (2.6 МБ)</a>
    </div>
  </header>

  <div class="hero">
    <video controls autoplay loop playsinline src="/video/full.mp4"></video>
    <div class="hero-bar">
      <span>▶ Включите звук: 134 BPM фонк + «мопед» Герани + залп пакета «Солнцепёка» + оппозит «Урала» + в финале народный фонк с гармонью, балалайкой и рёвом медведя!</span>
    </div>
  </div>

  <div class="dropzone">
    <div>
      <div style="font-weight:700;font-size:15px;">🎵 Загрузка трека «АЗБУКА — ПО ПОЛЯМ (.mp3)»</div>
      <div style="font-size:13px;color:#e0b252;margin-top:4px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Загрузить MP3 в студию</button>
    </div>
  </div>

  <h2>🆕 Партия №3 — Солнцепёк, Мотоцикл «Урал» с ковром и Победное Застолье с Самоваром (9 кадров)</h2>
  <div class="grid">{''.join(cards_b3)}</div>

  <h2>⚡ Партия №2 — Буханка, Рой «Гераней» и Т-90 «Царь-Мангал» с Медведем (9 кадров)</h2>
  <div class="grid">{''.join(cards_b2)}</div>
</div>
<script>
const input = document.getElementById('audioInput');
const statusEl = document.getElementById('uploadStatus');
input.addEventListener('change', async e => {{
  const file = e.target.files[0];
  if (!file) return;
  statusEl.textContent = '⏳ Загружаем ' + file.name + ' ...';
  const res = await fetch('/upload_audio', {{ method:'POST', headers:{{'X-Filename':encodeURIComponent(file.name)}}, body:file }});
  const data = await res.json();
  if (data.ok) statusEl.textContent = '✅ Загружен: ' + data.filename + ' (' + data.size_mb + ' МБ)! Пишите в чат «продолжай»!';
}});
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
    print("Serving Horde Full Campaign Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
