# ПОЛИТИКА ПО МУЗЫКЕ — ЖЁСТКОЕ ПРАВИЛО

## Запрещено навсегда
Любая **сгенерированная / процедурная музыка**: numpy/scipy-синтез, «drum&bass на скрипте»,
секвенсоры, любые файлы вида `music_catalog/*_174.ogg`, `music_dnb.py` и их производные.

Такие треки удалены из репозитория окончательно:
- `video_studio/music_catalog/dnb_neuro_174.ogg` — сгенерирован скриптом
- `video_studio/music_catalog/jungle_hoover_174.ogg` — сгенерирован скриптом
- `video_studio/v4/music_dnb.py` — сам генератор удалён

## Разрешено
Только реальные скачанные мастера из `video_studio/music_downloaded/`:
`fvi-BeatOne.ogg`, `fvi-Arpent.ogg`, `fvi-Chronos.ogg`, `fvi-Favorite.ogg`,
`fvi-Fireworks.ogg`, `fvi-Goodnightmare.ogg`, `fvi-3amWestEnd.ogg`, `warfork_arpent.ogg`.

## Правило для скриптов
Путь к музыке обязан содержать `/music_downloaded/`, иначе сборка падает с ошибкой.
