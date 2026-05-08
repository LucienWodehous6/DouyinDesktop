"""后台采集线程 — 在 QThread 中运行浏览器自动化模块，信号与主窗口通信"""

import io
import sys
import json
import time
import os
import threading
from contextlib import redirect_stdout, redirect_stderr

from PyQt6.QtCore import QThread, pyqtSignal


class DataWorker(QThread):
    log_signal = pyqtSignal(str, str)       # (message, level)
    progress_signal = pyqtSignal(int)        # 0-100
    finished_signal = pyqtSignal(str)        # result_file_path
    error_signal = pyqtSignal(str)           # error_message

    def __init__(
        self,
        task_id: str = "",
        task_store=None,
        platform: str = "抖音",
        search_text: str = "",
        match_keywords: list[str] | None = None,
        video_count: int = 5,
        max_scrolls: int = 50,
        sort_by: str = "最新发布",
        time_filter: str | None = None,
        cdp_url: str = "http://127.0.0.1:9222",
        cookie_file: str | None = None,
        use_cdp: bool = True,
        dm_message: str | None = None,
    ):
        super().__init__()
        self.task_id = task_id
        self.task_store = task_store
        self.platform = platform
        self.search_text = search_text
        self.match_keywords = match_keywords
        self.video_count = video_count
        self.max_scrolls = max_scrolls
        self.sort_by = sort_by
        self.time_filter = time_filter
        self.cdp_url = cdp_url
        self.cookie_file = cookie_file
        self.use_cdp = use_cdp
        self.dm_message = dm_message
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        """在后台线程中执行采集逻辑"""
        os.environ["DOUYIN_DESKTOP_MODE"] = "1"
        try:
            self._run_automation()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_automation(self):
        """动态导入浏览器自动化模块 — 根据平台选择抖音或小红书脚本"""

        if getattr(sys, 'frozen', False):
            scripts_dir = os.path.join(os.path.dirname(sys.executable), "core_modules")
        else:
            scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core_modules")

        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        # 根据平台选择模块
        if self.platform == "小红书":
            try:
                import xhs_search as xhs
            except ImportError:
                self.error_signal.emit(f"未找到小红书脚本！请将 xhs_search.py 放入：\n{scripts_dir}")
                return
            self._run_xhs(xhs)
        else:
            try:
                import browser_automation as dba
            except ImportError:
                self.error_signal.emit(f"未找到抖音脚本！请将 browser_automation.py 放入：\n{scripts_dir}")
                return
            self._run_douyin(dba)

    def _run_douyin(self, dba):
        """运行抖音采集"""
        os.environ["DOUYIN_DESKTOP_MODE"] = "1"

        captured = io.StringIO()

        class SignalStream:
            def __init__(self, signal, original):
                self.signal = signal
                self.original = original
                self._buffer = ""
                self._closed = False

            def write(self, s):
                if self._closed:
                    return
                try:
                    if sys.platform == 'win32':
                        s_out = s.encode('gbk', errors='replace').decode('gbk')
                        self.original.write(s_out)
                    else:
                        self.original.write(s)
                except (ValueError, IOError):
                    self._closed = True
                    return
                self._buffer += s
                if "\n" in self._buffer:
                    lines = self._buffer.split("\n")
                    self._buffer = lines[-1]
                    for line in lines[:-1]:
                        line = line.strip()
                        if line:
                            level = "INFO"
                            if "[!]" in line or "失败" in line:
                                level = "ERROR"
                            elif "[✓]" in line or "完成" in line or "成功" in line:
                                level = "SUCCESS"
                            elif "[*]" in line or "中止" in line:
                                level = "WARN"
                            self.signal.emit(line, level)

            def flush(self):
                pass

        signal_stream = SignalStream(self.log_signal, sys.stdout)

        with redirect_stdout(signal_stream), redirect_stderr(signal_stream):
            original_save = dba.save_results

            def patched_save(all_videos, search_text, match_keywords, output_dir=None):
                if self.task_store and self.task_id:
                    result_data = {
                        "search_term": search_text,
                        "match_keywords": match_keywords,
                        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                        "task_id": self.task_id,
                        "total_videos": len(all_videos),
                        "videos": all_videos,
                    }
                    result_path = self.task_store.save_result(self.task_id, result_data)
                else:
                    result_path = original_save(all_videos, search_text, match_keywords, output_dir)
                self.finished_signal.emit(result_path)
                return result_path

            dba.save_results = patched_save

            dba._MAX_SCROLLS = self.max_scrolls
            if dba.USE_CDP:
                dba.search_via_cdp(
                    search_text=self.search_text,
                    cookie_file=self.cookie_file,
                    match_keywords=self.match_keywords,
                    video_count=self.video_count,
                    sort_by=self.sort_by,
                    time_filter=self.time_filter,
                    dm_message=self.dm_message,
                )
            else:
                dba.search_via_launch(
                    search_text=self.search_text,
                    cookie_file=self.cookie_file,
                    match_keywords=self.match_keywords,
                    video_count=self.video_count,
                    sort_by=self.sort_by,
                    time_filter=self.time_filter,
                    dm_message=self.dm_message,
                )

    def _run_xhs(self, xhs):
        """运行小红书采集"""
        import re as regex

        class SignalStream:
            def __init__(self, signal, original):
                self.signal = signal
                self.original = original
                self._buffer = ""
                self._closed = False

            def write(self, s):
                if self._closed:
                    return
                try:
                    if sys.platform == 'win32':
                        s_out = s.encode('gbk', errors='replace').decode('gbk')
                        self.original.write(s_out)
                    else:
                        self.original.write(s)
                except (ValueError, IOError):
                    self._closed = True
                    return
                self._buffer += s
                if "\n" in self._buffer:
                    lines = self._buffer.split("\n")
                    self._buffer = lines[-1]
                    for line in lines[:-1]:
                        line = line.strip()
                        if line:
                            level = "INFO"
                            if "[!]" in line or "失败" in line:
                                level = "ERROR"
                            elif "[✓]" in line or "完成" in line or "成功" in line:
                                level = "SUCCESS"
                            elif "[*]" in line or "中止" in line:
                                level = "WARN"
                            self.signal.emit(line, level)

            def flush(self):
                pass

        signal_stream = SignalStream(self.log_signal, sys.stdout)

        with redirect_stdout(signal_stream), redirect_stderr(signal_stream):
            from playwright.sync_api import sync_playwright
            import urllib.parse

            # 构建 collect 参数
            match_kw_text = ",".join(self.match_keywords) if self.match_keywords else ""
            max_videos = self.video_count
            sort_map = {"最新发布": "最新", "最多点赞": "最多点赞", "最多评论": "最多评论", "最多收藏": "最多收藏"}
            sort_val = sort_map.get(self.sort_by, "综合") if self.sort_by else "综合"

            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp(self.cdp_url)
                except Exception as e:
                    self.error_signal.emit(f"CDP 连接失败: {e}")
                    return

                # 查找搜索结果页或创建新的
                search_page = None
                for ctx in browser.contexts:
                    for pg in ctx.pages:
                        if "xiaohongshu.com/search_result" in pg.url:
                            search_page = pg
                            break
                    if search_page:
                        break

                if not search_page:
                    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                    search_page = ctx.new_page()

                page = search_page

                keyword = self.search_text
                self.log_signal.emit(f"[小红书] 关键词: {keyword}", "INFO")

                # 导航到搜索结果页
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}"
                self.log_signal.emit(f"[小红书] 导航到: {search_url}", "INFO")
                page.goto(search_url, wait_until="domcontentloaded")
                time.sleep(2)

                # 应用筛选
                if sort_val != "综合":
                    xhs.apply_filter(page, sort=sort_val)
                    time.sleep(1)

                # 收集搜索结果
                all_results = xhs.collect_search_results(page, skip_recommend=True, max_count=max_videos * 3)
                self.log_signal.emit(f"[小红书] 共获取 {len(all_results)} 个搜索结果", "INFO")

                video_data = []
                total_matched_users = 0
                collected_videos = 0

                for r in all_results:
                    if collected_videos >= max_videos:
                        break

                    idx = r.get("index", 0)
                    title = r.get("title") or f"笔记{idx}"
                    self.log_signal.emit(f"[小红书] === 笔记 {collected_videos+1}: {title[:40]} ===", "INFO")

                    if not xhs.click_search_result(page, idx):
                        self.log_signal.emit(f"[小红书] 点击失败，跳过", "WARN")
                        continue

                    time.sleep(2)

                    # 检测评论区是否为空
                    is_empty = page.evaluate("""
                        () => {
                            const body = document.body.innerText;
                            return body.includes('荒地') || body.includes('点击评论') || body.includes('暂无评论');
                        }
                    """)
                    if is_empty:
                        self.log_signal.emit(f"[小红书] 评论区为空，跳过此笔记", "WARN")
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        continue

                    # 滚动评论
                    comments_data = xhs.collect_comments(
                        page,
                        max_count=500,
                        scroll_to_end=False,
                        scroll_pause=0.8
                    )
                    self.log_signal.emit(f"[小红书] 获取到 {len(comments_data)} 条评论", "INFO")

                    # 关键字过滤
                    v_matched_users = []
                    if match_kw_text:
                        kw_pattern = match_kw_text.replace(",", "|")
                        for c in comments_data:
                            content = c.get("content") or ""
                            author = c.get("author") or ""
                            if regex.search(kw_pattern, content + author):
                                self.log_signal.emit(f"[小红书]   匹配到: {author} — {content[:30]}", "INFO")
                                author_href = c.get("authorHref")
                                if author_href:
                                    page.evaluate(f"window.open('{author_href}', '_blank')")
                                    time.sleep(2)

                                new_page_found = False
                                for attempt in range(3):
                                    all_pages = browser.contexts[0].pages
                                    for pg in all_pages:
                                        if "xiaohongshu.com/user/profile" in pg.url:
                                            user_info = xhs.collect_user_profile(pg)
                                            user_info["comment_content"] = content
                                            user_info["comment_time"] = c.get("time") or ""
                                            user_info["comment_likes"] = c.get("likes") or ""
                                            v_matched_users.append(user_info)
                                            pg.close()
                                            time.sleep(0.3)
                                            new_page_found = True
                                            break
                                    if new_page_found:
                                        break
                                    time.sleep(1)

                        self.log_signal.emit(f"[小红书]   本笔记匹配用户: {len(v_matched_users)} 人", "INFO")
                        total_matched_users += len(v_matched_users)

                    # 构建视频数据
                    video_entry = {
                        "index": collected_videos + 1,
                        "title": title,
                        "video_id": r.get("href", "").split("/")[-1] if r.get("href") else "",
                        "href": r.get("href"),
                        "likes": "",
                        "comments_count": len(comments_data),
                        "collects": "",
                        "shares": "",
                        "comments": comments_data,
                        "matched_users": v_matched_users,
                    }
                    video_data.append(video_entry)
                    collected_videos += 1

                    # 关闭详情弹窗
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
                    page.keyboard.press("Escape")
                    time.sleep(0.8)

                # 保存结果
                output_data = {
                    "search_term": keyword,
                    "match_keywords": self.match_keywords or [],
                    "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                    "platform": "小红书",
                    "task_id": self.task_id,
                    "total_videos": len(video_data),
                    "total_matched_users": total_matched_users,
                    "videos": video_data,
                }

                self.log_signal.emit(f"\n{'='*60}", "INFO")
                self.log_signal.emit(f"采集完成！共 {len(video_data)} 个笔记，{total_matched_users} 个匹配用户", "SUCCESS")

                if self.task_store and self.task_id:
                    result_path = self.task_store.save_result(self.task_id, output_data)
                else:
                    import json as json_module
                    output_path = os.path.join(os.path.expanduser("~"), ".dy", "results", f"xhs_{time.strftime('%Y%m%d_%H%M%S')}.json")
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "w", encoding="utf-8") as f:
                        json_module.dump(output_data, f, ensure_ascii=False, indent=2)
                    result_path = output_path

                self.finished_signal.emit(result_path)
