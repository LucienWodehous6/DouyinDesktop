# 内容创作增强 — SEO 集成设计文档

> **子系统 A**：将 SEO 标题优化 + 标签推荐能力集成到剧本生成流程

## 背景

现有的剧本生成面板（`ScriptPanel`）调用 AI 生成剧本后，用户需要手动优化标题、添加标签。本次改进目标：剧本生成完成后，自动调用第二次 AI 对剧本进行 SEO 优化，将优化后的结果展示给用户。

## 设计决策

| 问题 | 选择 |
|------|------|
| 功能放在哪里 | 集成到剧本面板（ScriptPanel） |
| 何时触发 | 剧本生成完成后自动触发 |
| 结果展示方式 | 覆盖原剧本，展示优化后的版本 |

## 两阶段流程

```
阶段 1：剧本生成
用户输入提示词 → AI 生成剧本 → 展示剧本（临时）

阶段 2：自动 SEO 优化（剧本生成完成后立即触发）
拿阶段 1 的剧本 → 调用 SEO 优化 AI → 展示优化后剧本 → 用户看到最终结果
```

## 阶段 1：剧本生成（现有流程不变）

剧本生成逻辑保持不变，`_on_result()` 中剧本文本存入 `self._last_result`。

## 阶段 2：SEO 优化 Worker

新增 `SEOOptimizeWorker(QThread)`，在 `_on_result()` 中自动触发：

```python
def _on_result(self, text: str):
    self._last_result = text  # 临时保存原剧本
    # 自动触发 SEO 优化（不展示原剧本）
    self._run_seo_optimize(text)
```

### SEOOptimizeWorker

```python
class SEOOptimizeWorker(QThread):
    result_signal = pyqtSignal(str)  # 优化后的完整剧本
    error_signal = pyqtSignal(str)

    def __init__(self, script_text: str, topic: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.script_text = script_text
        self.topic = topic
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        # 构建 SEO 优化 prompt
        prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{self.script_text}

任务：
1. 优化标题（≤20字，吸睛，包含关键词）
2. 生成 2 个变体标题（信任型、紧迫型）
3. 推荐 5 个标签（以 # 开头）
4. 生成视频描述（≤100字）

输出格式（必须严格遵循）：

【优化标题】
标题内容

【标题变体】
变体A（信任型）：xxx
变体B（紧迫型）：xxx

【推荐标签】
#标签1 #标签2 #标签3 #标签4 #标签5

【视频描述】
描述内容

【优化后剧本】
（将优化后的完整剧本输出，保留原有结构，只优化标题和话术）
"""

        # 调用 AI，流式输出到 result_signal
        ...
```

## 数据流

```
_generate()
    ↓
ScriptWorker 生成剧本 → _on_result(text)
    ↓
_on_result 调用 _run_seo_optimize(text)
    ↓
SEOOptimizeWorker 调用 AI
    ↓
流式输出到 _on_seo_result(optimized_text)
    ↓
_on_seo_result 更新 result_label 为优化后剧本
    ↓
保存/修改按钮变为可用
```

## UI 变更

- `_on_result()` 中**不**立即展示剧本，改为保存后触发 SEO 优化
- 新增 `_on_seo_result()` 收到优化结果后展示到 result_label
- 进度条：阶段 1 显示 "AI 生成剧本..." → 阶段 2 显示 "正在优化 SEO..."
- 优化完成后 result_label 显示最终剧本（包含标题变体、标签、优化后正文）

## 依赖变更

- 无新依赖，复用现有 API 配置

## 依赖变更

- `models/script.md` — 更新系统提示词（无新依赖）

## 测试策略

1. **两阶段流程测试**：验证剧本生成完成后自动触发 SEO 优化
2. **标题变体验证**：验证输出包含 3 个标题（原+2变体）
3. **标签验证**：验证恰好 5 个标签，以 # 开头
4. **流式输出测试**：SEO 优化结果流式展示到 result_label
5. **API 失败处理**：SEO 调用失败时回退到显示原剧本

## 不涉及的范围

- 不修改 Skill 框架（子系统 C 已完成）
- 不新增 Tab 或独立页面
- 不改变剧本生成流程本身（ScriptWorker 保持不变）
