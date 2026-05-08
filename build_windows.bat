@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d %~dp0

echo =============================================
echo   Douyin Scraper Pro - Windows Build
echo =============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ not found
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed
    pause
    exit /b 1
)

echo [2/5] Installing Playwright Chromium...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Playwright installation failed
    pause
    exit /b 1
)

echo [3/5] Building...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller DouyinScraperPro.spec --noconfirm

if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo [4/5] Copying core scripts...

if not exist "dist\core_modules" mkdir "dist\core_modules"

if exist "core_modules\douyin_browser_automation.py" (
    copy /Y "core_modules\douyin_browser_automation.py" "dist\core_modules\" >nul
    echo   [OK] douyin_browser_automation.py
)

if exist "core_modules\xhs_search.py" (
    copy /Y "core_modules\xhs_search.py" "dist\core_modules\" >nul
    echo   [OK] xhs_search.py
)

if exist "core_modules\douyin_downloader.py" (
    copy /Y "core_modules\douyin_downloader.py" "dist\core_modules\" >nul
    echo   [OK] douyin_downloader.py
)

echo [5/5] Copying browser files...

for /f "tokens=*" %%i in ('python -c "import os; p=os.environ.get('LOCALAPPDATA',''); print(os.path.join(p, 'ms-playwright') if p else '')"') do set BROWSER_CACHE=%%i
if not exist "%BROWSER_CACHE%" (
    for /f "tokens=*" %%i in ('python -c "import os; print(os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright'))"') do set BROWSER_CACHE=%%i
)

if exist "%BROWSER_CACHE%" (
    echo   Cache: %BROWSER_CACHE%
    if not exist "dist\playwright_browsers" mkdir "dist\playwright_browsers"
    xcopy /E /I /Y "%BROWSER_CACHE%\*" "dist\playwright_browsers\"
    echo ok > "dist\playwright_browsers\.installed"
    echo   [OK] Browser embedded
) else (
    echo   [SKIP] Cache not found, will prompt install at first run
)

echo.
echo =============================================
echo   Build complete!
echo   Output: dist\DouyinScraperPro.exe
echo.
echo   Distribute these together:
echo     - DouyinScraperPro.exe
echo     - core_modules\  (core scripts)
echo     - playwright_browsers\  (optional)
echo =============================================
pause