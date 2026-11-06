# build_pdf.ps1 — сборка PDF-альбома A4 «Два горизонта» из готовых PNG.
#
# Что делает:
#   1) находит готовые PNG в 05_ГОТОВОЕ/png (1x или @2x — по параметру -Scale);
#   2) генерирует _render/print.html: обложка-титул (из P01) + постеры в порядке
#      альбома (бриф §4: P01 → P05 → P06 → P04 → P03 → P02 → P08 → P07 → P09 → P10)
#      + финальная страница CTA; @page A4 portrait margin 0, каждый постер вписан
#      с полями 8 мм без обрезки;
#   3) печатает print.html в PDF headless Chrome;
#   4) проверяет PDF через verify_pdf.py (страницы, A4, вшитые шрифты).
#
# Использование:
#   powershell -NoProfile -ExecutionPolicy Bypass -File _render\build_pdf.ps1
#   powershell ... -File _render\build_pdf.ps1 -Scale 1 -AllowPartial
#   powershell ... -File _render\build_pdf.ps1 -OutPdf "D:\...\test.pdf" -SkipPdfCheck
param(
    [string]$PngDir = "",
    [string]$OutPdf = "",
    [string]$PrintHtml = "",
    [ValidateSet("auto", "1", "2")][string]$Scale = "auto",
    [switch]$AllowPartial,
    [switch]$SkipChrome,
    [switch]$SkipPdfCheck,
    [switch]$SkipPdfShot,
    [string]$PosterOrder = "",
    [string]$Python = "C:\Users\TitanPC\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
# аккуратный вывод Python (UTF-8) в консоль
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = "utf-8"
} catch { }

$RenderDir = $PSScriptRoot
$Root = Split-Path $RenderDir -Parent
if (-not $PngDir)    { $PngDir = Join-Path $Root "05_ГОТОВОЕ\png" }
if (-not $OutPdf)    { $OutPdf = Join-Path $Root "05_ГОТОВОЕ\pdf\Инфографика_Два_горизонта_2026.pdf" }
if (-not $PrintHtml) { $PrintHtml = Join-Path $RenderDir "print.html" }
$OutPdf = [System.IO.Path]::GetFullPath($OutPdf)
$PrintHtml = [System.IO.Path]::GetFullPath($PrintHtml)

$OrderPdf = @("P01", "P05", "P06", "P04", "P03", "P02", "P08", "P07", "P09", "P10")
$OrderAll = @("P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10")
if ($PosterOrder) {
    $OrderPdf = @($PosterOrder.Split(",") | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ })
}

$Titles = @{
    "P01" = "Два горизонта";            "P02" = "Карта линейки"
    "P03" = "Эшелон защиты";            "P04" = "Что защищаем → что берём"
    "P05" = "B2B: почему сейчас";       "P06" = "Правовой компас"
    "P07" = "Купол на свой транспорт";  "P08" = "Сравнение моделей"
    "P09" = "Как купить: 6 шагов";      "P10" = "Документы и сервис"
}

$PageW = 210.0
$PageH = 296.8
$MarginMm = 8.0
$UsableW = $PageW - 2 * $MarginMm
$UsableH = $PageH - 2 * $MarginMm

# ---------------------------------------------------------------------------
# утилиты
# ---------------------------------------------------------------------------
function Get-FileUri([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    return (New-Object System.Uri($full)).AbsoluteUri
}

function Get-PngInfo([string]$Path) {
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read)
    try {
        $buf = New-Object byte[] 24
        $n = $fs.Read($buf, 0, 24)
        if ($n -lt 24) { throw "PNG короче 24 байт: $Path" }
        if ($buf[1] -ne 80 -or $buf[2] -ne 78 -or $buf[3] -ne 71) { throw "не PNG: $Path" }
        $w = ([long]$buf[16] -shl 24) -bor ([long]$buf[17] -shl 16) -bor ([long]$buf[18] -shl 8) -bor ([long]$buf[19])
        $h = ([long]$buf[20] -shl 24) -bor ([long]$buf[21] -shl 16) -bor ([long]$buf[22] -shl 8) -bor ([long]$buf[23])
        return [pscustomobject]@{ Width = [int]$w; Height = [int]$h; Bytes = (Get-Item -LiteralPath $Path).Length }
    } finally { $fs.Close() }
}

function Get-FitMm([int]$PxW, [int]$PxH, [double]$MaxW, [double]$MaxH) {
    $w = $MaxW
    $h = $w * $PxH / $PxW
    if ($h -gt $MaxH) {
        $h = $MaxH
        $w = $h * $PxW / $PxH
    }
    return [pscustomobject]@{ W = [math]::Round($w, 2); H = [math]::Round($h, 2) }
}

