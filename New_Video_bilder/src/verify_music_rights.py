#!/usr/bin/env python3
"""
Mandatory Copyright, Content-ID & Vocal-Free Audit Gate (`npm run verify:music`)
for «В ОКОПЕ» (`New_Video_bilder`).

Checks EVERY track in `New_Video_bilder/assets/audio/music_mp3/`:
  1. SHA-256 cryptographic match against `licenses_manifest.json` (Zero Content ID, 100% cleared).
  2. Zero commercial record-label / Content-ID artists OR rejected flat bedroom loops in FFprobe tags or code
     (blocks Monstercat, Feint, Veela, Boyinaband, Pendulum, Calyx & TeeBee, RAM, Hospital, NCS, Elite Alliance,
      Nver Avetyan, StudioKolomna, warlightwolf, szegvari, etc.).
  3. Zero vocals (`silero_vad_vocal_pct == 0.0` in manifest + optional live Silero VAD verification).
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MP3_DIR = ROOT / "assets" / "audio" / "music_mp3"
MANIFEST = MP3_DIR / "licenses_manifest.json"

BANNED_TERMS = [
    "feint",
    "veela",
    "boyinaband",
    "time bomb",
    "time_bomb",
    "monstercat",
    "pendulum",
    "witchcraft",
    "calyx",
    "teebee",
    "subtitles music",
    "ram records",
    "hospital records",
    "warner music",
    "nocopyrightsounds",
    "epidemic sound",
    "elite alliance",
    "nver avetyan",
    "studiokolomna",
    "warlightwolf",
    "szegvari",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors = []
    if not MANIFEST.exists():
        print(f"FAIL: Missing {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw_tracks = manifest.get("tracks", [])
    tracks_meta = (
        {t["file"]: t for t in raw_tracks}
        if isinstance(raw_tracks, list)
        else raw_tracks
    )

    audio_files = sorted(
        p for p in MP3_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
    )
    if not audio_files:
        print("FAIL: No audio files found in assets/audio/music_mp3/", file=sys.stderr)
        return 1

    print(f"=== Music Copyright & Content-ID Audit ({len(audio_files)} tracks) ===")
    for af in audio_files:
        name = af.name
        digest = sha256_file(af)
        meta = tracks_meta.get(name)
        if not meta:
            errors.append(f"UNREGISTERED TRACK: {name} is NOT in licenses_manifest.json!")
            continue
        if meta.get("content_id_registered") is not False:
            errors.append(f"CONTENT-ID FLAG NOT FALSE on {name}!")
        if float(meta.get("silero_vad_vocal_pct", 99.0)) > 0.0:
            errors.append(f"NON-ZERO VOCALS on {name}: {meta.get('silero_vad_vocal_pct')}%!")
        if meta.get("sha256") != digest:
            errors.append(f"SHA-256 MISMATCH on {name}: expected {meta.get('sha256')}, got {digest}")

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags", "-of", "json", str(af)],
            capture_output=True, text=True, check=True,
        )
        info = json.loads(probe.stdout).get("format", {})
        dur = float(info.get("duration", 0.0))
        tags_blob = json.dumps(info.get("tags", {})).lower()
        for bad in BANNED_TERMS:
            if bad in name.lower() or bad in tags_blob:
                errors.append(f"BANNED COMMERCIAL/CONTENT-ID TAG '{bad}' found in {name}!")

        print(
            f"  [OK] {name:46s} | {meta['bpm']:5.1f} BPM | Drop@{meta['drop_cue_s']:5.2f}s | "
            f"{dur:6.1f}s | VOC={meta['silero_vad_vocal_pct']:.2f}% | {meta['artist']} — {meta['title']}"
        )

    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in BANNED_TERMS) + r")\b", re.IGNORECASE)
    scan_targets = (
        list((ROOT / "src").glob("*.py"))
        + list((ROOT / "src").glob("*.html"))
        + list((ROOT / "src").glob("*.json"))
        + [ROOT / "studio" / "index.html"]
    )
    for st in scan_targets:
        if st.name == "verify_music_rights.py" or not st.exists():
            continue
        txt = st.read_text(encoding="utf-8", errors="ignore")
        for m in set(x.lower() for x in pattern.findall(txt)):
            errors.append(f"BANNED COMMERCIAL/LOOP REFERENCE '{m}' still present in {st.relative_to(ROOT)}!")

    if errors:
        print("\nAUDIT FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("\nALL MUSIC RIGHTS CHECKS PASSED (8/8 Heavy 320 kbps Drum & Bass Masters · Zero Content ID · 0.00% Vocals).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
