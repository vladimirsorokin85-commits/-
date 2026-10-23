#!/usr/bin/env python3
"""Two 9:16 reels («Их нравы») cut from the chapter voice-overs of the long video.
Voice = exact cut of the chapter narration (no extra TTS). Visuals = long-video frames on a blurred 9:16 background.
Captions and plates are PNG overlays made with PIL (this ffmpeg build has no drawtext).
Stage: python3 reels_dr.py [name ...]  -> reels/reel_<name>_9x16.mp4 (with branded short ident)."""
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/user/-/video_studio")
TMP = Path("/tmp/polevaya")
OUT = ROOT / "polevaya" / "reels"
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "toolkit" / "fonts" / "RussoOne-Regular.ttf"
MUSIC = ROOT / "music_catalog" / "dnb_neuro_174.ogg"
ASSETS = ROOT / "assets_polevaya"
TL = json.load(open(TMP / "timeline.json"))
FF = "ffmpeg"
CUT_MAX = 38.0      # reel voice ends at a sentence boundary before this (s)
TAIL = 2.5          # closing card with the long-video pointer (s)
FT = {sz: ImageFont.truetype(str(FONT), sz) for sz in (118, 84, 56, 40)}

REELS = [
    {"name": "cenzor", "body": 1, "imgs": ["dr_03", "dr_11", "dr_05", "dr_14"],
     "hook": ["ЦЕНЗОР ЧИТАЛ", "ПИСЬМА СОЛДАТ"], "tail": "ПОЛНЫЙ ВЫПУСК «ИХ НРАВЫ» — В ДЛИННОМ ВИДЕО"},
    {"name": "otkrytka", "body": 2, "imgs": ["dr_06", "dr_13", "dr_07", "dr_12"],
     "hook": ["ОТКРЫТКА", "«Я ЖИВ»"], "tail": "ПОЛНЫЙ ВЫПУСК «ИХ НРАВЫ» — В ДЛИННОМ ВИДЕО"},
    {"name": "pismo", "body": 3, "imgs": ["dr_16", "dr_15", "dr_10", "dr_01"],
     "hook": ["ПИСЬМО ПРИШЛО", "ПОСЛЕ ЧЕЛОВЕКА"], "tail": "ПОЛНЫЙ ВЫПУСК «ИХ НРАВЫ» — В ДЛИННОМ ВИДЕО"},
]


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise SystemExit(f"FFMPEG FAILED rc={r.returncode}: {r.stderr[-800:]}")


