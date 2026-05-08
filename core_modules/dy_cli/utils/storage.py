"""
本地文件存储工具 — JSON/SQLite 存储。

用于存储搜索结果、任务历史、生成记录等。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional


@dataclass
class SearchRecord:
    """搜索记录。"""
    id: int | None = None
    keyword: str = ""
    result_count: int = 0
    created_at: str = ""
    data: str = ""  # JSON string


@dataclass
class GenerationRecord:
    """AIGC 生成记录。"""
    id: int | None = None
    task_type: str = ""  # text2image, text2video, image2video
    prompt: str = ""
    submit_id: str = ""
    status: str = ""  # querying, success, fail
    created_at: str = ""
    result_url: str = ""
    metadata: str = ""  # JSON string


def get_storage_dir() -> Path:
    """获取存储目录。"""
    storage_dir = Path.home() / ".dy" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_db_path() -> Path:
    """获取 SQLite 数据库路径。"""
    return get_storage_dir() / "dy_cli.db"


def init_db() -> None:
    """初始化数据库表。"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 搜索记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            result_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            data TEXT
        )
    """)

    # 生成记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            prompt TEXT,
            submit_id TEXT,
            status TEXT DEFAULT 'querying',
            created_at TEXT NOT NULL,
            result_url TEXT,
            metadata TEXT
        )
    """)

    # 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_created ON search_records(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_generation_submit ON generation_records(submit_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_generation_created ON generation_records(created_at)
    """)

    conn.commit()
    conn.close()


def get_timestamp() -> str:
    """获取当前时间戳。"""
    return datetime.now().isoformat()


# ------------------------------------------------------------------
# JSON 存储
# ------------------------------------------------------------------


def save_json(filename: str, data: Any, subdir: str | None = None) -> Path:
    """保存数据为 JSON 文件。"""
    storage_dir = get_storage_dir()
    if subdir:
        storage_dir = storage_dir / subdir
        storage_dir.mkdir(parents=True, exist_ok=True)

    filepath = storage_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_json(filename: str, subdir: str | None = None, default: Any = None) -> Any:
    """加载 JSON 文件。"""
    storage_dir = get_storage_dir()
    if subdir:
        storage_dir = storage_dir / subdir

    filepath = storage_dir / filename
    if not filepath.exists():
        return default

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# SQLite 存储 - 搜索记录
# ------------------------------------------------------------------


def save_search_record(
    keyword: str,
    result_count: int = 0,
    data: Any = None,
) -> int:
    """保存搜索记录。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    data_json = json.dumps(data, ensure_ascii=False) if data else ""

    cursor.execute("""
        INSERT INTO search_records (keyword, result_count, created_at, data)
        VALUES (?, ?, ?, ?)
    """, (keyword, result_count, get_timestamp(), data_json))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return record_id


def get_search_records(limit: int = 50, keyword: str | None = None) -> list[SearchRecord]:
    """获取搜索记录。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if keyword:
        cursor.execute("""
            SELECT id, keyword, result_count, created_at, data
            FROM search_records
            WHERE keyword LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f"%{keyword}%", limit))
    else:
        cursor.execute("""
            SELECT id, keyword, result_count, created_at, data
            FROM search_records
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

    records = []
    for row in cursor.fetchall():
        records.append(SearchRecord(
            id=row["id"],
            keyword=row["keyword"],
            result_count=row["result_count"],
            created_at=row["created_at"],
            data=row["data"],
        ))

    conn.close()
    return records


# ------------------------------------------------------------------
# SQLite 存储 - 生成记录
# ------------------------------------------------------------------


def save_generation_record(
    task_type: str,
    prompt: str = "",
    submit_id: str = "",
    status: str = "querying",
    result_url: str = "",
    metadata: Any = None,
) -> int:
    """保存生成记录。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else ""

    cursor.execute("""
        INSERT INTO generation_records
        (task_type, prompt, submit_id, status, created_at, result_url, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_type, prompt, submit_id, status, get_timestamp(), result_url, metadata_json))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return record_id


def update_generation_status(submit_id: str, status: str, result_url: str = "") -> bool:
    """更新生成任务状态。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE generation_records
        SET status = ?, result_url = ?
        WHERE submit_id = ?
    """, (status, result_url, submit_id))

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return updated


def get_generation_records(
    limit: int = 50,
    task_type: str | None = None,
    status: str | None = None,
) -> list[GenerationRecord]:
    """获取生成记录。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT id, task_type, prompt, submit_id, status, created_at, result_url, metadata
        FROM generation_records
    """
    params = []
    conditions = []

    if task_type:
        conditions.append("task_type = ?")
        params.append(task_type)
    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)

    records = []
    for row in cursor.fetchall():
        records.append(GenerationRecord(
            id=row["id"],
            task_type=row["task_type"],
            prompt=row["prompt"],
            submit_id=row["submit_id"],
            status=row["status"],
            created_at=row["created_at"],
            result_url=row["result_url"],
            metadata=row["metadata"],
        ))

    conn.close()
    return records


def get_generation_by_submit_id(submit_id: str) -> GenerationRecord | None:
    """通过 submit_id 获取生成记录。"""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, task_type, prompt, submit_id, status, created_at, result_url, metadata
        FROM generation_records
        WHERE submit_id = ?
    """, (submit_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return GenerationRecord(
            id=row["id"],
            task_type=row["task_type"],
            prompt=row["prompt"],
            submit_id=row["submit_id"],
            status=row["status"],
            created_at=row["created_at"],
            result_url=row["result_url"],
            metadata=row["metadata"],
        )
    return None


# ------------------------------------------------------------------
# 导出功能
# ------------------------------------------------------------------


def export_records_to_json(records: list[Any], filepath: str) -> None:
    """导出记录为 JSON 文件。"""
    data = [asdict(r) for r in records]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_records_to_csv(records: list[Any], filepath: str) -> None:
    """导出记录为 CSV 文件。"""
    if not records:
        return

    import csv

    first = asdict(records[0])
    fieldnames = list(first.keys())

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
