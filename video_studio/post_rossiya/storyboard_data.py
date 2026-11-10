#!/usr/bin/env python3
"""Complete 100-shot storyboard & reference-chained prompt manifest for «ПОСТ-РОССИЯ».

88 main chronological shots (0:00 – 2:38 = 158.0s) + 12 universal B-roll cutaways = 100 shots,
plus 4 visual reference anchors (`ref_01_hero`, `ref_02_city`, `ref_03_choir`, `ref_04_color`).
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REFS_DIR = BASE_DIR / "refs"
FRAMES_DIR = BASE_DIR / "frames"
BROLL_DIR = BASE_DIR / "broll"

REFS = {
    "hero": "video_studio/post_rossiya/refs/ref_01_hero.jpg",
    "city": "video_studio/post_rossiya/refs/ref_02_city.jpg",
    "choir": "video_studio/post_rossiya/refs/ref_03_choir.jpg",
    "color": "video_studio/post_rossiya/refs/ref_04_color.jpg",
}

STYLE_TAIL = (
    "post-Soviet documentary surrealism photography, natural skin texture, muted desaturated palette, "
    "soft 35mm film grain, zero gloss, strictly no text, no readable signs, no logos, no flags, no watermarks"
)

# Each entry:
# (num, t0, t1, act, cue, desc_ru, color_state, move, focus, live_fx, fallback_ref, fallback_crop, refs_list, prompt_body)
# fallback_crop is (cx, cy, zoom_base) used ONLY while the dedicated shot_XXX.jpg is still queued for generation.
RAW_SHOTS = [
    # ==================== АКТ I. ЧУЖАЯ БОЛЬ (0:00–0:19) ====================
    (1, 0.0, 1.2, "АКТ I · ЧУЖАЯ БОЛЬ", "0:00–0:03 · Чёрный экран → свет экрана",
     "Смартфон в темноте на старом кухонном столе", "dirty_modern", "slow_in", (0.50, 0.50), "phone_emerge",
     "color", (0.5, 0.5, 1.05), ["color"],
     "16:9 widescreen cinematic photograph of a smartphone lying flat on a worn scratched wooden table in a pitch-dark Soviet apartment kitchen at night, a very faint cold pale-blue rectangular glow barely illuminating the screen and table grain, shot on 50mm f/1.8 lens"),
    (2, 1.2, 2.1, "АКТ I · ЧУЖАЯ БОЛЬ", "0:00–0:03 · Чёрный экран → свет экрана",
     "Сверхкрупный план треснувшего стекла смартфона", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "color", (0.5, 0.5, 1.15), ["color"],
     "16:9 widescreen extreme macro close-up of cracked glass on a dark smartphone screen at night, fine spiderweb hairline fractures catching a weak cold blue-grey glow in darkness, shot on 100mm macro lens"),
    (3, 2.1, 3.0, "АКТ I · ЧУЖАЯ БОЛЬ", "0:00–0:03 · Чёрный экран → свет экрана",
     "Отражение человеческого глаза в чёрном экране", "dirty_modern", "slow_in", (0.50, 0.46), None,
     "hero", (0.5, 0.32, 1.45), ["hero", "color"],
     "16:9 widescreen extreme close-up of a switched-off dark smartphone screen reflecting a single tired man's eye in a dark room at night, shot on 85mm macro lens"),
    (4, 3.0, 5.0, "АКТ I · ЧУЖАЯ БОЛЬ", "«Я плакал, смотря на чужой инстаграм»",
     "Мужчина сидит ночью на кухне панельной квартиры, свет от телефона", "dirty_modern", "slow_in", (0.52, 0.44), None,
     "hero", (0.5, 0.45, 1.08), ["hero", "color"],
     "16:9 widescreen cinematic shot of the same 35-year-old tired Russian man in a grey sweater sitting alone at night at a small table in a cramped Soviet panel-apartment kitchen, illuminated only by his smartphone screen, shot on 35mm f/1.8 lens"),
    (5, 5.0, 7.0, "АКТ I · ЧУЖАЯ БОЛЬ", "«Я плакал, смотря на чужой инстаграм»",
     "Крупный план лица героя: влажные глаза, сдержанное выражение", "dirty_modern", "slow_in", (0.50, 0.42), None,
     "hero", (0.5, 0.34, 1.32), ["hero", "color"],
     "16:9 widescreen intimate close-up of the same 35-year-old Russian man's face in a dark room lit from below by a phone screen, moist glistening eyes but stoic silent expression without dramatic crying, shot on 50mm f/1.8 lens"),
    (6, 7.0, 9.0, "АКТ I · ЧУЖАЯ БОЛЬ", "«Я плакал, смотря на чужой инстаграм»",
     "Вид через дверной проём: маленькая кухня и тёмный двор за окном", "dirty_modern", "slow_out", (0.50, 0.50), None,
     "city", (0.5, 0.48, 1.08), ["hero", "city"],
     "16:9 widescreen shot through a dark hallway doorway into a tiny Soviet kitchen at night: the man sits in silhouette at the table while outside the window yawns a vast dark courtyard of panel buildings, shot on 35mm lens"),
    (7, 9.0, 10.8, "АКТ I · ЧУЖАЯ БОЛЬ", "«Там кто-то вернулся с войны»",
     "Фотография: мужчина в гражданской одежде у старого автобуса с тростью", "dirty_modern", "slow_in", (0.50, 0.44), None,
     "hero", (0.5, 0.48, 1.06), ["city", "color"],
     "16:9 widescreen candid everyday Russian provincial photograph of a slim 30-year-old man in plain civilian olive-grey autumn jacket and jeans standing beside an old blue-and-white PAZ bus leaning on a black medical walking cane, no military uniform or medals, shot on 35mm lens"),
    (8, 10.8, 12.5, "АКТ I · ЧУЖАЯ БОЛЬ", "«Там кто-то вернулся с войны»",
     "Тот же человек на остановке, позади пустая пригородная дорога", "dirty_modern", "pan_right", (0.50, 0.46), None,
     "city", (0.55, 0.50, 1.12), ["shot_007", "city"],
     "16:9 widescreen shot of the exact same 30-year-old man in civilian jacket standing alone under a weathered concrete suburban bus shelter leaning on the same black cane, empty wet provincial road behind him, shot on 35mm lens"),
    (9, 12.5, 14.0, "АКТ I · ЧУЖАЯ БОЛЬ", "«Там кто-то вернулся с войны»",
     "Крупный план ботинка и трости на мокром асфальте", "dirty_modern", "static_live", (0.50, 0.55), "rain_streaks",
     "color", (0.52, 0.65, 1.22), ["color"],
     "16:9 widescreen low-angle close-up of a worn dark leather boot and the rubber tip of a walking cane resting on wet rain-slicked asphalt beside a puddle, shot on 50mm f/2 lens"),
    (10, 14.0, 15.6, "АКТ I · ЧУЖАЯ БОЛЬ", "«Принеся в ноге свинца пару грамм»",
     "Рентгеновский снимок ноги на старом негатоскопе с осколком", "dirty_modern", "slow_in", (0.50, 0.48), None,
     "shot_002", (0.5, 0.5, 1.12), ["color"],
     "16:9 widescreen close-up of a medical leg X-ray film clipped onto an old hospital fluorescent negatoscope in a dim provincial clinic, small white metallic lead fragment visible near the bone, shot on 50mm lens"),
    (11, 15.6, 17.3, "АКТ I · ЧУЖАЯ БОЛЬ", "«Принеся в ноге свинца пару грамм»",
     "Мужчина сидит на больничной кровати и массирует ногу", "dirty_modern", "slow_in", (0.50, 0.46), None,
     "shot_004", (0.5, 0.5, 1.12), ["shot_007", "color"],
     "16:9 widescreen shot of the same slim 30-year-old man sitting on a narrow provincial hospital bed in grey t-shirt and sweatpants gently massaging his lower leg, black cane leaning nearby, shot on 50mm f/2 lens"),
    (12, 17.3, 19.0, "АКТ I · ЧУЖАЯ БОЛЬ", "«Принеся в ноге свинца пару грамм»",
     "Вид из окна больничной палаты на дождливый двор (переход через капли)", "dirty_modern", "static_live", (0.50, 0.50), "rain_window_transition",
     "city", (0.48, 0.48, 1.10), ["city", "color"],
     "16:9 widescreen POV from inside a dim provincial hospital ward looking through a raindrop-streaked window onto a wet courtyard with bare trees and grey panel buildings, shot on 35mm lens"),

    # ==================== АКТ II. ПОЗДНЕЕ ПРОЩЕНИЕ (0:19–0:38) ====================
    (13, 19.0, 20.5, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Клали искусственные цветы к могилам»",
     "Дешёвые пластиковые цветы в ведре у кладбищенского киоска", "dirty_modern", "slow_in", (0.50, 0.52), None,
     "color", (0.42, 0.58, 1.18), ["color"],
     "16:9 widescreen documentary shot of cheap stiff artificial plastic flowers in galvanized metal buckets outside a weathered cemetery kiosk in late autumn drizzle, shot on 50mm lens"),
    (14, 20.5, 22.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Клали искусственные цветы к могилам»",
     "Женская рука выбирает искусственные красные гвоздики", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "shot_013", (0.45, 0.48, 1.18), ["shot_013", "color"],
     "16:9 widescreen close-up of a middle-aged woman's bare hand in a dark wool coat sleeve choosing cheap artificial red plastic carnations from a bucket in autumn drizzle, shot on 50mm lens"),
    (15, 22.0, 23.4, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Клали искусственные цветы к могилам»",
     "Крупный план пластмассового лепестка с каплей дождя", "dirty_modern", "static_live", (0.50, 0.50), "rain_streaks",
     "color", (0.40, 0.56, 1.35), ["color"],
     "16:9 widescreen extreme macro close-up of a frayed synthetic plastic red flower petal with visible molded plastic veins and a single cold raindrop on its surface, shot on 100mm macro lens"),
    (16, 23.4, 25.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Клали искусственные цветы к могилам»",
     "Общий план кладбища поздней осенью с искусственными цветами", "dirty_modern", "pan_left", (0.50, 0.52), None,
     "city", (0.45, 0.52, 1.12), ["city", "color"],
     "16:9 widescreen wide establishing shot of a Russian provincial cemetery in late November with bare black trees, muddy path, metal fences and bright artificial plastic flowers, shot on 35mm lens"),
    (17, 25.0, 26.6, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«И просили простить постфактум»",
     "Пожилая женщина стоит перед могилой, держа букет искусственных цветов", "dirty_modern", "slow_in", (0.50, 0.42), None,
     "choir", (0.46, 0.45, 1.35), ["choir", "shot_016"],
     "16:9 widescreen documentary photograph of a solitary elderly Russian woman in a worn dark coat and grey wool headscarf standing quietly with bowed head before a modest grave fence in a muddy late-autumn cemetery, holding a small bouquet of cheap red plastic carnations, overcast cold damp light, shot on 50mm f/2 lens"),
    (18, 26.6, 28.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«И просили простить постфактум»",
     "Крупный план пожилой руки, сжимающей мокрую чёрную ленту венка", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "shot_014", (0.50, 0.50, 1.22), ["shot_016", "color"],
     "16:9 widescreen macro close-up of an elderly woman's wrinkled hand gently gripping a rain-soaked black mourning ribbon without any text on an artificial pine wreath in cold drizzle, anatomically natural five fingers, shallow depth of field, cold slate-grey light, shot on 85mm f/2 lens"),
    (19, 28.0, 30.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«И просили простить постфактум»",
     "Пустая мокрая скамейка возле могилы (долгий неподвижный план)", "dirty_modern", "static_live", (0.50, 0.54), "rain_streaks",
     "shot_016", (0.35, 0.62, 1.28), ["shot_016", "color"],
     "16:9 widescreen static documentary composition of a small empty wet blue-painted wooden bench beside a modest iron grave fence in a deserted late-autumn Russian cemetery, fallen wet black leaves on the planks, bare trees in mist behind, cold flat overcast light, shot on 35mm f/2.8 lens"),
    (20, 30.0, 32.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Мы были такие красивые»",
     "Старая фотография конца 1990-х: молодые люди улыбаются во дворе", "dirty_modern", "slow_in", (0.50, 0.44), None,
     "hero", (0.50, 0.44, 1.12), ["city"],
     "16:9 widescreen authentic late-1990s Russian provincial analog snapshot of four young twenty-year-old friends—two young men and two young women in simple late-90s windbreakers, sweaters and denim—standing together and smiling warmly in a Soviet panel-building courtyard, slightly faded warm 1998 Kodacolor film aesthetic, full frame without borders or date stamps, shot on 35mm compact camera"),
    (21, 32.0, 33.8, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Мы были такие красивые»",
     "Та же фотография лежит на кухонном столе рядом с пустым стаканом", "dirty_modern", "slow_out", (0.50, 0.52), None,
     "shot_001", (0.52, 0.50, 1.16), ["shot_020", "shot_001"],
     "16:9 widescreen close-up still-life on a worn scratched Soviet kitchen table in dim cold twilight: a slightly curled glossy 10x15 printed photograph showing the exact same four smiling 1990s young friends from the reference image lies next to an empty faceted glass tumbler, cold blue window light, shot on 50mm f/2 lens"),
    (22, 33.8, 35.5, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Мы были такие красивые»",
     "Фотография отражается в тёмном оконном стекле на фоне ночного двора", "dirty_modern", "slow_in", (0.50, 0.48), None,
     "shot_006", (0.54, 0.46, 1.24), ["shot_020", "shot_006"],
     "16:9 widescreen double-reflection documentary shot: the printed 1990s snapshot of the four smiling young friends held near a dark apartment window at night softly reflects as a translucent ghost image across the dark glass over the dim courtyard of grey panel buildings outside, shot on 50mm f/1.8 lens"),
    (23, 35.5, 38.0, "АКТ II · ПОЗДНЕЕ ПРОЩЕНИЕ", "«Мы были такие красивые»",
     "Взрослые версии этих людей стоят в том же дворе спустя 20 лет, уставшие", "dirty_modern", "static_live", (0.50, 0.44), None,
     "hero", (0.50, 0.46, 1.06), ["shot_020", "city"],
     "16:9 widescreen documentary photograph of the exact same four friends from the 1990s reference photograph now twenty-five years older in their mid-forties, standing slightly apart in the exact same grey Soviet panel-house courtyard in late autumn, wearing plain dark everyday jackets, naturally aged tired faces with quiet estrangement, barely looking at one another, cold overcast light, shot on 35mm lens"),

    # ==================== АКТ III. ЦЕНА САМОУВЕРЕННОСТИ (0:38–0:52) ====================
    (24, 38.0, 39.8, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Все думали, самые умные, гордые»",
     "Молодые мужчины возле старого чёрного седана на фоне гаражей", "dirty_modern", "pan_right", (0.50, 0.46), None,
     "city", (0.28, 0.62, 1.26), ["city", "color"],
     "16:9 widescreen documentary photograph of three ordinary young Russian provincial men in their late twenties wearing neat dark leather and quilted jackets, standing in self-assured confident casual postures leaning beside an old black 2000s sedan car in front of rusty metal Soviet garages on wet gravel, ordinary faces without caricature villainy, cold grey daylight, shot on 35mm lens"),
    (25, 39.8, 41.4, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Все думали, самые умные, гордые»",
     "Крупный план дорогих металлических часов на руке одного из них", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "shot_002", (0.48, 0.52, 1.22), ["shot_024", "color"],
     "16:9 widescreen close-up of a heavy polished stainless-steel luxury wristwatch on a young man's wrist protruding from the cuff of a dark leather jacket as his hand rests on the black car door, cold overcast reflection on steel and wet car paint, no brand logo or readable dial text, shot on 85mm f/2 lens"),
    (26, 41.4, 43.0, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Все думали, самые умные, гордые»",
     "Отражение их лиц в тёмном боковом стекле автомобиля", "dirty_modern", "slow_in", (0.50, 0.45), None,
     "shot_003", (0.50, 0.45, 1.18), ["shot_024", "color"],
     "16:9 widescreen close-up of the tinted wet side window of an old black sedan reflecting the muted confident faces of two young men and the grey sky above rusty garages, raindrops on the dark glass, cold slate-blue palette, shot on 50mm f/2 lens"),
    (27, 43.0, 44.7, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Оказалось, вывезли за долги»",
     "Тот же чёрный автомобиль ночью у заброшенного промздания", "dirty_modern", "pan_left", (0.50, 0.52), None,
     "city", (0.62, 0.56, 1.24), ["shot_024", "color"],
     "16:9 widescreen nocturnal documentary wide shot of the exact same old black sedan parked alone at night on muddy ground beside a dark abandoned concrete industrial warehouse on the town outskirts, weak dim headlights cutting into cold mist and puddles, single distant sodium lamp, shot on 35mm f/1.8 lens"),
    (28, 44.7, 46.3, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Оказалось, вывезли за долги»",
     "Открытая задняя дверь чёрного автомобиля, в салоне темно", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "shot_001", (0.45, 0.52, 1.22), ["shot_024", "color"],
     "16:9 widescreen medium close-up at night of the flung-open rear passenger door of the old black sedan on a muddy industrial lot, pitch-dark empty car interior inside, mud on the sill and rain droplets on black metal in cold dim blue-yellow twilight, ominous quiet absence, shot on 50mm f/1.8 lens"),
    (29, 46.3, 48.0, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Оказалось, вывезли за долги»",
     "Одинокая мужская фигура стоит перед бетонной стеной, лица не видно", "dirty_modern", "static_live", (0.50, 0.48), None,
     "hero", (0.50, 0.48, 1.20), ["color"],
     "16:9 widescreen atmospheric nocturnal shot from behind of a solitary young man's silhouette standing motionless facing a damp stained concrete industrial wall at night, head slightly lowered, face completely unseen, no violence shown, harsh cold side-shadow and wet concrete texture, minimalist social horror, shot on 35mm f/2 lens"),
    (30, 48.0, 49.0, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Там и оставили модные и холодные»",
     "Дорогая тёмная куртка лежит в грязи и луже возле гаражей", "dirty_modern", "slow_in", (0.50, 0.55), None,
     "color", (0.55, 0.60, 1.20), ["shot_024", "color"],
     "16:9 widescreen low-angle documentary shot of an expensive dark leather jacket lying crumpled and abandoned in cold mud and rainwater puddles beside rusted metal garages at dawn, no blood, no body, quiet eerie aftermath, cold blue-grey pre-dawn light, shot on 50mm f/2 lens"),
    (31, 49.0, 50.0, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Там и оставили модные и холодные»",
     "Разбитые наручные часы на мокрой земле с остановившимися стрелками", "dirty_modern", "slow_in", (0.50, 0.50), None,
     "shot_002", (0.52, 0.48, 1.26), ["color"],
     "16:9 widescreen extreme close-up of a luxury stainless-steel wristwatch lying in wet dark mud and gravel with cracked crystal glass and stopped hands, no brand name or numbers on dial, cold grey morning light reflecting in water droplets, shot on 100mm macro lens"),
    (32, 50.0, 50.9, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Там и оставили модные и холодные»",
     "Чёрный автомобиль уезжает по пустой сырой дороге, красные задние огни", "dirty_modern", "static_live", (0.50, 0.52), None,
     "city", (0.72, 0.58, 1.28), ["shot_024", "color"],
     "16:9 widescreen wide shot of the old black sedan driving away down a deserted wet asphalt road at cold dusk, glowing red taillights reflecting as long red streaks on the slick wet pavement between bare dark fields, shot on 50mm f/2 lens"),
    (33, 50.9, 52.0, "АКТ III · ЦЕНА САМОУВЕРЕННОСТИ", "«Плати налоги и включай мозги» (резкий дневной срез)",
     "Длинная очередь уставших людей в коридоре госучреждения днём", "dirty_modern", "pan_right", (0.50, 0.46), None,
     "choir", (0.50, 0.45, 1.15), ["color"],
     "16:9 widescreen deadpan documentary wide shot inside a drab provincial Russian municipal office corridor during daytime: a long silent queue of ordinary tired citizens in autumn coats holding plain paper folders standing along pale beige-green walls under harsh cold fluorescent ceiling lights, dry bureaucratic absurdity, no readable signs or text, shot on 35mm f/2.8 lens"),

    # ==================== 3. ПЕРВЫЙ ПРИПЕВ — ГОЛОС ПОСТ-РОССИИ (0:52–1:17) ====================
    (34, 52.0, 55.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«И стонет в лапах бессилия»",
     "Огромное пустое осеннее поле, вдалеке на горизонте стоят люди", "faded_memory", "slow_in", (0.50, 0.48), "ground_mist",
     "choir", (0.50, 0.42, 1.02), ["choir"],
     "16:9 widescreen vast extreme wide establishing photograph of an immense empty late-autumn Russian field of black wet plowed earth and bleached dry grass stretching under a heavy pale-grey sky, far in the distance tiny dark figures of women stand motionless in low cold mist, shot on 28mm lens"),
    (35, 55.0, 58.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«И стонет в лапах бессилия»",
     "Средне-общий план: около тридцати женщин в обычных пальто, платках и старых куртках", "faded_memory", "slow_in", (0.50, 0.46), "ground_mist",
     "choir", (0.50, 0.48, 1.12), ["choir"],
     "16:9 widescreen medium-wide documentary shot of the thirty ordinary Russian provincial women of all ages from the reference image standing together in the misty late-autumn field, dressed in everyday worn coats, drab quilted jackets and wool headscarves, no folk costumes, pale grey sky, shot on 35mm lens"),
    (36, 58.0, 60.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Пост-Россия: прости меня»",
     "Крупный план пожилой женщины из хора, смотрящей прямо в объектив", "faded_memory", "slow_in", (0.50, 0.40), None,
     "choir", (0.46, 0.44, 1.48), ["choir"],
     "16:9 widescreen intimate documentary close-up portrait of a 70-year-old Russian grandmother from the choir in a worn grey wool shawl and dark coat, deeply lined exhausted calm face looking directly into the camera lens without blinking, misty field softly blurred behind, pale grey overcast light, shot on 50mm f/2 lens"),
    (37, 60.0, 62.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Пост-Россия: прости меня»",
     "Средний план нескольких женщин разного возраста, тихо поющих вместе", "faded_memory", "slow_in", (0.50, 0.44), None,
     "choir", (0.58, 0.46, 1.32), ["choir"],
     "16:9 widescreen medium shot of five women of different generations from the choir standing shoulder to shoulder in everyday dark coats and headscarves in the misty autumn field, mouths slightly open singing a solemn chant together, visible cold breath in damp air, shot on 50mm f/2.2 lens"),
    (38, 62.0, 64.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Пост-Россия: прости меня»",
     "Общий план хора на фоне низкого бледно-серого неба", "faded_memory", "slow_out", (0.50, 0.48), "ground_mist",
     "choir", (0.50, 0.45, 1.06), ["choir"],
     "16:9 widescreen low-angle wide shot of the entire women's choir standing motionless on black wet earth silhouetted softly against an enormous pale-grey overcast November sky and drifting cold fog, shot on 35mm lens"),
    (39, 64.0, 66.2, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Так пахнет утро последнее»",
     "Поле в низком холодном тумане, на горизонте панельный микрорайон", "faded_memory", "pan_right", (0.50, 0.50), "ground_mist",
     "city", (0.50, 0.44, 1.12), ["city", "choir"],
     "16:9 widescreen atmospheric landscape of a dark sodden autumn field blanketed in thick low ground fog, on the distant misty horizon rises the ghostly grey silhouette of a Soviet nine-story panel apartment district under a pale colorless sky, shot on 35mm lens"),
    (40, 66.2, 68.2, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Так пахнет утро последнее»",
     "Пустая бетонная автобусная остановка посреди туманного поля", "faded_memory", "static_live", (0.50, 0.50), "ground_mist",
     "shot_008", (0.36, 0.50, 1.18), ["shot_008", "choir"],
     "16:9 widescreen static documentary wide shot of a completely deserted weathered grey concrete Soviet bus stop shelter standing alone beside an empty wet road in the middle of a vast misty late-autumn field, no people, pale grey sky, shot on 35mm f/2.8 lens"),
    (41, 68.2, 70.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Так пахнет утро последнее»",
     "Ржавый дорожный указатель у обочины совершенно без надписей", "faded_memory", "slow_in", (0.50, 0.44), None,
     "shot_008", (0.68, 0.46, 1.30), ["choir"],
     "16:9 widescreen close-up of a weathered rusted rectangular metal roadside sign on a tilted pole beside a foggy field road, its paint completely peeled and bleached blank with zero letters or symbols, cold water droplets along the bottom edge, pale grey sky behind, shot on 50mm f/2.2 lens"),
    (42, 70.0, 72.3, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Предосеннее, предрасстрельное»",
     "Женщины стоят неподвижно в поле, над ними пролетает стая чёрных ворон", "faded_memory", "static_live", (0.50, 0.42), "crows_drift",
     "choir", (0.50, 0.38, 1.08), ["choir"],
     "16:9 widescreen wide documentary shot of the thirty women in coats and headscarves standing completely motionless in the dark autumn field while a scattered flock of black crows flies across the pale leaden-grey sky above their heads, cold ground fog, shot on 35mm lens"),
    (43, 72.3, 74.5, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Предосеннее, предрасстрельное»",
     "Крупный план молодой женщины из хора: по щеке медленно течёт слеза", "faded_memory", "slow_in", (0.50, 0.42), None,
     "choir", (0.36, 0.42, 1.48), ["choir"],
     "16:9 widescreen intimate close-up of a 25-year-old Russian woman standing among the choir in a plain dark wool coat and simple knitted scarf, pale natural face looking forward as a single tear tracks slowly down her cheek, completely quiet restrained expression, cold misty daylight, shot on 50mm f/1.8 lens"),
    (44, 74.5, 77.0, "I ПРИПЕВ · ГОЛОС ПОСТ-РОССИИ", "«Предосеннее, предрасстрельное»",
     "Очень широкий план поля: хор кажется крошечной группой среди пустоты", "faded_memory", "slow_out", (0.50, 0.54), "ground_mist",
     "choir", (0.50, 0.44, 1.01), ["choir"],
     "16:9 widescreen extreme distant aerial-hilltop perspective over a boundless empty black-and-grey late-autumn Russian plain shrouded in low mist, the women's choir visible only as a tiny fragile cluster of dark figures lost in the overwhelming silent landscape, shot on 24mm wide lens"),

    # ==================== 4. ВТОРОЙ КУПЛЕТ — РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ (1:17–2:04) ====================
    (45, 77.0, 78.4, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Рукомойник наполнить густыми мыслями»",
     "Старый эмалированный рукомойник и раковина в коммунальной кухне", "reality_decay", "slow_in", (0.50, 0.50), None,
     "shot_004", (0.28, 0.52, 1.28), ["color"],
     "16:9 widescreen documentary close-up of an old chipped stained white enamel washbasin and brass faucet on a peeling olive-brown wall in a dim Soviet communal apartment kitchen, damp rust stains, earthy swampy shadow tones, shot on 50mm f/2 lens"),
    (46, 78.4, 79.8, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Рукомойник наполнить густыми мыслями»",
     "Из старого крана медленно течёт густая чёрная маслянистая жидкость", "reality_decay", "static_live", (0.50, 0.50), "black_liquid_drip",
     "shot_002", (0.50, 0.50, 1.24), ["color"],
     "16:9 widescreen macro close-up of a tarnished old kitchen faucet pouring a slow heavy stream of thick glossy pitch-black liquid into a stained porcelain sink, understated mundane surrealism looking completely physical and real, dim muddy yellow-brown tungsten light, shot on 85mm macro lens"),
    (47, 79.8, 81.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Рукомойник наполнить густыми мыслями»",
     "Главный герой подставляет ладони под густую чёрную струю", "reality_decay", "slow_in", (0.50, 0.52), "black_liquid_drip",
     "shot_004", (0.42, 0.65, 1.32), ["hero", "color"],
     "16:9 widescreen close-up of the cupped bare hands of the 35-year-old man in rolled-up grey sweater sleeves held beneath an old kitchen tap as thick viscous black water pools in his palms, anatomically correct five-fingered hands, dim earthy brown-green light, shot on 50mm f/2 lens"),
    (48, 81.2, 82.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Умыть ключевое лицо»",
     "Крупный план главного героя перед старым треснувшим зеркалом", "reality_decay", "slow_in", (0.50, 0.42), None,
     "shot_005", (0.50, 0.42, 1.14), ["hero", "color"],
     "16:9 widescreen medium close-up of the exact same 35-year-old tired Russian man in grey sweater looking quietly at himself in a tarnished wall mirror crossed by a single diagonal crack in a dim bathroom, sickly warm-brown tungsten bulb light, shot on 50mm f/1.8 lens"),
    (49, 82.6, 84.0, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Умыть ключевое лицо»",
     "Герой умывает лицо чёрной водой над раковиной", "reality_decay", "slow_in", (0.50, 0.46), None,
     "shot_005", (0.50, 0.48, 1.24), ["hero", "color"],
     "16:9 widescreen close-up of the exact same 35-year-old man leaning over the sink pressing his hands wet with thick black water to his cheeks and forehead, dark droplets running down his skin, completely calm ordinary gesture, dim swampy-brown bathroom light, shot on 50mm f/2 lens"),
    (50, 84.0, 85.8, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Умыть ключевое лицо» (аномалия зеркала)",
     "Лицо мужчины мокрое в чёрных каплях, но отражение в зеркале абсолютно сухое", "reality_decay", "slow_in", (0.50, 0.44), None,
     "shot_005", (0.50, 0.40, 1.18), ["hero", "color"],
     "16:9 widescreen over-the-shoulder surreal documentary shot at a cracked bathroom mirror: in the foreground profile the 35-year-old man's real cheek and jaw are dripping wet with black water droplets, while his reflection facing us inside the mirror glass has a completely dry clean calm face, uncanny quiet impossibility, dim earthy light, shot on 50mm f/2 lens"),
    (51, 85.8, 87.3, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Паразиты, харам, нечистые»",
     "Переполненный тусклый подземный переход, люди идут в разные стороны", "reality_decay", "pan_left", (0.50, 0.48), None,
     "city", (0.55, 0.55, 1.20), ["city", "color"],
     "16:9 widescreen documentary shot inside a crowded grimy post-Soviet concrete pedestrian underpass: dozens of tired commuters in dark autumn coats walking past stained tiled walls in opposite directions with slight motion blur, flickering sickly yellow-green fluorescent ceiling tubes, shot on 35mm f/2.2 lens"),
    (52, 87.3, 88.7, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Паразиты, харам, нечистые»",
     "Крупный план грязной бурой воды, стекающей по ступеням перехода", "reality_decay", "static_live", (0.50, 0.55), "rain_streaks",
     "color", (0.60, 0.68, 1.28), ["color"],
     "16:9 widescreen low-angle close-up of muddy brown slush water trickling slowly down chipped concrete steps of an underground passage past scuffed boots walking by in the blurred background, swampy olive-brown reflection, shot on 50mm f/2 lens"),
    (53, 88.7, 90.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Паразиты, харам, нечистые»",
     "Человек в дорогом костюме стоит среди рабочих, его лицо скрыто густой тенью", "reality_decay", "slow_in", (0.50, 0.44), None,
     "hero", (0.50, 0.48, 1.18), ["color"],
     "16:9 widescreen eerie documentary medium shot inside a dim underpass crowd: a man in an immaculate tailored dark wool overcoat and crisp white collar stands dead still amid passing people in worn work jackets, an overhead broken light fixture casts deep pitch-black shadow completely obscuring his upper face, no caricature, shot on 50mm f/2 lens"),
    (54, 90.2, 91.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Раньше курицы было яйцо»",
     "Простое белое куриное яйцо на старом деревянном кухонном столе", "reality_decay", "slow_in", (0.50, 0.52), None,
     "shot_001", (0.48, 0.48, 1.22), ["color"],
     "16:9 widescreen minimalist close-up still-life of a single plain white raw chicken egg resting on a dark scarred wooden kitchen table in dim earthy afternoon light, shallow depth of field, quiet ominous simplicity, shot on 85mm f/2 lens"),
    (55, 91.6, 93.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Раньше курицы было яйцо»",
     "Из трещины в яичной скорлупе медленно вытекает густая чёрная жидкость", "reality_decay", "slow_in", (0.50, 0.52), "black_liquid_drip",
     "shot_002", (0.52, 0.52, 1.28), ["color"],
     "16:9 widescreen extreme macro close-up of the white chicken egg on the dark wooden table with a fine jagged crack in its shell from which thick glossy pitch-black viscous liquid slowly oozes onto the wood grain, tactile grounded surrealism echoing the black sink water, shot on 100mm macro lens"),
    (56, 93.2, 94.7, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Мы куражимся, нужные, босые»",
     "Мужчины в рабочей одежде стоят у старой заводской проходной утром", "reality_decay", "pan_right", (0.50, 0.48), None,
     "city", (0.78, 0.52, 1.28), ["city", "color"],
     "16:9 widescreen documentary wide shot of several ordinary Russian factory workers in worn dark canvas work jackets standing quietly smoking outside a weathered brick and concrete Soviet factory gatehouse in damp brown-grey morning mist, smokestacks behind, shot on 35mm f/2.8 lens"),
    (57, 94.7, 96.1, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Мы куражимся, нужные, босые»",
     "Крупный план тяжёлых грязных ботинок в глине на мокром асфальте", "reality_decay", "slow_in", (0.50, 0.58), None,
     "shot_009", (0.50, 0.55, 1.15), ["shot_009", "color"],
     "16:9 widescreen low-angle close-up of two pairs of mud-caked worn work boots standing in brown puddles on cracked wet asphalt outside a factory gate, cigarette butt floating in muddy water, earthy grey-brown palette, shot on 50mm f/2 lens"),
    (58, 96.1, 97.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Мы куражимся, нужные, босые»",
     "Крупный план рабочего: он слабо улыбается, хотя выглядит совершенно измученным", "reality_decay", "slow_in", (0.50, 0.40), None,
     "hero", (0.50, 0.36, 1.38), ["color"],
     "16:9 widescreen documentary close-up portrait of a 42-year-old Russian factory worker in a dusty work jacket with deep dark circles under his eyes and grimy stubble, offering a faint crooked weary smile to a coworker off-camera despite utter exhaustion, natural skin, cold muddy morning light, shot on 50mm f/1.8 lens"),
    (59, 97.6, 99.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Улыбаемся милым вам»",
     "Работник небольшого магазина вежливо улыбается покупателю", "reality_decay", "slow_in", (0.50, 0.42), None,
     "shot_004", (0.52, 0.42, 1.20), ["color"],
     "16:9 widescreen documentary medium close-up inside a small provincial grocery shop: a tired 38-year-old male clerk in a plain dark blue work vest behind the counter puts on a polite gentle customer-service smile toward a shopper's shoulder in the foreground, greenish-yellow fluorescent ceiling tubes, no readable labels or prices, shot on 50mm f/2 lens"),
    (60, 99.2, 100.8, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Улыбаемся милым вам»",
     "Тот же работник сидит один на ящике в тесной подсобке, опустив голову", "reality_decay", "slow_out", (0.50, 0.48), None,
     "shot_011", (0.48, 0.48, 1.16), ["shot_059", "color"],
     "16:9 widescreen documentary medium shot inside a cramped dim storage backroom stacked with plain unmarked cardboard boxes: the exact same 38-year-old shop worker in the dark blue vest sits alone on a plastic crate with elbows on knees and head bowed low in silent exhaustion under a bare dim bulb, shot on 35mm f/2 lens"),
    (61, 100.8, 102.3, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Но расквасят носы курносые»",
     "Двое обычных мужчин напряжённо стоят друг напротив друга у гаражей", "reality_decay", "static_live", (0.50, 0.46), None,
     "city", (0.30, 0.58, 1.24), ["city", "color"],
     "16:9 widescreen documentary wide-medium shot of two ordinary tired provincial men in plain dark jackets standing tensely two paces apart facing each other in a muddy alley between rusty metal garages, awkward real human confrontation without action-movie poses, damp overcast twilight, shot on 35mm f/2.8 lens"),
    (62, 102.3, 103.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Но расквасят носы курносые»",
     "Крупный план туго сжатого мужского кулака у кармана куртки", "reality_decay", "slow_in", (0.50, 0.50), None,
     "shot_014", (0.52, 0.52, 1.25), ["color"],
     "16:9 widescreen close-up of a man's bare cold-reddened hand clenched into a tight reluctant fist beside the frayed cuff of a dark autumn jacket, slightly scraped knuckles, anatomically accurate five fingers, shallow depth of field against muddy garage wall, shot on 85mm f/2 lens"),
    (63, 103.6, 105.0, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Но расквасят носы курносые»",
     "Крупный план разбитой губы на спокойном уставшем мужском лице", "reality_decay", "slow_in", (0.50, 0.52), None,
     "shot_005", (0.50, 0.55, 1.36), ["color"],
     "16:9 widescreen tight close-up of the lower face and chin of an ordinary 35-year-old stubbled man with a small fresh split and smudge of dark blood on his lower lip, calm numb expression without theatrics, cold damp evening light, natural skin pores, shot on 85mm macro lens"),
    (64, 105.0, 106.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«За стабильность любимых дам»",
     "Женщина спокойно спит под одеялом в полутёмной тёплой комнате", "reality_decay", "slow_in", (0.50, 0.46), None,
     "shot_004", (0.48, 0.45, 1.18), ["color"],
     "16:9 widescreen intimate documentary shot of an ordinary 33-year-old Russian woman sleeping peacefully on her side under a warm patterned duvet in a quiet dim panel-apartment bedroom, faint warm amber streetlight filtering through sheer curtains onto her calm face, tender fragile stillness, shot on 50mm f/1.8 lens"),
    (65, 106.6, 108.1, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«За стабильность любимых дам»",
     "Главный герой сидит ночью на кухне, молча разбирая бумажные счета", "reality_decay", "slow_in", (0.50, 0.46), None,
     "shot_004", (0.50, 0.48, 1.10), ["hero", "shot_004"],
     "16:9 widescreen documentary medium shot of the exact same 35-year-old man in his grey sweater sitting late at night at the small kitchen table under a dim warm-yellow hanging lamp, rubbing his forehead while looking down at a stack of plain paper utility bills, no readable text or numbers, shot on 35mm f/2 lens"),
    (66, 108.1, 109.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«За стабильность любимых дам»",
     "На столе лежат ключи от квартиры, квитанции и маленькая семейная фотография", "reality_decay", "slow_out", (0.50, 0.52), None,
     "shot_001", (0.50, 0.52, 1.18), ["color"],
     "16:9 widescreen overhead close-up still-life on an old oilcloth kitchen table under dim yellow lamp light: a simple metal apartment key ring, folded paper utility slips with blurred unreadable lines, and a small worn printed family snapshot of a woman and child, earthy brown-amber shadows, shot on 50mm f/2 lens"),
    (67, 109.6, 111.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Мы же им позавидуем тихонько»",
     "Главный герой стоит под дождём и смотрит на тёплые окна чужого дома", "reality_decay", "static_live", (0.50, 0.46), "rain_streaks",
     "hero", (0.50, 0.44, 1.12), ["hero", "city"],
     "16:9 widescreen nocturnal documentary shot of the exact same 35-year-old man in his wet dark autumn jacket standing motionless in cold rain in a dark muddy courtyard, seen from three-quarter back profile looking up toward warm glowing yellow apartment windows on the second floor of a grey panel building, shot on 35mm f/1.8 lens"),
    (68, 111.2, 112.8, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Мы же им позавидуем тихонько»",
     "За мокрым стеклом первого этажа семья тихо ужинает под абажуром", "reality_decay", "slow_in", (0.50, 0.46), "rain_streaks",
     "shot_006", (0.52, 0.48, 1.26), ["city", "color"],
     "16:9 widescreen exterior voyeuristic documentary view from the dark rainy street looking through a rain-beaded apartment window: inside under a warm orange kitchen lampshade a mother, father and child sit quietly eating dinner together, framed by dark cold wet concrete walls outside, shot on 50mm f/1.8 lens"),
    (69, 112.8, 114.4, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«В лес уйдём собирать падальё»",
     "Несколько людей в старых куртках идут по сырому осеннему лесу с пустыми корзинами", "reality_decay", "pan_right", (0.50, 0.48), None,
     "choir", (0.52, 0.50, 1.16), ["color"],
     "16:9 widescreen eerie documentary wide shot of four ordinary provincial people in drab mud-colored jackets walking silently single-file among bare black birch and aspen trunks in a sodden late-November forest, carrying empty woven wicker baskets, brown decaying leaf litter and mist, shot on 35mm f/2.8 lens"),
    (70, 114.4, 115.8, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«В лес уйдём собирать падальё»",
     "Крупный план мёртвой чёрной птицы среди мокрых бурых осенних листьев", "reality_decay", "slow_in", (0.50, 0.54), None,
     "color", (0.48, 0.62, 1.30), ["color"],
     "16:9 widescreen high-angle documentary close-up of a still dead black rook bird lying peacefully intact among wet rotting brown oak and birch leaves on dark forest soil, rainwater beads on glossy black feathers, understated natural memento mori without gore, shot on 50mm f/2.2 lens"),
    (71, 115.8, 117.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«В лес уйдём собирать падальё»",
     "Человеческая рука тянется к мокрой листве на земле, но замирает в воздухе", "reality_decay", "static_live", (0.50, 0.52), None,
     "shot_014", (0.48, 0.54, 1.24), ["color"],
     "16:9 widescreen low-angle close-up near the wet forest floor: a man's bare hand emerging from a dark jacket sleeve reaches hesitantly down toward sodden brown autumn leaves and freezes motionless mid-air inches above the dark earth, anatomically natural five fingers, shallow depth of field, shot on 50mm f/2 lens"),
    (72, 117.2, 118.7, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«И весна уже не воротится»",
     "Заброшенная советская детская площадка среди голых чёрных деревьев", "reality_decay", "pan_left", (0.50, 0.50), None,
     "city", (0.45, 0.55, 1.18), ["city", "color"],
     "16:9 widescreen wide documentary photograph of an abandoned Soviet metal playground with peeling faded paint standing in mud and puddles among bare black trees between grey panel houses in late autumn, completely empty, swampy brown-grey overcast light, shot on 35mm f/2.8 lens"),
    (73, 118.7, 120.2, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«И весна уже не воротится»",
     "Ржавые пустые качели едва заметно раскачиваются на холодном ветру", "reality_decay", "static_live", (0.50, 0.52), None,
     "shot_016", (0.55, 0.58, 1.26), ["city", "color"],
     "16:9 widescreen medium close-up of an empty rusted metal playground swing seat suspended on iron rods over a muddy puddle reflecting bare branches, slight diagonal tilt from cold autumn wind, muted brown and steel-grey tones, shot on 50mm f/2 lens"),
    (74, 120.2, 121.4, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Про неё нам споёт вороньё»",
     "Чёрная ворона сидит на мокрой голой ветке на фоне свинцового неба", "reality_decay", "slow_in", (0.50, 0.42), None,
     "shot_016", (0.50, 0.25, 1.38), ["color"],
     "16:9 widescreen telephoto close-up of a single wet black hooded crow perched motionless on a bare black birch branch silhouetted starkly against a heavy leaden-grey sky, ruffled feathers in cold wind, shot on 85mm f/2.8 lens"),
    (75, 121.4, 122.6, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Про неё нам споёт вороньё»",
     "Десятки чёрных ворон срываются и взлетают над тёмным осенним лесом", "reality_decay", "tilt_up", (0.50, 0.46), "crows_drift",
     "shot_016", (0.50, 0.28, 1.22), ["color"],
     "16:9 widescreen dramatic documentary wide shot of dozens of black crows bursting upward in dark silhouettes from the bare black canopy of a late-autumn forest into a turbulent pale-grey sky, slight wing motion blur, shot on 35mm lens"),
    (76, 122.6, 124.0, "II КУПЛЕТ · РАЗЛОЖЕНИЕ РЕАЛЬНОСТИ", "«Про неё нам споёт вороньё»",
     "Высокий подъём над верхушками деревьев: за лесом бесконечный серый город", "reality_decay", "tilt_up", (0.50, 0.48), None,
     "city", (0.55, 0.42, 1.05), ["city"],
     "16:9 widescreen high aerial documentary shot rising just above dark bare autumn forest treetops in the foreground to reveal an endless sprawling grey panorama of post-Soviet concrete panel apartment blocks and smoking chimneys stretching to the horizon under a heavy grey sky, shot on 35mm lens"),

    # ==================== 5. ФИНАЛЬНЫЙ ПРИПЕВ И ФИНАЛ (2:04–2:38) ====================
    (77, 124.0, 126.6, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«И стонет в лапах бессилия»",
     "Широкая пустая городская площадь ранним утром: посреди неё стоит тот же хор", "colorless_predawn", "slow_in", (0.50, 0.50), None,
     "choir", (0.50, 0.48, 1.04), ["choir", "city"],
     "16:9 widescreen wide establishing documentary shot of a vast completely deserted concrete post-Soviet provincial town square at cold pre-dawn surrounded by grey apartment blocks and administrative buildings: standing right in the middle of the empty wet asphalt is the exact same choir of thirty ordinary women in coats and headscarves, no banners, no monuments with text, nearly monochrome cold light, shot on 28mm lens"),
    (78, 126.6, 129.0, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«И стонет в лапах бессилия»",
     "Крупные планы лиц женщин разного возраста на фоне серых домов", "colorless_predawn", "slow_in", (0.50, 0.42), None,
     "choir", (0.52, 0.44, 1.38), ["choir", "city"],
     "16:9 widescreen tight medium close-up of four women of different ages from the choir—an elderly grandmother, two middle-aged women and a young woman in plain wool headscarves and coats—singing solemnly in the empty grey city square with blurred panel buildings behind them, pale colorless pre-dawn light, shot on 50mm f/2 lens"),
    (79, 129.0, 131.5, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Пост-Россия: прости меня»",
     "Главный герой стоит один посреди площади лицом к поющему хору", "colorless_predawn", "slow_in", (0.50, 0.42), None,
     "hero", (0.50, 0.42, 1.12), ["hero", "city"],
     "16:9 widescreen medium shot of the exact same 35-year-old Russian man in his dark charcoal jacket and grey sweater standing motionless alone in the middle of the empty concrete city square at pre-dawn, looking quietly forward with exhausted eyes, pale colorless morning light, shot on 50mm f/2 lens"),
    (80, 131.5, 134.0, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Пост-Россия: прости меня»",
     "Камера за спиной главного героя: перед ним на пустой площади десятки женщин", "colorless_predawn", "slow_out", (0.50, 0.46), None,
     "choir", (0.50, 0.46, 1.10), ["hero", "choir", "city"],
     "16:9 widescreen iconic over-the-shoulder wide shot framed directly behind the dark-jacketed back and short-haired head of the 35-year-old man in the foreground: standing across the wet asphalt square facing him are the thirty women of the choir in coats and headscarves against grey panel buildings, pale monochrome pre-dawn light, shot on 35mm f/2.2 lens"),
    (81, 134.0, 136.4, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Так пахнет утро последнее»",
     "Абсолютно пустая городская улица в холодном бесцветном утреннем свете", "colorless_predawn", "pan_right", (0.50, 0.50), None,
     "city", (0.60, 0.50, 1.10), ["city"],
     "16:9 widescreen wide documentary photograph of a long straight provincial Russian avenue lined with grey concrete nine-story panel buildings, overhead trolleybus wires and bare trees completely devoid of cars or people in pale colorless pre-dawn light, wet asphalt reflecting the grey sky, shot on 35mm lens"),
    (82, 136.4, 139.0, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Так пахнет утро последнее»",
     "Фасад панельного дома: в окнах один за другим гаснет свет", "colorless_predawn", "static_live", (0.50, 0.48), "windows_extinguish",
     "city", (0.52, 0.46, 1.24), ["city"],
     "16:9 widescreen straight-on architectural documentary shot filling the frame with the weathered grey concrete grid facade of a nine-story Soviet panel apartment block at pre-dawn, half a dozen scattered apartments still glowing with dim warm yellow light among dozens of dark cold windows, shot on 50mm f/2.8 lens"),
    (83, 139.0, 141.6, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Предосеннее, предрасстрельное»",
     "Хор стоит неподвижно на площади, но вокруг него поднимается сильный ветер", "colorless_predawn", "static_live", (0.50, 0.46), "red_petals_wind",
     "choir", (0.50, 0.46, 1.14), ["choir", "city"],
     "16:9 widescreen medium-wide documentary shot of the women's choir standing rock-still on the empty city square while a sudden cold gust of wind whips the edges of their wool headscarves, coat hems and stray dry leaves across the wet pavement, nearly monochrome pale light, shot on 35mm lens"),
    (84, 141.6, 144.0, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Предосеннее, предрасстрельное»",
     "Искусственные красные цветы гонит ветер по серому асфальту пустой площади", "colorless_predawn", "pan_right", (0.50, 0.58), "red_petals_wind",
     "color", (0.45, 0.55, 1.12), ["color", "city"],
     "16:9 widescreen low-angle wide shot across a vast empty wet grey asphalt town square at pre-dawn as dozens of loose cheap artificial red plastic carnations tumble and skitter in the wind across the monochrome pavement, the muted red petals providing the sole trace of color, shot on 35mm f/2.2 lens"),
    (85, 144.0, 146.5, "ФИНАЛЬНЫЙ ПРИПЕВ · ХОР В ГОРОДЕ", "«Предосеннее, предрасстрельное»",
     "Крупный план лица главного героя: он медленно закрывает глаза", "colorless_predawn", "slow_in", (0.50, 0.42), None,
     "shot_005", (0.50, 0.42, 1.16), ["hero"],
     "16:9 widescreen intimate close-up portrait of the exact same 35-year-old tired Russian man outdoors in cold colorless pre-dawn light, his eyes gently closed in quiet acceptance and exhaustion, wind touching his short dark hair, natural skin texture, nearly monochrome grey-blue tones, shot on 50mm f/1.8 lens"),
    (86, 146.5, 149.2, "ФИНАЛ · ПОСЛЕДНЕЕ УТРО", "Финальные секунды · Холодное море",
     "Холодное свинцовое море ранним утром", "predawn_horizon", "slow_in", (0.50, 0.52), None,
     "choir", (0.50, 0.22, 1.35), ["color"],
     "16:9 widescreen minimalist cinematic seascape of a cold leaden-grey northern sea at early pre-dawn, slow dark ripples washing quietly onto wet dark pebbles and sand in the foreground under a vast pale-grey sky, nearly monochrome steel tones, shot on 35mm f/2.8 lens"),
    (87, 149.2, 152.0, "ФИНАЛ · ПОСЛЕДНЕЕ УТРО", "Финальные секунды · Берег",
     "Главный герой стоит один на берегу моря спиной к камере", "predawn_horizon", "slow_out", (0.50, 0.48), None,
     "hero", (0.50, 0.42, 1.06), ["hero"],
     "16:9 widescreen wide documentary shot from behind of the solitary 35-year-old man in his dark charcoal jacket standing motionless on a wet stony northern seashore facing the vast grey sea and low overcast horizon at pre-dawn, nearly monochrome palette, shot on 35mm f/2.4 lens"),
    (88, 152.0, 158.0, "ФИНАЛ · ПОСЛЕДНЕЕ УТРО", "Финал · Удержание 6 с без титров",
     "На самом горизонте над холодным морем проступает слабая тёплая полоска света", "predawn_horizon", "static_live", (0.50, 0.50), "horizon_dawn_line",
     "choir", (0.50, 0.20, 1.32), ["color"],
     "16:9 widescreen minimalist wide horizon seascape of calm cold grey sea meeting heavy overcast clouds at pre-dawn, along the distant horizon line glimmers a barely perceptible fragile thin band of pale warm amber-gold dawn light breaking through the monochrome greyness, no people, no text, shot on 50mm f/2.8 lens"),
]

RAW_BROLL = [
    (1, "Пустой вагон пригородной электрички", "dirty_modern", "slow_in", ["color"],
     "16:9 widescreen documentary shot looking down the aisle of a completely empty old Russian suburban elektrichka train car at dawn, worn blue-grey vinyl benches, flickering cold fluorescent tube lights, dark wet trees blurring past windows, shot on 35mm lens"),
    (2, "Старый подъезд с облупившейся краской", "reality_decay", "tilt_up", ["color"],
     "16:9 widescreen documentary shot inside a Soviet panel-apartment stairwell (podyezd) with peeling half-green half-white oil paint on concrete walls, dented metal mailboxes without numbers, dim yellow stairwell bulb, shot on 35mm lens"),
    (3, "Крупный план воды, стекающей по ржавой трубе", "dirty_modern", "static_live", ["color"],
     "16:9 widescreen macro close-up of cold rainwater streaming and dripping down a corroded rusty metal drainpipe bolted against a damp grey concrete panel wall, shallow depth of field, shot on 85mm lens"),
    (4, "Одинокая собака на автобусной остановке", "faded_memory", "static_live", ["shot_008"],
     "16:9 widescreen documentary shot of a solitary scruffy stray mutt dog sitting calmly on wet asphalt under an empty concrete provincial bus shelter in misty late-autumn morning, waiting quietly, shot on 50mm lens"),
    (5, "Женщина с продуктовой сумкой возле панельного дома", "dirty_modern", "pan_right", ["city"],
     "16:9 widescreen documentary medium-wide shot of an ordinary middle-aged Russian woman in a drab coat walking slowly past a wet grey concrete nine-story panel apartment building carrying a heavy plain cloth grocery bag, cold overcast morning, shot on 35mm lens"),
    (6, "Сломанный детский велосипед у мусорных контейнеров", "reality_decay", "slow_in", ["city", "color"],
     "16:9 widescreen documentary shot of a rusted broken child's tricycle with a bent wheel lying abandoned on wet asphalt beside green metal courtyard dumpsters and fallen brown leaves, grey panel block behind, shot on 50mm lens"),
    (7, "Дворник, метущий мокрые листья", "faded_memory", "pan_left", ["city"],
     "16:9 widescreen documentary wide shot of an elderly courtyard janitor in a dark padded work vest sweeping wet brown autumn leaves across rain-slicked courtyard asphalt with a birch-twig broom in cold morning mist, shot on 35mm lens"),
    (8, "Пустой школьный коридор", "colorless_predawn", "slow_in", ["color"],
     "16:9 widescreen symmetrical documentary shot of a long completely deserted provincial Russian school corridor with worn linoleum floor reflecting tall cold rainy windows along one side, quiet institutional stillness, no posters or text, shot on 35mm lens"),
    (9, "Мужчина, курящий у открытого окна кухни", "dirty_modern", "static_live", ["hero", "shot_004"],
     "16:9 widescreen nocturnal documentary medium close-up of the exact same 35-year-old man in his grey sweater leaning silently beside a cracked-open kitchen casement window at night holding a glowing cigarette, thin blue smoke drifting out into the cold dark courtyard, shot on 50mm f/1.8 lens"),
    (10, "Пластиковая икона на приборной панели автомобиля", "reality_decay", "slow_in", ["color"],
     "16:9 widescreen close-up inside an old Russian car looking at a small weathered plastic triptych icon glued onto the dusty grey dashboard, beyond the rain-streaked windshield stretches a blurred grey provincial road, shot on 50mm f/2 lens"),
    (11, "Старые гаражи под низким серым небом", "dirty_modern", "pan_right", ["city"],
     "16:9 widescreen wide documentary shot of endless rows of rusted corrugated metal and brick Soviet garages with muddy ruts and puddles under an oppressive low grey November sky, shot on 35mm lens"),
    (12, "Птицы на проводах над промышленной окраиной", "colorless_predawn", "static_live", ["city"],
     "16:9 widescreen telephoto documentary shot of dozens of black birds perched in a quiet row along sagging utility wires above concrete fences and distant smoking factory chimneys against a pale grey sky, shot on 85mm lens"),
]


def resolve_ref_path(key: str) -> str:
    if key in REFS:
        return REFS[key]
    if key.startswith("shot_"):
        return f"video_studio/post_rossiya/frames/{key}.jpg"
    return REFS["color"]


def get_main_shots() -> list[dict]:
    shots = []
    for (num, t0, t1, act, cue, desc_ru, color_state, move, focus, live_fx,
         fb_ref, fb_crop, refs_list, prompt_body) in RAW_SHOTS:
        shot_id = f"shot_{num:03d}"
        file_rel = f"video_studio/post_rossiya/frames/{shot_id}.jpg"
        exists = (FRAMES_DIR / f"{shot_id}.jpg").exists()
        shots.append({
            "num": num,
            "id": shot_id,
            "file": file_rel,
            "generated": exists,
            "t0": round(t0, 2),
            "t1": round(t1, 2),
            "duration": round(t1 - t0, 2),
            "act": act,
            "cue": cue,
            "desc_ru": desc_ru,
            "color_state": color_state,
            "move": move,
            "focus": list(focus),
            "live_fx": live_fx,
            "fallback_source": resolve_ref_path(fb_ref),
            "fallback_crop": list(fb_crop),
            "refs": [resolve_ref_path(r) for r in refs_list],
            "prompt": f"{prompt_body}, {STYLE_TAIL}",
        })
    return shots


def get_broll_shots() -> list[dict]:
    items = []
    for num, desc_ru, color_state, move, refs_list, prompt_body in RAW_BROLL:
        bid = f"broll_{num:02d}"
        file_rel = f"video_studio/post_rossiya/broll/{bid}.jpg"
        exists = (BROLL_DIR / f"{bid}.jpg").exists()
        items.append({
            "num": num,
            "id": bid,
            "file": file_rel,
            "generated": exists,
            "duration": 4.5,
            "desc_ru": desc_ru,
            "color_state": color_state,
            "move": move,
            "refs": [resolve_ref_path(r) for r in refs_list],
            "prompt": f"{prompt_body}, {STYLE_TAIL}",
        })
    return items


def export_manifests() -> None:
    out_dir = BASE_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    main_shots = get_main_shots()
    broll_shots = get_broll_shots()
    data = {
        "title": "ПОСТ-РОССИЯ",
        "subtitle": "Последнее утро, которое продолжается",
        "duration_seconds": 158.0,
        "resolution": [1920, 1080],
        "fps": 30,
        "audio": False,
        "refs": REFS,
        "progress": {
            "refs_done": sum(1 for p in REFS.values() if (BASE_DIR.parents[1] / p).exists()),
            "main_done": sum(1 for s in main_shots if s["generated"]),
            "main_total": len(main_shots),
            "broll_done": sum(1 for b in broll_shots if b["generated"]),
            "broll_total": len(broll_shots),
        },
        "shots": main_shots,
        "broll": broll_shots,
    }
    (out_dir / "prompts_100.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Export clean human-readable Markdown production bible
    lines = [
        "# «ПОСТ-РОССИЯ» — Полная карта 100 кадров и промптов",
        "",
        "Подзаголовок: **«Последнее утро, которое продолжается»**  ",
        "Формат мастера: **1920×1080 (16:9), 30 fps, H.264, без звука (`-an`), без титров и водяных знаков, 2:38 (158.0 с)**.",
        "",
        "## Четыре визуальных эталона (`refs/`)",
        "- `ref_01_hero.jpg` — Главный герой (мужчина 35 лет, тёмная куртка, серый свитер)",
        "- `ref_02_city.jpg` — Главная локация (постсоветский город поздней осенью, панельки, гаражи, трубы)",
        "- `ref_03_choir.jpg` — Народный женский хор (30 женщин разного возраста в обычных пальто и платках)",
        "- `ref_04_color.jpg` — Цветовой эталон (пластиковый цветок в решётке ливнёвки на мокром асфальте)",
        "",
        "## Основные 88 кадров (0:00 – 2:38)",
        "",
    ]
    for s in main_shots:
        mark = "✅ ГОТОВ" if s["generated"] else "⏳ В ОЧЕРЕДИ"
        m0, s0 = int(s["t0"] // 60), s["t0"] % 60
        m1, s1 = int(s["t1"] // 60), s["t1"] % 60
        lines.append(
            f"### Кадр {s['num']:02d} ({m0}:{s0:04.1f}–{m1}:{s1:04.1f}) [{mark}] — {s['desc_ru']}"
        )
        lines.append(f"- **Блок / строка:** {s['act']} · {s['cue']}")
        lines.append(f"- **Цвет / движение:** `{s['color_state']}` · `{s['move']}`" + (f" · FX `{s['live_fx']}`" if s["live_fx"] else ""))
        lines.append(f"- **Референсы:** `{', '.join(Path(r).name for r in s['refs'])}`")
        lines.append(f"- **Prompt:** `{s['prompt']}`")
        lines.append("")

    lines.append("## 12 дополнительных перебивок (`broll_01` – `broll_12`)")
    lines.append("")
    for b in broll_shots:
        mark = "✅ ГОТОВ" if b["generated"] else "⏳ В ОЧЕРЕДИ"
        lines.append(f"### Перебивка {b['num']:02d} [{mark}] — {b['desc_ru']}")
        lines.append(f"- **Цвет / движение:** `{b['color_state']}` · `{b['move']}`")
        lines.append(f"- **Prompt:** `{b['prompt']}`")
        lines.append("")

    (BASE_DIR / "STORYBOARD_PROMPTS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    export_manifests()
    shots = get_main_shots()
    done = sum(1 for s in shots if s["generated"])
    print(f"Exported manifests: {done}/{len(shots)} main shots currently generated on disk.")
