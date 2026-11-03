# -*- coding: utf-8 -*-
"""Сборка «СВОДКИ»: озвучка + подложка → мастер, затем кадры → mp4.

    python3 build.py scripts/demo_format.json --audio     # только звук и тайминги
    python3 build.py scripts/demo_format.json --still 3 40
    python3 build.py scripts/demo_format.json --full

Выход по ТЗ: 1280×720, 25 fps, H.264 yuv420p, AAC 44 100 Гц, стерео, 128 кбит/с.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

import gfx as G
import scenes as S

BASE = os.path.dirname(os.path.abspath(__file__))
FF = None


def ffmpeg():
    global FF
    if FF is None:
        import imageio_ffmpeg
        FF = imageio_ffmpeg.get_ffmpeg_exe()
    return FF


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def dur(p):
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        raise RuntimeError("нет длительности: " + p)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


VO_CHAIN = ("highpass=f=80,equalizer=f=120:t=q:w=1.0:g=2.0,"
            "equalizer=f=3000:t=q:w=1.5:g=3.0,"
            "acompressor=threshold=-20dB:ratio=3.5:attack=4:release=70,"
            "loudnorm=I=-16:TP=-2:LRA=7")


def vo_chain(spec):
    tmp = float(spec.get("tempo", 1.0) or 1.0)
    tempo = "atempo=%.3f," % tmp if abs(tmp - 1.0) > 0.005 else ""
    return tempo + VO_CHAIN


def build_audio(spec):
    slug = spec["slug"]
    vo_dir = os.path.join(BASE, "vo", spec.get("vo_dir", slug))
    tmp = os.path.join(BASE, "out", slug)
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(vo_dir, exist_ok=True)

    segs, t = [], float(spec.get("lead", 0.5))
    est_all = "--estimate" in sys.argv
    for s in spec["segments"]:
        src = os.path.join(vo_dir, s["vo"])
        if not est_all and not os.path.exists(src):
            raise RuntimeError("нет реплики: %s (сначала озвучить этот сценарий)" % src)
        if est_all or not os.path.exists(src):
            src_txt = s.get("say") or s.get("sub", "") or s.get("head", "")
            words = len(re.findall(r"[\wА-Яа-яЁё]+", src_txt))
            d_est = max(1.6, words / 2.35 + 0.45)
            src = os.path.join(tmp, "e_" + s["vo"].replace(".mp3", ".wav"))
            run([ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", "%.2f" % d_est, "-c:a", "pcm_s16le", src])
            print("  [оценка] %s ≈ %.2f с (%d слов)" % (s["id"], d_est, words))
        stem = s["vo"].rsplit(".", 1)[0]
        ready = os.path.join(tmp, "v_" + stem + ".wav")
        if est_all:
            run([ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", "%.2f" % dur(src), "-c:a", "pcm_s16le", ready])
            d = dur(ready)
            segs.append({"id": s["id"], "scene": s["scene"], "file": ready,
                         "start": round(t, 3), "dur": round(d, 3), "spec": s})
            t += d + float(s.get("gap", 1.0))
            continue
        clean = os.path.join(tmp, "c_" + stem + ".wav")
        run([ffmpeg(), "-y", "-i", src, "-af",
             # только обрезка краёв: внутренние паузы не трогаем, они держат ритм
             "silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.04,"
             "areverse,silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.12,areverse",
             "-ar", "44100", "-ac", "2", clean])
        run([ffmpeg(), "-y", "-i", clean, "-af", vo_chain(spec), "-ar", "44100", "-ac", "2", ready])
        d = dur(ready)
        segs.append({"id": s["id"], "scene": s["scene"], "file": ready,
                     "start": round(t, 3), "dur": round(d, 3), "spec": s})
        t += d + float(s.get("gap", 1.0))
    total = round(t + float(spec.get("tail", 1.2)), 2)

    music = os.path.join(G.ROOT, "video_studio", "music_downloaded", spec["music"]["track"])
    off = float(spec["music"].get("offset", 0.0))
    lvl = float(spec["music"].get("level", 0.20))

    inputs = [ffmpeg(), "-y"]
    for sg in segs:
        inputs += ["-i", sg["file"]]
    inputs += ["-i", music]

    fc = []
    for i, sg in enumerate(segs):
        ms = int(sg["start"] * 1000)
        fc.append("[%d:a]adelay=%d|%d,aformat=sample_fmts=fltp:sample_rates=44100:"
                  "channel_layouts=stereo[v%d]" % (i, ms, ms, i))
    fc.append("".join("[v%d]" % i for i in range(len(segs))) +
              "amix=inputs=%d:dropout_transition=0:normalize=0,apad=whole_dur=%.2f[vo]"
              % (len(segs), total))
    # подложка: два режима — тихая (ТЗ) и драйв (MUSIC_POLICY канала)
    mode = (spec["music"].get("mode") or "quiet").lower()
    fc.append("[%d:a]atrim=%.2f:%.2f,asetpts=PTS-STARTPTS,"
              "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bg0]"
              % (len(segs), off, off + total + 3))
    if mode == "drive":
        fc.append("[bg0]highpass=f=30,acompressor=threshold=-18dB:ratio=3:attack=8:release=120,"
                  "loudnorm=I=-12:TP=-3:LRA=6,"
                  "afade=t=in:st=0:d=1.2,afade=t=out:st=%.2f:d=2.0[bg1]" % (total - 2.4))
        duck = "threshold=0.05:ratio=9:attack=5:release=180"
    else:
        fc.append("[bg0]highpass=f=45,lowpass=f=4200,volume=%.3f,"
                  "acompressor=threshold=-24dB:ratio=2.0:attack=20:release=250,"
                  "afade=t=in:st=0:d=1.2,afade=t=out:st=%.2f:d=2.0[bg1]" % (lvl, total - 2.4))
        duck = "threshold=0.028:ratio=12:attack=8:release=220"
    fc.append("[vo]asplit=2[vo_sc][vo_out]")
    fc.append("[bg1][vo_sc]sidechaincompress=%s[bgd]" % duck)
    fc.append("[bgd][vo_out]amix=inputs=2:dropout_transition=0:normalize=0,"
              "alimiter=limit=0.88:attack=6:release=70[out]")

    master = os.path.join(BASE, "out", "%s_master.m4a" % slug)
    run(inputs + ["-filter_complex", ";".join(fc), "-map", "[out]", "-t", "%.2f" % total,
                  "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k", master])

    # второй проход по громкости
    tgt = -23.0 if est_all else -14.5
    rep = subprocess.run([ffmpeg(), "-hide_banner", "-i", master, "-af",
                          "loudnorm=I=%.1f:TP=-1.5:LRA=8:print_format=json" % tgt, "-f", "null", "-"],
                         stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", rep, re.S)
    if m:
        d = json.loads(m.group(0))
        n = master.replace(".m4a", "_n.m4a")
        run([ffmpeg(), "-y", "-i", master, "-af",
             "loudnorm=I=%.1f:TP=-1.5:LRA=8:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
             "measured_thresh=%s:offset=%s:linear=true"
             % (tgt, d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"],
                d.get("target_offset", "0.0")),
             "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k", n])
        os.replace(n, master)

    o = subprocess.run([ffmpeg(), "-hide_banner", "-i", master, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr
    for line in o[o.rfind("Summary:"):].splitlines():
        if re.search(r"^\s+(I|LRA|Peak):", line):
            print("   ", line.strip())

    tl = {"slug": slug, "total": total, "fps": G.FPS, "date": spec["date"],
          "shift": spec["shift"], "demo": bool(spec.get("demo")), "segments": [
              {"id": s["id"], "scene": s["scene"], "start": s["start"], "dur": s["dur"]}
              for s in segs]}
    with open(os.path.join(BASE, "out", "%s_timeline.json" % slug), "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, "out", "%s_segments.json" % slug), "w", encoding="utf-8") as f:
        json.dump([{k: s[k] for k in ("id", "scene", "start", "dur")} | {"spec": s["spec"]}
                   for s in segs], f, ensure_ascii=False, indent=1)
    print("мастер: %.2f с → %s" % (total, master))
    for sg in segs:
        print("  %-5s %-7s %6.2f → %6.2f  (%5.2f с)"
              % (sg["id"], sg["scene"], sg["start"], sg["start"] + sg["dur"], sg["dur"]))
    return tl, master


def frame(seglist, tl, t):
    seg = seglist[0]
    for sg in seglist:
        if t >= sg["start"] - 1e-6:
            seg = sg
    l = t - seg["start"]
    cv = Image.new("RGBA", (G.W, G.H), G.ac(G.BG0, 255))
    G.stage(cv, t)
    G.sweep(cv, t)
    ui = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    cut = float(seg["spec"].get("cut", 0) or 0)
    if seg["spec"].get("scene2") and seg["dur"] and l >= seg["dur"] * cut:
        l2 = l - seg["dur"] * cut
        spec2 = dict(seg["spec"])
        spec2["sub"] = seg["spec"].get("sub2", seg["spec"].get("sub", ""))
        S.FN[seg["spec"]["scene2"]](cv, d, t, l2, spec2)
    else:
        S.FN[seg["scene"]](cv, d, t, l, seg["spec"])
    out = Image.alpha_composite(cv, ui)

    hud = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hud)
    G.header(hud, hd, t, tl["total"], tl["date"], tl["shift"])
    if tl.get("demo"):
        cw = int(G.F(G.MONO, 15).getlength("ДЕМО ФОРМАТА")) + 32
        G.chip(hd, 396, 15, "ДЕМО ФОРМАТА", G.GOLD, 15, 34, 235)
    G.footer(hud, hd, t, tl["total"])
    G.tick_marks(hd)
    out = Image.alpha_composite(out, hud)

    G.scanlines(out)
    G.grain(out, t)
    return out.convert("RGB")


def write_txt(spec, path):
    """Текст выпуска: первая строка «Источник: …», дальше — что читает ведущий."""
    head = spec.get("title_line") or ("СВОДКА · %s · %s" % (spec["date"], spec["shift"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("Источник: %s\n\n" % spec.get("source", "—"))
        f.write(head + "\n\n")
        for sg in spec["segments"]:
            f.write(sg.get("say", "") + "\n\n")


def main():
    spec_path = sys.argv[1]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    tl, master = build_audio(spec)
    with open(os.path.join(BASE, "out", "%s_segments.json" % spec["slug"]), encoding="utf-8") as f:
        seglist = json.load(f)

    if "--audio" in sys.argv:
        return

    if "--still" in sys.argv:
        idx = sys.argv.index("--still")
        times = [float(a) for a in sys.argv[idx + 1:] if re.match(r"^[\d.]+$", a)]
        os.makedirs("/tmp/sv", exist_ok=True)
        for t in times:
            frame(seglist, tl, t).save("/tmp/sv/%s_%05.2f.jpg" % (spec["slug"], t), quality=92)
            print("кадр", t)
        return

    out = os.path.join(BASE, "out", "%s.mp4" % spec["slug"])
    n = int(round(tl["total"] * G.FPS))
    cmd = [ffmpeg(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (G.W, G.H), "-r", str(G.FPS), "-i", "-", "-i", master,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-x264-params", "keyint=50:min-keyint=25:scenecut=0",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-t", "%.2f" % tl["total"], out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    import time
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(seglist, tl, i / float(G.FPS)).tobytes())
        if i % 250 == 0:
            el = time.time() - t0
            print("%d/%d %.2f кадр/с" % (i, n, i / max(el, .01)), flush=True)
    p.stdin.close()
    print("rc", p.wait(), "секунд", round(time.time() - t0, 1))
    print("файл", out, os.path.getsize(out) if os.path.exists(out) else "НЕТ")

    mp3 = out.replace(".mp4", ".mp3")
    run([ffmpeg(), "-y", "-i", master, "-c:a", "libmp3lame", "-b:a", "192k",
         "-ar", "44100", "-ac", "2", mp3])
    txt = out.replace(".mp4", ".txt")
    write_txt(spec, txt)
    print("mp3", mp3, "txt", txt)


if __name__ == "__main__":
    main()
