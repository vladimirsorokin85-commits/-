# -*- coding: utf-8 -*-
"""Применяет сохранённые корректорские правки (типографика) к собранным файлам.

edits.json — список {file, find, replace} из работы корректора (см. kilowatt/redesign/copy).
Скрипт встроен в build_data.py (data.js) и build_print.py (print-*.html), чтобы правки
не терялись при пересборке. Если find не найден — предупреждение (значит, текст изменился).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EDITS_PATH = os.path.join(HERE, "copy_edits.json")
CATALOG = os.path.dirname(HERE)  # kilowatt/catalog


def load_edits():
    if not os.path.exists(EDITS_PATH):
        return []
    return json.load(open(EDITS_PATH, encoding="utf-8"))


def edits_for(suffix):
    out = []
    for e in load_edits():
        f = e.get("file", "").replace("\\", "/")
        if f.endswith(suffix):
            out.append(e)
    return out


def apply_to_text(text, edits, label="", verbose=True):
    missed = []
    for e in edits:
        find, repl = e.get("find", ""), e.get("replace", "")
        if not find:
            continue
        cnt = text.count(find)
        if cnt == 0:
            missed.append(find[:60])
            continue
        text = text.replace(find, repl, 1)
    if missed and verbose:
        print(f"[typography] {label}: не найдено {len(missed)} фрагментов (текст изменился?)")
        for m in missed[:5]:
            print("   ·", m.replace("\n", " ⏎ ")[:90])
    return text, missed


def apply_to_file(path, suffix, verbose=True):
    if not os.path.exists(path):
        print(f"[typography] нет файла: {path}")
        return 0
    edits = edits_for(suffix)
    if not edits:
        return 0
    text = open(path, encoding="utf-8").read()
    text, missed = apply_to_text(text, edits, os.path.basename(path), verbose)
    open(path, "w", encoding="utf-8").write(text)
    if verbose:
        print(f"[typography] {os.path.basename(path)}: применено {len(edits) - len(missed)}/{len(edits)}")
    return len(edits) - len(missed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["data", "app", "print-field", "print-quiet", "variant-2", "check"], default="check")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.target == "check" or a.check:
        for suffix in ("data.js", "app.js", "variant-2.html", "print-quiet.html"):
            print(suffix, "->", len(edits_for(suffix)), "правок в наборе")
        return
    mapping = {
        "data": (os.path.join(CATALOG, "assets", "js", "data.js"), "data.js"),
        "app": (os.path.join(CATALOG, "assets", "js", "app.js"), "app.js"),
        "variant-2": (os.path.join(CATALOG, "variant-2.html"), "variant-2.html"),
        "print-field": (os.path.join(CATALOG, "print-field.html"), "print-quiet.html"),
        "print-quiet": (os.path.join(CATALOG, "print-quiet.html"), "print-quiet.html"),
    }
    path, suffix = mapping[a.target]
    apply_to_file(path, suffix)


if __name__ == "__main__":
    main()
