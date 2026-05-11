#!/usr/bin/env python3
"""
抖音图文发布脚本 v4 - 处理发布页跳转
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright


async def dump_editors(page):
    """列出所有可见的可编辑元素"""
    js = """
    () => {
        const results = [];
        const els = document.querySelectorAll('[contenteditable="true"], [role="textbox"], input, textarea');
        for (const el of els) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 10 && rect.height > 10) {
                results.push({
                    tag: el.tagName,
                    role: el.getAttribute('role'),
                    placeholder: (el.getAttribute('placeholder') || el.getAttribute('aria-label') || '').substring(0, 80),
                    text: (el.textContent || '').substring(0, 50),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    id: el.id || '',
                    class: el.className.substring(0, 80)
                });
            }
        }
        return JSON.stringify(results);
    }
    """
    return await page.evaluate(js)


async def fill_by_js(page, title, content):
    """通过 JS 填入标题和正文"""
    results = {}

    if title:
        escaped = title.replace("'", "\\'").replace("\n", "<br>")
        js = f"""
        () => {{
            const all = document.querySelectorAll('*');
            for (const el of all) {{
                const r = el.getBoundingClientRect();
                if (r.width > 100 && r.height >= 20 && r.height <= 80 &&
                    (el.getAttribute('contenteditable') === 'true' ||
                     el.getAttribute('role') === 'textbox' ||
                     el.getAttribute('role') === 'presentation')) {{
                    const txt = (el.textContent || '').trim();
                    if (txt.length < 100) {{
                        el.innerHTML = '{escaped}';
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'title_ok';
                    }}
                }}
            }}
            // 尝试找 input/textarea
            const inputs = document.querySelectorAll('input, textarea');
            for (const inp of inputs) {{
                const ph = (inp.getAttribute('placeholder') || '').toLowerCase();
                if (ph.includes('标题') || ph.includes('title')) {{
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(inp, '{escaped}');
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'title_input_ok';
                }}
            }}
            return 'title_not_found';
        }}
        """
        results['title'] = await page.evaluate(js)
        print(f"  标题: {results['title']}")

    if content:
        escaped = content.replace("'", "\\'").replace("\n", "<br>")
        js = f"""
        () => {{
            const all = document.querySelectorAll('*');
            let best = null, bestArea = 0;
            for (const el of all) {{
                const r = el.getBoundingClientRect();
                if (r.width > 200 && r.height > 100 && r.width * r.height > bestArea &&
                    (el.getAttribute('contenteditable') === 'true')) {{
                    best = el;
                    bestArea = r.width * r.height;
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
        results['content'] = await page.evaluate(js)
        print(f"  正文: {results['content']}")

    return results


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

        # 使用最后一个活跃的页面
        if browser.pages:
            page = browser.pages[-1]
        else:
            page = await browser.new_page()

        print("打开创作者中心...")
        await page.goto("https://creator.douyin.com/", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # 检查登录
        url = page.url
        html = await page.content()
        if "登录" in (await page.title()) or "扫码登录" in html[:2000]:
            print("未登录，请在浏览器中扫码登录...")
            await asyncio.Event().wait()
            return

        print(f"已登录，当前URL: {page.url}")

        # 点击发布图文
        print("查找并点击发布图文...")
        clicked = False
        for txt in ["发布图文", "图文", "发布作品"]:
            try:
                cnt = await page.locator(f"text={txt}").count()
                if cnt > 0:
                    print(f"  找到'{txt}'，点击")
                    await page.locator(f"text={txt}").first.click()
                    clicked = True
                    break
            except:
                pass

        if not clicked:
            print("未找到发布入口，请手动点击")
            await asyncio.Event().wait()
            return

        # 等待新页面加载完成
        print("等待发布页加载...")
        await asyncio.sleep(2)

        # 如果 URL 没变，尝试等网络空闲
        if page.url == url:
            print("  URL未变，等待网络空闲...")
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except:
                pass
            await asyncio.sleep(2)

        # 如果还是同一个页面，尝试切换到新页面
        if len(browser.pages) > 1:
            print(f"  检测到 {len(browser.pages)} 个页面，切换到最后一个")
            page = browser.pages[-1]

        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/publish_v4_page.png")

        print(f"当前页面: {page.url}")

        # 列出所有可编辑元素
        editors = await dump_editors(page)
        editors_list = json.loads(editors)
        print(f"\n页面可编辑元素 ({len(editors_list)} 个):")
        for e in editors_list:
            print(f"  [{e['tag']}] role={e['role']} ph='{e['placeholder']}' "
                  f"size={e['w']}x{e['h']} text='{e['text']}' id={e['id']}")

        # 填入标题和正文
        print("\n填入内容...")
        await fill_by_js(page, title, content)

        # 上传图片
        if images:
            print(f"\n上传 {len(images)} 张图片...")
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    print(f"  图片不存在: {img}")
                    continue
                print(f"  第{i+1}张: {os.path.basename(img)}")
                try:
                    file_inputs = page.locator('input[type="file"]')
                    cnt = await file_inputs.count()
                    if cnt > 0:
                        await file_inputs.first.set_input_files(img)
                        print(f"  上传成功")
                    else:
                        print(f"  未找到 file input")
                except Exception as e:
                    print(f"  上传失败: {e}")
                await asyncio.sleep(2)

        await asyncio.sleep(1)
        await page.screenshot(path="/tmp/publish_v4_result.png")

        # 点发布
        print("\n点击发布按钮...")
        for pub_txt in ["发布", "立即发布", "确认发布"]:
            try:
                cnt = await page.locator(f"text={pub_txt}").count()
                if cnt > 0:
                    print(f"  找到'{pub_txt}'，点击")
                    await page.locator(f"text={pub_txt}").first.click()
                    await asyncio.sleep(3)
                    break
            except:
                pass

        await page.screenshot(path="/tmp/publish_v4_final.png")
        print("\n✅ 完成！请在浏览器确认发布结果")
        print("浏览器保持打开，按 Ctrl+C 退出")
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音图文发布脚本 v4")
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
    print("抖音图文发布 v4")
    print("=" * 50)

    asyncio.run(publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    ))
