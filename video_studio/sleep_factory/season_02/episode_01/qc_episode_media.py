#!/usr/bin/env python3
"""Full-media QC for a rendered S02E01 MP4.

Checks the duration, 1280x720/24 fps H.264/AAC stream, complete FFmpeg decode,
WebRTC-VAD active-speech share, and reports EBU-style loudness measurements.
The VAD share is measured on the final MP4 audio (including the series sting),
not inferred from the planned scene timeline.

Install the optional VAD wheel with:
  python3 -m pip install -r requirements-qc.txt

Example:
  python3 qc_episode_media.py rendered/s02e01_full.mp4 \
      --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SAMPLE_RATE = 16_000
FRAME_MS = 30
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2


class QCError(RuntimeError):
    """A media, dependency, or QC execution error."""


def find_binary(name: str, explicit: str | None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise QCError(f"Не найден указанный {name}: {explicit}")
    found = shutil.which(name)
    if found:
        return found
    raise QCError(f"Не найден {name}; передайте путь через --{name}.")


def run(command: list[str], label: str, *, capture: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
    except OSError as exc:
        raise QCError(f"Не удалось запустить {label}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise QCError(f"{label} завершился с кодом {result.returncode}: {detail[-2500:]}")
    return result


def probe(ffprobe: str, media: Path) -> dict[str, Any]:
    result = run([
        ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,sample_rate,channels:format=duration,size",
        "-of", "json", str(media),
    ], "ffprobe")
    try:
        return json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QCError("ffprobe вернул некорректный JSON.") from exc


def rate_value(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def decode_audio_pcm(ffmpeg: str, media: Path) -> bytes:
    result = run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(media),
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1",
    ], "декодирование аудио для WebRTC VAD")
    return result.stdout


def measure_active_speech(pcm: bytes, mode: int) -> dict[str, Any]:
    try:
        import webrtcvad
    except ImportError as exc:
        raise QCError(
            "Не установлен WebRTC VAD. Выполните: python3 -m pip install -r requirements-qc.txt"
        ) from exc
    total_frames = len(pcm) // FRAME_BYTES
    if total_frames == 0:
        raise QCError("В аудиодорожке нет полных 30-мс кадров для анализа.")
    detector = webrtcvad.Vad(mode)
    active_frames = 0
    for offset in range(0, total_frames * FRAME_BYTES, FRAME_BYTES):
        if detector.is_speech(pcm[offset:offset + FRAME_BYTES], SAMPLE_RATE):
            active_frames += 1
    measured_seconds = total_frames * FRAME_MS / 1000
    active_seconds = active_frames * FRAME_MS / 1000
    return {
        "method": f"WebRTC VAD mode {mode}",
        "sample_rate_hz": SAMPLE_RATE,
        "frame_ms": FRAME_MS,
        "active_frames": active_frames,
        "total_frames": total_frames,
        "active_speech_seconds": round(active_seconds, 3),
        "vad_audio_seconds": round(measured_seconds, 3),
        "speech_share": active_frames / total_frames,
        "trailing_unanalysed_seconds": round(max(0.0, len(pcm) / (SAMPLE_RATE * 2) - measured_seconds), 4),
    }


def measure_loudness(ffmpeg: str, media: Path) -> dict[str, Any] | None:
    command = [
        ffmpeg, "-hide_banner", "-nostats", "-i", str(media), "-map", "0:a:0",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-",
    ]
    result = run(command, "измерение loudness")
    stderr = result.stderr.decode("utf-8", errors="replace")
    start = stderr.rfind("{")
    if start < 0:
        return None
    try:
        raw = json.loads(stderr[start:])
    except json.JSONDecodeError:
        return None
    values: dict[str, Any] = {}
    for source, target in (("input_i", "integrated_lufs"), ("input_tp", "true_peak_dbtp"),
                           ("input_lra", "loudness_range_lu"), ("input_thresh", "gate_threshold_lufs")):
        value = raw.get(source)
        try:
            number = float(value)
        except (TypeError, ValueError):
            values[target] = value
        else:
            values[target] = number if math.isfinite(number) else value
    values["measurement_only"] = True
    values["analysis_target_lufs"] = -16.0
    values["analysis_target_true_peak_dbtp"] = -1.5
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Финальный MP4")
    parser.add_argument("--report", type=Path, help="JSON-отчёт; по умолчанию рядом с MP4")
    parser.add_argument("--min-duration", type=float, default=2100.0,
                        help="Минимальная длительность в секундах (по умолчанию 35 минут)")
    parser.add_argument("--min-speech-share", type=float, default=0.85,
                        help="Минимальная доля активной речи (по умолчанию 0.85)")
    parser.add_argument("--vad-mode", type=int, choices=range(4), default=2,
                        help="Режим WebRTC VAD 0–3; QC по умолчанию использует mode 2")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    parser.add_argument("--skip-full-decode", action="store_true",
                        help="Пропустить полное декодирование MP4 (не рекомендуется для выпуска)")
    parser.add_argument("--skip-loudness", action="store_true",
                        help="Пропустить измерение loudness")
    args = parser.parse_args(argv)

    try:
        media = args.video.expanduser().resolve()
        if not media.is_file():
            raise QCError(f"Не найден MP4: {media}")
        if args.min_duration <= 0 or not 0 < args.min_speech_share <= 1:
            raise QCError("Порог длительности и доля речи должны быть положительными; доля — не выше 1.")
        ffmpeg = find_binary("ffmpeg", args.ffmpeg)
        ffprobe = find_binary("ffprobe", args.ffprobe)
        info = probe(ffprobe, media)
        streams = info.get("streams", [])
        video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        if video is None or audio is None:
            raise QCError("MP4 должен содержать хотя бы одну видео- и аудиодорожку.")
        try:
            duration = float(info["format"]["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise QCError("Не удалось определить длительность MP4.") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise QCError("Длительность MP4 некорректна.")

        checks = {
            "minimum_duration": duration >= args.min_duration,
            "resolution_1280x720": (int(video.get("width", 0)), int(video.get("height", 0))) == (1280, 720),
            "video_h264": video.get("codec_name") == "h264",
            "audio_aac": audio.get("codec_name") == "aac",
            "frame_rate_24fps": abs(rate_value(video.get("avg_frame_rate") or video.get("r_frame_rate")) - 24.0) <= 0.05,
        }
        if args.skip_full_decode:
            checks["full_decode"] = None
        else:
            run([ffmpeg, "-hide_banner", "-v", "error", "-i", str(media), "-f", "null", "-"],
                "полное декодирование MP4")
            checks["full_decode"] = True

        pcm = decode_audio_pcm(ffmpeg, media)
        speech = measure_active_speech(pcm, args.vad_mode)
        checks["minimum_active_speech_share"] = speech["speech_share"] >= args.min_speech_share
        loudness = None if args.skip_loudness else measure_loudness(ffmpeg, media)
        if loudness is not None and isinstance(loudness.get("true_peak_dbtp"), (int, float)):
            checks["no_clipping_true_peak"] = loudness["true_peak_dbtp"] < 0.0

        failures = [name for name, passed in checks.items() if passed is False]
        report = {
            "status": "passed" if not failures else "failed",
            "file": str(media),
            "duration_seconds": round(duration, 3),
            "duration_minutes": round(duration / 60, 3),
            "video": {
                "codec": video.get("codec_name"),
                "resolution": [video.get("width"), video.get("height")],
                "fps": round(rate_value(video.get("avg_frame_rate") or video.get("r_frame_rate")), 3),
            },
            "audio": {
                "codec": audio.get("codec_name"),
                "sample_rate_hz": audio.get("sample_rate"),
                "channels": audio.get("channels"),
            },
            "active_speech": speech,
            "loudness": loudness,
            "thresholds": {
                "minimum_duration_seconds": args.min_duration,
                "minimum_active_speech_share": args.min_speech_share,
            },
            "checks": checks,
            "failures": failures,
        }
        report_path = args.report.expanduser().resolve() if args.report else media.with_suffix(".active-speech.qc.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"QC: {report['status']}")
        print(f"Длительность: {duration / 60:.2f} мин; активная речь: {speech['speech_share']:.2%} "
              f"({speech['active_speech_seconds']:.1f} с по WebRTC VAD mode {args.vad_mode})")
        if loudness and "integrated_lufs" in loudness:
            print(f"Loudness: {loudness['integrated_lufs']} LUFS; true peak: {loudness.get('true_peak_dbtp')} dBTP")
        print(f"Отчёт: {report_path}")
        if failures:
            print("Не прошли проверки: " + ", ".join(failures), file=sys.stderr)
            return 1
        return 0
    except (QCError, OSError, ValueError) as exc:
        print(f"Ошибка QC: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
