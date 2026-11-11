#!/usr/bin/env python3
"""Live Preview Screening Room: АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele) · 58-Shot ARRI Anamorphic Master Film & 9:16 Reel."""
import html
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
CIN_DIR = HORDE_DIR / "cinema_polam"
PART5_DIR = HORDE_DIR / "mordor_svo_part5_song"
PART4_DIR = HORDE_DIR / "mordor_svo_part4"
PART3_DIR = HORDE_DIR / "mordor_svo_part3"
PART2_DIR = HORDE_DIR / "mordor_svo_part2"
MORDOR_DIR = HORDE_DIR / "mordor_svo_frames"
MODERN_DIR = HORDE_DIR / "modern_frames"
SHORTS_DIR = HORDE_DIR / "shorts_9x16"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS_CINEMA = [
    ("cinema_01_intro_frozen_fingers_sticks.jpg", "00:00 · [INTRO] Макро: окоченевшие перебинтованные пальцы орка в инее на стиках заледеневшего пульта FPV"),
    ("polam_02_ork.png", "00:03 · [INTRO] Крупный анаморфотный портрет: орк с пластырем на скуле вызывает «птичку» по рации в мёрзлом окопе"),
    ("cinema_02_antenna_silhouette_snow_field.jpg", "00:06 · [INTRO] Одинокий силуэт орка с направленной антенной Яги посреди бескрайних зимних полей"),
    ("polam_04_fpv.png", "00:09 · [ПОДВОДКА] Вид от 1-го лица с камеры FPV-дрона (11.8V · RSSI 75) на бреющем над снежными крышами"),
    ("cinema_09_fpv_terminal_dive_white_keep.jpg", "00:11 · «Только БАМ!» — вертикальное терминальное пике FPV-дрона (11.1V) прямо в горящие мраморные врата"),
    ("cinema_04_bam_bam_howitzer_recoil_portrait.jpg", "00:12 · «БАМ, БАМ, БАМ!» — ударная волна и сноп огня 152-мм выстрела в лицо клыкастого артиллериста"),
    ("cinema_03_babki_blood_mud_gold_boot.jpg", "00:24 · «У тебя бабки, бабки, бабки — а у меня тут...» — пачки долларов и кубок эльфов под берцем урук-хая на фоне выстрела Т-90М"),
    ("polam_05_vesna.png", "00:30 · «Весна придёт — тяну к небу ладошки!» — орк в снегу тянет перебинтованную ладонь к капле талой воды с антенны над зелёным ростком"),
    ("cinema_05_vyshla_iz_lucha_goggles_reflection.jpg", "01:00 · «В моём мониторе тебя нету, и ты падала» — гоблин поднимает FPV-очки перед белым шумом «НЕТ СИГНАЛА»"),
    ("cinema_06_raznes_chastoty_soldering_dark.jpg", "01:03 · «Я разнёс частоты твои, чтобы ты не плакала» — пайка видеопередатчика под лучом налобного фонаря и зелёный спектр"),
    ("cinema_08_lost_bird_in_pine_hands.jpg", "01:49 · «Где-то потерялась и нужно тебя найти!» — клыкастый урук бережно снимает заснеженную FPV-птичку с живым огоньком с еловой ветки"),
    ("cinema_10_izengardovka_dawn_silence.jpg", "02:24 · [ФИНАЛ] Тихий рассвет после боя: уставший орк с верным варгом у знака «НОВАЯ ИЗЕНГАРДОВКА»"),
]

