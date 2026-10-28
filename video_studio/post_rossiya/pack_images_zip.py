#!/usr/bin/env python3
"""Package all 104 «ПОСТ-РОССИЯ» images into song-synced timecoded folders (.zip)."""
from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[1]
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from storyboard_data import export_manifests  # noqa: E402


def fmt_tc_file(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}m{s:05.2f}s"


def slugify_ru(text: str, max_len: int = 44) -> str:
    s = text.strip()
    s = re.sub(r"[«»\"'`:,;!?()/\\]+", "", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len].rstrip("_")


def folder_for_synced_clip(sh: dict) -> tuple[str, str]:
    seq = sh["seq"]
    if seq <= 11:
        top = "01_ПРОЛОГ_И_ВСТУПИТЕЛЬНЫЙ_ХОР__00m00.00s-00m22.42s"
        if seq <= 3:
            return (top, "01_00m00.00s-00m02.81s__Черный_экран_смартфон")
        if seq <= 9:
            return (top, "02_00m02.81s-00m18.92s__Вступительный_хор_увертюра")
        return (top, "03_00m18.92s-00m22.42s__Вход_пульса_ночной_дом_и_окно")

    num = sh["num"]
    if 4 <= num <= 12:
        top = "02_КУПЛЕТ_1_АКТ_I_ЧУЖАЯ_БОЛЬ__00m22.42s-00m33.63s"
        if num <= 6:
            return (top, "01_00m22.42s-00m25.22s__Я_плакал_смотря_на_чужой_инстаграм")
        if num <= 9:
            return (top, "02_00m25.22s-00m28.02s__Там_кто-то_вернулся_с_войны")
        return (top, "03_00m28.02s-00m33.63s__Принеся_в_ноге_свинца_пару_грамм")

    if 13 <= num <= 23:
        top = "03_КУПЛЕТ_1_АКТ_II_ПОЗДНЕЕ_ПРОЩЕНИЕ__00m33.63s-00m44.84s"
        if num <= 16:
            return (top, "01_00m33.63s-00m36.43s__Клали_искусственные_цветы_к_могилам")
        if num <= 19:
            return (top, "02_00m36.43s-00m39.23s__И_просили_простить_постфактум")
        return (top, "03_00m39.23s-00m44.84s__Мы_были_такие_красивые")

    if 24 <= num <= 33:
        top = "04_КУПЛЕТ_1_АКТ_III_ЦЕНА_САМОУВЕРЕННОСТИ__00m44.84s-00m56.04s"
        if num <= 26:
            return (top, "01_00m44.84s-00m47.64s__Все_думали_самые_умные_гордые")
        if num <= 29:
            return (top, "02_00m47.64s-00m50.44s__Оказалось_вывезли_за_долги")
        return (top, "03_00m50.44s-00m56.04s__Модные_холодные_Плати_налоги")

    if 34 <= num <= 44:
        top = "05_ПЕРВЫЙ_ПРИПЕВ_ХОР_В_ПОЛЕ__00m56.04s-01m18.46s"
        if num <= 38:
            return (top, "01_00m56.04s-01m06.55s__Первая_волна_хора_в_поле")
        return (top, "02_01m06.55s-01m18.46s__Туман_вороны_слеза_и_простор")

    if 45 <= num <= 76:
        top = "06_ВТОРОЙ_КУПЛЕТ_РАЗЛОЖЕНИЕ_РЕАЛЬНОСТИ__01m18.46s-01m52.08s"
        bars = [
            (47, "01_01m18.46s-01m21.26s__Рукомойник_густыми_мыслями"),
            (50, "02_01m21.26s-01m24.06s__Умыть_ключевое_лицо"),
            (53, "03_01m24.06s-01m26.86s__Паразиты_харам_нечистые"),
            (55, "04_01m26.86s-01m29.66s__Раньше_курицы_было_яйцо"),
            (58, "05_01m29.66s-01m32.47s__Мы_куражимся_нужные_босые"),
            (60, "06_01m32.47s-01m35.27s__Улыбаемся_милым_вам"),
            (63, "07_01m35.27s-01m38.07s__Но_расквасят_носы_курносые"),
            (66, "08_01m38.07s-01m40.87s__За_стабильность_любимых_дам"),
            (68, "09_01m40.87s-01m43.67s__Мы_же_им_позавидуем_тихонько"),
            (71, "10_01m43.67s-01m46.47s__В_лес_уйдем_собирать_падалье"),
            (73, "11_01m46.47s-01m49.28s__И_весна_уже_не_воротится"),
            (76, "12_01m49.28s-01m52.08s__Про_нее_нам_споет_воронье"),
        ]
        for max_n, sub in bars:
            if num <= max_n:
                return (top, sub)

    if seq <= 88:
        return (
            "07_МОСТ_ХОР_А_КАПЕЛЛА_ПРЕДРАССВЕТ__01m52.08s-02m03.29s",
            "01_01m52.08s-02m03.29s__Хор_без_ударных_переход_к_финалу",
        )

    top = "08_ФИНАЛЬНЫЙ_ПРИПЕВ_И_МОРЕ__02m03.29s-02m37.56s"
    if num <= 85:
        return (top, "01_02m03.29s-02m25.70s__Хор_на_городской_площади_и_гаснущие_окна")
    return (top, "02_02m25.70s-02m37.56s__Кода_холодное_море_и_полоска_света")


