#!/usr/bin/env python3
"""
抖音图文发布脚本 final - 同步 Playwright API，不超时
用法:
    python3 douyin_publish_final.py -t "标题" -c "正文" -i "图1.jpg,图2.png"
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def publish_douyin(title, content, images, chromium_path, user_data_dir, cookies):
    with sync_playwright() as p:
        print("启动浏览器...", file=sys.stderr)
        browser = p.chromium.launch_persistent_context(
            executable_path=chromium_path,
            headless=False,
            user_data_dir=user_data_dir,
            args=["--disable-blink-features=AutomationControlled"],
        )

        if cookies:
            browser.add_cookies(cookies)
            print(f"已注入 {len(cookies)} 个 Cookie", file=sys.stderr)

        page = browser.pages[-1] if browser.pages else browser.new_page()

        print("打开创作者中心...", file=sys.stderr)
        page.goto("https://creator.douyin.com/", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        html = page.content()
        if "登录" in page.title() or "扫码登录" in html[:2000]:
            print("未登录，请在浏览器中扫码登录...", file=sys.stderr)
            page.wait_for_event("close")

        print(f"已登录: {page.url}", file=sys.stderr)

        # 点击发布图文
        print("点击发布图文...", file=sys.stderr)
        for txt in ["发布图文", "图文", "发布作品"]:
            try:
                if page.locator(f"text={txt}").count() > 0:
                    page.locator(f"text={txt}").first.click()
                    print(f"  点击了 '{txt}'", file=sys.stderr)
                    break
            except:
                pass

        # 等待发布页
        print("等待发布页跳转...", file=sys.stderr)
        try:
            page.wait_for_url("**/content/upload**", timeout=10000)
        except:
            pass
        print(f"  URL: {page.url}", file=sys.stderr)

        # 等待编辑器加载
        time.sleep(5)

        # 查找 textbox (编辑器)
        textbox = page.get_by_role("textbox")
        try:
            cnt = textbox.count()
            print(f"  找到 textbox {cnt} 个", file=sys.stderr)
        except:
            cnt = 0
            print(f"  textbox count 失败", file=sys.stderr)

        # 填标题
        if title and cnt > 0:
            print("填入标题...", file=sys.stderr)
            try:
                textbox.first.fill(title)
                print("  标题填写成功", file=sys.stderr)
            except Exception as e:
                print(f"  标题填写失败: {e}", file=sys.stderr)
                # 备选：点击并键盘输入
                try:
                    textbox.first.click(timeout=5000)
                    time.sleep(0.3)
                    page.keyboard.press("Control+a")
                    time.sleep(0.1)
                    page.keyboard.type(title, delay=20)
                    print("  标题键盘输入成功", file=sys.stderr)
                except Exception as e2:
                    print(f"  键盘输入也失败: {e2}", file=sys.stderr)

        # 填正文（找第二个或更大的 textbox）
        if content:
            print("填入正文...", file=sys.stderr)
            try:
                # 通常正文编辑器更大，找第二个 textbox
                all_tb = page.get_by_role("textbox")
                tb_cnt = all_tb.count()
                if tb_cnt >= 2:
                    all_tb.nth(1).fill(content)
                    print("  正文填写成功", file=sys.stderr)
                elif tb_cnt == 1:
                    # 只有一个，可能标题和正文是同一个（先标题再正文）
                    # 尝试 Tab 然后输入正文
                    textbox.first.click(timeout=5000)
                    time.sleep(0.3)
                    page.keyboard.press("Tab")
                    time.sleep(0.2)
                    page.keyboard.type(content, delay=10)
                    print("  正文键盘输入成功", file=sys.stderr)
            except Exception as e:
                print(f"  正文填写失败: {e}", file=sys.stderr)

        # 上传图片
        if images:
            print(f"上传 {len(images)} 张图片...", file=sys.stderr)
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    print(f"  [{i+1}] 不存在: {img}", file=sys.stderr)
                    continue
                print(f"  [{i+1}] {os.path.basename(img)}", file=sys.stderr)
                try:
                    fi = page.locator('input[type="file"]').first
                    fi.set_input_files(img)
                    print(f"    成功", file=sys.stderr)
                except Exception as e:
                    print(f"    失败: {e}", file=sys.stderr)
                time.sleep(2)

        time.sleep(1)
        page.screenshot(path="/tmp/publish_final_result.png")

        # 点发布
        print("点击发布按钮...", file=sys.stderr)
        for pub_txt in ["发布", "立即发布", "确认发布"]:
            try:
                if page.locator(f"text={pub_txt}").count() > 0:
                    page.locator(f"text={pub_txt}").first.click()
                    print(f"  点击了 '{pub_txt}'", file=sys.stderr)
                    time.sleep(3)
                    break
            except:
                pass

        page.screenshot(path="/tmp/publish_final_final.png")
        print("✅ 完成！请在浏览器中确认发布结果", file=sys.stderr)
        print("浏览器保持打开...", file=sys.stderr)
        page.wait_for_event("close")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音图文发布脚本 (同步版)")
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

    print("=" * 50, file=sys.stderr)
    print("抖音图文发布", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    publish_douyin(
        title=args.title or "",
        content=content,
        images=images,
        chromium_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        cookies=cookies,
    )
