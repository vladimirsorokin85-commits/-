import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/user/-/video_studio")
sys.path.insert(0, str(ROOT / "toolkit"))
import grade

OUT_FRAMES = ROOT / "ubetter" / "tactical_frames"
OUT_FRAMES.mkdir(parents=True, exist_ok=True)

ASSETS = ROOT / "assets"
CUTS = Path("/home/user/-/ubetter_pro/assets/cuts")
FONTS = ROOT / "toolkit" / "fonts"

font_title = ImageFont.truetype(str(FONTS / "RussoOne-Regular.ttf"), 48)
font_head = ImageFont.truetype(str(FONTS / "RussoOne-Regular.ttf"), 36)
font_val = ImageFont.truetype(str(FONTS / "RussoOne-Regular.ttf"), 44)
font_sub = ImageFont.truetype(str(FONTS / "RussoOne-Regular.ttf"), 22)
font_tag = ImageFont.truetype(str(FONTS / "DaysOne-Regular.ttf"), 22)
font_top_tag = ImageFont.truetype(str(FONTS / "DaysOne-Regular.ttf"), 20)
font_pip_label = ImageFont.truetype(str(FONTS / "DaysOne-Regular.ttf"), 17)

scenes = [
    {
        "id": "scene_0_intro",
        "bg": ASSETS / "smekalka_01.jpg",
        "tag": "ТЕХНИЧЕСКИЙ ОБЗОР",
        "title": "АВТОНОМНОЕ ЭНЕРГООБЕСПЕЧЕНИЕ ПОЗИЦИЙ",
        "specs": [
            ("ПРОБЛЕМА ГЕНЕРАТОРА", "ШУМ И ТЕПЛОВОЕ ПЯТНО", "Дроны с тепловизорами вскрывают дизель за секунды"),
            ("РИСК ЭЛЕКТРОНИКИ", "СКАЧКИ НАПРЯЖЕНИЯ", "Дешёвые станции сжигают платы управления БПЛА"),
            ("РЕШЕНИЕ «В ОКОПЕ»", "ТИХАЯ ГИБРИДНАЯ СИСТЕМА", "Чистый синус 220В + безопасные батареи LiFePO4")
        ],
        "prod": None,
        "det": None,
        "det_label": None
    },
    {
        "id": "scene_1_problem",
        "bg": ASSETS / "smekalka_04.jpg",
        "tag": "АНАЛИЗ УГРОЗ",
        "title": "ПОЧЕМУ ДИЗЕЛЬ НА ПЕРЕДКЕ — ЭТО ЦЕЛЬ",
        "specs": [
            ("АКУСТИЧЕСКИЙ ШУМ", "СЛЫШНО ЗА 1.5 КМ", "Выдает позицию опорного пункта и узла связи"),
            ("ТЕПЛОВОЙ ВЫХЛОП", "ДО 350°C НА ВЫХЛОПЕ", "Прямая мишень для тепловизионных FPV-дронов"),
            ("СЕТЕВАЯ НЕСТАБИЛЬНОСТЬ", "БРОСКИ ДО 280 ВОЛЬТ", "Выход из строя дорогостоящих комплексов РЭБ")
        ],
        "prod": CUTS / "m1_body.png",
        "det": CUTS / "m1_ports.png",
        "det_label": "КЛЕММЫ СЕТИ"
    },
    {
        "id": "scene_2_sine_avr",
        "bg": ASSETS / "smekalka_12.jpg",
        "tag": "МОДУЛЬ 1 // ИНВЕРТОР",
        "title": "МГНОВЕННЫЙ АВР И ЧИСТЫЙ СИНУС 220В",
        "specs": [
            ("ВРЕМЯ ПЕРЕКЛЮЧЕНИЯ", "< 10 МС (БЕЗ РАЗРЫВА)", "Связь, Starlink и пульты БПЛА не перезагружаются"),
            ("ФОРМА ВЫХОДНОГО ТОКА", "ИДЕАЛЬНЫЙ ЧИСТЫЙ СИНУС", "Безопасно для серверов, оптики и зарядных хабов"),
            ("ПИКОВАЯ МОЩНОСТЬ", "ДО 10 000 ВА ВСПЛЕСК", "Лёгкий запуск насосов, компрессоров и инструмента")
        ],
        "prod": CUTS / "m1_body.png",
        "det": CUTS / "m1_display.png",
        "det_label": "OLED СТАТУС"
    },
    {
        "id": "scene_3_lifepo4",
        "bg": ASSETS / "smekalka_16.jpg",
        "tag": "МОДУЛЬ 2 // БАТАРЕЯ",
        "title": "ХИМИЯ LIFEPO4: ЗАЩИТА ОТ ВОЗГОРАНИЯ",
        "specs": [
            ("ПОЖАРОБЕЗОПАСНОСТЬ", "НЕ САМОВОСПЛАМЕНЯЕТСЯ", "В отличие от Li-ion не взрывается при повреждении"),
            ("РЕСУРС ЭЛЕМЕНТОВ", "> 6000 ПОЛНЫХ ЦИКЛОВ", "Более 10 лет активной ежедневной эксплуатации"),
            ("ТЕМПЕРАТУРНЫЙ РЕЖИМ", "-20°C ДО +55°C", "Стабильная токоотдача в суровых полевых условиях")
        ],
        "prod": CUTS / "m2_battery.png",
        "det": CUTS / "m2_screen.png",
        "det_label": "BMS ТЕЛЕМЕТРИЯ"
    },
    {
        "id": "scene_4_split",
        "bg": ASSETS / "smekalka_22.jpg",
        "tag": "МОДУЛЬ 3 // СПЛИТ-СИСТЕМА",
        "title": "UBETTER 6.2 КВТ: 2 НЕЗАВИСИМЫХ MPPT",
        "specs": [
            ("НОМИНАЛЬНАЯ МОЩНОСТЬ", "6.2 КВТ (ПИК 12.4 КВА)", "Питание мощных комплексов РЭБ и станций связи"),
            ("СОЛНЕЧНЫЙ ВХОД", "ДО 9000 ВАТТ PV", "Два раздельных трекера для разных скатов и укрытий"),
            ("ГЛУБОКИЙ КОНТРОЛЬ", "ДВУХКАНАЛЬНЫЙ РЕЖИМ", "Параллельная работа без взаимных потерь КПД")
        ],
        "prod": CUTS / "m2_pair.png",
        "det": CUTS / "m2_inverter.png",
        "det_label": "ИНВЕРТОР 6.2K"
    },
    {
        "id": "scene_5_wheels",
        "bg": ASSETS / "smekalka_28.jpg",
        "tag": "МОДУЛЬ 4 // МОБИЛЬНЫЙ ФЛАГМАН",
        "title": "UBETTER 15 КВТ НА КОЛЁСНОЙ БАЗЕ",
        "specs": [
            ("ЁМКОСТЬ НАКОПИТЕЛЯ", "15.36 КВТ·Ч ЭНЕРГИИ", "Суточная автономия полевого госпиталя или базы БПЛА"),
            ("СИЛОВАЯ ЧАСТЬ", "15 КВТ ВЫХОДНОЙ ТОК", "Встроенные защитные автоматы и силовые клеммы"),
            ("МОБИЛЬНОСТЬ", "УСИЛЕННЫЕ ШАССИ", "Быстрая передислокация узла силами расчёта")
        ],
        "prod": CUTS / "m3_full.png",
        "det": CUTS / "m3_breakers.png",
        "det_label": "БЛОК АВТОМАТОВ"
    },
    {
        "id": "scene_6_outro",
        "bg": ASSETS / "smekalka_30.jpg",
        "tag": "ИТОГИ И РЕЗЮМЕ",
        "title": "НАДЁЖНОЕ ПИТАНИЕ — ЖИВУЧЕСТЬ ПОЗИЦИИ",
        "specs": [
            ("ОФИЦИАЛЬНЫЙ TELEGRAM", "T.ME/VOKOPE_RU", "Оперативные полевые тесты и разборы снаряжения"),
            ("ГРУППА ВКОНТАКТЕ", "VK.COM/VOKOPE_RUS", "Технические консультации и схемы подключения"),
            ("МАГАЗИН «В ОКОПЕ»", "ПРОВЕРЕННОЕ ЖЕЛЕЗО", "Официальная гарантия, консультации и поддержка")
        ],
        "prod": CUTS / "m3_wheels.png",
        "det": CUTS / "m1_ports.png",
        "det_label": "ПОРТЫ СИСТЕМЫ"
    }
]

