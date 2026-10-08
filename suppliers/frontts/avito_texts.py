#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тексты объявлений для Авито — поставщик front-ts.ru.

Один файл на раздел: suppliers/frontts/texts/<раздел>.py
В каждом — TEXTS: {slug: {"title": …, "category": …, "desc": …}}
Заголовок ≤ 50 знаков (лимит Авито), описание — продающее и «экспертное»:
что это, почему так устроено, кому и как подобрать. Без цен, остатков и оплаты.
"""
import importlib

GROUPS = ["odezhda", "ragruzka", "podacha", "med", "ryukzaki", "instrument", "tunning"]

GROUP_TITLES = {
    "odezhda": "Одежда и головные уборы",
    "ragruzka": "Разгрузка, подсумки, ремни",
    "podacha": "Системы подачи боеприпасов",
    "med": "Тактическая медицина",
    "ryukzaki": "Рюкзаки и сумки",
    "instrument": "Штурмовой инструмент",
    "tunning": "Тюнинг и аксессуары",
}

# товары, которые Авито может не пропустить (проверить перед выкладкой)
RISKY = {
    "rassypnaya-pulemetnaya-lenta-spoloh": "пулемётная лента — Авито может счесть снаряжением к оружию",
    "sistema-podachi-boepripasov-mantikora": "система подачи боеприпасов",
    "sistema-podachi-boepripasov-piton": "система подачи боеприпасов",
    "sistema-podachi-boepripasov-skorpion": "система подачи боеприпасов",
    "skorpion": "проверить, что это за позиция",
    "skorpion-english": "английская версия страницы «Скорпион»",
    "adapter-priklada-pkm": "деталь к оружию — формулировать как аксессуар",
}

TEXTS = {}
for _g in GROUPS:
    _m = importlib.import_module(f"texts.{_g}")
    for _k, _v in getattr(_m, "TEXTS", {}).items():
        assert _k not in TEXTS, f"дубль текста: {_k}"
        TEXTS[_k] = _v
