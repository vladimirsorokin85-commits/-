#!/usr/bin/env python3
"""Live Preview: 51-Unique-Shot 100%-Audited Clean Lyric Film (02:28 1080p) + 9:16 Reel + Instant MP3 Muxer."""
import html
import json
import os
import re
import shutil
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
PART5_DIR = HORDE_DIR / "mordor_svo_part5_song"
PART4_DIR = HORDE_DIR / "mordor_svo_part4"
PART3_DIR = HORDE_DIR / "mordor_svo_part3"
PART2_DIR = HORDE_DIR / "mordor_svo_part2"
MORDOR_DIR = HORDE_DIR / "mordor_svo_frames"
MODERN_DIR = HORDE_DIR / "modern_frames"
B2_DIR = HORDE_DIR / "batch2_frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS_P5 = {
    "mordor_41_antenna_po_polyam_orc_goblin_signal.jpg": "41 · «А я ищу твой сигнал антенной, по полям!» — урук-хай с направленной антенной, гоблин в FPV-очках и пёс-варг",
    "mordor_42_elves_babki_dollars_nato_luxury.jpg": "42 · «У тебя бабки, бабки, бабки...» — самонадеянные эльфы в мультикаме считают пачки долларов, пока в окно летят чёрные «Герани»!",
    "mordor_43_cold_winter_hands_orc_frozen_trench.jpg": "43 · «Руки околели от холодной зимы...» — индевевший орк и гоблин в зимнем ВКПО греют дыханием замёрзшие пальцы в снежном окопе",
    "mordor_44_no_signal_monitor_vyshla_iz_lucha.jpg": "44 · «В моём мониторе тебя нету, и ты падала...» — гоблин и урук у монитора «НЕТ СИГНАЛА / ПОТЕРЯ СВЯЗИ» при уходе птички из луча",
    "mordor_45_frequency_hopping_spectrum_orc_ew.jpg": "45 · «Я разнёс частоты твои, чтобы ты не плакала!» — Король-чародей и гоблины-связисты перестраивают спектр частот РЭБ",
    "mordor_46_minus_forty_snow_forest_search_wargs.jpg": "46 · «Этот лютый холод, минус сорок — лес, лес, лес... нужно тебя найти!» — уруки, гоблин и варги находят дрон в снежной чаще",
    "mordor_47_bird_rescued_orc_hugs_fpv_snow.jpg": "47 · «А я всё люблю тебя, ищу где потерял!» — клыкастый урук бережно прижимает спасённую FPV-птичку, а гоблин чистит объектив",
    "mordor_48_buhanka_snow_antenna_mast_po_polyam.jpg": "48 · «А я всё вожу этой антенной по полям» — фронтовая «Буханка» с мачтой ретранслятора, гоблином на крыше и уруками у «НОВОЙ ИЗЕНГАРДОВКИ»",
    "mordor_49_spring_comes_orc_palms_to_sky.jpg": "49 · «Весна придёт — тяну к небу ладошки!» — орк и гоблин тянут ладошки к тёплому весеннему солнцу среди цветущих яблонь под пролёт Су-34!",
    "mordor_50_spring_victory_citadel_radar_eye_clean.jpg": "50 · Весенний Финал без единого человека: крепость «НОВАЯ ИЗЕНГАРДОВКА», Око-РЛС, «Панцирь», Саурон, Тролль, урук, гоблины и варги!",
}

CAPTIONS_P4 = {
    "mordor_31_azog_pale_orc_bmpt_terminator_assault.jpg": "31 · Бледный орк АЗОГ с белыми варгами и пушки БМПТ «Терминатор-2» («А у меня тут дроны, пушки, танки!»)",
    "mordor_32_witch_king_ka52_alligator_vihr_strike.jpg": "32 · Король-чародей на Виверне и пара Ка-52М «Аллигатор» бьют «Вихрями» по полям",
    "mordor_33_goblin_fpv_workshop_dugout_soldering.jpg": "33 · Блиндажная мастерская: гоблины Мории и орк паяют FPV-птички и мотают оптоволокно",
    "mordor_34_smaug_drake_tu95_kh101_strategic_launch.jpg": "34 · Огненный Дрейк Мордора в сбруе с триколором взлетает на форсаже в паре с Ту-22М3 ВКС РФ",
    "mordor_35_black_numenorean_2s19_msta_s_krasnopol.jpg": "35 · САУ 2С19М2 «Мста-С» в «Накидке» и «мангале»: залп урук-хаев и назгула («Только бам!»)",
    "mordor_36_orc_medevac_armored_linza_warg_medic.jpg": "36 · Бронеавтомобиль «Линза»: зелёный гоблин-военврач перевязывает урук-хая с АК-12 рядом с псом-варгом",
    "mordor_37_haradrim_oliphaunt_column_po_polyam_march.jpg": "37 · Великий марш «По полям»: Олифанты в «Царь-Мангалах», Т-90М, «Буханки» и кавалерия варгов",
    "mordor_39_orc_banya_samovar_harmony_izengardovka.jpg": "39 · «Всё будет хорошо, плохое в прошлом»: баня, кипящий самовар на шишках и гармонь после взятия Цитадели",
}

