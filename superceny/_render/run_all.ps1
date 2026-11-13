# run_all.ps1 — полный прогон пакета «СУПЕРЦЕНЫ» (рендер карточек → галерея → чек-лист).
#
#   1. render_cards.py --all --batch-size N  — PNG 1080×1350 в 05_ГОТОВОЕ\<folder>\;
#   2. gallery.py                            — 05_ГОТОВОЕ\gallery\index.html;
#   3. check_files.py                        — 05_ГОТОВОЕ\ЧЕК_ЛИСТ_ФАЙЛОВ.md.
#
# Использование:
#   powershell -NoProfile -ExecutionPolicy Bypass -File _render\run_all.ps1
#   ... run_all.ps1 -OnlyNew
#   ... run_all.ps1 -SkipRender -BatchSize 80
param(
    [switch]$OnlyNew,
    [switch]$SkipRender,
    [switch]$TwoX,
    [int]$BatchSize = 40,
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

Invoke-Step "1/7 Проверка ассетов (img/print, прозрачность duotone)" { & $Python (Join-Path $RenderDir "check_assets.py") }
Invoke-Step "2/7 Проверка цен в HTML (positions.json)" { & $Python (Join-Path $RenderDir "check_prices.py"); if ($LASTEXITCODE -eq 2) { Write-Host "цены: проверка пропущена (нет price_display)" } }

if (-not $SkipRender) {
    Invoke-Step "3/7 Рендер карточек" {
        $pyArgs = @((Join-Path $RenderDir "render_cards.py"), "--all", "--batch-size", $BatchSize, "--prune")
        if ($OnlyNew) { $pyArgs += "--only-new" }
        if ($TwoX) { $pyArgs += "--2x" }
        & $Python @pyArgs
        if ($LASTEXITCODE -eq 2) { throw "рендер не смог запуститься" }
    }
} else { Write-Host "3/7 Рендер: пропущен (-SkipRender)" }

Invoke-Step "4/7 Контакт-листы карусели (4 слайда подряд)" { & $Python (Join-Path $RenderDir "make_carousels.py") }
Invoke-Step "5/7 Копии для QA читаемости (540/390)" { & $Python (Join-Path $RenderDir "make_readability.py") }
Invoke-Step "6/7 Галерея-карусель (печатный стиль)" { & $Python (Join-Path $RenderDir "gallery.py") }
Invoke-Step "7/7 Чек-лист" { & $Python (Join-Path $RenderDir "check_files.py") }

Write-Host ""
if ($Fail -gt 0) {
    Write-Host ("ПРОГОН: есть незавершённые шаги (" + $Fail + ")") -ForegroundColor Yellow
    exit 1
}
Write-Host "ПРОГОН: все шаги выполнены." -ForegroundColor Green
exit 0
