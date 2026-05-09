# 抖音投流工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在项目中集成抖音投流工具，支持巨量千川和抖音 DO+ 两个平台的自动投放管理和数据监控。

**Architecture:** 基于现有 Playwright CDP 浏览器自动化能力，新增投流模块 `app/widgets/ads/`。统一入口面板，按平台拆分为两个子模块。

---

## Task 1: 创建投流主面板 AdsPanel

**Files:**
- Create: `app/widgets/ads_panel.py`

- [ ] **Step 1: 创建 AdsPanel 类**

```python
"""投流主面板 — 巨量千川 + 抖音 DO+ 统一入口"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame, QProgressBar, QTextEdit, QComboBox,
)
from PyQt6.QtCore import Qt
from app.widgets.ads.juliang.juliang_panel import JuliangPanel
from app.widgets.ads.douyin_plus.douyin_plus_panel import DouyinPlusPanel


class AdsPanel(QWidget):
    """投流统一入口页面"""

    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QFrame()
        header.setObjectName("pageHeader")
        header.setMinimumHeight(60)
        header_layout = QHBoxLayout(header)

        title = QLabel("📊 投流管理")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addWidget(header)

        # Tab 页：巨量千川 | 抖音 DO+
        self.tabs = QTabWidget()
        self.tabs.addTab(JuliangPanel(self._settings), "巨量千川")
        self.tabs.addTab(DouyinPlusPanel(self._settings), "抖音 DO+")

        layout.addWidget(self.tabs)
```

- [ ] **Step 2: 提交**

```bash
git add app/widgets/ads_panel.py
git commit -m "feat(ads): add AdsPanel as unified ads management entry"
```

---

## Task 2: 创建巨量千川模块

**Files:**
- Create: `app/widgets/ads/juliang/__init__.py`
- Create: `app/widgets/ads/juliang/browser_ops.py`
- Create: `app/widgets/ads/juliang/plan_manager.py`
- Create: `app/widgets/ads/juliang/monitor.py`
- Create: `app/widgets/ads/juliang/juliang_panel.py`

- [ ] **Step 1: 创建目录结构和基础文件**

`app/widgets/ads/juliang/__init__.py`:
```python
"""巨量千川投流模块"""
```

`app/widgets/ads/juliang/browser_ops.py` — 浏览器操作：
```python
"""巨量千川浏览器自动化操作"""
import time
from typing import Optional


class JuliangBrowserOps:
    """巨量千川浏览器操作类"""

    def __init__(self, page, cdp_url: str):
        self.page = page
        self.cdp_url = cdp_url

    def login_if_needed(self) -> bool:
        """检查登录状态，必要时引导登录"""
        # 检查是否需要登录
        pass

    def navigate_to_live_heating(self):
        """导航到直播加热页面"""
        # 进入品牌投放 > 品牌竞价 > 直播加热
        pass

    def create_plan(self, plan_config: dict) -> dict:
        """创建投放计划"""
        # 填写定向、预算、出价等
        pass

    def get_plan_list(self) -> list:
        """获取计划列表"""
        pass

    def pause_plan(self, plan_id: str):
        """暂停计划"""
        pass

    def resume_plan(self, plan_id: str):
        """恢复计划"""
        pass

    def adjust_bid(self, plan_id: str, new_bid: float):
        """调整出价"""
        pass

    def delete_plan(self, plan_id: str):
        """删除计划"""
        pass
```

`app/widgets/ads/juliang/plan_manager.py` — 计划管理：
```python
"""巨量千川计划管理器"""
import json
import os
from datetime import datetime


class PlanManager:
    """管理巨量千川广告计划"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.expanduser("~/.dy/ads/juliang")

    def save_plan(self, plan: dict):
        """保存计划到本地"""
        pass

    def load_plans(self) -> list:
        """加载所有计划"""
        pass

    def update_plan_status(self, plan_id: str, status: str):
        """更新计划状态"""
        pass

    def check_duplicate(self, behavior: str, interest: str) -> bool:
        """检查计划是否重复（行为+兴趣组合）"""
        pass
```

