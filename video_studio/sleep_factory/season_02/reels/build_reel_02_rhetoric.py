#!/usr/bin/env python3
"""Build a separate vertical 40-second Reel announcing the S02 tone shift."""
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
SEASON_01 = SEASON.parent / "season_01"
EPISODE = SEASON / "episode_01"
INTRO_IMAGE = SEASON_01 / "series_intro_alternative.png"
EPISODE_IMAGE = EPISODE / "images" / "episode_01_cover.png"
PUMP_IMAGE = EPISODE / "images" / "pump_valve_macro.png"
SPA_IMAGE = EPISODE / "images" / "abandoned_spa_service_bay.png"
INTRO_STING = SEASON_01 / "series_micro_jingle.wav"
BULQ_AUDIO = HERE / "narration_bulq.mp3"
MEOWSKIS_AUDIO = HERE / "narration_meowskis.mp3"
OUTPUT = HERE / "reel_01_rhetoric_shift.mp4"
OUTPUT_SRT = HERE / "reel_01_rhetoric_shift.srt"
OUTPUT_ASS = HERE / "reel_01_rhetoric_shift.ass"
REPORT = HERE / "reel_01_rhetoric_shift.build_report.json"
WORK_ROOT = HERE.parents[3] / ".arena" / "reel_02_rhetoric_work"
FPS = 24
WIDTH, HEIGHT = 720, 1280
TARGET_SECONDS = 40.0
TITLE_SECONDS = 3.6
VOICE_GAP_SECONDS = 0.8
CTA_SECONDS = 4.0

BULQ_TEXT = (
    "Первый сезон я называл хлам «лотом с потенциалом». Хватит вежливости. "
    "Дальше — взрослая грязная чёрная комедия: мат, пошлость и космическое дерьмо. "
    "Первая серия уже пахнет закрытым спа. Мявскис, держи фильтр. Не нюхай, это товар."
)
MEOWSKIS_TEXT = (
    "Проверки останутся точными. Но утечка — не «ароматическое событие», "
    "а ебаный насос, собранный задом наперёд. За «свежесть» всё ещё списывают жетоны. "
    "Лот подтвердит давление. Запах Бульк назовёт сам. «Премиальная вонь» — старт второго сезона."
)
BULQ_CAPTIONS = [
    "Первый сезон я называл хлам",
    "«лотом с потенциалом». Хватит вежливости.",
    "Дальше — взрослая грязная чёрная комедия:",
    "мат, пошлость и космическое дерьмо.",
    "Первая серия уже пахнет закрытым спа.",
    "Мявскис, держи фильтр.",
    "Не нюхай, это товар.",
]
MEOWSKIS_CAPTIONS = [
    "Проверки останутся точными.",
    "Но утечка — не «ароматическое событие»,",
    "а ебаный насос, собранный задом наперёд.",
    "За «свежесть» всё ещё списывают жетоны.",
    "Лот подтвердит давление.",
    "Запах Бульк назовёт сам.",
    "«Премиальная вонь» — старт второго сезона.",
]


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
    pan: str


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
        raise RuntimeError("Пустой текст или нулевая длительность голосового фрагмента.")
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
        "[Script Info]", "Title: Второй сезон — смена риторики", "ScriptType: v4.00+",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,DejaVu Sans,39,&H00FFFFFF,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,3,1,2,42,42,190,1",
        "Style: Brand,DejaVu Sans,29,&H00D6EEE8,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,2,1,8,38,38,72,1",
        "Style: CTA,DejaVu Sans,34,&H00F7EBD4,&H000000FF,&HCC071115,&H99070D11,-1,0,0,0,100,100,0,0,1,3,1,2,48,48,260,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,{ass_stamp(TITLE_SECONDS)},{ass_stamp(TARGET_SECONDS-CTA_SECONDS)},Brand,,0,0,0,,ВТОРОЙ СЕЗОН • БЕЗ ЭВФЕМИЗМОВ",
        f"Dialogue: 1,{ass_stamp(TARGET_SECONDS-CTA_SECONDS)},{ass_stamp(TARGET_SECONDS)},CTA,,0,0,0,,ПРЕМИАЛЬНАЯ ВОНЬ • ПЕРВАЯ СЕРИЯ",
    ]
    for index, cue in enumerate(cues, 1):
        srt_lines.extend((str(index), f"{stamp(cue.start)} --> {stamp(cue.end)}", cue.text, ""))
        ass_lines.append(
            f"Dialogue: 2,{ass_stamp(cue.start)},{ass_stamp(cue.end)},Caption,,0,0,0,,{wrap_ass(cue.text)}"
        )
    OUTPUT_SRT.write_text("\n".join(srt_lines).rstrip() + "\n", encoding="utf-8")
    OUTPUT_ASS.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")


def render_segment(segment: Segment, output: Path) -> None:
    duration = segment.frames / FPS
    graph = (
        "[0:v]split=2[bgsrc][fgsrc];"
        "[bgsrc]scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=720:1280,gblur=sigma=26,eq=brightness=-0.28:saturation=0.75,"
        "zoompan=z='min(zoom+0.000035,1.035)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"trim=end_frame={segment.frames},setpts=PTS-STARTPTS[bg];"
        "[fgsrc]scale=680:382:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=680:382:(ow-iw)/2:(oh-ih)/2:color=0x091216,"
        "drawbox=x=0:y=0:w=iw-1:h=ih-1:color=0x2bcfc1@0.95:t=2,format=yuv420p[fg];"
        "[bg][fg]overlay=20:350:shortest=1,format=yuv420p[v]"
    )
    run(
        [FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-loop", "1",
         "-framerate", str(FPS), "-t", f"{duration:.6f}", "-i", str(segment.image),
         "-filter_complex", graph, "-map", "[v]", "-frames:v", str(segment.frames),
         "-an", "-r", str(FPS), "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "fast",
         "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)],
        f"рендер кадра {segment.label}",
    )


def make_audio(output: Path, bulq_seconds: float, meowskis_seconds: float,
               meowskis_start: float, tail: float) -> None:
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
        [FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(BULQ_AUDIO),
         "-i", str(MEOWSKIS_AUDIO), "-i", str(INTRO_STING),
         "-filter_complex", graph, "-map", "[out]", "-t", f"{TARGET_SECONDS:.6f}",
         "-c:a", "aac", "-b:a", "160k", "-ac", "1", "-ar", "44100", "-movflags", "+faststart",
         str(output)],
        "сборка аудиодорожки Reel",
    )


