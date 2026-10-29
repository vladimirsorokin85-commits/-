# -*- coding: utf-8 -*-
"""«Алдан-12» — вертикальный Reels 9:16: звук (голос voice-28 + реальный DnB)."""
import json
import os
import re
import subprocess
import sys

BASE = "/home/user/-/video_studio/aldan12"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-BeatOne.ogg"
MUSIC_OFFSET = 96.0
assert "/music_downloaded/" in MUSIC, "разрешена ТОЛЬКО реальная скачанная музыка"

sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

# сцены: (начало, целевая длина окна под голос)
SCENES = [
    ("hook", 0.00, 5.90),
    ("steps", 5.90, 4.00),
    ("qr", 9.90, 4.60),
    ("otg", 14.50, 5.10),
    ("flash", 19.60, 4.20),
    ("features", 23.80, 4.30),
    ("led", 28.10, 3.90),
    ("ascent", 32.00, 8.40),
]
LEAD = 0.22
OUTRO = 0.55
TOTAL = 40.40

VO_CHAIN = ("highpass=f=72,"
            "equalizer=f=110:t=q:w=1.0:g=3.0,"
            "equalizer=f=3400:t=q:w=1.5:g=3.5,"
            "acompressor=threshold=-19dB:ratio=4.5:attack=3:release=55,"
            "loudnorm=I=-14.5:TP=-1.4:LRA=8")


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


starts, windows = [], []
for i, (name, t0, win) in enumerate(SCENES):
    starts.append(round(t0 + LEAD, 3))
    windows.append(win - LEAD - 0.12)

proc = []
for i, (win, start) in enumerate(zip(windows, starts), 1):
    src = os.path.join(BASE, "vo", f"r{i}.mp3")
    d0 = dur(src)
    tempo = max(1.12, min(1.40, d0 / (win - 0.10)))
    dst = os.path.join(BASE, "vo", f"pr{i}.mp3")
    run([FF, "-y", "-i", src, "-af", f"atempo={tempo:.4f},{VO_CHAIN}",
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print(f"vo {i}: raw {d0:.2f}s tempo {tempo:.3f} -> {d1:.2f}s (окно {win:.2f})")
    if d1 > win:
        sys.exit(f"!! vo {i} не влезает")
    proc.append(dst)

n = len(proc)
delays = "".join(
    f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},"
    "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    f"[v{i}];" for i, s in enumerate(starts))
labels = "".join(f"[v{i}]" for i in range(n))
fc = (delays + labels +
      f"amix=inputs={n}:dropout_transition=0:normalize=0,apad=whole_dur={TOTAL}[vo];"
      f"[{n}:a]atrim={MUSIC_OFFSET}:{MUSIC_OFFSET + TOTAL + 2},asetpts=PTS-STARTPTS,"
      "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
      "[bg0]highpass=f=32,bass=g=3.0:f=95:w=0.6,"
      "acompressor=threshold=-15dB:ratio=3:attack=8:release=120,"
      "dynaudnorm=f=300:g=8:p=0.85:m=6,loudnorm=I=-11:TP=-2:LRA=9,"
      "afade=t=in:st=0:d=0.35[bg1];"
      "[vo]asplit=2[vo_sc][vo_out];"
      "[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=170[bg_duck];"
      f"[bg_duck]afade=t=out:st={TOTAL - OUTRO:.2f}:d={OUTRO:.2f}[bgf];"
      "[vo_out]volume=1.30[vob];"
      "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=50,loudnorm=I=-14:TP=-1.5:LRA=9[out]")

cmd = [FF, "-y"]
for p in proc:
    cmd += ["-i", p]
out = os.path.join(BASE, "master_aldan_reel.mp3")
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]",
        "-t", f"{TOTAL:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", out]
run(cmd)

o = subprocess.check_output([FF, "-hide_banner", "-i", out, "-af", "volumedetect",
                             "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print("   ", line.strip())
print(f"MASTER {out} {dur(out):.2f}s starts {starts}")
json.dump({"total": TOTAL, "starts": starts, "windows": windows,
           "scenes": [s[0] for s in SCENES]},
          open(os.path.join(BASE, "reel_timeline.json"), "w"), ensure_ascii=False, indent=1)
