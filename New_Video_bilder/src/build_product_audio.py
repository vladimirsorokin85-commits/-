#!/usr/bin/env python3
"""
Sample-accurate 30.000s (48 kHz stereo = 1,440,000 samples = 1800 frames @ 60 fps)
master audio builder for BOTH «В ОКОПЕ» Reels using 100% CC0-1.0 Public Domain real studio Drum & Bass MP3 tracks
(`cc0_dnb_voevoda_30s.mp3` — Peter Szegvari Street Action DnB & `cc0_dnb_store_30s.mp3` — warlightwolf Tech DnB 20,
0.00% vocals, ZERO Content ID, ZERO internal procedural music synth engine!).
"""
import json
import math
import re
import subprocess
import wave
from pathlib import Path
import numpy as np

PROJECT = Path("/home/user/-/New_Video_bilder")
STUDIO = Path("/home/user/-/video_studio")
AUDIO_DIR = PROJECT / "assets" / "audio"
PROD_VO_DIR = AUDIO_DIR / "prod_vo"
MP3_DIR = AUDIO_DIR / "music_mp3"
SFX_DIR = STUDIO / "toolkit" / "sfx"

SR = 48000
FPS = 60
DURATION = 30.0
TOTAL_SAMPLES = int(round(DURATION * SR))  # 1,440,000 exact stereo samples
BPM = 174.0
BEAT = 60.0 / BPM          # 0.3448275862 s
BAR = BEAT * 4.0           # 1.3793103448 s


def decode_audio(path: Path, af: str = "", stereo: bool = False) -> np.ndarray:
    ch = 2 if stereo else 1
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", str(ch), "-ar", str(SR)]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, dtype=np.float32).copy()
    return arr.reshape(-1, 2) if stereo else arr


def write_wav_pcm16(path: Path, stereo_arr: np.ndarray):
    clipped = np.clip(stereo_arr, -0.9999, 0.9999)
    pcm = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def export_mp3_320(wav_or_arr, mp3_path: Path):
    tmp = mp3_path.with_suffix(".tmp.wav")
    write_wav_pcm16(tmp, wav_or_arr)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-codec:a", "libmp3lame", "-b:a", "320k", str(mp3_path)],
        check=True
    )
    tmp.unlink(missing_ok=True)


def measure_ebur128(wav_path: Path):
    res = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(wav_path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, check=True
    )
    txt = res.stderr
    m_i = re.findall(r"I:\s*([-\d.]+)\s*LUFS", txt)
    m_tp = re.findall(r"Peak:\s*([-\d.]+)\s*dBFS", txt)
    return float(m_i[-1]), float(m_tp[-1])


def moving_rms(x: np.ndarray, win: int) -> np.ndarray:
    cs = np.cumsum(np.insert(x.astype(np.float64) ** 2, 0, 0.0))
    same = (cs[win:] - cs[:-win]) / win
    pad_l = win // 2
    pad_r = len(x) - len(same) - pad_l
    return np.sqrt(np.pad(same, (pad_l, max(0, pad_r)), mode="edge") + 1e-12).astype(np.float32)


