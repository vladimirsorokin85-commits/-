# -*- coding: utf-8 -*-
"""Звук рилса «Гамаши АРКОНА»: voice-28 + реальный трек + CC0-эффекты."""
import json
import os
import re
import subprocess
import sys

BASE = "/home/user/-/video_studio/arkona_gamashi"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Favorite.ogg"
MUSIC_OFFSET = 0.0
SFX = "/home/user/-/video_studio/toolkit/sfx"
TOTAL = 58.50

assert "/music_downloaded/" in MUSIC
sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

# (файл, начало сцены, конец окна)
VO = [("k1.mp3", 0.00, 7.00), ("k2.mp3", 7.00, 12.50), ("k3.mp3", 12.50, 20.00),
      ("k4.mp3", 20.00, 25.50), ("k5.mp3", 25.50, 29.50), ("k6.mp3", 29.50, 34.50),
      ("k7.mp3", 34.50, 41.00), ("k8.mp3", 41.00, 51.50), ("k9.mp3", 51.50, 58.50)]

SFX_CUES = [("impact_deep", 0.0, 0.55), ("whoosh_transition", 7.0, 0.40),
            ("cut_tick", 12.5, 0.32), ("impact_deep", 12.5, 0.34),
            ("whoosh_transition", 20.0, 0.38), ("cut_tick", 25.5, 0.30),
            ("cut_tick", 29.5, 0.30), ("impact_deep", 29.5, 0.32),
            ("whoosh_transition", 34.5, 0.40), ("cut_tick", 41.0, 0.34),
            ("riser_tension", 48.5, 0.26), ("logo_sting", 51.5, 0.46)]

VO_CHAIN = ("highpass=f=74,equalizer=f=115:t=q:w=1.0:g=3.2,"
            "equalizer=f=3400:t=q:w=1.5:g=3.6,"
            "acompressor=threshold=-19dB:ratio=4.5:attack=3:release=55,"
            "loudnorm=I=-14.5:TP=-1.4:LRA=8")


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


proc, starts = [], []
for name, t0, t1 in VO:
    src = os.path.join(BASE, "vo", name)
    trim = os.path.join(BASE, "vo", "c_" + name)
    run([FF, "-y", "-i", src, "-af",
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,"
         "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse,"
         "silenceremove=stop_periods=-1:stop_duration=0.20:stop_threshold=-42dB:stop_silence=0.05",
         "-ar", "48000", "-ac", "2", trim])
    d0 = dur(trim)
    win = (t1 - t0) - 0.20
    tempo = max(1.12, min(1.45, d0 / max(0.4, win - 0.08)))
    dst = os.path.join(BASE, "vo", "p_" + name)
    run([FF, "-y", "-i", trim, "-af", "atempo=%.4f,%s" % (tempo, VO_CHAIN),
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print("vo %-7s raw %5.2f tempo %.3f -> %5.2f окно %5.2f %s"
          % (name, d0, tempo, d1, win, "ok" if d1 <= win else "!! НЕ ВЛЕЗ"))
    if d1 > win:
        sys.exit("!! голос не влезает: " + name)
    proc.append(dst)
    starts.append(t0 + 0.10)

n_vo = len(proc)
inputs = [FF, "-y"]
for p in proc:
    inputs += ["-i", p]
inputs += ["-i", MUSIC]
for f, _, _ in SFX_CUES:
    inputs += ["-i", os.path.join(SFX, f + ".mp3")]

fc = []
for i, s in enumerate(starts):
    ms = int(s * 1000)
    fc.append("[%d:a]adelay=%d|%d,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v%d]"
              % (i, ms, ms, i))
fc.append("".join("[v%d]" % i for i in range(n_vo)) +
          "amix=inputs=%d:dropout_transition=0:normalize=0,apad=whole_dur=%.2f[vo]" % (n_vo, TOTAL))
fc.append("[%d:a]atrim=%.2f:%.2f,asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:"
          "channel_layouts=stereo[bg0]" % (n_vo, MUSIC_OFFSET, MUSIC_OFFSET + TOTAL + 2))
fc.append("[bg0]highpass=f=32,bass=g=3.0:f=95:w=0.6,"
          "acompressor=threshold=-15dB:ratio=3:attack=8:release=120,"
          "dynaudnorm=f=300:g=8:p=0.85:m=6,loudnorm=I=-11:TP=-2:LRA=9,"
          "afade=t=in:st=0:d=0.35[bg1]")
for j, (f, tt, vol) in enumerate(SFX_CUES):
    idx = n_vo + 1 + j
    ms = int(tt * 1000)
    fc.append("[%d:a]adelay=%d|%d,volume=%.2f,aformat=sample_fmts=fltp:sample_rates=48000:"
              "channel_layouts=stereo[fx%d]" % (idx, ms, ms, vol, j))
fc.append("".join("[fx%d]" % j for j in range(len(SFX_CUES))) +
          "amix=inputs=%d:dropout_transition=0:normalize=0,volume=0.9[fx]" % len(SFX_CUES))
fc.append("[vo]asplit=2[vo_sc][vo_out]")
fc.append("[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=170[bg_duck]")
fc.append("[bg_duck]afade=t=out:st=%.2f:d=1.2[bgf]" % (TOTAL - 1.3))
fc.append("[vo_out]volume=1.30[vob]")
fc.append("[bgf][vob][fx]amix=inputs=3:dropout_transition=0:normalize=0,"
          "alimiter=limit=0.89:attack=4:release=50,loudnorm=I=-14:TP=-1.5:LRA=9[out]")

master = os.path.join(BASE, "master_arkona_reel.m4a")
cmd = inputs + ["-filter_complex", ";".join(fc), "-map", "[out]",
                "-t", "%.2f" % TOTAL, "-ar", "48000", "-c:a", "aac", "-b:a", "256k", master]
run(cmd)

o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true", "-f", "null", "-"],
                   stderr=subprocess.PIPE, text=True).stderr
print(o[o.rfind("Summary:"):][:620])
json.dump({"total": TOTAL, "starts": starts}, open(os.path.join(BASE, "reel_timeline.json"), "w"),
          ensure_ascii=False, indent=1)
print("MASTER", master, round(dur(master), 2), "с")
