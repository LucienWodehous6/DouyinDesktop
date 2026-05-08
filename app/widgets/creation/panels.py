"""视频创建子面板组件"""

import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QSlider,
    QMenu, QFileDialog, QDialog,
)
from PyQt6.QtGui import QPixmap


def _extract_image_urls(data: dict) -> list:
    """自动从各种 API 返回中提取图片 URL 列表"""
    for path in ["images", "data.image_urls", "data.images", "data.photos", "result.photos", "output.images"]:
        images = data
        for key in path.split("."):
            images = images.get(key) if isinstance(images, dict) else None
            if images is None:
                break
        if isinstance(images, list) and len(images) > 0:
            urls = []
            for item in images:
                if isinstance(item, dict):
                    url = item.get("url") or item.get("image_url") or ""
                    if url:
                        urls.append(url)
                elif isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
            if urls:
                return urls
    return []


class SceneWidget(QGroupBox):
    """单个分镜 UI 组件"""
    image_generated = pyqtSignal(int)  # scene_index

    def __init__(self, scene_index: int, title: str, prompt: str, voice_text: str = "", panel=None, parent=None):
        super().__init__(f"分镜 {scene_index + 1}: {title}", parent)
        self.scene_index = scene_index
        self._panel = panel
        self.generated_image_path = ""
        self.generated_video_path = ""
        self.generated_voice_path = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 标题行：可编辑标题 + 操作按钮
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("分镜标题:"))

        self.title_edit = QLineEdit(title)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background: #0d1117; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 4px 8px; font-size: 12px;
            }
        """)
        self.title_edit.textChanged.connect(self._on_title_changed)
        title_row.addWidget(self.title_edit, 1)

        self.upload_img_btn = QPushButton("📤 上传图片")
        self.upload_img_btn.setObjectName("smallBtn")
        self.upload_img_btn.clicked.connect(self._on_upload_image)
        title_row.addWidget(self.upload_img_btn)

        layout.addLayout(title_row)

        # ── 口播文案 ──
        layout.addWidget(QLabel("口播文案:"))
        self.voice_edit = QTextEdit()
        self.voice_edit.setPlainText(voice_text)
        self.voice_edit.setMaximumHeight(70)
        self.voice_edit.setStyleSheet("""
            QTextEdit {
                background: #0d1117; color: #dfe6e9;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 8px; font-size: 12px;
            }
        """)
        self.voice_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.voice_edit.customContextMenuRequested.connect(self._on_text_context_menu)
        layout.addWidget(self.voice_edit)

        # 音频行
        voice_btn_row = QHBoxLayout()
        self.gen_voice_btn = QPushButton("🔊 生成音频")
        self.gen_voice_btn.setObjectName("smallBtn")
        self.gen_voice_btn.clicked.connect(self._on_gen_voice)
        voice_btn_row.addWidget(self.gen_voice_btn)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("smallBtn")
        self.play_pause_btn.setFixedWidth(36)
        self.play_pause_btn.setVisible(False)
        self.play_pause_btn.clicked.connect(self._on_play_pause)
        voice_btn_row.addWidget(self.play_pause_btn)

        self.voice_slider = QSlider(Qt.Orientation.Horizontal)
        self.voice_slider.setMinimumHeight(20)
        self.voice_slider.setVisible(False)
        self.voice_slider.sliderMoved.connect(self._on_voice_seek)
        voice_btn_row.addWidget(self.voice_slider, 1)

        self.voice_duration_label = QLabel("00:00 / 00:00")
        self.voice_duration_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.voice_duration_label.setFixedWidth(90)
        self.voice_duration_label.setVisible(False)
        voice_btn_row.addWidget(self.voice_duration_label)

        self.voice_status = QLabel("")
        self.voice_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        voice_btn_row.addWidget(self.voice_status)
        voice_btn_row.addStretch()
        layout.addLayout(voice_btn_row)

        # 提示词
        layout.addWidget(QLabel("生图提示词:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(prompt)
        self.prompt_edit.setMaximumHeight(80)
        self.prompt_edit.setStyleSheet("""
            QTextEdit {
                background: #0d1117; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 8px; font-size: 12px;
            }
        """)
        self.prompt_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.prompt_edit.customContextMenuRequested.connect(self._on_text_context_menu)
        layout.addWidget(self.prompt_edit)

        # 按钮行
        btn_row = QHBoxLayout()
        self.gen_img_btn = QPushButton("🖼️ 生成图片")
        self.gen_img_btn.setObjectName("smallBtn")
        btn_row.addWidget(self.gen_img_btn)

        self.img_status = QLabel("")
        self.img_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        btn_row.addWidget(self.img_status)
        btn_row.addStretch()

        self.gen_video_btn = QPushButton("🎬 生成视频")
        self.gen_video_btn.setObjectName("smallBtn")
        self.gen_video_btn.setEnabled(False)
        btn_row.addWidget(self.gen_video_btn)

        self.upload_video_btn = QPushButton("📤 上传视频")
        self.upload_video_btn.setObjectName("smallBtn")
        self.upload_video_btn.clicked.connect(self._on_upload_video)
        btn_row.addWidget(self.upload_video_btn)
        layout.addLayout(btn_row)

        # 图片预览
        self.img_label = QLabel("")
        self.img_label.setFixedSize(180, 320)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 1px dashed #30363d; border-radius: 8px;")
        self.img_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.img_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.img_label.customContextMenuRequested.connect(self._on_image_context_menu)
        self.img_label.mousePressEvent = lambda e: self._on_image_click() if e.button() == Qt.MouseButton.LeftButton else None
        layout.addWidget(self.img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 视频状态
        self.video_status_label = QLabel("")
        self.video_status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.video_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_status_label.setVisible(False)
        layout.addWidget(self.video_status_label)

        self.play_video_btn = QPushButton("[ 播放视频 ]")
        self.play_video_btn.setObjectName("smallBtn")
        self.play_video_btn.setVisible(False)
        self.play_video_btn.clicked.connect(self._play_video)
        layout.addWidget(self.play_video_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_title_changed(self, text: str):
        """修改分镜标题后同步更新 GroupBox 标题和场景数据"""
        self.setTitle(f"分镜 {self.scene_index + 1}: {text}")
        if self._panel and self.scene_index < len(self._panel._scenes):
            self._panel._scenes[self.scene_index]["title"] = text

    def _on_gen_voice(self):
        """为当前分镜生成语音"""
        from PyQt6.QtWidgets import QMessageBox
        text = self.voice_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "口播文案为空，请先填写口播内容。")
            return
        if self._panel:
            self._panel._generate_scene_voice(self.scene_index)

    def _on_play_pause(self):
        """播放/暂停当前分镜的语音"""
        if not self.generated_voice_path or not os.path.exists(self.generated_voice_path):
            return
        if self._panel:
            player = self._panel._audio_player
            if player.playbackState() == player.PlaybackState.PlayingState:
                player.pause()
            else:
                from PyQt6.QtCore import QUrl
                self._panel._current_playing_scene = self.scene_index
                if player.source().toLocalFile() != self.generated_voice_path:
                    player.setSource(QUrl.fromLocalFile(self.generated_voice_path))
                player.play()

    def _on_voice_seek(self, position):
        if self._panel:
            self._panel._audio_player.setPosition(position)

    def _on_upload_image(self):
        """上传自定义图片作为分镜图片"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择分镜图片", "",
            "Images (*.jpg *.jpeg *.png *.webp)")
        if not path:
            return
        import shutil
        import tempfile
        ext = os.path.splitext(path)[1] or ".png"
        dst = os.path.join(tempfile.gettempdir(), f"dy_scene_{self.scene_index}_{os.getpid()}{ext}")
        shutil.copy2(path, dst)
        self.generated_image_path = dst

        pixmap = QPixmap(dst).scaled(180, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        self.img_label.setPixmap(pixmap)
        self.img_label.setStyleSheet("border: 1px solid #2ed573; border-radius: 8px;")
        self.img_status.setText("📤 自定义图片")
        self.img_status.setStyleSheet("color: #2ed573; font-size: 11px;")
        self.gen_video_btn.setEnabled(True)
        if self._panel:
            self._panel._scenes[self.scene_index]["image"] = dst
        print(f"[视频创作] 分镜{self.scene_index+1} 已上传自定义图片: {dst}")

    def _on_upload_video(self):
        """上传自定义视频作为分镜视频"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择分镜视频", "",
            "视频 (*.mp4 *.mov *.avi *.mkv *.webm)")
        if not path:
            return
        import shutil, tempfile
        ext = os.path.splitext(path)[1] or ".mp4"
        dst = os.path.join(tempfile.gettempdir(), f"dy_video_{self.scene_index}_{os.getpid()}{ext}")
        shutil.copy2(path, dst)
        self.generated_video_path = dst
        if self._panel:
            self._panel._scenes[self.scene_index]["video"] = dst
        self.video_status_label.setText("📤 自定义视频")
        self.video_status_label.setStyleSheet("color: #2ed573; font-size: 11px;")
        self.video_status_label.setVisible(True)
        self.play_video_btn.setVisible(True)
        self.gen_video_btn.setText("🎬 重新生成")
        self.gen_video_btn.setEnabled(True)
        print(f"[视频创作] 分镜{self.scene_index+1} 已上传自定义视频: {dst}")

    def _on_image_click(self):
        """点击图片放大查看"""
        if not self.generated_image_path:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"分镜 {self.scene_index + 1} - 预览")
        dialog.setFixedSize(600, 900)
        dl = QVBoxLayout(dialog)
        lbl = QLabel()
        pixmap = QPixmap(self.generated_image_path).scaled(
            560, 840, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pixmap)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(lbl)
        dialog.exec()

    def _play_video(self):
        """用系统默认播放器打开视频"""
        if not self.generated_video_path:
            return
        import subprocess
        path = self.generated_video_path
        if sys.platform == "darwin":
            subprocess.run(["open", path])
        elif sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path])

    def _on_image_context_menu(self, pos):
        """右键菜单：另存为"""
        if not self.generated_image_path:
            return
        menu = QMenu(self)
        save_action = menu.addAction("另存为……")
        action = menu.exec(self.img_label.mapToGlobal(pos))
        if action == save_action:
            default_name = f"scene_{self.scene_index + 1}.png"
            path, _ = QFileDialog.getSaveFileName(self, "保存图片", default_name, "PNG (*.png)")
            if path:
                import shutil
                shutil.copy2(self.generated_image_path, path)
                print(f"[视频创作] 图片已保存: {path}")

    def _on_text_context_menu(self, pos):
        """中文右键菜单"""
        menu = QMenu(self)
        edit = self.prompt_edit
        menu.addAction("撤销", edit.undo).setEnabled(edit.document().isUndoAvailable())
        menu.addAction("重做", edit.redo).setEnabled(edit.document().isRedoAvailable())
        menu.addSeparator()
        menu.addAction("剪切", edit.cut).setEnabled(edit.textCursor().hasSelection())
        menu.addAction("复制", edit.copy).setEnabled(edit.textCursor().hasSelection())
        menu.addAction("粘贴", edit.paste)
        menu.addAction("删除", lambda e=edit: e.textCursor().removeSelectedText()).setEnabled(edit.textCursor().hasSelection())
        menu.addSeparator()
        menu.addAction("全选", edit.selectAll)
        menu.exec(edit.mapToGlobal(pos))