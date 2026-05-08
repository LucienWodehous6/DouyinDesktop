"""
dy prompt — 提示词优化命令（配合 OpenClaw 使用）。

通过 LLM 优化视频/图片生成的提示词。
"""
from __future__ import annotations

import json
import os
from typing import Any

import click

from dy_cli.utils.output import console, error, info, print_json, success, warning


PROMPT_OPTIMIZE_SYSTEM_PROMPT = """你是一个专业的 AIGC 提示词优化专家。你的任务是优化用户的提示词，使其更适合用于 AI 图像/视频生成。

优化原则：
1. **保持原意**：不要改变用户想要表达的核心内容
2. **增加细节**：添加场景、光照、风格、构图等细节
3. **专业术语**：使用摄影/电影专业术语（如： cinematic lighting, shallow depth of field, 8K, ultra detailed 等）
4. **风格指定**：如果用户没有指定风格，可以建议 1-2 种合适的风格
5. **多语言支持**：优化后的提示词使用英文（因为多数 AIGC 模型对英文支持更好）

输出格式：
只返回 JSON 格式，包含以下字段：
- original: 用户原始提示词
- optimized: 优化后的英文提示词
- style: 建议的风格（可选）
- notes: 优化说明（可选）

示例：
输入："一只猫"
输出：
{
  "original": "一只猫",
  "optimized": "A cute ginger cat sitting on a windowsill, golden hour lighting, shallow depth of field, 8K, ultra detailed, photorealistic, cozy atmosphere",
  "style": "Photorealistic",
  "notes": "添加了场景、光线和细节描述"
}
"""


@click.group("prompt", help="💡 提示词优化 (用于 AIGC 生成)")
def prompt_group():
    """提示词优化命令组。"""
    pass


@prompt_group.command("optimize", help="优化提示词")
@click.argument("prompt_text", required=True)
@click.option("--style", "-s", default=None, help="指定风格 (如: photorealistic, anime, cinematic)")
@click.option("--language", "-l", type=click.Choice(["en", "zh"]), default="en", help="输出语言 (默认英文)")
@click.option("--json-output", "as_json", is_flag=True, help="输出 JSON")
@click.option("--auto-apply", "-a", is_flag=True, help="自动应用到 dreamina 命令")
def prompt_optimize(prompt_text, style, language, as_json, auto_apply):
    """
    优化 AIGC 提示词。

    注意：此命令设计为在 OpenClaw 中使用，由 OpenClaw 提供 LLM 能力。
    如果在终端中直接运行，会显示优化建议框架。
    """
    info("提示词优化模式")
    console.print()

    result = {
        "original": prompt_text,
        "optimized": None,
        "style": style,
        "notes": "请在 OpenClaw 中运行以获得完整的 LLM 优化能力",
    }

    # 基础优化建议（不依赖 LLM）
    if not style:
        if "猫" in prompt_text or "cat" in prompt_text.lower():
            result["style"] = "Photorealistic"
        elif "动漫" in prompt_text or "anime" in prompt_text.lower():
            result["style"] = "Anime style"
        elif "风景" in prompt_text or "landscape" in prompt_text.lower():
            result["style"] = "Cinematic"

    # 生成简单的英文提示词
    result["optimized"] = _basic_english_translation(prompt_text)

    if as_json:
        print_json(result)
    else:
        _display_optimization_result(result)

    if auto_apply:
        console.print()
        info("优化后的提示词:")
        console.print(f"  [cyan]{result['optimized']}[/]")
        console.print()
        info("使用方式:")
        console.print(f"  dy dreamina text2image -p \"{result['optimized']}\"")


def _basic_english_translation(text: str) -> str:
    """基础的英文关键词替换（仅作为备用）。"""
    translations = {
        "猫": "cat",
        "狗": "dog",
        "风景": "landscape",
        "城市": "city",
        "森林": "forest",
        "山": "mountain",
        "海": "ocean",
        "天空": "sky",
        "女孩": "girl",
        "男孩": "boy",
        "人物": "person",
        "汽车": "car",
        "建筑": "building",
        "美丽": "beautiful",
        "可爱": "cute",
        "帅气": "handsome",
        "现代": "modern",
        "古典": "classic",
        "未来": "futuristic",
        "赛博朋克": "cyberpunk",
        "动漫": "anime style",
        "真实": "photorealistic",
        "电影": "cinematic",
    }

    result = text
    for zh, en in translations.items():
        result = result.replace(zh, en)

    # 如果检测到是中文但没替换完，添加通用建议
    if any("\u4e00" <= c <= "\u9fff" for c in result):
        result += " (Please use OpenClaw for full LLM optimization)"

    return result


