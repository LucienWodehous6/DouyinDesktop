"""协作流页面 — 可视化节点编排"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QFrame,
    QProgressBar,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import os


class WorkflowPage(QWidget):
    """协作流页面 — 多 Agent 流水线可视化编排"""

    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._pipeline_worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QFrame()
        header.setObjectName("pageHeader")
        header.setStyleSheet("background: #161b22; border-bottom: 1px solid #21262d;")
        header.setMinimumHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("⚡ 协作流")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setFixedWidth(100)
        self.run_btn.clicked.connect(self._on_run)
        header_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        header_layout.addWidget(self.stop_btn)

        layout.addWidget(header)

        # 主内容区
        content = QHBoxLayout()
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(12)

        # 左侧：节点列表
        left_panel = QFrame()
        left_panel.setObjectName("nodePanel")
        left_panel.setFixedWidth(200)
        left_panel.setStyleSheet("background: #161b22; border-radius: 8px; padding: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        node_label = QLabel("节点")
        node_label.setObjectName("sectionLabel")
        left_layout.addWidget(node_label)

        self.node_list = QListWidget()
        self.node_list.setObjectName("nodeList")
        self._populate_nodes()
        left_layout.addWidget(self.node_list)

        left_layout.addStretch()
        content.addWidget(left_panel)

        # 中间：可视化编辑器（简化版）
        self.canvas = QFrame()
        self.canvas.setObjectName("workflowCanvas")
        self.canvas.setStyleSheet("background: #0d1117; border: 1px solid #21262d; border-radius: 8px;")
        content.addWidget(self.canvas, 1)

        # 右侧：配置面板
        right_panel = QFrame()
        right_panel.setObjectName("configPanel")
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("background: #161b22; border-radius: 8px; padding: 12px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)

        config_label = QLabel("节点配置")
        config_label.setObjectName("sectionLabel")
        right_layout.addWidget(config_label)

        self.config_text = QTextEdit()
        self.config_text.setPlaceholderText("选择节点查看配置...")
        self.config_text.setObjectName("configEdit")
        right_layout.addWidget(self.config_text, 1)

        layout.addLayout(content)

        # 底部：日志面板
        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        log_frame.setMinimumHeight(150)
        log_frame.setStyleSheet("background: #0d1117; border-top: 1px solid #21262d;")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(12, 8, 12, 8)

        log_label = QLabel("执行日志")
        log_label.setObjectName("sectionLabel")
        log_layout.addWidget(log_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")
        self.log_view.setStyleSheet("""
            QTextEdit#logView {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #21262d;
                border-radius: 6px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_view)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        log_layout.addWidget(self.progress_bar)

        layout.addWidget(log_frame)

    def _populate_nodes(self):
        """填充默认节点列表"""
        nodes = [
            ("CDO", "数据采集"),
            ("CCO", "内容创作"),
            ("SEO", "SEO优化"),
            ("CMO", "发布分发"),
        ]
        for node_id, node_name in nodes:
            item = QListWidgetItem(f"{node_id} — {node_name}")
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            self.node_list.addItem(item)

    def _on_run(self):
        """开始执行流水线"""
        self.log_view.clear()
        self.log_view.append("[Pipeline] 开始执行...")

        # 从 settings 读取 API 配置
        api_key = self._settings.get("openai_api_key", "")
        api_base = self._settings.get("openai_text_api_base", "https://api.deepseek.com/v1")
        model = self._settings.get("openai_text_model", "deepseek-chat")

        agents = [
            {"Name": "CDO", "config": {
                "keyword": "测试",
                "platform": "抖音",
                "count": 10,
            }},
            {"Name": "CCO", "config": {
                "api_key": api_key,
                "api_base": api_base,
                "model": model,
                "style": "neutral",
            }},
            {"Name": "SEO", "config": {
                "api_key": api_key,
                "api_base": api_base,
                "model": model,
            }},
            {"Name": "CMO", "config": {
                "api_key": api_key,
                "api_base": api_base,
                "model": model,
                "target_platform": "抖音",
            }},
        ]

        output_dir = os.path.join(os.path.expanduser("~"), ".dy", "workflow_output")
        os.makedirs(output_dir, exist_ok=True)

        from app.widgets.workflow.pipeline_worker import PipelineWorker
        self._pipeline_worker = PipelineWorker(agents, output_dir)
        self._pipeline_worker.log_signal.connect(self._on_log)
        self._pipeline_worker.progress_signal.connect(self._on_progress)
        self._pipeline_worker.finished_signal.connect(self._on_finished)
        self._pipeline_worker.error_signal.connect(self._on_error)

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._pipeline_worker.start()

    def _on_stop(self):
        if self._pipeline_worker:
            self._pipeline_worker.stop()
            self._pipeline_worker.wait()
            self.log_view.append("[Pipeline] 用户停止执行")

    def _on_log(self, agent: str, msg: str):
        self.log_view.append(f"[{agent}] {msg}")

    def _on_progress(self, percent: int, status: str):
        self.progress_bar.setValue(percent)

    def _on_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_view.append("[Pipeline] ✓ 全部完成，输出文件已清理")

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_view.append(f"[Pipeline] ✗ 错误: {msg}")