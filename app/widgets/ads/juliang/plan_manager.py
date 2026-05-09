"""巨量千川计划管理器"""
import json
import os
from datetime import datetime


class PlanManager:
    """管理巨量千川广告计划"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".dy", "ads", "juliang")
        os.makedirs(self.storage_path, exist_ok=True)
        self.registry_file = os.path.join(self.storage_path, "plan_registry.json")

    def _load_registry(self) -> dict:
        if os.path.exists(self.registry_file):
            with open(self.registry_file, encoding="utf-8") as f:
                return json.load(f)
        return {"version": 1, "entries": [], "updatedAt": ""}

    def _save_registry(self, registry: dict):
        registry["updatedAt"] = datetime.now().isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)

    def save_plan(self, plan: dict):
        """保存计划到本地"""
        registry = self._load_registry()
        plan_id = plan.get("plan_id") or plan.get("planName", "")
        # 检查是否已存在
        for i, entry in enumerate(registry["entries"]):
            if entry.get("plan_id") == plan_id:
                registry["entries"][i] = {**entry, **plan}
                self._save_registry(registry)
                return
        registry["entries"].append(plan)
        self._save_registry(registry)

    def load_plans(self) -> list:
        """加载所有计划"""
        return self._load_registry().get("entries", [])

    def update_plan_status(self, plan_id: str, status: str):
        """更新计划状态"""
        registry = self._load_registry()
        for entry in registry["entries"]:
            if entry.get("plan_id") == plan_id:
                entry["status"] = status
                break
        self._save_registry(registry)

    def check_duplicate(self, behavior: str, interest: str) -> bool:
        """检查计划是否重复（行为+兴趣组合）"""
        registry = self._load_registry()
        combo_key = f"{behavior}::{interest}"
        for entry in registry.get("entries", []):
            entry_key = f"{entry.get('behavior', '')}::{entry.get('interest', '')}"
            if entry_key == combo_key and entry.get("status") != "deleted":
                return True
        return False

    def delete_plan(self, plan_id: str):
        """标记计划为已删除"""
        self.update_plan_status(plan_id, "deleted")
