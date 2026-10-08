#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
БАЗА ЗНАНИЙ «В ОКОПЕ» — факты с источниками, чтобы посты были грамотными.

  python3 knowledge/db.py find <слово>
  python3 knowledge/db.py topic <тема>
  python3 knowledge/db.py topics
  python3 knowledge/db.py add --topic <тема> --title <...> --fact <...> [--source <...>]
                              [--tag <...> ...] [--confidence high|medium|opinion]
  python3 knowledge/db.py all
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "db.json")


def load():
    return json.load(open(DB, encoding="utf-8"))


def save(data):
    json.dump(data, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def dump(entries, verbatim=False):
    for e in entries:
        print(f"[{e['topic']}] {e['title']}")
        print(f"  {e['fact']}")
        if e.get("source"):
            print(f"  источник: {e['source']}")
        meta = [f"теги: {', '.join(e.get('tags', []))}" if e.get("tags") else "",
                f"уверенность: {e.get('confidence', 'high')}",
                f"добавлено: {e.get('added', '')}"]
        print("  " + " | ".join(x for x in meta if x))
        print()


def norm(s):
    s = str(s or "").lower().replace("ё", "е")
    return re.sub(r"[^\w\s]", " ", s)


def main(argv=None):
    ap = argparse.ArgumentParser(description="База знаний магазина")
    sub = ap.add_subparsers(dest="cmd")

    p_f = sub.add_parser("find", help="поиск по слову")
    p_f.add_argument("query")
    p_t = sub.add_parser("topic", help="всё по теме")
    p_t.add_argument("topic")
    sub.add_parser("topics", help="список тем")
    sub.add_parser("all", help="вся база")
    p_a = sub.add_parser("add", help="добавить запись")
    p_a.add_argument("--topic", required=True)
    p_a.add_argument("--title", required=True)
    p_a.add_argument("--fact", required=True)
    p_a.add_argument("--source", default="")
    p_a.add_argument("--tag", action="append", default=[])
    p_a.add_argument("--confidence", default="high", choices=["high", "medium", "opinion"])

    args = ap.parse_args(argv or sys.argv[1:])
    data = load()
    entries = data["entries"]

    if args.cmd == "find":
        q = norm(args.query)
        hits = [e for e in entries
                if q in norm(e["title"]) or q in norm(e["fact"]) or q in norm(e["topic"])
                or any(q in norm(t) for t in e.get("tags", []))]
        print(f"Найдено: {len(hits)}\n")
        dump(hits)
    elif args.cmd == "topic":
        q = norm(args.topic)
        hits = [e for e in entries if q in norm(e["topic"])]
        print(f"Тема «{args.topic}»: {len(hits)} записей\n")
        dump(hits)
    elif args.cmd == "topics":
        topics = {}
        for e in entries:
            topics[e["topic"]] = topics.get(e["topic"], 0) + 1
        for t, n in sorted(topics.items()):
            print(f"  {t}: {n}")
        print(f"\nвсего записей: {len(entries)}")
    elif args.cmd == "all":
        dump(entries)
        print(f"всего записей: {len(entries)}")
    elif args.cmd == "add":
        rec = {
            "id": f"kb-{len(entries) + 1:03d}",
            "topic": args.topic, "title": args.title, "fact": args.fact,
            "source": args.source, "tags": args.tag,
            "confidence": args.confidence,
            "added": dt.date.today().isoformat(),
        }
        entries.append(rec)
        save(data)
        print("добавлено:", rec["id"], "|", rec["title"])
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
