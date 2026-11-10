#!/usr/bin/env python3
"""Live Preview, Video Player, Gallery & Audio Dropzone for MORDOR × MODERN SVO Studio."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
MORDOR_DIR = HORDE_DIR / "mordor_svo_frames"
MODERN_DIR = HORDE_DIR / "modern_frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS = {
    "mordor_01_warg_riders_desertcross_charge.jpg": "01 · Кавалерия Наездников на Варгах в кевларе «Мох» с триколором + багги Desertcross Назгула рвут «по полям» на Минас-Тирит",
    "mordor_02_goblins_fiber_fpv_lancet_team.jpg": "02 · Гоблины Мории и Король-чародей в ВКПО 3.0 «Мох» запускают Х-крылый «Ланцет» и оптоволоконный FPV",
    "mordor_03_armored_cave_troll_kontakt1_breach.jpg": "03 · 4-метровый Боевой Тролль Мордора в гигантском плитнике с триколором и «мангалом» на голове + Т-90М «Прорыв» проламывают Белые Врата",
    "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg": "04 · Боевой Олифант (Мумакил) в тепловой «Накидке» и огромном сварном «Царь-Мангале» с РЭБ, ПТУР и триколором идёт с варгами по полю",
    "mordor_05_nazgul_fell_beast_ka52_airbase.jpg": "05 · Крылатая тварь Назгула в тактической сбруе «Мох» с триколором, урук-хаи и пара Ка-52М «Аллигатор»",
    "mordor_06_geran_swarm_goblin_techs_night.jpg": "06 · Вечерний залп чёрных «Гераней-2» с пикапов с купольным РЭБ: орки, гоблин с планшетом и боевой пёс-варг",
    "mordor_07_cqb_wargs_orcs_capture_elves.jpg": "07 · Зачистка Минас-Тирита: урук-хаи, гоблин и боевые псы-варги на поводках берут в плен эльфов в мультикаме",
    "mordor_08_novaya_izengardovka_warg_svo.jpg": "08 · Знак «НОВАЯ ИЗЕНГАРДОВКА»: боевой варг в жилете «Мох», Король-чародей в плитнике, клыкастые орки и гоблин с шуруповёртом на плече!",
    "mordor_09_tricolor_mordor_flag_bare_orcs.jpg": "09 · Победа над Минас-Тиритом: клыкастые урук-хаи, гоблин и Король-чародей (без балаклав!) поднимают Триколор РФ и знамя Ока Мордора под пролёт виверны и Ка-52М",
    "mordor_10_throne_hall_orc_goblin_warg_pack.jpg": "10 · Привал всей мордорской братии в Тронном Зале: назгулы, орки с АК-12, гоблины с FPV и верные боевые псы-варги",
    "modern_01_orc_storm_squad_vkpo_moss.jpg": "11 · Штурмовая четвёрка орков в ВКПО 3.0 «Мох», плитниках с напашниками, АК-12 с банками и рюкзаком РЭБ",
    "modern_02_desertcross_buggy_enduro_po_polyam.jpg": "12 · Штурмовой багги Desertcross с РЭБ и кроссовые эндуро-мотоциклы орков летят через распутицу",
    "modern_03_lancet_and_fiber_fpv_team.jpg": "13 · Расчёт «Ланцета» и оптоволоконного FPV-дрона с Королём-чародеем над долиной",
    "modern_04_geran_black_swarm_night_pickup.jpg": "14 · Пуск матово-чёрных «Гераней-2» с пикапов в сумерках",
    "modern_05_su34_umpk_glide_bombs_citadel.jpg": "15 · Су-34 сбрасывает ФАБы с УМПК по бастионам Белой Крепости под корректировку орков-разведчиков",
    "modern_06_t90m_proryv_nakidka_breach.jpg": "16 · Т-90М «Прорыв» со штурмовиками орков давит натовский броневик в проломе ворот",
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
            "/video/mordor_svo.mp4": (OUTPUT_DIR / "mordor_svo_victory_1080p.mp4", "video/mp4", None),
            "/download/mordor_svo_victory_1080p.mp4": (OUTPUT_DIR / "mordor_svo_victory_1080p.mp4", "video/mp4", "mordor_svo_victory_1080p.mp4"),
            "/download/mordor_svo_complete_16_frames.zip": (OUTPUT_DIR / "mordor_svo_complete_16_frames.zip", "application/zip", "mordor_svo_complete_16_frames.zip"),
            "/download/mordor_svo_10_new_frames.zip": (OUTPUT_DIR / "mordor_svo_10_new_frames.zip", "application/zip", "mordor_svo_10_new_frames.zip"),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        if path.startswith("/msvo/"):
            fpath = MORDOR_DIR / os.path.basename(path)
            if fpath.is_file():
                self.serve_range_file(fpath, "image/jpeg")
                return
        if path.startswith("/mod/"):
            fpath = MODERN_DIR / os.path.basename(path)
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
            else "⏳ Скиньте сюда MP3 «АЗБУКА - ПО ПОЛЯМ», чтобы свести полный клип прямо на вокал!"
        )
        cards_m = []
        for f in sorted(MORDOR_DIR.glob("*.jpg")):
            cap = html.escape(CAPTIONS.get(f.name, f.name))
            cards_m.append(f"""
            <div class="card">
              <a href="/msvo/{html.escape(f.name)}" target="_blank"><img src="/msvo/{html.escape(f.name)}" loading="lazy" alt="{cap}"></a>
              <div class="meta"><span>{cap}</span><a class="dl-mini" href="/msvo/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a></div>
            </div>""")
        cards_o = []
        for f in sorted(MODERN_DIR.glob("*.jpg")):
            if f.name in CAPTIONS:
                cap = html.escape(CAPTIONS[f.name])
                cards_o.append(f"""
                <div class="card">
                  <a href="/mod/{html.escape(f.name)}" target="_blank"><img src="/mod/{html.escape(f.name)}" loading="lazy" alt="{cap}"></a>
                  <div class="meta"><span>{cap}</span><a class="dl-mini" href="/mod/{html.escape(f.name)}" download="{html.escape(f.name)}">⬇ JPG</a></div>
                </div>""")

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>МОРДОР СВО · НОВАЯ ИЗЕНГАРДОВКА (Варги, Гоблины, Орки, Тролль, Олифант, Виверна)</title>
<style>
  :root {{ --bg:#0e100d; --panel:#171b14; --border:#2d3627; --text:#eceae2; --muted:#9aa38e; --accent:#8fb352; --fire:#df7832; }}
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
  .hero-bar {{ padding:12px 16px; font-size:13px; color:var(--muted); }}
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
      <h1>🔥 МОРДОР × СВО · «НОВАЯ ИЗЕНГАРДОВКА» (1080p @ 30fps · 37.6 сек)</h1>
      <div class="sub">ВКПО 3.0 «Мох» · Плитники с напашниками · Наездники на Варгах · Гоблины с оптоволокном и «Ланцетом» · Боевой Тролль · Олифант в «Царь-Мангале» · Виверна и Ка-52М</div>
    </div>
    <div class="btns">
      <a class="btn fire" href="/download/mordor_svo_victory_1080p.mp4">🎬 Скачать видео 1080p MP4 (19.1 МБ)</a>
      <a class="btn" href="/download/mordor_svo_complete_16_frames.zip">📦 Скачать ВСЕ 16 кадров (ZIP · 4.3 МБ)</a>
      <a class="btn" href="/download/mordor_svo_10_new_frames.zip">📦 Новые 10 кадров с Варгами/Троллем (2.6 МБ)</a>
    </div>
  </header>

  <div class="hero">
    <video controls autoplay loop playsinline src="/video/mordor_svo.mp4"></video>
    <div class="hero-bar">▶ Включите звук: 134 BPM боевой фонк + рык варгов + «Герани» + прилёт УМПК + пулемёт Боевого Тролля + Триколор и Око Мордора над Новой Изенгардовкой!</div>
  </div>

  <div class="dropzone">
    <div>
      <div style="font-weight:700;font-size:15px;">🎵 Загрузка трека «АЗБУКА — ПО ПОЛЯМ (.mp3)»</div>
      <div style="font-size:13px;color:#e0b252;margin-top:4px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Закинуть MP3 в студию</button>
    </div>
  </div>

  <h2>🐺 Вся Мордорская Братия в обвесе СВО (Варги, Гоблины, Тролль, Олифант, Виверна, Назгулы — 10 кадров)</h2>
  <div class="grid">{''.join(cards_m)}</div>

  <h2>⚡ Штурмовые группы Орков, Су-34 УМПК, Багги и Т-90М «Прорыв» (6 кадров)</h2>
  <div class="grid">{''.join(cards_o)}</div>
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
    print("Serving Mordor SVO Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
