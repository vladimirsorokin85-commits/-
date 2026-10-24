@echo off
chcp 65001 >nul
title YouTube Market Research - V Okopé

echo ========================================
echo  YOUTUBE MARKET RESEARCH "V OKOPE"
echo ========================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Install Python from python.org
    echo and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/5] Python found
python --version

:: Install yt-dlp
echo.
echo [2/5] Installing yt-dlp...
python -m pip install -U yt-dlp --quiet

:: Create folder
if not exist "market_research" mkdir market_research
cd market_research

:: Download files using Python (works on any Windows)
echo.
echo [3/5] Downloading files...
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/6fcfd4f9-repo/find_outliers.py', 'find_outliers.py')"
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/vladimirsorokin85-commits/-/arena/6fcfd4f9-repo/MILITARY_KEYWORDS.txt', 'MILITARY_KEYWORDS.txt')"

:: Run collection
echo.
echo [4/5] Collecting data (wait a few minutes)...
python find_outliers.py --keywords-file MILITARY_KEYWORDS.txt --out outliers.csv

:: Open result
echo.
echo [5/5] Done!
if exist outliers.csv (
    start outliers.csv
    echo File outliers.csv opened in Excel.
) else (
    echo File not created. Check internet connection.
)

echo.
echo ========================================
echo  DONE. See outliers.csv
echo ========================================
pause
