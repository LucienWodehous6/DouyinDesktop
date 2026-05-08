"""抖音工具面板 — 集成 dy-cli 功能"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import pyqtSignal

from app.widgets.dy_tools.api_search_tab import ApiSearchTab
from app.widgets.dy_tools.trending_tab import TrendingTab
from app.widgets.dy_tools.interaction_tab import InteractionTab
from app.widgets.dy_tools.aigc_tab import AigcTab
from app.widgets.dy_tools.account_tab import AccountTab


class DyToolsPanel(QWidget):
    """抖音工具主面板 — 包含 5 个子标签"""

    log_signal = pyqtSignal(str, str)  # 转发日志到 ProgressPanel
    result_signal = pyqtSignal(str, dict)  # 结果信号 (result_type, data)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🛠 抖音工具")
        title.setObjectName("pageTitle")
        title.setContentsMargins(28, 20, 0, 8)
        layout.addWidget(title)

        tabs = QTabWidget()

        self.api_search_tab = ApiSearchTab(self._task_store, self._settings)
        self.api_search_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.api_search_tab, "API搜索")

        self.trending_tab = TrendingTab(self._task_store, self._settings)
        self.trending_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.trending_tab, "热榜直播")

        self.interaction_tab = InteractionTab(self._task_store, self._settings)
        self.interaction_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.interaction_tab, "互动操作")

        self.aigc_tab = AigcTab(self._task_store, self._settings)
        self.aigc_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.aigc_tab, "AIGC生成")

        from app.widgets.dy_tools.skill_executor_tab import SkillExecutorTab
        self.skill_executor_tab = SkillExecutorTab(self._task_store, self._settings)
        self.skill_executor_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.skill_executor_tab, "⚡ Skills")

        self.account_tab = AccountTab(self._task_store, self._settings)
        self.account_tab.log_signal.connect(self.log_signal.emit)
        tabs.addTab(self.account_tab, "账号管理")

        layout.addWidget(tabs)

    def set_settings(self, settings: dict):
        self._settings = settings
        self.api_search_tab.set_settings(settings)
        self.trending_tab.set_settings(settings)
        self.interaction_tab.set_settings(settings)
        self.aigc_tab.set_settings(settings)
        self.skill_executor_tab.set_settings(settings)
        self.account_tab.set_settings(settings)