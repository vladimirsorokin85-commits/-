#!/usr/bin/env bash
# «Окопная смекалка» v4 — full rebuild.
# Requires: pip install --break-system-packages pillow numpy scipy imageio-ffmpeg ; `ffmpeg` on PATH.
set -euo pipefail
cd "$(dirname "$0")"
[ -f ../music_catalog/dnb_neuro_174.ogg ] || python3 music_dnb.py     # DnB / jungle beds
python3 audio_stage.py                        # voice + timeline + mix -> /tmp/smk4
python3 render_stage.py part 0 2 &            # frames in 2 parallel halves
python3 render_stage.py part 1 2
wait
printf "file '/tmp/smk4/part_0.mp4'\nfile '/tmp/smk4/part_1.mp4'\n" > /tmp/smk4/parts.txt
ffmpeg -y -v error -f concat -safe 0 -i /tmp/smk4/parts.txt -i /tmp/smk4/mix.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -movflags +faststart -shortest /tmp/smk4/full_hq.mp4
# workspace copy is size-capped (snapshot limit) — 2-pass ~720 kbit/s video
ffmpeg -y -v error -i /tmp/smk4/full_hq.mp4 -c:v libx264 -preset medium -b:v 720k -pass 1 -passlogfile /tmp/smk4/x264 -an -f mp4 /dev/null
ffmpeg -y -v error -i /tmp/smk4/full_hq.mp4 -c:v libx264 -preset medium -b:v 720k -maxrate 1800k -bufsize 3600k \
  -pass 2 -passlogfile /tmp/smk4/x264 -c:a aac -b:a 128k -movflags +faststart /home/user/-/smekalka_video.mp4
echo "done: /home/user/-/smekalka_video.mp4"
