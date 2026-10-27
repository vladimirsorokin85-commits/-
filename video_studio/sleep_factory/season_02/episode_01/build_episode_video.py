#!/usr/bin/env python3
"""Build a 16:9 H.264 MP4 from a finished audio mix and numbered stills.

Images can be evenly distributed over the real audio duration or aligned to act
boundaries from the finished scene timeline. A slow alternating zoom is used. The
render is CFR and its duration is derived from the audio, not hard-coded.

Example:
  python3 build_video.py --audio out/episode_01.mp3 --images episode_01/images \
      --output download/episode_01.mp4

FFmpeg and ffprobe are required; Python standard library only.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


class BuildError(RuntimeError):
    """Actionable project, dependency, or render error."""


def find_binary(name: str, project_dir: Path, explicit: str | None = None) -> str:
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
            candidate = Path(value).expanduser()
            if value and candidate.is_file():
                if name == "ffmpeg":
                    return str(candidate.resolve())
                if candidate.name.startswith("ffmpeg"):
                    sibling = candidate.with_name(candidate.name.replace("ffmpeg", "ffprobe", 1))
                    if sibling.is_file():
                        return str(sibling.resolve())
    found = shutil.which(name)
    if found:
        return found
    raise BuildError(
        f"Не найден {name}. Установите FFmpeg/ffprobe или укажите путь через ffmpeg_path.txt."
    )


def run(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True)
    except OSError as exc:
        raise BuildError(f"Не удалось запустить {label}: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout or "нет подробностей").strip()
        raise BuildError(f"{label} завершился с ошибкой:\n{detail[-3000:]}")
    return result


def probe_media(ffprobe: str, path: Path) -> dict[str, Any]:
    result = run(
        [ffprobe, "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,duration:format=duration,size",
         "-of", "json", str(path)],
        f"ffprobe ({path.name})",
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BuildError(f"ffprobe вернул некорректные данные для {path}") from exc


def probe_audio_duration(ffprobe: str, path: Path) -> float:
    info = probe_media(ffprobe, path)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise BuildError(f"В файле нет аудиодорожки: {path}")
    value = audio.get("duration") or info.get("format", {}).get("duration")
    try:
        duration = float(value)
    except (TypeError, ValueError) as exc:
        raise BuildError(f"Не удалось определить длительность аудио: {path}") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise BuildError(f"Некорректная длительность аудио: {path}")
    return duration


def expand_images(raw: list[str], base: Path) -> list[Path]:
    paths: list[Path] = []
    for value in raw:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = base / candidate
        text = str(candidate)
        if glob.has_magic(text):
            matches = [Path(item) for item in sorted(glob.glob(text))]
        elif candidate.is_dir():
            matches = sorted(candidate.iterdir(), key=lambda item: item.name.lower())
        else:
            matches = [candidate]
        paths.extend(p.resolve() for p in matches if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    # Keep first occurrence, preserving explicit order while avoiding duplicates.
    result: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    if not result:
        raise BuildError("Не найдены изображения. Передайте файлы, glob-шаблон или папку.")
    return result


def distribute_frames(
    total_frames: int, segments: int, weights: list[float] | None = None,
) -> list[int]:
    if total_frames <= 0 or segments <= 0:
        raise BuildError("Число кадров и изображений должно быть положительным.")
    if segments > total_frames:
        raise BuildError("Изображений больше, чем кадров итогового видео; уменьшите число изображений.")
    if weights is None:
        weights = [1.0] * segments
    if len(weights) != segments or any(not math.isfinite(w) or w <= 0 for w in weights):
        raise BuildError("Нужен положительный вес для каждого изображения.")
    total_weight = sum(weights)
    exact = [total_frames * weight / total_weight for weight in weights]
    counts = [math.floor(value) for value in exact]
    remainder = total_frames - sum(counts)
    order = sorted(range(segments), key=lambda i: exact[i] - counts[i], reverse=True)
    for index in order[:remainder]:
        counts[index] += 1
    if any(count < 1 for count in counts):
        raise BuildError("Временной интервал изображения слишком короткий для одного кадра.")
    return counts


def weights_from_act_timeline(timeline_path: Path, frame_acts: list[str]) -> list[float]:
    """Split each act's real timeline interval evenly across its assigned stills."""
    try:
        data = json.loads(timeline_path.read_text(encoding="utf-8"))
        scenes = data["scenes"]
        duration = float(data["duration_seconds"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise BuildError(f"Некорректный таймлайн сцен: {timeline_path}") from exc
    pattern = re.compile(r"^s02e01_(?P<act>a\d{2})_")
    starts: dict[str, float] = {}
    for scene in scenes:
        match = pattern.match(str(scene.get("id", "")))
        if match:
            starts.setdefault(match.group("act"), float(scene["start"]))
    acts = list(starts)
    if not acts or len(frame_acts) == 0:
        raise BuildError("Нет act-разметки для таймлайна и изображений.")
    if any(act not in starts for act in frame_acts):
        missing = sorted(set(frame_acts) - set(starts))
        raise BuildError(f"Неизвестные акты в frame-acts: {', '.join(missing)}")
    order = {act: index for index, act in enumerate(acts)}
    ranks = [order[act] for act in frame_acts]
    if ranks != sorted(ranks):
        raise BuildError("Активы изображений должны идти в том же порядке, что и главы сценария.")
    present_acts = list(dict.fromkeys(frame_acts))
    counts = {act: frame_acts.count(act) for act in present_acts}
    weights: list[float] = []
    for index, act in enumerate(present_acts):
        start = 0.0 if index == 0 else starts[act]
        end = starts[present_acts[index + 1]] if index + 1 < len(present_acts) else duration
        interval = end - start
        if interval <= 0:
            raise BuildError(f"У акта {act} некорректный интервал в таймлайне.")
        weights.extend([interval / counts[act]] * counts[act])
    return weights


def concat_quote(path: Path) -> str:
    # FFmpeg concat-demuxer quoting: backslash-escape apostrophes inside single quotes.
    return "'" + str(path.resolve()).replace("'", "'\\''") + "'"


def encode_stills(
    *, ffmpeg: str, images: list[Path], frame_counts: list[int], folder: Path,
    width: int, height: int, fps: int, crf: int, preset: str,
) -> Path:
    segment_dir = folder / f"segments_crf_{crf}"
    shutil.rmtree(segment_dir, ignore_errors=True)
    segment_dir.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []

    for index, (image, frame_count) in enumerate(zip(images, frame_counts)):
        segment = segment_dir / f"segment_{index:03d}.mp4"
        # Small, slow alternating zooms add life without flashing or fast movement.
        if index % 2 == 0:
            zoom = "min(zoom+0.000035,1.045)"
        else:
            zoom = "if(eq(on,0),1.045,max(zoom-0.000035,1.0))"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={width}:{height},"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={fps}:s={width}x{height}:fps={fps},format=yuv420p"
        )
        command = [
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", "1", "-i", str(image),
            "-vf", vf, "-frames:v", str(frame_count), "-r", str(fps),
            "-fps_mode", "cfr", "-an", "-c:v", "libx264", "-preset", preset,
            "-tune", "stillimage", "-crf", str(crf), "-pix_fmt", "yuv420p",
            str(segment),
        ]
        run(command, f"кодирование кадра {image.name}")
        segment_paths.append(segment)

    list_path = folder / f"segments_crf_{crf}.txt"
    list_path.write_text(
        "".join(f"file {concat_quote(path)}\n" for path in segment_paths), encoding="utf-8"
    )
    video_only = folder / f"video_only_crf_{crf}.mp4"
    run(
        [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(video_only)],
        "склейка видеосегментов",
    )
    return video_only


def mux_audio(
    *, ffmpeg: str, video_only: Path, audio: Path, output: Path,
    duration: float, audio_bitrate: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-i", str(video_only),
         "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", f"{audio_bitrate}k", "-ac", "1", "-ar", "44100",
         "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)],
        "сведение видео и аудио",
    )


def verify_output(ffprobe: str, output: Path, *, width: int, height: int, fps: int, target: float) -> dict[str, Any]:
    info = probe_media(ffprobe, output)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise BuildError("Итоговый MP4 должен содержать видео- и аудиодорожку.")
    if (int(video.get("width", 0)), int(video.get("height", 0))) != (width, height):
        raise BuildError(f"Неверное разрешение: {video.get('width')}×{video.get('height')}; ожидалось {width}×{height}.")
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise BuildError(f"Ожидались H.264/AAC, получены {video.get('codec_name')}/{audio.get('codec_name')}.")
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        numerator, denominator = (float(part) for part in rate.split("/", 1))
        actual_fps = numerator / denominator
    except (ValueError, ZeroDivisionError):
        actual_fps = 0.0
    if abs(actual_fps - fps) > 0.05:
        raise BuildError(f"Неверная частота кадров: {rate}; ожидалось около {fps} fps.")
    value = info.get("format", {}).get("duration") or video.get("duration")
    actual_duration = float(value)
    tolerance = max(0.15, 2 / fps)
    if abs(actual_duration - target) > tolerance:
        raise BuildError(f"Длительность {actual_duration:.3f} с отличается от целевой {target:.3f} с.")
    return {
        "status": "passed", "duration_seconds": round(actual_duration, 3),
        "resolution": [width, height], "fps": round(actual_fps, 3),
        "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name"),
        "file_size_bytes": int(info.get("format", {}).get("size", 0) or 0),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path, help="Готовый дикторский микс")
    parser.add_argument("--images", required=True, nargs="+", help="Изображения, glob-шаблоны или папки")
    parser.add_argument("--timeline", type=Path, help="Таймлайн mix_stream.py для привязки кадров к актам")
    parser.add_argument("--frame-acts", type=Path, help="JSON с frame_acts: акт на каждое изображение")
    parser.add_argument("--output", required=True, type=Path, help="Итоговый MP4")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--crf", type=int, default=23, help="Качество H.264; меньшее значение даёт лучшее изображение")
    parser.add_argument("--preset", default="slow")
    parser.add_argument("--audio-bitrate", type=int, default=192, help="Битрейт AAC; качество важнее размера файла")
    parser.add_argument("--max-mb", type=float, default=None, help="Необязательный ориентир размера; качество ради него не ухудшается")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args(argv)

    try:
        audio = args.audio.expanduser().resolve()
        if not audio.is_file():
            raise BuildError(f"Не найден аудиомикс: {audio}")
        output = args.output.expanduser().resolve()
        images = expand_images(args.images, Path.cwd())
        if not 22 <= len(images) <= 40:
            raise BuildError(f"Для полного выпуска нужны 22–40 иллюстраций; получено {len(images)}.")
        ffmpeg = find_binary("ffmpeg", output.parent, args.ffmpeg)
        ffprobe = find_binary("ffprobe", output.parent, args.ffprobe)
        duration = probe_audio_duration(ffprobe, audio)
        if duration < 35 * 60:
            raise BuildError(f"Видео короче 35 минут: {duration / 60:.2f} мин.")
        frames_total = round(duration * args.fps)
        frame_acts: list[str] | None = None
        weights: list[float] | None = None
        if args.frame_acts:
            if not args.timeline:
                raise BuildError("--frame-acts требует --timeline.")
            try:
                act_data = json.loads(args.frame_acts.expanduser().read_text(encoding="utf-8"))
                frame_acts = act_data["frame_acts"] if isinstance(act_data, dict) else act_data
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise BuildError(f"Некорректная разметка кадров: {args.frame_acts}") from exc
            if not isinstance(frame_acts, list) or len(frame_acts) != len(images):
                raise BuildError("Число frame_acts должно совпадать с числом изображений.")
            weights = weights_from_act_timeline(args.timeline.expanduser().resolve(), frame_acts)
        frame_counts = distribute_frames(frames_total, len(images), weights=weights)
        if args.width <= 0 or args.height <= 0 or args.width % 2 or args.height % 2:
            raise BuildError("Ширина и высота должны быть положительными чётными числами.")
        if args.fps < 1 or args.fps > 60:
            raise BuildError("Частота кадров должна быть в диапазоне 1–60 fps.")
        if not 16 <= args.crf <= 40:
            raise BuildError("CRF должен быть в диапазоне 16–40.")
        if not 32 <= args.audio_bitrate <= 320:
            raise BuildError("Битрейт AAC должен быть в диапазоне 32–320 кбит/с.")
        if args.max_mb is not None and args.max_mb <= 0:
            raise BuildError("--max-mb должен быть положительным числом.")

        output.parent.mkdir(parents=True, exist_ok=True)
        report: dict[str, Any]
        with tempfile.TemporaryDirectory(prefix="sleep-video-", dir=output.parent) as temp_raw:
            temp = Path(temp_raw)
            video_only = encode_stills(
                ffmpeg=ffmpeg, images=images, frame_counts=frame_counts, folder=temp,
                width=args.width, height=args.height, fps=args.fps,
                crf=args.crf, preset=args.preset,
            )
            mux_audio(
                ffmpeg=ffmpeg, video_only=video_only, audio=audio, output=output,
                duration=duration, audio_bitrate=args.audio_bitrate,
            )
            report = verify_output(
                ffprobe, output, width=args.width, height=args.height,
                fps=args.fps, target=duration,
            )
            report["video_crf"] = args.crf
            report["video_preset"] = args.preset
            report["audio_bitrate_kbps"] = args.audio_bitrate
            report["image_timing"] = "act-aligned" if frame_acts else "uniform"
            report["frame_counts"] = frame_counts
            if frame_acts is not None:
                report["frame_acts"] = frame_acts
            report["size_target_mb"] = args.max_mb
            report["size_target_met"] = (
                None if args.max_mb is None
                else output.stat().st_size <= int(args.max_mb * 1_000_000)
            )

        qc_path = output.with_suffix(".qc.json")
        qc_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Готово: {output}")
        print(f"Хронометраж: {duration / 60:.2f} мин; кадров: {frames_total}; иллюстраций: {len(images)}")
        print(f"Размер: {output.stat().st_size / 1_000_000:.2f} МБ; QC: {qc_path}")
        if report.get("size_target_met") is False:
            print("Размер выше необязательного ориентира; качество не снижалось ради размера.")
        return 0
    except (BuildError, OSError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
