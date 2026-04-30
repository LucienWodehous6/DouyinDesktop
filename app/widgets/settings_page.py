"""设置页面 — 环境检查 + CDP/Cookie 配置"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QGroupBox, QFormLayout,
    QCheckBox, QFileDialog, QMessageBox,
)


class CdpSettingsTab(QWidget):
    """CDP 地址 + Cookie 配置"""
    settings_changed = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # CDP 地址
        cdp_group = QGroupBox("CDP 调试端口")
        cdp_form = QFormLayout(cdp_group)
        cdp_form.setSpacing(10)

        self.cdp_input = QLineEdit(self.settings.get("cdp_url", "http://127.0.0.1:9222"))
        self.cdp_input.textChanged.connect(self._save)
        cdp_form.addRow("连接地址:", self.cdp_input)

        hint = QLabel("Chrome 启动参数: --remote-debugging-port=9222")
        hint.setObjectName("hintLabel")
        cdp_form.addRow(hint)

        layout.addWidget(cdp_group)

        # Cookie
        cookie_group = QGroupBox("Cookie 登录配置")
        cookie_layout = QHBoxLayout(cookie_group)
        cookie_layout.setSpacing(8)

        self.cookie_input = QLineEdit(self.settings.get("cookie_file", ""))
        self.cookie_input.setPlaceholderText("选择 cookies.json ...")
        self.cookie_input.textChanged.connect(self._save)
        cookie_layout.addWidget(self.cookie_input, 1)

        browse = QPushButton("浏览")
        browse.setObjectName("smallBtn")
        browse.clicked.connect(self._browse_cookie)
        cookie_layout.addWidget(browse)

        layout.addWidget(cookie_group)

        # 存储路径
        storage_group = QGroupBox("任务结果存储")
        storage_layout = QHBoxLayout(storage_group)
        storage_layout.setSpacing(8)

        default_storage = os.path.join(os.path.expanduser("~"), ".dy", "results")
        self.storage_input = QLineEdit(self.settings.get("storage_path", default_storage))
        self.storage_input.setPlaceholderText("选择存储目录...")
        self.storage_input.textChanged.connect(self._save)
        storage_layout.addWidget(self.storage_input, 1)

        browse_storage = QPushButton("浏览")
        browse_storage.setObjectName("smallBtn")
        browse_storage.clicked.connect(self._browse_storage)
        storage_layout.addWidget(browse_storage)

        layout.addWidget(storage_group)

        # 模式
        mode_group = QGroupBox("运行模式")
        mode_layout = QVBoxLayout(mode_group)
        self.cdp_mode = QCheckBox("使用 CDP 连接已有 Chrome（推荐）")
        self.cdp_mode.setChecked(self.settings.get("use_cdp", True))
        self.cdp_mode.toggled.connect(self._save)
        mode_layout.addWidget(self.cdp_mode)
        layout.addWidget(mode_group)

        layout.addStretch()

    def _browse_cookie(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Cookie", "", "JSON (*.json)")
        if path:
            self.cookie_input.setText(path)
            self._save()

    def _browse_storage(self):
        path = QFileDialog.getExistingDirectory(self, "选择存储目录")
        if path:
            self.storage_input.setText(path)
            self._save()

    def _save(self):
        self.settings["cdp_url"] = self.cdp_input.text().strip()
        self.settings["cookie_file"] = self.cookie_input.text().strip() or None
        self.settings["storage_path"] = self.storage_input.text().strip()
        self.settings["use_cdp"] = self.cdp_mode.isChecked()
        self.settings_changed.emit()

    def get_cdp_url(self) -> str:
        return self.cdp_input.text().strip()


class SettingsPage(QWidget):
    """设置页面 = 环境检查 + CDP/Cookie"""
    ready_changed = pyqtSignal(bool)
    cookie_saved = pyqtSignal(str)

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("⚙ 设置")
        title.setObjectName("pageTitle")
        title.setContentsMargins(28, 20, 0, 8)
        layout.addWidget(title)

        tabs = QTabWidget()

        # 环境检查 tab
        from app.widgets.environment_panel import EnvironmentPanel
        self.env_tab = EnvironmentPanel(self.settings)
        self.env_tab.ready_changed.connect(self.ready_changed.emit)
        self.env_tab.cookie_saved.connect(self.cookie_saved.emit)
        tabs.addTab(self.env_tab, "环境检查")

        # CDP/Cookie tab
        self.cdp_tab = CdpSettingsTab(self.settings)
        self.cdp_tab.settings_changed.connect(self._on_settings_changed)
        tabs.addTab(self.cdp_tab, "连接配置")

        layout.addWidget(tabs)

    def _on_settings_changed(self):
        """CDP 地址变更时通知环境检查刷新"""
        self.env_tab.check_all()

    def is_ready(self) -> bool:
        return self.env_tab.is_ready()

    def cdp_url(self) -> str:
        return self.cdp_tab.get_cdp_url()
