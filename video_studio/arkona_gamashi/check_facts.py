#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка ролика «Гамаши АРКОНА» на запрещённые утверждения.
Сканирует экранные тексты рендерера и озвучку. Код 1 = ролик не выпускать.
"""
import io, os, re, sys, tokenize

HERE = os.path.dirname(os.path.abspath(__file__))

BANNED = [
    (r"цен[аыу]|стоимост|₽|руб\b|прайс|дешев|дорог|скидк", "цена"),
    (r"не\s*промок|водонепрониц|абсолютн|100\s?%|гарантир|вечн", "гарантия/свойства"),
    (r"лучш\w*|самый|самые|не имеет аналогов|уникальн|идеальн", "превосходная степень"),
    (r"невидим|не обнаруж|не видно в тепловизор|скрывает от", "скрытность"),
    (r"пул[июяь]|осколк|броне|баллистич", "баллистика"),
    (r"брезент|нейлон\b|полиэстер", "чужая ткань (в карточке только Кордура)"),
    (r"\b\d+(?:[.,]\d+)?\s?(?:кг|грамм|г)\b", "вес (в карточке нет)"),
]

ALLOW = [r"1000\s?d", r"кордура\s?1000", r"35\s?см", r"40\s?см", r"45\s?см",
         r"49\s?см", r"51\s?см", r"46\s?см", r"две штуки", r"2 шт"]


def clean(t):
    for a in ALLOW:
        t = re.sub(a, " ", t, flags=re.I)
    return t


def strings(path):
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(io.BytesIO(fh.read()).readline):
            if tok.type == tokenize.STRING:
                try:
                    v = eval(tok.string, {"__builtins__": {}})
                except Exception:
                    continue
                if isinstance(v, str) and len(v) > 2:
                    out.append(v)
    return out


bad = []
for f in ("render_reel.py", "build_audio.py"):
    for t in strings(os.path.join(HERE, f)):
        c = clean(t)
        for rx, why in BANNED:
            m = re.search(rx, c, flags=re.I)
            if m:
                bad.append((f, why, m.group(0), t))

if bad:
    for f, why, hit, t in bad:
        print("!! %s: %s — «%s»\n   %s" % (f, why, hit, t))
    print("\nвсего нарушений:", len(bad))
    sys.exit(1)
print("Запрещённых утверждений не найдено ✔")
