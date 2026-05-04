"""视频分析面板 — 提取视频文案 + AI 仿写生成"""

import os
import sys
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QGroupBox,
    QProgressBar, QMessageBox, QSplitter,
)


class ExtractWorker(QThread):
    """阶段 1: 提取视频文案"""

    log_signal = pyqtSignal(str)
    copy_extracted = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, video_url: str, settings: dict, parent=None):
        super().__init__(parent)
        self.video_url = video_url.strip()
        self.settings = settings
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            self.log_signal.emit("🔍 正在解析视频链接...")
            self.progress_signal.emit(10)

            api_key = (
                self.settings.get("video_api_key") or
                self.settings.get("openai_text_api_key") or
                self.settings.get("openai_api_key") or
                os.environ.get("DOUYIN_API_KEY") or
                os.environ.get("API_KEY", "")
            )
            if not api_key:
                self.error_signal.emit("未配置 API 密钥。请在设置 → 语音转文字 中配置密钥。")
                return

            import douyin_downloader as dld

            self.log_signal.emit("⏳ 正在下载视频并提取语音文案（约需 30~60 秒，请耐心等待）...")
            self.progress_signal.emit(20)

            result = dld.extract_text(self.video_url, api_key=api_key, show_progress=False)
            raw_text = result.get("text", "")
            title = result.get("video_info", {}).get("title", "")

            if not raw_text.strip():
                self.error_signal.emit("未能从视频中提取到语音文案，视频可能没有配音或语音不清晰。")
                return

            self.progress_signal.emit(100)
            self.log_signal.emit(f"✅ 文案提取成功！标题: {title}，共 {len(raw_text)} 字符")

            self.copy_extracted.emit(raw_text)

        except Exception as e:
            self.error_signal.emit(str(e))


class GenerateWorker(QThread):
    """阶段 2: AI 仿写（仅生成，不复用提取阶段）"""

    log_signal = pyqtSignal(str)
    ai_chunk = pyqtSignal(str)
    ai_done = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, reference_copy: str, product_info: str, settings: dict, system_prompt: str = "", parent=None):
        super().__init__(parent)
        self.reference_copy = reference_copy
        self.product_info = product_info.strip()
        self.settings = settings
        self.system_prompt = system_prompt
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            self.log_signal.emit("🤖 正在调用 AI 生成仿写文案...")
            self.progress_signal.emit(10)

            api_key = (
                self.settings.get("openai_text_api_key") or
                self.settings.get("openai_api_key") or
                os.environ.get("OPENAI_API_KEY", "")
            )
            api_base = (
                self.settings.get("openai_text_api_base") or
                self.settings.get("openai_api_base") or
                os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1")
            )
            model = (
                self.settings.get("openai_text_model") or
                self.settings.get("openai_model") or
                os.environ.get("OPENAI_MODEL", "deepseek-chat")
            )

            if not api_key:
                self.error_signal.emit("未配置文字 AI 模型密钥。请在设置页面配置。")
                return

            from openai import OpenAI

            base_url = api_base.rstrip("/")
            client = OpenAI(api_key=api_key, base_url=base_url)

            system_prompt = self.system_prompt
            if system_prompt:
                # 追加用户优先规则（与 script_panel 保持一致）
                system_prompt += (
                    "\n\n---\n\n"
                    "## 重要规则：用户提示词优先\n\n"
                    "如果用户的提示词与上述系统预置规则存在冲突，"
                    "必须以用户提示词为准，忽略冲突的系统规则。"
                )
            else:
                # 兜底：内置基础提示词
                system_prompt = (
                    "你是一个专业的短视频文案策划师。请根据参考视频文案的风格，"
                    "为用户指定的产品/服务创作一条类似风格的视频口播文案。"
                    "直接输出可用的口播文案，不要解释分析过程。"
                )

            user_prompt = (
                f"## 参考视频文案\n\n{self.reference_copy}\n\n"
                f"## 我的产品/服务\n\n{self.product_info}\n\n"
                f"请根据以上参考文案的风格，为我的产品/服务创作一条类似风格的视频口播文案。"
            )

            self.log_signal.emit(f"📡 API: {api_base} | 模型: {model}")
            self.log_signal.emit(f"📋 提示词: 系统 {len(system_prompt)} 字符 + 用户 {len(user_prompt)} 字符")
            self.progress_signal.emit(20)

            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=4096,
                stream=True,
            )

            self.progress_signal.emit(30)
            full_content = ""
            THINK_OPEN = "<think>"
            THINK_CLOSE = "</think>"
            in_think = False

            for chunk in stream:
                if self._stopped:
                    break
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", "") or ""
                if not text:
                    continue

                remaining = text
                while remaining:
                    if not in_think:
                        idx = remaining.find(THINK_OPEN)
                        if idx == -1:
                            full_content += remaining
                            self.ai_chunk.emit(remaining)
                            break
                        else:
                            full_content += remaining[:idx]
                            self.ai_chunk.emit(remaining[:idx])
                            self.log_signal.emit("💭 [思考中]")
                            in_think = True
                            remaining = remaining[idx + len(THINK_OPEN):]
                    else:
                        idx = remaining.find(THINK_CLOSE)
                        if idx == -1:
                            break
                        else:
                            self.log_signal.emit("💭 [思考结束]")
                            in_think = False
                            remaining = remaining[idx + len(THINK_CLOSE):]

            self.progress_signal.emit(95)

            if full_content.strip():
                self.log_signal.emit(f"✅ AI 文案生成完成！共 {len(full_content)} 字符")
                self.ai_done.emit(full_content)
            else:
                self.log_signal.emit("⚠️ AI 未返回有效内容")

            self.progress_signal.emit(100)

        except Exception as e:
            self.error_signal.emit(f"AI 生成失败: {e}")


