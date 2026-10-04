#!/usr/bin/env python3
"""Build a 9:16 Reel from narration, a visual playlist, optional music and captions.

Only Python's standard library is required. FFmpeg and ffprobe must be on PATH.
Run with: python3 -m video_studio.reels project.json
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MIN_DURATION_SECONDS = 60.0
MAX_DURATION_SECONDS = 20 * 60.0
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}


class ReelBuildError(RuntimeError):
    """An actionable project, dependency, or render error."""


@dataclass(frozen=True)
class VisualSpec:
    path: Path
    kind: str
    focus_x: float = 0.5
    focus_y: float = 0.5
    start_seconds: float = 0.0
    duration_seconds: float | None = None
    loop: bool = False
    source_duration_seconds: float | None = None
    manual_focus: bool = False
    focus_kind: str = "center"
    fit_mode: str | None = None


@dataclass(frozen=True)
class Scene:
    path: Path
    kind: str
    frames: int
    focus_x: float
    focus_y: float
    start_seconds: float
    loop: bool
    zoom_in: bool
    focus_kind: str = "center"
    fit_mode: str = "crop"


@dataclass(frozen=True)
class Settings:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    shot_seconds: float = 4.0
    chunk_scenes: int = 12
    crf: int = 20
    preset: str = "medium"
    music_gain: float = 0.12
    caption_mode: str = "burn"
    smart_crop: bool = False


@dataclass(frozen=True)
class Project:
    manifest: Path
    title: str
    audio: Path
    visuals: tuple[VisualSpec, ...]
    output: Path
    music: Path | None
    captions: Path | None
    duration_seconds: float | None
    settings: Settings


def _which(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise ReelBuildError(
            f"Не найден {binary}. Установите FFmpeg и убедитесь, что ffmpeg и ffprobe находятся в PATH."
        )
    return path


def _run(cmd: list[str], *, what: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise ReelBuildError(f"Не удалось запустить {what}: {exc}") from exc
    if result.returncode:
        details = (result.stderr or result.stdout or "нет подробностей").strip()
        raise ReelBuildError(f"{what} завершился с ошибкой:\n{details[-2500:]}")
    return result


def probe_duration(path: Path, stream_kind: str | None = None) -> float:
    """Read a media stream/container duration with ffprobe."""
    ffprobe = _which("ffprobe")
    cmd = [ffprobe, "-v", "error"]
    if stream_kind in {"audio", "video"}:
        cmd += ["-select_streams", "a:0" if stream_kind == "audio" else "v:0"]
    cmd += ["-show_entries", "stream=codec_type,duration:format=duration", "-of", "json", str(path)]
    result = _run(cmd, what=f"ffprobe ({path.name})")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReelBuildError(f"ffprobe вернул некорректные данные для {path}.") from exc
    streams = info.get("streams", [])
    if stream_kind and not streams:
        label = "аудио" if stream_kind == "audio" else "видео"
        raise ReelBuildError(f"В файле не найдена {label}-дорожка: {path}")
    if stream_kind and streams[0].get("codec_type") not in (None, stream_kind):
        label = "аудио" if stream_kind == "audio" else "видео"
        raise ReelBuildError(f"В файле не найдена {label}-дорожка: {path}")
    value: Any = streams[0].get("duration") if streams else None
    if value in (None, "N/A"):
        value = info.get("format", {}).get("duration")
    try:
        duration = float(value)
    except (TypeError, ValueError) as exc:
        kind = "аудиодорожку" if stream_kind == "audio" else "видеодорожку"
        raise ReelBuildError(f"Не удалось определить длительность {kind}: {path}") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise ReelBuildError(f"У файла нет корректной длительности: {path}")
    return duration


def verify_output(path: Path, *, duration: float, width: int, height: int, fps: int) -> dict[str, Any]:
    """Fail the build if the final MP4 does not match the requested delivery profile."""
    ffprobe = _which("ffprobe")
    cmd = [
        ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels,duration:format=duration,size",
        "-of", "json", str(path),
    ]
    result = _run(cmd, what="проверка готового MP4")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReelBuildError("ffprobe вернул некорректные данные о готовом MP4.") from exc
    streams = info.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise ReelBuildError("Готовый MP4 должен содержать и видеодорожку, и аудиодорожку.")
    if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        raise ReelBuildError(
            f"Неверное разрешение результата: {video.get('width')}×{video.get('height')}; ожидалось {width}×{height}."
        )
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise ReelBuildError(
            f"Неверные кодеки результата: видео={video.get('codec_name')}, аудио={audio.get('codec_name')}; ожидались H.264 + AAC."
        )
    measured_fps = 0.0
    rate = "unknown"
    for candidate in (video.get("avg_frame_rate"), video.get("r_frame_rate")):
        if not candidate:
            continue
        try:
            numerator, denominator = (float(part) for part in candidate.split("/", 1))
            candidate_fps = numerator / denominator
        except (ValueError, ZeroDivisionError):
            continue
        if math.isfinite(candidate_fps) and candidate_fps > 0:
            measured_fps, rate = candidate_fps, candidate
            break
    if not measured_fps or abs(measured_fps - fps) > 0.05:
        raise ReelBuildError(f"Неверная частота кадров: {rate}; ожидалось около {fps} fps.")
    duration_value = info.get("format", {}).get("duration") or video.get("duration")
    try:
        measured_duration = float(duration_value)
    except (TypeError, ValueError) as exc:
        raise ReelBuildError("Не удалось определить длительность итогового MP4.") from exc
    tolerance = max(0.15, 2 / fps)
    if not math.isfinite(measured_duration) or abs(measured_duration - duration) > tolerance:
        raise ReelBuildError(
            f"Длительность результата {measured_duration:.3f} с отличается от целевой {duration:.3f} с "
            f"(допуск ±{tolerance:.3f} с)."
        )
    return {
        "status": "passed",
        "duration_seconds": round(measured_duration, 3),
        "resolution": [width, height],
        "fps": round(measured_fps, 3),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate", 0) or 0),
        "audio_channels": int(audio.get("channels", 0) or 0),
        "file_size_bytes": int(info.get("format", {}).get("size", 0) or 0),
    }


def _resolve_file(raw: Any, base: Path, field: str, *, optional: bool = False) -> Path | None:
    if raw in (None, "") and optional:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ReelBuildError(f"В проекте укажите путь в поле «{field}».")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise ReelBuildError(f"Файл из поля «{field}» не найден: {path}")
    return path


def _number(value: Any, name: str, *, low: float, high: float) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ReelBuildError(f"Параметр «{name}» должен быть числом.") from exc
    if not math.isfinite(n) or not low <= n <= high:
        raise ReelBuildError(f"Параметр «{name}» должен быть в диапазоне {low:g}–{high:g}.")
    return n


def _expand_visuals(raw_visuals: Any, base: Path) -> tuple[VisualSpec, ...]:
    if not isinstance(raw_visuals, list) or not raw_visuals:
        raise ReelBuildError("Добавьте хотя бы одно изображение или видео в список «visuals».")

    result: list[VisualSpec] = []
    for item_no, item in enumerate(raw_visuals, start=1):
        if isinstance(item, str):
            item = {"path": item}
        if not isinstance(item, dict):
            raise ReelBuildError(f"Элемент visuals №{item_no} должен быть путём или объектом с полем path.")
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ReelBuildError(f"У элемента visuals №{item_no} нет поля path.")
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = base / candidate
        candidate_text = os.fspath(candidate)
        if glob.has_magic(candidate_text):
            matches = [Path(x) for x in sorted(glob.glob(candidate_text))]
        elif candidate.is_dir():
            matches = sorted((p for p in candidate.iterdir() if p.is_file()), key=lambda p: p.name.lower())
        else:
            matches = [candidate] if candidate.is_file() else []
        matches = [p.resolve() for p in matches if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES]
        if not matches:
            raise ReelBuildError(f"Не найден поддерживаемый визуал для «{raw_path}» (элемент №{item_no}).")

        focus = item.get("focus", [0.5, 0.5])
        if not isinstance(focus, (list, tuple)) or len(focus) != 2:
            raise ReelBuildError(f"focus у элемента №{item_no} должен быть массивом [x, y] от 0 до 1.")
        fx = _number(focus[0], f"visuals[{item_no}].focus[0]", low=0.0, high=1.0)
        fy = _number(focus[1], f"visuals[{item_no}].focus[1]", low=0.0, high=1.0)
        start = _number(item.get("start_seconds", 0), f"visuals[{item_no}].start_seconds", low=0.0, high=7200.0)
        clip_duration = item.get("duration_seconds")
        if clip_duration is not None:
            clip_duration = _number(
                clip_duration, f"visuals[{item_no}].duration_seconds", low=0.05, high=MAX_DURATION_SECONDS
            )
        loop = item.get("loop", False)
        if not isinstance(loop, bool):
            raise ReelBuildError(f"loop у элемента №{item_no} должен быть true или false.")
        fit_mode = item.get("fit_mode")
        if fit_mode is not None and (not isinstance(fit_mode, str) or fit_mode not in {"crop", "blur"}):
            raise ReelBuildError(f"fit_mode у элемента №{item_no} должен быть crop или blur.")

        for path in matches:
            suffix = path.suffix.lower()
            kind = "image" if suffix in IMAGE_SUFFIXES else "video"
            result.append(
                VisualSpec(
                    path=path,
                    kind=kind,
                    focus_x=fx,
                    focus_y=fy,
                    start_seconds=start,
                    duration_seconds=clip_duration,
                    loop=loop,
                    manual_focus="focus" in item,
                    focus_kind="manual" if "focus" in item else "center",
                    fit_mode=fit_mode,
                )
            )
    return tuple(result)


def load_project(manifest: Path) -> Project:
    manifest = manifest.expanduser().resolve()
    if not manifest.is_file():
        raise ReelBuildError(f"Файл проекта не найден: {manifest}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReelBuildError(f"Не удалось прочитать JSON-проект {manifest}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReelBuildError("Корень JSON-проекта должен быть объектом.")
    base = manifest.parent

    audio = _resolve_file(payload.get("audio"), base, "audio")
    assert audio is not None
    visuals = _expand_visuals(payload.get("visuals"), base)
    output_raw = payload.get("output", "output/reel.mp4")
    output = Path(output_raw).expanduser() if isinstance(output_raw, str) else Path()
    if not output.is_absolute():
        output = base / output
    output = output.resolve()
    if output.suffix.lower() != ".mp4":
        raise ReelBuildError("Файл назначения должен иметь расширение .mp4.")

    music = _resolve_file(payload.get("music"), base, "music", optional=True)
    captions = _resolve_file(payload.get("captions"), base, "captions", optional=True)
    duration = payload.get("duration_seconds")
    if duration is not None:
        duration = _number(duration, "duration_seconds", low=MIN_DURATION_SECONDS, high=MAX_DURATION_SECONDS)

    raw_settings = payload.get("settings", {})
    if not isinstance(raw_settings, dict):
        raise ReelBuildError("Поле «settings» должно быть JSON-объектом.")
    resolution = raw_settings.get("resolution", [1080, 1920])
    if not isinstance(resolution, (list, tuple)) or len(resolution) != 2:
        raise ReelBuildError("settings.resolution задаётся как [ширина, высота], например [1080, 1920].")
    try:
        width, height = int(resolution[0]), int(resolution[1])
    except (TypeError, ValueError) as exc:
        raise ReelBuildError("settings.resolution должен содержать целые числа.") from exc
    if width < 360 or height < 640 or width % 2 or height % 2:
        raise ReelBuildError("Разрешение должно быть чётным и не меньше 360×640.")
    if abs(width / height - 9 / 16) > 0.002:
        raise ReelBuildError("Формат Reels — вертикальный 9:16 (например, 1080×1920).")
    fps = int(_number(raw_settings.get("fps", 30), "settings.fps", low=24, high=60))
    shot_seconds = _number(raw_settings.get("shot_seconds", 4.0), "settings.shot_seconds", low=1.0, high=10.0)
    chunk_scenes = int(_number(raw_settings.get("chunk_scenes", 12), "settings.chunk_scenes", low=1, high=24))
    crf = int(_number(raw_settings.get("crf", 20), "settings.crf", low=16, high=28))
    preset = raw_settings.get("preset", "medium")
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ReelBuildError(f"Неподдерживаемый x264 preset: {preset!r}.")
    music_gain = _number(raw_settings.get("music_gain", 0.12), "settings.music_gain", low=0.0, high=1.0)
    caption_mode = raw_settings.get("caption_mode", "burn")
    if not isinstance(caption_mode, str) or caption_mode not in {"burn", "soft", "none"}:
        raise ReelBuildError("settings.caption_mode должен быть burn, soft или none.")
    smart_crop = raw_settings.get("smart_crop", False)
    if not isinstance(smart_crop, bool):
        raise ReelBuildError("settings.smart_crop должен быть true или false.")

    inputs = {audio, *(v.path for v in visuals)}
    if music:
        inputs.add(music)
    if captions:
        inputs.add(captions)
    if output in inputs:
        raise ReelBuildError("Файл output не должен совпадать с одним из входных файлов.")

    return Project(
        manifest=manifest,
        title=str(payload.get("title") or output.stem),
        audio=audio,
        visuals=visuals,
        output=output,
        music=music,
        captions=captions,
        duration_seconds=duration,
        settings=Settings(
            width=width,
            height=height,
            fps=fps,
            shot_seconds=shot_seconds,
            chunk_scenes=chunk_scenes,
            crf=crf,
            preset=preset,
            music_gain=music_gain,
            caption_mode=caption_mode,
            smart_crop=smart_crop,
        ),
    )


def _with_source_durations(project: Project) -> tuple[VisualSpec, ...]:
    updated = []
    for visual in project.visuals:
        if visual.kind == "video":
            duration = probe_duration(visual.path, "video")
            if visual.start_seconds >= duration:
                raise ReelBuildError(
                    f"start_seconds ({visual.start_seconds:g}) выходит за длительность видео {visual.path.name} ({duration:.2f} с)."
                )
            updated.append(VisualSpec(**{**visual.__dict__, "source_duration_seconds": duration}))
        else:
            updated.append(visual)
    return tuple(updated)


def _autofocus_visuals(visuals: tuple[VisualSpec, ...]) -> tuple[VisualSpec, ...]:
    """Choose one subject-aware crop anchor per still/clip using the repo's optional toolkit."""
    if not any(not visual.manual_focus for visual in visuals):
        return visuals
    try:
        from PIL import Image
        from video_studio.toolkit.smartcrop import focus_point
    except ImportError as exc:
        raise ReelBuildError(
            "Автокадрирование требует Pillow, NumPy и OpenCV. Установите "
            "video_studio/reels/requirements-smartcrop.txt или укажите settings.smart_crop=false."
        ) from exc

    ffmpeg = _which("ffmpeg")
    updated: list[VisualSpec] = []
    for visual in visuals:
        if visual.manual_focus:
            updated.append(visual)
            continue
        if visual.kind == "image":
            try:
                with Image.open(visual.path) as source:
                    frame = source.convert("RGB")
            except OSError as exc:
                raise ReelBuildError(f"Не удалось прочитать изображение для smart crop: {visual.path}") from exc
        else:
            source_duration = visual.source_duration_seconds or 0.0
            available = max(0.0, source_duration - visual.start_seconds)
            sample_at = visual.start_seconds + min(available / 2, (visual.duration_seconds or available) / 2)
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{sample_at:.3f}",
                "-i", str(visual.path), "-frames:v", "1", "-vf", "scale=640:-2",
                "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
            ]
            try:
                sampled = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError as exc:
                raise ReelBuildError(f"Не удалось извлечь кадр для smart crop из {visual.path.name}: {exc}") from exc
            if sampled.returncode or not sampled.stdout:
                details = sampled.stderr.decode("utf-8", errors="replace").strip()
                raise ReelBuildError(f"Не удалось извлечь кадр для smart crop из {visual.path.name}: {details[-500:]}")
            try:
                with Image.open(io.BytesIO(sampled.stdout)) as source:
                    frame = source.convert("RGB")
            except OSError as exc:
                raise ReelBuildError(f"FFmpeg вернул некорректный кадр из {visual.path.name}.") from exc

        try:
            fx, fy, kind = focus_point(frame)
            fx = _number(fx, "smart_crop.focus_x", low=0.0, high=1.0)
            fy = _number(fy, "smart_crop.focus_y", low=0.0, high=1.0)
        except Exception as exc:
            if isinstance(exc, ReelBuildError):
                raise
            raise ReelBuildError(f"Не удалось определить точку фокуса для {visual.path.name}: {exc}") from exc
        fit_mode = visual.fit_mode or ("blur" if kind == "saliency" else "crop")
        updated.append(
            VisualSpec(
                **{
                    **visual.__dict__,
                    "focus_x": fx,
                    "focus_y": fy,
                    "focus_kind": str(kind),
                    "fit_mode": fit_mode,
                }
            )
        )
    return tuple(updated)


