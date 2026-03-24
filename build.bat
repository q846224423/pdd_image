@echo off
chcp 65001 >nul
title Build - Image Spider

echo.
echo ========================================
echo   Image Spider - Build Script
echo ========================================
echo.

echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause & exit /b 1
)
echo       OK

echo [2/7] Installing dependencies...
pip install pyinstaller pillow playwright requests PyQt6 -q
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause & exit /b 1
)
echo       OK

echo [3/7] Installing Playwright Chromium...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Playwright install failed
    pause & exit /b 1
)
echo       OK

echo [4/7] Converting logo...
if exist logo.png (
    python -c "from PIL import Image; img=Image.open('logo.png'); img.save('logo.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32)])"
    set ICON_ARG=--icon=logo.ico
    echo       OK - logo.ico created
) else (
    set ICON_ARG=
    echo       SKIP - logo.png not found
)

echo [5/7] Cleaning old build...
if exist "dist\ImageSpider" rmdir /s /q "dist\ImageSpider"
if exist build rmdir /s /q build
if exist "ImageSpider.spec" del /q "ImageSpider.spec"
echo       OK

echo [6/7] Building...
echo.

pyinstaller ^
  --noconsole ^
  --onedir ^
  --name "ImageSpider" ^
  %ICON_ARG% ^
  --add-data "logo.png;." ^
  --add-data "platforms;platforms" ^
  --add-data "ui;ui" ^
  --hidden-import playwright ^
  --collect-all playwright ^
  --hidden-import PIL ^
  --hidden-import requests ^
  --collect-all PyQt6 ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check output above.
    pause & exit /b 1
)

echo [7/7] Copying files...
if exist logo.png copy /y logo.png "dist\ImageSpider\" >nul
if exist logo.ico copy /y logo.ico "dist\ImageSpider\" >nul
if not exist "dist\ImageSpider\user_data" mkdir "dist\ImageSpider\user_data"

echo.
echo ========================================
echo   Build complete!
echo   Output: dist\ImageSpider\
echo ========================================
echo.
echo Notes:
echo   1. First run requires login to XHS
echo   2. Do NOT delete user_data folder
echo   3. Do NOT delete config.json
echo.

explorer "dist\ImageSpider"
pause
