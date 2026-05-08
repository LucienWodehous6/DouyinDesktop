"""小红书搜索框和按钮定位策略"""

# ─────────────────────────────────────────
#  搜索框定位策略（按优先级尝试）
# ─────────────────────────────────────────
SEARCH_BOX_STRATEGIES = [
    # 1. placeholder 模糊匹配（最稳定）
    lambda p: p.locator('input[placeholder*="搜索"]').first,
    # 2. aria-label
    lambda p: p.locator('input[aria-label*="搜索"]').first,
    # 3. data-testid
    lambda p: p.locator('[data-testid="search_input"]').first,
    # 4. 搜索容器下的 input
    lambda p: p.locator('[class*="search"] input').first,
    lambda p: p.locator('[class*="Search"] input').first,
    # 5. 最后一个 input 且在 header 区域
    lambda p: p.locator('header input[type="text"]').first,
    lambda p: p.locator('header input').first,
]

SEARCH_BTN_STRATEGIES = [
    # 1. button with search text/icon
    lambda p: p.locator('button[aria-label*="搜索"]').first,
    lambda p: p.locator('[class*="search"] button').first,
    lambda p: p.locator('[class*="Search"] button').first,
    # 2. 回车作为备选
]


def find_search_box(page) -> object:
    """多策略定位搜索框"""
    for i, strategy in enumerate(SEARCH_BOX_STRATEGIES):
        try:
            el = strategy(page)
            if el.count() > 0 and el.is_visible():
                print(f"  [定位] 搜索框策略 {i+1} 成功")
                return el
        except Exception:
            pass
    raise RuntimeError("未找到搜索框，请手动定位或检查页面结构")