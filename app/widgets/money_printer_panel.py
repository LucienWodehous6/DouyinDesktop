"""AI 视频面板 - MoneyPrinterTurbo 集成"""

import os
import sys
import json
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QScrollArea, QFrame, QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QFont

from app.widgets.common_widgets import CLineEdit
from core_modules.mpt_services import TaskRunner


class MPTWorker(QThread):
    """MoneyPrinterTurbo 工作线程"""
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, topic, script, keywords, settings):
        super().__init__()
        self.topic = topic
        self.script = script
        self.keywords = keywords
        self.settings = settings

    def run(self):
        try:
            runner = TaskRunner(
                text_api_base=self.settings.get("openai_text_api_base", "https://api.deepseek.com/v1"),
                text_api_key=self.settings.get("openai_text_api_key", ""),
                text_model=self.settings.get("openai_text_model", "deepseek-chat"),
                voice_role=self.settings.get("mpt_voice_role", "zh-CN-XiaoxiaoNeural"),
                video_source=self.settings.get("mpt_video_source", "pexels"),
                video_api_key=self.settings.get("pexels_api_key", ""),
                video_format=self.settings.get("mpt_video_format", "9:16"),
                subtitle_enabled=self.settings.get("mpt_subtitle_enabled", True),
                bg_music=self.settings.get("mpt_bg_music", ""),
                bg_music_volume=self.settings.get("mpt_bg_music_volume", 0.3),
                progress_callback=self._on_progress,
                log_callback=self._on_log
            )

            result = runner.run(
                topic=self.topic,
                script=self.script if self.script else None,
                keywords=self.keywords if self.keywords else None,
                material_count=self.settings.get("mpt_material_count", 5)
            )

            runner.cleanup()
            self.finished_signal.emit(result)

        except Exception as e:
            self.error_signal.emit(str(e))

    def _on_progress(self, percent):
        self.progress_signal.emit(percent)

    def _on_log(self, message, level):
        self.log_signal.emit(message, level)


