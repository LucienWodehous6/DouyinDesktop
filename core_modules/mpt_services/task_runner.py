"""任务调度器 - 整合 LLM、素材、语音、字幕、视频合成"""

import os
import tempfile
from typing import Optional, Callable, List

from .llm import LLMService
from .material import MaterialService
from .voice import VoiceService
from .subtitle import SubtitleService
from .video_builder import VideoBuilder


class TaskRunner:
    """MoneyPrinterTurbo 任务调度器 - 完整流水线"""

    def __init__(
        self,
        text_api_base: str,
        text_api_key: str,
        text_model: str,
        voice_role: str = "zh-CN-XiaoxiaoNeural",
        video_source: str = "pexels",
        video_api_key: str = "",
        video_format: str = "9:16",
        subtitle_enabled: bool = True,
        bg_music: Optional[str] = None,
        bg_music_volume: float = 0.3,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None
    ):
        """
        Args:
            text_api_base: 文字模型 API 地址
            text_api_key: 文字模型 API 密钥
            text_model: 文字模型名称
            voice_role: 语音角色
            video_source: 素材源（pexels/pixabay）
            video_api_key: 素材 API 密钥
            video_format: 视频格式（9:16 或 16:9）
            subtitle_enabled: 是否生成字幕
            bg_music: 背景音乐路径
            bg_music_volume: 背景音乐音量
            progress_callback: 进度回调 (percent: int)
            log_callback: 日志回调 (message: str, level: str)
        """
        self.llm = LLMService(text_api_base, text_api_key, text_model)
        self.material = MaterialService(video_source, video_api_key)
        self.voice = VoiceService(voice_role)
        self.subtitle = SubtitleService()
        self.video_builder = VideoBuilder(video_format)

        self.subtitle_enabled = subtitle_enabled
        self.bg_music = bg_music
        self.bg_music_volume = bg_music_volume
        self.progress_callback = progress_callback or (lambda x: None)
        self.log_callback = log_callback or (lambda x, y: None)

        self._temp_files = []

    def run(self, topic: str, script: Optional[str] = None,
            keywords: Optional[List[str]] = None,
            material_count: int = 5) -> str:
        """
        运行完整视频生成流水线

        Args:
            topic: 视频主题
            script: 可选的手动文案（不传则 AI 生成）
            keywords: 素材搜索关键词
            material_count: 素材数量

        Returns:
            最终视频文件路径
        """
        output_dir = tempfile.mkdtemp(prefix="mpt_")
        self._temp_files = []

        try:
            # Step 1: 生成文案
            self._log("正在生成视频文案...", "INFO")
            self._progress(5)

            if script:
                final_script = script
            else:
                if keywords:
                    final_script = self.llm.generate_script_with_keywords(topic, keywords)
                else:
                    final_script = self.llm.generate_script(topic)

            self._log(f"文案生成完成 ({len(final_script)} 字)", "SUCCESS")
            self._progress(15)

            # Step 2: 生成语音
            self._log("正在合成语音...", "INFO")
            audio_path = self.voice.generate_speech(final_script)
            self._temp_files.append(audio_path)
            self._log("语音合成完成", "SUCCESS")
            self._progress(30)

            # Step 3: 搜索素材
            self._log(f"正在搜索视频素材 ({material_count} 个)...", "INFO")
            search_kw = keywords[0] if keywords else topic
            videos = self.material.search_videos(search_kw, per_page=material_count)

            if not videos:
                self._log("未找到合适的素材，使用本地素材", "WARN")

            self._log(f"找到 {len(videos)} 个素材", "SUCCESS")
            self._progress(40)

            # Step 4: 下载素材
            self._log("正在下载视频素材...", "INFO")
            video_paths = []
            for i, video in enumerate(videos[:material_count]):
                try:
                    path = self.material.download_video(video["url"], output_dir)
                    video_paths.append(path)
                    self._temp_files.append(path)
                    self._log(f"下载完成 {i+1}/{len(videos[:material_count])}", "INFO")
                except Exception as e:
                    self._log(f"素材 {i+1} 下载失败: {e}", "WARN")

            if not video_paths:
                raise RuntimeError("没有成功下载任何素材")

            self._progress(60)

            # Step 5: 生成字幕（可选）
            if self.subtitle_enabled:
                self._log("正在生成字幕...", "INFO")
                try:
                    subtitle_path = self.subtitle.generate_from_audio(audio_path)
                    self._temp_files.append(subtitle_path)
                    self._log("字幕生成完成", "SUCCESS")
                except Exception as e:
                    self._log(f"字幕生成失败（继续拼接）: {e}", "WARN")
            else:
                subtitle_path = None

            self._progress(70)

            # Step 6: 视频合成
            self._log("正在拼接视频...", "INFO")
            final_video = self.video_builder.concatenate_videos(
                video_paths,
                output_path=os.path.join(output_dir, "final.mp4"),
                voice_audio=audio_path,
                subtitle_path=subtitle_path,
                bg_music=self.bg_music,
                bg_music_volume=self.bg_music_volume
            )
            self._log("视频拼接完成", "SUCCESS")
            self._progress(90)

            # 保存文案和语音信息
            info_path = os.path.join(output_dir, "info.json")
            import json
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({
                    "topic": topic,
                    "script": final_script,
                    "audio_path": audio_path,
                    "subtitle_path": subtitle_path,
                    "materials": videos,
                    "video_path": final_video
                }, f, ensure_ascii=False, indent=2)

            self._progress(100)
            self._log(f"视频生成完成: {final_video}", "SUCCESS")

            return final_video

        except Exception as e:
            self._log(f"任务执行失败: {e}", "ERROR")
            raise

    def cleanup(self):
        """清理临时文件"""
        for f in self._temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        self._temp_files = []

    def _progress(self, percent: int):
        """更新进度"""
        self.progress_callback(percent)

    def _log(self, message: str, level: str = "INFO"):
        """输出日志"""
        self.log_callback(message, level)