# 内容创作增强 — SEO 集成设计文档

> **子系统 A**：将 SEO 标题优化 + 标签推荐能力集成到剧本生成流程

## 背景

现有的剧本生成面板（`ScriptPanel`）调用 AI 生成剧本后，用户需要手动复制标题、添加标签。SEO/标签优化作为独立 Skill 存在，但未被集成到剧本生成流程中。

本次改进目标：在剧本生成时，AI 一次性输出剧本 + SEO 元数据（优化标题、标签、描述），以 YAML frontmatter 格式附加在剧本开头。

## 设计决策

| 问题 | 选择 |
|------|------|
| 功能放在哪里 | 集成到剧本面板（ScriptPanel） |
| 何时触发 | 剧本生成时同一次 AI 调用 |
| 结果展示方式 | YAML frontmatter 在剧本开头 |

## 输出格式

AI 生成的完整内容结构：

```yaml
---
title: "主标题（吸睛型，≤20字）"
title_variants:
  - "变体标题1（信任型）"
  - "变体标题2（紧迫型）"
hashtags:
  - "#标签1"
  - "#标签2"
  - "#标签3"
  - "#标签4"
  - "#标签5"
description: "短视频描述（≤100字，用于平台展示）"
---

# 正式剧本正文

【开场钩子】
...

【产品介绍】
...

【促单话术】
...

【结束语】
```

## 系统提示词更新

修改 `models/script.md`，增加 SEO 输出要求：

```
## SEO 元数据输出要求（必须执行）

在剧本正文之前，先输出一段 YAML frontmatter，包含以下字段：

```yaml
---
title: "主标题（≤20字，吸睛型，含关键词）"
title_variants:
  - "变体A（信任型，≤20字）"
  - "变体B（紧迫型，≤20字）"
hashtags:
  - "#标签1"
  - "#标签2"
  - "#标签3"
  - "#标签4"
  - "#标签5"
description: "视频描述（≤100字，含关键词）"
---
```

要求：
- `title` 必须包含用户提供的关键词
- `hashtags` 必须恰好 5 个，以 `#` 开头，符合抖音平台规范
- `description` 涵盖核心卖点，字数控制在 100 字内
- YAML frontmatter 必须位于剧本正文之前，用 `---` 包裹
- 剧本正文结构保持原有格式：【开场钩子】【产品介绍】【场景演绎】【促单话术】【结束语】

## UI 变更

### ScriptPanel

- `prompt_edit` placeholder 更新为引导用户输入主题/产品信息
- 生成结果 `_render_markdown()` 已有代码块样式，会自动渲染 YAML frontmatter
- 无需新增 UI 控件，利用现有 result_label 展示

### 提示词模板示例

用户输入提示词时，提供示例帮助 AI 理解：

```
输入提示词示例：
"帮我生成一个护肤品带货剧本，主打补水保湿功效，目标用户是年轻女性"
```

AI 收到后，在 frontmatter 的 title/description/hashtags 中自动融入"补水保湿"等关键词。

## 数据流

```
用户输入提示词
    ↓
ScriptWorker 构建 messages（含更新后的 system_prompt）
    ↓
AI 流式返回：YAML frontmatter + 剧本正文
    ↓
chunk_signal 追加到 result_label
    ↓
mistune 渲染 YAML 为代码块样式，正文为 Markdown
    ↓
用户看到：带 SEO 元数据的完整剧本
```

## 依赖变更

- `models/script.md` — 更新系统提示词（无新依赖）

## 测试策略

1. **功能测试**：输入包含关键词的提示词，验证输出 frontmatter 包含该关键词
2. **格式测试**：验证 frontmatter 有 5 个标签、3 个标题变体
3. **渲染测试**：验证 mistune 正确渲染 YAML 代码块
4. **边界测试**：关键词为空、标签过长、标题超长等场景

## 不涉及的范围

- 不修改 Skill 框架（子系统 C 已完成）
- 不新增 Tab 或独立页面
- 不改变 API 调用流程（复用现有 ScriptWorker）
