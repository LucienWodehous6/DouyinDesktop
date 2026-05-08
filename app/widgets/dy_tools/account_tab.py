"""账号管理子标签 — 多账号切换"""

import os
import json
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QMessageBox,
)
from core_modules.dy_cli.utils import config


class AccountTab(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._init_ui()
        self._refresh_accounts()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 账号列表
        list_group = QGroupBox("已登录账号")
        list_layout = QVBoxLayout(list_group)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(3)
        self.account_table.setHorizontalHeaderLabels(["账号名", "Cookie状态", "默认"])
        self.account_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.account_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.account_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.account_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.account_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.account_table.setMaximumHeight(200)
        list_layout.addWidget(self.account_table)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.add_btn = QPushButton("➕ 添加账号")
        self.add_btn.setObjectName("smallBtn")
        self.add_btn.clicked.connect(self._on_add_account)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("➖ 删除账号")
        self.remove_btn.setObjectName("smallBtn")
        self.remove_btn.clicked.connect(self._on_remove_account)
        btn_layout.addWidget(self.remove_btn)

        self.set_default_btn = QPushButton("⭐ 设为默认")
        self.set_default_btn.setObjectName("smallBtn")
        self.set_default_btn.clicked.connect(self._on_set_default)
        btn_layout.addWidget(self.set_default_btn)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setObjectName("smallBtn")
        self.refresh_btn.clicked.connect(self._refresh_accounts)
        btn_layout.addWidget(self.refresh_btn)

        btn_layout.addStretch()

        list_layout.addLayout(btn_layout)

        layout.addWidget(list_group)

        # Cookie 管理
        cookie_group = QGroupBox("Cookie 文件")
        cookie_layout = QHBoxLayout(cookie_group)
        cookie_layout.setSpacing(8)

        cookie_layout.addWidget(QLabel("路径:"))

        from PyQt6.QtWidgets import QFileDialog
        self.cookie_path = QLineEdit()
        self.cookie_path.setPlaceholderText("选择或输入 Cookie 文件路径...")
        self.cookie_path.setReadOnly(True)
        cookie_layout.addWidget(self.cookie_path, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("smallBtn")
        browse_btn.clicked.connect(self._on_browse_cookie)
        cookie_layout.addWidget(browse_btn)

        import_btn = QPushButton("导入")
        import_btn.setObjectName("smallBtn")
        import_btn.clicked.connect(self._on_import_cookie)
        cookie_layout.addWidget(import_btn)

        layout.addWidget(cookie_group)

        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _refresh_accounts(self):
        cfg = config.load_config()
        cookies_dir = os.path.join(os.path.expanduser("~/.dy"), "cookies")

        accounts = []
        if os.path.isdir(cookies_dir):
            for fname in os.listdir(cookies_dir):
                if fname.endswith(".json"):
                    account_name = fname[:-5]  # 去掉 .json
                    cookie_path = os.path.join(cookies_dir, fname)
                    has_cookie = os.path.getsize(cookie_path) > 100
                    is_default = cfg["default"]["account"] == account_name
                    accounts.append({
                        "name": account_name,
                        "has_cookie": "✓ 已配置" if has_cookie else "✗ 空文件",
                        "is_default": "★" if is_default else "",
                        "path": cookie_path,
                    })

        self.account_table.setRowCount(len(accounts))
        for row, acc in enumerate(accounts):
            self.account_table.setItem(row, 0, QTableWidgetItem(acc["name"]))
            self.account_table.setItem(row, 1, QTableWidgetItem(acc["has_cookie"]))
            self.account_table.setItem(row, 2, QTableWidgetItem(acc["is_default"]))

        self.status_label.setText(f"共 {len(accounts)} 个账号")

    def _on_add_account(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "添加账号", "输入账号名称:")
        if not ok or not name.strip():
            return

        name = name.strip()
        cfg = config.load_config()

        # 创建新账号的 cookie 文件
        cookie_file = config.get_cookie_file(name)
        # 复制默认账号的 cookie 作为模板（如果有）
        default_cookie = config.get_cookie_file(cfg["default"]["account"])
        if os.path.exists(default_cookie) and default_cookie != cookie_file:
            with open(default_cookie, encoding="utf-8") as f:
                default_data = json.load(f)
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
        else:
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump({"cookies": [], "origins": []}, f)

        self.log_signal.emit(f"➕ 账号 {name} 已添加", "INFO")
        self._refresh_accounts()

    def _on_remove_account(self):
        row = self.account_table.currentRow()
        if row < 0:
            return

        name = self.account_table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"确定删除账号 {name}？")
        if reply != QMessageBox.StandardButton.Yes:
            return

        cookie_file = config.get_cookie_file(name)
        if os.path.exists(cookie_file):
            os.remove(cookie_file)

        self.log_signal.emit(f"➖ 账号 {name} 已删除", "INFO")
        self._refresh_accounts()

    def _on_set_default(self):
        row = self.account_table.currentRow()
        if row < 0:
            return

        name = self.account_table.item(row, 0).text()
        config.set_value("default.account", name)
        self.log_signal.emit(f"⭐ 账号 {name} 已设为默认", "SUCCESS")
        self._refresh_accounts()

    def _on_browse_cookie(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择 Cookie 文件", "", "JSON (*.json)")
        if path:
            self.cookie_path.setText(path)

    def _on_import_cookie(self):
        path = self.cookie_path.text().strip()
        if not path or not os.path.exists(path):
            self.status_label.setText("请先选择有效的 Cookie 文件")
            return

        row = self.account_table.currentRow()
        if row < 0:
            self.status_label.setText("请先在列表中选择一个账号")
            return

        name = self.account_table.item(row, 0).text()
        target_file = config.get_cookie_file(name)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.log_signal.emit(f"✅ Cookie 已导入到账号 {name}", "SUCCESS")
        self._refresh_accounts()

    def set_settings(self, settings: dict):
        self._settings = settings