"""
浏览器定位策略 — 搜索框定位等
"""

# 搜索框选择器（按优先级尝试，抖音经常改版）
SEARCH_SELECTORS = [
    'input[data-e2e="searchbar-input"]',           # 旧版
    'input[placeholder*="搜索"]',                    # 按 placeholder 匹配
    '#searchbar-input',                             # ID 方式
    '.search-input-container input',                # 容器定位
    'input[class*="search"]',                       # 模糊匹配
]


def find_search_input(page, timeout=10000):
    """尝试多个选择器定位搜索框"""
    for selector in SEARCH_SELECTORS:
        try:
            el = page.wait_for_selector(selector, timeout=timeout)
            if el and el.is_visible():
                print(f"[✓] 搜索框定位成功，使用选择器: {selector}")
                return el
        except Exception:
            continue
    raise Exception("未能定位到搜索框，所有选择器均失败")