def _display_optimization_result(result: dict[str, Any]):
    """显示优化结果。"""
    from rich.panel import Panel
    from rich.table import Table

    console.print(Panel(
        f"[bold]原始提示词[/]: {result['original']}\n\n"
        f"[bold green]优化后提示词[/]: {result['optimized']}\n\n"
        f"[bold]建议风格[/]: {result.get('style', 'N/A')}\n"
        f"[dim]{result.get('notes', '')}[/]",
        title="💡 提示词优化结果",
        border_style="cyan",
    ))

    console.print()
    info("💡 提示：在 OpenClaw 中运行可获得更好的 LLM 优化效果")


@prompt_group.command("templates", help="显示提示词模板")
def prompt_templates():
    """显示常用的提示词模板。"""
    from rich.panel import Panel
    from rich.table import Table

    console.print()
    console.print(Panel(
        "[bold]通用格式[/]:\n"
        "  [subject], [environment/setting], [lighting], [style], [camera shot], [quality details]\n\n"
        "[bold]示例[/]:\n"
        "  A cute cat, sitting on a windowsill, golden hour lighting, photorealistic, close-up shot, 8K ultra detailed\n\n"
        "[bold]关键元素[/]:\n"
        "  • 主体 (subject): 主要对象\n"
        "  • 环境 (environment): 在哪里\n"
        "  • 光线 (lighting): golden hour, cinematic, soft, neon\n"
        "  • 风格 (style): photorealistic, anime, cyberpunk, oil painting\n"
        "  • 镜头 (camera shot): close-up, wide angle, aerial view\n"
        "  • 画质 (quality): 8K, ultra detailed, masterpiece",
        title="📝 提示词模板",
        border_style="green",
    ))

    console.print()

    table = Table(title="🎨 风格推荐")
    table.add_column("风格", style="cyan")
    table.add_column("描述", style="dim")

    styles = [
        ("Photorealistic", "照片级真实"),
        ("Anime style", "动漫风格"),
        ("Cinematic", "电影感"),
        ("Cyberpunk", "赛博朋克"),
        ("Oil painting", "油画风格"),
        ("Watercolor", "水彩风格"),
        ("Studio Ghibli", "吉卜力风格"),
        ("Pixel art", "像素艺术"),
    ]

    for style_name, desc in styles:
        table.add_row(style_name, desc)

    console.print(table)


@prompt_group.command("save", help="保存提示词")
@click.argument("name")
@click.argument("prompt_text")
@click.option("--category", "-c", default="general", help="分类")
def prompt_save(name, prompt_text, category):
    """保存提示词到本地。"""
    from dy_cli.utils import config

    prompt_file = os.path.join(os.path.expanduser("~/.dy"), "prompts.json")
    os.makedirs(os.path.dirname(prompt_file), exist_ok=True)

    prompts = {}
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, encoding="utf-8") as f:
                prompts = json.load(f)
        except Exception:
            pass

    if category not in prompts:
        prompts[category] = {}

    prompts[category][name] = {
        "prompt": prompt_text,
        "created_at": _get_timestamp(),
    }

    with open(prompt_file, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    success(f"提示词已保存: [{category}] {name}")


@prompt_group.command("list", help="列出保存的提示词")
@click.option("--category", "-c", default=None, help="按分类筛选")
def prompt_list(category):
    """列出已保存的提示词。"""
    from dy_cli.utils import config

    prompt_file = os.path.join(os.path.expanduser("~/.dy"), "prompts.json")

    if not os.path.exists(prompt_file):
        info("没有保存的提示词")
        return

    try:
        with open(prompt_file, encoding="utf-8") as f:
            prompts = json.load(f)
    except Exception as e:
        error(f"读取提示词失败: {e}")
        return

    from rich.table import Table

    table = Table(title="💾 已保存的提示词")
    table.add_column("分类", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("提示词", style="dim", max_width=50)

    for cat, cat_prompts in prompts.items():
        if category and cat != category:
            continue
        for name, data in cat_prompts.items():
            prompt_text = data.get("prompt", "")[:50]
            if len(data.get("prompt", "")) > 50:
                prompt_text += "..."
            table.add_row(cat, name, prompt_text)

    console.print(table)


def _get_timestamp() -> str:
    """获取当前时间戳。"""
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")
