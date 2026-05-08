"""剧本生成面板 — 任务选择 + AI流式生成"""

import os
import json
import sys
import importlib.util

import mistune
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QProgressBar,
    QComboBox, QMessageBox, QInputDialog, QCheckBox, QMenu,
    QScrollArea,
)
from app.widgets.common_widgets import CTextEdit



class ScriptWorker(QThread):
    """AI 生成线程 — 流式输出，<think> 标签内容去控制台"""
    result_signal = pyqtSignal(str)      # 最终完整结果
    chunk_signal = pyqtSignal(str)       # 流式输出到界面
    progress_signal = pyqtSignal(int, str)  # (百分比, 步骤描述)
    error_signal = pyqtSignal(str)

    def __init__(self, api_key: str, api_base: str, model: str, prompt: str, system_prompt: str = "",
                 video_ids: list | None = None, extract_func=None):
        super().__init__()
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.video_ids = video_ids or []
        self.extract_func = extract_func  # callable(video_id) -> str

    def run(self):
        try:
            # ── 视频文案提取（在后台线程中执行）──
            if self.video_ids and self.extract_func:
                transcripts = []
                total = len(self.video_ids)
                for i, vid in enumerate(self.video_ids):
                    self.progress_signal.emit(20 + int((i / total) * 10), f"解析视频 {i+1}/{total}...")
                    try:
                        text = self.extract_func(vid)
                        transcripts.append(text)
                    except Exception as e:
                        print(f"[剧本] 视频 {i+1}/{total} 解析失败: {e}")
                if transcripts:
                    self.prompt = f"{self.prompt}\n\n--- 视频文案 ---\n\n" + "\n\n---\n\n".join(
                        f"## 视频 {j+1}\n\n{t}" for j, t in enumerate(transcripts)
                    )

            from openai import OpenAI
            print(f"[剧本] API 地址: {self.api_base}")
            print(f"[剧本] 模型: {self.model}")
            # 确保 base_url 不含尾部斜杠，OpenAI 客户端会自动追加路径
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt_preview = self.prompt[:200].replace("\n", "\\n")
            print(f"[剧本] 系统提示词({len(self.system_prompt)} 字符)")
            print(f"[剧本] 用户提示词({len(self.prompt)} 字符): {prompt_preview}...")
            print(f"[剧本] 正在流式调用 API...")
            self.progress_signal.emit(30, "正在调用 AI 模型...")

            # 构建 messages：系统提示词 + 用户提示词
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": self.prompt})

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=4096,
                stream=True,
            )

            self.progress_signal.emit(50, "AI 正在生成...")
            full_content = ""
            full_reasoning = ""
            prompt_tokens = 0
            completion_tokens = 0
            buf = ""
            first_chunk = True

            THINK_OPEN = "<think>"
            THINK_CLOSE = "</think>"
            in_think = False

            for chunk in stream:
                if first_chunk:
                    self.progress_signal.emit(70, "正在接收内容...")
                    first_chunk = False
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                text = delta.content or ""
                if not text:
                    if chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens
                        completion_tokens = chunk.usage.completion_tokens
                    continue

                buf += text

                # 解析 <think> 标签
                while buf:
                    if not in_think:
                        idx = buf.find(THINK_OPEN)
                        if idx == -1:
                            # 检查是否有不完整的 <think 开头
                            partial = _partial_tag(buf, THINK_OPEN)
                            if partial:
                                # 保留可能被截断的部分等下个 chunk
                                keep = buf[-partial:]
                                emit = buf[:-partial]
                                if emit:
                                    full_content += emit
                                    self.chunk_signal.emit(emit)
                                buf = keep
                                break
                            else:
                                full_content += buf
                                self.chunk_signal.emit(buf)
                                buf = ""
                                break
                        else:
                            # 找到 <think> — 之前的正文送界面
                            before = buf[:idx]
                            if before:
                                full_content += before
                                self.chunk_signal.emit(before)
                            buf = buf[idx + len(THINK_OPEN):]
                            in_think = True
                    else:
                        idx = buf.find(THINK_CLOSE)
                        if idx == -1:
                            # 检查是否有不完整的 </think 开头
                            partial = _partial_tag(buf, THINK_CLOSE)
                            if partial:
                                keep = buf[-partial:]
                                emit_think = buf[:-partial]
                                full_reasoning += emit_think
                                print(emit_think, end="", flush=True)
                                buf = keep
                                break
                            else:
                                full_reasoning += buf
                                print(buf, end="", flush=True)
                                buf = ""
                                break
                        else:
                            before = buf[:idx]
                            full_reasoning += before
                            print(before, end="", flush=True)
                            buf = buf[idx + len(THINK_CLOSE):]
                            in_think = False

            # 处理残留
            if buf:
                if in_think:
                    full_reasoning += buf
                    print(buf, end="", flush=True)
                else:
                    full_content += buf
                    self.chunk_signal.emit(buf)

            if full_reasoning:
                print()  # 换行

            print(f"\n[剧本] ✅ 流式调用完成")
            print(f"[剧本] token 用量: prompt={prompt_tokens} completion={completion_tokens}")
            print(f"[剧本] 思考内容({len(full_reasoning)} 字符)")
            print(f"[剧本] 生成内容({len(full_content)} 字符): {full_content[:200]}...")
            self.progress_signal.emit(100, "✅ 生成完成")
            self.result_signal.emit(full_content)

        except Exception as e:
            print(f"[剧本] ❌ 失败: {e}")
            print(f"[剧本] 请求信息: base_url={self.api_base}, model={self.model}")
            self.error_signal.emit(str(e))


