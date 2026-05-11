#!/usr/bin/env python3
"""
抖音创作者中心 - 获取作品列表

通过 Chrome DevTools Protocol (CDP) 读取已打开的 Chrome 浏览器页面，
获取抖音创作者中心的作品列表。

使用方式:
    python douyin_creator_cli.py list                    # 列出所有标签页
    python douyin_creator_cli.py works                   # 获取作品列表
    python douyin_creator_cli.py following               # 获取关注列表
    python douyin_creator_cli.py unfollow --user 用户名   # 取消关注指定用户
    python douyin_creator_cli.py comments --video 视频标题  # 获取作品评论
    python douyin_creator_cli.py reply --video 视频标题   # 评论自动回复

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


def scroll_and_load_works(page, max_works: int = 10, max_scrolls: int = 20) -> int:
    """
    滚动页面加载指定数量的作品

    策略：
    1. 先检查当前可见作品数量，如果 >= max_works 则停止
    2. 如果显示"没有更多作品"则停止
    3. 如果连续3次滚动没有新增作品则停止（说明已全部加载）
    4. 设置最大滚动次数防止无限循环

    Args:
        page: Playwright page 对象
        max_works: 最大收集作品数量
        max_scrolls: 最大滚动次数

    Returns:
        滚动次数
    """
    import re

    def count_works_in_section(section_text: str) -> int:
        """统计作品列表区域中的作品数量"""
        matches = re.findall(r'\d{2}:\d{2}|\d+张', section_text)
        return len(matches)

    def has_no_more(page_text: str) -> bool:
        """检查是否显示'没有更多作品'"""
        return "没有更多作品" in page_text

    def get_works_section(page_text: str) -> str:
        """提取作品列表区域"""
        start_idx = page_text.find("全部作品")
        if start_idx == -1:
            return ""
        end_idx = page_text.find("没有更多作品")
        if end_idx == -1:
            return page_text[start_idx:]
        return page_text[start_idx:end_idx]

    scroll_count = 0
    last_count = 0
    no_new_works_rounds = 0

    # 先检查初始状态
    page_text = page.inner_text("body")
    works_section = get_works_section(page_text)
    initial_count = count_works_in_section(works_section) if works_section else 0
    print(f"  初始可见 {initial_count} 个作品 (目标: {max_works})")

    # 如果初始就已经达到目标
    if initial_count >= max_works:
        print(f"  [完成] 初始已满足 {max_works} 个作品")
        return 0

    # 如果初始就显示没有更多
    if has_no_more(page_text):
        print("  [完成] 初始已显示没有更多作品")
        return 0

    # 开始滚动
    while scroll_count < max_scrolls:
        # 随机滚动距离: 300-600px（模拟人类）
        scroll_distance = random.randint(300, 600)
        page.evaluate(f"window.scrollBy(0, {scroll_distance})")

        # 随机延迟 0.5-1.5 秒（模拟人类）
        time.sleep(random.uniform(0.5, 1.5))

        scroll_count += 1

        # 检查滚动后的状态
        page_text = page.inner_text("body")
        works_section = get_works_section(page_text)
        current_count = count_works_in_section(works_section) if works_section else 0
        print(f"  滚动 #{scroll_count}: 当前可见 {current_count} 个作品 (目标: {max_works})")

        # 达到目标数量
        if current_count >= max_works:
            print(f"  [完成] 已收集到 {current_count} 个作品")
            return scroll_count

        # 检查是否显示"没有更多作品"
        if has_no_more(page_text):
            print("  [完成] 已显示没有更多作品")
            return scroll_count

        # 检查是否有新增作品
        if current_count > last_count:
            no_new_works_rounds = 0
        else:
            no_new_works_rounds += 1
            # 如果连续3次滚动都没有新增作品，说明已经加载完
            if no_new_works_rounds >= 3:
                print(f"  [完成] 连续 {no_new_works_rounds} 次滚动无新增作品，已加载 {current_count} 个")
                return scroll_count

        last_count = current_count

    print(f"  [完成] 达到最大滚动次数 {max_scrolls}")
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


def get_works(cdp_url: str = "http://127.0.0.1:9222", max_works: int = 10) -> list:
    """
    获取抖音创作者中心的作品列表

    Args:
        cdp_url: CDP 地址
        max_works: 最大收集作品数量

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

        # 滚动加载指定数量的作品
        print(f"\n滚动加载前 {max_works} 个作品...")
        scroll_count = scroll_and_load_works(target_page, max_works=max_works)
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
  1. Chrome 启动命令 (按平台选择):
     macOS:   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
     Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
     Linux:   google-chrome --remote-debugging-port=9222

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

    # works 子命令 - 获取作品列表
    works_parser = subparsers.add_parser("works", help="获取作品列表")
    works_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="收集作品数量 (默认: 10)"
    )

    # following 子命令 - 获取关注列表
    following_parser = subparsers.add_parser("following", help="获取关注列表")

    # unfollow 子命令 - 取消关注
    unfollow_parser = subparsers.add_parser("unfollow", help="取消关注")
    unfollow_parser.add_argument(
        "--user",
        type=str,
        required=True,
        help="要取消关注的用户名"
    )

    # comments 子命令 - 获取作品评论
    comments_parser = subparsers.add_parser("comments", help="获取作品评论")
    comments_parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="视频标题关键字"
    )
    comments_parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="获取评论数量 (默认: 20)"
    )

    # reply 子命令 - 评论自动回复
    reply_parser = subparsers.add_parser("reply", help="评论自动回复")
    reply_parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="视频标题关键字"
    )
    reply_parser.add_argument(
        "--content",
        type=str,
        default="感谢您的评论",
        help="回复内容"
    )
    reply_parser.add_argument(
        "--all",
        action="store_true",
        help="回复所有未回复的评论"
    )

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        return

    if args.action == "list":
        get_tabs(args.cdp)
    elif args.action == "works":
        get_works(args.cdp, max_works=args.count)
    elif args.action == "following":
        get_following(args.cdp)
    elif args.action == "unfollow":
        unfollow(args.cdp, username=args.user)
    elif args.action == "comments":
        get_comments(args.cdp, video_keyword=args.video, max_count=args.count)
    elif args.action == "reply":
        reply_comments(args.cdp, video_keyword=args.video, content=args.content, reply_all=args.all)


