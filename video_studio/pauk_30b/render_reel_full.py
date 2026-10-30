import os, sys, time, subprocess
sys.path.insert(0, "/home/user/-/video_studio/pauk_30b")
import render_reel as R

BASE = "/home/user/-/video_studio/pauk_30b"
AUDIO = os.path.join(BASE, "master_reel_9x16.mp3")
OUT = os.path.join(BASE, "v_okope_pauk_30b_reel_9x16.mp4")

FPS = 30
DUR = 50.83
N = int(DUR * FPS)
print("frames:", N, flush=True)

cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{R.W}x{R.H}", "-r", str(FPS), "-i", "-",
       "-i", AUDIO,
       "-c:v", "libx264", "-preset", "medium", "-crf", "19",
       "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
       "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", OUT]

p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
t0 = time.time()
for i in range(N):
    p.stdin.write(R.render_frame(i / FPS).tobytes())
    if i % 200 == 0:
        el = time.time() - t0
        print(f"{i}/{N} {i/N*100:.0f}% {i/max(el,.01):.2f}fps", flush=True)
p.stdin.close()
print("rc", p.wait(), "elapsed", round(time.time() - t0, 1), flush=True)
print("size", os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING", flush=True)
