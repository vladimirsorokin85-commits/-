# -*- coding: utf-8 -*-
"""«В ОКОПЕ» — РЭБ-рюкзак «ЗОНТ» S8, вертикальный Reels 9:16."""
import os, re, json, subprocess, sys

BASE = "/home/user/-/video_studio/zont_s8"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-BeatOne.ogg"
MUSIC_OFFSET = 68.0   # самый плотный участок мастера
assert "/music_downloaded/" in MUSIC, "разрешена ТОЛЬКО реальная скачанная музыка"
sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check
_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

INTRO = 2.40
GAP = 0.85
OUTRO = 0.70
TARGETS = [5.30, 8.80, 9.30, 8.40]

VO_CHAIN = ("highpass=f=70,"
            "equalizer=f=120:t=q:w=1.0:g=2.5,"
            "equalizer=f=3200:t=q:w=1.6:g=3.0,"
            "acompressor=threshold=-20dB:ratio=4:attack=4:release=60,"
            "loudnorm=I=-15:TP=-1.5:LRA=9")


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


starts, t = [], INTRO
for i, w in enumerate(TARGETS):
    starts.append(round(t, 3))
    t += w + (GAP if i < len(TARGETS) - 1 else 0)
total = round(t + OUTRO, 3)

proc = []
for i, (target, start) in enumerate(zip(TARGETS, starts), 1):
    src = os.path.join(BASE, f"vo_{i}.mp3")
    d0 = dur(src)
    tempo = max(1.12, min(1.36, d0 / (target - 0.28)))
    dst = os.path.join(BASE, f"proc_{i}.mp3")
    run([FF, "-y", "-i", src, "-af", f"atempo={tempo:.4f},{VO_CHAIN}",
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print(f"vo {i}: raw {d0:.2f}s tempo {tempo:.3f} -> {d1:.2f}s (окно {target:.2f})")
    if d1 > target - 0.05:
        sys.exit("!! не влезает")
    proc.append(dst)

n = len(proc)
delays = "".join(
    f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},"
    "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    f"[v{i}];" for i, s in enumerate(starts))
labels = "".join(f"[v{i}]" for i in range(n))
fc = (delays + labels +
      f"amix=inputs={n}:dropout_transition=0:normalize=0,apad=whole_dur={total}[vo];"
      f"[{n}:a]atrim={MUSIC_OFFSET}:{MUSIC_OFFSET + total + 2},asetpts=PTS-STARTPTS,"
      "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
      "[bg0]highpass=f=32,bass=g=3.5:f=95:w=0.6,acompressor=threshold=-15dB:ratio=3:attack=8:release=120,"
      "dynaudnorm=f=300:g=8:p=0.85:m=6,loudnorm=I=-11:TP=-2:LRA=9,afade=t=in:st=0:d=0.6[bg1];"
      "[vo]asplit=2[vo_sc][vo_out];"
      "[bg1][vo_sc]sidechaincompress=threshold=0.032:ratio=9:attack=5:release=190[bg_duck];"
      f"[bg_duck]afade=t=out:st={total - OUTRO - 0.4:.2f}:d={OUTRO + 0.4:.2f}[bgf];"
      "[vo_out]volume=1.35[vob];"
      "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=10[out]")

cmd = [FF, "-y"]
for p in proc:
    cmd += ["-i", p]
out = os.path.join(BASE, "master_zont_s8_9x16.mp3")
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]",
        "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", out]
run(cmd)

o = subprocess.check_output([FF, "-hide_banner", "-i", out, "-af", "volumedetect",
                             "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print("   ", line.strip())
print(f"MASTER {out} {dur(out):.2f}s starts {starts} total {total}")
json.dump({"total": total, "starts": starts, "blocks": TARGETS},
          open(os.path.join(BASE, "timeline.json"), "w"), ensure_ascii=False, indent=2)