function Find-Poster([string]$Id) {
    $res = [pscustomobject]@{ Id = $Id; OneX = $null; TwoX = $null }
    if (-not (Test-Path -LiteralPath $PngDir)) { return $res }
    $files = @(Get-ChildItem -LiteralPath $PngDir -Filter ($Id + "_*.png") -File -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) {
        $files = @(Get-ChildItem -LiteralPath $PngDir -Filter ($Id + "*.png") -File -ErrorAction SilentlyContinue)
    }
    foreach ($f in $files) {
        $bn = $f.BaseName
        if ($bn -notmatch ('^' + $Id)) { continue }
        if ($bn -match '@2x$') { $res.TwoX = $f.FullName; continue }
        if ($bn -match '_\d+x\d+$') { continue }   # wide/story
        if ($bn -match '_\d{3,4}$') { continue }   # _1920
        $res.OneX = $f.FullName
    }
    return $res
}

function Select-Png([string]$Id, $Poster) {
    $one = $Poster.OneX
    $two = $Poster.TwoX
    switch ($Scale) {
        "1" {
            if ($one) { return $one }
            if ($two) { Write-Warning "$Id : нет 1x PNG, беру @2x"; return $two }
            return $null
        }
        "2" {
            if ($two) { return $two }
            if ($one) { Write-Warning "$Id : нет @2x PNG, беру 1x"; return $one }
            return $null
        }
        default {
            if ($two) { return $two }
            return $one
        }
    }
}

# ---------------------------------------------------------------------------
# план альбома
# ---------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $PngDir)) { throw "Нет каталога с PNG: $PngDir" }

$placed = @()
$missing = @()
foreach ($id in $OrderPdf) {
    $poster = Find-Poster $id
    $png = Select-Png $id $poster
    if (-not $png) { $missing += $id; continue }
    $info = Get-PngInfo $png
    $fit = Get-FitMm $info.Width $info.Height $UsableW $UsableH
    $placed += [pscustomobject]@{
        Id = $id; Png = $png; Uri = (Get-FileUri $png)
        PxW = $info.Width; PxH = $info.Height; Bytes = $info.Bytes
        MmW = $fit.W; MmH = $fit.H; Title = $Titles[$id]
    }
}

if ($missing.Count -gt 0) {
    if (-not $AllowPartial) {
        throw ("Нет готовых PNG для постеров: " + ($missing -join ", ") + ". Сначала рендер (render_posters.py) или запустите с -AllowPartial.")
    }
    Write-Warning ("В альбоме не будет постеров: " + ($missing -join ", "))
}

# P01 для обложки-титула (если уже отрендерен)
$coverPng = $null
$p01 = $placed | Where-Object { $_.Id -eq "P01" } | Select-Object -First 1
if ($p01) { $coverPng = $p01 }
else {
    $poster = Find-Poster "P01"
    $one = Select-Png "P01" $poster
    if ($one) { $coverPng = [pscustomobject]@{ Png = $one; Uri = (Get-FileUri $one); PxW = (Get-PngInfo $one).Width; PxH = (Get-PngInfo $one).Height } }
}

# шрифты
$FontsDir = Join-Path (Split-Path $Root -Parent) "kilowatt\design\fonts"
$FontSofia = Join-Path $FontsDir "SofiaSansExtraCondensed-VF.ttf"
$FontOswald = Join-Path $FontsDir "Oswald-VF.ttf"
$FontTektur = Join-Path $FontsDir "Tektur-VF.ttf"
$Logo = Join-Path (Split-Path $Root -Parent) "kilowatt\catalog\assets\img\brand\logo_d_full.png"

$fontCss = @()
if (Test-Path -LiteralPath $FontSofia) {
    $fontCss += "@font-face { font-family:'SofiaCond'; src:url('" + (Get-FileUri $FontSofia) + "') format('truetype'); font-weight:100 900; font-style:normal; }"
}
if (Test-Path -LiteralPath $FontOswald) {
    $fontCss += "@font-face { font-family:'Oswald'; src:url('" + (Get-FileUri $FontOswald) + "') format('truetype'); font-weight:200 700; font-style:normal; }"
}
if (Test-Path -LiteralPath $FontTektur) {
    $fontCss += "@font-face { font-family:'Tektur'; src:url('" + (Get-FileUri $FontTektur) + "') format('truetype'); font-weight:400 900; font-style:normal; }"
}
if ($fontCss.Count -lt 3) { Write-Warning "Локальные шрифты найдены не все — обложка/финал могут уйти на системный шрифт" }

