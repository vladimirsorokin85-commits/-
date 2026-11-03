# -*- coding: utf-8 -*-
"""Ролик 15 с: «у тебя есть своя волна» — короткий, в лоб."""
import base as B
import lib_scenes as L
from base import MONO, OLV, RUSSO, TXT, ac, c01, chips_row, slam, stage, tick_marks

VO = "a15.mp3"
LEAD = 0.25
TITLE = "РАДИО «В ОКОПЕ» · 15 СЕКУНД"

SCENES_FRAC = [("trench", 0.00), ("cab", 0.13), ("kitchen", 0.26), ("wave", 0.40),
               ("logo", 0.50), ("songs", 0.56), ("nostop", 0.79), ("end", 0.88)]
FX = [("impact_deep", 0.00, 0.60), ("whoosh_transition", 0.26, 0.32),
      ("cut_tick", 0.40, 0.36), ("riser_tension", 0.56, 0.26),
      ("logo_sting", 0.88, 0.46)]


def s_trench(cv, d, t, l):
    L.place(cv, d, t, l, "bg_trench", "В ОКОПЕ", "ГДЕ БЫ ТЫ НИ БЫЛ", "01", OLV, 2.0)


def s_cab(cv, d, t, l):
    L.place(cv, d, t, l, "bg_cab", "В МАШИНЕ", "ГДЕ БЫ ТЫ НИ БЫЛ", "02", OLV, 1.8)


def s_kitchen(cv, d, t, l):
    L.place(cv, d, t, l, "bg_kitchen", "НА КУХНЕ", "ГДЕ БЫ ТЫ НИ БЫЛ", "03", OLV, 1.8)


def s_wave(cv, d, t, l):
    L.wave(cv, d, t, l, "r15", "СВОЯ ВОЛНА", "У КАЖДОГО СВОЯ ЧАСТОТА")


def s_logo(cv, d, t, l):
    L.logo_scene(cv, d, t, l, "r15", "РАДИО")


def s_songs(cv, d, t, l):
    L.songs(cv, d, t, l, "r15", "КРУГЛЫЕ СУТКИ", "СТАРЫЕ И НОВЫЕ ПЕСНИ")


def s_nostop(cv, d, t, l):
    L.nostop(cv, d, t, l, "r15")


def s_end(cv, d, t, l):
    B.end_card(cv, d, l, OLV, "r15")


FN = {"trench": s_trench, "cab": s_cab, "kitchen": s_kitchen, "wave": s_wave,
      "logo": s_logo, "songs": s_songs, "nostop": s_nostop, "end": s_end}
