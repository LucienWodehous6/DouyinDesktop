# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 单文件可执行"""

import sys, os
from pathlib import Path

PROJECT_DIR = Path(os.path.dirname(os.path.abspath(SPECPATH)))
if not (PROJECT_DIR / "main.py").exists():
    PROJECT_DIR = Path(os.getcwd())

datas = [
    (str(PROJECT_DIR / "models"), "models"),
]
for py_file in (PROJECT_DIR / "app").rglob("*.py"):
    rel = py_file.relative_to(PROJECT_DIR)
    datas.append((str(py_file), str(rel.parent)))

hiddenimports = [
    "app", "app.main_window", "app.worker", "app.styles", "app.theme",
    "app.widgets", "app.widgets.search_panel", "app.widgets.progress_panel",
    "app.widgets.results_panel",    "app.widgets.environment_panel",
    "app.widgets.settings_dialog", "app.widgets.settings_page",
    "app.widgets.script_panel",
    "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "PyQt6.sip",
    "playwright", "playwright.sync_api",
    "json", "asyncio", "threading", "urllib", "shutil", "subprocess",
    "html", "html.parser",
]

excludes = ["tkinter", "unittest", "pydoc", "xml"]

a = Analysis(
    [str(PROJECT_DIR / "main.py")],
    pathex=[str(PROJECT_DIR)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DouyinScraperPro",
    console=True,
    strip=False,
    upx=True,
    target_arch=None,
)