def scene_plan(
    visuals: tuple[VisualSpec, ...], *, total_frames: int, fps: int, shot_seconds: float
) -> list[Scene]:
    """Repeat the visual playlist until it covers the voiceover exactly in frames."""
    if total_frames <= 0 or fps <= 0:
        raise ReelBuildError("Некорректная длина таймлайна.")
    scenes: list[Scene] = []
    cursor = 0
    item_index = 0
    while cursor < total_frames:
        visual = visuals[item_index % len(visuals)]
        if visual.kind == "image":
            duration = visual.duration_seconds or shot_seconds
        else:
            source_duration = visual.source_duration_seconds
            if source_duration is None:
                raise ReelBuildError(f"Не определена длительность видео: {visual.path}")
            available = max(0.0, source_duration - visual.start_seconds)
            duration = visual.duration_seconds if visual.duration_seconds is not None else available
            if not visual.loop:
                duration = min(duration, available)
        frames = max(1, int(round(duration * fps)))
        if visual.kind == "video" and not visual.loop:
            available_frames = int(math.floor((visual.source_duration_seconds - visual.start_seconds) * fps + 1e-7))
            frames = min(frames, max(1, available_frames))
        frames = min(frames, total_frames - cursor)
        scenes.append(
            Scene(
                path=visual.path,
                kind=visual.kind,
                frames=frames,
                focus_x=visual.focus_x,
                focus_y=visual.focus_y,
                start_seconds=visual.start_seconds,
                loop=visual.loop,
                zoom_in=(len(scenes) % 2 == 0),
                focus_kind=visual.focus_kind,
                fit_mode=visual.fit_mode or "crop",
            )
        )
        cursor += frames
        item_index += 1
        if item_index > total_frames * 2:
            raise ReelBuildError("Слишком много пустых/коротких визуалов; проверьте project.json.")
    return scenes


