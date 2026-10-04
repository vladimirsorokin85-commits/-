#!/usr/bin/env python3
"""Create SRT captions from a script estimate or local faster-whisper ASR.

The estimated mode allocates time by character count. The optional ASR mode uses
word timestamps from faster-whisper. Review captions and proper nouns before release.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

try:
    from .build import ReelBuildError, probe_duration
except ImportError:  # also allow: python video_studio/reels/captions.py ...
    from build import ReelBuildError, probe_duration

CLOSE_PUNCTUATION = set(",.;:!?…%)]}»”’\"")
OPEN_PUNCTUATION = set("([{«“‘\"")


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?…])\s+", text) if part.strip()]


def _caption_chunks(text: str, *, max_words: int = 6, max_chars: int = 34) -> list[str]:
    chunks: list[str] = []
    for sentence in _sentences(text):
        words = sentence.split()
        current: list[str] = []
        for word in words:
            trial = " ".join(current + [word])
            if current and (len(current) >= max_words or len(trial) > max_chars):
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))
    return chunks


def _wrap(text: str, width: int = 34) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width and len(lines) == 0:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines[:2])


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def draft_srt(text: str, duration_seconds: float, *, gap_seconds: float = 0.08) -> str:
    """Allocate the supplied audio duration across short, word-count-weighted captions."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    chunks = _caption_chunks(text)
    if not chunks:
        raise ValueError("The script is empty")
    requested_gap = min(max(0.0, gap_seconds), 0.15)
    gap = min(requested_gap, duration_seconds / max(2, 2 * len(chunks)))
    active_duration = max(0.001, duration_seconds - gap * (len(chunks) - 1))
    weights = [max(1, len(chunk.replace(" ", ""))) for chunk in chunks]
    weight_total = sum(weights)

    entries: list[str] = []
    cursor = 0.0
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        length = active_duration * weight / weight_total
        end = duration_seconds if index == len(chunks) else min(duration_seconds, cursor + length)
        entries.append(f"{index}\n{_timestamp(cursor)} --> {_timestamp(end)}\n{_wrap(chunk)}")
        cursor = end + (gap if index < len(chunks) else 0.0)
    return "\n\n".join(entries) + "\n"


def _join_word_text(tokens: Iterable[str]) -> str:
    text = ""
    for raw in tokens:
        token = str(raw).strip()
        if not token:
            continue
        if text and token[0] not in CLOSE_PUNCTUATION and text[-1] not in OPEN_PUNCTUATION:
            text += " "
        text += token
    return text


def word_timed_srt(segments: Iterable[object], duration_seconds: float, *, max_words: int = 6,
                   max_chars: int = 34, max_caption_seconds: float = 3.2) -> str:
    """Group ASR word timestamps into readable, frame-timed SRT cues."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    words: list[tuple[str, float, float]] = []
    for segment in segments:
        for word in (getattr(segment, "words", None) or ()):
            raw_text = getattr(word, "word", "")
            start, end = getattr(word, "start", None), getattr(word, "end", None)
            try:
                start, end = float(start), float(end)
            except (TypeError, ValueError):
                continue
            token = str(raw_text).strip()
            if token and 0 <= start < end and start < duration_seconds:
                words.append((token, start, min(end, duration_seconds)))
    words.sort(key=lambda item: (item[1], item[2]))
    if not words:
        raise ValueError("Transcription returned no usable word timestamps")

    groups: list[list[tuple[str, float, float]]] = []
    current: list[tuple[str, float, float]] = []
    for item in words:
        candidate = _join_word_text([w[0] for w in current + [item]])
        duration = item[2] - current[0][1] if current else item[2] - item[1]
        long_pause = bool(current and item[1] - current[-1][2] > 0.65)
        too_many = len(current) >= max_words
        too_wide = len(candidate) > max_chars
        too_long = bool(current and duration > max_caption_seconds)
        sentence_end = bool(current and re.search(r"[.!?…][\"'»)]?$", current[-1][0]) and len(current) >= 3)
        if current and (long_pause or too_many or too_wide or too_long or sentence_end):
            groups.append(current)
            current = []
        current.append(item)
    if current:
        groups.append(current)

    cues: list[tuple[float, float, str]] = []
    for group in groups:
        start = max(0.0, group[0][1] - 0.04)
        end = min(duration_seconds, group[-1][2] + 0.10)
        text = _join_word_text(w[0] for w in group)
        if text and end > start:
            cues.append((start, end, text))

    # Keep adjacent captions from overlapping after applying small readability pads.
    adjusted: list[tuple[float, float, str]] = []
    for i, (start, end, text) in enumerate(cues):
        if i + 1 < len(cues):
            next_start = cues[i + 1][0]
            end = min(end, max(start + 0.04, (end + next_start) / 2))
        if adjusted:
            start = max(start, adjusted[-1][1])
        if end > start:
            adjusted.append((start, end, text))
    if not adjusted:
        raise ValueError("Transcription produced no captions after timing validation")
    return "\n\n".join(
        f"{i}\n{_timestamp(start)} --> {_timestamp(end)}\n{_wrap(text)}"
        for i, (start, end, text) in enumerate(adjusted, start=1)
    ) + "\n"


def segment_timed_srt(segments: Iterable[object], duration_seconds: float, *, max_words: int = 6,
                      max_chars: int = 34) -> str:
    """Fallback when ASR provides segment times/text but no usable word times."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    cues: list[tuple[float, float, str]] = []
    for segment in segments:
        try:
            start = max(0.0, float(getattr(segment, "start", 0.0)))
            end = min(duration_seconds, float(getattr(segment, "end", 0.0)))
        except (TypeError, ValueError):
            continue
        text = str(getattr(segment, "text", "") or "").strip()
        chunks = _caption_chunks(text, max_words=max_words, max_chars=max_chars)
        if end <= start or not chunks:
            continue
        gap = min(0.04, (end - start) / max(2, 2 * len(chunks)))
        active = max(0.001, end - start - gap * (len(chunks) - 1))
        weights = [max(1, len(chunk.replace(" ", ""))) for chunk in chunks]
        total_weight = sum(weights)
        cursor = start
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            cue_end = end if index == len(chunks) - 1 else min(end, cursor + active * weight / total_weight)
            cues.append((cursor, cue_end, chunk))
            cursor = cue_end + (gap if index < len(chunks) - 1 else 0.0)
    if not cues:
        raise ValueError("Transcription returned no usable segment timestamps")

    adjusted: list[tuple[float, float, str]] = []
    for start, end, text in cues:
        if adjusted:
            start = max(start, adjusted[-1][1])
        if end > start:
            adjusted.append((start, end, text))
    if not adjusted:
        raise ValueError("Transcription produced no captions after segment timing validation")
    return "\n\n".join(
        f"{i}\n{_timestamp(start)} --> {_timestamp(end)}\n{_wrap(text)}"
        for i, (start, end, text) in enumerate(adjusted, start=1)
    ) + "\n"


