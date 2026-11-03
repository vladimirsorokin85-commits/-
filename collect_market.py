#!/usr/bin/env python3
"""Сбор реальных данных по военной нише YouTube без API-ключа."""
import json, subprocess, sys, csv, os, re
from pathlib import Path

OUT = Path("market_data")
OUT.mkdir(exist_ok=True)

def ytdlp_json(url, extra=None):
    cmd = ["yt-dlp", "--skip-download", "--print-json", "--no-warnings"]
    if extra:
        cmd += extra
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return []
        out = []
        for line in r.stdout.strip().splitlines():
            if line.strip():
                try: out.append(json.loads(line))
                except: pass
        return out
    except Exception as e:
        print(f"ERR {url}: {e}", file=sys.stderr)
        return []

def search_videos(query, limit=30):
    print(f"[SEARCH] {query}")
    return ytdlp_json(f"ytsearch{limit}:{query}")

def channel_videos(handle, limit=60):
    print(f"[CHANNEL] {handle}")
    return ytdlp_json(f"https://www.youtube.com/@{handle}/videos", ["--max-downloads", str(limit)])

KEYWORDS = [
    "защита от FPV дронов",
    "сетка рабица от FPV",
    "пенофол блиндаж тепловизор",
    "чулок на прицеле антиблик",
    "лайфхаки СВО",
    "маскировка от тепловизора",
    "безопасность на войне советы",
    "военные лайфхаки",
    "бронежилет проверить документы",
    "V50 бронепленка",
]

CHANNELS = [
    "militarySummary_ru",
    "WarLeaks",
]

all_videos = []

# Search by keywords
for kw in KEYWORDS:
    for v in search_videos(kw, 25):
        v["_source"] = f"search:{kw}"
        all_videos.append(v)

# Channel videos
for ch in CHANNELS:
    for v in channel_videos(ch, 40):
        v["_source"] = f"channel:{ch}"
        all_videos.append(v)

# Deduplicate by id
seen = {}
for v in all_videos:
    vid = v.get("id")
    if vid and vid not in seen:
        seen[vid] = v

videos = list(seen.values())
print(f"\n[INFO] Уникальных видео собрано: {len(videos)}")

# Save raw
with open(OUT / "raw_videos.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)

# Build CSV
rows = []
for v in videos:
    rows.append({
        "video_id": v.get("id",""),
        "title": v.get("title",""),
        "views": v.get("view_count") or 0,
        "likes": v.get("like_count") or 0,
        "channel": v.get("channel",""),
        "channel_id": v.get("channel_id",""),
        "upload_date": v.get("upload_date",""),
        "duration": v.get("duration") or 0,
        "source": v.get("_source",""),
        "url": f"https://www.youtube.com/watch?v={v.get('id','')}",
    })

rows.sort(key=lambda r: r["views"], reverse=True)

with open(OUT / "videos.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
    w.writeheader()
    w.writerows(rows)

print(f"[INFO] Сохранено: {OUT}/videos.csv")
for r in rows[:15]:
    print(f"  {r['views']:>8}  {r['channel'][:35]:<35}  {r['title'][:70]}")