def render_scene(sc):
    bg_raw = Image.open(sc["bg"]).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    bg_graded = grade.look(bg_raw, "frontline")
    
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 0, 1920, 1080], fill=(6, 9, 14, 185))
    
    ov_draw.rectangle([60, 40, 1860, 125], fill=(12, 16, 24, 245), outline=(245, 180, 0, 220), width=2)
    ov_draw.rectangle([75, 52, 330, 113], fill=(245, 180, 0, 255))
    
    ov_draw.rectangle([60, 145, 950, 995], fill=(10, 14, 20, 240), outline=(45, 58, 75, 200), width=2)
    ov_draw.rectangle([980, 145, 1860, 995], fill=(10, 14, 20, 240), outline=(45, 58, 75, 200), width=2)
    
    img = Image.alpha_composite(bg_graded.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    draw.text((95, 62), "В ОКОПЕ", font=font_title, fill=(10, 12, 16))
    draw.text((355, 58), sc["tag"].upper(), font=font_top_tag, fill=(245, 180, 0))
    draw.text((355, 84), sc["title"].upper(), font=font_head, fill=(245, 248, 252))
    
    sy = 185
    for label, val, sub in sc["specs"]:
        draw.rectangle([1010, sy, 1830, sy + 115], fill=(14, 19, 28), outline=(38, 50, 68), width=1)
        draw.rectangle([1010, sy, 1018, sy + 115], fill=(245, 180, 0))
        draw.text((1035, sy + 12), label.upper(), font=font_tag, fill=(160, 175, 195))
        draw.text((1035, sy + 38), val, font=font_val, fill=(255, 255, 255))
        draw.text((1035, sy + 88), sub, font=font_sub, fill=(245, 180, 0))
        sy += 135
        
    draw.rectangle([1010, 875, 1830, 965], fill=(20, 28, 42), outline=(245, 180, 0), width=1)
    draw.text((1030, 887), "ТАКТИЧЕСКИЙ РЕЗУЛЬТАТ:", font=font_tag, fill=(245, 180, 0))
    draw.text((1030, 917), "ПОЛНАЯ ТЕПЛОВАЯ И ЗВУКОВАЯ МАСКИРОВКА ПОЗИЦИИ", font=font_sub, fill=(255, 255, 255))
    
    if sc["prod"] and Path(sc["prod"]).exists():
        prod = Image.open(sc["prod"]).convert("RGBA")
        prod.thumbnail((800, 760), Image.LANCZOS)
        px = 60 + (890 - prod.width) // 2
        py = 145 + (850 - prod.height) // 2
        img.paste(prod, (px, py), prod)
        
    if sc["det"] and Path(sc["det"]).exists():
        det = Image.open(sc["det"]).convert("RGBA")
        det.thumbnail((260, 260), Image.LANCZOS)
        dx = 660
        dy = 705
        draw.rectangle([dx-4, dy-4, dx+det.width+4, dy+det.height+4], fill=(12, 16, 24), outline=(245, 180, 0), width=2)
        img.paste(det, (dx, dy), det)
        if sc["det_label"]:
            label_text = sc["det_label"]
            lw = font_pip_label.getbbox(label_text)[2] + 20
            tab_w = max(det.width, lw)
            tab_x = dx + (det.width - tab_w) // 2
            draw.rectangle([tab_x, dy-26, tab_x + tab_w, dy], fill=(245, 180, 0))
            tx = tab_x + (tab_w - font_pip_label.getbbox(label_text)[2]) // 2
            draw.text((tx, dy-23), label_text, font=font_pip_label, fill=(10, 12, 16))
            
    return img

print("Rendering scene slides...")
slide_paths = []
for idx, sc in enumerate(scenes):
    fpath = OUT_FRAMES / f"slide_{idx}_{sc['id']}.png"
    img = render_scene(sc)
    img.save(fpath)
    slide_paths.append(fpath)
    print(f"Slide {idx} ready: {fpath.name}")

# Now build video segments
ff = "/home/user/.local/bin/ffmpeg"
AUDIO = ROOT / "ubetter" / "tactical_master_horizontal_16x9.mp3"
OUT_VIDEO = ROOT / "ubetter" / "v_okope_tactical_horizontal_overview_16x9.mp4"

durations = [2.0, 29.92, 28.66, 25.74, 25.11, 23.59, 24.02]
part_videos = []

for i, (s, d) in enumerate(zip(slide_paths, durations)):
    part_out = ROOT / "ubetter" / f"tactical_part_{i}.mp4"
    part_videos.append(part_out)
    n_frames = int(d * 30)
    
    vf = f"zoompan=z='min(zoom+0.00022,1.04)':d={n_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
    cmd = [
        ff, "-y",
        "-loop", "1",
        "-i", str(s),
        "-vf", vf,
        "-t", f"{d:.2f}",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(part_out)
    ]
    print(f"Encoding part {i} ({d:.2f}s)...")
    subprocess.run(cmd, check=True)

concat_list = ROOT / "ubetter" / "concat_parts.txt"
with open(concat_list, "w") as f:
    for p in part_videos:
        f.write(f"file '{p.resolve()}'\n")

print("Merging video segments and master audio...")
cmd_final = [
    ff, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(concat_list),
    "-i", str(AUDIO),
    "-c:v", "copy",
    "-c:a", "copy",
    "-shortest",
    str(OUT_VIDEO)
]
subprocess.run(cmd_final, check=True)
print(f"Film successfully created: {OUT_VIDEO}")