def strip(text, sz, fill, path, box=None, stroke=8, pad_w=40):
    """Transparent PNG with one line of text (optional plate). Returns width."""
    f = FT[sz]
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), text, font=f, stroke_width=stroke)
    if r - l > 980:  # shrink long captions so they never leave the 1080 px frame
        f = ImageFont.truetype(str(FONT), int(sz * 980 / (r - l)))
        l, t, r, b = probe.textbbox((0, 0), text, font=f, stroke_width=stroke)
    w, h = r - l, b - t
    W = min(1080, w + 2 * pad_w + 20)
    img = Image.new("RGBA", (W, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box:
        d.rounded_rectangle([0, 0, W - 1, h + 39], radius=22, fill=box)
    x = (W - w) // 2 - l
    d.text((x, 20 - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    img.save(path)
    return W


def build(rc):
    body_seg = next(s for s in TL["segments"] if s["kind"] == "body" and s["chapter"] == rc["body"])
    vt = body_seg["voice_t0"]
    sents = body_seg["sentences"]
    n = max(i for i, s in enumerate(sents) if s["t1"] <= CUT_MAX)
    end = sents[n]["t1"] + 0.25
    D = end + TAIL
    name = rc["name"]
    d = OUT / name
    d.mkdir(exist_ok=True)

    # 1) voice: exact cut of the chapter voice-over; music bed of the same length
    voice = d / "voice.wav"
    run([FF, "-y", "-v", "error", "-i", str(TMP / f"v_body{rc['body']}.wav"), "-t", f"{end:.3f}",
         "-af", f"afade=t=out:st={end-0.2:.3f}:d=0.2", str(voice)])
    music = d / "music.wav"
    run([FF, "-y", "-v", "error", "-ss", "40", "-i", str(MUSIC), "-t", f"{D:.3f}",
         "-af", f"afade=t=in:d=0.6,afade=t=out:st={D-2.0:.3f}:d=2.0", str(music)])

    # 2) video: one file per image (blurred 9:16 background + sharp 16:9 frame), then a concat list
    imgs = rc["imgs"]
    seg_d = D / len(imgs)
    seg_files = []
    for i, im in enumerate(imgs):
        sf = d / f"seg{i}.mp4"
        run([FF, "-y", "-v", "error", "-loop", "1", "-framerate", "60", "-t", f"{seg_d:.3f}",
             "-i", str(ASSETS / f"{im}.jpg"),
             "-filter_complex",
             "[0:v]split[a][b];"
             "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:4,"
             "eq=brightness=-0.12:saturation=0.9[bg];"
             "[b]scale=1080:-2,setsar=1[fg];"
             "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
             f"fade=t=in:st=0:d=0.3,fade=t=out:st={seg_d-0.3:.3f}:d=0.3,format=yuv420p[v]",
             "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", "60",
             "-pix_fmt", "yuv420p", str(sf)])
        seg_files.append(sf)
    lst = d / "segs.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seg_files), encoding="utf-8")
    base = d / "base.mp4"
    run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(base)])

    # 3) overlays: hook plates, caption lines per voice chunk, closing card, brand line
    overlays = []  # (png, x, y, t0, t1)
    for j, line in enumerate(rc["hook"]):
        pth = d / f"hook{j}.png"
        W = strip(line, 118, (255, 255, 255, 255), pth, box=(235, 40, 40, 215), stroke=10, pad_w=30)
        overlays.append((pth, (1080 - W) // 2, 300 + j * 150, 0.0, D))
    subs = [s for s in TL["subs"] if s["t0"] >= vt - 0.05 and s["t1"] <= vt + end + 0.05]
    for k, s in enumerate(subs):
        pth = d / f"sub{k:03d}.png"
        W = strip(" ".join(w for w, _ in s["words"]), 84, (255, 255, 255, 255), pth, stroke=8)
        overlays.append((pth, (1080 - W) // 2, 1420, s["t0"] - vt, s["t1"] - vt))
    pth = d / "tail.png"
    W = strip(rc["tail"], 56, (255, 255, 255, 255), pth, box=(0, 0, 0, 170), stroke=0, pad_w=24)
    overlays.append((pth, (1080 - W) // 2, 1650, D - TAIL, D))
    pth = d / "brand.png"
    W = strip("В ОКОПЕ · ИХ НРАВЫ", 40, (255, 204, 0, 255), pth, stroke=0, pad_w=20)
    overlays.append((pth, (1080 - W) // 2, 120, 0.0, D))

    # captions composited frame by frame in Python (ffmpeg overlays used too much memory here)
    audio = d / "audio.m4a"
    run([FF, "-y", "-v", "error", "-i", str(music), "-i", str(voice), "-filter_complex",
         # music bed: pulled well down (-24 LUFS) and ducked under the voice; voice at -16 LUFS
         "[0:a]loudnorm=I=-24:TP=-3:LRA=7[m];"
         "[1:a]loudnorm=I=-16:TP=-1.5:LRA=7,asplit=2[vk][vm];"
         "[m][vk]sidechaincompress=threshold=0.025:ratio=6:attack=8:release=350[duck];"
         "[duck][vm]amix=inputs=2:weights=1 1.2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=7[aout]",
         "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(audio)])
    loaded = [(Image.open(pth).convert("RGBA"), x, y, t0, t1) for pth, x, y, t0, t1 in overlays]
    W, H, FPS = 1080, 1920, 60
    nframes = int(round(D * FPS))
    dec = subprocess.Popen([FF, "-v", "error", "-i", str(base), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    body = d / f"{name}_body.mp4"
    enc = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                            "-c:a", "copy", "-t", f"{D:.3f}", str(body)], stdin=subprocess.PIPE, stderr=open(d / "enc.log", "w"))
    fsize = W * H * 3
    for i in range(nframes):
        raw = dec.stdout.read(fsize)
        if len(raw) < fsize:
            break
        t = i / FPS
        frame = Image.frombytes("RGB", (W, H), raw).convert("RGBA")
        for img, x, y, t0, t1 in loaded:
            if t0 <= t <= t1:
                frame.alpha_composite(img, (x, y))
        try:
            enc.stdin.write(frame.convert("RGB").tobytes())
        except BrokenPipeError:
            raise SystemExit(f"encoder died at frame {i}: " + open(d / "enc.log").read()[-500:])
    enc.stdin.close()
    enc.wait()
    dec.stdout.close()
    dec.wait()
    if enc.returncode:
        raise SystemExit(f"encode failed rc={enc.returncode}")

    # 4) branded short ident in front
    final = OUT / f"reel_{name}_9x16.mp4"
    subprocess.run(["python3", str(ROOT / "polevaya" / "prepend60.py"), str(body), str(final), "9x16"],
                   check=True, env=dict(os.environ, IDENT="short"),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(name, f"voice {end:.2f}s, body {D:.2f}s, captions {len(subs)}, cut at sentence {n+1}/{len(sents)}", flush=True)
    return final


if __name__ == "__main__":
    import sys
    only = sys.argv[1:] or [r["name"] for r in REELS]
    for rc in REELS:
        if rc["name"] in only:
            build(rc)