def main() -> None:
    for path in (INTRO_IMAGE, EPISODE_IMAGE, PUMP_IMAGE, SPA_IMAGE, INTRO_STING, BULQ_AUDIO, MEOWSKIS_AUDIO):
        if not path.is_file():
            raise FileNotFoundError(path)
    if " ".join(BULQ_CAPTIONS) != BULQ_TEXT or " ".join(MEOWSKIS_CAPTIONS) != MEOWSKIS_TEXT:
        raise RuntimeError("Текст Reel и субтитры не совпадают.")

    bulq_seconds = probe_duration(BULQ_AUDIO)
    meowskis_seconds = probe_duration(MEOWSKIS_AUDIO)
    sting_seconds = probe_duration(INTRO_STING)
    if abs(sting_seconds - TITLE_SECONDS) > 0.05:
        raise RuntimeError("Утверждённый sting заставки должен длиться 3,6 секунды.")
    meowskis_start = TITLE_SECONDS + bulq_seconds + VOICE_GAP_SECONDS
    meowskis_end = meowskis_start + meowskis_seconds
    cta_start = TARGET_SECONDS - CTA_SECONDS
    tail = TARGET_SECONDS - TITLE_SECONDS - bulq_seconds - VOICE_GAP_SECONDS - meowskis_seconds
    if tail < 0 or meowskis_end > cta_start + 0.1:
        raise RuntimeError("Две сезонные реплики не помещаются в Reel с финальным CTA.")

    cues = make_cues(bulq_seconds, meowskis_start, meowskis_seconds)
    write_captions(cues, meowskis_end)
    # Cut on clean visual beats; rounding cumulative boundaries prevents frame drift.
    visual_spans = [
        (0.0, TITLE_SECONDS, INTRO_IMAGE, "approved series intro"),
        (TITLE_SECONDS, 10.5, PUMP_IMAGE, "reversed valve macro"),
        (10.5, meowskis_start, SPA_IMAGE, "abandoned spa service bay"),
        (meowskis_start, 27.5, EPISODE_IMAGE, "two co-hosts announce S02E01"),
        (27.5, cta_start, PUMP_IMAGE, "pump detail under technical line"),
        (cta_start, TARGET_SECONDS, EPISODE_IMAGE, "S02E01 CTA"),
    ]
    frame_marks = [round(span[0] * FPS) for span in visual_spans]
    frame_marks.append(round(TARGET_SECONDS * FPS))
    frame_counts = [frame_marks[i+1]-frame_marks[i] for i in range(len(frame_marks)-1)]
    if any(count <= 0 for count in frame_counts) or sum(frame_counts) != round(TARGET_SECONDS * FPS):
        raise RuntimeError("Сумма кадров визуального плана не равна 40 секундам.")
    images = [span[2] for span in visual_spans]
    labels = [span[3] for span in visual_spans]

    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render_", dir=WORK_ROOT) as temp:
        work = Path(temp)
        segments: list[Path] = []
        for index, (image, frame_count, label) in enumerate(zip(images, frame_counts, labels)):
            path = work / f"segment_{index:02d}.mp4"
            if frame_count <= 0:
                continue
            render_segment(Segment(image, frame_count, label, "center"), path)
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
             "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(captioned)], "вжигание титров")
        audio = work / "audio.m4a"
        make_audio(audio, bulq_seconds, meowskis_seconds, meowskis_start, tail)
        run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", str(captioned),
             "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-t", f"{TARGET_SECONDS:.6f}",
             "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", str(OUTPUT)],
            "сборка финального MP4")

    run([FFMPEG, "-hide_banner", "-v", "error", "-i", str(OUTPUT), "-f", "null", "-"],
        "полное декодирование финального Reel")
    probe = json.loads(run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,nb_frames",
         "-of", "json", str(OUTPUT)], "ffprobe итогового Reel"))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    duration = float(probe["format"]["duration"])
    if abs(duration - TARGET_SECONDS) > 0.08:
        raise RuntimeError(f"Итоговый Reel длится {duration:.3f} с, ожидалось 40 с.")
    report = {
        "title": "Бульк меняет риторику — второй сезон без сахарной пудры",
        "duration_seconds": round(duration, 3),
        "video": video,
        "audio": audio,
        "size_bytes": int(probe["format"]["size"]),
        "speech_seconds": round(bulq_seconds + meowskis_seconds, 3),
        "speech_share_estimate": round((bulq_seconds + meowskis_seconds) / TARGET_SECONDS, 4),
        "subtitle_timing": "Estimated by character weight within each generated clip; not word-level forced alignment.",
        "visuals": ["approved season intro", "reverse-valve macro", "empty abandoned spa service bay", "S02E01 cover with only the two canon co-hosts"],
        "series_voice_tags": {"Bulq": "voice-07", "Mr. Meowskis": "voice-08"},
        "speech_tool_voice_ids": {"Bulq": "voice-09", "Mr. Meowskis": "voice-10"},
        "intro_sting_seconds": round(sting_seconds, 3),
        "full_decode_passed": True,
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
