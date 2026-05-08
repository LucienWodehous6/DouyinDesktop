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