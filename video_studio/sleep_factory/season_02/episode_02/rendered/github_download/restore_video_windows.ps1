param([string]$ExpectedSha256 = 'db2e1639550ede5576b2305ef9dce10b5bf397be3db8a1e061950c5c6b22a406')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$expected = $ExpectedSha256.Trim().ToLowerInvariant()
$embeddedExpected = 'db2e1639550ede5576b2305ef9dce10b5bf397be3db8a1e061950c5c6b22a406'
if ($expected -ne $embeddedExpected) {
    throw 'The checksum passed by the BAT does not match this helper.'
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$filename = 's02e02_full.mp4'
$parts = @(
    [pscustomobject]@{ Name = 's02e02_full.mp4.part00'; Size = 60524036; Url = 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/edfffcf3-repo/video_studio/sleep_factory/season_02/episode_02/rendered/github_download/s02e02_full.mp4.part00' }
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
