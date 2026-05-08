#!/usr/bin/env python3
"""小红书搜索 CLI - 通过 CDP 连接已有 Chrome 浏览器进行搜索和评论采集"""

import argparse
import random
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright

# 从子包导入定位和操作函数
from core_modules.xhs.locators import (
    SEARCH_BOX_STRATEGIES,
    SEARCH_BTN_STRATEGIES,
    find_search_box,
)
from core_modules.xhs.actions import search_keyword


def find_xiaohongshu_page(browser) -> object:
    """在已连接的浏览器中查找小红书页面（优先非搜索结果页）"""
    best = None
    for ctx in browser.contexts:
        for page in ctx.pages:
            if "xiaohongshu.com/search_result" in page.url:
                continue  # 跳过搜索结果页（由 collect 单独处理）
            if "xiaohongshu" in page.url:
                if "explore" in page.url or "discovery" in page.url:
                    return page
                best = page
    return best


def get_or_create_xhs_page(browser, open_url: str = "https://www.xiaohongshu.com/explore"):
    """获取已有小红书页面，或创建新的"""
    page = find_xiaohongshu_page(browser)
    if page:
        return page, False
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.new_page()
    page.goto(open_url, wait_until="domcontentloaded")
    time.sleep(1)
    return page, True


# ─────────────────────────────────────────
#  搜索结果定位策略
# ─────────────────────────────────────────
def collect_search_results(page, skip_recommend: bool = True, max_count: int = 50) -> list:
    """采集当前页面搜索结果，多策略自适应"""

    # JS 表达式，动态尝试多种选择器
    js_code = f"""
        () => {{
            const results = [];
            const MAX = {max_count};

            // 策略1: section.note-item（小红书搜索结果主要容器）
            let notes = document.querySelectorAll('section.note-item');
            if (notes.length > 0) {{
                notes.forEach((note, i) => {{
                    if (i >= MAX) return;
                    const titleEl = note.querySelector('.title');
                    const authorEl = note.querySelector('.author');
                    const coverImg = note.querySelector('a.cover img');
                    const linkEl = note.querySelector('a.cover');
                    const isRecommendCard = !titleEl && !linkEl;
                    if ({str(skip_recommend).lower()} && isRecommendCard) return;
                    results.push({{
                        index: i,
                        selector: 'section.note-item',
                        dataIndex: note.getAttribute('data-index') || String(i),
                        title: titleEl ? titleEl.textContent.trim() : null,
                        author: authorEl ? authorEl.textContent.trim() : null,
                        href: linkEl ? linkEl.href : null,
                        imgSrc: coverImg ? (coverImg.src || coverImg.getAttribute('data-xhs-img')) : null,
                        isRecommendCard
                    }});
                }});
                if (results.length > 0) return results;
            }}

            // 策略2: 任意包含 note 相关 class 的 section/div
            const altNotes = document.querySelectorAll('[class*="note-item"], [class*="noteItem"]');
            if (altNotes.length > 0) {{
                altNotes.forEach((note, i) => {{
                    if (i >= MAX) return;
                    const link = note.closest('a') || note.querySelector('a');
                    const title = note.querySelector('[class*="title"]');
                    const author = note.querySelector('[class*="author"], [class*="user"]');
                    results.push({{
                        index: i,
                        selector: '[class*="note-item"]',
                        dataIndex: note.getAttribute('data-index') || String(i),
                        title: title ? title.textContent.trim() : null,
                        author: author ? author.textContent.trim() : null,
                        href: link ? link.href : null,
                        isRecommendCard: !title && !link
                    }});
                }});
                if (results.length > 0) return results;
            }}

            // 策略3: 瀑布流容器下的直接子元素（feeds）
            const feeds = document.querySelectorAll('[class*="feeds"] > div, [class*="feeds"] > section');
            if (feeds.length > 0) {{
                feeds.forEach((el, i) => {{
                    if (i >= MAX) return;
                    const link = el.querySelector('a');
                    const title = el.querySelector('[class*="title"]');
                    results.push({{
                        index: i,
                        selector: '[class*="feeds"] direct child',
                        dataIndex: el.getAttribute('data-index') || String(i),
                        title: title ? title.textContent.trim() : null,
                        author: null,
                        href: link ? link.href : null,
                        isRecommendCard: !title && !link
                    }});
                }});
            }}

            return results;
        }}
    """

    try:
        results = page.evaluate(js_code)
        return results
    except Exception as e:
        print(f"  [采集] JS执行失败: {e}")
        return []


def scroll_to_load_more(page, scroll_range: int = 5, pause: float = 1.5) -> int:
    """滚动页面加载更多，返回滚动前后的增量"""
    prev_count = page.evaluate("""
        () => {
            const notes = document.querySelectorAll('section.note-item, [class*="note-item"]');
            return notes.length;
        }
    """)
    prev_count = prev_count or 0

    for _ in range(scroll_range):
        page.mouse.wheel(0, 800)
        time.sleep(random.uniform(0.3, 0.6))

    time.sleep(pause)

    new_count = page.evaluate("""
        () => {
            const notes = document.querySelectorAll('section.note-item, [class*="note-item"]');
            return notes.length;
        }
    """)
    new_count = new_count or 0

    return new_count - prev_count


