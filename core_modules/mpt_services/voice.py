"""语音服务 - Edge TTS 语音合成"""

import os
import tempfile
import asyncio
from typing import Optional


class VoiceService:
    """Edge TTS 语音合成服务"""

    # 常用语音角色
    VOICE_ROLES = [
        # 中文
        "zh-CN-XiaoxiaoNeural",    # 晓晓 - 女声
        "zh-CN-YunxiNeural",       # 云希 - 男声
        "zh-CN-YunyangNeural",     # 云扬 - 男声（新闻）
        "zh-CN-XiaoyiNeural",      # 小艺 - 女声
        "zh-CN-YunyeNeural",       # 云野 - 男声

        # 英文
        "en-US-JennyNeural",       # Jenny - 女声
        "en-US-GuyNeural",         # Guy - 男声
        "en-GB-SoniaNeural",       # Sonia - 英式女声

        # 日文
        "ja-JP-NanamiNeural",      #  七波 - 日语女声
        "ja-JP-KeitaNeural",       # 敬太 - 日语男声

        # 韩文
        "ko-KR-SunHiNeural",       # 贤妃 - 韩语女声
    ]

    def __init__(self, voice_role: str = "zh-CN-XiaoxiaoNeural",
                 voice_rate: str = "+0%",
                 voice_volume: str = "+0%"):
        self.voice_role = voice_role
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume

    def generate_speech(self, text: str, output_path: Optional[str] = None) -> str:
        """
        将文本转为语音并保存为音频文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径，默认临时文件

        Returns:
            生成的音频文件路径
        """
        if not output_path:
            import uuid
            unique = uuid.uuid4().hex[:8]
            output_path = os.path.join(tempfile.gettempdir(), f"mpt_voice_{os.getpid()}_{unique}.mp3")

        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("请安装 edge-tts: pip install edge-tts")

        async def _generate():
            try:
                communicate = edge_tts.Communicate(
                    text,
                    voice=self.voice_role,
                    rate=self.voice_rate,
                    volume=self.voice_volume
                )
                await communicate.save(output_path)
            except Exception as e:
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise RuntimeError(f"语音合成失败: {e}")

        try:
            asyncio.get_event_loop().run_until_complete(_generate())
        except RuntimeError:
            # Event loop already running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate())

        return output_path

    def generate_speech_with_timestamps(self, text: str, output_dir: Optional[str] = None) -> dict:
        """
        生成带时间戳的语音（用于字幕对齐）

        Args:
            text: 要转换的文本
            output_dir: 输出目录

        Returns:
            包含音频路径和时间戳信息的字典
        """
        if not output_dir:
            output_dir = tempfile.gettempdir()

        import uuid
        unique = uuid.uuid4().hex[:8]
        audio_path = os.path.join(output_dir, f"mpt_voice_ts_{os.getpid()}_{unique}.mp3")
        vtt_path = os.path.join(output_dir, f"mpt_voice_ts_{os.getpid()}_{unique}.vtt")

        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("请安装 edge-tts: pip install edge-tts")

        async def _generate():
            try:
                communicate = edge_tts.Communicate(
                    text,
                    voice=self.voice_role,
                    rate=self.voice_rate,
                    volume=self.voice_volume
                )
                await communicate.save(audio_path)

                # 生成 VTT 字幕
                submaker = edge_tts.SubMaker()
                async with communicate as stream:
                    async for chunk in stream.stream:
                        if chunk["type"] == "audio":
                            submaker.feed(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            submaker.new_word()

                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write(submaker.export_subtitles())

            except Exception as e:
                raise RuntimeError(f"语音合成失败: {e}")

        try:
            asyncio.get_event_loop().run_until_complete(_generate())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate())

        return {
            "audio_path": audio_path,
            "vtt_path": vtt_path
        }

    @staticmethod
    def list_available_voices() -> list:
        """获取所有可用的语音角色"""
        return VoiceService.VOICE_ROLES