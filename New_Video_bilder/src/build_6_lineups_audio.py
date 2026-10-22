#!/usr/bin/env python3
"""
Builds all 6 sample-accurate 30.000s (48 kHz stereo = 1,440,000 samples = 1800 frames @ 60 fps)
broadcast master WAVs (`-14.0 LUFS`, `<= -0.9 dBFS` True Peak) + `src/lineups_sync_map.json`
for the 6 individual Power Station Lineup Reels of «В ОКОПЕ»:
  01_DJI_Power        — DJI Power 1000W V2 · DJI Power 2000W
  02_EcoFlow_Delta    — EcoFlow Delta 3 Plus · 3 Max · 3 Max Plus · 3 Ultra Plus · Delta Pro 3
  03_Jackery_V2       — Jackery Explorer 1000 V2 · 2000 V2 · 3000 V2
  04_JQB_Power        — JQB Power 500W-1000Wh · 1000W-2000Wh · 1800W-4000Wh
  05_Allpowers_R      — Allpowers R2500 V.2 · Allpowers R4000
  06_Bluetti_AC       — Bluetti AC180P / 1800 Вт · Bluetti AC200PL / 2400 Вт
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
VO_DIR = AUDIO_DIR / "lineups_vo"
MP3_DIR = AUDIO_DIR / "music_mp3"
SFX_DIR = STUDIO / "toolkit" / "sfx"

SR = 48000
FPS = 60
DURATION = 30.0
TOTAL_SAMPLES = int(round(DURATION * SR))


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
    return float(m_i[-1]), float(m_tp[-1])


def moving_rms(x: np.ndarray, win: int) -> np.ndarray:
    cs = np.cumsum(np.insert(x.astype(np.float64) ** 2, 0, 0.0))
    same = (cs[win:] - cs[:-win]) / win
    pad_l = win // 2
    pad_r = len(x) - len(same) - pad_l
    return np.sqrt(np.pad(same, (pad_l, max(0, pad_r)), mode="edge") + 1e-12).astype(np.float32)


def split_5_phrases(raw_path: Path, phrases: list[str]) -> list[np.ndarray]:
    """Splits a 5-sentence `...`-delimited TTS MP3 at exact silence valleys matching text lengths."""
    x = decode_audio(raw_path)
    # Trim outer leading/trailing silence first
    active_idx = np.where(np.abs(x) > 0.015)[0]
    x = x[max(0, active_idx[0] - int(0.03 * SR)) : min(len(x), active_idx[-1] + int(0.08 * SR))]
    total_t = len(x) / SR

    # Expected cumulative character fractions for the 4 interior split points
    lens = [len(p) for p in phrases]
    cum_fracs = [sum(lens[:k]) / sum(lens) for k in range(1, 5)]

    w = int(0.01 * SR)
    n = len(x) // w
    rms_db = 20.0 * np.log10(np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, axis=1) + 1e-12))

    # Candidate quiet windows (< -38 dB for at least 180ms)
    quiet = rms_db < -38.0
    valleys = []
    i = 0
    while i < n:
        j = i
        while j < n and quiet[j] == quiet[i]:
            j += 1
        dur_s = (j - i) * 0.01
        mid_s = 0.5 * (i + j) * 0.01
        if quiet[i] and dur_s >= 0.16 and 1.2 < mid_s < (total_t - 1.2):
            valleys.append((mid_s, dur_s))
        i = j

    # Dynamic programming / greedy monotonic pick of 4 best valleys closest to expected char fractions & longest pause
    splits_s = []
    prev_s = 0.8
    for k, frac in enumerate(cum_fracs):
        target_s = frac * total_t
        max_allow = (cum_fracs[k + 1] * total_t - 0.8) if k < 3 else (total_t - 1.2)
        best = None
        for mid_s, dur_s in valleys:
            if mid_s <= prev_s + 1.2 or mid_s >= max_allow:
                continue
            score = dur_s * 2.2 - abs(mid_s - target_s) * 0.35
            if best is None or score > best[0]:
                best = (score, mid_s, dur_s)
        if best is None:
            # Fallback: minimum RMS window in [target_s - 1.4, target_s + 1.4]
            lo_i = max(int((prev_s + 1.0) / 0.01), int((target_s - 1.5) / 0.01))
            hi_i = min(n - 50, int((target_s + 1.5) / 0.01))
            min_i = lo_i + int(np.argmin(rms_db[lo_i:hi_i]))
            mid_s = min_i * 0.01
        else:
            mid_s = best[1]
        splits_s.append(mid_s)
        prev_s = mid_s

    pts = [0] + [int(round(s * SR)) for s in splits_s] + [len(x)]
    return [x[pts[i] : pts[i + 1]].copy() for i in range(5)]


def trim_and_polish_segment(seg: np.ndarray, tempo: float) -> np.ndarray:
    tmp_in = VO_DIR / "_seg_in.wav"
    clipped = np.clip(seg, -0.9999, 0.9999)
    with wave.open(str(tmp_in), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((clipped * 32767.0).astype(np.int16).tobytes())
    af = f"atempo={tempo:.4f},highpass=f=85,equalizer=f=3400:t=q:w=1.1:g=2.6"
    raw = decode_audio(tmp_in, af=af)
    tmp_in.unlink(missing_ok=True)

    # Trim silence + squeeze interior pauses > 0.16s
    idx = np.where(np.abs(raw) > 0.014)[0]
    if len(idx):
        raw = raw[max(0, idx[0] - int(0.025 * SR)) : min(len(raw), idx[-1] + int(0.065 * SR))].copy()
    w = int(0.02 * SR)
    n = len(raw) // w
    if n >= 4:
        rms = np.sqrt(np.mean(raw[: n * w].reshape(n, w) ** 2, axis=1) + 1e-12)
        quiet = (20.0 * np.log10(rms)) < -39.0
        chunks, i = [], 0
        while i < n:
            j = i
            while j < n and quiet[j] == quiet[i]:
                j += 1
            part = raw[i * w : j * w]
            if quiet[i] and 0 < i and j < n and len(part) > int(0.16 * SR):
                keep = int(0.16 * SR)
                half = keep // 2
                xf = min(240, half // 2)
                l, r = part[:half].copy(), part[-half:].copy()
                l[-xf:] *= np.linspace(1, 0, xf, dtype=np.float32)
                r[:xf] *= np.linspace(0, 1, xf, dtype=np.float32)
                part = np.concatenate([l[:-xf], l[-xf:] + r[:xf], r[xf:]])
            chunks.append(part)
            i = j
        chunks.append(raw[n * w :])
        raw = np.concatenate(chunks)

    fi = min(int(0.012 * SR), len(raw) // 4)
    fo = min(int(0.035 * SR), len(raw) // 4)
    if fi > 0:
        raw[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    if fo > 0:
        raw[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)

    env = moving_rms(raw, int(0.14 * SR))
    act = env[env > 0.008]
    med = float(np.percentile(act, 60)) if len(act) else 0.05
    gain = moving_rms(np.clip((med / np.maximum(env, med * 0.28)) ** 0.30, 0.65, 1.60), int(0.04 * SR))
    y = raw * gain
    rms_act = float(np.sqrt(np.mean(y[env > 0.008] ** 2) + 1e-12))
    return (y * ((10.0 ** (-16.2 / 20.0)) / rms_act)).astype(np.float32)


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
    mono = np.mean(np.abs(st[:avail]), axis=1)
    return (idx0 + (int(np.argmax(mono)) if len(mono) else 0)) / SR


def main():
    boom_cin = decode_audio(SFX_DIR / "boom_cinematic.mp3")
    imp_deep = decode_audio(SFX_DIR / "impact_deep.mp3")
    imp_bright = decode_audio(SFX_DIR / "impact_bright.mp3")
    cut_tick = decode_audio(SFX_DIR / "cut_tick.mp3")
    whoosh_s = decode_audio(SFX_DIR / "whoosh_short.mp3")
    whoosh_tr = decode_audio(SFX_DIR / "whoosh_transition.mp3")

    # 3 distinct CC0-1.0 Public Domain studio Drum & Bass MP3 tracks rotated across the 6 lineups!
    music_pool = [
        ("cc0_dnb_power_30s.mp3", 174.6, 27.4286),
        ("cc0_dnb_voevoda_30s.mp3", 174.6, 27.5862),
        ("cc0_dnb_store_30s.mp3", 174.6, 27.5862),
    ]

    lineups = [
        {
            "slug": "01_DJI_Power",
            "raw": "raw_01_dji.mp3",
            "music_idx": 0,
            "phrases": [
                "Тихое питание для расчётов БПЛА — станции DJI Power в магазине «В окопе»!",
                "В наличии обе флагманские модели: компактная DJI Power тысяча ватт V2 и мощная двухкиловаттная версия!",
                "Ускоренный разгон аккумуляторов дронов, сверхтихий режим двадцать три децибела и чистый синус двести двадцать вольт!",
                "Долговечные ячейки LiFePO4! Поставляем от одной штуки до партий, с НДС и без НДС!",
                "Заказывайте DJI Power в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
        {
            "slug": "02_EcoFlow_Delta",
            "raw": "raw_02_ecoflow.mp3",
            "music_idx": 1,
            "phrases": [
                "Эталон полевой мощности — вся линейка EcoFlow Delta в магазине «В окопе»!",
                "В наличии пять моделей: Delta три Плюс, Макс, Макс Плюс, Ультра Плюс и тяжёлый флагман Delta Pro три!",
                "Молниеносная зарядка меньше чем за час, бесперебойное питание связи и мощность до четырёх киловатт!",
                "Ресурс LiFePO4 четыре тысячи циклов! Отгружаем оптом и в розницу, с НДС и без!",
                "Заказывайте станции EcoFlow в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
        {
            "slug": "03_Jackery_Explorer_V2",
            "raw": "raw_03_jackery.mp3",
            "music_idx": 2,
            "phrases": [
                "Неубиваемое питание для выездов и блиндажей — линейка Jackery Explorer V2 в «В окопе»!",
                "В наличии все три мощности: Explorer тысяча V2, две тысячи V2 и тяжёлая три тысячи V2!",
                "Ударопрочный корпус, защита аккумулятора, чистая синусоида и быстрая зарядка от сети или солнца!",
                "Надёжные ячейки LiFePO4 без выхлопа и шума! Оптом и в розницу, с НДС и без НДС!",
                "Заказывайте Jackery в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
        {
            "slug": "04_JQB_Power",
            "raw": "raw_04_jqb.mp3",
            "music_idx": 0,
            "phrases": [
                "Максимум автономных часов без переплаты — зарядные станции JQB Power в магазине «В окопе»!",
                "В наличии три практичных номинала: на один, два и целых четыре киловатт-часа ёмкости!",
                "Долго питают комплексы РЭБ, ретрансляторы, рации и освещение в закрытых укрытиях без выхлопа!",
                "Долговечные батареи LiFePO4! Поставки от одной станции до крупных партий, с НДС и без!",
                "Заказывайте JQB Power в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
        {
            "slug": "05_Allpowers_R_Series",
            "raw": "raw_05_allpowers.mp3",
            "music_idx": 1,
            "phrases": [
                "Тяжёлая энергетика для штабов и позиций — станции Allpowers в магазине «В окопе»!",
                "В наличии силовые модели Allpowers R две пятьсот второй версии и мощнейшая R четыре тысячи!",
                "Высокая пиковая нагрузка, функция бесперебойника, чистый синус двести двадцать вольт и заряд от панелей!",
                "Ресурс LiFePO4 на годы работы! Отгружаем оптом и в розницу, с НДС и без НДС!",
                "Заказывайте станции Allpowers в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
        {
            "slug": "06_Bluetti_AC_Series",
            "raw": "raw_06_bluetti.mp3",
            "music_idx": 2,
            "phrases": [
                "Проверенная промышленная надёжность — станции Bluetti в магазине «В окопе»!",
                "В наличии ходовые модели: Bluetti AC сто восемьдесят P на тысячу восемьсот ватт и AC двести PL на две четыреста ватт!",
                "Турбо-зарядка, повышенная защита от пыли и стабильное питание чувствительной электроники и связи!",
                "Выносливые ячейки LiFePO4! Поставляем оптом и в розницу, с НДС и без!",
                "Заказывайте Bluetti в магазине «В окопе» — Телеграм, ВКонтакте и Авито!",
            ],
        },
    ]

    all_sync = {}
    fi, fo = int(0.015 * SR), int(0.350 * SR)
    gaps = [0.20, 0.20, 0.20, 0.20, 0.0]

    existing_sync = json.loads((PROJECT / "src" / "lineups_sync_map.json").read_text(encoding="utf-8"))

    for item in lineups:
        slug = item["slug"]
        mp3_name, bpm, sting_t = music_pool[item["music_idx"]]
        beat = 60.0 / bpm
        clean_stem = VO_DIR / f"clean_vo_{slug}.wav"
        raw_mp3 = VO_DIR / item["raw"]

        if raw_mp3.exists():
            raw_segs = split_5_phrases(raw_mp3, item["phrases"])
            best_tempo = 1.24
            for cand in [1.14, 1.18, 1.22, 1.26, 1.30, 1.34, 1.38, 1.42]:
                polished_try = [trim_and_polish_segment(s, cand) for s in raw_segs]
                tc = 1.5 * beat
                for ic, clip in enumerate(polished_try):
                    tc = math.ceil(tc / (beat / 2.0) - 1e-6) * (beat / 2.0)
                    tc += len(clip) / SR + gaps[ic]
                if tc <= 27.60:
                    best_tempo = cand
                    break
            clips = [trim_and_polish_segment(s, best_tempo) for s in raw_segs]
            v_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
            meta = []
            t_cur = 1.5 * beat
            for idx, (txt, clip) in enumerate(zip(item["phrases"], clips)):
                grid = beat / 2.0
                start_s = math.ceil(t_cur / grid - 1e-6) * grid
                end_s = start_s + len(clip) / SR
                add_stereo_clip(v_bus, clip, start_s, 0.0, 0.0)
                meta.append({"index": idx + 1, "text": txt, "voice_start": round(start_s, 4), "voice_end": round(end_s, 4)})
                t_cur = end_s + gaps[idx]
            cuts = [0.0] + [round(int(round(0.5 * (meta[i]["voice_end"] + meta[i + 1]["voice_start"]) * FPS)) / FPS, 6) for i in range(4)] + [30.0]
        else:
            # Frame-locked pre-isolated 30.000s mono voice stem -> 0.000000s visual drift!
            mono_v = decode_audio(clean_stem, af="highpass=f=85,equalizer=f=3350:t=q:w=1.1:g=2.2")[:TOTAL_SAMPLES]
            v_bus = np.column_stack([mono_v, mono_v])
            meta = existing_sync[slug]["scenes"]
            cuts = existing_sync[slug]["cuts"]
            best_tempo = existing_sync[slug]["voice_tempo"]

        sfx_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
        c1, c2, c3, c4 = cuts[1], cuts[2], cuts[3], cuts[4]
        p_lock = round(add_stereo_clip(sfx_bus, imp_deep, 0.40, -6.0, 0.0), 4)
        add_stereo_clip(sfx_bus, whoosh_tr, max(0.0, c1 - 0.14), -7.5, 0.0)
        add_stereo_clip(sfx_bus, imp_bright, c1 + 0.12, -9.0, -0.14)
        add_stereo_clip(sfx_bus, cut_tick, 0.5 * (c1 + c2), -7.0, 0.12)
        add_stereo_clip(sfx_bus, whoosh_s, max(0.0, c2 - 0.10), -8.0, 0.10)
        for k in range(4):
            add_stereo_clip(sfx_bus, cut_tick, c2 + (k + 0.6) * (c3 - c2) / 4.3, -7.2, 0.0)
        p_s4 = round(add_stereo_clip(sfx_bus, imp_deep, c3, -5.8, 0.0), 4)
        p_s5 = round(add_stereo_clip(sfx_bus, boom_cin, c4, -5.5, 0.0), 4)

        music_bus = decode_audio(MP3_DIR / mp3_name, af="equalizer=f=2200:t=q:w=1.0:g=-4.5,equalizer=f=3500:t=q:w=1.1:g=-2.8", stereo=True)[:TOTAL_SAMPLES].copy()
        speaking = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
        for m_seg in meta:
            s0 = max(0, int((m_seg["voice_start"] - 0.10) * SR))
            s1 = min(TOTAL_SAMPLES, int((m_seg["voice_end"] + 0.14) * SR))
            speaking[s0:s1] = 1.0
        duck_env = np.empty(TOTAL_SAMPLES, dtype=np.float32)
        prev, a_att, a_rel = 0.0, math.exp(-1.0 / (0.14 * SR)), math.exp(-1.0 / (0.45 * SR))
        for i in range(0, TOTAL_SAMPLES, 64):
            tgt = float(speaking[i])
            coeff = a_att if tgt > prev else a_rel
            prev = tgt + (prev - tgt) * (coeff ** 64)
            duck_env[i : i + 64] = prev

        v_bus *= (10.0 ** (-16.2 / 20.0)) / float(np.sqrt(np.mean(v_bus ** 2) + 1e-12))
        music_bus *= (10.0 ** (-20.4 / 20.0)) / float(np.sqrt(np.mean(music_bus ** 2) + 1e-12))
        music_bus *= (10.0 ** ((-5.5 * duck_env) / 20.0))[:, None]

        mix = v_bus + music_bus + sfx_bus * 0.65
        mix[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
        mix[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fo, dtype=np.float32))))[:, None]

        out_wav = AUDIO_DIR / f"master_{slug}.wav"
        tmp_wav = AUDIO_DIR / f"_tmp_{slug}.wav"
        pk = float(np.max(np.abs(mix))) + 1e-9
        write_wav_pcm16(tmp_wav, mix * (0.70 / pk))
        pre_lufs, _ = measure_ebur128(tmp_wav)
        cal = mix * (10.0 ** ((-14.0 - pre_lufs) / 20.0) * (0.70 / pk))
        ceiling = 10.0 ** (-1.05 / 20.0)
        peak_tr = np.maximum(np.abs(cal[:, 0]), np.abs(cal[:, 1]))
        win = int(0.005 * SR)
        pad = (win - (len(peak_tr) % win)) % win
        env_m = np.repeat(np.pad(peak_tr, (0, pad)).reshape(-1, win).max(axis=1), win)[:TOTAL_SAMPLES]
        lim_g = moving_rms(np.minimum(1.0, ceiling / np.maximum(env_m, 1e-9)), int(0.006 * SR))
        final_mix = np.clip(cal * lim_g[:, None], -ceiling, ceiling)
        write_wav_pcm16(out_wav, final_mix)
        i_lufs, tp_db = measure_ebur128(out_wav)
        if abs(-14.0 - i_lufs) > 0.12:
            final_mix = np.clip(final_mix * (10.0 ** ((-14.0 - i_lufs) / 20.0)), -ceiling, ceiling)
            write_wav_pcm16(out_wav, final_mix)
            i_lufs, tp_db = measure_ebur128(out_wav)
        tmp_wav.unlink(missing_ok=True)

        all_sync[slug] = {
            "bpm": bpm,
            "voice_tempo": best_tempo,
            "voice_end": meta[-1]["voice_end"],
            "master_lufs": round(i_lufs, 2),
            "true_peak_db": round(tp_db, 2),
            "cuts": cuts,
            "s1Lock": p_lock,
            "s4Drop": p_s4,
            "s5Slam": p_s5,
            "s5Sting": sting_t,
            "scenes": meta,
        }
        print(f"[{slug:24s}] {i_lufs:6.2f} LUFS | Peak {tp_db:5.2f} dBFS | Tempo {best_tempo:.2f}x | VoiceEnd {meta[-1]['voice_end']:6.3f}s | Cuts {cuts}")

    (PROJECT / "src" / "lineups_sync_map.json").write_text(json.dumps(all_sync, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
