# banners/story — 6 рекламных историй 1080×1920 (9:16)

Второй эшелон пакета баннеров. Роль: **designer-b**. Писать можно только сюда.
Сделано после `banners/_design` (banner.css + tokens.css) и 36 основных баннеров;
стиль и токены — те же, что у основных, компоновка пересобрана под вертикаль.

## Состав (6)

| Файл | Модель | Тема | Компоновка |
|---|---|---|---|
| `B01_kapyushon_k_8m_1080x1920.html` | «Капюшон» К-8М | field (тёмная) | hero: хук → К-8М → фото → 4 цифры 2×2 |
| `B02_kapyushon_k_12m_1080x1920.html` | «Капюшон» К-12М | field | hero: хук → К-12М → фото → 4 цифры 2×2 |
| `B07_kapyushon_fpv_7_moto_1080x1920.html` | «Капюшон» ФПВ-7 мото | field | hero → фото → 3 цифры в строку |
| `B08_shtora_k_12_700_1080x1920.html` | «Штора» К-12/700 | quiet (светлая) | hero → фото → 4 цифры 2×2 |
| `B10_rebus_4_1080x1920.html` | «Ребус-4» | quiet | hero → фото → 4 цифры 2×2 |
| `B12_signal_m2_1080x1920.html` | «Сигнал-М2» | quiet | hero → фото → 3 цифры (2+1, длинная во всю ширину) |

`story.css` — локальные правила формата 1080×1920 поверх `../_design/tokens.css` + `../_design/banner.css`.
`_qa/` — контрольные скриншоты 1× (Chrome headless, `--window-size=1080,1920 --force-device-scale-factor=1`).

## Анатомия сторис

1. Шапка: вербалка «В ОКОПЕ» + «НПО „Киловатт“ · производитель» + `B0X · 11.2026`.
2. Хук капсом с акцентной чертой (`b-eyebrow` + `b-headline`).
3. Название модели крупно, акцентом (`b-model`).
4. Рекламная строка ≤90 знаков (`b-line`).
5. Фото на бумажной плашке с уголками-засечками (`b-plate`), подпись модели (`b-plate-cap`);
   фото вписано через `inset: 26px` + `object-fit: contain`, чтобы не «прилипало» к краю.
6. 3–4 цифры-козыря (`b-stats`): 3 — в строку, 4 — сеткой 2×2.
7. Футер: `@vokope_ru` + телефон + «Цена по запросу · Доставка по РФ · Самовывоз в Москве»,
   справа «В ОКОПЕ · магазин брони / официальный дилер».
8. Юрстрока 11,5 px (дисклеймер по брифу баннеров §4.9).

## Контент

- Тексты и цифры — `../00_КОПИРАЙТ/banners_data.json` (B01, B02, B07, B08, B10, B12), без изменений.
- Claims: B01 C016/C017/C127 · B02 C019/C020/C127 · B07 C025/C127 · B08 C027/C028 ·
  B10 C030/C031 · B12 C033/C034.
- Фото — только реальные: `../_design/img/product/k8m.png`, `../_design/img/cut/k12m.png`,
  `../_design/img/product/fpv-7-moto.png`, `../_design/img/cut/shtora-k12.png`,
  `../_design/img/cut/rebus-4.png`, `../_design/img/cut/signal-m2.png`.
- Цены не публикуются: только «Цена по запросу».

## Как отрендерить (для renderer)

```powershell
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$out = "...\banners\05_ГОТОВОЕ\png"
Get-ChildItem "...\banners\story\*.html" | ForEach-Object {
  $name = $_.BaseName -replace '_1080x1920$',''   # B01_kapyushon_k_8m
  $uri  = ([System.Uri]::new($_.FullName)).AbsoluteUri
  & $chrome --headless=new --disable-gpu --hide-scrollbars --no-first-run `
    --no-default-browser-check --force-device-scale-factor=1 --virtual-time-budget=5000 `
    "--screenshot=$out\${name}_1080x1920.png" --window-size=1080,1920 $uri
  # @2x: тот же вызов с --force-device-scale-factor=2 → 2160×3840
}
```

Имена в `05_ГОТОВОЕ/png/`: `B01_kapyushon_k_8m_1080x1920.png` (+ `@2x`), по конвенции пакета.
