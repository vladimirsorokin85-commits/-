"""Storyboard for «Окопная смекалка» v4: chapter data, shot plan per sentence,
fact badges, subtitle display text."""
import re

AMBER = (245, 158, 11)
RED = (239, 68, 68)
GREEN = (132, 204, 22)
CYAN = (34, 211, 238)
WHITE = (240, 240, 240)

BRAND = "МАГАЗИН «В ОКОПЕ»"
BRAND_LINKS = "t.me/vokope_ru  ·  vk.com/vokope_rus"

# plan: sentence index -> image id | (image, move[, focus]) | [img, img, ...] (rapid split)
PROLOGUE = {
    "plan": {
        0: [(30, "in"), (5, "punch", (0.5, 0.3))],
        1: [1, (12, "punch", (0.5, 0.45))],
        2: [18, (16, "punch", (0.5, 0.5))],
        3: [(1, "in"), 2, 4, 20, 24, (29, "punch")],
        4: (27, "punch", (0.3, 0.45)),
        5: (9, "punch", (0.6, 0.35)),
    },
    "badges": {
        0: ("СПЕЦВЫПУСК · " + BRAND, AMBER),
        1: ("3 СЕКУНДЫ ДО ВЫСТРЕЛА", RED),
        2: ("ТЕПЛОВИЗОР ДРОНА", RED),
        3: ("ВЕЩИ ЗА КОПЕЙКИ", AMBER),
        4: ("5 ХИТРОСТЕЙ", AMBER),
    },
}

