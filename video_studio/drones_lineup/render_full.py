import os, sys, time, subprocess
sys.path.insert(0, "/home/user/-/video_studio/drones_lineup")
import render as R

BASE = "/home/user/-/video_studio/drones_lineup"
AUDIO = os.path.join(BASE, "master_drones_9x16.mp3")
OUT = os.path.join(BASE, "v_okope_drones_reel_9x16.mp4")
FPS, DUR = 30, R.TOTAL
N = int(round(DUR * FPS))
print("frames:", N, flush=True)
cmd = ["/home/user/.local/bin/ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{R.W}x{R.H}", "-r", str(FPS), "-i", "-", "-i", AUDIO,
       "-c:v", "libx264", "-preset", "medium", "-crf", "19",
       "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
       "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
t0 = time.time()
for i in range(N):
    p.stdin.write(R.render_frame(i / FPS).tobytes())
    if i % 150 == 0:
        el = time.time() - t0
        print(f"{i}/{N} {i/max(el,.01):.2f}fps", flush=True)
p.stdin.close()
print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
print("size", os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING", flush=True)
