"""Storyboard for спецвыпуск «Ноги довезут или похоронят».

Each chapter has a `pool` of scene ids (assets_nogi/nogi_XX.jpg). The shot builder walks the sentences and
cycles through the pool with varied camera moves (punch-zoom every 3rd shot, splits long sentences),
so a visual change happens every ~3-5 s. Badges are triggered by keywords in the sentence text.
"""
import re

AMBER = (245, 158, 11)
RED = (239, 68, 68)
GREEN = (132, 204, 22)
CYAN = (34, 211, 238)
WHITE = (240, 240, 240)

BRAND = "МАГАЗИН «В ОКОПЕ»"
BRAND_LINKS = "t.me/vokope_ru  ·  vk.com/vokope_rus"
SERIES = "ОКОПНАЯ СМЕКАЛКА"
N_CHAPTERS = 9  # 8 chapters + финал

# scene ids that are archive / painting / thermal / 3D — not film-graded
NO_GRADE = {2, 3, 7, 12, 18, 21, 22, 23, 25, 30, 33, 34, 35, 44}

PROLOGUE = {
    "pool": [2, 3, 2, (3, "punch", (0.45, 0.55)), 8, 4, 7, 1, 9, 6, (1, "punch", (0.7, 0.6))],
    "badges": [("тысяча девятьсот четырнадцатого", "ЗАПАДНЫЙ ФРОНТ · 1914", WHITE),
               ("втрое больше", "ПОТЕРИ ×3 — НЕ ОТ ПУЛЬ", RED),
               ("окопная стопа", "«ОКОПНАЯ СТОПА»", RED),
               ("восемь глав", "8 ГЛАВ", AMBER)],
}

