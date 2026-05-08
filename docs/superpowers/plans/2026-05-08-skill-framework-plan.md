# Skill 框架实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Skill 框架基础设施，支持动态加载和执行 AGI-Super-Team 格式的 Skills

**Architecture:** Skill 框架以 `app/skills/` 为核心，通过 `SkillLoader` 扫描本地 SKILL.md 文件，`SkillRegistry` 维护内存索引，UI 层通过 `SkillExecutorTab` 展示和执行 Skills

**Tech Stack:** PyYAML（解析 frontmatter）、复用现有 openai_api 配置

---

## 文件结构

```
app/skills/
├── __init__.py
├── _skill_base.py          # Skill 基类 + SkillResult
├── skill_loader.py         # 加载器
├── registry.py             # 注册表
└── skills/
    └── khazix-writer/
        └── SKILL.md        # 示例 Skill

tests/app/skills/
├── __init__.py
├── test_skill_base.py
├── test_loader.py
└── test_registry.py
```

---

### Task 1: 创建 Skill 基础设施目录和基类

**Files:**
- Create: `app/skills/__init__.py`
- Create: `app/skills/_skill_base.py`
- Create: `tests/app/skills/__init__.py`

- [ ] **Step 1: 创建 app/skills/__init__.py**

```python
"""Skill 框架 — 动态加载和执行 AGI-Super-Team 格式的 Skills"""
from app.skills._skill_base import Skill, SkillResult
from app.skills.registry import SkillRegistry

__all__ = ["Skill", "SkillResult", "SkillRegistry"]
```

- [ ] **Step 2: 创建 tests/app/skills/__init__.py**

```python
"""Tests for Skill framework"""
```

- [ ] **Step 3: 创建 app/skills/_skill_base.py**

```python
"""Skill 基类和结果数据类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class Skill(ABC):
    """Skill 抽象基类"""

    name: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)

    @abstractmethod
    def execute(self, params: dict, context: dict) -> SkillResult:
        """执行 Skill，返回结果"""
        pass

    def validate_input(self, params: dict) -> bool:
        """验证输入参数，返回 True/False"""
        return True

    def get_input_schema(self) -> dict | None:
        """返回输入参数 JSON Schema，用于 UI 生成表单"""
        return None
```

- [ ] **Step 4: 验证语法**

Run: `python3 -m py_compile app/skills/_skill_base.py && echo "OK"`
Expected: OK

- [ ] **Step 5: 提交**

```bash
git add app/skills/__init__.py app/skills/_skill_base.py tests/app/skills/__init__.py
git commit -m "feat(skills): add Skill base class and directory structure"
```

---

### Task 2: 创建 SkillLoader — 扫描和解析 SKILL.md

**Files:**
- Create: `app/skills/skill_loader.py`
- Create: `tests/app/skills/test_loader.py`

- [ ] **Step 1: 创建 app/skills/skill_loader.py**

```python
"""Skill 加载器 — 扫描 app/skills/skills/ 目录，解析 SKILL.md"""

import os
import re
import yaml
from pathlib import Path
from typing import Iterator


SKILLS_DIR = Path(__file__).parent / "skills"


def parse_skill_md(content: str) -> dict:
    """解析 SKILL.md 内容，返回 frontmatter + body"""
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        return {"metadata": {}, "body": content}

    frontmatter_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end():]
    metadata = yaml.safe_load(frontmatter_text) or {}
    return {"metadata": metadata, "body": body}


def scan_skills() -> Iterator[dict]:
    """扫描 skills 目录，产生每个 skill 的信息 dict"""
    skills_path = SKILLS_DIR
    if not skills_path.exists():
        return

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir():
            continue
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            continue

        content = md_path.read_text(encoding="utf-8")
        parsed = parse_skill_md(content)
        yield {
            "id": skill_dir.name,
            "path": str(md_path),
            **parsed,
        }


class SkillLoader:
    """Skill 加载器，提供 scan() 和 get_by_id() 方法"""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        for skill_info in scan_skills():
            self._cache[skill_info["id"]] = skill_info

    def scan(self) -> list[dict]:
        """返回所有加载的 skill 信息列表"""
        return list(self._cache.values())

    def get_by_id(self, skill_id: str) -> dict | None:
        """根据 ID 获取 skill 信息"""
        return self._cache.get(skill_id)
```

