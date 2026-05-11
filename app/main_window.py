"""主窗口 — 左侧导航 + 主工作区"""

import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QLocale
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMessageBox, QMenuBar, QMenu, QFileDialog,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel,
    QSplitter, QFrame, QPushButton, QSizePolicy,
)

from app.widgets.search_panel import SearchPanel
from app.widgets.progress_panel import ProgressPanel
from app.widgets.results_panel import ResultsPanel
from app.widgets.script_panel import ScriptPanel
from app.widgets.settings_page import SettingsPage
from app.worker import DataWorker
from app.task_store import TaskStore
from app.styles import MODERN_THEME
from app.theme import NEON_RED, NEON_GREEN, NEON_BLUE

APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".dy", "desktop_settings.json")


class SidebarButton(QPushButton):
    """左侧导航按钮 — 图标 + 文字"""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self.setCheckable(True)
        self.setObjectName("navBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(48)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker: DataWorker | None = None
        self.settings = self._load_settings()
        storage = self.settings.get("storage_path", "")
        self.task_store = TaskStore(storage if storage else None)
        self._init_ui()
        self._init_menu()
        self._init_statusbar()

    # ══════════════════════════════════════════
    #  UI 构建
    # ══════════════════════════════════════════

    def _init_ui(self):
        self.setWindowTitle("数据采集助手")
        self.setFixedSize(1280, 820)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 左侧导航 ──
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(4)

        # Logo
        logo = QLabel("  ◈  数据\n     采集助手")
        logo.setObjectName("sidebarLogo")
        logo.setMinimumHeight(60)
        sidebar_layout.addWidget(logo)

        sidebar_layout.addSpacing(16)

        # 导航按钮组
        self.nav_group = []
        nav_items = [
            ("🔍", "搜索采集"),
            ("🎬", "剧本生成"),
            ("📈", "视频分析"),
            ("📟", "运行日志"),
            ("📊", "结果查看"),
        ]
        for icon, text in nav_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, i=len(self.nav_group): self._switch_page(i))
            self.nav_group.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # 设置按钮（导航到设置页 index=5）
        settings_btn = SidebarButton("⚙", "设置")
        settings_btn.clicked.connect(lambda: self._switch_page(5))
        sidebar_layout.addWidget(settings_btn)

        # 底部版本
        version = QLabel("v2.0 · PyQt6")
        version.setObjectName("sidebarVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version)

        root.addWidget(sidebar)

        # ── 分隔线 ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("sidebarSep")
        root.addWidget(sep)

        # ── 主工作区 ──
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")

        self.search_panel = SearchPanel()
        self.search_panel.start_requested.connect(self._on_start)
        self.search_panel.stop_requested.connect(self._on_stop)
        self.stack.addWidget(self.search_panel)

        self.script_panel = ScriptPanel(self.task_store, self.settings)
        self.stack.addWidget(self.script_panel)

        from app.widgets.video_analysis_panel import VideoAnalysisPanel
        self.video_analysis_panel = VideoAnalysisPanel(self.task_store, self.settings)
        self.stack.addWidget(self.video_analysis_panel)

        self.progress_panel = ProgressPanel()
        self.stack.addWidget(self.progress_panel)

        self.results_panel = ResultsPanel(self.task_store)
        self.stack.addWidget(self.results_panel)

        self.settings_page = SettingsPage(self.settings)
        self.settings_page.ready_changed.connect(self._on_env_ready)
        self.settings_page.cookie_saved.connect(self._on_cookie_saved)
        self.settings_page.cdp_tab.settings_changed.connect(self._on_settings_changed)
        self.stack.addWidget(self.settings_page)

        root.addWidget(self.stack, 1)

        # 默认选中搜索页
        self._switch_page(0)

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_group):
            btn.setChecked(i == index)
        # 切换到对应页面时刷新数据
        if index == 1:   # 剧本生成
            self.script_panel._refresh_tasks()
        elif index == 4: # 结果查看
            self.results_panel._refresh_tasks()

    def _on_env_ready(self, ready: bool):
        """环境就绪状态变化时更新 UI"""
        self.search_panel.start_btn.setEnabled(ready)
        if ready:
            self.cdp_label.setText(f"CDP: {self.settings.get('cdp_url','--')} ●")
            self.cdp_label.setStyleSheet("color: #2ed573; font-size: 11px;")
        else:
            self.cdp_label.setText("CDP: 未连接 ●")
            self.cdp_label.setStyleSheet("color: #f85149; font-size: 11px;")

    def _on_cookie_saved(self, path: str):
        """Cookie 保存后更新设置"""
        self.settings["cookie_file"] = path
        self._save_settings()

    def _on_settings_changed(self):
        """设置变更后重建存储"""
        self._save_settings()
        self.settings_page.env_tab.check_all()  # 刷新环境检查
        storage = self.settings.get("storage_path", "")
        self.task_store = TaskStore(storage if storage else None)
        # 更新结果面板的 store 引用
        self.results_panel._task_store = self.task_store
        self.script_panel.set_task_store(self.task_store)
        self.script_panel.set_settings(self.settings)

    def _init_menu(self):
        menubar = self.menuBar()
        menubar.setObjectName("appMenuBar")

        # 文件
        file_menu = menubar.addMenu("文件")
        act_open = QAction("打开结果文件...", self)
        act_open.triggered.connect(self._open_result_file)
        file_menu.addAction(act_open)
        act_export = QAction("导出当前结果...", self)
        act_export.triggered.connect(self._export_results)
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        act_quit = QAction("退出", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # 设置
        settings_menu = menubar.addMenu("设置")
        act_settings = QAction("打开设置页面...", self)
        act_settings.triggered.connect(lambda: self._switch_page(5))
        settings_menu.addAction(act_settings)

        # 关于
        about_menu = menubar.addMenu("关于")
        act_about = QAction("关于 Data Scraper Pro", self)
        act_about.triggered.connect(self._show_about)
        about_menu.addAction(act_about)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("appStatusBar")
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusText")
        self.status_bar.addWidget(self.status_label)

        self.cdp_label = QLabel("CDP: --")
        self.cdp_label.setObjectName("statusInfo")
        self.status_bar.addPermanentWidget(self.cdp_label)

    # ══════════════════════════════════════════
    #  设置
    # ══════════════════════════════════════════

    def _load_settings(self) -> dict:
        defaults = {
            "cdp_url": "http://127.0.0.1:9222",
            "cookie_file": os.path.join(os.path.expanduser("~"), ".dy", "cookies", "default.json"),
            "use_cdp": True,
            "openai_api_base": "https://api.deepseek.com/v1",
            "openai_api_key": "",
            "openai_model": "deepseek-chat",
            "openai_text_api_base": "https://api.deepseek.com/v1",
            "openai_text_api_key": "",
            "openai_text_model": "deepseek-chat",
            "video_api_key": "",
            "openai_image_api_base": "https://api.siliconflow.cn/v1",
            "openai_image_api_key": "",
            "openai_image_model": "Kwai-Kolors/Kolors",
            "openai_video_api_base": "https://api.siliconflow.cn/v1",
            "openai_video_api_key": "",
            "openai_video_model": "Wan-AI/Wan2.2-I2V-A14B",
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE) as f:
                    defaults.update(json.load(f))
        except Exception:
            pass
        return defaults

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.get_settings()
            self._save_settings()
            self.cdp_label.setText(f"CDP: {self.settings.get('cdp_url','--')}")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 数据采集助手",
            "<h3>数据采集助手 v2.0</h3>"
            "<p>基于 PyQt6 + Playwright 的数据采集桌面应用。</p>"
            "<p>零 class 依赖 · 纯文本 DOM 定位 · 防反爬</p>"
        )

    # ══════════════════════════════════════════
    #  文件操作
    # ══════════════════════════════════════════

    def _open_result_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "打开结果文件", str(APP_DIR), "JSON (*.json)")
        if path:
            self.results_panel.load_file(path)
            self._switch_page(4)    # 跳转到结果查看

    def _export_results(self):
        if self.results_panel.is_empty():
            QMessageBox.information(self, "提示", "当前没有可导出的数据。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", str(APP_DIR), "JSON (*.json)")
        if path:
            self.results_panel.export_to(path)

    # ══════════════════════════════════════════
    #  采集控制
    # ══════════════════════════════════════════

    def _on_start(self, params: dict):
        if not self.settings_page.is_ready():
            QMessageBox.warning(self, "环境未就绪", "请先在「环境检查」页面确认 Chrome 和 CDP 已连接。")
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "提示", "采集任务正在进行中。")
            return

        self._switch_page(3)    # 跳转到运行日志
        self.progress_panel.clear()
        self.status_label.setText("● 运行中")
        self.status_label.setStyleSheet(f"color: {NEON_GREEN};")
        self.cdp_label.setText(f"CDP: {self.settings.get('cdp_url','--')}")
        self.search_panel.set_running(True)

        # 创建任务记录
        task_id = self.task_store.create_task(
            search_term=params["search_text"],
            notes=params.get("notes", ""),
            match_keywords=params.get("match_keywords"),
        )
        self.progress_panel.log(f"📋 任务 ID: {task_id}", "INFO")
        self.progress_panel.log(f"📋 采集平台: {params.get('platform', '抖音')}", "INFO")

        self.worker = DataWorker(
            task_id=task_id,
            task_store=self.task_store,
            platform=params.get("platform", "抖音"),
            search_text=params["search_text"],
            match_keywords=params.get("match_keywords"),
            video_count=params.get("video_count", 5),
            max_scrolls=params.get("max_scrolls", 50),
            sort_by=params.get("sort_by", "最新发布"),
            time_filter=params.get("time_filter"),
            cdp_url=self.settings.get("cdp_url", "http://127.0.0.1:9222"),
            cookie_file=self.settings.get("cookie_file"),
            use_cdp=self.settings.get("use_cdp", True),
            dm_message=params.get("dm_message"),
        )
        self.worker.log_signal.connect(self.progress_panel.log)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.terminate()
            self.worker.wait(2000)
            self.progress_panel.log("⏹ 用户手动中止采集", "WARN")
            self._reset_ui()

    def _on_finished(self, result_file: str):
        self._reset_ui()
        self.status_label.setText("● 完成")
        self.status_label.setStyleSheet(f"color: {NEON_GREEN};")
        self.progress_panel.log(f"✅ 采集完成！结果已保存: {os.path.basename(result_file)}", "SUCCESS")
        self.results_panel.load_file(result_file)
        self.results_panel._refresh_tasks()
        self.script_panel._refresh_tasks()

    def _on_error(self, message: str):
        self._reset_ui()
        self.status_label.setText("● 出错")
        self.status_label.setStyleSheet(f"color: {NEON_RED};")
        self.progress_panel.log(f"❌ {message}", "ERROR")
        QMessageBox.critical(self, "采集错误", message)

    def _reset_ui(self):
        self.search_panel.set_running(False)
        self.status_label.setStyleSheet("color: #888;")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出", "采集任务正在进行中，确定退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    QLocale.setDefault(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_THEME)

    window = MainWindow()
    window.show()

    # 更新 CDP 状态
    cdp = window.settings.get("cdp_url", "--")
    window.cdp_label.setText(f"CDP: {cdp}")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
