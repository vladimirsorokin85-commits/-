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

## 6. Пакет промпта (по навыку ai-drawing-prompt, leeyuyun/agent_skills)
Для каждого кадра или обложки держать один блок, а не одну строку:
1. **Primary prompt**: формула из §1, одно действие, один фокус.
2. **Параметры генератора**: размер — ближайший из доступных (например 1024x1536 или 1536x1024), затем точная подрезка до 1080x1920 или 1920x1080 (см. §7).
3. **Запреты**: в тексте промпта («no text, no logos…»). Отдельного поля для негативного промпта у генератора нет.
4. **Референс** (для текста на обложке, правок кадра): два списка.
   - `Сохранить`: композиция, лицо, палитра, положение предметов.
   - `Изменить`: только один параметр (текст, свет, одежда, фон).
   Короткие фразы, без противоречий.
5. **Варианты**: минимум 3 с контролируемой разницей: например план, свет, сила правки (низкая / средняя / высокая).
6. **Итерации**: 3 раунда, один параметр за раз.

Карта «проблема → правка»:
| Проблема | Правка |
|---|---|
| не тот предмет или лицо «уплыло» | переставить главное существительное в начало, убрать лишние стили |
| кадр не того плана | явно указать план (close-up / medium / wide) и место объекта слева/справа |
| стиль не тот | заменить «красиво» на носитель + эпоху + фактуру (например «35mm документальная плёнка, влажная земля») |
| артефакты, руки, лица | «anatomically correct hands, five fingers», «realistic adult face», детализация фактуры |
| текст искажён | текст отдельным проходом (§3), точная строка в кавычках, «exact spelling» |

## 7. Размеры и подрезка
- Генератор выдаёт ближайшие пропорции (например 1536x1024 или 1024x1536). Обложки и кадры финально приводим к **1920x1080** (16:9) и **1080x1920** (9:16) с подрезкой или растяжением минимальным, не больше 1%. Проверять по размеру файла.
- Запреты пишем позитивно, если модель их плохо держит: «no blur» → «sharp focus and crisp edges», «no clutter» → «minimal clean background».
