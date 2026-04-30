"""搜索面板 v3 — 标签式关键字 + 分区标题"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSpinBox, QComboBox,
    QGridLayout, QCheckBox, QFrame, QMessageBox,
)

TIME_MAP = {"不限": None, "一天内": "一天内", "一周内": "一周内", "半年内": "半年内"}


class KeywordTag(QPushButton):
    """单个关键字标签：文字 + ✖"""
    removed = pyqtSignal(object)

    def __init__(self, text: str, index: int):
        super().__init__(f"{text}  ✖")
        self.index = index
        self.setObjectName("tagBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.removed.emit(self))


class SearchPanel(QWidget):
    start_requested = pyqtSignal(dict)
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._keyword_tags: list[KeywordTag] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)

        # ── 标题 ──
        title = QLabel("🔍 采集任务配置")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ═══════════════════════════════════
        #  基础搜索
        # ═══════════════════════════════════
        section1 = QLabel("【基础搜索】")
        section1.setObjectName("sectionLabel")
        layout.addWidget(section1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入抖音搜索词，例如：核桃手串")
        self.search_input.setMinimumHeight(44)
        layout.addWidget(self.search_input)

        # ═══════════════════════════════════
        #  精准匹配
        # ═══════════════════════════════════
        section2 = QLabel("【精准匹配】")
        section2.setObjectName("sectionLabel")
        layout.addWidget(section2)

        self.kw_toggle = QCheckBox("启用评论关键字过滤（仅提取包含以下关键词的评论与用户）")
        self.kw_toggle.toggled.connect(self._on_kw_toggle)
        layout.addWidget(self.kw_toggle)

        # 标签行
        self.tag_area = QWidget()
        self.tag_area.setVisible(False)
        self.tag_layout = QHBoxLayout(self.tag_area)
        self.tag_layout.setContentsMargins(0, 4, 0, 4)
        self.tag_layout.setSpacing(8)
        self.tag_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.tag_area)

        # 输入 + 添加
        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("输入关键字后回车或点 + 添加")
        self.kw_input.setMinimumHeight(38)
        self.kw_input.setVisible(False)
        self.kw_input.returnPressed.connect(self._add_tag)
        add_row.addWidget(self.kw_input, 1)

        self.add_btn = QPushButton("+ 添加")
        self.add_btn.setObjectName("smallBtn")
        self.add_btn.setVisible(False)
        self.add_btn.clicked.connect(self._add_tag)
        add_row.addWidget(self.add_btn)

        layout.addLayout(add_row)

        # ═══════════════════════════════════
        #  筛选条件
        # ═══════════════════════════════════
        divider = QFrame()
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        section3 = QLabel("【筛选条件】")
        section3.setObjectName("sectionLabel")
        layout.addWidget(section3)

        filter_grid = QGridLayout()
        filter_grid.setSpacing(12)

        self.sort_check = QCheckBox("优先按最新发布排序")
        self.sort_check.setChecked(True)
        filter_grid.addWidget(self.sort_check, 0, 0, 1, 2)

        filter_grid.addWidget(QLabel("发布时间"), 1, 0)
        self.time_combo = QComboBox()
        self.time_combo.addItems(["不限", "一天内", "一周内", "半年内"])
        filter_grid.addWidget(self.time_combo, 1, 1)

        filter_grid.addWidget(QLabel("目标数量"), 2, 0)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(5)
        self.count_spin.setSuffix("  个视频")
        filter_grid.addWidget(self.count_spin, 2, 1)

        layout.addLayout(filter_grid)

        # ═══════════════════════════════════
        #  操作区
        # ═══════════════════════════════════
        layout.addSpacing(8)
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.stop_btn = QPushButton("⏹  停止采集")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        action_layout.addWidget(self.stop_btn)

        self.start_btn = QPushButton("▶  开始采集")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self._on_start)
        action_layout.addWidget(self.start_btn)

        layout.addLayout(action_layout)

        layout.addStretch()

    # ── 关键字标签管理 ──

    def _add_tag(self):
        text = self.kw_input.text().strip()
        if not text:
            return
        # 去重
        for tag in self._keyword_tags:
            if tag.text().replace("  ✖", "") == text:
                self.kw_input.clear()
                return
        tag = KeywordTag(text, len(self._keyword_tags))
        tag.removed.connect(self._remove_tag)
        self._keyword_tags.append(tag)
        self.tag_layout.addWidget(tag)
        self.kw_input.clear()
        self.kw_input.setFocus()

    def _remove_tag(self, tag: KeywordTag):
        self._keyword_tags.remove(tag)
        self.tag_layout.removeWidget(tag)
        tag.deleteLater()

    def _on_kw_toggle(self, checked: bool):
        self.tag_area.setVisible(checked)
        self.kw_input.setVisible(checked)
        self.add_btn.setVisible(checked)
        if checked:
            self.kw_input.setFocus()

    # ── 启动 ──

    def _on_start(self):
        text = self.search_input.text().strip()
        if not text:
            return

        match_keywords = None
        if self.kw_toggle.isChecked():
            keywords = [tag.text().replace("  ✖", "").strip() for tag in self._keyword_tags]
            if not keywords:
                QMessageBox.warning(self, "提示", "已启用评论筛选，但未填写关键词。")
                return
            match_keywords = keywords

        params = {
            "search_text": text,
            "match_keywords": match_keywords,
            "video_count": self.count_spin.value(),
            "sort_by": "最新发布" if self.sort_check.isChecked() else None,
            "time_filter": TIME_MAP[self.time_combo.currentText()],
        }
        self.start_requested.emit(params)

    def set_running(self, running: bool):
        self._running = running
        self.start_btn.setVisible(not running)
        self.stop_btn.setVisible(running)
        self.search_input.setEnabled(not running)
        self.kw_toggle.setEnabled(not running)
        self.kw_input.setEnabled(not running)
        self.add_btn.setEnabled(not running)
        for tag in self._keyword_tags:
            tag.setEnabled(not running)
        self.time_combo.setEnabled(not running)
        self.count_spin.setEnabled(not running)
        self.sort_check.setEnabled(not running)
