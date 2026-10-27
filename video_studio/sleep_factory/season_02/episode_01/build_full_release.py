#!/usr/bin/env python3
"""Build and QC the complete S02E01 release from the 67 scene MP3s.

This performs the approved series-intro prepend, mix, 22-frame body render,
subtitle/chapter generation with intro offsets, final WebRTC-VAD/loudness QC,
and GitHub-friendly packaging. It refuses to begin unless every scene MP3 and
all ordered frame assets are present.

Example:
  python3 build_full_release.py --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
INTRO = HERE.parents[1] / "season_01" / "series_intro_preview.mp4"
RENDERED = HERE / "rendered"
MIX_BASE = RENDERED / "s02e01_mix"
BODY = RENDERED / "s02e01_body.mp4"
FINAL = RENDERED / "s02e01_full.mp4"
INTRO_NORMALIZED = RENDERED / "s02e01_intro_normalized.mp4"
CONCAT_LIST = RENDERED / ".s02e01_concat.txt"
SRT = RENDERED / "s02e01_full.srt"
CHAPTERS = RENDERED / "s02e01_full_chapters.txt"
QC_REPORT = RENDERED / "s02e01_full.active-speech.qc.json"


class ReleaseError(RuntimeError):
    """Actionable release-build error."""


def run(command: list[str], label: str, *, cwd: Path = HERE, env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==", flush=True)
    try:
        subprocess.run(command, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise ReleaseError(f"{label} завершился с кодом {exc.returncode}.") from exc
    except OSError as exc:
        raise ReleaseError(f"Не удалось запустить {label}: {exc}") from exc


def ffprobe_duration(ffprobe: str, path: Path) -> float:
    result = subprocess.run([
        ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Не удалось считать длительность {path}.") from exc


def concat_quote(path: Path) -> str:
    return "'" + str(path.resolve()).replace("'", "'\\''") + "'"


def check_inputs(ffprobe: str) -> tuple[list[str], float]:
    script = (HERE / "script.md").read_text(encoding="utf-8")
    scene_ids = re.findall(r"(?m)^### \[(s02e01_a\d{2}_[a-z]\d{2})\] \[voice-\d{2}\]", script)
    if len(scene_ids) != 67 or len(set(scene_ids)) != 67:
        raise ReleaseError(f"Ожидалось 67 уникальных сцен сценария, найдено {len(scene_ids)}.")
    voice_dir = HERE / "voice2"
    missing = [scene_id + ".mp3" for scene_id in scene_ids if not (voice_dir / (scene_id + ".mp3")).is_file()]
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "…" if len(missing) > 8 else ""
        raise ReleaseError(f"Не хватает {len(missing)} MP3: {preview}{suffix}")

    try:
        manifest = json.loads((HERE / "frame_acts.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError("Не удалось прочитать frame_acts.json.") from exc
    acts = manifest.get("frame_acts")
    images = manifest.get("images")
    if not isinstance(acts, list) or not isinstance(images, list) or len(acts) != len(images):
        raise ReleaseError("frame_acts.json должен содержать парные списки frame_acts и images.")
    if len(images) != 22 or acts != [f"a{i:02d}" for i in range(1, 23)]:
        raise ReleaseError("Для S02E01 ожидаются 22 упорядоченных кадра для актов a01–a22.")
    missing_images = [str(path) for path in images if not (HERE / path).is_file()]
    if missing_images:
        raise ReleaseError("Не найдены кадры: " + ", ".join(missing_images))
    if len(set(images)) != len(images):
        raise ReleaseError("Список кадров содержит повторяющиеся файлы.")
    if not INTRO.is_file():
        raise ReleaseError(f"Не найдена утверждённая заставка: {INTRO}")
    return images, ffprobe_duration(ffprobe, INTRO)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"), help="Путь к FFmpeg")
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe"), help="Путь к ffprobe")
    parser.add_argument("--crf", type=int, default=32, help="CRF H.264 для длинного выпуска")
    parser.add_argument("--preset", default="veryfast")
    parser.add_argument("--audio-bitrate", type=int, default=128)
    parser.add_argument("--intro-pad", type=float, default=0.5,
                        help="Короткая пауза/амбиент после заставки и перед первой репликой")
    parser.add_argument("--min-gap", type=float, default=1.0,
                        help="Минимальная пауза между 67 сценами; краткая пауза помогает пройти VAD-порог")
    parser.add_argument("--keep-intermediates", action="store_true",
                        help="Не удалять временные body/intro MP4 после успешной склейки")
    args = parser.parse_args(argv)

    try:
        ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
        ffprobe = args.ffprobe or shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise ReleaseError("Нужны FFmpeg и ffprobe; передайте --ffmpeg и --ffprobe.")
        if not 16 <= args.crf <= 40 or not 32 <= args.audio_bitrate <= 320:
            raise ReleaseError("CRF должен быть 16–40, AAC bitrate — 32–320 kbit/s.")
        if not 0 <= args.intro_pad <= 10:
            raise ReleaseError("--intro-pad должен быть в диапазоне 0–10 секунд.")
        if not 0 <= args.min_gap <= 10:
            raise ReleaseError("--min-gap должен быть в диапазоне 0–10 секунд.")
        images, intro_duration = check_inputs(ffprobe)
        RENDERED.mkdir(parents=True, exist_ok=True)
        for path in (MIX_BASE.with_suffix(".mp3"), MIX_BASE.with_suffix(".timeline.json"),
                     BODY, INTRO_NORMALIZED, FINAL, SRT, CHAPTERS, QC_REPORT):
            if path.exists():
                path.unlink()

        run([
            sys.executable, "mix_stream.py", "script.md", str(MIX_BASE.relative_to(HERE)),
            "--intro", str(args.intro_pad), "--outro", "12", "--min-gap", str(args.min_gap),
            "--ffmpeg", ffmpeg, "--ffprobe", ffprobe,
        ], "Сведение озвучки", cwd=HERE)
        timeline = MIX_BASE.with_suffix(".timeline.json")
        audio = MIX_BASE.with_suffix(".mp3")
        if not timeline.is_file() or not audio.is_file():
            raise ReleaseError("Микшер не создал MP3 и timeline JSON.")

        manifest_path = HERE / "frame_acts.json"
        run([
            sys.executable, "build_episode_video.py", "--audio", str(audio.relative_to(HERE)),
            "--images", *images, "--timeline", str(timeline.relative_to(HERE)),
            "--frame-acts", str(manifest_path.relative_to(HERE)), "--output", str(BODY.relative_to(HERE)),
            "--crf", str(args.crf), "--preset", args.preset,
            "--audio-bitrate", str(args.audio_bitrate), "--ffmpeg", ffmpeg, "--ffprobe", ffprobe,
        ], "Рендер 22 сюжетных кадров", cwd=HERE)

        run([
            sys.executable, "build_subtitles.py", "--script", "script.md", "--timeline",
            str(timeline.relative_to(HERE)), "--output", str(SRT.relative_to(HERE)),
            "--offset", f"{intro_duration:.6f}",
        ], "Субтитры с учётом заставки", cwd=HERE)
        run([
            sys.executable, "build_chapters.py", "--script", "script.md", "--timeline",
            str(timeline.relative_to(HERE)), "--output", str(CHAPTERS.relative_to(HERE)),
            "--intro-offset", f"{intro_duration:.6f}",
        ], "Главы YouTube с учётом заставки", cwd=HERE)

        run([
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-i", str(INTRO),
            "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-ac", "1", "-ar", "44100", "-movflags", "+faststart",
            str(INTRO_NORMALIZED),
        ], "Подготовка утверждённой заставки к склейке", cwd=HERE)
        CONCAT_LIST.write_text(
            f"file {concat_quote(INTRO_NORMALIZED)}\nfile {concat_quote(BODY)}\n", encoding="utf-8"
        )
        run([
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(CONCAT_LIST), "-c", "copy", "-movflags", "+faststart", str(FINAL),
        ], "Склейка заставки и длинного выпуска", cwd=HERE)
        if not FINAL.is_file():
            raise ReleaseError("Не создан финальный MP4.")

        env = os.environ.copy()
        arena_packages = REPO / ".arena" / "python_packages"
        if arena_packages.is_dir():
            old_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(arena_packages) + (os.pathsep + old_pythonpath if old_pythonpath else "")
        run([
            sys.executable, "qc_episode_media.py", str(FINAL.relative_to(HERE)),
            "--ffmpeg", ffmpeg, "--ffprobe", ffprobe,
            "--report", str(QC_REPORT.relative_to(HERE)),
        ], "Полное декодирование и финальный QC речи", cwd=HERE, env=env)
        report = json.loads(QC_REPORT.read_text(encoding="utf-8"))
        if report.get("status") != "passed":
            raise ReleaseError("QC финального видео не пройден; пакет публикации не создавался.")

        run([
            sys.executable, "package_video.py", str(FINAL.relative_to(HERE)),
            "--duration", str(report["duration_seconds"]),
            "--speech-share", str(report["active_speech"]["speech_share"]),
        ], "Пакет загрузки для GitHub", cwd=HERE)

        try:
            CONCAT_LIST.unlink(missing_ok=True)
            if not args.keep_intermediates:
                BODY.unlink(missing_ok=True)
                INTRO_NORMALIZED.unlink(missing_ok=True)
        except OSError as exc:
            print(f"Предупреждение: не удалось удалить промежуточный файл: {exc}", file=sys.stderr)
        print("\nВыпуск собран и прошёл QC:")
        print(f"MP4: {FINAL}")
        print(f"SRT: {SRT}")
        print(f"Главы: {CHAPTERS}")
        print(f"QC: {QC_REPORT}")
        print(f"Пакет: {HERE / 'rendered' / 'github_download'}")
        return 0
    except (ReleaseError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Ошибка сборки релиза: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
