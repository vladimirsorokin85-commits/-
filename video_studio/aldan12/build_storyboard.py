#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Считает тайминг по VO и собирает storyboard.md + timeline.json для «Алдан-12».

Модель длительности: речь 2,8 слова/с (2,6–3,0 по брифу — берём середину),
плюс 0,32 с паузы на реплику, плюс запас 0,45 с на кадр.
Кадр не короче min_dur из shots.py. Блоков — по BLOCKS.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shots import BLOCKS, SHOTS, TEASER  # noqa: E402

WPS = 2.8          # слов в секунду
PAUSE = 0.32       # пауза после реплики
PAD = 0.90         # запас внутри кадра (время прочитать макет)
BASE = os.path.dirname(os.path.abspath(__file__))


def words(s):
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def shot_dur(vo, mn):
    if not vo:
        return mn
    d = words(vo) / WPS + PAUSE + PAD
    return max(mn, round(d, 2))


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}"


def build():
    rows, t = [], 0.0
    block_stats = {}
    for i, (blk, screen, vo, frame, sfx, mn) in enumerate(SHOTS, 1):
        d = shot_dur(vo, mn)
        rows.append(dict(n=i, block=blk, block_name=BLOCKS[blk], t0=round(t, 2),
                         t1=round(t + d, 2), dur=d, screen=screen, vo=vo,
                         frame=frame, sfx=sfx, words=words(vo)))
        st = block_stats.setdefault(blk, dict(name=BLOCKS[blk], t0=round(t, 2),
                                              words=0, shots=0))
        st["words"] += words(vo)
        st["shots"] += 1
        t += d
    for blk, st in block_stats.items():
        st["t1"] = round(max(r["t1"] for r in rows if r["block"] == blk), 2)
    total = round(t, 2)
    return rows, block_stats, total


def storyboard_md(rows, stats, total):
    L = []
    L.append("# Раскадровка «Алдан-12» — горизонталь 16:9\n")
    L.append(f"Длительность: **{fmt(total)}** ({total:.1f} с) · кадров: **{len(rows)}** · "
             f"слов VO: **{sum(r['words'] for r in rows)}**\n")
    L.append(f"Модель тайминга: {WPS} слова/с + {PAUSE} с паузы + {PAD} с запаса; кадр не короче своего минимума.\n")
    L.append("\n## Блоки\n")
    L.append("| # | Блок | Начало | Конец | Длит. | Кадров | Слов |")
    L.append("|---|---|---|---|---|---|---|")
    for blk in sorted(stats):
        s = stats[blk]
        L.append(f"| {blk} | {s['name']} | {fmt(s['t0'])} | {fmt(s['t1'])} | "
                 f"{s['t1']-s['t0']:.1f} с | {s['shots']} | {s['words']} |")
    L.append("\n## Кадры\n")
    L.append("| № | Тайм-код | Длит. | Что видно | Текст на экране | VO (дословно) | SFX / переход |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        vo = r["vo"].replace("|", "/") or "—"
        scr = (r["screen"] or "—").replace("|", "/")
        L.append(f"| {r['n']} | {fmt(r['t0'])}–{fmt(r['t1'])} | {r['dur']:.1f} | "
                 f"{r['frame']} | {scr} | {vo} | {r['sfx'] or '—'} |")
    return "\n".join(L) + "\n"


def build_teaser():
    rows, t = [], 0.0
    for i, (screen, vo, frame, sfx, mn) in enumerate(TEASER, 1):
        d = max(mn, round(words(vo) / 2.9 + 0.25 + 0.9, 2))
        rows.append(dict(n=i, t0=round(t, 2), t1=round(t + d, 2), dur=d, screen=screen,
                         vo=vo, frame=frame, sfx=sfx, words=words(vo)))
        t += d
    return rows, round(t, 2)


def teaser_md(rows, total):
    L = ["# Раскадровка тизера — вертикаль 9:16\n",
         f"Длительность: **{fmt(total)}** ({total:.1f} с) · кадров: **{len(rows)}**\n",
         "Безопасные зоны: 15 % сверху и снизу · субтитры по 2–4 слова, нижняя треть, кегль ≥ 40 px.\n",
         "| № | Тайм-код | Длит. | Что видно | Текст на экране | VO | SFX |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['n']} | {fmt(r['t0'])}–{fmt(r['t1'])} | {r['dur']:.1f} | {r['frame']} | "
                 f"{r['screen']} | {r['vo']} | {r['sfx'] or '—'} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    rows, stats, total = build()
    open(os.path.join(BASE, "storyboard.md"), "w", encoding="utf-8").write(
        storyboard_md(rows, stats, total))
    json.dump(dict(total=total, blocks={str(k): v for k, v in stats.items()},
                   shots=[{k: v for k, v in r.items()} for r in rows]),
              open(os.path.join(BASE, "timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"кадров: {len(rows)} · слов: {sum(r['words'] for r in rows)} · итог: {fmt(total)} ({total:.1f} с)")
    for blk in sorted(stats):
        s = stats[blk]
        print(f"  {blk:2d}. {s['name'][:44]:46s} {fmt(s['t0'])}–{fmt(s['t1'])}  "
              f"{s['t1']-s['t0']:6.1f} с  кадров {s['shots']:2d}  слов {s['words']:4d}")
    # VO-скрипт для синтеза: по одному файлу на кадр с репликой
    vo_lines = [f"# VO-скрипт «Алдан-12» · файлов: {sum(1 for r in rows if r['vo'])}"]
    for r in rows:
        if r["vo"]:
            vo_lines.append(f"{r['n']:02d}\t{r['t0']:07.2f}\t{r['dur']:05.2f}\t{r['vo']}")
    open(os.path.join(BASE, "vo_script.txt"), "w", encoding="utf-8").write("\n".join(vo_lines) + "\n")
    print(f"vo_script.txt: {len(vo_lines)-1} реплик")

    # Блочный VO: одна реплика-дорожка на блок (экономит лимит синтеза, склейки — по паузам)
    blocks_vo = {}
    for r in rows:
        if r["vo"]:
            b = blocks_vo.setdefault(r["block"], {"name": r["block_name"], "t0": r["t0"],
                                                  "parts": [], "shots": []})
            b["parts"].append(r["vo"].rstrip(" .") + ".")
            b["shots"].append(r["n"])
    json.dump(blocks_vo, open(os.path.join(BASE, "vo_blocks.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"блоков для синтеза: {len(blocks_vo)} · реплик всего: {len(vo_lines)-1}")

    trows, ttotal = build_teaser()
    open(os.path.join(BASE, "teaser.md"), "w", encoding="utf-8").write(teaser_md(trows, ttotal))
    json.dump(dict(total=ttotal, shots=trows),
              open(os.path.join(BASE, "teaser_timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"тизер: кадров {len(trows)} · итог {fmt(ttotal)} ({ttotal:.1f} с) · "
          + ("в брифе 45–60 с ✔" if 45 <= ttotal <= 60 else "!! вне брифа 45–60 с"))
    ok = 480 <= total <= 720
    print("В БРИФЕ 8:00–12:00 ✔" if ok else f"!! вне брифа ({fmt(total)})")
