# _render — пайплайн рендера пакета «Два горизонта»

Всё, что превращает HTML-постеры из `02_МАКЕТЫ/posters/` в готовые файлы
`05_ГОТОВОЕ/`. Скрипты не правят макеты: при поломке постера — сообщение Lead
с точным путём и скриншотом.

## Быстрый старт

```powershell
# полный прогон: рендер актуальных PNG → превью → контактный лист → галерея → PDF → чек-лист
powershell -NoProfile -ExecutionPolicy Bypass -File infographics\_render\run_all.ps1

# один постер (1× и 2×)
& $py infographics\_render\render_posters.py P01
& $py infographics\_render\render_posters.py P01_dva_gorizonta.html   # можно путём

# ПРОМЕЖУТОЧНЫЙ рендер новых постеров — только в тестовую папку, не в 05_ГОТОВОЕ:
& $py infographics\_render\render_posters.py --all --out infographics\_render\_qa\preview_render

# только широкие/истории
& $py infographics\_render\render_posters.py --kind wide --all
& $py infographics\_render\render_posters.py --kind story --all

# PDF отдельно (после всех постеров, после сигнала Lead «posters locked»)
powershell -NoProfile -ExecutionPolicy Bypass -File infographics\_render\build_pdf.ps1
```

Python с Pillow/pypdf (тот же runtime):
`C:\Users\TitanPC\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`

## Процесс (важно)

- Пока Lead не дал сигнал **«posters locked»**, постеры — черновые: рендерим их
  в `_render/_qa/preview_render/` и сообщаем Lead о проблемах. `05_ГОТОВОЕ`
  заполняется финальными рендерами после сигнала; старые промежуточные файлы
  перезаписываются, дата/время рендера каждого файла — в `ЧЕК_ЛИСТ_ФАЙЛОВ.md`.
- Постеры не правим: при поломке — сообщение Lead с путём постера и проблемного PNG.


## Скрипты

| Файл | Что делает |
|---|---|
| `posterlib.py` | общие пути, порядок постеров, форматы, имена, утилиты |
| `render_posters.py` | рендер HTML → PNG: Chrome CDP (1×/2×, wide 1920×1080, story 1080×1920), проверка фактических размеров, битых фото и переполнений; таблица OK/WARN/FAIL, JSON-отчёт |
| `verify_pdf.py` | проверка PDF: число страниц, A4, вшитые шрифты, непустые страницы |
| `pdf_preview.py` | открывает PDF в headless Chrome-viewer и снимает стр. 1 и последнюю — подтверждение, что PDF открывается |
| `build_pdf.ps1` | генерирует `print.html` (обложка-титул из P01 + постеры в порядке альбома + финальная CTA-страница), печатает в PDF, проверяет |
| `gallery.py` | `05_ГОТОВОЕ/gallery/index.html` — офлайн-галерея с подписями, клик → PNG |
| `make_previews.py` | JPG-превью (ширина 1080, q88) в `05_ГОТОВОЕ/превью/` |
| `make_tg_previews.py` | 3 лучших превью для Telegram владельца (P01, P02, P07) в `05_ГОТОВОЕ/превью_ТГ/` |
| `contact_sheet.py` | контактный лист всех PNG в `_render/_qa/contact_sheet.jpg` для QA |
| `check_files.py` | приёмка: пишет `05_ГОТОВОЕ/ЧЕК_ЛИСТ_ФАЙЛОВ.md` и `_render/_qa/files_report.json` |
| `run_all.ps1` | последовательный прогон всего пайплайна |

## Форматы и имена (бриф §5)

| Серия | HTML | Выход PNG |
|---|---|---|
| основная | `posters/P01_…html` | `P01_dva_gorizonta.png` (1080×1350) + `…@2x.png` (2160×2700) |
| широкая | `posters/wide/P01_…_1920.html` | `P01_dva_gorizonta_1920.png` (1920×1080) |
| история | `posters/story/P01_…_1080x1920.html` | `P01_dva_gorizonta_1080x1920.png` (1080×1920) |

PNG без альфа-канала (sRGB), фон — бумага/олива. Всё складывается в
`05_ГОТОВОЕ/png/`, JPG-превью — в `05_ГОТОВОЕ/превью/`.

## Диагностика рендера

`render_posters.py` (движок CDP) до скриншота проверяет страницу в браузере:

- **FAIL**: битые `<img>` (`naturalWidth=0`); документ шире/выше кадра
  (контент не влез — на PNG была бы обрезка); текст, вылезший за границу кадра;
  ошибки загрузки шрифтов; неверный размер/вес PNG (< 50 КБ);
- **WARN**: `overflow:hidden` с обрезанным содержимым (может быть намеренный кроп
  фото), наложение текстовых блоков (пересечение >35% площади — часто признак
  наехавшего футера/подписей), шрифты не в состоянии `loaded`, CLI-движок без диагностики.

Отчёт: `_render/_qa/render_report.json`. Если постер сломан — Lead получает
сообщение с путём постера и путём проблемного PNG/скриншота; макет не правим.

Резервный движок без диагностики:
`& $py render_posters.py P01 --engine cli` (Chrome `--screenshot` +
`--force-device-scale-factor`).

## PDF-альбом

`build_pdf.ps1` собирает 12 страниц: обложка-титул (из P01) → P01 → P05 → P06 →
P04 → P03 → P02 → P08 → P07 → P09 → P10 (порядок брифа §4) → финальная страница
с CTA. `@page A4 portrait; margin:0`, каждый постер вписан в 194×280,8 мм
(поля 8 мм) без обрезки, по центру. Шрифты обложки/финала — локальные OFL из
`kilowatt/design/fonts` (в PDF уходят либо встроенными, либо Type3-контурами,
т.е. без подмены на системные). PDF: `05_ГОТОВОЕ/pdf/Инфографика_Два_горизонта_2026.pdf`.

Параметры: `-Scale auto|1|2` (auto — @2x, если есть, иначе 1×), `-AllowPartial`
(собрать из того, что готово), `-SkipPdfShot`, `-OutPdf`, `-PngDir`.

## Тестовый прогон в песочнице

Скрипты уважают переменную `INF_ROOT` (корень пакета). Так можно прогнать
галерею/превью/чек-лист на тестовых файлах, не засоряя `05_ГОТОВОЕ`:

```powershell
$env:INF_ROOT = "D:\...\infographics\_render\_qa\_sandbox"
& $py gallery.py; & $py make_previews.py; & $py check_files.py
```

## Ограничения

- PDF-вьюер в headless Chrome доступен, но скриншоты `pdf_preview.py` включают
  интерфейс вьюера — это проверка «PDF открывается», а не финальный макет.
- Шрифты переменные (Sofia/Oswald/Tektur): Chrome может отдавать их в PDF как
  Type3-контуры. Визуально корректно, но текстовый поиск по PDF ограничен.
- Рендер идёт по HTML-странице, а не по её внутренним размерам: если дизайнер
  сделал холст не 1080×1350, `render_posters.py` сообщит FAIL с фактическими
  размерами — это сигнал Lead/дизайнеру, а не повод менять размер кадра.
