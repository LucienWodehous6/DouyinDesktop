"""
浏览器操作 — 搜索、滚动、视频处理、评论提取等
"""

import json
import os
import re
import sys
import time
import random
from playwright.sync_api import sync_playwright


def _get_dm_sent_store():
    """延迟导入，避免循环依赖"""
    from app.task_store import get_dm_sent_store
    return get_dm_sent_store()


def random_delay(min_s=0.5, max_s=1.0):
    """随机延迟，模拟人工操作间隔"""
    time.sleep(random.uniform(min_s, max_s))


def type_human_like(page, element, text, delay_ms=100):
    """
    模拟人工逐字符输入
    - 先清空输入框
    - 每个字符间隔 delay_ms 毫秒
    - 不使用 fill()，用 type() 逐字输入
    """
    # 点击聚焦
    element.click()
    time.sleep(0.3)

    # 逐字符输入
    for char in text:
        element.type(char, delay=delay_ms)
    print(f"[✓] 已模拟输入: {text}")


def get_first_video_item(page, timeout=15000):
    """
    从抖音搜索结果瀑布流中定位第一个视频/图文内容。
    不依赖动态 hash class，靠 DOM 结构和文本判断。

    瀑布流结构:
      div[id^="waterfall_item_"] -> 每个内容项（绝对定位）
        div.search-result-card
          ├─ 视频/图文卡片（包含背景图、时长、点赞数）
          └─ "相关搜索"卡片（包含文字"相关搜索"）
    """
    print("[*] 等待搜索结果加载...")
    page.wait_for_selector('[id^="waterfall_item_"]', timeout=timeout)
    time.sleep(2)  # 等瀑布流布局完成

    # 纯 DOM 结构判断，不依赖动态 class
    video_id = page.evaluate("""() => {
        const items = document.querySelectorAll('[id^="waterfall_item_"]');
        const candidates = [];
        for (const item of items) {
            const card = item.querySelector('.search-result-card');
            if (!card) continue;

            // 跳过"相关搜索"卡片：包含文本"相关搜索"
            if (card.textContent.includes('相关搜索')) continue;

            // 解析 translate 值确定位置
            const style = item.getAttribute('style') || '';
            const m = style.match(/translate\\(([\\d.]+)px,\\s*([\\d.]+)px\\)/);
            const x = m ? parseFloat(m[1]) : 9999;
            const y = m ? parseFloat(m[2]) : 9999;

            candidates.push({ id: item.id, x: x, y: y });
        }

        // 按 Y 坐标排序（同一行），若 Y 相同按 X 排序
        candidates.sort((a, b) => a.y - b.y || a.x - b.x);

        return candidates.length > 0 ? candidates[0].id : null;
    }""")

    if video_id:
        print(f"[✓] 定位到第一个内容: #{video_id}")
        return page.locator(f"#{video_id}")
    else:
        print("[!] 未找到视频内容")
        return None


def click_first_video(page, timeout=15000):
    """定位并点击第一个视频内容，进入视频播放页，处理弹窗和 X 键"""
    first = get_first_video_item(page, timeout)
    if not first:
        return False

    first.scroll_into_view_if_needed()
    random_delay()
    first.click()
    print("[✓] 已点击第一个视频")

    # 处理弹窗
    dismiss_dialog_if_present(page)

    # 按下 X 键
    random_delay()
    page.keyboard.press("x")
    print("[✓] 已按下 X 键")

    return True


# ========== 筛选面板 ==========
#
# 注意：抖音的 class 名全部是动态 hash，每次页面加载都可能变化。
# 以下所有函数禁止使用 class 选择器，全部通过文本内容定位。
#

# 分区标签文本（固定不变）
_SECTION_NAMES = ["排序依据", "发布时间", "视频时长", "搜索范围", "内容形式"]


def _find_filter_panel(page):
    """
    内部函数：在页面中定位筛选面板。

    策略：查找同时包含"排序依据"和"发布时间"的可见 div，
    选面积最小的那个（排除外层大布局容器）。
    """
    return page.evaluate("""() => {
        const allDivs = document.querySelectorAll('div');
        let panel = null;
        let minArea = Infinity;
        for (const d of allDivs) {
            const text = d.textContent;
            if (!text.includes('排序依据')) continue;
            if (!text.includes('发布时间')) continue;
            const r = d.getBoundingClientRect();
            if (r.width < 200 || r.height < 100) continue;
            const area = r.width * r.height;
            if (area < minArea) {
                panel = d;
                minArea = area;
            }
        }
        return panel !== null;
    }""")


def is_filter_panel_open(page):
    """判断筛选面板是否处于打开状态（纯文本匹配）"""
    return _find_filter_panel(page)


def toggle_filter_panel(page, open=True, timeout=5000):
    """
    打开或关闭筛选面板。

    面板通过鼠标悬浮在"筛选"按钮上触发。
    open=True:  悬浮打开面板，等待面板出现
    open=False: 移开鼠标关闭面板
    """
    filter_btn = page.locator('span:has-text("筛选")').first
    filter_btn.wait_for(state="visible", timeout=timeout)

    if open:
        if is_filter_panel_open(page):
            print("[*] 筛选面板已处于打开状态")
            return True
        print("[*] 悬浮打开筛选面板...")
        filter_btn.hover()
        time.sleep(0.5)
        # 轮询等待面板出现（最多等 timeout）
        waited = 0
        while waited < timeout:
            if is_filter_panel_open(page):
                time.sleep(0.3)
                print("[✓] 筛选面板已打开")
                random_delay()
                return True
            time.sleep(0.2)
            waited += 200
        print("[!] 筛选面板未能打开")
        return False
    else:
        if not is_filter_panel_open(page):
            return True
        print("[*] 关闭筛选面板...")
        page.mouse.move(10, 10)
        time.sleep(0.5)
        if not is_filter_panel_open(page):
            print("[✓] 筛选面板已关闭")
        random_delay()
        return True


