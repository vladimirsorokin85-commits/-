# run_all.ps1 — полный прогон пайплайна «Два горизонта» (рендер → превью → галерея → PDF → чек-лист).
#
# ВАЖНО (процесс): финальные файлы в 05_ГОТОВОЕ собираются ТОЛЬКО после сигнала
# Lead «posters locked». Промежуточные рендеры идут в тестовую папку:
#   & $py render_posters.py --all --out _render\_qa\preview_render
#
# Шаги:
#   1. render_posters.py --all  — PNG 1×/2× основной серии + wide/story (что уже есть);
#   2. make_previews.py         — JPG 1080 q88 в 05_ГОТОВОЕ/превью;
#   3. make_tg_previews.py      — 3 JPG для Telegram (P01, P02, P07) в 05_ГОТОВОЕ/превью_ТГ;
#   4. contact_sheet.py         — контактный лист QA в _render/_qa;
#   5. gallery.py               — 05_ГОТОВОЕ/gallery/index.html;
#   6. build_pdf.ps1            — PDF A4 (обложка + постеры + финал), когда есть все 10 постеров
#                                 (или с -PartialPdf — из того, что есть);
#   7. check_files.py           — 05_ГОТОВОЕ/ЧЕК_ЛИСТ_ФАЙЛОВ.md (с датой/временем рендера каждого файла).
#
# Использование:
#   powershell -NoProfile -ExecutionPolicy Bypass -File _render\run_all.ps1
#   ... run_all.ps1 -OnlyNew            # не перерендеривать актуальные PNG
#   ... run_all.ps1 -PartialPdf         # собрать PDF из неполного набора
#   ... run_all.ps1 -SkipPdf -SkipRender
param(
    [switch]$OnlyNew,
    [switch]$PartialPdf,
    [switch]$SkipRender,
    [switch]$SkipPdf,
    [switch]$SkipPdfShot,
    [string]$Python = "C:\Users\TitanPC\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = "utf-8"
} catch { }

$RenderDir = $PSScriptRoot
$Root = Split-Path $RenderDir -Parent
$PngDir = Join-Path $Root "05_ГОТОВОЕ\png"
$Fail = 0

if (-not (Test-Path -LiteralPath $Python)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source } else { throw "Python не найден: $Python" }
}

function Invoke-Step([string]$Name, [scriptblock]$Body) {
    Write-Host ""
    Write-Host ("=== " + $Name) -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Body
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("шаг не прошёл: " + $Name + " (код " + $LASTEXITCODE + ")")
        $script:Fail++
    }
}

# 1. рендер
if (-not $SkipRender) {
    Invoke-Step "1/7 Рендер PNG" {
        $pyArgs = @((Join-Path $RenderDir "render_posters.py"), "--all")
        if ($OnlyNew) { $pyArgs += "--only-new" }
        & $Python @pyArgs
        if ($LASTEXITCODE -eq 2) { throw "рендер не смог запуститься" }
    }
} else { Write-Host "1/7 Рендер: пропущен (-SkipRender)" }

# 2. превью 1080
Invoke-Step "2/7 JPG-превью 1080" {
    & $Python (Join-Path $RenderDir "make_previews.py")
}

# 3. превью для Telegram (3 лучших: P01, P02, P07)
Invoke-Step "3/7 Превью для Telegram (P01/P02/P07)" {
    & $Python (Join-Path $RenderDir "make_tg_previews.py")
}

# 4. контактный лист QA
Invoke-Step "4/7 Контактный лист QA" {
    & $Python (Join-Path $RenderDir "contact_sheet.py")
}

# 5. галерея
Invoke-Step "5/7 Галерея" {
    & $Python (Join-Path $RenderDir "gallery.py")
}

# 6. PDF — только когда есть все 10 постеров (или -PartialPdf)
$haveMain = 0
if (Test-Path -LiteralPath $PngDir) {
    $haveMain = @(Get-ChildItem -LiteralPath $PngDir -Filter "P*.png" -File |
        Where-Object { $_.Name -notmatch '@2x' -and $_.Name -notmatch '_\d+x\d+$' -and $_.Name -notmatch '_\d{3,4}$' }).Count
}
if ($SkipPdf) {
    Write-Host "6/7 PDF: пропущен (-SkipPdf)"
} elseif ($haveMain -ge 10 -or $PartialPdf) {
    Invoke-Step "6/7 PDF A4" {
        $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $RenderDir "build_pdf.ps1"))
        if ($PartialPdf -and $haveMain -lt 10) { $psArgs += "-AllowPartial" }
        if ($SkipPdfShot) { $psArgs += "-SkipPdfShot" }
        & powershell @psArgs
    }
} else {
    Write-Warning ("6/7 PDF: пропущен — готово постеров " + $haveMain + "/10 (для PDF нужен полный набор или -PartialPdf)")
}

# 7. чек-лист
Invoke-Step "7/7 Чек-лист файлов" {
    $pyArgs = @((Join-Path $RenderDir "check_files.py"))
    if ($haveMain -lt 10) { $pyArgs += "--partial" }
    & $Python @pyArgs
}

Write-Host ""
if ($Fail -gt 0) {
    Write-Host ("ПРОГОН: есть незавершённые шаги (" + $Fail + ") — см. вывод выше") -ForegroundColor Yellow
    exit 1
}
Write-Host "ПРОГОН: все шаги выполнены." -ForegroundColor Green
exit 0
