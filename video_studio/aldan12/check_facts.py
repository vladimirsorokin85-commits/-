#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка ролика на запрещённые утверждения (п. 2 и п. 11 брифа «Алдан-12»).

Сканирует экранные тексты и VO из shots.py, ищет то, что запрещено говорить:
дальность, цену, вес, габариты, «глушит/сбивает», «100 %» и т. п.
Код возврата 1 — есть нарушения, рендер не запускать.

    python3 video_studio/aldan12/check_facts.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shots import SHOTS, TEASER  # noqa: E402

# (регулярка, что именно запрещено)
BANNED = [
    (r"дальност|радиус обнаруж|обнаружива\w* за|километр|\bкм\b|метров\b|\bм\b(?![а-я])", "дальность/дистанция"),
    (r"цен[аыу]|стоимость|₽|руб|прайс|\bдешев", "цена"),
    (r"весит|\bкг\b|килограмм|(?<![а-яё])грамм", "вес"),
    (r"габарит|миллиметр|\bмм\b|\bсм\b", "габариты"),
    (r"(?<![а-яё])глуш|сбива|перехват|подавля", "воздействие на дрон"),
    (r"100\s?%|стопроцентн|гарантиру", "гарантия обнаружения"),
    (r"сертифиц|лицензи|официальное видео", "сертификация/статус"),
    (r"час(ов|а)? работ|время работы|автономн|до \d+ час", "время работы"),
    (r"\bмгц\b", "частота (кроме 5800)"),
]
# что разрешено, несмотря на совпадения
ALLOW = [
    r"5800\s?МГц|пяти тысячах восьмистах мегагерцах|пяти тысяч восьмисот мегагерц",
    r"10 минут|за десять минут",
]
NUM_OK = {"12", "8", "1.6", "1.2.6", "5800", "5", "3", "4", "2", "1", "5t", "a2", "a1", "otg", "led"}


def clean(text):
    for a in ALLOW:
        text = re.sub(a, " ", text, flags=re.I)
    return text


def scan():
    bad = []
    for src_name, items in (("ГОРИЗОНТАЛЬ", SHOTS), ("ТИЗЕР", TEASER)):
        for it in items:
            if src_name == "ГОРИЗОНТАЛЬ":
                _, screen, vo, _, _, _ = it
            else:
                screen, vo, _, _, _ = it
            for fld, txt in (("экран", screen), ("VO", vo)):
                t = clean(txt or "")
                for rx, why in BANNED:
                    m = re.search(rx, t, flags=re.I)
                    if m:
                        bad.append((src_name, fld, why, m.group(0), txt))
    return bad


def numbers():
    """Все цифры в текстах — сверить глазами со списком разрешённых."""
    seen = {}
    for it in SHOTS + TEASER:
        for txt in it:
            if not isinstance(txt, str):
                continue
            for m in re.finditer(r"\d[\d.,]*", txt):
                seen.setdefault(m.group(0), 0)
                seen[m.group(0)] += 1
    return seen


if __name__ == "__main__":
    bad = scan()
    if bad:
        print("НАРУШЕНИЯ:")
        for src, fld, why, frag, txt in bad:
            print(f"  ✘ [{src} · {fld}] {why}: «{frag}»  ← {txt[:90]}")
    else:
        print("Запрещённых утверждений не найдено ✔")
    print("\nЦифры в текстах (сверить со списком):")
    for k, v in sorted(numbers().items()):
        flag = "" if k.lower() in NUM_OK else "  ← проверить"
        print(f"  {k:8s} ×{v}{flag}")
    sys.exit(1 if bad else 0)
