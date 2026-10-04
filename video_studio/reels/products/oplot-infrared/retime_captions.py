#!/usr/bin/env python3
"""Привязать черновые субтитры к реальным паузам озвучки (без ASR).

Метод: границы реплик из `captions.srt` остаются привязанными к тем же текстовым
блокам, но их тайминги уточняются по акустике дорожки.

1. `ffmpeg silencedetect` находит интервалы тишины в дикторской дорожке.
2. Для каждой внутренней границы реплики известна оценка «по числу знаков»
   (она и лежит в черновом SRT). Граница либо остаётся на месте, либо
   переносится в ближайшую паузу.
3. Выбор границ — динамическое программирование по всем границам сразу:
   позиции строго возрастают, каждая пауза используется не более одного раза,
   минимальная длительность реплики соблюдается. Штраф за границу «внутри
   речи» больше для конца предложения («. ! ? …»), где пауза ожидается почти
   всегда, и меньше для середины фразы.

Это по-прежнему оценка, а не распознавание речи: точные таймкоды слов даёт
`python3 -m video_studio.reels.captions --transcribe` (faster-whisper). Скрипт
улучшает синхронизацию там, где слышимые паузы совпадают с границами фраз:
субтитр меняется в момент, когда диктор замолкает, а не посреди слова.

Запуск из корня репозитория:

    python3 video_studio/reels/products/oplot-infrared/retime_captions.py
    python3 .../retime_captions.py --draft-out captions.draft.srt --report captions.alignment.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SENTENCE_END = re.compile(r"[.!?…][»\"')\]]?$")
TIMING_LINE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)
PAUSE_START = re.compile(r"silence_start:\s*([\d.]+)")
PAUSE_END = re.compile(r"silence_end:\s*([\d.]+)")

# Отступы как в word_timed_srt(): реплика чуть переживает конец речи и
# появляется за мгновение до её начала.
LEAD_SECONDS = 0.04
TAIL_SECONDS = 0.10
GAP_SECONDS = 0.06
MIN_CUE_SECONDS = 0.45


class RetimeError(RuntimeError):
    """Понятная ошибка синхронизации субтитров."""


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _wrap(text: str, width: int = 34) -> str:
    """Перенос строк как в captions.py, чтобы вид реплик не изменился."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width and not lines:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines[:2])


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    raw = path.read_text(encoding="utf-8")
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\r?\n", raw.strip()):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        match = TIMING_LINE.search(lines[1])
        if not match:
            raise RetimeError(f"Не разобрана строка таймкода в {path.name}: {lines[1]!r}")
        head = [int(x) for x in match.groups()[:4]]
        tail = [int(x) for x in match.groups()[4:]]
        to_seconds = lambda h, m, s, ms: h * 3600 + m * 60 + s + ms / 1000  # noqa: E731
        text = " ".join(line.strip() for line in lines[2:] if line.strip())
        cues.append((to_seconds(*head), to_seconds(*tail), text))
    if not cues:
        raise RetimeError(f"В {path} не найдено ни одной реплики.")
    return cues


