"""抖音 DO+ 计划管理器"""
import json
import os
from datetime import datetime


class DouyinPlusPlanManager:
    """管理抖音 DO+ 内容推广计划"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".dy", "ads", "douyin_plus")
        os.makedirs(self.storage_path, exist_ok=True)
        self.registry_file = os.path.join(self.storage_path, "campaign_registry.json")

    def _load_registry(self) -> dict:
        if os.path.exists(self.registry_file):
            with open(self.registry_file, encoding="utf-8") as f:
                return json.load(f)
        return {"version": 1, "entries": [], "updatedAt": ""}

    def _save_registry(self, registry: dict):
        registry["updatedAt"] = datetime.now().isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)

    def save_campaign(self, campaign: dict):
        """保存推广到本地"""
        registry = self._load_registry()
        campaign_id = campaign.get("campaign_id") or campaign.get("video_id", "")
        for i, entry in enumerate(registry["entries"]):
            if entry.get("campaign_id") == campaign_id:
                registry["entries"][i] = {**entry, **campaign}
                self._save_registry(registry)
                return
        registry["entries"].append(campaign)
        self._save_registry(registry)

    def load_campaigns(self) -> list:
        """加载所有推广"""
        return self._load_registry().get("entries", [])

    def update_campaign_status(self, campaign_id: str, status: str):
        """更新推广状态"""
        registry = self._load_registry()
        for entry in registry["entries"]:
            if entry.get("campaign_id") == campaign_id:
                entry["status"] = status
                break
        self._save_registry(registry)

    def delete_campaign(self, campaign_id: str):
        """标记推广为已删除"""
        self.update_campaign_status(campaign_id, "deleted")
