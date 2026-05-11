#!/usr/bin/env python3
"""
抖音图文发布脚本
用法:
    python3 douyin_publisher.py --title "标题" --content "正文" --images /path/to/img1.jpg,img2.png
    python3 douyin_publisher.py --title "xxx" --content "xxx" --cookie "sid_tt=xxx;..."
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright


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


async def publish_image_text(cookies: list, title: str, content: str, images: list,
                              chromium_path: str, user_data_dir: str):
    """
    发布抖音图文
    流程：打开创作者中心 → 找发布图文入口 → 填写内容 → 上传图片 → 发布
    不依赖 class，使用文本定位和 JS 注入
    """
    async with async_playwright() as p:
        print("启动浏览器...")
        browser = await p.chromium.launch_persistent_context(
            executable_path=chromium_path,
            headless=False,
            user_data_dir=user_data_dir,
            args=["--disable-blink-features=AutomationControlled"],
        )

        if cookies:
            await browser.add_cookies(cookies)
            print(f"已注入 {len(cookies)} 个 Cookie")

        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Step 1: 打开创作者中心
        print("打开创作者中心...")
        await page.goto("https://creator.douyin.com/", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/step1_creator.png")

        title_text = await page.title()
        page_html = await page.content()
        print(f"页面标题: {title_text}")

        if "登录" in title_text or "登录" in page_html[:1000]:
            print("未登录，请先扫码登录。浏览器将保持打开...")
            await asyncio.Event().wait()
            return

        # Step 2: 点击「发布图文」
        print("\n查找发布图文入口...")
        clicked = False

        # 尝试各种文本定位方式
        text_options = ["发布图文", "图文", "发布作品", "发布视频"]
        for txt in text_options:
            try:
                count = await page.locator(f"text={txt}").count()
                if count > 0:
                    print(f"  找到文本 '{txt}' ({count}个)，点击第1个")
                    await page.locator(f"text={txt}").first.click()
                    clicked = True
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"  text={txt} 失败: {e}")

        # 如果 locator 失败，用 JS 直接点击
        if not clicked:
            print("  使用 JS 点击...")
            try:
                await page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('*');
                        for (const el of all) {
                            if (el.children.length === 0) {
                                const t = el.textContent || '';
                                if (t.includes('发布图文') && el.clientWidth > 0) {
                                    el.click();
                                    return;
                                }
                            }
                        }
                    }
                """)
                clicked = True
                await asyncio.sleep(3)
            except Exception as e:
                print(f"  JS点击失败: {e}")

        if not clicked:
            print("无法找到发布图文入口，请手动点击。浏览器保持打开。")
            await asyncio.Event().wait()
            return

        await page.screenshot(path="/tmp/step2_publish_page.png")
        print(f"发布页截图: /tmp/step2_publish_page.png")

        # Step 3: 填写标题（JS 注入）
        if title:
            print(f"\n填写标题: {title[:30]}...")
            try:
                title_js = json.dumps(title)
                await page.evaluate(f"""
                    () => {{
                        const inputs = document.querySelectorAll('input, textarea');
                        for (const input of inputs) {{
                            const ph = input.getAttribute('placeholder') || '';
                            const label = input.getAttribute('aria-label') || '';
                            if (ph.includes('标题') || label.includes('标题')) {{
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, {title_js});
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return;
                            }}
                        }}
                    }}
                """)
                print("  标题填写完成")
            except Exception as e:
                print(f"  标题填写失败: {e}")

        await asyncio.sleep(1)

        # Step 4: 填写正文（JS 注入富文本）
        if content:
            print(f"\n填写正文: {content[:30]}...")
            try:
                content_html = json.dumps(content.replace('\n', '<br>'))
                await page.evaluate(f"""
                    () => {{
                        const editors = document.querySelectorAll('[contenteditable="true"]');
                        if (editors.length > 0) {{
                            const editor = editors[0];
                            editor.innerHTML = {content_html};
                            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """)
                print("  正文填写完成")
            except Exception as e:
                print(f"  正文填写失败: {e}")

        await asyncio.sleep(1)

        # Step 5: 上传图片
        if images:
            print(f"\n上传 {len(images)} 张图片...")
            for i, img_path in enumerate(images):
                if not os.path.exists(img_path):
                    print(f"  图片不存在: {img_path}")
                    continue
                print(f"  上传第{i+1}张: {img_path}")
                try:
                    # 方式A: set_input_files
                    file_input = page.locator('input[type="file"]').first
                    count = await file_input.count()
                    if count > 0:
                        await file_input.set_input_files(img_path)
                        print(f"  上传成功")
                    else:
                        # 方式B: JS 触发文件选择
                        img_path_js = json.dumps(img_path)
                        await page.evaluate(f"""
                            () => {{
                                const input = document.createElement('input');
                                input.type = 'file';
                                input.accept = 'image/*';
                                input.style.display = 'none';
                                document.body.appendChild(input);
                                // 无法直接赋值文件，需用户交互
                            }}
                        """)
                        print(f"  需手动上传: {img_path}")
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"  上传失败: {e}")

        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/step3_before_publish.png")
        print("发布前截图: /tmp/step3_before_publish.png")

        # Step 6: 点击发布按钮
        print("\n查找发布按钮...")
        pub_clicked = False
        for pub_text in ["发布", "立即发布", "确认发布"]:
            try:
                count = await page.locator(f"text={pub_text}").count()
                if count > 0:
                    print(f"  找到'{pub_text}'，点击")
                    await page.locator(f"text={pub_text}").first.click()
                    pub_clicked = True
                    await asyncio.sleep(3)
                    break
            except:
                pass

        await page.screenshot(path="/tmp/step4_result.png")

        if pub_clicked:
            print("\n✅ 发布操作已执行，请查看截图确认")
        else:
            print("\n⚠️ 未找到发布按钮，请手动点击")

        print("\n浏览器保持打开，按 Ctrl+C 退出")
        await asyncio.Event().wait()


