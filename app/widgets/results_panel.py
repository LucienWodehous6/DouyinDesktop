"""结果面板 v3 — 主从视图 + JSON 详情"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QLabel, QPushButton,
    QFileDialog, QFrame,
)
from PyQt6.QtGui import QFont


class ResultsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("📊 采集结果列表")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        export_btn = QPushButton("⬇ 导出 JSON")
        export_btn.setObjectName("smallBtn")
        export_btn.clicked.connect(self._on_export)
        title_row.addWidget(export_btn)

        layout.addLayout(title_row)

        divider = QFrame()
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        # 分割面板
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧树
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["内容", "详情"])
        self.tree.setColumnWidth(0, 420)
        self.tree.setAnimated(True)
        self.tree.setIndentation(22)
        self.tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self.tree)

        # 右侧 JSON
        self.detail_view = QPlainTextEdit()
        self.detail_view.setObjectName("jsonView")
        self.detail_view.setReadOnly(True)
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.detail_view.setFont(font)
        self.detail_view.setPlaceholderText("点击左侧条目查看详情")
        splitter.addWidget(self.detail_view)

        splitter.setSizes([460, 540])
        layout.addWidget(splitter, 1)

    # ── 加载 / 导出 ──

    def load_file(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)
        except Exception:
            return
        self._build_tree()

    def export_to(self, path: str):
        if self._data:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    def is_empty(self) -> bool:
        return self._data is None

    # ── 构建树 ──

    def _build_tree(self):
        self.tree.clear()
        if not self._data:
            return

        root = self.tree.invisibleRootItem()
        kw = self._data.get("match_keywords")
        kw_str = " | ".join(kw) if kw else "无"

        info = QTreeWidgetItem(root, [
            f"📁 搜索: {self._data.get('search_term', '?')}",
            f"匹配: {kw_str}  ·  {self._data.get('total_videos', 0)} 视频",
        ])
        info.setData(0, Qt.ItemDataRole.UserRole, {"type": "meta"})

        for v in self._data.get("videos", []):
            s = f"👍{v.get('likes','0')}  💬{v.get('comments_count','0')}  ⭐{v.get('collects','0')}  ↗{v.get('shares','0')}"
            video_item = QTreeWidgetItem(root, [
                f"🎬 {v.get('title','无')[:50]}",
                s,
            ])
            video_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "video", "data": v})
            video_item.setExpanded(True)

            # 匹配用户
            for u in (v.get("matched_users") or []):
                user_item = QTreeWidgetItem(video_item, [
                    f"  👤 {u.get('username','?')}  ·  {u.get('shortId','?')}",
                    f"{u.get('comment_content','')[:30]}  ·  {u.get('comment_time','')}",
                ])
                user_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "user", "data": u})

            # 评论（无关键字模式）
            for idx, c in enumerate(v.get("comments", [])):
                cmt = QTreeWidgetItem(video_item, [
                    f"  💬 {c.get('username','?')}",
                    f"{c.get('content','')[:35]}",
                ])
                cmt.setData(0, Qt.ItemDataRole.UserRole, {"type": "comment", "data": c})
                if idx > 60 and len(v.get("comments", [])) > 100:
                    video_item.setExpanded(False)
                    break

        self.tree.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") != "meta":
            self.detail_view.setPlainText(
                json.dumps(data["data"], ensure_ascii=False, indent=2)
            )

    def _on_export(self):
        if not self._data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", "", "JSON (*.json)")
        if path:
            self.export_to(path)
