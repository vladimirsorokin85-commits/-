"""Storyboard for ep01: «Как армейская экипировка стала модой: полевая куртка M-65» (prologue + 4 chapters). Assets: assets_ep01_m65/dr_XX.jpg"""
import re

AMBER = (245, 158, 11)
RED = (239, 68, 68)
GREEN = (132, 204, 22)
CYAN = (34, 211, 238)
WHITE = (240, 240, 240)

BRAND = "МАГАЗИН «В ОКОПЕ»"
BRAND_LINKS = "t.me/vokope_ru  ·  vk.com/vokope_rus"
SERIES = "ЭКИПИРОВКА"
N_CHAPTERS = 4  # 4 chapters, prologue and outro are separate segments

# archival / sepia / B&W documents — not film-graded
NO_GRADE = {2, 3, 6, 7}

PROLOGUE = {
    "pool": [1, 4, (1, "punch", (0.45, 0.55)), 5, 9],
    "badges": [("сорока лет", "ДЕРЖАЛАСЬ БОЛЬШЕ 40 ЛЕТ", AMBER),
               ("дождя", "ДЛЯ ДОЖДЯ, ХОЛОДА И ГРЯЗИ", WHITE)],
}

CHAPTERS = {
    1: {"title": "ОТ М-51 К М-65", "sub": "АРМИЯ США · 1965", "short": "М-65",
        "hero": 2, "accent": AMBER,
        "pool": [2, (2, "punch", (0.5, 0.5)), 4, 5, (4, "punch", (0.5, 0.4)), 9, 2, (5, "punch", (0.3, 0.5))],
        "badges": [("1965 году", "1965 · ЗАМЕНА М-1951", AMBER),
                   ("Alpha", "ALPHA INDUSTRIES · NYCO", WHITE),
                   ("пятьдесят на пятьдесят", "50 НА 50 · НЕЙЛОН И ХЛОПОК", GREEN),
                   ("молнией", "КАПЮШОН В ВОРОТНИКЕ", RED),
                   ("липучками", "ЛИПУЧКИ ВМЕСТО ПУГОВИЦ", CYAN)]},
    2: {"title": "ВЬЕТНАМ И ДОЖДЬ", "sub": "МУССОНЫ · ФРОНТ", "short": "ВЬЕТНАМ",
        "hero": 3, "accent": RED,
        "pool": [3, (3, "punch", (0.5, 0.5)), 5, 6, (5, "punch", (0.5, 0.4)), 4, 3, (10, "punch", (0.3, 0.5))],
        "badges": [("муссонные", "МУССОННЫЕ ДОЖДИ", AMBER),
                   ("ста восьмидесяти", "180 000 АМЕРИКАНЦЕВ К КОНЦУ 1965", RED),
                   ("спрятанный", "КАПЮШОН НЕ ТЕРЯЕТСЯ", WHITE),
                   ("2009", "ВЫДАЧА ДО 2009 ГОДА", GREEN)]},
    3: {"title": "ОТ СТРОЯ К УЛИЦЕ", "sub": "ПРОТЕСТ · 1970-Е", "short": "УЛИЦА",
        "hero": 7, "accent": CYAN,
        "pool": [7, (7, "punch", (0.5, 0.5)), 8, 6, (8, "punch", (0.5, 0.5)), 7, 8, (9, "punch", (0.5, 0.5))],
        "badges": [("ветераны", "ВЕТЕРАНЫ ВЕРНУЛИСЬ ДОМОЙ", AMBER),
                   ("протеста", "КУРТКА КАК ЗНАК ПРОТЕСТА", RED),
                   ("семидесятых", "НАЧАЛО 1970-Х · ГРАЖДАНСКИЕ ВЕРСИИ", CYAN),
                   ("де ниро", "ДЕ НИРО · «ТАКСИСТ» 1976", WHITE)]},
    4: {"title": "ПОЧЕМУ ОНА ДЕРЖИТСЯ", "sub": "СХЕМА БЕЗ ЛИШНЕГО", "short": "СХЕМА",
        "hero": 9, "accent": GREEN,
        "pool": [9, (9, "punch", (0.5, 0.5)), 10, 1, (10, "punch", (0.4, 0.5)), 9, 4, (1, "punch", (0.5, 0.5))],
        "badges": [("сорока лет", "БОЛЬШЕ 40 ЛЕТ В СТРОЮ", AMBER),
                   ("прямой перед", "ПРЯМОЙ ПЕРЕД · ПРОСТАЯ СХЕМА", WHITE),
                   ("ветрозащитной", "ВЕТРОЗАЩИТНАЯ ПЛАНКА", RED),
                   ("сатин", "ПЛОТНЫЙ САТИН", GREEN),
                   ("первого взгляда", "УЗНАВАЕМА С ПЕРВОГО ВЗГЛЯДА", CYAN)]},
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
