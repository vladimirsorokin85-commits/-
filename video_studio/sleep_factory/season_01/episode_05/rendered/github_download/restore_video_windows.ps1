param([string]$ExpectedSha256 = '6412a49524d0d32ee73e192d6740d609b9f96fcf79d59daa3766ccee98f2c0ea')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$expected = $ExpectedSha256.Trim().ToLowerInvariant()
$embeddedExpected = '6412a49524d0d32ee73e192d6740d609b9f96fcf79d59daa3766ccee98f2c0ea'
if ($expected -ne $embeddedExpected) {
    throw 'The checksum passed by the BAT does not match this helper.'
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$filename = 's01e05_full.mp4'
$parts = @(
    [pscustomobject]@{ Name = 's01e05_full.mp4.part00'; Size = 78643200; Url = 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/edfffcf3-repo/video_studio/sleep_factory/season_01/episode_05/rendered/github_download/s01e05_full.mp4.part00' }
    [pscustomobject]@{ Name = 's01e05_full.mp4.part01'; Size = 78643200; Url = 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/edfffcf3-repo/video_studio/sleep_factory/season_01/episode_05/rendered/github_download/s01e05_full.mp4.part01' }
    [pscustomobject]@{ Name = 's01e05_full.mp4.part02'; Size = 5073788; Url = 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/edfffcf3-repo/video_studio/sleep_factory/season_01/episode_05/rendered/github_download/s01e05_full.mp4.part02' }
)
$destination = Join-Path $root $filename
$temp = $destination + '.tmp'

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    foreach ($part in $parts) {
        $partPath = Join-Path $root $part.Name
        $download = -not (Test-Path -LiteralPath $partPath)
        if (-not $download) {
            $download = (Get-Item -LiteralPath $partPath).Length -ne $part.Size
        }
        if ($download) {
            if (Test-Path -LiteralPath $partPath) {
                Remove-Item -LiteralPath $partPath -Force
            }
            Write-Host ("Downloading missing/incomplete part: " + $part.Name)
            $attempt = 0
            while ($attempt -lt 3) {
                $attempt++
                try {
                    Invoke-WebRequest -UseBasicParsing -Uri $part.Url -OutFile $partPath
                    break
                } catch {
                    if (Test-Path -LiteralPath $partPath) {
                        Remove-Item -LiteralPath $partPath -Force
                    }
                    if ($attempt -ge 3) { throw }
                    Start-Sleep -Seconds (2 * $attempt)
                }
            }
        } else {
            Write-Host ("Using downloaded part: " + $part.Name)
        }
        $actualSize = (Get-Item -LiteralPath $partPath).Length
        if ($actualSize -ne $part.Size) {
            throw ("Wrong size for " + $part.Name + ": expected " + $part.Size + ", got " + $actualSize)
        }
    }

    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force
    }
    $outputStream = [System.IO.File]::Open(
        $temp,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        foreach ($part in $parts) {
            $partPath = Join-Path $root $part.Name
            $inputStream = [System.IO.File]::OpenRead($partPath)
            try {
                $inputStream.CopyTo($outputStream)
            } finally {
                $inputStream.Dispose()
            }
        }
    } finally {
        $outputStream.Dispose()
    }

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($temp)
    try {
        $actual = ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
    if ($actual -ne $expected) {
        throw ("SHA-256 mismatch. Expected " + $expected + "; got " + $actual)
    }

    Move-Item -LiteralPath $temp -Destination $destination -Force
    Write-Host ("Restored and verified: " + $destination)
    Write-Host ("SHA-256: " + $actual)
} catch {
    Write-Host ("Restore failed: " + $_.Exception.Message) -ForegroundColor Red
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force
    }
    exit 1
}
