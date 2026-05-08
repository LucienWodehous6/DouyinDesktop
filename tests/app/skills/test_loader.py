"""Tests for SkillLoader"""

import pytest
from app.skills.skill_loader import parse_skill_md


def test_parse_skill_md_with_frontmatter():
    content = """---
name: test-skill
description: "A test skill"
metadata:
  version: "1.0.0"
---

# Test Skill
body content here
"""
    result = parse_skill_md(content)
    assert result["metadata"]["name"] == "test-skill"
    assert result["metadata"]["version"] == "1.0.0"
    assert "body content here" in result["body"]


def test_parse_skill_md_without_frontmatter():
    content = "# No frontmatter\nsome content"
    result = parse_skill_md(content)
    assert result["metadata"] == {}
    assert "No frontmatter" in result["body"]