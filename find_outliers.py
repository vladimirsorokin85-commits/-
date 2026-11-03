#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_outliers.py — поиск популярных видео в военной нише YouTube.
Запуск: python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --out outliers.csv
"""
import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def run_search(query, limit=20):
    """Поиск видео через yt-dlp (вызывается как модуль Python)."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download", "--print-json",
        "--max-downloads", str(limit),
        f"ytsearch{limit}:{query}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        print("[ERR] yt-dlp не установлен. Выполни: python -m pip install yt-dlp")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"[WARN] таймаут: {query}")
        return []
    videos = []
    for line in res.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def process_keyword(kw, limit, min_views):
    print(f"[INFO] ищу: {kw}")
    videos = run_search(kw, limit)
    rows = []
    for v in videos:
        vid = v.get("id")
        if not vid:
            continue
        views = v.get("view_count") or 0
        if views < min_views:
            continue
        rows.append({
            "title": v.get("title", ""),
            "views": views,
            "channel": v.get("channel", ""),
            "keyword": kw,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Поиск популярных видео в военной нише YouTube"
    )
    parser.add_argument("--keywords-file", default="MILITARY_KEYWORDS.txt")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", default="outliers.csv")
    parser.add_argument("--min-views", type=int, default=10000)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()

    kp = Path(args.keywords_file)
    if not kp.exists():
        print(f"[ERR] файл {args.keywords_file} не найден")
        sys.exit(1)

    keywords = []
    for line in kp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            keywords.append(line)

    if not keywords:
        print("[ERR] нет ключевых слов в файле")
        sys.exit(1)

    print(f"[INFO] ключевых слов: {len(keywords)}")
    print(f"[INFO] лимит по каждому: {args.limit}")
    print(f"[INFO] мин. просмотров: {args.min_views}")

    all_rows = []
    seen_ids = set()

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {
            pool.submit(process_keyword, kw, args.limit, args.min_views): kw
            for kw in keywords
        }
        for fut in as_completed(futures):
            rows = fut.result()
            for r in rows:
                if r["url"] not in seen_ids:
                    seen_ids.add(r["url"])
                    all_rows.append(r)

    print(f"[INFO] собрано видео: {len(all_rows)}")
    all_rows.sort(key=lambda r: r["views"], reverse=True)

    fieldnames = ["title", "views", "channel", "keyword", "url"]
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n[INFO] готово: {len(all_rows)} видео в {args.out}")


if __name__ == "__main__":
    main()
