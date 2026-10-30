# -*- coding: utf-8 -*-
"""«Добрыня» — сборка аудио-мастера с фиксированной сеткой сцен (вертикаль 9:16 (Reels))."""
import os, re, json, subprocess, sys

BASE = "/home/user/-/video_studio/dobrynya"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-BeatOne.ogg"

INTRO = 2.80
GAP = 1.05
OUTRO = 0.60
# целевые длительности речевых блоков
TARGETS = [12.00, 16.40, 12.20, 20.00, 6.30]
STARTS = []
t = INTRO
for i, w in enumerate(TARGETS):
    STARTS.append(round(t, 3))
    t += w + (GAP if i < len(TARGETS) - 1 else 0)
TOTAL = round(t + OUTRO, 3)

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


proc = []
for i, (target, start) in enumerate(zip(TARGETS, STARTS), 1):
    src = os.path.join(BASE, f"reel_vo_{i}.mp3")
    d0 = dur(src)
    tempo = d0 / (target - 0.30)
    dst = os.path.join(BASE, f"reel_proc_{i}.mp3")
    run([FF, "-y", "-i", src, "-af", f"atempo={tempo:.4f},{VO_CHAIN}",
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print(f"vo {i}: raw {d0:.2f}s  tempo {tempo:.3f}  ->  {d1:.2f}s  (окно {target:.2f}s)")
    if d1 > target - 0.05:
        sys.exit("!! блок не влезает в окно")
    proc.append(dst)

n = len(proc)
delays = "".join(
    f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},"
    "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    f"[v{i}];" for i, s in enumerate(STARTS))
labels = "".join(f"[v{i}]" for i in range(n))
fc = (delays + labels +
      f"amix=inputs={n}:dropout_transition=0:normalize=0,apad=whole_dur={TOTAL}[vo];"
      f"[{n}:a]atrim=0:{TOTAL + 2},asetpts=PTS-STARTPTS,"
      "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
      "[bg0]volume=0.30,afade=t=in:st=0:d=1.2[bg1];"
      "[vo]asplit=2[vo_sc][vo_out];"
      "[bg1][vo_sc]sidechaincompress=threshold=0.06:ratio=6:attack=8:release=250[bg_duck];"
      f"[bg_duck]afade=t=out:st={TOTAL - OUTRO - 0.4:.2f}:d={OUTRO + 0.4:.2f}[bgf];"
      "[vo_out]volume=1.35[vob];"
      "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=10[out]")

cmd = [FF, "-y"]
for p in proc:
    cmd += ["-i", p]
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]",
        "-t", f"{TOTAL:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k",
        os.path.join(BASE, "master_reel_9x16.mp3")]
run(cmd)

OUT = os.path.join(BASE, "master_reel_9x16.mp3")
o = subprocess.check_output([FF, "-hide_banner", "-i", OUT, "-af", "volumedetect",
                             "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print("   ", line.strip())
print("MASTER:", OUT, f"{dur(OUT):.2f}s", "| starts", STARTS, "| total", TOTAL)

json.dump({"total": TOTAL, "scenes": [
    {"idx": i + 1, "start": STARTS[i], "end": round(STARTS[i + 1], 3) if i < len(STARTS) - 1 else TOTAL}
    for i in range(len(STARTS))]},
    open(os.path.join(BASE, "timeline_reel.json"), "w"), ensure_ascii=False, indent=2)
print(json.dumps(json.load(open(os.path.join(BASE, "timeline_reel.json"))), ensure_ascii=False))
