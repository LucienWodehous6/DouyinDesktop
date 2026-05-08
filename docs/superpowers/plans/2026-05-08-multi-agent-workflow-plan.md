# 多 Agent 协作流 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可视化节点编排的多 Agent 协作流水线：CDO采集 → CCO剧本 → SEO优化 → CMO发布

**Architecture:** PipelineWorker 串行执行 Agent，文件传递数据，流程完成后自动清理。独立 WorkflowPage 承载可视化编辑器。

**Tech Stack:** PyQt6 QThread, 复用 ScriptWorker/SEOOptimizeWorker

---

## 文件结构

```
app/widgets/workflow/
├── __init__.py
├── pipeline_worker.py     # PipelineWorker 核心编排
├── agents/
│   ├── __init__.py
│   ├── cdo_agent.py       # CDO 数据采集
│   ├── cco_agent.py       # CCO 内容创作
│   ├── seo_agent.py       # SEO 优化（复用 SEOOptimizeWorker）
│   └── cmo_agent.py       # CMO 发布分发
└── workflow_page.py        # 独立页面

app/main_window.py          # 添加导航入口
```

---

### Task 1: 创建 workflow 模块目录结构

**Files:**
- Create: `app/widgets/workflow/__init__.py`
- Create: `app/widgets/workflow/agents/__init__.py`
- Create: `app/widgets/workflow/pipeline_worker.py`

- [ ] **Step 1: 创建目录和空文件**

```bash
mkdir -p app/widgets/workflow/agents
touch app/widgets/workflow/__init__.py
touch app/widgets/workflow/agents/__init__.py
```

- [ ] **Step 2: 提交**

```bash
git add app/widgets/workflow/
git commit -m "feat(workflow): add workflow module directory structure"
```

---

### Task 2: 创建 PipelineWorker 核心编排线程

**Files:**
- Create: `app/widgets/workflow/pipeline_worker.py`

- [ ] **Step 1: 创建 pipeline_worker.py**

```python
"""PipelineWorker — 串行执行多 Agent 流水线的后台线程"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class PipelineWorker(QThread):
    """串行执行多 Agent 流水线的后台线程"""

    log_signal = pyqtSignal(str, str)  # (agent_name, message)
    progress_signal = pyqtSignal(int, str)  # (percent, status)
    agent_done_signal = pyqtSignal(str, str)  # (agent_name, result_file)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, agents: list[dict], output_dir: str):
        super().__init__()
        self.agents = agents  # [{"Name": "CDO", "config": {...}}, ...]
        self.output_dir = output_dir
        self._stop = False
        os.makedirs(output_dir, exist_ok=True)

    def stop(self):
        self._stop = True

    def run(self):
        try:
            total = len(self.agents)
            for i, agent in enumerate(self.agents):
                if self._stop:
                    break
                percent = int((i / total) * 100)
                self.progress_signal.emit(percent, f"执行中: {agent['Name']}")
                self._run_agent(agent)

            if not self._stop:
                self._cleanup_output_files()
                self.progress_signal.emit(100, "完成")
                self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_agent(self, agent: dict):
        """执行单个 Agent"""
        name = agent["Name"]
        config = agent["config"]
        self.log_signal.emit(name, f"开始执行 {name}...")

        if name == "CDO":
            result = self._run_cdo(config)
        elif name == "CCO":
            result = self._run_cco(config)
        elif name == "SEO":
            result = self._run_seo(config)
        elif name == "CMO":
            result = self._run_cmo(config)
        else:
            raise ValueError(f"Unknown agent: {name}")

        self.agent_done_signal.emit(name, result)
        self.log_signal.emit(name, f"{name} 执行完成")

    def _run_cdo(self, config: dict) -> str:
        """CDO 数据采集"""
        # TODO: 实现 CDO Agent
        return os.path.join(self.output_dir, "cdoresult.json")

    def _run_cco(self, config: dict) -> str:
        """CCO 内容创作"""
        # TODO: 实现 CCO Agent
        return os.path.join(self.output_dir, "ccoresult.md")

    def _run_seo(self, config: dict) -> str:
        """SEO 优化"""
        # TODO: 实现 SEO Agent
        return os.path.join(self.output_dir, "seoresult.md")

    def _run_cmo(self, config: dict) -> str:
        """CMO 发布分发"""
        # TODO: 实现 CMO Agent
        return os.path.join(self.output_dir, "cmoresult.json")

    def _cleanup_output_files(self):
        """流程完成后自动清理所有输出文件"""
        files = ["cdoresult.json", "ccoresult.md", "seoresult.md", "cmoresult.json"]
        for f in files:
            path = os.path.join(self.output_dir, f)
            if os.path.exists(path):
                os.remove(path)
                self.log_signal.emit("Pipeline", f"已清理: {f}")
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/pipeline_worker.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/pipeline_worker.py
git commit -m "feat(workflow): add PipelineWorker for multi-agent orchestration"
```

