#!/usr/bin/env python3
"""Stream-mix narration with a quiet spacecraft ambience bed.

Example:
  python3 mix_stream.py episode_01/script.md out/episode_01 --target-seconds 2100

Python standard library only. FFmpeg and ffprobe are required. Scene headings:
  ### [s01e01_a01] [voice-00] [ГУДЕНИЕ] Scene title
  narration text...

Voice files are resolved from voice2/<scene-id>.(opus|mp3|wav|m4a).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

HEADER = re.compile(
    r"^###\s+\[(?P<scene_id>[A-Za-z0-9_-]+)\]\s+"
    r"\[(?P<voice>voice-\d{2})\](?:\s+\[(?P<tag>[^\]]+)\])?\s*(?P<title>.*)$"
)
SPOKEN_FORBIDDEN = re.compile(r"[A-Za-z0-9]")
VOICE_EXTENSIONS = (".opus", ".mp3", ".wav", ".m4a", ".aac")
MIN_SECONDS = 35 * 60
MAX_SECONDS = 60 * 60
DEFAULT_SPEECH_SHARE = 0.96


class BuildError(RuntimeError):
    """Actionable input, dependency, or render error."""


@dataclass(frozen=True)
class Scene:
    scene_id: str
    voice: str
    tag: str
    title: str
    text: str
    audio: Path | None = None
    duration: float = 0.0
    start: float = 0.0
    end: float = 0.0


def _find_binary(name: str, project_dir: Path, explicit: str | None = None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise BuildError(f"Указанный бинарник {name} не найден: {explicit}")
    for folder in (project_dir, project_dir.parent, Path.cwd()):
        hint = folder / "ffmpeg_path.txt"
        if hint.is_file():
            value = hint.read_text(encoding="utf-8").strip()
            if value:
                candidate = Path(value).expanduser()
                if candidate.is_file():
                    if name == "ffprobe" and candidate.name.startswith("ffmpeg"):
                        sibling = candidate.with_name(candidate.name.replace("ffmpeg", "ffprobe", 1))
                        if sibling.is_file():
                            return str(sibling.resolve())
                    if name == "ffmpeg":
                        return str(candidate.resolve())
    found = shutil.which(name)
    if found:
        return found
    raise BuildError(
        f"Не найден {name}. Установите FFmpeg/ffprobe или укажите путь через ffmpeg_path.txt."
    )


def _run(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True)
    except OSError as exc:
        raise BuildError(f"Не удалось запустить {label}: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout or "нет подробностей").strip()
        raise BuildError(f"{label} завершился с ошибкой:\n{detail[-3000:]}")
    return result


def parse_script(path: Path, *, lint: bool = True) -> list[Scene]:
    """Parse scene headings and their spoken text from a Markdown script."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise BuildError(f"Не удалось прочитать сценарий {path}: {exc}") from exc

    scenes: list[Scene] = []
    current: tuple[re.Match[str], list[str]] | None = None
    for line in lines + ["### [END] [voice-00] [END] "]:
        match = HEADER.match(line)
        if match:
            if current:
                header, body_lines = current
                body = " ".join(" ".join(body_lines).split())
                if body:
                    scenes.append(_scene_from(header, body, lint))
            if match.group("scene_id") == "END":
                current = None
                continue
            current = (match, [])
        elif current:
            # Markdown emphasis is harmless; keep the spoken words, not formatting markers.
            current[1].append(line)
    if not scenes:
        raise BuildError(
            "В сценарии не найдены сцены. Нужен заголовок вида "
            "### [s01e01_a01] [voice-00] [ГУДЕНИЕ] Название."
        )
    ids = [scene.scene_id for scene in scenes]
    duplicates = sorted({scene_id for scene_id in ids if ids.count(scene_id) > 1})
    if duplicates:
        raise BuildError(f"Повторяются ID сцен: {', '.join(duplicates)}")
    return scenes


def _scene_from(header: re.Match[str], body: str, lint: bool) -> Scene:
    scene_id = header.group("scene_id")
    voice = header.group("voice")
    if voice not in {"voice-04", "voice-05", "voice-06"}:
        raise BuildError(f"Неизвестный voice ID в сцене {scene_id}: {voice}")
    if lint:
        found = SPOKEN_FORBIDDEN.search(body)
        if found:
            char = found.group(0)
            raise BuildError(
                f"В тексте для озвучки сцены {scene_id} найден символ «{char}» "
                "(латинская буква или цифра). Напишите число словами либо запустите с --no-lint."
            )
    return Scene(
        scene_id=scene_id,
        voice=voice,
        tag=(header.group("tag") or "").strip(),
        title=(header.group("title") or "").strip(),
        text=body,
    )


