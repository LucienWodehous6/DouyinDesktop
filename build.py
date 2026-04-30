"""
一键打包脚本 — Windows/macOS 通用
运行: python build.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DIST_DIR = PROJECT_DIR / "dist" / "DouyinScraperPro"


def run(cmd, desc=""):
    print(f"  {desc}")
    result = subprocess.run(cmd, shell=True, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print(f"\n[错误] {desc} 失败")
        sys.exit(1)
    print(f"  [OK] {desc}")


def main():
    print("=" * 50)
    print("  Douyin Scraper Pro — 一键打包")
    print("=" * 50)
    print()

    # 1. 安装依赖
    run(f'"{sys.executable}" -m pip install -r requirements.txt -q', "安装依赖")

    # 2. 安装 Playwright Chromium
    run(f'"{sys.executable}" -m playwright install chromium', "安装 Chromium")

    # 3. 清理
    for d in ["build", "dist"]:
        path = PROJECT_DIR / d
        if path.exists():
            shutil.rmtree(path)
    print("  [OK] 清理旧构建")

    # 4. PyInstaller 打包
    run(f'"{sys.executable}" -m PyInstaller DouyinScraperPro.spec --noconfirm --clean', "PyInstaller 打包")

    # 5. 复制 Playwright 浏览器
    print("  复制浏览器文件...")
    browsers_src = None
    candidates = [
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            browsers_src = c
            break

    browsers_dst = DIST_DIR / "playwright_browsers"
    if browsers_src and os.path.isdir(browsers_src):
        if browsers_dst.exists():
            shutil.rmtree(browsers_dst)
        shutil.copytree(browsers_src, browsers_dst)
        (browsers_dst / ".installed").write_text("ok")
        print(f"  [OK] 浏览器已复制 ({browsers_src})")
    else:
        print("  [跳过] 未找到浏览器缓存，首次运行自动下载")

    # 5. 创建 scripts/ 目录（核心脚本外部加载，不打包）
    scripts_dst = DIST_DIR / "scripts"
    scripts_dst.mkdir(exist_ok=True)
    readme_path = scripts_dst / "README.txt"
    readme_path.write_text(
        "请将 douyin_browser_automation.py 放入此目录\n"
        "==============================================\n"
        "此文件是应用的核心采集脚本，出于安全原因未打包进应用。\n"
        "请联系开发者获取最新版本。\n",
        encoding="utf-8"
    )
    print(f"  [OK] scripts/ 目录已创建")

    # 6. 复制额外文件
    for extra in ["README.md"]:
        src = PROJECT_DIR / extra
        if src.exists():
            shutil.copy(src, DIST_DIR / extra)

    print()
    print("=" * 50)
    print(f"  打包完成！")
    print(f"  输出: {DIST_DIR}")
    if sys.platform == "win32":
        print(f"  运行: {DIST_DIR / 'DouyinScraperPro.exe'}")
    else:
        print(f"  运行: {DIST_DIR / 'DouyinScraperPro'}")
    print("=" * 50)


if __name__ == "__main__":
    main()