def _filter_for_scene(scene: Scene, index: int, *, width: int, height: int, fps: int) -> str:
    input_label = f"[{index}:v]"
    if scene.fit_mode == "blur":
        # For uncertain saliency-only frames, preserve the full image instead of
        # cutting away a possible second subject or important context.
        base_label = f"[base{index}]"
        filters = (
            f"{input_label}split=2[bgsrc{index}][fgsrc{index}];"
            f"[bgsrc{index}]scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={width}:{height},boxblur=20:2,colorchannelmixer=rr=0.55:gg=0.55:bb=0.55[bg{index}];"
            f"[fgsrc{index}]scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos[fg{index}];"
            f"[bg{index}][fg{index}]overlay=(W-w)/2:(H-h)/2{base_label};"
        )
    else:
        base_label = input_label
        filters = ""
        base_filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos",
            f"crop={width}:{height}:(iw-ow)*{scene.focus_x:.5f}:(ih-oh)*{scene.focus_y:.5f}",
        ]
        filters += f"{input_label}" + ",".join(base_filters) + f"{base_label};"

    post_filters = [f"fps={fps}"]
    if scene.kind == "image":
        frames_denominator = max(1, scene.frames - 1)
        if scene.zoom_in:
            zoom = f"1+0.045*on/{frames_denominator}"
        else:
            zoom = f"1.045-0.045*on/{frames_denominator}"
        post_filters.append(
            f"zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={width}x{height}:fps={fps}"
        )
    else:
        # Accurate seeking around keyframes can leave the last frame a few ms short;
        # clone that frame if needed so all concat inputs have their planned length.
        post_filters.append("tpad=stop_mode=clone:stop_duration=1")
    post_filters.extend(
        [f"trim=end_frame={scene.frames}", "setpts=PTS-STARTPTS", "setsar=1", "format=yuv420p"]
    )
    return filters + base_label + ",".join(post_filters) + f"[v{index}]"


