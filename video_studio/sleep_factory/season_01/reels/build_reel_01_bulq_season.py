#!/usr/bin/env python3
"""Build a separate 40-second Reel that briefly summarizes the whole first season.

The fresh narration uses the selected Bulq and Meowskis voices, with captions
estimated by character weight within each generated clip. Visuals sample objects
and settings across S01E02–S01E06 without reusing or overwriting pilot Reels.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEASON = HERE.parent
SLEEP_FACTORY = SEASON.parent
EP02 = SEASON / "episode_02"
EP03 = SEASON / "episode_03"
EP04 = SEASON / "episode_04"
EP05 = SEASON / "episode_05"
EP06 = SEASON / "episode_06"
BULQ_NARRATION = HERE / "narration_bulq.wav"
MEOWSKIS_NARRATION = HERE / "narration_meowskis.wav"
INTRO_STING = SEASON / "series_micro_jingle.wav"
BULQ_TEXT = (
    "В космическом магазинчике каждая сделка начинается с неожиданности: "
    "маяк спас груз, но страховщик спорит; тень получает тариф; "
    "универсальные скобы подходят не всем. Бульк ищет выгоду, "
    "пока Мявскис проверяет детали."
)
MEOWSKIS_TEXT = (
    "Мы с Бульком проверяем технику и условия сделки. "
    "В сезоне — карта с намеренно пустым участком и три стука в трюме. "
    "Лот сообщает только проверяемые данные. "
    "Каждая история самостоятельна, а вместе — первый сезон."
)
BULQ_CAPTIONS = [
    "В космическом магазинчике",
    "каждая сделка начинается с неожиданности:",
    "маяк спас груз, но страховщик спорит;",
    "тень получает тариф;",
    "универсальные скобы подходят не всем.",
    "Бульк ищет выгоду, пока Мявскис проверяет детали.",
]
MEOWSKIS_CAPTIONS = [
    "Мы с Бульком проверяем технику",
    "и условия сделки.",
    "В сезоне — карта с намеренно пустым участком",
    "и три стука в трюме.",
    "Лот сообщает только проверяемые данные.",
    "Каждая история самостоятельна,",
    "а вместе — первый сезон.",
]
OUTPUT = HERE / "reel_01_bulq_season.mp4"
OUTPUT_SRT = HERE / "reel_01_bulq_season.srt"
OUTPUT_ASS = HERE / "reel_01_bulq_season.ass"
REPORT = HERE / "reel_01_bulq_season.build_report.json"
WORK_ROOT = SLEEP_FACTORY.parents[1] / ".arena" / "reel_01_bulq_season_work"
FPS = 24
WIDTH, HEIGHT = 720, 1280
TARGET_SECONDS = 40.0
TITLE_SECONDS = 3.6
VOICE_GAP_SECONDS = 0.8
CTA_SECONDS = 4.0


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Segment:
    image: Path
    frames: int
    label: str


def binary(name: str) -> str:
    env = os.environ.get(name.upper() + "_PATH")
    if env and Path(env).is_file():
        return str(Path(env).resolve())
    found = shutil.which(name.lower())
    if found:
        return found
    raise RuntimeError(f"Не найден {name}; задайте {name.upper()}_PATH или добавьте бинарник в PATH.")


FFMPEG = binary("ffmpeg")
FFPROBE = binary("ffprobe")


def run(args: list[str], label: str) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout or "нет подробностей").strip()
        raise RuntimeError(f"{label}:\n{detail[-4000:]}")
    return result.stdout


def probe_duration(path: Path) -> float:
    value = run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        f"ffprobe {path.name}",
    ).strip()
    return float(value)


def stamp(value: float) -> str:
    ms = max(0, round(value * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def ass_stamp(value: float) -> str:
    cs = max(0, round(value * 100))
    hours, cs = divmod(cs, 360_000)
    minutes, cs = divmod(cs, 6_000)
    seconds, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{cs:02}"


def cue_weight(text: str) -> float:
    characters = sum(not char.isspace() for char in text)
    ending = text.rstrip("\"'»”’)]}")
    if ending.endswith((".", "!", "?", "…", ":")):
        return characters + 5.0
    if ending.endswith((",", ";")):
        return characters + 2.0
    return float(max(1, characters))


def timed_cues(chunks: list[str], start: float, duration: float) -> list[Cue]:
    if not chunks or duration <= 0:
        raise RuntimeError("Пустой текст или нулевая длительность дикторского фрагмента.")
    pad = min(0.045, duration / max(2, 2 * len(chunks)))
    active = duration - pad * (len(chunks) - 1)
    weights = [cue_weight(chunk) for chunk in chunks]
    total = sum(weights)
    cursor = start
    result: list[Cue] = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights)):
        end = start + duration if index == len(chunks) - 1 else cursor + active * weight / total
        result.append(Cue(cursor, end, chunk))
        cursor = end + (pad if index < len(chunks) - 1 else 0.0)
    return result


def make_cues(bulq_seconds: float, meowskis_start: float,
              meowskis_seconds: float) -> list[Cue]:
    if " ".join(BULQ_CAPTIONS) != BULQ_TEXT or " ".join(MEOWSKIS_CAPTIONS) != MEOWSKIS_TEXT:
        raise RuntimeError("Текст озвучки и набор субтитров разошлись.")
    return (
        timed_cues(BULQ_CAPTIONS, TITLE_SECONDS, bulq_seconds)
        + timed_cues(MEOWSKIS_CAPTIONS, meowskis_start, meowskis_seconds)
    )


def wrap_ass(text: str, max_chars: int = 29) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return r"\N".join(lines).replace("{", r"\{").replace("}", r"\}")


def write_captions(cues: list[Cue], meowskis_end: float) -> None:
    srt_lines: list[str] = []
    ass_lines = [
        "[Script Info]", "Title: Bulq — season one", "ScriptType: v4.00+",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,DejaVu Sans,38,&H00FFFFFF,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,3,1,2,46,46,170,1",
        "Style: Brand,DejaVu Sans,27,&H00D6EEE8,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,2,1,8,40,40,72,1",
        "Style: CTA,DejaVu Sans,32,&H00F7EBD4,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,3,1,2,52,52,260,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,{ass_stamp(TARGET_SECONDS)},Brand,,0,0,0,,ИСТОРИИ ПЕРВОГО СЕЗОНА",
        f"Dialogue: 1,{ass_stamp(max(meowskis_end, TARGET_SECONDS-CTA_SECONDS))},{ass_stamp(TARGET_SECONDS)},CTA,,0,0,0,,СЛУШАЙ ВЕСЬ СЕЗОН НА YOUTUBE",
    ]
    for index, cue in enumerate(cues, 1):
        srt_lines.extend((str(index), f"{stamp(cue.start)} --> {stamp(cue.end)}", cue.text, ""))
        ass_lines.append(
            f"Dialogue: 2,{ass_stamp(cue.start)},{ass_stamp(cue.end)},Caption,,0,0,0,,{wrap_ass(cue.text)}"
        )
    OUTPUT_SRT.write_text("\n".join(srt_lines).rstrip() + "\n", encoding="utf-8")
    OUTPUT_ASS.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")


def render_segment(segment: Segment, output: Path, folder: Path) -> None:
    graph = (
        "[0:v]split=2[bgsrc][fgsrc];"
        "[bgsrc]scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=720:1280,gblur=sigma=26,eq=brightness=-0.26:saturation=0.76,"
        "zoompan=z='min(zoom+0.000035,1.035)':x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':d=1:s=720x1280:fps=24,"
        f"trim=end_frame={segment.frames},setpts=PTS-STARTPTS[bg];"
        "[fgsrc]scale=680:382:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=680:382:(ow-iw)/2:(oh-ih)/2:color=0x091216,"
        "drawbox=x=0:y=0:w=iw-1:h=ih-1:color=0x2bcfc1@0.95:t=2,format=yuv420p[fg];"
        "[bg][fg]overlay=20:360:shortest=1,format=yuv420p[v]"
    )
    run(
        [FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-loop", "1",
         "-framerate", str(FPS), "-t", f"{segment.frames/FPS:.6f}", "-i", str(segment.image),
         "-filter_complex", graph, "-map", "[v]", "-frames:v", str(segment.frames),
         "-an", "-r", str(FPS), "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "fast",
         "-crf", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)],
        f"рендер кадра {segment.label}",
    )


def make_audio(output: Path, bulq_seconds: float, meowskis_seconds: float, tail: float) -> None:
    graph = (
        "[2:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
        f"atrim=duration={TITLE_SECONDS:.6f},asetpts=PTS-STARTPTS[head];"
        "[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
        f"atrim=duration={bulq_seconds:.6f},asetpts=PTS-STARTPTS[bulq];"
        f"anullsrc=r=44100:cl=mono:d={VOICE_GAP_SECONDS:.6f}[gap];"
        "[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
        f"atrim=duration={meowskis_seconds:.6f},asetpts=PTS-STARTPTS[meowskis];"
        f"anullsrc=r=44100:cl=mono:d={tail:.6f}[tail];"
        "[head][bulq][gap][meowskis][tail]concat=n=5:v=0:a=1[out]"
    )
    run(
        [FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(BULQ_NARRATION),
         "-i", str(MEOWSKIS_NARRATION), "-i", str(INTRO_STING),
         "-filter_complex", graph, "-map", "[out]",
         "-t", f"{TARGET_SECONDS:.6f}", "-c:a", "pcm_s16le", str(output)],
        "сборка аудиодорожки Reel",
    )


def main() -> None:
    for path in (BULQ_NARRATION, MEOWSKIS_NARRATION, INTRO_STING):
        if not path.is_file():
            raise FileNotFoundError(path)
    images = [
        SEASON / "series_intro_alternative.png",
        EP02 / "images" / "frames" / "s01e02_05.png",
        EP03 / "images" / "frames" / "s01e03_15.png",
        EP04 / "images" / "frames" / "s01e04_02.png",
        EP05 / "images" / "frames" / "s01e05_27.png",
        EP06 / "images" / "scene_17_stop_macro.png",
        EP05 / "images" / "frames" / "s01e05_30.png",
    ]
    for image in images:
        if not image.is_file():
            raise FileNotFoundError(image)

    bulq_seconds = probe_duration(BULQ_NARRATION)
    meowskis_seconds = probe_duration(MEOWSKIS_NARRATION)
    intro_seconds = probe_duration(INTRO_STING)
    if abs(intro_seconds - TITLE_SECONDS) > 0.05:
        raise RuntimeError("Утверждённый sting заставки должен длиться 3,6 секунды.")
    meowskis_start = TITLE_SECONDS + bulq_seconds + VOICE_GAP_SECONDS
    tail = TARGET_SECONDS - meowskis_start - meowskis_seconds
    if tail < 0:
        raise RuntimeError("Сезонная озвучка не помещается в 40 секунд.")
    cues = make_cues(bulq_seconds, meowskis_start, meowskis_seconds)
    write_captions(cues, meowskis_start + meowskis_seconds)

    # Keep the approved 3.6-second series sting on the opening card, then
    # follow the synopsis: beacon, shade, fasteners, map, hold/rail mystery,
    # and the co-host season-wide close.
    frames = [87, 161, 33, 263, 79, 124, 213]
    visual_labels = [
        "season intro", "episode 02 beacon console", "episode 03 shade canopy (no people)",
        "episode 04 fastener tray", "episode 05 three-dimensional map",
        "episode 06 hold/rail stop", "co-host season close",
    ]
    if sum(frames) != round(TARGET_SECONDS * FPS):
        raise RuntimeError("Сумма кадров визуального плана не равна 40 секундам.")
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render_", dir=WORK_ROOT) as temp:
        work = Path(temp)
        canopy_crop = work / "e03_shade_canopy.png"
        run(
            [FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(images[2]),
             "-vf", "crop=500:280:650:0", "-frames:v", "1", str(canopy_crop)],
            "подготовка кадра тени E03 без людей",
        )
        images[2] = canopy_crop
        segments: list[Path] = []
        for index, (image, frame_count) in enumerate(zip(images, frames)):
            path = work / f"segment_{index:02d}.mp4"
            render_segment(Segment(image, frame_count, f"сегмент {index+1}"), path, work)
            segments.append(path)
        concat_path = work / "segments.txt"
        concat_path.write_text(
            "".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n" for p in segments),
            encoding="utf-8",
        )
        base_video = work / "base.mp4"
        run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(concat_path), "-c", "copy", "-movflags", "+faststart", str(base_video)],
            "склейка визуальных сегментов")
        captioned = work / "captioned.mp4"
        run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(base_video),
             "-vf", f"ass={OUTPUT_ASS.resolve().as_posix()}", "-an", "-r", str(FPS),
             "-c:v", "libx264", "-preset", "medium", "-crf", "25", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(captioned)], "вжигание ASS-субтитров")
        audio = work / "audio.wav"
        make_audio(audio, bulq_seconds, meowskis_seconds, tail)
        HERE.mkdir(parents=True, exist_ok=True)
        run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(captioned),
             "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-t", f"{TARGET_SECONDS:.6f}",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-ar", "44100",
             "-movflags", "+faststart", str(OUTPUT)], "сведение финального Reel")

    info = json.loads(run([FFPROBE, "-v", "error", "-show_entries",
                           "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels,duration:format=duration,size",
                           "-of", "json", str(OUTPUT)], "ffprobe финального Reel"))
    streams = info["streams"]
    video = next((x for x in streams if x.get("codec_type") == "video"), {})
    audio = next((x for x in streams if x.get("codec_type") == "audio"), {})
    duration = float(info["format"]["duration"])
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise RuntimeError("Финальный Reel должен быть H.264/AAC.")
    if (video.get("width"), video.get("height")) != (WIDTH, HEIGHT):
        raise RuntimeError("Неверный размер кадра итогового Reel.")
    if abs(duration - TARGET_SECONDS) > 0.1:
        raise RuntimeError(f"Неверная длительность Reel: {duration:.3f} секунд.")
    run([FFMPEG, "-hide_banner", "-v", "error", "-i", str(OUTPUT), "-f", "null", "-"],
        "полное декодирование финального Reel")
    report = {
        "output": OUTPUT.name,
        "duration_seconds": duration,
        "resolution": [WIDTH, HEIGHT],
        "fps": FPS,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate", 0)),
        "audio_channels": int(audio.get("channels", 0)),
        "intro_sting_source": INTRO_STING.name,
        "intro_sting_seconds": intro_seconds,
        "intro_sting_note": "approved logo sting with two clicks and a soft ship hum; no synthesized melody",
        "caption_cues": len(cues),
        "narration_durations_seconds": {"Bulq": bulq_seconds, "Mr. Meowskis": meowskis_seconds},
        "voice_end_seconds": round(meowskis_start + meowskis_seconds, 3),
        "cta_start_seconds": round(max(meowskis_start + meowskis_seconds, TARGET_SECONDS - CTA_SECONDS), 3),
        "cta_duration_seconds": round(TARGET_SECONDS - max(meowskis_start + meowskis_seconds, TARGET_SECONDS - CTA_SECONDS), 3),
        "caption_timing": "estimated by character weight within the two generated narration clips; no forced alignment",
        "speech_sources": [BULQ_NARRATION.name, MEOWSKIS_NARRATION.name],
        "voice_map": {"Bulq": "voice-07", "Mr. Meowskis": "voice-08"},
        "season_synopsis": BULQ_TEXT + " " + MEOWSKIS_TEXT,
        "season_wide_visuals": visual_labels,
        "visual_timeline_seconds": [
            {
                "label": label,
                "start": round(sum(frames[:index]) / FPS, 3),
                "end": round(sum(frames[:index + 1]) / FPS, 3),
            }
            for index, label in enumerate(visual_labels)
        ],
        "full_decode_passed": True,
        "size_bytes": OUTPUT.stat().st_size,
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
