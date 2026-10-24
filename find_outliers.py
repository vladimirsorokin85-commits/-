#!/usr/bin/env python3
"""
find_outliers.py — быстрый поиск аномальных (outlier) видео в военной нише YouTube.

Метод адаптирован из youtube-outliers: ищем видео, которые бьют средний
уровень своего канала в 3x и более, чтобы понять, какие темы «выстреливают».

Быстрый режим (по умолчанию): не запрашивает подписчиков каналов,
работает только с просмотрами — в разы быстрее.

Требования:
    pip install -U yt-dlp

Использование (без YouTube Data API ключа):
    python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --out outliers.csv

С подписчиками (медленнее, но точнее для расчёта views/subscriber):
    python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --with-subs --out outliers.csv
"""

import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def run_yt_dlp_search(query: str, limit: int):
    """Один вызов yt-dlp для поиска по запросу. Возвращает список видео."""
    cmd = [
        sys.executable,
        "-m", "yt_dlp",
        "--skip-download",
        "--print-json",
        "--max-downloads", str(limit),
        f"ytsearch{limit}:{query}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            return []
    except subprocess.TimeoutExpired:
        print(f"[WARN] таймаут: {query}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("[ERR] yt-dlp не найден. Установите: pip install -U yt-dlp", file=sys.stderr)
        sys.exit(1)

    videos = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def get_channel_subscribers(channel_url: str):
    """Подписчики канала (отдельный медленный запрос, только при --with-subs)."""
    cmd = [sys.executable, "-m", "yt_dlp", "--skip-download", "--print-json", channel_url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout.strip():
            data = json.loads(result.stdout.strip().splitlines()[0])
            return data.get("channel_follower_count") or data.get("channel_subscribers")
    except Exception:
        pass
    return None


def process_keyword(kw: str, limit: int, min_views: int):
    """Собирает видео по одному ключевому слову и фильтрует по просмотрам."""
    print(f"[INFO] поиск: {kw}")
    videos = run_yt_dlp_search(kw, limit)
    rows = []
    for v in videos:
        vid = v.get("id")
        if not vid:
            continue
        views = v.get("view_count") or 0
        if views < min_views:
            continue
        channel_url = v.get("channel_url") or (
            f"https://www.youtube.com/channel/{v.get('channel_id')}"
            if v.get("channel_id")
            else None
        )
        rows.append({
            "video_id": vid,
            "title": v.get("title", ""),
            "views": views,
            "channel": v.get("channel", ""),
            "channel_url": channel_url or "",
            "upload_date": v.get("upload_date", ""),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "keyword": kw,
        })
    return rows


def fetch_subs_for_rows(rows: list, max_workers: int):
    """Добирает подписчиков для уникальных каналов параллельно (только --with-subs)."""
    unique_channels = {}
    for r in rows:
        url = r.get("channel_url")
        if url and url not in unique_channels:
            unique_channels[url] = None

    print(f"[INFO] собираю подписчики для {len(unique_channels)} каналов...")

    def get_one(url):
        return url, get_channel_subscribers(url)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(get_one, url): url for url in unique_channels}
        for fut in as_completed(futures):
            url, subs = fut.result()
            unique_channels[url] = subs

    for r in rows:
        r["subscribers"] = unique_channels.get(r.get("channel_url"), "") or ""
        subs = r["subscribers"]
        views = r["views"]
        try:
            r["views_per_sub"] = round(views / int(subs), 2) if subs else ""
        except (ValueError, ZeroDivisionError):
            r["views_per_sub"] = ""
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Быстрый поиск аномальных видео (outliers) в военной нише YouTube"
    )
    parser.add_argument("--keywords-file", default="MILITARY_KEYWORDS.txt",
                        help="Файл с ключевыми словами (по одной строке, # — комментарий)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Сколько видео собирать по каждому ключевому слову")
    parser.add_argument("--out", default="outliers.csv",
                        help="Путь к выходному CSV")
    parser.add_argument("--min-views", type=int, default=10_000,
                        help="Минимум просмотров для включения видео")
    parser.add_argument("--max-subs", type=int, default=20_000,
                        help("Макс. подписчиков канала (для фильтра малых игроков)")
    parser.add_argument("--min-ratio", type=float, default=3.0,
                        help="Минимум views/subscriber для флага outlier")
    parser.add_argument("--max-workers", type=int, default=6,
                        help="Количество параллельных потоков")
    parser.add_argument("--with-subs", action="store_true",
                        help="Также собирать подписчиков каналов (медленнее)")
    args = parser.parse_args()

    kp = Path(args.keywords_file)
    if not kp.exists():
        print(f"[ERR] файл {args.keywords_file} не найден", file=sys.stderr)
        sys.exit(1)

    keywords = []
    for line in kp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keywords.append(line)

    if not keywords:
        print("[ERR] нет ключевых слов в файле", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] ключевые слова: {len(keywords)}")
    print(f"[INFO] лимит по каждому: {args.limit}")
    print(f"[INFO] min views: {args.min_views}")
    print(f"[INFO] потоки: {args.max_workers}")
    if args.with_subs:
        print("[INFO] режим: с подписчиками (медленнее)")
    else:
        print("[INFO] режим: быстрый (без подписчиков)")

    # Собираем видео по всем ключевым словам параллельно
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
                if r["video_id"] not in seen_ids:
                    seen_ids.add(r["video_id"])
                    all_rows.append(r)

    print(f"[INFO] собрано видео: {len(all_rows)}")

    # Подписчики (опционально, медленно)
    if args.with_subs:
        all_rows = fetch_subs_for_rows(all_rows, args.max_workers)
    else:
        for r in all_rows:
            r["subscribers"] = ""
            r["views_per_sub"] = ""

    # Фильтр по малым каналам (если есть подписчики)
    if args.with_subs:
        filtered = []
        for r in all_rows:
            subs = r["subscribers"]
            if subs and subs.isdigit() and int(subs) > args.max_subs:
                continue
            ratio = r["views_per_sub"]
            if ratio and float(ratio) < args.min_ratio:
                continue
            filtered.append(r)
        all_rows = filtered
        print(f"[INFO] после фильтра по каналам: {len(all_rows)}")

    # Сортировка по просмотрам
    all_rows.sort(key=lambda r: r["views"], reverse=True)

    # CSV
    fieldnames = [
        "video_id", "title", "views", "subscribers", "views_per_sub",
        "upload_date", "channel", "keyword", "url",
    ]
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n[INFO] готово: {len(all_rows)} видео сохранено в {args.out}")
    print("[INFO] откройте CSV в Excel и посмотрите повторяющиеся темы в заголовках —")


if __name__ == "__main__":
    main()