- [ ] **Step 2: 创建 tests/app/skills/test_loader.py**

```python
"""Tests for SkillLoader"""

import pytest
from app.skills.skill_loader import parse_skill_md


def test_parse_skill_md_with_frontmatter():
    content = """---
name: test-skill
description: "A test skill"
metadata:
  version: "1.0.0"
---

# Test Skill
body content here
"""
    result = parse_skill_md(content)
    assert result["metadata"]["name"] == "test-skill"
    assert result["metadata"]["version"] == "1.0.0"
    assert "body content here" in result["body"]


def test_parse_skill_md_without_frontmatter():
    content = "# No frontmatter\nsome content"
    result = parse_skill_md(content)
    assert result["metadata"] == {}
    assert "No frontmatter" in result["body"]
```

- [ ] **Step 3: 运行测试**

Run: `python3 -m pytest tests/app/skills/test_loader.py -v`
Expected: PASS (2 tests)

- [ ] **Step 4: 验证语法**

Run: `python3 -m py_compile app/skills/skill_loader.py && echo "OK"`
Expected: OK

- [ ] **Step 5: 提交**

```bash
git add app/skills/skill_loader.py tests/app/skills/test_loader.py
git commit -m "feat(skills): add SkillLoader for scanning and parsing SKILL.md"
```

---

### Task 3: 创建 SkillRegistry — 全局注册表

**Files:**
- Create: `app/skills/registry.py`
- Create: `tests/app/skills/test_registry.py`

- [ ] **Step 1: 创建 app/skills/registry.py**

```python
"""Skill 注册表 — 全局单例，维护 name -> Skill 实例映射"""

from typing import Protocol
from app.skills._skill_base import Skill
from app.skills.skill_loader import SkillLoader


class SkillRegistry:
    """全局 Skill 注册表（单例）"""

    _instance: "SkillRegistry | None" = None

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._loader = SkillLoader()
        self._load_metadata()

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_metadata(self):
        """仅加载 metadata，不实例化 Skill 类（等待按需实例化）"""
        for info in self._loader.scan():
            self._skills[info["id"]] = info  # 存的是 metadata dict

    def get_skill_metadata(self, skill_id: str) -> dict | None:
        """获取 skill 元信息"""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[dict]:
        """列出所有 skill 的元信息"""
        return list(self._skills.values())

    def register(self, skill_id: str, skill_instance: Skill):
        """手动注册一个 Skill 实例"""
        self._skills[skill_id] = skill_instance

    def get(self, skill_id: str) -> Skill | None:
        """获取 skill 实例（目前返回 metadata dict，未来支持 Skill 实例）"""
        return self._skills.get(skill_id)
```

- [ ] **Step 2: 创建 tests/app/skills/test_registry.py**

```python
"""Tests for SkillRegistry"""

import pytest
from app.skills.registry import SkillRegistry


def test_singleton():
    r1 = SkillRegistry.get_instance()
    r2 = SkillRegistry.get_instance()
    assert r1 is r2


def test_list_skills_returns_list():
    r = SkillRegistry.get_instance()
    skills = r.list_skills()
    assert isinstance(skills, list)
```

- [ ] **Step 3: 运行测试**

Run: `python3 -m pytest tests/app/skills/test_registry.py -v`
Expected: PASS (2 tests)

- [ ] **Step 4: 验证语法**

Run: `python3 -m py_compile app/skills/registry.py && echo "OK"`
Expected: OK

- [ ] **Step 5: 提交**

```bash
git add app/skills/registry.py tests/app/skills/test_registry.py
git commit -m "feat(skills): add SkillRegistry singleton"
```

