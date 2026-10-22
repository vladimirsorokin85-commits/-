@echo off
setlocal EnableExtensions
cd /d "%~dp0"

for %%F in (s01e05_full.mp4.part00 s01e05_full.mp4.part01 s01e05_full.mp4.part02) do (
  if not exist "%%F" (
    echo Missing file: %%F
    pause
    exit /b 1
  )
)

copy /b /y s01e05_full.mp4.part00+s01e05_full.mp4.part01+s01e05_full.mp4.part02 s01e05_full.mp4 >nul
if errorlevel 1 (
  echo Failed to assemble s01e05_full.mp4.
  pause
  exit /b 1
)

set "EXPECTED=6412a49524d0d32ee73e192d6740d609b9f96fcf79d59daa3766ccee98f2c0ea"
set "ACTUAL="
for /f "delims=" %%H in ('certutil -hashfile s01e05_full.mp4 SHA256 ^| findstr /r /i "^[0-9a-f][0-9a-f]*$"') do set "ACTUAL=%%H"
if not defined ACTUAL (
  echo Could not calculate the MP4 SHA-256.
  pause
  exit /b 1
)
if /i not "%ACTUAL%"=="%EXPECTED%" (
  echo SHA-256 mismatch. Check the downloaded parts.
  echo Expected: %EXPECTED%
  echo Actual:   %ACTUAL%
  pause
  exit /b 1
)

echo Restored and verified: s01e05_full.mp4
echo SHA-256: %ACTUAL%
pause
