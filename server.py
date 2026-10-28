#!/usr/bin/env python3
"""Cinema Preview Studio for «ПОСТ-РОССИЯ» — Full Synced Music Video (1080p30 + Audio) & Assets."""
from __future__ import annotations

import html
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
PR_DIR = ROOT / "video_studio" / "post_rossiya"
PR_OUT = PR_DIR / "output"

HQ_STREAM_CANDIDATES = (
    Path("/tmp/post_rossiya/post_rossiya_hq_1080p.mp4"),
    PR_OUT / "post_rossiya_master_1080p.mp4",
)
DOWNLOAD_CANDIDATES = (
    PR_OUT / "post_rossiya_master_1080p.mp4",
    Path("/tmp/post_rossiya/post_rossiya_hq_1080p.mp4"),
)
SILENT_CANDIDATES = (
    Path("/tmp/post_rossiya/post_rossiya_silent_hq_1080p.mp4"),
    PR_OUT / "post_rossiya_ready_1080p.mp4",
)
LEGACY_VIDEO = next(
    (Path(c) for c in (ROOT / "smekalka_video.mp4", "/tmp/smk4/smekalka_video.mp4") if Path(c).exists()),
    Path("/tmp/smk4/smekalka_video.mp4"),
)
REEL_CANDIDATES = (
    Path(os.environ.get("REEL_PATH", str(ROOT / "video_studio" / "reels" / "output" / "reel.mp4"))),
    Path("/tmp/reel/reel_final.mp4"),
    Path("/tmp/reel/reel.mp4"),
)


def pick_existing(paths) -> Path | None:
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None


def load_synced_timeline() -> list[dict]:
    p = PR_OUT / "synced_timeline_100.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("shots", [])
    p2 = PR_OUT / "prompts_100.json"
    if p2.exists():
        return json.loads(p2.read_text(encoding="utf-8")).get("shots", [])
    return []


