# 抖音数据采集 & AI 内容创作桌面应用

基于 PyQt6 + Playwright 的多端桌面应用，集成抖音数据采集、AI 剧本生成、视频分镜创作。

---

## 功能特性

### 数据采集
| 模块 | 功能 |
|------|------|
| 搜索采集 | 关键词搜索 + 评论关键字匹配 + 发布时间筛选 + 采集数量控制 |
| 视频数据 | 提取视频标题、点赞数、评论数、收藏数、分享数 |
| 评论采集 | 滚动加载全部评论，提取用户名/内容/时间/点赞 |
| 用户匹配 | 评论关键字匹配，自动进入用户主页提取昵称 + 抖音号 |
| 视频解析 | 通过分享链接提取视频文案（下载→提取音频→语音转文字） |

### AI 创作
| 模块 | 功能 |
|------|------|
| 剧本生成 | 引用采集数据 + 视频文案解析 → AI 流式生成抖音推广剧本 |
| 视频创作 | 剧本拆分分镜 → 分镜生图 → 图生视频 |
| 系统提示词 | 预置 douyin_script.md / storyboard_split.md，自动注入 |

### AI 模型配置
| 类型 | 用途 | 默认 |
|------|------|------|
| 文字大模型 | 剧本生成 / 分镜拆分 | DeepSeek / 自定义 OpenAI 兼容 |
| 图片大模型 | 分镜生图 | SiliconFlow / MiniMax 自动适配 |
| 视频大模型 | 图生视频 | 待对接 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    MainWindow                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │搜索采集  │  │剧本生成  │  │视频创作  │  │结果查看  │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │
│       │            │            │            │        │
│  DouyinWorker  ScriptWorker  SceneWorker  TaskStore │
│       │            │            │            │        │
│  ┌────┴────────────┴────────────┴────────────┴────┐  │
│  │              ~/.dy/ (持久化存储)                 │  │
│  │  settings.json  /  results/  /  core_modules/       │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 项目结构

```
douyin-desktop/
├── main.py                          # 入口（浏览器检测 + 启动窗口）
├── requirements.txt                 # PyQt6 + playwright + openai + Pillow
├── core_modules/
│   ├── douyin_browser_automation.py # 核心采集脚本
│   └── douyin_downloader.py         # 视频下载 & 语音转文字
├── models/
│   ├── douyin_script.md             # 剧本生成系统提示词
│   └── storyboard_split.md          # 分镜拆分系统提示词
├── app/
│   ├── main_window.py               # 主窗口（侧边栏 + 6 页签）
│   ├── worker.py                    # QThread 采集线程
│   ├── task_store.py                # 任务持久化存储
│   ├── theme.py                     # 霓虹色常量
│   ├── styles.py                    # 暗色主题 QSS（521 行）
│   └── widgets/
│       ├── search_panel.py          # 搜索面板
│       ├── progress_panel.py        # 终端风格日志
│       ├── results_panel.py         # 结果查看（树形 + JSON）
│       ├── script_panel.py          # AI 剧本生成
│       ├── video_creation_panel.py  # 视频创作（分镜 + 生图）
│       ├── settings_page.py         # 设置（环境检查 + AI 配置）
│       ├── environment_panel.py     # Chrome/CDP/Cookie 环境管理
│       └── settings_dialog.py       # 设置弹窗（旧版）
└── .github/workflows/build.yml      # CI 自动构建 Windows EXE
```

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.10 |
| PyQt6 | ≥ 6.5 |
| Playwright | ≥ 1.40 |
| openai | ≥ 1.0 |
| Chrome | 最新稳定版 |

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 快速开始

### 1. 启动 Chrome CDP

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-cdp-profile &

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=C:\tmp\chrome-cdp-profile
```

### 2. 登录抖音（可选）

在应用「设置 → 环境检查」中：启动 CDP → 登录抖音 → 完成登录保存 Cookie。

### 3. 配置 AI 模型

在「设置 → 连接配置」中填入文字/图片/视频大模型的 API 地址、密钥、模型名称。

### 4. 启动应用

```bash
cd douyin-desktop
python main.py
```

---

## 页面说明

### 搜索采集
- 关键词搜索 + 评论关键字匹配
- 发布时间筛选、排序方式、采集数量控制
- 一键开始/停止

### 剧本生成
- 引用采集任务数据（视频标题、评论内容）
- 可选解析视频文案（通过分享链接提取语音转文字）
- AI 流式生成剧本，思维过程显示在控制台
- 生成结果可保存到持久化存储

### 视频创作
- 选择已保存的剧本 → AI 拆分为分镜
- 每个分镜可独立生成图片（支持上传参考图保持风格一致）
- 支持竖版 9:16 / 横版 16:9 两种视频方向
- 图片大模型自动适配 OpenAI / SiliconFlow / MiniMax 格式

### 运行日志
- 彩色分类日志流，实时滚动
- 进度条可视化

### 结果查看
- 左侧树形视图展示视频及匹配用户/评论
- 点击条目右侧显示完整 JSON
- 可导出 JSON 文件

### 设置
- 环境检查：Chrome 检测 / CDP 连接 / Cookie 管理
- 连接配置：CDP 地址 / Cookie 路径 / 存储路径
- AI 配置：文字/图片/视频大模型独立配置，含测试按钮

---

## 输出 JSON 格式

```json
{
  "search_term": "核桃手串",
  "match_keywords": ["怎么买", "多少钱"],
  "timestamp": "20260429_153000",
  "total_videos": 3,
  "videos": [
    {
      "index": 1,
      "title": "百元手串的天花板",
      "video_id": "74938271928394821",
      "likes": "7038",
      "comments_count": "807",
      "collects": "807",
      "shares": "2029",
      "comments": [],
      "matched_users": [
        {
          "username": "用户A",
          "shortId": "douyin12345",
          "comment_content": "这个怎么买啊",
          "comment_time": "3天前",
          "comment_likes": "12"
        }
      ]
    }
  ]
}
```

---

## 命令行用法

```bash
# 基础搜索
python core_modules/douyin_browser_automation.py -s "核桃手串"

# 带评论关键字
python core_modules/douyin_browser_automation.py -s "核桃手串" -k "怎么买|多少钱"

# 视频文案提取
python core_modules/douyin_downloader.py --link "抖音分享链接" --action extract --output ./output
```

---

## 技术细节

### 反爬策略
- CDP 连接模式，复用已有 Chrome 用户数据目录
- 模拟人工操作：随机延迟，逐字符输入
- 纯 textContent + tagName + data-e2e 定位，零 class 依赖
- Cookie 自动刷新，每次采集后更新

### AI 模型适配
- 文字模型：OpenAI 兼容 API（支持 DeepSeek、MiniMax 等）
- 图片模型：自动解析 images/data/data.image_urls 等多种返回格式
- 流式输出：`<think>` 标签内容到控制台，正文流式显示到界面
