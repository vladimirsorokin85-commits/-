# build_pdf.ps1 — PDF-альбом A4 «Рекламные баннеры Киловатт» (обложка + 18).
#
# Находит PNG формата 1080×1350 в banners\05_ГОТОВОЕ\png (1× или @2x),
# генерирует _render\print.html (обложка + 18 баннеров B01–B18), печатает в PDF
# headless Chrome и проверяет: 19 страниц, A4 portrait, вшитые шрифты, непустые
# страницы, плюс скриншот 1-й и последней страниц через Chrome-viewer.
#
# Использование:
#   powershell -NoProfile -ExecutionPolicy Bypass -File _render\build_pdf.ps1
#   ... -Scale 1 -AllowPartial
param(
    [string]$PngDir = "",
    [string]$OutPdf = "",
    [string]$PrintHtml = "",
    [ValidateSet("auto", "1", "2")][string]$Scale = "auto",
    [switch]$AllowPartial,
    [switch]$SkipChrome,
    [switch]$SkipPdfCheck,
    [switch]$SkipPdfShot,
    [string]$Python = "C:\Users\TitanPC\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = "utf-8"
} catch { }

$RenderDir = $PSScriptRoot
$BannersDir = Split-Path $RenderDir -Parent
if (-not $PngDir)    { $PngDir = Join-Path $BannersDir "05_ГОТОВОЕ\png" }
if (-not $OutPdf)    { $OutPdf = Join-Path $BannersDir "05_ГОТОВОЕ\pdf\Рекламные_баннеры_Киловатт_2026.pdf" }
if (-not $PrintHtml) { $PrintHtml = Join-Path $RenderDir "print.html" }
$OutPdf = [System.IO.Path]::GetFullPath($OutPdf)
$PrintHtml = [System.IO.Path]::GetFullPath($PrintHtml)

