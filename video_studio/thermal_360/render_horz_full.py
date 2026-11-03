"""Покадровый рендер горизонтали кусками: python3 render_horz_full.py START END OUT.mp4"""
import os
import subprocess
import sys
import time

sys.path.insert(0, "/home/user/-/video_studio/thermal_360")
import render_horz as R  # noqa: E402
from render_horz_base import TOTAL  # noqa: E402

FPS = 30
TOTAL_FRAMES = int(round(TOTAL * FPS))
a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
b = int(sys.argv[2]) if len(sys.argv) > 2 else TOTAL_FRAMES
out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/h.out.mp4"

cmd = ["/home/user/.local/bin/ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", "1920x1080", "-r", str(FPS), "-i", "-",
       "-c:v", "libx264", "-preset", "medium", "-crf", "20",
       "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
       "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
       "-movflags", "+faststart", out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
t0 = time.time()
for i in range(a, b):
    p.stdin.write(R.render_frame(i / FPS).tobytes())
    if (i - a) % 200 == 0:
        el = time.time() - t0
        print("%d/%d  %.2f fps  прошло %.0f с" % (i, b, (i - a) / max(el, .01), el), flush=True)
p.stdin.close()
print("rc", p.wait(), "время", round(time.time() - t0, 1), flush=True)