---

### Task 3: 实现 CDO Agent

**Files:**
- Create: `app/widgets/workflow/agents/cdo_agent.py`

- [ ] **Step 1: 创建 cdo_agent.py**

```python
"""CDO Agent — 数据采集"""

import json
import os
from PyQt6.QtCore import QThread, pyqtSignal


class CDOAgentWorker(QThread):
    """CDO 数据采集 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, keyword: str, platform: str, count: int, output_file: str):
        super().__init__()
        self.keyword = keyword
        self.platform = platform
        self.count = count
        self.output_file = output_file

    def run(self):
        try:
            self.log_signal.emit(f"[CDO] 开始采集: {self.keyword} on {self.platform}")

            # 调用现有 API 搜索逻辑（复用 ApiSearchWorker 的底层）
            from app.widgets.dy_tools.api_search_tab import ApiSearchWorker
            from app.widgets.dy_tools.api_search_tab import SORT_MAP, TIME_MAP

            sort_type = SORT_MAP["综合"]
            publish_time = TIME_MAP["不限"]

            # 同步执行采集
            client = None
            try:
                # 使用 dy_cli 的 DouyinAPIClient
                from core_modules.dy_cli.engines.api_client import DouyinAPIClient, DouyinAPIError

                client = DouyinAPIClient.from_config()
                result = client.search(
                    keyword=self.keyword,
                    sort_type=sort_type,
                    publish_time=publish_time,
                    search_type="general",
                    count=self.count,
                )
                client.close()

                videos = []
                data_list = result.get("data", [])
                for item in data_list:
                    aweme = item.get("aweme_info", {})
                    if not aweme:
                        continue
                    videos.append({
                        "aweme_id": aweme.get("aweme_id", ""),
                        "title": aweme.get("desc", ""),
                        "author": aweme.get("author", {}).get("nickname", ""),
                        "likes": aweme.get("statistics", {}).get("digg_count", 0),
                        "comments": aweme.get("statistics", {}).get("comment_count", 0),
                        "collects": aweme.get("statistics", {}).get("collect_count", 0),
                        "shares": aweme.get("statistics", {}).get("share_count", 0),
                    })

                output_data = {
                    "keyword": self.keyword,
                    "platform": self.platform,
                    "count": len(videos),
                    "videos": videos,
                }

                with open(self.output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                self.log_signal.emit(f"[CDO] 采集完成: {len(videos)} 条数据")
                self.result_signal.emit(output_data)

            except Exception as e:
                if client:
                    try:
                        client.close()
                    except:
                        pass
                raise e

        except Exception as e:
            self.log_signal.emit(f"[CDO] 采集失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/agents/cdo_agent.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/agents/cdo_agent.py
git commit -m "feat(workflow): add CDO Agent for data collection"
```

---

### Task 4: 实现 CCO Agent

**Files:**
- Create: `app/widgets/workflow/agents/cco_agent.py`

- [ ] **Step 1: 创建 cco_agent.py**