def _scene_input_seconds(scene: Scene, fps: int) -> float:
    """How much source material one scene needs before trim=end_frame.

    Stills get one extra frame: the blur chain splits the frame, re-inserts it via
    overlay and then passes through the fps filter, which drops the last frame of
    that chain. Without the slack every still would render one frame short, and a
    27-scene reel would lose ~0.9 s and fail the duration check in verify_output.
    The surplus is removed again by trim=end_frame={scene.frames}.
    """
    if scene.kind == "image":
        return (scene.frames + 1) / fps
    return scene.frames / fps + 0.12


def _render_scene_chunk(
    scenes: list[Scene], output: Path, *, width: int, height: int, fps: int, preset: str, crf: int
) -> None:
    ffmpeg = _which("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-filter_complex_threads", "2"]
    for scene in scenes:
        # Bound every input. In particular, a still-image loop or looped B-roll
        # must not leave an unbounded demuxer running behind the concat filter.
        input_seconds = _scene_input_seconds(scene, fps)
        if scene.kind == "image":
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{input_seconds:.6f}", "-i", str(scene.path)]
        else:
            if scene.loop:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-ss", f"{scene.start_seconds:.6f}", "-t", f"{input_seconds:.6f}", "-i", str(scene.path)]
    filters = [_filter_for_scene(s, i, width=width, height=height, fps=fps) for i, s in enumerate(scenes)]
    inputs = "".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{inputs}concat=n={len(scenes)}:v=1:a=0[outv]")
    cmd += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[outv]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-fps_mode",
        "cfr",
        "-g",
        str(fps * 2),
        "-keyint_min",
        str(fps * 2),
        "-sc_threshold",
        "0",
        "-movflags",
        "+faststart",
        str(output),
    ]
    _run(cmd, what=f"рендер видеосцен {output.name}")


