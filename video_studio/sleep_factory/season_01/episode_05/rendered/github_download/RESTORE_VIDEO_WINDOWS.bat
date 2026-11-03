@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 (
  echo Could not switch to the package folder: "%~dp0"
  pause
  exit /b 1
)
set "EXPECTED_SHA256=6412a49524d0d32ee73e192d6740d609b9f96fcf79d59daa3766ccee98f2c0ea"
set "EXPECTED_HELPER_SHA256=ed585e28368effe0f470f6be216944500178e3195dd65e3678fb07a117f5c6bc"
set "HELPER=restore_video_windows.ps1"
set "PSEXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PSEXE%" set "PSEXE=powershell.exe"
if /i "%PSEXE%"=="powershell.exe" (
  where powershell.exe >nul 2>nul
  if errorlevel 1 (
    echo Windows PowerShell is required but was not found.
    pause
    exit /b 1
  )
)

call :verify_helper
if errorlevel 1 goto download_helper
goto start_restore

:download_helper
echo Downloading or refreshing the small restore helper from GitHub...
del /q "%HELPER%" 2>nul
"%PSEXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [System.Net.ServicePointManager]::SecurityProtocol=[System.Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/edfffcf3-repo/video_studio/sleep_factory/season_01/episode_05/rendered/github_download/restore_video_windows.ps1' -OutFile 'restore_video_windows.ps1' -ErrorAction Stop"
if errorlevel 1 goto helper_download_failed
call :verify_helper
if errorlevel 1 goto helper_hash_failed
goto start_restore

:start_restore
echo Restoring s01e05_full.mp4. Missing or incomplete parts will be downloaded from GitHub.
"%PSEXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0%HELPER%" -ExpectedSha256 "%EXPECTED_SHA256%"
if errorlevel 1 goto restore_failed
echo The complete video has been restored and verified in this folder.
pause
exit /b 0

:helper_download_failed
echo Could not download the helper. Check your GitHub connection or download restore_video_windows.ps1 manually beside this BAT.
pause
exit /b 1

:helper_hash_failed
echo The restore helper failed its SHA-256 check.
pause
exit /b 1

:restore_failed
echo Restore failed. Read the PowerShell error above and try again.
pause
exit /b 1

:verify_helper
set "ACTUAL_HELPER_SHA256="
if not exist "%HELPER%" exit /b 1
for /f "delims=" %%H in ('certutil -hashfile "%HELPER%" SHA256 ^| findstr /r /i "^[0-9a-f][0-9a-f]*$"') do set "ACTUAL_HELPER_SHA256=%%H"
if /i not "%ACTUAL_HELPER_SHA256%"=="%EXPECTED_HELPER_SHA256%" exit /b 1
exit /b 0
