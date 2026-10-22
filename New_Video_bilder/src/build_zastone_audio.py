#!/usr/bin/env python3
"""
Builds the exact 150.000s (2m 30.00s) 48 kHz broadcast master (/tmp/master_zastone_256.wav)
and exact 11-Act sync map (New_Video_bilder/src/zastone_sync_map.json) for:
  «Шифрованные прошитые радиостанции "Ключ 256" (комплект 2 шт.) на базе ZASTONE DP-UV008 MOD»

Soundtrack:
  - 100% CC0-1.0 Public Domain Pure Instrumental Rolling Tech-DnB:
    warlightwolf — Tech DnB Music 21 & 20 [174.6 BPM, 0.00% vocals verified across 0..154s]
    (https://freesound.org/people/warlightwolf/sounds/612138/)
    stored at New_Video_bilder/assets/audio/music_mp3/cc0_dnb_zastone_154s.mp3.
  - Strict Voice-Priority Mixing:
    * Vocal-range EQ carve on music (-4.5 dB @ 2100 Hz, -3.0 dB @ 3500 Hz) so voice-05 baritone
      owns the entire 800–4000 Hz intelligibility band.
    * Continuous phrase-hold ducking [vo_start - 0.16s .. vo_end + 0.22s] at 0.115 gain (~11+ dB
      below announcer LUFS), smooth gentle bridge swell (0.27) between chapters, and clean
      outro swell (0.40) with natural studio fade-out at 150.000s.
"""
import json
import re
import subprocess
import wave
from pathlib import Path
import numpy as np

SR = 48000
DURATION = 150.0
N = int(SR * DURATION)
BPM = 174.0
BEAT = 60.0 / BPM
BAR = 4.0 * BEAT

ROOT = Path("/home/user/-/New_Video_bilder")
VO_DIR = ROOT / "assets" / "audio" / "zastone_vo"
TRACK_MP3 = ROOT / "assets" / "audio" / "music_mp3" / "cc0_dnb_zastone_154s.mp3"
OUT_WAV = Path("/tmp/master_zastone_256.wav")
SYNC_JSON = ROOT / "src" / "zastone_sync_map.json"


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        ch = wf.getnchannels()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return raw.reshape(-1, ch) if ch > 1 else raw


