"""抖音数据采集桌面应用入口 — 开箱即用"""

import sys
import os
import subprocess

# PyInstaller 打包路径
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# 设置 Playwright 浏览器路径（打包后的目录）
PLAYWRIGHT_BROWSERS = os.path.join(EXE_DIR, "playwright_browsers")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", PLAYWRIGHT_BROWSERS)


def ensure_playwright_browsers():
    """首次运行自动安装 Playwright Chromium"""
    marker = os.path.join(PLAYWRIGHT_BROWSERS, ".installed")
    if os.path.exists(marker):
        return True

    try:
        import playwright.sync_api
        print("[Setup] 首次运行，正在安装浏览器组件...")
        print("[Setup] 这可能需要几分钟，请耐心等待。")

        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            cwd=EXE_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            os.makedirs(PLAYWRIGHT_BROWSERS, exist_ok=True)
            with open(marker, "w") as f:
                f.write("ok")
            print("[Setup] 浏览器组件安装完成！")
            return True
        else:
            print(f"[Setup] 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"[Setup] 初始化异常: {e}")
        return False


if __name__ == "__main__":
    ensure_playwright_browsers()
    from app.main_window import main
    main()
