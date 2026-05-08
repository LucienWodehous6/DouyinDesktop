"""Skill 基类和结果数据类"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class Skill(ABC):
    """Skill 抽象基类"""

    name: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)

    @abstractmethod
    def execute(self, params: dict, context: dict) -> SkillResult:
        """执行 Skill，返回结果"""
        pass

    def validate_input(self, params: dict) -> bool:
        """验证输入参数，返回 True/False"""
        return True

    def get_input_schema(self) -> dict | None:
        """返回输入参数 JSON Schema，用于 UI 生成表单"""
        return None
