"""后台采集线程 — 在 QThread 中运行 douyin_browser_automation，信号与主窗口通信"""

import io
import sys
import json
import time
import os
import threading
from contextlib import redirect_stdout, redirect_stderr

from PyQt6.QtCore import QThread, pyqtSignal


class DouyinWorker(QThread):
    log_signal = pyqtSignal(str, str)       # (message, level)
    progress_signal = pyqtSignal(int)        # 0-100
    finished_signal = pyqtSignal(str)        # result_file_path
    error_signal = pyqtSignal(str)           # error_message

    def __init__(
        self,
        task_id: str = "",
        task_store=None,
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
            # 修改脚本中的全局配置（通过 monkey-patch 传入参数）
            self._run_automation()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_automation(self):
        """动态导入 douyin_browser_automation — 从 EXE_DIR/core_modules/ 加载（打包后）
        开发模式回退到项目根目录 core_modules/。核心脚本不打包进应用，保护代码安全。"""

        # 获取脚本所在目录
        if getattr(sys, 'frozen', False):
            # 打包后：exe 同级目录下的 core_modules/
            scripts_dir = os.path.join(os.path.dirname(sys.executable), "core_modules")
        else:
            # 开发模式：项目根目录 core_modules/
            scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core_modules")

        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        try:
            import douyin_browser_automation as dba
        except ImportError:
            self.error_signal.emit(
                f"未找到核心脚本！请将 douyin_browser_automation.py 放入：\n{scripts_dir}"
            )
            return

        # 覆盖配置
        dba.USE_CDP = self.use_cdp
        dba.CDP_URL = self.cdp_url
        dba.COOKIE_FILE = self.cookie_file

        # 重定向 stdout 到信号
        captured = io.StringIO()

        class SignalStream:
            def __init__(self, signal, original):
                self.signal = signal
                self.original = original
                self._buffer = ""

            def write(self, s):
                self.original.write(s)
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
            # 修改 save_results 使其返回文件路径并发出信号
            original_save = dba.save_results

            def patched_save(all_videos, search_text, match_keywords, output_dir=None):
                # 桌面模式：只保存到 TaskStore，不额外写文件
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

            # 执行采集
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
