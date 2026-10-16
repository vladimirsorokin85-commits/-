"""Storyboard for спецвыпуск «Их нравы», часть 8: паёк D (3 главы + пролог). Assets: assets_dration/dr_XX.jpg"""
import re

AMBER = (245, 158, 11)
RED = (239, 68, 68)
GREEN = (132, 204, 22)
CYAN = (34, 211, 238)
WHITE = (240, 240, 240)

BRAND = "МАГАЗИН «В ОКОПЕ»"
BRAND_LINKS = "t.me/vokope_ru  ·  vk.com/vokope_rus"
SERIES = "ИХ НРАВЫ"
N_CHAPTERS = 3  # 3 chapters, prologue and outro are separate segments

# scene ids that are archive / painting / thermal / 3D — not film-graded
NO_GRADE = {2, 3, 4, 5, 9}  # archival / sepia / B&W frames — not film-graded

PROLOGUE = {
    "pool": [1, 2, (1, "punch", (0.45, 0.55)), 2, 1],
    "badges": [("шоколад, который", "ШОКОЛАД, КОТОРЫЙ НЕНАВИДЕЛИ", AMBER),
               ("специально", "НЕ ИСПОРТИЛСЯ — СДЕЛАЛИ ТАКИМ", RED)],
}

CHAPTERS = {
    1: {"title": "ЗАДАНИЕ ИНТЕНДАНТА", "sub": "АПРЕЛЬ 1937 · HERSHEY", "short": "1937",
        "hero": 3, "accent": AMBER,
        "pool": [3, (3, "punch", (0.5, 0.5)), 4, 2, (5, "punch", (0.5, 0.4)), 5, 4, (2, "punch", (0.3, 0.5))],
        "badges": [("Пол Логан", "КАПИТАН ПОЛ ЛОГАН · 1937", WHITE),
                   ("четыре унции", "4 УНЦИИ · 113 ГРАММОВ", AMBER),
                   ("ста двадцати градусов", "ДО 120 °F · НЕ ПЛАВИТСЯ", WHITE),
                   ("картошки", "«ЧУТЬ ЛУЧШЕ КАРТОШКИ»", RED),
                   ("девяносто тысяч", "90 000 БАТОНЧИКОВ · ВРУЧНУЮ", GREEN),
                   ("шестьсот калорий", "600 КАЛОРИЙ · НА БАТОНЧИК", CYAN)]},
    2: {"title": "СЕКРЕТНОЕ ОРУЖИЕ", "sub": "ФРОНТ И ПАЁК D", "short": "ПАЁК D",
        "hero": 6, "accent": RED,
        "pool": [6, (6, "punch", (0.5, 0.6)), 7, 8, (7, "punch", (0.5, 0.5)), 6, 8, (8, "punch", (0.5, 0.5))],
        "badges": [("очень твёрдый", "СУХОЙ И ТВЁРДЫЙ", WHITE),
                   ("ножом", "СТРУГАЛИ НОЖОМ", RED),
                   ("получаса", "ЕСТЬ ДОЛГО: ПОЛЧАСА", AMBER),
                   ("секретное оружие Гитлера", "«СЕКРЕТНОЕ ОРУЖИЕ ГИТЛЕРА»", RED),
                   ("тысяча восемьсот", "1800 ККАЛ · НА ДЕНЬ", GREEN),
                   ("почти невозможно", "ЕСТЬ ПОЧТИ НЕВОЗМОЖНО", WHITE)]},
    3: {"title": "ТРИ МИЛЛИАРДА", "sub": "ЧТО ОСТАЛОСЬ ОТ ПАЙКА", "short": "TROPICAL",
        "hero": 9, "accent": CYAN,
        "pool": [9, (9, "punch", (0.5, 0.5)), 10, 9, (10, "punch", (0.4, 0.5)), 10, 9],
        "badges": [("трёх миллиардов", "3 МИЛЛИАРДА БАТОНЧИКОВ", AMBER),
                   ("двадцать четыре миллиона", "24 МЛН В НЕДЕЛЮ", RED),
                   ("Tropical", "TROPICAL — ДЛЯ ЖАРЫ", CYAN),
                   ("до 1991", "ВЫДАВАЛИ ДО 1991 ГОДА", WHITE),
                   ("не только калории", "ПАЁК — НЕ ТОЛЬКО КАЛОРИИ", GREEN)]},
}

# no text replacements needed for this episode (kept for pipeline compatibility)
REPL = []

def display_text(s):
    for a, b in REPL:
        s = s.replace(a, b)
    return s


HOT = ["нога", "ноги", "стоп", "мозол", "пузыр", "носк", "носок", "шерст", "хлопок", "хлопк", "портянк",
       "кирз", "мембран", "окопная", "онемени", "обморож", "снегом", "привал", "пластыр", "сапог", "берц",
       "сосуд", "влаг", "пот", "сдвиг", "лёд", "льда", "сухой", "сухая", "сухие", "смекалка", "окопе",
       "спецвыпуск", "телеграм", "вконтакте", "ресурс", "оружие", "вооружения"]
