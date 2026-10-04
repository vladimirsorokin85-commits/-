#!/usr/bin/env python3
"""Stage 1 — audio + timeline for «Окопная смекалка» v4.

* processes narration clips (tempo, loudness, announcer echo on chapter titles)
* lays out the timeline: intro splash -> prologue -> [title card -> body] x5 -> outro
* aligns sentence timings to detected pauses (dynamic programming)
* mixes voice + two alternating DnB/jungle beds (ducked, bar-aligned) + synthesized SFX
Writes /tmp/smk4/timeline.json and /tmp/smk4/mix.wav
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path("/home/user/-/video_studio")
sys.path.insert(0, str(ROOT / "script"))
sys.path.insert(0, str(ROOT / "v4"))
from narration import CLIPS  # noqa: E402
from storyboard import display_text, build_shots  # noqa: E402

FF = "ffmpeg"
SR = 48000
TMP = Path("/tmp/smk4")
TMP.mkdir(parents=True, exist_ok=True)
AUD = ROOT / "audio_v4"
MUSIC_A = ROOT / "music_catalog" / "dnb_neuro_174.ogg"
MUSIC_B = ROOT / "music_catalog" / "jungle_hoover_174.ogg"
BAR = 4 * 60 / 174

BODY_TEMPO = 1.2
TITLE_TEMPO = 1.08
PROLOGUE_SPLIT = 36.25          # seconds in raw c01 where "Хитрость номер один" starts
PROLOGUE_BOUNDS = [5.13, 10.34, 15.17, 24.79, 28.66]   # sentence ends (sped-up seconds)
INTRO_DUR = 4.5
OUTRO_DUR = 6.0


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_wav(p):
    sr, a = wavfile.read(p)
    a = a.astype(np.float32) / 32768.0
    if a.ndim > 1:
        a = a.mean(axis=1)
    assert sr == SR
    return a


def process_voice(src, dst, tempo, ss=None, to=None, announcer=False):
    af = [f"atempo={tempo}", "highpass=f=70", "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=3"]
    if announcer:
        af += ["equalizer=f=180:t=q:w=1:g=3", "aecho=0.85:0.6:70|140:0.22|0.10"]
    cmd = [FF, "-y"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if to is not None:
        cmd += ["-to", str(to)]
    cmd += ["-i", str(src), "-af", ",".join(af), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)]
    run(cmd)
    a = load_wav(dst)
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.12 * SR)]
    act = a[np.abs(a) > 0.02]
    rms = np.sqrt(np.mean(act ** 2)) if len(act) else 0.1
    return a * (10 ** (-17 / 20) / rms)


def find_pauses(a, thr_db=-38, min_len=0.12):
    win = int(0.02 * SR)
    n = len(a) // win
    fr = a[: n * win].reshape(n, win)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    db -= np.percentile(db, 95)
    quiet = db < (thr_db + 10)
    out, s = [], None
    for i, q in enumerate(quiet):
        if q and s is None:
            s = i
        if not q and s is not None:
            if (i - s) * 0.02 >= min_len:
                out.append((s * 0.02, i * 0.02))
            s = None
    return out


def split_sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def sentence_times(text, a, minp=0.2, wcost=6.0, wbonus=10.0, cap=0.4, manual=None):
    """Sentence-level DP alignment of text to detected pauses (char-length model, tuned by hand-annotation)."""
    sents = split_sentences(text)
    dur = len(a) / SR
    K = len(sents)
    ps = find_pauses(a, min_len=0.09)
    cand = [((s_ + e) / 2, e - s_) for s_, e in ps if e - s_ >= minp and 0.25 < (s_ + e) / 2 < dur - 0.25]
    w = [len(x) + 4 for x in sents]
    if manual is not None:
        bounds = [0.0] + list(manual) + [dur]
    elif K == 1 or len(cand) < K - 1:
        cum = np.cumsum(w) / sum(w)
        bounds = [0.0] + [float(c * dur) for c in cum[:-1]] + [dur]
    else:
        pos = np.array([0.0] + [c[0] for c in cand] + [dur])
        pl = np.array([0.0] + [c[1] for c in cand] + [0.0])
        P = len(pos)
        rate = dur / sum(w)
        INF = 1e18
        cost = np.full((K + 1, P), INF)
        back = np.zeros((K + 1, P), int)
        cost[0, 0] = 0
        for k in range(1, K + 1):
            e = w[k - 1] * rate
            for j in range(1, P):
                if (k == K) != (j == P - 1):
                    continue
                d = pos[j] - pos[:j]
                prev = cost[k - 1, :j]
                ok = (prev < INF) & (d > 0.3)
                if not ok.any():
                    continue
                c = np.where(ok, prev + wcost * np.log(np.maximum(d, .01) / e) ** 2, INF)
                i = int(np.argmin(c))
                cost[k, j] = c[i] - (0 if j == P - 1 else wbonus * min(pl[j], cap))
                back[k, j] = i
        j = P - 1
        idx = [j]
        for k in range(K, 0, -1):
            j = back[k, j]
            idx.append(j)
        bounds = [float(pos[i]) for i in idx[::-1]]
    return [{"text": x, "disp": display_text(x), "t0": bounds[i], "t1": bounds[i + 1]} for i, x in enumerate(sents)]


# ---------------------------------------------------------------- SFX synth
rng = np.random.default_rng(7)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def sfx_whoosh(dur=0.45, up=True):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    chunks = 24
    for c in range(chunks):
        a, b = c * n // chunks, (c + 1) * n // chunks
        frac = c / (chunks - 1)
        fc = 300 + 4500 * (frac if up else 1 - frac)
        sos = signal.butter(2, [max(80, fc * 0.6), min(20000, fc * 1.6)], btype="band", fs=SR, output="sos")
        out[a:b] = signal.sosfilt(sos, noise[max(0, a - 512): b])[-(b - a):]
    shape = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return (out * shape / (np.abs(out).max() + 1e-9)).astype(np.float32)


def sfx_impact(dur=1.4, f0=110, f1=38, punch=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.45)
    nb = signal.sosfilt(signal.butter(2, 2500, fs=SR, output="sos"), rng.standard_normal(n) * env_exp(n, 0.06))
    crack = rng.standard_normal(n) * env_exp(n, 0.012)
    x = np.tanh((sub + nb * 0.9 * punch + crack * 0.35 * punch) * 2.2)
    return (x / np.abs(x).max()).astype(np.float32)


def sfx_riser(dur=1.1):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    chunks = 20
    for c in range(chunks):
        a, b = c * n // chunks, (c + 1) * n // chunks
        sos = signal.butter(2, 400 * (12 ** (c / chunks)), btype="high", fs=SR, output="sos")
        out[a:b] = signal.sosfilt(sos, noise[max(0, a - 512): b])[-(b - a):]
    tone = np.sin(2 * np.pi * np.cumsum(180 * (8 ** (t / dur))) / SR) * 0.35
    x = (out / np.abs(out).max() * 0.8 + tone) * (t / dur) ** 2.2
    return (x / np.abs(x).max()).astype(np.float32)


def sfx_blip(freq=1400, dur=0.09):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) * env_exp(n, 0.025) + 0.5 * np.sin(2 * np.pi * freq * 1.5 * t) * env_exp(n, 0.015)
    return (x / np.abs(x).max()).astype(np.float32)


def sfx_tension(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = 0.6 * np.sin(2 * np.pi * 55 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)
    pulse = np.zeros(n)
    for k in np.arange(0, dur, 60 / 87):  # half-time of 174 BPM
        i = int(k * SR)
        m = min(n - i, int(0.25 * SR))
        pulse[i:i + m] += np.sin(2 * np.pi * 48 * np.arange(m) / SR) * env_exp(m, 0.07)
    nz = signal.sosfilt(signal.butter(2, 600, fs=SR, output="sos"), rng.standard_normal(n)) * 0.25
    fade = np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.4))
    x = (x + pulse * 1.2 + nz) * fade
    return (x / np.abs(x).max()).astype(np.float32)


def load_music(p):
    raw = TMP / (p.stem + ".wav")
    run([FF, "-y", "-i", str(p), "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", str(raw)])
    sr, a = wavfile.read(raw)
    a = a.astype(np.float32) / 32768.0
    return a / np.sqrt(np.mean(a ** 2)) * 10 ** (-12 / 20)


def music_slice(track, offset, dur):
    n = int(dur * SR)
    i0 = int(offset * SR) % len(track)
    out = np.zeros((n, 2), np.float32)
    pos = 0
    while pos < n:
        take = min(n - pos, len(track) - i0)
        out[pos:pos + take] = track[i0:i0 + take]
        pos += take
        i0 = 0
    return out


def main():
    timeline = {"intro": INTRO_DUR, "segments": [], "sfx": [], "chapters": []}
    vox = {}
    print("voice processing…")
    vox["prologue"] = process_voice(AUD / "c01_prologue.mp3", TMP / "v_prologue.wav", BODY_TEMPO, to=PROLOGUE_SPLIT)
    vox["title1"] = process_voice(AUD / "c01_prologue.mp3", TMP / "v_title1.wav", TITLE_TEMPO, ss=PROLOGUE_SPLIT - 0.1, announcer=True)
    for k, (tname, bname) in enumerate([(None, "c02_body1"), ("c03_title2", "c04_body2"), ("c05_title3", "c06_body3"),
                                        ("c07_title4", "c08_body4"), ("c09_title5", "c10_body5")], start=1):
        if tname:
            vox[f"title{k}"] = process_voice(AUD / f"{tname}.mp3", TMP / f"v_title{k}.wav", TITLE_TEMPO, announcer=True)
        vox[f"body{k}"] = process_voice(AUD / f"{bname}.mp3", TMP / f"v_body{k}.wav", BODY_TEMPO)
    for k, v in vox.items():
        print(f"  {k}: {len(v)/SR:.2f}s")

    t = INTRO_DUR
    voice_events = []
    pro_text = CLIPS["c01_prologue"].split("Хитрость номер один")[0].strip()
    pro_sents = sentence_times(pro_text, vox["prologue"], manual=PROLOGUE_BOUNDS)
    v0 = t + 0.05
    voice_events.append((v0, vox["prologue"]))
    timeline["segments"].append({"kind": "prologue", "t0": INTRO_DUR, "t1": v0 + len(vox["prologue"]) / SR + 0.3,
                                 "voice_t0": v0, "sentences": pro_sents})
    t = timeline["segments"][-1]["t1"]

    body_keys = ["c02_body1", "c04_body2", "c06_body3", "c08_body4", "c10_body5"]
    for k in range(1, 6):
        tv = vox[f"title{k}"]
        card_t0 = t
        tv0 = card_t0 + 0.45
        pauses = [p for p in find_pauses(tv, min_len=0.15) if p[0] > 0.6]
        phrase2 = pauses[0][1] if pauses else len(tv) / SR * 0.4
        card_t1 = tv0 + len(tv) / SR + 0.55
        voice_events.append((tv0, tv))
        timeline["segments"].append({"kind": "title", "chapter": k, "t0": card_t0, "t1": card_t1, "voice_t0": tv0,
                                     "slam_t": tv0 + 0.72, "phrase2_t": tv0 + phrase2})
        bv = vox[f"body{k}"]
        b_t0 = card_t1
        bv0 = b_t0 + 0.3
        sents = sentence_times(CLIPS[body_keys[k - 1]], bv)
        b_t1 = bv0 + len(bv) / SR + 0.35
        voice_events.append((bv0, bv))
        timeline["segments"].append({"kind": "body", "chapter": k, "t0": b_t0, "t1": b_t1, "voice_t0": bv0, "sentences": sents})
        timeline["chapters"].append({"chapter": k, "title_t0": card_t0, "body_t0": b_t0, "body_t1": b_t1})
        t = b_t1
    timeline["segments"].append({"kind": "outro", "t0": t, "t1": t + OUTRO_DUR})
    total = t + OUTRO_DUR
    timeline["total"] = total
    print(f"total duration: {total:.2f}s ({total/60:.2f} min)")

    shots, badges, subs = build_shots(timeline)
    timeline["shots"], timeline["badges"], timeline["subs"] = shots, badges, subs

    N = int(total * SR) + SR
    voice = np.zeros(N, np.float32)
    for st, arr in voice_events:
        i = int(st * SR)
        voice[i:i + len(arr)] += arr

    env = np.convolve(np.abs(voice), np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
    act = (env > 0.006).astype(np.float32)
    act = (np.convolve(act, np.ones(int(0.45 * SR)), mode="same") > 0).astype(np.float32)
    sm = int(0.12 * SR)
    act = np.convolve(act, np.ones(sm) / sm, mode="same")

    A = load_music(MUSIC_A)
    B = load_music(MUSIC_B)
    music = np.zeros((N, 2), np.float32)

    def put_music(track, off, t0, t1, fin=0.02, fout=0.25):
        sl = music_slice(track, off, t1 - t0)
        n = len(sl)
        g = np.ones(n, np.float32)
        fi, fo = int(fin * SR), int(fout * SR)
        if fi:
            g[:fi] = np.linspace(0, 1, fi)
        if fo:
            g[-fo:] *= np.linspace(1, 0, fo)
        i = int(t0 * SR)
        music[i:i + n] += sl * g[:, None]

    segs = timeline["segments"]
    # bar-aligned offsets into the 132-bar tracks (drops at bars 16, 56, 96)
    put_music(A, 96 * BAR, 0.0, segs[1]["t0"] + 0.05, fin=0.0, fout=0.3)
    plan = {1: (B, 16 * BAR), 2: (A, 56 * BAR), 3: (B, 56 * BAR), 4: (A, 16 * BAR), 5: (B, 64 * BAR)}
    for s in segs:
        if s["kind"] == "body":
            tr, off = plan[s["chapter"]]
            end = s["t1"] + (OUTRO_DUR if s["chapter"] == 5 else 0.0) + 0.05
            put_music(tr, off, s["t0"], end, fin=0.01, fout=3.0 if s["chapter"] == 5 else 0.25)

    gap_gain = 10 ** (-7 / 20)
    duck_gain = 10 ** (-17.5 / 20)
    music *= (gap_gain + (duck_gain - gap_gain) * act)[:, None]

    sfx = np.zeros(N, np.float32)
    bank = {"whoosh": sfx_whoosh(0.42), "whoosh_dn": sfx_whoosh(0.5, up=False), "impact": sfx_impact(),
            "hit": sfx_impact(0.7, 160, 55, 1.2), "riser": sfx_riser(1.1), "blip": sfx_blip()}

    def add(name, t0, g):
        x = bank[name]
        i = int(t0 * SR)
        if i < 0:
            x = x[-i:]
            i = 0
        sfx[i:i + len(x)] += x[: max(0, N - i)] * g
        timeline["sfx"].append([name, round(t0, 3)])

    for c in range(8):
        add("hit", c * 0.3, 0.55)
    add("riser", 2.4 - 1.1, 0.35)
    add("impact", 2.4, 0.9)
    add("impact", 2.75, 0.7)
    add("whoosh", 3.1, 0.3)
    add("whoosh_dn", INTRO_DUR - 0.25, 0.4)
    for s in segs:
        if s["kind"] == "title":
            add("riser", s["slam_t"] - 1.1, 0.45)
            add("whoosh", s["t0"] + 0.05, 0.45)
            add("impact", s["slam_t"], 1.0)
            add("whoosh", s["phrase2_t"] - 0.1, 0.35)
            ten = sfx_tension(s["t1"] - s["t0"])
            i = int(s["t0"] * SR)
            sfx[i:i + len(ten)] += ten * 0.16
            add("hit", s["t1"] - 0.02, 0.7)
        if s["kind"] == "outro":
            add("impact", s["t0"] + 0.1, 0.8)
    for sh in timeline["shots"]:
        if sh.get("sfx"):
            add(sh["sfx"], sh["t0"] - (0.18 if sh["sfx"].startswith("whoosh") else 0), sh.get("sfx_gain", 0.22))
    for b in timeline["badges"]:
        add("blip", b["t0"], 0.18)
        add("whoosh", b["t0"] - 0.15, 0.16)

    mix = music + np.stack([sfx, sfx], axis=1) * 0.5 + voice[:, None]
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix = mix[: int(total * SR)]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.93
    wavfile.write(TMP / "mix.wav", SR, (mix * 32767).astype(np.int16))
    with open(TMP / "timeline.json", "w") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=1)
    print("shots:", len(shots), "badges:", len(badges), "subs:", len(subs))


if __name__ == "__main__":
    main()
