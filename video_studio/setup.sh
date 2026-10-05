#!/usr/bin/env bash
# Restore the sandbox after a reset: python libs, ffmpeg, git history.
set -e
pip install -q --break-system-packages pillow numpy scipy imageio-ffmpeg pyloudnorm pedalboard librosa "opencv-python-headless<5" fonttools 2>&1 | tail -1
mkdir -p ~/.local/bin
ln -sf "$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" ~/.local/bin/ffmpeg
cd "$(dirname "$0")/.."
B=arena/01a100fe-repo
git fetch -q origin $B && git reset -q --mixed origin/$B
echo "ok: $(~/.local/bin/ffmpeg -version | head -1 | cut -c1-30) | git $(git log --oneline -1)"