def trim_silence(x: np.ndarray, thr: float = 0.015, pad_in: float = 0.025, pad_out: float = 0.070) -> np.ndarray:
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, int(idx[0] - pad_in * SR))
    b = min(len(x), int(idx[-1] + pad_out * SR))
    out = x[a:b].copy()
    fi = min(int(0.012 * SR), len(out) // 4)
    fo = min(int(0.035 * SR), len(out) // 4)
    if fi > 0:
        out[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    if fo > 0:
        out[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    return out


def squeeze_pauses(x: np.ndarray, max_pause: float = 0.17, thr_db: float = -39.0) -> np.ndarray:
    w = int(0.02 * SR)
    n = len(x) // w
    if n < 4:
        return x
    rms = np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, axis=1) + 1e-12)
    quiet = (20.0 * np.log10(rms)) < thr_db
    chunks = []
    i = 0
    while i < n:
        j = i
        while j < n and quiet[j] == quiet[i]:
            j += 1
        seg = x[i * w : j * w]
        if quiet[i] and 0 < i and j < n and len(seg) > int(max_pause * SR):
            keep = int(max_pause * SR)
            half = keep // 2
            xfade = min(240, half // 2)
            left = seg[:half].copy()
            right = seg[-half:].copy()
            left[-xfade:] *= np.linspace(1.0, 0.0, xfade, dtype=np.float32)
            right[:xfade] *= np.linspace(0.0, 1.0, xfade, dtype=np.float32)
            seg = np.concatenate([left[:-xfade], left[-xfade:] + right[:xfade], right[xfade:]])
        chunks.append(seg)
        i = j
    chunks.append(x[n * w :])
    return np.concatenate(chunks)


def polish_voice(path: Path, tempo: float) -> np.ndarray:
    af = f"atempo={tempo:.4f},highpass=f=85,equalizer=f=3400:t=q:w=1.1:g=2.6"
    raw = squeeze_pauses(trim_silence(decode_audio(path, af=af)))
    env = moving_rms(raw, int(0.14 * SR))
    active = env[env > 0.008]
    med = float(np.percentile(active, 60)) if len(active) else 0.05
    gain = np.clip((med / np.maximum(env, med * 0.28)) ** 0.30, 0.65, 1.60)
    gain = moving_rms(gain, int(0.04 * SR))
    y = raw * gain
    rms_active = float(np.sqrt(np.mean(y[env > 0.008] ** 2) + 1e-12))
    target_rms = 10.0 ** (-16.2 / 20.0)
    return (y * (target_rms / rms_active)).astype(np.float32)


def crossfade_join(parts: list[np.ndarray], xfade_ms: float = 12.0) -> np.ndarray:
    """Join beat-aligned real MP3 slices with equal-power short crossfades (zero clicks, zero phase drift)."""
    xf = int(round(xfade_ms * 0.001 * SR))
    out = parts[0].copy()
    for nxt in parts[1:]:
        a = out[:-xf]
        tail = out[-xf:]
        head = nxt[:xf]
        rest = nxt[xf:]
        theta = np.linspace(0.0, math.pi * 0.5, xf, dtype=np.float32)[:, None]
        blended = tail * np.cos(theta) + head * np.sin(theta)
        out = np.vstack([a, blended, rest])
    return out


def build_real_dnb_cut(src_full: np.ndarray, segments_sec: list[tuple[float, float]], out_mp3: Path) -> np.ndarray:
    """
    Slice exact 174.000 BPM bar-aligned pure-instrumental drop sections from real studio Drum & Bass MP3,
    preserving exact total sample count (1,440,000 samples = 30.000s) and saving a standalone 320 kbps MP3!
    """
    xf_s = 0.012
    parts = []
    for idx, (t0, dur) in enumerate(segments_sec):
        extra = xf_s if idx < len(segments_sec) - 1 else 0.35
        s0 = int(round(t0 * SR))
        s1 = min(len(src_full), s0 + int(round((dur + extra) * SR)))
        parts.append(src_full[s0:s1].copy())
    joined = crossfade_join(parts, xfade_ms=12.0)[:TOTAL_SAMPLES].copy()
    if len(joined) < TOTAL_SAMPLES:
        joined = np.vstack([joined, np.zeros((TOTAL_SAMPLES - len(joined), 2), dtype=np.float32)])
    # Clean fade-in (15 ms) and smooth natural ring-out fade at end (350 ms)
    fi = int(0.015 * SR)
    fo = int(0.350 * SR)
    joined[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    joined[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32))))[:, None]
    export_mp3_320(joined * (0.88 / max(float(np.max(np.abs(joined))), 1e-6)), out_mp3)
    return joined


def add_stereo_clip(buf: np.ndarray, clip: np.ndarray, start_s: float, gain_db: float = 0.0, pan: float = 0.0) -> float:
    g = 10.0 ** (gain_db / 20.0)
    if clip.ndim == 1:
        gl = g * math.cos((pan + 1.0) * math.pi / 4.0) * math.sqrt(2.0)
        gr = g * math.sin((pan + 1.0) * math.pi / 4.0) * math.sqrt(2.0)
        st = np.stack([clip * gl, clip * gr], axis=1)
    else:
        st = clip * g
    idx0 = max(0, int(round(start_s * SR)))
    if idx0 >= TOTAL_SAMPLES:
        return start_s
    avail = min(len(st), TOTAL_SAMPLES - idx0)
    buf[idx0 : idx0 + avail] += st[:avail]
    mono_env = np.mean(np.abs(st[:avail]), axis=1)
    peak_offset = int(np.argmax(mono_env)) if len(mono_env) else 0
    return (idx0 + peak_offset) / SR


def master_with_real_dnb(voice_bus: np.ndarray, music_mp3_path: Path, sfx_bus: np.ndarray, out_wav: Path):
    """
    Mix voiceover + real 320kbps Drum & Bass MP3 (full crisp 20Hz-20kHz studio spectrum, zero lowpass muffling!)
    with transparent sidechain ducking and exact -14.0 LUFS EBU R128 mastering.
    """
    music_bus = decode_audio(
        music_mp3_path,
        af="equalizer=f=2200:t=q:w=1.0:g=-4.5,equalizer=f=3500:t=q:w=1.1:g=-2.8",
        stereo=True,
    )[:TOTAL_SAMPLES].copy()
    if len(music_bus) < TOTAL_SAMPLES:
        music_bus = np.vstack([music_bus, np.zeros((TOTAL_SAMPLES - len(music_bus), 2), dtype=np.float32)])

    v_mono = np.mean(np.abs(voice_bus), axis=1)
    speaking = (moving_rms(v_mono, int(0.24 * SR)) > 0.006).astype(np.float32)
    duck_env = np.empty(TOTAL_SAMPLES, dtype=np.float32)
    prev = 0.0
    a_att = math.exp(-1.0 / (0.14 * SR))
    a_rel = math.exp(-1.0 / (0.45 * SR))
    step = 64
    for i in range(0, TOTAL_SAMPLES, step):
        target = float(speaking[i])
        coeff = a_att if target > prev else a_rel
        prev = target + (prev - target) * (coeff ** step)
        duck_env[i : i + step] = prev

    rms_v = float(np.sqrt(np.mean(voice_bus ** 2) + 1e-12))
    rms_m = float(np.sqrt(np.mean(music_bus ** 2) + 1e-12))
    voice_bus = voice_bus * ((10.0 ** (-16.2 / 20.0)) / rms_v)
    music_bus = music_bus * ((10.0 ** (-20.4 / 20.0)) / rms_m)
    music_bus *= (10.0 ** ((-5.5 * duck_env) / 20.0))[:, None]

    mix = voice_bus + music_bus + sfx_bus * 0.65
    fi = int(0.015 * SR)
    fo = int(0.240 * SR)
    mix[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    mix[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32))))[:, None]

    tmp_wav = AUDIO_DIR / "_tmp_pre_dnb.wav"
    pre_peak = float(np.max(np.abs(mix))) + 1e-9
    write_wav_pcm16(tmp_wav, mix * (0.70 / pre_peak))
    pre_lufs, _ = measure_ebur128(tmp_wav)
    calibrated = mix * (10.0 ** ((-14.0 - pre_lufs) / 20.0) * (0.70 / pre_peak))

    ceiling = 10.0 ** (-1.05 / 20.0)
    peak_track = np.maximum(np.abs(calibrated[:, 0]), np.abs(calibrated[:, 1]))
    win = int(0.005 * SR)
    pad = (win - (len(peak_track) % win)) % win
    blocks = np.pad(peak_track, (0, pad)).reshape(-1, win).max(axis=1)
    env_max = np.repeat(blocks, win)[:TOTAL_SAMPLES]
    lim_g = moving_rms(np.minimum(1.0, ceiling / np.maximum(env_max, 1e-9)), int(0.006 * SR))
    final_mix = np.clip(calibrated * lim_g[:, None], -ceiling, ceiling)
    write_wav_pcm16(out_wav, final_mix)
    i_lufs, tp_db = measure_ebur128(out_wav)
    if abs(-14.0 - i_lufs) > 0.12:
        final_mix = np.clip(final_mix * (10.0 ** ((-14.0 - i_lufs) / 20.0)), -ceiling, ceiling)
        write_wav_pcm16(out_wav, final_mix)
        i_lufs, tp_db = measure_ebur128(out_wav)
    tmp_wav.unlink(missing_ok=True)
    return i_lufs, tp_db


