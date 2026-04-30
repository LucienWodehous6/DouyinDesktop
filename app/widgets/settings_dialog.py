"""设置对话框 — CDP / Cookie 配置"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QDialogButtonBox,
    QCheckBox, QFileDialog, QHBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("设置")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # CDP
        cdp_group = QGroupBox("Chrome 调试端口")
        cdp_form = QFormLayout(cdp_group)
        cdp_form.setSpacing(10)
        self.cdp_url = QLineEdit(self.settings.get("cdp_url", "http://127.0.0.1:9222"))
        self.cdp_url.setPlaceholderText("http://127.0.0.1:9222")
        cdp_form.addRow("CDP 地址", self.cdp_url)
        layout.addWidget(cdp_group)

        # Cookie
        cookie_group = QGroupBox("免登录 Cookie")
        cookie_row = QHBoxLayout()
        self.cookie_path = QLineEdit(self.settings.get("cookie_file", ""))
        self.cookie_path.setPlaceholderText("选择 cookies.json ...")
        browse = QPushButton("浏览")
        browse.setObjectName("smallBtn")
        browse.clicked.connect(self._browse_cookie)
        cookie_row.addWidget(self.cookie_path)
        cookie_row.addWidget(browse)
        cookie_group.setLayout(cookie_row)
        layout.addWidget(cookie_group)

        # 模式
        mode_group = QGroupBox("运行模式")
        mode_layout = QVBoxLayout()
        self.use_cdp_check = QCheckBox("通过 CDP 连接已有 Chrome（推荐）")
        self.use_cdp_check.setChecked(self.settings.get("use_cdp", True))
        mode_layout.addWidget(self.use_cdp_check)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 按钮
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def _browse_cookie(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Cookie 文件", "", "JSON (*.json)")
        if path:
            self.cookie_path.setText(path)

    def get_settings(self) -> dict:
        return {
            "cdp_url": self.cdp_url.text().strip(),
            "cookie_file": self.cookie_path.text().strip() or None,
            "use_cdp": self.use_cdp_check.isChecked(),
        }
