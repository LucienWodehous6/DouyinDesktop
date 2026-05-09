"""巨量千川面板 UI"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QLabel, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class JuliangPanel(QWidget):
    """巨量千川投放管理面板"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("巨量千川 — 品牌竞价直播加热")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 控制栏
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 刷新计划")
        self.create_btn = QPushButton("➕ 创建计划")
        self.monitor_btn = QPushButton("📊 开始监控")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.create_btn)
        controls.addWidget(self.monitor_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # 计划列表
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(6)
        self.plan_table.setHorizontalHeaderLabels(["计划名", "状态", "出价", "消耗", "ROI", "操作"])
        self.plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plan_table.setMinimumHeight(300)
        layout.addWidget(self.plan_table)

        # 状态栏
        self.status_label = QLabel("未连接")
        layout.addWidget(self.status_label)

    def load_plans(self):
        """加载计划列表"""
        pass  # Task 2 后续完善
