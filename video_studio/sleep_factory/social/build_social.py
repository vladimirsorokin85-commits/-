#!/usr/bin/env python3
"""Build two vertical, captioned pilot teasers and copy-ready YouTube metadata."""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
EPISODE = PROJECT / "season_01" / "episode_01"
EXPORTS = EPISODE / "exports"
IMAGES = EPISODE / "images"
SOCIAL = PROJECT / "social"
REELS = SOCIAL / "reels"
TEMP = PROJECT / "out" / "social_render"
TIMELINE = EXPORTS / "s01e01_audio_mix.timeline.json"
MASTER = EXPORTS / "s01e01_audio_mix.mp3"
FPS = 24
WIDTH, HEIGHT = 720, 1280


def find_ffmpeg() -> str:
    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise SystemExit("Не найден FFmpeg. Установите FFmpeg или imageio-ffmpeg.") from exc


FFMPEG = find_ffmpeg()


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Segment:
    image: str
    frames: int


@dataclass(frozen=True)
class Reel:
    slug: str
    scene_id: str
    title: str
    segments: tuple[Segment, ...]
    cues: tuple[Cue, ...]


REEL_SPECS = (
    Reel(
        slug="reel_01_key_without_door",
        scene_id="s01e01_a04",
        title="Ключ без двери",
        segments=(
            Segment("s01e01_03_ai_console.jpg", 96),
            Segment("podcast_cockpit_key.jpg", 147),
            Segment("s01e01_05_old_key_detail.jpg", 81),
            Segment("s01e01_07_inventory_scan.jpg", 56),
            Segment("s01e01_05_old_key_detail.jpg", 287),
            Segment("s01e01_04_station_salvage_depot.jpg", 233),
        ),
        cues=(
            Cue(0.00, 4.00, "Вот видишь, ИИ понимает\\Nдраматургию лучше нас."),
            Cue(4.00, 10.10, "Есть предмет, есть заказчик,\\Nнет двери, а оплату ещё\\Nможно проверить."),
            Cue(10.10, 13.40, "Всё необходимое\\Nдля приличной истории."),
            Cue(13.40, 15.80, "Ключ лежит у меня на столе."),
            Cue(15.80, 21.00, "Он холодный даже в тёплой\\Nкаюте, хотя это, скорее всего,"),
            Cue(21.00, 27.70, "потому, что стол металлический,\\Nа не потому, что в нём живёт\\Nдревнее проклятие."),
            Cue(27.70, 30.80, "Проклятие — это лот с хвостом:"),
            Cue(30.80, 34.20, "спрос низкий, гарантийный\\Nсрок мутный,"),
            Cue(34.20, 37.50, "а возврат потом оформляют\\Nна наследников."),
        ),
    ),
    Reel(
        slug="reel_02_cosmic_bureaucracy",
        scene_id="s01e01_b12",
        title="Космическая бюрократия",
        segments=(
            Segment("s01e01_13_archive_registry.jpg", 207),
            Segment("s01e01_14_registry_stamp.jpg", 220),
            Segment("s01e01_12_empty_storage.jpg", 154),
            Segment("s01e01_13_archive_registry.jpg", 105),
            Segment("s01e01_14_registry_stamp.jpg", 209),
        ),
        cues=(
            Cue(0.00, 3.40, "Сведения из реестра\\Nвременного хранения."),
            Cue(3.40, 8.60, "Ключ принят на основании акта\\Nо неопределённой принадлежности."),
            Cue(8.60, 13.20, "Ответственным за сохранность\\Nназначен отдел, который"),
            Cue(13.20, 17.80, "не принимает посетителей\\Nбез предварительного разрешения."),
            Cue(17.80, 22.20, "Разрешение выдаётся после\\Nподтверждения цели визита."),
            Cue(22.20, 26.70, "Подтверждение цели требует\\Nуказать владельца предмета."),
            Cue(26.70, 28.70, "Владелец не установлен."),
            Cue(28.70, 33.00, "В журнале обращений имеется\\Nзапрос о возврате ключа."),
            Cue(33.00, 895 / FPS, "Запрос отклонён из-за отсутствия\\Nподписи владельца."),
        ),
    ),
)