CAPTIONS_P3 = {
    "mordor_21_mouth_of_sauron_capitulation_elves.jpg": "21 · Глашатай Саурона («Уста Саурона») у «Тигра-М» принимает безоговорочную капитуляцию эльфов",
    "mordor_22_balrog_iskander_missile_launch.jpg": "22 · «Только БАМ!» — закованный в броню с триколором БАЛРОГ и боевой пуск ОТРК «Искандер-М»",
    "mordor_23_gothmog_general_grad_tornado_salvo.jpg": "23 · Генерал орков ГОТМОГ командует залпом батареи РСЗО «Торнадо-Г»",
    "mordor_24_lurtz_uruk_sniper_svd_thermal_pair.jpg": "24 · Снайпер ЛУРТЦ с Белой Дланью в «Кикиморе» с винтовкой Орсис Т-5000 + гоблин и варг",
    "mordor_25_shelob_spider_fiber_optic_ambush.jpg": "25 · Гигантская паучиха ШЕЛОБ с катушками оптоволокна — связь без помех!",
    "mordor_26_olog_hai_troll_sapper_ur77_zmej_gorynych.jpg": "26 · 4-метровый тролль Олог-хай и УР-77 «Змей Горыныч» взрывают укрепления эльфов",
    "mordor_28_corsairs_umbar_raptor_boat_amphibious_orcs.jpg": "28 · Речной десант орков и варгов на бронекатерах «Раптор» мимо Осгилиата",
}

CAPTIONS_P2 = {
    "mordor_11_sauron_command_bunker_streams.jpg": "11 · Саурон на КСП в блиндаже перед экранами FPV-трансляций вместе с урук-хаями и гоблином",
    "mordor_12_grond_jet_battering_ram_reb.jpg": "12 · Таран «ГРОНД» на базе Т-90 с волчьей пастью, РЭБ и Боевыми Троллями ломает врата",
    "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg": "13 · ТОС-1А «Солнцепёк» даёт термобарический залп: урук-хаи, гоблин и варги",
    "mordor_14_uruk_hai_white_hand_enduro_assault.jpg": "14 · Мотоштурм Урук-хаев Белой Длани на кроссовых эндуро со стаей варгов",
    "mordor_15_fell_beast_umpk_fab_drop.jpg": "15 · Боевая Виверна Назгула сбрасывает крылатый ФАБ-500 с УМПК в паре с Су-34",
    "mordor_16_goblin_sappers_ground_robot_kurier.jpg": "16 · Гоблины Мории и варг ведут боевой наземный дрон НРТК «Курьер»",
    "mordor_17_saruman_tactical_pantsir_air_defense.jpg": "17 · Саруман в «Мохе» и плитнике с триколором командует огнём ЗРПК «Панцирь-С1»",
    "mordor_18_warg_cavalry_pursuit_fleeing_elves.jpg": "18 · Кавалерия Наездников на Варгах гонит разбитых эльфов мимо брошенной натовской техники",
    "mordor_20_grand_parade_victory_novaya_izengardovka.jpg": "20 · Торжественный Парад Победы всей Мордорской Братии в «НОВОЙ ИЗЕНГАРДОВКЕ»",
}

