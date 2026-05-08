"""小红书搜索操作相关函数"""

import random
import time
from .locators import find_search_box, SEARCH_BTN_STRATEGIES


def search_keyword(page, keyword: str):
    """在页面输入关键词并搜索"""
    search_box = find_search_box(page)
    search_box.click()
    time.sleep(0.2)

    # 模拟人工逐字输入
    for char in keyword:
        search_box.type(char, delay=random.uniform(80, 200))
        time.sleep(random.uniform(0.05, 0.15))

    # 优先尝试点击搜索按钮，否则回车
    searched = False
    for i, strategy in enumerate(SEARCH_BTN_STRATEGIES):
        try:
            btn = strategy(page)
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                searched = True
                print(f"  [定位] 搜索按钮策略 {i+1} 点击")
                break
        except Exception:
            pass

    if not searched:
        page.keyboard.press("Enter")
        print("  [定位] 使用回车搜索")

    time.sleep(1.5)