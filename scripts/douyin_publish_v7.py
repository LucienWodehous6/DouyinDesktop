#!/usr/bin/env python3
"""
抖音图文发布脚本 v7 - 处理跨域 iframe 内编辑器的内容注入
核心：切换到 lf-zt.douyin.com 上传组件 frame，用 execCommand('insertText') 注入内容
用法:
    python3 douyin_publish_v7.py -t "标题" -c "正文" -i "图1.jpg,图2.png"
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright


def find_upload_frame(pages):
    """根据 URL 特征找到上传组件的 frame"""
    patterns = ['lf-zt.douyin.com', 'uc-assets', 'x-storage-web']
    for page in pages:
        for frame in page.frames:
            url = frame.url
            if any(p in url for p in patterns):
                return frame
    return None


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

        # 等 iframe 完全加载
        print("等待上传组件 iframe 加载...", file=sys.stderr)
        await asyncio.sleep(3)

        upload_frame = find_upload_frame(browser.pages)
        if not upload_frame:
            print("未找到上传组件 iframe，请检查页面是否正常加载", file=sys.stderr)
            await asyncio.Event().wait()
            return

        print(f"找到上传组件 frame: {upload_frame.url[:80]}", file=sys.stderr)

        # 等 iframe 内部渲染
        try:
            await upload_frame.wait_for_load_state('domcontentloaded', timeout=10000)
        except:
            pass
        await asyncio.sleep(3)

        # 在 iframe 内查找编辑器
        print("在 iframe 内查找编辑器...", file=sys.stderr)

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
                        ariaLabel: el.getAttribute('aria-label') || '',
                        text: (el.textContent || '').trim().substring(0, 30),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                        id: el.id || '',
                        className: el.className.substring(0, 60)
                    });
                }
            });
            return JSON.stringify(results);
        }
        """)

        editors = json.loads(editors_info)
        print(f"  iframe 内找到 {len(editors)} 个可编辑元素:", file=sys.stderr)
        for e in editors:
            print(f"    [{e['index']}] {e['tag']} ph='{e['placeholder']}' "
                  f"ce={e['contenteditable']} {e['w']}x{e['h']} text='{e['text']}'", file=sys.stderr)

        # 填入标题：用 execCommand insertText
        if title:
            print("填入标题...", file=sys.stderr)
            # 先找到可能是标题的最小 contenteditable
            js_title = """
            () => {
                let titleEl = null;
                const cands = [];
                document.querySelectorAll('[contenteditable="true"], [role="textbox"]').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width > 50 && r.height > 0 && r.height < 200) {
                        cands.push({el, area: r.width * r.height});
                    }
                });
                // 找最小的（最可能是标题）
                cands.sort((a, b) => a.area - b.area);
                if (cands.length > 0) {
                    titleEl = cands[0].el;
                    titleEl.innerHTML = '';
                    titleEl.focus();
                    return 'title_el_found';
                }
                // 备选：用 input
                const inputs = document.querySelectorAll('input[placeholder*="标题"], input[placeholder*="title"]');
                if (inputs.length > 0) {
                    inputs[0].focus();
                    return 'input_found';
                }
                return 'title_not_found';
            }
            """
            result = await upload_frame.evaluate(js_title)
            print(f"  标题元素: {result}", file=sys.stderr)

            if result == 'title_el_found':
                # 用 execCommand 插入文本
                escaped = title.replace("'", "\\'")
                ins = await upload_frame.evaluate(f"""
                () => {{
                    document.execCommand('insertText', false, '{escaped}');
                    return 'done';
                }}
                """)
                print(f"  标题注入: {ins}", file=sys.stderr)
            elif result == 'input_found':
                # input 用 fill
                escaped = title.replace("'", "\\'")
                await upload_frame.fill(f'input[placeholder*="标题"]', title)
                print(f"  标题填充: done", file=sys.stderr)

        # 填入正文
        if content:
            print("填入正文...", file=sys.stderr)
            js_content = """
            () => {
                let bestEl = null, bestArea = 0;
                document.querySelectorAll('[contenteditable="true"]').forEach(el => {
                    const r = el.getBoundingClientRect();
                    const area = r.width * r.height;
                    if (r.width > 200 && r.height > 100 && area > bestArea) {
                        bestEl = el;
                        bestArea = area;
                    }
                });
                if (bestEl) {
                    bestEl.innerHTML = '';
                    bestEl.focus();
                    return 'content_el_found';
                }
                return 'content_not_found';
            }
            """
            result = await upload_frame.evaluate(js_content)
            print(f"  正文元素: {result}", file=sys.stderr)

            if result == 'content_el_found':
                escaped = content.replace("'", "\\'")
                ins = await upload_frame.evaluate(f"""
                () => {{
                    document.execCommand('insertText', false, `{escaped}`);
                    return 'done';
                }}
                """)
                print(f"  正文注入: {ins}", file=sys.stderr)

        await asyncio.sleep(1)

        # 上传图片（在主页面操作，因为 file input 不在 iframe 内）
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
                    await file_inputs.first.set_input_files(img)
                    print(f"    上传成功", file=sys.stderr)
                except Exception as e:
                    print(f"    失败: {e}", file=sys.stderr)
                await asyncio.sleep(2)

        await asyncio.sleep(1)

        # 点发布按钮（在主页面找）
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

        await page.screenshot(path="/tmp/publish_v7_result.png")
        print("✅ 发布操作已完成！请在浏览器中确认", file=sys.stderr)
        print("浏览器保持打开...", file=sys.stderr)
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="抖音图文发布脚本 v7（支持跨域 iframe 编辑器）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 douyin_publish_v7.py \\
    -t "🔴 建筑消防必看！" \\
    -c "正文内容换行可用\\\\n" \\
    -i "/path/img1.jpg,/path/img2.png"
        """
    )
    parser.add_argument("--title", "-t", type=str, help="图文标题")
    parser.add_argument("--content", "-c", type=str, help="图文正文（支持换行）")
    parser.add_argument("--images", "-i", type=str,
        help="图片路径，多个用逗号分隔")
    parser.add_argument("--cookie", type=str, help="Cookie 字符串（可选，默认从 config.json 读取）")
    parser.add_argument("--chrome-path", type=str,
        default="/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
    parser.add_argument("--user-data-dir", "-u", type=str,
        default="/tmp/chrome-douyin-publish")

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
                cookies.append({
                    "name": n.strip(), "value": v.strip(),
                    "domain": ".douyin.com", "path": "/"
                })

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
