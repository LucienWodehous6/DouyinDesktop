"""剧本生成面板 — 素材上传 + 视频信息"""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QListWidget,
    QListWidgetItem, QGroupBox, QTextEdit,
)


class ScriptPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.files: list[str] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("🎬 剧本生成")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("上传图片/视频素材，基于采集的视频信息生成推广剧本")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        # ═════ 素材上传 ═════
        section1 = QLabel("【素材上传】")
        section1.setObjectName("sectionLabel")
        layout.addWidget(section1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        add_img = QPushButton("📷 添加图片")
        add_img.setObjectName("smallBtn")
        add_img.clicked.connect(lambda: self._add_files("图片", "*.jpg *.png *.webp"))
        btn_row.addWidget(add_img)

        add_video = QPushButton("🎬 添加视频")
        add_video.setObjectName("smallBtn")
        add_video.clicked.connect(lambda: self._add_files("视频", "*.mp4 *.mov *.avi"))
        btn_row.addWidget(add_video)

        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("smallBtn")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        layout.addWidget(self.file_list)

        # ═════ 剧本编辑 ═════
        section2 = QLabel("【剧本内容】")
        section2.setObjectName("sectionLabel")
        layout.addWidget(section2)

        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText("在此编辑剧本内容...\n支持从采集结果中拖入视频信息")
        self.script_edit.setMinimumHeight(200)
        layout.addWidget(self.script_edit)

        # ═════ 操作 ═════
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()

        self.gen_btn = QPushButton("✨ 生成剧本")
        self.gen_btn.setObjectName("primaryBtn")
        btn_row2.addWidget(self.gen_btn)

        layout.addLayout(btn_row2)

        layout.addStretch()

    def _add_files(self, label: str, pattern: str):
        files, _ = QFileDialog.getOpenFileNames(
            self, f"选择{label}", "", f"{label} ({pattern})"
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
                item = QListWidgetItem(f"  {os.path.basename(f)}")
                item.setToolTip(f)
                self.file_list.addItem(item)

    def _clear(self):
        self.files.clear()
        self.file_list.clear()
