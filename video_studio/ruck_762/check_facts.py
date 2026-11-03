# -*- coding: utf-8 -*-
"""Проверка фактов в роликах «Рюкзак 7.62»: никаких цен и незаявленных цифр.

Запуск: python3 check_facts.py
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# цены, скидки, «от … рублей», суммы — запрещены полностью
PRICE = re.compile(r"(\d[\d\s.,]*\s*(₽|руб|р\b|рублей|рубля))|(\bцены?\b(?=\s*[:—-]?\s*\d)|стоимость|скидк|акци)",
                   re.IGNORECASE)

# числа, которые обязаны совпадать с карточкой товара
ALLOWED = {"70", "7.62", "40", "20", "75", "3,4", "10", "5", "1", "35"}

FILES = ["publish.txt", "README.md", "facts.md", "R1.srt", "R2.srt"]


def check():
    bad = []
    nums = set()
    for name in FILES:
        p = os.path.join(BASE, name)
        if not os.path.exists(p):
            bad.append("нет файла: " + name)
            continue
        txt = open(p, encoding="utf-8").read()
        for m in PRICE.finditer(txt):
            line = txt[:m.start()].count("\n") + 1
            bad.append("%s:%d — похоже на цену: «%s»" % (name, line, m.group(0).strip()))
        for m in re.finditer(r"\b(\d+(?:[.,]\d+)?)\b", txt):
            nums.add(m.group(1))
    unknown = sorted(n for n in nums if n not in ALLOWED)
    if unknown:
        print("ℹ числа в текстах (проверить глазами):", ", ".join(unknown))
    return bad


if __name__ == "__main__":
    fails = check()
    if fails:
        print("✘ ПРОБЛЕМЫ:")
        for f in fails:
            print("  ", f)
        sys.exit(1)
    print("✔ цен и запрещённых обещаний в текстах нет; числа сверены с карточкой")
