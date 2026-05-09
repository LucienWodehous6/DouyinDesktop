#!/usr/bin/env python3
"""
抖音创作者中心 - 获取作品列表

通过 Chrome DevTools Protocol (CDP) 读取已打开的 Chrome 浏览器页面，
获取抖音创作者中心的作品列表。

使用方式:
    python douyin_creator_cli.py list                    # 列出所有标签页
    python douyin_creator_cli.py works                   # 获取作品列表

依赖:
    pip install playwright
    playwright install chromium

Chrome 启动参数:
    Google Chrome --remote-debugging-port=9222
"""

import argparse
import random
import time
import json
import sys


def get_tabs(cdp_url: str = "http://127.0.0.1:9222"):
    """列出所有打开的标签页"""
    import urllib.request

    try:
        req = urllib.request.Request(f"{cdp_url}/json/list")
        with urllib.request.urlopen(req, timeout=5) as resp:
            tabs = json.loads(resp.read().decode())

        print(f"\n CDP 连接到: {cdp_url}")
        print(f" 发现 {len(tabs)} 个标签页\n")
        print("=" * 60)

        for i, tab in enumerate(tabs):
            title = tab.get('title', '')[:50]
            url = tab.get('url', '')[:70]
            print(f" [{i}] {title}")
            print(f"     URL: {url}")
            print()

        return tabs

    except Exception as e:
        print(f"连接失败: {e}")
        print("\n请确保 Chrome 已启动并开启 CDP:")
        print("  Chrome --remote-debugging-port=9222")
        return []


def find_douyin_creator_page(browser) -> object:
    """找到抖音创作者中心页面"""
    for ctx in browser.contexts:
        for page in ctx.pages:
            url = page.url
            if "creator.douyin.com" in url and "content/manage" in url:
                return page
            elif "creator.douyin.com" in url:
                return page
    return None


def click_menu_by_text(page, text: str, max_retries: int = 3):
    """
    通过文本内容点击菜单（不依赖 class）

    Args:
        page: Playwright page 对象
        text: 要点击的文本
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            page.click(f'text="{text}"', timeout=3000)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                raise e
    return False


def scroll_and_load_all(page, check_text: str = "没有更多作品") -> int:
    """
    滚动页面直到加载完成

    Args:
        page: Playwright page 对象
        check_text: 检查是否加载完成的文本

    Returns:
        滚动次数
    """
    scroll_count = 0
    max_scrolls = 20

    while scroll_count < max_scrolls:
        # 随机滚动距离: 300-600px（模拟人类）
        scroll_distance = random.randint(300, 600)

        page.evaluate(f"window.scrollBy(0, {scroll_distance})")

        # 随机延迟 0.5-1.5 秒（模拟人类）
        time.sleep(random.uniform(0.5, 1.5))

        # 检查是否加载完成
        if check_text in page.inner_text("body"):
            return scroll_count + 1

        scroll_count += 1

    return scroll_count


def parse_works_from_page(page) -> list:
    """
    解析页面中的作品列表

    Args:
        page: Playwright page 对象

    Returns:
        作品列表
    """
    import re

    content = page.inner_text("body")
    lines = content.split("\n")

    works = []
    current_work = None

    for line in lines:
        line = line.strip()

        # 检测状态
        if line in ["已发布", "审核中", "未通过", "私密"]:
            if current_work and "状态" not in current_work:
                current_work["状态"] = line

        # 检测日期（作品时间）
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})', line)
        if date_match:
            if current_work and "时间" not in current_work:
                current_work["时间"] = date_match.group(1)
                works.append(current_work)
            current_work = {"时间": date_match.group(1), "标题": "", "状态": ""}

        # 检测播放数据
        if "播放" in line and current_work:
            data_parts = line.split()
            for i, part in enumerate(data_parts):
                if "播放" in part and i > 0:
                    current_work["播放"] = data_parts[i - 1]
                if "点赞" in part and i > 0:
                    current_work["点赞"] = data_parts[i - 1]
                if "评论" in part and i > 0:
                    current_work["评论"] = data_parts[i - 1]
                if "分享" in part and i > 0:
                    current_work["分享"] = data_parts[i - 1]

        # 收集标题（找到时间和状态之间的文本）
        if current_work and not current_work["标题"]:
            if line and len(line) > 3 and len(line) < 200:
                if not any(x in line for x in ["已发布", "审核中", "未通过", "私密", "没有更多"]):
                    if not re.search(r'\d{4}年\d{2}月', line):
                        if not any(x in line for x in ["播放", "点赞", "评论", "分享", "编辑作品", "设置权限"]):
                            current_work["标题"] = line

    # 清理空标题
    for work in works:
        if not work.get("标题"):
            work["标题"] = "(无标题)"

    return works


def print_works(works: list):
    """打印作品列表"""
    print("\n" + "=" * 60)
    print(f"  作品列表 (共 {len(works)} 个)")
    print("=" * 60)

    for i, work in enumerate(works, 1):
        print(f"\n [{i}] {work.get('标题', 'N/A')}")
        print(f"     时间: {work.get('时间', 'N/A')}")
        print(f"     状态: {work.get('状态', 'N/A')}")

        # 播放数据
        plays = work.get("播放", "-")
        likes = work.get("点赞", "-")
        comments = work.get("评论", "-")
        shares = work.get("分享", "-")

        print(f"     播放:{plays} 点赞:{likes} 评论:{comments} 分享:{shares}")

    print("\n" + "=" * 60)


def get_works(cdp_url: str = "http://127.0.0.1:9222") -> list:
    """
    获取抖音创作者中心的作品列表

    Args:
        cdp_url: CDP 地址

    Returns:
        作品列表
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        print("\n正在连接到浏览器...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        print("已连接")

        # 找到创作者中心页面
        print("正在定位抖音创作者中心页面...")
        page = find_douyin_creator_page(browser)

        if not page:
            print("未找到抖音创作者中心页面，请先在 Chrome 中打开")
            browser.close()
            return []

        print(f"找到页面: {page.url}")

        # 点击"作品管理"
        print('\n点击"作品管理"...')
        click_menu_by_text(page, "作品管理")
        time.sleep(1.5)  # 等待页面加载

        print(f"当前页面: {page.url}")

        # 滚动加载完整列表
        print("\n滚动加载完整作品列表...")
        scroll_count = scroll_and_load_all(page)
        print(f"滚动 {scroll_count} 次完成")

        # 解析作品列表
        print("\n解析作品数据...")
        works = parse_works_from_page(page)

        # 打印结果
        print_works(works)

        browser.close()
        return works


def main():
    parser = argparse.ArgumentParser(
        description="抖音创作者中心 CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python douyin_creator_cli.py list                 # 列出所有标签页
  python douyin_creator_cli.py works                # 获取作品列表
  python douyin_creator_cli.py --cdp http://localhost:9222 works

前置条件:
  1. Chrome 启动命令:
     /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

  2. 安装 playwright:
     pip install playwright && playwright install chromium
        """
    )

    parser.add_argument(
        "--cdp",
        default="http://127.0.0.1:9222",
        help="CDP 地址 (默认: http://127.0.0.1:9222)"
    )

    subparsers = parser.add_subparsers(dest="action", help="操作命令")

    subparsers.add_parser("list", help="列出所有标签页")
    subparsers.add_parser("works", help="获取作品列表")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        return

    if args.action == "list":
        get_tabs(args.cdp)
    elif args.action == "works":
        get_works(args.cdp)


if __name__ == "__main__":
    main()