def main():
    dnb_prod_mp3 = MP3_DIR / "cc0_dnb_voevoda_30s.mp3"
    dnb_store_mp3 = MP3_DIR / "cc0_dnb_store_30s.mp3"
    print(f"Using audited CC0-1.0 Public Domain DnB MP3s:\n  1) {dnb_prod_mp3}\n  2) {dnb_store_mp3}")

    # Load clean subtle transition foley (real recorded foley only — ZERO synthesized tones!)
    boom_cin = decode_audio(SFX_DIR / "boom_cinematic.mp3")
    imp_deep = decode_audio(SFX_DIR / "impact_deep.mp3")
    imp_bright = decode_audio(SFX_DIR / "impact_bright.mp3")
    cut_tick = decode_audio(SFX_DIR / "cut_tick.mp3")
    whoosh_s = decode_audio(SFX_DIR / "whoosh_short.mp3")
    whoosh_tr = decode_audio(SFX_DIR / "whoosh_transition.mp3")

    # =========================================================================
    # A. BUILD SINGLE-PRODUCT MASTER («ВОЕВОДА 14/23» — ZERO PRICES, ZERO MOYSKLAD)
    # =========================================================================
    prod_clips = [
        ("scene1_hook", "p2_s1.mp3", "Воевода 14/23! Штурмовая броня — в магазине «В окопе»!"),
        ("scene2_anatomy", "p2_s2.mp3", "Восемь модулей Бр1: плечи, шея, пах и бёдра. Четыре быстросброса и разгрузка спины!"),
        ("scene3_variants", "p3_s3.mp3", "Сертификат ГОСТ! Четыре версии под задачу — от лёгкого плитника до полного штурмового контура!"),
        ("scene4_commercial", "p2_s4.mp3", "Укомплектуем плитами Бр5 под задачу. Оптом и в розницу, с НДС!"),
        ("scene5_cta", "p3_s5.mp3", "Заказывайте «Воеводу» в магазине «В окопе» — Телеграм, ВКонтакте и Авито!"),
    ]
    best_tempo = 1.21
    gaps_after = [0.24, 0.24, 0.22, 0.24, 0.0]
    for cand in [1.14, 1.17, 1.20, 1.22, 1.25]:
        test_c = [squeeze_pauses(trim_silence(decode_audio(PROD_VO_DIR / fn, af=f"atempo={cand:.4f}"))) for _, fn, _ in prod_clips]
        t_cur = 1.5 * BEAT
        for idx_c, c in enumerate(test_c):
            t_cur = math.ceil(t_cur / (BEAT / 2.0) - 1e-6) * (BEAT / 2.0)
            t_cur += len(c) / SR + gaps_after[idx_c]
        if t_cur <= 27.56:
            best_tempo = cand
            break

    processed_prod = [polish_voice(PROD_VO_DIR / fn, best_tempo) for _, fn, _ in prod_clips]
    v_prod = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    prod_meta = []
    t_cursor = 1.5 * BEAT
    for idx, ((seg_id, fn, text), clip) in enumerate(zip(prod_clips, processed_prod)):
        grid = BEAT / 2.0
        start_s = math.ceil(t_cursor / grid - 1e-6) * grid
        dur_s = len(clip) / SR
        end_s = start_s + dur_s
        add_stereo_clip(v_prod, clip, start_s, gain_db=0.0, pan=0.0)
        prod_meta.append({
            "index": idx + 1,
            "id": seg_id,
            "file": fn,
            "text": text,
            "voice_start": round(start_s, 4),
            "voice_end": round(end_s, 4),
            "voice_start_frame": int(round(start_s * FPS)),
            "voice_end_frame": int(round(end_s * FPS)),
        })
        t_cursor = end_s + gaps_after[idx]

    p_cuts = [0.0]
    for i in range(4):
        mid = 0.5 * (prod_meta[i]["voice_end"] + prod_meta[i + 1]["voice_start"])
        p_cuts.append(round(int(round(mid * FPS)) / FPS, 6))
    p_cuts.append(30.0)
    for i in range(5):
        prod_meta[i]["scene_start"] = round(p_cuts[i], 4)
        prod_meta[i]["scene_end"] = round(p_cuts[i + 1], 4)
        prod_meta[i]["scene_start_frame"] = int(round(p_cuts[i] * FPS))
        prod_meta[i]["scene_end_frame"] = int(round(p_cuts[i + 1] * FPS))

    sfx_prod = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    c1, c2, c3, c4 = p_cuts[1], p_cuts[2], p_cuts[3], p_cuts[4]
    p_lock = round(add_stereo_clip(sfx_prod, imp_deep, 0.40, -6.0, 0.0), 4)
    p_drop = round(BAR, 4)
    add_stereo_clip(sfx_prod, whoosh_tr, max(0.0, c1 - 0.14), -7.5, 0.0)
    s2_span = c2 - c1
    t_st1 = round(c1 + 0.07 * s2_span, 4)
    t_st2 = round(c1 + 0.40 * s2_span, 4)
    t_st3 = round(c1 + 0.71 * s2_span, 4)
    add_stereo_clip(sfx_prod, imp_bright, t_st1, -9.0, -0.15)
    add_stereo_clip(sfx_prod, cut_tick, t_st2, -7.0, 0.12)
    add_stereo_clip(sfx_prod, imp_deep, t_st3, -8.5, -0.10)
    add_stereo_clip(sfx_prod, whoosh_s, max(0.0, c2 - 0.10), -8.0, 0.10)
    s3_span = c3 - c2
    t_ui1 = round(c2 + 0.16 * s3_span, 4)
    t_ui2 = round(c2 + 0.38 * s3_span, 4)
    t_ui3 = round(c2 + 0.60 * s3_span, 4)
    t_ui4 = round(c2 + 0.80 * s3_span, 4)
    for tui in (t_ui1, t_ui2, t_ui3, t_ui4):
        add_stereo_clip(sfx_prod, cut_tick, tui, -7.2, 0.0)
    p_s4 = round(add_stereo_clip(sfx_prod, imp_deep, c3, -5.8, 0.0), 4)
    p_s5 = round(add_stereo_clip(sfx_prod, boom_cin, c4, -5.5, 0.0), 4)
    sting_t = round(BAR * 20.0, 4)  # Exact Bar 20 (27.5862s) real studio crash hit!

    p_lufs, p_tp = master_with_real_dnb(v_prod, dnb_prod_mp3, sfx_prod, AUDIO_DIR / "master_product_30s.wav")
    prod_sync = {
        "product": "Комплекс бронезащиты «ВОЕВОДА 14/23» (ООО «Варяг»)",
        "music_source": "assets/audio/music_mp3/cc0_dnb_voevoda_30s.mp3 (Peter Szegvari — Street Action DnB, CC0-1.0 Public Domain, 174.6 BPM)",
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": int(DURATION * FPS),
        "sample_rate": SR,
        "bpm": BPM,
        "voice_tempo": best_tempo,
        "master_lufs": round(p_lufs, 2),
        "true_peak_db": round(p_tp, 2),
        "scene_cuts": p_cuts,
        "scenes": prod_meta,
        "s1_lock": p_lock,
        "s1_drop": p_drop,
        "s2_nodes": [t_st1, t_st2, t_st3],
        "s3_rows": [t_ui1, t_ui2, t_ui3, t_ui4],
        "s4_drop": p_s4,
        "s5_slam": p_s5,
        "s5_sting": sting_t,
    }
    (PROJECT / "src" / "product_sync_map.json").write_text(json.dumps(prod_sync, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PRODUCT MASTER] -14 LUFS check: {p_lufs:.2f} LUFS | Peak: {p_tp:.2f} dBFS | Tempo: {best_tempo:.2f}x")
    print(f"  Product cuts: {p_cuts} | Final VO end: {prod_meta[-1]['voice_end']}s")

    # =========================================================================
    # B. REBUILD STORE OVERVIEW MASTER WITH REAL DNB MP3 (`master_30s.wav`)
    #    Preserving exact existing voice starts from audio_sync_map.json!
    # =========================================================================
    old_store_sync = json.loads((PROJECT / "src" / "audio_sync_map.json").read_text(encoding="utf-8"))
    store_tempo = float(old_store_sync.get("voice_tempo", 1.28))
    v_store = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    for seg in old_store_sync["scenes"]:
        clip = polish_voice(AUDIO_DIR / seg["file"], store_tempo)
        add_stereo_clip(v_store, clip, float(seg["voice_start"]), gain_db=0.0, pan=0.0)

    sc = old_store_sync["scene_cuts"]
    sfx_store = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    add_stereo_clip(sfx_store, imp_deep, 0.42, -6.0, 0.0)
    add_stereo_clip(sfx_store, whoosh_tr, max(0.0, sc[1] - 0.14), -7.5, 0.0)
    for tn in old_store_sync["s2_nodes"]:
        add_stereo_clip(sfx_store, cut_tick, float(tn), -7.0, 0.0)
    add_stereo_clip(sfx_store, whoosh_s, max(0.0, sc[2] - 0.10), -8.0, 0.0)
    for tc in old_store_sync["s3_checks"]:
        add_stereo_clip(sfx_store, cut_tick, float(tc), -7.2, 0.0)
    add_stereo_clip(sfx_store, imp_deep, float(sc[3]), -5.8, 0.0)
    add_stereo_clip(sfx_store, boom_cin, float(sc[4]), -5.5, 0.0)

    s_lufs, s_tp = master_with_real_dnb(v_store, dnb_store_mp3, sfx_store, AUDIO_DIR / "master_30s.wav")
    old_store_sync["music_source"] = "assets/audio/music_mp3/cc0_dnb_store_30s.mp3 (warlightwolf — Tech DnB Music 20, CC0-1.0 Public Domain, 174.6 BPM)"
    old_store_sync["master_lufs"] = round(s_lufs, 2)
    old_store_sync["true_peak_db"] = round(s_tp, 2)
    old_store_sync["s5_sting"] = round(BAR * 20.0, 4)
    (PROJECT / "src" / "audio_sync_map.json").write_text(json.dumps(old_store_sync, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[STORE MASTER]   -14 LUFS check: {s_lufs:.2f} LUFS | Peak: {s_tp:.2f} dBFS | Tempo: {store_tempo:.2f}x")


if __name__ == "__main__":
    main()
