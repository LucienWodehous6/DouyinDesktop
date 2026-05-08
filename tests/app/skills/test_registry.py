"""Tests for SkillRegistry"""

import pytest
from app.skills.registry import SkillRegistry


def test_singleton():
    r1 = SkillRegistry.get_instance()
    r2 = SkillRegistry.get_instance()
    assert r1 is r2


def test_list_skills_returns_list():
    r = SkillRegistry.get_instance()
    skills = r.list_skills()
    assert isinstance(skills, list)