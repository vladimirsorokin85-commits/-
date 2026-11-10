#!/usr/bin/env python3
"""Live Preview: 55-Unique-Shot 02:28 1080p Film + 20-Shot 9:16 Reel + 55-Frame Gallery & MP3 Dropzone."""
import html
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
HORDE_DIR = ROOT / "video_studio" / "horde_clip"
PART4_DIR = HORDE_DIR / "mordor_svo_part4"
PART3_DIR = HORDE_DIR / "mordor_svo_part3"
PART2_DIR = HORDE_DIR / "mordor_svo_part2"
MORDOR_DIR = HORDE_DIR / "mordor_svo_frames"
MODERN_DIR = HORDE_DIR / "modern_frames"
F1_DIR = HORDE_DIR / "frames"
B2_DIR = HORDE_DIR / "batch2_frames"
AUDIO_DIR = HORDE_DIR / "audio"
OUTPUT_DIR = HORDE_DIR / "output"

CAPTIONS_P4 = {
    "mordor_31_azog_pale_orc_bmpt_terminator_assault.jpg": "31 · Бледный орк АЗОГ Осквернитель с белыми варгами и БМПТ «Терминатор-2» бьют из спаренных 30-мм пушек и ПТУР «Атака»",
    "mordor_32_witch_king_ka52_alligator_vihr_strike.jpg": "32 · Король-чародей верхом на бронированной Виверне идёт крылом к крылу с парой Ка-52М «Аллигатор» — пуск ПТУР «Вихрь» по полям!",
    "mordor_33_goblin_fpv_workshop_dugout_soldering.jpg": "33 · Подземная мастерская в блиндаже: гоблины Мории и орк в ВКПО 3.0 «Мох» паяют FPV-дроны, мотают оптоволокно и вешают сбросы",
    "mordor_34_smaug_drake_tu95_kh101_strategic_launch.jpg": "34 · Огненный Дрейк Мордора в сбруе со звездой и триколором взлетает на форсаже в паре с ракетоносцем Ту-22М3 ВКС РФ",
    "mordor_35_black_numenorean_2s19_msta_s_krasnopol.jpg": "35 · САУ 2С19М2 «Мста-С» в «Накидке» и «мангале» бьёт снарядами «Краснополь»: расчёт урук-хаев и назгул с планшетом",
    "mordor_36_orc_medevac_armored_linza_warg_medic.jpg": "36 · Бронеавтомобиль «Линза» («Своих не бросаем»): гоблин-военврач перевязывает урук-хая с АК-12 рядом с псом-варгом",
    "mordor_37_haradrim_oliphaunt_column_po_polyam_march.jpg": "37 · Великий марш «ПО ПОЛЯМ»: два Олифанта в «Царь-Мангалах» с Триколором, Т-90М, «Буханки» с РЭБ и кавалерия варгов до горизонта!",
    "mordor_38_troll_trophy_haul_leopard_bradley_tow.jpg": "38 · Трофейная команда: два 4-метровых Пещерных Тролля и БРЭМ вытаскивают из грязи подбитую броню эльфов под съёмку орков на телефоны!",
    "mordor_39_orc_banya_samovar_harmony_izengardovka.jpg": "39 · Полевая баня, кипящий самовар на шишках и гармонь после боя: урук-хаи, гоблины и варги отдыхают во взятой Цитадели!",
    "mordor_40_mordor_brotherhood_group_portrait_victory_banner.jpg": "40 · Общее фото Победы всей Мордорской Братии (Саурон, Король-чародей, уруки, гоблины, Тролль и варги): «НОВАЯ ИЗЕНГАРДОВКА — НАША!»",
}

