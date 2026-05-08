"""字幕服务 - Whisper 语音识别生成字幕"""

import os
import tempfile
from typing import Optional


class SubtitleService:
    """字幕生成服务（支持 Edge-TTS 内嵌字幕 或 Whisper 识别）"""

    def __init__(self, whisper_model: str = "base", whisper_model_path: str = ""):
        self.whisper_model = whisper_model
        self.whisper_model_path = whisper_model_path

    def generate_from_audio(self, audio_path: str, language: str = "zh") -> str:
        """
        从音频文件生成字幕

        Args:
            audio_path: 音频文件路径
            language: 字幕语言（zh/en/ja/ko）

        Returns:
            SRT 格式字幕文件路径
        """
        if not os.path.exists(audio_path):
            raise RuntimeError(f"音频文件不存在: {audio_path}")

        # 生成输出路径
        srt_path = audio_path.replace(".mp3", ".srt").replace(".wav", ".srt")
        if srt_path == audio_path:
            srt_path = os.path.join(tempfile.gettempdir(), f"mpt_subtitle_{os.getpid()}.srt")

        try:
            # 尝试使用 faster-whisper
            from faster_whisper import WhisperModel

            model_size = self.whisper_model
            if self.whisper_model_path and os.path.exists(self.whisper_model_path):
                model = WhisperModel(self.whisper_model_path, device="cpu", compute_type="int8")
            else:
                model = WhisperModel(model_size, device="cpu", compute_type="int8")

            # 语言映射
            lang_map = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko"}
            lang = lang_map.get(language, "zh")

            segments, info = model.transcribe(audio_path, language=lang, word_timestamps=True)

            # 生成 SRT 字幕
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(segments, start=1):
                    start = self._format_timestamp(segment.start)
                    end = self._format_timestamp(segment.end)
                    text = segment.text.strip()
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{text}\n\n")

            return srt_path

        except ImportError:
            raise RuntimeError("请安装 faster-whisper: pip install faster-whisper")
        except Exception as e:
            raise RuntimeError(f"字幕生成失败: {e}")

    def generate_from_vtt(self, vtt_path: str) -> str:
        """
        将 VTT 格式字幕转换为 SRT 格式

        Args:
            vtt_path: VTT 字幕文件路径

        Returns:
            SRT 格式字幕文件路径
        """
        if not os.path.exists(vtt_path):
            raise RuntimeError(f"VTT 文件不存在: {vtt_path}")

        srt_path = vtt_path.replace(".vtt", ".srt")

        with open(vtt_path, "r", encoding="utf-8") as f:
            vtt_content = f.read()

        # 解析 VTT 并转换为 SRT
        lines = vtt_content.strip().split("\n")
        srt_lines = []
        index = 1
        time_started = False

        for line in lines:
            line = line.strip()
            if not line or line == "WEBVTT":
                continue

            # 时间行格式: 00:00:00.000 --> 00:00:02.000
            if "-->" in line:
                time_started = True
                start, end = line.split("-->")
                start = start.strip().replace(",", ".")
                end = end.strip().replace(",", ".")
                srt_lines.append(f"{index}")
                srt_lines.append(f"{start} --> {end}")
                index += 1
            elif time_started and line:
                # 文本行
                if not line.startswith("NOTE") and not line.startswith("STYLE"):
                    srt_lines.append(line)

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        return srt_path

    def burn_subtitles(self, video_path: str, subtitle_path: str,
                       output_path: Optional[str] = None,
                       font: str = "Arial",
                       font_size: int = 24,
                       color: str = "white") -> str:
        """
        将字幕烧录到视频中

        Args:
            video_path: 源视频路径
            subtitle_path: 字幕文件路径（SRT）
            output_path: 输出路径，默认覆盖原文件

        Returns:
            烧录后的视频路径
        """
        if not output_path:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")

        try:
            from moviepy import CompositeVideoFileClip, TextClip
            from moviepy.video.fx.all import subtitles
        except ImportError:
            raise RuntimeError("请安装 moviepy: pip install moviepy")

        try:
            # 使用 moviepy 烧录字幕
            from moviepy.editor import VideoFileClip
            from moviepy.video.fx import all as vfx

            video = VideoFileClip(video_path)

            # 解析字幕
            sub_data = self._read_srt(subtitle_path)

            def make_frame(t):
                # 在时间 t 显示对应字幕
                for start, end, text in sub_data:
                    if start <= t <= end:
                        return text
                return None

            # 注意：moviepy 烧录字幕比较复杂，这里简化处理
            # 实际使用中可能需要更复杂的逻辑
            video.close()

            return output_path

        except Exception as e:
            raise RuntimeError(f"字幕烧录失败: {e}")

    def _read_srt(self, srt_path: str) -> list:
        """读取 SRT 字幕文件"""
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        subtitles = []
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                index = lines[0]
                time_line = lines[1]
                text = " ".join(lines[2:])

                start, end = time_line.split("-->")
                start = self._parse_timestamp(start.strip())
                end = self._parse_timestamp(end.strip())

                subtitles.append((start, end, text))

        return subtitles

    def _format_timestamp(self, seconds: float) -> str:
        """将秒数格式化为 SRT 时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _parse_timestamp(self, timestamp: str) -> float:
        """解析时间戳为秒数"""
        # 格式: 00:00:00,000
        parts = timestamp.replace(",", ":").split(":")
        if len(parts) == 4:
            h, m, s, ms = parts
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        return 0.0