def main():
    parser = argparse.ArgumentParser(description="抖音图文发布脚本", prog="python3 douyin_publisher.py")
    parser.add_argument("--title", "-t", type=str, help="图文标题")
    parser.add_argument("--content", "-c", type=str, help="图文正文（支持\\n换行）")
    parser.add_argument("--images", "-i", type=str, help="图片路径，多个用逗号分隔")
    parser.add_argument("--cookie", type=str, help="抖音 Cookie（可选，默认从 config.json 读取）")
    parser.add_argument("--chrome-path", type=str,
                        default="/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
                        help="Chromium 路径")
    parser.add_argument("--user-data-dir", "-u", type=str,
                        default="/tmp/chrome-douyin-publish",
                        help="Chrome 用户数据目录")

    args = parser.parse_args()

    # 读取 Cookie
    if args.cookie:
        raw_cookie = args.cookie
    else:
        config_path = Path.home() / ".hermes/skills/douyin-auto-reply/config.json"
        try:
            with open(config_path) as f:
                raw_cookie = json.load(f).get("douyin_cookie", "")
        except:
            raw_cookie = ""

    cookies = parse_cookies(raw_cookie) if raw_cookie else []
    images = [p.strip() for p in args.images.split(",")] if args.images else []

    print("=" * 50)
    print("抖音图文发布脚本")
    print("=" * 50)
    print(f"标题: {args.title or '（无）'}")
    print(f"正文: {(args.content or '').replace(chr(10), ' | ')[:60]}...")
    print(f"图片: {images}")
    print(f"Cookie: {'已配置' if cookies else '未配置（需扫码登录）'}")
    print("=" * 50)

    asyncio.run(publish_image_text(
        cookies=cookies,
        title=args.title or "",
        content=(args.content or "").replace("\\n", "\n"),
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
    ))


if __name__ == "__main__":
    main()