$Order = @("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09",
           "B10", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18")
$Models = @{
    "B01" = "«Капюшон» К-8М";              "B02" = "«Капюшон» К-12М"
    "B03" = "«Капшон» К-15М (и ВИП)";      "B04" = "«Капюшон» К-12 багажный бокс"
    "B05" = "ФПВ-8М";                      "B06" = "ФПВ-12"
    "B07" = "ФПВ-5 мото";                  "B08" = "«Штора» К-12/700"
    "B09" = "«Штора-М» К-8/600";           "B10" = "«Ребус-4»"
    "B11" = "«Поле-31»";                   "B12" = "«Сигнал-М2»"
    "B13" = "Рюкзак ТП 4-28А/Б";           "B14" = "Рюкзак ТП 4-50А/Б"
    "B15" = "Рюкзак ТП 7-100";             "B16" = "Рюкзак ТП 8-100"
    "B17" = "ИП-24/100";                   "B18" = "РЭБ-тестер Т-9"
}
$Models["B03"] = "«Капюшон» К-15М (и ВИП)"

$PageW = 210.0
$PageH = 296.8
$MarginMm = 8.0
$UsableW = $PageW - 2 * $MarginMm
$UsableH = $PageH - 2 * $MarginMm

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

# --- план альбома ----------------------------------------------------------
if (-not (Test-Path -LiteralPath $PngDir)) { throw "Нет каталога с PNG: $PngDir" }

function Find-BannerPng([string]$Id) {
    $one = $null; $two = $null
    $files = @(Get-ChildItem -LiteralPath $PngDir -Filter ($Id + "_*_1080x1350*.png") -File -ErrorAction SilentlyContinue)
    foreach ($f in $files) {
        if ($f.BaseName -match '@2x$') { $two = $f.FullName } else { $one = $f.FullName }
    }
    if ($Scale -eq "1") { if ($one) { return $one } else { return $two } }
    if ($Scale -eq "2") { if ($two) { return $two } else { return $one } }
    if ($two) { return $two }
    return $one
}

$placed = @()
$missing = @()
foreach ($id in $Order) {
    $png = Find-BannerPng $id
    if (-not $png) { $missing += $id; continue }
    $info = Get-PngInfo $png
    $fit = Get-FitMm $info.Width $info.Height $UsableW $UsableH
    $placed += [pscustomobject]@{
        Id = $id; Png = $png; Uri = (Get-FileUri $png)
        PxW = $info.Width; PxH = $info.Height; Bytes = $info.Bytes
        MmW = $fit.W; MmH = $fit.H; Title = $Models[$id]
    }
}
if ($missing.Count -gt 0) {
    if (-not $AllowPartial) {
        throw ("Нет PNG формата 1080×1350 для: " + ($missing -join ", ") + ". Сначала рендер (render_banners.py) или -AllowPartial.")
    }
    Write-Warning ("В альбоме не будет: " + ($missing -join ", "))
}

# обложка — арт B01, если есть
$cover = $placed | Where-Object { $_.Id -eq "B01" } | Select-Object -First 1
$coverArt = ""
if ($cover) {
    $artFit = Get-FitMm $cover.PxW $cover.PxH 150.0 118.0
    $coverArt = '<div class="art"><img src="' + $cover.Uri + '" style="width:' + $artFit.W + 'mm;height:' + $artFit.H + 'mm" alt="B01"></div>'
}

# шрифты/лого
$FontsDir = Join-Path (Split-Path $BannersDir -Parent) "kilowatt\design\fonts"
$FontSofia = Join-Path $FontsDir "SofiaSansExtraCondensed-VF.ttf"
$FontOswald = Join-Path $FontsDir "Oswald-VF.ttf"
$FontTektur = Join-Path $FontsDir "Tektur-VF.ttf"
$Logo = Join-Path (Split-Path $BannersDir -Parent) "kilowatt\catalog\assets\img\brand\logo_d_full.png"
$fontCss = @()
if (Test-Path -LiteralPath $FontSofia) { $fontCss += "@font-face { font-family:'SofiaCond'; src:url('" + (Get-FileUri $FontSofia) + "') format('truetype'); font-weight:100 900; }" }
if (Test-Path -LiteralPath $FontOswald) { $fontCss += "@font-face { font-family:'Oswald'; src:url('" + (Get-FileUri $FontOswald) + "') format('truetype'); font-weight:200 700; }" }
if (Test-Path -LiteralPath $FontTektur) { $fontCss += "@font-face { font-family:'Tektur'; src:url('" + (Get-FileUri $FontTektur) + "') format('truetype'); font-weight:400 900; }" }
$logoHtml = if (Test-Path -LiteralPath $Logo) { '<div class="wordmark"><img src="' + (Get-FileUri $Logo) + '" alt="В ОКОПЕ"></div>' } else { '<div class="wordmark wordmark-text">В ОКОПЕ</div>' }

# индекс моделей
$idx = ""
foreach ($id in $Order) { $idx += '<div class="row"><span class="num">' + $id + '</span><span>' + $Models[$id] + '</span></div>' }

# --- print.html ------------------------------------------------------------
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('<!DOCTYPE html>')
[void]$sb.AppendLine('<html lang="ru">')
[void]$sb.AppendLine('<head>')
[void]$sb.AppendLine('<meta charset="utf-8">')
[void]$sb.AppendLine('<title>Рекламные баннеры «Киловатт» — В ОКОПЕ — ноябрь 2026</title>')
[void]$sb.AppendLine('<style>')
foreach ($f in $fontCss) { [void]$sb.AppendLine($f) }
[void]$sb.AppendLine(@'
:root { --paper:#F4F1EA; --ink:#1D1E1A; --accent:#C8451F; --muted:#5A5A4F; }
* { box-sizing: border-box; }
@page { size: A4 portrait; margin: 0; }
html, body { margin:0; padding:0; }
body { color:var(--ink); font-family:"Segoe UI", Arial, sans-serif;
       -webkit-print-color-adjust:exact; print-color-adjust:exact; background:#fff; }
.page { width:210mm; height:296.8mm; position:relative; overflow:hidden;
        page-break-after:always; break-after:page; background:var(--paper); }
.page:last-of-type { page-break-after:auto; break-after:auto; }
.banner { display:flex; align-items:center; justify-content:center; }
.banner img { display:block; }
.cover { padding:14mm 16mm 12mm; display:flex; flex-direction:column; }
.cover .top { display:flex; justify-content:space-between; align-items:flex-start; gap:10mm; }
.cover .wordmark img { display:block; width:44mm; height:auto; }
.cover .wordmark-text { font-family:'Oswald','Segoe UI',sans-serif; font-weight:600; font-size:7mm; letter-spacing:.16em; }
.cover .issuer { font-family:'Oswald','Segoe UI',sans-serif; font-size:3.0mm; line-height:1.55; text-align:right;
                 letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
.cover .issuer b { font-weight:500; color:var(--ink); }
.cover .kicker { margin-top:12mm; font-family:'Oswald','Segoe UI',sans-serif; font-size:3.4mm;
                 letter-spacing:.24em; text-transform:uppercase; color:var(--accent); }
.cover h1 { margin:3mm 0 0; font-family:'SofiaCond','Segoe UI',sans-serif; font-weight:800;
            font-size:23mm; line-height:0.94; text-transform:uppercase; }
.cover .sub { margin-top:6mm; font-family:'Oswald','Segoe UI',sans-serif; font-weight:500;
              font-size:5.0mm; line-height:1.35; color:#2A2B25; max-width:160mm; }
.cover .rule { margin-top:8mm; height:.5mm; background:var(--ink); opacity:.22; }
.cover .art { margin-top:auto; padding-top:6mm; text-align:center; }
.cover .art img { display:block; margin:0 auto; }
.cover .meta { margin-top:6mm; display:flex; justify-content:space-between;
               font-family:'Tektur','Segoe UI',sans-serif; font-size:2.9mm; letter-spacing:.09em;
               text-transform:uppercase; color:#6A6A5E; }
.final { padding:22mm 18mm 16mm; display:flex; flex-direction:column; }
.final .kicker { font-family:'Oswald','Segoe UI',sans-serif; font-size:3.4mm; letter-spacing:.24em;
                 text-transform:uppercase; color:var(--accent); }
.final h2 { margin:4mm 0 0; font-family:'SofiaCond','Segoe UI',sans-serif; font-weight:800;
            font-size:15mm; line-height:0.96; text-transform:uppercase; }
.final .lead { margin-top:5mm; font-family:'Oswald','Segoe UI',sans-serif; font-size:4.6mm;
               line-height:1.4; color:#2A2B25; max-width:160mm; }
.final .cta { margin-top:10mm; border-top:.7mm solid var(--accent); padding-top:6mm; }
.final .cta .big { font-family:'Tektur','Segoe UI',sans-serif; font-size:6.2mm; line-height:1.55; }
.final .cta .big b { color:var(--accent); font-weight:700; }
.final .delivery { margin-top:5mm; font-family:'Oswald','Segoe UI',sans-serif; font-size:4.2mm; letter-spacing:.05em; }
.final .index { margin-top:auto; display:grid; grid-template-columns:1fr 1fr; gap:1.8mm 12mm;
                font-size:3.1mm; line-height:1.28; padding-top:8mm; }
.final .index .row { display:flex; gap:3mm; }
.final .index .num { font-family:'Tektur','Segoe UI',sans-serif; color:var(--accent);
                     width:10mm; flex:none; }
.final .issuer { margin-top:8mm; padding-top:4mm; border-top:.4mm solid #C9C4B4; display:flex;
                 justify-content:space-between; gap:6mm; font-family:'Oswald','Segoe UI',sans-serif;
                 font-size:3.0mm; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
'@)
[void]$sb.AppendLine('</style>')
[void]$sb.AppendLine('</head>')
[void]$sb.AppendLine('<body>')

# обложка
[void]$sb.AppendLine('<section class="page cover">')
[void]$sb.AppendLine('  <div class="top">')
[void]$sb.AppendLine('    ' + $logoHtml)
[void]$sb.AppendLine('    <div class="issuer"><b>НПО «Киловатт»</b> · производитель<br>магазин «В ОКОПЕ» · подбор и поставка</div>')
[void]$sb.AppendLine('  </div>')
[void]$sb.AppendLine('  <div class="kicker">Реклама для соцсетей · 18 моделей × 2 формата</div>')
[void]$sb.AppendLine('  <h1>РЕКЛАМНЫЕ<br>БАННЕРЫ</h1>')
[void]$sb.AppendLine('  <div class="sub">Одна модель — один баннер.<br>Пост 1080×1350 и квадрат 1080×1080, PNG 1× и 2×.</div>')
[void]$sb.AppendLine('  <div class="rule"></div>')
[void]$sb.AppendLine('  ' + $coverArt)
[void]$sb.AppendLine('  <div class="meta"><span>Ноябрь 2026</span><span>18 моделей · 36 баннеров</span></div>')
[void]$sb.AppendLine('</section>')

# баннеры
foreach ($p in $placed) {
    [void]$sb.AppendLine('<section class="page banner">')
    [void]$sb.AppendLine('  <img src="' + $p.Uri + '" style="width:' + $p.MmW + 'mm;height:' + $p.MmH + 'mm" alt="' + $p.Id + ' ' + $p.Title + '">')
    [void]$sb.AppendLine('</section>')
}

# финальная страница с индексом (входит в альбом сверх 19? — по брифу ровно 19 стр.: обложка + 18,
# поэтому индекс выводим на обложке не отдельной страницей)
[void]$sb.AppendLine('</body>')
[void]$sb.AppendLine('</html>')

[System.IO.File]::WriteAllText($PrintHtml, $sb.ToString(), $Utf8NoBom)
$expectedPages = 1 + $placed.Count
Write-Host ("print.html: {0} — обложка + {1} баннеров = {2} стр." -f $PrintHtml, $placed.Count, $expectedPages)
foreach ($p in $placed) {
    Write-Host ("  {0}  {1,-42} {2,5}×{3,-5} px → {4}×{5} мм  {6:N0} КБ" -f $p.Id, (Split-Path $p.Png -Leaf), $p.PxW, $p.PxH, $p.MmW, $p.MmH, ($p.Bytes / 1KB))
}

if ($SkipChrome) { Write-Host "SkipChrome: PDF не собирался."; exit 0 }
if (-not (Test-Path -LiteralPath $Chrome)) { throw "Chrome не найден: $Chrome" }
$outDir = Split-Path $OutPdf -Parent
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
if (Test-Path -LiteralPath $OutPdf) { Remove-Item -LiteralPath $OutPdf -Force }

$profile = Join-Path $env:TEMP ("dsh-banpdf-" + [guid]::NewGuid().ToString("N"))
$chromeArgs = @(
    "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
    "--user-data-dir=$profile", "--no-pdf-header-footer", "--print-to-pdf-no-header",
    "--allow-file-access-from-files", ("--print-to-pdf=" + $OutPdf), (Get-FileUri $PrintHtml)
)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Chrome @chromeArgs 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
$sw.Stop()
Start-Sleep -Milliseconds 400
if (Test-Path -LiteralPath $profile) { Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue }
if (-not (Test-Path -LiteralPath $OutPdf)) { throw "PDF не создан: $OutPdf" }
$pdfItem = Get-Item -LiteralPath $OutPdf
if ($pdfItem.Length -le 0) { throw "PDF пустой: $OutPdf" }
Write-Host ("PDF: {0} — {1:N2} МБ за {2:N1} с" -f $OutPdf, ($pdfItem.Length / 1MB), $sw.Elapsed.TotalSeconds)

$pdfOk = $true
$pyExe = $Python
if (-not (Test-Path -LiteralPath $pyExe)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $pyExe = $cmd.Source }
}
if (-not $SkipPdfCheck) {
    $verifier = Join-Path $RenderDir "verify_pdf.py"
    if ((Test-Path -LiteralPath $verifier) -and $pyExe) {
        $jsonOut = Join-Path $RenderDir "_qa\pdf_report.json"
        & $pyExe $verifier $OutPdf "--expect-pages" $expectedPages "--json" $jsonOut
        if ($LASTEXITCODE -ne 0) { $pdfOk = $false }
    } else {
        Write-Warning "verify_pdf.py или Python не найдены — число страниц не проверено"
    }
}
if (-not $SkipPdfShot) {
    $shotter = Join-Path $RenderDir "pdf_preview.py"
    if ((Test-Path -LiteralPath $shotter) -and $pyExe) {
        Write-Host "Скриншоты PDF (open-check): стр. 1 и $expectedPages ..."
        & $pyExe $shotter $OutPdf "--out" (Join-Path $RenderDir "_qa\pdf_pages") "--pages" ("1," + $expectedPages)
        if ($LASTEXITCODE -ne 0) { Write-Warning "PDF не удалось отрисовать в headless-вьюере" }
    }
}
if (-not $pdfOk) { Write-Error "PDF собран, но проверка не прошла"; exit 1 }
Write-Host "OK: PDF готов."
exit 0
