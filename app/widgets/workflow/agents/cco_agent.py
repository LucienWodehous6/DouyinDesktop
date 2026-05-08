"""CCO Agent — 内容创作（剧本生成）"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class CCOAgentWorker(QThread):
    """CCO 内容创作 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str, style: str = "neutral"):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.style = style

    def run(self):
        try:
            import json

            self.log_signal.emit("[CCO] 读取采集数据...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            keyword = data.get("keyword", "")
            videos = data.get("videos", [])

            task_data_str = f"搜索词: {keyword}\n"
            for v in videos[:5]:
                task_data_str += f"\n视频: {v.get('title', '')[:50]}\n"
                task_data_str += f"  点赞:{v.get('likes',0)} 评论:{v.get('comments',0)}\n"

            system_prompt = self._load_system_prompt()

            user_prompt = f"""根据以下采集数据生成一个抖音剧本。

--- 采集数据 ---
{task_data_str}

剧本风格: {self.style}
要求：
1. 开场前3秒必须有强钩子（引起好奇或共鸣）
2. 语言简洁、口语化，适合配音阅读
3. 结构：开场钩子 → 核心内容 → 行动号召
"""

            self.log_signal.emit("[CCO] 调用 AI 生成剧本...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=4096,
                stream=True,
            )

            full_content = ""
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                text = delta.content or ""
                if text:
                    full_content += text

            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(full_content)

            self.log_signal.emit(f"[CCO] 剧本生成完成: {len(full_content)} 字")
            self.result_signal.emit(full_content)

        except Exception as e:
            self.log_signal.emit(f"[CCO] 生成失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        import sys
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models", "script.md"))
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidates.append(os.path.join(project_root, "models", "script.md"))
        candidates.append(os.path.join(os.getcwd(), "models", "script.md"))

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except:
                    pass
        return ""