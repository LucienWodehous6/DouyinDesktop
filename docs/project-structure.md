# 项目结构文档

## 1. 项目概述

**抖音数据采集助手**是一款基于 PyQt6 + Playwright 的社交媒体数据采集与 AI 内容创作桌面应用。

### 主要功能

| 模块 | 功能描述 |
|------|----------|
| 搜索采集 | 关键词搜索、评论关键字匹配、发布时间筛选、采集数量控制 |
| 视频数据 | 提取视频标题、点赞数、评论数、收藏数、分享数 |
| 评论采集 | 滚动加载全部评论，提取用户名/内容/时间/点赞 |
| 用户匹配 | 评论关键字匹配，自动进入用户主页提取昵称 + ID |
| 视频解析 | 通过分享链接提取视频文案（下载→提取音频→语音转文字） |
| 剧本生成 | 引用采集数据 + 视频文案解析 → AI 流式生成推广剧本 |
| 视频创作 | 剧本拆分分镜 → 分镜生图 → 图生视频 |

### 技术栈

- **GUI 框架**: PyQt6
- **浏览器自动化**: Playwright
- **AI 模型**: OpenAI 兼容 API（DeepSeek、SiliconFlow 等）
- **Python 版本**: ≥ 3.10

---

## 2. 目录结构