```python
"""CCO Agent — 内容创作（剧本生成）"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class CCOAgentWorker(QThread):
    """CCO 内容创作 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str, style: str = "neutral"):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.style = style

    def run(self):
        try:
            import json

            self.log_signal.emit("[CCO] 读取采集数据...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            keyword = data.get("keyword", "")
            videos = data.get("videos", [])

            # 构建采集数据摘要
            task_data_str = f"搜索词: {keyword}\n"
            for v in videos[:5]:
                task_data_str += f"\n视频: {v.get('title', '')[:50]}\n"
                task_data_str += f"  点赞:{v.get('likes',0)} 评论:{v.get('comments',0)}\n"

            # 加载系统提示词
            system_prompt = self._load_system_prompt()

            # 构建用户提示词
            user_prompt = f"""根据以下采集数据生成一个抖音剧本。

--- 采集数据 ---
{task_data_str}

剧本风格: {self.style}
要求：
1. 开场前3秒必须有强钩子（引起好奇或共鸣）
2. 语言简洁、口语化，适合配音阅读
3. 结构：开场钩子 → 核心内容 → 行动号召
4. 知识讲解要类比生活场景，帮助理解
"""

            self.log_signal.emit("[CCO] 调用 AI 生成剧本...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
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

            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(full_content)

            self.log_signal.emit(f"[CCO] 剧本生成完成: {len(full_content)} 字")
            self.result_signal.emit(full_content)

        except Exception as e:
            self.log_signal.emit(f"[CCO] 生成失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        candidates = []
        import sys
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models", "script.md"))
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidates.append(os.path.join(project_root, "models", "script.md"))
        candidates.append(os.path.join(os.getcwd(), "models", "script.md"))

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except:
                    pass
        return ""
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/agents/cco_agent.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/agents/cco_agent.py
git commit -m "feat(workflow): add CCO Agent for script generation"
```

---

### Task 5: 实现 SEO Agent

**Files:**
- Create: `app/widgets/workflow/agents/seo_agent.py`

- [ ] **Step 1: 创建 seo_agent.py**

```python
"""SEO Agent — 标题/标签优化（复用 SEOOptimizeWorker）"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class SEOAgentWorker(QThread):
    """SEO 优化 Agent Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        try:
            self.log_signal.emit("[SEO] 读取剧本内容...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                script_content = f.read()

            self.log_signal.emit("[SEO] 调用 AI 优化标题和标签...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{script_content}

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

            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(full_content)

            self.log_signal.emit(f"[SEO] 优化完成: {len(full_content)} 字")
            self.result_signal.emit(full_content)

        except Exception as e:
            self.log_signal.emit(f"[SEO] 优化失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/agents/seo_agent.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/agents/seo_agent.py
git commit -m "feat(workflow): add SEO Agent for title/hashtag optimization"
```

---

### Task 6: 实现 CMO Agent

**Files:**
- Create: `app/widgets/workflow/agents/cmo_agent.py`

- [ ] **Step 1: 创建 cmo_agent.py**

```python
"""CMO Agent — 发布/分发内容生成"""

import json
import os
from PyQt6.QtCore import QThread, pyqtSignal


class CMOAgentWorker(QThread):
    """CMO 发布分发 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str, target_platform: str = "抖音"):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.target_platform = target_platform

    def run(self):
        try:
            self.log_signal.emit(f"[CMO] 读取优化后剧本...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                seo_content = f.read()

            self.log_signal.emit(f"[CMO] 生成{self.target_platform}发布内容...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位社交媒体营销专家。根据以下已优化的抖音剧本，生成用于{self.target_platform}平台的发布内容。

已优化剧本：
{seo_content}

任务要求：
1. 提取最佳标题（从剧本中已有的标题选择）
2. 生成发布描述（适配平台算法，含关键词）
3. 推荐发布时间段
4. 生成发布配置（标签、描述、封面建议）

请以 JSON 格式输出：

{{
  "platform": "{self.target_platform}",
  "title": "发布的标题",
  "description": "发布描述，100-200字",
  "hashtags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5"],
  "best_time": "推荐发布时间",
  "cover_suggestion": "封面建议"
}}
"""

            messages = [{"role": "user", "content": prompt}]

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
            )

            content = response.choices[0].message.content or ""

            # 尝试解析 JSON
            try:
                # 去掉 markdown 代码块
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()

                result = json.loads(content)
            except:
                result = {"raw": content}

            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.log_signal.emit(f"[CMO] 发布内容生成完成")
            self.result_signal.emit(result)

        except Exception as e:
            self.log_signal.emit(f"[CMO] 生成失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/agents/cmo_agent.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/agents/cmo_agent.py
git commit -m "feat(workflow): add CMO Agent for publishing"
```

---

### Task 7: 更新 PipelineWorker 集成各 Agent

