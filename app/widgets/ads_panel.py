"""投流主面板 — 巨量千川 + 抖音 DO+ 统一入口"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame,
)
from PyQt6.QtCore import Qt


class AdsPanel(QWidget):
    """投流统一入口页面"""

    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QFrame()
        header.setObjectName("pageHeader")
        header.setMinimumHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("📊 投流管理")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addWidget(header)

        # Tab 页：巨量千川 | 抖音 DO+
        self.tabs = QTabWidget()

        # 巨量千川面板（占位，Task 2 会实现）
        from app.widgets.ads.juliang.juliang_panel import JuliangPanel
        self.tabs.addTab(JuliangPanel(self._settings), "巨量千川")

        # 抖音 DO+ 面板（占位，Task 3 会实现）
        from app.widgets.ads.douyin_plus.douyin_plus_panel import DouyinPlusPanel
        self.tabs.addTab(DouyinPlusPanel(self._settings), "抖音 DO+")

        layout.addWidget(self.tabs)