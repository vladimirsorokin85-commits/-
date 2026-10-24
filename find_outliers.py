#!/usr/bin/env python3
"""
find_outliers.py — поиск аномальных (outlier) видео в военной нише YouTube.

Метод адаптирован из репозитория youtube-outliers (marianina8 / 411tmnd-star
и др.): ищем видео, которые бьют средний уровень своего канала в 3x и более,
чтобы понять, какие темы и форматы «выстреливают».

Требования:
    pip install -U yt-dlp

Использование (без YouTube Data API ключа):
    python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --limit 20 --out outliers.csv

Пример вывода:
    video_id,title,views,subscribers,views_per_sub,upload_date,channel,url
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def run_yt_dlp(url_or_query: str, limit: int = 20):
    """
    Выполняет yt-dlp для поиска или списка видео и возвращает JSON с метаданными.
    """
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--print-json",
        "--max-downloads", str(limit),
    ]

    # Если это поисковый запрос (не URL), добавляем "ytsearchN:"
    if not url_or_query.startswith("http"):
        cmd.append(f"ytsearch{limit}:{url_or_query}")
    else:
        cmd.append(url_or_query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"[WARN] таймаут для {url_or_query}", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def get_channel_subscribers(channel_url: str):
    """
    Пытается получить количество подписчиков канала через yt-dlp.
    Возвращает None, если недоступно.
    """
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--print-json",
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout.strip():
            data = json.loads(result.stdout.strip().splitlines()[0])
            return data.get("channel_follower_count") or data.get("channel_subscribers")
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Поиск аномальных видео (outliers) в военной нише YouTube"
    )
    parser.add_argument(
        "--keywords-file",
        default="MILITARY_KEYWORDS.txt",
        help="Путь к файлу с ключевыми словами (по одной строке, игнорируются комментарии с #)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Сколько видео собирать по каждому ключевому слову",
    )
    parser.add_argument(
        "--out",
        default="outliers.csv",
        help="Путь к выходному CSV",
    )
    parser.add_argument(
        "--min-views",
        type=int,
        default=10_000,
        help="Минимальное число просмотров для включения видео",
    )
    parser.add_argument(
        "--max-subs",
        type=int,
        default=20_000,
        help="Максимальное число подписчиков канала (малые игроки)",
    )
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=3.0,
        help="Минимальный коэффициент views/subscribers для флага outlier",
    )
    args = parser.parse_args()

    # Читаем ключевые слова
    keywords_path = Path(args.keywords_file)
    if not keywords_path.exists():
        print(f"[ERR] файл {args.keywords_file} не найден", file=sys.stderr)
        sys.exit(1)

    keywords = []
    for line in keywords_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keywords.append(line)

    if not keywords:
        print("[ERR] нет ключевых слов в файле", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] ключевые слова: {len(keywords)}")
    print(f"[INFO] лимит по каждому: {args.limit}")
    print(f"[INFO] min views: {args.min_views}, max subs: {args.max_subs}, min ratio: {args.min_ratio}x")

    rows = []
    seen_ids = set()

    for kw in keywords:
        print(f"\n[INFO] поиск: {kw}")
        videos = run_yt_dlp(kw, limit=args.limit)
        for v in videos:
            vid = v.get("id")
            if not vid or vid in seen_ids:
                continue
            views = v.get("view_count") or 0
            if views < args.min_views:
                continue

            channel_id = v.get("channel_id") or v.get("channel")
            channel_url = v.get("channel_url") or f"https://www.youtube.com/channel/{channel_id}" if channel_id else None
            subscribers = None
            if channel_url:
                subscribers = get_channel_subscribers(channel_url)

            # Фильтр по малым каналам
            if subscribers is not None and subscribers > args.max_subs:
                continue

            ratio = None
            if subscribers and subscribers > 0:
                ratio = views / subscribers
            if ratio is not None and ratio < args.min_ratio:
                continue

            seen_ids.add(vid)
            rows.append({
                "video_id": vid,
                "title": v.get("title", ""),
                "views": views,
                "subscribers": subscribers or "",
                "views_per_sub": round(ratio, 2) if ratio else "",
                "upload_date": v.get("upload_date", ""),
                "channel": v.get("channel", ""),
                "url": f"https://www.youtube.com/watch?v={vid}",
            })

    # Сортировка по просмотрам (убывание)
    rows.sort(key=lambda r: r["views"], reverse=True)

    # Запись CSV
    fieldnames = [
        "video_id", "title", "views", "subscribers", "views_per_sub",
        "upload_date", "channel", "url",
    ]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[INFO] готово: {len(rows)} аномальных видео сохранено в {args.out}")
    print("[INFO] откройте CSV и проанализируйте повторяющиеся темы в заголовках — это и есть рабочие форматы для «В Окопе».")


if __name__ == "__main__":
    main()