def probe_duration(ffprobe: str, path: Path) -> float:
    result = _run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", str(path)],
        f"ffprobe ({path.name})",
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise BuildError(f"Не удалось определить длительность аудио: {path}") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise BuildError(f"У аудиофайла некорректная длительность: {path}")
    return duration


def resolve_voice_files(scenes: list[Scene], voice_dir: Path) -> list[Scene]:
    resolved: list[Scene] = []
    for scene in scenes:
        path = next((voice_dir / f"{scene.scene_id}{ext}" for ext in VOICE_EXTENSIONS
                     if (voice_dir / f"{scene.scene_id}{ext}").is_file()), None)
        if path is None:
            raise BuildError(
                f"Нет озвучки для сцены {scene.scene_id}. Ожидался файл в {voice_dir} "
                f"с одним из расширений: {', '.join(VOICE_EXTENSIONS)}"
            )
        resolved.append(Scene(**{**asdict(scene), "audio": path.resolve()}))
    return resolved


def build_timeline(
    scenes: list[Scene], *, target: float | None, intro: float, outro: float,
    min_gap: float, max_gap: float,
) -> tuple[list[Scene], float, float]:
    voice_total = sum(scene.duration for scene in scenes)
    count_gaps = max(0, len(scenes) - 1)
    minimum = intro + outro + voice_total + count_gaps * min_gap
    if target is None:
        # Keep the mix speech-forward, with short natural scene transitions.
        target = max(MIN_SECONDS, min(MAX_SECONDS, voice_total / DEFAULT_SPEECH_SHARE))
        target = max(target, minimum)
    if not MIN_SECONDS <= target <= MAX_SECONDS:
        raise BuildError("Целевая длительность должна быть в диапазоне 2100–3600 секунд (30–60 минут).")
    available = target - intro - outro - voice_total
    gap = available / count_gaps if count_gaps else 0.0
    if gap < min_gap - 0.02:
        raise BuildError(
            f"Озвучка слишком длинная для выбранного хронометража: средний межсценный интервал "
            f"{gap:.1f} с, минимум {min_gap:.1f} с. Сократите текст или увеличьте target."
        )
    if gap > max_gap:
        raise BuildError(
            f"В озвучке пока мало текста для выбранного хронометража: пришлось бы оставить "
            f"паузы по {gap:.1f} с. Допишите сценарий или сократите целевую длительность; "
            f"допустимый максимум — {max_gap:.1f} с."
        )

    cursor = intro
    result: list[Scene] = []
    for index, scene in enumerate(scenes):
        start = cursor
        end = start + scene.duration
        result.append(Scene(**{**asdict(scene), "start": start, "end": end}))
        cursor = end + (gap if index < len(scenes) - 1 else 0)
    return result, target, gap


