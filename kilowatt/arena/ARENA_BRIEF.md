# Задание Arena: арт для каталога «В ОКОПЕ» × НПО «Киловатт»

**Кому:** Arena Agent Mode, сессия с репозиторием `vladimirsorokin85-commits/-`.
**Срок/объём:** один прогон, **ровно 10 изображений**. Больше не генерировать.
**Куда:** папка `kilowatt/arena-art/` в твоей ветке `arena/<id>-repo`.
**Сдача:** ветка + **один PR** в `main` + отчёт `arena/mail/in/0002-arena.md`.

---

## 0. Контекст (читать до генерации)

Мы делаем самостоятельный каталог продукции **НПО «Киловатт»** (Липецк) —
станций радиоэлектронной борьбы «Капюшон», «Штора», комплекса «Ребус-4»,
детектора «Сигнал-М2», рюкзаков ТП и аксессуаров. Бренд каталога — **«В ОКОПЕ»**.
Аудитория B2B: предприятия, склады, охрана, инфраструктура, силовые структуры.

Изображения — **только арт-подложки для вёрстки** (обложка, hero, текстуры).
Весь текст, цифры и логотипы накладываются потом в HTML/CSS. **На картинках
не должно быть ни одной буквы, цифры или логотипа** — модели их портят.

## 1. Закон жанра: анти-слоп (обязательно к исполнению)

Из манифеста арт-директора (полная версия — у владельца; здесь рабочая выжимка):

- Сначала идея, потом картинка. Каждый концепт обязан продолжать фразу:
  «Запоминающаяся идея этого листа — ______». Если в пропуск просится шрифт,
  цвет, крупный номер или «минимализм» — это не идея, придумывай заново.
- Генерик убивается тестом: если заменить НПО «Киловатт» на банк, а дрон на
  что угодно — композиция работает? значит шаблон, брак.
- Визуальная школа: печатный плакат, шелкография/ризограф, ограниченная
  палитра (2–3 цвета), видимая печатная фактура (зерно бумаги, краска, лёгкая
  неприводка), крупные графичные формы. Не «стерильное 3D», не «сток».
- Пустота дорогая. Один смысл на лист. Продукт/техника — герой, а не декор.

**Запрещено категорически:** чёрный фон с золотом; «люкс-приглашение»; сине-
фиолетовые градиенты, неон, свечение, частицы, стекломорфизм; фейковые
дашборды и «висящие» UI-карточки; дешёвый 3D-глянец; десять инфоблоков со
значками; всё по центру и симметрично по умолчанию; текст в плашках поверх
фото; фонтанчики, конфетти, сток-фото людей; оружие в кадре, кровь, реальные
люди, символика и шевроны. Изображения **без текста** — это закон для этого
прогона.

## 2. Три концепта

### A. «ПОЛЕ» — купол как единственная чистая точка на карте помех
Механизм: инверсия масштаба + негативное пространство. Топографическая карта
(тонкие коричнево-оливковые горизонтали) покрыта плотной штриховкой «помех»;
в центре — круг «чистой зоны», где штриховка обрывается и остаётся пустая
бумага; из центра расходятся дуги радиоволн. Никаких подписей и отметок.
Палитра: олива `#4A5A3C`, графит `#1B1E19`, кислотный лайм `#CBFF00`
(акцент — только дуги/одна линия), бумага `#E8E2D2`.
Техника: 2-красочная шелкография, зерно бумаги, лёгкая неприводка.

### B. «ЧЕРТЁЖ» — изделие как паспортный лист
Механизм: продукт говорит сам / экстремальный кроп инженерного чертежа.
Тёплая бумага, графитовые линии: ортогональные проекции купольной станции
(вид спереди + вид сверху), размерные линии, выносные линии, сечение; тонкий
конус защиты, отмеченный единственным акцентным цветом. Никакого 3D-рендера,
только чертёжная графика. Пустое поле сверху слева — под типографику.
Палитра: бумага `#F2EDE3`, графит `#26261F`, акцент оксидный `#C6431E`.
Техника: ризограф-дуотон, лёгкий сдвиг красок, бумажное зерно.

### C. «СПЕКТР» — защита как тишина в спектре
Механизм: сообщение, изображённое буквально. Частотный спектр — плотные
вертикальные штрихи разной высоты по горизонтали; в середине полоса, где
штрихи обрываются — «тишина» (чистая бумага), и одна кислотная полоса
фиксирует эту зону. Сверху/снизу — много пустой бумаги под текст.
Палитра: бумага `#F4F0E8`, графит `#232420`, кислотный лайм `#CBFF00`.
Техника: плакатная печать, зерно, лёгкая неприводка.

## 3. Список файлов (ровно 10)

Формат PNG, sRGB. Имена — точно такие:

