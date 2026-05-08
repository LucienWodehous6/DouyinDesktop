"""热榜直播子标签 — 使用 dy-cli 的 DouyinAPIClient"""

import time
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QComboBox,
)
from PyQt6.QtGui import QFont

from core_modules.dy_cli.engines.api_client import DouyinAPIClient, DouyinAPIError


class TrendingWorker(QThread):
    log_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, count: int = 50):
        super().__init__()
        self.count = count

    def run(self):
        try:
            client = DouyinAPIClient.from_config()
            items = client.get_trending()
            client.close()
            self.result_signal.emit(items[:self.count])
            self.log_signal.emit(f"🔥 获取到 {len(items)} 条热榜", "SUCCESS")
        except DouyinAPIError as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            self.error_signal.emit(f"热榜获取失败: {e}")
        finally:
            self.finished_signal.emit()


class LiveInfoWorker(QThread):
    log_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, room_id: str):
        super().__init__()
        self.room_id = room_id

    def run(self):
        try:
            client = DouyinAPIClient.from_config()
            info = client.get_live_info(self.room_id)
            client.close()
            self.result_signal.emit(info)
            self.log_signal.emit(f"📺 直播间信息已获取", "SUCCESS")
        except DouyinAPIError as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            self.error_signal.emit(f"直播间信息获取失败: {e}")
        finally:
            self.finished_signal.emit()


class TrendingTab(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._worker = None
        self._results = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 操作栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.count_combo = QComboBox()
        self.count_combo.addItems(["Top 10", "Top 20", "Top 50", "Top 100"])
        self.count_combo.setCurrentIndex(2)
        toolbar.addWidget(QLabel("数量:"))
        toolbar.addWidget(self.count_combo)

        self.refresh_btn = QPushButton("🔄 刷新热榜")
        self.refresh_btn.setObjectName("primaryBtn")
        self.refresh_btn.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        toolbar.addWidget(self.status_label)

        layout.addLayout(toolbar)

        # 热榜表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["排名", "标题", "热度", "标签", "话题"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # 直播间查询
        live_box = QHBoxLayout()
        live_box.setSpacing(8)

        live_box.addWidget(QLabel("直播间ID:"))
        self.live_input = QLineEdit()
        self.live_input.setPlaceholderText("输入 room_id 或 URL...")
        live_box.addWidget(self.live_input, 1)

        self.live_btn = QPushButton("📺 查询直播间")
        self.live_btn.setObjectName("smallBtn")
        self.live_btn.clicked.connect(self._on_query_live)
        live_box.addWidget(self.live_btn)

        layout.addLayout(live_box)

    def _on_refresh(self):
        count_map = {"Top 10": 10, "Top 20": 20, "Top 50": 50, "Top 100": 100}
        count = count_map[self.count_combo.currentText()]

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("刷新中...")
        self.status_label.setText("加载中...")
        self.table.setRowCount(0)

        self._worker = TrendingWorker(count)
        self._worker.log_signal.connect(self._handle_log)
        self._worker.result_signal.connect(self._handle_result)
        self._worker.error_signal.connect(self._handle_error)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _handle_log(self, msg: str, level: str):
        self.log_signal.emit(f"[热榜] {msg}", level)

    def _handle_result(self, items: list):
        self._results = items
        self._populate_table(items)

    def _handle_error(self, msg: str):
        self.log_signal.emit(f"❌ {msg}", "ERROR")
        self.status_label.setText(f"错误: {msg}")

    def _on_finished(self):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新热榜")
        if self._results:
            self.status_label.setText(f"共 {len(self._results)} 条热榜")

    def _populate_table(self, items: list):
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            # Word HOT word type: 0=普通, 1=新, 2=热, 3=爆
            word_type = item.get("word_type", 0)
            type_labels = ["", "🆕 新", "🔥 热", "💥 爆"]
            type_label = type_labels[word_type] if word_type < len(type_labels) else ""

            self.table.setItem(row, 0, QTableWidgetItem(f"#{row + 1}"))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("word", "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get("heat_score", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(type_label))
            self.table.setItem(row, 4, QTableWidgetItem(item.get("hot_value", "")))

    def _on_query_live(self):
        room_id = self.live_input.text().strip()
        if not room_id:
            return
        self.log_signal.emit(f"📺 查询直播间: {room_id}", "INFO")
        # TODO: 实现直播间信息查询

    def set_settings(self, settings: dict):
        self._settings = settings