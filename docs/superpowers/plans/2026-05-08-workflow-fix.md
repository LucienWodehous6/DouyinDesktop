# 协作流修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复协作流无法运行的问题，让 CDO→CCO→SEO→CMO 流水线能正确从 settings 读取 API 配置并执行。

**Architecture:** 修改 `workflow_page.py` 的 `_on_run` 方法，从 `self._settings` 读取 API 配置填充到各 Agent 的 config 中。

**Tech Stack:** PyQt6, OpenAI SDK, httpx

---

## Task 1: 在 workflow_page.py 中添加配置读取方法

**Files:**
- Modify: `app/widgets/workflow/workflow_page.py:156-180`

- [ ] **Step 1: 修改 `_on_run` 方法，从 `self._settings` 读取 API 配置**

找到 `_on_run` 方法中 agents 的定义，替换为：

```python
def _on_run(self):
    """开始执行流水线"""
    self.log_view.clear()
    self.log_view.append("[Pipeline] 开始执行...")

    # 从 settings 读取 API 配置
    api_key = self._settings.get("openai_api_key", "")
    api_base = self._settings.get("openai_text_api_base", "https://api.deepseek.com/v1")
    model = self._settings.get("openai_text_model", "deepseek-chat")

    agents = [
        {"Name": "CDO", "config": {
            "keyword": "测试",
            "platform": "抖音",
            "count": 10,
        }},
        {"Name": "CCO", "config": {
            "api_key": api_key,
            "api_base": api_base,
            "model": model,
            "style": "neutral",
        }},
        {"Name": "SEO", "config": {
            "api_key": api_key,
            "api_base": api_base,
            "model": model,
        }},
        {"Name": "CMO", "config": {
            "api_key": api_key,
            "api_base": api_base,
            "model": model,
            "target_platform": "抖音",
        }},
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
```

- [ ] **Step 2: 提交代码**

```bash
git add app/widgets/workflow/workflow_page.py
git commit -m "fix(workflow): pass API config from settings to agents"
```

---

## Task 2: 验证 pipeline_worker 能正确读取 Agent 配置

**Files:**
- Modify: `app/widgets/workflow/pipeline_worker.py:43-61`

- [ ] **Step 1: 检查 `_run_agent` 方法确认配置传递正确**

当前 `_run_agent` 方法代码：

```python
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
```

代码已经正确读取 `agent["Name"]` 和 `agent["config"]`，无需修改。

- [ ] **Step 2: 检查 `_run_cco` 方法确认 config 参数传递**

当前 `_run_cco` 代码：

```python
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
```

代码已正确传递 config 参数。无需修改。

---

## Task 3: 验证所有 Agent 的 signal 连接

**Files:**
- Check: `app/widgets/workflow/agents/*.py`

- [ ] **Step 1: 确认 PipelineWorker 使用了正确的 signal 名称**

查看 `pipeline_worker.py` 第 10 行：
```python
log_signal = pyqtSignal(str, str)  # (agent_name, message)
```

但各 Agent 的 log_signal 是 `pyqtSignal(str)`，只传一个字符串。

检查发现：
- `pipeline_worker.py:10` 定义的是 `log_signal = pyqtSignal(str, str)`
- `cco_agent.py:10` 定义的是 `log_signal = pyqtSignal(str)`

**这会导致 signal 连接失败！**

需要修复 `pipeline_worker.py` 中对 Agent signal 的连接方式。当前代码在 `_run_agent` 中直接使用 `worker.log_signal.connect(...)` 但没有处理 signal 签名不匹配的问题。

实际上，QMetaObject 会自动处理 signal 转换，但需要确认 `_on_log` 能正确处理。

查看 `_on_log` 方法：
```python
def _on_log(self, agent: str, msg: str):
    self.log_view.append(f"[{agent}] {msg}")
```

这里 `_on_log` 接收两个参数 `(agent, msg)`，但 Agent 的 `log_signal` 只发送一个参数 `msg`。**这是一个问题！**

需要修复 pipeline_worker.py 中的 signal 连接逻辑，将 agent_name 和 log message 一起发送。

---

## Task 4: 修复 pipeline_worker 的 signal 签名不匹配

**Files:**
- Modify: `app/widgets/workflow/pipeline_worker.py:43-125`

- [ ] **Step 1: 为每个 Agent 的 worker 添加带有 agent_name 的 log handler**

替换所有 Agent 的 signal 连接方式：

当前代码：
```python
worker.finished_signal.connect(lambda: worker.deleteLater())
worker.start()
worker.wait()
```

需要改为：
```python
worker.log_signal.connect(lambda msg: self.log_signal.emit(name, msg))
worker.error_signal.connect(lambda e: self.error_signal.emit(f"{name}: {e}"))
worker.finished_signal.connect(lambda: worker.deleteLater())
worker.start()
worker.wait()
```

这样每个 Agent 的 worker 发送的单个参数 log 会通过 lambda 转发为双参数 `(name, msg)` 的 signal。

---

## Self-Review

1. **Spec coverage:** 所有问题都已覆盖 - name 大小写、API 配置传递、signal 签名
2. **Placeholder scan:** 无 placeholder，所有代码都是完整的
3. **Type consistency:** config 传递使用 `config.get()` 带默认值，类型一致

---

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-05-08-workflow-fix.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?