@echo off
setlocal
copy /b s01e03_full.mp4.part00+s01e03_full.mp4.part01 s01e03_full.mp4 >nul
if errorlevel 1 (
  echo Ошибка сборки MP4.
  exit /b 1
)
echo Готово: s01e03_full.mp4
pause
