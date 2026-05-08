"""LLM 服务 - 多大语言模型支持"""

import json
import os
from typing import Optional


class LLMService:
    """支持 OpenAI/DeepSeek/Moonshot/Azure/Gemini 等多种 LLM"""

    SUPPORTED_PROVIDERS = {
        "openai": ["openai", "deepseek", "siliconflow"],
        "anthropic": ["claude"],
        "google": ["gemini", "generativeai"],
        "moonshot": ["moonshot", "kimi"],
        "azure": ["azure"],
        "dashscope": ["qwen", "tongyi"],
    }

    def __init__(self, api_base: str, api_key: str, model: str):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            except Exception as e:
                raise RuntimeError(f"LLM 客户端初始化失败: {e}")
        return self._client

    def generate_script(self, topic: str, max_words: int = 500) -> str:
        """
        根据主题生成视频文案

        Args:
            topic: 视频主题/关键词
            max_words: 最大字数

        Returns:
            生成的文案内容
        """
        prompt = f"""你是一个专业的视频文案撰写师。请根据以下主题，撰写一段{max_words}字以内的视频口播文案。

主题：{topic}

要求：
1. 语言自然流畅，适合口语化表达
2. 结构清晰，有开头、过程、结尾
3. 可以适当加入悬念或引导性语句
4. 不要包含任何特殊格式标记，直接输出纯文本

文案："""

        return self._call_llm(prompt)

    def generate_script_with_keywords(self, topic: str, keywords: list, max_words: int = 500) -> str:
        """
        根据主题和关键词生成文案

        Args:
            topic: 视频主题
            keywords: 必须包含的关键词列表
            max_words: 最大字数

        Returns:
            生成的文案内容
        """
        kw_str = "、".join(keywords)
        prompt = f"""你是一个专业的视频文案撰写师。请根据以下主题，撰写一段{max_words}字以内的视频口播文案。

主题：{topic}
必须包含的关键词：{kw_str}

要求：
1. 语言自然流畅，适合口语化表达
2. 自然融入所有关键词
3. 结构清晰，有开头、过程、结尾
4. 不要包含任何特殊格式标记，直接输出纯文本

文案："""

        return self._call_llm(prompt)

    def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """调用 LLM 生成内容"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的视频文案撰写师，擅长创作吸引人的短视频口播文案。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                stream=False
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}")

    def generate_script_stream(self, topic: str, max_words: int = 500):
        """
        流式生成文案

        Args:
            topic: 视频主题
            max_words: 最大字数

        Yields:
            生成的内容片段
        """
        prompt = f"""你是一个专业的视频文案撰写师。请根据以下主题，撰写一段{max_words}字以内的视频口播文案。

主题：{topic}

要求：
1. 语言自然流畅，适合口语化表达
2. 结构清晰，有开头、过程、结尾
3. 不要包含任何特殊格式标记，直接输出纯文本

文案："""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的视频文案撰写师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"LLM 流式调用失败: {e}")