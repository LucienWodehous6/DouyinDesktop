# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 开箱即用单目录打包"""

import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

# ── 数据文件 ──
# douyin_browser_automation.py 不打包 — 运行时从 EXE_DIR/scripts/ 加载（保护核心代码）
datas = []
for py_file in (PROJECT_DIR / "app").rglob("*.py"):
    rel = py_file.relative_to(PROJECT_DIR)
    datas.append((str(py_file), str(rel.parent)))

# 递归收集 app/ 下的子目录
for sub_dir in (PROJECT_DIR / "app").rglob("*"):
    if sub_dir.is_dir() and sub_dir.name != "__pycache__":
        datas.append((str(sub_dir), str(sub_dir.relative_to(PROJECT_DIR))))

# ── 隐藏导入 ──
hiddenimports = [
    # 应用模块
    "app", "app.main_window", "app.worker", "app.styles", "app.theme",
    "app.widgets", "app.widgets.search_panel", "app.widgets.progress_panel",
    "app.widgets.results_panel", "app.widgets.environment_panel",
    "app.widgets.settings_dialog",
    # douyin_browser_automation 从外部 scripts/ 加载，不打包
    # PyQt6
    "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
    "PyQt6.sip",
    # Playwright
    "playwright", "playwright.sync_api", "playwright._impl",
    "playwright._impl._api_structures", "playwright._impl._browser",
    "playwright._impl._browser_context", "playwright._impl._page",
    "playwright._impl._connection", "playwright._impl._transport",
    "playwright._impl._object_factory",
    "playwright.async_api",
    "playwright.driver",
    # 标准库（可能被 tree-shaking 误删）
    "json", "asyncio", "threading", "urllib", "http.client",
    "shutil", "subprocess", "pathlib", "datetime",
]

# ── 排除项 ──
excludes = [
    "tkinter", "unittest", "test", "pydoc",
    "email", "html", "xml", "xmlrpc",
    "pdb", "profile", "cProfile",
]

# ── 分析 ──
a = Analysis(
    [str(PROJECT_DIR / "main.py")],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ── 收集 Playwright driver ──
def find_playwright_driver():
    """找到 playwright driver 路径"""
    try:
        import playwright
        driver_dir = os.path.dirname(playwright.__file__)
        driver_path = os.path.join(driver_dir, "driver")
        if os.path.exists(driver_path):
            return driver_path
    except Exception:
        pass

    # 备选：在 site-packages 中搜索
    for p in sys.path:
        candidate = os.path.join(p, "playwright", "driver")
        if os.path.exists(candidate):
            return candidate
    return None

driver_path = find_playwright_driver()
if driver_path:
    from PyInstaller.utils.hooks import collect_data_files
    driver_datas = collect_data_files("playwright")
    for src, dst in driver_datas:
        if "driver" in src:
            datas.append((src, os.path.dirname(dst)))

# ── EXE ──
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DouyinScraperPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_DIR / "resources" / "icon.ico") if (PROJECT_DIR / "resources" / "icon.ico").exists() else None,
)

# ── 收集分发文件 ──
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DouyinScraperPro",
)
