#!/usr/bin/env python3
"""Live Preview: Full 02:28 1080p Film + 9:16 Vertical Reel + 36-Photo Gallery & MP3 Dropzone."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
PART3_DIR = HORDE_DIR / "mordor_svo_part3"
PART2_DIR = HORDE_DIR / "mordor_svo_part2"
MORDOR_DIR = HORDE_DIR / "mordor_svo_frames"
MODERN_DIR = HORDE_DIR / "modern_frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS_P3 = {
    "mordor_21_mouth_of_sauron_capitulation_elves.jpg": "21 · Глашатай Саурона («Уста Саурона») в форме СВО с триколором у «Тигра-М» принимает безоговорочную капитуляцию эльфов и знамён Гондора",
    "mordor_22_balrog_iskander_missile_launch.jpg": "22 · Закованный в броню с триколором БАЛРОГ Моргота и боевой пуск ОТРК «Искандер-М» с клыкастыми гоблинами и орками",
    "mordor_23_gothmog_general_grad_tornado_salvo.jpg": "23 · Генерал орков ГОТМОГ командует огненным залпом батареи РСЗО «Торнадо-Г» в «мангалах» по эльфийским бастионам",
    "mordor_24_lurtz_uruk_sniper_svd_thermal_pair.jpg": "24 · Вожак урук-хаев ЛУРТЦ с Белой Дланью на лице в «Кикиморе» с винтовкой Орсис Т-5000 + гоблин-корректировщик и варг",
    "mordor_25_shelob_spider_fiber_optic_ambush.jpg": "25 · Гигантская паучиха ШЕЛОБ с катушками оптоволокна («Паутина СВО») и гоблины-операторы FPV добивают колонну эльфов",
    "mordor_26_olog_hai_troll_sapper_ur77_zmej_gorynych.jpg": "26 · 4-метровый тролль Олог-хай с молотом и установка разминирования УР-77 «Змей Горыныч» рвут линию укреплений Белой Крепости",
    "mordor_27_khamul_nazgul_lancet_operator_dugout.jpg": "27 · Назгул Кхамул и расчёт орков/гоблинов: таран-перехват тяжёлого вражеского гексакоптера в небе над блиндажом",
    "mordor_28_corsairs_umbar_raptor_boat_amphibious_orcs.jpg": "28 · Речной десант Мордора на бронекатерах «Раптор» под Триколором и Оком Мордора несётся мимо руин Осгилиата",
    "mordor_29_troll_field_kitchen_kp130_izengardovka.jpg": "29 · Полевая кухня КП-130 в «НОВОЙ ИЗЕНГАРДОВКЕ»: Тролль-повар раздаёт горячую гречку с тушёнкой оркам и гоблинам, а варги грызут кости у Т-90М",
    "mordor_30_eye_of_barad_dur_reb_radar_fortress_finale.jpg": "30 · Финал: укреплённая крепость «НОВАЯ ИЗЕНГАРДОВКА» с башней Ока-РЛС, ЗРПК «Панцирь-С1», Триколором, Виверной и парой Су-34!",
}

CAPTIONS_P2 = {
    "mordor_11_sauron_command_bunker_streams.jpg": "11 · Саурон на КСП в блиндаже: в огромном плитнике «Мох» с триколором перед экранами FPV-трансляций вместе с урук-хаем и гоблином",
    "mordor_12_grond_jet_battering_ram_reb.jpg": "12 · Таран «ГРОНД» на базе Т-90 с волчьей пастью, «Накидкой», РЭБ и двумя 4-метровыми Боевыми Троллями крушит врата Минас-Тирита",
    "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg": "13 · ТОС-1А «Солнцепёк» в антидроновом «мангале» даёт термобарический залп: экипаж урук-хаев, гоблина и варгов",
    "mordor_14_uruk_hai_white_hand_enduro_assault.jpg": "14 · Мотоштурм Урук-хаев с отпечатком Белой Длани Сарумана на шлемах + стая варгов летят «по полям»",
    "mordor_15_fell_beast_umpk_fab_drop.jpg": "15 · Боевая Виверна Назгула в сбруе «Мох» сбрасывает крылатый ФАБ-500 с модулем УМПК в паре с Су-34 ВКС РФ",
    "mordor_16_goblin_sappers_ground_robot_kurier.jpg": "16 · Гоблины Мории и варг ведут гусеничный наземный дрон НРТК «Курьер» с АГС и ПТУР",
    "mordor_17_saruman_tactical_pantsir_air_defense.jpg": "17 · Саруман Белый в софтшелле «Мох» и плитнике с триколором командует расчётом ЗРПК «Панцирь-С1»",
    "mordor_18_warg_cavalry_pursuit_fleeing_elves.jpg": "18 · Кавалерия Наездников на Варгах в обвесе СВО гонит разбитых эльфов мимо горящей западной брони",
    "mordor_19_buhanka_svo_goblin_checkpoint_izengardovka.jpg": "19 · Фронтовая «Буханка» в «мангале» и РЭБ у знака «НОВАЯ ИЗЕНГАРДОВКА»: гоблин-механик, урук-хаи и боевой пёс-варг",
    "mordor_20_grand_parade_victory_novaya_izengardovka.jpg": "20 · Грандиозный Парад Победы Мордорской Братии: Саурон на Т-90М, Тролли, Олифант, Варги, Виверна и Ка-52М под Триколором!",
}

CAPTIONS_P1 = {
    "mordor_01_warg_riders_desertcross_charge.jpg": "01 · Кавалерия Наездников на Варгах в кевларе «Мох» + багги Desertcross Назгула рвут «по полям» на Минас-Тирит",
    "mordor_02_goblins_fiber_fpv_lancet_team.jpg": "02 · Гоблины Мории и Король-чародей в ВКПО 3.0 «Мох» запускают Х-крылый «Ланцет» и оптоволоконный FPV",
    "mordor_03_armored_cave_troll_kontakt1_breach.jpg": "03 · 4-метровый Боевой Тролль Мордора в плитнике с триколором и «мангалом» + Т-90М «Прорыв» проламывают Белые Врата",
    "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg": "04 · Боевой Олифант (Мумакил) в тепловой «Накидке» и огромном сварном «Царь-Мангале» с РЭБ и ПТУР идёт с варгами",
    "mordor_05_nazgul_fell_beast_ka52_airbase.jpg": "05 · Крылатая тварь Назгула в тактической сбруе «Мох» с триколором, урук-хаи и пара Ка-52М «Аллигатор»",
    "mordor_06_geran_swarm_goblin_techs_night.jpg": "06 · Вечерний залп чёрных «Гераней-2» с пикапов с купольным РЭБ: орки, гоблин с планшетом и боевой пёс-варг",
    "mordor_07_cqb_wargs_orcs_capture_elves.jpg": "07 · Зачистка Минас-Тирита: урук-хаи, гоблин и боевые псы-варги на поводках берут в плен эльфов в мультикаме",
    "mordor_08_novaya_izengardovka_warg_svo.jpg": "08 · Знак «НОВАЯ ИЗЕНГАРДОВКА»: боевой варг в жилете «Мох», Король-чародей, клыкастые орки и гоблин с шуруповёртом",
    "mordor_09_tricolor_mordor_flag_bare_orcs.jpg": "09 · Флаги Победы: клыкастые урук-хаи, гоблин и Король-чародей поднимают Триколор РФ и знамя Ока Мордора",
    "mordor_10_throne_hall_orc_goblin_warg_pack.jpg": "10 · Привал всей мордорской братии в Тронном Зале: назгулы, орки с АК-12, гоблины с FPV и верные боевые псы-варги",
}

CAPTIONS_MOD = {
    "modern_01_orc_storm_squad_vkpo_moss.jpg": "31 · Штурмовая четвёрка орков в ВКПО 3.0 «Мох», плитниках с напашниками, АК-12 с банками и рюкзаком РЭБ",
    "modern_02_desertcross_buggy_enduro_po_polyam.jpg": "32 · Штурмовой багги Desertcross с РЭБ и кроссовые эндуро-мотоциклы орков летят через распутицу",
    "modern_03_lancet_and_fiber_fpv_team.jpg": "33 · Расчёт «Ланцета» и оптоволоконного FPV-дрона с Королём-чародеем над долиной",
    "modern_04_geran_black_swarm_night_pickup.jpg": "34 · Пуск матово-чёрных «Гераней-2» с пикапов в сумерках",
    "modern_05_su34_umpk_glide_bombs_citadel.jpg": "35 · Су-34 сбрасывает ФАБы с УМПК по бастионам Белой Крепости под корректировку орков-разведчиков",
    "modern_06_t90m_proryv_nakidka_breach.jpg": "36 · Т-90М «Прорыв» со штурмовиками орков давит натовский броневик в проломе ворот",
}


class StudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
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

    def do_HEAD(self):
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path in ("/", "/index.html"):
            self.serve_index()
            return
        routes = {
            "/video/mordor_svo_2m28s.mp4": (OUTPUT_DIR / "mordor_svo_full_2m28s_1080p.mp4", "video/mp4", None),
            "/video/mordor_svo_reel.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", None),
            "/download/mordor_svo_full_2m28s_1080p.mp4": (OUTPUT_DIR / "mordor_svo_full_2m28s_1080p.mp4", "video/mp4", "mordor_svo_full_2m28s_1080p.mp4"),
            "/download/mordor_svo_reel_9x16.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", "mordor_svo_reel_9x16.mp4"),
            "/download/mordor_svo_master_36_frames.zip": (OUTPUT_DIR / "mordor_svo_master_36_frames.zip", "application/zip", "mordor_svo_master_36_frames.zip"),
            "/download/mordor_svo_part3_10_frames.zip": (OUTPUT_DIR / "mordor_svo_part3_10_frames.zip", "application/zip", "mordor_svo_part3_10_frames.zip"),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        for prefix, folder in (("/mp3f/", PART3_DIR), ("/mp2/", PART2_DIR), ("/msvo/", MORDOR_DIR), ("/mod/", MODERN_DIR)):
            if path.startswith(prefix):
                fpath = folder / os.path.basename(path)
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
            if not getattr(self, "_head_only", False):
                self.wfile.write(chunk)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(fpath.read_bytes())

    @staticmethod
    def build_cards(folder: Path, prefix: str, captions: dict[str, str]) -> str:
        out = []
        for f in sorted(folder.glob("*.jpg")):
            if f.name not in captions:
                continue
            cap = html.escape(captions[f.name])
            nm = html.escape(f.name)
            out.append(f"""
            <div class="card">
              <a href="{prefix}{nm}" target="_blank"><img src="{prefix}{nm}" loading="lazy" alt="{cap}"></a>
              <div class="meta"><span>{cap}</span><a class="dl-mini" href="{prefix}{nm}" download="{nm}">⬇ JPG</a></div>
            </div>""")
        return "".join(out)

    def serve_index(self):
        audio_files = [p.name for p in sorted(AUDIO_DIR.glob("*")) if p.is_file() and p.name != "latest_track.mp3"]
        audio_status = (
            f"✅ Трек в студии: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⏳ Закиньте сюда MP3 «АЗБУКА - ПО ПОЛЯМ», чтобы свести полный 02:28 клип прямо на оригинальный вокал!"
        )
        cards_p3 = self.build_cards(PART3_DIR, "/mp3f/", CAPTIONS_P3)
        cards_p2 = self.build_cards(PART2_DIR, "/mp2/", CAPTIONS_P2)
        cards_p1 = self.build_cards(MORDOR_DIR, "/msvo/", CAPTIONS_P1)
        cards_mod = self.build_cards(MODERN_DIR, "/mod/", CAPTIONS_MOD)

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>МОРДОР × СВО · ПОЛНЫЙ ФИЛЬМ 02:28 (36 КАДРОВ) + REEL 9:16 · НОВАЯ ИЗЕНГАРДОВКА</title>
<style>
  :root {{ --bg:#0e100d; --panel:#171b14; --border:#2d3627; --text:#eceae2; --muted:#9aa38e; --accent:#8fb352; --fire:#df7832; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:22px; background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,sans-serif; }}
  .wrap {{ max-width:1420px; margin:0 auto; }}
  header {{ display:flex; flex-wrap:wrap; gap:14px; align-items:center; justify-content:space-between; padding-bottom:16px; border-bottom:1px solid var(--border); }}
  h1 {{ margin:0; font-size:22px; }}
  h2 {{ margin:28px 0 14px; font-size:18px; color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:14px; margin-top:4px; }}
  .btns {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .btn {{ display:inline-flex; align-items:center; gap:8px; background:var(--accent); color:#10130c; font-weight:700; padding:11px 15px; border-radius:7px; text-decoration:none; border:none; cursor:pointer; font-size:14px; }}
  .btn.fire {{ background:var(--fire); color:#140b04; }}
  .players {{ display:grid; grid-template-columns:1fr 330px; gap:18px; margin:20px 0; align-items:start; }}
  @media (max-width:980px) {{ .players {{ grid-template-columns:1fr; }} }}
  .hero {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
  video {{ width:100%; display:block; background:#000; }}
  .hero-bar {{ padding:11px 15px; font-size:13px; color:var(--muted); }}
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
      <h1>🔥 МОРДОР × СВО · ПОЛНОМЕТРАЖНЫЙ КЛИП 02:28 (7 АКТОВ · 36 КАДРОВ · 1080p) + REEL 9:16</h1>
      <div class="sub">Саурон · Саруман · Балрог + «Искандер» · Шелоб с оптоволокном · Луртц · Готмог + «Торнадо-Г» · Уста Саурона · «Гронд» · Полевая кухня Тролля и Око-РЛС в Новой Изенгардовке!</div>
    </div>
    <div class="btns">
      <a class="btn fire" href="/download/mordor_svo_full_2m28s_1080p.mp4">🎬 Полный фильм 02:28 1080p (25.6 МБ)</a>
      <a class="btn fire" href="/download/mordor_svo_reel_9x16.mp4">📱 Вертикальный Reel 9:16 (9.4 МБ)</a>
      <a class="btn" href="/download/mordor_svo_master_36_frames.zip">📦 ВСЕ 36 кадров (ZIP · 9.7 МБ)</a>
      <a class="btn" href="/download/mordor_svo_part3_10_frames.zip">📦 Часть 3 — 10 новых кадров (2.5 МБ)</a>
    </div>
  </header>

  <div class="players">
    <div class="hero">
      <video controls autoplay loop playsinline src="/video/mordor_svo_2m28s.mp4"></video>
      <div class="hero-bar">▶ ПОЛНАЯ ВЕРСИЯ 16:9 (02:28.7 · 1920×1080 @ 30fps · 134 BPM): все 36 сцен Мордорской Братии от КСП Саурона до капитуляции эльфов и Ока-РЛС!</div>
    </div>
    <div class="hero">
      <video controls muted loop playsinline src="/video/mordor_svo_reel.mp4"></video>
      <div class="hero-bar">📱 SHORTS / REELS / VK CLIPS (9:16 · 1080×1920 · 28.7 сек)</div>
    </div>
  </div>

  <div class="dropzone">
    <div>
      <div style="font-weight:700;font-size:15px;">🎵 Загрузка трека «АЗБУКА — ПО ПОЛЯМ (.mp3)» (таймлайн 02:28 уже синхронизирован под 134 BPM!)</div>
      <div style="font-size:13px;color:#e0b252;margin-top:4px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Закинуть MP3 в студию</button>
    </div>
  </div>

  <h2>🔥 ЧАСТЬ 3 (НОВИНКА — Балрог + «Искандер», Шелоб с оптоволокном, Уста Саурона, Луртц, Готмог, УР-77, Полевая кухня Тролля и Око-РЛС — 10 кадров)</h2>
  <div class="grid">{cards_p3}</div>

  <h2>⚔️ ЧАСТЬ 2 — Саурон на КСП, Саруман на «Панцире», «ГРОНД», «Солнцепёк», Виверна с ФАБ-УМПК, «Буханка» и Парад Победы (10 кадров)</h2>
  <div class="grid">{cards_p2}</div>

  <h2>🐺 ЧАСТЬ 1 — Кавалерия Варгов, Гоблины, Боевой Тролль, Олифант в «Царь-Мангале», Назгулы (10 кадров)</h2>
  <div class="grid">{cards_p1}</div>

  <h2>⚡ Штурмовые группы Орков, Су-34 УМПК, Багги и Т-90М «Прорыв» (6 кадров)</h2>
  <div class="grid">{cards_mod}</div>
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
  if (data.ok) statusEl.textContent = '✅ Загружен: ' + data.filename + ' (' + data.size_mb + ' МБ)! Пишите в чат «продолжай» для сведения с оригиналом!';
}});
</script>
</body>
</html>"""
        payload = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(payload)


if __name__ == "__main__":
    os.chdir(ROOT)
    srv = HTTPServer(("0.0.0.0", 8000), StudioHandler)
    print("Serving Mordor SVO Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
