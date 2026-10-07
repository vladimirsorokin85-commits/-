#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СЛЕЖЕНИЕ ЗА ЦЕНАМИ — закуп поставщика и наши розничные.

Задача владельца: «дальше будешь следить, чтоб не подорожал».
Как это работает:
  • baseline — зафиксированная закупка (catalog/price_baseline.json, в git);
  • при каждом обновлении каталога сравниваем и показываем, что подорожало/подешевело;
  • розницу (свою цену) владелец даёт сам — она записывается в catalog/retail.json;
  • если закупка выросла и маржа падает ниже порога — предупреждение.

Команды:
  python3 catalog/price_watch.py snapshot            # зафиксировать текущую закупку
  python3 catalog/price_watch.py check               # что изменилось (по умолчанию)
  python3 catalog/price_watch.py retail 00321 1200   # записать свою розницу
  python3 catalog/price_watch.py report              # отчёт по марже (нужна розница)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(HERE, "data", "catalog_index.json")
BASELINE = os.path.join(HERE, "price_baseline.json")
RETAIL = os.path.join(HERE, "retail.json")
REPORT_DIR = os.path.join(HERE, "reports")

MIN_MARGIN_PCT = 12.0  # ниже этого уровня предупреждаем: «закупка съедает маржу»


def load_index():
    if not os.path.exists(INDEX):
        raise SystemExit(f"Нет каталога: {INDEX} (сначала bash tools/catalog_pull.sh)")
    return json.load(open(INDEX, encoding="utf-8"))


def key(row):
    return str(row.get("code"))


def snapshot():
    idx = load_index()
    data = {
        r["id"]: {
            "code": str(r.get("code")), "name": r.get("name"), "purchase": r.get("price"),
            "stock": int(r.get("stock") or 0),
        }
        for r in idx if r.get("price")
    }
    json.dump(data, open(BASELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Зафиксировано позиций: {len(data)} → {os.path.relpath(BASELINE, ROOT)}")


def check():
    if not os.path.exists(BASELINE):
        raise SystemExit("Нет baseline — сначала: python3 catalog/price_watch.py snapshot")
    base = json.load(open(BASELINE, encoding="utf-8"))
    cur = {r["id"]: r for r in load_index()}

    up, down, gone, new = [], [], [], []
    for pid, b in base.items():
        c = cur.get(pid)
        if not c:
            gone.append(b)
            continue
        b_p, c_p = int(b.get("purchase") or 0), int(c.get("price") or 0)
        if c_p > b_p:
            up.append((b, c_p, (c_p - b_p) / b_p * 100 if b_p else 0))
        elif c_p < b_p:
            down.append((b, c_p, (c_p - b_p) / b_p * 100 if b_p else 0))
    base_ids = set(base)
    for pid, c in cur.items():
        if pid not in base_ids and c.get("price"):
            new.append(c)

    print(f"Проверено позиций: {len(base)}")
    print(f"  подорожало: {len(up)} | подешевело: {len(down)} | пропало из каталога: {len(gone)}")
    if up:
        print("\nПОДОРОЖАЛО (проверить розницу!):")
        for b, c_p, pct in sorted(up, key=lambda x: -x[2])[:30]:
            print(f"  {b['code']:>8} | {int(b['purchase']):>8} → {c_p:>8} (+{pct:.1f}%) | {b['name'][:52]}")
    if down:
        print("\nПОДЕШЕВЕЛО (можно сыграть на цене):")
        for b, c_p, pct in sorted(down, key=lambda x: x[2])[:20]:
            print(f"  {b['code']:>8} | {int(b['purchase']):>8} → {c_p:>8} ({pct:.1f}%) | {b['name'][:52]}")
    if gone:
        print("\nПРОПАЛО ИЗ КАТАЛОГА (проверить наличие перед постом):")
        for b in gone[:20]:
            print(f"  {b['code']:>8} | {b['name'][:60]}")
    if new:
        print(f"\nНОВЫЕ ПОЗИЦИИ: {len(new)}")

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "price_changes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Изменения закупки поставщика\n\n")
        f.write(f"- подорожало: {len(up)}\n- подешевело: {len(down)}\n- пропало: {len(gone)}\n- новых: {len(new)}\n\n")
        for title, rows in (("Подорожало", up), ("Подешевело", down)):
            f.write(f"## {title}\n\n")
            for b, c_p, pct in rows:
                f.write(f"- `{b['code']}` {b['name'][:70]}: {int(b['purchase'])} → {c_p} ({pct:+.1f}%)\n")
            f.write("\n")
    print(f"\nОтчёт: {os.path.relpath(path, ROOT)}")
    return 1 if up else 0


def set_retail(code, price):
    idx = load_index()
    row = next((r for r in idx if str(r.get("code")) == str(code)), None)
    if not row:
        raise SystemExit(f"Код {code} не найден в каталоге")
    data = json.load(open(RETAIL, encoding="utf-8")) if os.path.exists(RETAIL) else {}
    data[str(code)] = {
        "id": row["id"], "name": row["name"], "purchase": row.get("price"), "retail": int(price),
        "margin_pct": round((int(price) - int(row.get("price") or 0)) / int(price) * 100, 1) if int(price) else 0,
    }
    json.dump(data, open(RETAIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rec = data[str(code)]
    print(f"{code} {row['name'][:50]}: закуп {rec['purchase']} → розница {rec['retail']} "
          f"(маржа {rec['margin_pct']}%)")


def report():
    if not os.path.exists(RETAIL):
        raise SystemExit("Розница пока не задана: python3 catalog/price_watch.py retail <код> <цена>")
    data = json.load(open(RETAIL, encoding="utf-8"))
    # ищем строго по id: коды поставщика повторяются (62 дубля), по коду можно взять не тот товар
    cur = {r["id"]: r for r in load_index()}
    print(f"{'код':>8} | {'закуп':>8} | {'розница':>8} | {'маржа':>7} | позиция")
    warn = []
    for code, rec in sorted(data.items()):
        c = cur.get(rec.get("id")) or next((r for r in cur.values() if str(r.get("code")) == code), None)
        purchase = int(rec.get("purchase") or 0)
        retail = int(rec.get("retail") or 0)
        if c:
            purchase = int(c.get("price") or purchase)
        margin = (retail - purchase) / retail * 100 if retail else 0
        flag = ""
        if margin < MIN_MARGIN_PCT:
            flag = "  ⚠ маржа ниже порога"
            warn.append((code, rec["name"], margin))
        print(f"{code:>8} | {purchase:>8} | {retail:>8} | {margin:>6.1f}% | {rec['name'][:46]}{flag}")
    if warn:
        print(f"\nВНИМАНИЕ: {len(warn)} позиций с маржой ниже {MIN_MARGIN_PCT}% —"
              " либо поднять розницу, либо не давать скидку.")


def main(argv):
    cmd = (argv[0] if argv else "check").lower()
    if cmd == "snapshot":
        snapshot()
    elif cmd == "check":
        return check()
    elif cmd == "retail":
        if len(argv) < 3:
            raise SystemExit("Использование: price_watch.py retail <код> <цена>")
        set_retail(argv[1], argv[2])
    elif cmd == "report":
        report()
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
