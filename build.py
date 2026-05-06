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


def run(cmd, desc=""):
    print(f"  {desc}")
    result = subprocess.run(cmd, shell=True, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print(f"\n[错误] {desc} 失败")
        sys.exit(1)


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

    # 4. PyInstaller 打包
    run(f'"{sys.executable}" -m PyInstaller DouyinScraperPro.spec --noconfirm', "PyInstaller 打包")

    # 5. 复制核心脚本到 dist\core_modules（支持运行时动态加载）
    print("  复制核心脚本...")
    core_scripts = ["douyin_browser_automation.py", "xhs_search.py", "douyin_downloader.py"]
    core_dst = PROJECT_DIR / "dist" / "core_modules"
    core_dst.mkdir(exist_ok=True)
    for script in core_scripts:
        src = PROJECT_DIR / "core_modules" / script
        if src.exists():
            shutil.copy2(src, core_dst / script)
            print(f"  [OK] {script}")
    print("  [OK] 核心脚本复制完成")

    # 6. 复制 Playwright 浏览器到 dist
    print("  复制浏览器文件...")
    browsers_src = None
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            browsers_src = c
            break

    browsers_dst = PROJECT_DIR / "dist" / "playwright_browsers"
    if browsers_src:
        if browsers_dst.exists():
            shutil.rmtree(browsers_dst)
        shutil.copytree(browsers_src, browsers_dst)
        (browsers_dst / ".installed").write_text("ok")
        print(f"  [OK] 浏览器已复制")
    else:
        print("  [跳过] 未找到缓存，首次运行提示安装")

    print()
    print("=" * 50)
    exe_name = "DouyinScraperPro.exe" if sys.platform == "win32" else "DouyinScraperPro"
    print(f"  打包完成！输出: dist/{exe_name}")
    print(f"  核心脚本: dist/core_modules/")
    print("=" * 50)


if __name__ == "__main__":
    main()
