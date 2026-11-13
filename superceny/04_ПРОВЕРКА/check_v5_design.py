#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_v5_design.py — QA-аудитор ПЕЧАТНОГО ЯЗЫКА карусели v5 «СОРВАННЫЙ ЦЕННИК» (бриф §11).

Проверяет не только тексты, а именно идею/печатный язык:
  1) ПАЛИТРА PNG (все 81): бумага #F1E8D6 / тушь #17150F / красный #E23B2E;
     запрет тёмно-оливкового фона и лишних цветов (2 краски + бумага).
  2) ЗАПРЕТЫ anti-slop в CSS/HTML: box-shadow, glow, градиенты, тёмно-оливковые
     фоны, иконочные буллеты, пустые декоративные плашки, симметрия-дашборды.
  3) ОБЯЗАТЕЛЬНАЯ РЕМЕСЛЕННОСТЬ: бумажная текстура/зерно, полутон/duotone-фото
     (`img/print/*_duo*`), мисрегистрация/приводка, штамп, перфорация/купон,
     красная линия-нитка, стенсильные номера, рваные края.
  4) ИДЕЯ: слайды 01–03 — обрывок ценника/«СУПЕРЦЕНА», 04 — целый ценник
     «ПРАЙС ПО ЗАПРОСУ» + перфорация/отрывной купон + CTA/телефон.
  5) СТРУКТУРА: 81 PNG, 20 strips, gallery/чек-лист.

Выход: superceny\\04_ПРОВЕРКА\\QA_ЦЕННИК_V5_АВТОПРОВЕРКА.md/.json
Запуск: python check_v5_design.py [--selftest] [--no-write] [--stage all|html|png]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = "1.0"
QA = Path(__file__).resolve().parent
SC = QA.parent
HTML = SC / "03_HTML"
READY = SC / "05_ГОТОВОЕ"
DESIGN = SC / "02_ДИЗАЙН"
STRIPS = QA / "карусели"

_spec = importlib.util.spec_from_file_location("cs_v5", QA / "check_superceny.py")
if _spec is None or _spec.loader is None:
    raise SystemExit("не найден check_superceny.py рядом")
cs = importlib.util.module_from_spec(_spec)
sys.modules["cs_v5"] = cs
_spec.loader.exec_module(cs)

_spec2 = importlib.util.spec_from_file_location("cc_v5", QA / "check_carousel.py")

cc = importlib.util.module_from_spec(_spec2)
sys.modules["cc_v5"] = cc
_spec2.loader.exec_module(cc)

EXPECTED_POS = 20


def load_price_map() -> dict:
    f = QA / "_tmp" / "prices_expected.json"
    if not f.is_file():
        return {}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}
    m = {}
    for folder, w in (d.get("positions") or {}).items():
        m[folder[:2]] = w.get("retail")
    for folder in (d.get("unpriced") or {}):
        m[folder[:2]] = None
    return m
PAPER = (0xF1, 0xE8, 0xD6)
INK = (0x17, 0x15, 0x0F)
RED = (0xE2, 0x3B, 0x2E)

# --- запреты anti-slop (ищем в CSS + HTML) ---
BANNED_CSS = [
    ("box-shadow", re.compile(r"box-shadow\s*:", re.I), "плашки/тени-боксы"),
    ("text-shadow", re.compile(r"text-shadow\s*:", re.I), "glow/тень текста"),
    ("drop-shadow", re.compile(r"drop-shadow", re.I), "glow вокруг фото"),
    ("gradient", re.compile(r"(?:linear|radial|conic)-gradient", re.I), "градиенты"),
    ("backdrop-filter", re.compile(r"backdrop-filter", re.I), "glassmorphism"),
    ("filter-blur", re.compile(r"filter\s*:[^;]*blur", re.I), "размытие/glow"),
    ("icon-mask", re.compile(r"mask-image|-webkit-mask", re.I), "иконочные буллеты"),
    ("list-image", re.compile(r"list-style-image", re.I), "иконки-буллеты"),
    ("dark-olive", re.compile(r"#(?:2[0-9a-f]|3[0-3])[0-9a-f](?:2[0-9a-f]|3[0-3])[0-9a-f](?:1[0-9a-f]|2[0-3])[0-9a-f]\b", re.I), "тёмно-оливковый фон"),
    ("emoji-icon", re.compile(r"[☀-➿🚀-🛿✅❌⭐️📦🔥💥]", re.U), "эмодзи-иконки"),
]
# --- обязательный печатный язык (ищем в CSS/HTML/ассетах) ---
REQUIRED_MARKS = [
    ("paper", re.compile(r"#f1e8d6|--paper", re.I), "бумага #F1E8D6"),
    ("ink", re.compile(r"#17150f|--ink", re.I), "тушь #17150F"),
    ("red", re.compile(r"#e23b2e|--red|--signal", re.I), "красный #E23B2E"),
    ("grain", re.compile(r"grain|noise|txtr|texture", re.I), "бумажная текстура/зерно"),
    ("halftone", re.compile(r"halftone|полутон|duo", re.I), "полутон/duotone"),
    ("stamp", re.compile(r"stamp|штамп", re.I), "штамп"),
    ("perfor", re.compile(r"perfor|перфорац|coupon|купон|tear|отрыв", re.I), "перфорация/купон"),
    ("misreg", re.compile(r"misreg|непривод|приводк|offset-ink|red-shift", re.I), "мисрегистрация/приводка"),
    ("thread", re.compile(r"thread|нитк|red-line|line--red|redline", re.I), "красная нитка-линия"),
    ("stencil", re.compile(r"stencil|стенсил|ghost|num", re.I), "стенсильные номера"),
]