def ffmpeg_run(args: list[str], label: str) -> None:
    result = subprocess.run([FFMPEG, *args], text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{label} не удался:\n{detail[-4000:]}")


def scene_start(scene_id: str) -> float:
    data = json.loads(TIMELINE.read_text(encoding="utf-8"))
    scene = next(item for item in data["scenes"] if item["id"] == scene_id)
    return float(scene["start"])


def ass_time(seconds: float) -> str:
    total_cs = round(seconds * 100)
    hours, rem = divmod(total_cs, 360000)
    minutes, rem = divmod(rem, 6000)
    whole, centiseconds = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{whole:02d}.{centiseconds:02d}"


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    whole, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"


def write_subtitles(reel: Reel, duration: float) -> tuple[Path, Path]:
    ass_path = REELS / f"{reel.slug}.ass"
    srt_path = REELS / f"{reel.slug}.srt"
    ass = [
        "[Script Info]",
        "Title: " + reel.title,
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,DejaVu Sans,42,&H00FFFFFF,&H000000FF,&HCC061014,&H99060C10,-1,0,0,0,100,100,0,0,1,3,1,2,48,48,170,1",
        "Style: Brand,DejaVu Sans,25,&H00C8E8E2,&H000000FF,&HCC061014,&H99060C10,-1,0,0,0,100,100,0,0,1,2,1,8,40,40,78,1",
        "Style: CTA,DejaVu Sans,27,&H008AD0FF,&H000000FF,&HCC061014,&H99060C10,-1,0,0,0,100,100,0,0,1,3,1,8,40,40,138,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,{ass_time(duration)},Brand,,0,0,0,,МАГАЗИНЧИК ДЯДЮШКИ «БУЛЬК» · ПИЛОТ",
        f"Dialogue: 1,0:00:00.00,0:00:02.50,CTA,,0,0,0,,{reel.title.upper()}",
    ]
    srt: list[str] = []
    for index, cue in enumerate(reel.cues, start=1):
        cue_end = min(cue.end, duration)
        text = cue.text
        ass.append(
            f"Dialogue: 2,{ass_time(cue.start)},{ass_time(cue_end)},Caption,,0,0,0,,{text}"
        )
        srt.append(
            f"{index}\n{srt_time(cue.start)} --> {srt_time(cue_end)}\n"
            + cue.text.replace("\\N", "\n") + "\n"
        )
    cta_start = max(duration - 3.0, 0)
    ass.append(
        f"Dialogue: 3,{ass_time(cta_start)},{ass_time(duration)},CTA,,0,0,0,,ПОЛНЫЙ ВЫПУСК — НА YOUTUBE"
    )
    ass_path.write_text("\n".join(ass) + "\n", encoding="utf-8")
    srt_path.write_text("\n".join(srt).rstrip() + "\n", encoding="utf-8")
    return ass_path, srt_path


def render_segment(image: Path, frames: int, output: Path) -> None:
    duration = frames / FPS
    graph = (
        "[0:v]split=2[bgsrc][fgsrc];"
        "[bgsrc]scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=720:1280,gblur=sigma=28,eq=brightness=-0.28:saturation=0.72,"
        "zoompan=z='min(zoom+0.000035,1.025)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x1280:fps=24,"
        "trim=end_frame=" + str(frames) + ",setpts=PTS-STARTPTS[bg];"
        "[fgsrc]scale=680:382:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=680:382:(ow-iw)/2:(oh-ih)/2:color=0x091216,"
        "drawbox=x=0:y=0:w=iw-1:h=ih-1:color=0x24cfc2@0.95:t=2,format=yuv420p[fg];"
        "[bg][fg]overlay=20:360:shortest=1,format=yuv420p[v]"
    )
    ffmpeg_run(
        [
            "-hide_banner", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.6f}",
            "-i", str(image), "-filter_complex", graph, "-map", "[v]",
            "-frames:v", str(frames), "-an", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", "25",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ],
        f"рендер кадра {image.name}",
    )


def build_reel(reel: Reel) -> dict[str, object]:
    if not MASTER.is_file() or not TIMELINE.is_file():
        raise FileNotFoundError("Не найден мастер-аудио или монтажный таймлайн пилота.")
    REELS.mkdir(parents=True, exist_ok=True)
    folder = TEMP / reel.slug
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    total_frames = sum(segment.frames for segment in reel.segments)
    duration = total_frames / FPS
    audio_start = scene_start(reel.scene_id)
    ass_path, srt_path = write_subtitles(reel, duration)

    segment_paths: list[Path] = []
    for index, segment in enumerate(reel.segments):
        image = IMAGES / segment.image
        if not image.is_file():
            raise FileNotFoundError(image)
        output = folder / f"segment_{index:02d}.mp4"
        render_segment(image, segment.frames, output)
        segment_paths.append(output)

    concat_file = folder / "concat.txt"
    concat_file.write_text(
        "".join("file '" + str(path.resolve()).replace("'", "'\\''") + "'\n" for path in segment_paths),
        encoding="utf-8",
    )
    base_video = folder / "base.mp4"
    ffmpeg_run(
        ["-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(base_video)],
        "склейка кадров",
    )

    subtitled = folder / "subtitled.mp4"
    subtitle_path = ass_path.resolve().as_posix()
    ffmpeg_run(
        ["-hide_banner", "-y", "-loglevel", "error", "-i", str(base_video),
         "-vf", f"ass={subtitle_path}", "-an", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "medium", "-crf", "26",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(subtitled)],
        "вжигание субтитров",
    )

    output = REELS / f"{reel.slug}.mp4"
    ffmpeg_run(
        ["-hide_banner", "-y", "-loglevel", "error", "-i", str(subtitled),
         "-ss", f"{audio_start:.3f}", "-i", str(MASTER), "-map", "0:v:0", "-map", "1:a:0",
         "-frames:v", str(total_frames), "-t", f"{duration:.6f}", "-shortest",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-ac", "1", "-ar", "44100",
         "-movflags", "+faststart", str(output)],
        "сведение вертикального ролика",
    )
    return {
        "file": str(output.relative_to(PROJECT)),
        "captions": str(srt_path.relative_to(PROJECT)),
        "duration_seconds": round(duration, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "audio_start_seconds": audio_start,
        "size_bytes": output.stat().st_size,
    }


def create_social_pack() -> Path:
    pack = SOCIAL / "social_pack_v1_0.zip"
    members = [
        SOCIAL / "README.md",
        SOCIAL / "YOUTUBE_DESCRIPTION.md",
        SOCIAL / "YOUTUBE_DESCRIPTION.txt",
        *(REELS / f"{reel.slug}.{suffix}" for reel in REEL_SPECS for suffix in ("mp4", "srt")),
    ]
    with zipfile.ZipFile(pack, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for member in members:
            archive.write(member, member.relative_to(SOCIAL.parent))
    with zipfile.ZipFile(pack) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"Повреждённый элемент в архиве соцсетей: {bad_member}")
    return pack


def main() -> None:
    results = [build_reel(reel) for reel in REEL_SPECS]
    (SOCIAL / "render_manifest.json").write_text(
        json.dumps({"status": "rendered", "reels": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pack = create_social_pack()
    for item in results:
        print(item)
    print({"social_pack": str(pack.relative_to(PROJECT)), "size_bytes": pack.stat().st_size})


if __name__ == "__main__":
    main()
