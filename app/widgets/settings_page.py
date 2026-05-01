"""设置页面 — 环境检查 + CDP/Cookie 配置"""

import os
import json
import urllib.request
import urllib.error
import functools

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QGroupBox, QFormLayout,
    QCheckBox, QFileDialog, QMessageBox, QComboBox,
    QFrame, QScrollArea,
)


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


class CdpSettingsTab(QWidget):
    """CDP 地址 + Cookie 配置"""
    settings_changed = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._test_workers = []  # 保持引用防止 GC 回收
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # CDP 地址
        cdp_group = QGroupBox("CDP 调试端口")
        cdp_form = QFormLayout(cdp_group)
        cdp_form.setSpacing(10)

        self.cdp_input = QLineEdit(self.settings.get("cdp_url", "http://127.0.0.1:9222"))
        self.cdp_input.textChanged.connect(self._save)
        cdp_form.addRow("连接地址:", self.cdp_input)

        hint = QLabel("Chrome 启动参数: --remote-debugging-port=9222")
        hint.setObjectName("hintLabel")
        cdp_form.addRow(hint)

        layout.addWidget(cdp_group)

        # Cookie
        cookie_group = QGroupBox("Cookie 登录配置")
        cookie_layout = QHBoxLayout(cookie_group)
        cookie_layout.setSpacing(8)

        self.cookie_input = QLineEdit(self.settings.get("cookie_file", ""))
        self.cookie_input.setPlaceholderText("选择 cookies.json ...")
        self.cookie_input.textChanged.connect(self._save)
        cookie_layout.addWidget(self.cookie_input, 1)

        browse = QPushButton("浏览")
        browse.setObjectName("smallBtn")
        browse.clicked.connect(self._browse_cookie)
        cookie_layout.addWidget(browse)

        layout.addWidget(cookie_group)

        # 存储路径
        storage_group = QGroupBox("任务结果存储")
        storage_layout = QHBoxLayout(storage_group)
        storage_layout.setSpacing(8)

        default_storage = os.path.join(os.path.expanduser("~"), ".dy", "results")
        self.storage_input = QLineEdit(self.settings.get("storage_path", default_storage))
        self.storage_input.setPlaceholderText("选择存储目录...")
        self.storage_input.textChanged.connect(self._save)
        storage_layout.addWidget(self.storage_input, 1)

        browse_storage = QPushButton("浏览")
        browse_storage.setObjectName("smallBtn")
        browse_storage.clicked.connect(self._browse_storage)
        storage_layout.addWidget(browse_storage)

        layout.addWidget(storage_group)

        # 模式
        mode_group = QGroupBox("运行模式")
        mode_layout = QVBoxLayout(mode_group)
        self.cdp_mode = QCheckBox("使用 CDP 连接已有 Chrome（推荐）")
        self.cdp_mode.setChecked(self.settings.get("use_cdp", True))
        self.cdp_mode.toggled.connect(self._save)
        mode_layout.addWidget(self.cdp_mode)
        layout.addWidget(mode_group)

        # ═══════════════ AI 生成配置 ═══════════════
        # 文字大模型
        self._build_ai_group(layout, "📝 文字大模型设置", "openai_text",
                             "https://api.deepseek.com/v1", "deepseek-chat", "text")

        # 图片大模型
        self._build_ai_group(layout, "🖼️ 图片大模型设置", "openai_image",
                             "https://api.siliconflow.cn/v1", "Kwai-Kolors/Kolors", "image")

        # 视频大模型
        self._build_ai_group(layout, "🎬 视频大模型设置", "openai_video",
                             "https://api.siliconflow.cn/v1", "Wan-AI/Wan2.2-I2V-A14B", "video")

        # 抖音视频下载密钥
        dl_group = QGroupBox("📥 抖音视频下载")
        dl_form = QFormLayout(dl_group)
        dl_form.setSpacing(12)
        dl_key = "douyin_api_key"
        dl_input = QLineEdit(self.settings.get(dl_key, ""))
        dl_input.setPlaceholderText("用于语音转文字的 API Key")
        dl_input.setEchoMode(QLineEdit.EchoMode.Password)
        dl_input.setMinimumHeight(36)
        dl_input.textChanged.connect(lambda t, b=dl_input, k=dl_key: self._on_ai_field_change(b, k))
        dl_form.addRow("API 密钥:", dl_input)
        layout.addWidget(dl_group)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_ai_group(self, layout, title: str, prefix: str, default_base: str, default_model: str, model_type: str = "text"):
        """构建一个 AI 模型配置组"""
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setSpacing(12)

        base_key = f"{prefix}_api_base"
        key_key = f"{prefix}_api_key"
        model_key = f"{prefix}_model"
        fmt_key = f"{prefix}_format"
        path_key = f"{prefix}_json_path"

        base_input = QLineEdit(self.settings.get(base_key, default_base))
        base_input.setPlaceholderText(default_base)
        base_input.setMinimumHeight(36)
        base_input.textChanged.connect(lambda t, b=base_input, k=base_key: self._on_ai_field_change(b, k))
        form.addRow("API 地址:", base_input)

        key_input = QLineEdit(self.settings.get(key_key, ""))
        key_input.setPlaceholderText("sk-xxx...")
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setMinimumHeight(36)
        key_input.textChanged.connect(lambda t, b=key_input, k=key_key: self._on_ai_field_change(b, k))
        form.addRow("API 密钥:", key_input)

        model_input = QLineEdit(self.settings.get(model_key, default_model))
        model_input.setPlaceholderText(default_model)
        model_input.setMinimumHeight(36)
        model_input.textChanged.connect(lambda t, b=model_input, k=model_key: self._on_ai_field_change(b, k))
        form.addRow("模型名称:", model_input)

        # 测试按钮
        test_row = QHBoxLayout()
        test_row.addStretch()
        test_btn = QPushButton("🔌 测试连接")
        test_btn.setObjectName("smallBtn")
        test_status = QLabel("")
        test_status.setStyleSheet("color: #8b949e; font-size: 12px;")

        test_btn.clicked.connect(functools.partial(
            self._test_ai_api, base_input, key_input, model_input, test_btn, test_status, model_type, prefix))
        test_row.addWidget(test_btn)
        test_row.addWidget(test_status)
        test_row.addStretch()
        form.addRow(test_row)

        layout.addWidget(group)

    def _on_ai_field_change(self, input_widget, key: str):
        self.settings[key] = input_widget.text().strip()
        self._save()

    def _on_ai_combo_change(self, combo, key: str):
        self.settings[key] = "openai" if combo.currentIndex() == 0 else "custom"
        self._save()

    def _test_ai_api(self, base_input, key_input, model_input, test_btn, test_status, model_type="text", prefix=""):
        base = base_input.text().strip()
        key = key_input.text().strip()
        model = model_input.text().strip()

        print(f"[测试] API 地址: {base}")
        print(f"[测试] API 密钥: {key[:8]}...{key[-4:] if len(key) > 12 else ''}")
        print(f"[测试] 模型名称: {model}")

        if not base:
            QMessageBox.warning(self, "提示", "请先填写 API 地址。")
            return
        if not key:
            QMessageBox.warning(self, "提示", "请先填写 API 密钥。")
            return

        test_btn.setEnabled(False)
        test_btn.setText("测试中...")
        test_status.setText("⏳ 正在连接...")
        test_status.setStyleSheet("color: #ffa502; font-size: 12px;")

        class TestWorker(QThread):
            result_signal = pyqtSignal(bool, str)

            def __init__(self, base_url, api_key, model_name, model_type, settings, prefix):
                super().__init__()
                self.base_url = base_url.rstrip("/")
                self.api_key = api_key
                self.model_name = model_name
                self.model_type = model_type
                self.settings = settings
                self.prefix = prefix

            def run(self):
                try:
                    if self.model_type == "image":
                        # 图片模型：标准 OpenAI 格式 POST
                        url = f"{self.base_url}/images/generations"
                        print(f"[测试] 图片模型测试: {self.model_name}")
                        body = json.dumps({
                            "model": self.model_name,
                            "prompt": "a simple red circle on white background",
                            "n": 1, "size": "512x512", "image_size": "512x512",
                            "num_inference_steps": 10, "guidance_scale": 7.5, "batch_size": 1,
                        }).encode()
                        req = urllib.request.Request(url, data=body, method="POST")
                        req.add_header("Authorization", f"Bearer {self.api_key}")
                        req.add_header("Content-Type", "application/json")
                        print(f"[测试] POST {url}")
                        print(f"[测试] Body keys: {list(json.loads(body).keys())}")
                        resp = urllib.request.urlopen(req, timeout=30)
                        print(f"[测试] 响应状态: {resp.status}")
                        raw = resp.read()
                        print(f"[测试] 响应长度: {len(raw)} bytes")
                        print(f"[测试] 响应预览: {raw[:300]}")
                        data = json.loads(raw)
                        urls = _extract_image_urls(data)
                        img_url = urls[0] if urls else ""
                        if img_url:
                            msg = f"图片生成成功！\n模型: {self.model_name}\n图片URL: {img_url[:80]}..."
                            print(f"[测试] ✅ {msg}")
                            self.result_signal.emit(True, msg)
                            return
                        else:
                            self.result_signal.emit(False, f"未获取到图片URL，返回: {json.dumps(data)[:200]}")
                            return
                    else:
                        # 文字/视频模型：GET /models
                        url = f"{self.base_url}/models"
                    print(f"[测试] 请求 URL: {url}")
                    print(f"[测试] Authorization: Bearer {self.api_key[:8]}...")
                    req = urllib.request.Request(url, method="GET")
                    req.add_header("Authorization", f"Bearer {self.api_key}")
                    req.add_header("Content-Type", "application/json")
                    resp = urllib.request.urlopen(req, timeout=10)
                    print(f"[测试] 响应状态: {resp.status}")
                    raw = resp.read()
                    print(f"[测试] 响应长度: {len(raw)} bytes")
                    data = json.loads(raw)
                    model_ids = [m["id"] for m in data.get("data", [])]
                    print(f"[测试] 模型列表 ({len(model_ids)} 个): {model_ids[:10]}...")
                    if model_ids:
                        found = self.model_name in model_ids
                        info = f"模型 '{self.model_name}' {'✓ 可用' if found else '✗ 未找到'}"
                        msg = f"连接成功！{len(model_ids)} 个模型。{info}"
                        print(f"[测试] ✅ {msg}")
                        self.result_signal.emit(True, msg)
                    else:
                        print(f"[测试] ✅ 连接成功！但未返回模型列表。")
                        self.result_signal.emit(True, "连接成功！但未返回模型列表。")
                except urllib.error.HTTPError as e:
                    body = ""
                    try:
                        body = e.read().decode()[:200]
                    except Exception:
                        pass
                    msg = f"HTTP {e.code}: {e.reason}\n{body}"
                    print(f"[测试] ❌ {msg}")
                    self.result_signal.emit(False, msg)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    msg = f"连接失败: {type(e).__name__}: {str(e)[:200]}"
                    print(f"[测试] ❌ {msg}")
                    self.result_signal.emit(False, msg)

        worker = TestWorker(base, key, model, model_type, self.settings, prefix)
        self._test_workers.append(worker)  # 保持引用防止 GC 回收
        worker.result_signal.connect(
            lambda success, msg: self._on_test_result(success, msg, test_btn, test_status))
        worker.start()

    def _on_test_result(self, success: bool, message: str, test_btn, test_status):
        print(f"[测试] 回调 success={success} message={message[:100]}")
        test_btn.setEnabled(True)
        test_btn.setText("🔌 测试连接")
        if success:
            test_status.setText("✅ " + message.split("\n")[0])
            test_status.setStyleSheet("color: #2ed573; font-size: 12px;")
            QMessageBox.information(self, "测试结果", message)
        else:
            test_status.setText("❌ 失败")
            test_status.setStyleSheet("color: #ff4757; font-size: 12px;")
            QMessageBox.warning(self, "测试失败", message)

    def _browse_cookie(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Cookie", "", "JSON (*.json)")
        if path:
            self.cookie_input.setText(path)
            self._save()

    def _browse_storage(self):
        path = QFileDialog.getExistingDirectory(self, "选择存储目录")
        if path:
            self.storage_input.setText(path)
            self._save()

    def _save(self):
        self.settings["cdp_url"] = self.cdp_input.text().strip()
        self.settings["cookie_file"] = self.cookie_input.text().strip() or None
        self.settings["storage_path"] = self.storage_input.text().strip()
        self.settings["use_cdp"] = self.cdp_mode.isChecked()
        self.settings_changed.emit()

    def get_cdp_url(self) -> str:
        return self.cdp_input.text().strip()


class SettingsPage(QWidget):
    """设置页面 = 环境检查 + CDP/Cookie"""
    ready_changed = pyqtSignal(bool)
    cookie_saved = pyqtSignal(str)

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("⚙ 设置")
        title.setObjectName("pageTitle")
        title.setContentsMargins(28, 20, 0, 8)
        layout.addWidget(title)

        tabs = QTabWidget()

        # 环境检查 tab
        from app.widgets.environment_panel import EnvironmentPanel
        self.env_tab = EnvironmentPanel(self.settings)
        self.env_tab.ready_changed.connect(self.ready_changed.emit)
        self.env_tab.cookie_saved.connect(self.cookie_saved.emit)
        self.env_tab.settings_changed.connect(self._on_settings_changed)
        tabs.addTab(self.env_tab, "环境检查")

        # CDP/Cookie tab
        self.cdp_tab = CdpSettingsTab(self.settings)
        tabs.addTab(self.cdp_tab, "连接配置")

        layout.addWidget(tabs)

    def _on_settings_changed(self):
        """CDP 地址或设置变更时通知环境检查刷新，并转发给 MainWindow 持久化"""
        self.env_tab.check_all()
        # 转发给 MainWindow（通过 cdp_tab 的信号）
        self.cdp_tab.settings_changed.emit()

    def is_ready(self) -> bool:
        return self.env_tab.is_ready()

    def cdp_url(self) -> str:
        return self.cdp_tab.get_cdp_url()