```
douyin-desktop/
├── main.py                           # 应用入口（浏览器检测 + 启动窗口）
├── requirements.txt                  # Python 依赖
├── build.py                          # 构建脚本
├── build_macos.sh                    # macOS 构建脚本
├── build_windows.bat                 # Windows 构建脚本
├── DouyinScraperPro.spec             # PyInstaller 打包配置
│
├── app/                              # 桌面应用主模块
│   ├── __init__.py
│   ├── main_window.py                # 主窗口（侧边栏导航 + 主工作区）
│   ├── worker.py                     # QThread 采集线程
│   ├── task_store.py                 # 任务持久化存储
│   ├── styles.py                     # 暗色主题 QSS 样式（521 行）
│   ├── theme.py                      # 霓虹色常量
│   │
│   ├── skills/                       # 技能系统
│   │   ├── __init__.py
│   │   ├── _skill_base.py            # 技能基类
│   │   ├── registry.py               # 技能注册表
│   │   └── skill_loader.py           # 技能加载器
│   │
│   └── widgets/                      # UI 组件
│       ├── __init__.py
│       ├── common_widgets.py         # 通用组件
│       ├── search_panel.py           # 搜索采集面板
│       ├── progress_panel.py         # 终端风格日志面板
│       ├── results_panel.py          # 结果查看（树形 + JSON）
│       ├── script_panel.py           # AI 剧本生成面板
│       ├── script_editor/            # 剧本编辑器
│       │   ├── __init__.py
│       │   ├── editor.py             # 编辑器核心
│       │   ├── preview.py            # 预览组件
│       │   └── seo_worker.py         # SEO 分析后台
│       ├── video_creation_panel.py   # 视频创作面板
│       ├── video_analysis_panel.py   # 视频分析面板
│       ├── dy_tools_panel.py         # 抖音工具面板（聚合入口）
│       ├── dy_tools/                 # 抖音工具集
│       │   ├── __init__.py
│       │   ├── account_tab.py        # 账号管理
│       │   ├── aigc_tab.py           # AI 内容生成
│       │   ├── api_search_tab.py     # API 搜索
│       │   ├── interaction_tab.py    # 互动管理
│       │   ├── skill_executor_tab.py # 技能执行
│       │   └── trending_tab.py        # 热门内容
│       ├── money_printer_panel.py     # （功能面板占位）
│       ├── settings_page.py           # 设置页面（环境检查 + AI 配置）
│       ├── settings_dialog.py         # 设置弹窗（旧版）
│       ├── environment_panel.py       # Chrome/CDP/Cookie 环境管理
│       └── creation/                  # 创作相关组件
│           ├── __init__.py
│           ├── dialogs.py             # 创作对话框
│           └── panels.py              # 创作面板
│
├── core_modules/                     # 核心业务模块
│   ├── douyin_downloader.py          # 视频下载 & 语音转文字
│   ├── douyin_browser_automation.py  # 核心采集脚本（搜索 + 评论 + 私信）
│   ├── xhs_search.py                 # 小红书搜索功能
│   │
│   ├── browser/                      # 浏览器操作封装
│   │   ├── __init__.py
│   │   ├── actions.py                # 搜索、滚动、评论提取等操作
│   │   ├── cookies.py                # Cookie 加载与注入
│   │   └── locators.py               # DOM 定位器（纯文本定位）
│   │
│   ├── dy_cli/                       # 命令行工具
│   │   ├── __init__.py
│   │   ├── main.py                   # CLI 主入口
│   │   ├── engines/                  # 引擎层
│   │   │   ├── __init__.py
│   │   │   ├── api_client.py         # API 客户端
│   │   │   └── playwright_client.py  # Playwright 客户端
│   │   ├── commands/                 # 命令集合
│   │   │   ├── __init__.py
│   │   │   ├── account.py            # 账号相关
│   │   │   ├── analytics.py          # 数据分析
│   │   │   ├── auth.py               # 认证
│   │   │   ├── config_cmd.py         # 配置
│   │   │   ├── download.py           # 下载
│   │   │   ├── dreamina.py           # Dreamina 操作
│   │   │   ├── history.py            # 历史记录
│   │   │   ├── init.py               # 初始化
│   │   │   ├── interact.py           # 互动
│   │   │   ├── live.py               # 直播
│   │   │   ├── profile.py            # 主页
│   │   │   ├── prompt.py             # 提示词
│   │   │   ├── publish.py            # 发布
│   │   │   ├── search.py             # 搜索
│   │   │   └── trending.py           # 热门
│   │   └── utils/                    # 工具函数
│   │       ├── __init__.py
│   │       ├── config.py             # 配置管理
│   │       ├── constants.py          # 常量定义
│   │       ├── envelope.py           # 数据封装
│   │       ├── export.py             # 导出
│   │       ├── index_cache.py        # 索引缓存
│   │       ├── output.py             # 输出
│   │       ├── signature.py          # 签名
│   │       └── storage.py            # 存储
│   │
│   ├── mpt_services/                 # AI 内容创作服务
│   │   ├── __init__.py
│   │   ├── config.py                 # 服务配置
│   │   ├── llm.py                    # 大语言模型
│   │   ├── material.py               # 素材处理
│   │   ├── subtitle.py               # 字幕处理
│   │   ├── task_runner.py           # 任务运行器
│   │   ├── video_builder.py         # 视频构建
│   │   └── voice.py                  # 语音处理
│   │
│   └── xhs/                          # 小红书相关
│       ├── __init__.py
│       ├── actions.py                # 小红书操作
│       └── locators.py              # 定位器
│
├── models/                           # AI 提示词模板
│   ├── script.md                    # 剧本生成系统提示词
│   └── storyboard.md                # 分镜拆分系统提示词
│
├── tests/                            # 测试目录
│   └── app/
│       └── skills/
│           ├── __init__.py
│           ├── test_loader.py        # 技能加载测试
│           └── test_registry.py     # 技能注册测试
│
├── docs/                             # 文档目录
│   └── project-structure.md         # 本文档
│
└── resource/                         # 资源文件目录
```

---

## 3. 目录职责说明

### 3.1 `app/` — 桌面应用主模块

桌面应用的核心模块，包含主窗口、后台线程和 UI 组件。

| 文件/目录 | 职责 |
|-----------|------|
| `main_window.py` | 主窗口，顶部菜单栏 + 左侧导航栏 + 主工作区，支持 6 个功能页面切换 |
| `worker.py` | QThread 采集线程，负责在后台执行数据采集任务 |
| `task_store.py` | 任务持久化存储，管理采集任务的生命周期 |
| `styles.py` | PyQt 暗色主题 QSS 样式，521 行 |
| `theme.py` | 霓虹色常量（NEON_RED/GREEN/BLUE） |
| `skills/` | 技能系统，支持动态加载和注册功能扩展 |