COLOR_TOL = 46  # евклидово расстояние в RGB для бумаги


def classify_pixels(path: Path) -> dict:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((270, 338), Image.LANCZOS)
    px = list(im.getdata())
    n = len(px)
    cnt = {"paper": 0, "ink": 0, "red": 0, "olive": 0, "other": 0}
    for r, g, b in px:
        mx, mn = max(r, g, b), min(r, g, b)
        v = mx / 255.0
        s = 0 if mx == 0 else (mx - mn) / mx
        # евклидово до бумаги/красного
        d_paper = ((r - PAPER[0]) ** 2 + (g - PAPER[1]) ** 2 + (b - PAPER[2]) ** 2) ** 0.5
        d_red = ((r - RED[0]) ** 2 + (g - RED[1]) ** 2 + (b - RED[2]) ** 2) ** 0.5
        if d_paper < COLOR_TOL or (v > 0.78 and s < 0.25 and 25 <= _hue(r, g, b) <= 70):
            cnt["paper"] += 1
        elif v < 0.20:
            cnt["ink"] += 1
        elif d_red < 70 or (s > 0.45 and (340 <= _hue(r, g, b) or _hue(r, g, b) <= 15) and v > 0.35):
            cnt["red"] += 1
            if d_red < 70:
                cnt["red"] += 0
        elif 60 <= _hue(r, g, b) <= 110 and s > 0.12 and v < 0.45:
            cnt["olive"] += 1
        elif s > 0.28 and not (_hue(r, g, b) <= 70 or _hue(r, g, b) >= 330):
            cnt["other"] += 1
    return {k: round(x / n, 4) for k, x in cnt.items()}


def _hue(r: int, g: int, b: int) -> int:
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0
    d = mx - mn
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return int(h * 60) % 360


