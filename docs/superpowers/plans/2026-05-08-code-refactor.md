# 代码优化重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理无用代码/变量/函数，拆分大文件，保持现有架构，整理项目文档。

**Architecture:** 保持现有目录结构不变，仅拆分文件、清理无用代码、添加文档。

**Tech Stack:** Python, PyQt6, Playwright

---

## Task 1: 分析并清理 app/styles.py

**Files:**
- Modify: `app/styles.py`
- Create: `app/styles_constants.py` (如果需要)

- [ ] **Step 1: 分析 styles.py 内容**

读取 `app/styles.py` 完整内容（585行），识别：
1. 纯样式代码（QSS 字符串）
2. 非样式代码（Python 逻辑、函数、常量等）

- [ ] **Step 2: 清理无用代码**

如果发现非样式代码，移到适当位置或删除。

- [ ] **Step 3: 提交**

```bash
git add app/styles.py
git commit -m "refactor(styles): clean up non-style code in styles.py"
```

---

## Task 2: 分析并清理 app/worker.py

**Files:**
- Modify: `app/worker.py`
- Create: `app/workers/` (如果需要拆分)

- [ ] **Step 1: 分析 worker.py 内容**

读取 `app/worker.py` 完整内容（398行），识别：
1. DataWorker 类的完整职责
2. 辅助函数
3. 无用变量或死代码

- [ ] **Step 2: 清理无用代码**

- [ ] **Step 3: 提交**

```bash
git add app/worker.py
git commit -m "refactor(worker): clean up worker.py"
```

---

## Task 3: 拆分 core_modules/douyin_browser_automation.py

**Files:**
- Create: `core_modules/douyin_browser_automation.py` (精简版，保留核心接口)
- Create: `core_modules/browser/locators.py` (搜索框定位策略)
- Create: `core_modules/browser/cookies.py` (Cookie 管理)
- Create: `core_modules/browser/actions.py` (搜索、滚动等操作)
- Create: `core_modules/browser/__init__.py`
- Modify: `core_modules/douyin_browser_automation.py` (重导出，保持兼容性)

- [ ] **Step 1: 分析文件结构**

读取完整文件，识别：
1. 顶层函数（locators、cookies、actions 等）
2. 配置常量
3. 主入口函数

- [ ] **Step 2: 创建 browser 子包**

创建 `core_modules/browser/` 目录，按职责拆分：
- `locators.py`: 搜索框定位策略
- `cookies.py`: Cookie 管理相关
- `actions.py`: 搜索、滚动等操作
- `__init__.py`: 导出主要接口

- [ ] **Step 3: 精简主文件**

主文件保留主要入口函数，从子包导入。

- [ ] **Step 4: 提交**

```bash
git add core_modules/
git commit -m "refactor(browser): split douyin_browser_automation.py into browser/ subpackage"
```

---

## Task 4: 拆分 core_modules/xhs_search.py

**Files:**
- Create: `core_modules/xhs_search.py` (精简版)
- Create: `core_modules/xhs/locators.py` (小红书搜索框定位)
- Create: `core_modules/xhs/actions.py` (小红书搜索操作)
- Create: `core_modules/xhs/__init__.py`
- Modify: `core_modules/xhs_search.py` (重导出)

- [ ] **Step 1: 分析文件结构**

读取完整文件，识别职责模块。

- [ ] **Step 2: 创建 xhs 子包**

创建 `core_modules/xhs/` 目录，按职责拆分。

- [ ] **Step 3: 精简主文件并保持兼容性**

- [ ] **Step 4: 提交**

```bash
git add core_modules/
git commit -m "refactor(xhs): split xhs_search.py into xhs/ subpackage"
```

---

## Task 5: 拆分 app/widgets/video_creation_panel.py

**Files:**
- Create: `app/widgets/video_creation_panel.py` (精简版)
- Create: `app/widgets/creation/` (组件目录)
- Create: `app/widgets/creation/panels.py` (视频创建子面板)
- Create: `app/widgets/creation/dialogs.py` (对话框)
- Create: `app/widgets/creation/__init__.py`

- [ ] **Step 1: 分析文件结构**

读取完整文件，识别：
1. 视频创建面板类
2. 字幕编辑、素材选择等子组件
3. 对话框类

- [ ] **Step 2: 创建 creation/ 子包**

按 UI 组件拆分：
- `panels.py`: 子面板类
- `dialogs.py`: 对话框类
- `__init__.py`: 主类导出

- [ ] **Step 3: 精简主文件**

主文件保留 VideoCreationPanel，从子包导入组件。

- [ ] **Step 4: 提交**

```bash
git add app/widgets/
git commit -m "refactor(creation): split video_creation_panel.py into creation/ subpackage"
```

---

## Task 6: 拆分 app/widgets/script_panel.py

**Files:**
- Create: `app/widgets/script_panel.py` (精简版)
- Create: `app/widgets/script_editor/` (组件目录)
- Create: `app/widgets/script_editor/editor.py` (剧本编辑器)
- Create: `app/widgets/script_editor/preview.py` (预览组件)
- Create: `app/widgets/script_editor/__init__.py`

- [ ] **Step 1: 分析文件结构**

- [ ] **Step 2: 创建 script_editor/ 子包**

- [ ] **Step 3: 精简主文件**

- [ ] **Step 4: 提交**

```bash
git add app/widgets/
git commit -m "refactor(script): split script_panel.py into script_editor/ subpackage"
```

---

## Task 7: 创建项目结构文档

**Files:**
- Create: `docs/project-structure.md`

- [ ] **Step 1: 生成项目结构树**

```bash
find . -type f -name "*.py" -not -path "*/__pycache__/*" -not -path "*/.git/*" | sort
```

- [ ] **Step 2: 编写文档**

文档包含：
1. 项目概述
2. 目录结构及职责说明
3. 各模块说明
4. 入口点

- [ ] **Step 3: 提交**

```bash
git add docs/project-structure.md
git commit -m "docs: add project structure documentation"
```

---

## Self-Review

1. **Spec coverage:** 所有 6 个大文件都有清理/拆分任务，文档任务也有
2. **Placeholder scan:** 无 placeholder，所有步骤都有具体说明
3. **Type consistency:** 文件路径使用完整绝对路径

---

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-05-08-code-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?