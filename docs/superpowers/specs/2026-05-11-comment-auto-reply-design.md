# 评论管理增强设计文档

## 概述

在现有 `comment_panel.py` 基础上增强 AI 自动回复功能，支持智能回复和频率控制。

## 现有功能

- 作品选择
- 评论获取与展示
- AI 开关 + 系统提示词配置
- 基础日志

## 增强功能

### 1. AI 智能回复引擎

**新增模块**: `AIReplyEngine` 类

```
职责：
- 调用 DeepSeek API 生成个性化回复
- 支持提示词模板变量替换
- 过滤思考标签内容
- 异常时降级为默认回复
```

**API 配置来源**（从 settings 读取）：
| 配置项 | settings key | 默认值 |
|--------|--------------|--------|
| API Key | `openai_api_key` | - |
| API Base | `openai_api_base` | https://api.deepseek.com/v1 |
| Model | `openai_model` | deepseek-chat |

> 注意：也可支持 `openai_text_*` 系列配置，需在 UI 添加下拉选择

**模板变量**：
- `{{video_title}}` → 视频标题
- `{{comment}}` → 用户评论
- `{{username}}` → 评论用户名

### 2. 回复频率控制

**新增模块**: `ReplyScheduler` 类

```
职责：
- 控制每分钟最大回复数（配置项：max_per_minute）
- 控制最小发送间隔（配置项：min_interval_seconds）
- 随机间隔防作弊（min ~ max 之间随机）
- 提供 stop() 方法立即停止
```

**配置项**：
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| max_per_minute | 5 | 每分钟最大回复数 |
| min_interval | 3 | 最小发送间隔（秒） |
| max_interval | 8 | 最大发送间隔（秒） |

### 3. UI 增强

**新增控件**：
1. 频率控制折叠面板（可展开/收起）
   - 每分钟回复数：SpinBox（1-20）
   - 发送间隔：SpinBox（1-30秒）
2. 进度条（QProgressBar）
3. 回复状态筛选按钮（全部/未回复/已回复）

**现有控件调整**：
- 日志区域移至底部固定高度
- 按钮布局优化

### 4. 数据流

```
用户点击"开始回复"
  → ReplyScheduler.start()
    → 按频率调度 AIReplyEngine.generate()
      → 调用 DeepSeek API
      → 发送回复（CLI）
        → 更新评论状态
        → 刷新表格
        → 更新统计
```

### 5. 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| API Key 未配置 | 弹窗提示 + 停止回复 |
| API 调用失败 | 3次重试后跳过，使用默认回复 |
| CLI 发送失败 | 记录日志，继续下一条 |
| 用户手动停止 | 立即停止，更新 UI |

## 文件变更

| 文件 | 变更 |
|------|------|
| `app/widgets/comment_panel.py` | 增强 AI 回复逻辑，新增频率控制 |
| `app/styles.py` | 新增进度条样式 |

## 验证计划

1. 选择作品后获取评论
2. 配置提示词和频率参数
3. 点击开始回复，观察日志和进度
4. 检查评论状态是否正确更新
5. 测试停止按钮是否生效