def _ffconcat_quote(path: Path) -> str:
    value = os.fspath(path).replace("\\", "\\\\").replace("'", "'\\''")
    return f"file '{value}'"


def _has_filter(ffmpeg: str, name: str) -> bool:
    result = _run([ffmpeg, "-hide_banner", "-filters"], what="проверка фильтров FFmpeg")
    # FFmpeg writes its filter list to stderr on many builds.
    listing = result.stdout + "\n" + result.stderr
    return any(len(fields := line.split()) >= 2 and fields[1] == name for line in listing.splitlines())


def _audio_filter(project: Project, duration: float, *, has_music: bool, ducking: bool) -> str:
    fade_in = min(0.15, duration / 4)
    fade_out = min(0.8, duration / 4)
    fade_start = max(0.0, duration - fade_out)
    finish = f"afade=t=in:st=0:d={fade_in:.3f},afade=t=out:st={fade_start:.3f}:d={fade_out:.3f},loudnorm=I=-14:TP=-1:LRA=11,aformat=channel_layouts=stereo"
    if not has_music or project.settings.music_gain == 0:
        return f"[1:a]aresample=48000,{finish}[aout]"
    music_input = "[2:a]aresample=48000,volume={:.5f}[bed]".format(project.settings.music_gain)
    if ducking:
        prefix = "[1:a]asplit=2[voice_src][key_src];[voice_src]aresample=48000[voice];[key_src]aresample=48000[key]"
        music_input += ";[bed][key]sidechaincompress=threshold=0.1:ratio=4:attack=250:release=800:makeup=1[ducked]"
        mix = "[voice][ducked]amix=inputs=2:duration=first:weights='1 0.8':normalize=0[mix]"
    else:
        prefix = "[1:a]aresample=48000[voice]"
        mix = "[voice][bed]amix=inputs=2:duration=first:weights='1 0.8':normalize=0[mix]"
    return f"{prefix};{music_input};{mix};[mix]{finish}[aout]"


