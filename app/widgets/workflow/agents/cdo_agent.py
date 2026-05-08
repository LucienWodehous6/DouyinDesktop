"""CDO Agent — 数据采集"""

import json
import os
from PyQt6.QtCore import QThread, pyqtSignal


class CDOAgentWorker(QThread):
    """CDO 数据采集 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, keyword: str, platform: str, count: int, output_file: str):
        super().__init__()
        self.keyword = keyword
        self.platform = platform
        self.count = count
        self.output_file = output_file

    def run(self):
        try:
            self.log_signal.emit(f"[CDO] 开始采集: {self.keyword} on {self.platform}")

            client = None
            try:
                from core_modules.dy_cli.engines.api_client import DouyinAPIClient

                SORT_MAP = {"综合": 0, "最多点赞": 1, "最新发布": 2}
                TIME_MAP = {"不限": 0, "一天内": 1, "一周内": 7, "半年内": 182}

                client = DouyinAPIClient.from_config()
                result = client.search(
                    keyword=self.keyword,
                    sort_type=SORT_MAP["综合"],
                    publish_time=TIME_MAP["不限"],
                    search_type="general",
                    count=self.count,
                )
                client.close()

                videos = []
                data_list = result.get("data", [])
                for item in data_list:
                    aweme = item.get("aweme_info", {})
                    if not aweme:
                        continue
                    videos.append({
                        "aweme_id": aweme.get("aweme_id", ""),
                        "title": aweme.get("desc", ""),
                        "author": aweme.get("author", {}).get("nickname", ""),
                        "likes": aweme.get("statistics", {}).get("digg_count", 0),
                        "comments": aweme.get("statistics", {}).get("comment_count", 0),
                        "collects": aweme.get("statistics", {}).get("collect_count", 0),
                        "shares": aweme.get("statistics", {}).get("share_count", 0),
                    })

                output_data = {
                    "keyword": self.keyword,
                    "platform": self.platform,
                    "count": len(videos),
                    "videos": videos,
                }

                os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
                with open(self.output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                self.log_signal.emit(f"[CDO] 采集完成: {len(videos)} 条数据")
                self.result_signal.emit(output_data)

            except Exception as e:
                if client:
                    try:
                        client.close()
                    except:
                        pass
                raise e

        except Exception as e:
            self.log_signal.emit(f"[CDO] 采集失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
