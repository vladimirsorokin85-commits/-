#!/usr/bin/env python3
"""Build a reusable series opener from a licensed short logo sting.

Requires Python 3 (standard library only) and FFmpeg with libx264 + AAC.
The source sound is the CC0 1.0 `logo_sting.mp3` in video_studio/toolkit/sfx/;
FFmpeg gently rolls off the brightest frequencies and exports a 48 kHz, 24-bit
stereo WAV master. The title card appears after the sting over a generated starfield.

Example:
  python3 build_series_intro.py --ffmpeg /path/to/ffmpeg
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CARD = ROOT / "series_intro_alternative.png"
DEFAULT_SOURCE_AUDIO = (ROOT.parent.parent / "toolkit/sfx/logo_sting.mp3").resolve()
DEFAULT_WAV = ROOT / "series_micro_jingle.wav"
DEFAULT_VIDEO = ROOT / "series_intro_preview.mp4"
WIDTH, HEIGHT, FPS = 1280, 720, 24
SAMPLE_RATE = 48_000
JINGLE_DURATION = 1.83
VIDEO_DURATION = 4.2
TITLE_REVEAL_START = 1.70
TITLE_FADE_DURATION = 0.50


def run(command: list[str], label: str) -> None:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout or "нет подробностей").strip()
        raise SystemExit(f"{label}:\n{detail[-5000:]}")


def make_jingle(ffmpeg: str, source: Path, destination: Path) -> None:
    """Gently soften the licensed source sting and render a PCM master WAV."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    audio_filter = (
        "aresample=48000,"
        "lowpass=f=6000,"
        "volume=-5dB,"
        "afade=t=in:st=0:d=0.08,"
        "afade=t=out:st=1.43:d=0.40"
    )
    command = [
        ffmpeg, "-hide_banner", "-y", "-loglevel", "error",
        "-i", str(source), "-vn", "-af", audio_filter,
        "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s24le",
        "-t", f"{JINGLE_DURATION:.2f}", str(destination),
    ]
    run(command, "Не удалось подготовить мастер WAV из CC0-джингла")


def make_starfield(path: Path) -> None:
    """Create a subtle dark-teal PPM background using only the Python stdlib."""
    rng = random.Random(451902)
    pixels = bytearray(WIDTH * HEIGHT * 3)
    cx, cy = WIDTH * 0.51, HEIGHT * 0.50
    sx, sy = WIDTH * 0.39, HEIGHT * 0.45
    offset = 0
    for y in range(HEIGHT):
        yf = y / max(1, HEIGHT - 1)
        base_r = 4.0 + 3.0 * yf
        base_g = 13.0 + 12.0 * yf
        base_b = 23.0 + 17.0 * yf
        dy = (y - cy) / sy
        for x in range(WIDTH):
            dx = (x - cx) / sx
            glow = math.exp(-1.75 * (dx * dx + dy * dy))
            pixels[offset] = min(255, round(base_r + 2.0 * glow))
            pixels[offset + 1] = min(255, round(base_g + 15.0 * glow))
            pixels[offset + 2] = min(255, round(base_b + 22.0 * glow))
            offset += 3

    def set_pixel(x: int, y: int, rgb: tuple[int, int, int]) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            p = (y * WIDTH + x) * 3
            for c in range(3):
                pixels[p + c] = max(pixels[p + c], rgb[c])

    for _ in range(155):
        x = rng.randrange(WIDTH)
        y = rng.randrange(HEIGHT)
        bright = rng.randrange(34, 115)
        tint = rng.choice(((bright, bright + 7, bright + 15), (bright + 12, bright + 8, bright)))
        color = tuple(min(255, c) for c in tint)
        set_pixel(x, y, color)
        if rng.random() < 0.16:
            glint = tuple(min(255, c + 24) for c in color)
            set_pixel(x - 1, y, glint)
            set_pixel(x + 1, y, glint)
            set_pixel(x, y - 1, glint)
            set_pixel(x, y + 1, glint)

    path.write_bytes(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii") + pixels)


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise SystemExit(f"FFmpeg не найден: {explicit}")
    found = shutil.which("ffmpeg")
    if not found:
        raise SystemExit("Не найден FFmpeg. Установите FFmpeg или укажите --ffmpeg /путь/к/ffmpeg.")
    return found


def render_video(ffmpeg: str, card: Path, wav: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="series_intro_") as tmp:
        starfield = Path(tmp) / "starfield.ppm"
        make_starfield(starfield)
        filter_complex = (
            f"[0:v]scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1,format=rgba,"
            "fade=t=in:st=0:d=0.20[bg];"
            f"[1:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.00022,1.025)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
            "setsar=1,format=rgba,"
            f"fade=t=in:st={TITLE_REVEAL_START:.2f}:d={TITLE_FADE_DURATION:.2f}:alpha=1[card];"
            "[bg][card]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        audio_filter = f"apad=whole_dur={VIDEO_DURATION:.2f},atrim=duration={VIDEO_DURATION:.2f}"
        command = [
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-t", f"{VIDEO_DURATION:.3f}", "-i", str(starfield),
            "-loop", "1", "-framerate", str(FPS), "-t", f"{VIDEO_DURATION:.3f}", "-i", str(card),
            "-i", str(wav),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "2:a:0", "-af", audio_filter,
            "-r", str(FPS), "-frames:v", str(round(VIDEO_DURATION * FPS)),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE), "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(output),
        ]
        run(command, "Не удалось собрать MP4-пробник")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", type=Path, default=DEFAULT_CARD, help="PNG общей заставки с названием серии")
    parser.add_argument("--source-audio", type=Path, default=DEFAULT_SOURCE_AUDIO, help="исходный CC0 logo sting")
    parser.add_argument("--wav", type=Path, default=DEFAULT_WAV, help="куда сохранить обработанный мастер WAV")
    parser.add_argument("--output", type=Path, default=DEFAULT_VIDEO, help="куда сохранить MP4-пробник")
    parser.add_argument("--ffmpeg", help="путь к FFmpeg; по умолчанию берётся из PATH")
    args = parser.parse_args()

    card = args.card.expanduser().resolve()
    source = args.source_audio.expanduser().resolve()
    wav = args.wav.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not card.is_file():
        raise SystemExit(f"Не найден PNG заставки: {card}")
    if not source.is_file():
        raise SystemExit(f"Не найден исходный CC0-джингл: {source}")
    ffmpeg = find_ffmpeg(args.ffmpeg)
    make_jingle(ffmpeg, source, wav)
    render_video(ffmpeg, card, wav, output)
    print(f"Источник джингла (CC0 1.0): {source}")
    print(f"Мастер звука: {wav}")
    print(f"Пробник заставки: {output}")
    print(f"Длительность заставки: {VIDEO_DURATION:.1f} с; {WIDTH}x{HEIGHT}; {FPS} fps")


if __name__ == "__main__":
    main()