def get_filter_options(page, timeout=5000):
    """
    获取筛选面板中所有选项及其选中状态（纯文本匹配）。

    返回 dict:
    {
        "排序依据": [{"text": "综合排序", "selected": True}, ...],
        ...
    }
    面板未打开时返回空 dict。
    """
    if not is_filter_panel_open(page):
        print("[!] 筛选面板未打开，请先调用 toggle_filter_panel(page, open=True)")
        return {}

    return page.evaluate("""() => {
        // 找最小面积的面板
        let panel = null;
        let minArea = Infinity;
        const allDivs = document.querySelectorAll('div');
        for (const d of allDivs) {
            const text = d.textContent;
            if (!text.includes('排序依据')) continue;
            if (!text.includes('发布时间')) continue;
            const r = d.getBoundingClientRect();
            if (r.width < 200 || r.height < 100) continue;
            const area = r.width * r.height;
            if (area < minArea) { panel = d; minArea = area; }
        }
        if (!panel) return {};

        const sectionNames = ['排序依据', '发布时间', '视频时长', '搜索范围', '内容形式'];
        const sections = {};

        // 遍历面板内所有元素：DIV=分区标签, SPAN=选项
        let currentSection = null;
        let currentOptions = [];
        const allEls = panel.querySelectorAll('*');

        for (const el of allEls) {
            const text = el.textContent.trim();
            if (!text) continue;
            const tag = el.tagName;

            // 分区标签：DIV 且文本精确匹配
            if (tag === 'DIV' && sectionNames.includes(text)) {
                if (currentSection && currentOptions.length > 0) {
                    const seen = new Set();
                    sections[currentSection] = currentOptions.filter(o => {
                        if (seen.has(o.text)) return false;
                        seen.add(o.text);
                        return true;
                    });
                }
                currentSection = text;
                currentOptions = [];
                continue;
            }

            // 选项：SPAN，文本长度 2-10
            if (currentSection && tag === 'SPAN' && text.length >= 2 && text.length <= 10) {
                // 选中判断：通过计算样式颜色（抖音选中项为红色高亮 rgb(254,44,85)）
                const color = getComputedStyle(el).color;
                const selected = color === 'rgb(254, 44, 85)' || color === 'rgb(255, 0, 0)';
                currentOptions.push({ text: text, selected: selected });
            }
        }

        if (currentSection && currentOptions.length > 0) {
            const seen = new Set();
            sections[currentSection] = currentOptions.filter(o => {
                if (seen.has(o.text)) return false;
                seen.add(o.text);
                return true;
            });
        }

        return sections;
    }""")


def apply_filter(page, section_name, option_text, timeout=5000):
    """
    在筛选面板中点击指定分区的指定选项，并等待页面刷新（纯文本匹配）。

    section_name: 如 "排序依据"、"发布时间"、"视频时长" 等
    option_text:  如 "最新发布"、"一天内"、"1-5分钟" 等

    返回 True/False。
    """
    if not is_filter_panel_open(page):
        print("[!] 筛选面板未打开，无法操作")
        return False

    print(f"[*] 应用筛选: {section_name} → {option_text}")

    clicked = page.evaluate("""({section, option}) => {
        // 找最小面积的面板
        let panel = null;
        let minArea = Infinity;
        const allDivs = document.querySelectorAll('div');
        for (const d of allDivs) {
            const t = d.textContent;
            if (!t.includes('排序依据')) continue;
            if (!t.includes('发布时间')) continue;
            const r = d.getBoundingClientRect();
            if (r.width < 200 || r.height < 100) continue;
            const area = r.width * r.height;
            if (area < minArea) { panel = d; minArea = area; }
        }
        if (!panel) return false;

        // 遍历所有子元素：DIV=分区标签, SPAN=选项
        const sectionNames = ['排序依据', '发布时间', '视频时长', '搜索范围', '内容形式'];
        const allEls = panel.querySelectorAll('*');
        let inSection = false;

        for (const el of allEls) {
            const text = el.textContent.trim();
            if (!text) continue;
            const tag = el.tagName;

            // 分区标签：DIV 精确匹配
            if (tag === 'DIV' && sectionNames.includes(text)) {
                inSection = (text === section);
                continue;
            }

            // 选项：SPAN 文本匹配
            if (inSection && tag === 'SPAN' && text === option) {
                el.click();
                return true;
            }
        }
        return false;
    }""", {"section": section_name, "option": option_text})

    if not clicked:
        print(f"  [!] 未找到选项: {section_name} → {option_text}")
        return False

    print(f"  [✓] 已点击: {option_text}")
    random_delay()

    print("[*] 等待搜索结果刷新...")
    time.sleep(3)

    try:
        page.wait_for_selector('[id^="waterfall_item_"]', timeout=15000)
        print("[✓] 筛选结果已加载")
        random_delay()
        return True
    except Exception:
        print("[!] 筛选结果未加载，可能触发了验证码")
        return False


def process_one_video(page, video_index, match_keywords=None, dm_message=None, browser=None):
    """
    处理当前正在播放的视频：提取标题、滚动评论区、提取评论、匹配关键字

    video_index: 第几个视频（从 0 开始）
    match_keywords: 匹配关键字列表或 None
    dm_message: 私信内容，为 None 则不发送
    browser: Playwright browser 对象，用于发送私信
    返回: dict { index, title, comments, matched_users }，无评论时返回 None
    """
    print(f"\n{'='*40}")
    print(f"[*] 处理第 {video_index + 1} 个视频")
    print(f"{'='*40}")

    # 提取视频标题
    random_delay()
    video_title = get_video_title(page)

    # 提取视频 ID
    random_delay()
    video_id = get_video_id(page)

    # 提取视频互动数据（点赞/评论/收藏/分享）
    random_delay()
    video_stats = get_video_stats(page)

    # 确保评论面板已打开（如果当前在详情页，切回评论）
    page.evaluate("""() => {
        const spans = document.querySelectorAll('span');
        for (const span of spans) {
            const t = span.textContent.trim();
            if (t === '评论') {
                const r = span.getBoundingClientRect();
                const color = getComputedStyle(span).color;
                // 选中标签为纯白，未选中带透明度
                if (color !== 'rgb(249, 249, 249)' && r.width > 20) {
                    span.click();
                }
                break;
            }
        }
    }""")
    random_delay()

    # 检查是否"暂无评论"
    has_no_comments = page.evaluate("""() => {
        return document.body.textContent.includes('暂无评论');
    }""")
    if has_no_comments:
        print("[!] 该视频暂无评论，跳过")
        return None

    # 滚动评论区加载全部评论
    random_delay()
    max_scrolls = getattr(sys.modules[__name__], '_MAX_SCROLLS', 50)
    scroll_comment_area(page, max_scrolls=max_scrolls)

    # 提取评论数据
    random_delay()
    comments = extract_comments(page)

    if not comments:
        print("[!] 未提取到评论，跳过")
        return None

    if match_keywords:
        # 有匹配关键字：匹配评论并提取用户信息，同时发送私信
        random_delay()
        user_profiles = match_comment_and_click_user(page, comments, match_keywords, dm_message=dm_message, browser=browser)
    else:
        user_profiles = []

    return {
        "index": video_index + 1,
        "video_id": video_id,
        "title": video_title,
        "likes": video_stats.get('likes', '0'),
        "comments_count": video_stats.get('comments', '0'),
        "collects": video_stats.get('collects', '0'),
        "shares": video_stats.get('shares', '0'),
        "comments": [] if match_keywords else comments,
        "matched_users": user_profiles if match_keywords else None,
    }