| № | Файл | Размер | Что |
|---|---|---|---|
| 1 | `kilowatt/arena-art/A4-01-pole.png` | 2480×3508 | Концепт A на A4 вертикально: круг чистой зоны в нижних 2/3, верхняя треть пустая под текст |
| 2 | `kilowatt/arena-art/A4-02-chertezh.png` | 2480×3508 | Концепт B на A4 вертикально: чертёж станции в нижних 2/3, верх пустой тёплый |
| 3 | `kilowatt/arena-art/A4-03-spektr.png` | 2480×3508 | Концепт C на A4 вертикально: спектр-тишина на 55–65% высоты, крупные пустые поля |
| 4 | `kilowatt/arena-art/web-01-pole-2400x1350.png` | 2400×1350 | Концепт A, 16:9: круг справа, левые 40% пустые под заголовок |
| 5 | `kilowatt/arena-art/web-02-chertezh-2400x1350.png` | 2400×1350 | Концепт B, 16:9: чертёж слева, правая треть — пустая тёплая бумага |
| 6 | `kilowatt/arena-art/web-03-spektr-2400x1350.png` | 2400×1350 | Концепт C, 16:9: спектр полосой внизу 30%, верх пустой |
| 7 | `kilowatt/arena-art/tex-01-paper.png` | 2000×2000 | Бесшовная (насколько выйдет) текстура тёплой бумаги: зерно, мелкие вкрапления, без рисунка |
| 8 | `kilowatt/arena-art/tex-02-olive.png` | 2000×2000 | Бесшовная текстура оливковой шелкографии: мелкий растр/сетка, без сюжета |
| 9 | `kilowatt/arena-art/tex-03-blueprint.png` | 2000×2000 | Бесшовная текстура чертёжной сетки на тёплой бумаге, очень деликатная |
| 10 | `kilowatt/arena-art/og-1200x630.png` | 1200×630 | Соц-обложка: круг чистой зоны + спектр-тишина, графит/олива/лайм, без текста |

## 4. Промпты (использовать дословно, каждый — отдельная генерация)

**A4-01-pole:**
"Vertical poster background, A4 portrait 2480x3508, no text, no letters, no numbers, no logos. Screen-printed top-down topographic map in olive and graphite on warm off-white paper; dense interference hatching covers the map; in the lower two-thirds a clean circular clearing where hatching stops and bare paper shows; thin acid-lime radio-wave arcs radiate from its center; upper third almost completely empty warm paper for later typography; visible paper grain, slight ink misregistration, two-ink silkscreen print, flat graphic, no gradients, no glow, no 3D."

**A4-02-chertezh:**
"Vertical poster background, A4 portrait 2480x3508, no text, no letters, no numbers, no logos, no labels. Risograph duotone technical drawing on warm paper: orthographic front and top views of a dome-shaped antenna station, dimension lines and leader lines as delicate graphite linework, a thin protection cone marked with a single oxide-red accent; drawing occupies the lower two-thirds, top-left area left as empty warm paper; paper grain, slight ink offset misregistration, flat print, no 3D render, no gloss, no gradients."

**A4-03-spektr:**
"Vertical poster background, A4 portrait 2480x3508, no text, no letters, no numbers, no logos. Flat screen-printed radio spectrum: dense vertical graphite strokes of varying heights along a horizontal band at 55-65% height; in the middle the strokes break into a clean silence of bare warm paper, marked by one acid-lime vertical strip; large empty warm-paper fields above and below; visible ink grain, slight misregistration, two-ink print, no glow, no gradients, no 3D."

**web-01-pole:**
"Wide hero background 2400x1350, no text, no letters, no logos. Top-down topographic field in olive and graphite screenprint; a clean circular clearing with bare paper in the right half, acid-lime radio-wave arcs from its center; the left 40% almost empty for headline; paper grain, silkscreen misregistration, flat graphic, no glow, no gradients."

**web-02-chertezh:**
"Wide hero background 2400x1350, no text, no letters, no logos. Risograph duotone technical drawing on warm paper: orthographic dome-station drawing with dimension and leader lines on the left half, one oxide-red protection-cone accent; right third empty warm paper for headline; paper grain, slight misregistration, flat print, no 3D, no gradients."

**web-03-spektr:**
"Wide hero background 2400x1350, no text, no letters, no logos. Flat screen-printed radio spectrum as a bottom band 30% of height: vertical graphite strokes with a silence gap in the middle marked by one acid-lime strip; the top 70% empty warm paper for typography; ink grain, slight misregistration, no glow, no gradients."

**tex-01-paper:**
"Seamless texture tile 2000x2000, no text, no objects. Warm off-white paper grain, subtle fiber and tiny ink speckles, very low contrast, even lighting, flat scan-like appearance, no vignette, no pattern, no gradient."

**tex-02-olive:**
"Seamless texture tile 2000x2000, no text, no objects. Olive-green silkscreen print texture: fine halftone mesh, subtle ink unevenness and tiny misregistration dots, very low contrast, flat scan-like appearance, no pattern, no gradient."

**tex-03-blueprint:**
"Seamless texture tile 2000x2000, no text, no objects. Very delicate graphite technical grid on warm paper: thin regular lines, small crosshair ticks, low contrast, flat scan-like appearance, tileable, no gradient."

**og-1200x630:**
"Social share background 1200x630, no text, no letters, no logos. Graphic composition: a clean circular clearing of bare warm paper in an olive/graphite interference field on the left, a radio-spectrum band with a silent gap and one acid-lime strip on the right; flat screenprint texture, two inks, paper grain, no glow, no gradients, no 3D, no people."

## 5. Приёмка и сдача

1. Проверь каждый файл: размеры точные, PNG, без текста/логотипов/людей,
   нет свечения и градиентов, фактура читается. Битые/пустые — перегенерируй
   один раз с уточнённым промптом (не меняй композицию концепта).
2. Если модель отказывается или выдаёт «3D-сток» — перегенерируй с усилением
   «flat screenprint, paper grain, two-ink print, no 3D».
3. Каждый файл ≤ 8 МБ, общий вес ≤ 40 МБ. Не коммить видео и мусор.
4. `kilowatt/arena-art/MANIFEST.md`: таблица файл → промпт (кратко) → что
   получилось → ок/переделано.
5. Отчёт `arena/mail/in/0002-arena.md`: что сделано, что не вышло, где файлы,
   ссылка на PR.
6. Ветка `arena/<id>-repo` → **один PR** в `main`. Другие файлы репозитория
   не трогать. В `main` напрямую не пушить.
