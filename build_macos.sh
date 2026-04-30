#!/bin/bash
set -e

echo "========================================"
echo "  Douyin Scraper Pro — macOS/Linux 打包"
echo "========================================"
echo ""

echo "[1/4] 安装依赖..."
pip install -r requirements.txt -q

echo "[2/4] 安装 Playwright 浏览器..."
python -m playwright install chromium

echo "[3/4] 清理旧构建..."
rm -rf build dist

echo "[4/4] 开始打包..."
pyinstaller DouyinScraperPro.spec --noconfirm

echo ""
echo "========================================"
echo "  打包成功！"
echo "  输出: dist/DouyinScraperPro"
echo "========================================"
