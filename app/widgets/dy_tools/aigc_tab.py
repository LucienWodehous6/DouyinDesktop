"""AIGC生成子标签 — 即梦文生图、文生视频、图生视频"""

import subprocess
import threading
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QGroupBox, QFormLayout,
    QFileDialog, QProgressBar,
)


class AigcWorker(QThread):
    log_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, str)

    def __init__(self, mode: str, prompt: str, **kwargs):
        super().__init__()
        self.mode = mode
        self.prompt = prompt
        self.kwargs = kwargs

    def run(self):
        try:
            self.log_signal.emit(f"🎨 提交 {self.mode} 生成任务...", "INFO")
            self.progress_signal.emit(10, "准备中...")

            # TODO: 实现 Dreamina 调用
            # 这里先模拟进度
            for i in range(3):
                self.progress_signal.emit(20 + i * 20, f"生成中 ({i+1}/3)...")
                self.sleep(1)

            self.progress_signal.emit(100, "完成")
            self.result_signal.emit({"mode": self.mode, "prompt": self.prompt, "status": "success"})
            self.log_signal.emit(f"✅ 生成完成", "SUCCESS")
        except Exception as e:
            self.error_signal.emit(f"生成失败: {e}")
        finally:
            self.finished_signal.emit()


class AigcTab(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 模式选择
        mode_group = QGroupBox("生成模式")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["文生图", "文生视频", "图生视频"])
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self.mode_combo)

        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["1:1", "16:9", "9:16", "3:4", "4:3"])
        mode_layout.addWidget(QLabel("比例:"))
        mode_layout.addWidget(self.ratio_combo)

        mode_layout.addStretch()

        layout.addWidget(mode_group)

        # 图片输入（图生视频时显示）
        image_group = QGroupBox("图片输入")
        image_layout = QHBoxLayout(image_group)
        image_layout.setSpacing(8)

        self.image_input = QLineEdit()
        self.image_input.setPlaceholderText("选择图片路径...")
        image_layout.addWidget(self.image_input, 1)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setObjectName("smallBtn")
        self.browse_btn.clicked.connect(self._on_browse_image)
        image_layout.addWidget(self.browse_btn)

        layout.addWidget(image_group)

        # 提示词输入
        prompt_group = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("输入画面描述，如：一只可爱的橘猫在阳光下打盹...")
        self.prompt_input.setMinimumHeight(120)
        prompt_layout.addWidget(self.prompt_input)

        # 提示词优化按钮
        prompt_toolbar = QHBoxLayout()
        self.optimize_btn = QPushButton("✨ 优化提示词")
        self.optimize_btn.setObjectName("smallBtn")
        self.optimize_btn.clicked.connect(self._on_optimize_prompt)
        prompt_toolbar.addWidget(self.optimize_btn)
        prompt_toolbar.addStretch()
        prompt_layout.addLayout(prompt_toolbar)

        layout.addWidget(prompt_group)

        # 生成按钮和进度
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self.generate_btn = QPushButton("🎨 开始生成")
        self.generate_btn.setObjectName("primaryBtn")
        self.generate_btn.clicked.connect(self._on_generate)
        bottom.addWidget(self.generate_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        bottom.addWidget(self.progress_bar, 1)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("statusLabel")
        bottom.addWidget(self.progress_label)

        layout.addLayout(bottom)
        layout.addStretch()

        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._on_mode_changed(self.mode_combo.currentText())

    def _on_mode_changed(self, mode: str):
        if mode == "图生视频":
            self.image_input.setEnabled(True)
            self.browse_btn.setEnabled(True)
        else:
            self.image_input.setEnabled(False)
            self.browse_btn.setEnabled(False)

    def _on_browse_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.image_input.setText(path)

    def _on_optimize_prompt(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.progress_label.setText("请输入提示词")
            return
        self.log_signal.emit(f"✨ 优化提示词: {prompt[:20]}...", "INFO")
        # TODO: 调用 prompt 优化接口

    def _on_generate(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.progress_label.setText("请输入提示词")
            return

        mode = self.mode_combo.currentText()
        mode_map = {"文生图": "text2image", "文生视频": "text2video", "图生视频": "image2video"}
        mode_key = mode_map[mode]

        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("生成中...")

        self._worker = AigcWorker(mode_key, prompt)
        self._worker.log_signal.connect(self._handle_log)
        self._worker.progress_signal.connect(self._handle_progress)
        self._worker.result_signal.connect(self._handle_result)
        self._worker.error_signal.connect(self._handle_error)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _handle_log(self, msg: str, level: str):
        self.log_signal.emit(f"[AIGC] {msg}", level)

    def _handle_progress(self, value: int, text: str):
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)

    def _handle_result(self, result: dict):
        self.progress_label.setText(f"✅ {result['mode']} 完成")

    def _handle_error(self, msg: str):
        self.log_signal.emit(f"❌ {msg}", "ERROR")
        self.progress_label.setText(f"错误: {msg}")

    def _on_finished(self):
        self.generate_btn.setEnabled(True)

    def set_settings(self, settings: dict):
        self._settings = settings