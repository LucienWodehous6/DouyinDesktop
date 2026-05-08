# 多 Agent 协作流 — 设计文档

> **子系统 B**：可视化节点编排 + 多 Agent 串行流水线

## 背景

用户希望实现类似 AGI-Super-Team 的多 Agent 协作模式：在 douyin-desktop 中，用可视化方式编排 Agent 节点，让多个 Agent 串行执行完成内容生产全流程。

## 设计决策

| 问题 | 选择 |
|------|------|
| 入口 | 独立页面（顶部导航） |
| 节点编辑 | 可视化拖拽节点编辑器 |
| Agent 组合 | CDO采集 → CCO剧本 → SEO优化 → CMO发布 |
| 数据传递 | 文件传递（JSON/Markdown） |
| 完成后清理 | 自动清理输出文件，不询问 |

## 架构

```
协作流页面（WORKFLOW_TAB_INDEX=7）
├── 可视化节点编辑器（Canvas）
│   ├── CDO 节点（数据采集）
│   ├── CCO 节点（剧本生成）
│   ├── SEO 节点（标题/标签优化）
│   └── CMO 节点（发布/分发）
├── 节点配置面板（右侧）
├── 执行控制栏（运行/停止）
└── 日志输出面板（底部）
```

## 节点定义

| 节点 | Agent | 输入 | 输出文件 | 说明 |
|------|-------|------|---------|------|
| **CDO** | 数据采集 | keyword, platform | `cdoresult.json` | 调用现有采集逻辑 |
| **CCO** | 内容创作 | `cdoresult.json` | `ccoresult.md` | 基于采集数据生成剧本 |
| **SEO** | SEO优化 | `ccoresult.md` | `seoresult.md` | 复用子系统 A SEOOptimizeWorker |
| **CMO** | 发布分发 | `seoresult.md` | `cmoresult.json` | 生成发布内容（标题+标签+描述） |

## 数据流

```
用户配置节点 → 点击"运行"
    ↓
CDO Worker → 采集数据 → 写入 cdoresult.json → 日志: "[CDO] 采集完成"
    ↓
CCO Worker → 读取 cdoresult.json → 生成剧本 → 写入 ccoresult.md → 日志: "[CCO] 剧本生成完成"
    ↓
SEO Worker → 读取 ccoresult.md → 优化标题/标签 → 写入 seoresult.md → 日志: "[SEO] 优化完成"
    ↓
CMO Worker → 读取 seoresult.md → 生成发布内容 → 写入 cmoresult.json → 日志: "[CMO] 发布内容生成完成"
    ↓
全部完成 → 自动删除所有输出文件 → 日志: "[Pipeline] 清理完成"
```

## 文件约定

| 文件 | 格式 | 生命周期 |
|------|------|---------|
| `cdoresult.json` | JSON | Pipeline 开始时创建，结束时删除 |
| `ccoresult.md` | Markdown | 同上 |
| `seoresult.md` | Markdown | 同上 |
| `cmoresult.json` | JSON | 同上 |

文件保存在 `app/workflow/` 目录下。

## PipelineWorker

```python
class PipelineWorker(QThread):
    """串行执行多 Agent 流水线的后台线程"""

    log_signal = pyqtSignal(str, str)  # (agent_name, message)
    progress_signal = pyqtSignal(int, str)  # (percent, status)
    agent_done_signal = pyqtSignal(str, str)  # (agent_name, result_file)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, agents: list[dict], output_dir: str):
        super().__init__()
        self.agents = agents  # [{"name": "CDO", "config": {...}}, ...]
        self.output_dir = output_dir
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            for agent in self.agents:
                if self._stop:
                    break
                self._run_agent(agent)

            # 清理输出文件
            self._cleanup_output_files()

            if not self._stop:
                self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_agent(self, agent: dict):
        """执行单个 Agent，结果写入文件"""
        name = agent["name"]
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

        self.agent_done_signal.emit(name, result)
        self.log_signal.emit(name, f"{name} 执行完成")

    def _cleanup_output_files(self):
        """流程完成后自动清理所有输出文件"""
        import os
        files = ["cdoresult.json", "ccoresult.md", "seoresult.md", "cmoresult.json"]
        for f in files:
            path = os.path.join(self.output_dir, f)
            if os.path.exists(path):
                os.remove(path)
                self.log_signal.emit("Pipeline", f"已清理: {f}")
```

## UI 布局

```
┌──────────────────────────────────────────────────────────┐
│  �workflow 协作流                          [▶ 运行] [■ 停止] │
├──────────────────────────────────────────────────────────┤
│ ┌────────────┐  ┌──────────────────────────────────┐    │
│ │  节点列表  │  │                                  │    │
│ │            │  │     可视化编辑器 Canvas           │    │
│ │ [+ CDO]   │  │                                  │    │
│ │ [+ CCO]   │  │   [CDO] ──→ [CCO] ──→           │    │
│ │ [+ SEO]   │  │             │                    │    │
│ │ [+ CMO]   │  │         [SEO] ──→ [CMO]         │    │
│ │            │  │                                  │    │
│ └────────────┘  └──────────────────────────────────┘    │
├──────────────────────────────────────────────────────────┤
│ [日志面板]                                                 │
│ [CDO] 开始执行数据采集...                                  │
│ [CDO] 采集完成，找到 15 条数据                             │
│ [CCO] 开始生成剧本...                                      │
│ ...                                                        │
└──────────────────────────────────────────────────────────┘
```

## 节点配置面板

点击节点弹出配置：

| 节点 | 可配置项 |
|------|---------|
| **CDO** | 关键词、平台（抖音/小红书）、采集数量 |
| **CCO** | 文风（搞笑/专业/温情）、剧本类型（种草/测评/剧情） |
| **SEO** | （使用默认优化策略，无需配置） |
| **CMO** | 目标平台、发布时间、标签数量 |

## 依赖

- 无新依赖
- 复用现有 `ScriptWorker`、`SEOOptimizeWorker`
- 新增 `workflow` 目录存放流水线相关代码

## 不涉及范围

- 不实现并行 Agent 执行
- 不实现 Agent 间实时通信
- 不实现节点条件分支
- 不实现循环/重试机制