class VideoAnalysisPanel(QWidget):
    """视频分析页面"""

    def __init__(self, task_store=None, settings: dict | None = None, parent=None):
        super().__init__(parent)
        self.task_store = task_store
        self.settings = settings or {}
        self.extract_worker: ExtractWorker | None = None
        self.gen_worker: GenerateWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # ── 标题 ──
        title = QLabel("📈 视频分析")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f0f6fc;")
        layout.addWidget(title)

        desc = QLabel("粘贴视频链接 → 提取口播文案 → 输入你的产品信息 → AI 生成同风格文案")
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(4)

        # ── 步骤 1: 视频链接 + 提取 ──
        input_group = QGroupBox("📎 步骤 1: 提取视频口播文案")
        input_group.setStyleSheet(self._group_style())
        input_layout = QVBoxLayout(input_group)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴视频链接，例如: https://v.douyin.com/xxxxx/")
        self.url_input.setMinimumHeight(36)
        self.url_input.setStyleSheet(self._input_style())
        self.url_input.returnPressed.connect(self._start_extract)
        url_row.addWidget(self.url_input, 1)

        self.extract_btn = QPushButton("🔍 提取文案")
        self.extract_btn.setObjectName("primaryBtn")
        self.extract_btn.setMinimumHeight(36)
        self.extract_btn.setMinimumWidth(110)
        self.extract_btn.clicked.connect(self._start_extract)
        url_row.addWidget(self.extract_btn)

        self.stop_btn = QPushButton("[ 停止 ]")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setMinimumWidth(80)
        self.stop_btn.clicked.connect(self._stop_all)
        self.stop_btn.setVisible(False)
        url_row.addWidget(self.stop_btn)

        input_layout.addLayout(url_row)

        # 提取进度条
        self.extract_progress = QProgressBar()
        self.extract_progress.setRange(0, 100)
        self.extract_progress.setValue(0)
        self.extract_progress.setVisible(False)
        self.extract_progress.setFixedHeight(4)
        self.extract_progress.setStyleSheet("QProgressBar { background:#21262d; border:none; border-radius:2px; } QProgressBar::chunk { background:#58a6ff; border-radius:2px; }")
        input_layout.addWidget(self.extract_progress)

        layout.addWidget(input_group)

        # ── 内容区域 ──
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上方: 原文案
        copy_group = QGroupBox("📝 提取的原文案")
        copy_group.setStyleSheet(self._group_style())
        copy_layout = QVBoxLayout(copy_group)
        self.copy_edit = QTextEdit()
        self.copy_edit.setReadOnly(True)
        self.copy_edit.setPlaceholderText("视频口播文案提取后将显示在这里...")
        self.copy_edit.setStyleSheet(self._textarea_style())
        self.copy_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.copy_edit.customContextMenuRequested.connect(self._on_text_context_menu)
        copy_layout.addWidget(self.copy_edit)
        splitter.addWidget(copy_group)

        # 下方: 产品输入 + AI 结果
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        # 步骤 2: 产品输入
        product_group = QGroupBox("🏷️ 步骤 2: 输入你的产品/服务信息")
        product_group.setStyleSheet(self._group_style())
        product_layout = QVBoxLayout(product_group)

        prod_row = QHBoxLayout()
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("描述你要推广的产品或服务，例如：手工核桃手串、精选文玩配饰...")
        self.product_input.setMinimumHeight(36)
        self.product_input.setStyleSheet(self._input_style())
        self.product_input.returnPressed.connect(self._start_generate)
        prod_row.addWidget(self.product_input, 1)

        self.gen_btn = QPushButton("✨ AI 生成同风格文案")
        self.gen_btn.setObjectName("primaryBtn")
        self.gen_btn.setMinimumHeight(36)
        self.gen_btn.setMinimumWidth(170)
        self.gen_btn.clicked.connect(self._start_generate)
        self.gen_btn.setEnabled(False)
        prod_row.addWidget(self.gen_btn)

        product_layout.addLayout(prod_row)
        bottom_layout.addWidget(product_group)

        # 生成进度条
        self.gen_progress = QProgressBar()
        self.gen_progress.setRange(0, 100)
        self.gen_progress.setValue(0)
        self.gen_progress.setVisible(False)
        self.gen_progress.setFixedHeight(4)
        self.gen_progress.setStyleSheet("QProgressBar { background:#21262d; border:none; border-radius:2px; } QProgressBar::chunk { background:#3fb950; border-radius:2px; }")
        bottom_layout.addWidget(self.gen_progress)

        # 步骤 3: 生成结果
        result_group = QGroupBox("📋 步骤 3: AI 仿写文案（流式输出）")
        result_group.setStyleSheet(self._group_style())
        result_layout = QVBoxLayout(result_group)
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 根据原文案风格为你生成的营销文案将在这里实时流式输出...")
        self.result_edit.setStyleSheet(self._textarea_style())
        self.result_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_edit.customContextMenuRequested.connect(self._on_text_context_menu)
        result_layout.addWidget(self.result_edit)
        bottom_layout.addWidget(result_group, 1)

        splitter.addWidget(bottom)
        splitter.setSizes([180, 420])
        layout.addWidget(splitter, 1)

        # 底部状态
        self.status_label = QLabel("● 就绪 — 请粘贴视频链接")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.status_label)

    # ── 样式 ────────────────────────────────────

    def _group_style(self):
        return """
            QGroupBox {
                color: #c9d1d9; font-weight: bold; border: 1px solid #30363d;
                border-radius: 8px; margin-top: 8px; padding: 14px 10px 10px 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """

    def _input_style(self):
        return """
            QLineEdit {
                background: #0d1117; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 8px 12px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #58a6ff; }
        """

    def _textarea_style(self):
        return """
            QTextEdit {
                background: #0d1117; color: #c9d1d9;
                border: none; font-size: 13px; padding: 8px;
            }
        """

    # ── 右键菜单 ────────────────────────────────

    def _on_text_context_menu(self, pos):
        sender = self.sender()
        menu = sender.createStandardContextMenu()
        label_map = {
            "&Undo": "撤销(&U)", "&Redo": "重做(&R)",
            "Cu&t": "剪切(&T)", "&Copy": "复制(&C)",
            "&Paste": "粘贴(&P)", "Delete": "删除(&D)",
            "Select All": "全选(&A)",
        }
        for action in menu.actions():
            for eng, chn in label_map.items():
                if eng in action.text() or action.text().startswith(eng.replace("&", "")):
                    action.setText(chn)
                    break
        menu.exec(sender.mapToGlobal(pos))

    # ── 阶段 1: 提取文案 ────────────────────────

    def _load_copy_rewrite_prompt(self) -> str:
        """加载系统预置提示词 models/copy_rewrite.md"""
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models", "copy_rewrite.md"))
        else:
            # 开发模式：从 app/widgets/ 向上两级到项目根
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidates.append(os.path.join(project_root, "models", "copy_rewrite.md"))
        candidates.append(os.path.join(os.getcwd(), "models", "copy_rewrite.md"))

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        prompt = f.read()
                    print(f"[视频分析] 系统提示词已加载: {path} ({len(prompt)} 字符)")
                    return prompt
                except Exception as e:
                    print(f"[视频分析] 加载系统提示词失败 ({path}): {e}")

        print("[视频分析] 未找到 copy_rewrite.md，将使用内置兜底提示词")
        return ""

    def _start_extract(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请先输入视频链接。")
            return

        self.copy_edit.clear()
        self.result_edit.clear()
        self.gen_btn.setEnabled(False)
        self.extract_progress.setVisible(True)
        self.extract_progress.setValue(0)
        self.extract_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.status_label.setText("● 正在提取视频文案...")
        self.status_label.setStyleSheet("color: #d2991d; font-size: 12px;")

        self.extract_worker = ExtractWorker(url, self.settings)
        self.extract_worker.log_signal.connect(self._on_status)
        self.extract_worker.copy_extracted.connect(self._on_copy_extracted)
        self.extract_worker.progress_signal.connect(self.extract_progress.setValue)
        self.extract_worker.error_signal.connect(self._on_extract_error)
        self.extract_worker.finished.connect(self._on_extract_finished)
        self.extract_worker.start()

    def _on_copy_extracted(self, text: str):
        self.copy_edit.setPlainText(text)
        self.gen_btn.setEnabled(True)
        self.status_label.setText(f"✅ 文案提取完成！共 {len(text)} 字符 — 请输入产品信息后点击「AI 生成」")
        self.status_label.setStyleSheet("color: #2ed573; font-size: 12px;")

    def _on_extract_error(self, msg: str):
        self.status_label.setText(f"❌ {msg}")
        self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        QMessageBox.critical(self, "提取失败", msg)

    def _on_extract_finished(self):
        self.extract_btn.setVisible(True)
        self.stop_btn.setVisible(False)

    # ── 阶段 2: AI 生成 ─────────────────────────

    def _start_generate(self):
        product = self.product_input.text().strip()
        if not product:
            QMessageBox.warning(self, "提示", "请先输入你的产品/服务信息。")
            return

        original_copy = self.copy_edit.toPlainText().strip()
        if not original_copy:
            QMessageBox.warning(self, "提示", "请先提取视频文案。")
            return

        self.result_edit.clear()
        self.gen_progress.setVisible(True)
        self.gen_progress.setValue(0)
        self.gen_btn.setEnabled(False)
        self.extract_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.status_label.setText("● 正在 AI 生成仿写文案...")
        self.status_label.setStyleSheet("color: #d2991d; font-size: 12px;")

        system_prompt = self._load_copy_rewrite_prompt()
        self.gen_worker = GenerateWorker(original_copy, product, self.settings, system_prompt)
        self.gen_worker.log_signal.connect(self._on_status)
        self.gen_worker.ai_chunk.connect(self._on_ai_chunk)
        self.gen_worker.ai_done.connect(self._on_ai_done)
        self.gen_worker.progress_signal.connect(self.gen_progress.setValue)
        self.gen_worker.error_signal.connect(self._on_gen_error)
        self.gen_worker.finished.connect(self._on_gen_finished)
        self.gen_worker.start()

    def _on_ai_chunk(self, chunk: str):
        cursor = self.result_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.result_edit.setTextCursor(cursor)
        self.result_edit.ensureCursorVisible()

    def _on_ai_done(self, full_text: str):
        self.status_label.setText(f"✅ AI 文案生成完成！共 {len(full_text)} 字符")
        self.status_label.setStyleSheet("color: #2ed573; font-size: 12px;")

    def _on_gen_error(self, msg: str):
        self.status_label.setText(f"❌ {msg}")
        self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        QMessageBox.critical(self, "生成失败", msg)

    def _on_gen_finished(self):
        self.extract_btn.setVisible(True)
        self.gen_btn.setEnabled(True)
        self.stop_btn.setVisible(False)

    # ── 通用 ────────────────────────────────────

    def _on_status(self, msg: str):
        self.status_label.setText(msg)
        if msg.startswith("💭"):
            self.status_label.setStyleSheet("color: #6e7681; font-size: 12px;")
        elif msg.startswith("❌"):
            self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        elif msg.startswith("✅"):
            self.status_label.setStyleSheet("color: #2ed573; font-size: 12px;")
        elif msg.startswith("⚠"):
            self.status_label.setStyleSheet("color: #d2991d; font-size: 12px;")
        else:
            self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")

    def _stop_all(self):
        for w in (self.extract_worker, self.gen_worker):
            if w and w.isRunning():
                w.stop()
                w.terminate()
                w.wait(2000)
        self._on_status("⏹ 已停止")
        self.extract_btn.setVisible(True)
        self.gen_btn.setEnabled(bool(self.copy_edit.toPlainText().strip()))
        self.stop_btn.setVisible(False)
