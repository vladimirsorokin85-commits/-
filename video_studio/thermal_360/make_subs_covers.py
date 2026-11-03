# -*- coding: utf-8 -*-
"""Субтитры и обложки рилса «Тепловизор 360°»."""
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, "/home/user/-/video_studio/thermal_360")
import render_reel as R  # noqa: E402

BASE = "/home/user/-/video_studio/thermal_360"
FF = "/home/user/.local/bin/ffmpeg"
VIDEO = os.path.join(BASE, "v_okope_thermal360_reel_9x16.mp4")

# (начало голоса, длительность по замеру build_audio.py, фразы)
VO = [
    (0.10, 3.79, ["Тепловизор на крышу.", "Триста шестьдесят градусов. День и ночь."]),
    (4.10, 5.33, ["Магнитное крепление —", "ставится за минуту.", "Питание — двенадцать вольт,", "от прикуривателя."]),
    (11.10, 3.02, ["Поворот и наклон — с пульта,", "прямо из салона."]),
    (15.10, 4.13, ["Тепловизор шестьсот сорок", "на пятьсот двенадцать,", "пятьдесят кадров в секунду."]),
    (19.60, 3.86, ["Днём — дневная камера Full HD,", "угол сто два градуса."]),
    (24.10, 3.24, ["Лазер — до километра.", "Кнопка A включает."]),
    (27.60, 3.77, ["Фокус — ключом, до резкости.", "Сдвиг не больше миллиметра."]),
    (31.60, 3.34, ["Картинка на мониторе,", "управление с пульта —", "из машины."]),
    (36.10, 6.36, ["Только двенадцать вольт.", "Двадцать четыре —", "выгорит электроника.",
                   "Полный разбор —", "на канале «В Окопе»."]),
]


def tstamp(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return ("%02d:%02d:%06.3f" % (h, m, sec)).replace(".", ",")


def build_srt():
    cues, n = [], 1
    for start, dur, parts in VO:
        total_chars = sum(len(p) for p in parts)
        t = start
        for p in parts:
            d = dur * len(p) / total_chars
            cues.append((n, t, t + d, p))
            n += 1
            t += d
    out = []
    for i, a, b, txt in cues:
        out.append("%d\n%s --> %s\n%s\n" % (i, tstamp(a), tstamp(b), txt))
    path = os.path.join(BASE, "TEPLO_REEL.srt")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    print("SRT:", path, "реплик:", len(cues))
    return cues


def cover():
    """Обложка 1080×1920 из кадра хука + акцентная плашка."""
    from PIL import ImageDraw, ImageFont
    im = R.render_frame(2.55).convert("RGB")
    p = os.path.join(BASE, "thumb_1080x1920.jpg")
    im.save(p, quality=92)
    print("обложка:", p)
    return p


def preview():
    """Кадр-превью из центральной сцены (без текста поверх устройства)."""
    p = os.path.join(BASE, "preview_1080x1920.jpg")
    R.render_frame(34.9).save(p, quality=90)
    print("превью:", p)
    return p


def check_black():
    r = subprocess.run([FF, "-hide_banner", "-i", VIDEO, "-vf", "blackdetect=d=0.2:pix_th=0.06",
                        "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr
    hits = [ln for ln in r.splitlines() if "black_start" in ln]
    print("чёрные вставки:", len(hits))
    for h in hits[:5]:
        print("   ", h.strip())


if __name__ == "__main__":
    build_srt()
    cover()
    preview()
    check_black()