def _caption_filter_path(path: Path) -> str:
    # The caption is copied into a plain temporary path, avoiding filtergraph escaping issues.
    return os.fspath(path).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


SRT_TIMING = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _ass_timestamp(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _srt_cues(path: Path) -> list[tuple[float, float, str]]:
    """Read cues as (start, end, text), keeping the draft's manual line breaks."""
    raw = path.read_text(encoding="utf-8")
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\r?\n", raw.strip()):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        match = SRT_TIMING.search(lines[1])
        if not match:
            continue
        head = [int(value) for value in match.groups()[:4]]
        tail = [int(value) for value in match.groups()[4:]]

        def to_seconds(hours: int, minutes: int, secs: int, millis: int) -> float:
            return hours * 3600 + minutes * 60 + secs + millis / 1000

        text = "\\N".join(line.strip() for line in lines[2:] if line.strip())
        if text:
            cues.append((to_seconds(*head), to_seconds(*tail), text))
    if not cues:
        raise ReelBuildError(f"В файле субтитров нет пригодных реплик: {path}")
    return cues


def _fit_font_size(cues: list[tuple[float, float, str]], width: int, *, margin_lr: int = 30) -> int:
    """Choose a font size whose widest caption line still fits inside the frame.

    The average advance of DejaVu Sans Cyrillic is about 0.55 em, so the estimate is
    deliberately conservative: a slightly small caption is better than a clipped one.
    """
    longest = max((len(line) for _, _, text in cues for line in text.split("\\N")), default=1)
    available = max(1, width - 2 * margin_lr)
    size = available / (0.55 * max(1, longest))
    return int(max(32.0, min(96.0, size)))


def _write_ass_from_srt(srt: Path, ass: Path, *, width: int, height: int) -> None:
    """Convert an SRT into an ASS script pinned to the frame resolution.

    Pointing the subtitles filter straight at an SRT makes libass assume a 384x288
    script resolution. On a 1080x1920 frame every style value is then scaled ~6.7x:
    FontSize 50 becomes a huge caption that overflows the sides and climbs to the
    top edge, so only the tail of a line stays visible. Writing PlayResX/PlayResY
    keeps FontSize and MarginV in real pixels.
    """
    cues = _srt_cues(srt)
    font_size = _fit_font_size(cues, width)
    margin_lr, margin_v = 30, 250
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H00FFFFFF,&H80000000,&H70000000,"
        f"0,0,0,0,100,100,0,0,1,3,1,2,{margin_lr},{margin_lr},{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = [
        f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Default,,0,0,0,,{text}"
        for start, end, text in cues
    ]
    ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _write_timeline(path: Path, project: Project, scenes: list[Scene], duration: float) -> None:
    fps = project.settings.fps
    t = 0
    items = []
    for scene in scenes:
        start = t / fps
        t += scene.frames
        items.append(
            {
                "start_seconds": round(start, 3),
                "duration_seconds": round(scene.frames / fps, 3),
                "type": scene.kind,
                "source": scene.path.name,
                "focus": [round(scene.focus_x, 3), round(scene.focus_y, 3)],
                "focus_kind": scene.focus_kind,
                "fit_mode": scene.fit_mode,
            }
        )
    path.write_text(
        json.dumps(
            {
                "title": project.title,
                "duration_seconds": round(duration, 3),
                "format": "9:16",
                "resolution": [project.settings.width, project.settings.height],
                "fps": fps,
                "scenes": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build(project: Project, *, dry_run: bool = False) -> tuple[float, int]:
    _which("ffmpeg")
    _which("ffprobe")
    audio_duration = probe_duration(project.audio, "audio")
    duration = project.duration_seconds if project.duration_seconds is not None else audio_duration
    if duration > audio_duration + 0.05:
        raise ReelBuildError(
            f"Запрошено {duration / 60:.2f} мин, но аудиодорожка длится только {audio_duration / 60:.2f} мин."
        )
    if duration < MIN_DURATION_SECONDS - 0.05 or duration > MAX_DURATION_SECONDS + 0.05:
        raise ReelBuildError(
            f"Длительность Reels должна быть от 1 до 20 минут; аудио/таймкод проекта: {duration / 60:.2f} мин."
        )

    visuals = _with_source_durations(project)
    if project.settings.smart_crop:
        visuals = _autofocus_visuals(visuals)
    frames = int(round(duration * project.settings.fps))
    scenes = scene_plan(
        visuals,
        total_frames=frames,
        fps=project.settings.fps,
        shot_seconds=project.settings.shot_seconds,
    )
    caption_mode = project.settings.caption_mode if project.captions else "none"
    print(
        f"Проект: {project.title}\n"
        f"Длина: {duration / 60:.2f} мин · 9:16 · {project.settings.width}×{project.settings.height} · {project.settings.fps} fps\n"
        f"Визуальных сцен: {len(scenes)} · субтитры: {caption_mode} · выход: {project.output}"
    )
    if dry_run:
        return duration, len(scenes)

    project.output.parent.mkdir(parents=True, exist_ok=True)
    if project.settings.caption_mode == "burn" and project.captions:
        ffmpeg = _which("ffmpeg")
        if not _has_filter(ffmpeg, "subtitles"):
            raise ReelBuildError(
                "В установленном FFmpeg нет фильтра subtitles/libass. Установите сборку с libass "
                "или переключите settings.caption_mode на soft."
            )
    ducking = False
    if project.music and project.settings.music_gain > 0:
        ducking = _has_filter(_which("ffmpeg"), "sidechaincompress")

    try:
        with tempfile.TemporaryDirectory(prefix="reel_render_") as temp_name:
            temp = Path(temp_name)
            chunks: list[Path] = []
            chunk_size = project.settings.chunk_scenes
            groups = [scenes[i : i + chunk_size] for i in range(0, len(scenes), chunk_size)]
            for i, group in enumerate(groups, start=1):
                chunk = temp / f"visual_{i:04d}.mp4"
                print(f"[{i}/{len(groups)}] Рендер сцен {sum(len(g) for g in groups[:i-1]) + 1}–{sum(len(g) for g in groups[:i])}…", flush=True)
                _render_scene_chunk(
                    group,
                    chunk,
                    width=project.settings.width,
                    height=project.settings.height,
                    fps=project.settings.fps,
                    preset=project.settings.preset,
                    crf=project.settings.crf,
                )
                chunks.append(chunk)

            concat_file = temp / "scenes.ffconcat"
            concat_file.write_text(
                "ffconcat version 1.0\n" + "\n".join(_ffconcat_quote(p) for p in chunks) + "\n",
                encoding="utf-8",
            )
            final_cmd = [
                _which("ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-i",
                str(project.audio),
            ]
            music_index = None
            if project.music and project.settings.music_gain > 0:
                music_index = 2
                final_cmd += ["-stream_loop", "-1", "-i", str(project.music)]
            captions_index = None
            captions_for_filter = None
            if project.captions and project.settings.caption_mode == "soft":
                captions_index = 3 if music_index is not None else 2
                final_cmd += ["-i", str(project.captions)]
            elif project.captions and project.settings.caption_mode == "burn":
                captions_for_filter = temp / "captions.ass"
                _write_ass_from_srt(
                    project.captions,
                    captions_for_filter,
                    width=project.settings.width,
                    height=project.settings.height,
                )

            filter_parts: list[str] = []
            if captions_for_filter:
                subtitle_path = _caption_filter_path(captions_for_filter)
                filter_parts.append(f"[0:v]subtitles=filename='{subtitle_path}'[vout]")
            filter_parts.append(_audio_filter(project, duration, has_music=music_index is not None, ducking=ducking))
            final_cmd += ["-filter_complex", ";".join(filter_parts), "-map", "[aout]"]
            if captions_for_filter:
                final_cmd += ["-map", "[vout]", "-c:v", "libx264", "-preset", project.settings.preset,
                              "-crf", str(project.settings.crf), "-pix_fmt", "yuv420p", "-r", str(project.settings.fps)]
            else:
                final_cmd += ["-map", "0:v:0", "-c:v", "copy"]
            final_cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
            if captions_index is not None:
                final_cmd += ["-map", f"{captions_index}:0", "-c:s", "mov_text", "-metadata:s:s:0", "language=rus"]
            final_cmd += ["-metadata", f"title={project.title}", "-t", f"{duration:.6f}"]
            # In soft-caption mode -shortest would also consider the SRT stream and
            # could cut the picture at the final subtitle instead of the audio.
            if captions_index is None:
                final_cmd.append("-shortest")
            final_cmd += ["-movflags", "+faststart", str(project.output)]
            print("Финальная сборка и нормализация звука…", flush=True)
            _run(final_cmd, what="сборка финального MP4")
            qc = verify_output(
                project.output,
                duration=duration,
                width=project.settings.width,
                height=project.settings.height,
                fps=project.settings.fps,
            )
            _write_timeline(project.output.with_suffix(".timeline.json"), project, scenes, duration)
            project.output.with_suffix(".qc.json").write_text(
                json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    except Exception:
        for artifact in (
            project.output,
            project.output.with_suffix(".timeline.json"),
            project.output.with_suffix(".qc.json"),
        ):
            artifact.unlink(missing_ok=True)
        raise

    print(f"Готово: {project.output}")
    print(f"Таймлайн: {project.output.with_suffix('.timeline.json')}")
    print(f"Отчёт QC: {project.output.with_suffix('.qc.json')}")
    return duration, len(scenes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Сборка вертикального Reels 9:16 длительностью 1–20 минут.")
    parser.add_argument("project", type=Path, help="JSON-файл проекта; пути в нём считаются от его папки")
    parser.add_argument("--dry-run", action="store_true", help="проверить входы и показать план без рендера")
    args = parser.parse_args(argv)
    try:
        project = load_project(args.project)
        build(project, dry_run=args.dry_run)
    except ReelBuildError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Сборка прервана.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
