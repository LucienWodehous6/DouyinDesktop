#!/usr/bin/env python3
"""
抖音图文发布脚本 v8 - 等待 iframe 内部渲染完成后再注入内容
核心修复：iframe 内容是 React SPA，需显式等待特定元素出现
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright


def find_upload_frame(pages):
    patterns = ['lf-zt.douyin.com', 'uc-assets', 'x-storage-web']
    for page in pages:
        for frame in page.frames:
            if any(p in frame.url for p in patterns):
                return frame
    return None


async def wait_for_frame_ready(frame, timeout=20):
    """等待 iframe 内有可见元素"""
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout:
        try:
            count = await frame.locator('[contenteditable="true"], [role="textbox"]').count()
            if count > 0:
                return True
        except:
            pass
        await asyncio.sleep(1)
    return False


async def publish_douyin(title, content, images, chromium_path, user_data_dir, cookies):
    async with async_playwright() as p:
        print("启动浏览器...", file=sys.stderr)
        browser = await p.chromium.launch_persistent_context(
            executable_path=chromium_path,
            headless=False,
            user_data_dir=user_data_dir,
            args=["--disable-blink-features=AutomationControlled"],
        )

        if cookies:
            await browser.add_cookies(cookies)
            print(f"已注入 {len(cookies)} 个 Cookie", file=sys.stderr)

        page = browser.pages[-1]

        print("打开创作者中心...", file=sys.stderr)
        await page.goto("https://creator.douyin.com/", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        if "登录" in (await page.title()) or "扫码登录" in html[:2000]:
            print("未登录，请在浏览器中扫码登录...", file=sys.stderr)
            await asyncio.Event().wait()
            return

        print(f"已登录: {page.url}", file=sys.stderr)

        # 点击发布图文
        print("点击发布图文...", file=sys.stderr)
        for txt in ["发布图文", "图文", "发布作品"]:
            try:
                if await page.locator(f"text={txt}").count() > 0:
                    await page.locator(f"text={txt}").first.click()
                    print(f"  点击了 '{txt}'", file=sys.stderr)
                    break
            except:
                pass

        # 等待发布页跳转
        print("等待发布页跳转...", file=sys.stderr)
        try:
            await page.wait_for_url("**/content/upload**", timeout=10000)
        except:
            pass

        print("等待上传组件 iframe 加载（最多20秒）...", file=sys.stderr)
        upload_frame = None
        for _ in range(10):
            upload_frame = find_upload_frame(browser.pages)
            if upload_frame:
                print(f"  找到 iframe: {upload_frame.url[:60]}", file=sys.stderr)
                break
            await asyncio.sleep(1)

        if not upload_frame:
            print("未找到上传组件 iframe", file=sys.stderr)
            await asyncio.Event().wait()
            return

        # 等待 iframe 内部渲染（最多 20 秒）
        print("等待 iframe 内容渲染...", file=sys.stderr)
        frame_ready = await wait_for_frame_ready(upload_frame, timeout=20)
        if frame_ready:
            print("  iframe 内容已就绪", file=sys.stderr)
        else:
            print("  iframe 等待超时，继续尝试...", file=sys.stderr)

        await asyncio.sleep(2)

        # 再次 dump iframe 元素
        editors_info = await upload_frame.evaluate("""
        () => {
            const results = [];
            document.querySelectorAll('[contenteditable="true"], [role="textbox"], input, textarea').forEach((el, i) => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                    results.push({
                        index: i,
                        tag: el.tagName,
                        contenteditable: el.contentEditable,
                        role: el.getAttribute('role') || '',
                        placeholder: el.placeholder || el.getAttribute('placeholder') || '',
                        text: (el.textContent || '').trim().substring(0, 40),
                        w: Math.round(r.width),
                        h: Math.round(r.height)
                    });
                }
            });
            return JSON.stringify(results);
        }
        """)
        editors = json.loads(editors_info)
        print(f"  iframe 可编辑元素 ({len(editors)} 个):", file=sys.stderr)
        for e in editors:
            print(f"    [{e['index']}] {e['tag']} ph='{e['placeholder']}' "
                  f"ce={e['contenteditable']} {e['w']}x{e['h']} text='{e['text']}'", file=sys.stderr)

        # 填标题：聚焦并用 keyboard 输入
        if title:
            print("填入标题...", file=sys.stderr)
            filled = False

            # 策略1：点击 contenteditable 并用 keyboard.type
            for e in editors:
                if e['contenteditable'] == 'true' and e['h'] < 100:
                    try:
                        # 用 frame.locator 找到这个元素
                        js_focus = f"""
                        () => {{
                            const els = document.querySelectorAll('[contenteditable="true"]');
                            if (els[{e['index']}]) {{
                                els[{e['index']}].focus();
                                return 'focused';
                            }}
                            return 'not_found';
                        }}
                        """
                        res = await upload_frame.evaluate(js_focus)
                        if res == 'focused':
                            await upload_frame.keyboard.type(title, delay=15)
                            print(f"  标题输入成功 (ce编辑器 第{e['index']}个)", file=sys.stderr)
                            filled = True
                            break
                    except Exception as ex:
                        print(f"  失败: {ex}", file=sys.stderr)

            if not filled:
                # 策略2：用 execCommand
                try:
                    js = """
                    () => {
                        const el = document.querySelector('[contenteditable="true"]');
                        if (el) { el.innerHTML = ''; el.focus(); return 'ok'; }
                        return 'fail';
                    }
                    """
                    res = await upload_frame.evaluate(js)
                    if res == 'ok':
                        await upload_frame.keyboard.type(title, delay=15)
                        print(f"  标题输入成功 (execCommand策略)", file=sys.stderr)
                        filled = True
                except:
                    pass

            if not filled:
                print("  标题输入失败，请在浏览器中手动填写", file=sys.stderr)

        # 填正文
        if content:
            print("填入正文...", file=sys.stderr)
            filled = False

            for e in editors:
                if e['contenteditable'] == 'true' and e['w'] > 200 and e['h'] > 100:
                    try:
                        js_focus = f"""
                        () => {{
                            const els = document.querySelectorAll('[contenteditable="true"]');
                            if (els[{e['index']}]) {{
                                els[{e['index']}].innerHTML = '';
                                els[{e['index']}].focus();
                                return 'focused';
                            }}
                            return 'not_found';
                        }}
                        """
                        res = await upload_frame.evaluate(js_focus)
                        if res == 'focused':
                            await upload_frame.keyboard.type(content, delay=5)
                            print(f"  正文输入成功 (ce编辑器 第{e['index']}个)", file=sys.stderr)
                            filled = True
                            break
                    except Exception as ex:
                        print(f"  失败: {ex}", file=sys.stderr)

            if not filled:
                print("  正文输入失败，请在浏览器中手动填写", file=sys.stderr)

        await asyncio.sleep(1)

        # 上传图片
        if images:
            print(f"上传 {len(images)} 张图片...", file=sys.stderr)
            file_inputs = page.locator('input[type="file"]')
            cnt = await file_inputs.count()
            print(f"  主页面找到 {cnt} 个 file input", file=sys.stderr)

            for i, img in enumerate(images):
                if not os.path.exists(img):
                    print(f"  [{i+1}] 不存在: {img}", file=sys.stderr)
                    continue
                print(f"  [{i+1}] {os.path.basename(img)}", file=sys.stderr)
                try:
                    # 每次上传前重新获取 file input
                    fi = page.locator('input[type="file"]').first
                    await fi.set_input_files(img)
                    print(f"    成功", file=sys.stderr)
                except Exception as e:
                    print(f"    失败: {e}", file=sys.stderr)
                await asyncio.sleep(3)

        await asyncio.sleep(1)

        # 点发布
        print("点击发布按钮...", file=sys.stderr)
        for pub_txt in ["发布", "立即发布", "确认发布"]:
            try:
                cnt = await page.locator(f"text={pub_txt}").count()
                if cnt > 0:
                    await page.locator(f"text={pub_txt}").first.click()
                    print(f"  点击了 '{pub_txt}'", file=sys.stderr)
                    await asyncio.sleep(3)
                    break
            except:
                pass

        await page.screenshot(path="/tmp/publish_v8_result.png")
        print("✅ 完成！请在浏览器中确认发布结果", file=sys.stderr)
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="抖音图文发布脚本 v8",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--title", "-t", type=str, help="图文标题")
    parser.add_argument("--content", "-c", type=str, help="图文正文")
    parser.add_argument("--images", "-i", type=str, help="图片路径，逗号分隔")
    parser.add_argument("--cookie", type=str)
    parser.add_argument("--chrome-path", type=str,
        default="/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
    parser.add_argument("--user-data-dir", "-u", type=str, default="/tmp/chrome-douyin-publish")

    args = parser.parse_args()

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

    asyncio.run(publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    ))
