# -*- coding: utf-8 -*-
"""Пересборка аудио ПАУК 30Б с фиксированной сеткой (без сдвига сцен видео).

Блоки ВО подгоняются по длительности под уже смонтированную картинку:
начальные точки и общая длительность не меняются, темп подбирается
индивидуально (1.1–1.36), чтобы речь оставалась быстрой, но разборчивой.
"""
import os, re, json, subprocess, sys

BASE = "/home/user/-/video_studio/pauk_30b"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC_H = "/home/user/-/video_studio/music_downloaded/fvi-BeatOne.ogg"
MUSIC_R = "/home/user/-/video_studio/music_downloaded/fvi-Arpent.ogg"

def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def build(tag, raws, starts, total, music, vol, chain_extra, lufs, tp, out, tail=0.30):
    windows = [starts[i + 1] - starts[i] if i + 1 < len(starts) else total - starts[i]
               for i in range(len(starts))]
    proc = []
    for i, (src, win) in enumerate(zip(raws, windows), 1):
        d0 = dur(src)
        target = win - tail
        tempo = max(1.12, min(1.36, d0 / target))
        dst = os.path.join(BASE, f"{tag}_proc_{i}.mp3")
        af = (f"atempo={tempo:.4f},highpass=f={chain_extra['hp']},"
              f"equalizer=f=120:t=q:w=1.0:g={chain_extra['low']},"
              f"equalizer=f=3200:t=q:w=1.6:g={chain_extra['pres']},"
              "acompressor=threshold=-20dB:ratio=4:attack=4:release=60,"
              f"loudnorm=I={chain_extra['vo_i']}:TP=-1.5:LRA=9")
        run([FF, "-y", "-i", src, "-af", af, "-ar", "48000", "-ac", "2",
             "-b:a", "192k", dst])
        d1 = dur(dst)
        print(f"{tag} {i}: raw {d0:.2f}s -> tempo {tempo:.3f} -> {d1:.2f}s "
              f"(окно {win:.2f}s, запас {win - d1:.2f}s)")
        if d1 > win - 0.05:
            print("!! не влезает в окно", file=sys.stderr)
            sys.exit(1)
        proc.append(dst)

    n = len(proc)
    delays = "".join(
        f"[{i}:a]adelay={int(s*1000)}|{int(s*1000)},"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
        f"[v{i}];" for i, s in enumerate(starts))
    labels = "".join(f"[v{i}]" for i in range(n))
    fc = (delays + labels +
          f"amix=inputs={n}:dropout_transition=0:normalize=0,apad=whole_dur={total}[vo];"
          f"[{n}:a]atrim=0:{total + 2},asetpts=PTS-STARTPTS,"
          "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0];"
          f"[bg0]volume={vol},afade=t=in:st=0:d={chain_extra['fin']}[bg1];"
          "[vo]asplit=2[vo_sc][vo_out];"
          f"[bg1][vo_sc]sidechaincompress=threshold=0.06:ratio={chain_extra['ratio']}"
          f":attack={chain_extra['atk']}:release={chain_extra['rel']}[bg_duck];"
          f"[bg_duck]afade=t=out:st={max(0, total-chain_extra['fout']-0.4):.2f}"
          f":d={chain_extra['fout']+0.4:.2f}[bgf];"
          "[vo_out]volume=1.35[vob];"
          "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
          f"alimiter=limit=0.89:attack=4:release=60,loudnorm=I={lufs}:TP={tp}:LRA=9[out]")

    cmd = [FF, "-y"]
    for p in proc:
        cmd += ["-i", p]
    cmd += ["-i", music, "-filter_complex", fc, "-map", "[out]",
            "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", out]
    run(cmd)

    o = subprocess.check_output([FF, "-hide_banner", "-i", out, "-af", "volumedetect",
                                 "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
    for line in o.splitlines():
        if "mean_volume" in line or "max_volume" in line:
            print("   ", line.strip())
    print(f"MASTER {out}: {dur(out):.2f}s")


# ── горизонталь ──────────────────────────────────────────────
build("vo",
      [os.path.join(BASE, f"raw_vo_{i}.mp3") for i in (1, 2, 3, 4)],
      [2.60, 27.52, 50.06, 75.84], 103.16, MUSIC_H, 0.30,
      dict(hp=70, low=2.5, pres=3.0, vo_i=-15, fin=1.2, ratio=6, atk=8, rel=250, fout=3.2),
      -14, -1.5, os.path.join(BASE, "master_horizontal_16x9.mp3"))

# ── вертикаль ────────────────────────────────────────────────
build("reel",
      [os.path.join(BASE, f"reel_raw_{i}.mp3") for i in (1, 2, 3)],
      [1.80, 16.94, 32.37], 50.83, MUSIC_R, 0.34,
      dict(hp=75, low=3.0, pres=3.5, vo_i=-14, fin=0.8, ratio=7, atk=6, rel=220, fout=2.6),
      -13, -1.0, os.path.join(BASE, "master_reel_9x16.mp3"))

json.dump({"total": 103.16, "scenes": [
    {"idx": 1, "start": 2.60, "end": 27.52},
    {"idx": 2, "start": 27.52, "end": 50.06},
    {"idx": 3, "start": 50.06, "end": 75.84},
    {"idx": 4, "start": 75.84, "end": 103.16}]},
    open(os.path.join(BASE, "timeline.json"), "w"), ensure_ascii=False, indent=2)
json.dump({"total": 50.83, "scenes": [
    {"i": 1, "s": 1.80, "e": 16.94},
    {"i": 2, "s": 16.94, "e": 32.37},
    {"i": 3, "s": 32.37, "e": 50.83}]},
    open(os.path.join(BASE, "timeline_reel.json"), "w"), indent=2)
print("timeline.json / timeline_reel.json обновлены (сетка не изменилась)")
