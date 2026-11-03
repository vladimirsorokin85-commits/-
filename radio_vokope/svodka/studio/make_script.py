#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Из фактов владельца — в сценарий выпуска.

Вход — markdown вида `facts_YYYY-MM-DD_utro.md` (см. пример ниже),
выход — JSON для `build.py`, плюс проверки: объём текста, стоп-лист, длина реплик.

    python3 make_script.py facts_2026-11-04_utro.md -o scripts/svodka_2026-11-04_utro.json

Формат входного файла:

    # СВОДКА 2026-11-04 утро
    Источник: «Военные сводки», выпуск от 3 ноября — пересказ своими словами

    ## Факты
    - Продвижение на двух участках | Наши подразделения продвинулись на двух участках
      и закрепились на новых рубежах, работали штурмовые группы при поддержке артиллерии.
    - Работа беспилотников | Расчёты беспилотников вскрыли и уничтожили технику противника,
      корректировка огня шла в реальном времени.

    ## Где наши работают
    Кураховское · Покровское · Запорожское

    ## Благодарность
    Водителям · Медикам · Связистам

    ## Куда идти
    Адреса и сборы — в описании выпуска
"""
import argparse
import json
import os
import re
import sys

DAYS = ["первое", "второе", "третье", "четвёртое", "пятое", "шестое", "седьмое",
        "восьмое", "девятое", "десятое", "одиннадцатое", "двенадцатое", "тринадцатое",
        "четырнадцатое", "пятнадцатое", "шестнадцатое", "семнадцатое", "восемнадцатое",
        "девятнадцатое", "двадцатое", "двадцать первое", "двадцать второе",
        "двадцать третье", "двадцать четвёртое", "двадцать пятое", "двадцать шестое",
        "двадцать седьмое", "двадцать восьмое", "двадцать девятое", "тридцатое",
        "тридцать первое"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
              "сентябрь", "октябрь", "ноябрь", "декабрь"]

STOP_HARD = [
    (r"\bпотер(и|ь|ям|ях|ями)\b", "потери"),
    (r"\bжертв", "жертвы"),
    (r"\bпогиб", "погибшие"),
    (r"\bкоординат", "координаты"),
    (r"\bдислокац", "дислокация"),
    (r"\b\d{1,3}[.,]\d+\s*°", "градусы координат"),
    (r"\bплен(ных|ными|ные)\b", "пленные"),
]
STOP_SOFT = [
    (r"\bполит(ик|ическ)", "политика"),
    (r"\bпрогноз", "прогнозы"),
    (r"\bоценк", "оценки"),
    (r"\bзападн\w+ экспер", "оценки экспертов"),
    (r"\bпо мнению", "мнения"),
]


def parse(md_path):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    date = shift = source = ""
    m = re.search(r"^#\s+СВОДКА\s+(\d{4})-(\d{2})-(\d{2})\s+(утро|вечер)", raw, re.M)
    if m:
        date = "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
        shift = m.group(4)
    m = re.search(r"^Источник:\s*(.+)$", raw, re.M)
    if m:
        source = m.group(1).strip()

    def block(name):
        m = re.search(r"^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(name), raw, re.M | re.S | re.I)
        return m.group(1).strip() if m else ""

    facts = []
    for line in block("факты").splitlines():
        line = line.strip()
        if not re.match(r"^([-*•]|\d+[.)])\s+", line):
            continue
        body = re.sub(r"^([-*•]|\d+[.)])\s+", "", line).strip()
        if "|" in body:
            head, say = [x.strip() for x in body.split("|", 1)]
        elif re.search(r"\s[—–-]\s", body) and len(body.split("—")[0].split()) <= 8:
            head, say = [x.strip() for x in re.split(r"\s[—–-]\s", body, 1)]
        else:
            head, say = "", body
        say = re.sub(r"\s+", " ", say)
        if say:
            if not head:
                head = re.split(r"[.!?]\s", say)[0][:90].strip()
            note = ""
            parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", say) if x.strip()]
            if len(parts) > 1 and len(head.split()) <= 5:
                note = re.split(r",|\s—\s", parts[2] if len(parts) > 2 else parts[1])[0].strip()
                note = " ".join(note.split()[:10])
            facts.append({"head": head, "say": say, "note": note})
    dirs = [x.strip() for x in re.split(r"[·•|,]", block("Где наши работают")) if x.strip()]
    thanks = [x.strip() for x in re.split(r"[·•|,]", block("Благодарность")) if x.strip()]
    cta = block("Куда идти") or "Адреса и сборы — в описании выпуска"
    return {"date": date, "shift": shift, "source": source, "facts": facts,
            "dirs": dirs, "thanks": thanks, "cta": re.sub(r"\s+", " ", cta)}


def date_words(iso):
    y, mo, d = [int(x) for x in iso.split("-")]
    return "%s %s" % (DAYS[d - 1], MONTHS[mo - 1]), "%d %s %d" % (d, MONTHS[mo - 1].upper(), y)


def build_script(data, facts_max=7):
    if not data["date"]:
        sys.exit("во входном файле нет строки «# СВОДКА YYYY-MM-DD утро|вечер»")
    if not data["shift"]:
        sys.exit("не указано утро/вечер")
    facts = data["facts"][:facts_max]
    if len(facts) < 5:
        print("ВНИМАНИЕ: фактов %d, по ТЗ нужно 5–7" % len(facts), file=sys.stderr)
    say_date, up_date = date_words(data["date"])
    shift_word = "утро" if data["shift"] == "утро" else "вечер"
    shift_gen = "утра" if shift_word == "утро" else "вечера"   # «до вечера», «с утра»
    shift_acc = shift_word                                     # «сводка на утро / на вечер»

    segs = [{
        "id": "s01", "vo": "s01.mp3", "scene": "title", "gap": 1.10,
        "say": "Сводка на %s. Это радио «В ОКОПЕ». %s." % (shift_acc, say_date.capitalize()),
        "title": "СВОДКА", "kicker": "ЕЖЕДНЕВНАЯ ПЕРЕДАЧА",
        "badge": "%s · %s" % (shift_word.upper(), "08:00" if shift_word == "утро" else "20:00"),
        "date": up_date, "sub": "Сводка на %s. Это радио «В ОКОПЕ»." % shift_acc,
    }]

    n = len(facts)
    for i, f in enumerate(facts):
        segs.append({
            "id": "s%02d" % (i + 2), "vo": "s%02d.mp3" % (i + 2), "scene": "fact",
            "gap": 1.15, "idx": i + 1, "n": n,
            "say": f["say"], "head": f["head"], "note": f.get("note", ""),
            "sub": "",
        })

    idx = n + 2
    dirs = data["dirs"][:4]
    segs.append({
        "id": "s%02d" % idx, "vo": "s%02d.mp3" % idx, "scene": "line", "gap": 1.05,
        "say": "Отдельная строка — где наши работают. %s." % (", ".join(dirs) if dirs else "Направления коротко."),
        "kicker": "ОТДЕЛЬНАЯ СТРОКА", "head": "ГДЕ НАШИ РАБОТАЮТ",
        "items": [d.upper() for d in dirs] or ["НАПРАВЛЕНИЯ"],
        "sub": "Где наши работают — направления",
    })

    idx += 1
    th = data["thanks"][:5]
    segs.append({
        "id": "s%02d" % idx, "vo": "s%02d.mp3" % idx, "scene": "thanks", "gap": 1.05,
        "say": "Спасибо тем, кто помогает: %s. Тихо и по делу." % ", ".join(x.lower() for x in th),
        "kicker": "СПАСИБО", "head": "ТЕМ, КТО ПОМОГАЕТ",
        "items": [x.upper() for x in th] or ["ВСЕМ, КТО ПОМОГАЕТ"],
        "sub": "Спасибо всем, кто помогает",
    })

    idx += 1
    cta_say = "Куда идти помогать — %s." % data["cta"].rstrip(".")
    outro_say = "Своих не бросаем. Радио «В ОКОПЕ»."
    cut = round(len(cta_say) / float(len(cta_say) + len(outro_say) + 1), 3)
    segs.append({
        "id": "s%02d" % idx, "vo": "s%02d.mp3" % idx, "scene": "cta", "scene2": "outro",
        "cut": cut, "gap": 0.0, "say": cta_say + " " + outro_say,
        "kicker": "КУДА ИДТИ", "head": "ПОМОГАТЬ ЕСТЬ КУДА",
        "note": data["cta"], "sub": data["cta"],
        "sub2": "Своих не бросаем. Радио «В ОКОПЕ».",
    })

    # не больше 10 реплик за один ход синтеза: склеиваем «где наши» и «спасибо»
    if len(segs) > 10:
        li = next(i for i, x in enumerate(segs) if x["scene"] == "line")
        ti = next(i for i, x in enumerate(segs) if x["scene"] == "thanks")
        ln, th = segs[li], segs[ti]
        cut = round(len(ln["say"]) / float(len(ln["say"]) + len(th["say"]) + 1), 3)
        merged = {
            "id": ln["id"], "vo": ln["vo"], "scene": "line", "scene2": "thanks",
            "cut": cut, "gap": th["gap"],
            "say": ln["say"] + " " + th["say"],
            "kicker": ln["kicker"], "head": ln["head"], "items": ln["items"],
            "sub": ln["sub"],
            "spec2": {"kicker": th["kicker"], "head": th["head"],
                      "items": th["items"], "sub": th["sub"]},
            "sub2": th["sub"],
        }
        segs = [x for i, x in enumerate(segs) if i not in (li, ti)]
        segs.insert(li, merged)
        for n2, x in enumerate(segs, 1):
            x["id"] = "s%02d" % n2
            x["vo"] = "s%02d.mp3" % n2
        print("реплик больше 10 — «где наши» и «спасибо» склеены в одну")

    words = sum(len(s["say"].split()) for s in segs)
    spec = {
        # имя файла — строго латиницей, как требует ТЗ: svodka_YYYY-MM-DD_utro|vecher
        "slug": "svodka_%s_%s" % (data["date"], "utro" if shift_word == "утро" else "vecher"),
        "date": up_date, "shift": shift_word,
        "title_line": "СВОДКА · %s · %s" % (up_date.lower(), shift_word),
        "source": data["source"] or "—",
        "lead": 0.55, "tail": 1.80, "tempo": 1.12,
        "music": {"track": "fvi-Arpent.ogg", "offset": 12.0, "level": 0.20},
        "segments": segs,
    }
    return spec, words


def check(spec, words):
    say_all = " ".join(s["say"] for s in spec["segments"])
    bad = []
    for rx, name in STOP_HARD:
        if re.search(rx, say_all, re.I):
            bad.append("СТОП-ЛИСТ: " + name)
    for rx, name in STOP_SOFT:
        if re.search(rx, say_all, re.I):
            bad.append("проверить вручную: " + name)
    clips = len(spec["segments"])
    if clips > 10:
        bad.append("реплик %d — больше 10 за один ход (озвучивать в два хода)" % clips)
    est = words / 2.25 + 1.05 * clips + 2.35
    if words < 340:
        bad.append("слов %d — мало для 2–3 минут (нужно 350–420)" % words)
    if words > 430:
        bad.append("слов %d — много (нужно 350–420)" % words)
    print("слов: %d · реплик: %d · оценка длительности: %.0f с" % (words, clips, est))
    if not (120 <= est <= 180):
        bad.append("оценка длительности %.0f с вне окна 120–180 с" % est)
    for b in bad:
        print("  !", b)
    return not [b for b in bad if not b.startswith("проверить вручную")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--max-facts", type=int, default=7)
    a = ap.parse_args()
    spec, words = build_script(parse(a.facts), a.max_facts)
    ok = check(spec, words)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print("сценарий:", a.out)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
