#!/bin/sh
# Кадры из видео заказчика → последовательности для рендерера (1080×1920, 30 fps).
# Нужны только для рендера; в git не лежат (35 МБ), пересоздаются этой командой.
set -e
cd "$(dirname "$0")"
FF="${FF:-/home/user/.local/bin/ffmpeg}"
mkdir -p assets/vidfr/a assets/vidfr/b assets/vidfr/c assets/vidfr/d
"$FF" -hide_banner -loglevel error -ss 2.4  -t 4.2 -i assets/video/client_kit_1.mp4 -vf "fps=30,scale=1080:1920:flags=lanczos" -q:v 3 assets/vidfr/a/%03d.jpg
"$FF" -hide_banner -loglevel error -ss 13.0 -t 3.6 -i assets/video/client_kit_1.mp4 -vf "fps=30,scale=1080:1920:flags=lanczos" -q:v 3 assets/vidfr/b/%03d.jpg
"$FF" -hide_banner -loglevel error -ss 0.6  -t 3.6 -i assets/video/client_kit_2.mp4 -vf "fps=30,scale=1080:1920:flags=lanczos" -q:v 3 assets/vidfr/c/%03d.jpg
"$FF" -hide_banner -loglevel error -ss 9.0  -t 4.6 -i assets/video/client_kit_1.mp4 -vf "fps=30,scale=1080:1920:flags=lanczos" -q:v 3 assets/vidfr/d/%03d.jpg
echo "готово: $(ls assets/vidfr/*/ | wc -l) файлов"
