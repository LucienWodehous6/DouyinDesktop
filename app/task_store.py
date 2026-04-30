"""任务存储管理 — 持久化 + 任务ID + 备注"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class TaskStore:
    """管理采集任务的持久化存储"""

    def __init__(self, base_dir: str | None = None):
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

    def create_task(self, search_term: str, notes: str = "", match_keywords: list | None = None) -> str:
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
        filepath = self.base_dir / f"{task_id}.json"
        filepath.write_text(json.dumps(result_data, ensure_ascii=False, indent=2))
        self._index[task_id]["status"] = "completed"
        self._index[task_id]["total_videos"] = result_data.get("total_videos", 0)
        self._save_index()
        return str(filepath)

    def load_result(self, task_id: str) -> dict | None:
        """加载指定任务的结果"""
        info = self._index.get(task_id)
        if not info:
            return None
        filepath = Path(info["result_file"])
        if filepath.exists():
            return json.loads(filepath.read_text())
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
