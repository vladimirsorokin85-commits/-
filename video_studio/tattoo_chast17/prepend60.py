"""Prepend the brand ident to a 60 fps body without changing the shared brand/ident.py (which stays at 30 fps).
Usage: python3 prepend60.py <body.mp4> <out.mp4> [9x16|16x9]"""
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/user/-/video_studio")
sys.path.insert(0, str(ROOT / "brand"))
import ident  # noqa: E402

FPS60 = 60
ident.FPS = FPS60
ident.TMP = Path("/tmp/tattoo_chast17/ident60")  # separate cache: 60 fps idents never collide with the 30 fps brand cache
ident.TMP.mkdir(parents=True, exist_ok=True)
body, out = sys.argv[1], sys.argv[2]
fmt = sys.argv[3] if len(sys.argv) > 3 else "16x9"
path = ident.TMP / f"ident_{fmt}_{ident.KIND}.mp4"
if not path.exists():  # build once; run `prepend60.py` for one format before parallel jobs
    path = ident.build(fmt)
    path = Path(path)
subprocess.run([ident.FFMPEG, "-y", "-v", "error", "-i", str(path), "-i", body, "-filter_complex",
                f"[0:v]setsar=1,fps={FPS60}[v0];[1:v]setsar=1,fps={FPS60}[v1];"
                "[0:a]aresample=44100,aformat=channel_layouts=mono[a0];[1:a]aresample=44100,aformat=channel_layouts=mono[a1];"
                "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
print("done", out)
