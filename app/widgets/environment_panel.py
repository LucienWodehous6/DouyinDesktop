"""环境检查面板 — 检测 Chrome + CDP，自动启动，抖音登录"""

import os
import sys
import subprocess
import tempfile
import urllib.request
import urllib.error
import json
import shutil
import threading

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGroupBox, QLineEdit,
    QMessageBox,
)

# Chrome 可执行文件路径（按平台）
_CHROME_PATHS = {
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "win32": [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expandvars("%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe"),
    ],
    "linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ],
}

COOKIE_DIR = os.path.join(os.path.expanduser("~"), ".dy", "cookies")
DEFAULT_COOKIE_FILE = os.path.join(COOKIE_DIR, "default.json")


def find_chrome() -> str | None:
    paths = _CHROME_PATHS.get(sys.platform, [])
    paths.append(shutil.which("google-chrome") or "")
    paths.append(shutil.which("chromium") or "")
    paths.append(shutil.which("chrome") or "")
    for p in paths:
        if p and os.path.exists(p):
            if sys.platform == "darwin":
                if p.endswith(".app"):
                    p = os.path.join(p, "Contents/MacOS/Google Chrome")
                elif "Google Chrome" not in p:
                    continue
            if os.access(p, os.X_OK) or sys.platform == "win32":
                return p
    return None


def check_cdp(cdp_url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(f"{cdp_url}/json/version", method="GET")
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return "Browser" in data
    except Exception:
        return False


def start_chrome_cdp(chrome_path: str, port: int = 9222, user_data_dir: str = "") -> bool:
    if not user_data_dir:
        user_data_dir = os.path.join(tempfile.gettempdir(), "chrome-cdp-profile")

    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if sys.platform == "darwin":
        args.insert(1, "--args")

    try:
        if sys.platform == "win32":
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def open_douyin_login(cdp_url: str):
    """通过 Playwright CDP 打开抖音首页"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            if browser.contexts:
                ctx = browser.contexts[0]
                pages = ctx.pages
                if pages:
                    page = pages[0]
                    page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
                    return True
            # 没有页面则创建
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
            return True
    except Exception:
        return False


def extract_cookies_cdp(cdp_url: str) -> list | None:
    """通过 Playwright CDP 提取浏览器 Cookies"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            if browser.contexts:
                ctx = browser.contexts[0]
                all_cookies = ctx.cookies()
                # 过滤 douyin.com 相关
                douyin_cookies = [
                    c for c in all_cookies
                    if "douyin.com" in c.get("domain", "")
                ]
                if douyin_cookies:
                    # 转为可序列化格式
                    result = []
                    for c in douyin_cookies:
                        result.append({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c["domain"],
                            "path": c.get("path", "/"),
                            "expires": c.get("expires", -1),
                            "httpOnly": c.get("httpOnly", False),
                            "secure": c.get("secure", False),
                            "sameSite": c.get("sameSite", "Lax"),
                        })
                    return result
            return None
    except Exception:
        return None


class StatusRow(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)
        self.dot = QLabel("●")
        self.dot.setFixedWidth(20)
        layout.addWidget(self.dot)
        layout.addWidget(QLabel(label))
        self.status_label = QLabel("检测中...")
        self.status_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.status_label)
        layout.addStretch()