def transcribe_srt(audio_path: Path, *, model_name: str, language: str,
                   device: str, compute_type: str | None) -> tuple[str, str | None]:
    """Run optional local faster-whisper; returns SRT text and recognized transcript."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ReelBuildError(
            "Для --transcribe установите опциональную зависимость: "
            "python3 -m pip install -r video_studio/reels/requirements-asr.txt"
        ) from exc
    resolved_compute = compute_type or ("int8" if device == "cpu" else "float16")
    try:
        model = WhisperModel(model_name, device=device, compute_type=resolved_compute)
        segments, _info = model.transcribe(
            str(audio_path),
            language=None if language == "auto" else language,
            word_timestamps=True,
            vad_filter=True,
        )
        materialized = list(segments)
        duration = probe_duration(audio_path, "audio")
        try:
            srt = word_timed_srt(materialized, duration)
        except ValueError as word_error:
            try:
                srt = segment_timed_srt(materialized, duration)
            except ValueError as segment_error:
                raise ValueError(f"ASR вернул непригодные таймкоды слов и сегментов: {segment_error}") from word_error
        transcript = "\n".join(str(getattr(segment, "text", "")).strip() for segment in materialized).strip()
        return srt, transcript or None
    except ReelBuildError:
        raise
    except Exception as exc:
        raise ReelBuildError(f"faster-whisper не смог обработать дорожку: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создать SRT по тексту или локально распознать речь.")
    parser.add_argument("--script", type=Path, help="текст дикторской озвучки для примерной раскладки")
    parser.add_argument("--audio", required=True, type=Path, help="аудиодорожка")
    parser.add_argument("--output", type=Path, help="путь к SRT; по умолчанию рядом с аудио")
    parser.add_argument("--transcribe", action="store_true", help="использовать локальный faster-whisper")
    parser.add_argument("--model", default="small", help="Whisper model name (default: small)")
    parser.add_argument("--language", default="ru", help="язык речи: ru/en/... либо auto")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--compute-type", help="например int8 для CPU или float16 для CUDA")
    args = parser.parse_args(argv)
    try:
        audio_path = args.audio.expanduser().resolve()
        if not audio_path.is_file():
            raise ReelBuildError(f"Аудиодорожка не найдена: {audio_path}")
        if args.transcribe:
            srt, transcript = transcribe_srt(
                audio_path,
                model_name=args.model,
                language=args.language,
                device=args.device,
                compute_type=args.compute_type,
            )
        else:
            if not args.script:
                raise ReelBuildError("Укажите --script либо включите --transcribe.")
            script_path = args.script.expanduser().resolve()
            if not script_path.is_file():
                raise ReelBuildError(f"Файл текста не найден: {script_path}")
            duration = probe_duration(audio_path, "audio")
            srt = draft_srt(script_path.read_text(encoding="utf-8"), duration)
            transcript = None
        output = args.output.expanduser().resolve() if args.output else audio_path.with_suffix(".srt")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(srt, encoding="utf-8")
        if transcript:
            output.with_suffix(".txt").write_text(transcript + "\n", encoding="utf-8")
    except (OSError, ReelBuildError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(f"Субтитры записаны: {output}")
    if args.transcribe:
        print(f"Текст распознавания: {output.with_suffix('.txt')}")
        print("Проверьте имена, числа, пунктуацию и тайминг перед рендером.")
    else:
        print("Тайминг оценочный. Для синхронного SRT используйте --transcribe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