def go_next_video(page):
    """按 ↓ 键切换到下一个视频"""
    print("[*] 按 ↓ 进入下一个视频...")
    random_delay()
    page.keyboard.press("ArrowDown")
    time.sleep(3)  # 等待视频加载
    random_delay()
    # 处理可能再次弹出的弹窗
    dismiss_dialog_if_present(page)
    # 只在评论区未打开时按 X
    if not is_comment_panel_open(page):
        time.sleep(1)
        page.keyboard.press("x")
        print("[✓] 已按 X 打开评论区")
    print("[✓] 已切换到下一个视频")


def is_comment_panel_open(page):
    """判断评论区是否已打开"""
    open_state = page.evaluate("""() => {
        const list = document.querySelector('[data-e2e="comment-list"]');
        if (!list) return false;
        const rect = list.getBoundingClientRect();
        return rect.width > 0 && rect.height > 50;
    }""")
    return open_state


def dismiss_dialog_if_present(page, timeout=5000):
    """
    检测并关闭"我知道了"弹窗
    抖音视频详情页可能会弹出新手引导/提示弹窗
    """
    try:
        # 用文本内容定位，不依赖动态 class
        btn = page.locator('span:has-text("我知道了")').first
        btn.wait_for(state="visible", timeout=timeout)
        print('[*] 检测到"我知道了"弹窗，点击关闭...')
        time.sleep(0.3)
        btn.click()
        print("[✓] 弹窗已关闭")
    except Exception:
        pass  # 没有弹窗，正常跳过


def scroll_comment_area(page, max_scrolls=50):
    """
    在评论区域滚动，直到出现"暂时没有更多评论"或到达最大滚动次数
    每次滚动间隔 1 秒，模拟人工操作

    评论列表容器: div[data-e2e="comment-list"]
    """
    print(f"[*] 开始滚动评论区（最多 {max_scrolls} 次）...")

    # 等待评论区加载
    try:
        page.wait_for_selector('[data-e2e="comment-list"]', timeout=10000)
    except Exception:
        print("[!] 未找到评论区")
        return

    time.sleep(1)

    scroll_count = 0
    while scroll_count < max_scrolls:
        # 检查是否已到底
        stopped = page.evaluate("""() => {
            return document.body.textContent.includes('暂时没有更多评论');
        }""")

        if stopped:
            print(f'[✓] 检测到"暂时没有更多评论"，滚动 {scroll_count} 次后停止')
            break

        # 在评论区容器内向下滚动
        page.evaluate("""() => {
            const list = document.querySelector('[data-e2e="comment-list"]');
            if (list) {
                list.scrollBy(0, 3000);
            }
        }""")

        scroll_count += 1
        if scroll_count % 10 == 0:
            print(f"  已滚动 {scroll_count} 次...")

        time.sleep(1)

    print(f"[✓] 评论滚动完成，共 {scroll_count} 次")
    time.sleep(1)


def extract_comments(page):
    """
    提取评论区所有评论信息（含嵌套回复）

    结构:
      [data-e2e="comment-list"]
        [data-e2e="comment-item"]           ← 顶级评论
          .EpsntdUI → 用户名、内容、时间
          .replyContainer                   ← 嵌套回复区
            [data-e2e="comment-item"]       ← 作者回复等

    返回 list[dict]，嵌套回复挂在 replies 字段下
    """
    print("[*] 开始提取评论数据...")

    comments_data = page.evaluate("""() => {
        // 判断一个 span/文本是否在头像区域内
        function isInAvatar(el) {
            return !!(el.closest('[data-e2e="live-avatar"]') || el.closest('.comment-item-avatar'));
        }

        // 提取单条评论（不含嵌套回复）
        function parseComment(item) {
            try {
                // === 用户名 ===
                // 找所有用户链接，排除头像链接（含 live-avatar 组件）
                const allUserLinks = item.querySelectorAll('a[href*="/user/"]');
                let username = '';
                for (const link of allUserLinks) {
                    // 头像链接特征：包含 [data-e2e="live-avatar"]
                    // 注意：用户名链接内可能有 emoji <img>，不能简单判 img
                    if (link.querySelector('[data-e2e="live-avatar"]')) {
                        continue; // 头像链接，跳过
                    }
                    // 这是用户名链接，取深层 span 文本
                    const spans = link.querySelectorAll('span');
                    let bestText = '';
                    for (const s of spans) {
                        const t = s.textContent.trim();
                        if (t && t.length > 0 && t.length <= 50 && t !== '作者') {
                            bestText = t;
                        }
                    }
                    if (bestText) {
                        username = bestText;
                        break;
                    }
                }

                // === 作者标签 ===
                const authorTag = item.querySelector('[style*="rgb(254, 44, 85)"]');
                const isAuthor = !!authorTag;

                // === 评论内容 ===
                // 策略: 遍历所有 span，排除头像区、操作区、用户名区
                // 取剩余文本最长且不匹配已知模式的那个
                let commentText = '';
                const allSpans = item.querySelectorAll('span');
                for (const span of allSpans) {
                    // 只考虑叶子 span（无子 span）
                    if (span.querySelector('span')) continue;
                    const text = span.textContent.trim();
                    if (!text || text.length < 2) continue;
                    if (isInAvatar(span)) continue;
                    // 排除用户链接内和回复区的文本
                    if (span.closest('a[href*="/user/"]')) continue;
                    // 排除操作文字
                    if (/^(回复|分享|举报|删除|\\.{3}|作者|作者赞过)$/.test(text)) continue;
                    // 排除纯数字（点赞、楼层等）
                    if (/^\\d+(\\.\\d+)?万?$/.test(text)) continue;
                    // 排除时间格式
                    if (/^\\d{4}年|天前|月前|周前|小时前|分钟前|秒前/.test(text)) continue;
                    // 排除展开回复按钮
                    if (text.startsWith('展开') && text.includes('条回复')) continue;
                    // 排除和用户名相同的文本（短评论可能和用户名一样长）
                    if (username && text === username) continue;

                    // 取文本最长的（评论内容通常最长）
                    if (text.length > commentText.length && text.length <= 200) {
                        commentText = text;
                    }
                }

                // === 时间 ===
                // 匹配: "X天前·江苏", "X月前·河南", "X周前·北京", "X小时前", "XXXX年X月X日"
                let time = '';
                const timeRegex = /\\d+天前|\\d+月前|\\d+周前|\\d+小时前|\\d+分钟前|\\d{4}年\\d{1,2}月\\d{1,2}日/;
                for (const span of allSpans) {
                    const text = span.textContent.trim();
                    if (timeRegex.test(text)) {
                        time = text;
                        break;
                    }
                }

                // === 点赞数 ===
                let likes = '0';
                // 点赞 span 在 heart SVG 旁边，文本是纯数字或 "X.X万"
                const likeSpans = item.querySelectorAll('p span');
                for (const span of likeSpans) {
                    const text = span.textContent.trim();
                    if (/^\\d+(\\.\\d+)?万?$/.test(text) && text.length <= 8) {
                        likes = text;
                        break;
                    }
                }

                return {
                    username: username,
                    content: commentText,
                    time: time,
                    likes: likes,
                    isAuthor: isAuthor
                };
            } catch(e) {
                return null;
            }
        }

        const commentList = document.querySelector('[data-e2e="comment-list"]');
        if (!commentList) return [];

        const results = [];
        const allItems = commentList.querySelectorAll(':scope > div > [data-e2e="comment-item"]');

        for (const item of allItems) {
            const comment = parseComment(item);
            if (!comment) continue;

            // 检查嵌套回复
            const replyContainer = item.querySelector('.replyContainer');
            if (replyContainer) {
                comment.replies = [];
                const replyItems = replyContainer.querySelectorAll('[data-e2e="comment-item"]');
                for (const reply of replyItems) {
                    const r = parseComment(reply);
                    if (r) comment.replies.push(r);
                }
            }

            if (comment && comment.content) {
                results.push(comment);
            }
        }

        return results;
    }""")

    # 统计总条数（含回复）
    total = len(comments_data) + sum(len(c.get('replies', [])) for c in comments_data)
    print(f"[✓] 提取了 {len(comments_data)} 条评论（含 {total - len(comments_data)} 条回复）")
    return comments_data


