#!/usr/bin/env python3
"""Live Preview, Photo Gallery & Audio Dropzone Server for HORDE / ПО ПОЛЯМ Studio."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
FRAMES_DIR = HORDE_DIR / "frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

SHOT_CAPTIONS = {
    "01_po_polyam_nazgul_column.jpg": "01 · «По полям» — Багги назгулов и Короля-чародея с миниганом во главе бронеколонны в осенней распутице",
    "02_orc_quad_nvg_recon_field.jpg": "02 · Разведгруппа Орды в GPNVG-18 готовит FPV-дрон на кромке туманного поля",
    "03_witch_king_tablet_briefing.jpg": "03 · Полевой штаб на капоте шишиги: Король-чародей показывает штурмовикам Орды карту Белой Цитадели на защищённом планшете",
    "04_fpv_swarm_over_white_citadel.jpg": "04 · Ударный БПЛА заходит над ярусами Белой Крепости людей и эльфов",
    "05_elven_trench_panic_under_barrage.jpg": "05 · Окопы эльфов в серебряных доспехах и плитниках под плотным прилётом",
    "06_orc_mlrs_salvo_across_fields.jpg": "06 · Залп тяжёлых огнемётных РСЗО Орды через раскисшее поле по башням твердыни",
    "07_btr_breaching_ancient_marble_gates.jpg": "07 · Штурмовой танк с козырьком и орочьим тараном проламывает мраморные врата крепости",
    "08_urban_citadel_arches_orc_advance.jpg": "08 · Бой в белых колоннадах: пулемётчик Орды работает с постамента рухнувшей статуи",
    "09_captured_ramparts_trophies.jpg": "09 · Затишье на взятых бастионах: сваленные щиты Белого Древа и трофейные шлемы эльфов",
    "10_horde_victory_atop_citadel.jpg": "10 · Победа Орды: знамя Железной Короны над покорённой Белой Цитаделью",
}


class StudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
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
            # Also keep canonical symlink/copy track.mp3
            (AUDIO_DIR / "latest_track.mp3").write_bytes(data)
            payload = json.dumps({
                "ok": True,
                "filename": safe_name,
                "size_mb": round(len(data) / 1e6, 2),
                "saved_to": str(dst.relative_to(ROOT)),
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
        if path.startswith("/frames/"):
            fname = os.path.basename(path)
            fpath = FRAMES_DIR / fname
            if fpath.is_file():
                self.serve_binary(fpath, "image/jpeg")
                return
        if path == "/download/horde_po_polyam_batch1_10_photos.zip":
            zpath = OUTPUT_DIR / "horde_po_polyam_batch1_10_photos.zip"
            if zpath.is_file():
                self.serve_binary(zpath, "application/zip", attachment=zpath.name)
                return
        super().do_GET()

    def serve_binary(self, fpath: Path, ctype: str, attachment: str | None = None):
        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(data)

    def serve_index(self):
        frames = sorted(FRAMES_DIR.glob("*.jpg"))
        audio_files = [p.name for p in sorted(AUDIO_DIR.glob("*")) if p.is_file() and p.name != "latest_track.mp3"]
        audio_status = (
            f"✅ Загружен в студию: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⏳ Ожидаем MP3-файл «АЗБУКА - ПО ПОЛЯМ (Prod. by scaryele).mp3» для пословной синхронизации и сборки клипа"
        )
        cards_html = []
        for f in frames:
            cap = html.escape(SHOT_CAPTIONS.get(f.name, f.name))
            cards_html.append(f"""
            <div class="card">
              <a href="/frames/{html.escape(f.name)}" target="_blank">
                <img src="/frames/{html.escape(f.name)}" loading="lazy" alt="{cap}">
              </a>
              <div class="meta">
                <span>{cap}</span>
                <a class="dl-mini" href="/frames/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a>
              </div>
            </div>
            """)

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ОРДА · ПО ПОЛЯМ — Студия кадров и клипа</title>
<style>
  :root {{
    --bg: #111310;
    --panel: #1a1d18;
    --border: #2e3429;
    --text: #e6e4dc;
    --muted: #9aa08e;
    --accent: #8ea865;
    --accent2: #c59b48;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{ max-width: 1360px; margin: 0 auto; }}
  header {{
    display: flex; flex-wrap: wrap; gap: 16px;
    align-items: center; justify-content: space-between;
    padding-bottom: 18px; border-bottom: 1px solid var(--border);
  }}
  h1 {{ margin: 0; font-size: 24px; letter-spacing: 0.03em; text-transform: uppercase; }}
  .sub {{ color: var(--muted); font-size: 14px; margin-top: 4px; }}
  .btn {{
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--accent); color: #10130d; font-weight: 700;
    padding: 11px 18px; border-radius: 6px; text-decoration: none;
    border: none; cursor: pointer; font-size: 14px;
  }}
  .btn.secondary {{ background: #282d23; color: var(--text); border: 1px solid var(--border); }}
  .dropzone {{
    margin: 20px 0 26px; padding: 20px;
    background: var(--panel); border: 2px dashed var(--accent);
    border-radius: 10px; display: flex; flex-wrap: wrap;
    align-items: center; justify-content: space-between; gap: 16px;
  }}
  .status {{ font-size: 14px; color: var(--accent2); margin-top: 6px; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(560px, 1fr));
    gap: 18px;
  }}
  @media (max-width: 680px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden;
  }}
  .card img {{ width: 100%; display: block; aspect-ratio: 1376/768; object-fit: cover; }}
  .meta {{
    padding: 11px 14px; display: flex; justify-content: space-between;
    align-items: center; gap: 12px; font-size: 13px; color: var(--text);
  }}
  .dl-mini {{
    color: var(--accent); text-decoration: none; font-weight: 600;
    white-space: nowrap; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px;
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>ОРДА · «ПО ПОЛЯМ» (Dark-Fantasy × 35mm War Reportage)</h1>
      <div class="sub">Первая партия: 10 широкоформатных кадров (1376×768, 35mm Portra 800 / Superia эстетика по правилам Anti-Slop Design Director v2.0)</div>
    </div>
    <div>
      <a class="btn" href="/download/horde_po_polyam_batch1_10_photos.zip">📦 Скачать все 10 фото (ZIP · 2.45 МБ)</a>
    </div>
  </header>

  <div class="dropzone" id="dropzone">
    <div>
      <div style="font-weight:700;font-size:16px;">🎵 Загрузка трека для пословного разбора и сборки клипа</div>
      <div class="status" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Загрузить трек (.mp3) в студию</button>
    </div>
  </div>

  <div class="grid">
    {''.join(cards_html)}
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
      statusEl.textContent = '✅ Трек загружен в студию: ' + data.filename + ' (' + data.size_mb + ' МБ)! Напишите в чат «готово», и я сразу запускаю сборку клипа.';
    }} else {{
      statusEl.textContent = '❌ Ошибка загрузки';
    }}
  }} catch (e) {{
    statusEl.textContent = '❌ Ошибка: ' + e;
  }}
}}
input.addEventListener('change', e => uploadFile(e.target.files[0]));
const dz = document.getElementById('dropzone');
dz.addEventListener('dragover', e => {{ e.preventDefault(); dz.style.borderColor = '#c59b48'; }});
dz.addEventListener('dragleave', () => {{ dz.style.borderColor = '#8ea865'; }});
dz.addEventListener('drop', e => {{
  e.preventDefault();
  dz.style.borderColor = '#8ea865';
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
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
    print("Serving Horde Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
