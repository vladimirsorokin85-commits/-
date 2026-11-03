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
OUT = os.path.join(BASE, "v_okope_aldan12_horizontal_16x9_v1.mp4")
AUDIO = os.path.join(BASE, "master_aldan_horizontal.mp3")

LINES, TOTAL = R.load_plan()
N = int(round(TOTAL * R.FPS))
LIMIT = int(os.environ.get("LIMIT", "0")) or N
WORKERS = int(os.environ.get("WORKERS", "2"))


def frame_bytes(f):
    t = f / R.FPS
    it = R.at(t, LINES)
    im = R.render(it["n"], it["name"], it["block"], t, it["start"],
                  it["end"] - it["start"], TOTAL, last=(it["n"] == len(LINES)),
                  vo_text=it.get("text", ""))
    return im.tobytes()


def main():
    assert os.path.exists(AUDIO), "нет master_aldan_horizontal.mp3"
    print(f"кадров {N} · таймлайн {TOTAL:.2f}s · воркеров {WORKERS} · лимит {LIMIT}", flush=True)
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}",
           "-r", str(R.FPS), "-i", "-", "-i", AUDIO,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-x264-params", "keyint=60:min-keyint=30:scenecut=0",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()

    def feed(gen):
        for f, buf in gen:
            p.stdin.write(buf)
            if f % 300 == 0:
                el = max(time.time() - t0, .01)
                fps = f / el if f else 0
                eta = (LIMIT - f) / fps / 60 if fps else 0
                print(f"{f}/{LIMIT}  {fps:.2f} fps  ETA {eta:.1f} мин", flush=True)

    if WORKERS > 1:
        import multiprocessing as mp
        with mp.Pool(WORKERS) as pool:
            feed(enumerate(pool.imap(frame_bytes, range(LIMIT), chunksize=3)))
    else:
        feed((f, frame_bytes(f)) for f in range(LIMIT))

    p.stdin.close()
    rc = p.wait()
    print("rc", rc, "elapsed", round((time.time() - t0) / 60, 1), "мин", flush=True)
    print("size", os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING", flush=True)


if __name__ == "__main__":
    main()
