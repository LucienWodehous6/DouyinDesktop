"""搜索面板 v3 — 标签式关键字 + 分区标题"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSpinBox, QComboBox,
    QGridLayout, QCheckBox, QFrame, QMessageBox, QScrollArea,
)
from app.widgets.common_widgets import CLineEdit

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


class DMMsgTag(QPushButton):
    """单条私信内容标签：文字 + ✖"""
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
        self._dm_msg_tags: list[DMMsgTag] = []
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
            }
            QScrollArea > QWidget {
                background: transparent;
            }
            QScrollArea::corner {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #484f58;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        outer.addWidget(scroll)

        # 内容 widget（放在 scroll 之后）
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)
        scroll.setWidget(content)

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

        self.search_input = CLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词，如'核桃手串'")
        self.search_input.setMinimumHeight(44)
        layout.addWidget(self.search_input)

        # 备注
        self.notes_input = CLineEdit()
        self.notes_input.setPlaceholderText("任务备注（可选，方便后续查找）")
        self.notes_input.setMinimumHeight(36)
        layout.addWidget(self.notes_input)

        # ── 评论关键字开关 ──
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

        self.kw_input = CLineEdit()
        self.kw_input.setPlaceholderText("输入关键字后回车或点击 + 添加")
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
        #  私信发送
        # ═══════════════════════════════════
        divider_dm = QFrame()
        divider_dm.setObjectName("sectionDivider")
        divider_dm.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider_dm)

        section_dm = QLabel("【私信发送】")
        section_dm.setObjectName("sectionLabel")
        layout.addWidget(section_dm)

        self.dm_toggle = QCheckBox("向采集到的匹配用户发送私信（多条内容随机发送）")
        self.dm_toggle.toggled.connect(self._on_dm_toggle)
        layout.addWidget(self.dm_toggle)

        # 标签行
        self.dm_msg_area = QWidget()
        self.dm_msg_area.setVisible(False)
        self.dm_msg_layout = QHBoxLayout(self.dm_msg_area)
        self.dm_msg_layout.setContentsMargins(0, 4, 0, 4)
        self.dm_msg_layout.setSpacing(8)
        self.dm_msg_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.dm_msg_area)

        # 输入 + 添加
        dm_add_row = QHBoxLayout()
        dm_add_row.setSpacing(8)

        self.dm_msg_input = CLineEdit()
        self.dm_msg_input.setPlaceholderText("输入私信内容后回车或点击 + 添加（每条最多20字）")
        self.dm_msg_input.setMinimumHeight(38)
        self.dm_msg_input.setMaxLength(20)
        self.dm_msg_input.setVisible(False)
        self.dm_msg_input.returnPressed.connect(self._add_dm_msg)
        dm_add_row.addWidget(self.dm_msg_input, 1)

        self.dm_msg_add_btn = QPushButton("+ 添加")
        self.dm_msg_add_btn.setObjectName("smallBtn")
        self.dm_msg_add_btn.setVisible(False)
        self.dm_msg_add_btn.clicked.connect(self._add_dm_msg)
        dm_add_row.addWidget(self.dm_msg_add_btn)

        layout.addLayout(dm_add_row)

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

        filter_grid.addWidget(QLabel("滚动次数"), 3, 0)
        self.scroll_spin = QSpinBox()
        self.scroll_spin.setRange(1, 200)
        self.scroll_spin.setValue(50)
        self.scroll_spin.setSuffix("  次")
        filter_grid.addWidget(self.scroll_spin, 3, 1)

        layout.addLayout(filter_grid)

        # ═══════════════════════════════════
        #  操作区
        # ═══════════════════════════════════
        layout.addSpacing(8)
        action_layout = QHBoxLayout()

        self.save_btn = QPushButton("[ 保存配置 ]")
        self.save_btn.setObjectName("smallBtn")
        self.save_btn.clicked.connect(self._save_config)
        action_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("[ 读取配置 ]")
        self.load_btn.setObjectName("smallBtn")
        self.load_btn.clicked.connect(self._load_config)
        action_layout.addWidget(self.load_btn)

        action_layout.addStretch()

        self.stop_btn = QPushButton("[ 停止采集 ]")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        action_layout.addWidget(self.stop_btn)

        self.start_btn = QPushButton("[ 开始采集 ]")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self._on_start)
        action_layout.addWidget(self.start_btn)

        layout.addLayout(action_layout)

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

    # ── 私信消息标签管理 ──

    def _add_dm_msg(self):
        text = self.dm_msg_input.text().strip()
        if not text:
            return
        if len(text) > 20:
            QMessageBox.warning(self, "提示", "每条私信内容最多20个字符。")
            return
        # 去重
        for tag in self._dm_msg_tags:
            if tag.text().replace("  ✖", "") == text:
                self.dm_msg_input.clear()
                return
        tag = DMMsgTag(text, len(self._dm_msg_tags))
        tag.removed.connect(self._remove_dm_msg)
        self._dm_msg_tags.append(tag)
        self.dm_msg_layout.addWidget(tag)
        self.dm_msg_input.clear()
        self.dm_msg_input.setFocus()

    def _remove_dm_msg(self, tag: DMMsgTag):
        self._dm_msg_tags.remove(tag)
        self.dm_msg_layout.removeWidget(tag)
        tag.deleteLater()

    # ── 配置保存/读取 ──

    def _save_config(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "保存配置", "task_config.json", "JSON (*.json)"
        )
        if not path:
            return

        # 收集当前界面参数
        config = {
            "search_text": self.search_input.text().strip(),
            "notes": self.notes_input.text().strip(),
            "video_count": self.count_spin.value(),
            "max_scrolls": self.scroll_spin.value(),
            "sort_by": self.sort_check.isChecked(),
            "time_filter": self.time_combo.currentText(),
            "kw_toggle": self.kw_toggle.isChecked(),
            "keywords": [tag.text().replace("  ✖", "").strip() for tag in self._keyword_tags],
            "dm_toggle": self.dm_toggle.isChecked(),
            "dm_messages": [tag.text().replace("  ✖", "").strip() for tag in self._dm_msg_tags],
        }

        import json
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存成功", f"配置已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _load_config(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "读取配置", "", "JSON (*.json)"
        )
        if not path:
            return

        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", str(e))
            return

        # 填充基础字段
        self.search_input.setText(config.get("search_text", ""))
        self.notes_input.setText(config.get("notes", ""))
        self.count_spin.setValue(config.get("video_count", 5))
        self.scroll_spin.setValue(config.get("max_scrolls", 50))
        self.sort_check.setChecked(config.get("sort_by", False))

        time_text = config.get("time_filter", "不限")
        for i in range(self.time_combo.count()):
            if self.time_combo.itemText(i) == time_text:
                self.time_combo.setCurrentIndex(i)
                break

        # 关键字标签
        self._clear_tags(self._keyword_tags, self.tag_layout)
        self._keyword_tags.clear()
        for kw in config.get("keywords", []):
            tag = KeywordTag(kw, len(self._keyword_tags))
            tag.removed.connect(self._remove_tag)
            self._keyword_tags.append(tag)
            self.tag_layout.addWidget(tag)

        self.kw_toggle.setChecked(config.get("kw_toggle", False))
        self._on_kw_toggle(self.kw_toggle.isChecked())

        # 私信标签
        self._clear_tags(self._dm_msg_tags, self.dm_msg_layout)
        self._dm_msg_tags.clear()
        for msg in config.get("dm_messages", []):
            tag = DMMsgTag(msg, len(self._dm_msg_tags))
            tag.removed.connect(self._remove_dm_msg)
            self._dm_msg_tags.append(tag)
            self.dm_msg_layout.addWidget(tag)

        self.dm_toggle.setChecked(config.get("dm_toggle", False))
        self._on_dm_toggle(self.dm_toggle.isChecked())

        QMessageBox.information(self, "读取成功", f"配置已从:\n{path}\n\n注意：点击「开始采集」后才会实际应用新配置。")

    def _clear_tags(self, tags: list, layout):
        for tag in tags:
            layout.removeWidget(tag)
            tag.deleteLater()

    def _on_dm_toggle(self, checked: bool):
        self.dm_msg_area.setVisible(checked)
        self.dm_msg_input.setVisible(checked)
        self.dm_msg_add_btn.setVisible(checked)
        if checked:
            self.dm_msg_input.setFocus()

    # ── 启动 ──

    def _on_start(self):
        if self._running:
            QMessageBox.warning(self, "提示", "采集任务正在进行中，请等待当前任务完成。")
            return

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

        dm_message = None
        if self.dm_toggle.isChecked():
            msgs = [tag.text().replace("  ✖", "") for tag in self._dm_msg_tags]
            if not msgs:
                QMessageBox.warning(self, "提示", "已启用私信发送，但未填写私信内容。")
                return
            # 用换行符拼接传给后端，后端每次发送随机选一条
            dm_message = "\n".join(msgs)

        params = {
            "search_text": text,
            "notes": self.notes_input.text().strip(),
            "match_keywords": match_keywords,
            "video_count": self.count_spin.value(),
            "max_scrolls": self.scroll_spin.value(),
            "sort_by": "最新发布" if self.sort_check.isChecked() else None,
            "time_filter": TIME_MAP[self.time_combo.currentText()],
            "dm_message": dm_message,
        }
        self.start_requested.emit(params)

    def set_running(self, running: bool):
        self._running = running
        self.start_btn.setVisible(not running)
        self.stop_btn.setVisible(running)
        self.search_input.setEnabled(not running)
        self.notes_input.setEnabled(not running)
        self.kw_toggle.setEnabled(not running)
        self.kw_input.setEnabled(not running)
        self.add_btn.setEnabled(not running)
        for tag in self._keyword_tags:
            tag.setEnabled(not running)
        self.time_combo.setEnabled(not running)
        self.count_spin.setEnabled(not running)
        self.scroll_spin.setEnabled(not running)
        self.sort_check.setEnabled(not running)
        self.dm_toggle.setEnabled(not running)
        self.dm_msg_input.setEnabled(not running)
        self.dm_msg_add_btn.setEnabled(not running)
        self.save_btn.setEnabled(not running)
        self.load_btn.setEnabled(not running)
