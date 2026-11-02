# -*- coding: utf-8 -*-
"""Джинглы радио «В окопе» — 5 вариантов по 3,5–4,4 с.

Только реальные источники:
  • голос — voice-28 (голос канала);
  • музыкальные удары — реальные треки из video_studio/music_downloaded/;
  • эффекты — CC0 из video_studio/toolkit/sfx.

Каждый вариант: элементы → отдельные wav → микс → мастер (−13 LUFS, TP −1.2).
"""
import json
import os
import subprocess

FF = "/home/user/.local/bin/ffmpeg"
BASE = "/home/user/-/radio_vokope/jingle"
VO = os.path.join(BASE, "vo")
SFX = "/home/user/-/video_studio/toolkit/sfx"
MUS = "/home/user/-/video_studio/music_downloaded"
TMP = "/tmp/jing_tmp"

os.makedirs(TMP, exist_ok=True)

# ── голос: чистый, «радийный», но без потери разборчивости
VO_CHAIN = ("highpass=f=88,"
            "equalizer=f=115:t=q:w=1.0:g=2.5,"
            "equalizer=f=300:t=q:w=1.2:g=-2.0,"
            "equalizer=f=3200:t=q:w=1.4:g=4.0,"
            "acompressor=threshold=-20dB:ratio=4:attack=3:release=60,"
            "volume=1.15")

# тот же голос, но «в рации»: узкая полоса + плотная компрессия
RADIO_CHAIN = ("highpass=f=330,lowpass=f=3300,"
               "equalizer=f=1100:t=q:w=1.6:g=5.0,"
               "equalizer=f=2400:t=q:w=1.2:g=3.0,"
               "acompressor=threshold=-26dB:ratio=9:attack=2:release=40,"
               "volume=1.5,"
               "alimiter=limit=0.85")

MASTER = ("acompressor=threshold=-18dB:ratio=3:attack=5:release=120,"
          "alimiter=limit=0.92:attack=3:release=60,"
          "loudnorm=I=-13:TP=-1.2:LRA=7")


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def dur(path):
    """Длительность через ffmpeg (ffprobe в сборке отсутствует)."""
    s = subprocess.run([FF, "-hide_banner", "-i", path], stderr=subprocess.PIPE, text=True).stderr
    for line in s.splitlines():
        if "Duration:" in line:
            h, m, sec = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
    return 0.0


def tighten(src, tag):
    """Голос ведущего: убираем вдохи и паузы — военная подача без провисаний."""
    out = os.path.join(TMP, "tight_" + tag)
    run([FF, "-y", "-i", src, "-af",
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,"
         "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse,"
         "silenceremove=stop_periods=-1:stop_threshold=-42dB:stop_duration=0.24:stop_silence=0.09",
         "-ar", "48000", "-ac", "1", out])
    return out


def element(name, src, start=None, length=None, chain=None, gain=1.0):
    """Готовит один элемент: обрезка + обработка → wav 48k стерео."""
    out = os.path.join(TMP, name + ".wav")
    cmd = [FF, "-y"]
    if start is not None:
        cmd += ["-ss", "%.3f" % start]
    if length is not None:
        cmd += ["-t", "%.3f" % length]
    cmd += ["-i", src]
    fl = []
    if chain:
        fl.append(chain)
    if gain != 1.0:
        fl.append("volume=%.3f" % gain)
    fl.append("aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo")
    cmd += ["-af", ",".join(fl), "-ar", "48000", "-ac", "2", out]
    run(cmd)
    return out


