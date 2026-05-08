"""
Cookie 管理 — 加载、注入、刷新 Cookie
"""

import os
import json


def _refresh_cookies(context, cookie_file):
    """提取当前浏览器 Cookie 并保存到文件，保持登录态最新"""
    if not cookie_file:
        return
    try:
        cookies = context.cookies()
        douyin_cookies = [c for c in cookies if "douyin.com" in c.get("domain", "")]
        if douyin_cookies:
            data = {"cookies": douyin_cookies, "origins": ["https://www.douyin.com"]}
            os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[✓] Cookie 已更新 ({len(douyin_cookies)} 条)")
    except Exception as e:
        print(f"[!] Cookie 刷新失败: {e}")


def load_cookies_from_file(cookie_file):
    """从 JSON 文件加载 Cookie（兼容两种格式）"""
    path = os.path.join(os.path.dirname(__file__), cookie_file)
    if not os.path.exists(path):
        print(f"[!] Cookie 文件不存在: {path}")
        return None
    with open(path, "r") as f:
        data = json.load(f)
    # 兼容 Playwright 导出格式 {"cookies": [...], "origins": [...]}
    if isinstance(data, dict) and "cookies" in data:
        cookies = data["cookies"]
    else:
        cookies = data
    print(f"[✓] 从 {cookie_file} 加载了 {len(cookies)} 个 Cookie")
    return cookies


def inject_cookies(context, cookies):
    """通过 CDP 注入 Cookie 到浏览器上下文"""
    if not cookies:
        return
    context.add_cookies(cookies)
    print("[✓] Cookie 已注入")