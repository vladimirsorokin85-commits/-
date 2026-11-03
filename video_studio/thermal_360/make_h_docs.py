# -*- coding: utf-8 -*-
"""Субтитры и обложки горизонтали."""
import os
import sys

sys.path.insert(0, "/home/user/-/video_studio/thermal_360")
import render_horz as R
from render_horz_base import SHOTS

BASE = "/home/user/-/video_studio/thermal_360"


def ts(s):
    return ("%02d:%02d:%06.3f" % (int(s // 3600), int((s % 3600) // 60), s % 60)).replace(".", ",")


lines = []
for i, sh in enumerate(SHOTS, 1):
    txt = (sh["vo"] or "").strip()
    if not txt:
        continue
    lines.append("%d\n%s --> %s\n%s\n" % (i, ts(sh["t0"] + 0.08), ts(sh["t1"] - 0.10), txt))
open(os.path.join(BASE, "TEPLO_HORZ.srt"), "w", encoding="utf-8").write("\n".join(lines))
print("SRT:", len(lines), "реплик")

R.render_frame(2.6).save(os.path.join(BASE, "thumb_1280x720.jpg"), quality=92)
R.render_frame(140.0).save(os.path.join(BASE, "preview_1280x720.jpg"), quality=90)
print("обложки готовы")
