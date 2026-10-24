@echo off
chcp 65001 >nul
title Исследование рынка YouTube - В Окопе

echo ========================================
echo  ИССЛЕДОВАНИЕ РЫНКА YOUTUBE "В ОКОПЕ"
echo ========================================
echo.

:: Проверка Python
where python >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден.
    echo Установите Python с сайта python.org
    echo и поставьте галочку "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/5] Python найден
python --version

:: Установка yt-dlp
echo.
echo [2/5] Установка yt-dlp...
python -m pip install -U yt-dlp --quiet

:: Папка для результата
if not exist "market_research" mkdir market_research
cd market_research

:: Скачивание файлов с GitHub
echo.
echo [3/5] Скачивание файлов...
powershell -command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/6fcfd4f9-repo/find_outliers.py' -OutFile 'find_outliers.py'"
powershell -command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/6fcfd4f9-repo/MILITARY_KEYWORDS.txt' -OutFile 'MILITARY_KEYWORDS.txt'"

:: Запуск сбора данных
echo.
echo [4/5] Запуск сбора данных (подождите несколько минут)...
python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --out outliers.csv

:: Открытие результата
echo.
echo [5/5] Готово!
if exist outliers.csv (
    start outliers.csv
    echo Файл outliers.csv открыт в Excel.
) else (
    echo Файл не создан. Проверьте интернет-подключение.
)

echo.
echo ========================================
echo  ГОТОВО. Смотрите файл outliers.csv
echo ========================================
pause