class EnvironmentPanel(QWidget):
    ready_changed = pyqtSignal(bool)
    cookie_saved = pyqtSignal(str)  # cookie 文件路径

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._ready = False
        self._login_in_progress = False
        self.chrome_path = find_chrome()
        self._init_ui()
        QTimer.singleShot(500, self.check_all)

        # 每 5 秒自动检测 CDP 状态
        self._cdp_timer = QTimer(self)
        self._cdp_timer.timeout.connect(self._check_cdp_auto)
        self._cdp_timer.start(5000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("⚙ 环境检查 & 账号登录")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ═══════════════ 状态卡片 ═══════════════
        status_card = QGroupBox("运行环境")
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(8)

        self.chrome_row = StatusRow("Chrome 浏览器")
        status_layout.addWidget(self.chrome_row)

        self.cdp_row = StatusRow("CDP 调试端口")
        status_layout.addWidget(self.cdp_row)

        self.cookie_row = StatusRow("Cookie 登录态")
        status_layout.addWidget(self.cookie_row)

        layout.addWidget(status_card)

        # ═══════════════ CDP 地址 ═══════════════
        cdp_card = QGroupBox("CDP 连接地址")
        cdp_layout = QHBoxLayout(cdp_card)
        self.cdp_input = QLineEdit(self.settings.get("cdp_url", "http://127.0.0.1:9222"))
        self.cdp_input.textChanged.connect(lambda: self._update_settings())
        cdp_layout.addWidget(QLabel("地址:"))
        cdp_layout.addWidget(self.cdp_input)
        layout.addWidget(cdp_card)

        # ═══════════════ 操作按钮 ═══════════════
        btn_layout = QHBoxLayout()

        self.start_cdp_btn = QPushButton("🚀 启动 Chrome CDP")
        self.start_cdp_btn.setObjectName("primaryBtn")
        self.start_cdp_btn.clicked.connect(self._start_cdp)
        self.start_cdp_btn.setVisible(False)
        btn_layout.addWidget(self.start_cdp_btn)

        self.login_btn = QPushButton("🔑 登录抖音")
        self.login_btn.setObjectName("primaryBtn")
        self.login_btn.clicked.connect(self._start_login)
        self.login_btn.setVisible(False)
        btn_layout.addWidget(self.login_btn)

        self.complete_login_btn = QPushButton("✅ 完成登录，保存 Cookie")
        self.complete_login_btn.setObjectName("primaryBtn")
        self.complete_login_btn.clicked.connect(self._complete_login)
        self.complete_login_btn.setVisible(False)
        btn_layout.addWidget(self.complete_login_btn)

        self.recheck_btn = QPushButton("🔄 重新检查")
        self.recheck_btn.setObjectName("smallBtn")
        self.recheck_btn.clicked.connect(self.check_all)
        btn_layout.addWidget(self.recheck_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ═══════════════ 提示 ═══════════════
        self.hint = QLabel(
            "步骤：① 启动 Chrome CDP → ② 登录抖音 → ③ 完成登录保存 Cookie"
        )
        self.hint.setObjectName("hintLabel")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        layout.addStretch()

    # ═══════════════ 检查 ═══════════════

    def _check_cdp_auto(self):
        """轻量自动检测：只刷新 CDP 状态和按钮"""
        cdp_url = self.cdp_input.text().strip()
        cdp_ok = check_cdp(cdp_url, timeout=1.0)
        prev_ready = self._ready
        self._ready = cdp_ok

        if cdp_ok:
            self.cdp_row.dot.setStyleSheet("color: #2ed573; font-size: 16px;")
            self.cdp_row.status_label.setText("连接成功")
            self.cdp_row.status_label.setStyleSheet("color: #2ed573;")
        else:
            self.cdp_row.dot.setStyleSheet("color: #f85149; font-size: 16px;")
            self.cdp_row.status_label.setText("未连接")
            self.cdp_row.status_label.setStyleSheet("color: #f85149;")

        self.start_cdp_btn.setVisible(self.chrome_path is not None and not cdp_ok)

        if prev_ready != self._ready:
            self.ready_changed.emit(self._ready)

    def check_all(self):
        cdp_url = self.cdp_input.text().strip()

        # Chrome
        if self.chrome_path:
            self.chrome_row.dot.setStyleSheet("color: #2ed573; font-size: 16px;")
            self.chrome_row.status_label.setText("已检测到")
            self.chrome_row.status_label.setStyleSheet("color: #2ed573;")
        else:
            self.chrome_row.dot.setStyleSheet("color: #f85149; font-size: 16px;")
            self.chrome_row.status_label.setText("未找到")
            self.chrome_row.status_label.setStyleSheet("color: #f85149;")

        # CDP
        cdp_ok = check_cdp(cdp_url)
        if cdp_ok:
            self.cdp_row.dot.setStyleSheet("color: #2ed573; font-size: 16px;")
            self.cdp_row.status_label.setText("连接成功")
            self.cdp_row.status_label.setStyleSheet("color: #2ed573;")
        else:
            self.cdp_row.dot.setStyleSheet("color: #f85149; font-size: 16px;")
            self.cdp_row.status_label.setText("未连接")
            self.cdp_row.status_label.setStyleSheet("color: #f85149;")

        # Cookie
        cookie_file = self.settings.get("cookie_file", DEFAULT_COOKIE_FILE)
        if cookie_file and os.path.exists(cookie_file):
            try:
                with open(cookie_file) as f:
                    data = json.load(f)
                count = len(data.get("cookies", data)) if isinstance(data, (dict, list)) else 0
                self.cookie_row.dot.setStyleSheet("color: #2ed573; font-size: 16px;")
                self.cookie_row.status_label.setText(f"已配置 ({count} 个 Cookie)")
                self.cookie_row.status_label.setStyleSheet("color: #2ed573;")
            except Exception:
                self.cookie_row.dot.setStyleSheet("color: #d29922; font-size: 16px;")
                self.cookie_row.status_label.setText("文件损坏")
                self.cookie_row.status_label.setStyleSheet("color: #d29922;")
        else:
            self.cookie_row.dot.setStyleSheet("color: #f85149; font-size: 16px;")
            self.cookie_row.status_label.setText("未配置")
            self.cookie_row.status_label.setStyleSheet("color: #f85149;")

        # 整体就绪
        self._ready = cdp_ok
        self.start_cdp_btn.setVisible(self.chrome_path is not None and not cdp_ok)
        self.login_btn.setVisible(cdp_ok and not self._login_in_progress)
        self.complete_login_btn.setVisible(self._login_in_progress)

        self.ready_changed.emit(self._ready)

    def _start_cdp(self):
        if not self.chrome_path:
            QMessageBox.warning(self, "错误", "未找到 Chrome 浏览器。")
            return

        port = 9222
        cdp_url = self.cdp_input.text().strip()
        if ":" in cdp_url.replace("http://", "").replace("https://", ""):
            try:
                port = int(cdp_url.rsplit(":", 1)[-1])
            except ValueError:
                pass

        self.start_cdp_btn.setEnabled(False)
        self.start_cdp_btn.setText("启动中...")

        if start_chrome_cdp(self.chrome_path, port):
            for _ in range(10):
                if check_cdp(cdp_url, timeout=1.0):
                    break
                QTimer.singleShot(1000, lambda: None)
            self.check_all()
        else:
            QMessageBox.warning(self, "错误", "启动 Chrome 失败。")
            self.start_cdp_btn.setEnabled(True)

        self.start_cdp_btn.setText("🚀 启动 Chrome CDP")

    # ═══════════════ 登录流程 ═══════════════

    def _start_login(self):
        """打开抖音首页，让用户手动登录"""
        cdp_url = self.cdp_input.text().strip()
        if not check_cdp(cdp_url):
            QMessageBox.warning(self, "错误", "CDP 未连接，请先启动 Chrome。")
            return

        success = open_douyin_login(cdp_url)
        if not success:
            QMessageBox.warning(self, "错误", "无法通过 CDP 打开抖音页面。")
            return

        self._login_in_progress = True
        self.login_btn.setVisible(False)
        self.complete_login_btn.setVisible(True)
        self.hint.setText(
            "请在 Chrome 浏览器中手动完成抖音登录（扫码/手机验证）。\n"
            "登录成功后，点击下方「完成登录，保存 Cookie」。"
        )
        QMessageBox.information(
            self, "登录抖音",
            "已在 Chrome 中打开抖音首页。\n\n"
            "请在浏览器中完成登录，然后回到本软件点击「完成登录，保存 Cookie」。"
        )

    def _complete_login(self):
        """提取 Cookie 并保存"""
        cdp_url = self.cdp_input.text().strip()
        self.complete_login_btn.setEnabled(False)
        self.complete_login_btn.setText("提取中...")

        cookies = extract_cookies_cdp(cdp_url)
        if cookies is None or len(cookies) == 0:
            QMessageBox.warning(self, "错误", "无法提取 Cookie，请确认已在 Chrome 中登录抖音。")
            self.complete_login_btn.setEnabled(True)
            self.complete_login_btn.setText("✅ 完成登录，保存 Cookie")
            return

        # 保存
        os.makedirs(COOKIE_DIR, exist_ok=True)
        data = {"cookies": cookies, "origins": ["https://www.douyin.com"]}
        with open(DEFAULT_COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新设置
        self.settings["cookie_file"] = DEFAULT_COOKIE_FILE
        self.cookie_saved.emit(DEFAULT_COOKIE_FILE)

        self._login_in_progress = False
        self.complete_login_btn.setVisible(False)
        self.complete_login_btn.setEnabled(True)
        self.complete_login_btn.setText("✅ 完成登录，保存 Cookie")
        self.hint.setText(f"✅ Cookie 已保存！共 {len(cookies)} 条。")

        QMessageBox.information(
            self, "登录成功",
            f"Cookie 已保存到：\n{DEFAULT_COOKIE_FILE}\n\n共 {len(cookies)} 条 Cookie。"
        )
        self.check_all()

    # ═══════════════ 工具 ═══════════════

    def _update_settings(self):
        self.settings["cdp_url"] = self.cdp_input.text().strip()

    def is_ready(self) -> bool:
        return self._ready

    def refresh_chrome_path(self):
        self.chrome_path = find_chrome()
        self.check_all()
