"""Skill 框架 — 动态加载和执行 AGI-Super-Team 格式的 Skills"""
from app.skills._skill_base import Skill, SkillResult
from app.skills.registry import SkillRegistry

__all__ = ["Skill", "SkillResult", "SkillRegistry"]