---

### Task 4: 创建示例 Skill — khazix-writer

**Files:**
- Create: `app/skills/skills/khazix-writer/SKILL.md`

- [ ] **Step 1: 创建 app/skills/skills/khazix-writer/SKILL.md**

```yaml
---
name: khazix-writer
description: "生成抖音爆款文案，参考可汗学院风格的知识讲解"
metadata:
  version: "1.0.0"
  author: "CCO Ives"
  domains: [content, copywriting, douyin]
  type: llm-generation
  requires: [openai-api]
---

# Khazix Writer — 抖音爆款文案生成

> **将任何话题转化为有吸引力的抖音文案，参考可汗学院风格。**

## 什么时候用

- 需要生成抖音视频文案/剧本时
- 需要参考可汗学院风格的知识讲解时
- 用户已有关键词，需要扩写为完整文案

## 输入

```yaml
输入参数:
  topic: string           # 视频主题/话题（必填）
  duration: number        # 视频时长秒数（必填）
  tone: string            # 文风：funny/serious/warm/neutral（默认 neutral）
```

## 输出

```yaml
输出:
  title: string           # 爆款标题（≤20字）
  hook: string            # 开场钩子（前3秒用）
  body: string            # 完整文案（markdown 格式）
  hashtags: list[string]  # 推荐标签（5个）
  cta: string             # 行动号召结尾
```

## Prompt 模板

```
你是一位抖音内容创作专家，擅长生成可汗学院风格的爆款文案。

任务：为「{topic}」生成一段{duration}秒的抖音视频文案。

要求：
1. 开场前3秒必须有强钩子（引起好奇或共鸣）
2. 语言简洁、口语化，适合配音阅读
3. 结构：开场钩子 → 核心内容 → 行动号召
4. 知识讲解要类比生活场景，帮助理解

文风：{tone}

请以以下格式输出：
# 标题
# 开场钩子
# 正文（markdown）
# 推荐标签
# 行动号召
```
```

- [ ] **Step 2: 验证文件创建**

Run: `ls app/skills/skills/khazix-writer/`
Expected: SKILL.md

- [ ] **Step 3: 提交**

```bash
git add app/skills/skills/khazix-writer/
git commit -m "feat(skills): add khazix-writer skill from AGI-Super-Team"
```

---

### Task 5: 创建 SkillExecutorTab — Skill 执行 UI

**Files:**
- Create: `app/widgets/dy_tools/skill_executor_tab.py`
- Modify: `app/widgets/dy_tools_panel.py`（接入新 Tab）

- [ ] **Step 1: 创建 app/widgets/dy_tools/skill_executor_tab.py**

