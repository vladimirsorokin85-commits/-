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
            "/video_studio/sleep_factory/season_02/episode_02/rendered/github_download/")
    rows = "\n".join(f"{name}:\n{base}{name}\n" for name in parts)
    return (
        "СБОРКА ВИДЕО S02E02 — ГРИМБАЛЬТ «КЭШ» ПОДГОРНЫЙ-404\n\n"
        f"Полный MP4 разделён на {len(parts)} части по 75 МиБ или меньше.\n"
        "Windows: достаточно скачать и запустить RESTORE_VIDEO_WINDOWS.bat — он "
        "загрузит недостающие или неполные части и соберёт видео. Нужен Windows PowerShell "
        "и доступ к GitHub. Если части уже скачаны вручную, положите их рядом с BAT.\n"
        "Ссылки на части для ручной загрузки:\n\n" + rows + "\n"
        "Windows BAT:\n" + base + "RESTORE_VIDEO_WINDOWS.bat\n"
        "PowerShell-helper (BAT загрузит его при необходимости):\n" +
        base + "restore_video_windows.ps1\n\n"
        "Linux/macOS — скачайте все части в одну папку и выполните `sh restore_video.sh`:\n" +
        base + "restore_video.sh\n\n"
        "SHA-256 не требует отдельной загрузки: контрольная сумма встроена в BAT, "
        "PowerShell-helper и shell restore. Файл .sha256 приложен только для ручной сверки.\n\n"
        f"Файл: {filename}\n"
        f"Длительность: {duration / 60:.3f} мин; речь по WebRTC VAD mode 2: {speech_share:.2%}.\n"
        f"Параметры видео: {resolution}, {fps} fps, H.264/AAC.\n"
        f"SHA-256: {digest}\n"
    )


def windows_restore_ps1(filename: str, parts: list[tuple[str, int]], digest: str) -> str:
    """Create the readable PowerShell worker used by the Windows BAT."""
    base = ("https://raw.githubusercontent.com/" + REPOSITORY + "/" + BRANCH +
            "/video_studio/sleep_factory/season_02/episode_02/rendered/github_download/")
    rows = "\n".join(
        f"    [pscustomobject]@{{ Name = '{name}'; Size = {size}; Url = '{base}{name}' }}"
        for name, size in parts
    )
    script = """param([string]$ExpectedSha256 = '__EXPECTED__')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$expected = $ExpectedSha256.Trim().ToLowerInvariant()
$embeddedExpected = '__EXPECTED__'
if ($expected -ne $embeddedExpected) {
    throw 'The checksum passed by the BAT does not match this helper.'
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$filename = '__FILENAME__'
$parts = @(
__PART_ROWS__
)
$destination = Join-Path $root $filename
$temp = $destination + '.tmp'

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    foreach ($part in $parts) {
        $partPath = Join-Path $root $part.Name
        $download = -not (Test-Path -LiteralPath $partPath)
        if (-not $download) {
            $download = (Get-Item -LiteralPath $partPath).Length -ne $part.Size
        }
        if ($download) {
            if (Test-Path -LiteralPath $partPath) {
                Remove-Item -LiteralPath $partPath -Force
            }
            Write-Host ("Downloading missing/incomplete part: " + $part.Name)
            $attempt = 0
            while ($attempt -lt 3) {
                $attempt++
                try {
                    Invoke-WebRequest -UseBasicParsing -Uri $part.Url -OutFile $partPath
                    break
                } catch {
                    if (Test-Path -LiteralPath $partPath) {
                        Remove-Item -LiteralPath $partPath -Force
                    }
                    if ($attempt -ge 3) { throw }
                    Start-Sleep -Seconds (2 * $attempt)
                }
            }
        } else {
            Write-Host ("Using downloaded part: " + $part.Name)
        }
        $actualSize = (Get-Item -LiteralPath $partPath).Length
        if ($actualSize -ne $part.Size) {
            throw ("Wrong size for " + $part.Name + ": expected " + $part.Size + ", got " + $actualSize)
        }
    }

    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force
    }
    $outputStream = [System.IO.File]::Open(
        $temp,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        foreach ($part in $parts) {
            $partPath = Join-Path $root $part.Name
            $inputStream = [System.IO.File]::OpenRead($partPath)
            try {
                $inputStream.CopyTo($outputStream)
            } finally {
                $inputStream.Dispose()
            }
        }
    } finally {
        $outputStream.Dispose()
    }

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($temp)
    try {
        $actual = ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
    if ($actual -ne $expected) {
        throw ("SHA-256 mismatch. Expected " + $expected + "; got " + $actual)
    }

    Move-Item -LiteralPath $temp -Destination $destination -Force
    Write-Host ("Restored and verified: " + $destination)
    Write-Host ("SHA-256: " + $actual)
} catch {
    Write-Host ("Restore failed: " + $_.Exception.Message) -ForegroundColor Red
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force
    }
    exit 1
}
"""
    return (script.replace("__FILENAME__", filename)
            .replace("__EXPECTED__", digest)
            .replace("__PART_ROWS__", rows))


