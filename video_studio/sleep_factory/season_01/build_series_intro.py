#!/usr/bin/env python3
"""Build a reusable, six-second series opener with an original short melody.

Requires Python 3 (standard library only) and FFmpeg with libx264 + AAC.
The melody is synthesized directly as 48 kHz, 24-bit stereo PCM. The title card
fades in over a generated starfield, then receives a very gentle push-in.

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
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CARD = ROOT / "series_intro_alternative.png"
DEFAULT_WAV = ROOT / "series_micro_jingle.wav"
DEFAULT_VIDEO = ROOT / "series_intro_preview.mp4"
WIDTH, HEIGHT, FPS = 1280, 720, 24
SAMPLE_RATE = 48_000
DURATION = 6.0

# A tiny, original G-major phrase: warm plucks that rise and resolve on G.
NOTES = [
    (392.00, 0.00),  # G4
    (493.88, 0.38),  # B4
    (587.33, 0.76),  # D5
    (493.88, 1.14),  # B4
    (783.99, 1.52),  # G5
]


def synthesize_melody(path: Path, duration: float = DURATION) -> None:
    """Write an original bell/pluck melody with a soft stereo echo tail."""
    count = round(duration * SAMPLE_RATE)
    dry_left = array("f", [0.0]) * count
    dry_right = array("f", [0.0]) * count

    for index, (frequency, start) in enumerate(NOTES):
        start_sample = round(start * SAMPLE_RATE)
        # Let the final note ring longer so it carries the reveal of the title card.
        decay = 0.92 if index == len(NOTES) - 1 else 0.34
        note_samples = min(round((1.70 if index == len(NOTES) - 1 else 0.72) * SAMPLE_RATE), count - start_sample)
        pan_left, pan_right = ((0.77, 0.67) if index % 2 == 0 else (0.67, 0.77))
        amplitude = 0.205

        for offset in range(note_samples):
            t = offset / SAMPLE_RATE
            attack = min(1.0, t / 0.009)
            envelope = attack * math.exp(-t / decay)
            # Harmonics give the sine-based voice a soft, wooden/celesta-like edge.
            tone = (
                math.sin(2.0 * math.pi * frequency * t)
                + 0.31 * math.sin(2.0 * math.pi * frequency * 2.0 * t)
                + 0.14 * math.sin(2.0 * math.pi * frequency * 3.0 * t)
                + 0.055 * math.sin(2.0 * math.pi * frequency * 4.08 * t)
            )
            sample = amplitude * envelope * tone
            pos = start_sample + offset
            dry_left[pos] += sample * pan_left
            dry_right[pos] += sample * pan_right

    # A few quiet, short reflections add warmth without turning this into a long sting.
    reflections = [
        (0.23, 0.22),
        (0.47, 0.16),
        (0.78, 0.11),
        (1.16, 0.075),
        (1.62, 0.045),
        (2.12, 0.025),
    ]
    left = array("f", dry_left)
    right = array("f", dry_right)
    for delay_seconds, gain in reflections:
        delay = round(delay_seconds * SAMPLE_RATE)
        for i in range(count - delay):
            # Slight cross-feed widens the echo while keeping the melody centered.
            left[i + delay] += gain * (0.82 * dry_left[i] + 0.18 * dry_right[i])
            right[i + delay] += gain * (0.82 * dry_right[i] + 0.18 * dry_left[i])

    peak = max(max(abs(v) for v in left), max(abs(v) for v in right), 1e-9)
    target_peak = 0.38  # approximately -8.4 dBFS, leaving AAC true-peak headroom
    scale = target_peak / peak

    pcm = bytearray(count * 6)  # 24-bit stereo
    out = 0
    for i in range(count):
        # Fade the final reflection smoothly; keep the title card free of a hard cutoff.
        fade_start = round(5.15 * SAMPLE_RATE)
        fade = 1.0 if i < fade_start else max(0.0, (count - i) / max(1, count - fade_start))
        for value in (left[i], right[i]):
            quantized = max(-8_388_608, min(8_388_607, round(value * scale * fade * 8_388_607)))
            if quantized < 0:
                quantized += 1 << 24
            pcm[out] = quantized & 0xFF
            pcm[out + 1] = (quantized >> 8) & 0xFF
            pcm[out + 2] = (quantized >> 16) & 0xFF
            out += 3

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(3)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)


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

    # Sparse, restrained stars; a handful get a tiny cross-shaped glint.
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


def render_video(ffmpeg: str, card: Path, wav: Path, output: Path, duration: float = DURATION) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="series_intro_") as tmp:
        starfield = Path(tmp) / "starfield.ppm"
        make_starfield(starfield)
        filter_complex = (
            f"[0:v]scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1,format=rgba,"
            "fade=t=in:st=0:d=0.25[bg];"
            f"[1:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.00022,1.04)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
            "setsar=1,format=rgba,fade=t=in:st=1.25:d=0.65:alpha=1[card];"
            "[bg][card]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        command = [
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(starfield),
            "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(card),
            "-i", str(wav),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "2:a:0",
            "-r", str(FPS), "-frames:v", str(round(duration * FPS)),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE), "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(output),
        ]
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            detail = (result.stderr or result.stdout or "нет подробностей").strip()
            raise SystemExit(f"FFmpeg завершился с ошибкой:\n{detail[-5000:]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", type=Path, default=DEFAULT_CARD, help="PNG общей заставки с названием серии")
    parser.add_argument("--wav", type=Path, default=DEFAULT_WAV, help="куда сохранить мастер мелодии WAV")
    parser.add_argument("--output", type=Path, default=DEFAULT_VIDEO, help="куда сохранить MP4-пробник")
    parser.add_argument("--ffmpeg", help="путь к FFmpeg; по умолчанию берётся из PATH")
    args = parser.parse_args()

    card = args.card.expanduser().resolve()
    wav = args.wav.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not card.is_file():
        raise SystemExit(f"Не найден PNG заставки: {card}")
    ffmpeg = find_ffmpeg(args.ffmpeg)
    synthesize_melody(wav)
    render_video(ffmpeg, card, wav, output)
    print(f"Мастер мелодии: {wav}")
    print(f"Пробник заставки: {output}")
    print(f"Длительность: {DURATION:.1f} с; {WIDTH}x{HEIGHT}; {FPS} fps")


if __name__ == "__main__":
    main()
