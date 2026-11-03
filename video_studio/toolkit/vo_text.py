#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подготовка текста озвучки для «В Окопе»: словарь ударений и произношения.

Зачем: движок синтеза не знает терминов магазина и омографов. Здесь единый
источник правды — `glossary_stress.json` — и безопасное применение к тексту.

Режимы (--mode):
  plain    — как есть, только предупредить о рискованных словах (по умолчанию);
  plus     — вставить «+» перед ударной гласной (для движков, понимающих разметку);
  respell  — заменить термины на фонетическую запись из поля `say` (понимает любой движок).

Примеры:
    python3 video_studio/toolkit/vo_text.py --report "Три ПРО: комбо, комплект, тушка."
    python3 video_studio/toolkit/vo_text.py --mode plus "Индекс 3Т — тепловизор."
    python3 video_studio/toolkit/vo_text.py --selftest
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GLOSSARY = os.path.join(HERE, "glossary_stress.json")
VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"


def load(path=GLOSSARY):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _word_re(word):
    return re.compile(r"(?<![А-Яа-яЁёA-Za-z])" + re.escape(word) + r"(?![А-Яа-яЁёA-Za-z])")


def _syllables(word):
    return len([c for c in word if c in VOWELS])


def validate(g):
    """Проверка словаря: ровно один «+», не на первом месте, не в односложном слове."""
    errors, warns = [], []
    for w, item in g["terms"].items():
        marked = item.get("marked", "")
        base = marked.replace("+", "")
        if base.lower() != w.lower():
            errors.append(f"{w}: marked «{marked}» не совпадает со словом")
            continue
        if marked.count("+") == 0:
            if _syllables(w) > 1:
                warns.append(f"{w}: ударение не размечено")
        elif marked.count("+") > 1:
            errors.append(f"{w}: больше одного «+»")
        else:
            i = marked.index("+")
            if i == 0:
                errors.append(f"{w}: «+» в начале слова")
            elif marked[i + 1] not in VOWELS:
                errors.append(f"{w}: «+» стоит не перед гласной")
            if _syllables(w) == 1:
                warns.append(f"{w}: односложное слово — «+» не нужен")
        if item.get("confidence") not in ("ok", "needs_check"):
            warns.append(f"{w}: не указан confidence")
    return errors, warns


def risky_terms(text, g):
    """Термины из словаря, которые встречаются в тексте."""
    found = []
    for w in list(g["terms"]) + list(g.get("phrases", {})):
        if _word_re(w).search(text):
            found.append(w)
    return found


def unknown_terms(text, g):
    """Слова с «трудными» признаками, которых нет в словаре (латиница, аббревиатуры)."""
    known = {w.lower() for w in g["terms"]} | {w.lower() for w in g.get("phrases", {})}
    out = []
    for m in re.finditer(r"[A-Za-zА-Яа-яЁё0-9\-]+", text):
        tok = m.group(0)
        low = tok.lower()
        if low in known:
            continue
        letters = re.sub(r"[^А-Яа-яЁёA-Za-z]", "", tok)
        if not letters:
            continue
        if re.fullmatch(r"[A-ZА-ЯЁ]{2,4}", tok):
            out.append(tok)
        elif re.search(r"[A-Za-z]", tok):
            out.append(tok)
        elif len(set(letters.lower())) <= 2 and len(letters) > 3:
            out.append(tok)
    return sorted(set(out))


def prepare(text, mode="plain", g=None):
    g = g or load()
    if mode == "plain":
        return text
    if mode == "plus":
        for w, item in sorted(g["terms"].items(), key=lambda kv: -len(kv[0])):
            text = _word_re(w).sub(item.get("marked", w), text)
        return text
    if mode == "respell":
        for w, item in sorted(list(g["terms"].items()) + list(g.get("phrases", {}).items()),
                              key=lambda kv: -len(kv[0])):
            say = item.get("say")
            if say:
                text = _word_re(w).sub(say, text)
        return text
    raise SystemExit(f"неизвестный режим: {mode}")


def report(text, g=None):
    g = g or load()
    errors, warns = validate(g)
    print("ТЕКСТ:", text)
    found = risky_terms(text, g)
    print("\nТермины из словаря:", ", ".join(found) if found else "нет")
    for w in found:
        item = g["terms"].get(w) or g.get("phrases", {}).get(w)
        mark = item.get("marked", w)
        say = item.get("say", "")
        conf = item.get("confidence", "—")
        print(f"  {w:16s} → {mark:18s} | произносим: {say:18s} | {conf}")
    unk = unknown_terms(text, g)
    if unk:
        print("\n⚠ Нет в словаре (проверить на слух):", ", ".join(unk))
    print("\nРежим plus :", prepare(text, "plus", g))
    print("Режим respell:", prepare(text, "respell", g))
    if errors:
        print("\nОШИБКИ СЛОВАРЯ:")
        for e in errors:
            print("  ✘", e)
    if warns:
        print("\nЗамечания:")
        for w in warns:
            print("  •", w)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="*", help="текст озвучки")
    ap.add_argument("--mode", default="plain", choices=["plain", "plus", "respell"])
    ap.add_argument("--report", action="store_true", help="полный отчёт по тексту")
    ap.add_argument("--selftest", action="store_true", help="проверить сам словарь")
    a = ap.parse_args()

    g = load()
    if a.selftest:
        errors, warns = validate(g)
        print(f"терминов: {len(g['terms'])} · фраз: {len(g.get('phrases', {}))}")
        for w in warns:
            print("  •", w)
        for e in errors:
            print("  ✘", e)
        print("СЛОВАРЬ OK ✔" if not errors else "СЛОВАРЬ С ОШИБКАМИ ✘")
        return 0 if not errors else 1

    text = " ".join(a.text).strip()
    if not text:
        ap.print_help()
        return 2
    if a.report:
        report(text, g)
        return 0
    print(prepare(text, a.mode, g))
    return 0


if __name__ == "__main__":
    sys.exit(main())