CAPTIONS_P1 = {
    "mordor_01_warg_riders_desertcross_charge.jpg": "01 · Кавалерия Наездников на Варгах + багги Desertcross Назгула рвут «по полям»",
    "mordor_02_goblins_fiber_fpv_lancet_team.jpg": "02 · «ДРОНЫ»: Гоблины Мории и Король-чародей запускают «Ланцет» и FPV",
    "mordor_03_armored_cave_troll_kontakt1_breach.jpg": "03 · 4-метровый Боевой Тролль в плитнике с триколором + Т-90М «Прорыв» врываются в ворота",
    "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg": "04 · Боевой Олифант (Мумакил) в «Накидке» и «Царь-Мангале» с РЭБ и варгами",
    "mordor_05_nazgul_fell_beast_ka52_airbase.jpg": "05 · Крылатая Виверна Назгула с триколором, клыкастые урук-хаи и пара Ка-52М",
    "mordor_06_geran_swarm_goblin_techs_night.jpg": "06 · Вечерний залп чёрных «Гераней-2» с пикапов с РЭБ: урук-хаи, гоблин и варг",
    "mordor_07_cqb_wargs_orcs_capture_elves.jpg": "07 · Зачистка Белой Крепости: урук-хаи, гоблин и боевые варги берут в плен эльфов",
    "mordor_08_novaya_izengardovka_warg_svo.jpg": "08 · Гоблин с шуруповёртом на плече орка вешает знак «НОВАЯ ИЗЕНГАРДОВКА»",
    "mordor_09_tricolor_mordor_flag_bare_orcs.jpg": "09 · Клыкастые орки, гоблин и Король-чародей поднимают Триколор РФ и знамя Мордора",
}

CAPTIONS_CLEAN_MOD = [
    (MODERN_DIR, "/mod/", "modern_01_orc_storm_squad_vkpo_moss.jpg", "Штурмовая четвёрка орков в ВКПО 3.0 «Мох» с АК-12 и рюкзаком РЭБ"),
    (MODERN_DIR, "/mod/", "modern_02_desertcross_buggy_enduro_po_polyam.jpg", "Багги Desertcross и кроссовые эндуро орков летят через поля"),
    (MODERN_DIR, "/mod/", "modern_03_lancet_and_fiber_fpv_team.jpg", "Расчёт «Ланцета» и оптоволоконного FPV с Королём-чародеем"),
    (MODERN_DIR, "/mod/", "modern_04_geran_black_swarm_night_pickup.jpg", "Ночной залп матово-чёрных «Гераней-2» с пикапов"),
    (MODERN_DIR, "/mod/", "modern_06_t90m_proryv_nakidka_breach.jpg", "«ТАНКИ»: Т-90М «Прорыв» с десантом орков давит западный броневик"),
    (MODERN_DIR, "/mod/", "modern_08_novaya_izengardovka_sign_svo.jpg", "Король-чародей, клыкастые орки и Т-90М у знака «НОВАЯ ИЗЕНГАРДОВКА»"),
    (B2_DIR, "/b2/", "s06_geran_f2_swarm.jpg", "Рой чёрных «Гераней-2» пикирует сквозь облака на башни цитадели"),
    (B2_DIR, "/b2/", "s07_geran_f3_strike.jpg", "Прямое попадание «Гераней» в верхний ярус Белой Крепости"),
]


