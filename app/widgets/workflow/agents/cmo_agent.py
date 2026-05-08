"""CMO Agent — 发布/分发内容生成"""

import json
import os
from PyQt6.QtCore import QThread, pyqtSignal


class CMOAgentWorker(QThread):
    """CMO 发布分发 Worker"""

    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, input_file: str, output_file: str, api_key: str,
                 api_base: str, model: str, target_platform: str = "抖音"):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.target_platform = target_platform

    def run(self):
        try:
            self.log_signal.emit(f"[CMO] 读取优化后剧本...")

            with open(self.input_file, "r", encoding="utf-8") as f:
                seo_content = f.read()

            self.log_signal.emit(f"[CMO] 生成{self.target_platform}发布内容...")

            from openai import OpenAI
            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位社交媒体营销专家。根据以下已优化的抖音剧本，生成用于{self.target_platform}平台的发布内容。

已优化剧本：
{seo_content}

请以 JSON 格式输出：

{{
  "platform": "{self.target_platform}",
  "title": "发布的标题",
  "description": "发布描述，100-200字",
  "hashtags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5"],
  "best_time": "推荐发布时间",
  "cover_suggestion": "封面建议"
}}
"""

            messages = [{"role": "user", "content": prompt}]

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
            )

            content = response.choices[0].message.content or ""

            try:
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()

                result = json.loads(content)
            except:
                result = {"raw": content}

            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.log_signal.emit(f"[CMO] 发布内容生成完成")
            self.result_signal.emit(result)

        except Exception as e:
            self.log_signal.emit(f"[CMO] 生成失败: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()