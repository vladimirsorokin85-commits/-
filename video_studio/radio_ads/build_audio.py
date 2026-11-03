# -*- coding: utf-8 -*-
"""Звук трёх анонсов радио «В ОКОПЕ»: voice-28 + реальный трек + CC0-эффекты.

    python3 build_audio.py            # все три
    python3 build_audio.py r15        # один

Пишет master_<tag>.m4a, timeline_<tag>.json и spectrum_<tag>.json
(последний нужен рендереру: эквалайзер рисуется по настоящему спектру трека).
"""
import importlib
import json
import os
import re
import subprocess
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
FF = "/home/user/.local/bin/ffmpeg"
MUSIC_DIR = "/home/user/-/video_studio/music_downloaded"
SFX = "/home/user/-/video_studio/toolkit/sfx"

sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

VO_CHAIN = ("highpass=f=78,equalizer=f=120:t=q:w=1.0:g=2.6,"
            "equalizer=f=3200:t=q:w=1.4:g=3.6,"
            "acompressor=threshold=-19dB:ratio=4:attack=3:release=55,"
            "loudnorm=I=-14.5:TP=-1.4:LRA=8")

MUSIC = {
    "r5": {"track": "fvi-BeatOne.ogg", "offset": 47.25, "bpm": 162},
    "r15": {"track": "fvi-Favorite.ogg", "offset": 38.40, "bpm": 120},
    "r30": {"track": "fvi-Chronos.ogg", "offset": 61.35, "bpm": 120},
}