CHAPTERS = {
    1: {
        "title": "КАПРОНОВЫЙ ЧУЛОК НА ПРИЦЕЛЕ",
        "sub": "АНТИБЛИК ОПТИКИ ЗА 0 ₽",
        "short": "ЧУЛОК НА ПРИЦЕЛЕ",
        "hero": 2, "accent": AMBER,
        "plan": {
            0: (11, "in", (0.5, 0.6)), 1: (1, "punch", (0.55, 0.3)), 2: (1, "left"), 3: (11, "punch", (0.5, 0.65)),
            4: (12, "shake"), 5: (13, "in"), 6: (2, "out"), 7: (2, "punch", (0.5, 0.35)), 8: (2, "right"),
            9: (13, "punch", (0.75, 0.55)), 10: (1, "in"), 11: (13, "left", (0.25, 0.5)), 12: (14, "out"),
            13: (14, "punch", (0.62, 0.55)), 14: (1, "right"), 15: (2, "in"), 16: (13, "punch", (0.75, 0.5)),
            17: (11, "out"),
        },
        "badges": {
            3: ("БЛИК ВИДЕН ЗА 2 КМ", RED), 5: ("KILLFLASH — ДОРОГО", WHITE), 7: ("ЧУЛОК 20–40 DEN", AMBER),
            10: ("СЕТКА В РАСФОКУСЕ", GREEN), 13: ("БЛЕНДА 7–10 СМ + САЖА", AMBER), 15: ("ЩЕЛЬ 3 ММ", AMBER),
            17: ("ЦЕНА: 0 ₽", GREEN),
        },
    },
    2: {
        "title": "ПЕНОФОЛ: БЛИНДАЖ-ТЕРМОС",
        "sub": "НЕВИДИМ ДЛЯ НОЧНОГО ДРОНА",
        "short": "БЛИНДАЖ-ТЕРМОС",
        "hero": 4, "accent": RED,
        "plan": {
            0: (16, "punch", (0.5, 0.5)), 1: (4, "in"), 2: (17, "left"), 3: (18, "punch", (0.6, 0.25)),
            4: (3, "in"), 5: (3, "punch", (0.3, 0.3)), 6: (3, "right"), 7: [(15, "in"), (16, "punch", (0.5, 0.5))],
            8: (15, "punch", (0.6, 0.45)), 9: (4, "out"), 10: (4, "punch", (0.6, 0.25)), 11: (17, "shake"),
            12: (17, "in"), 13: (17, "punch", (0.5, 0.3)), 14: (4, "left"), 15: (4, "right"), 16: (18, "out"),
            17: (17, "right"), 18: (18, "in"),
        },
        "badges": {
            0: ("ГЛАВНЫЙ ВРАГ — ТЕПЛОВИЗОР", RED), 5: ("ОШИБКА: ПЕНОФОЛ СНАРУЖИ", RED), 8: ("ПОЗИЦИЯ ВСКРЫТА", RED),
            10: ("ФОЛЬГОЙ ВНУТРЬ", GREEN), 12: ("ЗАЗОР 3–5 СМ", AMBER), 14: ("ОТРАЖАЕТ ДО 97% ТЕПЛА", GREEN),
            16: ("КРЫША ХОЛОДНАЯ", CYAN), 18: ("БЛИНДАЖ-ТЕРМОС", GREEN),
        },
    },
    3: {
        "title": "УДОЧКА ЗА 500 ₽",
        "sub": "4 ПРИМЕНЕНИЯ В ОКОПЕ",
        "short": "УДОЧКА ЗА 500 ₽",
        "hero": 20, "accent": GREEN,
        "plan": {
            0: (19, "in"), 1: (19, "punch", (0.4, 0.45)), 2: (5, "left"), 3: (20, "punch", (0.5, 0.3)),
            4: (20, "up"), 5: (5, "in"), 6: (20, "out"), 7: (21, "punch", (0.55, 0.45)), 8: (21, "left"),
            9: (21, "punch", (0.85, 0.65)), 10: [(6, "in"), (21, "right")], 11: (6, "punch", (0.6, 0.45)),
            12: (5, "punch", (0.5, 0.4)), 13: (5, "right"), 14: (22, "punch", (0.45, 0.5)), 15: (22, "left"),
            16: (19, "in"), 17: (20, "out"),
        },
        "badges": {
            0: ("6 МЕТРОВ · 500 ₽", AMBER), 3: ("№1 — МАЧТА СВЯЗИ", GREEN), 6: ("+10–15 КМ ДАЛЬНОСТИ", GREEN),
            7: ("№2 — САПЁРНЫЙ ЩУП", GREEN), 8: ("ДИЭЛЕКТРИК", CYAN), 12: ("№3 — ЛОЖНАЯ ЦЕЛЬ", GREEN),
            14: ("№4 — ПОЛЕВАЯ СВЯЗЬ", GREEN), 16: ("500 ₽ = 4 ЗАДАЧИ", AMBER),
        },
    },
    4: {
        "title": "АВТОЗЕРКАЛО НА ПАЛКЕ",
        "sub": "ЗАГЛЯНУТЬ ЗА УГОЛ — И НЕ ПОЙМАТЬ ПУЛЮ",
        "short": "ЗЕРКАЛО ЗА УГОЛ",
        "hero": 23, "accent": CYAN,
        "plan": {
            0: (23, "in"), 1: (23, "left"), 2: (7, "punch", (0.5, 0.4)), 3: (7, "shake"),
            4: (24, "punch", (0.45, 0.45)), 5: (24, "in"), 6: (23, "right"),
            7: [(24, "out"), (24, "punch", (0.45, 0.45))], 8: (7, "in"), 9: (26, "up"), 10: (25, "punch", (0.6, 0.4)),
            11: (8, "in"), 12: (25, "left"), 13: (8, "punch", (0.5, 0.4)), 14: (25, "punch", (0.55, 0.45)),
            15: (8, "right"), 16: (23, "punch", (0.75, 0.25)), 17: (24, "out"),
        },
        "badges": {
            2: ("СМЕРТЕЛЬНЫЙ УГОЛ", RED), 5: ("ВЫПУКЛОЕ ЗЕРКАЛО", CYAN), 7: ("ОБЗОР ×2,5", GREEN),
            8: ("ИЗОЛЕНТА · УГОЛ 45°", AMBER), 10: ("USB-ЭНДОСКОП · 600 ₽", CYAN), 14: ("LED — ЗАКЛЕИТЬ!", RED),
            15: ("ТЕЛЕФОН В АВИАРЕЖИМ", RED),
        },
    },
    5: {
        "title": "МИКРОВОЛНОВКА И РАБИЦА",
        "sub": "«МАНГАЛ» ПРОТИВ FPV-ДРОНА",
        "short": "«МАНГАЛ» ПРОТИВ FPV",
        "hero": 28, "accent": RED,
        "plan": {
            0: (27, "punch", (0.3, 0.45)), 1: (27, "right"), 2: (9, "in"), 3: (9, "left"),
            4: (28, "punch", (0.45, 0.5)), 5: (28, "in"), 6: (28, "punch", (0.3, 0.75)), 7: (9, "punch", (0.55, 0.4)),
            8: (29, "out"), 9: (29, "punch", (0.3, 0.75)), 10: [(10, "in"), (29, "right")],
            11: [(2, "punch"), (4, "punch"), (20, "punch"), (24, "punch"), (29, "punch")],
            12: (30, "in"), 13: (10, "punch", (0.5, 0.4)), 14: (30, "out"), 15: (5, "in"), 16: (30, "right"),
        },
        "badges": {
            0: ("FPV · 100 КМ/Ч", RED), 1: ("МЯГКАЯ СЕТЬ ПРОВИСАЕТ", RED), 3: ("2 СЛОЯ · ЗАЗОР 30–40 СМ", GREEN),
            6: ("ПГ-7В: ПОДРЫВ ДО УДАРА", AMBER), 7: ("СТРУЯ В 50 СМ ОТ КРЫШИ", GREEN),
            9: ("МИКРОВОЛНОВКИ · ПАНЦИРНЫЕ СЕТКИ", AMBER), 10: ("«МАНГАЛ»", GREEN),
            14: ("СПЕЦВЫПУСК · " + BRAND, AMBER), 15: ("TG: @vokope_ru · VK: vokope_rus", CYAN),
        },
    },
}

