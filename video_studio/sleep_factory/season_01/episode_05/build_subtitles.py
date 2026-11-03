#!/usr/bin/env python3
"""Build readable Russian SRT cues from the final scene timeline.

Cue timing is estimated within each already-generated TTS clip by character weight;
without word-level forced alignment, review the captions against audio before upload.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEADER = re.compile(r"^### \[(?P<id>s01e05_[^\]]+)\] \[voice-[^\]]+\](?: \[[^\]]+\])? .+$")
SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+")
CLOSE = "\"'»”’)]}"


def parse_script(path: Path) -> dict[str, str]:
    scenes: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADER.match(line)
        if match:
            current = match.group("id")
            if current in scenes:
                raise ValueError(f"Duplicate script ID: {current}")
            scenes[current] = []
        elif current is not None:
            scenes[current].append(line)
    return {
        scene_id: " ".join(" ".join(lines).split())
        for scene_id, lines in scenes.items()
    }


def split_cues(text: str, max_words: int, max_chars: int) -> list[str]:
    cues: list[str] = []
    normalized = " ".join(text.split())
    for sentence in SENTENCE_BREAK.split(normalized):
        current: list[str] = []
        for word in sentence.split():
            candidate = " ".join(current + [word])
            if current and (len(current) >= max_words or len(candidate) > max_chars):
                cues.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            cues.append(" ".join(current))
    return cues


def weight(cue: str) -> float:
    characters = sum(not ch.isspace() for ch in cue)
    end = cue.rstrip(CLOSE)
    if end.endswith((".", "!", "?", "…")):
        return characters + 7.0
    if end.endswith((",", ";", ":")):
        return characters + 2.0
    return float(max(1, characters))


def timestamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def build_srt(script: Path, timeline: Path, *, offset: float, max_words: int, max_chars: int) -> str:
    texts = parse_script(script)
    data = json.loads(timeline.read_text(encoding="utf-8"))
    entries: list[tuple[float, float, str]] = []
    scene_ids = [scene["id"] for scene in data["scenes"]]
    if scene_ids != list(texts):
        raise ValueError("Timeline IDs do not match script IDs and order")
    for scene in data["scenes"]:
        scene_id = scene["id"]
        start = float(scene["start"])
        duration = float(scene["end"]) - start
        cues = split_cues(texts[scene_id], max_words, max_chars)
        if not cues or duration <= 0:
            raise ValueError(f"Empty text or invalid duration for {scene_id}")
        pad = min(0.045, duration / max(2, 2 * len(cues)))
        active = duration - pad * (len(cues) - 1)
        cue_weights = [weight(cue) for cue in cues]
        total = sum(cue_weights)
        cursor = start
        for index, (cue, cue_weight) in enumerate(zip(cues, cue_weights)):
            cue_end = (start + duration if index == len(cues) - 1
                       else cursor + active * cue_weight / total)
            entries.append((cursor + offset, cue_end + offset, cue))
            cursor = cue_end + (pad if index < len(cues) - 1 else 0.0)

    lines: list[str] = []
    for index, (start, end, text) in enumerate(entries, 1):
        lines.extend((str(index), f"{timestamp(start)} --> {timestamp(end)}", text, ""))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=Path(__file__).with_name("script.md"))
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offset", type=float, default=4.586,
                        help="Seconds of the separate logo intro prepended to the mix")
    parser.add_argument("--max-words", type=int, default=6)
    parser.add_argument("--max-chars", type=int, default=34)
    args = parser.parse_args()
    if args.offset < 0 or args.max_words < 1 or args.max_chars < 8:
        parser.error("offset must be nonnegative, max-words positive, max-chars at least 8")
    srt = build_srt(args.script, args.timeline, offset=args.offset,
                    max_words=args.max_words, max_chars=args.max_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(srt, encoding="utf-8")
    print(f"Wrote estimated, scene-aligned captions: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
