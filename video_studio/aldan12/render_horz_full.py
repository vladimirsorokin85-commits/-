# -*- coding: utf-8 -*-
"""Полный рендер горизонтали: 1920×1080@30 → ffmpeg (libx264, AAC 320k) + звук."""
import json
import os
import subprocess
import sys
import time

BASE = "/home/user/-/video_studio/aldan12"
sys.path.insert(0, BASE)
import render_horz as R  # noqa: E402

FF = "/home/user/.local/bin/ffmpeg"
OUT = os.path.join(BASE, "v_okope_aldan12_horizontal_16x9.mp4")
AUDIO = os.path.join(BASE, "master_aldan_horizontal.mp3")

if not os.path.exists(AUDIO):
    sys.exit("!! нет master_aldan_horizontal.mp3 — сначала build_audio_h.py")
if not os.path.exists(os.path.join(BASE, "horizontal_timeline.json")):
    sys.exit("!! нет horizontal_timeline.json")

lines, total = R.load_plan()
N = int(round(total * R.FPS))
print(f"кадров {N} · таймлайн {total:.2f}s · 90 реплик", flush=True)

cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}",
       "-r", str(R.FPS), "-i", "-", "-i", AUDIO,
       "-c:v", "libx264", "-preset", "medium", "-crf", "19",
       "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
       "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
t0 = time.time()
last = len(lines)
for f in range(N):
    t = f / R.FPS
    it = R.at(t, lines)
    im = R.render(it["n"], it["name"], it["block"], t, it["start"],
                  it["end"] - it["start"], total, last=(it["n"] == last))
    p.stdin.write(im.tobytes())
    if f % 600 == 0:
        el = time.time() - t0
        print(f"{f}/{N}  {f / max(el, .01):.2f} fps  ETA {(N - f) / max(f / max(el, .01), .01) / 60:.1f} мин",
              flush=True)
p.stdin.close()
rc = p.wait()
print("rc", rc, "elapsed", round((time.time() - t0) / 60, 1), "мин", flush=True)
print("size", os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING", flush=True)
