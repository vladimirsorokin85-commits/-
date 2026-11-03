import subprocess, re, json, os

BASE = "/home/user/-/video_studio/petr_3mx"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Arpent.ogg"
OUT = os.path.join(BASE, "master_reel_9x16.mp3")

TEMPO = 1.18
INTRO_PAD = 1.8
GAP = 0.55
OUTRO_PAD = 2.6

VO_CHAIN = (
    f"atempo={TEMPO},highpass=f=75,"
    "equalizer=f=120:t=q:w=1.0:g=3.0,"
    "equalizer=f=3000:t=q:w=1.6:g=3.5,"
    "acompressor=threshold=-20dB:ratio=4:attack=4:release=60,"
    "loudnorm=I=-14:TP=-1.5:LRA=9"
)

def dur(p):
    s = subprocess.run(["ffmpeg", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)

proc = []
for i in (1, 2, 3):
    src = os.path.join(BASE, f"reel_raw_{i}.mp3")
    dst = os.path.join(BASE, f"reel_proc_{i}.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", src, "-af", VO_CHAIN,
                    "-ar", "48000", "-ac", "2", "-b:a", "192k", dst],
                   check=True, stderr=subprocess.DEVNULL)
    proc.append(dst)
    print(f"reel_proc_{i}: {dur(dst):.2f}s")

starts, t = [], INTRO_PAD
for i, p in enumerate(proc):
    starts.append(t)
    t += dur(p)
    if i < 2:
        t += GAP
total = t + OUTRO_PAD
print("starts", [round(x, 2) for x in starts], "total", round(total, 2))

delays = "".join(
    f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v{i}];"
    for i, s in enumerate(starts))
labels = "".join(f"[v{i}]" for i in range(3))
fc = (delays + labels +
      "amix=inputs=3:dropout_transition=0:normalize=0,apad=whole_dur=" + f"{total}[vo];"
      f"[3:a]atrim=0:{total+2},asetpts=PTS-STARTPTS,"
      "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
      "r[bg0]volume=0.34,afade=t=in:st=0:d=0.8[bg1];"
      "[vo]asplit=2[vo_sc][vo_out];"
      "[bg1][vo_sc]sidechaincompress=threshold=0.06:ratio=7:attack=6:release=220[bg_duck];"
      f"[bg_duck]afade=t=out:st={max(0,total-OUTRO_PAD-0.3):.2f}:d={OUTRO_PAD+0.3:.2f}[bgf];"
      "[vo_out]volume=1.35[vob];"
      "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-13:TP=-1.0:LRA=9[out]").replace("r[bg0]", "[bg0]")

cmd = ["ffmpeg", "-y"]
for p in proc:
    cmd += ["-i", p]
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]", "-t", f"{total:.2f}",
        "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", OUT]
subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

o = subprocess.check_output(["ffmpeg", "-i", OUT, "-af", "volumedetect", "-f", "null", "-"],
                            stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print(line.strip())
print("REEL MASTER:", OUT, f"{dur(OUT):.2f}s")

scenes = [{"i": i + 1, "s": round(starts[i], 3),
           "e": round(starts[i + 1] if i < 2 else total, 3)} for i in range(3)]
json.dump({"total": round(total, 3), "scenes": scenes},
          open(os.path.join(BASE, "timeline_reel.json"), "w"), indent=2)
print(json.dumps(scenes))
