"""
抖音浏览器自动化 — 定位输入框并输入指定内容
使用 Playwright CDP 连接模式，模拟人工操作，避免触发验证码
"""

import json
import os
import re
import sys
import time
import random
import asyncio
from pathlib import Path
from playwright.sync_api import sync_playwright

# Re-export from submodules for backward compatibility
from core_modules.browser.locators import (
    SEARCH_SELECTORS,
    find_search_input,
)
from core_modules.browser.cookies import (
    load_cookies_from_file,
    inject_cookies,
    _refresh_cookies,
)
from core_modules.browser.actions import (
    random_delay,
    type_human_like,
    get_first_video_item,
    click_first_video,
    is_filter_panel_open,
    toggle_filter_panel,
    get_filter_options,
    apply_filter,
    process_one_video,
    go_next_video,
    is_comment_panel_open,
    dismiss_dialog_if_present,
    scroll_comment_area,
    extract_comments,
    get_video_id,
    get_video_ai_notes,
    get_video_title,
    get_video_stats,
    save_results,
    save_comments,
    extract_user_profile,
    match_comment_and_click_user,
    _immediate_dm_send,
    _send_dm_to_matched_users,
    save_user_profiles,
    search_via_cdp,
    search_via_launch,
    send_dm_via_cdp,
)

# Keep module-level constants for existing imports
SEARCH_TEXT = "你的搜索内容"
USE_CDP = True
CDP_URL = "http://127.0.0.1:9222"
COOKIE_FILE = "cookies.json"


def _get_dm_sent_store():
    """延迟导入，避免循环依赖"""
    from app.task_store import get_dm_sent_store
    return get_dm_sent_store()


def random_delay(min_s=0.5, max_s=1.0):
    """随机延迟，模拟人工操作间隔"""
    time.sleep(random.uniform(min_s, max_s))


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="抖音搜索 + 评论采集 + 用户主页信息提取"
    )
    parser.add_argument(
        "-s", "--search",
        default=SEARCH_TEXT,
        help="搜索关键词"
    )
    parser.add_argument(
        "-k", "--keywords",
        default=None,
        help="评论匹配关键字，多个用 | 分隔，如 '怎么买|多少钱'"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=5,
        help="处理的视频数量，默认 5"
    )
    parser.add_argument(
        "-t", "--time",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="发布时间筛选: 1=一天内, 2=一周内, 3=半年内"
    )
    parser.add_argument(
        "-m", "--dm",
        dest="dm_message",
        default=None,
        help="私信内容（指定后自动向采集到的用户发送私信）"
    )

    args = parser.parse_args()

    # 解析
    search_text = args.search
    match_keywords = None
    if args.keywords:
        match_keywords = [kw.strip() for kw in args.keywords.split("|") if kw.strip()]
    video_count = args.count

    # 时间筛选映射
    TIME_MAP = {1: "一天内", 2: "一周内", 3: "半年内"}
    time_filter = TIME_MAP.get(args.time) if args.time else None

    # 排序默认"最新发布"
    sort_by = "最新发布"

    print(f"搜索内容: {search_text}")
    if match_keywords:
        print(f"匹配关键字: {' | '.join(match_keywords)}")
    print(f"视频数量: {video_count}")
    print(f"排序: {sort_by}")
    if time_filter:
        print(f"发布时间: {time_filter}")
    dm_message = args.dm_message
    if dm_message:
        print(f"私信内容: {dm_message}")
        print(f"模式: {'CDP连接' if USE_CDP else '启动新浏览器'}")
        if COOKIE_FILE:
            print(f"Cookie: {COOKIE_FILE}")

        if USE_CDP:
            search_via_cdp(search_text, cookie_file=COOKIE_FILE, match_keywords=match_keywords,
                           video_count=video_count, sort_by=sort_by, time_filter=time_filter,
                           dm_message=dm_message)
        else:
            search_via_launch(search_text, cookie_file=COOKIE_FILE, match_keywords=match_keywords,
                              video_count=video_count, sort_by=sort_by, time_filter=time_filter,
                              dm_message=dm_message)
    else:
        print(f"模式: {'CDP连接' if USE_CDP else '启动新浏览器'}")
        if COOKIE_FILE:
            print(f"Cookie: {COOKIE_FILE}")

        if USE_CDP:
            search_via_cdp(search_text, cookie_file=COOKIE_FILE, match_keywords=match_keywords,
                           video_count=video_count, sort_by=sort_by, time_filter=time_filter)
        else:
            search_via_launch(search_text, cookie_file=COOKIE_FILE, match_keywords=match_keywords,
                              video_count=video_count, sort_by=sort_by, time_filter=time_filter)