def build_pack() -> tuple[Path, int]:
    export_manifests()
    staging = Path("/tmp/post_rossiya_pack/ПОСТ-РОССИЯ_КАДРЫ_ПО_ТАЙМКОДАМ")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    count = 0
    ref_dir = staging / "00_ВИЗУАЛЬНЫЕ_ЭТАЛОНЫ_РЕФЕРЕНСЫ"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in [
        ("ref_01_hero.jpg", "01_эталон__главный_герой_35_лет.jpg"),
        ("ref_02_city.jpg", "02_эталон__постсоветский_город_осень.jpg"),
        ("ref_03_choir.jpg", "03_эталон__народный_женский_хор.jpg"),
        ("ref_04_color.jpg", "04_эталон__цветовой_камертон_цветок_в_ливневке.jpg"),
    ]:
        src = THIS_DIR / "refs" / src_name
        if src.exists():
            shutil.copy2(src, ref_dir / dst_name)
            count += 1

    synced_json = THIS_DIR / "output" / "synced_timeline_100.json"
    shots = json.loads(synced_json.read_text(encoding="utf-8"))["shots"]

    index_lines = [
        "ПОСТ-РОССИЯ — Полный каталог 104 кадров с точными тайм-кодами под песню Пост-Россия.mp3 (00:00.00 – 02:37.56)",
        "Темп трека: 85.66 BPM (1 доля = 0.700 с, 1 такт = 2.802 с)",
        "=" * 96,
        "",
    ]
    for sh in shots:
        src = REPO_ROOT / sh["file"]
        if not src.exists():
            continue
        act_folder, scene_folder = folder_for_synced_clip(sh)
        dest_dir = staging / act_folder / scene_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        tc_tag = f"{fmt_tc_file(sh['t0'])}-{fmt_tc_file(sh['t1'])}"
        fname = f"план_{sh['seq']:03d}__{sh['display_code']}__{tc_tag}__{slugify_ru(sh['desc_ru'])}.jpg"
        shutil.copy2(src, dest_dir / fname)
        index_lines.append(f"[{tc_tag}] План {sh['seq']:03d} ({sh['display_code']}) | {sh['cue']} | {act_folder}/{scene_folder}/{fname}")
        count += 1

    lut_dir = staging / "09_КИНОПЛЕНОЧНЫЕ_LUT_И_МОНТАЖНЫЙ_ЛИСТ"
    lut_dir.mkdir(parents=True, exist_ok=True)
    luts_src = THIS_DIR.parent / "toolkit" / "luts"
    for lut_file, dst_lut in [
        ("fuji_xtrans_iii_classic_chrome.cube", "01_Куплет1_Грязная_современность__fuji_classic_chrome.cube"),
        ("fuji_xtrans_iii_pro_neg_hi.cube", "02_Припев1_Выцветшая_память__fuji_pro_neg_hi.cube"),
        ("fuji_3513_constlmap.cube", "03_Куплет2_Разложение_реальности__fuji_3513.cube"),
        ("kodak_tri-x_400.cube", "04_Финал_Бесцветное_предутро__kodak_tri_x_400.cube"),
    ]:
        if (luts_src / lut_file).exists():
            shutil.copy2(luts_src / lut_file, lut_dir / dst_lut)

    for doc_src, doc_dst in [
        (THIS_DIR / "STORYBOARD_PROMPTS.md", "ПОЛНАЯ_РАСКАДРОВКА_И_ПРОМПТЫ.md"),
        (THIS_DIR / "output" / "ТАЙМКОДЫ_ПОД_ПЕСНЮ.md", "ТАЙМКОДЫ_ПОД_ПЕСНЮ.md"),
    ]:
        if doc_src.exists():
            shutil.copy2(doc_src, lut_dir / doc_dst)

    (staging / "00_СПИСОК_ФАЙЛОВ_И_ТАЙМКОДОВ.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    out_zip = THIS_DIR / "output" / "post_rossiya_all_images_by_timecode.zip"
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        for file_path in sorted(staging.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(staging.parent))

    print(f"Packed {count} images into {out_zip} ({out_zip.stat().st_size / 1e6:.2f} MB)")
    return out_zip, count


if __name__ == "__main__":
    build_pack()