def get_video_id(page):
    """从页面 URL 提取当前视频 ID（纯 URL 正则，零 class 依赖）"""
    try:
        vid = page.evaluate("""() => {
            const url = location.href;
            // /video/ 页面
            let m = url.match(/\\/video\\/(\\d{15,20})/);
            if (m) return m[1];
            // 搜索预览 modal_id
            m = url.match(/modal_id=(\\d{15,20})/);
            if (m) return m[1];
            return '';
        }""")
        if vid:
            print(f"  视频ID: {vid}")
        return vid or ''
    except Exception:
        return ''


def get_video_ai_notes(page, timeout=10000):
    """
    点击「详情」标签，提取 AI 笔记内容和视频描述。
    完成后切回「评论」标签。

    返回 dict: {"description": "...", "ai_notes": "..."}
    """
    print("[*] 提取 AI 笔记...")

    try:
        result = page.evaluate("""() => {
            // 1. 找到并点击「详情」标签（纯文本定位，找可见的 span）
            const allSpans = document.querySelectorAll('span');
            let detailTab = null;
            for (const span of allSpans) {
                if (span.textContent.trim() === '详情') {
                    const r = span.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10) {
                        detailTab = span;
                        break;
                    }
                }
            }
            if (!detailTab) return JSON.stringify({ description: '', ai_notes: '' });

            detailTab.click();

            // 2. 等待内容加载（轮询最多 5 秒）
            const start = Date.now();
            let descText = '';
            let aiText = '';

            while (Date.now() - start < 5000) {
                // 找描述：可见的 span 包含 # 标签（视频描述必有 hashtag）
                const spans = document.querySelectorAll('span');
                for (const span of spans) {
                    const t = span.textContent.trim();
                    const r = span.getBoundingClientRect();
                    if (r.width > 200 && r.height > 10 &&
                        t.length > 20 && t.includes('#')) {
                        descText = t;
                        break;
                    }
                }
                if (descText) break;
            }

            // 3. 找 AI 笔记：文本以「AI 笔记」开头且可见的 div
            const allDivs = document.querySelectorAll('div');
            for (const div of allDivs) {
                const t = div.textContent.trim();
                const r = div.getBoundingClientRect();
                if (t.startsWith('AI 笔记') && r.width > 200 && r.height > 50) {
                    aiText = t;
                    break;
                }
            }

            // 4. 点击「评论」切回去
            const allSpans2 = document.querySelectorAll('span');
            for (const span of allSpans2) {
                if (span.textContent.trim() === '评论') {
                    const r = span.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10) {
                        span.click();
                        break;
                    }
                }
            }

            return JSON.stringify({ description: descText, ai_notes: aiText });
        }""")

        data = json.loads(result)
        if data.get("description"):
            print(f"  描述: {data['description'][:60]}...")
        if data.get("ai_notes"):
            print(f"  AI笔记: {data['ai_notes'][:60]}...")
        return data
    except Exception:
        return {"description": "", "ai_notes": ""}


def get_video_title(page, timeout=5000):
    """提取当前视频的标题（纯 DOM 定位，不依赖动态 class）"""
    try:
        title = page.evaluate("""() => {
            const activeVideo = document.querySelector('[data-e2e="feed-active-video"]');
            const scope = activeVideo || document;

            const desc = scope.querySelector('[data-e2e="video-desc"]');
            if (!desc) return '';

            // 找叶子 SPAN（无子 SPAN），排除标签/前缀
            const allSpans = desc.querySelectorAll('span');
            let bestText = '';
            for (const span of allSpans) {
                // 只考虑没有子 SPAN 的叶子节点
                if (span.querySelector('span')) continue;
                const t = span.textContent.trim();
                if (!t || t === '展开' || t.length < 5) continue;
                // 跳过纯标签
                if (t.startsWith('#') || t.startsWith('@')) continue;
                // 跳过 "第N集" / "第N期" 前缀
                if (/^第\\d+[集期]/.test(t)) continue;
                if (t.length > bestText.length) {
                    bestText = t;
                }
            }
            return bestText;
        }""")
        if title:
            print(f"  视频标题: {title[:60]}{'...' if len(title) > 60 else ''}")
        else:
            print("  [!] 未提取到视频标题")
        return title or ''
    except Exception:
        print("  [!] 提取视频标题失败")
        return ''


