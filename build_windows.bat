@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =============================================
echo   Douyin Scraper Pro — 开箱即用打包
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
echo [1/5] 安装依赖...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 2. 安装 Playwright（需在打包前安装浏览器到默认位置）
echo [2/5] 安装 Playwright Chromium...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [错误] Playwright 浏览器安装失败
    pause
    exit /b 1
)

:: 3. 找到 Chromium 路径（打包进输出目录）
echo [3/5] 准备浏览器文件...
for /f "tokens=*" %%i in ('python -c "import playwright; import os; p=os.path.dirname(playwright.__file__); print(os.path.dirname(p))"') do set PW_DIR=%%i
echo Playwright 路径: %PW_DIR%

:: 4. 清理旧构建
echo [4/5] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 5. 打包
echo [5/5] 开始打包（这需要几分钟）...
pyinstaller DouyinScraperPro.spec --noconfirm

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 6. 复制 Playwright browsers 到输出目录
echo [6/6] 复制浏览器文件...

:: 获取 Playwright browsers 路径
for /f "tokens=*" %%i in ('python -c "import os; p=os.environ.get('PLAYWRIGHT_BROWSERS_PATH',''); print(p if p else os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright'))"') do set BROWSER_CACHE=%%i

if exist "%BROWSER_CACHE%" (
    echo 复制浏览器从: %BROWSER_CACHE%
    if not exist "dist\DouyinScraperPro\playwright_browsers" mkdir "dist\DouyinScraperPro\playwright_browsers"
    xcopy /E /I /Y "%BROWSER_CACHE%\*" "dist\DouyinScraperPro\playwright_browsers\"
    :: 标记已安装
    echo ok > "dist\DouyinScraperPro\playwright_browsers\.installed"
    echo [OK] 浏览器文件已复制
) else (
    echo [警告] 未找到 Playwright 浏览器缓存，首次运行时会自动下载
)

echo.
echo =============================================
echo   打包完成！
echo   输出目录: dist\DouyinScraperPro\
echo   运行: dist\DouyinScraperPro\DouyinScraperPro.exe
echo =============================================
echo.
echo 提示：将整个 DouyinScraperPro 文件夹复制到
echo       任意电脑即可运行，无需安装 Python。
echo.
pause
