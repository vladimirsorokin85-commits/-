#!/usr/bin/env python3
"""Render the two vertical Episode 2 Reels from scene audio and key art."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
EP = HERE.parent
SCRIPT = EP / "script.md"
FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg")

REELS = [
    ("s01e02_a01", "reel_01_bulq_alien.png", "reel_01_alien"),
    ("s01e02_a08", "reel_02_return_loop.png", "reel_02_archive"),
]


def scene_text(scene_id: str) -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    pattern = rf"(?ms)^### \[{re.escape(scene_id)}\].*?\n\n(.*?)(?=^### \[|\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Scene not found: {scene_id}")
    return " ".join(line.strip() for line in match.group(1).splitlines()).strip()


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path), "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read duration for {path}: {result.stderr[-1000:]}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def caption_chunks(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        current = ""
        for word in words:
            if current and len(current) + 1 + len(word) > 66:
                chunks.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            chunks.append(current)
    return chunks


def stamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    whole, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{millis:03}"


def write_srt(text: str, duration: float, path: Path) -> None:
    chunks = caption_chunks(text)
    weights = [max(1, len(chunk.split())) for chunk in chunks]
    total = sum(weights)
    cursor = 0.0
    rows = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), 1):
        end = duration if index == len(chunks) else cursor + duration * weight / total
        lines = textwrap.wrap(chunk, width=34, break_long_words=False, break_on_hyphens=False)
        rows.append(f"{index}\n{stamp(cursor)} --> {stamp(end)}\n" + "\n".join(lines) + "\n")
        cursor = end
    path.write_text("\n".join(rows), encoding="utf-8")


def render(scene_id: str, image_name: str, output_stem: str) -> None:
    audio = EP / "voice2" / f"{scene_id}.opus"
    image = EP / "images" / image_name
    output = HERE / f"{output_stem}.mp4"
    srt = HERE / f"{output_stem}.srt"
    text = scene_text(scene_id)
    duration = audio_duration(audio)
    write_srt(text, duration, srt)
    voice_text = output_stem.replace("_alien", "_voice").replace("_archive", "_voice")
    (HERE / f"{voice_text}.txt").write_text(text, encoding="utf-8")
    vf = (
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        "zoompan=z='min(zoom+0.00012,1.05)':d=1:s=720x1280:fps=24,"
        f"subtitles='{srt.as_posix()}':force_style='FontName=DejaVu Sans,FontSize=42,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,"
        "Outline=3,Shadow=1,Alignment=2,MarginV=110',format=yuv420p"
    )
    subprocess.run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", "24", "-i", str(image), "-i", str(audio),
        "-vf", vf, "-map", "0:v", "-map", "1:a", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
    ], check=True)
    subprocess.run([FFMPEG, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True)
    print(f"Rendered {output.name}: {duration:.2f}s; {output.stat().st_size} bytes")


if not FFMPEG:
    raise SystemExit("Set FFMPEG to a working FFmpeg binary.")
for reel in REELS:
    render(*reel)
