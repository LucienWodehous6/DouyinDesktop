#!/usr/bin/env python3
"""
抖音图文发布脚本 v2 - 纯文本定位，不依赖 class
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright


async def js_click_by_text(page, text):
    """通过 JS 查找并点击包含指定文本的元素"""
    js = f"""
    () => {{
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            if (el.children.length === 0) {{
                const t = (el.textContent || '').trim();
                if (t.includes('{text}') && el.clientWidth > 0 && el.clientHeight > 0) {{
                    el.click();
                    return 'clicked';
                }}
            }}
        }}
        return 'not_found';
    }}
    """
    return await page.evaluate(js)


async def fill_by_placeholder(page, placeholder_keyword, value):
    """通过 placeholder 关键词填写输入框"""
    escaped_value = value.replace("'", "\\'").replace("\n", "<br>")
    js = f"""
    () => {{
        const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        for (const el of inputs) {{
            const ph = el.getAttribute('placeholder') || '';
            const label = el.getAttribute('aria-label') || '';
            const tag = el.tagName.toLowerCase();
            if (ph.includes('{placeholder_keyword}') || label.includes('{placeholder_keyword}')) {{
                if (tag === 'input' || tag === 'textarea') {{
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(el, '{escaped_value}');
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'filled';
                }} else {{
                    el.innerHTML = '{escaped_value}';
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    return 'filled';
                }}
            }}
        }}
        return 'not_found';
    }}
    """
    return await page.evaluate(js)


async def publish_douyin(title, content, images, chromium_path, user_data_dir, cookies):
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
        await page.screenshot(path="/tmp/publish_v2_1.png")

        html = await page.content()
        if "登录" in (await page.title()) or "登录" in html[:500]:
            print("未登录，请在浏览器中扫码登录...")
            await asyncio.Event().wait()
            return

        print("已登录，开始发布...")

        # Step 2: 点击发布图文
        print("查找发布图文入口...")
        clicked = False

        # 方法A: locator text
        for txt in ["发布图文", "图文", "发布作品"]:
            try:
                cnt = await page.locator(f"text={txt}").count()
                if cnt > 0:
                    print(f"  locator 找到 '{txt}' ({cnt}个)")
                    await page.locator(f"text={txt}").first.click()
                    clicked = True
                    await asyncio.sleep(4)
                    break
            except:
                pass

        # 方法B: JS 点击
        if not clicked:
            result = await js_click_by_text(page, "发布图文")
            print(f"  JS 点击发布图文: {result}")
            if result == "clicked":
                clicked = True
                await asyncio.sleep(4)

        if not clicked:
            result = await js_click_by_text(page, "图文")
            print(f"  JS 点击图文: {result}")
            if result == "clicked":
                clicked = True
                await asyncio.sleep(4)

        if not clicked:
            print("无法找到发布入口，请在页面上手动点击'发布图文'按钮")
            await asyncio.Event().wait()
            return

        await page.screenshot(path="/tmp/publish_v2_2.png")
        print("发布页已打开")

        # Step 3: 上传图片（必须先上传，编辑框才会出现！）
        if images:
            print(f"上传 {len(images)} 张图片...")
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    print(f"  图片不存在: {img}")
                    continue
                print(f"  上传第{i+1}张: {img}")
                try:
                    file_inputs = page.locator('input[type="file"]')
                    cnt = await file_inputs.count()
                    if cnt > 0:
                        await file_inputs.first.set_input_files(img)
                        print(f"  上传成功")
                    else:
                        result = await page.evaluate(f"""
                        () => {{
                            const inputs = document.querySelectorAll('input[type="file"]');
                            if (inputs.length > 0) {{
                                inputs[0].click();
                                return 'triggered';
                            }}
                            return 'not_found';
                        }}
                        """)
                        print(f"  文件上传触发: {result}（需用户手动选择文件）")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"  上传失败: {e}")

        # 等待编辑框出现（上传图片后才有标题/正文输入框）
        print("等待编辑框出现...")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/publish_v2_after_upload.png")

        # Step 4: 填写标题（上传图片后才能填写）
        if title:
            print(f"填写标题: {title[:30]}...")
            result = await fill_by_placeholder(page, "标题", title)
            print(f"  标题填写: {result}")
            await asyncio.sleep(1)

        # Step 5: 填写正文（正文在 iframe 内，尝试通过 iframe 操作）
        if content:
            print(f"填写正文...")
            # 尝试在主页面查找
            result = await fill_by_placeholder(page, "描述", content)
            if result == "not_found":
                result = await fill_by_placeholder(page, "作品描述", content)
            if result == "not_found":
                # 尝试 contenteditable 主页面
                escaped_content = content.replace("'", "\\'").replace("\n", "<br>")
                js = f"""
                () => {{
                    const editors = document.querySelectorAll('[contenteditable="true"]');
                    for (const e of editors) {{
                        if (e.clientWidth > 100 && e.clientHeight > 50) {{
                            e.innerHTML = '{escaped_content}';
                            e.dispatchEvent(new Event('input', {{bubbles: true}}));
                            return 'filled';
                        }}
                    }}
                    return 'not_found';
                }}
                """
                result = await page.evaluate(js)
            print(f"  正文填写: {result}")
            await asyncio.sleep(1)

        # Step 6: 点击发布按钮
        print("查找发布按钮...")
        pub_clicked = False
        for pub_txt in ["发布", "立即发布", "确认发布"]:
            try:
                cnt = await page.locator(f"text={pub_txt}").count()
                if cnt > 0:
                    print(f"  找到'{pub_txt}'，点击")
                    await page.locator(f"text={pub_txt}").first.click()
                    pub_clicked = True
                    await asyncio.sleep(3)
                    break
            except:
                pass

        if not pub_clicked:
            # JS 方式
            for pub_txt in ["发布", "立即发布"]:
                result = await js_click_by_text(page, pub_txt)
                if result == "clicked":
                    print(f"  JS 点击'{pub_txt}'成功")
                    pub_clicked = True
                    await asyncio.sleep(3)
                    break

        await page.screenshot(path="/tmp/publish_v2_result.png")

        if pub_clicked:
            print("\n✅ 发布操作已执行！请查看截图确认结果")
        else:
            print("\n⚠️ 未找到发布按钮，请在页面上手动点击")

        print("\n浏览器保持打开，按 Ctrl+C 退出")
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音图文发布脚本 v2")
    parser.add_argument("--title", "-t", type=str)
    parser.add_argument("--content", "-c", type=str)
    parser.add_argument("--images", "-i", type=str)
    parser.add_argument("--cookie", type=str)
    parser.add_argument("--chrome-path", type=str,
                        default="/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
    parser.add_argument("--user-data-dir", "-u", type=str, default="/tmp/chrome-douyin-publish")

    args = parser.parse_args()

    # 读取 Cookie
    if args.cookie:
        raw = args.cookie
    else:
        try:
            cfg = Path.home() / ".hermes/skills/douyin-auto-reply/config.json"
            with open(cfg) as f:
                raw = json.load(f).get("douyin_cookie", "")
        except:
            raw = ""

    cookies = []
    if raw:
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                n, _, v = part.partition("=")
                cookies.append({"name": n.strip(), "value": v.strip(), "domain": ".douyin.com", "path": "/"})

    images = [p.strip() for p in args.images.split(",")] if args.images else []
    content = (args.content or "").replace("\\n", "\n")

    print("=" * 50)
    print("抖音图文发布")
    print("=" * 50)
    print(f"标题: {args.title or ''}")
    print(f"图片: {images}")
    print("=" * 50)

    asyncio.run(publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    ))