def windows_batch(filename: str, parts: list[str], digest: str, helper_sha256: str) -> str:
    """Create a self-starting BAT that fetches its helper and missing chunks."""
    base = ("https://raw.githubusercontent.com/" + REPOSITORY + "/" + BRANCH +
            "/video_studio/sleep_factory/season_02/episode_02/rendered/github_download/")
    helper = "restore_video_windows.ps1"
    helper_url = base + helper
    return f"""@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 (
  echo Could not switch to the package folder: "%~dp0"
  pause
  exit /b 1
)
set "EXPECTED_SHA256={digest}"
set "EXPECTED_HELPER_SHA256={helper_sha256}"
set "HELPER={helper}"
set "PSEXE=%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
if not exist "%PSEXE%" set "PSEXE=powershell.exe"
if /i "%PSEXE%"=="powershell.exe" (
  where powershell.exe >nul 2>nul
  if errorlevel 1 (
    echo Windows PowerShell is required but was not found.
    pause
    exit /b 1
  )
)

call :verify_helper
if errorlevel 1 goto download_helper
goto start_restore

:download_helper
echo Downloading or refreshing the small restore helper from GitHub...
del /q "%HELPER%" 2>nul
"%PSEXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [System.Net.ServicePointManager]::SecurityProtocol=[System.Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '{helper_url}' -OutFile '{helper}' -ErrorAction Stop"
if errorlevel 1 goto helper_download_failed
call :verify_helper
if errorlevel 1 goto helper_hash_failed
goto start_restore

:start_restore
echo Restoring {filename}. Missing or incomplete parts will be downloaded from GitHub.
"%PSEXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0%HELPER%" -ExpectedSha256 "%EXPECTED_SHA256%"
if errorlevel 1 goto restore_failed
echo The complete video has been restored and verified in this folder.
pause
exit /b 0

:helper_download_failed
echo Could not download the helper. Check your GitHub connection or download {helper} manually beside this BAT.
pause
exit /b 1

:helper_hash_failed
echo The restore helper failed its SHA-256 check.
pause
exit /b 1

:restore_failed
echo Restore failed. Read the PowerShell error above and try again.
pause
exit /b 1

:verify_helper
set "ACTUAL_HELPER_SHA256="
if not exist "%HELPER%" exit /b 1
for /f "delims=" %%H in ('certutil -hashfile "%HELPER%" SHA256 ^| findstr /r /i "^[0-9a-f][0-9a-f]*$"') do set "ACTUAL_HELPER_SHA256=%%H"
if /i not "%ACTUAL_HELPER_SHA256%"=="%EXPECTED_HELPER_SHA256%" exit /b 1
exit /b 0
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
    parser.add_argument("--filename", default="s02e02_full.mp4")
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

    part_manifest = [(name, (destination / name).stat().st_size) for name in parts]
    helper_text = windows_restore_ps1(args.filename, part_manifest, digest)
    helper_path = destination / "restore_video_windows.ps1"
    helper_path.write_text(helper_text, encoding="ascii", newline="\n")
    helper_sha256 = hashlib.sha256(helper_text.encode("ascii")).hexdigest()
    (destination / "RESTORE_VIDEO_WINDOWS.bat").write_text(
        windows_batch(args.filename, parts, digest, helper_sha256),
        encoding="ascii", newline="\r\n")
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
