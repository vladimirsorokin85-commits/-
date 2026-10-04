# toolkit — «прокачка» студии «В Окопе»

| Модуль | Что делает | Основа (GitHub) |
|---|---|---|
| `typo.py` | Типографика уровня After Effects: градиенты, 3D-фаска со светом, экструзия, N обводок, свечение, тени, гранж, трафарет, скотч-лейбл, глитч; 13 пресетов; авто-подмена недостающих глифов (₽) | google/fonts (OFL) |
| `fonts/` | 26 профессиональных шрифтов с кириллицей (Russo One, Dela Gothic, Unbounded, Oswald, Tektur, Rubik Mono …) | google/fonts |
| `grade.py` | Киноцвет: настоящие .cube LUT плёнок (Kodak 2383, Fuji 3513, Portra, Tri-X), teal&orange, ореолы, зерно, виньетка; пресеты `frontline / night_ops / thermal / archive` | YahiaAngelo/Film-Luts |
| `audio_fx.py` | Голос «как на радио»: пословное выравнивание громкости, EQ присутствия, 2 компрессора, де-эссер, лимитер (Spotify pedalboard); сетка битов (librosa, с подсказкой 174 BPM для DnB), плавный дакинг без «качелей», мастер −14 LUFS | spotify/pedalboard, librosa |
| `smartcrop.py` | 16:9 → 9:16: лицо / фигура / заметность; если не уверен — безопасный режим с размытым фоном | opencv |
| `sfx/` | 18 CC0 звуков монтажа: whoosh, impact, riser, boom, tick, gong, typing … | RezaParsian/free-sfx-bgm-pack |
| `PROMPT_GUIDE.md` | Формула промптов, свет/камера, чек-лист аутентичности, рецепт обложек | cliprise, horushe93 |

Образцы: `specimen_fonts.jpg`, `specimen_effects.jpg`, `specimen_grade.jpg` (`python3 specimen.py`).

Уровни SFX: whoosh за 3–5 кадров до склейки −8 dB · tick −14 dB · impact −8 dB · riser стартует за 2.6 с до кульминации.