RED_HOT = ["ошибк", "ампутац", "отмирать", "кров", "беды", "беда", "враг", "ловушк", "опасн", "вредн",
           "убить", "похоронят", "некроз", "срыв"]


def word_color(w):
    lw = w.lower()
    if any(ch.isdigit() for ch in w) or "₽" in w or "%" in w:
        return "num"
    if any(h in lw for h in RED_HOT):
        return "red"
    if any(h.lower() in lw for h in HOT):
        return "hot"
    return "w"


def chunk_words(text, max_words=4, max_chars=26):
    words = text.split()
    chunks, cur = [], []
    for w in words:
        if w in ("—", "-") and cur:
            cur.append(w)
            continue
        trial = " ".join(cur + [w])
        if cur and (len(cur) >= max_words or len(trial) > max_chars):
            chunks.append(cur)
            cur = [w]
        else:
            cur.append(w)
        if re.search(r"[.!?:,]$", w) and len(cur) >= 2:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c]


# ---------------------------------------------------------------- shot builder
MOVES = ["in", "left", "out", "right", "up", "in", "out"]
TARGET = 3.6     # seconds per shot


def norm_item(it, k):
    if isinstance(it, int):
        return {"img": it, "move": MOVES[k % len(MOVES)], "focus": [0.5, 0.45]}
    img, move = it[0], it[1]
    focus = list(it[2]) if len(it) > 2 else [0.5, 0.45]
    return {"img": img, "move": move, "focus": focus}


def build_shots(tl):
    shots, badges, subs = [], [], []
    shots.append({"kind": "intro", "t0": 0.0, "t1": tl["intro"]})
    k = 0
    for seg in tl["segments"]:
        if seg["kind"] in ("prologue", "body"):
            data = PROLOGUE if seg["kind"] == "prologue" else CHAPTERS[seg["chapter"]]
            sents, vt, pool = seg["sentences"], seg["voice_t0"], data["pool"]
            # cut points: sentence boundaries, long sentences split into ~TARGET pieces
            cuts = []
            for i, s in enumerate(sents):
                a = seg["t0"] if i == 0 else vt + s["t0"]
                b = seg["t1"] if i == len(sents) - 1 else vt + s["t1"]
                n = max(1, round((b - a) / TARGET))
                cuts += [(a + (b - a) * j / n, a + (b - a) * (j + 1) / n) for j in range(n)]
            # merge very short pieces (<1.6 s) into the previous one
            merged = []
            for a, b in cuts:
                if merged and b - a < 1.6:
                    merged[-1] = (merged[-1][0], b)
                else:
                    merged.append((a, b))
            seg_shots = []
            for j, (a, b) in enumerate(merged):
                it = norm_item(pool[j % len(pool)], k)
                sh = {"kind": "img", "t0": round(a, 3), "t1": round(b, 3), **it}
                sh["flash"] = it["move"] == "punch"
                sh["sfx"] = "hit" if it["move"] == "punch" else "whoosh"
                sh["sfx_gain"] = 0.30 if it["move"] == "punch" else 0.15
                seg_shots.append(sh)
                k += 1
            seg_shots[0]["sfx"] = None
            shots.extend(seg_shots)
            # keyword badges
            used = set()
            bl = []
            for kw, text, col in data["badges"]:
                for i, s in enumerate(sents):
                    if kw.lower() in s["text"].lower() and i not in used:
                        used.add(i)
                        bl.append((i, text, col))
                        break
            bl.sort()
            for n_, (i, text, col) in enumerate(bl):
                s = sents[i]
                t0 = vt + s["t0"] + 0.15
                t1 = min(vt + s["t1"] + 0.4, t0 + 3.8, seg["t1"] - 0.05)
                if n_ + 1 < len(bl):
                    t1 = min(t1, vt + sents[bl[n_ + 1][0]]["t0"] + 0.05)
                badges.append({"t0": round(t0, 3), "t1": round(t1, 3), "text": text, "color": list(col)})
            for s in sents:
                chunks = chunk_words(s["disp"])
                total_chars = sum(len(" ".join(c)) for c in chunks)
                st, en = vt + s["t0"], vt + s["t1"] - 0.05
                cur = st
                for c in chunks:
                    L = len(" ".join(c))
                    d = (en - st) * L / max(1, total_chars)
                    subs.append({"t0": round(cur, 3), "t1": round(cur + d, 3),
                                 "words": [[w, word_color(w)] for w in c]})
                    cur += d
        elif seg["kind"] == "title":
            shots.append({"kind": "title", "chapter": seg["chapter"], "t0": seg["t0"], "t1": seg["t1"],
                          "slam_t": seg["slam_t"], "phrase2_t": seg["phrase2_t"]})
        elif seg["kind"] == "outro":
            shots.append({"kind": "outro", "t0": seg["t0"], "t1": seg["t1"]})
    return shots, badges, subs
