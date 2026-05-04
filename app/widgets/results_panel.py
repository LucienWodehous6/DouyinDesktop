"""结果面板 v4 — 清晰数据展示"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QLabel, QPushButton,
    QFileDialog, QFrame, QComboBox, QGridLayout, QMessageBox,
)
from PyQt6.QtGui import QFont


class ResultsPanel(QWidget):
    def __init__(self, task_store=None):
        super().__init__()
        self._data = None
        self._task_store = task_store
        self._init_ui()
        self._refresh_tasks()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── 标题行 ──
        title_row = QHBoxLayout()
        title = QLabel("📊 采集结果")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("statLabel")
        title_row.addWidget(self.summary_label)

        title_row.addStretch()

        if self._task_store:
            self.task_combo = QComboBox()
            self.task_combo.setMinimumWidth(280)
            self.task_combo.setPlaceholderText("选择历史任务……")
            self.task_combo.currentIndexChanged.connect(self._on_task_selected)
            title_row.addWidget(self.task_combo)

            refresh_btn = QPushButton("[ 刷新 ]")
            refresh_btn.setObjectName("smallBtn")
            refresh_btn.clicked.connect(self._refresh_tasks)
            title_row.addWidget(refresh_btn)

        self.delete_btn = QPushButton("[ 删除 ]")
        self.delete_btn.setObjectName("smallBtn")
        self.delete_btn.clicked.connect(self._on_delete_task)
        title_row.addWidget(self.delete_btn)

        export_btn = QPushButton("导出 JSON")
        export_btn.setObjectName("smallBtn")
        export_btn.clicked.connect(self._on_export)
        title_row.addWidget(export_btn)

        layout.addLayout(title_row)

        # ── 分割面板 ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧树（3列）
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["标题 / 用户", "互动数据", "时间"])
        self.tree.setColumnWidth(0, 380)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 130)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self.tree)

        # 右侧详情
        self.detail_view = QPlainTextEdit()
        self.detail_view.setObjectName("jsonView")
        self.detail_view.setReadOnly(True)
        font = QFont("SF Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.detail_view.setFont(font)
        self.detail_view.setPlaceholderText("点击条目查看详情")
        splitter.addWidget(self.detail_view)

        splitter.setSizes([520, 480])
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

        videos = self._data.get("videos", [])
        kw = self._data.get("match_keywords")
        total_comments = sum(len(v.get("comments", [])) for v in videos)
        total_matched = sum(len(v.get("matched_users") or []) for v in videos)

        # 概要标签
        kw_str = " | ".join(kw) if kw else "—"
        match_info = f"已匹配 {total_matched} 个用户" if kw else f"{total_comments} 条评论"
        self.summary_label.setText(
            f"搜索: {self._data.get('search_term','?')}  |  "
            f"视频: {len(videos)}  |  {match_info}"
        )

        root = self.tree.invisibleRootItem()

        for v in videos:
            idx = v.get("index", "?")
            title = v.get("title", "无标题")
            vid = v.get("video_id", "")
            vid_str = f"  ID:{vid}" if vid else ""

            stats = (
                f"👍{v.get('likes','0')}  "
                f"💬{v.get('comments_count','0')}  "
                f"⭐{v.get('collects','0')}  "
                f"↗{v.get('shares','0')}"
            )
            time_str = v.get("matched_users", [{}])[0].get("comment_time", "") if v.get("matched_users") else ""

            video_item = QTreeWidgetItem(root, [
                f"#{idx}  {title[:55]}{vid_str}",
                stats,
                time_str,
            ])
            video_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "video", "data": v})
            video_item.setExpanded(len(v.get("matched_users") or []) <= 5)

            # 匹配用户
            for u in (v.get("matched_users") or []):
                user_item = QTreeWidgetItem(video_item, [
                    f"@{u.get('username','?')}  ·  {u.get('shortId','?')}",
                    f"「{u.get('comment_content','')[:25]}」",
                    u.get("comment_time", ""),
                ])
                user_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "user", "data": u})

            # 评论（无关键字模式）
            for idx_c, c in enumerate(v.get("comments", [])):
                cmt = QTreeWidgetItem(video_item, [
                    f"{c.get('username','?')}",
                    c.get("content", "")[:35],
                    c.get("time", ""),
                ])
                cmt.setData(0, Qt.ItemDataRole.UserRole, {"type": "comment", "data": c})
                if idx_c > 80 and len(v.get("comments", [])) > 120:
                    video_item.setExpanded(False)
                    break

        self.tree.expandAll()

    # ── 任务历史 ──

    def _refresh_tasks(self):
        if not self._task_store:
            return
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("— 选择任务 —", "")
        for t in self._task_store.list_tasks():
            if t.get("status") == "script":
                continue  # 剧本不显示在采集结果页
            status = "✅" if t.get("status") == "completed" else "🔄"
            label = f"{status} {t['created_at'][:16]} | {t.get('search_term','')[:20]}"
            if t.get("notes"):
                label += f" — {t['notes'][:15]}"
            self.task_combo.addItem(label, t["task_id"])
        self.task_combo.blockSignals(False)

    def _on_task_selected(self, index: int):
        if index <= 0 or not self._task_store:
            return
        task_id = self.task_combo.currentData()
        if task_id:
            self._displayed_task_id = task_id
            data = self._task_store.load_result(task_id)
            if data:
                self._data = data
                self._build_tree()

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") == "meta":
            return

        obj = data["data"]
        if data["type"] == "video":
            self.detail_view.setPlainText(
                f"标题: {obj.get('title','')}\n"
                f"ID: {obj.get('video_id','')}\n"
                f"点赞: {obj.get('likes','0')}  |  "
                f"评论: {obj.get('comments_count','0')}  |  "
                f"收藏: {obj.get('collects','0')}  |  "
                f"分享: {obj.get('shares','0')}\n"
                f"\n--- 完整数据 ---\n"
                f"{json.dumps(obj, ensure_ascii=False, indent=2)}"
            )
        else:
            self.detail_view.setPlainText(
                json.dumps(obj, ensure_ascii=False, indent=2)
            )

    def _on_export(self):
        if not self._data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", "", "JSON (*.json)")
        if path:
            self.export_to(path)

    def _on_delete_task(self):
        if not self._task_store:
            return
        current_idx = self.task_combo.currentIndex()
        if current_idx <= 0:
            QMessageBox.warning(self, "提示", "请先选择一个任务。")
            return

        task_id = self.task_combo.currentData()
        task_text = self.task_combo.currentText()
        search_term = ""
        if "|" in task_text:
            search_term = task_text.split("|")[-1].strip()

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除该采集任务吗？\n\n搜索词：{search_term}\n此操作不可恢复。",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        # 记住当前展示的任务 ID，删除后清空
        displayed_task_id = getattr(self, "_displayed_task_id", None)
        self._task_store.delete_task(task_id)

        if displayed_task_id == task_id:
            self._data = None
            self.tree.clear()
            self.detail_view.clear()
            self.summary_label.setText("")

        self._refresh_tasks()
        QMessageBox.information(self, "删除成功", "任务已删除。")