# ---------------------------------------------------------------- subtitles
REPL = [
    ("Шестиметровая", "6-метровая"), ("три секунды", "3 секунды"), ("пятьсот рублей", "500 ₽"),
    ("Пятьсот рублей", "500 ₽"), ("Пять хитростей", "5 хитростей"), ("два километра", "2 км"),
    ("«Киллфлэш»", "KillFlash"), ("двадцать — сорок ден", "20–40 DEN"),
    ("семь — десять сантиметров", "7–10 см"), ("три миллиметра", "3 мм"), ("ноль рублей", "0 ₽"),
    ("три — пять сантиметров", "3–5 см"), ("девяноста семи процентов", "97%"), ("две минуты", "2 минуты"),
    ("плюс шесть метров", "+6 м"), ("плюс десять — пятнадцать километров", "+10–15 км"),
    ("шести метров", "6 м"), ("два с половиной раза", "2,5 раза"), ("сорок пять градусов", "45°"),
    ("шестьсот рублей", "600 ₽"), ("сто километров в час", "100 км/ч"),
    ("тридцать — сорок сантиметров", "30–40 см"), ("Применение первое", "Применение №1"),
    ("Применение второе", "Применение №2"), ("Применение третье", "Применение №3"),
    ("Применение четвёртое", "Применение №4"), ("в полуметре", "в 50 см"), ("Два важных правила", "2 важных правила"),
    ("в один слой", "в 1 слой"), ("в два слоя", "в 2 слоя"),
]


def display_text(s):
    for a, b in REPL:
        s = s.replace(a, b)
    return s


HOT = ["снайпер", "тепловизор", "чулок", "пенофол", "удочк", "зеркал", "микроволнов", "рабиц", "бленд",
       "ошибка", "пулю", "пуля", "вскрыта", "смертельн", "термос", "мачта", "щуп", "ложная", "эндоскоп",
       "авиарежим", "мангал", "зазор", "дрон", "блик", "маяк", "броню", "граната", "гранат", "фольг", "сетк",
       "смекалка", "капрон", "конденсат", "растяжк", "выпукл", "fpv", "killflash", "сажа", "черноты", "ПГ-7В",
       "окопе", "спецвыпуск", "телеграм", "вконтакте"]
RED_HOT = ["ошибка", "пулю", "пуля", "вскрыта", "смертельн", "снайпер", "лотерея"]


def word_color(w):
    lw = w.lower()
    if any(ch.isdigit() for ch in w) or "₽" in w or "%" in w:
        return "num"
    if any(h in lw for h in RED_HOT):
        return "red"
    if any(h.lower() in lw for h in HOT):
        return "hot"
    return "w"


def chunk_words(text, max_words=5, max_chars=30):
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
DEFAULT_MOVES = ["in", "left", "out", "right"]


def norm_item(it, k):
    if isinstance(it, int):
        return {"img": it, "move": DEFAULT_MOVES[k % 4], "focus": [0.5, 0.45]}
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
            sents = seg["sentences"]
            vt = seg["voice_t0"]
            seg_shots = []
            last = None
            for i, s in enumerate(sents):
                a = seg["t0"] if i == 0 else vt + s["t0"]
                b = seg["t1"] if i == len(sents) - 1 else vt + s["t1"]
                item = data["plan"].get(i)
                if item is None:
                    if last is None:
                        item = data.get("hero", 1)
                    else:
                        seg_shots[-1]["t1"] = b
                        continue
                items = item if isinstance(item, list) else [item]
                items = [norm_item(x, k + j) for j, x in enumerate(items)]
                if len(items) == 1 and b - a > 7.0:
                    second = dict(items[0])
                    second["move"] = "punch" if items[0]["move"] != "punch" else "out"
                    items.append(second)
                n = len(items)
                for j, it in enumerate(items):
                    t0 = a + (b - a) * j / n
                    t1 = a + (b - a) * (j + 1) / n
                    sh = {"kind": "img", "t0": round(t0, 3), "t1": round(t1, 3), **it}
                    sh["flash"] = it["move"] == "punch"
                    sh["sfx"] = "hit" if it["move"] == "punch" else "whoosh"
                    sh["sfx_gain"] = 0.32 if it["move"] == "punch" else 0.17
                    seg_shots.append(sh)
                    k += 1
                last = items[-1]
            seg_shots[0]["sfx"] = None
            shots.extend(seg_shots)
            bk = sorted(data["badges"].keys())
            for idx, si in enumerate(bk):
                if si >= len(sents):
                    continue
                s = sents[si]
                t0 = vt + s["t0"] + 0.15
                # badge lives for its sentence (+0.4 s), max 3.8 s
                t1 = min(vt + s["t1"] + 0.4, t0 + 3.8, seg["t1"] - 0.05)
                if idx + 1 < len(bk) and bk[idx + 1] < len(sents):
                    t1 = min(t1, vt + sents[bk[idx + 1]]["t0"] + 0.05)
                text, col = data["badges"][si]
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