CAPTIONS_P3 = {
    "mordor_21_mouth_of_sauron_capitulation_elves.jpg": "21 · Глашатай Саурона («Уста Саурона») у «Тигра-М» принимает безоговорочную капитуляцию эльфов и знамён Гондора",
    "mordor_22_balrog_iskander_missile_launch.jpg": "22 · Закованный в броню с триколором БАЛРОГ Моргота и боевой пуск ОТРК «Искандер-М»",
    "mordor_23_gothmog_general_grad_tornado_salvo.jpg": "23 · Генерал орков ГОТМОГ командует залпом батареи РСЗО «Торнадо-Г» в «мангалах»",
    "mordor_24_lurtz_uruk_sniper_svd_thermal_pair.jpg": "24 · Вожак урук-хаев ЛУРТЦ с Белой Дланью в «Кикиморе» с винтовкой Орсис Т-5000 + гоблин-корректировщик и варг",
    "mordor_25_shelob_spider_fiber_optic_ambush.jpg": "25 · Гигантская паучиха ШЕЛОБ с катушками оптоволокна («Паутина СВО») и гоблины-операторы FPV",
    "mordor_26_olog_hai_troll_sapper_ur77_zmej_gorynych.jpg": "26 · 4-метровый тролль Олог-хай с молотом и УР-77 «Змей Горыныч» рвут укрепления Белой Крепости",
    "mordor_27_khamul_nazgul_lancet_operator_dugout.jpg": "27 · Назгул Кхамул и расчёт орков/гоблинов: воздушный таран вражеской «Бабы-Яги»",
    "mordor_28_corsairs_umbar_raptor_boat_amphibious_orcs.jpg": "28 · Речной десант Мордора на бронекатерах «Раптор» под Триколором и Оком Мордора мимо Осгилиата",
    "mordor_29_troll_field_kitchen_kp130_izengardovka.jpg": "29 · Полевая кухня КП-130 в «НОВОЙ ИЗЕНГАРДОВКЕ»: Тролль-повар раздаёт гречку с тушёнкой оркам и гоблинам",
    "mordor_30_eye_of_barad_dur_reb_radar_fortress_finale.jpg": "30 · Финал: крепость «НОВАЯ ИЗЕНГАРДОВКА» с башней Ока-РЛС, ЗРПК «Панцирь-С1», Триколором, Виверной и Су-34!",
}

CAPTIONS_P2 = {
    "mordor_11_sauron_command_bunker_streams.jpg": "11 · Саурон на КСП в блиндаже перед экранами FPV-трансляций вместе с урук-хаем и гоблином",
    "mordor_12_grond_jet_battering_ram_reb.jpg": "12 · Таран «ГРОНД» на базе Т-90 с волчьей пастью, РЭБ и двумя Боевыми Троллями крушит врата Минас-Тирита",
    "mordor_13_tos1a_solntsepek_goblin_uruk_svo.jpg": "13 · ТОС-1А «Солнцепёк» в «мангале» даёт термобарический залп: экипаж урук-хаев, гоблина и варгов",
    "mordor_14_uruk_hai_white_hand_enduro_assault.jpg": "14 · Мотоштурм Урук-хаев с отпечатком Белой Длани Сарумана на шлемах + стая варгов летят «по полям»",
    "mordor_15_fell_beast_umpk_fab_drop.jpg": "15 · Боевая Виверна Назгула сбрасывает крылатый ФАБ-500 с модулем УМПК в паре с Су-34 ВКС РФ",
    "mordor_16_goblin_sappers_ground_robot_kurier.jpg": "16 · Гоблины Мории и варг ведут гусеничный наземный дрон НРТК «Курьер» с АГС и ПТУР",
    "mordor_17_saruman_tactical_pantsir_air_defense.jpg": "17 · Саруман Белый в софтшелле «Мох» и плитнике с триколором командует расчётом ЗРПК «Панцирь-С1»",
    "mordor_18_warg_cavalry_pursuit_fleeing_elves.jpg": "18 · Кавалерия Наездников на Варгах в обвесе СВО гонит разбитых эльфов мимо горящей западной брони",
    "mordor_19_buhanka_svo_goblin_checkpoint_izengardovka.jpg": "19 · Фронтовая «Буханка» в «мангале» и РЭБ у знака «НОВАЯ ИЗЕНГАРДОВКА»: гоблин-механик, урук-хаи и варг",
    "mordor_20_grand_parade_victory_novaya_izengardovka.jpg": "20 · Грандиозный Парад Победы Мордорской Братии: Саурон на Т-90М, Тролли, Олифант, Варги, Виверна и Ка-52М!",
}