def click_search_result(page, index: int = 0) -> bool:
    """点击第 N 个搜索结果（按 DOM 顺序，不依赖 data-index）"""
    success = page.evaluate(f"""
        () => {{
            const notes = document.querySelectorAll('section.note-item');
            const target = notes[{index}];
            if (!target) return false;
            const link = target.querySelector('a.cover') || target.querySelector('a') || target;
            link.click();
            return true;
        }}
    """)
    if success:
        time.sleep(1.5)
        print(f"  [点击] 已点击第 {index} 个搜索结果: {page.url}")
    return bool(success)


# ─────────────────────────────────────────
#  筛选功能
# ─────────────────────────────────────────
FILTER_OPTIONS = {
    # 排序
    "综合":    "sort_comprehensive",
    "最新":    "sort_latest",
    "最多点赞": "sort_likes",
    "最多评论": "sort_comments",
    "最多收藏": "sort_collects",
    # 笔记类型
    "不限":     "note_all",
    "视频":     "note_video",
    "图文":     "note_image",
    # 发布时间
    "一天内":   "time_day",
    "一周内":   "time_week",
    "半年内":   "time_halfyear",
    # 搜索范围
    "已看过":   "range_seen",
    "未看过":   "range_unseen",
    "已关注":   "range_followed",
    # 位置
    "同城":     "loc_samecity",
    "附近":     "loc_nearby",
}

FILTER_PANEL_SELECTORS = [
    '.filter-panel',
    '[class*="filter-panel"]',
    '[class*="filterPanel"]',
    '[class*="filter"] [class*="panel"]',
]

SORT_ITEMS_JS = """
    () => {
        const panel = document.querySelector('.filter-panel');
        if (!panel) return [];
        const items = panel.querySelectorAll('span, li, [class*="item"], [class*="option"]');
        return Array.from(items).map(el => ({
            text: el.textContent.trim(),
            class: el.className
        })).filter(item => item.text.length > 0 && item.text.length < 20);
    }
"""


