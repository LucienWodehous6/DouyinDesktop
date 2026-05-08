"""
dy dreamina — 即梦 (Dreamina) AIGC 生成命令（抖音生态功能）。

集成即梦官方 CLI，支持文生图、文生视频、图生视频等功能。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import click

from dy_cli.utils.output import console, error, info, print_json, success, warning
from dy_cli.utils.storage import save_generation_record, update_generation_status


DREAMINA_INSTALL_URL = "https://jimeng.jianying.com/cli"


def _check_dreamina_installed() -> bool:
    """检查 dreamina CLI 是否已安装。"""
    return shutil.which("dreamina") is not None


def _install_dreamina() -> bool:
    """自动安装 dreamina CLI（调用官方安装脚本）。"""
    info("正在下载并安装 dreamina CLI...")

    try:
        # 直接调用官方安装脚本
        if shutil.which("curl"):
            cmd = ["curl", "-fsSL", DREAMINA_INSTALL_URL]
            install_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            subprocess.run(["bash"], stdin=install_proc.stdout, check=True)
        elif shutil.which("wget"):
            cmd = ["wget", "-qO-", DREAMINA_INSTALL_URL]
            install_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            subprocess.run(["bash"], stdin=install_proc.stdout, check=True)
        else:
            error("需要 curl 或 wget 来下载 dreamina CLI")
            return False

        success("dreamina CLI 安装完成!")
        return True

    except subprocess.CalledProcessError as e:
        error(f"安装失败: {e}")
        return False
    except Exception as e:
        error(f"安装过程出错: {e}")
        return False


def _is_interactive() -> bool:
    """检查是否在交互式终端中运行。"""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _ensure_dreamina() -> None:
    """确保 dreamina CLI 已安装，未安装则自动安装。"""
    if not _check_dreamina_installed():
        warning("dreamina CLI 未安装")

        # 非交互环境（OpenClaw/CI）直接自动安装
        if not _is_interactive():
            info("非交互环境，自动安装 dreamina CLI...")
            if _install_dreamina():
                # 重新检查 PATH
                if not _check_dreamina_installed():
                    warning("安装完成但 dreamina 仍未在 PATH 中")
                    info("请重新打开终端或刷新 PATH")
                    info("或者手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
                    raise SystemExit(1)
            else:
                error("自动安装失败，请手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
                raise SystemExit(1)
            return

        # 交互环境询问用户
        if click.confirm("是否自动安装 dreamina CLI?", default=True):
            if _install_dreamina():
                # 重新检查 PATH
                if not _check_dreamina_installed():
                    warning("安装完成但 dreamina 仍未在 PATH 中")
                    info("请重新打开终端或刷新 PATH")
                    info("或者手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
                    raise SystemExit(1)
            else:
                error("自动安装失败，请手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
                raise SystemExit(1)
        else:
            error("请手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
            raise SystemExit(1)


def _run_dreamina(cmd_args: list[str], capture: bool = False) -> str | None:
    """运行 dreamina 命令。"""
    _ensure_dreamina()

    cmd = ["dreamina"] + cmd_args
    info(f"执行: {' '.join(cmd)}")

    try:
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        else:
            subprocess.run(cmd, check=True)
            return None
    except subprocess.CalledProcessError as e:
        error(f"dreamina 命令执行失败: {e}")
        if e.stderr:
            console.print(f"  stderr: {e.stderr}")
        raise SystemExit(1)


def _parse_json_output(output: str) -> Any | None:
    """尝试解析 dreamina 的 JSON 输出。"""
    try:
        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                return json.loads(line)
        return None
    except json.JSONDecodeError:
        return None


def _save_generation_task(
    task_type: str,
    prompt: str,
    output: str | None,
    metadata: dict | None = None,
) -> None:
    """保存生成任务到本地存储。"""
    if not output:
        return

    data = _parse_json_output(output)
    if not data:
        return

    submit_id = data.get("submit_id", "")
    status = data.get("gen_status", "querying")

    if submit_id:
        save_generation_record(
            task_type=task_type,
            prompt=prompt,
            submit_id=submit_id,
            status=status,
            metadata=metadata,
        )


@click.group("dreamina", help="🎨 即梦 AIGC 生成 (文生图/视频/图生视频)")
def dreamina_group():
    """即梦 (Dreamina) AIGC 生成命令组。"""
    pass


# ------------------------------------------------------------------
# 账号相关命令
# ------------------------------------------------------------------


@dreamina_group.command("login", help="登录即梦账号")
@click.option("--headless", is_flag=True, help="无头模式（适合远程/agent使用）")
def dreamina_login(headless):
    """登录即梦账号。"""
    args = ["login"]
    if headless:
        args.append("--headless")
    _run_dreamina(args)


@dreamina_group.command("logout", help="退出登录")
def dreamina_logout():
    """退出即梦账号。"""
    _run_dreamina(["logout"])


@dreamina_group.command("relogin", help="重新登录")
@click.option("--headless", is_flag=True, help="无头模式")
def dreamina_relogin(headless):
    """重新登录即梦账号。"""
    args = ["relogin"]
    if headless:
        args.append("--headless")
    _run_dreamina(args)


@dreamina_group.command("install", help="安装/更新 dreamina CLI")
def dreamina_install():
    """安装或更新 dreamina CLI。"""
    if _check_dreamina_installed():
        info("dreamina CLI 已安装，正在更新...")
    else:
        info("dreamina CLI 未安装，正在安装...")

    if _install_dreamina():
        success("安装完成！请重新打开终端或刷新 PATH 使更改生效")
    else:
        error("安装失败，请手动运行: curl -fsSL https://jimeng.jianying.com/cli | bash")
        raise SystemExit(1)


@dreamina_group.command("uninstall", help="卸载 dreamina CLI")
@click.option("--yes", "-y", is_flag=True, help="确认卸载")
def dreamina_uninstall(yes):
    """卸载 dreamina CLI。"""
    dreamina_path = shutil.which("dreamina")
    if not dreamina_path:
        info("dreamina CLI 未安装")
        return

    if not yes:
        confirm = click.confirm(f"确定要卸载 dreamina CLI 吗？\n  路径: {dreamina_path}", default=False)
        if not confirm:
            info("已取消")
            return

    try:
        os.remove(dreamina_path)
        success(f"已卸载 dreamina CLI: {dreamina_path}")

        # 也尝试删除 skill 文件
        skill_path = os.path.expanduser("~/.dreamina_cli/dreamina/SKILL.md")
        skill_dir = os.path.dirname(skill_path)
        if os.path.exists(skill_path):
            try:
                os.remove(skill_path)
                if os.path.exists(skill_dir):
                    try:
                        os.rmdir(skill_dir)
                    except Exception:
                        pass
                info("已删除 dreamina skill 文件")
            except Exception as e:
                warning(f"删除 skill 文件失败: {e}")

    except Exception as e:
        error(f"卸载失败: {e}")
        raise SystemExit(1)


@dreamina_group.command("credit", help="查看账户余额")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
def dreamina_credit(as_json):
    """查看账户余额。"""
    output = _run_dreamina(["user_credit"], capture=True)
    if output:
        if as_json:
            data = _parse_json_output(output)
            if data:
                print_json(data)
            else:
                console.print(output)
        else:
            console.print(output)


# ------------------------------------------------------------------
# 任务相关命令
# ------------------------------------------------------------------


@dreamina_group.command("tasks", help="列出任务历史")
@click.option("--gen-status", default=None, help="按状态筛选 (success/querying/fail)")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
def dreamina_list_tasks(gen_status, as_json):
    """列出已保存的任务。"""
    args = ["list_task"]
    if gen_status:
        args.append(f"--gen_status={gen_status}")
    output = _run_dreamina(args, capture=True)
    if output:
        if as_json:
            data = _parse_json_output(output)
            if data:
                print_json(data)
            else:
                console.print(output)
        else:
            console.print(output)


@dreamina_group.command("query", help="查询异步任务结果")
@click.argument("submit_id")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
def dreamina_query(submit_id, as_json):
    """查询异步任务结果。"""
    output = _run_dreamina(["query_result", f"--submit_id={submit_id}"], capture=True)
    if output:
        if as_json:
            data = _parse_json_output(output)
            if data:
                print_json(data)
            else:
                console.print(output)
        else:
            console.print(output)


# ------------------------------------------------------------------
# 生成命令
# ------------------------------------------------------------------


@dreamina_group.command("text2image", help="文生图")
@click.option("--prompt", "-p", required=True, help="提示词")
@click.option("--ratio", default=None, help="比例 (1:1, 16:9, 9:16 等)")
@click.option("--resolution", default=None, help="分辨率 (1k, 2k, 4k)")
@click.option("--model", default=None, help="模型版本 (3.0, 4.0, 4.5, 5.0, lab)")
@click.option("--poll", type=int, default=0, help="轮询等待秒数")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
@click.option("--no-save", is_flag=True, help="不保存到历史记录")
def dreamina_text2image(prompt, ratio, resolution, model, poll, as_json, no_save):
    """文本生成图片。"""
    args = ["text2image", f"--prompt={prompt}"]
    if ratio:
        args.append(f"--ratio={ratio}")
    if resolution:
        args.append(f"--resolution_type={resolution}")
    if model:
        args.append(f"--model_version={model}")
    if poll:
        args.append(f"--poll={poll}")

    output = _run_dreamina(args, capture=as_json or not no_save)
    if output and as_json:
        data = _parse_json_output(output)
        if data:
            print_json(data)
        else:
            console.print(output)

    if output and not no_save:
        _save_generation_task(
            "text2image",
            prompt,
            output,
            {"ratio": ratio, "resolution": resolution, "model": model},
        )


@dreamina_group.command("text2video", help="文生视频")
@click.option("--prompt", "-p", required=True, help="提示词")
@click.option("--duration", "-d", type=int, default=5, help="视频时长 (秒)")
@click.option("--ratio", default=None, help="比例 (1:1, 16:9, 9:16 等)")
@click.option("--resolution", default=None, help="分辨率 (720p)")
@click.option("--model", default=None, help="模型版本 (seedance2.0, seedance2.0fast)")
@click.option("--poll", type=int, default=0, help="轮询等待秒数")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
def dreamina_text2video(prompt, duration, ratio, resolution, model, poll, as_json):
    """文本生成视频。"""
    args = ["text2video", f"--prompt={prompt}", f"--duration={duration}"]
    if ratio:
        args.append(f"--ratio={ratio}")
    if resolution:
        args.append(f"--video_resolution={resolution}")
    if model:
        args.append(f"--model_version={model}")
    if poll:
        args.append(f"--poll={poll}")

    output = _run_dreamina(args, capture=as_json)
    if output and as_json:
        data = _parse_json_output(output)
        if data:
            print_json(data)
        else:
            console.print(output)


@dreamina_group.command("image2video", help="图生视频")
@click.option("--image", "-i", required=True, help="输入图片路径")
@click.option("--prompt", "-p", default="", help="提示词")
@click.option("--duration", "-d", type=int, default=None, help="视频时长 (秒)")
@click.option("--resolution", default=None, help="分辨率 (720p, 1080p)")
@click.option("--model", default=None, help="模型版本 (3.0, 3.5pro, seedance2.0)")
@click.option("--poll", type=int, default=0, help="轮询等待秒数")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
def dreamina_image2video(image, prompt, duration, resolution, model, poll, as_json):
    """单张图片生成视频。"""
    args = ["image2video", f"--image={image}"]
    if prompt:
        args.append(f"--prompt={prompt}")
    if duration is not None:
        args.append(f"--duration={duration}")
    if resolution:
        args.append(f"--video_resolution={resolution}")
    if model:
        args.append(f"--model_version={model}")
    if poll:
        args.append(f"--poll={poll}")

    output = _run_dreamina(args, capture=as_json)
    if output and as_json:
        data = _parse_json_output(output)
        if data:
            print_json(data)
        else:
            console.print(output)


@dreamina_group.command("multiframe2video", help="多帧图生视频")
@click.option("--help", "-h", is_flag=True, help="查看完整帮助")
def dreamina_multiframe2video(help):
    """多张图片生成连贯视频故事。"""
    if help:
        _run_dreamina(["multiframe2video", "-h"])
    else:
        info("使用 dreamina multiframe2video -h 查看完整帮助和所有选项")
        warning("该命令支持多图输入，请查看完整帮助后使用")


@dreamina_group.command("multimodal2video", help="多模态生视频 (旗舰模式)")
@click.option("--help", "-h", is_flag=True, help="查看完整帮助")
def dreamina_multimodal2video(help):
    """多模态生成视频 (支持图片/视频/音频参考，Seedance 2.0)。"""
    if help:
        _run_dreamina(["multimodal2video", "-h"])
    else:
        info("使用 dreamina multimodal2video -h 查看完整帮助和所有选项")
        warning("该命令为旗舰模式，支持多种参考输入，请查看完整帮助后使用")


@dreamina_group.command("image2image", help="图生图")
@click.option("--help", "-h", is_flag=True, help="查看完整帮助")
def dreamina_image2image(help):
    """图片生成图片。"""
    if help:
        _run_dreamina(["image2image", "-h"])
    else:
        info("使用 dreamina image2image -h 查看完整帮助和所有选项")


@dreamina_group.command("upscale", help="图片超分")
@click.option("--help", "-h", is_flag=True, help="查看完整帮助")
def dreamina_upscale(help):
    """图片超分辨率。"""
    if help:
        _run_dreamina(["image_upscale", "-h"])
    else:
        info("使用 dreamina upscale -h 查看完整帮助和所有选项")


@dreamina_group.command("frames2video", help="首尾帧生视频")
@click.option("--help", "-h", is_flag=True, help="查看完整帮助")
def dreamina_frames2video(help):
    """通过首尾帧生成视频。"""
    if help:
        _run_dreamina(["frames2video", "-h"])
    else:
        info("使用 dreamina frames2video -h 查看完整帮助和所有选项")


# ------------------------------------------------------------------
# 直通命令 (直接透传)
# ------------------------------------------------------------------


@dreamina_group.command("raw", context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def dreamina_raw(args):
    """
    直接透传参数给 dreamina CLI。

    示例:
      dy dreamina raw -- text2image --prompt=\"a cat\"
      dy dreamina raw -- user_credit
    """
    _run_dreamina(list(args))
