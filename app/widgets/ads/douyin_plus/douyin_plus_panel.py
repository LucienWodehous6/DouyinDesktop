"""抖音 DO+ 面板 UI — 占位实现"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class DouyinPlusPanel(QWidget):
    """抖音 DO+ 投放管理面板（占位）"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("抖音 DO+ 模块 - 开发中"))