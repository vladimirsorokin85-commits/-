# -*- coding: utf-8 -*-
"""Звук горизонтали «Тепловизор 360°»: 10 блоков voice-28 + Chronos (петля) + CC0 SFX."""
import json
import os
import re
import subprocess
import sys

BASE = "/home/user/-/video_studio/thermal_360"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Chronos.ogg"
SFX = "/home/user/-/video_studio/toolkit/sfx"
TOTAL = 232.01

assert "/music_downloaded/" in MUSIC
sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

BLOCKS = json.load(open(os.path.join(BASE, "vo_blocks.json"), encoding="utf-8"))
NAMES = [str(i) for i in range(1, 11)]
STARTS = [BLOCKS[n]["t0"] for n in NAMES] + [TOTAL]

VO_CHAIN = ("highpass=f=74,"
            "equalizer=f=115:t=q:w=1.0:g=3.0,"
            "equalizer=f=3400:t=q:w=1.5:g=3.4,"
            "acompressor=threshold=-19dB:ratio=4.2:attack=3:release=55,"
            "loudnorm=I=-15:TP=-1.6:LRA=9")


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


# ── 1. голос по блокам
proc, starts = [], []
for i, name in enumerate(NAMES):
    src = os.path.join(BASE, "vo", "h%s.mp3" % name)
    trim = os.path.join(BASE, "vo", "ch%s.mp3" % name)
    run([FF, "-y", "-i", src, "-af",
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,"
         "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse",
         "-ar", "48000", "-ac", "2", trim])
    d0 = dur(trim)
    win = STARTS[i + 1] - STARTS[i] - 0.25
    tempo = max(1.12, min(1.42, d0 / max(0.4, win - 0.10)))
    dst = os.path.join(BASE, "vo", "ph%s.mp3" % name)
    run([FF, "-y", "-i", trim, "-af", "atempo=%.4f,%s" % (tempo, VO_CHAIN),
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print("vo %-2s raw %6.2f tempo %.3f -> %6.2f  окно %6.2f  %s"
          % (name, d0, tempo, d1, win, "ok" if d1 <= win else "!! НЕ ВЛЕЗ"))
    if d1 > win:
        sys.exit("!! блок не влезает: " + name)
    proc.append(dst)
    starts.append(STARTS[i] + 0.12)

# ── 2. музыка: Chronos 129 с → два прохода по 128 с = 256 с
LOOP = 128.0
mus = os.path.join(BASE, "music_loop.m4a")
run([FF, "-y", "-ss", "0", "-t", "%.2f" % LOOP, "-i", MUSIC,
     "-ss", "0", "-t", "%.2f" % LOOP, "-i", MUSIC,
     "-filter_complex",
     "[0:a]afade=t=in:st=0:d=0.05,afade=t=out:st=%.2f:d=0.05[a];"
     "[1:a]afade=t=in:st=0:d=0.05[a2];[a][a2]concat=n=2:v=0:a=1[out]"
     % (LOOP - 0.05), "-map", "[out]", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", mus])
print("музыка-петля:", round(dur(mus), 2), "с")

# ── 3. эффекты на переходах блоков и ключевых кадрах
SFX_CUES = [("impact_deep", 0.0, 0.55), ("whoosh_transition", 25.51, 0.40),
            ("impact_deep", 53.34, 0.45), ("whoosh_transition", 75.58, 0.38),
            ("impact_deep", 97.32, 0.42), ("cut_tick", 135.10, 0.32),
            ("impact_deep", 135.10, 0.40), ("cut_tick", 153.24, 0.32),
            ("impact_deep", 175.31, 0.50), ("riser_tension", 190.5, 0.26),
            ("cut_tick", 195.31, 0.34), ("whoosh_transition", 215.17, 0.40),
            ("logo_sting", 227.0, 0.44)]

n_vo = len(proc)
inputs = [FF, "-y"]
for p in proc:
    inputs += ["-i", p]
inputs += ["-i", mus]
for f, _, _ in SFX_CUES:
    inputs += ["-i", os.path.join(SFX, f + ".mp3")]

fc = []
for i, s in enumerate(starts):
    ms = int(s * 1000)
    fc.append("[%d:a]adelay=%d|%d,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v%d]"
              % (i, ms, ms, i))
fc.append("".join("[v%d]" % i for i in range(n_vo)) +
          "amix=inputs=%d:dropout_transition=0:normalize=0,apad=whole_dur=%.2f[vo]" % (n_vo, TOTAL))
fc.append("[%d:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:"
          "channel_layouts=stereo[bg0]" % (n_vo, TOTAL + 2))
fc.append("[bg0]highpass=f=30,bass=g=2.6:f=95:w=0.6,"
          "acompressor=threshold=-15dB:ratio=2.8:attack=10:release=140,"
          "dynaudnorm=f=400:g=7:p=0.9:m=4,loudnorm=I=-13.5:TP=-2:LRA=9,"
          "afade=t=in:st=0:d=0.6[bg1]")
for j, (f, tt, vol) in enumerate(SFX_CUES):
    idx = n_vo + 1 + j
    ms = int(tt * 1000)
    fc.append("[%d:a]adelay=%d|%d,volume=%.2f,aformat=sample_fmts=fltp:sample_rates=48000:"
              "channel_layouts=stereo[fx%d]" % (idx, ms, ms, vol, j))
fc.append("".join("[fx%d]" % j for j in range(len(SFX_CUES))) +
          "amix=inputs=%d:dropout_transition=0:normalize=0,volume=0.85[fx]" % len(SFX_CUES))
fc.append("[vo]asplit=2[vo_sc][vo_out]")
fc.append("[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=8:attack=6:release=200[bg_duck]")
fc.append("[bg_duck]afade=t=out:st=%.2f:d=1.4[bgf]" % (TOTAL - 1.5))
fc.append("[vo_out]volume=1.32[vob]")
fc.append("[bgf][vob][fx]amix=inputs=3:dropout_transition=0:normalize=0,"
          "alimiter=limit=0.89:attack=5:release=60,loudnorm=I=-14:TP=-1.5:LRA=10[out]")

master = os.path.join(BASE, "master_thermal_horz.m4a")
cmd = inputs + ["-filter_complex", ";".join(fc), "-map", "[out]",
                "-t", "%.2f" % TOTAL, "-ar", "48000", "-c:a", "aac", "-b:a", "256k", master]
run(cmd)

o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true", "-f", "null", "-"],
                   stderr=subprocess.PIPE, text=True).stderr
tail = o[o.rfind("Summary:"):]
print(tail[:700])
json.dump({"total": TOTAL, "starts": starts}, open(os.path.join(BASE, "horz_audio.json"), "w"),
          ensure_ascii=False, indent=1)
print("MASTER", master, round(dur(master), 2), "s")
