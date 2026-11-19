# Мультфильм «В своём ритме» — новый монтаж

30 секунд рисованной анимации. Детектор замечает неизвестный дрон на подлёте, и на объекте звучит короткий сигнал. Вместо сцены с телефоном — звуковой акцент и восемь коротких планов цеха. Заводской кот и финальная карточка сохранены.

Озвучка перезаписана голосом, выбранным на прослушивании `ru-RU`. Музыка — [Storm Riders Unleashed от StockTune](https://stocktune.com/free-music/storm-riders-unleashed-59750-53368), [MP3 владельца](../../StockTune-Storm%20Riders%20Unleashed_1794986419.mp3) из корня репозитория. Использован 30-секундный фрагмент с 0:55,154; склейки привязаны к быстрым ударным акцентам (~174 в минуту по записи). Сборка не генерирует музыку. Прежняя песня с вокалом не используется. Эффекты — из [`toolkit/sfx`](../toolkit/sfx/LICENSE.txt).

## Видео и контакты

- **«Инкубатор 3.30»** — [вертикальный MP4](./v_okope_incubator_330.mp4), [кадры и сборка](./incubator/README.md), [текст и заголовок](./incubator/publish.txt). Плеер `/incubator-330/`.
- **RunCam Helmet Camera 2** — [вертикальный MP4](./v_okope_runcam_helmet_camera_2.mp4), [источники и сборка](./runcam/README.md), [текст для публикации](./runcam/publish.txt). Плеер `/runcam-helmet-2/`.
- **GONGTEX Reversible Jacket** — [вертикальный MP4](./v_okope_gongtex_reversible_jacket.mp4), [описание и сборка](./gongtex/README.md), [текст для публикации](./gongtex/publish.txt). Плеер `/gongtex-reversible/`.
- **«Электростанции в наличии»** — [минутный MP4](./v_okope_elektrostancii_v_nalichii.mp4), [22 позиции без цен](./power-stations/catalogue.txt) и [раскадровка](./power-stations/README.md). Плеер `/power-stations/`.
- **«Стриж» — визуальный обзор** — [минутный MP4](./v_okope_strizh_obzor.mp4) из трёх фото с рисованными перебивками, [описание и сборка](./strizh/README.md). Плеер `/strizh/`.
- **«XMETIX TAK710» — новый монтаж под DnB** — [MP4](./v_okope_xmetix_tak710.mp4), [описание](./tak710/README.md) и [тексты для Shorts и ВК](./tak710/publish.txt). Отдельный плеер `/tak710/`.
- **«Булат v4 · дрон-детектор»** — [MP4](./v_okope_bulat_v4_detektor.mp4) и [описание](./bulat/README.md). Плеер `/bulat/`.
- **Сценарий №2 «Game Over для дрона»** — [MP4](./v_okope_game_over.mp4) и [описание](./game/README.md). Отдельный плеер `/game-over/`.
- **[Готовый MP4 — новый монтаж](./v_okope_v_svoem_ritme_montazh.mp4)** — 30 секунд, 1080 × 1920, 30 кадров/с.
- Ранние версии: [«В своём ритме»](./v_okope_v_svoem_ritme.mp4), [«Знать вовремя»](./v_okope_znat_vovremya.mp4) и [«Дрон над объектом»](./v_okope_dron_nad_obektom.mp4).
- [Telegram](https://t.me/vokope_ru) · [ВКонтакте](https://vk.com/vokope_rus) · [Авито](https://www.avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241). Ссылки доступны под плеером и в виде QR-кодов на финальной заставке.

Архив: [«Дрон над объектом: памятка»](./site-safety/README.md) — отдельный ранний ролик, не обзор «Стрижа».

## Собрать заново

Нужны Node.js 20+ и Python 3 с NumPy для проверки музыкального фрагмента. Системный FFmpeg с `libx264` используется, если он есть; иначе сборка использует бинарник из опциональной зависимости npm. Свой бинарник можно указать через `FFMPEG_BIN`, интерпретатор Python — через `PYTHON`.

```sh
cd video_studio/drone_cartoon
npm ci
npm test
npm run render
npm run preview
```

Плеер открывается на `http://localhost:8000` (порт можно изменить через `PORT`). Он использует свежий рендер или доставочный MP4 из репозитория. Экспорт сохраняет `output/v-svoem-ritme-montazh.mp4`, JPEG обложки и звуковой мастер. Для прогона 540 × 960 используйте `npm run render -- --draft`. Промежуточные файлы `output/` не входят в Git.

| Начало | Сцена |
| --- | --- |
| 0:00 | Дрон на подлёте. |
| 0:04,1 | Детектор замечает дрон. Короткий звуковой сигнал. |
| 0:08,3 | Восемь планов: цех, лента, упаковка, проверка, склад. |
| 0:19,3 | «Даже заводской кот ничего не заметил. У него по расписанию обед». |
| 0:24,8 | Не будь мишенью. Будь «В окопе»! — магазин и три QR-кода. |

Монтажные точки и реплики — в `story.mjs`; рисунки — в `film.mjs`; звук — в `vo/` и `mix.mjs`; экспорт — в `render.mjs`.