CHAPTERS = {
    1: {"title": "ГЛАВНЫЙ ТРАНСПОРТ ПЕХОТЫ", "sub": "ПОЧЕМУ НОГИ СДАЮТ ПЕРВЫМИ", "short": "ТРАНСПОРТ",
        "hero": 6, "accent": AMBER,
        "pool": [5, (5, "punch", (0.75, 0.6)), 4, 15, 6, (4, "punch", (0.6, 0.7)), 7, (7, "punch", (0.5, 0.8)),
                 8, 10, 9, (9, "punch", (0.4, 0.5))],
        "badges": [("двухсот пятидесяти тысяч", "250 000 ПОТОВЫХ ЖЕЛЁЗ", AMBER),
                   ("пол-литра", "~0,5 Л ВЛАГИ В ДЕНЬ", CYAN),
                   ("сорока тысяч", "30 КМ = 40 000 ШАГОВ", AMBER),
                   ("сужаются", "СОСУДЫ СУЖАЮТСЯ", RED),
                   ("боевой ресурс", "НОГИ = БОЕВОЙ РЕСУРС", GREEN)]},
    2: {"title": "МОЗОЛЬ — ЭТО НЕ ТРЕНИЕ", "sub": "ФИЗИКА КРОВАВОЙ РАНЫ", "short": "МОЗОЛЬ",
        "hero": 11, "accent": RED,
        "pool": [11, 12, (12, "punch", (0.45, 0.45)), 4, 12, 11, 15, (11, "punch", (0.6, 0.6)), 13, 14, 13,
                 (13, "punch", (0.45, 0.6))],
        "badges": [("разрыв внутри кожи", "ПУЗЫРЬ = РАЗРЫВ ВНУТРИ КОЖИ", RED),
                   ("слегка влажная", "ОПАСНЕЕ ВСЕГО — ВЛАЖНАЯ КОЖА", AMBER),
                   ("вдвое больше", "ХЛОПОК: ×2 МОЗОЛЕЙ, ×3 РАЗМЕР", RED),
                   ("Две минуты", "2 МИНУТЫ НА ПЛАСТЫРЬ", GREEN)]},
    3: {"title": "ХЛОПОК — ВРАГ, ШЕРСТЬ — ОРУЖИЕ", "sub": "ВОЙНА МАТЕРИАЛОВ", "short": "МАТЕРИАЛЫ",
        "hero": 14, "accent": GREEN,
        "pool": [14, (14, "punch", (0.4, 0.4)), 24, 15, 16, (16, "punch", (0.35, 0.8)), 15, 17, 16,
                 (17, "punch", (0.3, 0.3)), 9, 10],
        "badges": [("набухает", "ХЛОПОК НАБУХАЕТ НА ~45%", RED),
                   ("тридцать семь", "37 НОВОБРАНЦЕВ · 4 ДНЯ МАРША", WHITE),
                   ("суше в шерсти", "В ШЕРСТИ КОЖА СУШЕ", GREEN),
                   ("в три раза", "ШЕРСТЬ ВПИТАЛА ×2,9", GREEN),
                   ("два слоя", "ЛАЙНЕР + ШЕРСТЬ", AMBER),
                   ("правило трёх пар", "ПРАВИЛО ТРЁХ ПАР", AMBER)]},
    4: {"title": "ПОРТЯНКА", "sub": "ГЕНИАЛЬНАЯ НИЩЕТА", "short": "ПОРТЯНКА",
        "hero": 19, "accent": AMBER,
        "pool": [18, (18, "punch", (0.3, 0.6)), 19, (19, "punch", (0.6, 0.65)), 21, 20, 22, 20,
                 (20, "punch", (0.5, 0.4)), 19, 10, 20],
        "badges": [("Потёмкин", "ПОТЁМКИН — ЕКАТЕРИНЕ II", WHITE),
                   ("сухой участок", "ВСЕГДА ЕСТЬ СУХОЙ УЧАСТОК", GREEN),
                   ("сорок первого", "ЗИМА 1941", WHITE),
                   ("Поморцев", "КИРЗА · ПОМОРЦЕВ · 1904", AMBER),
                   ("две тысячи седьмом", "ОТМЕНЕНА В 2007", RED)]},
    5: {"title": "МЕМБРАНА", "sub": "НЕПРОМОКАЕМЫЙ ОБМАН", "short": "МЕМБРАНА",
        "hero": 24, "accent": CYAN,
        "pool": [23, (23, "punch", (0.5, 0.5)), 24, 23, 25, (25, "punch", (0.5, 0.6)), 24, 15, 26,
                 (26, "punch", (0.5, 0.7)), 27, (27, "punch", (0.5, 0.5))],
        "badges": [("полиэтиленовый пакет", "МОКРАЯ МЕМБРАНА = ПАКЕТ", RED),
                   ("Кореи", "КОРЕЯ · 1950-е", WHITE),
                   ("не значит сухо", "НЕПРОМОКАЕМО ≠ СУХО", RED),
                   ("резиновые сапоги", "ВОДА: САПОГИ + ПАКЕТ", AMBER),
                   ("вечерней ноге", "ОБУВЬ — ПО ВЕЧЕРНЕЙ НОГЕ", GREEN)]},
    6: {"title": "ОКОПНАЯ СТОПА", "sub": "12 ЧАСОВ — И ПОДОШВА СТАНОВИТСЯ ГУБКОЙ", "short": "ОКОПНАЯ СТОПА",
        "hero": 28, "accent": RED,
        "pool": [28, 8, (28, "punch", (0.5, 0.75)), 29, (29, "punch", (0.5, 0.5)), 30, (30, "punch", (0.5, 0.5)),
                 2, 31, 32, (31, "punch", (0.5, 0.6))],
        "badges": [("от нуля до плюс шестнадцати", "0…+16 °C · 10–14 ЧАСОВ", AMBER),
                   ("Онемение", "ОНЕМЕНИЕ — ГЛАВНАЯ ЛОВУШКА", RED),
                   ("Анцио", "АНЦИО · 1944", WHITE),
                   ("сто три", "1951 ПРОТИВ 103", RED),
                   ("часы, а не градусы", "СЧИТАЙ ЧАСЫ, А НЕ ГРАДУСЫ", GREEN)]},
    7: {"title": "ОБМОРОЖЕНИЕ", "sub": "НЕ РАСТИРАЙ СНЕГОМ!", "short": "ОБМОРОЖЕНИЕ",
        "hero": 33, "accent": CYAN,
        "pool": [33, (33, "punch", (0.5, 0.5)), 34, 35, (35, "punch", (0.5, 0.5)), 10, 36, (36, "punch", (0.5, 0.5)),
                 37, 8],
        "badges": [("Наполеон", "1812 · ОТСТУПЛЕНИЕ НАПОЛЕОНА", WHITE),
                   ("кристаллы льда", "КРИСТАЛЛЫ ЛЬДА В ТКАНЯХ", CYAN),
                   ("тридцать семь", "ВОДА 37–40 °C", GREEN),
                   ("Никакого массажа", "НЕ ТЕРЕТЬ · НЕ ГРЕТЬ У ОГНЯ", RED),
                   ("не отогревай", "ВПЕРЕДИ МОРОЗ — НЕ ОТОГРЕВАЙ", RED)]},
    8: {"title": "РИТУАЛ 15 МИНУТ", "sub": "ЧТО ДЕЛАЕТ БЫВАЛЫЙ НА ПРИВАЛЕ", "short": "ПРИВАЛ",
        "hero": 38, "accent": GREEN,
        "pool": [38, 39, (39, "punch", (0.5, 0.5)), 40, 11, 16, 13, 41, 42, (42, "punch", (0.5, 0.5)), 31],
        "badges": [("пятнадцати минут", "ПРИВАЛ > 15 МИН — ОБУВЬ ДОЛОЙ", GREEN),
                   ("песчинка", "1 ПЕСЧИНКА = КРОВЬ ЗА 10 КМ", RED),
                   ("горячие точки", "ИЩИ «ГОРЯЧИЕ ТОЧКИ»", AMBER),
                   ("Пластырь", "ПЛАСТЫРЬ ДО МОЗОЛИ", GREEN),
                   ("сушишь носки на себе", "НОСКИ СУШИ НА СЕБЕ", AMBER),
                   ("друг другу", "ПРОВЕРКА В ПАРАХ", GREEN)]},
    9: {"title": "БОЕВАЯ МАТЕМАТИКА", "sub": "ЦЕНА СБИТОГО ПАЛЬЦА", "short": "ФИНАЛ", "label": "ФИНАЛ",
        "hero": 43, "accent": RED,
        "pool": [6, 43, (43, "punch", (0.5, 0.5)), 44, (44, "punch", (0.5, 0.5)), 4, 16, 38, 31, 9, 45,
                 (45, "punch", (0.5, 0.6))],
        "badges": [("два с половиной", "5 КМ/Ч → 2,5 КМ/Ч", RED),
                   ("сорока шести тысяч", "~46 000 ХОЛОДОВЫХ ТРАВМ", RED),
                   ("система вооружения", "НОГИ — СИСТЕМА ВООРУЖЕНИЯ", GREEN)]},
}

