# -*- coding: utf-8 -*-
"""Звук прайс-роликов: voice-28 + драйв-мастер + CC0-эффекты.

Пишет master_<tag>.m4a и timeline_<tag>.json (старты сцен = старты реплик).
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

REELS = {
    "g": {"music": "fvi-BeatOne.ogg", "offset": 6.0, "lead": 0.45, "gap": 0.38, "tail": 0.9,
          "blocks": [("g1.mp3", "hook", 1.10), ("g2.mp3", "cats", 1.08)],
          "fx": [("impact_deep", "hook", 0.55), ("whoosh_transition", "cats", 0.32),
                 ("logo_sting", "outro", 0.44)]},
    "auto": {"music": "fvi-Favorite.ogg", "offset": 22.0, "lead": 0.45, "gap": 0.36, "tail": 0.9,
             "blocks": [("au1.mp3", "hook", 1.10), ("au2.mp3", "table", 1.08)],
             "fx": [("impact_deep", "hook", 0.55), ("cut_tick", "table", 0.34),
                    ("logo_sting", "outro", 0.44)]},
    "port": {"music": "fvi-BeatOne.ogg", "offset": 96.0, "lead": 0.45, "gap": 0.36, "tail": 0.9,
             "blocks": [("po1.mp3", "hook", 1.10), ("po2.mp3", "table", 1.08)],
             "fx": [("impact_deep", "hook", 0.55), ("cut_tick", "table", 0.34),
                    ("logo_sting", "outro", 0.44)]},
    "stat": {"music": "fvi-Chronos.ogg", "offset": 9.0, "lead": 0.45, "gap": 0.36, "tail": 0.9,
             "blocks": [("st1.mp3", "hook", 1.10), ("st2.mp3", "table", 1.08)],
             "fx": [("impact_deep", "hook", 0.55), ("cut_tick", "table", 0.34),
                    ("logo_sting", "outro", 0.44)]},
    "moto": {"music": "fvi-Favorite.ogg", "offset": 112.0, "lead": 0.45, "gap": 0.36, "tail": 0.9,
             "blocks": [("mo1.mp3", "hook", 1.10)],
             "fx": [("impact_deep", "hook", 0.55), ("logo_sting", "outro", 0.44)]},
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
    print("музыка %s → %s" % (cfg["music"], "ДРАЙВ ✔" if ok else "ПРОВАЛ: " + "; ".join(fails)))
    if not ok:
        sys.exit("!! трек не проходит проверку на драйв")

    vo_dir = os.path.join(BASE, "vo")
    clips, t = [], cfg["lead"]
    for name, scene, tempo in cfg["blocks"]:
        src = os.path.join(vo_dir, name)
        trim = os.path.join(vo_dir, "t_" + name)
        run([FF, "-y", "-i", src, "-af",
             "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,"
             "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse,"
             "silenceremove=stop_periods=-1:stop_threshold=-42dB:stop_duration=0.22:stop_silence=0.07",
             "-ar", "48000", "-ac", "2", trim])
        dst = os.path.join(vo_dir, "p_" + name)
        run([FF, "-y", "-i", trim, "-af", "atempo=%.3f,%s" % (tempo, VO_CHAIN),
             "-ar", "48000", "-ac", "2", dst])
        d = dur(dst)
        clips.append({"scene": scene, "file": dst, "start": round(t, 3), "dur": round(d, 3)})
        print("  %-9s %-7s %5.2f с  старт %5.2f  конец %5.2f" % (name, scene, d, t, t + d))
        t += d + cfg["gap"]

    scenes = {c["scene"]: c["start"] for c in clips if c["scene"] != "outro"}
    last = clips[-1]
    scenes["outro"] = round(last["start"] + last["dur"] + 0.20, 3)
    total = round(scenes["outro"] + 4.6 + cfg["tail"], 2)

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
    fc.append("[bg0]highpass=f=30,bass=g=2.6:f=95:w=0.6,"
              "acompressor=threshold=-13dB:ratio=2.0:attack=14:release=190,"
              "volume=0.86,afade=t=in:st=0:d=0.26[bg1]")
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
              "alimiter=limit=0.91:attack=5:release=60[out]")

    master = os.path.join(BASE, "master_%s.m4a" % tag)
    run(inputs + ["-filter_complex", ";".join(fc), "-map", "[out]", "-t", "%.2f" % total,
                  "-ar", "48000", "-c:a", "aac", "-b:a", "320k", master])

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
             "-ar", "48000", "-c:a", "aac", "-b:a", "320k", tmp])
        os.replace(tmp, master)

    o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    tail = o[o.rfind("Summary:"):]
    for line in tail.splitlines():
        if "I:" in line or "Peak:" in line:
            print("   ", line.strip())

    tl = {"total": total, "music": cfg["music"], "offset": cfg["offset"],
          "scenes": scenes, "vo": clips}
    with open(os.path.join(BASE, "timeline_%s.json" % tag), "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    print("%s: %.2f с → %s" % (tag, total, master))
    return tl


if __name__ == "__main__":
    for tag in (sys.argv[1:] or list(REELS)):
        build(tag, REELS[tag])
