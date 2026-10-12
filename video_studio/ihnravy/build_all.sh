#!/usr/bin/env bash
# «Ноги довезут или похоронят» — full rebuild. Run ../setup.sh first after a sandbox reset.
set -euo pipefail
cd "$(dirname "$0")"
export PATH=~/.local/bin:$PATH
N=${N:-4}
python3 audio_stage.py
for i in $(seq 0 $((N-1))); do python3 render_stage.py part $i $N > /tmp/nogi/render_$i.log 2>&1 & done
wait
: > /tmp/nogi/parts.txt
for i in $(seq 0 $((N-1))); do echo "file '/tmp/nogi/part_$i.mp4'" >> /tmp/nogi/parts.txt; done
ffmpeg -y -v error -f concat -safe 0 -i /tmp/nogi/parts.txt -i /tmp/nogi/mix.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest /tmp/nogi/nogi_full_hq.mp4
echo "done: /tmp/nogi/nogi_full_hq.mp4"
