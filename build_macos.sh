#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  Douyin Scraper Pro — macOS 打包"
echo "========================================"
echo ""

echo "[1/4] 安装依赖..."
pip install -r requirements.txt -q

echo "[2/4] 安装 Playwright Chromium..."
python -m playwright install chromium

echo "[3/4] 清理 + 打包..."
rm -rf build dist
pyinstaller DouyinScraperPro.spec --noconfirm --clean

echo "[4/4] 复制浏览器到 .app..."
RESOURCES="dist/DouyinScraperPro.app/Contents/Resources"
BROWSERS="$RESOURCES/playwright_browsers"
mkdir -p "$BROWSERS"

# 找最新版 Chromium
CHROMIUM=$(ls -d ~/Library/Caches/ms-playwright/chromium-* 2>/dev/null | sort -V | tail -1)
if [ -n "$CHROMIUM" ]; then
    cp -r "$CHROMIUM" "$BROWSERS/"
    echo "ok" > "$BROWSERS/.installed"
    echo "  [OK] Chromium 已内嵌"
else
    echo "  [跳过] 未找到 Chromium，首次运行自动下载"
fi

echo ""
echo "========================================"
echo "  打包完成！"
echo "  输出: dist/DouyinScraperPro.app"
echo "  大小: $(du -sh dist/DouyinScraperPro.app | cut -f1)"
echo "========================================"