### 3.2 `app/widgets/` — UI 组件

| 文件/目录 | 职责 |
|-----------|------|
| `search_panel.py` | 搜索采集面板，关键词输入、筛选条件、开始/停止控制 |
| `progress_panel.py` | 终端风格日志面板，显示采集进度和运行日志 |
| `results_panel.py` | 结果查看面板，树形结构 + JSON 视图 |
| `script_panel.py` | AI 剧本生成面板，引用采集数据生成推广剧本 |
| `video_creation_panel.py` | 视频创作面板，剧本拆分分镜 → 生图 → 视频 |
| `video_analysis_panel.py` | 视频分析面板 |
| `dy_tools_panel.py` | 抖音工具聚合面板 |
| `dy_tools/` | 抖音工具集（账号、AIGC、API搜索、互动、热门等） |
| `settings_page.py` | 设置页面，包含环境检查、AI 模型配置 |
| `environment_panel.py` | Chrome/CDP/Cookie 环境管理 |

### 3.3 `core_modules/` — 核心业务模块

| 目录 | 职责 |
|------|------|
| `browser/` | Playwright 浏览器操作封装，纯 DOM 定位（防反爬） |
| `dy_cli/` | 命令行工具集，支持各种抖音操作命令 |
| `mpt_services/` | AI 内容创作服务（大模型、生图、生视频等） |
| `xhs/` | 小红书搜索功能模块 |

| 文件 | 职责 |
|------|------|
| `douyin_downloader.py` | 抖音视频下载、无水印链接提取、音频提取、语音转文字 |
| `douyin_browser_automation.py` | 核心采集脚本，搜索 + 评论提取 + 私信发送 |
| `xhs_search.py` | 小红书笔记搜索 |

### 3.4 `core_modules/browser/` — 浏览器操作封装

| 文件 | 职责 |
|------|------|
| `actions.py` | 搜索、滚动、视频处理、评论提取、用户信息提取、私信发送等 |
| `cookies.py` | Cookie 加载与注入，支持免登录访问 |
| `locators.py` | DOM 定位器，纯文本定位策略（不依赖动态 class） |

---

## 4. 入口点

### 4.1 应用入口

```
main.py
```

- 检测 Chromium 浏览器是否可用
- 设置 Playwright 浏览器路径和国内镜像
- 启动 PyQt6 主窗口

```bash
python main.py
```

### 4.2 命令行入口

```
core_modules/dy_cli/main.py
```

支持子命令：search, download, account, publish 等

```bash
python core_modules/dy_cli/main.py search -s "关键词"
```

### 4.3 视频下载入口

```
core_modules/douyin_downloader.py
```

```bash
# 获取视频信息
python douyin_downloader.py --link "分享链接" --action info

# 下载视频
python douyin_downloader.py --link "分享链接" --action download --output ./videos

# 提取文案（需要 API_KEY）
python douyin_downloader.py --link "分享链接" --action extract --output ./output
```

---

## 5. 数据流概览

```
用户操作 (PyQt6 UI)
    │
    ▼
app/worker.py (QThread 采集线程)
    │
    ▼
core_modules/browser/actions.py (浏览器自动化)
    │                          │
    ▼                          ▼
douyin_browser_automation.py   xhs_search.py
    │                          │
    ▼                          ▼
抖音网页                     小红书网页
    │
    ▼
app/task_store.py (持久化存储)
    │
    ▼
results_panel.py / JSON 文件
```

---

## 6. 主要配置文件

| 文件 | 用途 |
|------|------|
| `~/.dy/desktop_settings.json` | 用户设置（CDP地址、API密钥、存储路径等） |
| `models/script.md` | 剧本生成系统提示词 |
| `models/storyboard.md` | 分镜拆分系统提示词 |
| `requirements.txt` | Python 依赖列表 |
