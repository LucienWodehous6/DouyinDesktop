"""任务存储管理 — 持久化 + 任务ID + 备注"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class DMSentStore:
    """永久记录已发送私信的用户，避免重复发送"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.join(os.path.expanduser("~"), ".dy"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.record_path = self.base_dir / "dm_sent.json"
        self._records: dict = self._load()

    def _load(self) -> dict:
        """加载已发送记录，格式: { secId: { username, shortId, sent_at } }"""
        if self.record_path.exists():
            try:
                return json.loads(self.record_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self):
        self.record_path.write_text(json.dumps(self._records, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_sent(self, sec_id: str) -> bool:
        """检查用户是否已发送过私信"""
        return sec_id in self._records

    def mark_sent(self, sec_id: str, username: str = "", short_id: str = ""):
        """标记用户已发送私信"""
        self._records[sec_id] = {
            "username": username,
            "short_id": short_id,
            "sent_at": datetime.now().isoformat(),
        }
        self._save()

    def get_record(self, sec_id: str) -> Optional[dict]:
        return self._records.get(sec_id)


# 全局单例
_dm_sent_store: Optional[DMSentStore] = None


def get_dm_sent_store() -> DMSentStore:
    global _dm_sent_store
    if _dm_sent_store is None:
        _dm_sent_store = DMSentStore()
    return _dm_sent_store


class TaskStore:
    """管理采集任务的持久化存储"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.join(os.path.expanduser("~"), ".dy", "results"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "index.json"
        self._index: dict = self._load_index()

    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except Exception:
                pass
        return {}

    def _save_index(self):
        self.index_path.write_text(json.dumps(self._index, ensure_ascii=False, indent=2))

    def create_task(self, search_term: str, notes: str = "", match_keywords: Optional[list] = None) -> str:
        """创建新任务，返回 task_id"""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        self._index[task_id] = {
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
            "search_term": search_term,
            "match_keywords": match_keywords,
            "notes": notes,
            "result_file": str(self.base_dir / f"{task_id}.json"),
            "status": "running",
        }
        self._save_index()
        return task_id

    def save_result(self, task_id: str, result_data: dict):
        """保存采集结果"""
        if task_id not in self._index:
            return
        if not result_data.get("videos"):
            return
        filepath = self.base_dir / f"{task_id}.json"
        filepath.write_text(json.dumps(result_data, ensure_ascii=False, indent=2))
        self._index[task_id]["status"] = "completed"
        self._index[task_id]["total_videos"] = result_data.get("total_videos", 0)
        self._save_index()
        return str(filepath)

    def load_result(self, task_id: str) -> Optional[dict]:
        """加载指定任务的结果"""
        info = self._index.get(task_id)
        if not info:
            return None
        filepath = Path(info["result_file"])
        if filepath.exists() and filepath.stat().st_size > 0:
            try:
                return json.loads(filepath.read_text())
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    def list_tasks(self, limit: int = 50) -> list[dict]:
        """列出最近的任务"""
        tasks = sorted(self._index.values(), key=lambda t: t["created_at"], reverse=True)
        return tasks[:limit]

    def update_notes(self, task_id: str, notes: str):
        """更新任务备注"""
        if task_id in self._index:
            self._index[task_id]["notes"] = notes
            self._save_index()

    def delete_task(self, task_id: str):
        """删除任务及结果文件"""
        info = self._index.pop(task_id, None)
        if info:
            filepath = Path(info["result_file"])
            if filepath.exists():
                filepath.unlink()
            self._save_index()

    def get_result_path(self, task_id: str) -> str:
        """获取结果文件路径"""
        return str(self.base_dir / f"{task_id}.json")

    def save_script(self, script_text: str, prompt: str, notes: str, model: str = "") -> str:
        """保存生成的剧本"""
        script_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        script_dir = self.base_dir.parent / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        filepath = script_dir / f"{script_id}.json"
        data = {
            "script_id": script_id,
            "created_at": datetime.now().isoformat(),
            "prompt": prompt,
            "notes": notes,
            "model": model,
            "content": script_text,
        }
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._index[script_id] = {
            "task_id": script_id,
            "created_at": datetime.now().isoformat(),
            "search_term": prompt[:50] if prompt else "(剧本生成)",
            "notes": notes,
            "result_file": str(filepath),
            "status": "script",
        }
        self._save_index()
        return str(filepath)