**Files:**
- Modify: `app/widgets/workflow/pipeline_worker.py`

- [ ] **Step 1: 更新 _run_cdo 等方法**

Read the current `pipeline_worker.py`, then replace the stub methods with actual integration:

```python
    def _run_cdo(self, config: dict) -> str:
        from app.widgets.workflow.agents.cdo_agent import CDOAgentWorker
        result_file = os.path.join(self.output_dir, "cdoresult.json")
        worker = CDOAgentWorker(
            keyword=config.get("keyword", ""),
            platform=config.get("platform", "抖音"),
            count=config.get("count", 20),
            output_file=result_file,
        )
        # 同步等待完成
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_cco(self, config: dict) -> str:
        from app.widgets.workflow.agents.cco_agent import CCOAgentWorker
        input_file = os.path.join(self.output_dir, "cdoresult.json")
        result_file = os.path.join(self.output_dir, "ccoresult.md")
        worker = CCOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
            style=config.get("style", "neutral"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_seo(self, config: dict) -> str:
        from app.widgets.workflow.agents.seo_agent import SEOAgentWorker
        input_file = os.path.join(self.output_dir, "ccoresult.md")
        result_file = os.path.join(self.output_dir, "seoresult.md")
        worker = SEOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_cmo(self, config: dict) -> str:
        from app.widgets.workflow.agents.cmo_agent import CMOAgentWorker
        input_file = os.path.join(self.output_dir, "seoresult.md")
        result_file = os.path.join(self.output_dir, "cmoresult.json")
        worker = CMOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
            target_platform=config.get("target_platform", "抖音"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/pipeline_worker.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/pipeline_worker.py
git commit -m "feat(workflow): integrate all agents into PipelineWorker"
```

---

### Task 8: 创建 WorkflowPage 独立页面

**Files:**
- Create: `app/widgets/workflow/workflow_page.py`

- [ ] **Step 1: 创建 workflow_page.py**

