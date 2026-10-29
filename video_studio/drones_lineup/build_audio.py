# -*- coding: utf-8 -*-
"""«В ОКОПЕ» — ДРОНЫ В НАЛИЧИИ, вертикальный Reels 9:16. Звук: voice-28 + реальный мастер."""
import os, re, json, subprocess, sys

BASE = "/home/user/-/video_studio/drones_lineup"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Chronos.ogg"
MUSIC_OFFSET = 60.0          # плотный участок реального мастера
assert "/music_downloaded/" in MUSIC, "разрешена ТОЛЬКО реальная скачанная музыка"

# границы сцен (совпадают с render.py)
BOUNDS = [0.00, 4.20, 10.60, 17.40, 23.60, 30.20, 34.60, 40.60]
LEAD = 0.28                  # отступ от начала сцены до голоса
TAIL = 0.55                  # сколько оставить после голоса
OUTRO = 0.70

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


TARGETS = [round(BOUNDS[i + 1] - BOUNDS[i] - TAIL, 3) for i in range(len(BOUNDS) - 1)]
starts = [round(b + LEAD, 3) for b in BOUNDS[:-1]]
total = round(BOUNDS[-1], 3)

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
        sys.exit(f"!! vo {i} не влезает в окно")
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
      "[bg0]highpass=f=38,volume=0.62,afade=t=in:st=0:d=0.6[bg1];"
      "[vo]asplit=2[vo_sc][vo_out];"
      "[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=180[bg_duck];"
      f"[bg_duck]afade=t=out:st={total - OUTRO - 0.4:.2f}:d={OUTRO + 0.4:.2f}[bgf];"
      "[vo_out]volume=1.35[vob];"
      "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=10[out]")

cmd = [FF, "-y"]
for p in proc:
    cmd += ["-i", p]
out = os.path.join(BASE, "master_drones_9x16.mp3")
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]",
        "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", out]
run(cmd)

o = subprocess.check_output([FF, "-hide_banner", "-i", out, "-af", "volumedetect",
                             "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print("   ", line.strip())
print(f"MASTER {out} {dur(out):.2f}s starts {starts} total {total}")
json.dump({"total": total, "starts": starts, "blocks": TARGETS, "bounds": BOUNDS},
          open(os.path.join(BASE, "timeline.json"), "w"), ensure_ascii=False, indent=2)