def _partial_tag(buf: str, tag: str) -> int:
    """检查 buf 末尾是否有 tag 的不完整前缀，返回匹配长度"""
    for n in range(len(tag) - 1, 0, -1):
        if buf.endswith(tag[:n]):
            return n
    return 0


class ScriptPanel(QWidget):
    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._worker: ScriptWorker | None = None
        self._init_ui()
        self._refresh_tasks()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(4)

        # ── 标题 ──
        title = QLabel("🎬 剧本生成")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ═════ 任务选择 ═════
        section2 = QLabel("【引用采集数据】")
        section2.setObjectName("sectionLabel")
        layout.addWidget(section2)

        task_row = QHBoxLayout()
        task_row.setSpacing(8)
        task_row.addWidget(QLabel("选择任务:"))

        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(300)
        self.task_combo.setPlaceholderText("选择历史采集任务……")
        task_row.addWidget(self.task_combo)
        task_row.addStretch()
        layout.addLayout(task_row)

        # ═════ 视频解析 ═════
        section_video = QLabel("【视频文案解析】")
        section_video.setObjectName("sectionLabel")
        layout.addWidget(section_video)

        video_toggle_row = QHBoxLayout()
        self.video_toggle = QCheckBox("自动解析采集任务中的视频文案（通过视频ID提取文本，注入提示词）")
        video_toggle_row.addWidget(self.video_toggle)
        video_toggle_row.addStretch()
        layout.addLayout(video_toggle_row)

        self.video_status = QLabel("")
        self.video_status.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.video_status.setFixedHeight(18)
        layout.addWidget(self.video_status)

        # ═════ 提示词 ═════
        section3 = QLabel("【生成提示词】")
        section3.setObjectName("sectionLabel")
        layout.addWidget(section3)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setObjectName("promptEdit")
        self.prompt_edit.setPlaceholderText(
            "输入生成提示词...\n"
            "例如：根据以下视频数据，生成一篇带货推广剧本，包含开场、产品介绍、促单话术。"
        )
        self.prompt_edit.setMaximumHeight(70)
        self.prompt_edit.setStyleSheet("""
            QTextEdit#promptEdit {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                selection-background-color: rgba(255,107,129,0.3);
            }
            QTextEdit#promptEdit:focus {
                border: 1px solid #ff6b81;
                background: #161b22;
            }
        """)
        # setPlaceholderText 在 Qt 中通过 palette 控制，需要单独设
        self.prompt_edit.viewport().setStyleSheet("background: #0d1117;")
        self._setup_chinese_context_menu(self.prompt_edit)
        layout.addWidget(self.prompt_edit)

        # ═════ 生成按钮 ═════
        gen_row = QHBoxLayout()
        gen_row.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        gen_row.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.progress_label.setVisible(False)
        gen_row.addWidget(self.progress_label)

        gen_row.addStretch()

        self.gen_btn = QPushButton("✨ AI 生成剧本")
        self.gen_btn.setObjectName("primaryBtn")
        self.gen_btn.clicked.connect(self._generate)
        gen_row.addWidget(self.gen_btn)

        layout.addLayout(gen_row)

        # ═════ 生成结果 ═════
        section4 = QLabel("【生成结果】")
        section4.setObjectName("sectionLabel")
        layout.addWidget(section4)

        self.result_scroll = QScrollArea()
        self.result_scroll.setObjectName("resultScroll")
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setMinimumHeight(350)
        self.result_scroll.setStyleSheet("""
            QScrollArea#resultScroll {
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QScrollArea#resultScroll > QWidget {
                background: #0d1117;
            }
        """)

        self.result_label = QLabel()
        self.result_label.setObjectName("resultLabel")
        self.result_label.setText("AI 生成的剧本将显示在这里……")
        self.result_label.setStyleSheet("""
            QLabel#resultLabel {
                background: #0d1117;
                color: #c9d1d9;
                padding: 12px;
                font-size: 13px;
                selection-background-color: rgba(255,107,129,0.3);
            }
        """)
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.result_scroll.setWidget(self.result_label)
        layout.addWidget(self.result_scroll)

        result_btns = QHBoxLayout()
        result_btns.addStretch()
        self.save_btn = QPushButton("[ 保存结果 ]")
        self.save_btn.setObjectName("smallBtn")
        self.save_btn.clicked.connect(self._save_script)
        self.save_btn.setEnabled(False)
        result_btns.addWidget(self.save_btn)

        self.modify_btn = QPushButton("✏ 修改剧本")
        self.modify_btn.setObjectName("smallBtn")
        self.modify_btn.clicked.connect(self._modify_script)
        self.modify_btn.setEnabled(False)
        result_btns.addWidget(self.modify_btn)
        layout.addLayout(result_btns)

    # ── 生成 ──

    def _extract_video_transcript(self, video_id: str) -> str:
        """通过 video_downloader 提取单个视频文案"""
        share_link = f"https://www.iesdouyin.com/share/video/{video_id}/"
        return self._extract_transcript_from_link(share_link)

    def _extract_transcript_from_link(self, share_link: str) -> str:
        """通过 video_downloader 提取视频文案，返回文本"""
        # 惰性导入，避免 check_dependencies() 在 import 时 sys.exit
        spec = importlib.util.spec_from_file_location(
            "video_downloader",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core_modules", "video_downloader.py")
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 video_downloader.py")

        # 绕过 check_dependencies：mock sys.exit
        _orig_exit = sys.exit
        sys.exit = lambda code=0: (_ for _ in ()).throw(RuntimeError(f"依赖模块缺失 (退出码 {code})，请安装: pip install requests ffmpeg-python"))
        try:
            dld = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dld)
        finally:
            sys.exit = _orig_exit

        api_key = (self._settings.get("video_api_key") or
                   self._settings.get("openai_text_api_key") or
                   self._settings.get("openai_api_key") or
                   os.environ.get("API_KEY", ""))
        if not api_key:
            raise RuntimeError("视频解析需要 API 密钥，请在设置中配置「视频提取密钥」或文字大模型 API Key")

        result = dld.extract_text(share_link, api_key=api_key, show_progress=True)
        return result.get("text", "")

    def _load_system_prompt(self) -> str:
        """加载系统预置提示词 models/script.md"""
        # 查找脚本文件路径
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models", "script.md"))
        else:
            # 开发模式：从 app/widgets/ 向上两级到项目根
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidates.append(os.path.join(project_root, "models", "script.md"))
        # 兜底：当前工作目录
        candidates.append(os.path.join(os.getcwd(), "models", "script.md"))

        system_prompt = ""
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        base = f.read()
                    # 追加冲突规则
                    base += (
                        "\n\n---\n\n"
                        "## 重要规则：用户提示词优先\n\n"
                        "如果用户的提示词与上述系统预置规则存在冲突，"
                        "必须以用户提示词为准，忽略冲突的系统规则。"
                    )
                    system_prompt = base
                    print(f"[剧本] 系统提示词已加载: {path} ({len(base)} 字符)")
                    break
                except Exception as e:
                    print(f"[剧本] 加载系统提示词失败 ({path}): {e}")

        return system_prompt

    def _format_task_data(self, task_result: dict) -> str:
        """格式化采集任务数据为摘要文本"""
        data = task_result
        lines = [f"搜索词: {data.get('search_term','')}"]
        for v in data.get("videos", [])[:5]:
            lines.append(
                f"\n视频{v.get('index','?')}: {v.get('title','')}\n"
                f"  点赞:{v.get('likes','0')} 评论:{v.get('comments_count','0')} "
                f"收藏:{v.get('collects','0')} 分享:{v.get('shares','0')}"
            )
            for u in (v.get("matched_users") or [])[:3]:
                lines.append(f"  用户@{u.get('username','')}: {u.get('comment_content','')}")
        return "\n".join(lines)

    def _generate(self):
        if self._worker and self._worker.isRunning():
            return

        # 获取任务数据（一次性加载）
        task_result = None
        task_id = self.task_combo.currentData()
        if task_id and self._task_store:
            task_result = self._task_store.load_result(task_id)

        # 构建提示词
        task_data_str = ""
        if task_result:
            task_data_str = self._format_task_data(task_result)
        user_prompt = self.prompt_edit.toPlainText().strip()
        if not user_prompt and not task_data_str and not self.video_toggle.isChecked():
            QMessageBox.warning(self, "提示", "请输入提示词或选择采集任务。")
            return

        full_prompt = user_prompt
        if task_data_str:
            full_prompt = f"{user_prompt}\n\n--- 采集数据 ---\n{task_data_str}"

        # 视频文案解析 — 只验证，实际提取在 ScriptWorker 后台线程中执行
        video_ids = []
        if self.video_toggle.isChecked():
            if not task_result:
                QMessageBox.warning(self, "提示", "请先选择一个采集任务。")
                return
            videos = task_result.get("videos", [])
            if not videos:
                QMessageBox.warning(self, "提示", "采集任务中没有视频数据。")
                return
            for v in videos:
                vid = v.get("video_id", "")
                if vid:
                    video_ids.append(vid)
            if not video_ids:
                QMessageBox.warning(self, "提示", "采集任务中的视频没有有效的视频ID。")
                return

        # API 配置（优先使用设置，回退到环境变量及旧key）
        api_key = self._settings.get("openai_text_api_key") or self._settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
        api_base = self._settings.get("openai_text_api_base") or self._settings.get("openai_api_base") or os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1")
        model = self._settings.get("openai_text_model") or self._settings.get("openai_model") or os.environ.get("OPENAI_MODEL", "deepseek-chat")

        print(f"[剧本] === 开始生成 ===")
        print(f"[剧本] API 地址: {api_base}")
        print(f"[剧本] 模型: {model}")
        print(f"[剧本] 用户提示词({len(full_prompt)} 字符): {full_prompt[:150]}...")

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(5)
        self.progress_label.setVisible(True)
        self.progress_label.setText("加载系统提示词...")

        # 加载系统预置提示词
        system_prompt = self._load_system_prompt()
        self.progress_bar.setValue(15)
        self.progress_label.setText("准备就绪")

        if not api_key:
            self._hide_progress()
            QMessageBox.warning(self, "提示",
                "请先在设置页面配置 OpenAI API Key。\n"
                "（或设置环境变量 OPENAI_API_KEY）")
            return

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("生成中……")
        if hasattr(self, "_result_buf"):
            self._result_buf = ""
        self.result_label.setText("AI 正在生成剧本，请稍候……")

        self._worker = ScriptWorker(
            api_key, api_base, model, full_prompt, system_prompt,
            video_ids=video_ids,
            extract_func=self._extract_video_transcript if video_ids else None,
        )
        self._worker.chunk_signal.connect(self._on_chunk)
        self._worker.progress_signal.connect(self._on_progress)
        self._worker.result_signal.connect(self._on_result)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_chunk(self, text: str):
        """流式追加到界面"""
        if not hasattr(self, "_result_buf"):
            self._result_buf = ""
        self._result_buf += text
        html = self._render_markdown(self._result_buf)
        self.result_label.setText(html)
        self.result_scroll.verticalScrollBar().setValue(self.result_scroll.verticalScrollBar().maximum())

    def _render_markdown(self, text: str) -> str:
        """将 markdown 渲染为带样式的 HTML"""
        html = mistune.html(text)
        css = """
        <style>
        body { color: #c9d1d9; font-size: 13px; line-height: 1.6; margin: 0; padding: 12px; }
        h1, h2, h3, h4 { color: #e6edf3; font-weight: bold; margin: 12px 0 8px 0; }
        h1 { font-size: 18px; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
        h2 { font-size: 16px; }
        h3 { font-size: 14px; }
        p { margin: 8px 0; }
        code { background: #161b22; color: #ff7b72; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; }
        pre { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; overflow-x: auto; }
        pre code { background: none; padding: 0; color: #c9d1d9; }
        blockquote { border-left: 3px solid #ff6b81; margin: 8px 0; padding: 4px 12px; color: #8b949e; }
        ul, ol { margin: 8px 0; padding-left: 24px; }
        li { margin: 4px 0; }
        strong { color: #e6edf3; font-weight: bold; }
        em { color: #c9d1d9; font-style: italic; }
        a { color: #58a6ff; text-decoration: none; }
        table { border-collapse: collapse; width: 100%; margin: 8px 0; }
        th, td { border: 1px solid #30363d; padding: 6px 12px; text-align: left; }
        th { background: #161b22; color: #e6edf3; }
        tr:nth-child(even) { background: #161b22; }
        hr { border: none; border-top: 1px solid #30363d; margin: 12px 0; }
        </style>
        """
        return f"<!DOCTYPE html><html><head>{css}</head><body>{html}</body></html>"

    def _on_progress(self, value: int, message: str):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def _hide_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    def _on_result(self, text: str):
        print(f"[剧本] === 生成完成 === ({len(text)} 字符)")
        self._last_result = text
        self._last_prompt = self.prompt_edit.toPlainText().strip()
        self._hide_progress()

        # 自动触发 SEO 优化（不立即展示原剧本）
        topic = self.prompt_edit.toPlainText().strip()[:50]
        self._run_seo_optimize(text, topic)

    def _run_seo_optimize(self, script_text: str, topic: str):
        """触发 SEO 优化流程"""
        api_key = self._settings.get("openai_text_api_key") or self._settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
        api_base = self._settings.get("openai_text_api_base") or self._settings.get("openai_api_base") or os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1")
        model = self._settings.get("openai_text_model") or self._settings.get("openai_model") or os.environ.get("OPENAI_MODEL", "deepseek-chat")

        if not api_key:
            # 无 API key，直接显示原剧本
            self._show_final_result(script_text)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在优化 SEO...")
        self.result_label.setText("AI 正在优化标题和标签，请稍候...")
        self.gen_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.modify_btn.setEnabled(False)

        self._worker = SEOOptimizeWorker(
            script_text=script_text,
            api_key=api_key,
            api_base=api_base,
            model=model,
        )
        self._worker.chunk_signal.connect(self._on_seo_chunk)
        self._worker.result_signal.connect(self._on_seo_result)
        self._worker.error_signal.connect(self._on_seo_error)
        self._worker.start()

    def _on_seo_chunk(self, text: str):
        """SEO 优化流式追加"""
        if not hasattr(self, "_seo_result_buf"):
            self._seo_result_buf = ""
        self._seo_result_buf += text
        html = self._render_markdown(self._seo_result_buf)
        self.result_label.setText(html)
        self.result_scroll.verticalScrollBar().setValue(
            self.result_scroll.verticalScrollBar().maximum()
        )

    def _on_seo_result(self, text: str):
        """SEO 优化完成"""
        # Clear streaming buffer after completion
        if hasattr(self, "_seo_result_buf"):
            del self._seo_result_buf
        print(f"[剧本] === SEO 优化完成 === ({len(text)} 字符)")
        self._last_result = text
        self._hide_progress()
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)
        self.gen_btn.setText("✨ AI 生成剧本")
        # 直接显示优化后结果
        self._show_final_result(text)

    def _on_seo_error(self, msg: str):
        """SEO 优化失败，回退到原剧本"""
        print(f"[剧本] === SEO 优化失败 === {msg}")
        self._hide_progress()
        self.result_label.setText(
            f"<p style='color:#f85149'>⚠️ SEO 优化失败，显示原始剧本：</p>"
            f"<pre style='color:#c9d1d9'>{self._last_result[:500]}</pre>"
        )
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)

    def _show_final_result(self, text: str):
        """展示最终结果（渲染 markdown）"""
        html = self._render_markdown(text)
        self.result_label.setText(html)
        self.result_scroll.verticalScrollBar().setValue(0)

    def _on_modify_result(self, text: str):
        print(f"[剧本] === 修改完成 === ({len(text)} 字符)")
        self._last_result = text
        self._hide_progress()
        self.save_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("✨ AI 生成剧本")
        QMessageBox.information(self, "修改成功", "剧本已根据您的意见修改完成。")

    def _on_error(self, msg: str):
        print(f"[剧本] === 生成失败 === {msg}")
        self._hide_progress()
        self.result_label.setText(f"<p style='color:#f85149'>❌ 生成失败: {msg}</p>")
        self.gen_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)
        self.gen_btn.setText("✨ AI 生成剧本")

    def _save_script(self):
        """保存生成的剧本到持久化存储"""
        if not hasattr(self, "_last_result") or not self._last_result:
            QMessageBox.warning(self, "提示", "没有可保存的剧本内容。")
            return
        if not self._task_store:
            QMessageBox.warning(self, "提示", "存储未初始化，请检查设置。")
            return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("保存剧本")
        dialog.setLabelText("请输入备注信息（方便后续查找）：")
        dialog.setTextValue("")
        dialog.setOkButtonText("确定")
        dialog.setCancelButtonText("取消")
        if dialog.exec() != QInputDialog.DialogCode.Accepted:
            return
        notes = dialog.textValue()

        try:
            path = self._task_store.save_script(
                script_text=self._last_result,
                prompt=self._last_prompt or "",
                notes=notes.strip(),
                model=self._settings.get("openai_text_model") or self._settings.get("openai_model", ""),
            )
            print(f"[剧本] 💾 已保存: {path}")
            QMessageBox.information(
                self, "保存成功",
                f"剧本已保存到：\n{path}\n\n备注：{notes.strip() or '(无)'}"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _modify_script(self):
        """弹出输入框收集修改意见，调用 AI 修改剧本"""
        if not hasattr(self, "_last_result") or not self._last_result:
            QMessageBox.warning(self, "提示", "没有可修改的剧本，请先生成。")
            return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("修改剧本")
        dialog.setLabelText("请描述您的修改意见：")
        dialog.setTextValue("")
        dialog.setOkButtonText("确定")
        dialog.setCancelButtonText("取消")
        if dialog.exec() != QInputDialog.DialogCode.Accepted:
            return
        user_feedback = dialog.textValue().strip()
        if not user_feedback:
            QMessageBox.warning(self, "提示", "修改意见不能为空。")
            return

        # 构建修改提示词
        modify_prompt = (
            f"以下是原始剧本：\n{self._last_result}\n\n"
            f"用户修改意见：{user_feedback}\n\n"
            f"请根据用户的修改意见，对上述剧本进行修改。只输出修改后的剧本，不要额外的解释。"
        )

        # API 配置
        api_key = self._settings.get("openai_text_api_key") or self._settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
        api_base = self._settings.get("openai_text_api_base") or self._settings.get("openai_api_base") or os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1")
        model = self._settings.get("openai_text_model") or self._settings.get("openai_model") or os.environ.get("OPENAI_MODEL", "deepseek-chat")

        if not api_key:
            QMessageBox.warning(self, "提示", "请先在设置页面配置 OpenAI API Key。")
            return

        print(f"[剧本] === 开始修改 ===")
        print(f"[剧本] API 地址: {api_base}")
        print(f"[剧本] 模型: {model}")

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在修改剧本...")

        self.modify_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        if hasattr(self, "_result_buf"):
            self._result_buf = ""
        self.result_label.setText("AI 正在修改剧本，请稍候……")

        self._worker = ScriptWorker(
            api_key, api_base, model, modify_prompt, "",
            video_ids=None,
            extract_func=None,
        )
        self._worker.chunk_signal.connect(self._on_chunk)
        self._worker.progress_signal.connect(self._on_progress)
        self._worker.result_signal.connect(self._on_modify_result)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    # ── 外部调用 ──

    def set_task_store(self, store):
        self._task_store = store
        self._refresh_tasks()

    def set_settings(self, settings: dict):
        self._settings = settings

    def _setup_chinese_context_menu(self, edit: QTextEdit):
        """为 QTextEdit 设置中文右键菜单"""
        edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        def show_menu(pos):
            menu = QMenu(edit)
            if not edit.isReadOnly():
                menu.addAction("撤销", edit.undo).setEnabled(edit.document().isUndoAvailable())
                menu.addAction("重做", edit.redo).setEnabled(edit.document().isRedoAvailable())
                menu.addSeparator()
                menu.addAction("剪切", edit.cut).setEnabled(edit.textCursor().hasSelection())
            menu.addAction("复制", edit.copy).setEnabled(edit.textCursor().hasSelection())
            if not edit.isReadOnly():
                menu.addAction("粘贴", edit.paste)
                menu.addAction("删除", lambda e=edit: e.textCursor().removeSelectedText()).setEnabled(edit.textCursor().hasSelection())
            menu.addSeparator()
            menu.addAction("全选", edit.selectAll)
            menu.exec(edit.mapToGlobal(pos))
        edit.customContextMenuRequested.connect(show_menu)

    def _refresh_tasks(self):
        if not self._task_store:
            return
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("— 不引用 —", "")
        for t in self._task_store.list_tasks():
            if t.get("status") == "completed":
                label = f"{t['created_at'][:16]} | {t.get('search_term','')[:25]}"
                if t.get("notes"):
                    label += f" — {t['notes'][:12]}"
                self.task_combo.addItem(label, t["task_id"])
        self.task_combo.blockSignals(False)


class SEOOptimizeWorker(QThread):
    """SEO 优化后台线程 — 对已生成的剧本进行标题和标签优化"""

    chunk_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, script_text: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.script_text = script_text
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        try:
            from openai import OpenAI

            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{self.script_text}

任务要求：
1. 优化标题（≤20字，吸睛，包含关键词）
2. 生成 2 个变体标题（信任型、紧迫型）
3. 推荐 5 个标签（以 # 开头，符合抖音平台规范）
4. 生成视频描述（≤100字）
5. 优化剧本正文（保留原有结构，只优化标题和话术表达）

请严格按以下格式输出：

【优化标题】
（标题内容，≤20字）

【标题变体】
变体A（信任型）：xxx
变体B（紧迫型）：xxx

【推荐标签】
#标签1 #标签2 #标签3 #标签4 #标签5

【视频描述】
（描述内容，≤100字）

【优化后剧本】
（将优化后的完整剧本输出，保留原有结构）
"""

            messages = [{"role": "user", "content": prompt}]

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                stream=True,
            )

            full_content = ""
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                text = delta.content or ""
                if text:
                    full_content += text
                    self.chunk_signal.emit(text)

            self.result_signal.emit(full_content)

        except Exception as e:
            self.error_signal.emit(str(e))
