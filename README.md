# «В ОКОПЕ» — рабочий репозиторий магазина

Здесь живут инструменты магазина брони «В ОКОПЕ»: умный поиск и рекомендации по каталогу
поставщика, готовые карточки для пересылки клиенту, бланки заказов и посты для ВК.
Плюс — студия вертикальных Reels для видео.

**Главный файл контекста — [`docs/KNOWLEDGE_BASE.md`](docs/KNOWLEDGE_BASE.md): правила, поставщики, цены.**
Читать первым. Как устроена работа с каталогом — [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Что уже есть

| Блок | Файлы | Что делает |
|---|---|---|
| Каталог и наличие | [`catalog/`](catalog/README.md) | снапшот каталога Димы, умный поиск (синонимы, опечатки, размеры, бюджеты), электростанции |
| Карточки и бланки | `media/blank/` | «полевой бланк»: карточка товара, карточка из каталога одной командой, бланк заказа |
| Посты для ВК | [`vk/`](vk/README.md) | текст поста из данных поставщика + подборка фото под загрузку в ВК |
| Стиль и правила постов | [`docs/VK_STYLE.md`](docs/VK_STYLE.md) | каркас поста, тон, хештеги |
| Видео | [`video_studio/`](video_studio/reels/README.md) | вертикальные Reels 9:16 от 1 до 20 минут |

## Быстрый старт

```bash
bash tools/bootstrap.sh                      # один раз: Pillow в vendor/
bash tools/catalog_pull.sh                   # забрать свежий снапшот каталога и фото

python3 -m catalog.search "бронежилет в пикселе до 85к"     # умный поиск
python3 media/blank/from_catalog.py --code 00895 --price 24900   # карточка для клиента
python3 -m vk.post --query "ботинки прабос greyman" --price 24900 # пост для ВК
```

## Как обновляются данные

GitHub Actions «Catalog fetch» тянет каталог МойСклад и фото поставщика в ветку `catalog-data`,
оттуда их забирает `tools/catalog_pull.sh`. Запускается сам при правке `catalog/requests/**`
(например, когда нужно добавить товары в заявку на фото). Подробнее — [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Видеостудия (Reels)

Для сборки вертикальных роликов 9:16 длительностью **от 1 до 20 минут** — пакет
[`video_studio/reels`](video_studio/reels/README.md). Нужны `ffmpeg` и `ffprobe` в `PATH`:

```bash
python3 -m video_studio.reels video_studio/reels/project.example.json --dry-run
python3 -m video_studio.reels video_studio/reels/project.example.json
```

Детали по визуалам, музыке, субтитрам и экспорту — в README пакета.
