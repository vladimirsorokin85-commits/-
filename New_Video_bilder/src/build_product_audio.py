#!/usr/bin/env python3
"""
Sample-accurate 30.000s (48 kHz stereo = 1,440,000 samples = 1800 frames @ 60 fps)
master audio builder for the Single-Product Flagship Reel:
Комплекс бронезащиты «ВОЕВОДА 14/23» (ООО «Варяг») — «В ОКОПЕ · магазин брони».
Uses pure numpy + native FFmpeg DSP filters & EBU R128 / ITU-R BS.1770-4 true-peak metering.
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
SFX_DIR = STUDIO / "toolkit" / "sfx"
SAMPLES_DIR = STUDIO / "reel" / "samples"
MUSIC_DIR = STUDIO / "music_catalog"

SR = 48000
FPS = 60
DURATION = 30.0
TOTAL_SAMPLES = int(round(DURATION * SR))  # 1,440,000 exact stereo samples
BPM = 174.0
BEAT = 60.0 / BPM          # 0.344827586 s
BAR = BEAT * 4.0           # 1.379310345 s


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


def measure_ebur128(wav_path: Path):
    res = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(wav_path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, check=True
    )
    txt = res.stderr
    m_i = re.findall(r"I:\s*([-\d.]+)\s*LUFS", txt)
    m_tp = re.findall(r"Peak:\s*([-\d.]+)\s*dBFS", txt)
    i_lufs = float(m_i[-1])
    tp_db = float(m_tp[-1])
    return i_lufs, tp_db


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
    af = f"atempo={tempo:.4f},highpass=f=85,equalizer=f=3400:t=q:w=1.1:g=2.8"
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


def synth_radar_ping(freq0=1280.0, dur=0.20) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False, dtype=np.float32)
    env = np.exp(-t * 14.0) * np.minimum(1.0, t / 0.004)
    sig = 0.65 * np.sin(2 * np.pi * freq0 * t) + 0.35 * np.sin(2 * np.pi * freq0 * 1.5 * t)
    return (sig * env * 0.5).astype(np.float32)


def synth_confirm_chord(dur=0.34) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False, dtype=np.float32)
    n1 = np.sin(2 * np.pi * 587.33 * t) * np.exp(-t * 9.0)
    n2 = np.sin(2 * np.pi * 880.00 * np.maximum(0.0, t - 0.045)) * np.exp(-np.maximum(0.0, t - 0.045) * 8.0) * (t >= 0.045)
    n3 = np.sin(2 * np.pi * 1174.66 * np.maximum(0.0, t - 0.09)) * np.exp(-np.maximum(0.0, t - 0.09) * 7.5) * (t >= 0.09)
    fade = np.minimum(1.0, t / 0.005)
    return ((0.42 * n1 + 0.36 * n2 + 0.28 * n3) * fade * 0.45).astype(np.float32)


def main():
    clip_files = [
        ("scene1_hook", "p2_s1.mp3", "Воевода 14/23! Штурмовая броня — в магазине «В окопе»!"),
        ("scene2_anatomy", "p2_s2.mp3", "Восемь модулей Бр1: плечи, шея, пах и бёдра. Четыре быстросброса и разгрузка спины!"),
        ("scene3_catalog_matrix", "p2_s3.mp3", "Сертификат ГОСТ. Все версии в каталоге — от плитника до комплектации «Штурм»!"),
        ("scene4_commercial", "p2_s4.mp3", "Укомплектуем плитами Бр5 под задачу. Оптом и в розницу, с НДС!"),
        ("scene5_cta", "p2_s5.mp3", "Заказывайте «Воеводу» в онлайн-каталоге и Телеграм «В окопе»!"),
    ]

    best_tempo = 1.15
    for cand in [1.05, 1.08, 1.12, 1.15, 1.18, 1.22]:
        test_clips = [squeeze_pauses(trim_silence(decode_audio(PROD_VO_DIR / fn, af=f"atempo={cand:.4f}"))) for _, fn, _ in clip_files]
        t_cur = 1.5 * BEAT
        for c in test_clips:
            t_cur = math.ceil(t_cur / (BEAT / 2.0) - 1e-6) * (BEAT / 2.0)
            t_cur += len(c) / SR + 0.28
        end_v = t_cur - 0.28
        print(f"Candidate tempo {cand:.2f}x -> voice ends at {end_v:.3f}s")
        if end_v <= 28.25:
            best_tempo = cand
            break

    print(f"Selected natural unhurried baritone tempo: {best_tempo:.2f}x")
    processed = [polish_voice(PROD_VO_DIR / fn, best_tempo) for _, fn, _ in clip_files]

    voice_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    segments_meta = []
    t_cursor = 1.5 * BEAT  # 0.5172s
    gaps_after = [0.28, 0.28, 0.26, 0.28, 0.0]

    for idx, ((seg_id, fn, text), clip) in enumerate(zip(clip_files, processed)):
        grid = BEAT / 2.0
        start_s = math.ceil(t_cursor / grid - 1e-6) * grid
        dur_s = len(clip) / SR
        end_s = start_s + dur_s
        add_stereo_clip(voice_bus, clip, start_s, gain_db=0.0, pan=0.0)
        segments_meta.append({
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

    scene_cuts = [0.0]
    for i in range(4):
        mid = 0.5 * (segments_meta[i]["voice_end"] + segments_meta[i + 1]["voice_start"])
        scene_cuts.append(round(int(round(mid * FPS)) / FPS, 6))
    scene_cuts.append(30.0)
    for i in range(5):
        segments_meta[i]["scene_start"] = round(scene_cuts[i], 4)
        segments_meta[i]["scene_end"] = round(scene_cuts[i + 1], 4)
        segments_meta[i]["scene_start_frame"] = int(round(scene_cuts[i] * FPS))
        segments_meta[i]["scene_end_frame"] = int(round(scene_cuts[i + 1] * FPS))

    # Music bed with native FFmpeg EQ vocal carve + lowpass intro/bridge!
    dnb_full = decode_audio(MUSIC_DIR / "dnb_neuro_174.ogg", af="equalizer=f=2100:t=q:w=0.9:g=-5.0", stereo=True)
    dnb_low = decode_audio(MUSIC_DIR / "dnb_neuro_174.ogg", af="lowpass=f=620", stereo=True)
    dnb_mid = decode_audio(MUSIC_DIR / "dnb_neuro_174.ogg", af="lowpass=f=2400,equalizer=f=2000:t=q:w=1.0:g=-5.0", stereo=True)
    jng_full = decode_audio(MUSIC_DIR / "jungle_hoover_174.ogg", af="equalizer=f=2100:t=q:w=0.9:g=-5.0", stereo=True)

    def tile_to(arr):
        while len(arr) < TOTAL_SAMPLES + SR:
            arr = np.vstack([arr, arr])
        return arr[:TOTAL_SAMPLES].copy()

    dnb_full, dnb_low, dnb_mid, jng_full = map(tile_to, [dnb_full, dnb_low, dnb_mid, jng_full])
    t_axis = np.arange(TOTAL_SAMPLES, dtype=np.float32) / SR
    c1, c2, c3, c4 = scene_cuts[1], scene_cuts[2], scene_cuts[3], scene_cuts[4]

    def smooth_gate(t_arr, a, b, ramp=0.14):
        up = np.clip((t_arr - (a - ramp / 2)) / ramp, 0.0, 1.0)
        dn = 1.0 - np.clip((t_arr - (b - ramp / 2)) / ramp, 0.0, 1.0)
        return (up * dn)[:, None]

    music_bus = (
        dnb_low * smooth_gate(t_axis, -1.0, BAR) * 0.95
        + dnb_full * smooth_gate(t_axis, BAR, c2) * 1.02
        + dnb_mid * smooth_gate(t_axis, c2, c3) * 0.88
        + (0.74 * dnb_full + 0.50 * jng_full) * smooth_gate(t_axis, c3, 31.0) * 1.05
    ).astype(np.float32)

    sfx_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    boom_cin = decode_audio(SFX_DIR / "boom_cinematic.mp3")
    imp_deep = decode_audio(SFX_DIR / "impact_deep.mp3")
    imp_bright = decode_audio(SFX_DIR / "impact_bright.mp3")
    riser = decode_audio(SFX_DIR / "riser_tension.mp3")
    cut_tick = decode_audio(SFX_DIR / "cut_tick.mp3")
    whoosh_s = decode_audio(SFX_DIR / "whoosh_short.mp3")
    whoosh_tr = decode_audio(SFX_DIR / "whoosh_transition.mp3")
    logo_sting = decode_audio(SFX_DIR / "logo_sting.mp3")
    splash_hd = decode_audio(SAMPLES_DIR / "drum_splash_hard.flac")
    radar_ping = synth_radar_ping(1320.0, 0.20)
    confirm_chime = synth_confirm_chord(0.34)

    sync_events = []
    def add_event(name, clip, target_s, gain_db, pan=0.0):
        peak_s = add_stereo_clip(sfx_bus, clip, target_s, gain_db=gain_db, pan=pan)
        sync_events.append({"event": name, "start_s": round(target_s, 4), "peak_s": round(peak_s, 4)})
        return round(peak_s, 4)

    add_event("s1_radar_ping", radar_ping, 0.08, -7.0, -0.15)
    p_lock = add_event("s1_lock_impact", imp_deep, 0.40, -4.2, 0.0)
    p_drop = add_event("s1_bar1_drop", splash_hd, BAR, -9.2, 0.1)

    add_event("cut_s1_to_s2", whoosh_tr, max(0.0, c1 - 0.14), -6.5, 0.0)
    s2_span = c2 - c1
    t_st1 = round(c1 + 0.07 * s2_span, 4)
    t_st2 = round(c1 + 0.40 * s2_span, 4)
    t_st3 = round(c1 + 0.71 * s2_span, 4)
    add_event("s2_mod1_shoulder", imp_bright, t_st1, -8.2, -0.18)
    add_event("s2_mod2_groin", cut_tick, t_st2, -5.8, 0.15)
    add_event("s2_mod3_belt_br5", imp_deep, t_st3, -7.5, -0.10)

    add_event("cut_s2_to_s3", whoosh_s, max(0.0, c2 - 0.10), -7.2, 0.12)
    s3_span = c3 - c2
    t_ui1 = round(c2 + 0.16 * s3_span, 4)
    t_ui2 = round(c2 + 0.38 * s3_span, 4)
    t_ui3 = round(c2 + 0.60 * s3_span, 4)
    t_ui4 = round(c2 + 0.80 * s3_span, 4)
    add_event("s3_sku1", cut_tick, t_ui1, -6.0, -0.12)
    add_event("s3_sku2", cut_tick, t_ui2, -5.8, 0.0)
    add_event("s3_sku3_shturm", confirm_chime, t_ui3, -6.2, 0.10)
    add_event("s3_sku4_bmdsh", cut_tick, t_ui4, -5.8, 0.15)

    p_s4 = add_event("cut_s3_to_s4_drop", imp_deep, c3, -4.5, 0.0)
    riser_peak_idx = int(np.argmax(np.abs(riser)))
    riser_tr = riser[: riser_peak_idx + int(0.08 * SR)].copy()
    rfade = min(int(0.06 * SR), len(riser_tr) // 4)
    riser_tr[-rfade:] *= np.linspace(1.0, 0.0, rfade, dtype=np.float32)
    add_event("s4_to_s5_riser", riser_tr, max(c3 + 0.15, c4 - riser_peak_idx / SR), -8.5, 0.0)

    p_s5 = add_event("cut_s4_to_s5_slam", boom_cin, c4, -4.0, 0.0)
    add_event("s5_latch_click", cut_tick, c4 + 0.03, -4.5, 0.08)
    sting_t = round(min(28.35, segments_meta[4]["voice_end"] + 0.14), 4)
    add_event("s5_brand_sting", logo_sting, sting_t, -8.2, 0.0)

    # Smooth sidechain ducking of music under speech
    v_mono = np.mean(np.abs(voice_bus), axis=1)
    speaking = (moving_rms(v_mono, int(0.18 * SR)) > 0.008).astype(np.float32)
    duck_env = np.empty(TOTAL_SAMPLES, dtype=np.float32)
    prev = 0.0
    a_att = math.exp(-1.0 / (0.20 * SR))
    a_rel = math.exp(-1.0 / (0.65 * SR))
    step = 64
    for i in range(0, TOTAL_SAMPLES, step):
        target = float(speaking[i])
        coeff = a_att if target > prev else a_rel
        prev = target + (prev - target) * (coeff ** step)
        duck_env[i : i + step] = prev

    rms_v = float(np.sqrt(np.mean(voice_bus ** 2) + 1e-12))
    rms_m = float(np.sqrt(np.mean(music_bus ** 2) + 1e-12))
    voice_bus *= (10.0 ** (-16.2 / 20.0)) / rms_v
    music_bus *= (10.0 ** (-22.6 / 20.0)) / rms_m
    music_bus *= (10.0 ** ((-5.2 * duck_env) / 20.0))[:, None]

    mix = voice_bus + music_bus + sfx_bus * 0.85
    fi = int(0.020 * SR)
    fo = int(0.220 * SR)
    mix[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    mix[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32))))[:, None]

    # Exact EBU R128 two-pass calibration to -14.0 LUFS & -1.05 dBFS true-peak ceiling!
    out_wav = AUDIO_DIR / "master_product_30s.wav"
    tmp_wav = AUDIO_DIR / "_tmp_pre.wav"
    pre_peak = float(np.max(np.abs(mix))) + 1e-9
    write_wav_pcm16(tmp_wav, mix * (0.70 / pre_peak))
    pre_lufs, _ = measure_ebur128(tmp_wav)
    gain_to_14 = 10.0 ** ((-14.0 - pre_lufs) / 20.0) * (0.70 / pre_peak)
    calibrated = mix * gain_to_14

    # Soft transparent brickwall lookahead limiter at -1.1 dBFS + fine LUFS trim
    ceiling = 10.0 ** (-1.15 / 20.0)
    peak_track = np.maximum(np.abs(calibrated[:, 0]), np.abs(calibrated[:, 1]))
    # 5ms box window max envelope
    win = int(0.005 * SR)
    pad = (win - (len(peak_track) % win)) % win
    blocks = np.pad(peak_track, (0, pad)).reshape(-1, win).max(axis=1)
    env_max = np.repeat(blocks, win)[:TOTAL_SAMPLES]
    lim_g = moving_rms(np.minimum(1.0, ceiling / np.maximum(env_max, 1e-9)), int(0.006 * SR))
    final_mix = np.clip(calibrated * lim_g[:, None], -ceiling, ceiling)
    write_wav_pcm16(out_wav, final_mix)
    i_lufs, tp_db = measure_ebur128(out_wav)
    # 2nd micro-trim if limiter nudged LUFS by 0.2-0.4 dB
    if abs(-14.0 - i_lufs) > 0.15:
        final_mix = np.clip(final_mix * (10.0 ** ((-14.0 - i_lufs) / 20.0)), -ceiling, ceiling)
        write_wav_pcm16(out_wav, final_mix)
        i_lufs, tp_db = measure_ebur128(out_wav)
    tmp_wav.unlink(missing_ok=True)

    sync_data = {
        "product": "Комплекс бронезащиты «ВОЕВОДА 14/23» (ООО «Варяг»)",
        "catalog_url": "https://wduxqtygsunz.moysklad.shop/catalog",
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": int(DURATION * FPS),
        "sample_rate": SR,
        "bpm": BPM,
        "voice_tempo": best_tempo,
        "master_lufs": round(i_lufs, 2),
        "true_peak_db": round(tp_db, 2),
        "scene_cuts": scene_cuts,
        "scenes": segments_meta,
        "s1_lock": p_lock,
        "s1_drop": p_drop,
        "s2_nodes": [t_st1, t_st2, t_st3],
        "s3_rows": [t_ui1, t_ui2, t_ui3, t_ui4],
        "s4_drop": p_s4,
        "s5_slam": p_s5,
        "s5_sting": sting_t,
    }
    sync_path = PROJECT / "src" / "product_sync_map.json"
    sync_path.write_text(json.dumps(sync_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MASTER PRODUCT WAV WRITTEN: {out_wav} ({len(final_mix)} samples = {len(final_mix)/SR:.6f}s)")
    print(f"EBU R128 Verified -> Loudness: {i_lufs:.2f} LUFS | Peak: {tp_db:.2f} dBFS")
    print(json.dumps(sync_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