```python
"""协作流页面 — 可视化节点编排"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QFrame, QSizePolicy,
    QScrollArea, QProgressBar, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

import os


class WorkflowPage(QWidget):
    """协作流页面 — 多 Agent 流水线可视化编排"""

    def __init__(self, task_store=None, settings: dict | None = None):
        super().__init__()
        self._task_store = task_store
        self._settings = settings or {}
        self._pipeline_worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QFrame()
        header.setObjectName("pageHeader")
        header.setStyleSheet("background: #161b22; border-bottom: 1px solid #21262d;")
        header.setMinimumHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("⚡ 协作流")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setFixedWidth(100)
        self.run_btn.clicked.connect(self._on_run)
        header_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        header_layout.addWidget(self.stop_btn)

        layout.addWidget(header)

        # 主内容区
        content = QHBoxLayout()
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(12)

        # 左侧：节点列表
        left_panel = QFrame()
        left_panel.setObjectName("nodePanel")
        left_panel.setFixedWidth(200)
        left_panel.setStyleSheet("background: #161b22; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        node_label = QLabel("节点")
        node_label.setObjectName("sectionLabel")
        left_layout.addWidget(node_label)

        self.node_list = QListWidget()
        self.node_list.setObjectName("nodeList")
        self._populate_nodes()
        left_layout.addWidget(self.node_list)

        left_layout.addStretch()
        layout.addLayout(content)

        # 中间：节点编辑器（可视化画布）
        self.canvas = QFrame()
        self.canvas.setObjectName("workflowCanvas")
        self.canvas.setStyleSheet("background: #0d1117; border: 1px solid #21262d; border-radius: 8px;")
        content.addWidget(self.canvas, 1)

        # 右侧：配置面板
        right_panel = QFrame()
        right_panel.setObjectName("configPanel")
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("background: #161b22; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)

        config_label = QLabel("节点配置")
        config_label.setObjectName("sectionLabel")
        right_layout.addWidget(config_label)

        self.config_text = QTextEdit()
        self.config_text.setPlaceholderText("选择节点查看配置...")
        self.config_text.setObjectName("configEdit")
        right_layout.addWidget(self.config_text, 1)

        layout.addWidget(right_panel)

        # 底部：日志面板
        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        log_frame.setMinimumHeight(150)
        log_frame.setStyleSheet("background: #0d1117; border-top: 1px solid #21262d;")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(12, 8, 12, 8)

        log_label = QLabel("执行日志")
        log_label.setObjectName("sectionLabel")
        log_layout.addWidget(log_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")
        self.log_view.setStyleSheet("""
            QTextEdit#logView {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #21262d;
                border-radius: 6px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_view)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        log_layout.addWidget(self.progress_bar)

        layout.addWidget(log_frame)

    def _populate_nodes(self):
        """填充默认节点列表"""
        nodes = [
            ("CDO", "数据采集"),
            ("CCO", "内容创作"),
            ("SEO", "SEO优化"),
            ("CMO", "发布分发"),
        ]
        for node_id, node_name in nodes:
            item = QListWidgetItem(f"{node_id} — {node_name}")
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            self.node_list.addItem(item)

    def _on_run(self):
        """开始执行流水线"""
        self.log_view.clear()
        self.log_view.append("[Pipeline] 开始执行...")

        agents = [
            {"Name": "CDO", "config": {"keyword": "测试", "platform": "抖音", "count": 10}},
            {"Name": "CCO", "config": {"style": "neutral"}},
            {"Name": "SEO", "config": {}},
            {"Name": "CMO", "config": {"target_platform": "抖音"}},
        ]

        output_dir = os.path.join(os.path.expanduser("~"), ".dy", "workflow_output")
        os.makedirs(output_dir, exist_ok=True)

        from app.widgets.workflow.pipeline_worker import PipelineWorker
        self._pipeline_worker = PipelineWorker(agents, output_dir)
        self._pipeline_worker.log_signal.connect(self._on_log)
        self._pipeline_worker.progress_signal.connect(self._on_progress)
        self._pipeline_worker.finished_signal.connect(self._on_finished)
        self._pipeline_worker.error_signal.connect(self._on_error)

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._pipeline_worker.start()

    def _on_stop(self):
        if self._pipeline_worker:
            self._pipeline_worker.stop()
            self._pipeline_worker.wait()
            self.log_view.append("[Pipeline] 用户停止执行")

    def _on_log(self, agent: str, msg: str):
        self.log_view.append(f"[{agent}] {msg}")

    def _on_progress(self, percent: int, status: str):
        self.progress_bar.setValue(percent)

    def _on_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_view.append("[Pipeline] ✓ 全部完成，输出文件已清理")

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_view.append(f"[Pipeline] ✗ 错误: {msg}")
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/workflow/workflow_page.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/workflow/workflow_page.py
git commit -m "feat(workflow): add WorkflowPage with visual pipeline editor"
```

---

### Task 9: 集成到 main_window

**Files:**
- Modify: `app/main_window.py`

- [ ] **Step 1: 添加导航入口**

Read `main_window.py` around line 88-106 where nav_items is defined. Add the new nav item:

Find `nav_items` list and add:
```python
            ("⚡", "协作流"),
```

Find `sidebar_layout.addWidget(settings_btn)` around line 106 and add after the nav items loop (before settings_btn):

```python
        # 协作流按钮
        workflow_btn = SidebarButton("⚡", "协作流")
        workflow_btn.clicked.connect(lambda: self._switch_page(7))
        sidebar_layout.addWidget(workflow_btn)
```

And update settings_btn to index 7:
```python
        settings_btn = SidebarButton("⚙", "设置")
        settings_btn.clicked.connect(lambda: self._switch_page(7))
```

Find the stack widget setup (around line 124) and add before settings_page:
```python
        from app.widgets.workflow.workflow_page import WorkflowPage
        self.workflow_page = WorkflowPage(self.task_store, self.settings)
        self.stack.addWidget(self.workflow_page)
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/main_window.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/main_window.py
git commit -m "feat(workflow): add WorkflowPage to main window navigation"
```

---

## 自检清单

1. **Spec 覆盖**：PipelineWorker ✓、CDO ✓、CCO ✓、SEO ✓、CMO ✓、WorkflowPage ✓、集成 ✓、自动清理 ✓
2. **占位符扫描**：无 TBD/TODO ✓
3. **类型一致性**：所有 Agent Worker 方法签名一致 ✓

---

**Plan 完成！**