LYRIC_MAP = [
    ("00:00 – 00:12", "ИНТРО + ПОДВОДКА («Только бам!»)", "5 анаморфотных планов: иней на стиках пульта → орк с рацией → силуэт антенны в поле → заход FPV (11.8V) → вертикальное пике в горящие врата (11.1V)"),
    ("00:12 – 00:36", "ПРИПЕВ 1 (ДРОП 160 BPM)", "4 быстрых удара под «Бам-бам-бам-бам» (гаубица, Балрог+Искандер, Солнцепёк, взрыв Герани) → «Ищу сигнал антенной по полям» → доллары эльфов под берцем → «Дроны · Пушки · Танки» (1-2-3!) → «Весна придёт — тяну к небу ладошки»"),
    ("00:36 – 01:00", "КУПЛЕТ 1 · ЧАСТЬ А (Зима)", "«Руки околели от холодной зимы» (живой снегопад в окопе) → мастерская гоблинов → тепловизор Луртца → уход птички из луча («Вышла из луча»)"),
    ("01:00 – 01:12", "КУПЛЕТ 1 · ЧАСТЬ Б (Яма без баса)", "Крупный план гоблина у экрана «НЕТ СИГНАЛА» → пайка частот в тёмном блиндаже («Я разнёс частоты твои») → мачта антенны на «Буханке» по полям"),
    ("01:12 – 01:36", "ПРИПЕВ 2 (ВТОРОЙ ДРОП)", "Залп Готмога, Дрейк+Ту-22М3, ФАБ-500 УМПК с Виверны, УР-77 → марш Олифантов и кавалерии варгов по полям → бегство эльфов → Шелоб (дроны) · Азог на Терминаторе (пушки) · таран ГРОНД (танки) → эвакуация «Своих не бросаем»"),
    ("01:36 – 02:00", "КУПЛЕТ 2 («Лютый холод минус сорок»)", "Метель в ночном ельнике («Лес, лес, лес — холодно») → поиск пропавшего борта → бережное спасение заснеженной FPV-птички с еловой ветки!"),
    ("02:00 – 02:28.5", "ПРИПЕВ 3 + РАССВЕТ ПОБЕДЫ", "Ка-52М, Панцирь-С1 Сарумана и пролом Боевого Тролля → капитуляция эльфов перед Устами Саурона → Триколор РФ → баня с самоваром → тихий рассвет с варгом у знака «НОВАЯ ИЗЕНГАРДОВКА»"),
]


class StudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
            "/video/master.mp4": (OUTPUT_DIR / "azbuka_po_polyam_mordor_svo_master_1080p.mp4", "video/mp4", None),
            "/video/reel.mp4": (OUTPUT_DIR / "azbuka_po_polyam_shorts_native_9x16_1080p.mp4", "video/mp4", None),
            "/video/shorts_native.mp4": (OUTPUT_DIR / "azbuka_po_polyam_shorts_native_9x16_1080p.mp4", "video/mp4", None),
            "/download/azbuka_po_polyam_shorts_native_9x16_1080p.mp4": (
                OUTPUT_DIR / "azbuka_po_polyam_shorts_native_9x16_1080p.mp4", "video/mp4", "azbuka_po_polyam_shorts_native_9x16_1080p.mp4"
            ),
            "/download/azbuka_po_polyam_shorts_9x16_frames.zip": (
                OUTPUT_DIR / "azbuka_po_polyam_shorts_9x16_frames.zip", "application/zip", "azbuka_po_polyam_shorts_9x16_frames.zip"
            ),
            "/download/azbuka_po_polyam_mordor_svo_master_1080p.mp4": (
                OUTPUT_DIR / "azbuka_po_polyam_mordor_svo_master_1080p.mp4", "video/mp4", "azbuka_po_polyam_mordor_svo_master_1080p.mp4"
            ),
            "/download/azbuka_po_polyam_reel_9x16.mp4": (
                OUTPUT_DIR / "azbuka_po_polyam_reel_9x16.mp4", "video/mp4", "azbuka_po_polyam_reel_9x16.mp4"
            ),
            "/download/azbuka_po_polyam_12_cinema_frames.zip": (
                OUTPUT_DIR / "azbuka_po_polyam_12_cinema_frames.zip", "application/zip", "azbuka_po_polyam_12_cinema_frames.zip"
            ),
            "/download/azbuka_po_polyam_58_timecoded_frames.zip": (
                OUTPUT_DIR / "azbuka_po_polyam_58_timecoded_frames.zip", "application/zip", "azbuka_po_polyam_58_timecoded_frames.zip"
            ),
            "/download/medal_za_vzyatie_novoy_izengardovki.jpg": (
                OUTPUT_DIR / "medal_za_vzyatie_novoy_izengardovki.jpg", "image/jpeg", "medal_za_vzyatie_novoy_izengardovki.jpg"
            ),
            "/download/SOCIAL_MEDIA_PACK_NOVAYA_IZENGARDOVKA.md": (
                OUTPUT_DIR / "SOCIAL_MEDIA_PACK_NOVAYA_IZENGARDOVKA.md", "text/markdown; charset=utf-8", "SOCIAL_MEDIA_PACK_NOVAYA_IZENGARDOVKA.md"
            ),
            "/medal.jpg": (
                OUTPUT_DIR / "medal_za_vzyatie_novoy_izengardovki.jpg", "image/jpeg", None
            ),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        for prefix, folder in (
            ("/cin/", CIN_DIR), ("/mp5f/", PART5_DIR), ("/mp4f/", PART4_DIR),
            ("/mp3f/", PART3_DIR), ("/mp2/", PART2_DIR), ("/msvo/", MORDOR_DIR), ("/mod/", MODERN_DIR),
        ):
            if path.startswith(prefix):
                fpath = folder / os.path.basename(path)
                if fpath.is_file():
                    ctype = "image/png" if fpath.suffix.lower() == ".png" else "image/jpeg"
                    self.serve_range_file(fpath, ctype)
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

    def serve_index(self):
        cin_cards = []
        for fname, desc in CAPTIONS_CINEMA:
            if (CIN_DIR / fname).is_file():
                nm = html.escape(fname)
                cap = html.escape(desc)
                cin_cards.append(f"""
                <div class="card">
                  <a href="/cin/{nm}" target="_blank"><img src="/cin/{nm}" loading="lazy" alt="{cap}"></a>
                  <div class="meta"><span>{cap}</span><a class="dl-mini" href="/cin/{nm}" download="{nm}">⬇ ORIG</a></div>
                </div>""")

        rows = "".join(
            f"<tr><td class='tc'>{html.escape(tc)}</td><td class='sec'>{html.escape(sec)}</td><td>{html.escape(txt)}</td></tr>"
            for tc, sec, txt in LYRIC_MAP
        )

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>АЗБУКА — ПО ПОЛЯМ · КИНОКЛИП С ОРИГИНАЛЬНЫМ ТРЕКОМ (58 КАДРОВ · 1080p)</title>
<style>
  :root {{ --bg:#090C0F; --panel:#11161C; --border:#232D38; --text:#E8EEF4; --muted:#8E9EAD; --fire:#E07828; --ice:#6BA6CD; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:26px; background:var(--bg); color:var(--text); font-family:Inter,system-ui,-apple-system,sans-serif; }}
  .wrap {{ max-width:1440px; margin:0 auto; }}
  header {{ display:flex; flex-wrap:wrap; gap:18px; align-items:flex-end; justify-content:space-between; padding-bottom:20px; border-bottom:1px solid var(--border); }}
  h1 {{ margin:0; font-size:24px; letter-spacing:-0.02em; }}
  h2 {{ margin:32px 0 14px; font-size:17px; color:var(--fire); text-transform:uppercase; letter-spacing:0.04em; }}
  .sub {{ color:var(--muted); font-size:14px; margin-top:6px; max-width:860px; line-height:1.5; }}
  .btns {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .btn {{ display:inline-flex; align-items:center; gap:8px; background:var(--fire); color:#120802; font-weight:700; padding:11px 16px; border-radius:6px; text-decoration:none; font-size:13.5px; }}
  .btn.ice {{ background:var(--ice); color:#071018; }}
  .players {{ display:grid; grid-template-columns:1fr 330px; gap:20px; margin:22px 0; align-items:start; }}
  @media (max-width:980px) {{ .players {{ grid-template-columns:1fr; }} }}
  .hero {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  video {{ width:100%; display:block; background:#000; }}
  .hero-bar {{ padding:12px 16px; font-size:13px; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; font-size:13.5px; }}
  td {{ padding:11px 14px; border-bottom:1px solid var(--border); vertical-align:top; line-height:1.45; }}
  tr:last-child td {{ border-bottom:none; }}
  td.tc {{ white-space:nowrap; font-family:ui-monospace,monospace; color:var(--fire); font-weight:700; width:130px; }}
  td.sec {{ font-weight:700; width:240px; color:var(--ice); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(560px,1fr)); gap:16px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  .card img {{ width:100%; display:block; aspect-ratio:16/9; object-fit:cover; }}
  .meta {{ padding:11px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:13px; line-height:1.4; }}
  .dl-mini {{ color:var(--ice); text-decoration:none; font-weight:700; white-space:nowrap; padding:4px 9px; border:1px solid var(--border); border-radius:4px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>🎬 АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele) · 58 КАДРОВ ПОД ОРИГИНАЛЬНЫЙ ВОКАЛ</h1>
      <div class="sub">Сведено миллисекунда в миллисекунду с загруженным треком (02:28.52 · сетка 160.0 BPM, дропы на 0:12.04 / 1:12.05 / 2:00.05, яма на 1:00.05) · Единый киногрейдинг ARRI Alexa Mini LF (холодный сланец + тёплый вольфрам) · 0 людей, 0 старых касок, 0 повторов</div>
    </div>
    <div class="btns">
      <a class="btn" href="/download/azbuka_po_polyam_shorts_native_9x16_1080p.mp4">🔥 НОВЫЙ SHORTS 9:16 БЕЗ ОБРЕЗКИ (15.7 МБ)</a>
      <a class="btn ice" href="/download/azbuka_po_polyam_shorts_9x16_frames.zip">📦 10 нативных вертикальных кадров 9:16 (2.2 МБ)</a>
      <a class="btn" href="/download/azbuka_po_polyam_mordor_svo_master_1080p.mp4">⬇ Плавный Мастер-Клип 16:9 (20.9 МБ)</a>
      <a class="btn" href="/download/medal_za_vzyatie_novoy_izengardovki.jpg">🏅 Медаль «ЗА ВЗЯТИЕ НОВОЙ ИЗЕНГАРДОВКИ» (JPG)</a>
      <a class="btn ice" href="/download/azbuka_po_polyam_58_timecoded_frames.zip">📦 Все 58 кадров 16:9 (21.4 МБ)</a>
    </div>
  </header>

  <div class="players">
    <div class="hero">
      <video controls autoplay playsinline src="/video/master.mp4"></video>
      <div class="hero-bar">🔊 ПОЛНЫЙ МАСТЕР 16:9: «АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele)» · 58 строго уникальных сцен · 1920×1080 30fps</div>
    </div>
    <div class="hero">
      <video controls loop playsinline src="/video/shorts_native.mp4"></video>
      <div class="hero-bar">📱 НОВЫЙ ПОЛНОЦЕННЫЙ SHORTS 9:16 (1080×1920 · 100% нативные вертикальные кадры без кропа 16:9 · припев 01:11–01:36)</div>
    </div>
  </div>

  <h2>Карта синхронизации под вокал и биты трека (160.0 BPM · 02:28.52)</h2>
  <table>{rows}</table>

  <h2>12 флагманских анаморфотных кинокадров (ARRI Alexa Mini LF · единичный герой и метафора)</h2>
  <div class="grid">{''.join(cin_cards)}</div>
</div>
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
    print("Serving AZBUKA PO POLYAM Master Cinema Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