CAPTIONS_P1 = {
    "mordor_01_warg_riders_desertcross_charge.jpg": "01 · Кавалерия Наездников на Варгах в кевларе «Мох» + багги Desertcross Назгула рвут «по полям»",
    "mordor_02_goblins_fiber_fpv_lancet_team.jpg": "02 · Гоблины Мории и Король-чародей в ВКПО 3.0 «Мох» запускают Х-крылый «Ланцет» и оптоволоконный FPV",
    "mordor_03_armored_cave_troll_kontakt1_breach.jpg": "03 · 4-метровый Боевой Тролль Мордора в плитнике с триколором + Т-90М «Прорыв» проламывают Белые Врата",
    "mordor_04_mumakil_oliphaunt_tsar_mangal.jpg": "04 · Боевой Олифант (Мумакил) в «Накидке» и огромном сварном «Царь-Мангале» с РЭБ и ПТУР идёт с варгами",
    "mordor_05_nazgul_fell_beast_ka52_airbase.jpg": "05 · Крылатая тварь Назгула в тактической сбруе «Мох» с триколором, урук-хаи и пара Ка-52М «Аллигатор»",
    "mordor_06_geran_swarm_goblin_techs_night.jpg": "06 · Вечерний залп чёрных «Гераней-2» с пикапов с купольным РЭБ: орки, гоблин с планшетом и варг",
    "mordor_07_cqb_wargs_orcs_capture_elves.jpg": "07 · Зачистка Минас-Тирита: урук-хаи, гоблин и боевые псы-варги на поводках берут в плен эльфов",
    "mordor_08_novaya_izengardovka_warg_svo.jpg": "08 · Знак «НОВАЯ ИЗЕНГАРДОВКА»: боевой варг в жилете «Мох», Король-чародей, орки и гоблин с шуруповёртом",
    "mordor_09_tricolor_mordor_flag_bare_orcs.jpg": "09 · Флаги Победы: урук-хаи, гоблин и Король-чародей поднимают Триколор РФ и знамя Ока Мордора",
    "mordor_10_throne_hall_orc_goblin_warg_pack.jpg": "10 · Привал всей мордорской братии в Тронном Зале: назгулы, орки с АК-12, гоблины с FPV и варги",
}

