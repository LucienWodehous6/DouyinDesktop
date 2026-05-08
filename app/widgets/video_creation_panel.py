"""视频创作面板 — 剧本拆分 → 分镜生图 → 图生视频"""

import os
import sys
import json
import base64
import threading

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QProgressBar,
    QComboBox, QMessageBox, QInputDialog, QDialog, QMenu,
    QScrollArea, QFrame, QFileDialog, QCheckBox,
    QGroupBox, QGridLayout, QSlider,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import io
from PIL import Image
import tempfile
import urllib.request
import urllib.error

# 从子包导入子面板组件
from app.widgets.creation import SceneWidget


class VideoCreationPanel(QWidget):
    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._scenes: list[dict] = []  # [{title, prompt, voice, image, video}]
        self._scene_widgets: list[SceneWidget] = []
        self._reference_image = ""  # 参考图路径
        self._workers: list = []
        # 内置音频播放器
        self._audio_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._audio_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._current_playing_scene = -1  # 当前播放的分镜索引
        self._audio_player.positionChanged.connect(self._on_global_position_changed)
        self._audio_player.durationChanged.connect(self._on_global_duration_changed)
        self._audio_player.playbackStateChanged.connect(self._on_global_playback_changed)
        self._init_ui()

    @staticmethod
    def _format_duration(ms: int) -> str:
        total_sec = max(0, ms // 1000)
        m = total_sec // 60
        s = total_sec % 60
        return f"{m:02d}:{s:02d}"

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(6)

        title = QLabel("🎥 视频创作")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ═════ 剧本选择 ═════
        script_row = QHBoxLayout()
        script_row.addWidget(QLabel("选择剧本:"))
        self.script_combo = QComboBox()
        self.script_combo.setMinimumWidth(350)
        self.script_combo.setPlaceholderText("选择已保存的剧本……")
        script_row.addWidget(self.script_combo)
        script_row.addStretch()

        self.split_btn = QPushButton("🔀 AI 拆分分镜")
        self.split_btn.setObjectName("primaryBtn")
        self.split_btn.clicked.connect(self._split_storyboard)
        script_row.addWidget(self.split_btn)
        layout.addLayout(script_row)

        # ═════ 参考图 ═════
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("商品参考图:"))
        self.ref_path_label = QLabel("(未选择)")
        self.ref_path_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        ref_row.addWidget(self.ref_path_label)
        self.ref_upload_btn = QPushButton("📷 上传")
        self.ref_upload_btn.setObjectName("smallBtn")
        self.ref_upload_btn.clicked.connect(self._upload_reference)
        ref_row.addWidget(self.ref_upload_btn)
        ref_row.addStretch()
        layout.addLayout(ref_row)

        # ═════ 视频方向 ═════
        orient_row = QHBoxLayout()
        orient_row.addWidget(QLabel("视频方向:"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["竖版 9:16", "横版 16:9"])
        orient_row.addWidget(self.orientation_combo)
        orient_row.addStretch()
        layout.addLayout(orient_row)

        # ═════ 进度 + 全部生成 ═════
        action_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        action_row.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.progress_label.setVisible(False)
        action_row.addWidget(self.progress_label)
        action_row.addStretch()

        self.gen_all_btn = QPushButton("🖼️ 生成全部分镜图片")
        self.gen_all_btn.setObjectName("primaryBtn")
        self.gen_all_btn.clicked.connect(self._generate_all_images)
        self.gen_all_btn.setEnabled(False)
        action_row.addWidget(self.gen_all_btn)

        self.gen_all_voice_btn = QPushButton("🔊 生成全部音频")
        self.gen_all_voice_btn.setObjectName("primaryBtn")
        self.gen_all_voice_btn.clicked.connect(self._generate_all_voices)
        self.gen_all_voice_btn.setEnabled(False)
        action_row.addWidget(self.gen_all_voice_btn)

        self.add_scene_btn = QPushButton("➕ 手动添加分镜")
        self.add_scene_btn.setObjectName("primaryBtn")
        self.add_scene_btn.clicked.connect(self._add_scene)
        action_row.addWidget(self.add_scene_btn)

        self.create_video_btn = QPushButton("[ 创作视频 ]")
        self.create_video_btn.setObjectName("primaryBtn")
        self.create_video_btn.clicked.connect(self._create_video)
        self.create_video_btn.setEnabled(False)
        action_row.addWidget(self.create_video_btn)
        layout.addLayout(action_row)

        # ═════ 分镜列表（可滚动） ═════
        self.scene_scroll = QScrollArea()
        self.scene_scroll.setWidgetResizable(True)
        self.scene_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scene_container = QWidget()
        self.scene_layout = QVBoxLayout(self.scene_container)
        self.scene_layout.setSpacing(10)
        self.scene_layout.addStretch()
        self.scene_scroll.setWidget(self.scene_container)
        layout.addWidget(self.scene_scroll, 1)

    def _load_scripts(self):
        """加载已保存的剧本列表"""
        self.script_combo.blockSignals(True)
        self.script_combo.clear()
        self.script_combo.addItem("— 选择剧本 —", "")
        if self._task_store:
            for t in self._task_store.list_tasks():
                if t.get("status") == "script":
                    label = f"{t['created_at'][:16]} | {t.get('search_term','')[:30]}"
                    if t.get("notes"):
                        label += f" — {t['notes'][:12]}"
                    self.script_combo.addItem(label, t["task_id"])
        self.script_combo.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_scripts()

    def _upload_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择商品参考图", "",
                                               "Images (*.jpg *.jpeg *.png *.webp)")
        if path:
            self._reference_image = path
            self.ref_path_label.setText(os.path.basename(path))
            self.ref_path_label.setStyleSheet("color: #2ed573; font-size: 12px;")

    def _get_script_content(self) -> str | None:
        task_id = self.script_combo.currentData()
        if not task_id or not self._task_store:
            QMessageBox.warning(self, "提示", "请先选择剧本。")
            return None
        data = self._task_store.load_result(task_id)
        if not data:
            QMessageBox.warning(self, "提示", "无法加载剧本数据。")
            return None
        return data.get("content", "")

    def _load_storyboard_prompt(self) -> str:
        """加载系统预置分镜提示词 models/storyboard_split.md"""
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models", "storyboard_split.md"))
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidates.append(os.path.join(project_root, "models", "storyboard_split.md"))
        candidates.append(os.path.join(os.getcwd(), "models", "storyboard_split.md"))

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    content += (
                        "\n\n---\n\n"
                        "## 重要规则：用户提示词优先\n\n"
                        "如果用户的提示词与上述系统预置规则存在冲突，"
                        "必须以用户提示词为准，忽略冲突的系统规则。"
                    )
                    print(f"[视频创作] 分镜系统提示词已加载: {path} ({len(content)} 字符)")
                    return content
                except Exception as e:
                    print(f"[视频创作] 加载分镜提示词失败 ({path}): {e}")
        return ""

    # ═══════════════ 剧本拆分 ═══════════════

    def _split_storyboard(self):
        content = self._get_script_content()
        if not content:
            return

        system_prompt = self._load_storyboard_prompt()

        self.split_btn.setEnabled(False)
        self.split_btn.setText("拆分中……")

        class SplitWorker(QThread):
            result_signal = pyqtSignal(str)
            error_signal = pyqtSignal(str)

            def __init__(self, settings, script_content, ref_image, sys_prompt):
                super().__init__()
                self.settings = settings
                self.script = script_content
                self.ref_image = ref_image
                self.sys_prompt = sys_prompt

            def run(self):
                try:
                    from openai import OpenAI
                    api_key = self.settings.get("openai_text_api_key") or self.settings.get("openai_api_key", "")
                    api_base = self.settings.get("openai_text_api_base") or self.settings.get("openai_api_base", "https://api.deepseek.com/v1")
                    model = self.settings.get("openai_text_model") or self.settings.get("openai_model", "deepseek-chat")
                    base_url = api_base.rstrip("/")

                    client = OpenAI(api_key=api_key, base_url=base_url)

                    prompt = (
                        f"请将以下剧本拆分为5-8个分镜。每个分镜包含：\n"
                        f"1. 分镜标题（≤10字）\n"
                        f"2. 口播文案（该分镜对应的口播内容，用于配音，简洁有力，适合宣传口播风格，每段15-60字）\n"
                        f"3. 生图提示词（详细描述画面内容、构图、光线、风格，适合AI生图）\n\n"
                        f"输出格式（严格JSON）：\n"
                        f'[{{"title":"分镜标题","voice":"口播文案内容","prompt":"生图提示词"}}, ...]\n'
                        f"\n剧本内容：\n{self.script}"
                    )

                    messages = []
                    if self.sys_prompt:
                        messages.append({"role": "system", "content": self.sys_prompt})
                    messages.append({"role": "user", "content": prompt})

                    print(f"[视频创作] API 地址: {api_base}")
                    print(f"[视频创作] 模型: {model}")
                    print(f"[视频创作] 系统提示词({len(self.sys_prompt)} 字符)")
                    print(f"[视频创作] 正在流式拆分分镜...")

                    stream = client.chat.completions.create(
                        model=model, messages=messages,
                        temperature=0.7, max_tokens=4096,
                        stream=True,
                    )

                    full_text = ""
                    full_reasoning = ""
                    buf = ""
                    THINK_OPEN = "<think>"
                    THINK_CLOSE = "</think>"
                    in_think = False

                    for chunk in stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta is None:
                            continue
                        text = delta.content or ""
                        if not text:
                            continue

                        buf += text
                        while buf:
                            if not in_think:
                                idx = buf.find(THINK_OPEN)
                                if idx == -1:
                                    partial = self._partial_tag(buf, THINK_OPEN)
                                    if partial:
                                        keep = buf[-partial:]
                                        emit = buf[:-partial]
                                        if emit:
                                            full_text += emit
                                            print(emit, end="", flush=True)
                                        buf = keep
                                        break
                                    else:
                                        full_text += buf
                                        print(buf, end="", flush=True)
                                        buf = ""
                                        break
                                else:
                                    before = buf[:idx]
                                    if before:
                                        full_text += before
                                        print(before, end="", flush=True)
                                    buf = buf[idx + len(THINK_OPEN):]
                                    in_think = True
                            else:
                                idx = buf.find(THINK_CLOSE)
                                if idx == -1:
                                    partial = self._partial_tag(buf, THINK_CLOSE)
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

                    if buf:
                        if in_think:
                            full_reasoning += buf
                            print(buf, end="", flush=True)
                        else:
                            full_text += buf
                            print(buf, end="", flush=True)

                    if full_reasoning:
                        print()
                    print(f"\n[视频创作] ✅ 拆分完成 ({len(full_text)} 字符)")

                    self.result_signal.emit(full_text)

                except Exception as e:
                    print(f"[视频创作] ❌ 拆分失败: {e}")
                    self.error_signal.emit(str(e))

            @staticmethod
            def _partial_tag(buf: str, tag: str) -> int:
                for n in range(len(tag) - 1, 0, -1):
                    if buf.endswith(tag[:n]):
                        return n
                return 0

        worker = SplitWorker(self._settings, content, self._reference_image, system_prompt)
        worker.result_signal.connect(self._on_split_done, Qt.ConnectionType.QueuedConnection)
        worker.error_signal.connect(self._on_split_error, Qt.ConnectionType.QueuedConnection)
        self._workers.append(worker)
        worker.start()

    def _on_split_done(self, text: str):
        self.split_btn.setEnabled(True)
        self.split_btn.setText("🔀 AI 拆分分镜")
        try:
            print(f"[视频创作] 拆分返回 ({len(text)} 字符)")
            import re
            # 优先提取 markdown 代码块内的 JSON
            json_str = None
            code_block_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
            if code_block_match:
                json_str = code_block_match.group(1).strip()
                print(f"[视频创作] 从代码块提取 JSON ({len(json_str)} 字符)")
            else:
                # fallback: 括号计数提取
                idx = text.find("[")
                if idx != -1:
                    depth = 0
                    start = idx
                    for i, ch in enumerate(text[idx:], start):
                        if ch == "[":
                            depth += 1
                        elif ch == "]":
                            depth -= 1
                            if depth == 0:
                                json_str = text[start:i+1]
                                break

            if json_str:
                print(f"[视频创作] 提取JSON ({len(json_str)} 字符)")
                cleaned = json_str.strip()
                # 修复尾随逗号
                cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
                try:
                    scenes = json.loads(cleaned)
                except json.JSONDecodeError as je:
                    print(f"[视频创作] JSON 修复尝试...")
                    # 尝试修复：对象之间缺少逗号的情况
                    # 在 } 和 "title" 之间插入逗号
                    fixed = re.sub(r"\}\s*(\"[\w一-鿿])", r"},\1", cleaned)
                    try:
                        scenes = json.loads(fixed)
                        print(f"[视频创作] JSON 修复成功")
                    except json.JSONDecodeError:
                        print(f"[视频创作] JSON 解析失败: {je}")
                        print(f"[视频创作] 出错位置附近: ...{cleaned[max(0,je.pos-30):je.pos+30]}...")
                        QMessageBox.critical(self, "解析失败", f"JSON 解析错误:\n{je}\n\nAI 返回的 JSON 格式异常（对象之间缺少逗号）。")
                        return
            else:
                QMessageBox.critical(self, "解析失败", "未找到有效的 JSON 数据，请重试。")
                return

            if not isinstance(scenes, list):
                raise ValueError(f"AI 返回的不是数组，类型: {type(scenes).__name__}")

            # 过滤掉参考图分镜，补充 voice 字段默认值
            for s in scenes:
                if "参考图" in s.get("title", ""):
                    continue
                s.setdefault("voice", "")
                self._scenes.append(s)
            print(f"[视频创作] 解析到 {len(self._scenes)} 个分镜")

            # 重建 UI
            try:
                self._build_scene_ui()
            except Exception as ue:
                print(f"[视频创作] _build_scene_ui 失败: {ue}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "UI 构建失败", str(ue))
                return
            self.gen_all_btn.setEnabled(True)
            self.gen_all_voice_btn.setEnabled(True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "拆分失败", f"解析AI返回失败: {e}\n\n原始返回:\n{text[:500]}")

    def _on_split_error(self, msg: str):
        self.split_btn.setEnabled(True)
        self.split_btn.setText("🔀 AI 拆分分镜")
        QMessageBox.critical(self, "拆分失败", msg)

    def _add_scene(self):
        """手动添加一个新分镜"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("添加分镜")
        dialog.setLabelText("分镜标题:")
        dialog.setTextValue("")
        dialog.setOkButtonText("确定")
        dialog.setCancelButtonText("取消")
        if dialog.exec() != QInputDialog.DialogCode.Accepted:
            return
        title = dialog.textValue().strip()
        if not title:
            QMessageBox.warning(self, "提示", "分镜标题不能为空。")
            return

        new_scene = {"title": title, "prompt": "请描述这个分镜的画面内容", "voice": "", "image": "", "video": ""}
        scene_index = len(self._scenes)
        self._scenes.append(new_scene)

        sw = SceneWidget(scene_index, title, new_scene["prompt"], new_scene["voice"], panel=self)
        sw.gen_img_btn.clicked.connect(
            lambda checked, idx=scene_index: self._generate_scene_image(idx))
        sw.gen_video_btn.clicked.connect(
            lambda checked, idx=scene_index: self._generate_scene_video(idx))
        self.scene_layout.insertWidget(self.scene_layout.count() - 1, sw)
        self._scene_widgets.append(sw)
        self.gen_all_btn.setEnabled(True)
        self.gen_all_voice_btn.setEnabled(True)
        print(f"[视频创作] 手动添加分镜: {title}")

    def _build_scene_ui(self):
        """根据分镜数据重建 UI"""
        for w in self._scene_widgets:
            self.scene_layout.removeWidget(w)
            w.deleteLater()
        self._scene_widgets.clear()

        for i, scene in enumerate(self._scenes):
            sw = SceneWidget(i, scene["title"], scene["prompt"], scene.get("voice", ""), panel=self)
            sw.gen_img_btn.clicked.connect(
                lambda checked, idx=i: self._generate_scene_image(idx))
            sw.gen_video_btn.clicked.connect(
                lambda checked, idx=i: self._generate_scene_video(idx))
            self.scene_layout.insertWidget(self.scene_layout.count() - 1, sw)
            self._scene_widgets.append(sw)

    # ═══════════════ 单分镜生图 ═══════════════

    def _generate_scene_image(self, scene_index: int):
        sw = self._scene_widgets[scene_index]
        prompt = sw.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入生图提示词。")
            return

        sw.gen_img_btn.setEnabled(False)
        sw.gen_img_btn.setText("生成中……")
        sw.img_status.setText("⏳")
        sw.img_status.setStyleSheet("color: #ffa502; font-size: 11px;")

        ref_path = self._reference_image
        scene_title = self._scenes[scene_index]["title"]

        class ImageGenWorker(QThread):
            result_signal = pyqtSignal(int, str)  # scene_index, b64
            error_signal = pyqtSignal(int, str)

            def __init__(self, settings, prompt, ref_path, scene_index, scene_title, orientation):
                super().__init__()
                self.settings = settings
                self.prompt = prompt
                self.ref_path = ref_path
                self.scene_index = scene_index
                self.scene_title = scene_title
                self.orientation = orientation  # "竖版 9:16" or "横版 16:9"

            def run(self):
                try:
                    from openai import OpenAI
                    api_key = self.settings.get("openai_image_api_key") or self.settings.get("openai_api_key", "")
                    api_base = self.settings.get("openai_image_api_base") or self.settings.get("openai_api_base", "https://api.siliconflow.cn/v1")
                    model = self.settings.get("openai_image_model") or "Kwai-Kolors/Kolors"
                    base_url = api_base.rstrip("/")
                    client = OpenAI(api_key=api_key, base_url=base_url)

                    # 方向和尺寸
                    orientation = self.orientation
                    if orientation.startswith("横"):
                        image_size = "1792x1024"
                        orient_text = "横版 16:9"
                    else:
                        image_size = "1024x1792"
                        orient_text = "竖版 9:16"

                    full_prompt = f"{self.prompt}\n\n画面比例：{orient_text}，必须严格按此比例构图。"

                    print(f"[视频创作] 生图: 分镜{self.scene_index+1}, base={base_url}, model={model}")

                    if self.ref_path and os.path.exists(self.ref_path):
                        # 图生图：压缩参考图后用 data URI 格式
                        img = Image.open(self.ref_path)
                        # 缩放到合理尺寸
                        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="PNG", optimize=True)
                        ref_b64 = base64.b64encode(buf.getvalue()).decode()
                        data_uri = f"data:image/png;base64,{ref_b64}"
                        full_prompt = (
                            f"{full_prompt}\n\n"
                            f"参考图片已提供，请保持与参考图一致的视觉风格、色彩和构图。"
                        )
                        print(f"[视频创作] 图生图模式，参考图压缩后: {len(ref_b64)} chars")
                        # 检查请求体大小
                        body_size = len(data_uri)
                        print(f"[视频创作] image字段大小: {body_size} bytes")
                        resp = client.images.generate(
                            model=model,
                            prompt=full_prompt,
                            n=1,
                            size=image_size,
                            extra_body={
                                "image": data_uri,
                                "image_size": image_size,
                                "num_inference_steps": 20,
                                "guidance_scale": 7.5,
                                "strength": 0.75,
                            }
                        )
                    else:
                        # 文生图
                        resp = client.images.generate(
                            model=model,
                            prompt=full_prompt,
                            n=1,
                            size=image_size,
                            extra_body={
                                "image_size": image_size,
                                "num_inference_steps": 20,
                                "guidance_scale": 7.5,
                                "batch_size": 1,
                                "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
                            }
                        )

                    # 解析返回 URL
                    img_url = None
                    if hasattr(resp, "data") and resp.data:
                        img_url = resp.data[0].url
                    if not img_url and hasattr(resp, "images") and resp.images:
                        img_url = resp.images[0].url

                    if img_url:
                        import urllib.request
                        img_data = urllib.request.urlopen(img_url, timeout=120).read()
                        self.result_signal.emit(self.scene_index, base64.b64encode(img_data).decode())
                    else:
                        self.error_signal.emit(self.scene_index, f"未获取到图片URL, resp={resp}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.error_signal.emit(self.scene_index, str(e))

        orientation = self.orientation_combo.currentText()
        worker = ImageGenWorker(self._settings, prompt, ref_path, scene_index, scene_title, orientation)
        worker.result_signal.connect(self._on_scene_image_done)
        worker.error_signal.connect(self._on_scene_image_error)
        self._workers.append(worker)
        worker.start()

    def _on_scene_image_done(self, scene_index: int, b64_data: str):
        sw = self._scene_widgets[scene_index]
        import tempfile
        path = os.path.join(tempfile.gettempdir(), f"dy_scene_{scene_index}_{os.getpid()}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        sw.generated_image_path = path
        self._scenes[scene_index]["image"] = path

        pixmap = QPixmap(path).scaled(180, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        sw.img_label.setPixmap(pixmap)
        sw.img_label.setStyleSheet("border: 1px solid #2ed573; border-radius: 8px;")
        sw.gen_img_btn.setEnabled(True)
        sw.gen_img_btn.setText("🖼️ 生成图片")
        sw.img_status.setText("✅")
        sw.img_status.setStyleSheet("color: #2ed573; font-size: 11px;")
        sw.gen_video_btn.setEnabled(True)

        # 全部完成后启用视频创作按钮
        all_done = all(w.generated_image_path for w in self._scene_widgets)
        if all_done:
            self.create_video_btn.setEnabled(True)

    def _on_scene_image_error(self, scene_index: int, msg: str):
        sw = self._scene_widgets[scene_index]
        sw.gen_img_btn.setEnabled(True)
        sw.gen_img_btn.setText("🖼️ 生成图片")
        sw.img_status.setText("❌")
        sw.img_status.setStyleSheet("color: #ff4757; font-size: 11px;")
        QMessageBox.critical(self, "生图失败", f"分镜{scene_index+1}: {msg}")

    def _generate_all_voices(self):
        """为所有分镜生成音频"""
        total = len(self._scene_widgets)
        if total == 0:
            return
        for i in range(total):
            sw = self._scene_widgets[i]
            text = sw.voice_edit.toPlainText().strip()
            if text and not sw.generated_voice_path:
                self._generate_scene_voice(i)

    # ═══════════════ 全部分镜生图 ═══════════════

    def _generate_all_images(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        total = len(self._scene_widgets)
        for i in range(total):
            self.progress_label.setText(f"生成分镜 {i+1}/{total}...")
            self.progress_bar.setValue(int((i / total) * 100))
            self._generate_scene_image(i)
        # Note: this fires them all in parallel due to QThread; progress is approximate

    # ═══════════════ 单分镜语音生成 ═══════════════

    def _generate_scene_voice(self, scene_index: int):
        sw = self._scene_widgets[scene_index]
        text = sw.voice_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "口播文案为空。")
            return

        sw.gen_voice_btn.setEnabled(False)
        sw.gen_voice_btn.setText("生成中…")
        sw.voice_status.setText("⏳")
        sw.voice_status.setStyleSheet("color: #ffa502; font-size: 11px;")

        voice_role = self._settings.get("mpt_voice_role", "zh-CN-XiaoxiaoNeural")

        class VoiceWorker(QThread):
            done_signal = pyqtSignal(int, str)
            err_signal = pyqtSignal(int, str)

            def __init__(self, text, voice_role, scene_index):
                super().__init__()
                self.text = text
                self.voice_role = voice_role
                self.scene_index = scene_index

            def run(self):
                try:
                    from core_modules.mpt_services.voice import VoiceService
                    svc = VoiceService(self.voice_role)
                    out = svc.generate_speech(self.text)
                    self.done_signal.emit(self.scene_index, out)
                except Exception as e:
                    self.err_signal.emit(self.scene_index, str(e))

        worker = VoiceWorker(text, voice_role, scene_index)
        worker.done_signal.connect(self._on_voice_done)
        worker.err_signal.connect(self._on_voice_error)
        self._workers.append(worker)
        worker.start()

    # ═══════════════ 音频播放器全局信号处理 ═══════════════

    def _on_global_position_changed(self, position):
        if self._current_playing_scene < 0:
            return
        sw = self._scene_widgets[self._current_playing_scene]
        if sw.voice_slider.isSliderDown():
            return
        sw.voice_slider.blockSignals(True)
        sw.voice_slider.setValue(position)
        sw.voice_slider.blockSignals(False)
        # 更新当前时间
        duration = self._audio_player.duration()
        cur = self._format_duration(position)
        dur = self._format_duration(duration)
        sw.voice_duration_label.setText(f"{cur} / {dur}")

    def _on_global_duration_changed(self, duration):
        if self._current_playing_scene < 0:
            return
        sw = self._scene_widgets[self._current_playing_scene]
        sw.voice_slider.blockSignals(True)
        sw.voice_slider.setRange(0, duration)
        sw.voice_slider.blockSignals(False)
        sw.voice_duration_label.setText(f"00:00 / {self._format_duration(duration)}")

    def _on_global_playback_changed(self, state):
        if self._current_playing_scene < 0:
            return
        sw = self._scene_widgets[self._current_playing_scene]
        if state == self._audio_player.PlaybackState.PlayingState:
            sw.play_pause_btn.setText("⏸")
        else:
            sw.play_pause_btn.setText("▶")
            if state == self._audio_player.PlaybackState.StoppedState:
                self._audio_player.setPosition(0)
                sw.voice_slider.blockSignals(True)
                sw.voice_slider.setValue(0)
                sw.voice_slider.blockSignals(False)

    def _on_voice_done(self, scene_index: int, audio_path: str):
        sw = self._scene_widgets[scene_index]
        sw.generated_voice_path = audio_path
        self._scenes[scene_index]["voice"] = audio_path
        sw.gen_voice_btn.setEnabled(True)
        sw.gen_voice_btn.setText("🔊 重新生成")
        sw.play_pause_btn.setVisible(True)
        sw.voice_slider.setVisible(True)
        sw.voice_duration_label.setVisible(True)
        sw.voice_slider.setValue(0)
        sw.voice_duration_label.setText("00:00 / 00:00")
        sw.play_pause_btn.setText("▶")
        sw.voice_status.setText("✅")
        sw.voice_status.setStyleSheet("color: #2ed573; font-size: 11px;")

    def _on_voice_error(self, scene_index: int, msg: str):
        sw = self._scene_widgets[scene_index]
        sw.gen_voice_btn.setEnabled(True)
        sw.gen_voice_btn.setText("🔊 生成音频")
        sw.play_pause_btn.setVisible(False)
        sw.voice_slider.setVisible(False)
        sw.voice_duration_label.setVisible(False)
        sw.voice_status.setText("❌")
        sw.voice_status.setStyleSheet("color: #ff4757; font-size: 11px;")
        QMessageBox.critical(self, "语音生成失败", f"分镜{scene_index+1}: {msg}")

    # ═══════════════ 视频生成 ═══════════════

    def _generate_scene_video(self, scene_index: int):
        sw = self._scene_widgets[scene_index]
        sw.gen_video_btn.setEnabled(False)
        sw.gen_video_btn.setText("生成中……")
        sw.video_status_label.setText("⏳ 视频生成中……")
        sw.video_status_label.setStyleSheet("color: #ffa502; font-size: 11px;")
        sw.video_status_label.setVisible(True)

        class VideoGenWorker(QThread):
            result_signal = pyqtSignal(int, str)   # scene_index, video_url
            error_signal = pyqtSignal(int, str)

            def __init__(self, settings, image_path, scene_index, scene_prompt, orientation):
                super().__init__()
                self.settings = settings
                self.image_path = image_path
                self.scene_index = scene_index
                self.scene_prompt = scene_prompt
                self.orientation = orientation

            def run(self):
                try:
                    import time
                    api_key = self.settings.get("openai_video_api_key") or self.settings.get("openai_api_key", "")
                    api_base = self.settings.get("openai_video_api_base") or self.settings.get("openai_api_base", "https://api.siliconflow.cn/v1")
                    model = self.settings.get("openai_video_model") or "Wan-AI/Wan2.2-I2V-A14B"
                    base_url = api_base.rstrip("/")

                    img_size = "1280x720" if self.orientation.startswith("横") else "720x1280"

                    # 编码首帧图片
                    with open(self.image_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    image_data = f"data:image/png;base64,{img_b64}"
                    print(f"[视频创作] 视频-分镜{self.scene_index+1}: 首帧图片 {len(img_b64)} chars")

                    # Step 1: 提交视频生成任务
                    submit_url = f"{base_url}/video/submit"
                    body = json.dumps({
                        "model": model,
                        "prompt": self.scene_prompt,
                        "image": image_data,
                        "image_size": img_size,
                    }).encode()
                    req = urllib.request.Request(submit_url, data=body, method="POST")
                    req.add_header("Authorization", f"Bearer {api_key}")
                    req.add_header("Content-Type", "application/json")
                    print(f"[视频创作] POST {submit_url}")
                    resp = urllib.request.urlopen(req, timeout=30)
                    submit_data = json.loads(resp.read())
                    request_id = submit_data.get("requestId", "")
                    print(f"[视频创作] 任务已提交, requestId={request_id}")
                    print(f"[视频创作] 提交响应: {json.dumps(submit_data, ensure_ascii=False)}")

                    if not request_id:
                        self.error_signal.emit(self.scene_index, f"未获取到requestId: {submit_data}")
                        return

                    # Step 2: 轮询状态
                    status_url = f"{base_url}/video/status"
                    max_polls = 60  # 最多10分钟
                    for poll in range(max_polls):
                        time.sleep(10)
                        body = json.dumps({"requestId": request_id}).encode()
                        req = urllib.request.Request(status_url, data=body, method="POST")
                        req.add_header("Authorization", f"Bearer {api_key}")
                        req.add_header("Content-Type", "application/json")
                        resp = urllib.request.urlopen(req, timeout=30)
                        status_data = json.loads(resp.read())
                        status = status_data.get("status", "")
                        print(f"[视频创作] 轮询 {poll+1}/{max_polls}: status={status}")
                        print(f"[视频创作] 状态响应: {json.dumps(status_data, ensure_ascii=False)[:300]}")

                        if status == "Succeed":
                            videos = (status_data.get("results", {}).get("videos") or [])
                            if videos and videos[0].get("url"):
                                video_url = videos[0]["url"]
                                print(f"[视频创作] ✅ 视频生成成功: {video_url[:100]}...")
                                # 下载视频
                                vd = urllib.request.urlopen(video_url, timeout=120).read()
                                video_path = os.path.join(tempfile.gettempdir(), f"dy_video_{self.scene_index}_{os.getpid()}.mp4")
                                with open(video_path, "wb") as vf:
                                    vf.write(vd)
                                print(f"[视频创作] 视频已保存: {video_path} ({len(vd)} bytes)")
                                self.result_signal.emit(self.scene_index, video_path)
                                return
                            else:
                                self.error_signal.emit(self.scene_index, "视频生成成功但未获取到URL")
                                return
                        elif status in ("Failed", "Error"):
                            reason = status_data.get("reason", "未知错误")
                            self.error_signal.emit(self.scene_index, f"视频生成失败: {reason}")
                            return

                    self.error_signal.emit(self.scene_index, f"视频生成超时 ({max_polls*10}秒)")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.error_signal.emit(self.scene_index, str(e))

        prompt_text = self._scenes[scene_index]["title"]
        orientation = self.orientation_combo.currentText()
        worker = VideoGenWorker(self._settings, sw.generated_image_path, scene_index, prompt_text, orientation)
        worker.result_signal.connect(lambda idx, p: self._on_scene_video_done(idx, p))
        worker.error_signal.connect(lambda idx, m: self._on_scene_video_error(idx, m))
        self._workers.append(worker)
        worker.start()

    def _on_scene_video_done(self, scene_index: int, video_path: str = ""):
        sw = self._scene_widgets[scene_index]
        sw.generated_video_path = video_path
        sw.gen_video_btn.setText("🎬 重新生成")
        sw.gen_video_btn.setEnabled(True)
        sw.video_status_label.setText("✅ 视频已生成")
        sw.video_status_label.setStyleSheet("color: #2ed573; font-size: 11px;")
        sw.play_video_btn.setVisible(True)

    def _on_scene_video_error(self, scene_index: int, msg: str):
        sw = self._scene_widgets[scene_index]
        sw.gen_video_btn.setEnabled(True)
        sw.gen_video_btn.setText("🎬 生成视频")
        sw.video_status_label.setText(f"❌ {msg}")
        sw.video_status_label.setStyleSheet("color: #ff4757; font-size: 11px;")
        QMessageBox.critical(self, "视频生成失败", f"分镜{scene_index+1}: {msg}")

    # ═══════════════ 最终视频创作 ═══════════════

    def _create_video(self):
        """用 FFmpeg 将所有分镜视频片段拼接为一个完整视频"""
        segments_with_audio = []
        for sw in self._scene_widgets:
            if sw.generated_video_path and os.path.exists(sw.generated_video_path):
                segments_with_audio.append({
                    "video": sw.generated_video_path,
                    "voice": sw.generated_voice_path if (sw.generated_voice_path and os.path.exists(sw.generated_voice_path)) else None,
                })

        if not segments_with_audio:
            QMessageBox.warning(self, "提示", "没有任何视频片段可拼接，请先生成或上传视频。")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存完整视频", "完整视频.mp4", "MP4 (*.mp4)"
        )
        if not output_path:
            return

        self.create_video_btn.setEnabled(False)
        self.create_video_btn.setText("拼接中……")

        class ConcatWorker(QThread):
            finished_signal = pyqtSignal(str)
            error_signal = pyqtSignal(str)
            progress_signal = pyqtSignal(int)

            def __init__(self, segments, output_path):
                super().__init__()
                self.segments = segments
                self.output_path = output_path

            def run(self):
                try:
                    import subprocess
                    import tempfile

                    # Step 1: 逐个处理分镜 → 静音原声 + 叠加语音配音
                    processed = []
                    total = len(self.segments)
                    for i, seg in enumerate(self.segments):
                        video_path = seg["video"]
                        voice_path = seg["voice"]
                        out = os.path.join(tempfile.gettempdir(), f"dy_seg_{i}_{os.getpid()}.mp4")

                        if voice_path:
                            # 视频流保留，音频用分镜配音（-shortest 以配音为准截断/延长视频）
                            cmd = [
                                "ffmpeg", "-y",
                                "-i", video_path,
                                "-i", voice_path,
                                "-map", "0:v",
                                "-map", "1:a",
                                "-c:v", "copy",
                                "-c:a", "aac",
                                "-shortest",
                                out
                            ]
                        else:
                            # 无配音：静音原视频
                            cmd = [
                                "ffmpeg", "-y",
                                "-i", video_path,
                                "-an",
                                "-c:v", "copy",
                                out
                            ]

                        print(f"[创作] 处理分镜 {i+1}/{total}")
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode != 0:
                            print(f"[创作] 分镜 {i+1} 处理失败: {result.stderr.decode()[-300:]}")
                            import shutil
                            shutil.copy2(video_path, out)
                        processed.append(out)
                        self.progress_signal.emit(int((i + 1) / total * 70))

                    # Step 2: 拼接所有分镜
                    self.progress_signal.emit(75)
                    list_path = os.path.join(tempfile.gettempdir(), "dy_concat_list.txt")
                    with open(list_path, "w", encoding="utf-8") as f:
                        for p in processed:
                            f.write(f"file '{p.replace(os.sep, '/')}'\n")

                    result = subprocess.run(
                        [
                            "ffmpeg", "-y",
                            "-f", "concat", "-safe", "0",
                            "-i", list_path,
                            "-c:v", "libx264", "-preset", "fast",
                            "-c:a", "aac",
                            self.output_path
                        ],
                        capture_output=True, timeout=600
                    )
                    os.remove(list_path)

                    # 清理临时文件
                    for p in processed:
                        try:
                            os.remove(p)
                        except Exception:
                            pass

                    self.progress_signal.emit(100)

                    if result.returncode != 0:
                        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-500:])

                    self.finished_signal.emit(self.output_path)

                except subprocess.TimeoutExpired:
                    self.error_signal.emit("视频拼接超时，请检查 FFmpeg 是否安装。")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.error_signal.emit(f"拼接失败: {e}")

        def on_done(path):
            self.create_video_btn.setEnabled(True)
            self.create_video_btn.setText("创作视频")
            QMessageBox.information(self, "创作完成", f"视频已保存到:\n{path}")

        def on_error(msg):
            self.create_video_btn.setEnabled(True)
            self.create_video_btn.setText("创作视频")
            QMessageBox.critical(self, "拼接失败", msg)

        worker = ConcatWorker(segments_with_audio, output_path)
        worker.finished_signal.connect(on_done)
        worker.error_signal.connect(on_error)
        worker.progress_signal.connect(self.progress_bar.setValue)
        self._workers.append(worker)
        worker.start()
