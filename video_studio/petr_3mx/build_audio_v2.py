import subprocess, re, json, os

BASE = "/home/user/-/video_studio/petr_3mx"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-BeatOne.ogg"
OUT = os.path.join(BASE, "master_horizontal_16x9.mp3")

TEMPO = 1.18
INTRO_PAD = 2.6      # music-only intro before first block
GAP = 1.35           # pause between blocks
OUTRO_PAD = 3.2      # music-only outro

VO_CHAIN = (
    f"atempo={TEMPO},"
    "highpass=f=70,"
    "equalizer=f=120:t=q:w=1.0:g=2.5,"
    "equalizer=f=3200:t=q:w=1.6:g=3.0,"
    "acompressor=threshold=-20dB:ratio=4:attack=4:release=60,"
    "loudnorm=I=-15:TP=-1.5:LRA=9"
)


def dur(path):
    p = subprocess.run(["ffmpeg", "-i", path], stderr=subprocess.PIPE, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# 1. Process each raw VO
proc = []
for i in range(1, 5):
    src = os.path.join(BASE, f"raw_vo_{i}.mp3")
    dst = os.path.join(BASE, f"proc_vo_{i}.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-af", VO_CHAIN,
        "-ar", "48000", "-ac", "2", "-b:a", "192k", dst
    ], check=True, stderr=subprocess.DEVNULL)
    proc.append(dst)
    print(f"processed {os.path.basename(src)} -> {dur(dst):.2f}s")

# 2. Timeline
starts = []
t = INTRO_PAD
for i, p in enumerate(proc):
    starts.append(t)
    t += dur(p)
    if i < 3:
        t += GAP
total = t + OUTRO_PAD
print("starts:", [round(s, 2) for s in starts], "total:", round(total, 2))

# 3. Mix
delays = "".join(
    f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v{i}];"
    for i, s in enumerate(starts)
)
labels = "".join(f"[v{i}]" for i in range(4))
fc = (
    delays
    + labels + "amix=inputs=4:dropout_transition=0:normalize=0,"
    + "apad=whole_dur=" + str(total) + "[vo];"
    + f"[{len(proc)}:a]atrim=0:{total + 2},asetpts=PTS-STARTPTS,"
      "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
    + "[bg0]volume=0.30,afade=t=in:st=0:d=1.2[bg1];"
    + "[vo]asplit=2[vo_sc][vo_out];"
    + "[bg1][vo_sc]sidechaincompress=threshold=0.06:ratio=6:attack=8:release=250[bg_duck];"
    + f"[bg_duck]afade=t=out:st={max(0, total-OUTRO_PAD-0.4):.2f}:d={OUTRO_PAD+0.4:.2f}[bgf];"
    + "[vo_out]volume=1.35[vob];"
    + "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
      "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=10[out]"
)

cmd = ["ffmpeg", "-y"]
for p in proc:
    cmd += ["-i", p]
cmd += ["-i", MUSIC, "-filter_complex", fc, "-map", "[out]",
        "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", OUT]
subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

# 4. Verify
out = subprocess.check_output(["ffmpeg", "-i", OUT, "-af", "volumedetect", "-f", "null", "-"],
                              stderr=subprocess.STDOUT).decode()
for line in out.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print(line.strip())
print("MASTER:", OUT, f"{dur(OUT):.2f}s")

# 5. Timeline for renderer
scenes = []
for i, s in enumerate(starts):
    end = starts[i + 1] if i < 3 else total
    scenes.append({"idx": i + 1, "start": round(s, 3), "end": round(end, 3)})
json.dump({"total": round(total, 3), "scenes": scenes}, open(os.path.join(BASE, "timeline.json"), "w"), ensure_ascii=False, indent=2)
print(json.dumps(scenes, ensure_ascii=False))
