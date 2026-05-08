"""Skill 加载器 — 扫描 app/skills/skills/ 目录，解析 SKILL.md"""

import os
import re
import yaml
from pathlib import Path
from typing import Iterator


SKILLS_DIR = Path(__file__).parent / "skills"


def parse_skill_md(content: str) -> dict:
    """解析 SKILL.md 内容，返回 frontmatter + body"""
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        return {"metadata": {}, "body": content}

    frontmatter_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end():]
    metadata = yaml.safe_load(frontmatter_text) or {}
    return {"metadata": metadata, "body": body}


def scan_skills() -> Iterator[dict]:
    """扫描 skills 目录，产生每个 skill 的信息 dict"""
    skills_path = SKILLS_DIR
    if not skills_path.exists():
        return

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir():
            continue
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            continue

        content = md_path.read_text(encoding="utf-8")
        parsed = parse_skill_md(content)
        yield {
            "id": skill_dir.name,
            "path": str(md_path),
            **parsed,
        }


class SkillLoader:
    """Skill 加载器，提供 scan() 和 get_by_id() 方法"""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        for skill_info in scan_skills():
            self._cache[skill_info["id"]] = skill_info

    def scan(self) -> list[dict]:
        """返回所有加载的 skill 信息列表"""
        return list(self._cache.values())

    def get_by_id(self, skill_id: str) -> dict | None:
        """根据 ID 获取 skill 信息"""
        return self._cache.get(skill_id)