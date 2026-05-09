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


def find_and_click_works_menu(page):
    """
    找到并点击作品管理菜单（兼容不同账号版本）

    策略：
    1. 先尝试"作品管理"
    2. 如果没有，再尝试"内容管理" -> 子菜单会出现"作品管理"

    Args:
        page: Playwright page 对象

    Returns:
        是否成功
    """
    # 先检查页面文本
    page_text = page.inner_text("body")

    if "作品管理" in page_text:
        # 直接点击"作品管理"
        print('找到"作品管理"，直接点击')
        page.click('text="作品管理"', timeout=3000)
        return True

    if "内容管理" in page_text:
        print('未找到"作品管理"，先点击"内容管理"')
        page.click('text="内容管理"', timeout=3000)
        time.sleep(1.5)

        # 检查子菜单是否出现"作品管理"
        page_text = page.inner_text("body")
        if "作品管理" in page_text:
            print('点击"内容管理"后出现"作品管理"，点击')
            page.click('text="作品管理"', timeout=3000)
            return True

    return False


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


def wait_for_navigation(page, expected_url_contains: str, timeout: int = 5000):
    """等待页面导航到指定 URL"""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    try:
        page.wait_for_url(lambda url: expected_url_contains in url, timeout=timeout)
        return True
    except PlaywrightTimeout:
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

    页面结构可能有两种顺序:
    顺序1: 时长 → 标题 → 操作按钮 → 时间 → 状态 → 播放数据
    顺序2: 时长 → 状态 → 标题 → 操作按钮 → 时间 → 播放数据

    Args:
        page: Playwright page 对象

    Returns:
        作品列表
    """
    import re

    content = page.inner_text("body")

    # 找到作品列表部分
    start_idx = content.find("全部作品")
    if start_idx == -1:
        return []

    # 找到"没有更多作品"的位置
    end_idx = content.find("没有更多作品")
    if end_idx == -1:
        end_idx = len(content)

    works_section = content[start_idx:end_idx]
    lines = works_section.split("\n")

    works = []
    current_work = None

    skip_words = ["全部作品", "已发布", "审核中", "未通过", "私密",
                   "编辑作品", "设置权限", "作品置顶", "删除作品",
                   "共", "个作品", "没有更多", "高清发布", "首页",
                   "活动管理", "内容管理", "互动管理", "数据中心",
                   "变现中心", "创作中心", "通知", "网址", "抖音",
                   "播放", "点赞", "评论", "分享", "收藏",
                   "流量减少", "查看详情", "文案展开率", "平均浏览图片"]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 跳过无用的行
        if not line or any(x in line for x in skip_words):
            i += 1
            continue

        # 检测时长行（如 "00:32" 或 "1张"）
        duration_match = re.match(r'^(\d{2}:\d{2})$|^(\d+张)$', line)
        if duration_match:
            # 保存上一个作品
            if current_work and "时间" in current_work:
                works.append(current_work)

            # 开始新作品
            current_work = {
                "时长": line,
                "标题": "",
                "时间": "",
                "状态": "",
                "播放": "-",
                "点赞": "-",
                "评论": "-",
                "分享": "-"
            }
            i += 1

            # 可能是状态（如"私密"）在标题之前
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line in ["已发布", "审核中", "未通过", "私密"]:
                    current_work["状态"] = next_line
                    i += 1

            # 找标题（下一行是标题，除非是时间或操作按钮）
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line and not re.search(r'\d{4}年', next_line) and not any(x in next_line for x in ["编辑作品", "设置权限", "作品置顶", "删除作品"]):
                    current_work["标题"] = next_line
                    i += 1

            # 跳过操作按钮行
            while i < len(lines) and any(x in lines[i] for x in ["编辑作品", "设置权限", "作品置顶", "删除作品"]):
                i += 1

            # 找时间和状态
            while i < len(lines):
                next_line = lines[i].strip()
                if re.search(r'\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}', next_line):
                    current_work["时间"] = next_line
                    i += 1
                elif next_line in ["已发布", "审核中", "未通过", "私密"]:
                    current_work["状态"] = next_line
                    i += 1
                elif "播放" in next_line:
                    # 解析播放数据
                    parts = next_line.split()
                    for j, part in enumerate(parts):
                        if "播放" in part and j > 0:
                            current_work["播放"] = parts[j - 1]
                        if "点赞" in part and j > 0:
                            current_work["点赞"] = parts[j - 1]
                        if "评论" in part and j > 0:
                            current_work["评论"] = parts[j - 1]
                        if "分享" in part and j > 0:
                            current_work["分享"] = parts[j - 1]
                    i += 1
                    break
                else:
                    i += 1
                    if current_work.get("时间"):
                        break
        else:
            i += 1

    # 保存最后一个作品
    if current_work and "时间" in current_work:
        works.append(current_work)

    return works


def print_works(works: list):
    """打印作品列表"""
    print("\n" + "=" * 60)
    print(f"  作品列表 (共 {len(works)} 个)")
    print("=" * 60)

    for i, work in enumerate(works, 1):
        print(f"\n [{i}] {work.get('标题', 'N/A')[:50]}")
        print(f"     时长: {work.get('时长', 'N/A')}")
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

        # 找到或创建创作者中心页面
        print("正在打开抖音创作者中心...")

        # 先尝试找到已存在的页面
        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "creator.douyin.com" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            # 如果没有已存在的页面，创建新的
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            target_page = context.new_page()
            target_page.goto("https://creator.douyin.com/", wait_until="domcontentloaded", timeout=30000)

        print(f"已打开: {target_page.url}")

        # 等待页面加载
        time.sleep(2)

        # 点击"作品管理"（兼容不同账号版本）
        print('\n点击"作品管理"...')
        find_and_click_works_menu(target_page)
        time.sleep(1.5)  # 等待页面加载

        print(f"当前页面: {target_page.url}")

        # 滚动加载完整列表
        print("\n滚动加载完整作品列表...")
        scroll_count = scroll_and_load_all(target_page)
        print(f"滚动 {scroll_count} 次完成")

        # 解析作品列表
        print("\n解析作品数据...")
        works = parse_works_from_page(target_page)

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