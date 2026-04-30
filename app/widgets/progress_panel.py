"""进度面板 v3 — 终端风格日志 + 时间戳"""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QLabel, QPlainTextEdit, QPushButton, QFrame,
)
from app.theme import LOG_COLORS


class ProgressPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("📟 实时运行日志")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        clear_btn = QPushButton("清空日志")
        clear_btn.setObjectName("smallBtn")
        clear_btn.clicked.connect(self.clear)
        title_row.addWidget(clear_btn)

        layout.addLayout(title_row)

        # 分隔线
        div = QFrame()
        div.setObjectName("sectionDivider")
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)

        # 日志视图 — 终端风格
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.log_view.setFont(font)
        layout.addWidget(self.log_view, 1)

        # 底部状态
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self.progress_label = QLabel("等待任务...")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        bottom.addWidget(self.progress_label)
        bottom.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(10)
        bottom.addWidget(self.progress_bar)

        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        bottom.addWidget(self.percent_label)

        layout.addLayout(bottom)

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = QColor(LOG_COLORS.get(level, "#dfe6e9"))

        cursor = self.log_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # 时间戳
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor("#484f58"))
        cursor.insertText(f"[{timestamp}] ", ts_fmt)

        # 级别标签
        lvl_fmt = QTextCharFormat()
        lvl_fmt.setForeground(color)
        lvl_fmt.setFontWeight(700)
        cursor.insertText(f"[{level}] ", lvl_fmt)

        # 消息
        msg_fmt = QTextCharFormat()
        msg_fmt.setForeground(QColor("#c9d1d9"))
        cursor.insertText(message + "\n", msg_fmt)

        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()

    def set_progress(self, value: int):
        value = min(max(value, 0), 100)
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")
        if value >= 100:
            self.progress_label.setText("完成")
        elif value > 0:
            self.progress_label.setText("采集中...")

    def clear(self):
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.progress_label.setText("等待任务...")