def get_following_list(page) -> list:
    """获取关注列表"""
    users = page.evaluate('''
        () => {
            const rows = document.querySelectorAll('table tbody tr');
            return Array.from(rows).map(row => {
                const cells = row.querySelectorAll('td');
                return cells[0].innerText.replace('取消关注', '').trim();
            });
        }
    ''')
    return users


def navigate_to_following(page):
    """导航到关注管理页面"""
    page_text = page.inner_text("body")

    if '关注管理' in page_text:
        page.click('text="关注管理"', timeout=3000)
    elif '互动管理' in page_text:
        page.click('text="互动管理"', timeout=3000)
        time.sleep(1)
        if '关注管理' in page.inner_text("body"):
            page.click('text="关注管理"', timeout=3000)


def unfollow_user(page, username: str) -> bool:
    """
    取消关注指定用户

    Args:
        page: Playwright page 对象
        username: 要取消关注的用户名

    Returns:
        是否成功
    """
    try:
        # 获取当前关注列表
        users = get_following_list(page)

        if username not in users:
            # 尝试模糊匹配
            matched = False
            for u in users:
                if username in u or u in username:
                    username = u  # 使用实际用户名
                    matched = True
                    break
            if not matched:
                print(f"  用户 '{username}' 不在关注列表中")
                print(f"  当前关注列表: {users}")
                return False

        # 找到用户的取消关注按钮并点击
        # 遍历每一行，找到匹配用户名的取消关注按钮
        rows = page.locator('table tbody tr').all()
        for row in rows:
            cells = row.locator('td').all()
            if not cells:
                continue
            name_cell_text = cells[0].inner_text()
            name = name_cell_text.replace('取消关注', '').strip()

            if username in name:
                # 找到取消关注按钮并点击
                row.locator('text="取消关注"').click()
                time.sleep(0.5)

                # 点击确认
                page.locator('text="确认"').click()
                time.sleep(1)
                print(f"  已取消关注: {username}")
                return True

        return False
    except Exception as e:
        print(f"  取消关注失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_following(cdp_url: str = "http://127.0.0.1:9222") -> bool:
    """
    获取关注列表

    Args:
        cdp_url: CDP 地址

    Returns:
        是否成功
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        print("\n正在连接到浏览器...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        print("已连接")

        # 找到创作者中心页面
        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "creator.douyin.com" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            print("未找到抖音创作者中心页面")
            return False

        # 导航到关注管理
        print("\n正在导航到关注管理...")
        navigate_to_following(target_page)
        time.sleep(2)

        print(f"当前页面: {target_page.url}")

        # 显示当前关注列表
        users = get_following_list(target_page)
        print(f"\n当前关注列表 (共 {len(users)} 个):")
        for i, name in enumerate(users, 1):
            print(f"  [{i}] {name}")

        browser.close()
        return True


def unfollow(cdp_url: str = "http://127.0.0.1:9222", username: str = None) -> bool:
    """
    取消关注功能

    Args:
        cdp_url: CDP 地址
        username: 要取消关注的用户名

    Returns:
        是否成功
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        print("\n正在连接到浏览器...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        print("已连接")

        # 找到创作者中心页面
        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "creator.douyin.com" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            print("未找到抖音创作者中心页面")
            return False

        # 导航到关注管理
        print("\n正在导航到关注管理...")
        navigate_to_following(target_page)
        time.sleep(2)

        print(f"当前页面: {target_page.url}")

        # 显示当前关注列表
        users = get_following_list(target_page)
        print(f"\n当前关注列表 (共 {len(users)} 个):")
        for i, name in enumerate(users, 1):
            print(f"  [{i}] {name}")

        # 取消关注指定用户
        print(f"\n正在取消关注用户: {username}")
        success = unfollow_user(target_page, username)
        if success:
            print("取消关注成功")
            # 显示更新后的列表
            users = get_following_list(target_page)
            print(f"\n更新后关注列表 (共 {len(users)} 个):")
            for i, name in enumerate(users, 1):
                print(f"  [{i}] {name}")
        else:
            print("取消关注失败")

        browser.close()
        return True


def get_comments(cdp_url: str = "http://127.0.0.1:9222", video_keyword: str = None, max_count: int = 20) -> list:
    """
    获取指定视频的评论列表

    Args:
        cdp_url: CDP 地址
        video_keyword: 视频标题关键字
        max_count: 最大获取评论数量

    Returns:
        评论列表
    """
    from playwright.sync_api import sync_playwright

    if not video_keyword:
        print("错误: 需要指定视频标题关键字 (--video)")
        return []

    with sync_playwright() as p:
        print("\n正在连接到浏览器...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        print("已连接")

        # 找到创作者中心页面
        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "creator.douyin.com" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            print("未找到抖音创作者中心页面")
            return False

        # 导航到评论管理
        print("\n正在导航到评论管理...")
        target_page.goto('https://creator.douyin.com/creator-micro/interactive/comment', timeout=10000)
        target_page.wait_for_load_state('networkidle', timeout=15000)
        time.sleep(2)

        # 点击选择作品
        print(f"\n正在选择视频: {video_keyword}")
        target_page.click('text="选择作品"', timeout=5000)
        time.sleep(2)

        # 在列表中滚动查找视频
        for scroll_num in range(20):
            page_text = target_page.inner_text('body')
            if video_keyword in page_text:
                # 找到了，找到该视频的行并点击
                lines = page_text.split('\n')
                for line in lines:
                    if video_keyword in line:
                        try:
                            # 使用更精确的选择器
                            dialog = target_page.locator('[role="dialog"], .select-video, [class*=dialog]').first
                            dialog.get_by_text(line.strip(), exact=False).click(timeout=3000)
                            print(f'已选择视频: {line[:40]}...')
                            time.sleep(2)
                            break
                        except Exception as e:
                            print(f'点击失败: {e}')
                            # 备选方案：直接在页面上查找
                            try:
                                target_page.get_by_text(line.strip(), exact=False).last.click(timeout=3000)
                                print(f'已选择视频(备选): {line[:40]}...')
                                time.sleep(2)
                                break
                            except Exception as e2:
                                print(f'备选点击也失败: {e2}')
                break
            # 滚动列表
            try:
                target_page.evaluate('document.querySelector("[class*=list]").scrollBy(0, 300)')
            except:
                pass
            time.sleep(random.uniform(0.5, 1.0))
            print(f'滚动 #{scroll_num + 1}...')
        else:
            print(f'未找到包含 "{video_keyword}" 的视频')
            browser.close()
            return []

        print(f"当前页面: {target_page.url}")

        # 滚动加载评论（直到"没有更多评论"）
        print(f"\n滚动加载评论...")
        for scroll_num in range(50):
            page_text = target_page.inner_text('body')
            if '没有更多评论' in page_text:
                print(f'  [完成] 已加载到底')
                break
            target_page.evaluate('window.scrollBy(0, 300)')
            time.sleep(random.uniform(0.5, 1.5))
            print(f'  滚动 #{scroll_num + 1}')
        else:
            print(f'  [完成] 达到最大滚动次数')

        # 解析评论
        print("\n解析评论数据...")
        comments = parse_comments_from_page_v2(target_page)

        # 打印结果
        print_comments(comments)

        browser.close()
        return comments


def parse_comments_from_page_v2(page) -> list:
    """
    解析页面中的评论列表（基于实际页面结构）

    页面结构:
    最新发布
    爱你呦
    16分钟前
    回复测试
    0
    回复
    删除
    举报
    查看1条回复
    爱你呦
    17分钟前
    你好
    0
    回复
    删除
    举报
    没有更多评论

    Args:
        page: Playwright page 对象

    Returns:
        评论列表
    """
    page_text = page.inner_text('body')

    # 找到评论区域
    start_idx = page_text.find('最新发布')
    if start_idx == -1:
        return []

    end_idx = page_text.find('没有更多评论')
    if end_idx == -1:
        end_idx = len(page_text)

    comments_section = page_text[start_idx:end_idx]
    lines = comments_section.split('\n')

    comments = []
    current_comment = None

    skip_words = ['最新发布', '回复', '删除', '举报', '查看1条回复', '没有更多评论',
                  '取消', '发送', '选择作品', '评论管理', '发布于']

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 先检查是否有回复标记（不影响跳过逻辑）
        if '查看1条回复' in line and current_comment:
            current_comment['has_replied'] = True

        # 跳过无用行
        if not line or any(x in line for x in skip_words):
            # 保存当前评论（如果存在）
            if current_comment and current_comment.get('content'):
                comments.append(current_comment)
                current_comment = None
            i += 1
            continue

        # 检查是否是时间格式（如"16分钟前"）
        if '分钟前' in line or '小时前' in line or '天前' in line:
            if current_comment:
                current_comment['time'] = line
            i += 1
            continue

        # 检查是否是数字（点赞数）
        if line.isdigit() and current_comment:
            current_comment['like_count'] = line
            i += 1
            continue

        # 检查是否是用户名（一行文字，后面跟着时间）
        if current_comment is None:
            current_comment = {
                'username': line,
                'content': '',
                'time': '',
                'like_count': '0',
                'has_replied': False
            }
            i += 1
            continue

        # 如果有当前评论，检查是否是内容
        if current_comment and not current_comment['content']:
            # 内容不是时间，不是数字，不是"回复"等按钮
            if '分钟前' not in line and '小时前' not in line and '天前' not in line \
               and not line.isdigit() and line not in ['回复', '删除', '举报']:
                current_comment['content'] = line
                i += 1
                continue

        # 如果当前评论已有内容，保存它开始新的
        if current_comment and current_comment['content']:
            comments.append(current_comment)
            current_comment = None

        i += 1

    # 保存最后一个评论
    if current_comment and current_comment['content']:
        comments.append(current_comment)

    return comments


def reply_comments(cdp_url: str = "http://127.0.0.1:9222", video_keyword: str = None,
                   content: str = "感谢您的评论", reply_all: bool = False) -> bool:
    """
    评论自动回复功能

    Args:
        cdp_url: CDP 地址
        video_keyword: 视频标题关键字
        content: 回复内容
        reply_all: 是否回复所有未回复的评论

    Returns:
        是否成功
    """
    from playwright.sync_api import sync_playwright

    if not video_keyword:
        print("错误: 需要指定视频标题关键字 (--video)")
        return False

    with sync_playwright() as p:
        print("\n正在连接到浏览器...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        print("已连接")

        # 找到创作者中心页面
        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "creator.douyin.com" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            print("未找到抖音创作者中心页面")
            return False

        # 导航到评论管理
        print("\n正在导航到评论管理...")
        target_page.goto('https://creator.douyin.com/creator-micro/interactive/comment', timeout=10000)
        target_page.wait_for_load_state('networkidle', timeout=15000)
        time.sleep(2)

        # 点击选择作品
        print(f"\n正在选择视频: {video_keyword}")
        target_page.click('text="选择作品"', timeout=5000)
        time.sleep(2)

        # 在列表中滚动查找视频
        for scroll_num in range(20):
            page_text = target_page.inner_text('body')
            if video_keyword in page_text:
                lines = page_text.split('\n')
                for line in lines:
                    if video_keyword in line:
                        try:
                            # 使用 dialog 中的元素，因为页面上可能有两个匹配的元素
                            target_page.get_by_role('dialog').get_by_text(line.strip()).click(timeout=3000)
                            print(f'已选择视频: {line[:40]}...')
                            time.sleep(2)
                            break
                        except Exception as e:
                            print(f'点击失败: {e}')
                break
            target_page.evaluate('document.querySelector("[class*=list]").scrollBy(0, 300)')
            time.sleep(random.uniform(0.5, 1.0))
            print(f'滚动 #{scroll_num + 1}...')
        else:
            print(f'未找到包含 "{video_keyword}" 的视频')
            browser.close()
            return False

        # 滚动加载评论
        print("\n滚动加载评论...")
        for scroll_num in range(50):
            page_text = target_page.inner_text('body')
            if '没有更多评论' in page_text:
                print(f'  [完成] 已加载到底')
                break
            target_page.evaluate('window.scrollBy(0, 300)')
            time.sleep(random.uniform(0.5, 1.5))

        # 解析评论
        print("\n解析评论数据...")
        comments = parse_comments_from_page_v2(target_page)

        if not comments:
            print("没有评论可回复")
            browser.close()
            return False

        print(f"共找到 {len(comments)} 条评论")

        # 筛选未回复的评论
        unreplied = [c for c in comments if not c['has_replied']]
        print(f"其中 {len(unreplied)} 条未回复")

        if not unreplied:
            print("所有评论都已回复")
            browser.close()
            return True

        # 回复评论
        if reply_all:
            print(f"\n开始自动回复所有 {len(unreplied)} 条评论...")
            for i, comment in enumerate(unreplied, 1):
                print(f"\n[{i}/{len(unreplied)}] 回复: {comment['username']} - {comment['content'][:30]}...")

                # 找到回复按钮并点击
                reply_btns = target_page.locator('text="回复"').all()
                if i - 1 < len(reply_btns):
                    try:
                        reply_btns[i - 1].click()
                        time.sleep(1)

                        # 使用placeholder定位输入框
                        target_page.locator('[placeholder^="回复 "]').click()
                        time.sleep(0.3)

                        # 输入回复内容
                        target_page.keyboard.type(content, delay=50)
                        time.sleep(0.5)

                        # 点击发送（第二个发送按钮）
                        target_page.locator('text="发送"').nth(1).click()
                        time.sleep(2)

                        print(f"  回复成功")
                    except Exception as e:
                        print(f"  回复失败: {e}")
                else:
                    print(f"  未找到回复按钮")
        else:
            print("\n使用 --all 参数回复所有未回复评论")

        browser.close()
        return True


def print_comments(comments: list):
    """打印评论列表"""
    print("\n" + "=" * 60)
    print(f"  评论列表 (共 {len(comments)} 条)")
    print("=" * 60)

    for i, comment in enumerate(comments, 1):
        username = comment.get('username', '未知用户')
        content = comment.get('content', '')
        time_str = comment.get('time', '')
        like_count = comment.get('like_count', '0')

        print(f"\n [{i}] {username}")
        if time_str:
            print(f"     时间: {time_str}")
        print(f"     点赞: {like_count}")
        print(f"     内容: {content[:100]}{'...' if len(content) > 100 else ''}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()