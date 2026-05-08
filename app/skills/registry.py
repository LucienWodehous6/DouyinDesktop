"""Skill 注册表 — 全局单例，维护 name -> Skill 实例映射"""

from typing import Protocol
from app.skills._skill_base import Skill
from app.skills.skill_loader import SkillLoader


class SkillRegistry:
    """全局 Skill 注册表（单例）"""

    _instance: "SkillRegistry | None" = None

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._loader = SkillLoader()
        self._load_metadata()

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_metadata(self):
        """仅加载 metadata，不实例化 Skill 类（等待按需实例化）"""
        for info in self._loader.scan():
            self._skills[info["id"]] = info  # 存的是 metadata dict

    def get_skill_metadata(self, skill_id: str) -> dict | None:
        """获取 skill 元信息"""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[dict]:
        """列出所有 skill 的元信息"""
        return list(self._skills.values())

    def register(self, skill_id: str, skill_instance: Skill):
        """手动注册一个 Skill 实例"""
        self._skills[skill_id] = skill_instance

    def get(self, skill_id: str) -> Skill | None:
        """获取 skill 实例（目前返回 metadata dict，未来支持 Skill 实例）"""
        return self._skills.get(skill_id)