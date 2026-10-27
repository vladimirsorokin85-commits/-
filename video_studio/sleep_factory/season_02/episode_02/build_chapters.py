#!/usr/bin/env python3
"""Build YouTube chapter markers from episode 01's act headings and scene timeline."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEADER = re.compile(
    r"^### \[(?P<id>s02e02_(?P<act>a\d{2})_[^\]]+)\] "
    r"\[voice-\d{2}\](?: \[[^\]]+\])? (?P<title>.+)$"
)
SCENE_ACT = re.compile(r"^s02e02_(a\d{2})_")


def timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=Path(__file__).with_name("script.md"))
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--intro-offset", type=float, default=4.586)
    args = parser.parse_args()

    titles: dict[str, str] = {}
    for line in args.script.read_text(encoding="utf-8").splitlines():
        match = HEADER.match(line)
        if match:
            titles.setdefault(match.group("id"), match.group("title").strip())

    data = json.loads(args.timeline.read_text(encoding="utf-8"))
    acts: dict[str, tuple[float, str]] = {}
    for scene in data["scenes"]:
        scene_id = scene["id"]
        match = SCENE_ACT.match(scene_id)
        if not match or scene_id not in titles:
            raise ValueError(f"No matching act heading for timeline scene: {scene_id}")
        act = match.group(1)
        acts.setdefault(act, (float(scene["start"]) + args.intro_offset, titles[scene_id]))

    ordered = sorted(acts.items())
    if not ordered:
        raise ValueError("No chapter headings found")
    lines = [f"00:00 {ordered[0][1][1]}"]
    previous = 0
    for _, (seconds, title) in ordered[1:]:
        current = int(seconds)
        if current - previous < 10:
            raise ValueError(f"Chapter is too close to the previous one: {title}")
        lines.append(f"{timestamp(seconds)} {title}")
        previous = current

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} chapter markers: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