def get_video_stats(page, timeout=5000):
    """
    提取当前视频的互动数据：点赞、评论、收藏、分享数。

    返回 dict: {"likes": "7038", "comments": "807", "collects": "807", "shares": "2029"}
    """
    try:
        stats = page.evaluate("""() => {
            // 定位当前播放的视频容器
            const activeVideo = document.querySelector('[data-e2e="feed-active-video"]');
            const scope = activeVideo || document;

            const result = { likes: '0', comments: '0', collects: '0', shares: '0' };

            // 点赞
            const digg = scope.querySelector('[data-e2e="video-player-digg"]');
            if (digg) {
                let raw = digg.textContent.trim();
                result.likes = (raw === '点赞' || raw === '') ? '0' : raw;
            }

            // 收藏
            const collect = scope.querySelector('[data-e2e="video-player-collect"]');
            if (collect) {
                let raw = collect.textContent.trim();
                result.collects = (raw === '收藏' || raw === '') ? '0' : raw;
            }

            // 分享
            const share = scope.querySelector('[data-e2e="video-player-share"]');
            if (share) {
                let raw = share.textContent.trim();
                result.shares = (raw === '转发' || raw === '') ? '0' : raw;
            }

            // 评论数：优先从评论区标题获取 "全部评论(N)"
            const commentList = scope.querySelector('[data-e2e="comment-list"]');
            if (commentList) {
                const text = commentList.textContent;
                const m = text.match(/全部评论\\((\\d+(?:\\.\\d+)?万?)\\)/);
                if (m) result.comments = m[1];
            }
            // 备选：feed-comment-icon
            if (result.comments === '0') {
                const icon = scope.querySelector('[data-e2e="feed-comment-icon"]')
                    || document.querySelector('[data-e2e="feed-comment-icon"]');
                if (icon) {
                    let raw = icon.textContent.trim();
                    result.comments = (raw === '抢首评' || raw === '评论' || raw === '') ? '0' : raw;
                }
            }

            return result;
        }""")
        print(f"  点赞:{stats.get('likes','0')} 评论:{stats.get('comments','0')} "
              f"收藏:{stats.get('collects','0')} 分享:{stats.get('shares','0')}")
        return stats
    except Exception:
        print("  [!] 提取视频互动数据失败")
        return {"likes": "0", "comments": "0", "collects": "0", "shares": "0"}


