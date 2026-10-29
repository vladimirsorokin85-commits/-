# -*- coding: utf-8 -*-
"""Релизные артефакты горизонтали: SRT, publish.txt, release/README.md, обложка 1280×720."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BASE = "/home/user/-/video_studio/aldan12"
sys.path.insert(0, BASE)
import shots  # noqa: E402

TL = os.path.join(BASE, "horizontal_timeline.json")


def ts(x):
    h = int(x // 3600)
    m = int((x % 3600) // 60)
    s = x % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def srt(lines, total, path):
    """SRT: длинные реплики делим на два субтитра, чтобы строки были короткими."""
    import re

    def split2(t):
        if len(t) <= 92:
            return [t]
        best = None
        for m in re.finditer(r"(?<=[.!?])\s+|(?<=—)\s+|(?<=,)\s+", t):
            i = m.end()
            if i < len(t) * 0.25 or i > len(t) * 0.8:
                continue
            score = abs(i - len(t) / 2)
            if best is None or score < best[0]:
                best = (score, i)
        if best is None:
            return [t]
        return [t[:best[1]].strip(), t[best[1]:].strip()]

    out, n = [], 0
    for i, it in enumerate(lines):
        a = it["start"]
        b = lines[i + 1]["start"] if i + 1 < len(lines) else total
        parts = split2(it.get("text") or "")
        if len(parts) == 1:
            n += 1
            out.append(f"{n}\n{ts(a)} --> {ts(b)}\n{parts[0]}\n")
        else:
            w = [len(p) for p in parts]
            mid = a + (b - a) * w[0] / sum(w)
            n += 1
            out.append(f"{n}\n{ts(a)} --> {ts(mid)}\n{parts[0]}\n")
            n += 1
            out.append(f"{n}\n{ts(mid)} --> {ts(b)}\n{parts[1]}\n")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return path


def fmt(x):
    m = int(x // 60)
    sec = int(round(x % 60))
    if sec == 60:
        m, sec = m + 1, 0
    return f"{m:02d}:{sec:02d}"""


def chapters(lines):
    """Главы = начало блока (для описания YouTube/VK)."""
    out, seen = [], set()
    for it in lines:
        b = int(it["block"])
        if b in seen:
            continue
        seen.add(b)
        out.append((b, it["start"]))
    return out


CH = {1: "Хук: два одинаковых прибора, один молчит", 2: "Что за приборы и что будет в видео",
      3: "Шаги 1–2: кейс, QR-код, канал, приложение", 4: "Шаги 3–5: сборка, режим прошивки, кабель",
      5: "Шаги 6–8: помощник, местная прошивка, проверка", 6: "Файлы прошивки A2 и A1 — как не перепутать",
      7: "Пять функций новой версии", 8: "«Алдан-8» и часы оповещения",
      9: "Пять частых ошибок", 10: "Чек-лист перед обновлением", 11: "Планы производителя и финал"}


def publish(path, lines, total):
    ch = chapters(lines)
    desc = [
        "«Алдан-12»: обновление прошивки до версии 1.6 с телефона — без компьютера. "
        "Восемь шагов, где взять файлы A2/A1, пять функций новой версии, часы оповещения и чек-лист.",
        "",
        "Что внутри:",
        "• как войти в режим прошивки (две боковые кнопки);",
        "• кабель USB Type-C + OTG — что включить в телефоне;",
        "• «Помощник обновления» и «Местная прошивка» в приложении «Алдан» 1.2.6;",
        "• проверка версии после обновления;",
        "• файлы A2 («Алдан-12») и A1 («Алдан-8») — как не перепутать;",
        "• пять функций: быстрые клавиши, «Штурм», LED, яркость, Walksnail Ascent 5800 МГц;",
        "• часы оповещения и кнопка 5T;",
        "• пять частых ошибок и чек-лист.",
        "",
        "Источник: видео производителя и руководство пользователя. Без догадок, без ТТХ, без цен.",
        "Схемы и макеты экранов — иллюстрации, а не съёмка реального прибора.",
        "",
        "Главы:",
    ]
    for b, st in ch:
        desc.append(f"{fmt(st)} — {CH.get(b, '')}")
    desc += ["", "Подписывайтесь: t.me/vokope_ru · vk.com/vokope_rus",
             "Магазин: avito.ru/brands/…", "", "Тайм-коды указаны по финальному монтажу."]
    title = "«Алдан-12»: прошивка 1.6 с телефона — 8 шагов, 5 функций, A2/A1"
    tags = ("#Алдан12 #прошивка #детектордронов #ВОКОПЕ #Walksnail #Ascent #FPV "
            "#обновлениеПО #инструкция #БПЛА")
    open(path, "w", encoding="utf-8").write(
        f"ЗАГОЛОВОК ({len(title)} знаков):\n{title}\n\nОПИСАНИЕ:\n" + "\n".join(desc) +
        f"\n\nТЕГИ:\n{tags}\n\nДЛИТЕЛЬНОСТЬ: {fmt(total)}\n")
    return title