# ---------------------------------------------------------------- subtitles
REPL = [
    ("тысяча девятьсот четырнадцатого", "1914-го"), ("двухсот пятидесяти тысяч", "250 000"),
    ("пол-литра", "0,5 л"), ("семьдесят сантиметров", "70 см"), ("Тридцать километров", "30 км"),
    ("тридцать километров", "30 км"), ("сорока тысяч", "40 000"), ("шестидесятые годы", "1960-е"),
    ("вдвое больше", "в 2 раза больше"), ("втрое крупнее", "в 3 раза крупнее"), ("Две минуты", "2 минуты"),
    ("тридцать семь новобранцев", "37 новобранцев"), ("четыре дня", "4 дня"), ("в три раза", "в 3 раза"),
    ("четыре — шесть часов", "4–6 часов"), ("тысяча девятьсот четвёртом", "1904-м"),
    ("сорок первого", "1941-го"), ("три километра", "3 км"), ("две тысячи седьмом", "2007-м"),
    ("от нуля до плюс шестнадцати", "от 0 до +16 °C"), ("десять — четырнадцать часов", "10–14 часов"),
    ("сорок четвёртого", "1944-го"), ("тысяча девятьсот пятьдесят один", "1951"), ("сто три", "103"),
    ("в десять раз", "в 10 раз"), ("Тысяча восемьсот двенадцатый", "1812-й"),
    ("тридцать семь — сорок градусов", "37–40 °C"), ("пятнадцати минут", "15 минут"),
    ("десять километров", "10 км"), ("пять километров в час", "5 км/ч"), ("два с половиной", "2,5"),
    ("Двенадцать часов", "12 часов"), ("шесть часов", "6 часов"), ("сорока шести тысяч", "46 000"),
    ("восемь глав", "8 глав"), ("Екатерине Второй", "Екатерине II"), ("Ещё в Первую мировую", "Ещё в Первую мировую"),
]


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
