# 抖音数据采集桌面应用

基于 PyQt6 + Playwright 的多端桌面应用，通过 Chrome CDP 协议自动化采集抖音搜索结果中的视频数据。

---

## 功能特性

| 模块 | 功能 |
|------|------|
| 搜索采集 | 关键词搜索 + 评论关键字匹配 + 发布时间筛选 + 采集数量控制 |
| 筛选面板 | 自动定位筛选面板（纯文本 DOM 匹配，零 class 依赖），支持「最新发布」排序 |
| 视频数据 | 提取视频标题、点赞数、评论数、收藏数、分享数 |
| 评论采集 | 滚动加载全部评论，提取用户名/内容/时间/点赞/作者标记 |
| 用户匹配 | 在评论中匹配关键字，自动进入用户主页提取昵称 + 抖音号 |
| 结果输出 | 统一 JSON 文件，按视频分组，记录完整互动数据 |
| 实时日志 | 彩色分类日志流，运行进度可视化 |

---

## 系统架构

```
SearchPanel ──start_requested──▶ MainWindow ──▶ DouyinWorker(QThread)
                                                     │
                          ┌──────────────────────────┼──────────────────────────┐
                          ▼                          ▼                          ▼
                     log_signal               progress_signal            finished_signal
                          │                          │                          │
                          ▼                          ▼                          ▼
                   ProgressPanel              ProgressPanel              ResultsPanel
                   (实时日志)                  (进度条)                   (任务结果查看)
```

### 核心设计

- **QThread 后台线程**：采集逻辑完全隔离，UI 永不冻结
- **Signal/Slot 通信**：`redirect_stdout` 实时捕获脚本日志，按级别染色
- **纯文本 DOM 定位**：抖音 class 名全为动态 hash，所有选择器基于 `data-e2e` + `textContent` + `tagName`，零 class 依赖
- **环境变量桌面模式**：`DOUYIN_DESKTOP_MODE=1` 控制脚本在完成任务后直接返回，不阻塞线程

---

## 项目结构

```
douyin-desktop/
├── main.py                          # 入口文件
├── requirements.txt                 # PyQt6 + playwright
├── douyin_browser_automation.py     # 核心采集脚本（1200+ 行）
├── app/
│   ├── __init__.py
│   ├── main_window.py               # 主窗口（3 页签 + 菜单 + 状态栏）
│   ├── worker.py                    # QThread 后台工作线程
│   ├── styles.py                    # 暗色主题 QSS（350+ 行）
│   └── widgets/
│       ├── __init__.py
│       ├── search_panel.py          # 搜索面板：关键词/关键字/筛选/控制
│       ├── progress_panel.py        # 进度面板：实时日志 + 进度条
│       ├── results_panel.py         # 结果面板：树形查看 + JSON 导出
│       └── settings_dialog.py       # 设置对话框：CDP/Cookie 配置
└── resources/                       # 资源目录（图标等）
```

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.10 |
| PyQt6 | ≥ 6.5 |
| Playwright | ≥ 1.40 |
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
  --user-data-dir=/tmp/chrome-cdp-profile \
  --disable-blink-features=AutomationControlled &

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=C:\tmp\chrome-cdp-profile ^
  --disable-blink-features=AutomationControlled
```

### 2. 配置 Cookie（可选）

在 Chrome CDP 窗口中登录抖音，然后用 Playwright 导出 Cookie：

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]
    cookies = context.cookies()
    import json
    with open("cookies.json", "w") as f:
        json.dump({"cookies": cookies}, f)
```

在应用菜单「设置 → Cookie / CDP 配置」中指定该文件路径。

### 3. 启动应用

```bash
cd douyin-desktop
python main.py
```

---

## 页面说明

### 搜索采集

```
┌──────────────────────────────────────────┐
│  抖音数据采集                              │
│  搜索关键词，自动提取视频标题、评论及用户数据   │
│                                          │
│  ┌─ 搜索 ────────────────────────────┐   │
│  │  输入搜索关键词，如"核桃手串"       │   │
│  │                                    │   │
│  │  ☑ 启用评论关键字匹配               │   │
│  │  ┌──────────────┐ ┌──┐            │   │
│  │  │ 关键字 1      │ │− │            │   │
│  │  └──────────────┘ └──┘            │   │
│  │  [+ 添加关键字]                     │   │
│  └────────────────────────────────────┘   │
│                                          │
│  ┌─ 筛选条件 ─────────────────────────┐   │
│  │  发布时间  [不限        ▾]         │   │
│  │  ☑ 按最新发布排序                   │   │
│  │  采集数量  [5 个视频  ▴▾]          │   │
│  └────────────────────────────────────┘   │
│                                          │
│              [⏹ 停止采集]  [▶ 开始采集]    │
└──────────────────────────────────────────┘
```

