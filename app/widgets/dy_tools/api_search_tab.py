"""API搜索子标签 — 使用 dy-cli 的 DouyinAPIClient"""

import json
import os
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QFrame, QFileDialog,
)
from PyQt6.QtGui import QFont

from core_modules.dy_cli.engines.api_client import DouyinAPIClient, DouyinAPIError


SORT_OPTIONS = ["综合", "最多点赞", "最新发布"]
TIME_OPTIONS = ["不限", "一天内", "一周内", "半年内"]

SORT_MAP = {"综合": 0, "最多点赞": 1, "最新发布": 2}
TIME_MAP = {"不限": 0, "一天内": 1, "一周内": 7, "半年内": 182}


class ApiSearchWorker(QThread):
    """API搜索后台线程"""
    log_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, keyword: str, sort_type: int, publish_time: int, count: int):
        super().__init__()
        self.keyword = keyword
        self.sort_type = sort_type
        self.publish_time = publish_time
        self.count = count
        self._stop = False

    def run(self):
        try:
            self.log_signal.emit(f"🔍 开始搜索: {self.keyword}", "INFO")
            client = DouyinAPIClient.from_config()
            result = client.search(
                keyword=self.keyword,
                sort_type=self.sort_type,
                publish_time=self.publish_time,
                search_type="general",
                count=self.count,
            )
            client.close()

            videos = []
            data_list = result.get("data", [])
            for item in data_list:
                aweme = item.get("aweme_info", {})
                if not aweme:
                    continue
                videos.append({
                    "aweme_id": aweme.get("aweme_id", ""),
                    "title": aweme.get("desc", ""),
                    "author": aweme.get("author", {}).get("nickname", ""),
                    "likes": aweme.get("statistics", {}).get("digg_count", 0),
                    "comments": aweme.get("statistics", {}).get("comment_count", 0),
                    "collects": aweme.get("statistics", {}).get("collect_count", 0),
                    "shares": aweme.get("statistics", {}).get("share_count", 0),
                    "duration": aweme.get("duration", 0),
                    "create_time": aweme.get("create_time", 0),
                })
            self.result_signal.emit(videos)
            self.log_signal.emit(f"✅ 找到 {len(videos)} 条结果", "SUCCESS")
        except DouyinAPIError as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            self.error_signal.emit(f"搜索失败: {e}")
        finally:
            self.finished_signal.emit()


class ApiSearchTab(QWidget):
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

        # 搜索框区域
        search_bar = QHBoxLayout()
        search_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.setMinimumHeight(36)
        self.search_input.returnPressed.connect(self._on_search)
        search_bar.addWidget(self.search_input, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(SORT_OPTIONS)
        search_bar.addWidget(self.sort_combo)

        self.time_combo = QComboBox()
        self.time_combo.addItems(TIME_OPTIONS)
        search_bar.addWidget(self.time_combo)

        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.clicked.connect(self._on_search)
        search_bar.addWidget(self.search_btn)

        layout.addLayout(search_bar)

        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["标题", "作者", "点赞", "评论", "收藏", "分享"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # 底部操作区
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label)

        bottom.addStretch()

        self.export_btn = QPushButton("📤 导出JSON")
        self.export_btn.setObjectName("smallBtn")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        bottom.addWidget(self.export_btn)

        layout.addLayout(bottom)

    def _on_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        self.status_label.setText("搜索中...")
        self.table.setRowCount(0)
        self._results = []
        self.export_btn.setEnabled(False)

        sort_idx = self.sort_combo.currentIndex()
        time_idx = self.time_combo.currentIndex()
        sort_type = SORT_MAP[SORT_OPTIONS[sort_idx]]
        publish_time = TIME_MAP[TIME_OPTIONS[time_idx]]

        self._worker = ApiSearchWorker(keyword, sort_type, publish_time, 20)
        self._worker.log_signal.connect(self._handle_log)
        self._worker.result_signal.connect(self._handle_result)
        self._worker.error_signal.connect(self._handle_error)
        self._worker.finished_signal.connect(self._on_search_finished)
        self._worker.start()

    def _handle_log(self, msg: str, level: str):
        self.log_signal.emit(f"[API搜索] {msg}", level)

    def _handle_result(self, videos: list):
        self._results = videos
        self._populate_table(videos)

    def _handle_error(self, msg: str):
        self.log_signal.emit(f"❌ {msg}", "ERROR")
        self.status_label.setText(f"错误: {msg}")

    def _on_search_finished(self):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 搜索")
        if self._results:
            self.status_label.setText(f"找到 {len(self._results)} 条结果")
            self.export_btn.setEnabled(True)
        else:
            self.status_label.setText("未找到结果")

    def _populate_table(self, videos: list):
        self.table.setRowCount(len(videos))
        for row, v in enumerate(videos):
            self.table.setItem(row, 0, QTableWidgetItem(v["title"][:50]))
            self.table.setItem(row, 1, QTableWidgetItem(v["author"]))
            self.table.setItem(row, 2, QTableWidgetItem(self._format_count(v["likes"])))
            self.table.setItem(row, 3, QTableWidgetItem(self._format_count(v["comments"])))
            self.table.setItem(row, 4, QTableWidgetItem(self._format_count(v["collects"])))
            self.table.setItem(row, 5, QTableWidgetItem(self._format_count(v["shares"])))

    def _format_count(self, num: int) -> str:
        if num >= 10000:
            return f"{num / 10000:.1f}w"
        return str(num)

    def _on_export(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", "douyin_search.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"keyword": self.search_input.text(), "videos": self._results}, f, ensure_ascii=False, indent=2)
            self.log_signal.emit(f"✅ 已导出到 {path}", "SUCCESS")

    def set_settings(self, settings: dict):
        self._settings = settings