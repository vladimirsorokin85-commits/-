@echo off
setlocal
copy /b s01e04_full.mp4.part00+s01e04_full.mp4.part01+s01e04_full.mp4.part02 s01e04_full.mp4 >nul
if errorlevel 1 (
  echo Ошибка сборки MP4.
  exit /b 1
)
echo Готово: s01e04_full.mp4
echo Проверьте SHA-256 по файлу s01e04_full.mp4.sha256.
certutil -hashfile s01e04_full.mp4 SHA256
pause
