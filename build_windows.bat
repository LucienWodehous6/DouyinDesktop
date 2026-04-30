@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =============================================
echo   Douyin Scraper Pro — Windows 打包
echo =============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python 3.10+
    pause
    exit /b 1
)

:: 1. 安装依赖
echo [1/4] 安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 2. 安装 Playwright Chromium（打包前缓存）
echo [2/4] 安装 Playwright Chromium...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [错误] Playwright 安装失败
    pause
    exit /b 1
)

:: 3. 清理 + 打包
echo [3/4] 开始打包...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller DouyinScraperPro.spec --noconfirm

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 4. 复制浏览器文件到 exe 同目录（首次运行自动复用）
echo [4/4] 复制浏览器文件...

:: 找 Playwright 缓存
for /f "tokens=*" %%i in ('python -c "import os; p=os.environ.get('LOCALAPPDATA',''); print(os.path.join(p, 'ms-playwright') if p else '')"') do set BROWSER_CACHE=%%i
if not exist "%BROWSER_CACHE%" (
    for /f "tokens=*" %%i in ('python -c "import os; print(os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright'))"') do set BROWSER_CACHE=%%i
)

if exist "%BROWSER_CACHE%" (
    echo   缓存路径: %BROWSER_CACHE%
    if not exist "dist\playwright_browsers" mkdir "dist\playwright_browsers"
    xcopy /E /I /Y "%BROWSER_CACHE%\*" "dist\playwright_browsers\"
    echo ok > "dist\playwright_browsers\.installed"
    echo   [OK] 浏览器已内嵌
) else (
    echo   [跳过] 未找到缓存，首次运行会提示安装
)

echo.
echo =============================================
echo   打包完成！
echo   输出: dist\DouyinScraperPro.exe
echo.
echo   将 DouyinScraperPro.exe 和 playwright_browsers\
echo   一起复制到任意电脑即可运行。
echo =============================================
pause
