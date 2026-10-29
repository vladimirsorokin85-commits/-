# -*- coding: utf-8 -*-
"""«Алдан-12» — горизонталь 16:9: звук.

Схема: 12 клипов озвучки (voice-28) по блокам → нарезка на 90 реплик по паузам →
цепочка обработки на каждую реплику → последовательная укладка с паузами →
реальный мастер fvi-Favorite (120 BPM, ДРАЙВ) в луп с кроссфейдами → дакинг → лимитер.

Результат: master_aldan_horizontal.mp3 + horizontal_timeline.json (тайминги 90 кадров).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

BASE = "/home/user/-/video_studio/aldan12"
FF = "/home/user/.local/bin/ffmpeg"
MUSIC = "/home/user/-/video_studio/music_downloaded/fvi-Favorite.ogg"
assert "/music_downloaded/" in MUSIC, "разрешена ТОЛЬКО реальная скачанная музыка"

sys.path.insert(0, "/home/user/-/video_studio/toolkit")
from music_check import check as drive_check  # noqa: E402

_ok, _m, _fails = drive_check(MUSIC)
if not _ok:
    sys.exit("!! трек не проходит проверку на драйв: " + "; ".join(_fails))

SR = 16000
LEAD = 0.55          # тишина до первой реплики
GAP = 0.26           # пауза между репликами внутри блока
GAP_BLOCK = 0.62     # пауза на стыке блоков
TAIL = 1.15          # хвост после последней реплики (эндкард)
VO_CHAIN = ("highpass=f=70,"
            "equalizer=f=115:t=q:w=1.0:g=2.6,"
            "equalizer=f=3300:t=q:w=1.5:g=3.0,"
            "acompressor=threshold=-19dB:ratio=4:attack=4:release=60,"
            "loudnorm=I=-15:TP=-1.8:LRA=9")

CLIPS = [("h1", "1"), ("h2", "2"), ("h3", "3"), ("h4", "4"), ("h5", "5"), ("h6", "6"),
         ("h7a", "7a"), ("h7b", "7b"), ("h8", "8"), ("h9", "9"), ("h10", "10"), ("h11", "11")]


def dur(p):
    s = subprocess.run([FF, "-hide_banner", "-i", p], stderr=subprocess.PIPE, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def run(cmd):
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def decode_mono(p):
    raw = subprocess.check_output([FF, "-v", "error", "-i", p, "-f", "s16le",
                                   "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def pauses(y, thr_db=-34.0, min_len=0.10):
    """Список (start, end) тихих участков длиной >= min_len."""
    win = int(SR * 0.01)
    n = len(y) // win
    rms = np.sqrt(np.mean(y[:n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    sil = db < thr_db
    out, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 0.01 >= min_len:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def cut_points(y, texts):
    """Границы сегментов: DP по паузам, минимизируем отклонение от пропорций текста."""
    n_parts = len(texts)
    total = len(y) / SR
    ps = [(a, b) for a, b in pauses(y) if a > total * 0.03 and b < total * 0.97]
    if len(ps) < n_parts - 1:
        print(f"   !! пауз найдено {len(ps)} < {n_parts - 1} — делю пропорционально тексту")
        return None
    cand = [0.0] + [(a + b) / 2 for a, b in ps] + [total]
    m = len(cand)
    k = total / float(sum(len(t) for t in texts))
    want = [k * len(t) for t in texts]
    INF = 1e18
    dp = [[INF] * m for _ in range(n_parts + 1)]
    back = [[-1] * m for _ in range(n_parts + 1)]
    dp[0][0] = 0.0
    for nseg in range(1, n_parts + 1):
        for i in range(1, m):
            best, arg = INF, -1
            for pj in range(0, i):
                if dp[nseg - 1][pj] >= INF:
                    continue
                seg = cand[i] - cand[pj]
                if seg < 0.55 * want[nseg - 1]:
                    continue
                cost = dp[nseg - 1][pj] + abs(seg - want[nseg - 1])
                if cost < best:
                    best, arg = cost, pj
            dp[nseg][i] = best
            back[nseg][i] = arg
    j = m - 1
    if dp[n_parts][j] >= INF:
        print("   !! DP не нашёл разбиения — пропорционально тексту")
        return None
    cuts = []
    for nseg in range(n_parts, 0, -1):
        pj = back[nseg][j]
        cuts.append(cand[pj])
        j = pj
    return sorted(c for c in cuts if 0.05 < c < total - 0.05)


def write_wav(seg, p):
    import wave
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(seg, -1, 1) * 32767).astype(np.int16).tobytes())


# ── 1. реплики ───────────────────────────────────────────────────────────────
blocks = json.load(open(os.path.join(BASE, "vo_blocks.json"), encoding="utf-8"))
plan = []   # (блок, номер реплики в блоке, текст, файл-клип)
for clip, key in CLIPS:
    src_parts = blocks[key[:1]]["parts"] if key in ("1", "2") else None
    if key.endswith("a"):
        parts = blocks["7"]["parts"][:10]
    elif key.endswith("b"):
        parts = blocks["7"]["parts"][10:]
    else:
        parts = blocks[key]["parts"]
    for i, t in enumerate(parts):
        plan.append((key, i, t, os.path.join(BASE, "vo", clip + ".mp3")))

print(f"реплик в плане: {len(plan)}")
missing = sorted({p[3] for p in plan if not os.path.exists(p[3])})
if missing:
    sys.exit("!! нет клипов озвучки: " + ", ".join(os.path.basename(m) for m in missing))

os.makedirs(os.path.join(BASE, "vo", "lines"), exist_ok=True)
by_clip = {}
for key, i, t, f in plan:
    by_clip.setdefault(f, []).append((key, i, t))

segs = []   # (key, text, wav path, dur)
for f, items in by_clip.items():
    y = decode_mono(f)
    cuts = cut_points(y, [t for _, _, t in items])
    total = len(y) / SR
    if cuts is None:
        # пропорционально длине текста
        weights = np.array([len(t) for _, _, t in items], np.float32)
        edges = np.cumsum(weights) / weights.sum() * total
        bounds = [0.0] + [float(edges[i]) for i in range(len(items) - 1)] + [total]
    else:
        bounds = [0.0] + cuts + [total]
    for n, (key, i, t) in enumerate(items):
        a = max(0.0, bounds[n] - 0.04)
        b = min(total, bounds[n + 1] + 0.02)
        seg = y[int(a * SR):int(b * SR)]
        # обрезаем хвостовую тишину, оставляя 60 мс
        segs.append((key, t, seg, b - a))
    print(f"{os.path.basename(f)}: {len(items)} реплик, {total:.2f}s, паузы: "
          f"{'да' if cuts else 'пропорц.'}")

# ── 2. обработка и укладка ───────────────────────────────────────────────────
timeline, t = [], LEAD
prev_key = None
for n, (key, text, seg, d0) in enumerate(segs):
    if prev_key is not None:
        t += GAP_BLOCK if key != prev_key else GAP
    raw = os.path.join(BASE, "vo", "lines", f"l{n + 1:02d}.wav")
    prc = os.path.join(BASE, "vo", "lines", f"p{n + 1:02d}.mp3")
    write_wav(seg, raw)
    run([FF, "-y", "-i", raw, "-af", VO_CHAIN, "-ar", "48000", "-ac", "2",
         "-b:a", "192k", prc])
    d = dur(prc)
    timeline.append({"n": n + 1, "block": key, "start": round(t, 3),
                     "dur": round(d, 3), "text": text})
    t += d
    prev_key = key

TOTAL = round(t + TAIL, 2)
print(f"итог по голосу: {TOTAL:.2f}s = {int(TOTAL // 60):02d}:{TOTAL % 60:05.2f}")

# приводим к цели ~590 с: речь бодрее, хронометраж в брифе
TARGET = 590.0
if TOTAL > TARGET * 1.02:
    k = TOTAL / TARGET
    print(f"ускоряю реплики на {k:.3f} (цель {TARGET:.0f}s, было {TOTAL:.1f}s)")
    for n, item in enumerate(timeline, 1):
        prc = os.path.join(BASE, "vo", "lines", f"p{n:02d}.mp3")
        run([FF, "-y", "-i", prc, "-af", f"atempo={min(1.18, k):.4f}", "-ar", "48000",
             "-ac", "2", "-b:a", "192k", prc + ".t.mp3"])
        os.replace(prc + ".t.mp3", prc)
    t = LEAD
    for n, item in enumerate(timeline, 1):
        item["start"] = round(t, 3)
        item["dur"] = round(dur(os.path.join(BASE, "vo", "lines", f"p{n:02d}.mp3")), 3)
        t += item["dur"] + (GAP_BLOCK if n < len(timeline) and timeline[n]["block"] != item["block"] else GAP)
    TOTAL = round(t + TAIL, 2)

# ── 3. музыка: луп с кроссфейдами ────────────────────────────────────────────
md = dur(MUSIC)
need = TOTAL + 4
copies = int(need / (md - 0.8)) + 1
ins = "".join(f"[0:a]" for _ in range(1))
fc = []
for i in range(copies):
    fc.append(f"[0:a]asplit={copies}" + "".join(f"[c{j}]" for j in range(copies)) + ";")
    break
chain = []
for i in range(copies):
    chain.append(f"[c{i}]atrim=0:{md:.3f},asetpts=PTS-STARTPTS[m{i}]")
prev = "m0"
for i in range(1, copies):
    out = f"x{i}"
    chain.append(f"[{prev}][m{i}]acrossfade=d=0.6:c1=tri:c2=tri[{out}]")
    prev = out
graph = "".join(fc) + ";".join(chain) + f";[{prev}]atrim=0:{TOTAL + 2:.2f}[bed]"
bed = os.path.join(BASE, "music_bed_h.wav")
run([FF, "-y", "-i", MUSIC, "-filter_complex", graph, "-map", "[bed]",
     "-ar", "48000", "-ac", "2", bed])
print(f"музыкальный бед: {dur(bed):.2f}s (трек {md:.2f}s × {copies})")

# ── 4. финальный микс ────────────────────────────────────────────────────────
n = len(timeline)
cmd = [FF, "-y"]
for item in timeline:
    cmd += ["-i", os.path.join(BASE, "vo", "lines", f"p{item['n']:02d}.mp3")]
cmd += ["-i", bed]

delays = "".join(
    f"[{i}:a]adelay={int(item['start'] * 1000)}|{int(item['start'] * 1000)},"
    "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    f"[v{i}];" for i, item in enumerate(timeline))
labels = "".join(f"[v{i}]" for i in range(n))
mix = (delays + labels +
       f"amix=inputs={n}:dropout_transition=0:normalize=0,apad=whole_dur={TOTAL}[vo];"
       f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
       "highpass=f=30,bass=g=2.5:f=95:w=0.6,"
       "acompressor=threshold=-16dB:ratio=2.6:attack=10:release=140,"
       "dynaudnorm=f=400:g=6:p=0.88:m=5,loudnorm=I=-13:TP=-2:LRA=10,"
       "afade=t=in:st=0:d=0.8[bg1];"
       "[vo]asplit=2[vo_sc][vo_out];"
       "[bg1][vo_sc]sidechaincompress=threshold=0.028:ratio=10:attack=4:release=200[bg_duck];"
       f"[bg_duck]afade=t=out:st={TOTAL - 1.4:.2f}:d=1.4[bgf];"
       "[vo_out]volume=1.22[vob];"
       "[bgf][vob]amix=inputs=2:dropout_transition=0:normalize=0,"
       "alimiter=limit=0.89:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=9[out]")

out = os.path.join(BASE, "master_aldan_horizontal.mp3")
cmd += ["-filter_complex", mix, "-map", "[out]", "-t", f"{TOTAL:.2f}",
        "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "320k", out]
run(cmd)

o = subprocess.check_output([FF, "-hide_banner", "-i", out, "-af", "volumedetect",
                             "-f", "null", "-"], stderr=subprocess.STDOUT).decode()
for line in o.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print("   ", line.strip())

json.dump({"total": TOTAL, "lead": LEAD,
           "lines": timeline,
           "shots": [{"n": it["n"], "start": it["start"], "dur": it["dur"]} for it in timeline]},
          open(os.path.join(BASE, "horizontal_timeline.json"), "w"), ensure_ascii=False, indent=1)
print(f"MASTER {out} {dur(out):.2f}s")
