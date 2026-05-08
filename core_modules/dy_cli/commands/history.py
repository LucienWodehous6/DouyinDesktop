"""
dy history — 历史记录命令。

查看搜索历史、生成历史等。
"""
from __future__ import annotations

import json
import os

import click

from dy_cli.utils.output import console, error, info, print_json, success, warning
from dy_cli.utils.storage import (
    GenerationRecord,
    SearchRecord,
    export_records_to_csv,
    export_records_to_json,
    get_generation_records,
    get_search_records,
    save_generation_record,
    save_search_record,
    update_generation_status,
)


@click.group("history", help="📜 历史记录管理")
def history_group():
    """历史记录命令组。"""
    pass


# ------------------------------------------------------------------
# 搜索历史
# ------------------------------------------------------------------


@history_group.command("search", help="查看搜索历史")
@click.option("--keyword", "-k", default=None, help="按关键词筛选")
@click.option("--limit", "-n", type=int, default=20, help="显示条数")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
@click.option("-o", "--output", default=None, help="导出到文件 (.json/.csv)")
def history_search(keyword, limit, as_json, output):
    """查看搜索历史记录。"""
    records = get_search_records(limit=limit, keyword=keyword)

    if not records:
        info("没有搜索历史记录")
        return

    if as_json:
        from dataclasses import asdict
        data = [asdict(r) for r in records]
        print_json(data)
        return

    if output:
        from dataclasses import asdict
        if output.endswith(".json"):
            export_records_to_json(records, output)
        elif output.endswith(".csv"):
            export_records_to_csv(records, output)
        else:
            error("不支持的导出格式，请使用 .json 或 .csv")
            raise SystemExit(1)
        success(f"已导出到: {output}")
        return

    _display_search_records(records)


def _display_search_records(records: list[SearchRecord]):
    """显示搜索记录。"""
    from rich.table import Table

    table = Table(title="🔍 搜索历史")
    table.add_column("ID", style="cyan")
    table.add_column("关键词", style="green")
    table.add_column("结果数", style="yellow")
    table.add_column("时间", style="dim")

    for r in records:
        table.add_row(
            str(r.id) if r.id else "",
            r.keyword[:30] + "..." if len(r.keyword) else "",
            str(r.result_count),
            r.created_at[:19] if r.created_at else "",
        )

    console.print(table)


# ------------------------------------------------------------------
# 生成历史
# ------------------------------------------------------------------


@history_group.command("gen", help="查看生成历史")
@click.option("--task-type", "-t", default=None, help="按任务类型筛选 (text2image/text2video/image2video)")
@click.option("--status", "-s", default=None, help="按状态筛选 (success/querying/fail)")
@click.option("--limit", "-n", type=int, default=20, help="显示条数")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
@click.option("-o", "--output", default=None, help="导出到文件 (.json/.csv)")
def history_gen(task_type, status, limit, as_json, output):
    """查看 AIGC 生成历史记录。"""
    records = get_generation_records(limit=limit, task_type=task_type, status=status)

    if not records:
        info("没有生成历史记录")
        return

    if as_json:
        from dataclasses import asdict
        data = [asdict(r) for r in records]
        print_json(data)
        return

    if output:
        from dataclasses import asdict
        if output.endswith(".json"):
            export_records_to_json(records, output)
        elif output.endswith(".csv"):
            export_records_to_csv(records, output)
        else:
            error("不支持的导出格式，请使用 .json 或 .csv")
            raise SystemExit(1)
        success(f"已导出到: {output}")
        return

    _display_generation_records(records)


def _display_generation_records(records: list[GenerationRecord]):
    """显示生成记录。"""
    from rich.table import Table

    table = Table(title="🎨 生成历史")
    table.add_column("ID", style="cyan")
    table.add_column("类型", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("提示词", style="dim", max_width=30)
    table.add_column("时间", style="dim")

    for r in records:
        status_style = "green" if r.status == "success" else "yellow" if r.status == "querying" else "red"
        status_text = f"[{status_style}]{r.status}[/{status_style}]"
        table.add_row(
            str(r.id) if r.id else "",
            r.task_type,
            status_text,
            r.prompt[:30] + "..." if len(r.prompt) > 30 else r.prompt,
            r.created_at[:19] if r.created_at else "",
        )

    console.print(table)


# ------------------------------------------------------------------
# 清空历史
# ------------------------------------------------------------------


@history_group.command("clear", help="清空历史记录")
@click.option("--search", is_flag=True, help="只清空搜索历史")
@click.option("--gen", is_flag=True, help="只清空生成历史")
@click.option("--yes", "-y", is_flag=True, help="确认清空")
def history_clear(search, gen, yes):
    """清空历史记录。"""
    from dy_cli.utils.storage import get_db_path, init_db
    import sqlite3

    if not search and not gen:
        error("请指定 --search 或 --gen")
        raise SystemExit(1)

    if not yes:
        confirm = click.confirm("确定要清空历史记录吗？", default=False)
        if not confirm:
            info("已取消")
            return

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if search:
        cursor.execute("DELETE FROM search_records")
        info(f"已清空搜索历史")

    if gen:
        cursor.execute("DELETE FROM generation_records")
        info(f"已清空生成历史")

    conn.commit()
    conn.close()

    success("操作完成")