def render_mix(
    scenes: list[Scene], target: float, output: Path, *, ffmpeg: str,
    hum_gain: float, air_gain: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command: list[str] = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error"]
    for scene in scenes:
        assert scene.audio is not None
        command += ["-i", str(scene.audio)]

    count = len(scenes)
    command += [
        "-f", "lavfi", "-t", f"{target:.3f}", "-i",
        "sine=frequency=48:sample_rate=44100",
        "-f", "lavfi", "-t", f"{target:.3f}", "-i",
        "anoisesrc=color=brown:amplitude=0.12:sample_rate=44100",
    ]
    filters: list[str] = []
    voice_labels: list[str] = []
    for index, scene in enumerate(scenes):
        delay_ms = round(scene.start * 1000)
        voice_fx = "highpass=f=75,lowpass=f=8500"
        if scene.voice == "voice-05":
            voice_fx = "highpass=f=220,lowpass=f=5600"
        label = f"v{index}"
        filters.append(
            f"[{index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
            f"{voice_fx},volume=1.0,adelay=delays={delay_ms}:all=1[{label}]"
        )
        voice_labels.append(f"[{label}]")
    filters.append(
        f"{''.join(voice_labels)}amix=inputs={count}:duration=longest:"
        "dropout_transition=0:normalize=0[voices]"
    )
    hum_index = count
    air_index = count + 1
    filters.append(f"[{hum_index}:a]volume={hum_gain:.4f}[hum]")
    filters.append(f"[{air_index}:a]lowpass=f=420,volume={air_gain:.4f}[air]")
    filters.append("[hum][air]amix=inputs=2:duration=first:normalize=0[bed]")
    filters.append("[voices]asplit=2[voice_main][voice_sidechain]")
    filters.append(
        f"[voice_sidechain]apad=whole_dur={target:.3f}[voice_sidechain_padded]"
    )
    filters.append(
        "[bed][voice_sidechain_padded]sidechaincompress=threshold=0.025:ratio=4:"
        "attack=250:release=900[ducked]"
    )
    filters.append(
        f"[voice_main][ducked]amix=inputs=2:duration=longest:normalize=0,"
        f"alimiter=limit=0.90,apad=whole_dur={target:.3f},"
        f"atrim=duration={target:.3f},asetpts=PTS-STARTPTS[outa]"
    )
    command += [
        "-filter_complex", ";".join(filters), "-map", "[outa]", "-t", f"{target:.3f}",
        "-c:a", "libmp3lame", "-b:a", "96k", "-ac", "1", "-ar", "44100",
        "-write_xing", "0", str(output),
    ]
    _run(command, "сведение речи и амбиента")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="Markdown-сценарий со сценами")
    parser.add_argument("output_base", type=Path, help="Путь и имя итогового микса без расширения")
    parser.add_argument("--voice-dir", type=Path, help="Папка с voice2-фрагментами; по умолчанию рядом со сценарием")
    parser.add_argument("--target-seconds", type=float, help="Целевая длительность, 2100–3600 секунд; по умолчанию вычисляется по речи")
    parser.add_argument("--intro", type=float, default=6.0, help="Вступительный амбиент в секундах (по умолчанию 6)")
    parser.add_argument("--outro", type=float, default=12.0, help="Финальный амбиент в секундах (по умолчанию 12)")
    parser.add_argument("--min-gap", type=float, default=3.0, help="Минимум секунд между сценами")
    parser.add_argument("--max-gap", type=float, default=20.0, help="Максимум секунд между сценами")
    parser.add_argument("--hum-gain", type=float, default=0.018, help="Громкость низкого гула, 0–0.1")
    parser.add_argument("--air-gain", type=float, default=0.035, help="Громкость мягкой вентиляции, 0–0.2")
    parser.add_argument("--no-lint", action="store_true", help="Не проверять цифры и латиницу в дикторском тексте")
    parser.add_argument("--ffmpeg", help="Явный путь к ffmpeg")
    parser.add_argument("--ffprobe", help="Явный путь к ffprobe")
    args = parser.parse_args(argv)

    try:
        script = args.script.expanduser().resolve()
        scenes = parse_script(script, lint=not args.no_lint)
        voice_dir = (args.voice_dir.expanduser().resolve() if args.voice_dir
                     else (script.parent / "voice2").resolve())
        ffmpeg = _find_binary("ffmpeg", script.parent, args.ffmpeg)
        ffprobe = _find_binary("ffprobe", script.parent, args.ffprobe)
        scenes = resolve_voice_files(scenes, voice_dir)
        scenes = [Scene(**{**asdict(scene), "duration": probe_duration(ffprobe, scene.audio)})
                  for scene in scenes]
        target = args.target_seconds
        if target is not None and not MIN_SECONDS <= target <= MAX_SECONDS:
            raise BuildError("--target-seconds должен быть от 2100 до 3600.")
        timeline, target_value, gap = build_timeline(
            scenes, target=target, intro=args.intro, outro=args.outro,
            min_gap=args.min_gap, max_gap=args.max_gap,
        )
        voice_total = sum(scene.duration for scene in timeline)
        if voice_total / target_value < 0.85:
            raise BuildError(
                f"Доля речи составила {voice_total / target_value:.1%}; нужно не менее 85%. "
                "Добавьте содержательную речь или сократите паузы."
            )
        output_base = args.output_base.expanduser().resolve()
        output = output_base.with_suffix(".mp3")
        render_mix(
            timeline, target_value, output, ffmpeg=ffmpeg,
            hum_gain=args.hum_gain, air_gain=args.air_gain,
        )
        data = {
            "duration_seconds": round(target_value, 3),
            "voice_seconds": round(sum(scene.duration for scene in timeline), 3),
            "speech_share": round(sum(scene.duration for scene in timeline) / target_value, 4),
            "inter_scene_gap_seconds": round(gap, 3),
            "scenes": [
                {"id": s.scene_id, "voice": s.voice, "tag": s.tag, "title": s.title,
                 "start": round(s.start, 3), "end": round(s.end, 3),
                 "audio": os.path.relpath(s.audio, start=output_base.parent)}
                for s in timeline
            ],
        }
        timeline_path = output_base.with_suffix(".timeline.json")
        timeline_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Сцен: {len(timeline)}; речь: {data['voice_seconds'] / 60:.1f} мин; "
              f"итог: {target_value / 60:.1f} мин; доля речи: {data['speech_share']:.0%}; "
              f"пауза: {gap:.1f} с")
        print(f"Микс: {output}\nТаймлайн: {timeline_path}")
        return 0
    except BuildError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
