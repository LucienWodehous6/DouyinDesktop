"""巨量千川面板 UI"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QLabel, QHeaderView, QAbstractItemView,
    QMessageBox, QInputDialog, QLineEdit, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import threading


class JuliangWorker(QThread):
    """后台线程执行巨量千川操作"""
    log_signal = pyqtSignal(str, str)
    plans_loaded = pyqtSignal(list)
    plan_created = pyqtSignal(bool, str)

    def __init__(self, cdp_url: str, parent=None):
        super().__init__(parent)
        self.cdp_url = cdp_url
        self._ops = None

    def run(self):
        from app.widgets.ads.juliang.browser_ops import JuliangBrowserOps
        self._ops = JuliangBrowserOps(self.cdp_url)

        if not self._ops.connect():
            self.log_signal.emit("连接浏览器失败", "ERROR")
            return

        self.log_signal.emit("已连接到巨量千川浏览器", "INFO")

        # 导航到直播加热页面
        if not self._ops.navigate_to_live_heating():
            self.log_signal.emit("导航到直播加热页面失败", "ERROR")
            return

        self.log_signal.emit("正在获取计划列表...", "INFO")
        plans = self._ops.get_plan_list()
        self.plans_loaded.emit(plans)

    def create_plan(self, config: dict):
        if self._ops:
            result = self._ops.create_plan(config)
            self.plan_created.emit(result["success"], result.get("message", ""))


class JuliangPanel(QWidget):
    """巨量千川投放管理面板"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("巨量千川 — 品牌竞价直播加热")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # CDP URL 配置
        cdp_layout = QHBoxLayout()
        cdp_layout.addWidget(QLabel("CDP:"))
        self.cdp_combo = QComboBox()
        self.cdp_combo.setEditable(True)
        self.cdp_combo.addItems([
            self._settings.get("cdp_url", "http://127.0.0.1:9222"),
            "http://127.0.0.1:9222",
            "http://localhost:9222",
        ])
        cdp_layout.addWidget(self.cdp_combo, 1)
        layout.addLayout(cdp_layout)

        # 控制栏
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 刷新计划")
        self.create_btn = QPushButton("➕ 创建计划")
        self.monitor_btn = QPushButton("📊 开始监控")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.create_btn)
        controls.addWidget(self.monitor_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # 连接按钮信号
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.create_btn.clicked.connect(self._on_create)
        self.monitor_btn.clicked.connect(self._on_monitor)

        # 计划列表
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(7)
        self.plan_table.setHorizontalHeaderLabels(["ID", "计划名", "状态", "出价", "消耗", "播放", "操作"])
        self.plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plan_table.setMinimumHeight(300)
        layout.addWidget(self.plan_table)

        # 状态栏
        self.status_label = QLabel("未连接")
        layout.addWidget(self.status_label)

        self._worker = None

    def _get_cdp_url(self) -> str:
        return self.cdp_combo.currentText().strip() or "http://127.0.0.1:9222"

    def _on_refresh(self):
        """刷新计划列表"""
        self.status_label.setText("正在刷新...")
        self.refresh_btn.setEnabled(False)

        cdp_url = self._get_cdp_url()
        self._worker = JuliangWorker(cdp_url)
        self._worker.log_signal.connect(self._update_status)
        self._worker.plans_loaded.connect(self._display_plans)
        self._worker.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._worker.start()

    def _update_status(self, msg: str, level: str = "INFO"):
        self.status_label.setText(msg)

    def _display_plans(self, plans: list):
        """显示计划列表"""
        self.plan_table.setRowCount(0)
        for plan in plans:
            row = self.plan_table.rowCount()
            self.plan_table.insertRow(row)
            self.plan_table.setItem(row, 0, QTableWidgetItem(plan.get("id", "")))
            self.plan_table.setItem(row, 1, QTableWidgetItem(plan.get("name", "")))
            self.plan_table.setItem(row, 2, QTableWidgetItem(plan.get("status", "")))
            self.plan_table.setItem(row, 3, QTableWidgetItem(plan.get("bid", "")))
            self.plan_table.setItem(row, 4, QTableWidgetItem(plan.get("spend", "")))
            self.plan_table.setItem(row, 5, QTableWidgetItem(plan.get("plays", "")))

            # 操作按钮
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(2, 2, 2, 2)

            pause_btn = QPushButton("暂停")
            pause_btn.setFixedWidth(60)
            plan_id = plan.get("id", "")

            def make_pause_handler(pid):
                return lambda: self._pause_plan(pid)
            pause_btn.clicked.connect(make_pause_handler(plan_id))

            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(60)

            def make_delete_handler(pid):
                return lambda: self._delete_plan(pid)
            delete_btn.clicked.connect(make_delete_handler(plan_id))

            ops_layout.addWidget(pause_btn)
            ops_layout.addWidget(delete_btn)
            self.plan_table.setCellWidget(row, 6, ops_widget)

        self.status_label.setText(f"已加载 {len(plans)} 个计划")

    def _on_create(self):
        """创建新计划"""
        dialog = CreatePlanDialog(self._get_cdp_url(), self)
        dialog.exec()

    def _on_monitor(self):
        """开始监控"""
        from app.widgets.ads.juliang.monitor import JuliangMonitor
        self.status_label.setText("监控功能开发中")
        QMessageBox.information(self, "提示", "监控功能正在开发...")

    def _pause_plan(self, plan_id: str):
        """暂停计划"""
        self.status_label.setText(f"正在暂停计划 {plan_id}...")
        # TODO: 实现暂停逻辑

    def _delete_plan(self, plan_id: str):
        """删除计划"""
        reply = QMessageBox.question(self, "确认", f"确定删除计划 {plan_id}？")
        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText(f"正在删除计划 {plan_id}...")
            # TODO: 实现删除逻辑

    def load_plans(self):
        """加载计划列表"""
        self._on_refresh()


class CreatePlanDialog(QInputDialog):
    """创建计划对话框"""

    def __init__(self, cdp_url: str, parent=None):
        super().__init__(parent)
        self.cdp_url = cdp_url
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("创建巨量千川计划")
        self.setLabelText("请输入计划配置（JSON）:")
        self.setTextValue('{"behavior": "美妆", "interest": "护肤", "bid": "0.22", "budget": "100"}')
        self.setOkButtonText("创建")

    def done(self, result):
        if result:
            config_text = self.textValue()
            try:
                import json
                config = json.loads(config_text)
                self._create_plan(config)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "错误", f"JSON 格式错误: {e}")

    def _create_plan(self, config: dict):
        from app.widgets.ads.juliang.browser_ops import JuliangBrowserOps
        ops = JuliangBrowserOps(self.cdp_url)
        if not ops.connect():
            QMessageBox.warning(self, "错误", "连接浏览器失败")
            return

        ops.navigate_to_live_heating()
        result = ops.create_plan(config)
        ops.disconnect()

        if result["success"]:
            QMessageBox.information(self, "成功", f"计划创建成功: {result.get('plan_id', '')}")
        else:
            QMessageBox.warning(self, "失败", result.get("message", "创建失败"))