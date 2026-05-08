"""素材服务 - 从 Pexels/Pixabay 获取视频素材"""

import os
import re
import requests
import tempfile
from typing import Optional
from urllib.parse import urlencode


class MaterialService:
    """视频素材搜索与下载服务"""

    PEXELS_API = "https://api.pexels.com/videos/search"
    PIXABAY_API = "https://pixabay.com/api/videos/"

    def __init__(self, source: str = "pexels", api_key: str = ""):
        self.source = source.lower()
        self.api_key = api_key

    def search_videos(self, query: str, min_duration: int = 5, max_duration: int = 60,
                      per_page: int = 15) -> list:
        """
        搜索视频素材

        Args:
            query: 搜索关键词
            min_duration: 最小时长（秒）
            max_duration: 最大时长（秒）
            per_page: 每页数量

        Returns:
            视频素材列表
        """
        if self.source == "pexels":
            return self._search_pexels(query, min_duration, max_duration, per_page)
        else:
            return self._search_pixabay(query, min_duration, max_duration, per_page)

    def _search_pexels(self, query: str, min_duration: int, max_duration: int, per_page: int) -> list:
        """从 Pexels 搜索视频"""
        if not self.api_key:
            # 使用公开 API（有限制）
            headers = {"Authorization": "demo"}
        else:
            headers = {"Authorization": self.api_key}

        params = {
            "query": query,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "per_page": per_page,
            "orientation": "portrait"  # 竖屏素材优先
        }

        try:
            response = requests.get(
                self.PEXELS_API,
                headers=headers,
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                videos = []
                for item in data.get("videos", []):
                    # 选择合适的分辨率
                    video_files = item.get("video_files", [])
                    best = self._select_best_video(video_files)
                    if best:
                        videos.append({
                            "id": item["id"],
                            "url": best["link"],
                            "duration": item["duration"],
                            "width": best["width"],
                            "height": best["height"],
                            "thumbnail": item["image"],
                            "source": "pexels"
                        })
                return videos
            else:
                raise RuntimeError(f"Pexels API 错误: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"搜索 Pexels 失败: {e}")

    def _search_pixabay(self, query: str, min_duration: int, max_duration: int, per_page: int) -> list:
        """从 Pixabay 搜索视频"""
        if not self.api_key:
            return []

        params = {
            "key": self.api_key,
            "q": query,
            "video_type": "film",
            "min_duration": min_duration,
            "max_duration": max_duration,
            "per_page": per_page,
            "safesearch": "true"
        }

        try:
            response = requests.get(self.PIXABAY_API, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                videos = []
                for item in data.get("hits", []):
                    videos.append({
                        "id": item["id"],
                        "url": item["videos"]["medium"]["url"],
                        "duration": item["videos"]["medium"]["duration"],
                        "width": item["videos"]["medium"]["width"],
                        "height": item["videos"]["medium"]["height"],
                        "thumbnail": item["videos"]["medium"]["url"].replace(".mp4", ".jpg"),
                        "source": "pixabay"
                    })
                return videos
            else:
                raise RuntimeError(f"Pixabay API 错误: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"搜索 Pixabay 失败: {e}")

    def _select_best_video(self, video_files: list) -> Optional[dict]:
        """从多个分辨率中选择最合适的视频"""
        if not video_files:
            return None

        # 优先选择竖屏（9:16）
        portrait = [v for v in video_files if v.get("height", 0) > v.get("width", 0)]
        if portrait:
            # 选择中等分辨率（避免太大导致下载慢）
            portrait.sort(key=lambda x: x.get("height", 0), reverse=True)
            mid = len(portrait) // 2
            return portrait[mid] if mid < len(portrait) else portrait[0]

        # 没有竖屏则选横屏
        video_files.sort(key=lambda x: x.get("height", 0), reverse=True)
        mid = len(video_files) // 2
        return video_files[mid] if mid < len(video_files) else video_files[0]

    def download_video(self, url: str, output_dir: Optional[str] = None) -> str:
        """
        下载视频到本地

        Args:
            url: 视频 URL
            output_dir: 输出目录，默认临时目录

        Returns:
            本地视频文件路径
        """
        if output_dir is None:
            output_dir = tempfile.gettempdir()

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成文件名
        filename = f"mpt_video_{os.path.basename(url)[:50]}.mp4"
        filepath = os.path.join(output_dir, filename)

        try:
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return filepath
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise RuntimeError(f"视频下载失败: {e}")

    def download_thumbnail(self, url: str, output_dir: Optional[str] = None) -> str:
        """下载视频缩略图"""
        if output_dir is None:
            output_dir = tempfile.gettempdir()

        filename = f"mpt_thumb_{os.path.basename(url)[:50]}.jpg"
        filepath = os.path.join(output_dir, filename)

        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return filepath
        except Exception as e:
            return ""