def _get_filter_btn(page) -> object:
    """多策略定位筛选按钮"""
    selectors = [
        'div.filter',
        '[class*="filter"]',
        'button:has-text("筛选")',
        '[class*="筛选"]',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                return el
        except Exception:
            pass
    return None


def open_filter_panel(page) -> bool:
    """悬浮到筛选按钮展开面板，返回是否成功"""
    btn = _get_filter_btn(page)
    if not btn:
        print("  [筛选] 未找到筛选按钮")
        return False

    box = btn.bounding_box()
    if not box:
        print("  [筛选] 筛选按钮无 bounding_box")
        return False

    # hover 再移动到中心（避免 mouse.move 直接触发 mouseout 关闭面板）
    btn.hover()
    time.sleep(0.3)
    x = box['x'] + box['width'] / 2
    y = box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    time.sleep(0.5)

    # 确认面板已展开
    for _ in range(3):
        panel_visible = page.evaluate("""
            () => {
                const panel = document.querySelector('.filter-panel, [class*="filter-panel"], .filter-container, [class*="filter-container"]');
                return panel && panel.offsetParent !== null;
            }
        """)
        if panel_visible:
            return True
        time.sleep(0.3)

    return False


def _click_filter_option(page, option_text: str) -> bool:
    """在筛选面板中点击指定选项文本"""
    if not open_filter_panel(page):
        return False

    time.sleep(0.3)

    # 在面板内找匹配文本的元素
    clicked = page.evaluate(f"""
        (text) => {{
            const panel = document.querySelector('.filter-panel');
            if (!panel) return false;
            // 精确匹配
            const exact = panel.querySelector(`span[text="${{text}}"], li[text="${{text}}"]`);
            if (exact) {{
                exact.click();
                return true;
            }}
            // 模糊匹配
            const allEls = panel.querySelectorAll('span, li, [class*="item"], [class*="option"]');
            for (const el of allEls) {{
                if (el.textContent.trim() === text) {{
                    el.click();
                    return true;
                }}
            }}
            return false;
        }}
    """, option_text)

    if clicked:
        print(f"  [筛选] 已选择: {option_text}")
        time.sleep(0.5)
    return bool(clicked)


def apply_filter(page, sort: str = None, note_type: str = None,
                 time_range: str = None, search_scope: str = None,
                 location: str = None) -> bool:
    """
    应用筛选条件，支持多选
    sort:        综合/最新/最多点赞/最多评论/最多收藏
    note_type:   不限/视频/图文
    time_range:  不限/一天内/一周内/半年内
    search_scope: 不限/已看过/未看过/已关注
    location:    不限/同城/附近
    """
    if not open_filter_panel(page):
        print("  [筛选] 打开筛选面板失败")
        return False

    time.sleep(0.3)

    # 先点"重置"清除现有筛选
    page.evaluate("""
        () => {
            const panel = document.querySelector('.filter-panel');
            if (!panel) return;
            const btns = panel.querySelectorAll('button, span');
            for (const btn of btns) {
                if (btn.textContent.trim() === '重置') {
                    btn.click();
                    break;
                }
            }
        }
    """)
    time.sleep(0.3)

    applied = []

    # 需要点"不限"来先取消当前选择的情况
    resets = {
        "sort": None,
        "note_type": "不限",
        "time_range": "不限",
        "search_scope": "不限",
        "location": "不限",
    }

    if sort:
        if not _click_filter_option(page, sort):
            print(f"  [筛选] 未找到排序选项: {sort}")
        else:
            applied.append(f"排序={sort}")

    if note_type:
        if note_type != "不限":
            _click_filter_option(page, "不限")  # 先清除
            time.sleep(0.2)
        if not _click_filter_option(page, note_type):
            print(f"  [筛选] 未找到笔记类型: {note_type}")
        else:
            applied.append(f"类型={note_type}")

    if time_range:
        if time_range != "不限":
            _click_filter_option(page, "不限")
            time.sleep(0.2)
        if not _click_filter_option(page, time_range):
            print(f"  [筛选] 未找到时间范围: {time_range}")
        else:
            applied.append(f"时间={time_range}")

    if search_scope:
        if search_scope != "不限":
            _click_filter_option(page, "不限")
            time.sleep(0.2)
        if not _click_filter_option(page, search_scope):
            print(f"  [筛选] 未找到搜索范围: {search_scope}")
        else:
            applied.append(f"范围={search_scope}")

    if location:
        if location != "不限":
            _click_filter_option(page, "不限")
            time.sleep(0.2)
        if not _click_filter_option(page, location):
            print(f"  [筛选] 未找到位置: {location}")
        else:
            applied.append(f"位置={location}")

    # 收起面板（点击空白区域或按ESC）
    page.keyboard.press("Escape")
    time.sleep(0.5)

    if applied:
        print(f"  [筛选] 已应用: {', '.join(applied)}")
    return True


def reset_filter(page) -> bool:
    """重置所有筛选"""
    if not open_filter_panel(page):
        return False
    time.sleep(0.3)
    reset = page.evaluate("""
        () => {
            const panel = document.querySelector('.filter-panel');
            if (!panel) return false;
            const btns = panel.querySelectorAll('button, span');
            for (const btn of btns) {
                if (btn.textContent.trim() === '重置') {
                    btn.click();
                    return true;
                }
            }
            return false;
        }
    """)
    page.keyboard.press("Escape")
    time.sleep(0.5)
    if reset:
        print("  [筛选] 已重置")
    return bool(reset)


# ─────────────────────────────────────────
#  评论采集
# ─────────────────────────────────────────
def get_comment_count(page) -> int:
    """获取评论总数"""
    try:
        text = page.evaluate("""
            () => {
                const el = document.querySelector('.total, [class*="total"], [class*="comment"] [class*="count"]');
                return el ? el.textContent : null;
            }
        """)
        if text:
            import re
            m = re.search(r'(\d+)', text)
            if m:
                return int(m.group(1))
    except:
        pass
    return 0


def scroll_comments(page, scroll_range: int = 10, pause: float = 1.0) -> tuple[int, bool]:
    """
    滚动评论区加载更多，返回 (新增评论数, 是否已到底)
    到底标志: 出现 "THE END" 或类似字样
    """
    prev = _get_visible_comment_items(page)

    for _ in range(scroll_range):
        # 滚动到评论区底部
        page.evaluate("""
            () => {
                const list = document.querySelector('.list-container, [class*="comment"] ul, [class*="comments"]');
                if (list) list.scrollTop = list.scrollHeight;
                else window.scrollBy(0, 600);
            }
        """)
        time.sleep(random.uniform(0.4, 0.8))

    time.sleep(pause)
    new = _get_visible_comment_items(page)

    # 检查是否到底
    end_text = page.evaluate("""
        () => {
            const allText = document.body.innerText;
            return allText.includes('THE END') || allText.includes('The End') || allText.includes('到底了') || allText.includes('没有更多');
        }
    """)

    return new - prev, bool(end_text)


def _get_visible_comment_items(page) -> int:
    """获取当前可见评论数量"""
    try:
        # 多种容器策略
        count = page.evaluate("""
            () => {
                const selectors = [
                    '.comment-item',
                    '[class*="comment-item"]',
                    '[class*="commentList"] > div',
                    '[class*="comments"] .item',
                    '[class*="comment"] li',
                    'ul[class*="comment"] > li'
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) return els.length;
                }
                return 0;
            }
        """)
        return count or 0
    except:
        return 0


def find_user_profile_page(browser) -> object:
    """在浏览器中查找用户主页"""
    for ctx in browser.contexts:
        for page in ctx.pages:
            if "xiaohongshu.com/user/profile" in page.url:
                return page
    return None


def collect_user_profile(page) -> dict:
    """
    采集用户主页信息
    采集字段: 用户名、小红书号、IP属地、简介、粉丝数、关注数、笔记数等
    """
    page.wait_for_load_state('networkidle', timeout=5000)

    body_text = page.evaluate("() => document.body.innerText")
    profile_url = page.url

    import re

    result = {}

    # 1. 用户名
    name = page.evaluate("""
        () => {
            const el = document.querySelector('h1') ||
                      document.querySelector('.user-name') ||
                      document.querySelector('[class*="userName"]') ||
                      document.querySelector('[class*="name"]');
            return el ? el.textContent.trim() : null;
        }
    """)
    result['name'] = name

    # 2. 小红书号
    xhs_match = re.search(r'小红书号[：:\s]*([0-9]{5,})', body_text)
    result['xhsId'] = xhs_match.group(1) if xhs_match else None

    # 3. IP属地
    ip_match = re.search(r'IP属地[：:\s]*([^\s\n]+)', body_text)
    result['ipLocation'] = ip_match.group(1).strip() if ip_match else None

    # 4. 简介
    bio = None
    if ip_match:
        idx = body_text.index(ip_match.group(0)) + len(ip_match.group(0))
        rest = body_text[idx:].strip()
        lines = [l for l in rest.split('\n') if l.strip()]
        bio_lines = []
        for line in lines[:10]:
            if re.match(r'^\d+\s*岁|粉丝|关注|笔记|获赞', line):
                break
            if line.strip() and 'ICP' not in line and '版权所有' not in line:
                bio_lines.append(line.strip())
        bio = '\n'.join(bio_lines[:3]) if bio_lines else None
    result['bio'] = bio

    # 5. 数据统计
    stats = {}
    stat_patterns = [
        ('followers', r'粉丝[：:\s]*([\d,万+]+)'),
        ('following', r'关注[：:\s]*([\d,万+]+)'),
        ('notes', r'笔记[：:\s]*([\d,万+]+)'),
        ('likes', r'获赞与收藏[：:\s]*([\d,万+]+)'),
    ]
    for key, pattern in stat_patterns:
        m = re.search(pattern, body_text)
        if m:
            stats[key] = m.group(1)
    result['stats'] = stats

    # 6. 年龄
    age_match = re.search(r'(\d+)岁', body_text)
    result['age'] = age_match.group(1) if age_match else None

    # 7. URL & user_id
    result['profileUrl'] = profile_url
    url_match = re.search(r'user/profile/([a-f0-9]+)', profile_url)
    result['userId'] = url_match.group(1) if url_match else None

    return result


def collect_comments(page, max_count: int = 200, scroll_to_end: bool = True,
                     scroll_pause: float = 1.0) -> list:
    """
    采集当前详情页所有评论，多定位策略自适应
    采集字段: 评论人、评论时间、评论内容、点赞数、用户主页链接
    """

    if scroll_to_end:
        print("  [评论] 滚动加载中...")
        reached_end = False
        last_count = 0

        while not reached_end and last_count < max_count:
            delta, reached_end = scroll_comments(page, scroll_range=8, pause=scroll_pause)
            current = _get_visible_comment_items(page)
            print(f"  [评论] 已加载 {current} 条...", end="")
            if delta <= 0 and not reached_end:
                # 再给一次机会
                delta2, reached_end = scroll_comments(page, scroll_range=5, pause=scroll_pause)
                current = _get_visible_comment_items(page)
                print(f" -> {current} 条", end="")
                if current <= last_count:
                    print(" [已到底]")
                    break
            last_count = current
            print()
            if reached_end:
                print("  [评论] 已滚动到底部")

    # 采集所有可见评论
    comments = page.evaluate(f"""
        () => {{
            const items = document.querySelectorAll('.comment-item');
            if (items.length === 0) {{
                // 备选策略
                const altItems = document.querySelectorAll('[class*="comment-item"]');
                if (altItems.length > 0) {{
                    items = altItems;
                }}
            }}

            return Array.from(items).slice(0, {max_count}).map((item, i) => {{
                // 多策略找各字段
                const getText = (sel) => {{
                    const el = item.querySelector(sel);
                    return el ? el.textContent.trim() : null;
                }};
                const getAttr = (sel, attr) => {{
                    const el = item.querySelector(sel);
                    return el ? (el.getAttribute(attr) || (el[attr])) : null;
                }};

                // 评论人名称: name class > author class > 任意含名字的元素
                const nameEl = item.querySelector('.name') ||
                               item.querySelector('[class*="author"]') ||
                               item.querySelector('[class*="user"]');
                const author = nameEl ? nameEl.textContent.trim() : null;
                const authorHref = nameEl ? (nameEl.href || nameEl.getAttribute('href')) : null;

                // 评论内容: content class > 任意文本节点（排除时间和作者）
                const contentEl = item.querySelector('.content') ||
                                  item.querySelector('[class*="text"]') ||
                                  item.querySelector('[class*="content"]');
                const content = contentEl ? contentEl.textContent.trim() : null;

                // 评论时间: date class > time class > 任意含日期的元素
                const timeEl = item.querySelector('.date') ||
                               item.querySelector('[class*="time"]') ||
                               item.querySelector('[class*="time"]');
                let time = timeEl ? timeEl.textContent.trim() : null;

                // 点赞数
                const likeEl = item.querySelector('.like .count, [class*="like"] [class*="count"]');
                const likes = likeEl ? likeEl.textContent.trim() : null;

                // 回复数
                const replyEl = item.querySelector('.reply .count');
                const replies = replyEl ? replyEl.textContent.trim() : null;

                // 地理位置
                const locEl = item.querySelector('.location');
                const location = locEl ? locEl.textContent.trim() : null;

                return {{
                    index: i,
                    author,
                    authorHref,
                    content,
                    time,
                    likes,
                    replies,
                    location
                }};
            }});
        }}
    """)

    # 去重（按 author + content）
    seen = set()
    unique = []
    for c in comments:
        key = (c.get('author'), c.get('content'))
        if key not in seen and c.get('content'):
            seen.add(key)
            unique.append(c)

    return unique


def print_results(results: list, show_img: bool = False, result_type: str = "结果"):
    """格式化打印"""
    if not results:
        print(f"\n未找到任何{result_type}\n")
        return

    print(f"\n{'='*60}")
    print(f"共采集 {len(results)} 条{result_type}")
    print(f"{'='*60}\n")

    if result_type == "搜索":
        for r in results:
            tag = "[推荐]" if r.get("isRecommendCard") else ""
            print(f"[{r['index']:02d}] {tag} {r.get('title') or '(无标题)'}")
            print(f"     作者: {r.get('author') or '未知'}")
            print(f"     链接: {r.get('href') or '无'}")
            print()
    else:
        for c in results:
            loc = f" @ {c['location']}" if c.get('location') else ""
            print(f"[{c['index']:02d}] {c['author'] or '?'} | {c['time'] or ''}{loc}")
            print(f"     {c['content'] or ''}")
            if c.get('likes'):
                print(f"     赞: {c['likes']} | 回复: {c.get('replies', '')}")
            print()


# ─────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="小红书搜索 & 评论采集 CLI")
    sub = parser.add_subparsers(dest="cmd", help="子命令")

    # 搜索命令
    search_parser = sub.add_parser("search", help="搜索并采集结果")
    search_parser.add_argument("-k", "--keyword", type=str, required=True, help="搜索关键词")
    search_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")
    search_parser.add_argument("-n", "--count", type=int, default=20)
    search_parser.add_argument("-s", "--scroll", action="store_true", help="滚动加载")
    search_parser.add_argument("--no-skip-recommend", action="store_true")

    # 采集评论命令
    comment_parser = sub.add_parser("comments", help="采集当前详情页评论")
    comment_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")
    comment_parser.add_argument("-n", "--max", type=int, default=200, help="最大评论数")
    comment_parser.add_argument("--no-scroll-end", action="store_true", help="不自动滚动到底")

    # 用户主页命令
    user_parser = sub.add_parser("user", help="采集当前用户主页信息")
    user_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")

    # 一键采集命令
    collect_parser = sub.add_parser("collect", help="完整采集流程:搜索→筛选→点击笔记→滚动评论→关键字匹配→采集评论人信息")
    collect_parser.add_argument("-k", "--keyword", type=str, required=True, help="搜索关键词")
    collect_parser.add_argument("-m", "--match-keywords", type=str, default="", help="评论关键字匹配（逗号分隔，多个用|连接）")
    collect_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")
    collect_parser.add_argument("-n", "--max-videos", type=int, default=10, help="最大采集视频数")
    collect_parser.add_argument("--scroll-comments", type=int, default=20, help="评论滚动次数")
    collect_parser.add_argument("--sort", type=str, choices=["综合", "最新", "最多点赞", "最多评论", "最多收藏"], help="排序方式")
    collect_parser.add_argument("--type", type=str, choices=["不限", "视频", "图文"], help="笔记类型")
    collect_parser.add_argument("--time", type=str, choices=["不限", "一天内", "一周内", "半年内"], help="发布时间")
    collect_parser.add_argument("--scope", type=str, choices=["不限", "已看过", "未看过", "已关注"], help="搜索范围")
    collect_parser.add_argument("--loc", type=str, choices=["不限", "同城", "附近"], help="位置距离")
    collect_parser.add_argument("-o", "--output", type=str, help="输出 JSON 文件路径")

    # 筛选命令
    filter_parser = sub.add_parser("filter", help="筛选搜索结果")
    filter_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")
    filter_parser.add_argument("--sort", type=str, choices=["综合", "最新", "最多点赞", "最多评论", "最多收藏"], help="排序方式")
    filter_parser.add_argument("--type", type=str, choices=["不限", "视频", "图文"], help="笔记类型")
    filter_parser.add_argument("--time", type=str, choices=["不限", "一天内", "一周内", "半年内"], help="发布时间")
    filter_parser.add_argument("--scope", type=str, choices=["不限", "已看过", "未看过", "已关注"], help="搜索范围")
    filter_parser.add_argument("--loc", type=str, choices=["不限", "同城", "附近"], help="位置距离")
    filter_parser.add_argument("--reset", action="store_true", help="重置筛选")

    # 交互命令
    inter_parser = sub.add_parser("interactive", help="交互模式")
    inter_parser.add_argument("-c", "--cdp", type=str, default="http://127.0.0.1:9222")

    # 默认: search
    args = parser.parse_args(args=None if sys.argv[1:] else ["search", "-k", ""])

    # 自动从当前页面搜索
    if args.cmd == "search":
        keyword = args.keyword
        if not keyword:
            keyword = input("请输入搜索关键词: ").strip()
        if not keyword:
            print("关键词不能为空")
            sys.exit(1)

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            page = find_xiaohongshu_page(browser)
            if not page:
                print("未找到小红书页面，请先在 Chrome 中打开")
                sys.exit(1)

            print(f"[小红书] CDP: {args.cdp}")
            print(f"[小红书] 关键词: {keyword}")

            search_keyword(page, keyword)
            time.sleep(1)

            if args.scroll:
                print("[小红书] 滚动加载中...")
                while True:
                    delta = scroll_to_load_more(page, scroll_range=5)
                    results = collect_search_results(page, skip_recommend=not args.no_skip_recommend, max_count=args.count)
                    print(f"  已加载 {len(results)} 个结果 (本次新增 {delta})")
                    if len(results) >= args.count or delta == 0:
                        break

            results = collect_search_results(page, skip_recommend=not args.no_skip_recommend, max_count=args.count)
            print_results(results, result_type="搜索")

            # 保存结果供后续使用
            return results

    elif args.cmd == "comments":
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            page = find_xiaohongshu_page(browser)
            if not page:
                print("未找到小红书页面，请先打开一个笔记详情页")
                sys.exit(1)

            total = get_comment_count(page)
            print(f"[评论] 当前页面: {page.url}")
            print(f"[评论] 评论总数: {total}")

            comments = collect_comments(
                page,
                max_count=args.max,
                scroll_to_end=not args.no_scroll_end
            )
            print_results(comments, result_type="评论")

    elif args.cmd == "user":
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            page = find_user_profile_page(browser)
            if not page:
                print("未找到用户主页，请先打开一个用户主页")
                sys.exit(1)

            print(f"[用户] 当前页面: {page.url}")
            info = collect_user_profile(page)

            print(f"\n{'='*50}")
            print("用户信息")
            print(f"{'='*50}")
            print(f"  用户名:   {info.get('name') or '未知'}")
            print(f"  小红书号: {info.get('xhsId') or '未知'}")
            print(f"  IP属地:   {info.get('ipLocation') or '未知'}")
            if info.get('age'):
                print(f"  年龄:     {info.get('age')}岁")
            if info.get('city'):
                print(f"  城市:     {info.get('city')}")
            print(f"  简介:     {info.get('bio') or '无'}")
            stats = info.get('stats') or {}
            if stats:
                print(f"  粉丝:     {stats.get('followers', '-')}")
                print(f"  关注:     {stats.get('following', '-')}")
                print(f"  笔记:     {stats.get('notes', '-')}")
                print(f"  获赞:     {stats.get('likes', '-')}")
            print(f"  user_id:  {info.get('userId') or '未知'}")
            print(f"  主页URL:  {info.get('profileUrl')}")
            print(f"{'='*50}\n")

    elif args.cmd == "filter":
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            page = find_xiaohongshu_page(browser)
            if not page:
                print("未找到小红书搜索页面")
                sys.exit(1)

            print(f"[筛选] 当前页面: {page.url}")

            if args.reset:
                reset_filter(page)
            else:
                if not any([args.sort, args.type, args.time, args.scope, args.loc]):
                    # 无参数时，展示筛选面板
                    if open_filter_panel(page):
                        panel_text = page.evaluate(
                            "() => { const p = document.querySelector('.filter-panel'); return p ? p.innerText : null; }"
                        )
                        print(f"\n筛选面板内容:\n{panel_text}")
                        page.keyboard.press("Escape")
                    else:
                        print("无法打开筛选面板")
                else:
                    apply_filter(
                        page,
                        sort=args.sort,
                        note_type=args.type,
                        time_range=args.time,
                        search_scope=args.scope,
                        location=args.loc
                    )
                    time.sleep(1)
                    results = collect_search_results(page)
                    print(f"  筛选后结果数: {len(results)}")

    elif args.cmd == "collect":
        import json as _json

        keyword = args.keyword
        match_kw_text = args.match_keywords.strip()
        # 把逗号分隔的多个关键字合并为 | 分隔的正则
        if match_kw_text:
            match_keywords = [kw.strip() for kw in match_kw_text.split(",") if kw.strip()]
            kw_pattern = "|".join(match_keywords)
        else:
            match_keywords = []
            kw_pattern = ""

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            # 优先使用已有的搜索结果页，否则创建新的
            search_page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    if "xiaohongshu.com/search_result" in pg.url:
                        search_page = pg
                        break
                if search_page:
                    break

            if not search_page:
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                search_page = ctx.new_page()

            page = search_page

            print(f"[采集] 关键词: {keyword}")
            print(f"[采集] 匹配关键字: {match_keywords or '无'}")
            print(f"[采集] 最大视频数: {args.max_videos}")
            print(f"[采集] 评论滚动次数: {args.scroll_comments}")

            # 1. 直接导航到搜索结果页（比重复输入搜索框更稳定）
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}"
            print(f"[采集] 导航到: {search_url}")
            page.goto(search_url, wait_until="domcontentloaded")
            time.sleep(2)

            # 2. 应用筛选
            if any([args.sort, args.type, args.time, args.scope, args.loc]):
                apply_filter(
                    page,
                    sort=args.sort,
                    note_type=args.type,
                    time_range=args.time,
                    search_scope=args.scope,
                    location=args.loc
                )
                time.sleep(1)

            # 3. 收集当前页结果（不预先滚动）
            print("[采集] 采集当前页搜索结果...")

            # 4. 收集搜索结果
            all_results = collect_search_results(page, skip_recommend=True, max_count=args.max_videos * 3)
            print(f"[采集] 共获取 {len(all_results)} 个搜索结果")

            video_data = []
            total_matched_users = 0
            collected_videos = 0

            for r in all_results:
                if collected_videos >= args.max_videos:
                    break

                idx = r.get("index", 0)
                title = r.get("title") or f"笔记{idx}"
                print(f"\n[采集] === 视频 {collected_videos+1}: {title[:40]} ===")

                # 点击搜索结果
                if not click_search_result(page, idx):
                    print(f"[采集] 点击失败，跳过")
                    continue

                time.sleep(2)

                # 检测是否进入详情页（弹窗）
                detail_url = page.url
                if "xiaohongshu.com/explore" not in detail_url and "xiaohongshu.com/discovery" not in detail_url:
                    print(f"[采集] 详情页 URL: {detail_url}")

                # 检测评论区域是否有内容（荒地检测）
                is_empty = page.evaluate("""
                    () => {
                        const body = document.body.innerText;
                        return body.includes('荒地') || body.includes('点击评论') || body.includes('暂无评论');
                    }
                """)
                if is_empty:
                    print(f"[采集] 评论区为空（荒地），跳过此笔记")
                    # 关闭详情弹窗
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
                    continue

                # 滚动评论区
                print(f"[采集] 滚动评论区（{args.scroll_comments} 次）...")
                comments_data = collect_comments(
                    page,
                    max_count=500,
                    scroll_to_end=False,
                    scroll_pause=0.8
                )
                print(f"[采集] 获取到 {len(comments_data)} 条评论")

                # 关键字过滤
                v_matched_users = []
                if kw_pattern:
                    import re as _re
                    for c in comments_data:
                        content = c.get("content") or ""
                        author = c.get("author") or ""
                        if _re.search(kw_pattern, content + author):
                            print(f"[采集]   匹配到: {author} — {content[:30]}")
                            # 使用 window.open 打开评论人主页（强制新标签）
                            author_href = c.get("authorHref")
                            opened = False
                            if author_href:
                                page.evaluate(f"window.open('{author_href}', '_blank')")
                                opened = True
                            else:
                                # authorHref 为空，尝试通过 Playwright locator + Ctrl/Cmd+Click
                                try:
                                    safe_name = author.replace('"', '\\"')
                                    name_locator = page.locator(f'.comment-item .name:has-text("{safe_name}")').first
                                    if name_locator.count() > 0:
                                        name_locator.click(modifiers=["Control", "Meta"], timeout=3000)
                                        opened = True
                                    else:
                                        print(f"[采集]   未找到评论人元素: {author}")
                                except Exception as e:
                                    print(f"[采集]   点击失败: {e}")

                            if not opened:
                                print(f"[采集]   无法打开用户主页，跳过")
                                continue

                            time.sleep(2)

                            # 切换到新标签页
                            new_page_found = False
                            for attempt in range(3):
                                all_pages = browser.contexts[0].pages
                                for pg in all_pages:
                                    if "xiaohongshu.com/user/profile" in pg.url:
                                        user_info = collect_user_profile(pg)
                                        user_info["comment_content"] = content
                                        user_info["comment_time"] = c.get("time") or ""
                                        user_info["comment_likes"] = c.get("likes") or ""
                                        v_matched_users.append(user_info)
                                        pg.close()
                                        time.sleep(0.3)
                                        new_page_found = True
                                        break
                                if new_page_found:
                                    break
                                time.sleep(1)

                            if not new_page_found:
                                print(f"[采集]   未能打开用户主页标签页")

                    print(f"[采集]   本视频匹配用户: {len(v_matched_users)} 人")
                    total_matched_users += len(v_matched_users)
                else:
                    # 无关键字模式：采集所有评论人
                    print(f"[采集] 无关键字，采集前 20 条评论人信息")
                    for c in comments_data[:20]:
                        author = c.get("author") or ""
                        author_href = c.get("authorHref") or ""
                        if not author_href:
                            continue
                        page.evaluate(f"window.open('{author_href}', '_blank')")
                        time.sleep(2)

                        new_page_found = False
                        for attempt in range(3):
                            all_pages = browser.contexts[0].pages
                            for pg in all_pages:
                                if "xiaohongshu.com/user/profile" in pg.url:
                                    user_info = collect_user_profile(pg)
                                    user_info["comment_content"] = c.get("content") or ""
                                    user_info["comment_time"] = c.get("time") or ""
                                    user_info["comment_likes"] = c.get("likes") or ""
                                    v_matched_users.append(user_info)
                                    pg.close()
                                    time.sleep(0.3)
                                    new_page_found = True
                                    break
                            if new_page_found:
                                break
                            time.sleep(1)
                    print(f"[采集]   本视频采集用户: {len(v_matched_users)} 人")

                # 构建视频数据
                video_entry = {
                    "index": collected_videos + 1,
                    "title": title,
                    "video_id": r.get("href", "").split("/")[-1] if r.get("href") else "",
                    "href": r.get("href"),
                    "likes": "",
                    "comments_count": len(comments_data),
                    "collects": "",
                    "shares": "",
                    "comments": comments_data,
                    "matched_users": v_matched_users,
                }
                video_data.append(video_entry)
                collected_videos += 1

                # 关闭详情弹窗，返回搜索页
                page.keyboard.press("Escape")
                time.sleep(0.5)
                page.keyboard.press("Escape")
                time.sleep(0.8)

            # 5. 输出结果
            output_data = {
                "search_term": keyword,
                "match_keywords": match_keywords,
                "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                "total_videos": len(video_data),
                "total_matched_users": total_matched_users,
                "videos": video_data,
            }

            print(f"\n{'='*60}")
            print(f"采集完成！共 {len(video_data)} 个视频，{total_matched_users} 个匹配用户")
            print(f"{'='*60}")

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    _json.dump(output_data, f, ensure_ascii=False, indent=2)
                print(f"结果已保存: {args.output}")
            else:
                print(_json.dumps(output_data, ensure_ascii=False, indent=2)[:2000])

            return output_data

    elif args.cmd == "interactive":
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(args.cdp)
            except Exception as e:
                print(f"CDP 连接失败: {e}")
                sys.exit(1)

            print("交互模式 - 输入命令:")
            print("  search <关键词>   - 搜索")
            print("  results           - 采集当前搜索结果")
            print("  click <N>         - 点击第N个搜索结果")
            print("  filter            - 打开筛选面板（不加参数）")
            print("  filter --sort 最新 --type 视频 - 应用筛选")
            print("  comments          - 采集当前页评论")
            print("  user              - 采集当前用户主页信息")
            print("  scroll            - 滚动当前页")
            print("  url               - 显示当前URL")
            print("  quit              - 退出")

            while True:
                try:
                    cmd = input("\n> ").strip()
                except EOFError:
                    break
                if not cmd:
                    continue

                parts = cmd.split(maxsplit=1)
                action = parts[0]
                arg = parts[1] if len(parts) > 1 else ""

                page = find_xiaohongshu_page(browser)
                if not page:
                    print("未找到小红书页面")
                    continue

                if action == "quit":
                    print("再见!")
                    break
                elif action == "search":
                    if arg:
                        search_keyword(page, arg)
                        print(f"已搜索: {arg}")
                elif action == "results":
                    results = collect_search_results(page)
                    print_results(results, result_type="搜索")
                elif action.isdigit():
                    idx = int(action)
                    if click_search_result(page, idx):
                        print(f"已点击第 {idx} 个结果")
                elif action == "comments":
                    comments = collect_comments(page)
                    print_results(comments, result_type="评论")
                elif action == "user":
                    user_page = find_user_profile_page(browser)
                    if user_page:
                        info = collect_user_profile(user_page)
                        stats = info.get('stats') or {}
                        print(f"\n  用户名: {info.get('name') or '未知'}")
                        print(f"  小红书号: {info.get('xhsId') or '未知'}")
                        print(f"  IP属地: {info.get('ipLocation') or '未知'}")
                        print(f"  简介: {info.get('bio') or '无'}")
                        print(f"  粉丝: {stats.get('followers', '-')} | 关注: {stats.get('following', '-')} | 笔记: {stats.get('notes', '-')}\n")
                    else:
                        print("未找到用户主页")
                elif action == "scroll":
                    scroll_to_load_more(page)
                    print("已滚动")
                elif action == "filter":
                    if open_filter_panel(page):
                        panel_text = page.evaluate(
                            "() => { const p = document.querySelector('.filter-panel'); return p ? p.innerText : null; }"
                        )
                        print(f"\n筛选面板:\n{panel_text}")
                        page.keyboard.press("Escape")
                elif action == "url":
                    print(page.url)
                else:
                    print("未知命令")


if __name__ == "__main__":
    main()