# PROMPT GUIDE — «В Окопе» (AI-кадры, обложки, текст)

Источники: cliprise/awesome-ai-image-generator-prompts, cliprise/awesome-ai-thumbnail-prompts,
horushe93 realism gist (свет = главный фактор реализма) + наш опыт («Окопная смекалка», обложки — «кайф»).

## 1. Формула кадра (8 слотов, строго по порядку)

```
[SUBJECT]  in [ENVIRONMENT], [COMPOSITION], [LIGHTING], [STYLE], [CAMERA], [MOOD], [QUALITY], [RESTRICTIONS]
```

| Слот | Что писать | Пример |
|---|---|---|
| SUBJECT | кто, что делает, ОДНО действие, предмет в руках | `a modern Russian soldier in EMR digital camo (Tsifra) and 6B47 helmet, holding an AK-74M, fixing a car-mirror periscope to a trench wall` |
| ENVIRONMENT | место + сезон + погода + фактура | `inside a muddy modern trench lined with wooden boards and sandbags, late autumn, drizzle` |
| COMPOSITION | план, позиция субъекта, место под текст | `medium shot, subject on the right third, empty dark area on the left for title text` |
| LIGHTING | **самое важное** — источник, направление, цвет | `overcast soft daylight, cold rim light from behind, warm lantern fill from below` |
| STYLE | жанр | `cinematic documentary war photography, gritty realism` |
| CAMERA | объектив/плёнка | `shot on Sony A7S III, 35mm f/1.8, shallow depth of field, Kodak Vision3 500T grain` |
| MOOD | эмоция | `tense, focused, quiet before the storm` |
| QUALITY | детализация | `highly detailed fabric and mud textures, sharp eyes, 8k` |
| RESTRICTIONS | что запрещено | `no text, no logos, no patches, no flags, no WWII gear, no distorted hands, no extra fingers` |

### Камера / объективы — шпаргалка
| Задача | Ключ |
|---|---|
| эпичный общий план | `24mm wide angle, low angle, deep focus` |
| «документалка» | `35mm, handheld, slight motion blur` |
| портрет / эмоция | `85mm f/1.4, bokeh, catchlight in eyes` |
| деталь (лайфхак крупно) | `100mm macro, extreme close-up of hands and object` |
| дрон | `aerial top-down drone shot, 4k` |
| ночь | `night vision green tint` / `thermal ironbow palette` / `moonlight + red flashlight` |

### Свет (горячие формулы)
- `golden hour backlight, long shadows, dust in the air` — героика
- `overcast flat light, desaturated` — окопная правда
- `single warm candle / trench-candle light in a dark dugout, deep shadows` — блиндаж
- `explosion glow on the horizon, orange rim light on helmet` — драма
- `cold blue moonlight, red headlamp beam` — ночь

## 2. Чек-лист аутентичности (ВСЕГДА в промпте)
- ✅ `modern Russian soldier`, `EMR digital camouflage (Tsifra)`, `6B47 helmet`, `AK-74M` / `AK-12`, `plate carrier`, `Ratnik gear`
- ❌ `no WWI/WWII uniforms, no Mosin, no PPSh, no ushanka with star, no foreign patches, no flags, no insignia, no text on clothing`
- Лица: `realistic adult face, no distortions`; руки: `anatomically correct hands, five fingers`

## 3. Обложка (thumbnail) — рабочий рецепт
1. Сгенерировать **фон без текста** по формуле §1 (`empty area for text`).
2. Второй проход — передать фон как reference и добавить текст:
```
Add premium aggressive typography: condensed heavy display lettering, metallic gold-orange gradient,
chunky 3D bevel, thick black outline, outer glow, subtle grunge.
Text line 1 (top-left, huge): "ЧУЛОК ПРОТИВ"   Text line 2 (below, red): "СНАЙПЕРА"
Label (yellow tape, bottom-right): "0 ₽"
Exact Cyrillic spelling. No other text, no patches, no flags, no watermarks.
```
3. Проверить орфографию глазами (Ё, Й, ₽, №). Если ошибка — повтор с фразой `exact spelling: ...`.
4. Правила обложки (cliprise): 2–5 слов, 1 лицо с эмоцией, контраст ≥ 3 цветов, нет мелкого текста, нет мусора.

## 4. Видео-кадры для ролика
- 30+ уникальных сцен, смена визуала каждые 3–5 с.
- Для каждой главы: 1 «establishing» (общий) + 2–3 «деталь» (macro лайфхак) + 1 «эмоция» (портрет).
- Вертикаль 9:16 лучше генерировать сразу вертикальной; иначе `smartcrop.vertical()`.

## 5. Текст поверх видео (если не AI)
`typo.py` пресеты: `gold` (заголовок), `chrome`, `fire` (удар), `blood` (опасность), `stencil` (армейская маркировка),
`steel`, `hud` (дрон/прицел), `caption` / `caption_hot` (субтитры 2–4 слова, караоке),
`soviet`, `spray`, `marker`, `glitch`, `tape()` — рваный скотч-лейбл («0 ₽», «БЛИК»).
Шрифты: Russo One, Dela Gothic One, Unbounded, Oswald, Montserrat, Tektur, Rubik Mono, Seymour One … (26 OFL).
