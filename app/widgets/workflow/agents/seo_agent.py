"""SEO Agent — 标题/标签优化"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class SEOAgentWorker(QThread):
    """SEO 优化 Agent Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        try:
            self.log_signal.emit("[SEO] 读取剧本内容...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                script_content = f.read()

            self.log_signal.emit("[SEO] 调用 AI 优化标题和标签...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{script_content}

任务要求：
1. 优化标题（≤20字，吸睛，包含关键词）
2. 生成 2 个变体标题（信任型、紧迫型）
3. 推荐 5 个标签（以 # 开头，符合抖音平台规范）
4. 生成视频描述（≤100字）

请严格按以下格式输出：

【优化标题】
（标题内容，≤20字）

【标题变体】
变体A（信任型）：xxx
变体B（紧迫型）：xxx

【推荐标签】
#标签1 #标签2 #标签3 #标签4 #标签5

【视频描述】
（描述内容，≤100字）

【优化后剧本】
（将优化后的完整剧本输出，保留原有结构）
"""

            messages = [{"role": "user", "content": prompt}]

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
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

            self.log_signal.emit(f"[SEO] 优化完成: {len(full_content)} 字")
            self.result_signal.emit(full_content)

        except Exception as e:
            self.log_signal.emit(f"[SEO] 优化失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()