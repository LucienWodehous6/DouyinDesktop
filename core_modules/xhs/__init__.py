"""
小红书搜索子包
导出主要接口，保持与 xhs_search.py 的向后兼容
"""

from .locators import (
    SEARCH_BOX_STRATEGIES,
    SEARCH_BTN_STRATEGIES,
    find_search_box,
)
from .actions import search_keyword

__all__ = [
    "SEARCH_BOX_STRATEGIES",
    "SEARCH_BTN_STRATEGIES",
    "find_search_box",
    "search_keyword",
]