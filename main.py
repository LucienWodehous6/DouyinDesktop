"""社交媒体数据采集桌面应用入口"""

import sys
import os
import shutil
import subprocess

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# 浏览器安装到可写目录
BROWSERS_DIR = os.path.join(EXE_DIR, "playwright_browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
# 国内镜像加速
os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = "https://npmmirror.com/mirrors/playwright/"


def find_chromium():
    """查找已安装的 Chromium"""
    if not os.path.isdir(BROWSERS_DIR):
        return None
    for d in os.listdir(BROWSERS_DIR):
        if d.startswith("chromium-") or d.startswith("chrome-"):
            return os.path.join(BROWSERS_DIR, d)
    return None


def ensure_browsers():
    """确保 Chromium 可用（优先用系统缓存，否则提示安装）"""
    if find_chromium():
        return True

    # 尝试从系统 Playwright 缓存复用
    import playwright
    pw_dir = os.path.dirname(playwright.__file__)
    # 默认缓存路径（按平台优先级）
    if sys.platform == "win32":
        caches = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
            os.path.expanduser("~/.cache/ms-playwright"),
        ]
    elif sys.platform == "darwin":
        caches = [
            os.path.expanduser("~/Library/Caches/ms-playwright"),
            os.path.expanduser("~/.cache/ms-playwright"),
        ]
    else:
        caches = [
            os.path.expanduser("~/.cache/ms-playwright"),
        ]

    for cache in caches:
        if not cache or not os.path.isdir(cache):
            continue
        for d in sorted(os.listdir(cache), reverse=True):
            if d.startswith("chromium-") or d.startswith("chrome-"):
                src = os.path.join(cache, d)
                dst = os.path.join(BROWSERS_DIR, d)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                print(f"  复用已有浏览器: {d}")
                shutil.copytree(src, dst)
                return True

    # 都没有，提示用户手动安装
    print("=" * 50)
    print("  未找到浏览器组件")
    print("")
    print("  请手动执行以下命令：")
    print(f"  PLAYWRIGHT_BROWSERS_PATH={BROWSERS_DIR}")
    print(f"  playwright install chromium")
    print("")
    print("  或从已安装 Playwright 的电脑复制")
    print(f"  ~/Library/Caches/ms-playwright/chromium-*")
    print(f"  到 {BROWSERS_DIR}")
    print("=" * 50)
    return False


if __name__ == "__main__":
    if not ensure_browsers():
        print("\n[错误] 浏览器组件下载失败，请检查网络后重试。")
        input("按 Enter 退出...")
        sys.exit(1)

    from app.main_window import main
    main()
