"""
dy account — 多账号管理命令。
"""
from __future__ import annotations

import os

import click
from rich import box
from rich.table import Table

from dy_cli.engines.playwright_client import PlaywrightClient
from dy_cli.utils import config
from dy_cli.utils.output import console, error, info, success


@click.group("account", help="多账号管理")
def account_group():
    pass


@account_group.command("list", help="列出所有账号")
def list_accounts():
    """列出已配置的账号。"""
    cookies_dir = config.COOKIES_DIR
    default_account = config.load_config()["default"]["account"]

    if not os.path.isdir(cookies_dir):
        info("暂无配置账号")
        info("使用 [bold]dy account add <name>[/] 添加账号")
        return

    files = [f for f in os.listdir(cookies_dir) if f.endswith(".json")]
    if not files:
        info("暂无配置账号")
        return

    table = Table(title="📱 账号列表", box=box.ROUNDED)
    table.add_column("名称", style="bold")
    table.add_column("Cookie 文件")
    table.add_column("状态")
    table.add_column("默认", justify="center")

    for f in sorted(files):
        name = f.replace(".json", "")
        cookie_path = os.path.join(cookies_dir, f)
        size = os.path.getsize(cookie_path)
        status_text = "✅ 有效" if size > 100 else "⚠️ 空"
        is_default = "⭐" if name == default_account else ""
        table.add_row(name, cookie_path, status_text, is_default)

    console.print(table)


@account_group.command("add", help="添加新账号并登录")
@click.argument("name")
def add_account(name):
    """添加新账号并打开浏览器登录。"""
    cookie_file = config.get_cookie_file(name)
    if os.path.isfile(cookie_file):
        if not click.confirm(f"账号 '{name}' 已存在，是否重新登录?", default=False):
            return

    info(f"正在为账号 '{name}' 打开登录页面...")
    client = PlaywrightClient(account=name, headless=False)
    try:
        ok = client.login()
        if ok:
            success(f"账号 '{name}' 已添加并登录")
        else:
            error("登录失败")
    except Exception as e:
        error(f"登录失败: {e}")
        raise SystemExit(1)


@account_group.command("remove", help="删除账号")
@click.argument("name")
@click.confirmation_option(prompt="确认删除此账号?")
def remove_account(name):
    """删除账号 (Cookie 文件)。"""
    cookie_file = config.get_cookie_file(name)
    if os.path.isfile(cookie_file):
        os.remove(cookie_file)
        success(f"账号 '{name}' 已删除")
    else:
        error(f"账号 '{name}' 不存在")
        raise SystemExit(1)


@account_group.command("default", help="设置默认账号")
@click.argument("name")
def set_default(name):
    """设置默认账号。"""
    cookie_file = config.get_cookie_file(name)
    if not os.path.isfile(cookie_file):
        warning_text = f"账号 '{name}' 尚未登录"
        info(warning_text)
        if not click.confirm("仍要设为默认?", default=False):
            return

    config.set_value("default.account", name)
    success(f"默认账号已设为: {name}")
