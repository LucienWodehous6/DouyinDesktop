"""Skill 执行 Tab — 列出可用 Skills 并执行"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.skills.registry import SkillRegistry
from app.skills._skill_base import SkillResult


class SkillExecutorTab(QWidget):
    """Skill 执行界面"""

    log_signal = pyqtSignal(str, str)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._current_skill: dict | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("⚡ Skill 执行器")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # 左侧：Skill 列表
        content = QHBoxLayout()

        self.skill_list = QListWidget()
        self.skill_list.setMinimumWidth(200)
        self.skill_list.currentItemChanged.connect(self._on_skill_selected)
        content.addWidget(self.skill_list, 1)

        # 右侧：Skill 详情和执行
        right = QVBoxLayout()

        self.skill_desc = QLabel("选择一个 Skill 开始")
        self.skill_desc.setWordWrap(True)
        right.addWidget(self.skill_desc)

        # 参数表单
        self.params_box = QGroupBox("输入参数")
        params_layout = QFormLayout()
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("视频主题/话题")
        params_layout.addRow("topic:", self.topic_input)
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("60")
        params_layout.addRow("duration (秒):", self.duration_input)
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["neutral", "funny", "serious", "warm"])
        params_layout.addRow("tone:", self.tone_combo)
        self.params_box.setLayout(params_layout)
        right.addWidget(self.params_box)

        # 输出区
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Skill 输出将显示在这里...")
        right.addWidget(self.output_text, 1)

        # 执行按钮
        exec_layout = QHBoxLayout()
        self.exec_btn = QPushButton("⚡ 执行 Skill")
        self.exec_btn.setObjectName("primaryBtn")
        self.exec_btn.clicked.connect(self._on_execute)
        self.exec_btn.setEnabled(False)
        exec_layout.addWidget(self.exec_btn)
        exec_layout.addStretch()
        right.addLayout(exec_layout)

        content.addLayout(right, 3)
        layout.addLayout(content, 1)

        self._load_skills()

    def _load_skills(self):
        registry = SkillRegistry.get_instance()
        for skill_info in registry.list_skills():
            item = QListWidgetItem(skill_info.get("id", "unknown"))
            item.setData(Qt.ItemDataRole.UserRole, skill_info)
            self.skill_list.addItem(item)

    def _on_skill_selected(self, current: QListWidgetItem | None):
        if not current:
            return
        self._current_skill = current.data(Qt.ItemDataRole.UserRole)
        desc = self._current_skill.get("metadata", {}).get("description", "")
        self.skill_desc.setText(f"**{self._current_skill['id']}**: {desc}")
        self.exec_btn.setEnabled(True)

    def _on_execute(self):
        if not self._current_skill:
            return
        skill_id = self._current_skill["id"]
        try:
            duration = int(self.duration_input.text() or "60")
        except ValueError:
            duration = 60
        params = {
            "topic": self.topic_input.text().strip(),
            "duration": duration,
            "tone": self.tone_combo.currentText(),
        }
        self.log_signal.emit(f"[Skill] 开始执行: {skill_id}", "INFO")
        self.output_text.append(f"⚡ 执行 {skill_id}...\n")

        # TODO: 实际调用 LLM，暂用模拟输出
        self.output_text.append(f"📝 主题: {params['topic']}\n")
        self.output_text.append("✅ Skill 执行完成（模拟）")
        self.log_signal.emit(f"[Skill] {skill_id} 执行完成", "SUCCESS")
