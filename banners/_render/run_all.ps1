# run_all.ps1 — полный прогон пайплайна рекламных баннеров.
#
#   1. render_banners.py --all   — PNG 1×/2× постов и квадратов (что уже есть в banners\html);
#   2. make_previews.py          — JPG 1080 q88 в 05_ГОТОВОЕ\превью;
#   3. contact_sheet.py          — контактный лист QA в _render\_qa;
#   4. gallery.py                — 05_ГОТОВОЕ\gallery\index.html;
#   5. build_pdf.ps1             — PDF A4 (обложка + 18 постов), когда готовы все 18 постов
#                                  (или с -PartialPdf);
#   6. check_files.py            — 05_ГОТОВОЕ\ЧЕК_ЛИСТ_ФАЙЛОВ.md (размеры/веса/время рендера).
#
# Использование:
#   powershell -NoProfile -ExecutionPolicy Bypass -File _render\run_all.ps1
#   ... run_all.ps1 -OnlyNew
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
$BannersDir = Split-Path $RenderDir -Parent
$PngDir = Join-Path $BannersDir "05_ГОТОВОЕ\png"
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

if (-not $SkipRender) {
    Invoke-Step "1/6 Рендер PNG баннеров" {
        $pyArgs = @((Join-Path $RenderDir "render_banners.py"), "--all")
        if ($OnlyNew) { $pyArgs += "--only-new" }
        & $Python @pyArgs
        if ($LASTEXITCODE -eq 2) { throw "рендер не смог запуститься" }
    }
} else { Write-Host "1/6 Рендер: пропущен (-SkipRender)" }

Invoke-Step "2/6 JPG-превью" { & $Python (Join-Path $RenderDir "make_previews.py") }
Invoke-Step "3/6 Контактный лист QA" { & $Python (Join-Path $RenderDir "contact_sheet.py") }
Invoke-Step "4/6 Галерея" { & $Python (Join-Path $RenderDir "gallery.py") }

$havePoster = 0
if (Test-Path -LiteralPath $PngDir) {
    $havePoster = @(Get-ChildItem -LiteralPath $PngDir -Filter "*_1080x1350.png" -File).Count
}
if ($SkipPdf) {
    Write-Host "5/6 PDF: пропущен (-SkipPdf)"
} elseif ($havePoster -ge 18 -or $PartialPdf) {
    Invoke-Step "5/6 PDF A4" {
        $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $RenderDir "build_pdf.ps1"))
        if ($PartialPdf -and $havePoster -lt 18) { $psArgs += "-AllowPartial" }
        if ($SkipPdfShot) { $psArgs += "-SkipPdfShot" }
        & powershell @psArgs
    }
} else {
    Write-Warning ("5/6 PDF: пропущен — готово постов " + $havePoster + "/18 (нужен полный набор или -PartialPdf)")
}

Invoke-Step "6/6 Чек-лист файлов" {
    $pyArgs = @((Join-Path $RenderDir "check_files.py"))
    if ($havePoster -lt 18) { $pyArgs += "--partial" }
    & $Python @pyArgs
}

Write-Host ""
if ($Fail -gt 0) {
    Write-Host ("ПРОГОН: есть незавершённые шаги (" + $Fail + ")") -ForegroundColor Yellow
    exit 1
}
Write-Host "ПРОГОН: все шаги выполнены." -ForegroundColor Green
exit 0
