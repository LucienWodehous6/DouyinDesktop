"""互动操作子标签 — 点赞、评论、关注、收藏"""

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QGroupBox, QFormLayout,
)


class InteractionWorker(QThread):
    log_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, action: str, target: str, content: str = ""):
        super().__init__()
        self.action = action
        self.target = target
        self.content = content

    def run(self):
        try:
            self.log_signal.emit(f"⚡ 执行 {self.action}: {self.target[:30]}...", "INFO")
            # TODO: 实现互动操作
            self.result_signal.emit({"action": self.action, "target": self.target, "success": True})
            self.log_signal.emit(f"✅ 操作完成", "SUCCESS")
        except Exception as e:
            self.error_signal.emit(f"操作失败: {e}")
        finally:
            self.finished_signal.emit()


class InteractionTab(QWidget):
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

        # 操作类型选择
        action_group = QGroupBox("互动操作")
        action_layout = QHBoxLayout(action_group)
        action_layout.setSpacing(12)

        self.action_combo = QComboBox()
        self.action_combo.addItems(["点赞", "取消点赞", "收藏", "取消收藏", "评论", "关注"])
        action_layout.addWidget(QLabel("操作:"))
        action_layout.addWidget(self.action_combo)

        action_layout.addStretch()

        layout.addWidget(action_group)

        # 目标输入
        target_group = QGroupBox("目标")
        target_layout = QVBoxLayout(target_group)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("视频链接 / aweme_id / 用户 sec_user_id...")
        target_layout.addWidget(self.target_input)

        # 评论内容（仅评论时显示）
        self.comment_widget = QWidget()
        self.comment_box = QVBoxLayout(self.comment_widget)
        self.comment_label = QLabel("评论内容:")
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("输入评论内容...")
        self.comment_input.setMaximumHeight(80)
        self.comment_box.addWidget(self.comment_label)
        self.comment_box.addWidget(self.comment_input)
        self.comment_widget.setVisible(False)
        target_layout.addWidget(self.comment_widget)

        layout.addWidget(target_group)

        # 批量设置
        batch_group = QGroupBox("批量操作")
        batch_layout = QFormLayout(batch_group)
        batch_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.batch_count = QLineEdit("1")
        self.batch_delay = QLineEdit("2")
        batch_layout.addRow("批量数量:", self.batch_count)
        batch_layout.addRow("间隔(秒):", self.batch_delay)

        layout.addWidget(batch_group)

        # 执行按钮
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.execute_btn = QPushButton("⚡ 执行")
        self.execute_btn.setObjectName("primaryBtn")
        self.execute_btn.clicked.connect(self._on_execute)
        bottom.addWidget(self.execute_btn)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label)

        bottom.addStretch()

        layout.addLayout(bottom)
        layout.addStretch()

        # 操作类型变化时显示/隐藏评论输入
        self.action_combo.currentTextChanged.connect(self._on_action_changed)

    def _on_action_changed(self, text: str):
        if text == "评论":
            self.comment_widget.setVisible(True)
        else:
            self.comment_widget.setVisible(False)

    def _on_execute(self):
        target = self.target_input.text().strip()
        if not target:
            self.status_label.setText("请输入目标")
            return

        action = self.action_combo.currentText()
        content = self.comment_input.toPlainText().strip() if action == "评论" else ""

        self.execute_btn.setEnabled(False)
        self.status_label.setText("执行中...")

        self._worker = InteractionWorker(action, target, content)
        self._worker.log_signal.connect(self._handle_log)
        self._worker.result_signal.connect(self._handle_result)
        self._worker.error_signal.connect(self._handle_error)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _handle_log(self, msg: str, level: str):
        self.log_signal.emit(f"[互动] {msg}", level)

    def _handle_result(self, result: dict):
        self.status_label.setText(f"✅ {result['action']} 成功")

    def _handle_error(self, msg: str):
        self.log_signal.emit(f"❌ {msg}", "ERROR")
        self.status_label.setText(f"错误: {msg}")

    def _on_finished(self):
        self.execute_btn.setEnabled(True)

    def set_settings(self, settings: dict):
        self._settings = settings