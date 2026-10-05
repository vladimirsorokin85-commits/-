#!/usr/bin/env python3
"""Режиссура рилса «Оплот Infrared»: биты, грейдинг, плашки, музыка, SFX.

Сборщик `video_studio/reels/build.py` умеет только «дорожка + визуалы + субтитры».
Весь «прокачанный» слой студии живёт в `video_studio/toolkit` и подключается здесь:

    grade.look()      киноцвет: Kodak 2383 (frontline), ночь (night_ops), тепловизор (thermal)
    typo.py           экранные плашки: золото, сталь, трафарет, HUD, совконструктивизм
    audio_fx          voice_chain(), beat_grid(bpm_hint=174), carve(), duck(), master()
    toolkit/sfx       CC0 акценты на склейках и раскрытиях

Скрипт готовит материалы и проект, затем вызывает сборщик:

    python3 video_studio/reels/products/oplot-infrared/director.py
    python3 .../director.py --skip-build      # только подготовить материалы

Что делает по шагам:
  1. Читает озвучку, прогоняет её через voice_chain() — голос «как на радио».
  2. Берёт музыкальную дорожку, находит сетку битов (174 BPM) и выбирает отрезок
     с естественной аркой: энергия → брейкдаун → энергия.
  3. Раскладывает монтаж по битам: длины планов заданы в долях бара, поэтому
     склейки попадают в долю, а не «почти» в неё.
  4. Красит фото под каждый блок (frontline / night_ops / thermal) и собирает
     кадрирование: общие планы — весь кадр на размытой подложке, детали — кроп
     с точкой фокуса на капюшоне, торсе, боках.
  5. Рисует экранные плашки пресетами typo.py и привязывает их к репликам
     озвучки, а не к монтажному плану «на глаз».
  6. Сводит музыку: carve() вырезает полку 700–4000 Гц под голос, duck() плавно
     приглушает её во время речи (атака 0,25 с, релиз 0,7 с — без «качелей»),
     сверху — SFX. Итог уходит в master() на −14 LUFS / −1 dBTP.
  7. Пишет project.json и запускает сборщик, который вшивает субтитры и делает QC.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
# video_studio.* нужен корень репозитория, а toolkit.* — папка video_studio.
for entry in (str(REPO), str(REPO / "video_studio")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from toolkit import audio_fx as ax  # noqa: E402
from toolkit import grade  # noqa: E402
from toolkit.typo import PRESETS, fit, render, tape  # noqa: E402
from video_studio.reels.build import probe_duration  # noqa: E402
from PIL import Image  # noqa: E402
import numpy as np  # noqa: E402

BUILD = HERE / "build"
STILLS = BUILD / "stills"
CARD_DIR = BUILD / "cards"
SR = ax.SR

# ----------------------------------------------------------------------------- материал
PHOTOS = [HERE / f"photo_{i}_2026-10-04_15-43-26.jpg" for i in range(1, 6)]
NARRATION = HERE / "narration.mp3"
MUSIC = REPO / "video_studio" / "music_catalog" / "dnb_neuro_174.ogg"
CAPTIONS = HERE / "captions.srt"

# Куда врезать музыку: с 20 с — полная энергия, с 55 с брейкдаун, с 77 с снова драйв.
MUSIC_START = 20.0
BPM_HINT = 174

# Точки кропa под каждое фото (x, y в долях кадра): капюшон, торс, бока, низ.
FOCUS = {
    1: [(0.50, 0.15), (0.50, 0.52), (0.50, 0.86)],
    2: [(0.46, 0.17), (0.50, 0.55), (0.55, 0.86)],
    3: [(0.50, 0.20), (0.50, 0.46), (0.24, 0.42), (0.76, 0.42)],
    4: [(0.50, 0.16), (0.50, 0.52)],
    5: [(0.50, 0.18), (0.50, 0.50), (0.50, 0.84)],
}

# Секции монтажа: (конец секции, длина плана в битах). Склейки садятся на бит,
# поэтому длины планов кратны бару, а не подобраны на глаз.
SECTIONS = [
    (8.3, 6),     # хук — «239 м/с»
    (16.0, 6),    # размеры
    (27.6, 8),    # V50
    (34.4, 8),    # «не универсальная гарантия»
    (39.0, 8),    # протокол (ночной грейд)
    (47.4, 8),    # подготовка к блоку про ИК
    (60.4, 8),    # брейкдаун + тепловизор
    (77.0, 4),    # карточки характеристик — самый быстрый участок
    (93.31, 8),   # документы и финал
]
MIN_CUT_SECONDS = 0.5

# Баланс звука: на сколько дБ музыка тише голоса в паузах и на сколько её ещё
# приглушает duck() во время речи.
MUSIC_OFFSET_DB = 10.0
DUCK_DEPTH_DB = 6.0
VOICE_PEAK = 0.9

# Экранные плашки: привязаны к репликам озвучки, а не к монтажному плану.
# (начало, конец, текст, пресет, y)
CARDS = [
    (0.0, 8.3, "239 м/с — что это значит?", "gold", 210),
    (8.3, 16.0, "ТРИ ДОКУМЕНТА ПЕРЕД ПОКУПКОЙ", "tape", 240),
    (16.0, 25.0, "150×340 СМ · ЗАЯВЛЕННАЯ В ПОЛНЫЙ РОСТ", "steel", 230),
    (25.0, 27.6, "7,5 КГ", "caption_hot", 250),
    (27.6, 34.4, "V50: 239 М/С*", "hud", 230),
    (34.4, 39.0, "НЕ УНИВЕРСАЛЬНАЯ ГАРАНТИЯ", "caption_hot", 240),
    (39.0, 47.4, "ПРОТОКОЛ № 3/031224", "hud", 240),
    (47.4, 60.4, "ИК-ЗАЩИТА ≠ НЕВИДИМОСТЬ", "glitch", 235),
    (60.4, 65.0, "−40…+40 °C*", "caption_hot", 250),
    (65.0, 70.0, "MULTICAM / A-TACS FG", "caption_hot", 250),
    (70.0, 77.0, "74 000 ₽*", "caption_hot", 240),
    (77.0, 86.0, "ПАСПОРТ · ПРОТОКОЛ · ДОКУМЕНТЫ", "soviet", 235),
    (86.0, 93.31, "НАПИШИТЕ: ПРОТОКОЛ", "gold", 210),
]

# Звуковые акценты. Уровни — как в toolkit/README: whoosh/impact −8 дБ, тихие — −14 дБ.
SFX = [
    (0.00, "impact_deep", -8.0),          # удар под хук
    (8.30, "whoosh_transition", -8.0),    # «три документа»
    (27.60, "text_reveal_soft", -14.0),   # V50
    (39.00, "swipe_paper", -12.0),        # листаем документ
    (47.40, "riser_tension", -10.0),      # нарастание к блоку про ИК
    (60.40, "impact_bright", -8.0),       # возврат энергии
    (70.00, "text_reveal_soft", -14.0),   # цена
    (86.00, "logo_sting", -8.0),          # CTA
]


# ----------------------------------------------------------------------------- аудио
def mix_audio(duration: float, out: Path) -> dict:
    """Голос + музыка + SFX. Голос всегда громче музыки; музыка — carve() + duck()."""
    voice = ax.voice_chain(ax.load(NARRATION))
    music = ax.load(MUSIC)

    tempo, beats = ax.beat_grid(music, bpm_hint=BPM_HINT)
    start = min(beats, key=lambda b: abs(b - MUSIC_START))
    a, b = int(start * SR), int((start + duration) * SR)
    bed = music[a:b].copy()
    if len(bed) < int(duration * SR):  # дорожка короче нужного — доциклим
        pad = int(duration * SR) - len(bed)
        bed = ax.np.concatenate([bed, music[:pad]])

    # Голос всегда громче музыки: подложка сначала ставится на MUSIC_OFFSET_DB ниже
    # дорожки, затем получает carve() (полка 700–4000 Гц под голос) и duck() во время
    # речи. Без явного выравнивания bed укладывался всего на 0,6 дБ ниже голоса.
    voice = voice / max(1e-9, np.abs(voice).max()) * VOICE_PEAK
    n = min(len(bed), len(voice))
    bed = ax.gain_to(bed[:n], ax.lufs(voice[:n]) - MUSIC_OFFSET_DB)
    bed = ax.carve(bed)
    bed = ax.duck(bed, voice[:n], depth_db=DUCK_DEPTH_DB, attack=0.25, release=0.7)

    mix = voice[:n] + bed
    for at, name, gain_db in SFX:
        if at >= duration:
            continue
        clip = ax.sfx(name)
        i = int(at * SR)
        j = min(len(mix), i + len(clip))
        if j > i:
            mix[i:j] += clip[: j - i] * 10 ** (gain_db / 20)

    mix = ax.master(mix, target=-14.0, ceiling_db=-1.0)
    if len(mix) < int(duration * SR):  # страховка по длительности
        mix = ax.np.concatenate([mix, ax.np.zeros(int(duration * SR) - len(mix), mix.dtype)])
    ax.save(out, mix[: int(duration * SR)])
    return {"tempo_bpm": round(float(tempo), 1), "music_start": round(float(start), 3),
            "beats_in_reel": int(((beats >= start) & (beats <= start + duration)).sum())}


# ----------------------------------------------------------------------------- кадры
def _look_for(t: float) -> str:
    """Визуальная арка: плёнка → ночные документы → тепловизор на блоке про ИК → плёнка."""
    if 39.0 <= t < 47.4:
        return "night_ops"
    if 47.4 <= t < 60.4:
        return "thermal"
    return "frontline"


def grade_stills(cuts: list[float], plan: list[dict]) -> None:
    """Красит каждую уникальную пару (фото, Look) один раз и переиспользует."""
    STILLS.mkdir(parents=True, exist_ok=True)
    cache: dict[tuple[int, str], Path] = {}
    for index, item in enumerate(plan):
        key = (item["photo"], item["look"])
        if key not in cache:
            out = STILLS / f"p{item['photo']}_{item['look']}.jpg"
            if not out.exists():
                img = Image.open(PHOTOS[item["photo"] - 1]).convert("RGB")
                grade.look(img, item["look"], seed=index).save(out, quality=94)
            cache[key] = out
        item["still"] = cache[key]


def plan_cuts(duration: float, beats) -> tuple[list[float], list[dict]]:
    """Раскладывает планы по секциям и битам, раздает фото, ракурсы и грейд."""
    reel_beats = sorted(
        b - MUSIC_START for b in beats if 0.0 <= b - MUSIC_START <= duration + 0.001
    )
    cuts = [0.0]
    section_start = 0.0
    for section_end, step in SECTIONS:
        section_end = min(section_end, duration)
        first = next((k for k, b in enumerate(reel_beats) if b >= section_start - 1e-6), None)
        if first is None:
            break
        index = first
        while index < len(reel_beats):
            beat = reel_beats[index]
            if beat >= section_end - 1e-6:
                break
            if beat - cuts[-1] >= MIN_CUT_SECONDS:
                cuts.append(round(beat, 3))
            index += step
        section_start = section_end

    # Хвост: либо отдельным планом, либо растягиваем последний, чтобы не было огрызка.
    if duration - cuts[-1] >= MIN_CUT_SECONDS:
        cuts.append(round(duration, 3))
    else:
        cuts[-1] = round(duration, 3)

    plan: list[dict] = []
    for i in range(len(cuts) - 1):
        start, end = cuts[i], cuts[i + 1]
        mid = (start + end) / 2
        photo = (i % 5) + 1
        # Каждый третий план — общий (весь кадр), остальные — детали с точкой фокуса.
        if i % 3 == 0:
            fit_mode, focus = "blur", [0.5, 0.5]
        else:
            fit_mode = "crop"
            focus = list(FOCUS[photo][(i // 3) % len(FOCUS[photo])])
        plan.append({"start": start, "end": end, "photo": photo, "look": _look_for(mid),
                     "fit_mode": fit_mode, "focus": focus})
    return cuts, plan


# ----------------------------------------------------------------------------- плашки
def render_cards(width: int) -> list[dict]:
    """Рисует плашки пресетами typo.py и подгоняет под ширину кадра."""
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    limit = width - 80
    result = []
    for start, end, text, preset, y in CARDS:
        if preset == "tape":
            layer = tape(text.upper(), size=54)
        else:
            style = PRESETS[preset]
            layer = render(text, style, size=fit(text, style, limit, size=150, min_size=28))
        if layer.width > limit:  # fit() не учитывает отступы эффектов
            layer = layer.resize((limit, int(layer.height * limit / layer.width)), Image.LANCZOS)
        path = CARD_DIR / f"card_{len(result):02d}_{preset}.png"
        layer.save(path)
        result.append({"path": path, "start_seconds": start, "end_seconds": end,
                       "x": "center", "y": y, "fade_seconds": 0.3})
    return result


# ----------------------------------------------------------------------------- сборка
def _rel(path: Path) -> str:
    """Путь относительно папки сборки — в project.json все пути считаются от него."""
    return os.path.relpath(path, BUILD)


def write_project(audio: Path, plan: list[dict], overlays: list[dict], out: Path,
                  width: int, height: int, fps: int) -> None:
    project = {
        "title": "Оплот Infrared — характеристики и проверка документов",
        "audio": _rel(audio),
        "visuals": [
            {"path": _rel(item["still"]),
             "duration_seconds": round(item["end"] - item["start"], 3),
             "fit_mode": item["fit_mode"], "focus": item["focus"]}
            for item in plan
        ],
        "music": None,
        "captions": _rel(CAPTIONS),
        "overlays": [
            {"path": _rel(ov["path"]), "start_seconds": ov["start_seconds"],
             "end_seconds": ov["end_seconds"], "x": ov["x"], "y": ov["y"],
             "fade_seconds": ov["fade_seconds"]}
            for ov in overlays
        ],
        "output": _rel(HERE / "output" / "oplot-infrared.mp4"),
        "duration_seconds": None,
        "settings": {"resolution": [width, height], "fps": fps, "shot_seconds": 4,
                     "chunk_scenes": 12, "crf": 20, "preset": "medium", "music_gain": 0,
                     "caption_mode": "burn", "smart_crop": False},
    }
    out.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Режиссура рилса «Оплот Infrared».")
    parser.add_argument("--skip-build", action="store_true", help="только подготовить материалы")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args(argv)

    for tool in ("ffmpeg", "ffprobe"):
        if subprocess.run(["which", tool], capture_output=True).returncode:
            print(f"Ошибка: не найден {tool}.", file=sys.stderr)
            return 2
    for path in (*PHOTOS, NARRATION, MUSIC, CAPTIONS):
        if not path.is_file():
            print(f"Ошибка: не найден файл {path}", file=sys.stderr)
            return 2

    BUILD.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(NARRATION, "audio")
    print(f"Озвучка: {duration:.2f} с · музыка: {MUSIC.name} · {BPM_HINT} BPM")

    info = mix_audio(duration, BUILD / "audio_mix.wav")
    print(f"Микс: темп {info['tempo_bpm']} BPM, старт музыки {info['music_start']} с, "
          f"битов в ролике {info['beats_in_reel']}")

    _, beats = ax.beat_grid(ax.load(MUSIC), bpm_hint=BPM_HINT)
    cuts, plan = plan_cuts(duration, beats)
    print(f"Монтаж: {len(plan)} планов по битам, "
          f"длительности {min(c['end'] - c['start'] for c in plan):.2f}–"
          f"{max(c['end'] - c['start'] for c in plan):.2f} с")

    grade_stills(cuts, plan)
    looks = sorted({item["look"] for item in plan})
    print(f"Грейд: {', '.join(looks)}")

    overlays = render_cards(args.width)
    print(f"Плашки: {len(overlays)}")

    write_project(BUILD / "audio_mix.wav", plan, overlays, BUILD / "project.json",
                  args.width, args.height, args.fps)
    print(f"Проект: {BUILD / 'project.json'}")
    if args.skip_build:
        return 0

    result = subprocess.run(
        [sys.executable, "-m", "video_studio.reels", str(BUILD / "project.json")],
        cwd=str(REPO),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
