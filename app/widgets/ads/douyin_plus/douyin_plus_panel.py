"""抖音 DO+ 面板 UI"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QLabel, QHeaderView, QAbstractItemView,
    QMessageBox, QInputDialog, QLineEdit, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class DouyinPlusWorker(QThread):
    """后台线程执行抖音 DO+ 操作"""
    log_signal = pyqtSignal(str, str)
    campaigns_loaded = pyqtSignal(list)
    campaign_created = pyqtSignal(bool, str)

    def __init__(self, cdp_url: str, parent=None):
        super().__init__(parent)
        self.cdp_url = cdp_url
        self._ops = None

    def run(self):
        from app.widgets.ads.douyin_plus.browser_ops import DouyinPlusBrowserOps
        self._ops = DouyinPlusBrowserOps(self.cdp_url)

        if not self._ops.connect():
            self.log_signal.emit("连接浏览器失败", "ERROR")
            return

        self.log_signal.emit("已连接到抖音 DO+ 浏览器", "INFO")

        # 导航到推广列表页面
        if not self._ops.navigate_to_promote_list():
            self.log_signal.emit("导航到推广列表页面失败", "ERROR")
            return

        self.log_signal.emit("正在获取推广列表...", "INFO")
        campaigns = self._ops.get_campaign_list()
        self.campaigns_loaded.emit(campaigns)

    def create_campaign(self, video_id: str, config: dict):
        if self._ops:
            result = self._ops.create_content_heating(video_id, config)
            self.campaign_created.emit(result["success"], result.get("message", ""))


class DouyinPlusPanel(QWidget):
    """抖音 DO+ 投放管理面板"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("抖音 DO+ — 内容加热推广")
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
        self.refresh_btn = QPushButton("🔄 刷新推广")
        self.create_btn = QPushButton("➕ 创建推广")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.create_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # 连接按钮信号
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.create_btn.clicked.connect(self._on_create)

        # 推广列表
        self.campaign_table = QTableWidget()
        self.campaign_table.setColumnCount(7)
        self.campaign_table.setHorizontalHeaderLabels(["ID", "推广名", "状态", "预算", "播放", "互动", "操作"])
        self.campaign_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.campaign_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.campaign_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.campaign_table.setMinimumHeight(300)
        layout.addWidget(self.campaign_table)

        # 状态栏
        self.status_label = QLabel("未连接")
        layout.addWidget(self.status_label)

        self._worker = None

    def _get_cdp_url(self) -> str:
        return self.cdp_combo.currentText().strip() or "http://127.0.0.1:9222"

    def _on_refresh(self):
        """刷新推广列表"""
        self.status_label.setText("正在刷新...")
        self.refresh_btn.setEnabled(False)

        cdp_url = self._get_cdp_url()
        self._worker = DouyinPlusWorker(cdp_url)
        self._worker.log_signal.connect(self._update_status)
        self._worker.campaigns_loaded.connect(self._display_campaigns)
        self._worker.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._worker.start()

    def _update_status(self, msg: str, level: str = "INFO"):
        self.status_label.setText(msg)

    def _display_campaigns(self, campaigns: list):
        """显示推广列表"""
        self.campaign_table.setRowCount(0)
        for campaign in campaigns:
            row = self.campaign_table.rowCount()
            self.campaign_table.insertRow(row)
            self.campaign_table.setItem(row, 0, QTableWidgetItem(campaign.get("id", "")))
            self.campaign_table.setItem(row, 1, QTableWidgetItem(campaign.get("name", "")))
            self.campaign_table.setItem(row, 2, QTableWidgetItem(campaign.get("status", "")))
            self.campaign_table.setItem(row, 3, QTableWidgetItem(campaign.get("budget", "")))
            self.campaign_table.setItem(row, 4, QTableWidgetItem(campaign.get("plays", "")))
            self.campaign_table.setItem(row, 5, QTableWidgetItem(campaign.get("interactions", "")))

            # 操作按钮
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(2, 2, 2, 2)

            pause_btn = QPushButton("暂停")
            pause_btn.setFixedWidth(60)
            campaign_id = campaign.get("id", "")

            def make_pause_handler(cid):
                return lambda: self._pause_campaign(cid)
            pause_btn.clicked.connect(make_pause_handler(campaign_id))

            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(60)

            def make_delete_handler(cid):
                return lambda: self._delete_campaign(cid)
            delete_btn.clicked.connect(make_delete_handler(campaign_id))

            ops_layout.addWidget(pause_btn)
            ops_layout.addWidget(delete_btn)
            self.campaign_table.setCellWidget(row, 6, ops_widget)

        self.status_label.setText(f"已加载 {len(campaigns)} 个推广")

    def _on_create(self):
        """创建新推广"""
        dialog = CreateCampaignDialog(self._get_cdp_url(), self)
        dialog.exec()

    def _pause_campaign(self, campaign_id: str):
        """暂停推广"""
        self.status_label.setText(f"正在暂停推广 {campaign_id}...")
        # TODO: 实现暂停逻辑

    def _delete_campaign(self, campaign_id: str):
        """删除推广"""
        reply = QMessageBox.question(self, "确认", f"确定删除推广 {campaign_id}？")
        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText(f"正在删除推广 {campaign_id}...")
            # TODO: 实现删除逻辑

    def load_campaigns(self):
        """加载推广列表"""
        self._on_refresh()


class CreateCampaignDialog(QInputDialog):
    """创建推广对话框"""

    def __init__(self, cdp_url: str, parent=None):
        super().__init__(parent)
        self.cdp_url = cdp_url
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("创建抖音 DO+ 推广")
        self.setLabelText("请输入视频 ID 和配置（JSON）:")
        self.setTextValue('{"video_id": "123456789", "budget": "100", "duration": 7}')
        self.setOkButtonText("创建")

    def done(self, result):
        if result:
            config_text = self.textValue()
            try:
                import json
                config = json.loads(config_text)
                video_id = config.pop("video_id", "")
                self._create_campaign(video_id, config)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "错误", f"JSON 格式错误: {e}")

    def _create_campaign(self, video_id: str, config: dict):
        from app.widgets.ads.douyin_plus.browser_ops import DouyinPlusBrowserOps
        ops = DouyinPlusBrowserOps(self.cdp_url)
        if not ops.connect():
            QMessageBox.warning(self, "错误", "连接浏览器失败")
            return

        ops.navigate_to_home()
        result = ops.create_content_heating(video_id, config)
        ops.disconnect()

        if result["success"]:
            QMessageBox.information(self, "成功", f"推广创建成功: {result.get('campaign_id', '')}")
        else:
            QMessageBox.warning(self, "失败", result.get("message", "创建失败"))