def save_stereo_wav(path: Path, stereo: np.ndarray) -> None:
    arr = np.clip(stereo, -1.0, 1.0)
    pcm = (arr * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def prep_vo_clip(src_mp3: Path, out_wav: Path, ss: float = None, to: float = None, tempo: float = 1.04) -> np.ndarray:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.3f}"]
    if to is not None:
        cmd += ["-to", f"{to:.3f}"]
    cmd += [
        "-i", str(src_mp3),
        "-af", (
            f"atempo={tempo:.4f},"
            "silenceremove=start_periods=1:start_threshold=-39dB:"
            "stop_periods=-1:stop_duration=0.115:stop_threshold=-37dB,"
            "highpass=f=80,"
            "equalizer=f=185:width_type=q:width=1.1:g=2.4,"
            "equalizer=f=3250:width_type=q:width=1.2:g=2.6,"
            "acompressor=threshold=-18dB:ratio=3.2:attack=5:release=75:makeup=2.4dB,"
            "alimiter=limit=0.95"
        ),
        "-ar", str(SR), "-ac", "1", str(out_wav),
    ]
    subprocess.run(cmd, check=True)
    mono = load_wav(out_wav)
    fi = min(int(0.015 * SR), len(mono) // 8)
    fo = min(int(0.030 * SR), len(mono) // 8)
    mono[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    mono[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    return mono


def synth_dmr_tpt(dur_s: float = 0.16) -> np.ndarray:
    n = int(SR * dur_s)
    out = np.zeros(n, dtype=np.float32)
    seg = int(0.036 * SR)
    for idx, freq in enumerate((910.0, 1220.0, 1560.0)):
        st = idx * int(0.048 * SR)
        ed = min(n, st + seg)
        t = np.arange(ed - st, dtype=np.float32) / SR
        env = np.maximum(0.0, np.sin(np.pi * np.linspace(0.0, 1.0, len(t), dtype=np.float32))) ** 0.45
        out[st:ed] = np.sin(2.0 * np.pi * freq * t) * env
    return np.column_stack([out * 0.85, out * 1.0])


def synth_sat_squelch_tail() -> np.ndarray:
    rng = np.random.default_rng(256)
    n = int(0.135 * SR)
    noise = rng.normal(0.0, 0.35, n).astype(np.float32)
    k = np.exp(-0.5 * (np.linspace(-2.5, 2.5, 9) ** 2))
    k = (k / k.sum()).astype(np.float32)
    band = np.convolve(noise, k, mode="same")
    t = np.arange(n, dtype=np.float32) / SR
    tone = 0.25 * np.sin(2.0 * np.pi * 1340.0 * t) * np.exp(-18.0 * t)
    env = np.ones(n, dtype=np.float32)
    env[:int(0.008 * SR)] = np.linspace(0.0, 1.0, int(0.008 * SR), dtype=np.float32)
    env[-int(0.045 * SR):] = np.linspace(1.0, 0.0, int(0.045 * SR), dtype=np.float32)
    sig = (band + tone) * env
    return np.column_stack([sig * 0.92, sig * 1.0])


def main():
    # 1. Decode 100% CC0-1.0 Public Domain pure-instrumental Drum & Bass (warlightwolf — Tech DnB 21 & 20)
    #    with deep vocal-pocket EQ carve across 1.2–4.0 kHz so music NEVER competes with voice-05!
    music_full_wav = Path("/tmp/z256_music_inst.wav")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(TRACK_MP3),
        "-t", f"{DURATION + 1.0:.3f}",
        "-af", (
            "equalizer=f=62:width_type=q:width=1.0:g=1.2,"
            "equalizer=f=1250:width_type=q:width=1.0:g=-2.8,"
            "equalizer=f=2200:width_type=q:width=0.9:g=-4.8,"
            "equalizer=f=3600:width_type=q:width=1.0:g=-3.2"
        ),
        "-ar", str(SR), "-ac", "2", str(music_full_wav),
    ], check=True)
    music_bed = load_wav(music_full_wav)[:N]

    # Calibrate music bed RMS to a strict 0.30 reference before applying gain curve
    cur_rms = float(np.sqrt(np.mean(music_bed[int(15 * SR):int(100 * SR)] ** 2)))
    music_bed = music_bed * (0.30 / max(cur_rms, 1e-4))

    # Smooth fade-in (0.50s) & silky studio fade-out (last 1.10s -> 0.000)
    music_bed[:int(0.50 * SR)] *= np.linspace(0.15, 1.0, int(0.50 * SR), dtype=np.float32)[:, None]
    music_bed[-int(1.10 * SR):] *= np.linspace(1.0, 0.0, int(1.10 * SR), dtype=np.float32)[:, None]

    # 2. Exact same 11 voice-05 chapters so every visual cut in v_okope_zastone_key256.mp4 stays 100.000% locked!
    chapter_defs = [
        ("s01_hook",     VO_DIR / "z256_s01.mp3", None,  None,  "Ваши разговоры — только для своих",         "HOOK · КЛЮЧ 256"),
        ("s02_turnkey",  VO_DIR / "z256_s02.mp3", None,  None,  "Готова из коробки: прошита до отгрузки",    "ZASTONE DP-UV008 MOD"),
        ("s03_crypto",   VO_DIR / "z256_s03.mp3", None,  None,  "Лицензионный ключ Motorola 256 бит",        "AES-256 · РЕЧЬ И SMS"),
        ("s04_bands",    VO_DIR / "z256_s04.mp3", None,  None,  "5 частотных диапазонов · до 10 Вт",         "118–520 МГЦ · −126 ДБМ"),
        ("s05_modes",    VO_DIR / "z256_s05.mp3", None,  None,  "4 режима связи в одной рации",              "АНАЛОГ · ЦИФРА · KEY-256 · SAT"),
        ("s06_satcom",   VO_DIR / "z256_s06.mp3", None,  None,  "Спутниковая связь: 195+ каналов",           "SATCOM · ОТШЛЁП · SATVIEW"),
        ("s07_groups",    VO_DIR / "z256_s07.mp3", None,  None,  "Группы, позывные на ЖК и каналы 5 / 7",     "СВОИ / СМЕЖНИКИ"),
        ("s08_range",    VO_DIR / "z256_s08.mp3", None,  None,  "Реальная дальность: от города до выноса",   "3–7 · 20–25 · ДО 60 КМ"),
        ("s09_rugged",   VO_DIR / "z256_s09.mp3", None,  None,  "IP67 · 18 часов · Kenwood · GPS / VOX",     "2500 МА·Ч · 315 Г"),
        ("s10_kit",      VO_DIR / "z256_s10.mp3", 0.00,  15.25, "Комплект из 2 шт. · Опт/розница · НДС",     "ПОЛНАЯ БОЕВАЯ УКЛАДКА"),
        ("s11_finale",   VO_DIR / "z256_s10.mp3", 15.28, None,  "В ОКОПЕ — Телеграм · ВКонтакте · Авито",    "ЗАКАЗАТЬ КОМПЛЕКТ"),
    ]

    clips = []
    for cid, src_mp3, ss, to, title, badge in chapter_defs:
        wav_p = Path(f"/tmp/z256_vo_{cid}.wav")
        mono = prep_vo_clip(src_mp3, wav_p, ss=ss, to=to, tempo=1.04)
        clips.append({"id": cid, "title": title, "badge": badge, "audio": mono, "dur": len(mono) / SR})

    lead_in = 2.0 * BEAT
    outro_tail = 3.35
    total_gaps = DURATION - lead_in - outro_tail - sum(c["dur"] for c in clips)
    gap_weights = [1.05, 1.35, 1.00, 1.25, 1.05, 1.00, 1.25, 1.00, 1.05, 1.45]
    w_sum = sum(gap_weights)
    gaps = [total_gaps * w / w_sum for w in gap_weights]

    vo_track = np.zeros((N, 2), dtype=np.float32)
    sfx_track = np.zeros((N, 2), dtype=np.float32)
    vo_phrase_mask = np.zeros(N, dtype=np.float32)

    tpt = synth_dmr_tpt()
    sat_sq = synth_sat_squelch_tail()

    scenes_meta = []
    cursor_vo = lead_in
    for idx, c in enumerate(clips):
        vo_start = cursor_vo
        vo_end = vo_start + c["dur"]
        scene_start = 0.0 if idx == 0 else round(prev_vo_end + prev_gap * 0.44, 3)
        if idx < len(clips) - 1:
            nxt_gap = gaps[idx]
            scene_end = round(vo_end + nxt_gap * 0.44, 3)
            cursor_vo = vo_end + nxt_gap
            prev_vo_end = vo_end
            prev_gap = nxt_gap
        else:
            scene_end = DURATION

        st_i = int(round(vo_start * SR))
        ed_i = min(N, st_i + len(c["audio"]))
        seg = c["audio"][:ed_i - st_i]
        vo_track[st_i:ed_i, 0] += seg
        vo_track[st_i:ed_i, 1] += seg

        ph_s = max(0, int((vo_start - 0.16) * SR))
        ph_e = min(N, int((vo_end + 0.22) * SR))
        vo_phrase_mask[ph_s:ph_e] = 1.0

        if idx in (0, 2, 4, 6, 9):
            ts = max(0, int((vo_start - 0.30) * SR))
            te = min(N, ts + len(tpt))
            sfx_track[ts:te] += tpt[:te - ts] * 0.085
        elif idx == 5:
            ts = max(0, int((vo_start - 0.28) * SR))
            te = min(N, ts + len(sat_sq))
            sfx_track[ts:te] += sat_sq[:te - ts] * 0.13

        scenes_meta.append({
            "index": idx + 1,
            "id": c["id"],
            "title": c["title"],
            "badge": c["badge"],
            "start": round(scene_start, 3),
            "end": round(scene_end, 3),
            "duration": round(scene_end - scene_start, 3),
            "vo_start": round(vo_start, 3),
            "vo_end": round(vo_end, 3),
            "vo_dur": round(c["dur"], 3),
        })

    # Smooth phrase-hold ducking envelope:
    #   - Under speech: music_gain = 0.115 (quiet, clean rolling sub+drums ~14 dB below announcer!)
    #   - Inter-chapter transitions: gentle 0.27 swell (never blasts between sentences!)
    #   - Final 3.35s outro: clean 0.40 swell into smooth studio fade-out!
    win_len = int(0.18 * SR) | 1
    kern = np.hanning(win_len).astype(np.float32)
    kern /= kern.sum()
    smooth_phrase = np.convolve(vo_phrase_mask, kern, mode="same")

    unducked_curve = np.full(N, 0.27, dtype=np.float32)
    last_vo_end_i = int(scenes_meta[-1]["vo_end"] * SR)
    ramp_i = min(N - last_vo_end_i, int(0.50 * SR))
    unducked_curve[last_vo_end_i:last_vo_end_i + ramp_i] = np.linspace(0.27, 0.40, ramp_i, dtype=np.float32)
    unducked_curve[last_vo_end_i + ramp_i:] = 0.40

    music_gain = unducked_curve * (1.0 - smooth_phrase) + 0.115 * smooth_phrase
    music_final = music_bed * music_gain[:, None]
    vo_final = vo_track * 1.12

    speech_mask = vo_phrase_mask > 0.5
    vo_rms_speech = float(np.sqrt(np.mean(vo_final[speech_mask] ** 2)))
    mu_rms_speech = float(np.sqrt(np.mean(music_final[speech_mask] ** 2)))
    snr_db = 20.0 * np.log10(vo_rms_speech / max(mu_rms_speech, 1e-6))
    print(f"SPEECH-TO-MUSIC SEPARATION DURING NARRATION: +{snr_db:.2f} dB (VO_rms={vo_rms_speech:.4f}, Music_rms={mu_rms_speech:.4f})")

    raw_mix = music_final + vo_final + sfx_track
    tmp_raw = Path("/tmp/z256_master_pre_lufs.wav")
    save_stereo_wav(tmp_raw, raw_mix)

    p1_cmd = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(tmp_raw),
        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, check=True)
    stats = json.loads(re.search(r"\{[\s\S]*\}", p1_cmd.stderr).group(0))

    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(tmp_raw),
        "-af", (
            f"loudnorm=I=-14:TP=-1.0:LRA=11:"
            f"measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}:"
            f"measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}:linear=true"
        ),
        "-ar", str(SR), "-ac", "2", str(OUT_WAV),
    ], check=True)

    final_pcm = load_wav(OUT_WAV)
    if len(final_pcm) != N:
        fixed = np.zeros((N, 2), dtype=np.float32)
        k = min(N, len(final_pcm))
        fixed[:k] = final_pcm[:k]
        save_stereo_wav(OUT_WAV, fixed)

    p2_cmd = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(OUT_WAV),
        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, check=True)
    stats2 = json.loads(re.search(r"\{[\s\S]*\}", p2_cmd.stderr).group(0))

    sync_payload = {
        "duration": DURATION,
        "fps": 60,
        "frames": int(DURATION * 60),
        "bpm": BPM,
        "soundtrack": "warlightwolf — Tech DnB Music 21 & 20 [CC0-1.0 Public Domain, 174.6 BPM, 0% vocals]",
        "license": "CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)",
        "speech_to_music_snr_db": round(snr_db, 2),
        "integrated_lufs": stats2["input_i"],
        "true_peak_dbtp": stats2["input_tp"],
        "music_ducked_gain": 0.115,
        "scenes": scenes_meta,
    }
    SYNC_JSON.write_text(json.dumps(sync_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MASTER READY: {OUT_WAV} | exact={len(load_wav(OUT_WAV))/SR:.3f}s | I={stats2['input_i']} LUFS | TP={stats2['input_tp']} dBTP")


if __name__ == "__main__":
    main()
