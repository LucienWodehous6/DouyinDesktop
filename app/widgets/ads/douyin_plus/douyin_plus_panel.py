"""抖音 DO+ 面板 UI"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QLabel, QHeaderView, QAbstractItemView,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DouyinPlusPanel(QWidget):
    """抖音 DO+ 投放管理面板"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("抖音 DO+ — 内容加热推广")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 控制栏
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 刷新推广")
        self.create_btn = QPushButton("➕ 创建推广")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.create_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # 连接按钮信号
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.create_btn.clicked.connect(self._on_create)

        # 推广列表
        self.campaign_table = QTableWidget()
        self.campaign_table.setColumnCount(6)
        self.campaign_table.setHorizontalHeaderLabels(["视频", "状态", "预算", "播放", "互动", "操作"])
        self.campaign_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.campaign_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.campaign_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.campaign_table.setMinimumHeight(300)
        layout.addWidget(self.campaign_table)

        # 状态栏
        self.status_label = QLabel("未连接")
        layout.addWidget(self.status_label)

    def _on_refresh(self):
        """刷新推广列表"""
        self.status_label.setText("正在刷新...")
        QMessageBox.information(self, "提示", "刷新功能开发中")

    def _on_create(self):
        """创建新推广"""
        QMessageBox.information(self, "提示", "创建推广功能开发中")

    def load_campaigns(self):
        """加载推广列表"""
        pass