def check_html(positions_raw: list[dict]) -> tuple[list, dict]:
    findings: list = []
    # css-файлы дизайна
    css_files = sorted(DESIGN.glob("*.css"))
    css_text = ""
    for f in css_files:
        try:
            css_text += cs.read_text(f)
        except Exception:
            pass
    css_scan = {}
    for name, rx, _dt in BANNED_CSS:
        if name == "text-shadow":
            # мисрегистрация = жёсткий красный/чернильный офсет с blur 0 — это ремесло, не glow
            bad = 0
            for mm in re.finditer(r"text-shadow\s*:\s*([^;}]+)", css_text, re.I):
                val = mm.group(1)
                v2 = re.sub(r"(?:rgba?|hsla?)\([^)]*\)|#[0-9a-f]{3,8}|\b(?:red|black|white|none)\b", " ", val, flags=re.I)
                nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", v2)]
                hard = len(nums) == 2 or (len(nums) >= 3 and nums[2] == 0)
                red = re.search(r"226\s*,\s*59\s*,\s*46|23\s*,\s*21\s*,\s*15|#e23b2e|#17150f|var\(--red\)|var\(--ink\)", val, re.I)
                if not (hard and red):
                    bad += 1
            css_scan[name] = bad
        else:
            css_scan[name] = len(rx.findall(css_text))
    for name, hits in css_scan.items():
        if hits:
            dt = next(d for n, _r, d in BANNED_CSS if n == name)
            findings.append(cs.Finding("Б2", "css", f"запрещённый приём «{dt}»: {hits} вхождений в CSS", str(css_files[0] if css_files else DESIGN)))
    # обязательные марки
    required_found = {}
    for name, rx, dt in REQUIRED_MARKS:
        required_found[name] = bool(rx.search(css_text))
        if not required_found[name]:
            # ищем и в html (инлайновые стили/классы)
            required_found[name] = False
    # html: 81 слайд
    cards, hero, struct_f = cs.html_tree()
    findings.extend(struct_f)
    html_text_all = ""
    for order, slides in cards.items():
        for idx, p in slides.items():
            html_text_all += "\n" + cs.read_text(p)
    html_text_all += "\n" + "\n".join(cs.read_text(p) for p in hero.values())
    for name, rx, dt in REQUIRED_MARKS:
        if not required_found.get(name) and rx.search(html_text_all):
            required_found[name] = True
        if not required_found.get(name):
            # мисрегистрация часто реализована жёсткими офсетами text-shadow, а не словом
            if name == "misreg":
                hard_shadows = 0
                for mm in re.finditer(r"text-shadow\s*:\s*([^;}]+)", css_text, re.I):
                    val = mm.group(1)
                    v2 = re.sub(r"(?:rgba?|hsla?)\([^)]*\)|#[0-9a-f]{3,8}|\b(?:red|black|white|none)\b", " ", val, flags=re.I)
                    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", v2)]
                    hard = len(nums) == 2 or (len(nums) >= 3 and nums[2] == 0)
                    col = re.search(r"226\s*,\s*59\s*,\s*46|23\s*,\s*21\s*,\s*15|#e23b2e|#17150f|var\(--red\)|var\(--ink\)", val, re.I)
                    if hard and col:
                        hard_shadows += 1
                if hard_shadows:
                    required_found[name] = True
            if not required_found.get(name):
                findings.append(cs.Finding("З", "css", f"не найден обязательный элемент печатного языка: {dt}", str(DESIGN)))
    # дуотон-ассеты
    duo_dir = DESIGN / "img" / "print"
    duo = sorted(duo_dir.glob("*_duo*.png")) if duo_dir.is_dir() else []
    if len(duo) < 18:
        findings.append(cs.Finding("Б2", "assets", f"duotone-ассетов {len(duo)}/18 в {duo_dir}", str(duo_dir)))
    refs = len(re.findall(r"img/print/|_duo", html_text_all))
    if refs < 20:
        findings.append(cs.Finding("Б2", "assets", f"в HTML нет ссылок на полутоновые ассеты (найдено {refs}) — фото могут быть нетронутыми", str(HTML)))
    required_found["duo_refs"] = refs
    # текстовые/смысловые маркеры
    for order, slides in cards.items():
        name = cs.EXPECTED_BY_ORDER.get(order, {}).get("name", str(order))
        sid = f"{order:02d} {name}"
        txt = {}
        for idx in ("01", "02", "03", "04"):
            p = slides.get(idx)
            if p:
                txt[idx] = cs.read_text(p)
        blob = " ".join(txt.values())
        # идея: ценник/штамп на 01–03, целый ценник+перфорация на 04
        for idx in ("01", "02", "03"):
            if idx in txt and not re.search(r"ценик|ценник|price[-_ ]?tag|СУПЕРЦЕН", txt[idx], re.I):
                findings.append(cs.Finding("З", f"{order:02d} {idx}", "нет обрывка ценника/«СУПЕРЦЕНА» (идея серии)", str(slides[idx])))
        t4 = txt.get("04", "")
        if t4:
            pmap = load_price_map()
            known = f"{order:02d}" in pmap
            exp = pmap.get(f"{order:02d}")
            if known and exp is not None:
                if str(exp) not in re.sub(r"[^\d]", "", t4):
                    findings.append(cs.Finding("Б1", f"{order:02d} 04", f"на финале нет цены {exp} ₽", str(slides.get("04"))))
            elif not re.search(r"прайс\s+по\s+запросу", t4, re.I):
                findings.append(cs.Finding("Б4", f"{order:02d} 04", "на финале нет «ПРАЙС ПО ЗАПРОСУ»", str(slides.get("04"))))
            if not re.search(r"перфорац|отрыв|купон|coupon|tear", t4, re.I):
                findings.append(cs.Finding("З", f"{order:02d} 04", "на финале нет перфорации/отрывного купона (идея)", str(slides.get("04"))))
            if not cs.TG_RE.search(t4) or not cs.PHONE_RE.search(t4):
                findings.append(cs.Finding("Б4", f"{order:02d} 04", "на финале нет CTA/@vokope_ru/телефона", str(slides.get("04"))))
        # запрет плашек-боксов: text-bearing элементы с background-color — ищем классы-«card/box/plate»
        for mm in re.finditer(r'class="([^"]*)"', blob):
            cl = mm.group(1).lower()
            if re.search(r"\b(?:card|box|plate|panel|pane|tile)\b", cl) and "stat" not in cl:
                findings.append(cs.Finding("З", f"{order:02d}", f"класс-намёк на плашку-бокс: «{cl[:60]}»", str(p)))
                break
    return findings, {"duo_assets": len(duo), "duo_refs": refs, "css_banned": {k: v for k, v in css_scan.items() if v}}


