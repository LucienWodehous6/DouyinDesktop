#!/usr/bin/env python3
"""
抖音图文发布脚本 v6 - 先点击编辑器激活，再用 keyboard.type 输入
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright


async def wait_and_click_editable(page, timeout=15000):
    """等待并点击页面上的可编辑区域"""
    selectors = [
        '[contenteditable="true"]',
        '[role="textbox"]',
        '[role="presentation"]',
        '.edit-area',
        '.editor',
        '[class*="editor"]',
    ]
    for sel in selectors:
        try:
            els = page.locator(sel)
            cnt = await els.count()
            for i in range(cnt):
                el = els.nth(i)
                visible = await el.is_visible()
                if visible:
                    await el.click()
                    await asyncio.sleep(0.5)
                    return True
        except:
            pass
    return False


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

        page = browser.pages[-1]

        print("打开创作者中心...")
        await page.goto("https://creator.douyin.com/", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

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
                if await page.locator(f"text={txt}").count() > 0:
                    await page.locator(f"text={txt}").first.click()
                    print(f"  点击了 '{txt}'")
                    break
            except:
                pass

        # 等待跳转
        print("等待发布页跳转...")
        try:
            await page.wait_for_url("**/content/upload**", timeout=10000)
            print(f"  跳转成功: {page.url}")
        except:
            print(f"  未跳转: {page.url}")

        # 等待编辑器渲染
        print("等待发布表单渲染...")
        try:
            await page.wait_for_selector('[contenteditable="true"]', timeout=15000)
            print("  编辑器已加载")
        except:
            print("  等待编辑器超时")

        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/publish_v6_form.png")

        # 填标题：点击第一个 contenteditable
        print("填写标题...")
        title_filled = False
        try:
            editors = page.locator('[contenteditable="true"]')
            cnt = await editors.count()
            print(f"  找到 {cnt} 个 contenteditable")
            for i in range(cnt):
                el = editors.nth(i)
                try:
                    visible = await el.is_visible()
                    box = await el.bounding_box()
                    if visible and box and box['width'] > 50 and box['height'] > 0:
                        await el.click()
                        await asyncio.sleep(0.3)
                        # 清空并输入
                        await page.keyboard.press('Control+a')
                        await asyncio.sleep(0.2)
                        await page.keyboard.type(title, delay=20)
                        title_filled = True
                        print(f"  标题输入成功 (第{i+1}个编辑器)")
                        break
                except Exception as e:
                    print(f"  第{i+1}个失败: {e}")
        except Exception as e:
            print(f"  查找编辑器失败: {e}")

        # 填正文
        print("填写正文...")
        content_filled = False
        try:
            editors = page.locator('[contenteditable="true"]')
            cnt = await editors.count()
            for i in range(1, cnt):  # 跳过标题
                el = editors.nth(i)
                try:
                    visible = await el.is_visible()
                    box = await el.bounding_box()
                    if visible and box and box['width'] > 200 and box['height'] > 100:
                        await el.click()
                        await asyncio.sleep(0.3)
                        await page.keyboard.press('Control+a')
                        await asyncio.sleep(0.2)
                        await page.keyboard.type(content, delay=10)
                        content_filled = True
                        print(f"  正文输入成功 (第{i+1}个编辑器)")
                        break
                except Exception as e:
                    print(f"  第{i+1}个正文编辑器失败: {e}")
        except Exception as e:
            print(f"  查找正文编辑器失败: {e}")

        if not title_filled and not content_filled:
            print("  ⚠️ 自动填写失败，请在浏览器中手动填写")

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
        await page.screenshot(path="/tmp/publish_v6_before_pub.png")

        # 点发布
        print("\n点击发布按钮...")
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

        await page.screenshot(path="/tmp/publish_v6_result.png")
        print("\n✅ 完成！请在浏览器确认发布结果")
        print("浏览器保持打开...")
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音图文发布 v6")
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
    print("抖音图文发布 v6")
    print("=" * 50)

    asyncio.run(publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    ))
