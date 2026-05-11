#!/usr/bin/env python3
"""用项目内置 Playwright + chromium 在本地弹出 Chrome 窗口"""

import sys
import os
import json
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
browsers_path = os.path.join(project_root, "playwright_browsers")
sys.path.insert(0, browsers_path)

from playwright.sync_api import sync_playwright

# Cookie 配置
cookie_file = os.path.expanduser("~/.hermes/skills/douyin-auto-reply/config.json")
with open(cookie_file) as f:
    config = json.load(f)

raw_cookies = config.get("douyin_cookie", "")

cookie_list = []
for part in raw_cookies.split(";"):
    part = part.strip()
    if "=" in part:
        name, _, value = part.partition("=")
        cookie_list.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": ".douyin.com",
            "path": "/"
        })

print(f"Loaded {len(cookie_list)} cookies")
print("Launching browser (should appear on your screen now)...")

chromium_path = os.path.join(
    browsers_path,
    "chromium-1208",
    "chrome-mac-arm64",
    "Google Chrome for Testing.app",
    "Contents",
    "MacOS",
    "Google Chrome for Testing"
)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            executable_path=chromium_path,
            headless=False,
            user_data_dir="/tmp/chrome-hermes-test",
            args=["--disable-blink-features=AutomationControlled"],
        )

        browser.add_cookies(cookie_list)
        print("Cookies injected")

        page = browser.pages[0] if browser.pages else browser.new_page()

        video_url = "https://www.douyin.com/video/7619703556590292395"
        print(f"Opening {video_url}...")
        page.goto(video_url, timeout=30000)
        print("Waiting for page to settle...")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        time.sleep(5)  # 给足时间让 JS 加载完

        print(f"Page title: {page.title()}")

        screenshot_path = "/tmp/douyin-local-browser.png"
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot: {screenshot_path}")

        print("\n=== Browser is open on your screen ===")
        print("Press ENTER here to close the browser...")
        input()

        browser.close()
        print("Done.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    print("\nIf browser is open, just close it manually.")
    sys.exit(1)