PRIMARY = {"t-big", "t-giant", "cover-claim", "cover-sub", "sub", "w", "n", "stencil",
           "lead-sub", "tail", "tag__v", "contact", "cta", "kick", "price", "big", "mid"}
THRESH = {"01": ("cover-claim", 26), "02": ("num", 60), "03": ("w", 24), "04": ("tag__v", 28)}


def check_typography() -> tuple[list, dict]:
    """Печатная типографика: ключевые классы и их кегли по 81 финальному HTML."""
    findings: list = []
    try:
        spec = importlib.util.spec_from_file_location("cl_v5", QA / "check_superceny_layout.py")
        cl = importlib.util.module_from_spec(spec)
        sys.modules["cl_v5"] = cl
        spec.loader.exec_module(cl)
    except Exception as exc:
        return [cs.Finding("И", "typo", f"замер кеглей недоступен: {exc}", str(QA))], {}
    tmp = QA / "_tmp" / "layout_v5"
    tmp.mkdir(parents=True, exist_ok=True)
    cards, hero, _f = cs.html_tree()
    stats = {"slides": 0, "min_primary": None, "per_slide": {}}
    for order in sorted(cards):
        name = cs.EXPECTED_BY_ORDER.get(order, {}).get("name", str(order))
        for idx, path in sorted(cards[order].items()):
            try:
                payload = cl.measure(path, (1080, 1350), tmp)
            except Exception as exc:
                findings.append(cs.Finding("И", f"{order:02d} {idx}", f"не замерился: {exc}", str(path)))
                continue
            items = payload.get("items") or []
            prim = [it for it in items if set((it.get("cls") or "").split()) & PRIMARY]
            fs = [it["fs"] for it in prim] or [0]
            mn = min(fs)
            stats["slides"] += 1
            if stats["min_primary"] is None or mn < stats["min_primary"]:
                stats["min_primary"] = mn
            stats["per_slide"][f"{order:02d} {idx}"] = {"min": mn, "max": max(fs), "n": len(prim), "outside": len(payload.get("outside") or []), "overlaps": len(payload.get("overlaps") or [])}
            if mn < 16:
                findings.append(cs.Finding("З", f"{order:02d} {idx}", f"основная типографика {mn:.0f}px (<16) — мелко для печатного языка", str(path)))
            ok_cls, need = THRESH.get(idx, (None, 0))
            if ok_cls:
                got = [it["fs"] for it in prim if ok_cls in (it.get("cls") or "").split()]
                if not got:
                    findings.append(cs.Finding("З", f"{order:02d} {idx}", f"нет ключевого класса {ok_cls} (смысловой акцент слайда)", str(path)))
                elif max(got) < need:
                    findings.append(cs.Finding("З", f"{order:02d} {idx}", f"{ok_cls} {max(got):.0f}px < {need}px", str(path)))
    # hero
    for key, path in hero.items():
        try:
            payload = cl.measure(path, (1080, 1350), tmp)
            items = payload.get("items") or []
            prim = [it for it in items if set((it.get("cls") or "").split()) & PRIMARY]
            stats["per_slide"]["hero"] = {"min": min([it["fs"] for it in prim] or [0]), "n": len(prim)}
        except Exception:
            pass
    vals = [v["min"] for k, v in stats["per_slide"].items() if k != "hero" and v.get("min")]
    if vals:
        stats["min_primary"] = min(vals)
        stats["median_primary"] = sorted(vals)[len(vals) // 2]
    return findings, stats


def check_png(positions_raw: list[dict]) -> tuple[list, dict]:
    findings: list = []
    stats: dict = {}
    pngs = sorted(READY.rglob("*.png"))
    stats["png"] = len(pngs)
    worst = []
    for f in pngs:
        try:
            c = classify_pixels(f)
        except Exception as exc:
            findings.append(cs.Finding("Б3", "png", f"{f.name}: не читается ({exc})", str(f)))
            continue
        worst.append((f, c))
        if c["olive"] > 0.03:
            findings.append(cs.Finding("Б2", f.name, f"тёмно-оливковые пиксели {c['olive']:.1%} (>4%) — запрет", str(f)))
        if c["other"] > 0.09:
            findings.append(cs.Finding("З", f.name, f"посторонние цвета {c['other']:.1%} (>9%) — нарушение 2-красочности", str(f)))
        if c["paper"] + c["ink"] + c["red"] < 0.70:
            findings.append(cs.Finding("З", f.name, f"покрытие бумага+тушь+красный {c['paper'] + c['ink'] + c['red']:.0%} (<70%)", str(f)))
    if worst:
        avg = {k: round(sum(c[k] for _f, c in worst) / len(worst), 4) for k in ("paper", "ink", "red", "olive", "other")}
        stats["palette_avg"] = avg
        stats["olive_max"] = max(c["olive"] for _f, c in worst)
        stats["other_max"] = max(c["other"] for _f, c in worst)
        stats["calm_min"] = min(c["paper"] + c["ink"] + c["red"] for _f, c in worst)
    strips = sorted(STRIPS.glob("*.png")) + sorted(STRIPS.glob("*.jpg")) if STRIPS.is_dir() else []
    stats["strips"] = len(strips)
    if len(strips) < EXPECTED_POS:
        findings.append(cs.Finding("Б3", "strips", f"контакт-листов {len(strips)}/20", str(STRIPS)))
    return findings, stats


def build_report(generated: str, findings: list, stats: dict, cc_stats: dict) -> str:
    B = [f for f in findings if f.code.startswith("Б")]
    Z = [f for f in findings if f.code == "З"]
    I = [f for f in findings if f.code == "И"]
    L = ["# QA ЦЕННИК v5 — автопроверка печатного языка", "",
         f"**Сгенерировано:** {generated} · аудитор v{VERSION} · 20 позиций × 4 + hero = 81 PNG", "",
         f"**Блокеры:** {len(B)} · **Замечания:** {len(Z)} · **Инфо:** {len(I)}", ""]
    L += ["## 1. Палитра (2 краски + бумага)", ""]
    avg = stats.get("palette_avg") or {}
    L += [f"- среднее по 81 PNG: бумага **{avg.get('paper', 0):.0%}**, тушь **{avg.get('ink', 0):.0%}**, "
          f"красный **{avg.get('red', 0):.0%}**, оливковый **{avg.get('olive', 0):.1%}** (max {stats.get('olive_max', 0):.1%}), "
          f"посторонние **{avg.get('other', 0):.1%}** (max {stats.get('other_max', 0):.1%})",
          f"- минимум покрытия бумага+тушь+красный: **{stats.get('calm_min', 0):.0%}** (порог 70%)",
          f"- duotone-ассеты: **{stats.get('duo_assets', 0)}/18**, ссылок в HTML: {stats.get('duo_refs', 0)}", ""]
    L += ["## 2. Печатная типографика (ключевые классы)", "",
          f"- замерено слайдов: **{stats.get('slides', 0)}/80** (+hero), min основной типографики: **{stats.get('min_primary') or 0}px**, медиана: {stats.get('median_primary') or 0}px", ""]
    L += ["## 3. CSS/HTML: запреты и ремесло", ""]
    bad = stats.get("css_banned") or {}
    L.append("- запрещённые приёмы: " + ("**нет**" if not bad else ", ".join(f"{k}×{v}" for k, v in bad.items())))
    L += ["", "## 4. Блокеры", ""]
    if B:
        for f in B:
            L.append(f"- **[{f.code}] {f.subject}** — {f.msg}" + (f"  \n  `{f.path}`" if f.path else ""))
    else:
        L.append("Нет.")
    L += ["", "## 5. Замечания", ""]
    if Z:
        for f in Z[:60]:
            L.append(f"- [{f.code}] {f.subject} — {f.msg}" + (f" · `{f.path}`" if f.path else ""))
        if len(Z) > 60:
            L.append(f"- … ещё {len(Z) - 60} (см. json)")
    else:
        L.append("Нет.")
    L += ["", "## 6. Инфо", ""]
    for f in I:
        L.append(f"- [{f.code}] {f.subject} — {f.msg}")
    L += ["", "## 7. Тексты/каталог (из check_carousel)", "",
          f"- data/html/png: {cc_stats}", "",
          "_Визуальный аудит идеи (ценник летит/рвётся, финал с целым ценником+перфорацией, полутон,"
          " отсутствие плашек/иконок/симметрии/glow, узнаваемость фото) — заполняется вручную в QA_ОТЧЁТ_КАРУСЕЛЬ_V5.md._"]
    return "\n".join(L) + "\n"


def run(stage: str = "all", write: bool = True) -> dict:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    positions, err = cs.load_positions()
    findings: list = []
    stats: dict = {}
    cc_stats: dict = {}
    if positions is None:
        positions = []
        findings.append(cs.Finding("И", "positions", (err or "нет positions.json") + " — прогон неполный", str(SC / "01_ДАННЫЕ")))
    if stage in ("all", "html"):
        hf, hs = check_html(positions)
        findings.extend(hf)
        stats.update(hs)
    if stage in ("all", "typo"):
        tf, ts = check_typography()
        findings.extend(tf)
        stats.update(ts)
    if stage in ("all", "png"):
        pf, ps = check_png(positions)
        findings.extend(pf)
        stats.update(ps)
    seen, uniq = set(), []
    for f in findings:
        key = (f.code, f.subject, f.msg)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    findings = uniq
    B = sum(1 for f in findings if f.code.startswith("Б"))
    Z = sum(1 for f in findings if f.code == "З")
    I = sum(1 for f in findings if f.code == "И")
    result = {"generated": generated, "version": VERSION, "stage": stage, "stats": stats, "carousel": cc_stats,
              "summary": {"blockers": B, "warnings": Z, "infos": I},
              "findings": [cs.as_dict(f) for f in findings]}
    md = build_report(generated, findings, stats, cc_stats)
    if write:
        (QA / "QA_ЦЕННИК_V5_АВТОПРОВЕРКА.md").write_text(md, encoding="utf-8")
        (QA / "QA_ЦЕННИК_V5_АВТОПРОВЕРКА.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_md"] = md
    return result


def selftest() -> int:
    print("== SELFTEST check_v5_design.py ==")
    ok = True
    # палитра: бумага/чёрный/красный
    from PIL import Image
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="qa_v5_"))
    try:
        img = Image.new("RGB", (120, 160), PAPER)
        px = img.load()
        for y in range(0, 140, 20):
            for x in range(0, 100, 20):
                for dy in range(10):
                    for dx in range(10):
                        px[x + dx, y + dy] = RED if y % 40 == 0 else INK
        p = tmp / "test.png"
        img.save(p)
        c = classify_pixels(p)
        checks = [
            ("палитра: бумага>30%", c["paper"] > 0.3),
            ("палитра: красный>10%", c["red"] > 0.10),
            ("палитра: оливковый 0", c["olive"] < 0.01),
            ("палитра: посторонние 0", c["other"] < 0.01),
        ]
        # оливковый фон
        olive = Image.new("RGB", (120, 160), (58, 62, 44))
        po = tmp / "olive.png"
        olive.save(po)
        co = classify_pixels(po)
        checks.append(("детектор оливы", co["olive"] > 0.5))
        for name, cond in checks:
            print(("  PASS " if cond else "  FAIL ") + name)
            ok = ok and cond
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print("== SELFTEST:", "OK" if ok else "FAILED", "==")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA-аудитор печатного языка v5 «СОРВАННЫЙ ЦЕННИК»")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--stage", default="all", choices=["all", "html", "png"])
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    res = run(stage=args.stage, write=not args.no_write)
    s = res["summary"]
    print(f"check_v5_design v{VERSION}: {res['generated']}")
    print(f"  БЛОКЕРЫ: {s['blockers']} | замечаний: {s['warnings']} | инфо: {s['infos']}")
    print(f"  палитра avg: {res['stats'].get('palette_avg')}")
    for f in res["findings"]:
        if f["code"].startswith("Б"):
            print(f"   [{f['code']}] {f['subject']}: {f['msg']}")
    if not args.no_write:
        print(f"  отчёт: {QA / 'QA_ЦЕННИК_V5_АВТОПРОВЕРКА.md'}")
    return 1 if res["summary"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