`app/widgets/ads/juliang/monitor.py` — 数据监控：
```python
"""巨量千川数据监控"""
import time
from datetime import datetime


class JuliangMonitor:
    """监控广告数据并自动调价"""

    def __init__(self, browser_ops, plan_manager):
        self.browser_ops = browser_ops
        self.plan_manager = plan_manager

    def start_monitoring(self, interval: int = 900):
        """开始监控（默认15分钟间隔）"""
        pass

    def get_plan_metrics(self, plan_id: str) -> dict:
        """获取计划指标（播放、转化、ROI等）"""
        pass

    def auto_adjust_bid(self, plan_id: str, target_roi: float):
        """根据 ROI 自动调价"""
        pass

    def stop_monitoring(self):
        """停止监控"""
        pass
```

`app/widgets/ads/juliang/juliang_panel.py` — 面板 UI：
```python
"""巨量千川面板 UI"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QLabel, QComboBox, QLineEdit,
)
from PyQt6.QtCore import Qt


class JuliangPanel(QWidget):
    """巨量千川投放管理面板"""

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 控制栏
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新计划")
        self.create_btn = QPushButton("创建计划")
        self.monitor_btn = QPushButton("开始监控")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.create_btn)
        controls.addWidget(self.monitor_btn)
        layout.addLayout(controls)

        # 计划列表
        self.plan_table = QTableWidget()
        self.plan_table.setColumnHeaders(["计划名", "状态", "出价", "消耗", "ROI"])
        layout.addWidget(self.plan_table)
```

- [ ] **Step 2: 提交**

```bash
git add app/widgets/ads/
git commit -m "feat(ads): add Juliang module for oceanengine ads automation"
```

---

## Task 3: 创建抖音 DO+ 模块

**Files:**
- Create: `app/widgets/ads/douyin_plus/__init__.py`
- Create: `app/widgets/ads/douyin_plus/browser_ops.py`
- Create: `app/widgets/ads/douyin_plus/plan_manager.py`
- Create: `app/widgets/ads/douyin_plus/douyin_plus_panel.py`

- [ ] **Step 1: 创建目录结构和基础文件**

结构与巨量千川类似，但针对抖音 DO+ 平台特点：
- 内容加热（提升播放量/互动）
- DO+ 计划管理
- 数据监控

`app/widgets/ads/douyin_plus/browser_ops.py`:
```python
"""抖音 DO+ 浏览器自动化操作"""


class DouyinPlusBrowserOps:
    """抖音 DO+ 浏览器操作类"""

    def __init__(self, page, cdp_url: str):
        self.page = page
        self.cdp_url = cdp_url

    def navigate_to_douyin_plus(self):
        """导航到 DO+ 推广页面"""
        pass

    def create_content_heating(self, video_id: str, budget: float, duration: int):
        """创建内容加热"""
        pass

    def get_campaign_list(self) -> list:
        """获取推广计划列表"""
        pass

    def pause_campaign(self, campaign_id: str):
        """暂停推广"""
        pass

    def get_metrics(self, campaign_id: str) -> dict:
        """获取推广数据"""
        pass
```

- [ ] **Step 2: 提交**

```bash
git add app/widgets/ads/douyin_plus/
git commit -m "feat(ads): add DouyinPlus module for DO+ content heating"
```

---

## Task 4: 集成到主窗口导航

**Files:**
- Modify: `app/main_window.py`

- [ ] **Step 1: 添加导航项和页面**

在 nav_items 中添加投流入口：
```python
("📊", "投流管理"),
```

在 _init_ui 中添加 AdsPanel：
```python
from app.widgets.ads_panel import AdsPanel
self.ads_panel = AdsPanel(self.task_store, self.settings)
self.stack.addWidget(self.ads_panel)
```

- [ ] **Step 2: 提交**

```bash
git add app/main_window.py
git commit -m "feat(ads): integrate AdsPanel into main window navigation"
```

---

## Self-Review

1. **Spec coverage:** 两个平台（巨量千川、抖音 DO+）都有对应模块
2. **Placeholder scan:** 关键函数已有框架，具体实现待填充
3. **Type consistency:** 模块结构统一，便于扩展

---

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-05-09-ads-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?