def thumb(path, lines):
    """Обложка 1280×720: тёмная панель + реальное фото в рамке."""
    W, H = 1280, 720
    base = Image.new("RGB", (W, H), (8, 9, 10))
    # фото справа, вписано целиком
    ph = Image.open(os.path.join(BASE, "assets", "hero_kit.jpg")).convert("RGB")
    s = min(560 / ph.width, 560 / ph.height)
    ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    ph = Image.eval(ph, lambda v: int(v * 0.86))
    px, py = 700 + (580 - ph.width) // 2, 80
    base.paste(ph, (px, py))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([px - 2, py - 2, px + ph.width + 2, py + ph.height + 2],
                outline=(255, 122, 46, 210), width=3)
    d.rectangle([0, 0, 700, H], fill=(7, 8, 10, 236))
    d.rectangle([698, 0, 706, H], fill=(255, 122, 46, 240))
    d.rectangle([0, 0, W, 6], fill=(255, 122, 46, 255))

    RUSSO = "/home/user/-/video_studio/toolkit/fonts/RussoOne-Regular.ttf"
    DAYS = "/home/user/-/video_studio/toolkit/fonts/DaysOne-Regular.ttf"
    MONO = "/home/user/-/video_studio/toolkit/fonts/JetBrainsMono-VF.ttf"

    def ft(p, s):
        return ImageFont.truetype(p, s)

    d.text((48, 44), "«В ОКОПЕ»", font=ft(RUSSO, 32), fill=(242, 243, 245, 255))
    d.text((48, 96), "ПРОШИВКА 1.6", font=ft(DAYS, 74), fill=(255, 122, 46, 255))
    d.text((48, 200), "С ТЕЛЕФОНА", font=ft(RUSSO, 60), fill=(242, 243, 245, 255))
    d.text((48, 272), "БЕЗ КОМПЬЮТЕРА", font=ft(RUSSO, 60), fill=(242, 243, 245, 255))
    d.rectangle([48, 366, 250, 374], fill=(255, 122, 46, 255))
    d.text((48, 402), "8 ШАГОВ  ·  5 ФУНКЦИЙ", font=ft(RUSSO, 40), fill=(46, 200, 190, 255))
    d.text((48, 486), "A2 — «АЛДАН-12»   A1 — «АЛДАН-8»", font=ft(MONO, 25), fill=(210, 214, 220, 255))
    d.text((48, 528), "МАКЕТЫ ЭКРАНОВ — ИЛЛЮСТРАЦИИ", font=ft(MONO, 21), fill=(150, 156, 166, 255))
    d.text((48, 610), "t.me/vokope_ru  ·  vk.com/vokope_rus", font=ft(MONO, 24), fill=(170, 176, 186, 255))
    d.text((W - 40, H - 46), "«АЛДАН-12» · КОМПЛЕКТ", font=ft(MONO, 21),
           fill=(230, 233, 238, 230), anchor="ra")
    out = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    out.save(path, quality=92)
    return path


if __name__ == "__main__":
    data = json.load(open(TL, encoding="utf-8"))
    lines, total = data["lines"], data["total"]
    print("SRT:", srt(lines, total, os.path.join(BASE, "ALDan_HORZ.srt")))
    t = publish(os.path.join(BASE, "publish.txt"), lines, total)
    print("publish.txt:", t, len(t), "знаков")
    print("обложка:", thumb(os.path.join(BASE, "thumb_1280x720.jpg"), lines))
    rel = os.path.join(BASE, "release")
    os.makedirs(rel, exist_ok=True)
    print("release/: создан")
