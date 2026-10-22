#!/usr/bin/env python3
"""Split a finished MP4 into GitHub-friendly chunks and create restore scripts."""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

CHUNK_BYTES = 75 * 1024 * 1024
REPOSITORY = "vladimirsorokin85-commits/-"
BRANCH = "arena/edfffcf3-repo"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_readme(filename: str, parts: list[str], digest: str, duration: float,
                   speech_share: float, resolution: str, fps: int) -> str:
    base = ("https://raw.githubusercontent.com/" + REPOSITORY + "/" + BRANCH +
            "/video_studio/sleep_factory/season_01/episode_05/rendered/github_download/")
    rows = "\n".join(f"{name}:\n{base}{name}\n" for name in parts)
    return (
        "СБОРКА ВИДЕО S01E05 — «ПУСТОЕ МЕСТО НА КАРТЕ»\n\n"
        f"Полный MP4 разделён на {len(parts)} части по 75 МиБ или меньше.\n"
        "Скачайте все части в одну папку:\n\n" + rows + "\n"
        "Windows — скачайте и запустите RESTORE_VIDEO_WINDOWS.bat:\n" +
        base + "RESTORE_VIDEO_WINDOWS.bat\n\n"
        "Linux/macOS — скачайте restore_video.sh и выполните `sh restore_video.sh`:\n" +
        base + "restore_video.sh\n\n"
        "SHA-256 не требует отдельной загрузки: контрольная сумма встроена в оба скрипта. "
        "Файл .sha256 приложен только для ручной сверки.\n\n"
        f"Файл: {filename}\n"
        f"Длительность: {duration / 60:.3f} мин; речь по WebRTC VAD mode 2: {speech_share:.2%}.\n"
        f"Параметры видео: {resolution}, {fps} fps, H.264/AAC.\n"
        f"SHA-256: {digest}\n"
    )


def windows_batch(filename: str, parts: list[str], digest: str) -> str:
    names = " ".join(parts)
    joined = "+".join(parts)
    return f"""@echo off
setlocal EnableExtensions
cd /d "%~dp0"

for %%F in ({names}) do (
  if not exist "%%F" (
    echo Missing file: %%F
    pause
    exit /b 1
  )
)

copy /b /y {joined} {filename} >nul
if errorlevel 1 (
  echo Failed to assemble {filename}.
  pause
  exit /b 1
)

set "EXPECTED={digest}"
set "ACTUAL="
for /f "delims=" %%H in ('certutil -hashfile {filename} SHA256 ^| findstr /r /i "^[0-9a-f][0-9a-f]*$"') do set "ACTUAL=%%H"
if not defined ACTUAL (
  echo Could not calculate the MP4 SHA-256.
  pause
  exit /b 1
)
if /i not "%ACTUAL%"=="%EXPECTED%" (
  echo SHA-256 mismatch. Check the downloaded parts.
  echo Expected: %EXPECTED%
  echo Actual:   %ACTUAL%
  pause
  exit /b 1
)

echo Restored and verified: {filename}
echo SHA-256: %ACTUAL%
pause
"""


def shell_restore(filename: str, parts: list[str], digest: str) -> str:
    joined = " ".join(parts)
    return f"""#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"
expected={digest}
cat {joined} > {filename}

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum {filename} | awk '{{print $1}}')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 {filename} | awk '{{print $1}}')
else
  printf 'No SHA-256 utility found (sha256sum or shasum required).\\n' >&2
  exit 1
fi

if [ "$actual" != "$expected" ]; then
  printf 'SHA-256 mismatch. Expected %s, got %s.\\n' "$expected" "$actual" >&2
  exit 1
fi

printf 'Restored and verified: {filename}\\nSHA-256: %s\\n' "$actual"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Final MP4 to split")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).with_name("rendered") / "github_download")
    parser.add_argument("--filename", default="s01e05_full.mp4")
    parser.add_argument("--chunk-bytes", type=int, default=CHUNK_BYTES)
    parser.add_argument("--duration", type=float, required=True, help="Final MP4 duration in seconds")
    parser.add_argument("--speech-share", type=float, required=True, help="Measured active speech share, 0–1")
    parser.add_argument("--resolution", default="1280×720")
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    destination = args.output_dir.expanduser().resolve()
    if not video.is_file():
        parser.error(f"MP4 not found: {video}")
    if args.chunk_bytes < 1 or not 0 < args.speech_share <= 1 or args.duration <= 0:
        parser.error("chunk size, duration and speech share must be positive")

    destination.mkdir(parents=True, exist_ok=True)
    for old in destination.glob(args.filename + ".part[0-9][0-9]"):
        old.unlink()

    parts: list[str] = []
    with video.open("rb") as source:
        index = 0
        while True:
            name = f"{args.filename}.part{index:02d}"
            target = destination / name
            remaining = args.chunk_bytes
            wrote = 0
            with target.open("wb") as out:
                while remaining:
                    block = source.read(min(1024 * 1024, remaining))
                    if not block:
                        break
                    out.write(block)
                    wrote += len(block)
                    remaining -= len(block)
            if wrote == 0:
                target.unlink(missing_ok=True)
                break
            parts.append(name)
            index += 1
            if wrote < args.chunk_bytes:
                break

    digest = sha256(video)
    assembled = hashlib.sha256()
    total = 0
    for name in parts:
        part = destination / name
        if part.stat().st_size > args.chunk_bytes:
            raise RuntimeError(f"Part exceeds size limit: {name}")
        with part.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                assembled.update(block)
                total += len(block)
    if assembled.hexdigest() != digest or total != video.stat().st_size:
        raise RuntimeError("Split verification failed: reassembled checksum/size does not match")

    (destination / "RESTORE_VIDEO_WINDOWS.bat").write_text(
        windows_batch(args.filename, parts, digest), encoding="ascii", newline="\r\n")
    shell_path = destination / "restore_video.sh"
    shell_path.write_text(shell_restore(args.filename, parts, digest), encoding="utf-8")
    shell_path.chmod(0o755)
    (destination / f"{args.filename}.sha256").write_text(
        f"{digest}  {args.filename}\n", encoding="ascii")
    (destination / "README_RU.txt").write_text(
        package_readme(args.filename, parts, digest, args.duration,
                       args.speech_share, args.resolution, args.fps), encoding="utf-8")
    print(f"Parts: {len(parts)}; bytes: {total}; SHA-256: {digest}")
    for name in parts:
        print(f"{name}: {(destination / name).stat().st_size} bytes")
    print(f"Package: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
