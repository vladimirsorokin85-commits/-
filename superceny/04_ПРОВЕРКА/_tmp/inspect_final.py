import json
import re
from pathlib import Path

QA = Path(r"D:\Проекты Дипсик\В ОКОПЕ\superceny\04_ПРОВЕРКА")
READY = Path(r"D:\Проекты Дипсик\В ОКОПЕ\superceny\05_ГОТОВОЕ")
SC = READY.parent

d = json.loads((QA / "QA_АВТОПРОВЕРКА_СУПЕРЦЕНЫ.json").read_text(encoding="utf-8"))
print("summary:", d["summary"], "| stats:", {k: v for k, v in d["stats"].items() if k != "positions_list"})
for f in d["findings"]:
    print(f"[{f['code']}] {f['subject']} — {f['msg'][:180]}")

cl = (READY / "ЧЕК_ЛИСТ_ФАЙЛОВ.md").read_text(encoding="utf-8")
print("\nchecklist head:")
print("\n".join(cl.splitlines()[:10]))

g = (READY / "gallery" / "index.html").read_text(encoding="utf-8")
refs = set(re.findall(r"[^\"']+\.png", g))
print("gallery refs:", len(refs), "| external:", len(re.findall(r"https?://", g)))
gpos = sorted(set(re.findall(r"(\d{2}_[А-Яа-яЁёA-Za-z0-9\-]+)/", g)))
print("gallery folders:", len(gpos))

print("\npositions (20):")
for p in d["positions"]:
    print(p["order"], "|", p["folder"], "|", p["name"], "| cat:", p["catalog"], "| specs:", p["specs"], "| placeholder:", p["placeholder"])
