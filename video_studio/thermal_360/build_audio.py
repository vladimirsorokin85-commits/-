# -*- coding: utf-8 -*-
"""Звук рилса «Тепловизор 360°»: голос voice-28 + реальная музыка + CC0-эффекты.

Проверки:
  • музыка только из video_studio/music_downloaded/ и обязана проходить music_check (ДРАЙВ);
  • мастер: −14 LUFS интегрировано, TP ≤ −1 dBTP (иначе брак).
"""
import json
import os
import re
import subprocess
import sys

BASE = "/home/user/-/video_studio/thermal_360"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Chronos.ogg"
MUSIC_OFFSET = 24.0            # кратно 0.5 с → склейки ложатся на бит 120 BPM
SFX = "/home/user/-/video_studio/toolkit/sfx"

assert "/music_downloaded/" in MUSIC, "разрешена ТОЛЬКО реальная скачанная музыка"
sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

TOTAL = 46.00
OUTRO = 0.9

# (файл голоса, начало сцены, конец окна)
VO = [
    ("t1.mp3", 0.00, 4.00),
    ("t2.mp3", 4.00, 11.00),
    ("t3.mp3", 11.00, 15.00),
    ("t4.mp3", 15.00, 19.50),
    ("t5.mp3", 19.50, 24.00),
    ("t6.mp3", 24.00, 27.50),
    ("t7.mp3", 27.50, 31.50),
    ("t8.mp3", 31.50, 36.00),
    ("t9.mp3", 36.00, 46.00),
]

# эффекты: (файл, время, громкость)
SFX_CUES = [
    ("impact_deep", 0.00, 0.55),
    ("whoosh_transition", 4.00, 0.42),
    ("impact_deep", 4.00, 0.34),
    ("pop_bubble", 5.90, 0.22),
    ("cut_tick", 7.50, 0.30),
    ("whoosh_transition", 11.00, 0.46),
    ("impact_deep", 11.00, 0.30),
    ("cut_tick", 13.00, 0.26),
    ("impact_deep", 15.00, 0.40),
    ("camera_shutter", 19.50, 0.34),
    ("impact_bright", 19.50, 0.26),
    ("cut_tick", 24.00, 0.30),
    ("impact_deep", 24.00, 0.34),
    ("cut_tick", 27.50, 0.28),
    ("impact_deep", 27.50, 0.34),
    ("whoosh_transition", 31.50, 0.42),
    ("impact_deep", 36.00, 0.55),
    ("riser_tension", 38.00, 0.30),
    ("logo_sting", 40.50, 0.46),
]

VO_CHAIN = ("highpass=f=74,"
            "equalizer=f=115:t=q:w=1.0:g=3.2,"
            "equalizer=f=3400:t=q:w=1.5:g=3.6,"
            "acompressor=threshold=-19dB:ratio=4.5:attack=3:release=55,"
            "loudnorm=I=-14.5:TP=-1.4:LRA=8")


def dur(path):
    s = subprocess.run([FF, "-hide_banner", "-i", path], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


# 1. голос: срезать паузы по краям, ускорить под окно, прогнать через цепочку
proc, starts = [], []
for name, t0, t1 in VO:
    src = os.path.join(BASE, "vo", name)
    trim = os.path.join(BASE, "vo", "c_" + name)
    run([FF, "-y", "-i", src, "-af",
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,"
         "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse",
         "-ar", "48000", "-ac", "2", trim])
    d0 = dur(trim)
    win = (t1 - t0) - 0.16
    tempo = max(1.12, min(1.46, d0 / max(0.4, win - 0.08)))
    dst = os.path.join(BASE, "vo", "p_" + name)
    run([FF, "-y", "-i", trim, "-af", "atempo=%.4f,%s" % (tempo, VO_CHAIN),
         "-ar", "48000", "-ac", "2", "-b:a", "192k", dst])
    d1 = dur(dst)
    print("vo %-7s raw %5.2f  tempo %.3f -> %5.2f  окно %.2f  %s"
          % (name, d0, tempo, d1, t1 - t0, "ok" if d1 <= win else "!! НЕ ВЛЕЗ"))
    if d1 > win:
        sys.exit("!! голос не влезает в окно: " + name)
    proc.append(dst)
    starts.append(t0 + 0.10)

# 2. музыка: только реальный трек, кроп с бита, драйв-обработка
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
fc.append("[bg0]highpass=f=30,bass=g=3.2:f=95:w=0.6,"
          "acompressor=threshold=-14dB:ratio=3.2:attack=8:release=110,"
          "dynaudnorm=f=260:g=8:p=0.9:m=5,loudnorm=I=-11.5:TP=-2:LRA=8,"
          "afade=t=in:st=0:d=0.30[bg1]")
for j, (f, tt, vol) in enumerate(SFX_CUES):
    idx = n_vo + 1 + j
    ms = int(tt * 1000)
    fc.append("[%d:a]adelay=%d|%d,volume=%.2f,aformat=sample_fmts=fltp:sample_rates=48000:"
              "channel_layouts=stereo[fx%d]" % (idx, ms, ms, vol, j))
fc.append("".join("[fx%d]" % j for j in range(len(SFX_CUES))) +
          "amix=inputs=%d:dropout_transition=0:normalize=0,volume=0.9[fx]" % len(SFX_CUES))
fc.append("[vo]asplit=2[vo_sc][vo_out]")
fc.append("[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=170[bg_duck]")
fc.append("[bg_duck]afade=t=out:st=%.2f:d=%.2f[bgf]" % (TOTAL - OUTRO, OUTRO))
fc.append("[vo_out]volume=1.28[vob]")
fc.append("[bgf][vob][fx]amix=inputs=3:dropout_transition=0:normalize=0,"
          "alimiter=limit=0.89:attack=4:release=50,loudnorm=I=-14:TP=-1.5:LRA=9[out]")

master = os.path.join(BASE, "master_thermal_reel.m4a")
cmd = inputs + ["-filter_complex", ";".join(fc), "-map", "[out]",
                "-t", "%.2f" % TOTAL, "-ar", "48000", "-c:a", "aac", "-b:a", "256k", master]
run(cmd)

# 3. контроль громкости
o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true",
                    "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr
tail = o[o.rfind("Summary:"):]
print(tail[:900])
json.dump({"total": TOTAL, "starts": starts, "music": MUSIC, "offset": MUSIC_OFFSET,
           "vo": [v[0] for v in VO]},
          open(os.path.join(BASE, "reel_timeline.json"), "w"), ensure_ascii=False, indent=1)
print("MASTER", master, round(dur(master), 2), "s")
