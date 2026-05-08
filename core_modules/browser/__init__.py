"""
浏览器自动化子模块
"""

from core_modules.browser.locators import (
    SEARCH_SELECTORS,
    find_search_input,
)
from core_modules.browser.cookies import (
    load_cookies_from_file,
    inject_cookies,
    _refresh_cookies,
)
from core_modules.browser.actions import (
    random_delay,
    type_human_like,
    get_first_video_item,
    click_first_video,
    is_filter_panel_open,
    toggle_filter_panel,
    get_filter_options,
    apply_filter,
    process_one_video,
    go_next_video,
    is_comment_panel_open,
    dismiss_dialog_if_present,
    scroll_comment_area,
    extract_comments,
    get_video_id,
    get_video_ai_notes,
    get_video_title,
    get_video_stats,
    save_results,
    save_comments,
    extract_user_profile,
    match_comment_and_click_user,
    _immediate_dm_send,
    _send_dm_to_matched_users,
    save_user_profiles,
    search_via_cdp,
    search_via_launch,
    send_dm_via_cdp,
)

__all__ = [
    # locators
    "SEARCH_SELECTORS",
    "find_search_input",
    # cookies
    "load_cookies_from_file",
    "inject_cookies",
    "_refresh_cookies",
    # actions
    "random_delay",
    "type_human_like",
    "get_first_video_item",
    "click_first_video",
    "is_filter_panel_open",
    "toggle_filter_panel",
    "get_filter_options",
    "apply_filter",
    "process_one_video",
    "go_next_video",
    "is_comment_panel_open",
    "dismiss_dialog_if_present",
    "scroll_comment_area",
    "extract_comments",
    "get_video_id",
    "get_video_ai_notes",
    "get_video_title",
    "get_video_stats",
    "save_results",
    "save_comments",
    "extract_user_profile",
    "match_comment_and_click_user",
    "_immediate_dm_send",
    "_send_dm_to_matched_users",
    "save_user_profiles",
    "search_via_cdp",
    "search_via_launch",
    "send_dm_via_cdp",
]