CAPTIONS_EXTRA = [
    (MODERN_DIR, "/mod/", "modern_01_orc_storm_squad_vkpo_moss.jpg", "41 · Штурмовая четвёрка орков в ВКПО 3.0 «Мох», плитниках с напашниками, АК-12 с банками и РЭБ"),
    (MODERN_DIR, "/mod/", "modern_02_desertcross_buggy_enduro_po_polyam.jpg", "42 · Штурмовой багги Desertcross с РЭБ и кроссовые эндуро орков летят через распутицу"),
    (MODERN_DIR, "/mod/", "modern_03_lancet_and_fiber_fpv_team.jpg", "43 · Расчёт «Ланцета» и оптоволоконного FPV-дрона с Королём-чародеем над долиной"),
    (MODERN_DIR, "/mod/", "modern_04_geran_black_swarm_night_pickup.jpg", "44 · Пуск матово-чёрных «Гераней-2» с пикапов в сумерках"),
    (MODERN_DIR, "/mod/", "modern_05_su34_umpk_glide_bombs_citadel.jpg", "45 · Су-34 сбрасывает ФАБы с УМПК по бастионам Белой Крепости"),
    (MODERN_DIR, "/mod/", "modern_06_t90m_proryv_nakidka_breach.jpg", "46 · Т-90М «Прорыв» со штурмовиками орков давит натовский броневик в проломе ворот"),
    (MODERN_DIR, "/mod/", "modern_07_citadel_cqb_elves_defeated.jpg", "47 · Урук-хаи в ВКПО 3.0 «Мох» с триколором и назгулы берут в плен эльфийский гарнизон"),
    (MODERN_DIR, "/mod/", "modern_08_novaya_izengardovka_sign_svo.jpg", "48 · Король-чародей, клыкастые орки и Т-90М у дорожного знака «НОВАЯ ИЗЕНГАРДОВКА»"),
    (F1_DIR, "/f1/", "03_witch_king_tablet_briefing.jpg", "49 · Полевой инструктаж у капота: Король-чародей и штурмовики орков сверяют карту на планшете"),
    (B2_DIR, "/b2/", "s06_geran_f2_swarm.jpg", "50 · Пикирующий рой чёрных «Гераней-2» заходит сквозь ливень на башни Белой Крепости"),
    (B2_DIR, "/b2/", "s07_geran_f3_strike.jpg", "51 · Прямое попадание «Гераней» и детонация на верхнем ярусе эльфийской цитадели"),
    (F1_DIR, "/f1/", "05_elven_trench_panic_under_barrage.jpg", "52 · Паника в окопах эльфов под плотным артиллерийским валом"),
    (F1_DIR, "/f1/", "06_orc_mlrs_salvo_across_fields.jpg", "53 · Двойной залп тяжёлых огнемётных систем через раскисшие поля"),
    (F1_DIR, "/f1/", "07_btr_breaching_ancient_marble_gates.jpg", "54 · Танк с колейным минным тралом и пехота орков врываются в мраморные врата"),
    (F1_DIR, "/f1/", "09_captured_ramparts_trophies.jpg", "55 · Перекур орков на трофейных ящиках над горой брошенных щитов Гондора"),
]


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
            "/video/mordor_svo_55shots.mp4": (OUTPUT_DIR / "mordor_svo_55shots_2m28s_1080p.mp4", "video/mp4", None),
            "/video/mordor_svo_reel.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", None),
            "/download/mordor_svo_55shots_2m28s_1080p.mp4": (OUTPUT_DIR / "mordor_svo_55shots_2m28s_1080p.mp4", "video/mp4", "mordor_svo_55shots_2m28s_1080p.mp4"),
            "/download/mordor_svo_reel_9x16.mp4": (OUTPUT_DIR / "mordor_svo_reel_9x16.mp4", "video/mp4", "mordor_svo_reel_9x16.mp4"),
            "/download/mordor_svo_master_55_frames.zip": (OUTPUT_DIR / "mordor_svo_master_55_frames.zip", "application/zip", "mordor_svo_master_55_frames.zip"),
            "/download/mordor_svo_part4_10_frames.zip": (OUTPUT_DIR / "mordor_svo_part4_10_frames.zip", "application/zip", "mordor_svo_part4_10_frames.zip"),
        }
        if path in routes:
            fpath, ctype, att = routes[path]
            if fpath.is_file():
                self.serve_range_file(fpath, ctype, attachment=att)
                return
        for prefix, folder in (
            ("/mp4f/", PART4_DIR), ("/mp3f/", PART3_DIR), ("/mp2/", PART2_DIR),
            ("/msvo/", MORDOR_DIR), ("/mod/", MODERN_DIR), ("/f1/", F1_DIR), ("/b2/", B2_DIR),
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
            f"✅ Трек в студии: {', '.join(html.escape(a) for a in audio_files)}"
            if audio_files
            else "⏳ Закиньте сюда MP3 «АЗБУКА - ПО ПОЛЯМ», чтобы свести все 55 кадров прямо на оригинальный вокал!"
        )
        cards_p4 = self.build_cards(PART4_DIR, "/mp4f/", CAPTIONS_P4)
        cards_p3 = self.build_cards(PART3_DIR, "/mp3f/", CAPTIONS_P3)
        cards_p2 = self.build_cards(PART2_DIR, "/mp2/", CAPTIONS_P2)
        cards_p1 = self.build_cards(MORDOR_DIR, "/msvo/", CAPTIONS_P1)
        cards_ex = []
        for folder, pref, fname, text in CAPTIONS_EXTRA:
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
<title>МОРДОР × СВО · 55 УНИКАЛЬНЫХ КАДРОВ НА 02:28 (1080p) + REEL 9:16</title>
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
      <h1>🔥 МОРДОР × СВО · 55 УНИКАЛЬНЫХ КАДРОВ НА 02:28.7 (0 ПОВТОРОВ · 1080p) + REEL 9:16</h1>
      <div class="sub">Азог + «Терминатор-2» · Дрейк + Ту-22М3 · Балрог + «Искандер» · Шелоб с оптоволокном · Мастерская гоблинов · Тролли с трофеями · Полевая баня с самоваром · «НОВАЯ ИЗЕНГАРДОВКА — НАША!»</div>
    </div>
    <div class="btns">
      <a class="btn fire" href="/download/mordor_svo_55shots_2m28s_1080p.mp4">🎬 Фильм 55 кадров · 02:28 1080p (25.6 МБ)</a>
      <a class="btn fire" href="/download/mordor_svo_reel_9x16.mp4">📱 Вертикальный Reel 9:16 (9.3 МБ)</a>
      <a class="btn" href="/download/mordor_svo_master_55_frames.zip">📦 ВСЕ 55 кадров по таймкодам (ZIP · 14.8 МБ)</a>
      <a class="btn" href="/download/mordor_svo_part4_10_frames.zip">📦 Часть 4 — 10 новых кадров (2.7 МБ)</a>
    </div>
  </header>

  <div class="players">
    <div class="hero">
      <video controls autoplay loop playsinline src="/video/mordor_svo_55shots.mp4"></video>
      <div class="hero-bar">▶ МАСТЕР-ВЕРСИЯ 16:9 (02:28.7 · 55 СТРОГО УНИКАЛЬНЫХ КАДРОВ · средняя смена плана 2.7 сек · 134 BPM · 0 повторов!)</div>
    </div>
    <div class="hero">
      <video controls muted loop playsinline src="/video/mordor_svo_reel.mp4"></video>
      <div class="hero-bar">📱 20-КАДРОВЫЙ REEL / SHORTS (9:16 · 1080×1920 · 32.2 сек)</div>
    </div>
  </div>

  <div class="dropzone">
    <div>
      <div style="font-weight:700;font-size:15px;">🎵 Загрузка трека «АЗБУКА — ПО ПОЛЯМ (.mp3)» (55 кадров уже стоят по сетке 134 BPM на 02:28.7!)</div>
      <div style="font-size:13px;color:#e0b252;margin-top:4px;" id="uploadStatus">{audio_status}</div>
    </div>
    <div>
      <input type="file" id="audioInput" accept=".mp3,.wav,.m4a,.ogg,audio/*" style="display:none">
      <button class="btn" onclick="document.getElementById('audioInput').click()">⬆ Закинуть MP3 в студию</button>
    </div>
  </div>

  <h2>🔥 ЧАСТЬ 4 (НОВИНКА — Азог + «Терминатор-2», Дрейк + Ту-22М3, Мастерская гоблинов, «Мста-С», «Линза», Марш Олифантов, Трофеи и Баня с самоваром — 10 кадров)</h2>
  <div class="grid">{cards_p4}</div>

  <h2>⚔️ ЧАСТЬ 3 — Балрог + «Искандер», Шелоб с оптоволокном, Уста Саурона, Луртц, Готмог, УР-77, Кухня Тролля и Око-РЛС (10 кадров)</h2>
  <div class="grid">{cards_p3}</div>

  <h2>🛡️ ЧАСТЬ 2 — Саурон на КСП, Саруман на «Панцире», «ГРОНД», «Солнцепёк», Виверна с ФАБ-УМПК, «Буханка» и Парад Победы (10 кадров)</h2>
  <div class="grid">{cards_p2}</div>

  <h2>🐺 ЧАСТЬ 1 — Кавалерия Варгов, Гоблины, Боевой Тролль, Олифант в «Царь-Мангале», Назгулы (10 кадров)</h2>
  <div class="grid">{cards_p1}</div>

  <h2>⚡ ШТУРМОВЫЕ И УДАРНЫЕ СЦЕНЫ В СОСТАВЕ 55-КАДРОВОГО МОНТАЖА (15 кадров)</h2>
  <div class="grid">{''.join(cards_ex)}</div>
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
    print("Serving Mordor SVO 55-Frame Studio on http://0.0.0.0:8000", flush=True)
    srv.serve_forever()
