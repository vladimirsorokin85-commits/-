#!/usr/bin/env python3
"""
Sample-accurate 30.000s (48 kHz stereo = 1,440,000 samples = 1800 frames @ 60 fps)
master audio builder for the Power Stations Commercial («Зарядные станции — В ОКОПЕ»):
- Uses 100% CC0-1.0 Public Domain real studio Drum & Bass MP3 (`assets/audio/music_mp3/cc0_dnb_power_30s.mp3`)
  from warlightwolf — Tech DnB Music 21 (https://freesound.org/people/warlightwolf/sounds/612138/, 0.00% vocals, ZERO Content ID).
- Voices: `voice-05` (`pwr_s1..pwr_s5.mp3`), zero prices, zero internal links.
- Masters to exact -14.0 LUFS / <= -0.8 dBFS True Peak.
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
VO_DIR = AUDIO_DIR / "power_vo"
MP3_DIR = AUDIO_DIR / "music_mp3"
SFX_DIR = STUDIO / "toolkit" / "sfx"

SR = 48000
FPS = 60
DURATION = 30.0
TOTAL_SAMPLES = int(round(DURATION * SR))  # 1,440,000 exact stereo samples
BPM = 175.0
BEAT = 60.0 / BPM          # 0.3428571429 s
BAR = BEAT * 4.0           # 1.3714285714 s


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


def export_mp3_320(arr: np.ndarray, mp3_path: Path):
    tmp = mp3_path.with_suffix(".tmp.wav")
    write_wav_pcm16(tmp, arr)
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
    xf = int(round(xfade_ms * 0.001 * SR))
    out = parts[0].copy()
    for nxt in parts[1:]:
        a, tail = out[:-xf], out[-xf:]
        head, rest = nxt[:xf], nxt[xf:]
        theta = np.linspace(0.0, math.pi * 0.5, xf, dtype=np.float32)[:, None]
        out = np.vstack([a, tail * np.cos(theta) + head * np.sin(theta), rest])
    return out


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


def main():
    fi, fo = int(0.015 * SR), int(0.350 * SR)
    dnb_power_mp3 = MP3_DIR / "cc0_dnb_power_30s.mp3"
    print(f"Using audited CC0-1.0 Public Domain DnB MP3 -> {dnb_power_mp3}")

    # 2. Arrange `voice-05` narration clips (`pwr_s1..pwr_s5.mp3`) on half-beat grid finishing cleanly before 27.42s crash!
    clips_cfg = [
        ("scene1_hook", "pwr_s1.mp3", "Когда позиции нужна тишина — работают зарядные станции из магазина «В окопе»!"),
        ("scene2_brands", "pwr2_s2.mp3", "В наличии вся линейка: DJI для дронов, мощные EcoFlow, неубиваемые Jackery и Bluetti!"),
        ("scene3_matrix", "pwr2_s3.mp3", "Ресурс LiFePO4! От киловаттников до тяжёлых станций Allpowers и JQB на четыре киловатта!"),
        ("scene4_field_vat", "pwr_s4.mp3", "Тянут РЭБ, связь и блиндажи без шума и выхлопа! Оптом и в розницу, с НДС и без!"),
        ("scene5_cta", "pwr_s5.mp3", "Заказывайте питание в магазине «В окопе» — Телеграм, ВКонтакте и Авито!"),
    ]
    gaps = [0.22, 0.22, 0.22, 0.22, 0.0]
    best_tempo = 1.24
    for cand in [1.14, 1.18, 1.21, 1.24, 1.27, 1.30]:
        tc = [squeeze_pauses(trim_silence(decode_audio(VO_DIR / fn, af=f"atempo={cand:.4f}"))) for _, fn, _ in clips_cfg]
        t_cur = 1.5 * BEAT
        for i_c, c in enumerate(tc):
            t_cur = math.ceil(t_cur / (BEAT / 2.0) - 1e-6) * (BEAT / 2.0)
            t_cur += len(c) / SR + gaps[i_c]
        print(f"Candidate tempo {cand:.2f}x -> voice ends at {t_cur:.3f}s")
        if t_cur <= 27.38:
            best_tempo = cand
            break

    processed = [polish_voice(VO_DIR / fn, best_tempo) for _, fn, _ in clips_cfg]
    v_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    meta = []
    t_cursor = 1.5 * BEAT
    for idx, ((seg_id, fn, text), clip) in enumerate(zip(clips_cfg, processed)):
        grid = BEAT / 2.0
        start_s = math.ceil(t_cursor / grid - 1e-6) * grid
        dur_s = len(clip) / SR
        end_s = start_s + dur_s
        add_stereo_clip(v_bus, clip, start_s, gain_db=0.0, pan=0.0)
        meta.append({
            "index": idx + 1,
            "id": seg_id,
            "file": fn,
            "text": text,
            "voice_start": round(start_s, 4),
            "voice_end": round(end_s, 4),
            "voice_start_frame": int(round(start_s * FPS)),
            "voice_end_frame": int(round(end_s * FPS)),
        })
        t_cursor = end_s + gaps[idx]

    cuts = [0.0]
    for i in range(4):
        mid = 0.5 * (meta[i]["voice_end"] + meta[i + 1]["voice_start"])
        cuts.append(round(int(round(mid * FPS)) / FPS, 6))
    cuts.append(30.0)
    for i in range(5):
        meta[i]["scene_start"] = round(cuts[i], 4)
        meta[i]["scene_end"] = round(cuts[i + 1], 4)
        meta[i]["scene_start_frame"] = int(round(cuts[i] * FPS))
        meta[i]["scene_end_frame"] = int(round(cuts[i + 1] * FPS))

    # Subtle real transition impacts & ticks
    sfx_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    boom_cin = decode_audio(SFX_DIR / "boom_cinematic.mp3")
    imp_deep = decode_audio(SFX_DIR / "impact_deep.mp3")
    imp_bright = decode_audio(SFX_DIR / "impact_bright.mp3")
    cut_tick = decode_audio(SFX_DIR / "cut_tick.mp3")
    whoosh_s = decode_audio(SFX_DIR / "whoosh_short.mp3")
    whoosh_tr = decode_audio(SFX_DIR / "whoosh_transition.mp3")

    c1, c2, c3, c4 = cuts[1], cuts[2], cuts[3], cuts[4]
    p_lock = round(add_stereo_clip(sfx_bus, imp_deep, 0.40, -6.0, 0.0), 4)
    p_drop = round(BAR, 4)
    add_stereo_clip(sfx_bus, whoosh_tr, max(0.0, c1 - 0.14), -7.5, 0.0)
    s2_span = c2 - c1
    t_st1 = round(c1 + 0.07 * s2_span, 4)
    t_st2 = round(c1 + 0.40 * s2_span, 4)
    t_st3 = round(c1 + 0.71 * s2_span, 4)
    add_stereo_clip(sfx_bus, imp_bright, t_st1, -9.0, -0.15)
    add_stereo_clip(sfx_bus, cut_tick, t_st2, -7.0, 0.12)
    add_stereo_clip(sfx_bus, imp_deep, t_st3, -8.5, -0.10)
    add_stereo_clip(sfx_bus, whoosh_s, max(0.0, c2 - 0.10), -8.0, 0.10)
    s3_span = c3 - c2
    t_ui1 = round(c2 + 0.15 * s3_span, 4)
    t_ui2 = round(c2 + 0.37 * s3_span, 4)
    t_ui3 = round(c2 + 0.59 * s3_span, 4)
    t_ui4 = round(c2 + 0.80 * s3_span, 4)
    for tui in (t_ui1, t_ui2, t_ui3, t_ui4):
        add_stereo_clip(sfx_bus, cut_tick, tui, -7.2, 0.0)
    p_s4 = round(add_stereo_clip(sfx_bus, imp_deep, c3, -5.8, 0.0), 4)
    p_s5 = round(add_stereo_clip(sfx_bus, boom_cin, c4, -5.5, 0.0), 4)
    sting_t = round(BAR * 20.0, 4)  # 27.4286s real studio crash outro!

    music_bus = decode_audio(dnb_power_mp3, af="equalizer=f=2200:t=q:w=1.0:g=-4.5,equalizer=f=3500:t=q:w=1.1:g=-2.8", stereo=True)[:TOTAL_SAMPLES].copy()
    speaking = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
    for m_seg in meta:
        s0 = max(0, int((m_seg["voice_start"] - 0.10) * SR))
        s1 = min(TOTAL_SAMPLES, int((m_seg["voice_end"] + 0.14) * SR))
        speaking[s0:s1] = 1.0
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

    rms_v = float(np.sqrt(np.mean(v_bus ** 2) + 1e-12))
    rms_m = float(np.sqrt(np.mean(music_bus ** 2) + 1e-12))
    v_bus = v_bus * ((10.0 ** (-16.2 / 20.0)) / rms_v)
    music_bus = music_bus * ((10.0 ** (-20.4 / 20.0)) / rms_m)
    music_bus *= (10.0 ** ((-5.5 * duck_env) / 20.0))[:, None]

    mix = v_bus + music_bus + sfx_bus * 0.65
    mix[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    mix[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32))))[:, None]

    out_wav = AUDIO_DIR / "master_power_30s.wav"
    tmp_wav = AUDIO_DIR / "_tmp_pre_power.wav"
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

    sync_data = {
        "product": "Зарядные станции (DJI Power / EcoFlow Delta 3 / Jackery V2 / Bluetti / Allpowers / JQB)",
        "music_source": "assets/audio/music_mp3/cc0_dnb_power_30s.mp3 (warlightwolf — Tech DnB Music 21, CC0-1.0 Public Domain, 174.6 BPM)",
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": int(DURATION * FPS),
        "sample_rate": SR,
        "bpm": BPM,
        "voice_tempo": best_tempo,
        "master_lufs": round(i_lufs, 2),
        "true_peak_db": round(tp_db, 2),
        "scene_cuts": cuts,
        "scenes": meta,
        "s1_lock": p_lock,
        "s1_drop": p_drop,
        "s2_nodes": [t_st1, t_st2, t_st3],
        "s3_rows": [t_ui1, t_ui2, t_ui3, t_ui4],
        "s4_drop": p_s4,
        "s5_slam": p_s5,
        "s5_sting": sting_t,
    }
    (PROJECT / "src" / "power_sync_map.json").write_text(json.dumps(sync_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[POWER MASTER] -14 LUFS check: {i_lufs:.2f} LUFS | Peak: {tp_db:.2f} dBFS | Tempo: {best_tempo:.2f}x")
    print(json.dumps(sync_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
