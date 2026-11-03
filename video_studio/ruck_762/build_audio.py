# -*- coding: utf-8 -*-
"""Звук двух роликов «Рюкзак 7.62»: voice-28 + реальный мастер + CC0-эффекты.

Собирает `master_r1.m4a` и `master_r2.m4a` и кладёт рядом `timeline_r1.json` /
`timeline_r2.json` — по ним рендерер ставит кадры ровно под речь.
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
FF = "/home/user/.local/bin/ffmpeg"
MUSIC_DIR = "/home/user/-/video_studio/music_downloaded"
SFX = "/home/user/-/video_studio/toolkit/sfx"

sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

VO_CHAIN = ("highpass=f=76,equalizer=f=118:t=q:w=1.0:g=3.0,"
            "equalizer=f=3300:t=q:w=1.5:g=3.8,"
            "acompressor=threshold=-19dB:ratio=4.5:attack=3:release=55,"
            "loudnorm=I=-14.5:TP=-1.4:LRA=8")

# ── сценарии: (файл, сцена, запас до следующей, эффекты на входе в сцену)
REELS = {
    "r1": {
        "music": "fvi-Chronos.ogg", "offset": 61.35, "pad_end": 2.75, "lead": 0.55,
        "blocks": [
            ("r1_a.mp3", "hook", 0.55),
            ("r1_b.mp3", "why", 0.45),
            ("r1_c.mp3", "narrow", 0.45),
            ("r1_d.mp3", "access", 0.45),
            ("r1_e.mp3", "molle", 0.45),
            ("r1_f.mp3", "colors", 0.0),
        ],
        "fx": [("impact_deep", "hook", 0.55), ("whoosh_transition", "why", 0.34),
               ("cut_tick", "narrow", 0.34), ("impact_deep", "narrow", 0.30),
               ("whoosh_transition", "access", 0.32), ("cut_tick", "molle", 0.34),
               ("riser_tension", "colors", 0.24), ("logo_sting", "outro", 0.44)],
    },
    "r2": {
        "music": "fvi-BeatOne.ogg", "offset": 47.25, "pad_end": 2.85, "lead": 0.50,
        "blocks": [
            ("r2_a.mp3", "lid", 0.45),
            ("r2_b.mp3", "zip", 0.45),
            ("r2_c.mp3", "bottom", 0.45),
            ("r2_d.mp3", "harness", 0.0),
        ],
        "fx": [("impact_deep", "lid", 0.55), ("whoosh_transition", "zip", 0.34),
               ("cut_tick", "zip", 0.30), ("impact_deep", "bottom", 0.30),
               ("whoosh_transition", "harness", 0.34), ("riser_tension", "harness", 0.22),
               ("logo_sting", "outro", 0.44)],
    },
}


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def build(tag, cfg):
    music = os.path.join(MUSIC_DIR, cfg["music"])
    ok, info, fails = drive_check(music)
    print("музыка %s → %s %s" % (cfg["music"], "ДРАЙВ ✔" if ok else "ПРОВАЛ", info))
    if not ok:
        sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(fails))

    vo_dir = os.path.join(BASE, "vo")
    clips, t = [], cfg["lead"]
    for name, scene, gap in cfg["blocks"]:
        src = os.path.join(vo_dir, name)
        trim = os.path.join(vo_dir, "t_" + name)
        run([FF, "-y", "-i", src, "-af",
             "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,"
             "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse,"
             "silenceremove=stop_periods=-1:stop_threshold=-42dB:stop_duration=0.22:stop_silence=0.07",
             "-ar", "48000", "-ac", "2", trim])
        dst = os.path.join(vo_dir, "p_" + name)
        run([FF, "-y", "-i", trim, "-af", VO_CHAIN, "-ar", "48000", "-ac", "2", dst])
        d = dur(dst)
        clips.append({"scene": scene, "file": dst, "start": round(t, 3), "dur": round(d, 3)})
        print("  %-10s %-9s %5.2f с  старт %5.2f  конец %5.2f" % (name, scene, d, t, t + d))
        t += d + gap

    total = round(t - cfg["blocks"][-1][2] + cfg["pad_end"], 2)
    scenes = {c["scene"]: c["start"] for c in clips}
    scenes["outro"] = round(clips[-1]["start"] + clips[-1]["dur"], 3)

    n = len(clips)
    inputs = [FF, "-y"]
    for c in clips:
        inputs += ["-i", c["file"]]
    inputs += ["-i", music]
    for f, _, _ in cfg["fx"]:
        inputs += ["-i", os.path.join(SFX, f + ".mp3")]

    fc = []
    for i, c in enumerate(clips):
        ms = int(c["start"] * 1000)
        fc.append("[%d:a]adelay=%d|%d,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v%d]"
                  % (i, ms, ms, i))
    fc.append("".join("[v%d]" % i for i in range(n)) +
              "amix=inputs=%d:dropout_transition=0:normalize=0,apad=whole_dur=%.2f[vo]" % (n, total))
    fc.append("[%d:a]atrim=%.2f:%.2f,asetpts=PTS-STARTPTS,"
              "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0]"
              % (n, cfg["offset"], cfg["offset"] + total + 2))
    fc.append("[bg0]highpass=f=32,bass=g=3.0:f=95:w=0.6,"
              "acompressor=threshold=-15dB:ratio=3:attack=8:release=120,"
              "dynaudnorm=f=300:g=8:p=0.85:m=6,loudnorm=I=-11:TP=-2:LRA=9,"
              "afade=t=in:st=0:d=0.30[bg1]")
    for j, (f, scene, vol) in enumerate(cfg["fx"]):
        idx = n + 1 + j
        ms = int(scenes[scene] * 1000)
        fc.append("[%d:a]adelay=%d|%d,volume=%.2f,aformat=sample_fmts=fltp:sample_rates=48000:"
                  "channel_layouts=stereo[fx%d]" % (idx, ms, ms, vol, j))
    fc.append("".join("[fx%d]" % j for j in range(len(cfg["fx"]))) +
              "amix=inputs=%d:dropout_transition=0:normalize=0,volume=0.9[fx]" % len(cfg["fx"]))
    fc.append("[vo]asplit=2[vo_sc][vo_out]")
    fc.append("[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=170[bg_duck]")
    fc.append("[bg_duck]afade=t=out:st=%.2f:d=1.2[bgf]" % (total - 1.3))
    fc.append("[vo_out]volume=1.34[vob]")
    fc.append("[bgf][vob][fx]amix=inputs=3:dropout_transition=0:normalize=0,"
              "alimiter=limit=0.89:attack=4:release=50,loudnorm=I=-14:TP=-1.5:LRA=9[out]")

    master = os.path.join(BASE, "master_%s.m4a" % tag)
    run(inputs + ["-filter_complex", ";".join(fc), "-map", "[out]", "-t", "%.2f" % total,
                  "-ar", "48000", "-c:a", "aac", "-b:a", "256k", master])

    # второй точный проход по громкости
    rep = subprocess.run([FF, "-hide_banner", "-i", master, "-af",
                          "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
                         stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", rep, re.S)
    if m:
        d = json.loads(m.group(0))
        tmp = master.replace(".m4a", "_n.m4a")
        run([FF, "-y", "-i", master, "-af",
             "loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
             "measured_thresh=%s:offset=%s:linear=true"
             % (d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"], d.get("target_offset", "0.0")),
             "-ar", "48000", "-c:a", "aac", "-b:a", "256k", tmp])
        os.replace(tmp, master)

    o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    print(o[o.rfind("Summary:"):][:340])

    tl = {"total": total, "music": cfg["music"], "offset": cfg["offset"],
          "scenes": scenes, "vo": clips}
    with open(os.path.join(BASE, "timeline_%s.json" % tag), "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    print("%s: %.2f с → %s" % (tag, total, master))
    return tl


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["r1", "r2"]):
        build(tag, REELS[tag])