def save_results(all_videos, search_text, match_keywords, output_dir=None):
    """保存本次运行的全部结果到一个 JSON 文件"""
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"douyin_results_{timestamp}.json")

    # 关键字模式下只保留有匹配结果的视频
    if match_keywords:
        videos = [v for v in all_videos if v.get('matched_users')]
    else:
        videos = all_videos

    result = {
        "search_term": search_text,
        "match_keywords": match_keywords,
        "timestamp": timestamp,
        "total_videos": len(videos),
        "videos": videos,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 统计
    total_comments = sum(len(v.get('comments', [])) for v in videos)
    total_matched = sum(len(v.get('matched_users', []) or []) for v in videos)

    print(f"\n[✓] 全部结果已保存到: {filepath}")
    print(f"    视频数: {len(videos)}")
    print(f"    评论数: {total_comments}")
    if match_keywords:
        print(f"    匹配用户数: {total_matched}")
    return filepath


def save_comments(comments, output_dir=None):
    """保存评论数据到 JSON 文件"""
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"comments_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    print(f"[✓] 评论已保存到: {filepath}")
    return filepath


def extract_user_profile(page, timeout=10000):
    """
    在用户主页提取：用户名、抖音号（shortId）
    如果页面显示"用户不存在"返回 None

    不依赖动态 class，使用：
      [data-e2e="user-info"] h1  → 用户名
      span 文本含 "抖音号："     → shortId
    """
    print("[*] 提取用户主页信息...")

    # 等待用户主页关键元素加载完成
    try:
        page.wait_for_selector('[data-e2e="user-info"]', timeout=timeout)
    except Exception:
        pass  # 可能不存在，继续尝试提取

    random_delay()

    # 检查是否"用户不存在"
    not_found = page.evaluate("""() => {
        return document.body.textContent.includes('用户不存在');
    }""")

    if not_found:
        print("  [!] 用户不存在，跳过")
        return None

    random_delay()

    data = page.evaluate("""() => {
        const result = { username: '', shortId: '', secId: '' };

        // 用户名：[data-e2e="user-info"] 里的 h1
        const userInfo = document.querySelector('[data-e2e="user-info"]');
        if (userInfo) {
            const h1 = userInfo.querySelector('h1');
            if (h1) result.username = h1.textContent.trim();
        }

        // 抖音号：遍历 span，找 "抖音号：" 开头
        const spans = document.querySelectorAll('span');
        for (const s of spans) {
            const t = s.textContent.trim();
            if (t.startsWith('抖音号：')) {
                result.shortId = t.replace('抖音号：', '').trim();
                break;
            }
        }

        // 备选：从 title 提取
        if (!result.username) {
            const m = document.title.match(/^(.+)的抖音/);
            if (m) result.username = m[1];
        }

        // secId: 从 URL 提取 /user/后面的 msns 串
        const urlMatch = location.href.match(/\/user\/([^/?]+)/);
        if (urlMatch) result.secId = urlMatch[1];

        return result;
    }""")

    if data['username'] or data['shortId']:
        print(f"  用户名: {data['username']}")
        print(f"  抖音号: {data['shortId']}")
    else:
        print("[!] 未提取到用户信息")

    return data


def match_comment_and_click_user(page, comments, match_keywords, dm_message=None, browser=None):
    """
    在评论中匹配关键字（OR 逻辑），找到后点击用户名链接进入用户主页，
    并提取用户主页信息（用户名、抖音号）。
    如果 dm_message 不为空，提取到用户 secId 后立即发送私信。

    match_keywords: list[str]
    dm_message: 私信内容，为 None 则不发送
    browser: Playwright browser 对象
    返回匹配到的用户数据列表
    """
    if not match_keywords:
        return []

    print(f'[*] 匹配评论关键字: {" | ".join(match_keywords)}')
    matched = []

    for comment in comments:
        content = comment.get('content', '')
        if any(kw in content for kw in match_keywords):
            matched.append(comment)
        for reply in comment.get('replies', []):
            if any(kw in reply.get('content', '') for kw in match_keywords):
                matched.append(reply)

    if not matched:
        print('[!] 未找到包含关键字的评论')
        return []

    print(f"[✓] 找到 {len(matched)} 条匹配评论")

    # 保存提取到的用户数据
    user_profiles = []

    for i, m in enumerate(matched):
        random_delay()
        username = m.get('username', '')
        content_preview = m.get('content', '')[:40]
        if not username:
            continue

        print(f'  [{i+1}] 用户: {username}  → 内容: {content_preview}...')

        # 使用 Playwright expect_page 等待新标签页打开
        random_delay()
        try:
            with page.context.expect_page(timeout=15000) as new_page_info:
                page.evaluate(f"""(username) => {{
                    const links = document.querySelectorAll('a[href*="/user/"]');
                    for (const link of links) {{
                        if (link.textContent.includes(username) && !link.querySelector('[data-e2e="live-avatar"]')) {{
                            link.click();
                            return true;
                        }}
                    }}
                    return false;
                }}""", username)
            profile_page = new_page_info.value
        except Exception:
            print(f'    [!] 等待新页面超时（15s）')
            continue

        random_delay()
        try:
            profile_page.wait_for_load_state('domcontentloaded', timeout=10000)
            random_delay()
            time.sleep(2)
            random_delay()
            profile_data = extract_user_profile(profile_page)
            if profile_data is None:
                try:
                    profile_page.close()
                except Exception:
                    pass
                continue
            profile_data['comment_content'] = m.get('content', '')
            profile_data['comment_time'] = m.get('time', '')
            profile_data['comment_likes'] = m.get('likes', '0')
            profile_data['is_author'] = m.get('isAuthor', False)
            user_profiles.append(profile_data)

            # 立即发送私信（提取到 secId 后，使用已打开的用户主页）
            if dm_message and profile_data.get("secId"):
                _immediate_dm_send(profile_page, profile_data, dm_message)

            try:
                profile_page.close()
            except Exception:
                pass
        except Exception as e:
            print(f'    [!] 提取用户信息失败: {e}')

        time.sleep(1)

    return user_profiles


def _immediate_dm_send(page, user_data: dict, dm_message: str):
    """
    立即向指定用户发送私信（在提取到 secId 后立即调用）。
    使用已经打开的用户主页 page，不需要重新导航。
    dm_message 支持多行（用换行分隔），每次随机选取一条发送。

    page: Playwright page 对象（已停在用户主页）
    user_data: 包含 secId/shortId/username 的用户信息字典
    dm_message: 要发送的私信内容，多行时随机选一条
    """
    # 多行内容随机选一条
    lines = [l.strip() for l in dm_message.split("\n") if l.strip()]
    msg = random.choice(lines) if len(lines) > 1 else (lines[0] if lines else "")
    if not msg:
        user_data["dm_sent"] = False
        user_data["dm_result"] = "无私信内容"
        return

    # 检查是否已发送过（永久记录）
    sec_id = user_data.get("secId", "")
    dm_store = _get_dm_sent_store()
    if sec_id and dm_store.is_sent(sec_id):
        record = dm_store.get_record(sec_id)
        print(f"    [跳过] @{user_data.get('username','')} 已发送过私信（{record.get('sent_at','')}），跳过")
        user_data["dm_sent"] = True
        user_data["dm_result"] = "已发送过，跳过"
        return

    print(f"    [*] 正在发送私信（内容: {msg[:20]}...）...")

    try:
        # 等待页面稳定
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        random_delay(1.5, 2.5)

        # JS 点击第二个私信按钮
        clicked = page.evaluate('''
            () => {
                const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.trim() === '私信');
                if (btns.length < 2) return 'no_button';
                btns[1].scrollIntoView({block: 'center'});
                setTimeout(() => btns[1].click(), 500);
                return 'clicked';
            }
        ''')
        print(f"    [*] DM按钮点击结果: {clicked}")
        random_delay(2.5, 3.5)

        # 等待私信对话框出现，尝试多种选择器
        msg_input = None
        selectors = [
            '[aria-describedby][contenteditable="true"]',
            '[data-e2e="msg-input"] [contenteditable="true"]',
            '[data-e2e="msg-input"] div[contenteditable="true"]',
            'div[contenteditable="true"][aria-label="发送消息"]',
        ]
        for sel in selectors:
            for _ in range(8):
                msg_input = page.query_selector(sel)
                if msg_input:
                    print(f"    [*] 找到输入框: {sel}")
                    break
                time.sleep(0.4)
            if msg_input:
                break

        if not msg_input:
            # 最后尝试：直接查所有可编辑元素
            msg_input = page.evaluate('''() => {
                const els = document.querySelectorAll('[contenteditable="true"]');
                for (const el of els) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        return el.className + '|' + el.getAttribute('data-e2e') + '|' + el.getAttribute('aria-describedby');
                    }
                }
                return null;
            }''')
            print(f"    [!] 所有contenteditable: {msg_input}")
            user_data["dm_sent"] = False
            user_data["dm_result"] = "输入框未找到"
            return

        msg_input.scroll_into_view_if_needed()
        random_delay(0.3)
        msg_input.click()
        random_delay(0.3)
        msg_input.fill("")
        msg_input.type(msg, delay=80)
        random_delay(0.3)
        msg_input.press("Enter")
        random_delay(1.5, 2.0)

        user_data["dm_sent"] = True
        user_data["dm_result"] = "发送成功"
        print(f"    [✓] 私信发送成功")
        # 永久记录已发送用户
        if sec_id:
            dm_store.mark_sent(sec_id, username=user_data.get("username", ""), short_id=user_data.get("shortId", ""))

    except Exception as e:
        print(f"    [!] 私信发送失败: {e}")
        user_data["dm_sent"] = False
        user_data["dm_result"] = str(e)


def _send_dm_to_matched_users(browser, context, all_videos, dm_message):
    """遍历所有视频的 matched_users，向每个用户发送私信"""
    total_sent = 0
    total_failed = 0

    for video in all_videos:
        matched_users = video.get("matched_users") or []
        if not matched_users:
            continue

        video_title = video.get("title", "")
        print(f"\n[*] 视频「{video_title}」发现 {len(matched_users)} 个匹配用户，开始发送私信...")
        random_delay(0.5, 1.0)

        for i, user in enumerate(matched_users):
            # 多行内容随机选一条
            lines = [l.strip() for l in dm_message.split("\n") if l.strip()]
            msg = random.choice(lines) if len(lines) > 1 else (lines[0] if lines else "")

            short_id = user.get("shortId", "")
            sec_id = user.get("secId", "")
            username = user.get("username", "")

            print(f"  [{i+1}/{len(matched_users)}] 发送给 @{username} ({short_id}) ...")

            # 检查是否已发送过
            dm_store = _get_dm_sent_store()
            if sec_id and dm_store.is_sent(sec_id):
                record = dm_store.get_record(sec_id)
                print(f"    [跳过] 已发送过私信（{record.get('sent_at','')}），跳过")
                user["dm_sent"] = True
                user["dm_result"] = "已发送过，跳过"
                total_sent += 1
                continue

            if sec_id:
                profile_url = f"https://www.douyin.com/user/{sec_id}"
            elif short_id:
                profile_url = f"https://www.douyin.com/user/{short_id}"
            else:
                print(f"    [!] 用户 secId/shortId 缺失，跳过")
                user["dm_sent"] = False
                user["dm_result"] = "secId缺失"
                total_failed += 1
                continue

            try:
                page = context.new_page()
                page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
                random_delay(1.5, 2.5)

                btns = page.query_selector_all("button")
                pm_btns = [b for b in btns if b.inner_text().strip() == "私信"]
                if len(pm_btns) < 2:
                    print(f"    [!] 私信按钮不足2个")
                    user["dm_sent"] = False
                    user["dm_result"] = "私信按钮未找到"
                    total_failed += 1
                    page.close()
                    continue

                page.evaluate('''
                    () => {
                        const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.trim() === '私信');
                        if (btns[1]) {
                            btns[1].scrollIntoView({block: 'center'});
                            setTimeout(() => btns[1].click(), 400);
                        }
                    }
                ''')
                random_delay(2.0, 3.0)

                msg_input = page.query_selector('[data-e2e="msg-input"] [contenteditable="true"]')
                if not msg_input:
                    print(f"    [!] 未找到输入框")
                    user["dm_sent"] = False
                    user["dm_result"] = "输入框未找到"
                    total_failed += 1
                    page.close()
                    continue

                msg_input.scroll_into_view_if_needed()
                random_delay(0.2)
                msg_input.click()
                random_delay(0.2)
                msg_input.fill("")
                msg_input.type(msg, delay=80)
                random_delay(0.3)
                msg_input.press("Enter")
                random_delay(1.5, 2.0)

                user["dm_sent"] = True
                user["dm_result"] = "发送成功"
                print(f"    [✓] 发送成功")
                total_sent += 1
                # 永久记录已发送用户
                if sec_id:
                    dm_store.mark_sent(sec_id, username=username, short_id=short_id)

                page.close()
                random_delay(2.0, 4.0)

            except Exception as e:
                print(f"    [!] 发送失败: {e}")
                user["dm_sent"] = False
                user["dm_result"] = str(e)
                total_failed += 1
                try:
                    page.close()
                except Exception:
                    pass
                random_delay(1.0, 2.0)

    print(f"\n{'='*50}")
    print(f"[*] 私信发送完成: 成功 {total_sent} 个, 失败 {total_failed} 个")
    print(f"{'='*50}")


def save_user_profiles(profiles, output_dir=None):
    """保存用户主页数据到 JSON 文件"""
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"user_profiles_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"[✓] 用户数据已保存到: {filepath}")
    return filepath


# ========== 主入口函数 ==========

SEARCH_TEXT = "你的搜索内容"
USE_CDP = True
CDP_URL = "http://127.0.0.1:9222"
COOKIE_FILE = "cookies.json"


def search_via_cdp(search_text=SEARCH_TEXT, cookie_file=None, match_keywords=None,
                    video_count=5, sort_by="最新发布", time_filter=None, dm_message=None):
    """通过 CDP 连接已有 Chrome 浏览器进行搜索"""
    with sync_playwright() as p:
        print(f"[*] 连接 CDP: {CDP_URL}")
        browser = p.chromium.connect_over_cdp(CDP_URL)

        # 获取已有页面或新建
        if browser.contexts:
            context = browser.contexts[0]
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = context.new_page()
        else:
            context = browser.new_context()
            page = context.new_page()

        # 设置窗口大小（确保坐标定位一致）
        page.set_viewport_size({"width": 1280, "height": 720})

        # 注入 Cookie（免登录）
        if cookie_file:
            from core_modules.browser.cookies import load_cookies_from_file, inject_cookies
            cookies = load_cookies_from_file(cookie_file)
            inject_cookies(context, cookies)

        # 导航到抖音首页
        print("[*] 导航到抖音首页...")
        page.goto("https://www.douyin.com/jingxuan", wait_until="domcontentloaded")
        time.sleep(3)

        # 定位搜索框
        from core_modules.browser.locators import find_search_input
        search_input = find_search_input(page)

        # 模拟人工输入
        type_human_like(page, search_input, search_text)

        # 按回车搜索
        search_input.press("Enter")
        print(f"[✓] 已搜索: {search_text}")
        random_delay()

        # 应用筛选条件
        if sort_by or time_filter:
            print(f"\n[*] 应用筛选条件...")
            # 打开筛选面板
            toggle_filter_panel(page, open=True)

            # 应用排序
            if sort_by:
                apply_filter(page, "排序依据", sort_by)

            # 应用发布时间
            if time_filter:
                # 如果排序筛选已刷新页面，面板已关闭，需要重新打开
                if sort_by:
                    toggle_filter_panel(page, open=True)
                apply_filter(page, "发布时间", time_filter)

            # 确保面板关闭
            toggle_filter_panel(page, open=False)
            print("[✓] 筛选条件应用完毕\n")
            random_delay()

        # 点击第一个视频
        if not click_first_video(page):
            print("[!] 未找到视频，退出")
            return

        # 循环处理视频
        all_videos = []
        for i in range(video_count):
            if i > 0:
                go_next_video(page)
                random_delay()

            video_data = process_one_video(page, i, match_keywords, dm_message=dm_message, browser=browser)
            if video_data is None:
                print(f"  ⏭ 跳过第 {i + 1} 个视频\n")
                continue
            all_videos.append(video_data)

        # 统一保存所有视频数据到一个文件
        save_results(all_videos, search_text, match_keywords)

        # 汇总
        print(f"\n{'='*40}")
        print(f"[✓] 全部完成！处理了 {video_count} 个视频")
        total_comments = sum(len(v.get('comments', [])) for v in all_videos)
        total_matched = sum(len(v.get('matched_users', []) or []) for v in all_videos)
        print(f"  评论总数: {total_comments}")
        if match_keywords:
            print(f"  匹配用户数: {total_matched}")
        print(f"{'='*40}")

        # 桌面模式：私信已在采集过程中实时发送，跳过批量发送
        # 非桌面模式：私信在全部采集完成后批量发送（兼容 CLI 模式）
        if dm_message and not os.environ.get("DOUYIN_DESKTOP_MODE"):
            _send_dm_to_matched_users(browser, context, all_videos, dm_message)

        if os.environ.get("DOUYIN_DESKTOP_MODE"):
            from core_modules.browser.cookies import _refresh_cookies
            _refresh_cookies(context, cookie_file)
            return

        # 保持浏览器打开
        print("\n[*] 浏览器保持打开，按 Ctrl+C 退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] 退出。")


def search_via_launch(search_text=SEARCH_TEXT, cookie_file=None, match_keywords=None,
                       video_count=5, sort_by="最新发布", time_filter=None, dm_message=None):
    """启动新浏览器进行搜索（可能触发验证码）"""
    with sync_playwright() as p:
        print("[*] 启动新浏览器...")
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--remote-allow-origins=*",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        # 设置窗口大小（确保坐标定位一致）
        page.set_viewport_size({"width": 1280, "height": 720})

        # 注入 Cookie（免登录）
        if cookie_file:
            from core_modules.browser.cookies import load_cookies_from_file, inject_cookies
            cookies = load_cookies_from_file(cookie_file)
            inject_cookies(context, cookies)

        # 导航
        print("[*] 导航到抖音首页...")
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
        time.sleep(3)

        # 定位搜索框
        from core_modules.browser.locators import find_search_input
        search_input = find_search_input(page)

        # 模拟人工输入
        type_human_like(page, search_input, search_text)

        # 按回车搜索
        search_input.press("Enter")
        print(f"[✓] 已搜索: {search_text}")
        random_delay()

        # 应用筛选条件
        if sort_by or time_filter:
            print(f"\n[*] 应用筛选条件...")
            toggle_filter_panel(page, open=True)
            if sort_by:
                apply_filter(page, "排序依据", sort_by)
            if time_filter:
                if sort_by:
                    toggle_filter_panel(page, open=True)
                apply_filter(page, "发布时间", time_filter)
            toggle_filter_panel(page, open=False)
            print("[✓] 筛选条件应用完毕\n")
            random_delay()

        # 点击第一个视频
        if not click_first_video(page):
            print("[!] 未找到视频，退出")
            return

        # 循环处理视频
        all_videos = []
        for i in range(video_count):
            if i > 0:
                go_next_video(page)
                random_delay()

            video_data = process_one_video(page, i, match_keywords, dm_message=dm_message, browser=browser)
            if video_data is None:
                print(f"  ⏭ 跳过第 {i + 1} 个视频\n")
                continue
            all_videos.append(video_data)

        # 统一保存所有视频数据到一个文件
        save_results(all_videos, search_text, match_keywords)

        # 汇总
        print(f"\n{'='*40}")
        print(f"[✓] 全部完成！处理了 {video_count} 个视频")
        total_comments = sum(len(v.get('comments', [])) for v in all_videos)
        total_matched = sum(len(v.get('matched_users', []) or []) for v in all_videos)
        print(f"  评论总数: {total_comments}")
        if match_keywords:
            print(f"  匹配用户数: {total_matched}")
        print(f"{'='*40}")

        # CLI 模式：私信在全部采集完成后批量发送
        if dm_message:
            _send_dm_to_matched_users(browser, context, all_videos, dm_message)

        # 保持浏览器打开
        print("\n[*] 浏览器保持打开，按 Ctrl+C 退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[*] 关闭浏览器...")
            browser.close()


def send_dm_via_cdp(cdp_url: str, message: str = "你好") -> dict:
    """
    在已打开的抖音用户主页上，点击私信按钮，找到输入框，输入消息并发送。

    Args:
        cdp_url: Chrome CDP 地址，如 http://127.0.0.1:9222
        message: 要发送的消息内容，默认 "你好"

    Returns:
        dict: {"success": True/False, "message": "描述"}
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)

            # 1. 找到抖音用户主页
            target_page = None
            for ctx in browser.contexts:
                for page in ctx.pages:
                    if "douyin.com/user" in page.url and "MS4wLjAB" in page.url:
                        target_page = page
                        break
                if target_page:
                    break

            if not target_page:
                return {"success": False, "message": "未找到抖音用户主页，请确认已打开目标用户页面"}

            # 提取 secId 从 URL
            sec_id = ""
            url = target_page.url
            m = re.search(r"/user/([^/?]+)", url) if "douyin.com/user" in url else None
            if m:
                sec_id = m.group(1)

            # 检查是否已发送过
            dm_store = _get_dm_sent_store()
            if sec_id and dm_store.is_sent(sec_id):
                record = dm_store.get_record(sec_id)
                return {"success": False, "message": f"已发送过私信（{record.get('sent_at','')}），请勿重复发送"}

            # 2. JS 点击第二个私信按钮
            target_page.evaluate('''
                () => {
                    const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.trim() === '私信');
                    if (btns[1]) {
                        btns[1].scrollIntoView({block: 'center'});
                        setTimeout(() => btns[1].click(), 300);
                    }
                }
            ''')
            time.sleep(2)

            # 3. 定位输入框: data-e2e="msg-input" 容器内的 contenteditable div
            msg_input = None
            for _ in range(10):
                msg_input = target_page.query_selector('[data-e2e="msg-input"] [contenteditable="true"]')
                if msg_input:
                    break
                time.sleep(0.3)

            if not msg_input:
                return {"success": False, "message": "未找到私信输入框"}

            # 4. 输入消息并按 Enter 发送
            msg_input.scroll_into_view_if_needed()
            time.sleep(0.2)
            msg_input.click()
            time.sleep(0.2)
            msg_input.fill("")
            msg_input.type(message, delay=80)
            time.sleep(0.3)
            msg_input.press("Enter")
            time.sleep(1.5)

            # 记录已发送
            if sec_id:
                dm_store.mark_sent(sec_id)

            return {"success": True, "message": f"消息「{message}」已发送"}

    except Exception as e:
        return {"success": False, "message": f"发送失败: {str(e)}"}