def render_page() -> str:
    shots = load_synced_timeline()
    dl_vid = pick_existing(DOWNLOAD_CANDIDATES)
    dl_mb = dl_vid.stat().st_size / 1e6 if dl_vid else 0.0
    zip_f = PR_OUT / "post_rossiya_all_images_by_timecode.zip"
    zip_mb = zip_f.stat().st_size / 1e6 if zip_f.exists() else 0.0
    silent_vid = pick_existing(SILENT_CANDIDATES)

    cards = []
    for idx, s in enumerate(shots, 1):
        seq = s.get("seq", idx)
        code = s.get("display_code", f"{s['num']:03d}")
        rel_media = s["file"].replace("video_studio/post_rossiya/", "")
        m0, s0 = int(s["t0"] // 60), s["t0"] % 60
        cards.append(
            f'<div class="card" onclick="seekTo({s["t0"]})">'
            f'<img src="/media/{rel_media}" loading="lazy">'
            f'<div class="cap"><b>План {seq:03d} ({html.escape(code)})</b> · {m0}:{s0:05.2f}<br>'
            f'<span style="color:#8cb4c9">{html.escape(s["cue"])}</span><br>{html.escape(s["desc_ru"])}</div>'
            f'</div>'
        )

    shots_json = json.dumps([
        {
            "seq": s.get("seq", i + 1),
            "code": s.get("display_code", f"{s['num']:03d}"),
            "t0": s["t0"],
            "t1": s["t1"],
            "act": s["act"],
            "cue": s["cue"],
            "desc": s["desc_ru"],
            "color": s["color_state"],
            "move": s["move"],
        }
        for i, s in enumerate(shots)
    ], ensure_ascii=False)

    silent_btn = (
        '<a class="btn" href="/post_rossiya_silent.mp4" download="ПОСТ-РОССИЯ_немая_видеодорожка_1080p.mp4">'
        '🔇 Скачать немую видеодорожку (без звука)</a>'
        if silent_vid else ""
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ПОСТ-РОССИЯ — Готовый клип со звуком (1080p)</title>
<style>
:root {{
  --bg: #0b0d0e;
  --panel: #131719;
  --border: #232a2e;
  --text: #e3e7ea;
  --muted: #8b969e;
  --accent: #b84a46;
  --cold: #7a98ad;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.45;
}}
.wrap {{ max-width: 1260px; margin: 0 auto; padding: 24px 20px 64px; }}
h1 {{ margin: 0 0 4px; font-size: 28px; letter-spacing: 0.06em; font-weight: 700; }}
.sub {{ color: var(--muted); font-size: 14px; margin-bottom: 18px; }}
.bar-box {{
  background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: 14px 16px; margin-bottom: 18px;
}}
.bar-top {{ display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; font-size: 13.5px; margin-bottom: 8px; }}
.bar-track {{ height: 8px; background: #1c2226; border-radius: 99px; overflow: hidden; }}
.bar-fill {{ height: 100%; width: 100%; background: linear-gradient(90deg, #4b7f64, #78b894); }}
.tabs {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
button.tab, a.btn, label.btn {{
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 14px; border-radius: 8px; font-size: 13.5px; font-weight: 500;
  background: var(--panel); color: var(--text); border: 1px solid var(--border);
  cursor: pointer; text-decoration: none; transition: border-color .15s, background .15s;
}}
button.tab.active, a.btn.primary {{ background: #232d33; border-color: var(--cold); }}
button.tab:hover, a.btn:hover, label.btn:hover {{ border-color: #546672; }}
video {{
  width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 10px;
  border: 1px solid var(--border); display: block;
}}
.monitor {{
  margin-top: 10px; padding: 13px 16px; border-radius: 10px;
  background: var(--panel); border: 1px solid var(--border);
  display: grid; grid-template-columns: 96px 1fr auto; gap: 14px; align-items: center;
}}
.tc {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 21px; font-weight: 700; color: #fff; }}
.cue-act {{ font-size: 11.5px; letter-spacing: 0.08em; color: var(--cold); text-transform: uppercase; }}
.cue-desc {{ font-size: 15px; font-weight: 600; margin: 2px 0; }}
.cue-lyric {{ font-size: 13px; color: #c7d5de; font-style: italic; }}
.badge {{ font-size: 12px; padding: 4px 9px; border-radius: 6px; white-space: nowrap; background: rgba(76,145,105,.18); color: #8cd9ab; border: 1px solid rgba(76,145,105,.4); }}
.actions {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 16px 0 28px; }}
h2 {{ font-size: 18px; margin: 28px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 7px; }}
.grid4 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(265px, 1fr)); gap: 12px; }}
.card {{
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; cursor: pointer; transition: transform .12s, border-color .12s;
}}
.card:hover {{ transform: translateY(-2px); border-color: var(--cold); }}
.card img {{ width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; }}
.card .cap {{ padding: 8px 10px; font-size: 12px; color: var(--muted); }}
.card .cap b {{ color: var(--text); }}
.specimen {{ width: 100%; border-radius: 10px; border: 1px solid var(--border); display: block; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>«ПОСТ-РОССИЯ»</h1>
  <div class="sub">Готовый клип с оригинальной песней · Хронометраж: 02:37.56 · Темп синхронизации: 85.66 BPM · 1920×1080 @ 30 fps</div>

  <div class="bar-box">
    <div class="bar-top">
      <div><b>Готовность проекта: 100%</b> (104/104 кадров · 100 монтажных планов синхронизированы по тактам и строкам песни)</div>
      <div style="color:#8cd9ab"><b>Аудиодорожка вшита:</b> Пост-Россия.mp3 (48 кГц AAC 256 кбит/с)</div>
    </div>
    <div class="bar-track"><div class="bar-fill"></div></div>
  </div>

  <video id="vid" src="/post_rossiya_master.mp4" controls preload="metadata" poster="/media/refs/ref_04_color.jpg"></video>

  <div class="monitor">
    <div class="tc" id="tcBox">0:00.0</div>
    <div>
      <div class="cue-act" id="cueAct">ПРОЛОГ · ХОЛОДНЫЙ РАССВЕТ · dirty_modern</div>
      <div class="cue-desc" id="cueDesc">План 001 (001) — Смартфон в темноте на старом кухонном столе</div>
      <div class="cue-lyric" id="cueLyric">0:00–0:02.8 · Вступление из темноты</div>
    </div>
    <div class="badge" id="cueBadge">🎵 Синхрон с песней · 85.66 BPM</div>
  </div>

  <div class="actions">
    <a class="btn primary" style="background:#1f4d36;border-color:#3a8f63" href="/download/post_rossiya_reel_chorus.mp4" download="VES_Post_Rossiya_REEL_CHORUS_1080x1920.mp4">📱 Скачать Рилс с припевом 9:16 (MP4 1080×1920, 17.7 МБ)</a>
    <a class="btn primary" href="/reel_frames.zip" download="VES_Post_Rossiya_REEL_10_vertical_frames.zip">📦 10 вертикальных кадров Рилса (ZIP)</a>
    <a class="btn primary" href="/post_rossiya_download.mp4" download="ПОСТ-РОССИЯ_клип_со_звуком_1080p.mp4">🎬 Полный клип 16:9 со звуком ({dl_mb:.1f} МБ)</a>
    <a class="btn" href="/covers.zip" download="VES_Post_Rossiya_10_covers.zip">🖼 10 обложек 16:9 (ZIP)</a>
    <a class="btn" href="/post_rossiya_images.zip" download="ПОСТ-РОССИЯ_все_104_кадра_по_папкам_с_таймкодами.zip">📦 Все 104 кадра клипа ({zip_mb:.1f} МБ)</a>
  </div>

  <h2>📱 Отдельный вертикальный Рилс / Shorts 9:16 — Только Припев (0:45.6, 1080×1920, 10 новых кадров)</h2>
  <div style="display:flex;justify-content:center;margin:14px 0 24px">
    <video src="/reel_chorus.mp4" controls preload="metadata" poster="/media/reel_chorus/frames/reel_05.jpg" style="max-width:360px;aspect-ratio:9/16"></video>
  </div>

  <h2>0. Десять вариантов обложки «VES - Пост-Россия» (без людей, кликните для скачивания оригинала)</h2>
  <div class="grid4">
    <a class="card" href="/media/covers/cover_01_sea_horizon.jpg" download><img src="/media/covers/cover_01_sea_horizon.jpg"><div class="cap"><b>01 · Холодное море и рассвет</b></div></a>
    <a class="card" href="/media/covers/cover_02_panel_window.jpg" download><img src="/media/covers/cover_02_panel_window.jpg"><div class="cap"><b>02 · Панельный дом и одно окно</b></div></a>
    <a class="card" href="/media/covers/cover_03_red_flowers_rain.jpg" download><img src="/media/covers/cover_03_red_flowers_rain.jpg"><div class="cap"><b>03 · Гвоздики в дождевой луже</b></div></a>
    <a class="card" href="/media/covers/cover_04_field_mist_crows.jpg" download><img src="/media/covers/cover_04_field_mist_crows.jpg"><div class="cap"><b>04 · Осеннее поле и вороны</b></div></a>
    <a class="card" href="/media/covers/cover_05_rusty_swing.jpg" download><img src="/media/covers/cover_05_rusty_swing.jpg"><div class="cap"><b>05 · Пустые ржавые качели</b></div></a>
    <a class="card" href="/media/covers/cover_06_elektrichka_dawn.jpg" download><img src="/media/covers/cover_06_elektrichka_dawn.jpg"><div class="cap"><b>06 · Пустой вагон электрички</b></div></a>
    <a class="card" href="/media/covers/cover_07_crows_wires_chimneys.jpg" download><img src="/media/covers/cover_07_crows_wires_chimneys.jpg"><div class="cap"><b>07 · Птицы на проводах и трубы</b></div></a>
    <a class="card" href="/media/covers/cover_08_night_kitchen_phone.jpg" download><img src="/media/covers/cover_08_night_kitchen_phone.jpg"><div class="cap"><b>08 · Ночная кухня и экран телефона</b></div></a>
    <a class="card" href="/media/covers/cover_09_bus_stop_highway.jpg" download><img src="/media/covers/cover_09_bus_stop_highway.jpg"><div class="cap"><b>09 · Остановка у туманной трассы</b></div></a>
    <a class="card" href="/media/covers/cover_10_black_water_mirror.jpg" download><img src="/media/covers/cover_10_black_water_mirror.jpg"><div class="cap"><b>10 · Треснувшее зеркало и чёрная вода</b></div></a>
  </div>

  <h2>1. Четыре визуальных эталона (единая вселенная фильма)</h2>
  <div class="grid4">
    <div class="card"><img src="/media/refs/ref_01_hero.jpg"><div class="cap"><b>Эталон 1 · Главный герой</b><br>Мужчина 35 лет, тёмная куртка, серый свитер</div></div>
    <div class="card"><img src="/media/refs/ref_02_city.jpg"><div class="cap"><b>Эталон 2 · Главная локация</b><br>Постсоветский город поздней осенью, панельки, гаражи</div></div>
    <div class="card"><img src="/media/refs/ref_03_choir.jpg"><div class="cap"><b>Эталон 3 · Народный хор</b><br>30 женщин разного возраста в обычных пальто и платках</div></div>
    <div class="card"><img src="/media/refs/ref_04_color.jpg"><div class="cap"><b>Эталон 4 · Цветовой камертон</b><br>Искусственный цветок в решётке ливнёвки на рассвете</div></div>
  </div>

  <h2>2. Цветовая драматургия (киноплёночные .cube LUT из репозитория)</h2>
  <img class="specimen" src="/specimen_grades.jpg" alt="4 цветовых состояния клипа">

  <h2>3. Полная монтажная лента под песню (100 планов, 0:00.00 – 2:37.56) — кликните для перехода</h2>
  <div class="grid4">
    {''.join(cards)}
  </div>
</div>

<script>
const SHOTS = {shots_json};
const vid = document.getElementById('vid');
const tcBox = document.getElementById('tcBox');
const cueAct = document.getElementById('cueAct');
const cueDesc = document.getElementById('cueDesc');
const cueLyric = document.getElementById('cueLyric');

function fmtTime(t) {{
  const m = Math.floor(t / 60);
  const s = (t % 60).toFixed(1).padStart(4, '0');
  return `${{m}}:${{s}}`;
}}

function updateCue() {{
  const t = vid.currentTime || 0;
  tcBox.textContent = fmtTime(t);
  let cur = SHOTS[SHOTS.length - 1];
  for (const s of SHOTS) {{
    if (t >= s.t0 && t < s.t1) {{ cur = s; break; }}
  }}
  if (!cur) return;
  cueAct.textContent = `${{cur.act}} · цвет: ${{cur.color}} · камера: ${{cur.move}}`;
  cueDesc.textContent = `План ${{String(cur.seq).padStart(3, '0')}} (${{cur.code}}) — ${{cur.desc}}`;
  cueLyric.textContent = cur.cue;
}}

vid.addEventListener('timeupdate', updateCue);
vid.addEventListener('seeked', updateCue);

function seekTo(sec) {{
  vid.currentTime = sec;
  vid.play().catch(()=>{{}});
}}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _serve_file(self, path: Path | None, ctype: str, download_name: str | None = None):
        if path is None or not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and not download_name and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
            elif m.group(2):
                start = max(0, size - int(m.group(2)))
            if start > end or start >= size:
                self.send_error(416)
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
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
        p = unquote(self.path.split("?", 1)[0])
        if p in ("/", "/index.html"):
            body = render_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif p == "/reel_chorus.mp4":
            self._serve_file(PR_OUT / "post_rossiya_reel_chorus_1080x1920.mp4", "video/mp4")
        elif p == "/download/post_rossiya_reel_chorus.mp4":
            self._serve_file(PR_OUT / "post_rossiya_reel_chorus_1080x1920.mp4", "application/octet-stream", "VES_Post_Rossiya_REEL_CHORUS_1080x1920.mp4")
        elif p == "/reel_frames.zip":
            self._serve_file(PR_OUT / "post_rossiya_reel_10_vertical_frames.zip", "application/octet-stream", "VES_Post_Rossiya_REEL_10_vertical_frames.zip")
        elif p == "/covers.zip":
            self._serve_file(PR_OUT / "VES_Post_Rossiya_10_covers.zip", "application/octet-stream", "VES_Post_Rossiya_10_covers.zip")
        elif p == "/post_rossiya_images.zip":
            self._serve_file(PR_OUT / "post_rossiya_all_images_by_timecode.zip", "application/octet-stream", "POST_ROSSIYA_104_frames_timecoded.zip")
        elif p == "/post_rossiya_master.mp4":
            self._serve_file(pick_existing(HQ_STREAM_CANDIDATES), "video/mp4")
        elif p in ("/post_rossiya_download.mp4", "/download/post_rossiya_1080p.mp4"):
            self._serve_file(pick_existing(DOWNLOAD_CANDIDATES), "application/octet-stream", "POST_ROSSIYA_1080p_with_song.mp4")
        elif p in ("/post_rossiya_hq_download.mp4", "/download/post_rossiya_hq_1080p.mp4"):
            self._serve_file(pick_existing(HQ_STREAM_CANDIDATES), "application/octet-stream", "POST_ROSSIYA_MASTER_HQ_1080p.mp4")
        elif p in ("/post_rossiya_silent.mp4", "/download/post_rossiya_silent_1080p.mp4"):
            self._serve_file(pick_existing(SILENT_CANDIDATES), "application/octet-stream", "POST_ROSSIYA_silent_1080p.mp4")
        elif p == "/synced_timecodes.md":
            self._serve_file(PR_OUT / "ТАЙМКОДЫ_ПОД_ПЕСНЮ.md", "text/markdown; charset=utf-8")
        elif p == "/specimen_grades.jpg":
            self._serve_file(PR_OUT / "specimen_post_rossiya_grades.jpg", "image/jpeg")
        elif p == "/prompts_100.json":
            self._serve_file(PR_OUT / "synced_timeline_100.json", "application/json; charset=utf-8")
        elif p == "/STORYBOARD_PROMPTS.md":
            self._serve_file(PR_DIR / "STORYBOARD_PROMPTS.md", "text/markdown; charset=utf-8")
        elif p.startswith("/media/"):
            rel = p[len("/media/"):]
            cand = (PR_DIR / rel).resolve()
            if str(cand).startswith(str(PR_DIR.resolve())) and cand.suffix.lower() in (".jpg", ".jpeg", ".png"):
                self._serve_file(cand, "image/jpeg")
            else:
                self.send_error(404)
        elif p == "/video.mp4":
            self._serve_file(LEGACY_VIDEO, "video/mp4")
        elif p == "/reel.mp4":
            self._serve_file(pick_existing(REEL_CANDIDATES), "video/mp4")
        else:
            self.send_error(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"serving «ПОСТ-РОССИЯ» studio on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
