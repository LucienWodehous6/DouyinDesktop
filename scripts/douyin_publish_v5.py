#!/usr/bin/env python3
"""
抖音图文发布脚本 v5 - 等待发布表单渲染完成后再操作
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright


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

        page = browser.pages[-1] if browser.pages else await browser.new_page()

        print("打开创作者中心...")
        await page.goto("https://creator.douyin.com/", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # 检查登录
        html = await page.content()
        if "登录" in (await page.title()) or "扫码登录" in html[:2000]:
            print("未登录，请在浏览器中扫码登录...")
            await asyncio.Event().wait()
            return

        print(f"已登录: {page.url}")

        # 点击发布图文
        print("点击发布图文...")
        for txt in ["发布图文", "图文", "发布作品"]:
            try:
                cnt = await page.locator(f"text={txt}").count()
                if cnt > 0:
                    await page.locator(f"text={txt}").first.click()
                    print(f"  点击了 '{txt}'")
                    break
            except:
                pass

        # 等待发布页 URL 变化
        print("等待发布页跳转...")
        try:
            await page.wait_for_url("**/content/upload**", timeout=10000)
            print(f"  跳转到: {page.url}")
        except:
            print(f"  URL未跳转到上传页，当前: {page.url}")

        await asyncio.sleep(3)  # 等待 SPA 渲染

        # 等编辑器出现
        print("等待发布表单渲染...")
        try:
            await page.wait_for_selector(
                '[contenteditable="true"], [role="textbox"], input[type="file"]',
                timeout=15000
            )
            print("  编辑器已出现")
        except:
            print("  等待超时，继续尝试...")

        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/publish_v5_form.png")

        # 通过 JS 填入内容
        print("填入标题...")
        if title:
            escaped = title.replace("'", "\\'").replace("\n", "<br>")
            js = f"""
            () => {{
                const all = document.querySelectorAll('*');
                let titleEl = null;
                for (const el of all) {{
                    const r = el.getBoundingClientRect();
                    if (r.width > 50 && r.height >= 20 && r.height <= 80 &&
                        (el.contentEditable === 'true' ||
                         el.getAttribute('role') === 'textbox')) {{
                        const txt = (el.textContent || '').trim();
                        if (txt.length < 80) {{
                            titleEl = el;
                            break;
                        }}
                    }}
                }}
                if (titleEl) {{
                    titleEl.innerHTML = '{escaped}';
                    titleEl.dispatchEvent(new Event('input', {{bubbles: true}}));
                    titleEl.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'title_ok';
                }}
                return 'title_not_found';
            }}
            """
            result = await page.evaluate(js)
            print(f"  标题: {result}")

        print("填入正文...")
        if content:
            escaped = content.replace("'", "\\'").replace("\n", "<br>")
            js = f"""
            () => {{
                const all = document.querySelectorAll('*');
                let best = null, bestArea = 0;
                for (const el of all) {{
                    const r = el.getBoundingClientRect();
                    if (r.width > 200 && r.height > 150 &&
                        el.contentEditable === 'true') {{
                        const area = r.width * r.height;
                        if (area > bestArea) {{
                            best = el;
                            bestArea = area;
                        }}
                    }}
                }}
                if (best) {{
                    best.innerHTML = '{escaped}';
                    best.dispatchEvent(new Event('input', {{bubbles: true}}));
                    best.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'content_ok (area=' + bestArea + ')';
                }}
                return 'content_not_found';
            }}
            """
            result = await page.evaluate(js)
            print(f"  正文: {result}")

        # 上传图片
        if images:
            print(f"\n上传 {len(images)} 张图片...")
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    print(f"  [{i+1}] 不存在: {img}")
                    continue
                print(f"  [{i+1}] {os.path.basename(img)}")
                try:
                    file_inputs = page.locator('input[type="file"]')
                    cnt = await file_inputs.count()
                    if cnt > 0:
                        await file_inputs.first.set_input_files(img)
                        print(f"    成功")
                    else:
                        print(f"    未找到 file input")
                except Exception as e:
                    print(f"    失败: {e}")
                await asyncio.sleep(2)

        await asyncio.sleep(1)
        await page.screenshot(path="/tmp/publish_v5_before_publish.png")

        # 点发布
        print("\n点击发布...")
        for pub_txt in ["发布", "立即发布", "确认发布"]:
            try:
                cnt = await page.locator(f"text={pub_txt}").count()
                if cnt > 0:
                    await page.locator(f"text={pub_txt}").first.click()
                    print(f"  点击了 '{pub_txt}'")
                    await asyncio.sleep(3)
                    break
            except:
                pass

        await page.screenshot(path="/tmp/publish_v5_result.png")
        print("\n✅ 完成！请在浏览器中确认发布结果")
        print("浏览器保持打开...")
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音图文发布 v5")
    parser.add_argument("--title", "-t", type=str)
    parser.add_argument("--content", "-c", type=str)
    parser.add_argument("--images", "-i", type=str)
    parser.add_argument("--cookie", type=str)
    parser.add_argument("--chrome-path", type=str,
        default="/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
    parser.add_argument("--user-data-dir", "-u", type=str, default="/tmp/chrome-douyin-publish")

    args = parser.parse_args()

    # 读 Cookie
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
    print("抖音图文发布 v5")
    print("=" * 50)

    asyncio.run(publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    ))