$logoHtml = ""
if (Test-Path -LiteralPath $Logo) {
    $logoHtml = '<div class="wordmark"><img src="' + (Get-FileUri $Logo) + '" alt="В ОКОПЕ"></div>'
} else {
    $logoHtml = '<div class="wordmark wordmark-text">В ОКОПЕ</div>'
}

# обложка: картинка P01, вписанная в 178×132 мм
$coverArt = ""
if ($coverPng) {
    $artFit = Get-FitMm $coverPng.PxW $coverPng.PxH 178.0 132.0
    $coverArt = '<div class="art"><img src="' + $coverPng.Uri + '" style="width:' + $artFit.W + 'mm;height:' + $artFit.H + 'mm" alt="P01 Два горизонта"></div>'
}

# финальная страница: индекс постеров
$idx = ""
foreach ($id in $OrderAll) {
    $idx += '<div class="row"><span class="num">' + $id + '</span><span>' + $Titles[$id] + '</span></div>'
}

# ---------------------------------------------------------------------------
# print.html
# ---------------------------------------------------------------------------
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('<!DOCTYPE html>')
[void]$sb.AppendLine('<html lang="ru">')
[void]$sb.AppendLine('<head>')
[void]$sb.AppendLine('<meta charset="utf-8">')
[void]$sb.AppendLine('<title>Инфографика «Два горизонта» — НПО «Киловатт» × «В ОКОПЕ» — ноябрь 2026</title>')
[void]$sb.AppendLine('<style>')
foreach ($f in $fontCss) { [void]$sb.AppendLine($f) }
[void]$sb.AppendLine(@'
:root { --paper:#F4F1EA; --ink:#1D1E1A; --accent:#C8451F; --muted:#5A5A4F; }
* { box-sizing: border-box; }
@page { size: A4 portrait; margin: 0; }
html, body { margin:0; padding:0; }
body {
  color: var(--ink);
  font-family: "Segoe UI", Arial, sans-serif;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  background: #FFFFFF;
}
.page {
  width: 210mm; height: 296.8mm;
  position: relative; overflow: hidden;
  page-break-after: always;
  break-after: page;
  background: var(--paper);
}
.page:last-of-type { page-break-after: auto; break-after: auto; }
.poster { display: flex; align-items: center; justify-content: center; }
.poster img { display: block; }
/* ---------- обложка ---------- */
.cover { padding: 14mm 16mm 12mm; display: flex; flex-direction: column; }
.cover .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10mm; }
.cover .wordmark img { display: block; width: 44mm; height: auto; }
.cover .wordmark-text { font-family: 'Oswald','Segoe UI',sans-serif; font-weight: 600; font-size: 7mm; letter-spacing: .16em; }
.cover .issuer { font-family: 'Oswald','Segoe UI',sans-serif; font-size: 3.0mm; line-height: 1.55; text-align: right; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.cover .issuer b { font-weight: 500; color: var(--ink); }
.cover .kicker { margin-top: 12mm; font-family: 'Oswald','Segoe UI',sans-serif; font-size: 3.4mm; letter-spacing: .24em; text-transform: uppercase; color: var(--accent); }
.cover h1 { margin: 3mm 0 0; font-family: 'SofiaCond','Segoe UI',sans-serif; font-weight: 800; font-size: 25mm; line-height: 0.94; text-transform: uppercase; letter-spacing: .01em; }
.cover .sub { margin-top: 6mm; font-family: 'Oswald','Segoe UI',sans-serif; font-weight: 500; font-size: 5.0mm; line-height: 1.35; color: #2A2B25; max-width: 160mm; }
.cover .slogan { margin-top: 4mm; font-family: 'Tektur','Segoe UI',sans-serif; font-size: 3.9mm; color: var(--accent); letter-spacing: .02em; }
.cover .rule { margin-top: 8mm; height: .5mm; background: var(--ink); opacity: .22; }
.cover .art { margin-top: auto; padding-top: 8mm; text-align: center; }
.cover .art img { display: block; margin: 0 auto; }
.cover .meta { margin-top: 6mm; display: flex; justify-content: space-between; font-family: 'Tektur','Segoe UI',sans-serif; font-size: 2.9mm; letter-spacing: .09em; text-transform: uppercase; color: #6A6A5E; }
/* ---------- финал ---------- */
.final { padding: 22mm 18mm 16mm; display: flex; flex-direction: column; }
.final .kicker { font-family: 'Oswald','Segoe UI',sans-serif; font-size: 3.4mm; letter-spacing: .24em; text-transform: uppercase; color: var(--accent); }
.final h2 { margin: 4mm 0 0; font-family: 'SofiaCond','Segoe UI',sans-serif; font-weight: 800; font-size: 15mm; line-height: 0.96; text-transform: uppercase; }
.final .lead { margin-top: 5mm; font-family: 'Oswald','Segoe UI',sans-serif; font-size: 4.6mm; line-height: 1.4; color: #2A2B25; max-width: 160mm; }
.final .cta { margin-top: 12mm; border-top: .7mm solid var(--accent); padding-top: 7mm; }
.final .cta .big { font-family: 'Tektur','Segoe UI',sans-serif; font-size: 6.2mm; line-height: 1.55; }
.final .cta .big b { color: var(--accent); font-weight: 700; }
.final .delivery { margin-top: 5mm; font-family: 'Oswald','Segoe UI',sans-serif; font-size: 4.2mm; letter-spacing: .05em; }
.final .note { margin-top: 3mm; font-size: 3.2mm; color: #6A6A5E; }
.final .index { margin-top: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 2.2mm 12mm; font-size: 3.3mm; line-height: 1.3; padding-top: 10mm; }
.final .index .row { display: flex; gap: 3mm; }
.final .index .num { font-family: 'Tektur','Segoe UI',sans-serif; color: var(--accent); width: 9mm; flex: none; }
.final .issuer { margin-top: 9mm; padding-top: 4mm; border-top: .4mm solid #C9C4B4; display: flex; justify-content: space-between; gap: 6mm; font-family: 'Oswald','Segoe UI',sans-serif; font-size: 3.0mm; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
'@)
[void]$sb.AppendLine('</style>')
[void]$sb.AppendLine('</head>')
[void]$sb.AppendLine('<body>')

# --- обложка ---
[void]$sb.AppendLine('<section class="page cover">')
[void]$sb.AppendLine('  <div class="top">')
[void]$sb.AppendLine('    ' + $logoHtml)
[void]$sb.AppendLine('    <div class="issuer"><b>НПО «Киловатт»</b> · производитель<br>официальный дилер · магазин «В ОКОПЕ»</div>')
[void]$sb.AppendLine('  </div>')
[void]$sb.AppendLine('  <div class="kicker">Инфографика · B2B + розница</div>')
[void]$sb.AppendLine('  <h1>ДВА<br>ГОРИЗОНТА</h1>')
[void]$sb.AppendLine('  <div class="sub">Одна линейка. Один поставщик.<br>Два горизонта продаж — розница и объект.</div>')
[void]$sb.AppendLine('  <div class="slogan">«Сначала обнаружь. Потом подави.»</div>')
[void]$sb.AppendLine('  <div class="rule"></div>')
[void]$sb.AppendLine('  ' + $coverArt)
[void]$sb.AppendLine('  <div class="meta"><span>Инфографика · ноябрь 2026</span><span>10 постеров · A4</span></div>')
[void]$sb.AppendLine('</section>')

# --- постеры ---
foreach ($p in $placed) {
    [void]$sb.AppendLine('<section class="page poster">')
    [void]$sb.AppendLine('  <img src="' + $p.Uri + '" style="width:' + $p.MmW + 'mm;height:' + $p.MmH + 'mm" alt="' + $p.Id + ' ' + $p.Title + '">')
    [void]$sb.AppendLine('</section>')
}

# --- финальная страница ---
[void]$sb.AppendLine('<section class="page final">')
[void]$sb.AppendLine('  <div class="kicker">Следующий шаг</div>')
[void]$sb.AppendLine('  <h2>Покажем линейку<br>под вашу задачу</h2>')
[void]$sb.AppendLine('  <div class="lead">Разберём задачу, подберём конфигурацию и пришлём КП. Для КП достаточно пяти вводных: объект, площадь, типовые цели, питание, срок.</div>')
[void]$sb.AppendLine('  <div class="cta">')
[void]$sb.AppendLine('    <div class="big">Telegram <b>@vokope_ru</b><br>Телефон <b>+7 999 136-71-42</b></div>')
[void]$sb.AppendLine('    <div class="delivery">Доставка по РФ · Самовывоз в Москве</div>')
[void]$sb.AppendLine('    <div class="note">Цена по запросу · КП под задачу · без публикации цен</div>')
[void]$sb.AppendLine('  </div>')
[void]$sb.AppendLine('  <div class="index">' + $idx + '</div>')
[void]$sb.AppendLine('  <div class="issuer"><span>НПО «Киловатт» · производитель</span><span>В ОКОПЕ · официальный дилер</span><span>ноябрь 2026</span></div>')
[void]$sb.AppendLine('</section>')

[void]$sb.AppendLine('</body>')
[void]$sb.AppendLine('</html>')

[System.IO.File]::WriteAllText($PrintHtml, $sb.ToString(), $Utf8NoBom)

$expectedPages = 1 + $placed.Count + 1
Write-Host ("print.html: {0} ({1:N0} Б) — обложка + {2} постеров + финал = {3} стр." -f $PrintHtml, (Get-Item $PrintHtml).Length, $placed.Count, $expectedPages)
foreach ($p in $placed) {
    Write-Host ("  {0}  {1,-8} {2,5}×{3,-5} px  →  {4}×{5} мм  {6}" -f $p.Id, (Split-Path $p.Png -Leaf), $p.PxW, $p.PxH, $p.MmW, $p.MmH, ('{0:N0} КБ' -f ($p.Bytes / 1KB)))
}

if ($SkipChrome) {
    Write-Host "SkipChrome: PDF не собирался."
    exit 0
}

if (-not (Test-Path -LiteralPath $Chrome)) { throw "Chrome не найден: $Chrome" }
$outDir = Split-Path $OutPdf -Parent
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
if (Test-Path -LiteralPath $OutPdf) { Remove-Item -LiteralPath $OutPdf -Force }

$profile = Join-Path $env:TEMP ("dsh-pdf-" + [guid]::NewGuid().ToString("N"))
$chromeArgs = @(
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=20000",
    "--user-data-dir=$profile",
    "--no-pdf-header-footer",
    "--print-to-pdf-no-header",
    "--allow-file-access-from-files",
    ("--print-to-pdf=" + $OutPdf),
    (Get-FileUri $PrintHtml)
)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"   # Chrome пишет в stderr; в PS 5.1 не должно валить скрипт
& $Chrome @chromeArgs 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
$sw.Stop()
Start-Sleep -Milliseconds 400
if (Test-Path -LiteralPath $profile) { Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue }

if (-not (Test-Path -LiteralPath $OutPdf)) { throw "PDF не создан: $OutPdf" }
$pdfItem = Get-Item -LiteralPath $OutPdf
if ($pdfItem.Length -le 0) { throw "PDF пустой (0 байт): $OutPdf" }
Write-Host ("PDF: {0} — {1:N2} МБ за {2:N1} с" -f $OutPdf, ($pdfItem.Length / 1MB), $sw.Elapsed.TotalSeconds)

# ---------------------------------------------------------------------------
# проверка PDF
# ---------------------------------------------------------------------------
$pdfOk = $true
$pyExe = $Python
if (-not (Test-Path -LiteralPath $pyExe)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $pyExe = $cmd.Source }
}
if (-not $SkipPdfCheck) {
    $verifier = Join-Path $RenderDir "verify_pdf.py"
    if ((Test-Path -LiteralPath $verifier) -and $pyExe -and (Test-Path -LiteralPath $pyExe)) {
        $jsonOut = Join-Path $RenderDir "_qa\pdf_report.json"
        & $pyExe $verifier $OutPdf "--expect-pages" $expectedPages "--json" $jsonOut
        if ($LASTEXITCODE -ne 0) { $pdfOk = $false }
    } else {
        Write-Warning "verify_pdf.py или Python не найдены — число страниц PDF не проверено (честно отметить в отчёте)"
    }
}

# визуальная проверка: открываем PDF в Chrome-viewer и снимаем 1-ю и последнюю страницы
if (-not $SkipPdfShot) {
    $shotter = Join-Path $RenderDir "pdf_preview.py"
    if ((Test-Path -LiteralPath $shotter) -and $pyExe -and (Test-Path -LiteralPath $pyExe)) {
        Write-Host "Скриншоты PDF (open-check): стр. 1 и $expectedPages ..."
        & $pyExe $shotter $OutPdf "--out" (Join-Path $RenderDir "_qa\pdf_pages") "--pages" ("1," + $expectedPages)
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "PDF не удалось отрисовать в headless-вьюере — открытие PDF проверить вручную/QA"
        }
    }
}

if (-not $pdfOk) {
    Write-Error "PDF собран, но проверка не прошла (см. вывод выше)"
    exit 1
}
Write-Host "OK: PDF готов."
exit 0
