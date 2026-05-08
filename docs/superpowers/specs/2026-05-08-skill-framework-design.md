# Skill 框架设计文档

> **子系统 C：Skill 框架复用** — AGI-Super-Team 的 Skill 体系融入桌面应用

## 背景

AGI-Super-Team 提供了 727+ 可复用的 Skill，每个 Skill 是独立的能力单元，以 `SKILL.md` 格式定义。douyin-desktop 需要一个类似的 Skill 框架来：
1. 结构化 AI 能力（剧本生成、SEO优化、内容创作等）
2. 支持 Skill 的动态加载和执行
3. 为子系统 A（内容增强）和子系统 B（协作流）提供基础设施

## 设计目标

- **Skill 格式**：采用与 AGI-Super-Team 兼容的 `SKILL.md` + YAML frontmatter 格式
- **本地存储**：Skills 保存在 `app/skills/` 目录
- **能力抽象**：统一的 Skill 接口，支持 LLM 调用、脚本执行、工作流编排
- **UI 集成**：在「抖音工具」面板中可浏览和执行 Skill

## 架构

```
app/skills/                    # Skill 存储目录
├── _skill_base.py             # Skill 基类和接口定义
├── skill_loader.py            # 动态加载 SKILL.md
├── registry.py                # Skill 注册表（内存索引）
└── skills/                    # 具体 Skill 实现
    ├── khazix-writer/         # 爆款文案 Skill
    │   └── SKILL.md
    ├── seo-optimize/          # SEO 优化 Skill
    │   └── SKILL.md
    └── ...                    # 更多 Skills

app/widgets/dy_tools/
└── skill_executor_tab.py      # Skill 执行界面（新增 Tab）
```

## Skill 格式

每个 Skill 是一个目录，包含 `SKILL.md`：

```yaml
---
name: khazix-writer
description: "生成抖音爆款文案，参考可汗学院风格"
metadata:
  version: "1.0.0"
  author: "CCO Ives"
  domains: [content, copywriting, douyin]
  type: llm-generation
  requires: [openai-api]
---

# Khazix Writer — 抖音爆款文案生成

## 什么时候用
- 需要生成抖音视频文案/剧本时
- 需要参考可汗学院风格的知识讲解时

## 输入
- topic: 视频主题
- duration: 视频时长（秒）
- tone: 文风（搞笑/严肃/温情...）

## 输出
- markdown 格式的完整文案
```

## 核心接口

```python
class Skill(ABC):
    name: str
    description: str
    metadata: dict

    @abstractmethod
    def execute(self, params: dict, context: dict) -> SkillResult:
        """执行 Skill，返回结果"""
        pass

    def validate_input(self, params: dict) -> bool:
        """验证输入参数"""
        pass
```

## 数据流

1. `SkillLoader` 扫描 `app/skills/skills/` 目录，加载所有 `SKILL.md`
2. `SkillRegistry` 维护 name → Skill 实例的映射
3. `SkillExecutorTab`（UI）列出可用 Skills，用户选择后填写参数执行
4. 执行结果通过 `log_signal` 输出到运行日志

## 文件清单

| 文件 | 职责 |
|------|------|
| `app/skills/_skill_base.py` | `Skill` 基类、`SkillResult` 数据类 |
| `app/skills/skill_loader.py` | 扫描目录、解析 SKILL.md |
| `app/skills/registry.py` | Skill 注册表，全局单例 |
| `app/skills/skills/khazix-writer/SKILL.md` | 示例 Skill（迁移自 AGI-Super-Team） |
| `app/widgets/dy_tools/skill_executor_tab.py` | Skill 执行 UI Tab |
| `app/widgets/dy_tools_panel.py` | 接入 skill_executor_tab |

## 测试策略

- `tests/app/skills/test_skill_base.py` — 基类接口测试
- `tests/app/skills/test_loader.py` — Skill 加载解析测试
- `tests/app/skills/test_registry.py` — 注册表功能测试

## 依赖

- PyYAML（解析 frontmatter）
- 复用了现有的 `openai_api` 配置（来自 `settings`）