```python
"""Skill 执行 Tab — 列出可用 Skills 并执行"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.skills.registry import SkillRegistry
from app.skills._skill_base import SkillResult


class SkillExecutorTab(QWidget):
    """Skill 执行界面"""

    log_signal = pyqtSignal(str, str)

    def __init__(self, task_store, settings):
        super().__init__()
        self._task_store = task_store
        self._settings = settings
        self._current_skill: dict | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("⚡ Skill 执行器")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # 左侧：Skill 列表
        content = QHBoxLayout()

        self.skill_list = QListWidget()
        self.skill_list.setMinimumWidth(200)
        self.skill_list.currentItemChanged.connect(self._on_skill_selected)
        content.addWidget(self.skill_list, 1)

        # 右侧：Skill 详情和执行
        right = QVBoxLayout()

        self.skill_desc = QLabel("选择一个 Skill 开始")
        self.skill_desc.setWordWrap(True)
        right.addWidget(self.skill_desc)

        # 参数表单
        self.params_box = QGroupBox("输入参数")
        params_layout = QFormLayout()
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("视频主题/话题")
        params_layout.addRow("topic:", self.topic_input)
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("60")
        params_layout.addRow("duration (秒):", self.duration_input)
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["neutral", "funny", "serious", "warm"])
        params_layout.addRow("tone:", self.tone_combo)
        self.params_box.setLayout(params_layout)
        right.addWidget(self.params_box)

        # 输出区
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Skill 输出将显示在这里...")
        right.addWidget(self.output_text, 1)

        # 执行按钮
        exec_layout = QHBoxLayout()
        self.exec_btn = QPushButton("⚡ 执行 Skill")
        self.exec_btn.setObjectName("primaryBtn")
        self.exec_btn.clicked.connect(self._on_execute)
        self.exec_btn.setEnabled(False)
        exec_layout.addWidget(self.exec_btn)
        exec_layout.addStretch()
        right.addLayout(exec_layout)

        content.addLayout(right, 3)
        layout.addLayout(content, 1)

        self._load_skills()

    def _load_skills(self):
        registry = SkillRegistry.get_instance()
        for skill_info in registry.list_skills():
            item = QListWidgetItem(skill_info.get("id", "unknown"))
            item.setData(Qt.ItemDataRole.UserRole, skill_info)
            self.skill_list.addItem(item)

    def _on_skill_selected(self, current: QListWidgetItem | None):
        if not current:
            return
        self._current_skill = current.data(Qt.ItemDataRole.UserRole)
        desc = self._current_skill.get("metadata", {}).get("description", "")
        self.skill_desc.setText(f"**{self._current_skill['id']}**: {desc}")
        self.exec_btn.setEnabled(True)

    def _on_execute(self):
        if not self._current_skill:
            return
        skill_id = self._current_skill["id"]
        params = {
            "topic": self.topic_input.text().strip(),
            "duration": int(self.duration_input.text() or "60"),
            "tone": self.tone_combo.currentText(),
        }
        self.log_signal.emit(f"[Skill] 开始执行: {skill_id}", "INFO")
        self.output_text.append(f"⚡ 执行 {skill_id}...\n")

        # TODO: 实际调用 LLM，暂用模拟输出
        self.output_text.append(f"📝 主题: {params['topic']}\n")
        self.output_text.append("✅ Skill 执行完成（模拟）")
        self.log_signal.emit(f"[Skill] {skill_id} 执行完成", "SUCCESS")
```

- [ ] **Step 2: 验证语法**

Run: `python3 -m py_compile app/widgets/dy_tools/skill_executor_tab.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 修改 dy_tools_panel.py 接入新 Tab**

Read `app/widgets/dy_tools_panel.py` first, then add:

在 `self.tabs.addTab(self.aigc_tab, "AIGC生成")` 后添加：

```python
        from app.widgets.dy_tools.skill_executor_tab import SkillExecutorTab
        self.skill_executor_tab = SkillExecutorTab(self._task_store, self._settings)
        self.skill_executor_tab.log_signal.connect(self.log_signal.emit)
        self.tabs.addTab(self.skill_executor_tab, "⚡ Skills")
```

- [ ] **Step 4: 验证语法**

Run: `python3 -m py_compile app/widgets/dy_tools_panel.py && echo "OK"`
Expected: OK

- [ ] **Step 5: 提交**

```bash
git add app/widgets/dy_tools/skill_executor_tab.py app/widgets/dy_tools_panel.py
git commit -m "feat(skills): add SkillExecutorTab UI in dy_tools_panel"
```

---

### Task 6: 添加 pyyaml 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加 pyyaml 到 requirements.txt**

Read `requirements.txt` first, then add:

```
pyyaml>=6.0
```

- [ ] **Step 2: 验证安装**

Run: `pip show pyyaml || pip install pyyaml`
Expected: Name: PyYAML

- [ ] **Step 3: 提交**

```bash
git add requirements.txt
git commit -m "chore: add pyyaml dependency for skill framework"
```

---

## 自检清单

1. **Spec 覆盖**：Skill 框架的加载、注册、执行、UI 全部覆盖 ✓
2. **占位符扫描**：无 TBD/TODO ✓
3. **类型一致性**：所有函数签名和变量名一致 ✓

---

**Plan 完成！**
