#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭЛЕКТРОСТАНЦИИ И ПАНЕЛИ (EcoFlow / Jackery / DJI) — подбор и честный расчёт автономности.

Правила:
  • наличие у поставщика подтверждаем ПЕРЕД обещанием клиенту;
  • розница = закуп +10 % (уже посчитана в прайсе);
  • автономность НИКОГДА не считаем по паспортной ёмкости:
    самопотребление 15–25 Вт + КПД 0.80–0.90 на нагрузке <200 Вт (и это ещё «лето»).

Примеры:
  python3 -m catalog.power --list
  python3 -m catalog.power --need 12h@62W              # сколько Вт·ч реально нужно
  python3 -m catalog.power --pick 12h@62W              # что из прайса тянет, что нет
  python3 -m catalog.power --pick 8h@120W --budget 90000
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

SUP_PATH = os.path.join(HERE, "suppliers.json")
SELF_W = (15, 25)          # самопотребление станции, Вт
EFF = (0.80, 0.90)         # КПД на нагрузке <200 Вт


def load_power():
    data = json.load(open(SUP_PATH, encoding="utf-8"))
    return data["power"]


def money(v):
    return "—" if v is None else f"{int(round(v)):,}".replace(",", " ") + " ₽"


def parse_load(spec: str):
    """'12h@62W' -> (12.0, 62.0); '500' -> (None, 500)."""
    m = re.match(r"^\s*(?:(\d+(?:[.,]\d+)?)\s*h\s*[@хx*]\s*)?(\d+(?:[.,]\d+)?)\s*(?:w|вт)?\s*$", spec, re.I)
    if not m:
        raise SystemExit(f"Не понял нагрузку «{spec}». Пример: 12h@62W")
    hours = float(m.group(1).replace(",", ".")) if m.group(1) else None
    watts = float(m.group(2).replace(",", "."))
    return hours, watts


def required_wh(watts: float, hours: float):
    """Реально необходимая ёмкость: худший случай (самопотребление 25 Вт, КПД 0.80)."""
    need_best = (watts + SELF_W[0]) * hours / EFF[1]
    need_worst = (watts + SELF_W[1]) * hours / EFF[0]
    return need_best, need_worst


def pick(need_worst, capacity, budget=None):
    lines = []
    for it in capacity:
        if budget and it["retail"] and it["retail"] > budget:
            continue
        if not it["wh"]:
            # ёмкость в прайсе не указана — не выдумываем, отправляем уточнять
            verdict = "ёмкость уточнить"
        elif it["wh"] >= need_worst:
            verdict = "ТЯНЕТ с запасом"
        elif it["wh"] >= need_worst * 0.75:
            verdict = "на грани — не гарантирую"
        else:
            verdict = "НЕ ТЯНЕТ"
        lines.append(f"[{verdict:18}] {it['model']:<26} {it['wh'] or '?':>4} Вт·ч   "
                     f"закуп {money(it['purchase'])}   розница {money(it['retail'])}"
                     + (f"   ({it['note']})" if it.get("note") else ""))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Электростанции: подбор + расчёт автономности")
    ap.add_argument("--list", action="store_true", help="весь прайс")
    ap.add_argument("--need", help="посчитать нужную ёмкость, пример 12h@62W")
    ap.add_argument("--pick", help="подобрать из прайса под нагрузку, пример 12h@62W")
    ap.add_argument("--budget", type=float, help="розница не дороже")
    args = ap.parse_args(argv)

    power = load_power()
    items = [i for i in power["items"] if not i.get("panel")]
    panels = [i for i in power["items"] if i.get("panel")]

    if args.list or not (args.need or args.pick):
        print("Прайс поставщика от %s. Наличие и EU-версию подтверждать перед обещанием клиенту.\n"
              % power.get("price_date", "—"))
        for it in power["items"]:
            extra = f" · {it['note']}" if it.get("note") else ""
            print(f"{it['model']:<34} {'панель' if it.get('panel') else (str(it['wh']) + ' Вт·ч'):>8}   "
                  f"закуп {money(it['purchase']):>10}   розница {money(it['retail']):>10}{extra}")
        print("\nРозница = закуп +10 %. Логистика: СДЭК, предоплата переводом, доставку платит клиент.")
        return 0

    spec = args.need or args.pick
    hours, watts = parse_load(spec)
    if hours is None:
        raise SystemExit("Для расчёта нужна длительность: например 12h@62W")
    best, worst = required_wh(watts, hours)
    print(f"Нагрузка {watts:g} Вт на {hours:g} ч")
    print(f"  · самопотребление {SELF_W[0]}–{SELF_W[1]} Вт, КПД {EFF[0]:.2f}–{EFF[1]:.2f}")
    print(f"  · реально нужно: от {best:.0f} до {worst:.0f} Вт·ч (для гарантии ориентируйся на {worst:.0f})")
    print("  · паспортная ёмкость ≠ автономность: никогда не обещать по паспорту\n")

    if args.pick:
        print("Что подходит из прайса (розница = закуп +10 %):")
        for line in pick(worst, items, args.budget):
            print("  " + line)
        if panels:
            print("\nПанели (заряд на солнце):")
            for it in panels:
                print(f"  · {it['model']:<24} закуп {money(it['purchase'])}   розница {money(it['retail'])}")
        unknown = [it["model"] for it in items if not it["wh"]]
        if unknown:
            print("\nЁмкость в прайсе не указана (уточнить у поставщика, не выдумывать): "
                  + ", ".join(unknown))
        print("\n⚠ Наличие у поставщика подтвердить ПЕРЕД обещанием клиенту. "
              "Фото — только от поставщика. EU-версию подтверждать отдельно.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