class MoneyPrinterPanel(QWidget):
    """AI 视频生成面板"""

    def __init__(self, task_store=None, settings=None):
        super().__init__()
        self.task_store = task_store
        self.settings = settings or {}
        self.worker = None
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
            QScrollArea { background: transparent; }
            QScrollArea > QWidget { background: transparent; }
            QScrollBar:vertical { background: #161b22; width: 6px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; min-height: 30px; }
        """)
        outer.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)
        scroll.setWidget(content)

        # 标题
        title = QLabel("🤖 AI 视频生成")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # 说明
        desc = QLabel("输入主题关键词，AI 自动生成文案、合成语音、匹配素材、拼接视频")
        desc.setObjectName("sectionLabel")
        layout.addWidget(desc)

        # ═══════════════════════════════════
        #  主题输入
        # ═══════════════════════════════════
        section1 = QLabel("【视频主题】")
        section1.setObjectName("sectionLabel")
        layout.addWidget(section1)

        self.topic_input = CLineEdit()
        self.topic_input.setPlaceholderText("输入视频主题，如：健身教程、美食推荐、科技测评")
        self.topic_input.setMinimumHeight(44)
        layout.addWidget(self.topic_input)

        # 素材关键词
        self.keywords_input = CLineEdit()
        self.keywords_input.setPlaceholderText("素材搜索关键词（多个用逗号分隔），如：健身动作,健康饮食")
        self.keywords_input.setMinimumHeight(38)
        layout.addWidget(self.keywords_input)

        # ═══════════════════════════════════
        #  文案编辑
        # ═══════════════════════════════════
        section2 = QLabel("【视频文案】")
        section2.setObjectName("sectionLabel")
        layout.addWidget(section2)

        self.script_area = QTextEdit()
        self.script_area.setPlaceholderText("在此编辑视频文案（可选），留空则 AI 自动生成...")
        self.script_area.setMinimumHeight(150)
        self.script_area.setStyleSheet("""
            QTextEdit {
                background: #1e2530;
                color: #dfe6e9;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.script_area)

        # 文案生成按钮
        self.generate_script_btn = QPushButton("✨ AI 生成文案")
        self.generate_script_btn.setObjectName("smallBtn")
        self.generate_script_btn.clicked.connect(self._on_generate_script)
        layout.addWidget(self.generate_script_btn)

        # ═══════════════════════════════════
        #  语音配置
        # ═══════════════════════════════════
        section3 = QLabel("【语音配置】")
        section3.setObjectName("sectionLabel")
        layout.addWidget(section3)

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("语音角色"))

        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumHeight(36)
        self.voice_combo.addItems([
            "zh-CN-XiaoxiaoNeural (晓晓 - 女声)",
            "zh-CN-YunxiNeural (云希 - 男声)",
            "zh-CN-YunyangNeural (云扬 - 男声)",
            "zh-CN-XiaoyiNeural (小艺 - 女声)",
            "zh-CN-YunyeNeural (云野 - 男声)",
            "en-US-JennyNeural (Jenny - 英女声)",
            "en-US-GuyNeural (Guy - 英男声)",
        ])
        voice_row.addWidget(self.voice_combo, 1)
        layout.addLayout(voice_row)

        # ═══════════════════════════════════
        #  视频设置
        # ═══════════════════════════════════
        section4 = QLabel("【视频设置】")
        section4.setObjectName("sectionLabel")
        layout.addWidget(section4)

        video_settings = QHBoxLayout()
        video_settings.setSpacing(12)

        video_settings.addWidget(QLabel("视频格式"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["9:16 竖屏 (1080x1920)", "16:9 横屏 (1920x1080)"])
        self.format_combo.setMinimumHeight(36)
        video_settings.addWidget(self.format_combo, 1)

        video_settings.addWidget(QLabel("素材数量"))
        self.material_count_spin = QSpinBox()
        self.material_count_spin.setRange(1, 20)
        self.material_count_spin.setValue(5)
        self.material_count_spin.setMinimumHeight(36)
        video_settings.addWidget(self.material_count_spin)

        layout.addLayout(video_settings)

        # ═══════════════════════════════════
        #  字幕与音乐
        # ═══════════════════════════════════
        section5 = QLabel("【字幕与音乐】")
        section5.setObjectName("sectionLabel")
        layout.addWidget(section5)

        self.subtitle_check = QCheckBox("生成字幕")
        self.subtitle_check.setChecked(True)
        layout.addWidget(self.subtitle_check)

        bg_music_row = QHBoxLayout()
        self.bg_music_check = QCheckBox("背景音乐")
        self.bg_music_check.toggled.connect(self._on_bg_music_toggled)
        bg_music_row.addWidget(self.bg_music_check)

        self.bg_music_input = CLineEdit()
        self.bg_music_input.setPlaceholderText("选择背景音乐文件...")
        self.bg_music_input.setVisible(False)
        bg_music_row.addWidget(self.bg_music_input, 1)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setObjectName("smallBtn")
        self.browse_btn.setVisible(False)
        self.browse_btn.clicked.connect(self._on_browse_music)
        bg_music_row.addWidget(self.browse_btn)

        layout.addLayout(bg_music_row)

        # ═══════════════════════════════════
        #  进度显示
        # ═══════════════════════════════════
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #1e2530;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #dfe6e9;
            }
            QProgressBar::chunk {
                background: #2ed573;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setMinimumHeight(120)
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background: #161b22;
                color: #dfe6e9;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_area)

        # ═══════════════════════════════════
        #  操作按钮
        # ═══════════════════════════════════
        action_row = QHBoxLayout()

        self.start_btn = QPushButton("🎬 开始生成视频")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.clicked.connect(self._on_start)
        action_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop)
        action_row.addWidget(self.stop_btn)

        action_row.addStretch()

        self.open_btn = QPushButton("📂 打开文件夹")
        self.open_btn.setObjectName("smallBtn")
        self.open_btn.clicked.connect(self._on_open_folder)
        action_row.addWidget(self.open_btn)

        layout.addLayout(action_row)

    def _on_bg_music_toggled(self, checked: bool):
        self.bg_music_input.setVisible(checked)
        self.browse_btn.setVisible(checked)

    def _on_browse_music(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择背景音乐", "", "音频文件 (*.mp3 *.wav *.m4a)")
        if path:
            self.bg_music_input.setText(path)

    def _on_generate_script(self):
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入视频主题")
            return

        keywords_text = self.keywords_input.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else None

        self._log("正在调用 AI 生成文案...", "INFO")
        self.generate_script_btn.setEnabled(False)

        # 使用简单的同步方式生成文案（可以用 QThread 实现异步）
        try:
            from core_modules.mpt_services import LLMService
            llm = LLMService(
                api_base=self.settings.get("openai_text_api_base", "https://api.deepseek.com/v1"),
                api_key=self.settings.get("openai_text_api_key", ""),
                model=self.settings.get("openai_text_model", "deepseek-chat")
            )

            if keywords:
                script = llm.generate_script_with_keywords(topic, keywords)
            else:
                script = llm.generate_script(topic)

            self.script_area.setPlainText(script)
            self._log("文案生成完成", "SUCCESS")

        except Exception as e:
            self._log(f"文案生成失败: {e}", "ERROR")
            QMessageBox.critical(self, "错误", f"文案生成失败:\n{e}")
        finally:
            self.generate_script_btn.setEnabled(True)

    def _on_start(self):
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入视频主题")
            return

        script_text = self.script_area.toPlainText().strip()

        keywords_text = self.keywords_input.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else None

        # 准备设置
        voice_text = self.voice_combo.currentText()
        voice_role = voice_text.split(" ")[0]  # 取括号前的部分作为 role 名

        # 从完整选项中提取正确的 role
        role_map = {
            "zh-CN-XiaoxiaoNeural": "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunxiNeural": "zh-CN-YunxiNeural",
            "zh-CN-YunyangNeural": "zh-CN-YunyangNeural",
            "zh-CN-XiaoyiNeural": "zh-CN-XiaoyiNeural",
            "zh-CN-YunyeNeural": "zh-CN-YunyeNeural",
            "en-US-JennyNeural": "en-US-JennyNeural",
            "en-US-GuyNeural": "en-US-GuyNeural",
        }

        # 提取 role
        display_text = self.voice_combo.currentText()
        for role_key, role_val in role_map.items():
            if role_key in display_text:
                voice_role = role_val
                break

        format_text = self.format_combo.currentText()
        video_format = "9:16" if "9:16" in format_text else "16:9"

        settings = {
            "openai_text_api_base": self.settings.get("openai_text_api_base", "https://api.deepseek.com/v1"),
            "openai_text_api_key": self.settings.get("openai_text_api_key", ""),
            "openai_text_model": self.settings.get("openai_text_model", "deepseek-chat"),
            "mpt_voice_role": voice_role,
            "mpt_video_source": "pexels",
            "pexels_api_key": self.settings.get("pexels_api_key", ""),
            "mpt_video_format": video_format,
            "mpt_subtitle_enabled": self.subtitle_check.isChecked(),
            "mpt_bg_music": self.bg_music_input.text() if self.bg_music_check.isChecked() else "",
            "mpt_bg_music_volume": 0.3,
            "mpt_material_count": self.material_count_spin.value(),
        }

        self._set_running(True)
        self._log("=" * 50, "INFO")
        self._log("开始 AI 视频生成任务", "INFO")
        self._log(f"主题: {topic}", "INFO")
        if keywords:
            self._log(f"关键词: {', '.join(keywords)}", "INFO")
        self._log(f"素材数量: {self.material_count_spin.value()}", "INFO")
        self._log(f"视频格式: {video_format}", "INFO")
        self._log("=" * 50, "INFO")

        self.worker = MPTWorker(topic, script_text if script_text else None, keywords, settings)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.log_signal.connect(self._on_log)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(3000)
            self._log("任务已停止", "WARN")
            self._set_running(False)

    def _on_progress(self, percent):
        self.progress_bar.setValue(percent)

    def _on_log(self, message, level):
        prefix = {"INFO": "[*]", "SUCCESS": "[✓]", "WARN": "[!]", "ERROR": "[✗]"}.get(level, "[*]")
        self.log_area.append(f"{prefix} {message}")

    def _on_finished(self, video_path):
        self._log(f"视频生成完成: {video_path}", "SUCCESS")
        self._set_running(False)
        QMessageBox.information(self, "完成", f"视频已生成:\n{video_path}")

    def _on_error(self, message):
        self._log(f"错误: {message}", "ERROR")
        self._set_running(False)
        QMessageBox.critical(self, "错误", f"任务执行失败:\n{message}")

    def _on_open_folder(self):
        if self.worker and self.worker.isFinished():
            QMessageBox.information(self, "提示", "请从日志中复制视频路径")

    def _set_running(self, running: bool):
        self.start_btn.setVisible(not running)
        self.stop_btn.setVisible(running)
        self.topic_input.setEnabled(not running)
        self.keywords_input.setEnabled(not running)
        self.script_area.setEnabled(not running)
        self.voice_combo.setEnabled(not running)
        self.format_combo.setEnabled(not running)
        self.material_count_spin.setEnabled(not running)
        self.subtitle_check.setEnabled(not running)
        self.bg_music_check.setEnabled(not running)
        self.bg_music_input.setEnabled(not running)
        self.browse_btn.setEnabled(not running)
        self.generate_script_btn.setEnabled(not running)

    def _log(self, message, level="INFO"):
        self._on_log(message, level)

    def set_settings(self, settings):
        self.settings = settings
        # 加载上次的配置
        voice_role = settings.get("mpt_voice_role", "zh-CN-XiaoxiaoNeural")
        for i, text in enumerate(self.voice_combo.itemText(i) for i in range(self.voice_combo.count())):
            if voice_role in text:
                self.voice_combo.setCurrentIndex(i)
                break

        video_format = settings.get("mpt_video_format", "9:16")
        self.format_combo.setCurrentIndex(0 if video_format == "9:16" else 1)
        self.subtitle_check.setChecked(settings.get("mpt_subtitle_enabled", True))