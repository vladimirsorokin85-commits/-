# Как это работает: мост к каталогу, поиск, карточки, посты ВК

## Схема (важно понять один раз)

```
МойСклад (Дима)  ──►  GitHub Actions «Catalog fetch»  ──►  ветка catalog-data  ──►  рабочее место
  b2b.moysklad.ru        тянет каталог + фото               catalog/data/*.json       catalog/
                         по заявке catalog/requests/          catalog/photos/*        (снапшот + фото)
```

Почему так: рабочая песочница/агент **не имеет прямого доступа** к `b2b.moysklad.ru`,
`tinyimage-prod.moysklad.ru` и к хранилищу артефактов GitHub. Поэтому каталог приносит сам
GitHub Actions, а результат забирается через git-ветку `catalog-data` (одна команда).

## Обновить каталог и фото (2 минуты)

1. Сказать агенту, что нужно (или отредактировать файлы заявок самостоятельно):

   - `catalog/requests/photos.json` — **какие товары нужны с фото**:

     ```json
     {"ids": ["<uuid>"], "codes": ["00895"], "queries": ["ботинки prabos"], "limit_per_product": 4}
     ```
   - `catalog/requests/fetch.json` — маркер «обнови каталог» (менять дату `touched`).

2. Любое изменение в `catalog/requests/**` **запускает** workflow: Actions → «Catalog fetch».
   (Или вручную: GitHub → Actions → Catalog fetch → Run workflow.)

3. Забрать готовое:

   ```bash
   bash tools/catalog_pull.sh
   ```

   Появятся `catalog/data/` (индекс, полные карточки, отчёт, диагностика фото) и
   `catalog/photos/<код>/*.jpg` + `catalog/photos/manifest.json`.

## Задачник: что чем решается

| Нужно | Команда |
|---|---|
| Сводка по базе (сколько всего, что в наличии) | `python3 catalog/query.py` |
| Живое наличие по словам | `python3 catalog/query.py ботинки 42` |
| Только в наличии / только отсутствующее | `python3 catalog/query.py --in-stock` / `--no-stock` |
| Умный поиск (синонимы, опечатки, размеры) | `python3 -m catalog.search "броник пиксель" --budget 85000` |
| Подбор по цвету и размеру | `python3 -m catalog.search "подсумок" --color мох --size 42` |
| Электростанции: подбор и автономность | `python3 -m catalog.power --pick 12h@62W` |
| Бланк заказа (несколько позиций, итог) | `python3 media/blank/blank.py media/blank/order.json media/blank/out.png` |
| Карточка товара (фото-сетка, описание, допродажа) | `python3 media/blank/card.py media/blank/card.json media/blank/out.jpg` |
| Пост для ВК | `python3 -m vk.post --query "ботинки прабос greyman" --price 24900` |

Первая настройка окружения (один раз): `bash tools/bootstrap.sh` — ставит Pillow в `vendor/`.

## Правила, которые проверяет код

- **Фото только от поставщика.** `blank.py` и `card.py` отказываются собирать карточку,
  если фото нет в `catalog/photos/` — с прямым текстом «попроси фото у поставщика».
- **Цены.** Внутри инструментов поле `price` из каталога подписано как **«закуп Димы»**.
  В постах ВК цена подставляется **только** через `--price` (розница владельца);
  без него пишется «по запросу». Розница электростанций = закуп +10 % (заложено в прайс).
- **Наличие.** Формулировки «на складе у Димы» / «НЕТУ на складе у Димы» — только по `stock > 0`
  из свежего снапшота. Если снапшот старше суток, инструменты сами предупреждают.
- **Одна позиция = одна строка.** Умный поиск схлопывает размеры одной модели в одну строку.

## Если что-то отвалилось

- **Нет снапшота** (`catalog/data/catalog_index.json`): запусти Actions → Catalog fetch,
  затем `bash tools/catalog_pull.sh`.
- **Ветка catalog-data не появилась**: проверь Settings → Actions → General →
  Workflow permissions → «Read and write permissions».
- **Нет фото, хотя в каталоге они есть**: открой `catalog/data/diag_photos.txt` —
  там сырые ответы `/getFullImages` (какие методы и коды вернулись).
- **Авито (Оситинов)**: не трогаем, пока владелец не даст residential-прокси или прайс.