def duration_of(path: Path, ffprobe: str) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RetimeError(f"ffprobe не смог прочитать {path.name}: {result.stderr.strip()[-300:]}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RetimeError(f"Не удалось определить длительность {path.name}.") from exc


def detect_pauses(ffmpeg: str, audio: Path, *, noise_db: int, min_pause: float) -> list[tuple[float, float]]:
    """Интервалы тишины длиннее min_pause по данным silencedetect."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(audio), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_pause}", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    log = result.stderr or ""
    starts = [float(x) for x in PAUSE_START.findall(log)]
    ends = [float(x) for x in PAUSE_END.findall(log)]
    if not starts:
        raise RetimeError("silencedetect не нашёл ни одной паузы — проверьте озвучку.")
    pauses = [(s, e) for s, e in zip(starts, ends) if e - s >= min_pause * 0.9]
    if not pauses:
        raise RetimeError("Все найденные паузы короче порога — уменьшите --min-pause.")
    return pauses


def choose_boundaries(
    cues: list[tuple[float, float, str]],
    pauses: list[tuple[float, float]],
    duration: float,
    *,
    penalty_sentence: float,
    penalty_middle: float,
    min_cue: float,
) -> tuple[list[float], list[bool]]:
    """Границы реплик: DP по возрастающим позициям с одиночным использованием паузы."""
    boundary_count = len(cues) - 1
    if boundary_count <= 0:
        raise RetimeError("Для синхронизации нужно минимум две реплики.")
    estimates = [cues[k][1] for k in range(boundary_count)]
    is_sentence_end = [bool(SENTENCE_END.search(cues[k][2])) for k in range(boundary_count)]

    options: list[list[tuple[int, float, float]]] = []
    for k in range(boundary_count):
        penalty = penalty_sentence if is_sentence_end[k] else penalty_middle
        current = [(-1, estimates[k], penalty)]
        for index, (start, end) in enumerate(pauses):
            snapped = min(start + TAIL_SECONDS, end - 0.02)
            if snapped <= 0.0 or snapped >= duration:
                continue
            current.append((index, snapped, abs(snapped - estimates[k])))
        options.append(current)

    infinity = math.inf
    best: dict[tuple[int, float], float] = {}
    for pause_index, position, cost in options[0]:
        best[(pause_index, position)] = min(best.get((pause_index, position), infinity), cost)

    backpointers: list[dict[tuple[int, float], tuple[int, float]]] = []
    for k in range(1, boundary_count):
        nxt: dict[tuple[int, float], float] = {}
        pointers: dict[tuple[int, float], tuple[int, float]] = {}
        for (previous_pause, previous_position), cost in best.items():
            for pause_index, position, step in options[k]:
                if pause_index != -1 and pause_index <= previous_pause:
                    continue
                if position - previous_position < min_cue:
                    continue
                key = (pause_index, position)
                if cost + step < nxt.get(key, infinity):
                    nxt[key] = cost + step
                    pointers[key] = (previous_pause, previous_position)
        if not nxt:
            raise RetimeError("Не удалось уложить реплики без наложений — проверьте черновой SRT.")
        backpointers.append(pointers)
        best = nxt

    final = min(best, key=lambda key: best[key])
    chosen = [final]
    for k in range(boundary_count - 1, 0, -1):
        chosen.append(backpointers[k - 1][chosen[-1]])
    chosen.reverse()
    return [position for _, position in chosen], [
        pause_index != -1 for pause_index, _ in chosen
    ]


def cue_windows(
    cues: list[tuple[float, float, str]],
    boundaries: list[float],
    pauses: list[tuple[float, float]],
    duration: float,
) -> tuple[list[float], list[float]]:
    starts: list[float] = []
    ends: list[float] = []
    previous_end = 0.0
    for k, cue in enumerate(cues):
        start = 0.0 if k == 0 else max(previous_end + GAP_SECONDS, boundaries[k - 1])
        end = duration if k == len(cues) - 1 else boundaries[k]
        if k > 0:
            for pause_start, pause_end in pauses:
                if pause_start <= boundaries[k - 1] <= pause_end:
                    start = max(previous_end + GAP_SECONDS, pause_end - LEAD_SECONDS)
                    break
        starts.append(start)
        ends.append(end)
        previous_end = end
    return starts, ends


def silence_share(pauses: list[tuple[float, float]], windows: list[tuple[float, float]]) -> float:
    total = sum(end - start for start, end in windows)
    if total <= 0:
        return 0.0
    silent = 0.0
    for start, end in windows:
        for pause_start, pause_end in pauses:
            silent += max(0.0, min(end, pause_end) - max(start, pause_start))
    return silent / total


def distance_to_pause(pauses: list[tuple[float, float]], position: float) -> float:
    return min(min(abs(position - start), abs(position - end)) for start, end in pauses)


def render_srt(cues: list[tuple[float, float, str]], starts: list[float], ends: list[float]) -> str:
    blocks = []
    for index, ((_, _, text), start, end) in enumerate(zip(cues, starts, ends), start=1):
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{_wrap(text)}")
    return "\n\n".join(blocks) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Синхронизация SRT с паузами озвучки без ASR.")
    parser.add_argument("--captions", type=Path, default=HERE / "captions.srt", help="черновой SRT")
    parser.add_argument("--audio", type=Path, default=HERE / "narration.mp3", help="дикторская дорожка")
    parser.add_argument("--output", type=Path, default=None, help="куда записать уточнённый SRT")
    parser.add_argument("--draft-out", type=Path, default=None, help="сохранить исходный черновик по этому пути")
    parser.add_argument("--report", type=Path, default=None, help="JSON-отчёт о синхронизации")
    parser.add_argument("--noise-db", type=int, default=-35, help="порог тишины для silencedetect (дБ)")
    parser.add_argument("--min-pause", type=float, default=0.22, help="минимальная пауза, с")
    parser.add_argument("--penalty-sentence", type=float, default=0.9, help="допуск сдвига для конца предложения, с")
    parser.add_argument("--penalty-middle", type=float, default=0.30, help="допуск сдвига внутри фразы, с")
    parser.add_argument("--min-cue", type=float, default=MIN_CUE_SECONDS, help="минимальная длительность реплики, с")
    args = parser.parse_args(argv)

    output = args.output or args.captions
    captions_path = args.captions.expanduser().resolve()
    audio_path = args.audio.expanduser().resolve()
    if not captions_path.is_file():
        print(f"Ошибка: не найден SRT: {captions_path}", file=sys.stderr)
        return 2
    if not audio_path.is_file():
        print(f"Ошибка: не найдена дорожка: {audio_path}", file=sys.stderr)
        return 2
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("Ошибка: нужны ffmpeg и ffprobe в PATH.", file=sys.stderr)
        return 2

    try:
        duration = duration_of(audio_path, ffprobe)
        cues = parse_srt(captions_path)
        pauses = detect_pauses(ffmpeg, audio_path, noise_db=args.noise_db, min_pause=args.min_pause)
        boundaries, snapped = choose_boundaries(
            cues, pauses, duration,
            penalty_sentence=args.penalty_sentence,
            penalty_middle=args.penalty_middle,
            min_cue=args.min_cue,
        )
        starts, ends = cue_windows(cues, boundaries, pauses, duration)
    except RetimeError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2

    before = [(cue[0], cue[1]) for cue in cues]
    after = list(zip(starts, ends))
    if any(b <= a for a, b in after):
        print("Ошибка: после синхронизации получились некорректные таймкоды.", file=sys.stderr)
        return 2

    sentence_ends = [k for k, cue in enumerate(cues[:-1]) if SENTENCE_END.search(cue[2])]
    before_distances = sorted(distance_to_pause(pauses, cues[k][1]) for k in sentence_ends)
    after_distances = sorted(distance_to_pause(pauses, ends[k]) for k in sentence_ends)
    median = lambda values: values[len(values) // 2] if values else 0.0  # noqa: E731

    report = {
        "audio_duration_seconds": round(duration, 3),
        "cues": len(cues),
        "pauses_detected": len(pauses),
        "boundaries_moved": sum(1 for moved in snapped if moved),
        "max_shift_seconds": round(max((abs(a - b) for a, b in zip(boundaries, [c[1] for c in cues[:-1]])), default=0.0), 3),
        "sentence_ends": {
            "count": len(sentence_ends),
            "median_distance_to_pause_before": round(median(before_distances), 3),
            "median_distance_to_pause_after": round(median(after_distances), 3),
            "within_0.25s_before": sum(1 for value in before_distances if value <= 0.25),
            "within_0.25s_after": sum(1 for value in after_distances if value <= 0.25),
        },
        "silence_inside_cues_percent": {
            "before": round(silence_share(pauses, before) * 100, 2),
            "after": round(silence_share(pauses, after) * 100, 2),
        },
        "cue_duration_seconds": {
            "min": round(min(b - a for a, b in after), 3),
            "median": round(median(sorted(b - a for a, b in after)), 3),
            "max": round(max(b - a for a, b in after), 3),
        },
        "method": "silence-aware boundary snap (no ASR); text blocks preserved from the draft SRT",
        "parameters": {
            "noise_db": args.noise_db,
            "min_pause_seconds": args.min_pause,
            "penalty_sentence_seconds": args.penalty_sentence,
            "penalty_middle_seconds": args.penalty_middle,
            "min_cue_seconds": args.min_cue,
        },
    }

    if args.draft_out and captions_path == output:
        args.draft_out.expanduser().resolve().write_text(captions_path.read_text(encoding="utf-8"), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_srt(cues, starts, ends), encoding="utf-8")
    if args.report:
        args.report.expanduser().resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(f"Синхронизировано реплик: {len(cues)} · пауз найдено: {len(pauses)} · границ подвинуто: {report['boundaries_moved']}")
    print(
        "Концы предложений до/после (медиана до ближайшей паузы): "
        f"{report['sentence_ends']['median_distance_to_pause_before']:.3f} с → "
        f"{report['sentence_ends']['median_distance_to_pause_after']:.3f} с; "
        f"в пределах 0,25 с: {report['sentence_ends']['within_0.25s_before']}/"
        f"{report['sentence_ends']['count']} → {report['sentence_ends']['within_0.25s_after']}/"
        f"{report['sentence_ends']['count']}"
    )
    print(
        "Тишина внутри реплик: "
        f"{report['silence_inside_cues_percent']['before']:.1f}% → "
        f"{report['silence_inside_cues_percent']['after']:.1f}%"
    )
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
