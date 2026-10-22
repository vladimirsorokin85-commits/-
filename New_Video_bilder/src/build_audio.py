#!/usr/bin/env python3
"""
Sample-accurate 30.000s (48 kHz stereo = 1,440,000 samples = 1800 frames @ 60 fps)
master audio builder for «В окопе» Reels in New_Video_bilder.
"""
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfilt

PROJECT = Path("/home/user/-/New_Video_bilder")
STUDIO = Path("/home/user/-/video_studio")
AUDIO_DIR = PROJECT / "assets" / "audio"
SFX_DIR = STUDIO / "toolkit" / "sfx"
SAMPLES_DIR = STUDIO / "reel" / "samples"
MUSIC_DIR = STUDIO / "music_catalog"

SR = 48000
FPS = 60
DURATION = 30.0
TOTAL_SAMPLES = int(round(DURATION * SR))  # 1,440,000 exact samples (800 samples / frame)
BPM = 174.0
BEAT = 60.0 / BPM          # 0.344827586 s
BAR = BEAT * 4.0           # 1.379310345 s


def decode_audio(path: Path, tempo: float = 1.0, stereo: bool = False) -> np.ndarray:
    ch = 2 if stereo else 1
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", str(ch), "-ar", str(SR)]
    if abs(tempo - 1.0) > 1e-4:
        cmd += ["-af", f"atempo={tempo:.4f}"]
    cmd += ["-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, dtype=np.float32).copy()
    if stereo:
        return arr.reshape(-1, 2)
    return arr


def trim_silence(x: np.ndarray, thr: float = 0.014, pad_in: float = 0.025, pad_out: float = 0.065) -> np.ndarray:
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, int(idx[0] - pad_in * SR))
    b = min(len(x), int(idx[-1] + pad_out * SR))
    out = x[a:b].copy()
    fade_in = min(int(0.012 * SR), len(out) // 4)
    fade_out = min(int(0.030 * SR), len(out) // 4)
    if fade_in > 0:
        out[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    if fade_out > 0:
        out[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)
    return out


def squeeze_pauses(x: np.ndarray, max_pause: float = 0.17, thr_db: float = -39.0) -> np.ndarray:
    w = int(0.02 * SR)
    n = len(x) // w
    if n < 4:
        return x
    rms = np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms)
    quiet = db < thr_db
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


def polish_voice(x: np.ndarray, meter: pyln.Meter, target_lufs: float = -16.0) -> np.ndarray:
    hp = butter(2, 85.0, btype="highpass", fs=SR, output="sos")
    y = sosfilt(hp, x).astype(np.float32)
    bp = butter(2, [2400.0, 5600.0], btype="bandpass", fs=SR, output="sos")
    presence = sosfilt(bp, y).astype(np.float32)
    y = y + 0.28 * presence
    env = np.sqrt(uniform_filter1d(y ** 2, int(0.14 * SR)) + 1e-8)
    med = np.percentile(env[env > 0.01], 60)
    gain = np.clip((med / np.maximum(env, med * 0.28)) ** 0.30, 0.65, 1.65)
    gain = uniform_filter1d(gain, int(0.04 * SR))
    y = y * gain
    loud = meter.integrated_loudness(y.astype(np.float64))
    y = y * (10.0 ** ((target_lufs - loud) / 20.0))
    return y.astype(np.float32)


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


def synth_radar_ping(freq0=1320.0, dur=0.22) -> np.ndarray:
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
    meter = pyln.Meter(SR)

    clip_files = [
        ("scene1_hook", "s1_hook.mp3", "Когда небо решает всё — нужна заводская техника, проверенная делом!"),
        ("scene2_catalog", "s2_catalog_tight.mp3", "В магазине «В окопе» — огромный выбор от заводов: РЭБ Капюшон, Скания, Зонт и Ромашка, детекторы Булат и Алдан, Мавики, рации и питание!"),
        ("scene3_personal", "s3_personal_tight.mp3", "Личный подход к каждому: разберём вашу задачу и согласуем с поставщиком нужные частоты и прошивку!"),
        ("scene4_wholesale", "s4_wholesale_tight.mp3", "От одного комплекта до крупной партии — оптом и в розницу, с НДС и без!"),
        ("scene5_cta", "s5_cta.mp3", "Магазин «В окопе»! Переходите в наш Телеграм, ВКонтакте или на Авито!"),
    ]

    best_tempo = 1.30
    for cand_tempo in [1.20, 1.24, 1.28, 1.31, 1.34]:
        test_clips = [squeeze_pauses(trim_silence(decode_audio(AUDIO_DIR / fn, tempo=cand_tempo))) for _, fn, _ in clip_files]
        t_cur = 1.5 * BEAT  # 0.517s opening radar lock impact before voice
        for c in test_clips:
            t_cur = math.ceil(t_cur / (BEAT / 2.0) - 1e-6) * (BEAT / 2.0)
            t_cur += len(c) / SR + 0.19
        end_voice = t_cur - 0.19
        print(f"Candidate tempo {cand_tempo:.2f}x -> voice ends at {end_voice:.3f}s")
        if end_voice <= 28.45:
            best_tempo = cand_tempo
            break

    print(f"Selected natural crisp voice tempo: {best_tempo:.2f}x")
    processed_clips = [
        polish_voice(squeeze_pauses(trim_silence(decode_audio(AUDIO_DIR / fn, tempo=best_tempo))), meter, target_lufs=-16.0)
        for _, fn, _ in clip_files
    ]

    voice_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    segments_meta = []
    t_cursor = 1.5 * BEAT  # 0.5172s (Frame 31)
    gaps_after = [0.20, 0.22, 0.20, 0.22, 0.0]

    for idx, ((seg_id, fn, text), clip) in enumerate(zip(clip_files, processed_clips)):
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
        cut_frame = int(round(mid * FPS))
        scene_cuts.append(round(cut_frame / FPS, 6))
    scene_cuts.append(30.0)

    for i in range(5):
        segments_meta[i]["scene_start"] = round(scene_cuts[i], 4)
        segments_meta[i]["scene_end"] = round(scene_cuts[i + 1], 4)
        segments_meta[i]["scene_start_frame"] = int(round(scene_cuts[i] * FPS))
        segments_meta[i]["scene_end_frame"] = int(round(scene_cuts[i + 1] * FPS))

    dnb = decode_audio(MUSIC_DIR / "dnb_neuro_174.ogg", stereo=True)
    jng = decode_audio(MUSIC_DIR / "jungle_hoover_174.ogg", stereo=True)
    while len(dnb) < TOTAL_SAMPLES + SR:
        dnb = np.vstack([dnb, dnb])
    while len(jng) < TOTAL_SAMPLES + SR:
        jng = np.vstack([jng, jng])
    dnb = dnb[:TOTAL_SAMPLES].copy()
    jng = jng[:TOTAL_SAMPLES].copy()

    lp_intro = butter(3, 620.0, btype="lowpass", fs=SR, output="sos")
    lp_bridge = butter(2, 2400.0, btype="lowpass", fs=SR, output="sos")
    dnb_low = np.column_stack([sosfilt(lp_intro, dnb[:, 0]), sosfilt(lp_intro, dnb[:, 1])]).astype(np.float32)
    dnb_mid = np.column_stack([sosfilt(lp_bridge, dnb[:, 0]), sosfilt(lp_bridge, dnb[:, 1])]).astype(np.float32)

    t_axis = np.arange(TOTAL_SAMPLES, dtype=np.float32) / SR
    c1, c2, c3, c4 = scene_cuts[1], scene_cuts[2], scene_cuts[3], scene_cuts[4]

    def smooth_gate(t_arr, a, b, ramp=0.14):
        up = np.clip((t_arr - (a - ramp / 2)) / ramp, 0.0, 1.0)
        dn = 1.0 - np.clip((t_arr - (b - ramp / 2)) / ramp, 0.0, 1.0)
        return (up * dn)[:, None]

    w_intro = smooth_gate(t_axis, -1.0, BAR)
    w_s1_drop = smooth_gate(t_axis, BAR, c2)
    w_s3 = smooth_gate(t_axis, c2, c3)
    w_climax = smooth_gate(t_axis, c3, 31.0)

    music_bus = (
        dnb_low * w_intro * 0.95
        + dnb * w_s1_drop * 1.00
        + dnb_mid * w_s3 * 0.88
        + (0.72 * dnb + 0.52 * jng) * w_climax * 1.06
    ).astype(np.float32)

    vocal_carve_sos = butter(2, [850.0, 3800.0], btype="bandpass", fs=SR, output="sos")
    for ch in range(2):
        carved = sosfilt(vocal_carve_sos, music_bus[:, ch]).astype(np.float32)
        music_bus[:, ch] -= 0.46 * carved

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
    radar_ping = synth_radar_ping(1360.0, 0.20)
    confirm_chime = synth_confirm_chord(0.34)

    sync_events = []

    def add_event(name: str, clip: np.ndarray, target_s: float, gain_db: float, pan: float = 0.0, role: str = ""):
        peak_s = add_stereo_clip(sfx_bus, clip, target_s, gain_db=gain_db, pan=pan)
        sync_events.append({
            "event": name,
            "role": role,
            "start_s": round(target_s, 4),
            "peak_s": round(peak_s, 4),
            "target_frame": int(round(target_s * FPS)),
            "peak_frame": int(round(peak_s * FPS)),
        })

    add_event("s1_radar_ping", radar_ping, 0.08, -7.0, -0.15, "Всплеск радиоспектра на старте")
    add_event("s1_lock_impact", imp_deep, 0.40, -4.5, 0.0, "Захват цели пеленгом 360° + удар титра")
    add_event("s1_bar1_drop", splash_hd, BAR, -9.5, 0.1, "Вступление основного ритма 174 BPM")

    add_event("cut_s1_to_s2", whoosh_tr, max(0.0, c1 - 0.14), -6.5, 0.0, "Пролёт в 3D-шину заводского выбора")
    s2_span = c2 - c1
    t_st1 = round(c1 + 0.08 * s2_span, 4)
    t_st2 = round(c1 + 0.44 * s2_span, 4)
    t_st3 = round(c1 + 0.74 * s2_span, 4)
    add_event("s2_node1_reb", imp_bright, t_st1, -8.5, -0.2, "Фокус узла 1: РЭБ Капюшон / Скания / Зонт / Ромашка")
    add_event("s2_node2_det", radar_ping, t_st2, -8.5, 0.18, "Фокус узла 2: Детекторы Булат V4 / Алдан-8/12")
    add_event("s2_node3_comms_fpv", cut_tick, t_st3, -6.5, -0.1, "Фокус узла 3: Mavic / Рации / Питание")

    add_event("cut_s2_to_s3", whoosh_s, max(0.0, c2 - 0.10), -7.5, 0.12, "Переход к карте согласования с заводом")
    s3_span = c3 - c2
    t_ui1 = round(c2 + 0.22 * s3_span, 4)
    t_ui2 = round(c2 + 0.50 * s3_span, 4)
    t_ui3 = round(c2 + 0.76 * s3_span, 4)
    add_event("s3_check1_task", cut_tick, t_ui1, -6.0, -0.12, "Пункт 1: Разбор задачи и типа транспорта/позиции")
    add_event("s3_check2_freq", cut_tick, t_ui2, -5.5, 0.0, "Пункт 2: Согласование рабочих частот с поставщиком")
    add_event("s3_check3_firmware_ok", confirm_chime, t_ui3, -6.5, 0.12, "Пункт 3: Нужная заводская прошивка и комплектация ✓")

    add_event("cut_s3_to_s4_case_drop", imp_deep, c3, -4.5, 0.0, "Посадка комплекта в защитный кейс + раскрытие склада")
    riser_peak_idx = int(np.argmax(np.abs(riser)))
    riser_trimmed = riser[: riser_peak_idx + int(0.08 * SR)].copy()
    rfade = min(int(0.06 * SR), len(riser_trimmed) // 4)
    riser_trimmed[-rfade:] *= np.linspace(1.0, 0.0, rfade, dtype=np.float32)
    add_event("s4_to_s5_riser", riser_trimmed, max(c3 + 0.15, c4 - riser_peak_idx / SR), -8.5, 0.0, "Нарастание точно в защёлку кейса")

    add_event("cut_s4_to_s5_latch_slam", boom_cin, c4, -4.0, 0.0, "Финальная защёлка кейса и раскрытие «В ОКОПЕ» + CTA")
    add_event("s5_latch_click", cut_tick, c4 + 0.03, -4.5, 0.08, "Металлический щелчок замков кейса")
    add_event("s5_brand_sting", logo_sting, min(28.2, segments_meta[4]["voice_end"] + 0.12), -8.5, 0.0, "Финальный фирменный акцент после речи диктора")

    v_mono = np.mean(np.abs(voice_bus), axis=1)
    speaking = (uniform_filter1d(v_mono, int(0.18 * SR)) > 0.008).astype(np.float32)
    duck_env = np.empty(TOTAL_SAMPLES, dtype=np.float32)
    prev = 0.0
    a_att = math.exp(-1.0 / (0.22 * SR))
    a_rel = math.exp(-1.0 / (0.68 * SR))
    step = 64
    for i in range(0, TOTAL_SAMPLES, step):
        target = float(speaking[i])
        coeff = a_att if target > prev else a_rel
        prev = target + (prev - target) * (coeff ** step)
        duck_env[i : i + step] = prev

    lv = meter.integrated_loudness(voice_bus.astype(np.float64))
    lm = meter.integrated_loudness(music_bus.astype(np.float64))
    voice_bus *= 10.0 ** ((-15.5 - lv) / 20.0)
    music_bus *= 10.0 ** ((-21.8 - lm) / 20.0)
    music_bus *= (10.0 ** ((-5.2 * duck_env) / 20.0))[:, None]

    mix = voice_bus + music_bus + sfx_bus * 0.85

    fi = int(0.020 * SR)
    fo = int(0.220 * SR)
    mix[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    cos_out = 0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32)))
    mix[-fo:] *= cos_out[:, None]

    l_mix = meter.integrated_loudness(mix.astype(np.float64))
    mix *= 10.0 ** ((-14.0 - l_mix) / 20.0)
    tp_ceiling = 10.0 ** (-1.05 / 20.0)
    peak_env = np.maximum(
        maximum_filter1d(np.abs(mix[:, 0]), int(0.005 * SR)),
        maximum_filter1d(np.abs(mix[:, 1]), int(0.005 * SR)),
    )
    lim_gain = np.minimum(1.0, tp_ceiling / np.maximum(peak_env, 1e-9))
    lim_gain = uniform_filter1d(lim_gain, int(0.005 * SR))
    mix = np.clip(mix * lim_gain[:, None], -tp_ceiling, tp_ceiling)

    final_lufs = meter.integrated_loudness(mix.astype(np.float64))
    final_peak_db = 20.0 * math.log10(float(np.max(np.abs(mix))) + 1e-12)

    out_wav = AUDIO_DIR / "master_30s.wav"
    sf.write(str(out_wav), mix, SR, subtype="PCM_16")

    sync_data = {
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": int(DURATION * FPS),
        "sample_rate": SR,
        "bpm": BPM,
        "beat_seconds": round(BEAT, 6),
        "voice_tempo": best_tempo,
        "master_lufs": round(final_lufs, 2),
        "true_peak_db": round(final_peak_db, 2),
        "scene_cuts": scene_cuts,
        "scenes": segments_meta,
        "s2_nodes": [t_st1, t_st2, t_st3],
        "s3_checks": [t_ui1, t_ui2, t_ui3],
        "sync_events": sync_events,
    }
    sync_path = PROJECT / "src" / "audio_sync_map.json"
    sync_path.write_text(json.dumps(sync_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MASTER WAV WRITTEN: {out_wav} ({len(mix)} samples = {len(mix)/SR:.6f}s)")
    print(f"Loudness: {final_lufs:.2f} LUFS | Peak: {final_peak_db:.2f} dBFS")
    print(json.dumps(sync_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
