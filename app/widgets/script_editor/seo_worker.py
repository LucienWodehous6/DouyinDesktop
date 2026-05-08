"""SEO 优化后台线程 — 对已生成的剧本进行标题和标签优化"""

from PyQt6.QtCore import QThread, pyqtSignal


class SEOOptimizeWorker(QThread):
    """SEO 优化后台线程 — 对已生成的剧本进行标题和标签优化"""

    chunk_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, script_text: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.script_text = script_text
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        try:
            from openai import OpenAI

            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{self.script_text}

任务要求：
1. 优化标题（≤20字，吸睛，包含关键词）
2. 生成 2 个变体标题（信任型、紧迫型）
3. 推荐 5 个标签（以 # 开头，符合抖音平台规范）
4. 生成视频描述（≤100字）
5. 优化剧本正文（保留原有结构，只优化标题和话术表达）

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
                max_tokens=16384,
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
                    self.chunk_signal.emit(text)

            self.result_signal.emit(full_content)

        except Exception as e:
            self.error_signal.emit(str(e))
