#!/usr/bin/env python3
"""
抖音评论监控脚本
持续监控指定视频的新评论，匹配关键词后打印提醒
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# 读取配置
config_path = Path.home() / ".hermes/skills/douyin-auto-reply/config.json"
with open(config_path) as f:
    config = json.load(f)

KEYWORDS = config.get("keywords", {})
VIDEO_URL = "https://www.douyin.com/video/7619703556590292395"

# 已见过的评论ID集合（避免重复提醒）
seen_ids = set()


def match_keyword(text: str) -> Optional[Tuple[str, str]]:
    """匹配关键词，返回 (关键词, 回复内容) 或 None"""
    text_lower = text.lower()
    for kw, reply in KEYWORDS.items():
        if kw.lower() in text_lower:
            return (kw, reply)
    return None


def parse_cookies(raw_cookie: str) -> list:
    """解析 Cookie 字符串为 Playwright 格式"""
    cookie_list = []
    for part in raw_cookie.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookie_list.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".douyin.com",
                "path": "/"
            })
    return cookie_list


async def extract_comments(page) -> list:
    """提取当前页面可见的评论"""
    try:
        result = await page.evaluate("""
            () => {
                // 找评论区域
                const containers = document.querySelectorAll('[class*="comment"], [id*="comment"]');
                const results = [];

                for (const container of containers) {
                    // 获取直接子元素（评论项）
                    const items = container.querySelectorAll(':scope > *');
                    for (const item of items) {
                        const rect = item.getBoundingClientRect();
                        const text = (item.textContent || '').trim();

                        // 过滤：可见、有内容、不是导航元素
                        if (rect.width < 30 || rect.height < 20) continue;
                        if (text.length < 5 || text.length > 500) continue;

                        // 生成伪ID
                        const id = text.slice(0, 60).replace(/\\s+/g, '_');
                        results.push({ id, text: text.slice(0, 200) });
                    }
                }
                return results;
            }
        """)
        return result
    except Exception as e:
        return []


async def monitor_comments(browser, page, interval: int = 10):
    """每隔 interval 秒检查一次新评论"""
    print(f"🔍 开始监控评论，间隔 {interval} 秒")
    print(f"📋 监控视频：{VIDEO_URL}")
    print(f"🔑 关键词：{list(KEYWORDS.keys())}")
    print("=" * 50)

    while True:
        try:
            comments = await extract_comments(page)
            new_found = False

            for c in comments:
                cid = c.get('id', '')
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    text = c.get('text', '')
                    new_found = True

                    # 尝试提取作者名
                    author = text.split('·')[0].strip() if '·' in text else '未知'
                    match = match_keyword(text)

                    print(f"\n{'='*50}")
                    print(f"🆕 新评论 [{author}]")
                    print(f"   内容：{text[:120]}")
                    print(f"   ID：{cid[:30]}...")

                    if match:
                        kw, reply = match
                        print(f"   ✅ 匹配关键词「{kw}」")
                        print(f"   💬 建议回复：{reply}")
                        print(f"   ⚠️  回复前会先确认，是否继续？")
                    else:
                        print(f"   ⚪ 无关键词匹配")

            if not new_found:
                print(f"\r⏳ [{time.strftime('%H:%M:%S')}] 监控中... 已见 {len(seen_ids)} 条评论", end='', flush=True)

        except Exception as e:
            print(f"\n[错误] {e}")

        await asyncio.sleep(interval)


async def main():
    from playwright.async_api import async_playwright

    project_root = Path(__file__).parent.parent
    browsers_path = project_root / "playwright_browsers"
    chromium_path = browsers_path / "chromium-1208" / "chrome-mac-arm64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"

    raw_cookies = config.get("douyin_cookie", "")
    cookie_list = parse_cookies(raw_cookies)
    print(f"Loaded {len(cookie_list)} cookies")

    async with async_playwright() as p:
        print("Launching browser (should appear on your screen now)...")
        browser = await p.chromium.launch_persistent_context(
            executable_path=str(chromium_path),
            headless=False,
            user_data_dir="/tmp/chrome-hermes-monitor",
            args=["--disable-blink-features=AutomationControlled"],
        )

        await browser.add_cookies(cookie_list)
        print("Cookies injected")

        page = browser.pages[0] if browser.pages else await browser.new_page()
        print(f"Opening {VIDEO_URL}...")
        await page.goto(VIDEO_URL, timeout=30000)
        await page.wait_for_load_state("domcontentloaded", timeout=20000)
        await asyncio.sleep(8)  # 等待页面渲染

        print(f"✅ 页面标题：{await page.title()}")
        print(f"✅ 浏览器已启动，窗口应在你的屏幕上")
        print()

        try:
            await monitor_comments(browser, page, interval=10)
        except KeyboardInterrupt:
            print("\n\n⏹ 已停止监控")
        finally:
            await browser.close()
            print("浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
