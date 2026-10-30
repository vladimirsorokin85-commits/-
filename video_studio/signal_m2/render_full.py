import os, sys, time, subprocess
sys.path.insert(0, "/home/user/-/video_studio/signal_m2")
import render as R

BASE = "/home/user/-/video_studio/signal_m2"
FPS = 30

JOBS = [("A", "master_signal_m2_9x16.mp3", "v_okope_signal_m2_reel_9x16.mp4", 43.90),
        ("B", "master_kit_9x16.mp3", "v_okope_kit_reel_9x16.mp4", 44.05)]

for film, audio, out_name, dur in JOBS:
    audio = os.path.join(BASE, audio)
    out = os.path.join(BASE, out_name)
    n = int(dur * FPS)
    print(f"=== {film} frames {n}", flush=True)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{R.W}x{R.H}", "-r", str(FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(R.render_frame(film, i / FPS).tobytes())
        if i % 300 == 0:
            el = time.time() - t0
            print(f"{film} {i}/{n} {i/max(el,.01):.2f}fps", flush=True)
    p.stdin.close()
    print(film, "rc", p.wait(), "elapsed", round(time.time() - t0, 1),
          "size", os.path.getsize(out) if os.path.exists(out) else "MISSING", flush=True)
