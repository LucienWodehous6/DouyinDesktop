"""视频合成服务 - MoviePy 视频编辑"""

import os
import tempfile
import subprocess
from typing import Optional, List


class VideoBuilder:
    """视频合成服务，使用 MoviePy 将素材拼接、添加字幕、背景音乐"""

    def __init__(self, video_format: str = "9:16"):
        """
        Args:
            video_format: 9:16 竖屏 或 16:9 横屏
        """
        self.video_format = video_format

        # 尺寸配置
        if video_format == "9:16":
            self.width = 1080
            self.height = 1920
        else:
            self.width = 1920
            self.height = 1080

    def concatenate_videos(self, video_paths: List[str], output_path: Optional[str] = None,
                           voice_audio: Optional[str] = None,
                           subtitle_path: Optional[str] = None,
                           bg_music: Optional[str] = None,
                           bg_music_volume: float = 0.3) -> str:
        """
        将多个视频片段拼接成一个视频

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出路径
            voice_audio: TTS 语音文件路径（优先作为配音）
            subtitle_path: SRT 字幕文件路径（烧录到视频）
            bg_music: 背景音乐路径
            bg_music_volume: 背景音乐音量 (0.0-1.0)

        Returns:
            拼接后的视频路径
        """
        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), f"mpt_concat_{os.getpid()}.mp4")

        if len(video_paths) == 0:
            raise RuntimeError("没有视频片段")
        if len(video_paths) == 1:
            # 单个视频，直接复制（需要烧录字幕的话用 ffmpeg）
            import shutil
            shutil.copy(video_paths[0], output_path)
            if subtitle_path and os.path.exists(subtitle_path):
                output_path = self._burn_subtitle(output_path, subtitle_path, voice_audio)
            return output_path

        try:
            # moviepy 2.x 使用 moviepy import，1.x 使用 moviepy.editor
            try:
                from moviepy import (
                    VideoFileClip, concatenate_videoclips,
                    AudioFileClip, CompositeAudioClip
                )
            except (ImportError, SyntaxError):
                from moviepy.editor import (
                    VideoFileClip, concatenate_videoclips,
                    AudioFileClip, CompositeAudioClip
                )
        except ImportError:
            raise RuntimeError("请安装 moviepy: pip install moviepy")

        try:
            # 加载所有视频片段
            clips = []
            for path in video_paths:
                if not os.path.exists(path):
                    raise RuntimeError(f"视频文件不存在: {path}")

                clip = VideoFileClip(path)

                # 缩放/裁剪为统一尺寸
                clip = self._resize_clip(clip)

                clips.append(clip)

            # 拼接视频
            final_video = concatenate_videoclips(clips, method="compose")

            # 设置音频：优先使用 TTS 配音（ffmpeg 混音，兼容所有 moviepy 版本）
            if voice_audio and os.path.exists(voice_audio):
                temp_video = os.path.join(tempfile.gettempdir(), f"mpt_video_{os.getpid()}.mp4")
                temp_audio = os.path.join(tempfile.gettempdir(), f"mpt_audio_{os.getpid()}.aac")

                # 先保存视频（无音频）
                final_video.write_videofile(
                    temp_video,
                    codec='libx264',
                    audio_codec='aac',
                    bitrate='5000k',
                    fps=30,
                    preset='medium',
                    audio=False
                )

                # 用 ffmpeg 混音：TTS 配音 + 背景音乐
                cmd = ["ffmpeg", "-y"]
                cmd += ["-i", temp_video]

                if bg_music and os.path.exists(bg_music):
                    # TTS 配音降低音量 + 背景音乐混合
                    cmd += [
                        "-i", voice_audio,
                        "-i", bg_music,
                        "-filter_complex",
                        f"[1:a]volume=0.2[bg];[0:a]volume=1.0[voice];[voice][bg]amix=inputs=2:duration=longest[aout]",
                        "-map", "0:v",
                        "-map", "[aout]",
                    ]
                else:
                    cmd += [
                        "-i", voice_audio,
                        "-map", "0:v",
                        "-map", "1:a",
                    ]

                cmd += [
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    output_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    # ffmpeg 失败则用原 video（保留素材音频）
                    pass
                else:
                    # 清理临时文件
                    for f in [temp_video, temp_audio]:
                        if os.path.exists(f):
                            os.remove(f)
            else:
                # 保存
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    bitrate='5000k',
                    fps=30,
                    preset='medium',
                    audio=True
                )

            # 关闭所有 clips
            for clip in clips:
                clip.close()
            final_video.close()

            # 烧录字幕
            if subtitle_path and os.path.exists(subtitle_path):
                output_path = self._burn_subtitle(output_path, subtitle_path, voice_audio)

            return output_path

        except Exception as e:
            raise RuntimeError(f"视频拼接失败: {e}")

    def add_intro(self, video_path: str, intro_path: str, output_path: Optional[str] = None) -> str:
        """
        在视频前添加片头

        Args:
            video_path: 原视频路径
            intro_path: 片头视频路径
            output_path: 输出路径

        Returns:
            添加片头后的视频路径
        """
        if not output_path:
            output_path = video_path.replace(".mp4", "_intro.mp4")

        try:
            try:
                from moviepy import VideoFileClip, concatenate_videoclips
            except (ImportError, SyntaxError):
                from moviepy.editor import VideoFileClip, concatenate_videoclips
        except ImportError:
            raise RuntimeError("请安装 moviepy: pip install moviepy")

        try:
            video = VideoFileClip(video_path)
            intro = VideoFileClip(intro_path)

            # 调整片头尺寸
            intro = self._resize_clip(intro)

            # 拼接
            final = concatenate_videoclips([intro, video], method="compose")

            final.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='5000k',
                fps=30,
                preset='medium'
            )

            video.close()
            intro.close()
            final.close()

            return output_path

        except Exception as e:
            raise RuntimeError(f"添加片头失败: {e}")

    def add_outro(self, video_path: str, outro_path: str, output_path: Optional[str] = None) -> str:
        """
        在视频后添加片尾

        Args:
            video_path: 原视频路径
            outro_path: 片尾视频路径
            output_path: 输出路径

        Returns:
            添加片尾后的视频路径
        """
        if not output_path:
            output_path = video_path.replace(".mp4", "_outro.mp4")

        try:
            try:
                from moviepy import VideoFileClip, concatenate_videoclips
            except (ImportError, SyntaxError):
                from moviepy.editor import VideoFileClip, concatenate_videoclips
        except ImportError:
            raise RuntimeError("请安装 moviepy: pip install moviepy")

        try:
            video = VideoFileClip(video_path)
            outro = VideoFileClip(outro_path)

            outro = self._resize_clip(outro)

            final = concatenate_videoclips([video, outro], method="compose")

            final.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='5000k',
                fps=30,
                preset='medium'
            )

            video.close()
            outro.close()
            final.close()

            return output_path

        except Exception as e:
            raise RuntimeError(f"添加片尾失败: {e}")

    def _resize_clip(self, clip):
        """调整 clip 尺寸以匹配目标尺寸"""
        try:
            # 计算缩放比例
            scale_w = self.width / clip.w
            scale_h = self.height / clip.h
            scale = max(scale_w, scale_h)  # 使用更大的缩放以覆盖目标

            # 缩放
            clip = clip.resize(scale)

            # 居中裁剪
            if clip.w > self.width or clip.h > self.height:
                x_center = clip.w / 2
                y_center = clip.h / 2
                clip = clip.crop(
                    x_center=x_center,
                    y_center=y_center,
                    width=self.width,
                    height=self.height
                )

            return clip

        except Exception:
            return clip

    def _burn_subtitle(self, video_path: str, subtitle_path: str, audio_path: Optional[str] = None) -> str:
        """使用 ffmpeg 将字幕烧录到视频中"""
        output_path = video_path.replace(".mp4", "_sub.mp4")
        try:
            import subprocess
            import platform

            def ffmpeg_path(p):
                """Windows 路径转换为 ffmpeg 可用的格式"""
                if platform.system() == "Windows":
                    return p.replace("\\", "/").replace(":", "\\\\:")
                return p

            video_path_ff = ffmpeg_path(video_path)
            subtitle_path_ff = ffmpeg_path(subtitle_path)

            cmd = [
                "ffmpeg", "-y",
                "-i", video_path_ff,
                "-vf", f"subtitles='{subtitle_path_ff}'",
            ]

            if audio_path and os.path.exists(audio_path):
                cmd.extend(["-i", ffmpeg_path(audio_path)])
                cmd.extend(["-map", "0:v", "-map", "1:a"])
            else:
                cmd.extend(["-map", "0:v", "-map", "0:a?"])

            cmd.extend([
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                output_path
            ])

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return video_path
            return output_path
        except FileNotFoundError:
            return video_path
        except Exception:
            return video_path

    def get_video_info(self, video_path: str) -> dict:
        """获取视频信息"""
        try:
            try:
                from moviepy import VideoFileClip
            except (ImportError, SyntaxError):
                from moviepy.editor import VideoFileClip
            clip = VideoFileClip(video_path)
            info = {
                "duration": clip.duration,
                "width": clip.w,
                "height": clip.h,
                "fps": clip.fps
            }
            clip.close()
            return info
        except Exception as e:
            return {"error": str(e)}