- **搜索关键词**：必填，输入抖音搜索词
- **启用评论关键字匹配**：开关控制，开启后至少填写一个关键字
- **关键字输入框**：独立输入，不手工输入 `|` 分隔符；点 `+` 增加，点 `−` 删除
- **发布时间**：不限 / 一天内 / 一周内 / 半年内
- **按最新发布排序**：勾选后自动打开筛选面板选取「最新发布」
- **采集数量**：1-50 个视频

### 运行日志

- 彩色分类：info(灰) / success(绿) / warn(黄) / error(红)
- 实时滚动，最大保留 5000 行
- 底部进度条 + 百分比

### 结果查看

```
┌── 视频树 ──────────────┬── JSON 详情 ──────────┐
│ 搜索: 核桃手串          │ {                     │
│ ▸ 百元手串的天花板...    │   "index": 1,         │
│   👍7038 💬807 ⭐807    │   "title": "...",     │
│   @用户A · douyin123   │   "likes": "7038",    │
│     怎么买 · 3天前      │   ...                 │
│   @用户B · douyin456   │ }                     │
│     多少钱 · 1周前      │                       │
└────────────────────────┴───────────────────────┘
```

- 左侧树形视图展示视频及匹配用户/评论
- 点击条目右侧显示完整 JSON
- 可导出为 JSON 文件

### 设置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| CDP 地址 | Chrome 调试端口 | `http://127.0.0.1:9222` |
| Cookie 文件 | 免登录 cookies.json 路径 | `~/.dy/cookies/default.json` |
| 运行模式 | CDP 连接 / 启动新浏览器 | CDP 连接 |

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
      "title": "百元手串的天花板，一百块盘出千元效果",
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
          "comment_likes": "12",
          "is_author": false
        }
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `search_term` | 搜索关键词 |
| `match_keywords` | 评论匹配关键字列表 |
| `timestamp` | 采集时间戳 |
| `total_videos` | 有效视频数（跳过无评论的） |
| `videos[].title` | 视频标题 |
| `videos[].likes` | 点赞数 |
| `videos[].comments_count` | 评论总数 |
| `videos[].collects` | 收藏数 |
| `videos[].shares` | 分享数 |
| `videos[].comments` | 全部评论（无关键字模式） |
| `videos[].matched_users` | 匹配到的用户（关键字模式） |
| `matched_users[].shortId` | 抖音号 |
| `matched_users[].comment_content` | 匹配的评论内容 |
| `matched_users[].comment_time` | 评论时间 |

---

## 命令行用法

采集脚本也可独立在终端运行：

```bash
# 基础搜索（最新发布 + 不限时间 + 5 个视频）
python douyin_browser_automation.py -s "核桃手串"

# 带评论关键字
python douyin_browser_automation.py -s "核桃手串" -k "怎么买|多少钱"

# 指定时间筛选（1=一天内 2=一周内 3=半年内）
python douyin_browser_automation.py -s "核桃手串" -t 1 -n 10
```

---

## 技术细节

### 反爬策略

- CDP 连接模式，复用已有 Chrome 用户数据目录
- 模拟人工操作：随机 0.5-1.0 秒延迟，逐字符输入
- 禁止依赖动态 class 名，全部使用 `data-e2e` + 文本内容定位
- 筛选面板通过「最小面积法」定位，兼容不同页面（`/search/` vs `/jingxuan/search/`）

### 数据提取

| 数据 | 定位方式 |
|------|----------|
| 当前播放视频 | `[data-e2e="feed-active-video"]` |
| 视频标题 | `[data-e2e="video-desc"]` → 叶子 SPAN |
| 点赞 | `[data-e2e="video-player-digg"]` |
| 收藏 | `[data-e2e="video-player-collect"]` |
| 分享 | `[data-e2e="video-player-share"]` |
| 评论数 | `全部评论(N)` 正则 或 `[data-e2e="feed-comment-icon"]` |
| 评论列表 | `[data-e2e="comment-list"]` → `[data-e2e="comment-item"]` |
| 筛选面板 | 含「排序依据」+「发布时间」文本的最小 div |
| 用户名 | `a[href*="/user/"]` 排除 `[data-e2e="live-avatar"]` |
| 抖音号 | user-info 内 `span` 含「抖音号：」前缀 |
