#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПОСТЫ по MG Ultra (ДТКП «Матильда»).

  python3 suppliers/mgultra/post.py maxim-long-oriks foks kompakt-mini
  python3 suppliers/mgultra/post.py --list

Собирает папку vk/posts/mgultra/<slug>/: фото поставщика (1.jpg…), пост.txt (без цен и остатков).
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CAT = json.load(open(os.path.join(HERE, "catalog.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "vk", "posts", "mgultra")

CTA = "СДЭК по России, оплата при получении. Напишите в личные сообщения — подберём под ваш карабин."

ABOUT = ("ДТКП — дульный тормоз-компенсатор-пламегаситель закрытого типа. Внутри конусные камеры: "
         "пороховые газы тормозятся, отдача и подброс ствола снижаются, вспышка гасится, "
         "звук выстрела становится глуше и комфортнее для стрелка. Это не глушитель — "
         "бесшумной стрельбы не будет.")


def slug(name):
    s = re.sub(r"[^\w\s-]", "", name.lower().replace("ё", "е"), flags=re.UNICODE)
    return re.sub(r"[\s_]+", "-", s).strip("-")[:40]


def find(name_or_slug):
    q = name_or_slug.strip().lower()
    for m in CAT["models"]:                      # 1) точный слаг
        if slug(m["name"]) == q:
            return m
    for m in CAT["models"]:                      # 2) имя начинается с запроса
        if m["name"].lower().startswith(q):
            return m
    for m in CAT["models"]:                      # 3) запрос встречается в имени
        if q in m["name"].lower():
            return m
    return None


def facts(m):
    out = []
    sp = m.get("specs") or {}
    for k, v in sp.items():
        k = k.strip(":")
        out.append(f"{k}: {v}")
    first = (m.get("texts") or [""])[0]
    for t in (m.get("texts") or [])[:5]:
        if t and not t.startswith("+") and t != first:
            out.append(t)
    return out


def build(m, dir_name=None):
    d = os.path.join(OUT, dir_name or slug(m["name"]))
    os.makedirs(d, exist_ok=True)
    photos = m.get("photos_local") or []
    for i, p in enumerate(photos, 1):
        shutil.copyfile(os.path.join(ROOT, p), os.path.join(d, f"{i}.jpg"))
    L = [f"🔧 ДТКП «{m['name']}» — MG Ultra (Матильда)", ""]
    txt = (m.get("texts") or [""])[0]
    L += [txt or "Дульный тормоз-компенсатор-пламегаситель закрытого типа.", "", ABOUT, ""]
    f = facts(m)
    if f:
        L.append("Что важно:")
        L += [f"▪️ {x}" for x in f[:5]]
        L.append("")
    if m.get("video"):
        L += ["Есть видеообзор работы устройства — пришлём по запросу.", ""]
    L += ["В наличии.", "", CTA, "",
          "#вокопе #дтк #тюнингоружия #карабин #охота #стрельба #экипировка"]
    text = "\n".join(L).strip() + "\n"

    for label, rx in (("цена", r"\d[\d\s]*(₽|руб)"), ("«у Димы»", r"\bДимы?\b"),
                      ("поставщик", r"поставщик"), ("склад", r"\b(на|со)\s+склад"),
                      ("остаток", r"\b\d+\s*(шт|компл|пар)\b")):
        mm = re.search(rx, text, re.I)
        assert not mm, f"в тексте запрещённое: {label} → {mm.group(0)!r}"

    open(os.path.join(d, "пост.txt"), "w", encoding="utf-8").write(text)
    print(f"  {m['name']}: фото {len(photos)} → {os.path.relpath(d, ROOT)}")
    return d


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        for m in CAT["models"]:
            print(f"  {slug(m['name']):42} {m['name']}")
        return
    for a in args:
        m = find(a)
        if not m:
            print(f"  !! не нашёл «{a}»")
            continue
        build(m)


if __name__ == "__main__":
    main()