def find_ffmpeg() -> str:
    if os.path.exists("/usr/local/bin/ffmpeg"):
        return "/usr/local/bin/ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def instant_mux_mp3(mp3_path: Path) -> tuple[bool, str]:
    """Losslessly copy 1080p & 9:16 H.264 video streams and mux real MP3 vocal track in ~1.5s!"""
    ff = find_ffmpeg()
    targets = [
        (OUTPUT_DIR / "mordor_svo_clean_51shots_2m28s_1080p.mp4", "160k"),
        (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "160k"),
    ]
    for mp4, abr in targets:
        if not mp4.is_file():
            continue
        tmp_out = mp4.with_suffix(".muxing.mp4")
        cmd = [
            ff, "-y",
            "-i", str(mp4),
            "-i", str(mp3_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", abr,
            "-movflags", "+faststart",
            "-shortest", str(tmp_out),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if res.returncode != 0:
            return False, res.stderr[-400:]
        shutil.move(str(tmp_out), str(mp4))
    return True, "Оба видео (16:9 1080p и 9:16 Reel) мгновенно сведены с оригинальным вокалом MP3!"


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
            raw_name = unquote(self.headers.get("X-Filename", "azbuka_po_polyam.mp3"))
            safe_name = re.sub(r"[^\w.\- ()а-яА-ЯёЁ]", "_", os.path.basename(raw_name)) or "azbuka_po_polyam.mp3"
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            data = self.rfile.read(length)
            dst = AUDIO_DIR / safe_name
            dst.write_bytes(data)
            latest = AUDIO_DIR / "latest_track.mp3"
            latest.write_bytes(data)
            mux_ok, mux_msg = instant_mux_mp3(latest)
            payload = json.dumps({
                "ok": True,
                "muxed": mux_ok,
                "message": mux_msg,
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
            "/video/mordor_svo_clean51.mp4": (OUTPUT_DIR / "mordor_svo_clean_51shots_2m28s_1080p.mp4", "video/mp4", None),
            "/video/mordor_svo_reel.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", None),
            "/download/mordor_svo_clean_51shots_2m28s_1080p.mp4": (OUTPUT_DIR / "mordor_svo_clean_51shots_2m28s_1080p.mp4", "video/mp4", "mordor_svo_clean_51shots_2m28s_1080p.mp4"),
            "/download/mordor_svo_reel_9x16.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", "mordor_svo_reel_9x16.mp4"),
            "/download/mordor_svo_clean_51_frames.zip": (OUTPUT_DIR / "mordor_svo_clean_51_frames.zip", "application/zip", "mordor_svo_clean_51_frames.zip"),
            "/download/mordor_svo_song_10_frames.zip": (OUTPUT_DIR / "mordor_svo_song_10_frames.zip", "application/zip", "mordor_svo_song_10_frames.zip"),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        for prefix, folder in (
            ("/mp5f/", PART5_DIR), ("/mp4f/", PART4_DIR), ("/mp3f/", PART3_DIR),
            ("/mp2/", PART2_DIR), ("/msvo/", MORDOR_DIR), ("/mod/", MODERN_DIR), ("/b2/", B2_DIR),
        ):
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
            f"✅ Оригинальный вокал уже вшит в оба клипа: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⚡ Перетащите сюда файл АЗБУКА - ПО ПОЛЯМ.mp3 (или нажмите кнопку справа) — за 2 секунды он автоматически вошьётся в оба видео без потери качества!"
        )
        cards_p5 = self.build_cards(PART5_DIR, "/mp5f/", CAPTIONS_P5)
        cards_p4 = self.build_cards(PART4_DIR, "/mp4f/", CAPTIONS_P4)
        cards_p3 = self.build_cards(PART3_DIR, "/mp3f/", CAPTIONS_P3)
        cards_p2 = self.build_cards(PART2_DIR, "/mp2/", CAPTIONS_P2)
        cards_p1 = self.build_cards(MORDOR_DIR, "/msvo/", CAPTIONS_P1)
        cards_ex = []
        for folder, pref, fname, text in CAPTIONS_CLEAN_MOD:
            if (folder / fname).is_file():
                cap = html.escape(text)
                nm = html.escape(fname)
                cards_ex.append(f"""
                <div class="card">
                  <a href="{pref}{nm}" target="_blank"><img src="{pref}{nm}" loading="lazy" alt="{cap}"></a>
                  <div class="meta"><span>{cap}</span><a class="dl-mini" href="{pref}{nm}" download="{nm}">⬇ JPG</a></div>
                </div>""")

        page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>АЗБУКА — ПО ПОЛЯМ · 51 ЧИСТЫЙ КАДР (МОРДОР × СВО · 02:28 · 1080p)</title>
<style>
  :root {{ --bg:#0B0D0A; --panel:#141812; --border:#273022; --text:#EDEBE4; --muted:#97A08B; --accent:#A4CC52; --fire:#E07A35; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--text); font-family:Inter,system-ui,-apple-system,sans-serif; }}
  .wrap {{ max-width:1420px; margin:0 auto; }}
  header {{ display:flex; flex-wrap:wrap; gap:16px; align-items:center; justify-content:space-between; padding-bottom:18px; border-bottom:1px solid var(--border); }}
  h1 {{ margin:0; font-size:22px; letter-spacing:-0.02em; }}
  h2 {{ margin:30px 0 14px; font-size:17px; color:var(--accent); letter-spacing:-0.01em; }}
  .sub {{ color:var(--muted); font-size:13.5px; margin-top:5px; line-height:1.45; }}
  .btns {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .btn {{ display:inline-flex; align-items:center; gap:8px; background:var(--accent); color:#0D1009; font-weight:700; padding:11px 15px; border-radius:7px; text-decoration:none; border:none; cursor:pointer; font-size:13.5px; }}
  .btn.fire {{ background:var(--fire); color:#160B03; }}
  .btn.ghost {{ background:transparent; color:var(--accent); border:1px solid var(--accent); }}
  .players {{ display:grid; grid-template-columns:1fr 330px; gap:18px; margin:20px 0; align-items:start; }}
  @media (max-width:980px) {{ .players {{ grid-template-columns:1fr; }} }}
  .hero {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
  video {{ width:100%; display:block; background:#000; }}
  .hero-bar {{ padding:11px 15px; font-size:13px; color:var(--muted); }}
  .dropzone {{ margin:18px 0 26px; padding:18px 20px; background:var(--panel); border:2px dashed var(--accent); border-radius:10px; display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:14px; transition:background 150ms ease; }}
  .dropzone.drag {{ background:#1d2617; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(560px,1fr)); gap:16px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  .card img {{ width:100%; display:block; aspect-ratio:1376/768; object-fit:cover; }}
  .meta {{ padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:13px; line-height:1.4; }}
  .dl-mini {{ color:var(--accent); text-decoration:none; font-weight:700; white-space:nowrap; padding:4px 9px; border:1px solid var(--border); border-radius:5px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>⚔️ АЗБУКА — ПО ПОЛЯМ · 51 СТРОГО ПРОВЕРЕННЫЙ КАДР (100% МОРДОР × СВО · 02:28 · 1080p)</h1>
      <div class="sub">0 людей · 0 старых касок 90-х · 0 американской экипировки у Орды · Сюжет строка в строку по песне: «Ищу сигнал антенной по полям» → «У тебя бабки — у меня дроны, пушки, танки» → «Руки околели / Вышла из луча / Разнёс частоты» → «Минус сорок, лес — нашёл птичку!» → «Весна придёт — тяну к небу ладошки!»</div>
    </div>
    <div class="btns">
      <a class="btn fire" id="dlMain" href="/download/mordor_svo_clean_51shots_2m28s_1080p.mp4">🎬 Чистый Фильм 51 кадр · 02:28 (25.6 МБ)</a>
      <a class="btn fire" id="dlReel" href="/download/mordor_svo_reel_9x16.mp4">📱 Вертикальный Reel 9:16 (9.3 МБ)</a>
      <a class="btn" href="/download/mordor_svo_clean_51_frames.zip">📦 ВСЕ 51 чистый кадр (ZIP · 13.9 МБ)</a>
      <a class="btn" href="/download/mordor_svo_song_10_frames.zip">📦 10 кадров по тексту песни (2.8 МБ)</a>
    </div>
  </header>

  <div class="players">
    <div class="hero">
      <video id="vidMain" controls autoplay loop playsinline src="/video/mordor_svo_clean51.mp4"></video>
      <div class="hero-bar">▶ МАСТЕР 16:9 (02:28.66 · 51 УНИКАЛЬНЫЙ ЧИСТЫЙ КАДР · снег в зимних куплетах + весеннее солнце в финале · 134 BPM)</div>
    </div>
    <div class="hero">
      <video id="vidReel" controls muted loop playsinline src="/video/mordor_svo_reel.mp4"></video>
      <div class="hero-bar">📱 REEL / SHORTS 9:16 (1080×1920 · 32.2 сек · по куплетам и припеву песни)</div>
    </div>
  </div>

  <div class="dropzone" id="dropZone">
    <div style="max-width:820px;">
      <div style="font-weight:700;font-size:15px;">🎵 Мгновенное вшивание оригинального MP3 «АЗБУКА — ПО ПОЛЯМ (Prod. by scaryele).mp3» (за 2 секунды!)</div>
      <div style="font-size:13px;color:#e4b85d;margin-top:5px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div class="btns">
      <button class="btn ghost" onclick="pullFromYandex()">☁️ Скачать MP3 со ссылки Яндекс.Диска</button>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Выбрать MP3 и вшить в клип</button>
    </div>
  </div>

  <h2>🎵 СЮЖЕТНЫЕ КАДРЫ СТРОКА В СТРОКУ ПО ТЕКСТУ «АЗБУКА — ПО ПОЛЯМ» (10 новых кадров)</h2>
  <div class="grid">{cards_p5}</div>

  <h2>🔥 УДАРНАЯ МОЩЬ МОРДОРСКОЙ БРАТИИ — ЧАСТЬ 4 (8 проверенных кадров)</h2>
  <div class="grid">{cards_p4}</div>

  <h2>⚔️ БАЛРОГ, ШЕЛОБ, УСТА САУРОНА, ЛУРТЦ, ГОТМОГ И ДЕCАНТ — ЧАСТЬ 3 (7 проверенных кадров)</h2>
  <div class="grid">{cards_p3}</div>

  <h2>🛡️ САУРОН, САРУМАН, «ГРОНД», «СОЛНЦЕПЁК», ВИВЕРНА С УМПК И ПАРАД — ЧАСТЬ 2 (9 проверенных кадров)</h2>
  <div class="grid">{cards_p2}</div>

  <h2>🐺 КАВАЛЕРИЯ ВАРГОВ, ГОБЛИНЫ, ТРОЛЛЬ, ОЛИФАНТ И ФЛАГИ ПОБЕДЫ — ЧАСТЬ 1 (9 проверенных кадров)</h2>
  <div class="grid">{cards_p1}</div>

  <h2>⚡ ШТУРМОВЫЕ СЦЕНЫ И ЧЁРНЫЕ «ГЕРАНИ» В МОНТАЖЕ (8 проверенных кадров)</h2>
  <div class="grid">{''.join(cards_ex)}</div>
</div>
<script>
const input = document.getElementById('audioInput');
const statusEl = document.getElementById('uploadStatus');
const dropZone = document.getElementById('dropZone');

async function uploadAndMuxFile(file) {{
  if (!file) return;
  statusEl.textContent = '⏳ Загружаем и вшиваем ' + file.name + ' в оба видео (16:9 и 9:16)...';
  const res = await fetch('/upload_audio', {{
    method: 'POST',
    headers: {{ 'X-Filename': encodeURIComponent(file.name) }},
    body: file
  }});
  const data = await res.json();
  if (data.ok && data.muxed) {{
    const ts = Date.now();
    document.getElementById('vidMain').src = '/video/mordor_svo_clean51.mp4?v=' + ts;
    document.getElementById('vidReel').src = '/video/mordor_svo_reel.mp4?v=' + ts;
    document.getElementById('vidMain').muted = false;
    document.getElementById('vidMain').play();
    statusEl.style.color = '#A4CC52';
    statusEl.textContent = '✅ ГОТОВО! ' + data.filename + ' (' + data.size_mb + ' МБ) вшит в оба видео! Жмите Play или кнопку скачивания MP4 сверху!';
  }} else {{
    statusEl.textContent = '⚠️ Ошибка сведения: ' + (data.message || 'неизвестная ошибка');
  }}
}}

input.addEventListener('change', e => uploadAndMuxFile(e.target.files[0]));
dropZone.addEventListener('dragover', e => {{ e.preventDefault(); dropZone.classList.add('drag'); }});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag'));
dropZone.addEventListener('drop', e => {{
  e.preventDefault();
  dropZone.classList.remove('drag');
  if (e.dataTransfer.files.length) uploadAndMuxFile(e.dataTransfer.files[0]);
}});

async function pullFromYandex() {{
  statusEl.textContent = '⏳ Запрашиваем прямую ссылку у Яндекс.Диска...';
  try {{
    const api = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key=' + encodeURIComponent('https://disk.yandex.ru/d/hc7gQWhNlz8WuA');
    const r = await fetch(api);
    const j = await r.json();
    if (!j.href) throw new Error('Нет ссылки');
    try {{
      const bin = await fetch(j.href);
      const blob = await bin.blob();
      if (blob.size > 1000000) {{
        await uploadAndMuxFile(new File([blob], 'АЗБУКА - ПО ПОЛЯМ (Prod. by scaryele).mp3', {{ type: 'audio/mpeg' }}));
        return;
      }}
    }} catch (_) {{}}
    window.open(j.href, '_blank');
    statusEl.textContent = '⬇ Браузер начал скачивание MP3 с Яндекс.Диска — перетащите скачанный файл прямо в эту рамку!';
  }} catch (err) {{
    window.open('https://disk.yandex.ru/d/hc7gQWhNlz8WuA', '_blank');
    statusEl.textContent = '⬇ Скачайте MP3 в открывшейся вкладке и перетащите его прямо в эту рамку!';
  }}
}}
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
    print("Serving Mordor SVO 51-Clean-Frame Lyric Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