def match_loudness(wav, target=-13.0):
    """Точная подгонка к target LUFS: измерить -> применить linear-проход."""
    import json, re
    r = subprocess.run([FF, "-hide_banner", "-i", wav, "-af",
                        "loudnorm=I=%.1f:TP=-1.2:LRA=7:print_format=json" % target,
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        return wav
    d = json.loads(m.group(0))
    tmp = wav[:-4] + "_norm.wav"
    run([FF, "-y", "-i", wav, "-af",
         "loudnorm=I=%.1f:TP=-1.2:LRA=7:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
         "measured_thresh=%s:offset=%s:linear=true"
         % (target, d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"],
            d.get("target_offset", "0.0")),
         "-ar", "48000", "-c:a", "pcm_s16le", tmp])
    os.replace(tmp, wav)
    return wav


def mix(name, total, items, fade_out=0.30, duk=0.55):
    """items: (wav, задержка, громкость, роль). Роль: "bed" или "vo".

    Голос — всегда сверху: подложка уходит вниз по sidechain, поэтому слова
    «В окопе» слышны даже на мощном ударе.
    """
    cmd = [FF, "-y"]
    for w, _, _, _ in items:
        cmd += ["-i", w]
    fc, beds, vos = [], [], []
    for i, (_, delay, gain, role) in enumerate(items):
        ms = int(round(delay * 1000))
        fc.append("[%d:a]adelay=%d|%d,volume=%.3f[e%d]" % (i, ms, ms, gain, i))
        (vos if role == "vo" else beds).append(i)
    fc.append("".join("[e%d]" % i for i in beds) +
              "amix=inputs=%d:dropout_transition=0:normalize=0,"
              "atrim=0:%.3f,asetpts=PTS-STARTPTS,apad=whole_dur=%.3f[bed]"
              % (len(beds), total, total))
    if vos:
        fc.append("".join("[e%d]" % i for i in vos) +
                  "amix=inputs=%d:dropout_transition=0:normalize=0,"
                  "atrim=0:%.3f,asetpts=PTS-STARTPTS,volume=3.0[vo]" % (len(vos), total))
        fc.append("[vo]asplit=2[vo_sc0][vo_mix]")
        fc.append("[vo_sc0]apad=whole_dur=%.3f[vo_sc]" % total)
        fc.append("[bed][vo_sc]sidechaincompress=threshold=0.020:ratio=7:attack=4:release=140,"
                  "volume=%.2f[bed_d]" % duk)
        fc.append("[bed_d][vo_mix]amix=inputs=2:dropout_transition=0:normalize=0,"
                  "atrim=0:%.3f,asetpts=PTS-STARTPTS[mix]" % total)
    else:
        fc.append("[bed]atrim=0:%.3f,asetpts=PTS-STARTPTS[mix]" % total)
    fc.append("[mix]%s,afade=t=out:st=%.2f:d=%.2f,"
              "aformat=sample_fmts=s16:sample_rates=48000:channel_layouts=stereo[out]"
              % (MASTER, max(0.0, total - fade_out), fade_out))
    wav = os.path.join(BASE, name + ".wav")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[out]", "-t", "%.3f" % total,
            "-ar", "48000", "-c:a", "pcm_s16le", wav]
    run(cmd)
    match_loudness(wav)
    out = os.path.join(BASE, name + ".mp3")
    run([FF, "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "320k", out])
    return out


def lufs(path):
    s = subprocess.run([FF, "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    tail = s[s.rfind("Summary:"):]
    i = [l for l in tail.splitlines() if "I:" in l]
    p = [l for l in tail.splitlines() if "Peak:" in l]
    return (i[0].strip() if i else "?"), (p[0].strip() if p else "?")


# ═══════════════════════ 1. «УДАР» — классический тяжёлый айди
def v1():
    e = []
    e.append((element("v1_boom", os.path.join(SFX, "boom_cinematic.mp3"), 0.0, 3.50,
                      "lowpass=f=180,equalizer=f=55:t=q:w=1.2:g=3", 0.80), 0.0, 1.0, "bed"))
    e.append((element("v1_deep", os.path.join(SFX, "impact_deep.mp3"), 0.0, 1.6, None, 0.9), 0.0, 1.0, "bed"))
    e.append((element("v1_br", os.path.join(SFX, "impact_bright.mp3"), 0.0, 0.55,
                      "highpass=f=900", 0.16), 0.02, 1.0, "bed"))
    e.append((element("v1_vo", tighten(os.path.join(VO, "j1_v_okope.mp3"), "j1.wav"), None, None, VO_CHAIN, 1.0), 0.55, 1.0, "vo"))
    e.append((element("v1_sting", os.path.join(SFX, "logo_sting.mp3"), 0.0, 1.45,
                      "highpass=f=200,lowpass=f=9000", 0.60), 2.10, 1.0, "bed"))
    return mix("vokope_jingle_1_udar", 3.6, e, 0.35), e, 3.6


# ═══════════════════════ 2. «ПОЗЫВНЫЕ» — рация, щелчок, узкая полоса
def v2():
    e = []
    e.append((element("v2_click", os.path.join(SFX, "camera_shutter.mp3"), 0.0, 0.32, None, 0.9), 0.0, 1.0, "bed"))
    e.append((element("v2_beeps", os.path.join(SFX, "countdown_beeps.mp3"), 0.0, 0.55,
                      "highpass=f=700,volume=0.28", 0.5), 0.06, 1.0, "bed"))
    e.append((element("v2_bed", os.path.join(MUS, "fvi-Chronos.ogg"), 61.35, 3.4,
                      "lowpass=f=900,highpass=f=40", 0.38), 0.0, 1.0, "bed"))
    e.append((element("v2_vo", tighten(os.path.join(VO, "j2_radio_v_okope.mp3"), "j2.wav"), None, None, RADIO_CHAIN, 1.0), 0.26, 1.0, "vo"))
    e.append((element("v2_click2", os.path.join(SFX, "camera_shutter.mp3"), 0.0, 0.32, "volume=0.8", 0.55),
              2.74, 1.0, "bed"))
    e.append((element("v2_deep", os.path.join(SFX, "impact_deep.mp3"), 0.0, 1.6, "lowpass=f=140", 0.5),
              2.80, 1.0, "bed"))
    return mix("vokope_jingle_2_pozyvnye", 3.9, e, 0.30, 0.62), e, 3.9


# ═══════════════════════ 3. «ДРАЙВ» — бит и быстрый голос
def v3():
    e = []
    e.append((element("v3_stab", os.path.join(MUS, "fvi-BeatOne.ogg"), 47.25, 3.80,
                      "lowpass=f=12000", 0.72), 0.0, 1.0, "bed"))
    e.append((element("v3_deep", os.path.join(SFX, "impact_deep.mp3"), 0.0, 1.2, None, 0.65), 0.0, 1.0, "bed"))
    e.append((element("v3_whoosh", os.path.join(SFX, "whoosh_short.mp3"), 0.0, 0.42,
                      "highpass=f=400", 0.4), 0.58, 1.0, "bed"))
    e.append((element("v3_vo", tighten(os.path.join(VO, "j3_v_okope_na_svyazi.mp3"), "j3.wav"), None, None,
                      "atempo=1.06," + VO_CHAIN, 1.0), 0.30, 1.0, "vo"))
    return mix("vokope_jingle_3_drayv", 3.8, e, 0.30), e, 3.8


# ═══════════════════════ 4. «МАРШ» — три удара, тяжёлый хвост
def v4():
    e = []
    e.append((element("v4_a", os.path.join(SFX, "impact_deep.mp3"), 0.0, 1.1, None, 0.95), 0.0, 1.0, "bed"))
    e.append((element("v4_b", os.path.join(SFX, "impact_deep.mp3"), 0.0, 0.9, "highpass=f=90", 0.55), 0.50, 1.0, "bed"))
    e.append((element("v4_c", os.path.join(SFX, "impact_deep.mp3"), 0.0, 0.8, "highpass=f=140", 0.40), 1.26, 1.0, "bed"))
    e.append((element("v4_vo", tighten(os.path.join(VO, "j4_eto_v_okope.mp3"), "j4.wav"), None, None, VO_CHAIN, 1.0), 0.98, 1.0, "vo"))
    e.append((element("v4_boom", os.path.join(SFX, "boom_cinematic.mp3"), 0.0, 1.9,
                      "lowpass=f=220", 0.60), 2.22, 1.0, "bed"))
    e.append((element("v4_gong", os.path.join(SFX, "gong_section.mp3"), 0.0, 1.6,
                      "lowpass=f=1500", 0.30), 2.32, 1.0, "bed"))
    return mix("vokope_jingle_4_marsh", 4.4, e, 0.45), e, 4.4


# ═══════════════════════ 5. «ПОДЛОЖКА» — без голоса, под начитку ведущего
def v5():
    e = []
    e.append((element("v5_bed", os.path.join(MUS, "fvi-Chronos.ogg"), 61.35, 3.5,
                      "highpass=f=38,lowpass=f=11000", 0.85), 0.0, 1.0, "bed"))
    e.append((element("v5_deep", os.path.join(SFX, "impact_deep.mp3"), 0.0, 1.4, None, 0.75), 0.0, 1.0, "bed"))
    e.append((element("v5_sting", os.path.join(SFX, "logo_sting.mp3"), 0.0, 1.6,
                      "highpass=f=250", 0.45), 1.55, 1.0, "bed"))
    e.append((element("v5_whoosh", os.path.join(SFX, "whoosh_transition.mp3"), 0.0, 0.95,
                      "highpass=f=500", 0.32), 0.30, 1.0, "bed"))
    return mix("vokope_jingle_5_podlozhka", 3.5, e, 0.40), e, 3.5


def vo_contribution(items, total):
    """Насколько голос прибавляет в речевой полосе 1–4 кГц (дБ). > 6 — слышно уверенно."""
    import numpy as np
    SR = 48000
    n = int(total * SR)
    bed = np.zeros(n, np.float32)
    vo = np.zeros(n, np.float32)
    for w, delay, gain, role in items:
        x = np.frombuffer(subprocess.run([FF, "-v", "quiet", "-i", w, "-ac", "1", "-ar", str(SR),
                                          "-f", "s16le", "-"], capture_output=True).stdout,
                          dtype=np.int16).astype(np.float32) / 32768
        i0 = int(delay * SR)
        seg = x[:max(0, n - i0)] * gain
        if role == "vo":
            vo[i0:i0 + len(seg)] += seg * 3.0
        else:
            bed[i0:i0 + len(seg)] += seg

    def band_e(sig):
        X = np.fft.rfft(sig)
        f = np.fft.rfftfreq(len(sig), 1 / SR)
        X[(f < 1000) | (f > 4000)] = 0
        return float((np.fft.irfft(X, len(sig)) ** 2).sum())

    voiced = np.flatnonzero(np.abs(vo) > 0.02)
    if voiced.size == 0:
        return 0.0
    a, b = int(voiced[0]), int(voiced[-1]) + 1
    e_all, e_bed = band_e((bed + vo)[a:b]), band_e(bed[a:b])
    return 10 * np.log10(max(e_all, 1e-12) / max(e_bed, 1e-12))


if __name__ == "__main__":
    outs = []
    for fn in (v1, v2, v3, v4, v5):
        p, items, total = fn()
        i, pk = lufs(p)
        d = dur(p)
        vc = vo_contribution(items, total) if any(it[3] == "vo" for it in items) else None
        extra = ("голос: +%.1f дБ в речевой полосе" % vc) if vc else "без голоса"
        print("%-38s %5.2f с   %s   %s   %s" % (os.path.basename(p), d, i, pk, extra))
        outs.append({"file": os.path.basename(p), "duration": round(d, 2),
                     "lufs": i.split(":")[1].strip() if ":" in i else i,
                     "vo_boost_db": round(vc, 1) if vc else None,
                     "file_path": p})
    json.dump(outs, open(os.path.join(BASE, "jingles.json"), "w"), ensure_ascii=False, indent=1)
