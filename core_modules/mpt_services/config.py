"""MPT 配置模块"""

import os
import sys
from pathlib import Path

# 项目路径
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

RESOURCE_DIR = os.path.join(BASE_DIR, "resource")
FONTS_DIR = os.path.join(RESOURCE_DIR, "fonts")
SONGS_DIR = os.path.join(RESOURCE_DIR, "songs")

# 默认配置
DEFAULT_CONFIG = {
    # LLM 配置（复用项目的文字模型配置）
    "text_api_base": "https://api.deepseek.com/v1",
    "text_api_key": "",
    "text_model": "deepseek-chat",

    # 素材源
    "video_source": "pexels",  # pexels 或 pixabay
    "pexels_api_key": "",
    "pixabay_api_key": "",

    # 语音合成
    "voice_role": "zh-CN-XiaoxiaoNeural",
    "voice_rate": "+0%",
    "voice_volume": "+0%",

    # 字幕
    "subtitle_enabled": True,
    "subtitle_font": "arial.ttf",
    "subtitle_size": 24,
    "subtitle_color": "#FFFFFF",

    # 视频设置
    "video_format": "9:16",  # 9:16 竖屏 或 16:9 横屏
    "video_quality": "720p",

    # 背景音乐
    "bg_music_enabled": False,
    "bg_music_file": "",

    # Whisper 模型
    "whisper_model": "base",
    "whisper_model_path": "",
}


def get_config():
    """从项目设置文件加载配置"""
    settings_file = os.path.join(os.path.expanduser("~"), ".dy", "desktop_settings.json")
    if os.path.exists(settings_file):
        try:
            import json
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            # 映射项目设置到 MPT 配置
            cfg["text_api_base"] = settings.get("openai_text_api_base", cfg["text_api_base"])
            cfg["text_api_key"] = settings.get("openai_text_api_key", cfg["text_api_key"])
            cfg["text_model"] = settings.get("openai_text_model", cfg["text_model"])
            cfg["voice_role"] = settings.get("mpt_voice_role", cfg["voice_role"])
            cfg["subtitle_enabled"] = settings.get("mpt_subtitle_enabled", cfg["subtitle_enabled"])
            cfg["bg_music_enabled"] = settings.get("mpt_bg_music_enabled", cfg["bg_music_enabled"])
            cfg["video_format"] = settings.get("mpt_video_format", cfg["video_format"])
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()