#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка ролика «Тепловизор 360°» на запрещённые утверждения.

Сканирует экранные тексты и VO из shots.py. Запрещено: цены, эффекты оружия
(«глушит/сбивает/перехватывает»), гарантии обнаружения, выдуманная дальность,
время автономной работы, сертификация.

    python3 video_studio/thermal_360/check_facts.py    # код 1 = ролик не собирать
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shots import SHOTS, TEASER  # noqa: E402

BANNED = [
    (r"цен[аыу]|стоимост|₽|руб\b|прайс|дешев|дорог|скидк", "цена"),
    (r"глуш|сбива|перехват|подавля|уничтож|поража", "воздействие на цель"),
    (r"100\s?%|стопроцентн|гарантиру|всегда обнаруж|безотказн", "гарантия"),
    (r"(обнаруж|видит|засека|берёт|берет)\w*[^.]{0,24}(километр|\d+\s?км)", "дальность обнаружения"),
    (r"час(ов|а)? работ|время работы|автономн|сутки работ", "время работы"),
    (r"сертифиц|лицензи|официальн\w* поставщик", "сертификация/статус"),
    (r"лучш\w*|самый точн|не имеет аналогов|уникальн", "превосходная степень"),
]

# что разрешено, несмотря на совпадения
ALLOW = [
    r"до тысячи метров|до 1000\s?м|тысячи метров",     # лазерный целеуказатель
    r"12\s?(в|вольт)|двенадцати вольт|двенадцать вольт",
    r"24\s?(в|вольт)|двадцать четыре вольта|двадцати четырёх вольт",
    r"1000\s?м", r"3,8\s?кг", r"40×30×30", r"640×512", r"1920×1080",
]


def clean(text):
    for a in ALLOW:
        text = re.sub(a, " ", text, flags=re.I)
    return text


def reels_texts():
    """Все строковые литералы рендерера рилса (экранные тексты и титры)."""
    import io
    import tokenize
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_reel.py")
    if not os.path.exists(path):
        return []
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


def scan():
    bad = []
    for src, items in (("ГОРИЗОНТАЛЬ", SHOTS), ("ТИЗЕР", TEASER)):
        for it in items:
            if src == "ГОРИЗОНТАЛЬ":
                _, screen, vo = it[0], it[1], it[2]
            else:
                screen, vo = it[0], it[1]
            for field, txt in (("экран", screen), ("VO", vo)):
                t = clean(txt or "")
                for rx, why in BANNED:
                    m = re.search(rx, t, flags=re.I)
                    if m:
                        bad.append((src, field, why, m.group(0), txt))
    for txt in reels_texts():
        t = clean(txt)
        for rx, why in BANNED:
            m = re.search(rx, t, flags=re.I)
            if m:
                bad.append(("РИЛС", "экран", why, m.group(0), txt))
    return bad


if __name__ == "__main__":
    bad = scan()
    if not bad:
        print("Запрещённых утверждений не найдено ✔")
    else:
        for src, field, why, hit, txt in bad:
            print(f"!! {src} / {field}: {why} — «{hit}»\n   {txt}")
        print(f"\nвсего нарушений: {len(bad)}")
        sys.exit(1)

    # подсказка: все цифры в ролике — сверить глазами с facts.md
    nums = set()
    for it in SHOTS:
        for txt in (it[1], it[2]):
            nums |= set(re.findall(r"\d+[.,]?\d*\s?(?:мм|см|кг|м|в|°|мкм|мкм)?", txt or ""))
    print("\nЦифры в текстах (сверить со списком):")
    for n in sorted(nums):
        print("  ", n.strip())
