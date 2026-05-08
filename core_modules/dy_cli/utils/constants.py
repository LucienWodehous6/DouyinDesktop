"""
常量定义 - 避免魔法数字，提高代码可维护性。
"""
from __future__ import annotations

# ------------------------------------------------------------------
# API 客户端常量
# ------------------------------------------------------------------

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BASE_DELAY = 1.0
INDEX_EXPIRY_SECONDS = 3600  # 1小时

# ------------------------------------------------------------------
# Playwright 常量
# ------------------------------------------------------------------

# 超时时间（毫秒）
LOGIN_CHECK_TIMEOUT_MS = 8000
LOGIN_TIMEOUT_MS = 120000  # 2分钟
INPUT_WAIT_TIMEOUT_MS = 5000
UPLOAD_WAIT_TIMEOUT_MS = 5000

# 轮询次数
MAX_UPLOAD_POLLS = 120  # 10分钟 (5秒间隔)
MAX_NOTIFICATION_POLLS = 10
MAX_ELEMENT_WAIT_POLLS = 15

# 等待时间（毫秒）
ELEMENT_WAIT_INTERVAL_MS = 2000
PAGE_WAIT_TIMEOUT_MS = 30000

# ------------------------------------------------------------------
# Trending 常量
# ------------------------------------------------------------------

TRENDING_WATCH_INTERVAL_SECONDS = 300  # 5分钟
TRENDING_ERROR_WAIT_SECONDS = 60

# ------------------------------------------------------------------
# Download 常量
# ------------------------------------------------------------------

DOWNLOAD_RATE_LIMIT_SECONDS = 1

# ------------------------------------------------------------------
# 存储常量
# ------------------------------------------------------------------

DEFAULT_SEARCH_HISTORY_LIMIT = 50
DEFAULT_GENERATION_HISTORY_LIMIT = 50