TARGET = {"r5": 5.0, "r15": 15.0, "r30": 30.0}


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    if not m:
        raise RuntimeError("не читается длительность: " + p)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def pcm(path, sr=48000):
    raw = subprocess.run([FF, "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def spectrum(path, sr=48000, bands=24, fmin=45.0, fmax=14000.0):
    """24 лог-полосы на каждый кадр 30 fps — для эквалайзера в кадре."""
    x = pcm(path, sr)
    step = sr // 30
    win = 2048
    edges = np.geomspace(fmin, fmax, bands + 1)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    idx = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(bands)]
    out = []
    hann = np.hanning(win)
    for t0 in range(0, max(1, len(x) - win), step):
        seg = x[t0:t0 + win]
        if len(seg) < win:
            break
        mag = np.abs(np.fft.rfft(seg * hann))
        vals = []
        for ii in idx:
            vals.append(float(mag[ii].mean()) if len(ii) else 0.0)
        out.append(vals)
    arr = np.array(out)
    arr = np.log1p(arr * 60.0)
    # каждая полоса нормализуется своей громкостью за трек:
    # иначе низ всегда «стена», а верх еле шевелится
    for i in range(arr.shape[1]):
        col = arr[:, i]
        lo, hi = np.percentile(col, 8), np.percentile(col, 99.5)
        arr[:, i] = (col - lo) / max(1e-6, hi - lo)
    arr = np.clip(arr, 0, 1) ** 0.78
    return arr.round(3).tolist()


def build(tag):
    mod = importlib.import_module("reel" + tag[1:])
    target = TARGET[tag]
    cfg = MUSIC[tag]
    music = os.path.join(MUSIC_DIR, cfg["track"])
    ok, info, fails = drive_check(music)
    print("музыка %s → %s" % (cfg["track"], "ДРАЙВ ✔" if ok else "ПРОВАЛ: " + "; ".join(fails)))
    if not ok:
        sys.exit("!! трек не проходит проверку на драйв")

    lead = mod.LEAD
    tail = 0.18
    src = os.path.join(BASE, "vo", mod.VO)
    clean = os.path.join(BASE, "vo", "c_" + mod.VO)
    run([FF, "-y", "-i", src, "-af",
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,"
         "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.04,areverse,"
         "silenceremove=stop_periods=-1:stop_threshold=-40dB:stop_duration=0.26:stop_silence=0.09",
         "-ar", "48000", "-ac", "2", clean])
    d_clean = dur(clean)
    tempo = d_clean / max(0.2, target - lead - tail)
    print("  голос: исходник %.2f с → после чистки %.2f с → темп ×%.3f" % (dur(src), d_clean, tempo))
    if tempo > 1.62:
        sys.exit("!! текст не влезает в %s с даже на ×%.2f" % (target, tempo))

    voice = os.path.join(BASE, "vo", "v_" + tag + ".mp3")
    run([FF, "-y", "-i", clean, "-af", "atempo=%.4f,%s" % (tempo, VO_CHAIN),
         "-ar", "48000", "-ac", "2", voice])
    d_vo = dur(voice)
    print("  финальный голос %.3f с, вход %.2f" % (d_vo, lead))

    scenes = [(n, round(lead + f * d_vo, 3)) for n, f in mod.SCENES_FRAC]
    total = target

    n_inputs = 2  # voice + music
    fx_list = [(f, scenes[i][1] if isinstance(i, int) else lead + i * d_vo, v)
               for f, i, v in mod.FX]
    inputs = [FF, "-y", "-i", voice, "-i", music]
    for f, _, _ in fx_list:
        inputs += ["-i", os.path.join(SFX, f + ".mp3")]

    fc = ["[0:a]adelay=%d|%d,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[vo]"
          % (int(lead * 1000), int(lead * 1000))]
    fc.append("[1:a]atrim=%.2f:%.2f,asetpts=PTS-STARTPTS,"
              "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[bg0]"
              % (cfg["offset"], cfg["offset"] + total + 3))
    fc.append("[bg0]highpass=f=30,bass=g=2.4:f=95:w=0.6,"
              "acompressor=threshold=-13dB:ratio=2.0:attack=14:release=190,volume=0.88,"
              "afade=t=in:st=0:d=0.22[bg1]")
    for j, (f, st, vol) in enumerate(fx_list):
        ms = int(st * 1000)
        fc.append("[%d:a]adelay=%d|%d,volume=%.2f,aformat=sample_fmts=fltp:sample_rates=48000:"
                  "channel_layouts=stereo[fx%d]" % (2 + j, ms, ms, vol, j))
    fc.append("".join("[fx%d]" % j for j in range(len(fx_list))) +
              "amix=inputs=%d:dropout_transition=0:normalize=0,volume=0.92[fx]" % max(1, len(fx_list)))
    fc.append("[vo]asplit=2[vo_sc][vo_out]")
    fc.append("[bg1][vo_sc]sidechaincompress=threshold=0.030:ratio=9:attack=5:release=170[bg_duck]")
    fc.append("[bg_duck]afade=t=out:st=%.2f:d=0.35[bgf]" % (total - 0.4))
    fc.append("[vo_out]volume=1.34[vob]")
    fc.append("[bgf][vob][fx]amix=inputs=3:dropout_transition=0:normalize=0,"
              "alimiter=limit=0.89:attack=5:release=60[out]")

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
             % (d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"],
                d.get("target_offset", "0.0")),
             "-ar", "48000", "-c:a", "aac", "-b:a", "320k", tmp])
        os.replace(tmp, master)

    o = subprocess.run([FF, "-hide_banner", "-i", master, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    for line in o[o.rfind("Summary:"):].splitlines():
        if re.search(r"^\s+(I|LRA|Peak):", line):
            print("   ", line.strip())

    # спектр считаем по чистой музыке (без голоса), чтобы эквалайзер жил на бите
    music_ref = os.path.join(BASE, "_music_%s.wav" % tag)
    run([FF, "-y", "-i", music, "-ss", "%.2f" % cfg["offset"], "-t", "%.2f" % total,
         "-ac", "1", "-ar", "48000", music_ref])
    spec = spectrum(music_ref)
    os.remove(music_ref)
    with open(os.path.join(BASE, "spectrum_%s.json" % tag), "w") as f:
        json.dump(spec, f)

    tl = {"total": total, "bpm": cfg["bpm"], "track": cfg["track"], "offset": cfg["offset"],
          "vo": {"file": voice, "start": lead, "dur": round(d_vo, 3)},
          "scenes": scenes, "tempo": round(tempo, 4)}
    with open(os.path.join(BASE, "timeline_%s.json" % tag), "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    print("%s: %.2f с → %s, полос спектра %d" % (tag, total, master, len(spec)))
    return tl


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["r5", "r15", "r30"]):
        build(t)
